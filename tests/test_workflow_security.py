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
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader
    sys.modules[name] = module; spec.loader.exec_module(module); return module


LOCK = load("phase10_security_lock", "scripts/planning-lock.py")
MCP = load("phase10_security_mcp", "scripts/mcp-server.py")
from workflow_runtime import approvals, compiler, contracts, denials, ownership, retry, start_integration, state, storage, task_scope, transitions


def setup_workflow(root: Path, run_id: str = "phase10-run", features: list[str] | None = None) -> tuple[str, str]:
    selected = features or ["code-graph-mapper", "requirement-completion-harness", "evidence-aware-testing", "review"]
    report = {"goal":"prove negative assurance", "guided_delivery":{"mode":"guided-delivery"}, "navigator":{"registry_workflow":{"feature_ids":selected}, "requirement_matrix":[{"display_id":"REQ-01","statement":"Preserve fail-closed controls","kind":"change","acceptance_criteria":["Negative paths stop"],"preserve_rules":["No mutation on denial"],"likely_paths":["scripts/"],"evidence_plan":["negative tests"]}]}}
    report["workflow_runtime"] = start_integration.draft(report, run_id)
    LOCK.create(root, report["goal"], run_id); LOCK.save_start_report(root, run_id, report)
    activated = LOCK.activate(root, run_id, True); workflow_id = activated["workflow_runtime"]["workflow_id"]
    task_scope.initialize(root, workflow_id); transitions.ensure_stages(root, workflow_id)
    return run_id, workflow_id


class WorkflowSecurityTests(unittest.TestCase):
    def test_cases_1_3_4_forgery_annotation_and_cross_workflow_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); _run,wid=setup_workflow(root,"phase10-authority")
            plan=compiler.show(root,wid); approved=approvals.decide(root,wid,stage_ids=["bootstrap"],action_classes=["read_local"],operation_kind="other-guarded",operation_ref=plan["artifact"],decision="approved",rationale="Exact bounded read.")["record"]
            note=ownership.binding_path(root,wid).parent/"operator-note.txt"; note.write_text("benign annotation",encoding="utf-8")
            self.assertEqual(approvals.authorize_stage(root,wid,"bootstrap",approved["approval_id"])["approval_id"],approved["approval_id"])
            ledger=approvals.path(root,wid); payload=json.loads(ledger.read_text()); payload["approvals"][0]["approval_id"]="wfauth-"+"0"*24; ledger.write_text(json.dumps(payload))
            self.assertFalse(approvals.validate(root,wid)["valid"])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); _run,first=setup_workflow(root,"phase10-first"); foreign=approvals.decide(root,first,stage_ids=["bootstrap"],action_classes=["read_local"],operation_kind="other-guarded",operation_ref=compiler.show(root,first)["artifact"],decision="approved",rationale="First workflow only.")["record"]
            state.cancel(root,first,True); _run,second=setup_workflow(root,"phase10-second")
            with self.assertRaises(ValueError): approvals.authorize_stage(root,second,"bootstrap",foreign["approval_id"])

    def test_cases_2_10_11_12_modified_plan_retry_provider_and_session_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); _run,wid=setup_workflow(root,"phase10-guards")
            with self.assertRaisesRegex(ValueError,"only read_local/write_tailtrail_state"):
                approvals.grant_session(root,wid,["execute_project"],True)
            with self.assertRaisesRegex(ValueError,"only read_local/write_tailtrail_state"):
                approvals.grant_session(root,wid,["external_provider"],True)
            decision=retry.decide(root,wid,"implement")
            self.assertFalse(decision["eligible"]); self.assertIn("never retry",decision["reason"])
            approval=approvals.decide(root,wid,stage_ids=["bootstrap"],action_classes=["read_local"],operation_kind="other-guarded",operation_ref=compiler.show(root,wid)["artifact"],decision="approved",rationale="Frozen plan only.")["record"]
            plan_path=root/compiler.show(root,wid)["artifact"]; changed=json.loads(plan_path.read_text()); changed["revision"]+=1; plan_path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError): approvals.authorize_stage(root,wid,"bootstrap",approval["approval_id"])

    def test_case_15_other_workflow_reservation_and_receipts_are_not_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); run,wid=setup_workflow(root,"phase10-owner")
            binding=ownership.show(root,wid)
            forged={**binding,"workflow_id":"ttw-foreign","tailtrail_run_id":"other-run"}
            self.assertTrue(contracts.validate_artifact(forged))
            with self.assertRaises(ValueError): ownership.show(root,"ttw-foreign")
            self.assertEqual(ownership.show(root,wid)["tailtrail_run_id"],run)

    def test_denied_mcp_action_records_only_categorical_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); _run,wid=setup_workflow(root,"phase10-denial")
            hostile="Bearer "+"A"*30
            with self.assertRaises(ValueError): MCP.call_tool("workflow_retention_cleanup",{"root":root.as_posix(),"workflow_id":wid,"plan_fingerprint":hostile,"approved":True})
            audit=denials.show(root,wid); encoded=json.dumps(audit)
        self.assertEqual(audit["denials"][-1]["source"],"mcp")
        self.assertNotIn(hostile,encoded); self.assertNotIn("Bearer",encoded)


if __name__ == "__main__": unittest.main()
