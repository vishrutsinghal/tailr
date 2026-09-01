from __future__ import annotations

import importlib.util
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
FIXTURES = ROOT / "tests" / "fixtures" / "workflow_runtime" / "templates"


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


LOCK = load("workflow_template_execution_lock", "scripts/planning-lock.py")
from workflow_runtime import adapter_catalog, adapters, approvals, compiler, executor, ownership, stage_results, start_integration, storage, task_scope


class WorkflowTemplateExecutionTests(unittest.TestCase):
    def _activate(self, root: Path, fixture: dict[str, Any], suffix: str = "") -> tuple[str, str]:
        run_id = f"phase5-{fixture['template_id']}{suffix}"
        LOCK.create(root, "deliver an approved bounded behavior", run_id)
        statement = "Deliver the approved behavior with privacy controls" if fixture["template_id"] == "risk-sensitive" else "Deliver the approved behavior"
        report = {"goal": statement, "guided_delivery": {"mode": "guided-delivery"}, "navigator": {
            "registry_workflow": {"feature_ids": fixture["feature_ids"]},
            "requirement_matrix": [{"display_id": "REQ-01", "statement": statement, "kind": "change", "acceptance_criteria": ["Behavior is proven"], "preserve_rules": ["Existing behavior remains"], "likely_paths": ["src/service.py"], "evidence_plan": ["focused proof"]}],
        }}
        report["workflow_runtime"] = start_integration.draft(report, run_id)
        LOCK.save_start_report(root, run_id, report)
        activated = LOCK.activate(root, run_id, True)
        workflow_id = str(activated["workflow_runtime"]["workflow_id"])
        uid = ownership.show(root, workflow_id)["requirement_uids"][0]
        self.assertEqual(compiler.show(root, workflow_id)["template_id"], fixture["template_id"])
        return workflow_id, uid

    def _approval(self, root: Path, workflow_id: str, stage: dict[str, Any]) -> str:
        action = stage["adapter_action_class"]
        operation = {"write_project": "fix-application", "execute_project": "broad-test-build", "scan_local": "scanner"}.get(action, "other-guarded")
        result = approvals.decide(root, workflow_id, stage_ids=[stage["stage_id"]], action_classes=[action], operation_kind=operation, operation_ref=compiler.show(root, workflow_id)["artifact"], decision="approved", rationale=f"Approve the exact {stage['stage_id']} stage boundary.")
        return result["record"]["approval_id"]

    def _result(self, adapter_id: str, uid: str, stage_id: str, root: Path, workflow_id: str) -> dict[str, Any]:
        samples: dict[str, dict[str, Any]] = {
            "debug-intake": {"outcome":"pass","reproduction_contract_ref":".tailtrail/debug/reproduction.json","requirement_uid":uid,"safety_boundary":"local deterministic reproduction only","status":"captured"},
            "debug-reproduction": {"outcome":"pass","exact_command":"python -m unittest tests.test_reproduction","reproduction_fingerprint":"sha256:reproduction","artifact_ref":".tailtrail/debug/reproduction-result.json","status":"reproduced"},
            "debug-hypothesis": {"outcome":"pass","hypothesis_refs":[".tailtrail/debug/hypothesis.json"],"requirement_uid":uid,"evidence_gaps":[],"cycle":1,"status":"ranked"},
            "debug-experiment": {"outcome":"pass","hypothesis_id":"H1","exact_command":"python -m unittest tests.test_experiment","expected_signal":"deterministic discriminating signal","artifact_ref":".tailtrail/debug/experiment.json","cycle":1},
            "debug-root-cause": {"outcome":"pass","proven_hypothesis":"H1","supporting_evidence_refs":[".tailtrail/debug/experiment.json"],"eliminated_hypothesis_refs":[],"status":"proven"},
            "debug-correction-proposal": {"outcome":"pass","requirement_uid":uid,"root_cause_ref":".tailtrail/debug/root-cause.json","bounded_changed_paths":["src/service.py"],"preserve_rules":["Existing behavior remains"],"validation_plan":["focused regression"],"status":"proposed"},
            "debug-closure": {"outcome":"pass","requirement_results":[{"requirement_uid":uid,"status":"complete"}],"root_cause_ref":".tailtrail/debug/root-cause.json","correction_ref":".tailtrail/debug/correction.json","regression_refs":[".tailtrail/debug/regression.json"],"drift_status":"none","status":"complete"},
            "bootstrap": {"outcome":"pass","target_identity_ref":".tailtrail/target.json","repository_readiness":"ready","policy_refs":[],"manifest_refs":[],"languages":["python"],"host":"local","canonical_state_refs":[".tailtrail/state.json"]},
            "graph-discovery": {"outcome":"pass","graph_ref":".tailtrail/graph.json","graph_version":"v1","inventory_fingerprint":"sha256:graph","freshness":"fresh","likely_callers":[],"likely_tests":[],"read_order":[],"evidence_label":"local-evidence"},
            "clarification-aidlc": {"outcome":"pass","aidlc_mode":"lite","lifecycle_stage":"requirements","approved_requirement_refs":[".tailtrail/anchor.json"],"authority_source":"tailtrail-lite","status":"approved"},
            "planning": {"outcome":"pass","approved_requirement_refs":[".tailtrail/anchor.json"],"impact_map_ref":".tailtrail/impact.json","implementation_slices":[],"evidence_requirements":[],"status":"rejected" if stage_id == "optional-fix-proposal" else "planned"},
            "implementation-boundary": {"outcome":"pass","source_edit_receipt_refs":[".tailtrail/edit.json"],"changed_paths":["src/service.py"],"requirement_uids":[uid],"preservation_status":"preserved","status":"changed"},
            "focused-testing": {"outcome":"pass","exact_command":"python -m unittest tests.test_service","tier":"focused","environment":"local","asserted_behavior":"approved behavior","artifact_ref":".tailtrail/test.json"},
            "review": {"outcome":"pass","finding_refs":[],"requirement_findings":[],"severity_counts":{},"scope_status":"pass","architecture_status":"pass","behavior_status":"pass","maintainability_status":"pass","preservation_status":"pass"},
            "requirement-fulfilment": {"outcome":"pass","requirement_results":[{"requirement_uid":uid,"status":"complete"}],"proof_tier_status":"met","bounded_next_action":"none","status":"complete"},
            "security": {"outcome":"pass","control_type":"vulnerability","finding_summary":{},"artifact_ref":".tailtrail/security.json","evidence_boundary":"local"},
            "quality": {"outcome":"pass","control_type":"quality","finding_summary":{},"artifact_ref":".tailtrail/quality.json","evidence_boundary":"saved-ci-receipt" if stage_id == "ingest-finding" else "local"},
            "handoff": {"outcome":"pass","implementation_refs":[],"validation_refs":[],"remaining_risks":[],"rollout_refs":[],"rollback_refs":[],"operations_refs":[],"status":"ready"},
        }
        result = dict(samples[adapter_id])
        if stage_id == "risk-plan":
            authority_ref = ".tailtrail/authorities/risk.json"
            authority = {"schema_version":"1","type":"tailtrail-workflow-risk-authority","authority_id":"wfrisk-local-test","risk_classes":["privacy"],"status":"approved","policy_refs":["GUARDRAILS.md"],"boundary":"Fixture authority for the exact approved risk class."}
            destination = root / authority_ref; destination.parent.mkdir(parents=True, exist_ok=True); destination.write_text(json.dumps(authority), encoding="utf-8")
            result.update({"risk_classes":["privacy"], "authority_refs":[authority_ref]})
        return result

    def _run_template(self, root: Path, fixture: dict[str, Any]) -> dict[str, Any]:
        workflow_id, uid = self._activate(root, fixture)
        for stage in compiler.show(root, workflow_id)["stages"]:
            approval_id = None
            needs_approval = stage["approval_class"] != "none" or stage["adapter_action_class"] in adapter_catalog.GUARDED_ACTIONS
            if needs_approval:
                waiting = executor.start(root, workflow_id, stage["stage_id"], None)
                self.assertEqual(waiting["status"], "awaiting-approval")
                approval_id = self._approval(root, workflow_id, stage)
            started = executor.start(root, workflow_id, stage["stage_id"], approval_id)
            if stage.get("control_kind"):
                continue
            result_ref = f".tailtrail/results/{stage['stage_id']}.json"
            destination = root / result_ref; destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(self._result(stage["adapter_id"], uid, stage["stage_id"], root, workflow_id)), encoding="utf-8")
            adapters.record(root, workflow_id, stage["stage_id"], stage["adapter_id"], result_ref)
            executor.finish(root, workflow_id, stage["stage_id"])
            canonical = stage_results.show(root, workflow_id, stage["stage_id"])["results"]
            self.assertEqual(len(canonical), 1)
            self.assertEqual(canonical[0]["result_kind"], "transition")
            self.assertEqual(canonical[0]["outcome"], "pass")
        completed = executor.status(root, workflow_id)
        self.assertEqual(completed["workflow_status"], "completed")
        self.assertTrue(completed["terminal"])
        self.assertIsNone(completed["next_stage_id"])
        self.assertTrue(storage.replay(root, workflow_id)["valid"])
        self.assertEqual(completed, executor.status(root, workflow_id))
        if fixture["template_id"] == "review-only":
            self.assertFalse(any(row["adapter_id"] == "implementation-boundary" for row in completed["stages"]))
        return completed

    def test_all_six_templates_complete_from_typed_results(self) -> None:
        fixtures = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(FIXTURES.glob("*.json"))]
        for fixture in fixtures:
            with self.subTest(template=fixture["template_id"]), tempfile.TemporaryDirectory() as temp:
                self._run_template(Path(temp), fixture)

    def test_status_is_read_only_and_missing_authority_stops_before_dispatch(self) -> None:
        fixture = json.loads((FIXTURES / "small-change.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, _ = self._activate(root, fixture, "-authority")
            receipt_path = executor.path(root, workflow_id)
            before = executor.status(root, workflow_id)
            self.assertFalse(receipt_path.exists())
            waiting = executor.start(root, workflow_id, "bootstrap", None)
            self.assertEqual(waiting["status"], "awaiting-approval")
            self.assertEqual(adapters.show(root, workflow_id, "bootstrap")["status"], "not-prepared")
            self.assertEqual(before["next_stage_id"], "bootstrap")

    def test_ci_live_provider_input_blocks_without_inventing_completion(self) -> None:
        fixture = json.loads((FIXTURES / "ci-scanner-remediation.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, uid = self._activate(root, fixture, "-live")
            stage = compiler.show(root, workflow_id)["stages"][0]
            waiting = executor.start(root, workflow_id, stage["stage_id"], None); self.assertEqual(waiting["status"], "awaiting-approval")
            approval_id = self._approval(root, workflow_id, stage); executor.start(root, workflow_id, stage["stage_id"], approval_id)
            result = self._result("quality", uid, "quality", root, workflow_id); result["evidence_boundary"] = "live-provider"
            result_ref = ".tailtrail/results/live.json"; destination = root / result_ref; destination.parent.mkdir(parents=True, exist_ok=True); destination.write_text(json.dumps(result), encoding="utf-8")
            adapters.record(root, workflow_id, "ingest-finding", "quality", result_ref)
            with self.assertRaisesRegex(ValueError, "saved CI/scanner receipt"):
                executor.finish(root, workflow_id, "ingest-finding")
            self.assertEqual(executor.status(root, workflow_id)["workflow_status"], "blocked")

    def test_failed_stage_stops_and_explicit_skip_needs_its_own_approval(self) -> None:
        fixture = json.loads((FIXTURES / "small-change.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, uid = self._activate(root, fixture, "-failure")
            stage = compiler.show(root, workflow_id)["stages"][0]
            executor.start(root, workflow_id, "bootstrap", None)
            approval_id = self._approval(root, workflow_id, stage); executor.start(root, workflow_id, "bootstrap", approval_id)
            failed = self._result("bootstrap", uid, "bootstrap", root, workflow_id); failed["outcome"] = "fail"
            result_ref = ".tailtrail/results/failed.json"; destination = root / result_ref; destination.parent.mkdir(parents=True, exist_ok=True); destination.write_text(json.dumps(failed), encoding="utf-8")
            adapters.record(root, workflow_id, "bootstrap", "bootstrap", result_ref); executor.finish(root, workflow_id, "bootstrap")
            self.assertEqual(executor.status(root, workflow_id)["workflow_status"], "failed")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, _ = self._activate(root, fixture, "-skip")
            task_scope.initialize(root, workflow_id)
            with self.assertRaisesRegex(ValueError, "unknown-or-forged"):
                executor.skip(root, workflow_id, "bootstrap", "unknown")
            plan_ref = compiler.show(root, workflow_id)["artifact"]
            command = [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "workflow", "approvals", "skip", "--root", root.as_posix(), "--workflow-id", workflow_id, "--stage-id", "bootstrap", "--operation-ref", plan_ref, "--reason-code", "duplicate-proof", "--rationale", "Explicitly skip redundant bootstrap proof.", "--approved"]
            recorded = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(recorded.returncode, 0, recorded.stdout + recorded.stderr)
            approval = json.loads(recorded.stdout)["record"]
            result = executor.skip(root, workflow_id, "bootstrap", approval["approval_id"])
            self.assertEqual(next(row for row in result["stages"] if row["stage_id"] == "bootstrap")["status"], "skipped")
            saved = stage_results.show(root, workflow_id, "bootstrap")["results"][0]
            self.assertEqual(saved["outcome"], "skipped")
            transition = next(row for row in reversed(storage.events(root, workflow_id)["events"]) if row["event_type"] == "stage-skipped")
            duplicate = stage_results.record(root, workflow_id, "bootstrap", outcome="skipped", reason_code="stage-skipped-approved",
                idempotency_key="wfidem-" + hashlib.sha256(f"{workflow_id}:bootstrap:{approval['approval_id']}:skip".encode()).hexdigest(),
                transition_event=transition, evidence_refs=[])
            self.assertEqual(duplicate["record_status"], "duplicate-suppressed")
            self.assertEqual(len(stage_results.show(root, workflow_id, "bootstrap")["results"]), 1)

    def test_stale_dispatch_records_explicit_non_transition(self) -> None:
        fixture = json.loads((FIXTURES / "small-change.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "src").mkdir(); owned = root / "src" / "service.py"; owned.write_text("VALUE = 1\n", encoding="utf-8")
            workflow_id, _ = self._activate(root, fixture, "-stale-result")
            executor.start(root, workflow_id, "bootstrap", None)
            owned.write_text("VALUE = 2\n", encoding="utf-8")
            result = executor.start(root, workflow_id, "bootstrap", None)
            rows = stage_results.show(root, workflow_id, "bootstrap")["results"]

        self.assertEqual(result["status"], "freshness-stale")
        self.assertEqual(rows[-1]["result_kind"], "non-transition")
        self.assertEqual(rows[-1]["outcome"], "stale")


if __name__ == "__main__":
    unittest.main()
