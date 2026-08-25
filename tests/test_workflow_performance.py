from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from tests.test_workflow_security import setup_workflow
from workflow_runtime import state, storage


class WorkflowPerformanceBudgetTests(unittest.TestCase):
    """Phase E7 (ENT-E7-001): documented performance regression budgets.

    Budgets are intentionally generous so the suite is not flaky in CI; the
    point is to catch a gross regression (for example an accidental O(n^2)
    replay or an unbounded projection), not to certify absolute latency. The
    fixture workflow is built once for the whole class to keep suite runtime
    bounded (event capture includes an fsync per append).
    """

    EVENT_COUNT = 60
    REPLAY_BUDGET_SECONDS = 5.0
    REPLAY_PER_EVENT_BUDGET_MS = 40.0
    DOCTOR_BUDGET_SECONDS = 2.0

    @classmethod
    def setUpClass(cls) -> None:
        cls._temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._temp.name)
        _run, cls.workflow_id = setup_workflow(cls.root, "phase-e7-performance")
        for _ in range(cls.EVENT_COUNT):
            storage.capture(cls.root, cls.workflow_id)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temp.cleanup()

    def test_replay_time_scales_within_documented_budget(self) -> None:
        started = time.perf_counter()
        replay = storage.replay(self.root, self.workflow_id)
        elapsed = time.perf_counter() - started

        self.assertTrue(replay["valid"], replay["issues"])
        self.assertLess(
            elapsed, self.REPLAY_BUDGET_SECONDS,
            f"replay of {self.EVENT_COUNT}+ events took {elapsed:.3f}s, exceeding the {self.REPLAY_BUDGET_SECONDS}s budget",
        )
        per_event_ms = (elapsed / self.EVENT_COUNT) * 1000
        self.assertLess(
            per_event_ms, self.REPLAY_PER_EVENT_BUDGET_MS,
            f"per-event replay overhead {per_event_ms:.3f}ms exceeds the {self.REPLAY_PER_EVENT_BUDGET_MS}ms budget",
        )

    def test_doctor_diagnosis_stays_fast_on_a_populated_workflow(self) -> None:
        started = time.perf_counter()
        diagnosis = state.doctor(self.root, self.workflow_id)
        elapsed = time.perf_counter() - started

        self.assertIn("status", diagnosis)
        self.assertLess(
            elapsed, self.DOCTOR_BUDGET_SECONDS,
            f"doctor diagnosis took {elapsed:.3f}s, exceeding the {self.DOCTOR_BUDGET_SECONDS}s budget",
        )

    def test_projection_size_stays_bounded_relative_to_journal_size(self) -> None:
        journal_bytes = storage.journal_path(self.root, self.workflow_id).stat().st_size
        projection_bytes = storage.projection_path(self.root, self.workflow_id).stat().st_size

        # The projection is a reduced, current-state view; it must not grow
        # proportionally to the full append-only journal history.
        self.assertLess(
            projection_bytes, journal_bytes,
            "projection size should stay smaller than the full event journal it was reduced from",
        )


if __name__ == "__main__":
    unittest.main()
