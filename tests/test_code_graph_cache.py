"""Phase 1 focused check: core code-graph cache infrastructure.

Run: python -m unittest tests.test_code_graph_cache -v
"""

from __future__ import annotations

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

    def test_mapper_shaped_cache_is_reported_not_touched(self) -> None:
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
        self.assertEqual(code, 2)
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(raw["schema_version"], "1")
        self.assertEqual(len(raw["graph"]["symbols"]), 1)


if __name__ == "__main__":
    unittest.main()
