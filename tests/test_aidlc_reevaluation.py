from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import metrics_extractor  # noqa: E402


# A complexity dict with enough signal to exceed the standard thresholds but
# not the scope floor (which would keep Lite).
_COMPLEXITY_HI = {
    "source": "scope_evidence",
    "available": True,
    "affected_files": 25,
    "changed_lines_estimate": 200,
    "cross_layer_edges": 3,
    "call_chain_depth_stddev": 3.5,
    "module_resolution_ambiguous": 4,
    "new_external_deps": 2,
    "behavior_chain_incomplete": True,
    "thresholds": dict(metrics_extractor.DEFAULT_THRESHOLDS),
}

# A complexity dict that stays under all standard thresholds.
_COMPLEXITY_LOW = {
    "source": "likely_impacted_files_only",
    "available": True,
    "affected_files": 3,
    "changed_lines_estimate": 20,
    "cross_layer_edges": 0,
    "call_chain_depth_stddev": 0.0,
    "module_resolution_ambiguous": 0,
    "new_external_deps": 0,
    "behavior_chain_incomplete": False,
    "thresholds": dict(metrics_extractor.DEFAULT_THRESHOLDS),
}



class ComputeReEvaluationBasicTests(unittest.TestCase):
    def test_fires_for_lite_when_scope_signal_and_no_floor(self):
        suggestion = metrics_extractor.compute_re_evaluation(
            "lite", _COMPLEXITY_HI, scope_quality_blocking=False, complexity_available=True
        )
        self.assertIsNotNone(suggestion)
        self.assertTrue(suggestion["re_evaluation_suggested"])
        self.assertEqual(suggestion["suggested_mode"], "standard")
        self.assertEqual(suggestion["initial_mode"], "lite")
        self.assertTrue(suggestion["scope_signal"])
        self.assertFalse(suggestion["scope_floor_lite"])
        self.assertIn("complexity_snapshot", suggestion)
        self.assertIn("triggered_signals", suggestion)
        self.assertTrue(suggestion["triggered_signals"])

    def test_does_not_fire_for_off(self):
        self.assertIsNone(metrics_extractor.compute_re_evaluation("off", _COMPLEXITY_HI, complexity_available=True))

    def test_does_not_fire_for_full(self):
        self.assertIsNone(metrics_extractor.compute_re_evaluation("full", _COMPLEXITY_HI, complexity_available=True))

    def test_does_not_fire_for_standard(self):
        self.assertIsNone(metrics_extractor.compute_re_evaluation("standard", _COMPLEXITY_HI, complexity_available=True))

    def test_does_not_fire_when_scope_signal_false(self):
        suggestion = metrics_extractor.compute_re_evaluation(
            "lite", _COMPLEXITY_LOW, scope_quality_blocking=False, complexity_available=True
        )
        self.assertIsNone(suggestion)

    def test_does_not_fire_when_scope_floor_lite_applies(self):
        tiny = {
            "affected_files": 2,
            "changed_lines_estimate": 10,
            "cross_layer_edges": 5,
            "thresholds": dict(metrics_extractor.DEFAULT_THRESHOLDS),
        }
        suggestion = metrics_extractor.compute_re_evaluation(
            "lite", tiny, scope_quality_blocking=False, complexity_available=True
        )
        self.assertIsNone(suggestion)


class ComputeReEvaluationAvailabilityTests(unittest.TestCase):
    def test_does_not_fire_when_complexity_unavailable(self):
        self.assertIsNone(
            metrics_extractor.compute_re_evaluation(
                "lite", None, complexity_available=False
            )
        )

    def test_does_not_fire_when_complexity_is_none_dict(self):
        self.assertIsNone(
            metrics_extractor.compute_re_evaluation(
                "lite", None, scope_quality_blocking=False, complexity_available=True
            )
        )

    def test_does_not_fire_when_complexity_empty_dict(self):
        suggestion = metrics_extractor.compute_re_evaluation(
            "lite", {}, scope_quality_blocking=False, complexity_available=True
        )
        self.assertIsNone(suggestion)


class EvaluateScopeSignalTests(unittest.TestCase):
    def test_none_returns_false_false(self):
        signal, floor = metrics_extractor.evaluate_scope_signal(None)
        self.assertFalse(signal)
        self.assertFalse(floor)

    def test_high_complexity_scope_signal_true(self):
        signal, floor = metrics_extractor.evaluate_scope_signal(_COMPLEXITY_HI)
        self.assertTrue(signal)
        self.assertFalse(floor)

    def test_low_complexity_scope_signal_false_floor_true(self):
        signal, floor = metrics_extractor.evaluate_scope_signal(_COMPLEXITY_LOW)
        self.assertFalse(signal)
        self.assertTrue(floor)


class PlanningLockStorageTests(unittest.TestCase):
    def test_create_stores_re_evaluation_suggestion(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "planning_lock", str(ROOT / "scripts" / "planning_lock.py")
        )
        self.assertIsNotNone(spec)
        pl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pl)
        suggestion = {"re_evaluation_suggested": True, "suggested_mode": "standard", "initial_mode": "lite"}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock = pl.create(root, "fix a bug", "start-test-reeval-1", re_evaluation_suggestion=suggestion)
        self.assertIsNotNone(lock.get("re_evaluation_suggestion"))
        self.assertEqual(lock["re_evaluation_suggestion"]["suggested_mode"], "standard")

    def test_create_without_suggestion_stores_none(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "planning_lock", str(ROOT / "scripts" / "planning_lock.py")
        )
        pl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pl)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock = pl.create(root, "fix a bug", "start-test-reeval-2")
        self.assertIsNone(lock.get("re_evaluation_suggestion"))


if __name__ == "__main__":
    unittest.main()
