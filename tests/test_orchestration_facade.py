from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader
    sys.modules[name] = module; spec.loader.exec_module(module); return module

FACADE = load("pm2_facade_test", "orchestration_facade.py")
LOCK = load("pm2_facade_lock_test", "planning-lock.py")
from workflow_runtime import start_integration

class OrchestrationFacadeTests(unittest.TestCase):
    def _planned(self, root: Path, run_id: str) -> None:
        LOCK.create(root, "add a focused validation rule", run_id)
        report = {"goal":"add a focused validation rule","guided_delivery":{"mode":"guided-delivery"},"aidlc_mode":{"mode":"lite"},"navigator":{
            "registry_workflow":{"feature_ids":["navigator","requirement-completion-harness","evidence-aware-testing"]},
            "requirement_matrix":[{"display_id":"REQ-01","statement":"Reject invalid values","kind":"change","acceptance_criteria":["Invalid values are rejected"],"preserve_rules":["Valid values remain valid"],"likely_paths":["src/validation.py"],"evidence_plan":["focused test"]}]}}
        report["workflow_runtime"] = start_integration.draft(report, run_id)
        LOCK.save_start_report(root, run_id, report)

    def test_safe_resolver_rejects_ambiguous_active_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._planned(root, "run-one"); self._planned(root, "run-two")
            with self.assertRaisesRegex(ValueError, "multiple matching"):
                FACADE.resolve_run(root, None, states={"awaiting-approval"})

    def test_discuss_approve_status_continue_share_one_run_and_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._planned(root, "facade-run")
            discussion = FACADE.discuss(root, None, "Why is src/validation.py selected?")
            activated = FACADE.approve(root, "facade-run")
            status = FACADE.status(root, "facade-run")
            continued = FACADE.continue_run(root, "facade-run", None)
        self.assertEqual(discussion["run_id"], "facade-run")
        self.assertEqual(activated["state"], "plan-approved")
        self.assertEqual(status["workflow_id"], activated["workflow_id"])
        self.assertEqual(continued["workflow_id"], activated["workflow_id"])
        self.assertEqual(continued["state"], "stage-awaiting-approval")

    def test_stage_approval_is_exact_and_prepares_only_next_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._planned(root, "stage-run"); FACADE.approve(root, "stage-run")
            FACADE.continue_run(root, "stage-run", None); result = FACADE.approve(root, "stage-run")
        self.assertEqual(result["state"], "stage-running")
        self.assertEqual(result["approval"]["stage_ids"], [result["stage_id"]])

    def test_close_delegates_to_canonical_closure_service(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._planned(root, "close-run"); FACADE.approve(root, "close-run")
            with mock.patch.object(FACADE.CLOSURE, "close", return_value={"state":"awaiting-acceptance","completion_report":"report.json"}) as close:
                result = FACADE.close(root, "close-run", None, None, None, None)
        close.assert_called_once(); self.assertEqual(result["state"], "awaiting-acceptance")

    def test_public_flow_status_and_direct_status_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._planned(root, "cli-run")
            for prefix in (["flow","status"],["status"]):
                result = subprocess.run([sys.executable,(ROOT/"scripts"/"tailtrail.py").as_posix(),*prefix,"--root",root.as_posix(),"--run-id","cli-run","--format","json"],cwd=ROOT,text=True,capture_output=True,check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)["run_id"], "cli-run")

if __name__ == "__main__": unittest.main()
