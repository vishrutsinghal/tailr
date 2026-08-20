from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


LOCK = load("dwr3_lock_test", "scripts/planning-lock.py")
from workflow_runtime import evidence


class WorkflowEvidenceTests(unittest.TestCase):
    def _workflow(self, root: Path, run_id: str) -> tuple[str, str]:
        command = [sys.executable, (ROOT / "scripts" / "task-start.py").as_posix(), "fix a bounded validation rule", "--root", root.as_posix(), "--planning-run-id", run_id, "--format", "json"]
        started = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        activated = LOCK.activate(root, run_id, True)
        return activated["workflow_runtime"]["workflow_id"], activated["workflow_runtime"]["state"]

    def test_collect_is_reference_only_and_resume_preserves_unaffected_passed_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, state = self._workflow(root, "dwr3-collect")
            collected = evidence.collect(root, workflow_id)
            refreshed = evidence.refresh(root, workflow_id, ["source-edit"])
            continuation = evidence.resume(root, workflow_id)

        self.assertEqual(state, "compiled")
        self.assertFalse(collected["reused"])
        self.assertIn("bootstrap", continuation["preserved_passed_stage_ids"])
        self.assertIn("implement", continuation["stale_stage_ids"])
        self.assertEqual(continuation["next_stage"], "implement")
        self.assertEqual(refreshed["freshness_events"][-1]["change_types"], ["source-edit"])

    def test_freshness_matrix_covers_eight_change_types_without_staling_doc_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, _ = self._workflow(root, "dwr3-matrix")
            evidence.collect(root, workflow_id)
            matrix = {}
            for change_type in sorted(evidence.CHANGE_TYPES):
                refreshed = evidence.refresh(root, workflow_id, [change_type])
                matrix[change_type] = refreshed["freshness_events"][-1]["stale_stage_ids"]

        self.assertEqual(set(matrix), evidence.CHANGE_TYPES)
        self.assertEqual(matrix["doc-only-edit"], [])
        self.assertIn("implement", matrix["source-edit"])
        self.assertIn("discover", matrix["manifest-change"])
        self.assertIn("discover", matrix["graph-stale"])
        self.assertIn("bootstrap", matrix["branch-change"])
        self.assertIn("bootstrap", matrix["policy-change"])
        self.assertIn("discover", matrix["dependency-add"])
        self.assertIn("review", matrix["security-finding"])

    def test_completion_receipt_is_fail_closed_and_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, _ = self._workflow(root, "dwr3-close")
            report = {"run_id": "dwr3-close", "overall_status": "evidence-incomplete", "run_artifact": ".tailtrail/runs/dwr3-close/completion-reports/report-1.json"}
            receipt = evidence.sync_closure(root, "dwr3-close", report)
            validation = evidence.validate(root, workflow_id)

        self.assertEqual(receipt["state"], "evidence-incomplete")
        self.assertNotEqual(receipt["state"], "completed")
        self.assertTrue(validation["valid"])

    def test_evidence_schemas_are_closed(self) -> None:
        evidence_schema = json.loads((ROOT / "schemas" / "workflow-evidence.schema.json").read_text(encoding="utf-8"))
        receipt_schema = json.loads((ROOT / "schemas" / "workflow-completion-receipt.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(evidence_schema["additionalProperties"])
        self.assertFalse(receipt_schema["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
