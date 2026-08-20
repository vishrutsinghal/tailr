from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module; spec.loader.exec_module(module); return module


LOCK = load("dwr0_contract_lock", ROOT / "scripts" / "planning-lock.py")
from workflow_runtime import capabilities, compiler, contracts, evidence, ownership, reason_codes, storage, task_scope, templates


class WorkflowContractTests(unittest.TestCase):
    def test_aidlc_mode_fixtures_validate_without_sensitive_content(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "workflow_runtime"
        modes = set()
        for path in sorted(fixture_root.glob("aidlc-*.json")):
            payload = json.loads(path.read_text(encoding="utf-8")); modes.add(payload["aidlc"]["mode"])
            self.assertEqual(contracts.validate_artifact(payload), [], path.name)
            self.assertNotIn("prompt", json.dumps(payload).lower())
        self.assertEqual(modes, {"off", "lite", "standard", "full"})

    def test_each_new_contract_validates_a_real_example(self) -> None:
        examples = [
            {"schema_version":"1","type":"tailtrail-workflow-stage","stage_id":"focused-test","capability_ids":["evidence-aware-testing"],"prerequisites":["implement"],"input_schema_ref":"schemas/workflow-evidence-record.schema.json","output_schema_ref":"schemas/workflow-evidence-record.schema.json","required_evidence_types":["focused-validation"],"approval_class":"stage","action_classes":["execute_project"],"retry_policy":{"eligible":False,"max_attempts":1},"freshness_inputs":["source-edit"],"completion_rule":"A linked focused receipt passes.","skip_rule":{"allowed":False,"reason_code":None},"failure_behavior":"blocked","status":"pending"},
            {"schema_version":"1","type":"tailtrail-workflow-action","action_id":"wfa-focused-test","stage_id":"focused-test","action_class":"execute_project","operation_ref":".tailtrail/operations/focused-test.json","idempotency_key":"sha256:action","requires_approval":True,"status":"proposed"},
            {"schema_version":"1","type":"tailtrail-workflow-transition","scope":"workflow","subject_id":"ttw-contract","from_state":"running","to_state":"completed","reason_code":"workflow-completed","legal":True},
            {"schema_version":"1","type":"tailtrail-workflow-approval-record","approval_id":"wfauth-1234567890abcdef12345678","workflow_id":"ttw-contract","tailtrail_run_id":"run-contract","revision":1,"compiler_plan_fingerprint":"sha256:plan","stage_graph_fingerprint":"sha256:graph","target_identity_fingerprint":"sha256:target","approved_anchor_fingerprint":"sha256:anchor","stage_ids":["focused-test"],"action_classes":["execute_project"],"operation_kind":"broad-test-build","bounded_operation_ref":".tailtrail/operations/focused-test.json","scope_ref":".tailtrail/scopes/focused-test.json","scope_fingerprint":"sha256:scope","requirement_uids":["run-contract:REQ-01:v1"],"decision":"approved","source":"interactive","created_at":"2026-08-20T00:00:00+00:00","expires_at":None,"session_id":None,"policy_ref":None,"policy_fingerprint":"sha256:policy","rationale":"User approved the bounded focused-test operation.","skip_reason_code":None,"reason_code":"approval-granted","authority_boundary":"Runtime authority only; canonical approvals remain separate."},
            {"schema_version":"1","type":"tailtrail-workflow-evidence-record","evidence_id":"wfev-1","workflow_id":"ttw-contract","stage_id":"focused-test","requirement_uids":["REQ-01"],"evidence_type":"focused-validation","artifact_ref":".tailtrail/evidence/test.json","artifact_hash":"sha256:evidence","outcome":"pass","label":"local-evidence"},
            {"schema_version":"1","type":"tailtrail-workflow-context-receipt","workflow_id":"ttw-contract","stage_id":"focused-test","selected_refs":["src/validation.py"],"avoided_categories":["unrelated-docs"],"exactness":"must-be-exact","token_posture":"estimated"},
            {"schema_version":"1","type":"tailtrail-workflow-completion-contract","workflow_id":"ttw-contract","requirement_status":"complete","harness_status":"pass","unresolved_drift":0,"evidence_status":"complete","overall_status":"complete","completion_report_ref":".tailtrail/completion/report.json"},
            {"schema_version":"1","type":"tailtrail-workflow-runtime-event","event_id":"wfrt-1","workflow_id":"ttw-contract","sequence":1,"event_type":"stage-passed","stage_id":"focused-test","reason_code":"workflow-completed","artifact_refs":[".tailtrail/evidence/test.json"],"summary":"Focused validation passed."},
        ]
        for example in examples:
            with self.subTest(contract=example["type"]): self.assertEqual(contracts.validate_artifact(example), [])

    def test_malformed_unknown_private_unsafe_and_oversized_artifacts_fail_closed(self) -> None:
        base = json.loads((ROOT / "tests" / "fixtures" / "workflow_runtime" / "aidlc-lite.json").read_text(encoding="utf-8"))
        cases = []
        cases.append({**base, "schema_version":"2"})
        cases.append({**base, "unexpected":True})
        cases.append({**base, "raw_prompt":"do not retain"})
        cases.append({**base, "planning_lock_ref":"../outside.json"})
        cases.append({**base, "boundary":"x" * (contracts.MAX_ARTIFACT_BYTES + 1)})
        for payload in cases:
            self.assertTrue(contracts.validate_artifact(payload))

    def test_transition_table_file_and_reason_codes_match_runtime_authority(self) -> None:
        saved = json.loads((ROOT / "schemas" / "workflow-transition-table-v1.json").read_text(encoding="utf-8"))
        self.assertEqual({key:set(value) for key, value in saved["workflow"].items()}, reason_codes.WORKFLOW_TRANSITIONS)
        self.assertEqual({key:set(value) for key, value in saved["stage"].items()}, reason_codes.STAGE_TRANSITIONS)
        self.assertTrue(reason_codes.transition_allowed("workflow", "running", "completed"))
        self.assertFalse(reason_codes.transition_allowed("workflow", "completed", "running"))

    def test_all_compiler_template_stages_resolve_to_implemented_registry_features(self) -> None:
        registry = json.loads((ROOT / "tailtrail-registry.json").read_text(encoding="utf-8"))
        features = {item["id"]: item for item in registry["features"]}
        for template_id, stages in templates.TEMPLATES.items():
            for stage in stages:
                with self.subTest(template=template_id, stage=stage["stage_id"]):
                    self.assertIn(stage["capability_id"], features)
                    self.assertEqual(features[stage["capability_id"]]["status"], "implemented")

    def test_persisted_runtime_artifacts_validate_against_registered_schemas(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); run_id = "dwr0-real"; workflow_id = ownership.suggested_id(run_id)
            LOCK.create(root, "validate DWR-0 contracts", run_id)
            LOCK.save_start_report(root, run_id, {"goal":"validate DWR-0 contracts","guided_delivery":{"mode":"guided-delivery"},"navigator":{"requirement_matrix":[{"display_id":"REQ-01","statement":"Validate contracts","kind":"change","acceptance_criteria":["Contracts validate"],"preserve_rules":["No project work"],"likely_paths":["schemas/"],"evidence_plan":["contract tests"]}]}})
            LOCK.activate(root, run_id, True); ownership.bind(root, run_id, workflow_id)
            capabilities.propose(root, workflow_id, ["code-graph-mapper","requirement-completion-harness","evidence-aware-testing","review"])
            task_scope.initialize(root, workflow_id); storage.initialize(root, workflow_id); compiler.compile(root, workflow_id); evidence.collect(root, workflow_id)
            evidence.sync_closure(root, run_id, {"run_id":run_id,"overall_status":"evidence-incomplete","run_artifact":None})
            directory = root / ".tailtrail" / "workflows" / workflow_id
            artifacts = [json.loads(path.read_text(encoding="utf-8")) for path in directory.glob("*.json")]
            events = [json.loads(line) for line in (directory / "journal-v1.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertGreaterEqual(len(artifacts), 7)
        for artifact in [*artifacts, *events]:
            with self.subTest(kind=artifact.get("type")): self.assertEqual(contracts.validate_artifact(artifact), [])


if __name__ == "__main__": unittest.main()
