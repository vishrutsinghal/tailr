from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
    return module


task_start = load("debug_orientation_task_start", "scripts/task-start.py")
reproduction = load("debug_orientation_reproduction", "scripts/debug-reproduction.py")
orientation = load("debug_orientation_subject", "scripts/debug-orientation.py")
from workflow_runtime import contracts


class DebugOrientationTests(unittest.TestCase):
    def _approved(self, root: Path, run_id: str = "debug-orientation") -> dict:
        source = root / "src" / "payments.py"; source.parent.mkdir(parents=True); source.write_text("def charge():\n    return 'ok'\n", encoding="utf-8")
        graph = orientation.GRAPH.build_graph(root, ["src/payments.py"], "debug", [], 20)
        orientation.GRAPH.write_cache(root / "tailtrail-meta" / "code-graph-cache.json", graph)
        report = task_start.build_report("payments are charged twice after timeout", root, [], "python3 scripts/tailtrail.py")
        lock = task_start.planning_lock.create(root, report["goal"], run_id=run_id); report["planning_lock"] = lock
        task_start.planning_lock.save_start_report(root, run_id, report)
        initial = task_start.planning_lock.activate(root, run_id, True)
        contract = initial["reproduction_contract"]
        revised = reproduction.draft(root, run_id, {
            "requirement_uid": contract["requirement_uid"], "domain": "api-integration", "trigger": contract["trigger"],
            "expected": "one payment effect", "actual": "two payment effects",
            "reproduction_method": "run local timeout-after-acceptance test", "preserve_rules": ["single worker remains valid"],
            "safety_boundary": "local adapters only",
        })
        return reproduction.approve(root, run_id, revised["revision"])

    def test_fresh_cache_is_reused_and_new_file_proposes_incremental_refresh(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved(root)
            first = orientation.create(root, "debug-orientation")
            self.assertEqual(first["cache"]["status"], "fresh")
            self.assertEqual(first["refresh_proposal"]["state"], "not-needed")
            self.assertTrue(any(row["path"] == "src/payments.py" for row in first["confirmed_paths"]))
            self.assertEqual(first["stage_id"], "d-03-project-orientation")
            self.assertEqual(first["status"], "awaiting-reproduction-evidence")
            self.assertFalse((root / "src" / "payments.py").read_text(encoding="utf-8") == "")

            (root / "src" / "new_worker.py").write_text("# new untracked source\n", encoding="utf-8")
            second = orientation.create(root, "debug-orientation")
            self.assertEqual(second["revision"], 2)
            self.assertEqual(second["cache"]["status"], "stale")
            self.assertEqual(second["refresh_proposal"]["kind"], "incremental")
            self.assertIn("graph refresh", second["refresh_proposal"]["command"])
            self.assertTrue((root / ".tailtrail" / "runs" / "debug-orientation" / "debug" / "orientation" / "orientation-v2.json").is_file())

            schema = json.loads((ROOT / "schemas" / "debug-orientation.schema.json").read_text(encoding="utf-8"))
            self.assertEqual(contracts.validate_document({key: value for key, value in second.items() if key != "artifact"}, schema), [])

    def test_orientation_requires_approved_native_debug_handoff(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "required debug artifact"):
                orientation.create(Path(temp), "missing-run")


if __name__ == "__main__":
    unittest.main()
