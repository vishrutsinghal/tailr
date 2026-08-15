from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lock = load("planning_investigation_lock_test", "scripts/planning-lock.py")
investigation = load("planning_investigation_test", "scripts/planning-investigation.py")


class PlanningInvestigationTests(unittest.TestCase):
    def plan(self, root: Path, run_id: str = "investigation") -> Path:
        source = root / "src" / "service.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("def cancel_order():\n    return True\n", encoding="utf-8")
        test = root / "tests" / "test_service.py"
        test.parent.mkdir(parents=True, exist_ok=True)
        test.write_text("def test_cancel_order():\n    assert True\n", encoding="utf-8")
        lock.create(root, "add cancellation", run_id)
        lock.save_start_report(root, run_id, {
            "goal": "add cancellation",
            "navigator": {
                "likely_impacted_files": [
                    {"path": "src/service.py", "reason": "saved caller path"},
                    {"path": "tests/test_service.py", "reason": "focused proof"},
                ],
                "graph_cache": {"status": "fresh"},
            },
        })
        return source

    def test_requires_explicit_read_only_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.plan(root)
            with self.assertRaisesRegex(ValueError, "approved-read-only"):
                investigation.investigate(root, "investigation", ["src/service.py"], False)

    def test_reads_only_planned_path_and_records_sanitized_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = self.plan(root)
            before = source.read_text(encoding="utf-8")
            result = investigation.investigate(root, "investigation", ["src/service.py"], True)
            persisted = (root / result["artifact"]).read_text(encoding="utf-8")
            shown = investigation.show(root, "investigation")
            after = source.read_text(encoding="utf-8")

        self.assertEqual(result["paths_read"], ["src/service.py"])
        self.assertEqual(result["commands_run"], [])
        self.assertFalse(result["source_changed"])
        self.assertFalse(result["tests_run"])
        self.assertIn("cancel_order", result["source_facts"][0]["symbols"])
        self.assertNotIn("return True", persisted)
        self.assertEqual(before, after)
        self.assertEqual(shown["investigation_id"], "investigation-001")

    def test_rejects_outside_root_and_unplanned_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.plan(root)
            (root / "src" / "private.py").write_text("SECRET = 'no'\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "outside the saved planned"):
                investigation.investigate(root, "investigation", ["src/private.py"], True)
            with self.assertRaisesRegex(ValueError, "repository-relative"):
                investigation.investigate(root, "investigation", ["../outside.py"], True)

    def test_detects_stale_graph_without_rebuilding_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = self.plan(root)
            original = source.read_bytes()
            cache_dir = root / "tailtrail-meta"; cache_dir.mkdir()
            cache = {
                "schema_version": "1",
                "root": root.as_posix(),
                "scope": ["src/service.py"],
                "source_files": {"src/service.py": {"sha256": hashlib.sha256(original).hexdigest()}},
            }
            (cache_dir / "code-graph-cache.json").write_text(json.dumps(cache), encoding="utf-8")
            source.write_text("def cancel_order():\n    return False\n", encoding="utf-8")
            result = investigation.investigate(root, "investigation", ["src/service.py"], True)

        self.assertEqual(result["graph_evidence"]["status"], "stale")
        self.assertFalse(result["graph_evidence"]["reused"])
        self.assertTrue(any("changed after" in item for item in result["graph_evidence"]["reasons"]))


if __name__ == "__main__":
    unittest.main()
