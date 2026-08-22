from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.workflow_enterprise_helpers import activate, policy_source, workflow, write
from workflow_runtime import enterprise


class WorkflowEnterpriseAdapterTests(unittest.TestCase):
    def test_entry_is_evidence_gated_and_local_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); enterprise.record_policy(root,policy_source(root),True); result=enterprise.entry(root,"entp-reference")
        self.assertEqual(result["status"],"blocked"); self.assertTrue(result["local_default"]); self.assertIn("phase11-release-gate-blocked",result["issues"])

    def test_all_controls_are_required_and_activation_is_separately_approved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); controls={key:True for key in enterprise.CONTROL_NAMES}; controls["cost"]=False
            with self.assertRaisesRegex(ValueError,"every enterprise operational control"): enterprise.record_policy(root,policy_source(root,controls),True)
            wid=workflow(root); enterprise.record_policy(root,policy_source(root),True)
            with patch.object(enterprise.release,"evaluate",return_value={"status":"passed","gate_fingerprint":"sha256:"+"a"*64}):
                with self.assertRaisesRegex(ValueError,"explicit approval"): enterprise.activate(root,wid,"entp-reference","tenant-alpha","repo-primary","actor-operator",False)
                result=enterprise.activate(root,wid,"entp-reference","tenant-alpha","repo-primary","actor-operator",True)
        self.assertEqual(result["continuation_mode"],"local"); self.assertIn("Canonical local",result["boundary"])

    def test_parent_child_identity_is_read_only_and_tenant_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); wid=workflow(root); activate(root,wid)
            identity=write(root,"child.json",{"child_workflow_id":"ttw-child-repo","child_run_id":"child-run","child_repository_id":"repo-child","tenant_id":"tenant-alpha"})
            link=enterprise.link(root,wid,identity,"actor-operator",True)
            forged=write(root,"forged-child.json",{"child_workflow_id":"ttw-child-repo-2","child_run_id":"child-run-2","child_repository_id":"repo-child","tenant_id":"tenant-other"})
            with self.assertRaisesRegex(ValueError,"crosses tenant"): enterprise.link(root,wid,forged,"actor-operator",True)
        self.assertEqual(link["authority"],"read-only-reference")

    def test_privacy_and_immutable_policy_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=json.loads((root/policy_source(root)).read_text()); source["secret"]="sk-"+"x"*30; ref=write(root,"unsafe.json",source)
            with self.assertRaisesRegex(ValueError,"privacy-safe"): enterprise.record_policy(root,ref,True)
            enterprise.record_policy(root,policy_source(root),True)
            with self.assertRaisesRegex(ValueError,"immutable"): enterprise.record_policy(root,policy_source(root),True)


if __name__=="__main__": unittest.main()
