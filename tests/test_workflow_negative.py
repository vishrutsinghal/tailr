from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_workflow_security import ROOT, setup_workflow
from workflow_runtime import adapter_catalog, assurance, compiler, contracts, evidence, freshness, reason_codes, retention, state, storage, templates


def load(name: str, relative: str):
    spec=importlib.util.spec_from_file_location(name,ROOT/relative); module=importlib.util.module_from_spec(spec); assert spec and spec.loader
    sys.modules[name]=module; spec.loader.exec_module(module); return module


HOST=load("phase10_negative_host","scripts/host-adapter-conformance.py")


class WorkflowNegativeTests(unittest.TestCase):
    def test_case_5_gap_duplicate_hash_and_interrupted_journals_preserve_projection(self) -> None:
        mutations=("gap","duplicate","hash","interrupted")
        for kind in mutations:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root=Path(temp); _run,wid=setup_workflow(root,f"phase10-storage-{kind}"); path=storage.journal_path(root,wid); before=storage.status(root,wid)["last_valid_projection"]
                lines=path.read_text().splitlines(); event=json.loads(lines[-1])
                if kind=="gap": event["sequence"]+=2; event["event_hash"]=storage._event_hash(event); lines[-1]=json.dumps(event)
                elif kind=="duplicate": lines.append(lines[-1])
                elif kind=="hash": event["event_hash"]="sha256:"+"0"*64; lines[-1]=json.dumps(event)
                else: lines.append("{interrupted")
                path.write_text("\n".join(lines)+"\n")
                replay=storage.replay(root,wid)
                self.assertFalse(replay["valid"]); self.assertEqual(storage.status(root,wid)["last_valid_projection"],before)

    def test_case_6_terminal_transition_is_illegal(self) -> None:
        value={"schema_version":"1","type":"tailtrail-workflow-transition","scope":"workflow","subject_id":"ttw-terminal","from_state":"completed","to_state":"running","reason_code":"workflow-started","legal":True}
        self.assertFalse(reason_codes.transition_allowed("workflow","completed","running"))
        self.assertTrue(contracts.validate_artifact(value))

    def test_case_13_stale_policy_graph_scope_ci_and_completion_cannot_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); run,wid=setup_workflow(root,"phase10-stale"); baseline=freshness.ensure(root,wid)
            (root/"tailtrail-policy.md").write_text("changed policy",encoding="utf-8")
            assessment=freshness.assess(root,wid)
            evidence.sync_closure(root,run,{"run_id":run,"overall_status":"evidence-incomplete","run_artifact":None})
            receipt=json.loads(evidence.receipt_path(root,wid).read_text())
        self.assertTrue(baseline["snapshot_fingerprint"].startswith("sha256:")); self.assertEqual(assessment["status"],"stale")
        self.assertIn("policy-change",assessment["change_types"]); self.assertNotEqual(receipt["state"],"completed")

    def test_case_14_unknown_contract_capability_action_stage_reason_and_template_stop(self) -> None:
        unknown={"schema_version":"2","type":"tailtrail-workflow-stage"}
        self.assertTrue(contracts.validate_artifact(unknown))
        with self.assertRaises(ValueError): adapter_catalog.get("unknown-adapter")
        self.assertNotIn("unknown-template",templates.TEMPLATES)
        self.assertNotIn("unknown-reason",reason_codes.REASON_CODES)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); _run,wid=setup_workflow(root,"phase10-unknown")
            with self.assertRaises(ValueError): state.transition_stage(root,wid,"unknown-stage","running","unknown-reason")

    def test_cases_16_17_cancel_recovery_and_incomplete_evidence_never_claim_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); run,wid=setup_workflow(root,"phase10-cancel")
            cancelled=state.cancel(root,wid,True); evidence.sync_closure(root,run,{"run_id":run,"overall_status":"evidence-incomplete","run_artifact":None})
            receipt=json.loads(evidence.receipt_path(root,wid).read_text())
        self.assertEqual(cancelled["workflow_status"],"cancelled"); self.assertNotIn("rollback",json.dumps(cancelled).lower())
        self.assertTrue(receipt["state"].startswith("evidence-incomplete")); self.assertNotEqual(receipt["state"],"completed")

    def test_case_20_start_report_and_host_stop_rule_remain_explicit(self) -> None:
        body=HOST.render(HOST.load(ROOT)["hosts"][0],HOST.load(ROOT))
        self.assertIn("`tailtrail start` is planning-only",body); self.assertIn("requires approval before implementation",body)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); run,wid=setup_workflow(root,"phase10-host-stop"); report=root/".tailtrail"/"runs"/run/"planning"/"start-report-v1.json"; before=report.read_bytes(); assurance.inspect(root,wid)
            self.assertEqual(report.read_bytes(),before)

    def test_governance_and_manual_retention_are_closed_and_run_history_is_preserved(self) -> None:
        governance=assurance.governance(ROOT); self.assertEqual(governance["status"],"passed",governance)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); run1,wid1=setup_workflow(root,"phase10-retain-1"); state.cancel(root,wid1,True)
            run2,wid2=setup_workflow(root,"phase10-retain-2"); state.cancel(root,wid2,True)
            policy=retention.default_policy(); policy["max_terminal_workflows"]=1; policy["policy_fingerprint"]=retention.policy_fingerprint(policy)
            policy_path=root/".tailtrail"/"retention-policy.json"; policy_path.write_text(json.dumps(policy)); ref=".tailtrail/retention-policy.json"
            planned=retention.plan(root,ref); candidate=planned["candidate_workflow_ids"][0]
            with self.assertRaisesRegex(ValueError,"explicit approval"): retention.cleanup(root,candidate,planned["plan_fingerprint"],ref,False)
            receipt=retention.cleanup(root,candidate,planned["plan_fingerprint"],ref,True)
            kept_run=run1 if candidate==wid1 else run2
            self.assertTrue((root/".tailtrail"/"runs"/kept_run).exists())
        self.assertEqual(receipt["state"],"removed-local-workflow-runtime")
        self.assertFalse(policy["background_deletion"]); self.assertFalse(policy["upload"]); self.assertTrue(policy["manual_cleanup_only"])


if __name__ == "__main__": unittest.main()
