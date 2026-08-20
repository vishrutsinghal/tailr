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


lock = load("workflow_start_lock_test", "scripts/planning-lock.py")
from workflow_runtime import start_integration


class WorkflowStartIntegrationTests(unittest.TestCase):
    def _start(self, root: Path, run_id: str, no_workflow: bool = False) -> dict[str, object]:
        command = [sys.executable, (ROOT / "scripts" / "task-start.py").as_posix(), "fix a bounded validation rule", "--root", root.as_posix(), "--planning-run-id", run_id, "--format", "json"]
        if no_workflow: command.append("--no-workflow")
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_start_creates_only_a_draft_until_the_exact_plan_is_approved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); report = self._start(root, "dwr2-draft")
            draft = report["workflow_runtime"]
            workflow_dir = root / ".tailtrail" / "workflows" / draft["workflow_id"]
            saved = lock.active_start_report(root, "dwr2-draft")["report"]
            workflow_exists_before_approval = workflow_dir.exists()

        self.assertTrue(draft["enabled"])
        self.assertEqual(draft["state"], "draft")
        self.assertFalse(workflow_exists_before_approval)
        self.assertEqual(saved["workflow_runtime"]["workflow_id"], draft["workflow_id"])

    def test_stage_approval_schema_is_closed(self) -> None:
        schema = json.loads((ROOT / "schemas" / "workflow-stage-approvals.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["type"]["const"], "tailtrail-workflow-stage-approvals")

    def test_activation_creates_the_canonical_runtime_and_compiler_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); report = self._start(root, "dwr2-activate")
            activated = lock.activate(root, "dwr2-activate", True)
            runtime = activated["workflow_runtime"]
            compiler_artifact = root / runtime["compiler"]["artifact"]
            compiler_exists = compiler_artifact.is_file()
            state_view = subprocess.run([sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "workflow", "state", "show", "--root", root.as_posix(), "--workflow-id", runtime["workflow_id"]], cwd=ROOT, text=True, capture_output=True, check=False)

        self.assertEqual(runtime["state"], "compiled")
        self.assertTrue(compiler_exists)
        self.assertEqual(json.loads(state_view.stdout)["current_stage"], "not-executing")
        self.assertEqual(activated["execution_handoff"]["workflow_runtime"]["compiler"]["template_id"], runtime["compiler"]["template_id"])

    def test_no_workflow_is_a_compatibility_escape_hatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); report = self._start(root, "dwr2-no-workflow", no_workflow=True)
            activated = lock.activate(root, "dwr2-no-workflow", True)

        self.assertFalse(report["workflow_runtime"]["enabled"])
        self.assertEqual(activated["workflow_runtime"]["state"], "disabled")
        self.assertFalse((root / ".tailtrail" / "workflows").exists())

    def test_policy_and_session_stage_approvals_are_recorded_but_non_executing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); report = self._start(root, "dwr2-approvals")
            policy = {"schema_version": "1", "type": "tailtrail-workflow-compiler-policy", "required_capabilities": [], "forbidden_capabilities": [], "stage_prerequisites": {}, "pre_approved_stages": ["bootstrap"]}
            policy_path = root / ".tailtrail" / "workflow-compiler-policy-v1.json"; policy_path.write_text(json.dumps(policy), encoding="utf-8")
            activated = lock.activate(root, "dwr2-approvals", True); workflow_id = activated["workflow_runtime"]["workflow_id"]
            session = start_integration.grant_session(root, workflow_id, ["read-only"], True)
            validated = start_integration.validate_approvals(root, workflow_id)

        sources = {item["source"] for item in session["approvals"]}
        self.assertIn("policy", sources); self.assertIn("session", sources); self.assertIn("interactive", sources)
        self.assertTrue(validated["valid"])

    def test_guide_remains_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = subprocess.run([sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "guide", "fix a bounded validation rule", "--root", root.as_posix()], cwd=ROOT, text=True, capture_output=True, check=False)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((root / ".tailtrail" / "workflows").exists())
        self.assertFalse((root / ".tailtrail" / "runs").exists())


if __name__ == "__main__":
    unittest.main()
