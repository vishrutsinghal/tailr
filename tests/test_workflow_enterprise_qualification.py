from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from tests.workflow_enterprise_helpers import activate, event, workflow
from workflow_runtime import enterprise, enterprise_recovery, enterprise_transport


ROOT = Path(__file__).resolve().parents[1]


class WorkflowEnterpriseQualificationTests(unittest.TestCase):
    """Phase E8 (ENT-E8-001): closes the load/soak, secret-rotation,
    disaster-recovery, offline-continuation, and administrator-diagnostics
    gaps identified against the existing provider-neutral local adapter in
    `workflow_runtime.enterprise*`. This does not add a real deployed
    provider, production scale test, or human on-call runbook — it proves
    the local contract behaves correctly under those specific conditions.
    """

    # Load/soak
    def test_sustained_ingest_throughput_stays_within_documented_budget(self) -> None:
        event_count = 100
        budget_seconds = 20.0
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wid = workflow(root)
            activate(root, wid, {"lease_seconds": 3600, "max_events_per_workflow": event_count, "max_backups": 5, "retained_events": event_count})
            lease = enterprise_transport.acquire(root, wid, "tenant-alpha", "actor-operator", True)

            started = time.perf_counter()
            for sequence in range(1, event_count + 1):
                ref = event(root, wid, lease, sequence, f"ente-soak-{sequence}")
                enterprise_transport.ingest(root, wid, ref, True)
            elapsed = time.perf_counter() - started

            replay = enterprise_transport.replay(root, wid)
            enterprise_recovery.backup(root, wid, True)
            conformance = enterprise_recovery.conformance(root, wid)

        self.assertTrue(replay["valid"], replay["issues"])
        self.assertEqual(len(replay["events"]), event_count)
        self.assertEqual(conformance["status"], "passed", conformance)
        self.assertLess(elapsed, budget_seconds, f"{event_count} sequential ingests took {elapsed:.2f}s, exceeding the {budget_seconds}s budget")

    # Secret rotation
    def test_fencing_token_rotation_permanently_invalidates_prior_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wid = workflow(root)
            activate(root, wid)

            first = enterprise_transport.acquire(root, wid, "tenant-alpha", "actor-operator", True)
            enterprise_transport.ingest(root, wid, event(root, wid, first, 1, "ente-rotate-1"), True)
            enterprise_transport.release_lease(root, wid, "tenant-alpha", "actor-operator", first["lease_id"], first["fencing_token"], True)

            second = enterprise_transport.acquire(root, wid, "tenant-alpha", "actor-operator", True)
            self.assertGreater(second["epoch"], first["epoch"])
            self.assertNotEqual(second["fencing_token"], first["fencing_token"])

            # the rotated-out credential must never be honored again, even for a new event
            stale_ref = event(root, wid, first, 2, "ente-rotate-2")
            with self.assertRaisesRegex(ValueError, "stale or unauthorized"):
                enterprise_transport.ingest(root, wid, stale_ref, True)

            # the current credential still works
            enterprise_transport.ingest(root, wid, event(root, wid, second, 2, "ente-rotate-2b"), True)
            enterprise_transport.release_lease(root, wid, "tenant-alpha", "actor-operator", second["lease_id"], second["fencing_token"], True)

            third = enterprise_transport.acquire(root, wid, "tenant-alpha", "actor-operator", True)
            self.assertGreater(third["epoch"], second["epoch"])
            with self.assertRaisesRegex(ValueError, "stale or unauthorized"):
                enterprise_transport.ingest(root, wid, event(root, wid, second, 3, "ente-rotate-3"), True)

    # Disaster recovery drill
    def test_journal_corruption_after_backup_fails_closed_across_replay_restore_and_conformance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wid = workflow(root)
            activate(root, wid)
            lease = enterprise_transport.acquire(root, wid, "tenant-alpha", "actor-operator", True)
            enterprise_transport.ingest(root, wid, event(root, wid, lease), True)
            backup = enterprise_recovery.backup(root, wid, True)

            # simulate real data loss: corrupt the live distributed event journal in place
            event_journal = enterprise.directory(root) / "state-store" / "events" / f"{wid}.jsonl"
            event_journal.write_text(event_journal.read_text(encoding="utf-8") + "{not valid json\n", encoding="utf-8")

            replay = enterprise_transport.replay(root, wid)
            restored = enterprise_recovery.restore_validate(root, backup["artifact"])
            conformance = enterprise_recovery.conformance(root, wid)

        # every diagnostic must fail closed and none may claim the corrupted state is recoverable
        self.assertFalse(replay["valid"])
        self.assertEqual(restored["status"], "blocked")
        self.assertIn("backup-artifact-stale", restored["issues"])
        self.assertFalse(restored["canonical_state_replaced"])
        self.assertEqual(conformance["status"], "blocked")
        self.assertIn("replay", conformance["issues"])

    # Offline reconciliation / local continuation
    def test_local_canonical_runtime_continues_when_enterprise_store_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            from workflow_runtime import storage

            root = Path(temp)
            wid = workflow(root)
            activate(root, wid)
            store_root = enterprise.directory(root) / "state-store"
            store_root.mkdir(parents=True, exist_ok=True)
            store_root.chmod(0o000)
            try:
                with self.assertRaises(OSError):
                    enterprise_transport.acquire(root, wid, "tenant-alpha", "actor-operator", True)
                # canonical local runtime must be completely unaffected by enterprise unavailability
                snapshot = storage.capture(root, wid)
                self.assertTrue(storage.replay(root, wid)["valid"])
                self.assertIn("event", snapshot)
            finally:
                store_root.chmod(0o755)

            # once available again, the workflow resumes normal ingestion without conflict
            lease = enterprise_transport.acquire(root, wid, "tenant-alpha", "actor-operator", True)
            enterprise_transport.ingest(root, wid, event(root, wid, lease), True)
            self.assertTrue(enterprise_transport.replay(root, wid)["valid"])

    # Administrator diagnostics (CLI surface)
    def test_cli_administrator_conformance_diagnostic_is_categorical_and_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wid = workflow(root)
            activate(root, wid)
            lease = enterprise_transport.acquire(root, wid, "tenant-alpha", "actor-operator", True)
            enterprise_transport.ingest(root, wid, event(root, wid, lease), True)
            enterprise_recovery.backup(root, wid, True)

            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "workflow-runtime.py"), "enterprise", "conformance", "--root", root.as_posix(), "--workflow-id", wid],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "passed", payload)
            self.assertIn("checks", payload)
            self.assertIn("provider deployment", payload["boundary"])


if __name__ == "__main__":
    unittest.main()
