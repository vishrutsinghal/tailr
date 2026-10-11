import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts" / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


tracker = load_module("tailtrail_flaky_tracker_test", "flaky-test-tracker.py")
ledger = load_module("tailtrail_flaky_ledger_test", "run-ledger.py")

# Order-distinguishing sequence from the issues log: swapped positions
# (2<->10, 3<->11, 4<->12 under lexicographic sort) carry different values,
# so a scrambled read cannot hide behind equal parities.
SEQUENCE = ["pass", "fail", "fail", "fail", "pass", "pass", "pass",
            "pass", "pass", "blocked", "blocked", "blocked"]


class FlakyTrackerOrderingTests(unittest.TestCase):
    def test_history_keeps_chronological_order_past_ten(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger.init_run(root, "run", "flaky ordering")
            result = {}
            for outcome in SEQUENCE:
                result = tracker.record(root, "run", "test-login", outcome)
            self.assertEqual(result["history"], SEQUENCE)

    def test_status_never_masks_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger.init_run(root, "run", "flaky ordering")
            result = {}
            for outcome in SEQUENCE:
                result = tracker.record(root, "run", "test-login", outcome)
            self.assertEqual(result["status"], "flaky")


if __name__ == "__main__":
    unittest.main()
