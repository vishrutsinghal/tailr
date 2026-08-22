from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.workflow_enterprise_helpers import activate, event, workflow, write
from workflow_runtime import enterprise_transport, ownership


class WorkflowEnterpriseTransportTests(unittest.TestCase):
    def test_ordered_ingest_replay_idempotency_and_observability(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); wid=workflow(root); activate(root,wid); lease=enterprise_transport.acquire(root,wid,"tenant-alpha","actor-operator",True); ref=event(root,wid,lease)
            first=enterprise_transport.ingest(root,wid,ref,True); second=enterprise_transport.ingest(root,wid,ref,True); replay=enterprise_transport.replay(root,wid); view=enterprise_transport.observe(root,wid)
        self.assertFalse(first["idempotent"]); self.assertTrue(second["idempotent"]); self.assertTrue(replay["valid"]); self.assertEqual(view["transport_event_count"],1); self.assertTrue(view["read_only"])

    def test_fencing_failover_rejects_old_lease_and_wrong_tenant(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); wid=workflow(root); activate(root,wid); old=enterprise_transport.acquire(root,wid,"tenant-alpha","actor-operator",True); new=enterprise_transport.acquire(root,wid,"tenant-alpha","actor-operator",True)
            with self.assertRaisesRegex(ValueError,"stale or unauthorized"): enterprise_transport.ingest(root,wid,event(root,wid,old),True)
            with self.assertRaisesRegex(ValueError,"tenant boundary"): enterprise_transport.acquire(root,wid,"tenant-other","actor-operator",True)
        self.assertGreater(new["epoch"],old["epoch"]); self.assertNotEqual(new["fencing_token"],old["fencing_token"])

    def test_sequence_cross_run_and_duplicate_conflict_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); wid=workflow(root); activate(root,wid); lease=enterprise_transport.acquire(root,wid,"tenant-alpha","actor-operator",True)
            with self.assertRaisesRegex(ValueError,"sequence"): enterprise_transport.ingest(root,wid,event(root,wid,lease,2,"ente-gap-2"),True)
            ref=event(root,wid,lease); enterprise_transport.ingest(root,wid,ref,True); value=json.loads((root/ref).read_text()); value["event_kind"]="continuation"; conflict=write(root,"conflict.json",value)
            with self.assertRaisesRegex(ValueError,"different content"): enterprise_transport.ingest(root,wid,conflict,True)
            value["event_id"]="ente-cross-run"; value["sequence"]=2; value["tailtrail_run_id"]="another-run"; cross=write(root,"cross.json",value)
            with self.assertRaisesRegex(ValueError,"run or kind"): enterprise_transport.ingest(root,wid,cross,True)
            self.assertEqual(ownership.validate(root,wid)["valid"],True)

    def test_ingestion_requires_explicit_approval_and_safe_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); wid=workflow(root); activate(root,wid); lease=enterprise_transport.acquire(root,wid,"tenant-alpha","actor-operator",True)
            with self.assertRaisesRegex(ValueError,"explicit approval"): enterprise_transport.ingest(root,wid,event(root,wid,lease),False)
            with self.assertRaisesRegex(ValueError,"safe"): enterprise_transport.ingest(root,wid,"../event.json",True)

    def test_event_cost_limit_blocks_without_partial_append(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); wid=workflow(root); activate(root,wid,{"lease_seconds":300,"max_events_per_workflow":1,"max_backups":1,"retained_events":1}); lease=enterprise_transport.acquire(root,wid,"tenant-alpha","actor-operator",True); enterprise_transport.ingest(root,wid,event(root,wid,lease),True)
            with self.assertRaisesRegex(ValueError,"cost limit"): enterprise_transport.ingest(root,wid,event(root,wid,lease,2,"ente-checkpoint-2"),True)
            self.assertEqual(len(enterprise_transport.replay(root,wid)["events"]),1)


if __name__=="__main__": unittest.main()
