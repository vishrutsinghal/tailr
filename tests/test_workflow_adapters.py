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
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module; spec.loader.exec_module(module); return module


lock = load("workflow_adapter_lock_test", "scripts/planning-lock.py")
from workflow_runtime import adapter_catalog, adapters, approvals, contracts, start_integration, task_scope


class WorkflowAdapterTests(unittest.TestCase):
    def _activated(self, root: Path, run_id: str) -> tuple[str, dict[str, object]]:
        lock.create(root, "deliver one controlled change", run_id)
        report = {"goal": "deliver one controlled change", "guided_delivery": {"mode": "guided-delivery"}, "navigator": {
            "registry_workflow": {"feature_ids": ["canonical-local-state", "code-graph-mapper", "requirement-completion-harness", "evidence-aware-testing", "review"]},
            "requirement_matrix": [{"display_id": "REQ-01", "statement": "Deliver the approved behavior", "kind": "change", "acceptance_criteria": ["Behavior is proven"], "preserve_rules": ["Existing behavior remains"], "likely_paths": ["src/service.py"], "evidence_plan": ["focused test"]}],
        }}
        report["workflow_runtime"] = start_integration.draft(report, run_id); lock.save_start_report(root, run_id, report)
        activated = lock.activate(root, run_id, True); runtime = activated["workflow_runtime"]
        task_scope.initialize(root, str(runtime["workflow_id"]))
        return str(runtime["workflow_id"]), runtime

    def _samples(self) -> dict[str, dict[str, object]]:
        return {
            "bootstrap": {"outcome":"pass","target_identity_ref":".tailtrail/target.json","repository_readiness":"ready","policy_refs":[],"manifest_refs":[],"languages":["python"],"host":"local","canonical_state_refs":[".tailtrail/state.json"]},
            "graph-discovery": {"outcome":"pass","graph_ref":".tailtrail/graph.json","graph_version":"v1","inventory_fingerprint":"sha256:graph","freshness":"fresh","likely_callers":[],"likely_tests":[],"read_order":[],"evidence_label":"local-evidence"},
            "clarification-aidlc": {"outcome":"pass","aidlc_mode":"lite","lifecycle_stage":"requirements","approved_requirement_refs":[".tailtrail/anchor.json"],"authority_source":"tailtrail-lite","status":"approved"},
            "planning": {"outcome":"pass","approved_requirement_refs":[".tailtrail/anchor.json"],"impact_map_ref":".tailtrail/impact.json","implementation_slices":[],"evidence_requirements":[],"status":"planned"},
            "implementation-boundary": {"outcome":"pass","source_edit_receipt_refs":[".tailtrail/edit.json"],"changed_paths":["src/service.py"],"requirement_uids":["run:REQ-01:v1"],"preservation_status":"preserved","status":"changed"},
            "focused-testing": {"outcome":"pass","exact_command":"python -m unittest tests.test_service","tier":"focused","environment":"local","asserted_behavior":"approved behavior","artifact_ref":".tailtrail/test.json"},
            "review": {"outcome":"pass","finding_refs":[],"requirement_findings":[],"severity_counts":{},"scope_status":"pass","architecture_status":"pass","behavior_status":"pass","maintainability_status":"pass","preservation_status":"pass"},
            "requirement-fulfilment": {"outcome":"pass","requirement_results":[],"proof_tier_status":"met","bounded_next_action":"none","status":"complete"},
            "security": {"outcome":"pass","control_type":"vulnerability","finding_summary":{},"artifact_ref":".tailtrail/security.json","evidence_boundary":"local"},
            "quality": {"outcome":"pass","control_type":"quality","finding_summary":{},"artifact_ref":".tailtrail/quality.json","evidence_boundary":"local"},
            "handoff": {"outcome":"pass","implementation_refs":[],"validation_refs":[],"remaining_risks":[],"rollout_refs":[],"rollback_refs":[],"operations_refs":[],"status":"ready"},
        }

    def test_catalog_maps_every_adapter_to_one_implemented_registry_capability(self) -> None:
        result = adapters.catalog()
        self.assertTrue(result["valid"]); self.assertEqual(len(result["adapters"]), 18)
        for row in result["adapters"]:
            contract = adapters.contract(row["adapter_id"])
            self.assertEqual(contract["capability_id"], row["capability_id"])
            self.assertTrue(contract["registered_scripts"] or contract["registered_commands"])

    def test_every_adapter_accepts_its_typed_result_and_rejects_missing_evidence(self) -> None:
        for adapter_id, sample in self._samples().items():
            definition = adapters.contract(adapter_id)
            with self.subTest(adapter=adapter_id):
                adapters._validate_result(definition, sample)
                output = {"schema_version":"1","type":"tailtrail-workflow-adapter-output","workflow_id":"ttw-contract","stage_id":adapter_id,"adapter_id":adapter_id,"capability_id":definition["capability_id"],"action_class":definition["action_class"],"authority":definition["authority"],"idempotency_key":"wfidem-contract","requirement_uids":["REQ-01"],"outcome":sample["outcome"],"result":sample,"evidence_refs":[],"recorded_at":"2026-08-20T00:00:00+00:00","boundary":"Factual result only."}
                self.assertEqual(contracts.validate_artifact(output), [])
                broken = dict(sample); broken.pop(definition["required_outputs"][0])
                with self.assertRaisesRegex(ValueError, "missing typed fields"):
                    adapters._validate_result(definition, broken)

    def test_official_aidlc_and_graph_proof_boundaries_fail_closed(self) -> None:
        standard = dict(self._samples()["clarification-aidlc"], aidlc_mode="standard", authority_source="tailtrail-lite")
        with self.assertRaisesRegex(ValueError, "official AIDLC authority"):
            adapters._validate_result(adapters.contract("clarification-aidlc"), standard)
        graph = dict(self._samples()["graph-discovery"], evidence_label="proof")
        with self.assertRaisesRegex(ValueError, "cannot be labelled as proof"):
            adapters._validate_result(adapters.contract("graph-discovery"), graph)

    def test_prepare_and_record_are_schema_valid_idempotent_and_non_executing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, runtime = self._activated(root, "adapter-bootstrap")
            approval = approvals.decide(root, workflow_id, stage_ids=["bootstrap"], action_classes=["read_local"], operation_kind="other-guarded", operation_ref=runtime["compiler"]["artifact"], decision="approved", rationale="Approve only the typed bootstrap read.")["record"]
            prepared = adapters.prepare(root, workflow_id, "bootstrap", "bootstrap", approval["approval_id"])
            repeated = adapters.prepare(root, workflow_id, "bootstrap", "bootstrap", approval["approval_id"])
            result_ref = ".tailtrail/adapter-result.json"; result_path = root / result_ref; result_path.parent.mkdir(exist_ok=True)
            result_path.write_text(json.dumps(self._samples()["bootstrap"]), encoding="utf-8")
            recorded = adapters.record(root, workflow_id, "bootstrap", "bootstrap", result_ref)
            duplicate = adapters.record(root, workflow_id, "bootstrap", "bootstrap", result_ref)
            validation = adapters.validate(root, workflow_id, "bootstrap")

        self.assertEqual(prepared["dispatch_status"], "prepared")
        self.assertEqual(repeated["dispatch_status"], "already-prepared")
        self.assertEqual(recorded["record_status"], "recorded")
        self.assertEqual(duplicate["record_status"], "duplicate-suppressed")
        self.assertTrue(validation["valid"])
        self.assertNotIn("command", prepared)

    def test_guarded_implementation_requires_exact_action_authority_and_rejects_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, runtime = self._activated(root, "adapter-guarded")
            with self.assertRaisesRegex(ValueError, "approval_id=required"):
                adapters.prepare(root, workflow_id, "implement", "implementation-boundary")
            wrong = approvals.decide(root, workflow_id, stage_ids=["implement"], action_classes=["write_tailtrail_state"], operation_kind="other-guarded", operation_ref=runtime["compiler"]["artifact"], decision="approved", rationale="Insufficient metadata-only approval.")["record"]
            with self.assertRaisesRegex(ValueError, "compiler stage action class"):
                adapters.prepare(root, workflow_id, "implement", "implementation-boundary", wrong["approval_id"])
            correct = approvals.decide(root, workflow_id, stage_ids=["implement"], action_classes=["write_project"], operation_kind="fix-application", operation_ref=runtime["compiler"]["artifact"], decision="approved", rationale="Approve this exact source-edit boundary.")["record"]
            prepared = adapters.prepare(root, workflow_id, "implement", "implementation-boundary", correct["approval_id"])
            with self.assertRaisesRegex(ValueError, "not stage capability"):
                adapters.prepare(root, workflow_id, "implement", "focused-testing", correct["approval_id"])

        self.assertEqual(prepared["action_class"], "write_project")

    def test_closed_schemas_reject_raw_output_and_arbitrary_top_level_fields(self) -> None:
        output = {"schema_version":"1","type":"tailtrail-workflow-adapter-output","workflow_id":"ttw-contract","stage_id":"review","adapter_id":"review","capability_id":"review","action_class":"read_local","authority":"tailtrail-review","idempotency_key":"wfidem-contract","requirement_uids":["REQ-01"],"outcome":"pass","result":self._samples()["review"],"evidence_refs":[],"recorded_at":"2026-08-20T00:00:00+00:00","boundary":"Factual result only."}
        self.assertEqual(contracts.validate_artifact(output), [])
        self.assertTrue(contracts.validate_artifact({**output, "command": "arbitrary"}))
        private = dict(output); private["result"] = {**private["result"], "raw_log": "sensitive"}
        self.assertTrue(contracts.validate_artifact(private))


if __name__ == "__main__": unittest.main()
