"""Phase 1 focused check: core code-graph cache infrastructure.

Run: python -m unittest tests.test_code_graph_cache -v
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import code_graph_cache as cgc  # noqa: E402


def _load_mapper():
    spec = importlib.util.spec_from_file_location(
        "stage0a_code_graph_mapper", REPO / "scripts" / "code-graph-mapper.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUTH_PY = '''"""Auth module."""
import src.db as db
from src.config import SETTINGS


def login_user(name):
    return db.find(name)


def validate_token(token):
    return token in SETTINGS
'''

DB_PY = '''"""DB module."""


def find(name):
    return {"name": name}
'''


class CodeGraphCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "auth.py").write_text(AUTH_PY, encoding="utf-8")
        (self.root / "src" / "db.py").write_text(DB_PY, encoding="utf-8")
        self.cache_path = self.root / ".tailtrail" / "code-graph-cache.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_mapper_excludes_nested_worktrees_but_keeps_real_files(self) -> None:
        mapper = _load_mapper()
        real = self.root / "src" / "real.py"
        real.write_text("VALUE = 1\n", encoding="utf-8")
        nested = self.root / ".claude" / "worktrees" / "stale" / "src" / "ghost.py"
        nested.parent.mkdir(parents=True)
        nested.write_text("VALUE = 2\n", encoding="utf-8")

        paths = {path.relative_to(self.root).as_posix() for path in mapper.list_text_files(self.root)}

        self.assertIn("src/real.py", paths)
        self.assertNotIn(".claude/worktrees/stale/src/ghost.py", paths)

    def test_load_missing_returns_empty(self) -> None:
        data, error = cgc.load(self.cache_path)
        self.assertEqual(error, "missing")
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["files"], {})

    def test_load_corrupt_never_crashes(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text("not json", encoding="utf-8")
        data, error = cgc.load(self.cache_path)
        self.assertTrue(str(error).startswith("invalid"))
        self.assertEqual(data["files"], {})

    def test_update_creates_file_level_entries(self) -> None:
        summary = cgc.update(self.root, ["src/auth.py", "src/db.py"], path=self.cache_path)
        self.assertEqual(summary["updated"], 2)
        self.assertEqual(summary["errors"], [])
        data, error = cgc.load(self.cache_path)
        self.assertIsNone(error)
        auth = data["files"]["src/auth.py"]
        self.assertIn("login_user", auth["symbols"])
        self.assertIn("validate_token", auth["symbols"])
        self.assertTrue(auth["imports"])
        self.assertGreater(auth["size_bytes"], 0)
        self.assertTrue(auth["last_read"])
        self.assertIn("find", data["files"]["src/db.py"]["symbols"])

    def test_update_is_incremental_and_prunes_missing(self) -> None:
        cgc.update(self.root, ["src/auth.py", "src/db.py"], path=self.cache_path)
        (self.root / "src" / "db.py").unlink()
        summary = cgc.update(self.root, ["src/db.py"], path=self.cache_path)
        self.assertEqual(summary["pruned"], 1)
        data, _ = cgc.load(self.cache_path)
        self.assertIn("src/auth.py", data["files"])
        self.assertNotIn("src/db.py", data["files"])

    def test_invalidate_and_clear(self) -> None:
        cgc.update(self.root, ["src/auth.py", "src/db.py"], path=self.cache_path)
        self.assertEqual(cgc.invalidate(self.cache_path, ["src/db.py"]), 1)
        data, _ = cgc.load(self.cache_path)
        self.assertNotIn("src/db.py", data["files"])
        cgc.clear(self.cache_path)
        data, _ = cgc.load(self.cache_path)
        self.assertEqual(data["files"], {})

    def test_stale_files_detects_modification(self) -> None:
        cgc.update(self.root, ["src/auth.py"], path=self.cache_path)
        data, _ = cgc.load(self.cache_path)
        self.assertEqual(cgc.stale_files(self.root, data), [])
        # Ensure mtime advances past last_read, then modify.
        time.sleep(0.02)
        with (self.root / "src" / "auth.py").open("a", encoding="utf-8") as handle:
            handle.write("\n# touch\n")
        data, _ = cgc.load(self.cache_path)
        self.assertEqual(cgc.stale_files(self.root, data), ["src/auth.py"])

    def test_normalize_drops_malformed_entries(self) -> None:
        data = cgc.normalize_cache({"version": 1, "files": {"ok.py": {"symbols": ["a"]}, "bad": "nope", "": {}}})
        self.assertIn("ok.py", data["files"])
        self.assertNotIn("bad", data["files"])
        self.assertNotIn("", data["files"])
        self.assertEqual(data["files"]["ok.py"]["imports"], [])


class LifecycleCliTests(unittest.TestCase):
    """Phase 7: explicit-request lifecycle operations."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "keep.py").write_text("def keep():\n    return 1\n", encoding="utf-8")
        (self.root / "src" / "gone.py").write_text("def gone():\n    return 0\n", encoding="utf-8")
        cgc.update(self.root, ["src/keep.py", "src/gone.py"])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _run(self, *argv: str) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = cgc.main(["--root", self.root.as_posix(), *argv])
        return code, buffer.getvalue()

    def test_status_reports_counts(self) -> None:
        code, text = self._run("status")
        self.assertEqual(code, 0)
        self.assertIn("Files: `2`", text)

    def test_prune_missing_drops_gone_files(self) -> None:
        (self.root / "src" / "gone.py").unlink()
        code, text = self._run("prune-missing", "--format", "json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text)["removed"], 1)
        data, _ = cgc.load(cgc.default_cache_path(self.root))
        self.assertNotIn("src/gone.py", data["files"])
        self.assertIn("src/keep.py", data["files"])

    def test_invalidate_drops_listed_files(self) -> None:
        code, _ = self._run("invalidate", "--file", "src/gone.py")
        self.assertEqual(code, 0)
        data, _ = cgc.load(cgc.default_cache_path(self.root))
        self.assertNotIn("src/gone.py", data["files"])

    def test_clear_wipes_all(self) -> None:
        code, _ = self._run("clear")
        self.assertEqual(code, 0)
        data, _ = cgc.load(cgc.default_cache_path(self.root))
        self.assertEqual(data["files"], {})

    def test_mapper_shaped_cache_is_reported_and_preserved_on_clear(self) -> None:
        path = cgc.default_cache_path(self.root)
        path.write_text(
            json.dumps({"schema_version": "1", "scope": ["src/keep.py"],
                        "graph": {"symbols": [{"file": "src/keep.py"}]}}),
            encoding="utf-8",
        )
        code, text = self._run("status")
        self.assertEqual(code, 0)
        self.assertIn("mapper-shaped", text)
        code, _ = self._run("clear")
        self.assertEqual(code, 0)
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(raw["schema_version"], 2)
        self.assertEqual(raw["sections"]["mapper_graph"]["graph"]["symbols"], [{"file": "src/keep.py"}])
        self.assertEqual(raw["sections"]["phase1_files"]["files"], {})


class Stage0bContainerTests(unittest.TestCase):
    """Stage 0b: one v2 container, two sections; writers preserve each other."""

    MAPPER_PAYLOAD = {
        "schema_version": "1",
        "graph_mode": "review",
        "scope": ["src/keep.py"],
        "source_files": {"src/keep.py": {"sha256": "x", "mtime": 0, "size": 1}},
        "graph": {"symbols": [{"file": "src/keep.py"}]},
    }
    PHASE1_ENTRY = {
        "last_read": None,
        "symbols": ["keep"],
        "endpoints": [],
        "imports": [],
        "size_bytes": 10,
    }

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "keep.py").write_text("def keep():\n    return 1\n", encoding="utf-8")
        self.cache_path = self.root / ".tailtrail" / "code-graph-cache.json"
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.mapper = _load_mapper()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write(self, payload: dict) -> bytes:
        raw = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
        self.cache_path.write_bytes(raw)
        return raw

    def _phase1_payload(self) -> dict:
        return {"version": 1, "last_updated": None, "files": {"src/keep.py": dict(self.PHASE1_ENTRY)}}

    def test_phase1_load_still_surfaces_mapper_shape_mismatch(self) -> None:
        self._write(dict(self.MAPPER_PAYLOAD))
        data, error = cgc.load(self.cache_path)
        self.assertTrue(str(error).startswith("shape-mismatch"))
        self.assertEqual(data["files"], {})

    def test_phase1_save_migrates_mapper_file_to_container(self) -> None:
        self._write(dict(self.MAPPER_PAYLOAD))
        cgc.save(self.cache_path, cgc.empty_cache())
        raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["schema_version"], 2)
        self.assertEqual(raw["sections"]["mapper_graph"]["graph"]["symbols"], [{"file": "src/keep.py"}])
        self.assertEqual(raw["sections"]["phase1_files"]["files"], {})

    def test_phase1_update_merges_into_mapper_file(self) -> None:
        self._write(dict(self.MAPPER_PAYLOAD))
        summary = cgc.update(self.root, ["src/keep.py"], path=self.cache_path)
        self.assertEqual(summary["updated"], 1)
        self.assertEqual(summary["errors"], [])
        raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["schema_version"], 2)
        self.assertIn("src/keep.py", raw["sections"]["phase1_files"]["files"])
        self.assertEqual(raw["sections"]["mapper_graph"]["graph"]["symbols"], [{"file": "src/keep.py"}])

    def test_invalidate_on_mapper_only_file_changes_nothing(self) -> None:
        before = self._write(dict(self.MAPPER_PAYLOAD))
        self.assertEqual(cgc.invalidate(self.cache_path, ["src/keep.py"]), 0)
        self.assertEqual(self.cache_path.read_bytes(), before)

    def test_mapper_load_on_phase1_file_reports_missing_section(self) -> None:
        before = self._write(self._phase1_payload())
        cache, error = self.mapper.load_cache(self.cache_path)
        self.assertIsNone(cache)
        self.assertIn("mapper_graph", str(error))
        self.assertEqual(self.cache_path.read_bytes(), before)

    def test_mapper_status_on_phase1_file_leaves_bytes_unchanged(self) -> None:
        before = self._write(self._phase1_payload())
        status = self.mapper.status_for(self.root, self._phase1_payload(), ["src/keep.py"])
        self.assertEqual(status["status"], "invalid")
        self.assertTrue(any("mapper_graph" in str(item) for item in status["reasons"]))
        self.assertEqual(self.cache_path.read_bytes(), before)

    def test_mapper_write_migrates_phase1_file_to_container(self) -> None:
        self._write(self._phase1_payload())
        graph = self.mapper.build_graph(self.root, ["src/keep.py"], "review", [], 5)
        self.mapper.write_cache(self.cache_path, graph)
        raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["schema_version"], 2)
        self.assertEqual(raw["sections"]["phase1_files"]["files"]["src/keep.py"]["symbols"], ["keep"])
        self.assertIn("src/keep.py", raw["sections"]["mapper_graph"]["scope"])

    def test_both_writers_round_trip_without_loss(self) -> None:
        cgc.update(self.root, ["src/keep.py"], path=self.cache_path)
        graph = self.mapper.build_graph(self.root, ["src/keep.py"], "review", [], 5)
        self.mapper.write_cache(self.cache_path, graph)
        cgc.update(self.root, ["src/keep.py"], path=self.cache_path)
        raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["schema_version"], 2)
        self.assertIn("src/keep.py", raw["sections"]["phase1_files"]["files"])
        self.assertIn("src/keep.py", raw["sections"]["mapper_graph"]["scope"])
        data, error = cgc.load(self.cache_path)
        self.assertIsNone(error)
        cache, error = self.mapper.load_cache(self.cache_path)
        self.assertIsNone(error)
        self.assertIsNotNone(cache)

    def test_unified_reader_classifies_and_warns(self) -> None:
        container, error = cgc.read_container(self.cache_path)
        self.assertEqual(error, "missing")
        self._write(self._phase1_payload())
        container, error = cgc.read_container(self.cache_path)
        self.assertIsNone(error)
        self.assertEqual(container["kind"], "phase1")
        self.assertTrue(container["warnings"])
        self.assertIsNotNone(container["phase1_files"])
        self.assertIsNone(container["mapper_graph"])
        self._write(dict(self.MAPPER_PAYLOAD))
        container, error = cgc.read_container(self.cache_path)
        self.assertIsNone(error)
        self.assertEqual(container["kind"], "mapper")
        self.assertTrue(container["warnings"])
        graph = self.mapper.build_graph(self.root, ["src/keep.py"], "review", [], 5)
        self.mapper.write_cache(self.cache_path, graph)
        container, error = cgc.read_container(self.cache_path)
        self.assertIsNone(error)
        self.assertEqual(container["kind"], "mapper")
        self.assertIsNone(container["phase1_files"])
        self.assertIsNotNone(container["mapper_graph"])
        cgc.save(self.cache_path, cgc.empty_cache())
        container, error = cgc.read_container(self.cache_path)
        self.assertIsNone(error)
        self.assertEqual(container["kind"], "combined")
        self.assertFalse(container["warnings"])
        self.assertIsNotNone(container["phase1_files"])
        self.assertIsNotNone(container["mapper_graph"])

    def test_unknown_top_level_keys_survive_section_writes(self) -> None:
        payload = dict(self.MAPPER_PAYLOAD)
        payload["custom_tool_state"] = {"pinned": True}
        self._write(payload)
        cgc.save(self.cache_path, cgc.empty_cache())
        raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["sections"]["mapper_graph"]["custom_tool_state"], {"pinned": True})
        raw["tool_note"] = "keep-me"
        self.cache_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
        cgc.update(self.root, ["src/keep.py"], path=self.cache_path)
        raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["tool_note"], "keep-me")
        self.assertEqual(raw["sections"]["mapper_graph"]["custom_tool_state"], {"pinned": True})


