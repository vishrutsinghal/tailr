from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import test_workflow_template_execution as template_support
from workflow_runtime import evidence_completion, ownership, release


METRICS={"approval_prompts":1,"false_approvals":0,"stale_recomputations":1,"resume_checks":1,"resume_accurate":True,"duplicate_executions":0,"false_interventions":0,"correction_cycles":0,"recovery_safe":True,"review_effort":"moderate","estimated_token_receipts":1,"measured_token_receipts":1}
FIXTURES=template_support.FIXTURES


class WorkflowRealRunTests(unittest.TestCase):
    def test_all_supported_templates_accept_sanitized_completed_local_run_proof(self) -> None:
        helper=template_support.WorkflowTemplateExecutionTests(); accepted=set()
        for fixture_path in sorted(FIXTURES.glob("*.json")):
            fixture=json.loads(fixture_path.read_text())
            with self.subTest(template=fixture["template_id"]), tempfile.TemporaryDirectory() as temp:
                root=Path(temp); completed=helper._run_template(root,fixture); wid=completed["workflow_id"]; binding=ownership.show(root,wid)
                evidence_completion.receipt(root,wid,{"run_id":binding["tailtrail_run_id"],"overall_status":"complete","run_artifact":None})
                refs=[]
                for host in sorted(release.HOST.HOSTS):
                    ref=f".tailtrail/incoming/{host}.json"; path=root/ref; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps({"host":host,"run_id":binding["tailtrail_run_id"]})); refs.append(ref)
                observation={"proof_id":f"wfrp-{fixture['template_id']}","workflow_id":wid,"tailtrail_run_id":binding["tailtrail_run_id"],"host_receipt_refs":refs,"requirements":{"complete":True,"preserved":True,"unresolved_drift":0},"metrics":METRICS}; ref=".tailtrail/incoming/real-run.json"; (root/ref).write_text(json.dumps(observation))
                with patch.object(release.HOST,"validate_receipt",side_effect=lambda _root,host,_payload:{"evaluation":"passed","host":host}): proof=release.record_real_run(root,wid,ref,True)
                accepted.add(proof["template_id"]); self.assertEqual(proof["status"],"accepted"); self.assertNotIn("token_savings",json.dumps(proof))
        self.assertEqual(accepted,release.TEMPLATES)

    def test_real_run_rejects_incomplete_completion_missing_hosts_and_material_issues(self) -> None:
        helper=template_support.WorkflowTemplateExecutionTests(); fixture=json.loads((FIXTURES/"small-change.json").read_text())
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); wid,_=helper._activate(root,fixture,"-real-negative"); binding=ownership.show(root,wid); ref=".tailtrail/incoming/real-run.json"; path=root/ref; path.parent.mkdir(parents=True)
            source={"proof_id":"wfrp-negative","workflow_id":wid,"tailtrail_run_id":binding["tailtrail_run_id"],"host_receipt_refs":[],"requirements":{"complete":True,"preserved":True,"unresolved_drift":0},"metrics":METRICS}; path.write_text(json.dumps(source))
            with self.assertRaisesRegex(ValueError,"canonical completion"): release.record_real_run(root,wid,ref,True)


if __name__=="__main__": unittest.main()
