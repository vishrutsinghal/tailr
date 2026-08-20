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


LOCK = load("dwr4_lock_test", "scripts/planning-lock.py")
EXECUTION = load("dwr4_execution_test", "scripts/execution-evidence.py")
from workflow_runtime import evidence, vertical


class WorkflowVerticalTests(unittest.TestCase):
    def _setup(self, root: Path, run_id: str) -> tuple[str, str]:
        (root / "src").mkdir(); (root / "tests").mkdir()
        (root / "src" / "validation.py").write_text("def validate(value):\n    return value > 0\n", encoding="utf-8")
        (root / "tests" / "test_validation.py").write_text("import unittest\n", encoding="utf-8")
        command = [sys.executable, (ROOT / "scripts" / "task-start.py").as_posix(), "fix a bounded validation rule", "--root", root.as_posix(), "--planning-run-id", run_id, "--changed", "src/validation.py", "--changed", "tests/test_validation.py", "--format", "json"]
        started = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        activated = LOCK.activate(root, run_id, True)
        workflow_id = activated["workflow_runtime"]["workflow_id"]
        anchor = json.loads((root / ".tailtrail" / "runs" / run_id / "anchors" / "approved-v1.json").read_text(encoding="utf-8"))
        return workflow_id, anchor["requirements"][0]["requirement_uid"]

    def test_proven_vertical_requires_saved_host_facts_then_finalizes_complete_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, uid = self._setup(root, "dwr4-vertical")
            before = vertical.status(root, workflow_id)
            EXECUTION.append(root, "dwr4-vertical", {"kind": "source-edit", "requirement_uids": [uid], "changed_paths": ["src/validation.py", "tests/test_validation.py"]}, True)
            EXECUTION.append(root, "dwr4-vertical", {"kind": "command-result", "requirement_uids": [uid], "changed_paths": ["src/validation.py", "tests/test_validation.py"], "tier": "unit", "command_label": "focused validation", "command": "python -m unittest tests.test_validation", "outcome": "pass", "environment": "local", "asserted_behavior": "positive values remain valid and zero is rejected"}, True)
            after = vertical.status(root, workflow_id)
            result = vertical.finalize(root, workflow_id)
            receipt = evidence.receipt_path(root, workflow_id).is_file()

        self.assertEqual(before["status"], "evidence-needed")
        self.assertEqual(after["status"], "ready-to-finalize")
        self.assertEqual(result["vertical_status"], "complete")
        self.assertEqual(result["receipt_state"], "completed")
        self.assertTrue(receipt)

    def test_vertical_does_not_close_or_retry_when_evidence_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, _ = self._setup(root, "dwr4-gap")
            result = vertical.finalize(root, workflow_id)
            reports = root / ".tailtrail" / "runs" / "dwr4-gap" / "completion-reports"

        self.assertEqual(result["vertical_status"], "evidence-incomplete")
        self.assertFalse(reports.exists())

    def test_vertical_rejects_non_small_change_templates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, _ = self._setup(root, "dwr4-template")
            plan_path = root / ".tailtrail" / "workflows" / workflow_id / "compiler-plan-v1.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8")); plan["template_id"] = "delivery"; plan_path.write_text(json.dumps(plan), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "small-change"):
                vertical.status(root, workflow_id)


if __name__ == "__main__":
    unittest.main()