class MergeRefreshedFilesTests(unittest.TestCase):
    def _section(self):
        return {
            "schema_version": 1,
            "scope": ["a.py"],
            "source_files": {"a.py": {"sha256": "old-a", "size": 10},
                             "b.py": {"sha256": "keep-b", "size": 20}},
            "graph": {
                "symbols": [
                    {"name": "old", "kind": "function", "file": "a.py", "line": 1},
                    {"name": "keep", "kind": "function", "file": "b.py", "line": 1},
                ],
                "references": [
                    {"target": "x", "referring_file": "a.py", "reference_type": "import"},
                    {"target": "y", "referring_file": "b.py", "reference_type": "import"},
                ],
            },
        }

    def test_replaces_touched_keeps_untouched(self):
        import copy
        before = self._section()
        snapshot = copy.deepcopy(before)
        merged = cgc.merge_refreshed_files(before, [{
            "path": "a.py", "sha256": "new-a",
            "symbols": [{"name": "new", "kind": "function", "file": "a.py", "line": 1}],
            "references": [{"target": "z", "referring_file": "a.py", "reference_type": "import"}],
        }], updated_at="2026-01-01T00:00:00+00:00")
        # Input untouched (pure function).
        self.assertEqual(before, snapshot)
        symbols = {(item["file"], item["name"]) for item in merged["graph"]["symbols"]}
        self.assertEqual(symbols, {("a.py", "new"), ("b.py", "keep")})
        refs = {(item["referring_file"], item["target"]) for item in merged["graph"]["references"]}
        self.assertEqual(refs, {("a.py", "z"), ("b.py", "y")})
        self.assertEqual(merged["source_files"]["a.py"]["sha256"], "new-a")
        self.assertEqual(merged["source_files"]["b.py"]["sha256"], "keep-b")
        self.assertEqual(merged["refreshed_paths"], ["a.py"])
        self.assertEqual(merged["updated_at"], "2026-01-01T00:00:00+00:00")

    def test_malformed_entries_skipped(self):
        merged = cgc.merge_refreshed_files(self._section(), [
            {"path": "", "sha256": "x"},
            {"path": "a.py"},
            "not-a-dict",
            {"path": "c.py", "sha256": "new-c", "symbols": [], "references": []},
        ], updated_at="t")
        self.assertEqual(merged["refreshed_paths"], ["c.py"])
        self.assertEqual(len(merged["refresh_skipped"]), 3)
        self.assertIn("c.py", merged["scope"])

    def test_empty_section_starts_clean(self):
        merged = cgc.merge_refreshed_files(None, [
            {"path": "a.py", "sha256": "s", "symbols": [], "references": []},
        ], updated_at="t")
        self.assertEqual(merged["refreshed_paths"], ["a.py"])
        self.assertEqual(merged["source_files"]["a.py"]["sha256"], "s")


