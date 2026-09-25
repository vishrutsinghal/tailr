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
LOCK = load("pm2_facade_lock_test", "planning_lock.py")
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
            activated = FACADE.approve(root, None)
            status = FACADE.status(root, None)
            continued = FACADE.continue_run(root, None, None)
        self.assertEqual(discussion["run_id"], "facade-run")
        self.assertEqual(activated["state"], "plan-approved")
        self.assertEqual(status["workflow_id"], activated["workflow_id"])
        self.assertEqual(continued["workflow_id"], activated["workflow_id"])
        self.assertEqual(continued["state"], "stage-awaiting-approval")
        self.assertNotIn("--run-id", discussion["next_action"])
        self.assertNotIn("--run-id", activated["next_action"])

    def test_facade_presentation_mode_is_user_selectable(self) -> None:
        value = {"verb":"status","run_id":"one-run","state":"awaiting-approval","next_action":"Approve.","boundary":"Read only."}
        for mode in ("quick", "guided", "expert"):
            rendered = FACADE.render(value, mode=mode, verbose=mode == "expert")
            self.assertIn(f"Presentation: {mode}", rendered)

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

    def test_host_decisions_record_list_and_validate(self) -> None:
        decisions = load("pm2_host_decision_test", "host-decision.py")
        schema = json.loads((ROOT / "schemas" / "host-decision.schema.json").read_text(encoding="utf-8"))
        from workflow_runtime import contracts
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            LOCK.create(root, "decision contract test", "d-run")
            self.assertEqual(decisions.latest(root, "d-run"), None)
            first = decisions.record(root, "d-run", "approve", "approved", option="approve",
                                     rationale="Plan looks right.", host="claude",
                                     prior_state="awaiting-approval", resulting_state="plan-approved")
            second = decisions.record(root, "d-run", "discuss", "asked")
            entries = decisions.list_decisions(root, "no-run")
            self.assertEqual(entries, [])
            entries = decisions.list_decisions(root, "d-run")
            self.assertEqual([entry["decision_id"] for entry in entries],
                             [first["decision_id"], second["decision_id"]])
            self.assertEqual(decisions.latest(root, "d-run")["decision_id"], second["decision_id"])
            for entry in entries:
                self.assertEqual(contracts.validate_document(entry, schema), [])
            self.assertEqual(first["option"], "approve")
            self.assertIsNone(second["option"])
            self.assertIsNone(second["rationale"])
        with self.assertRaises(ValueError):
            decisions.record(root, "d-run", "execute", "approved")
        with self.assertRaises(ValueError):
            decisions.record(root, "d-run", "approve", "  ")
        with self.assertRaises(ValueError):
            decisions.record(root, "../escape", "approve", "approved")

    def test_discuss_approve_close_record_decisions_and_status_surfaces_last(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._planned(root, "decision-run")
            FACADE.discuss(root, "decision-run", "Why this scope?")
            FACADE.approve(root, "decision-run", rationale="Scope is bounded.", option="approve")
            status = FACADE.status(root, "decision-run")
            last = status["last_host_decision"]
            self.assertEqual(last["verb"], "approve")
            self.assertEqual(last["decision"], "approved")
            self.assertEqual(last["rationale"], "Scope is bounded.")
            with mock.patch.object(FACADE.CLOSURE, "close", return_value={"state": "awaiting-acceptance"}) as close:
                FACADE.close(root, "decision-run", None, None, None, None, rationale="Evidence reviewed.")
            close.assert_called_once()
            again = FACADE.status(root, "decision-run")
            self.assertEqual(again["last_host_decision"]["verb"], "close")
            self.assertEqual(again["last_host_decision"]["rationale"], "Evidence reviewed.")

    def test_planning_direct_verbs_record_decisions(self) -> None:
        decisions = load("pm2_host_decision_direct_test", "host-decision.py")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._planned(root, "direct-run")
            LOCK.approve(root, "direct-run", True, rationale="Direct approval.")
            self._planned(root, "feedback-run")
            template = LOCK.feedback_template(root, "feedback-run")
            uids = [row["requirement_uid"] for row in template["requirements"]]
            self.assertTrue(uids)
            LOCK.record_feedback(root, "feedback-run", json.dumps(
                [{"requirement_uid": uids[0], "decision": "reject", "comment": "Needs a narrower path."}]
            ))
            entries = decisions.list_decisions(root, "direct-run")
            feedback_entries = decisions.list_decisions(root, "feedback-run")
        self.assertEqual([entry["verb"] for entry in entries], ["approve"])
        self.assertEqual(entries[0]["rationale"], "Direct approval.")
        self.assertEqual(entries[0]["resulting_state"], "approved")
        self.assertEqual([entry["verb"] for entry in feedback_entries], ["revise"])
        self.assertIn(uids[0], feedback_entries[0]["rationale"])

    def test_planning_activate_records_decision(self) -> None:
        decisions = load("pm2_host_decision_activate_test", "host-decision.py")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._planned(root, "activate-run")
            LOCK.activate(root, "activate-run", True, rationale="Activate it.")
            entries = decisions.list_decisions(root, "activate-run")
        activates = [entry for entry in entries if entry["verb"] == "activate"]
        self.assertEqual(len(activates), 1)
        self.assertEqual(activates[0]["rationale"], "Activate it.")

    def test_public_flow_status_and_direct_status_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._planned(root, "cli-run")
            for prefix in (["flow","status"],["status"]):
                result = subprocess.run([sys.executable,(ROOT/"scripts"/"tailtrail.py").as_posix(),*prefix,"--root",root.as_posix(),"--run-id","cli-run","--format","json"],cwd=ROOT,text=True,capture_output=True,check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)["run_id"], "cli-run")

if __name__ == "__main__": unittest.main()
