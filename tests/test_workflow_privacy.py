from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.test_workflow_security import setup_workflow
from workflow_runtime import assurance, context, contracts, ownership


class WorkflowPrivacyTests(unittest.TestCase):
    def test_cases_7_8_paths_sensitive_content_and_size_are_rejected(self) -> None:
        base={"schema_version":"1","type":"tailtrail-workflow-context-receipt","workflow_id":"ttw-private","stage_id":"bootstrap","selected_refs":[".tailtrail/a.json"],"avoided_categories":[],"exactness":"must-be-exact","token_posture":"estimated","context_budget_tokens":1,"reduction_status":"not-requested","retrieval_refs":[],"receipt_fingerprint":"sha256:x","boundary":"safe"}
        cases=[{**base,"selected_refs":["../outside"]},{**base,"selected_refs":["/absolute"]},{**base,"raw_prompt":"hostile"},{**base,"email":"person@example.invalid"},{**base,"boundary":"AKIA"+"A"*16},{**base,"boundary":"x"*(contracts.MAX_ARTIFACT_BYTES+1)}]
        for payload in cases:
            with self.subTest(payload=list(payload)[-1]): self.assertTrue(contracts.validate_artifact(payload))

    def test_case_9_untrusted_command_event_is_rejected_and_never_executed(self) -> None:
        marker="never-created-by-command"
        event={"schema_version":"1","type":"tailtrail-workflow-runtime-event","event_id":"wfrt-command","workflow_id":"ttw-private","sequence":1,"event_type":"stage-passed","stage_id":"bootstrap","reason_code":"stage-passed","artifact_refs":[],"summary":"categorical","command":f"touch {marker}"}
        self.assertTrue(contracts.validate_artifact(event)); self.assertFalse(Path(marker).exists())

    def test_case_18_measured_tokens_require_linked_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); run,wid=setup_workflow(root,"phase10-telemetry")
            source=root/".tailtrail"/"fake.json"; source.write_text(json.dumps({"workflow_id":wid,"tailtrail_run_id":run,"stage_id":"bootstrap","provider":"host","usage":{}}))
            with self.assertRaisesRegex(ValueError,"total_tokens"):
                context.record_telemetry(root,wid,"bootstrap",".tailtrail/fake.json")
            self.assertFalse(context.telemetry_path(root,wid,"bootstrap").exists())

    def test_case_19_learning_and_evaluation_reject_raw_data(self) -> None:
        learning={"schema_version":"1","type":"tailtrail-workflow-learning-link","workflow_id":"ttw-private","tailtrail_run_id":"run","completion_receipt_ref":".tailtrail/c.json","learning_kind":"positive","candidate_id":"candidate","promotion":"candidate-only","artifact_fingerprint":"sha256:x","boundary":"safe","source_body":"private"}
        evaluation={"schema_version":"1","type":"tailtrail-workflow-evaluation-event","workflow_id":"ttw-private","tailtrail_run_id":"run","template_id":"small-change","stage_outcomes":{},"stale_recomputation_count":0,"correction_cycle_count":0,"approval_count":0,"requirement_completion":"incomplete","closure_state":"evidence-incomplete","event_fingerprint":"sha256:x","boundary":"Bearer "+"A"*30}
        self.assertTrue(contracts.validate_artifact(learning)); self.assertTrue(contracts.validate_artifact(evaluation))

    def test_assurance_reports_only_categorical_privacy_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); _run,wid=setup_workflow(root,"phase10-assurance")
            hostile="ghp_"+"A"*30; path=ownership.binding_path(root,wid).parent/"hostile.json"; path.write_text(json.dumps({"note":hostile}))
            result=assurance.inspect(root,wid); encoded=json.dumps(result)
        self.assertEqual(result["status"],"blocked"); self.assertIn("privacy-violation",encoded); self.assertNotIn(hostile,encoded)


if __name__ == "__main__": unittest.main()