GHOST_REL = ".claude/worktrees/stale/src/ghost.py"


class CachePolicyExclusionTests(unittest.TestCase):
    """Phase 3: stale-role rejection on cache reads plus polluted-section pruning."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "real.py").write_text("VALUE = 1\n", encoding="utf-8")
        nested = self.root / ".claude" / "worktrees" / "stale" / "src" / "ghost.py"
        nested.parent.mkdir(parents=True)
        nested.write_text("VALUE = 2\n", encoding="utf-8")
        self.cache_path = self.root / ".tailtrail" / "code-graph-cache.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_load_with_root_rejects_policy_excluded_entries(self) -> None:
        cgc.update(self.root, ["src/real.py", GHOST_REL], path=self.cache_path)
        data, error = cgc.load(self.cache_path, root=self.root)
        self.assertIsNone(error)
        self.assertIn("src/real.py", data["files"])
        self.assertNotIn(GHOST_REL, data["files"])
        self.assertEqual(data["policy_excluded"], [GHOST_REL])

    def test_load_without_root_keeps_legacy_behavior(self) -> None:
        cgc.update(self.root, ["src/real.py", GHOST_REL], path=self.cache_path)
        data, error = cgc.load(self.cache_path)
        self.assertIsNone(error)
        self.assertIn(GHOST_REL, data["files"])
        self.assertNotIn("policy_excluded", data)

    def test_merge_refreshed_files_rejects_policy_excluded_with_root(self) -> None:
        merged = cgc.merge_refreshed_files(None, [
            {"path": "src/real.py", "sha256": "r",
             "symbols": [{"name": "real", "kind": "function", "file": "src/real.py", "line": 1}],
             "references": []},
            {"path": GHOST_REL, "sha256": "g",
             "symbols": [{"name": "ghost", "kind": "function", "file": GHOST_REL, "line": 1}],
             "references": []},
        ], updated_at="t", root=self.root)
        self.assertEqual(merged["refreshed_paths"], ["src/real.py"])
        self.assertEqual(merged["refresh_policy_excluded"], [GHOST_REL])
        self.assertIn(GHOST_REL, merged["refresh_skipped"])
        self.assertNotIn(GHOST_REL, merged["scope"])
        self.assertNotIn(GHOST_REL, merged["source_files"])
        files = {row["file"] for row in merged["graph"]["symbols"]}
        self.assertNotIn(GHOST_REL, files)

    def _write_polluted_combined_cache(self) -> None:
        cgc.update(self.root, ["src/real.py", GHOST_REL], path=self.cache_path)
        mapper = _load_mapper()
        mapper.write_cache(self.cache_path, {
            "schema_version": "1",
            "root": self.root.as_posix(),
            "scope": ["src/real.py", GHOST_REL],
            "source_files": {"src/real.py": {"sha256": "r"}, GHOST_REL: {"sha256": "g"}},
            "watch_files": {},
            "graph": {
                "symbols": [
                    {"name": "real", "kind": "function", "file": "src/real.py", "line": 1},
                    {"name": "ghost", "kind": "function", "file": GHOST_REL, "line": 1},
                ],
                "references": [
                    {"target": "x", "referring_file": GHOST_REL, "reference_type": "import"},
                ],
            },
        })

    def test_prune_policy_excluded_cleans_both_sections(self) -> None:
        self._write_polluted_combined_cache()
        summary = cgc.prune_policy_excluded(self.root, self.cache_path)
        self.assertEqual(summary["removed_phase1"], 1)
        self.assertEqual(summary["removed_mapper_scope"], [GHOST_REL])
        self.assertEqual(summary["removed_mapper_rows"], 3)
        data, _ = cgc.load(self.cache_path, root=self.root)
        self.assertIn("src/real.py", data["files"])
        self.assertEqual(data["policy_excluded"], [])
        raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
        mapper = raw["sections"]["mapper_graph"]
        self.assertEqual(mapper["scope"], ["src/real.py"])
        self.assertNotIn(GHOST_REL, mapper["source_files"])
        self.assertEqual(
            {(row["file"], row["name"]) for row in mapper["graph"]["symbols"]},
            {("src/real.py", "real")},
        )
        self.assertEqual(mapper["graph"]["references"], [])

    def test_prune_policy_excluded_is_idempotent(self) -> None:
        self._write_polluted_combined_cache()
        cgc.prune_policy_excluded(self.root, self.cache_path)
        before = self.cache_path.read_bytes()
        summary = cgc.prune_policy_excluded(self.root, self.cache_path)
        self.assertEqual(summary["removed_phase1"], 0)
        self.assertEqual(summary["removed_mapper_scope"], [])
        self.assertEqual(summary["removed_mapper_rows"], 0)
        self.assertEqual(self.cache_path.read_bytes(), before)

    def test_cli_prune_excluded_removes_ghosts(self) -> None:
        cgc.update(self.root, ["src/real.py", GHOST_REL])
        path = cgc.default_cache_path(self.root)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = cgc.main(["--root", self.root.as_posix(), "--format", "json", "prune-excluded"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buffer.getvalue())["removed"], 1)
        data, _ = cgc.load(path, root=self.root)
        self.assertIn("src/real.py", data["files"])
        self.assertNotIn(GHOST_REL, data["files"])

    def test_mapper_status_for_flags_policy_excluded_scope(self) -> None:
        mapper = _load_mapper()
        section = {
            "schema_version": "1",
            "root": self.root.as_posix(),
            "scope": ["src/real.py", GHOST_REL],
            "source_files": {"src/real.py": {"sha256": "r"}, GHOST_REL: {"sha256": "g"}},
            "watch_files": {},
        }
        status = mapper.status_for(self.root, section, [])
        self.assertTrue(any("workspace policy" in reason for reason in status["reasons"]))


if __name__ == "__main__":
    unittest.main()
