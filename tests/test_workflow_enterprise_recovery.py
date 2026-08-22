from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.workflow_enterprise_helpers import activate, event, workflow
from workflow_runtime import enterprise, enterprise_recovery, enterprise_transport, ownership


class WorkflowEnterpriseRecoveryTests(unittest.TestCase):
    def prepared(self, root: Path) -> tuple[str,dict,dict]:
        wid=workflow(root); activate(root,wid); lease=enterprise_transport.acquire(root,wid,"tenant-alpha","actor-operator",True); enterprise_transport.ingest(root,wid,event(root,wid,lease),True); backup=enterprise_recovery.backup(root,wid,True); return wid,lease,backup

    def test_backup_restore_migration_and_exact_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); wid,_lease,backup=self.prepared(root); restored=enterprise_recovery.restore_validate(root,backup["artifact"]); plan=enterprise_recovery.migration_plan(root,wid,"local-to-enterprise")
            with self.assertRaisesRegex(ValueError,"exact current"): enterprise_recovery.migrate(root,wid,"local-to-enterprise","sha256:wrong",True)
            applied=enterprise_recovery.migrate(root,wid,"local-to-enterprise",plan["migration_fingerprint"],True)
            with self.assertRaisesRegex(ValueError,"exact applied"): enterprise_recovery.rollback(root,wid,"sha256:wrong",True)
            rolled=enterprise_recovery.rollback(root,wid,applied["migration_fingerprint"],True)
            self.assertEqual(enterprise.show(root,wid)["continuation_mode"],"local")
        self.assertEqual(restored["status"],"passed"); self.assertFalse(restored["canonical_state_replaced"]); self.assertEqual(rolled["state"],"rolled-back")

    def test_stale_backup_and_unapproved_operations_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); wid,_lease,backup=self.prepared(root)
            with self.assertRaisesRegex(ValueError,"explicit approval"): enterprise_recovery.backup(root,wid,False)
            ownership.binding_path(root,wid).write_text("{}",encoding="utf-8"); result=enterprise_recovery.restore_validate(root,backup["artifact"])
        self.assertEqual(result["status"],"blocked"); self.assertIn("backup-artifact-stale",result["issues"])

    def test_conformance_covers_isolation_replay_recovery_cost_privacy_and_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); wid,_lease,_backup=self.prepared(root); report=enterprise_recovery.conformance(root,wid)
        self.assertEqual(report["status"],"passed",report); self.assertTrue(all(report["checks"].values())); self.assertIn("provider deployment",report["boundary"])

    def test_backup_count_limit_requires_manual_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); wid=workflow(root); activate(root,wid,{"lease_seconds":300,"max_events_per_workflow":2,"max_backups":1,"retained_events":2}); lease=enterprise_transport.acquire(root,wid,"tenant-alpha","actor-operator",True); enterprise_transport.ingest(root,wid,event(root,wid,lease),True); enterprise_recovery.backup(root,wid,True)
            with self.assertRaisesRegex(ValueError,"manual cleanup"): enterprise_recovery.backup(root,wid,True)

    def test_forged_backup_artifact_path_cannot_escape_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); _wid,_lease,backup=self.prepared(root); value=json.loads((root/backup["artifact"]).read_text()); value["artifact_hashes"]={"../outside.json":"sha256:"+"0"*64}; value["backup_fingerprint"]=""; value["backup_fingerprint"]=enterprise.digest({key:item for key,item in value.items() if key!="backup_fingerprint"}); forged=root/"forged-backup.json"; forged.write_text(json.dumps(value),encoding="utf-8"); result=enterprise_recovery.restore_validate(root,"forged-backup.json")
        self.assertEqual(result["status"],"blocked"); self.assertIn("backup-artifact-stale",result["issues"])


if __name__=="__main__": unittest.main()
