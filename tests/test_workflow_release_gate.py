from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from workflow_runtime import release


class WorkflowReleaseGateTests(unittest.TestCase):
    def test_empty_gate_is_blocked_and_retirement_never_removes_compatibility(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); gate=release.evaluate(root)
            with self.assertRaisesRegex(ValueError,"exact current passing"): release.retire(root,gate["gate_fingerprint"],True)
        self.assertEqual(gate["status"],"blocked"); self.assertTrue(gate["retirement_requires_separate_approval"])
        self.assertIn("scenario-coverage-incomplete",gate["issues"]); self.assertIn("host-conformance-incomplete",gate["issues"])

    def test_complete_evidence_logic_passes_but_retirement_is_still_separate(self) -> None:
        scenarios=[{"scenario_id":value,"outcome":"passed"} for value in release.SCENARIOS]
        metrics={"approval_prompts":1,"false_approvals":0,"stale_recomputations":1,"resume_checks":1,"resume_accurate":True,"duplicate_executions":0,"false_interventions":0,"correction_cycles":1,"recovery_safe":True,"review_effort":"moderate","measured_token_receipts":1,"estimated_token_receipts":1}
        proofs=[{"template_id":value,"status":"accepted","metrics":metrics} for value in release.TEMPLATES]
        hosts={"runtime_conformance":[{"host":host,"runtime_status":"passed"} for host in sorted(release.HOST.HOSTS)]}
        compatibility={"status":"passed","report_fingerprint":"sha256:compat"}
        with tempfile.TemporaryDirectory() as temp, patch.object(release,"show",return_value={"scenarios":scenarios,"real_runs":proofs}), patch.object(release.HOST,"report",return_value=hosts), patch.object(release,"compatibility",return_value=compatibility):
            root=Path(temp); gate=release.evaluate(root); decision=release.retire(root,gate["gate_fingerprint"],True)
        self.assertEqual(gate["status"],"passed"); self.assertEqual(decision["state"],"approved-for-separate-release-change")
        self.assertIn("does not remove --no-workflow",decision["boundary"])

    def test_migration_report_preserves_history_retention_hosts_and_rollback(self) -> None:
        report=release.compatibility(Path(__file__).resolve().parents[1])
        self.assertEqual(report["status"],"passed",report); self.assertFalse(report["automatic_history_migration"]); self.assertEqual(report["aliases"],[])
        self.assertTrue(report["installed_pack_complete"]); self.assertTrue(report["no_workflow_documented"]); self.assertTrue(report["retention_manual_only"]); self.assertTrue(report["rollback_documented"]); self.assertTrue(all(report["host_guidance"].values()))


if __name__=="__main__": unittest.main()
