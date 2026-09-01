import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    path = ROOT / "scripts" / "real-evaluation-portfolio.py"
    spec = importlib.util.spec_from_file_location("real_evaluation_portfolio_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class RealEvaluationPortfolioTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_catalog_is_multi_repository_and_protocol_only(self):
        result = self.module.validate_catalog()
        self.assertEqual("passed", result["status"])
        self.assertGreaterEqual(result["task_count"], 15)
        self.assertGreaterEqual(result["repository_fixture_count"], 3)
        self.assertEqual("evaluation-protocol", result["evidence_label"])

    def test_empty_report_does_not_claim_performance(self):
        result = self.module.report(self.root)
        self.assertEqual("protocol-ready", result["status"])
        self.assertEqual("no-performance-claim", result["claim_status"])
        self.assertEqual(0, result["observation_count"])
        self.assertEqual({"positive": 0, "neutral": 0, "negative": 0}, result["outcomes"])
        self.assertEqual(0, result["metric_summary"]["provider_total_tokens"]["measured_pair_count"])

    def test_prepare_separates_blinded_packet_and_assignment(self):
        with self.assertRaisesRegex(ValueError, "--approved"):
            self.module.prepare(self.root, "focused-validation", 1, "a" * 64, "b" * 64, False)
        result = self.module.prepare(self.root, "focused-validation", 1, "a" * 64, "b" * 64, True)
        packet = json.loads((self.root / result["packet_ref"]).read_text(encoding="utf-8"))
        assignment = json.loads((self.root / result["assignment_ref"]).read_text(encoding="utf-8"))
        self.assertNotEqual(Path(result["packet_ref"]).parent, Path(result["assignment_ref"]).parent)
        self.assertNotIn("mapping", packet)
        self.assertEqual({"baseline", "tailtrail"}, set(assignment["mapping"].values()))

    def test_grade_unblind_retains_observation(self):
        prepared = self.module.prepare(self.root, "focused-validation", 1, "a" * 64, "b" * 64, True)
        required = prepared["required_metrics"]
        metric = {name: 0 for name in required}
        metric.update({"requirements_completed": 2, "requirements_total": 3, "provider_total_tokens": None})
        grade_input = self.root / "grade-input.json"
        grade_input.write_text(json.dumps({"A": metric, "B": metric, "reviewer_ref": "reviewer-01"}), encoding="utf-8")
        graded = self.module.grade(self.root, Path(prepared["packet_ref"]), grade_input.relative_to(self.root), True)
        observed = self.module.unblind(self.root, Path(graded["artifact"]), Path(prepared["assignment_ref"]), True)
        self.assertEqual("neutral", observed["outcome"])
        report = self.module.report(self.root)
        self.assertEqual("collecting", report["status"])
        self.assertEqual(1, report["outcomes"]["neutral"])
        self.assertEqual(1, report["metric_summary"]["requirements_completed"]["measured_pair_count"])
        self.assertEqual(0, report["metric_summary"]["provider_total_tokens"]["measured_pair_count"])
        self.assertEqual("no-performance-claim", report["claim_status"])

    def test_raw_fields_and_paths_outside_root_are_rejected(self):
        prepared = self.module.prepare(self.root, "focused-validation", 1, "a" * 64, "b" * 64, True)
        unsafe = self.root / "unsafe.json"
        unsafe.write_text(json.dumps({"raw_prompt": "do not retain"}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "prohibited"):
            self.module.grade(self.root, Path(prepared["packet_ref"]), Path("unsafe.json"), True)
        with self.assertRaisesRegex(ValueError, "inside"):
            self.module.grade(self.root, Path("../packet.json"), Path("unsafe.json"), True)

    def test_immutable_artifact_cannot_be_replaced(self):
        prepared = self.module.prepare(self.root, "focused-validation", 1, "a" * 64, "b" * 64, True)
        packet = self.root / prepared["packet_ref"]
        packet.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.module.prepare(self.root, "focused-validation", 1, "a" * 64, "b" * 64, True)


if __name__ == "__main__":
    unittest.main()
