from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from tests.test_workflow_security import setup_workflow
from workflow_runtime import ownership, retry, storage


class WorkflowConcurrencyTests(unittest.TestCase):
    """Phase E7 (ENT-E7-001): local concurrency and idempotency fixtures.

    These exercise the real `LEDGER.RunLock` file lock used by
    `workflow_runtime.storage`, not a simulation, so contention and
    serialization failures would surface as real assertion failures.
    """

    def test_concurrent_appends_serialize_without_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _run, wid = setup_workflow(root, "phase-e7-concurrency")
            before = len(storage.events(root, wid)["events"])
            thread_count, per_thread = 8, 6
            errors: list[BaseException] = []
            barrier = threading.Barrier(thread_count)

            def worker() -> None:
                barrier.wait()
                for _ in range(per_thread):
                    try:
                        storage.capture(root, wid)
                    except BaseException as exc:  # noqa: BLE001 - captured for assertion, not silenced
                        errors.append(exc)

            threads = [threading.Thread(target=worker) for _ in range(thread_count)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.assertEqual(errors, [], errors)
            replay = storage.replay(root, wid)
            self.assertTrue(replay["valid"], replay["issues"])
            rows = storage.events(root, wid)["events"]
            self.assertEqual(len(rows), before + thread_count * per_thread)
            sequences = [row["sequence"] for row in rows]
            self.assertEqual(sequences, list(range(1, len(sequences) + 1)))

    def test_concurrent_lock_acquisition_never_interleaves_partial_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _run, wid = setup_workflow(root, "phase-e7-lock-interleave")
            journal = storage.journal_path(root, wid)

            def worker() -> None:
                for _ in range(4):
                    storage.capture(root, wid)

            threads = [threading.Thread(target=worker) for _ in range(6)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            lines = journal.read_text(encoding="utf-8").splitlines()
            self.assertTrue(all(line.strip().startswith("{") and line.strip().endswith("}") for line in lines))
            validation = storage.validate(root, wid)
            self.assertEqual(validation["issues"], [])

    def test_duplicate_initial_retry_dispatch_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _run, wid = setup_workflow(root, "phase-e7-idempotency")
            binding = ownership.show(root, wid)
            first = retry.register_initial(root, wid, "bootstrap", None, "workflow-input-ref")
            second = retry.register_initial(root, wid, "bootstrap", None, "workflow-input-ref")
            self.assertEqual(first["status"], "recorded")
            self.assertEqual(second["status"], "duplicate-suppressed")
            self.assertEqual(first["operation_id"], second["operation_id"])
            attempts = retry.show(root, wid)["attempts"]
            initial_rows = [row for row in attempts if row["operation_id"] == first["operation_id"] and row["attempt"] == 0]
            self.assertEqual(len(initial_rows), 1, "a duplicate initial dispatch must not create a second attempt row")
            self.assertEqual(binding["tailtrail_run_id"], "phase-e7-idempotency")


if __name__ == "__main__":
    unittest.main()
