from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from tests import test_learning_use_receipt as PM3


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "benchmarks" / "evaluation" / "learning-calibration" / "v1.json"


def load_script(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CAL = load_script("pm_l5_learning_calibration", "scripts/learning-calibration.py")
META = load_script("pm_l5_meta_harness", "scripts/meta-harness-analyze.py")
META_PROPOSE = load_script("pm_l5_meta_harness_propose", "scripts/meta-harness-propose.py")
HARNESS = load_script("pm_l5_harness_review", "scripts/harness-review.py")
RETRIEVAL = load_script("pm_l5_learning_retrieval", "scripts/learning-retrieval.py")


class LearningCalibrationTests(unittest.TestCase):
    def catalog(self):
        return json.loads(CATALOG.read_text(encoding="utf-8"))

    def seal(self, value):
        value["integrity"]["digest"] = CAL.unsigned_digest(value)
        return value

    def test_catalog_is_closed_sealed_complete_and_later_observed(self):
        value = self.catalog()
        CAL.validate_catalog(value)
        self.assertEqual(CAL.CLASSES, {row["learning_class"] for row in value["classes"]})
        self.assertTrue(all(len(row["observations"]) >= 4 for row in value["classes"]))
        self.assertTrue(all(
            CAL.parse_time(observation["observed_at"]) > CAL.parse_time(observation["captured_at"])
            for row in value["classes"] for observation in row["observations"]
        ))
        tampered = copy.deepcopy(value)
        tampered["classes"][0]["observations"][0]["confidence_score"] += 1
        with self.assertRaisesRegex(CAL.CalibrationError, "digest mismatch"):
            CAL.validate_catalog(tampered)
        extra = copy.deepcopy(value)
        extra["raw_prompt"] = "forbidden"
        self.seal(extra)
        with self.assertRaisesRegex(CAL.CalibrationError, "not closed"):
            CAL.validate_catalog(extra)

    def test_evaluation_is_deterministic_and_fixture_claims_are_blocked(self):
        first = CAL.evaluate(self.catalog())
        second = CAL.evaluate(self.catalog())
        self.assertEqual(first, second)
        self.assertEqual(28, first["overall"]["sample_count"])
        self.assertEqual(7, len(first["classes"]))
        self.assertEqual(0.6667, first["overall"]["precision"])
        self.assertEqual(0.5, first["overall"]["false_intervention_rate"])
        self.assertIn("correction_cycle_delta", first["overall"])
        self.assertIn("review_time_delta_ms", first["overall"])
        self.assertIn("token_overhead", first["overall"])
        self.assertEqual("fixture-only-no-public-performance-claim", first["claims"]["posture"])
        self.assertEqual([], first["claims"]["publishable"])
        CAL.validate_report(first)

    def test_project_calibration_requires_minimum_and_mixed_later_outcomes(self):
        insufficient = [
            {"receipt_id": f"r-{index}", "learning_class": "positive-pattern", "confidence_score": 80, "observed_usefulness": True}
            for index in range(4)
        ]
        row = CAL.project_metrics(insufficient, 4)[0]
        self.assertFalse(row["eligible"])
        self.assertEqual(0, row["suggested_adjustment"])
        mixed = [
            {"receipt_id": f"r-{index}", "learning_class": "positive-pattern", "confidence_score": 80, "observed_usefulness": index < 2}
            for index in range(4)
        ]
        row = CAL.project_metrics(mixed, 4)[0]
        self.assertTrue(row["eligible"])
        self.assertEqual(-8, row["suggested_adjustment"])

    def test_real_receipt_chains_drive_report_and_approved_projection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            helper = PM3.LearningUseReceiptTests()
            original_now = PM3.V3.now
            PM3.V3.now = lambda: "2026-01-01T00:00:00+00:00"
            try:
                for index in range(4):
                    run_id = f"calibration-{index}"
                    learning, uid, _ = helper.setup_run(root, run_id)
                    helper.record(root, learning, uid, run_id=run_id)
                    PM3.RECEIPTS.attribute_completion(
                        root, run_id, PM3.completion(uid, drift=index >= 2),
                        completion_ref=f".tailtrail/runs/{run_id}/completion-reports/report.json",
                    )
                    report_path = root / f".tailtrail/runs/{run_id}/completion-reports/report.json"
                    report_path.parent.mkdir(parents=True, exist_ok=True)
                    report_path.write_text("{}\n", encoding="utf-8")
            finally:
                PM3.V3.now = original_now
            observations = CAL.project_observations(root)
            self.assertEqual(4, len(observations))
            report = CAL.evaluate(self.catalog(), root)
            row = report["project_calibration"][0]
            self.assertTrue(row["eligible"])
            self.assertEqual((2, 2), (row["positive_count"], row["negative_count"]))
            report_path = root / ".tailtrail/evaluation/learning-calibration/report.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report), encoding="utf-8")
            projection = CAL.apply_report(root, report_path, True)
            self.assertIn("positive-pattern", projection["adjustments"])
            self.assertEqual((projection["adjustments"], []), CAL.load_adjustments(root))

    def test_approved_projection_is_bounded_report_linked_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = CAL.evaluate(self.catalog())
            frame = CAL.load_module("pm_l5_test_frame", "learning-v3.py").project_frame(root)
            report["project_frame"] = frame
            report["project_calibration"] = [{
                "learning_class": "positive-pattern", "sample_count": 4, "positive_count": 2,
                "negative_count": 2, "mean_confidence": 0.8, "observed_usefulness_rate": 0.5,
                "calibration_gap": 0.3, "suggested_adjustment": -8, "eligible": True,
            }]
            self.seal(report)
            report_path = root / ".tailtrail/evaluation/learning-calibration/report.json"
            report_path.parent.mkdir(parents=True)
            report_path.write_text(json.dumps(report), encoding="utf-8")
            receipt_rows = [
                {"receipt_id": f"r-{index}", "learning_class": "positive-pattern", "confidence_score": 80, "observed_usefulness": index < 2}
                for index in range(4)
            ]
            with mock.patch.object(CAL, "project_observations", return_value=receipt_rows):
                with self.assertRaisesRegex(CAL.CalibrationError, "requires --approved"):
                    CAL.apply_report(root, report_path, False)
                projection = CAL.apply_report(root, report_path, True)
            self.assertEqual({"positive-pattern": -8}, projection["adjustments"])
            with mock.patch.object(CAL, "project_observations", return_value=receipt_rows):
                adjustments, blocks = CAL.load_adjustments(root)
            self.assertEqual({"positive-pattern": -8}, adjustments)
            self.assertEqual([], blocks)
            score, reasons = RETRIEVAL.applicability({
                "applicability": {"task_types": ["test"], "tags": [], "requirement_ids": [], "path_patterns": []},
                "utility": {"confidence_score": 80, "curated": False},
            }, {"task_types": ["test"], "tags": [], "requirement_ids": [], "paths": []}, confidence_score=72)
            self.assertEqual(49, score)
            report["classes"][0]["precision"] = 0.0
            report_path.write_text(json.dumps(report), encoding="utf-8")
            with mock.patch.object(CAL, "project_observations", return_value=receipt_rows):
                adjustments, blocks = CAL.load_adjustments(root)
            self.assertEqual({}, adjustments)
            self.assertTrue(blocks)
            self.assertIn("report digest mismatch", blocks[0])

    def test_meta_feed_is_repeated_sanitized_and_analyzable(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "signals.jsonl"
            summary = CAL.meta_feed(self.catalog(), output)
            self.assertGreaterEqual(summary["event_count"], 14)
            events = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            for event in events:
                HARNESS.validate_shared_event(event)
                serialized = json.dumps(event).lower()
                self.assertNotIn("scenario_id", serialized)
                self.assertNotIn("receipt_id", serialized)
                self.assertNotIn("review_time_ms", serialized)
                self.assertNotIn("input_tokens", serialized)
            analysis = META.build_analysis([output], threshold=2)
            findings = [row for row in analysis["findings"] if row["category"] == "learning-calibration-gap"]
            self.assertEqual(7, len(findings))
            self.assertTrue(all(row["candidate_change_type"] == "learning-calibration" for row in findings))
            proposal = META_PROPOSE.build_proposal(ROOT, analysis, "proposal-pm-l5", findings[0]["finding_id"])
            self.assertEqual("proposed", proposal["status"])
            self.assertEqual("learning-calibration-gap", proposal["source_finding"]["category"])

    def test_cli_routes_learning_evaluation(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/tailtrail.py"), "eval", "learning", "evaluate", "--format", "summary"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("28 paired observations", result.stdout)


if __name__ == "__main__":
    unittest.main()
