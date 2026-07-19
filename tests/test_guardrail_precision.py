import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "guardrail-precision.py"


def load_module():
    spec = importlib.util.spec_from_file_location("tailtrail_guardrail_precision_test", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


precision = load_module()


class GuardrailPrecisionTests(unittest.TestCase):
    def test_score_rule_computes_confusion_matrix(self):
        cases = [
            {"label": "expected-finding", "findings": [{"rule_class": "dependency-gate"}]},
            {"label": "expected-finding", "findings": []},
            {"label": "expected-clean", "findings": [{"rule_class": "dependency-gate"}]},
            {"label": "expected-clean", "findings": []},
        ]
        result = precision.score_rule("dependency-gate", cases, {"min_precision": 0.5, "min_fixtures": 1})
        self.assertEqual(result["tp"], 1)
        self.assertEqual(result["fp"], 1)
        self.assertEqual(result["tn"], 1)
        self.assertEqual(result["fn"], 1)
        self.assertEqual(result["precision"], 0.5)
        self.assertEqual(result["recall"], 0.5)
        self.assertEqual(result["false_positive_rate"], 0.5)
        self.assertEqual(result["fixture_count"], 4)
        self.assertEqual(result["confidence"], "low")
        self.assertEqual(result["status"], "ok")

    def test_insufficient_fixtures_are_not_ok(self):
        cases = [
            {"label": "expected-finding", "findings": [{"rule_class": "dependency-gate"}]},
            {"label": "expected-clean", "findings": []},
        ]
        result = precision.score_rule("dependency-gate", cases, {"min_precision": 0.5, "min_fixtures": 8})
        self.assertEqual(result["status"], "insufficient-fixtures")

    def test_cross_rule_findings_do_not_count_against_scored_rule(self):
        cases = [
            {"label": "expected-clean", "findings": [{"rule_class": "safeguard-removal"}]},
        ]
        result = precision.score_rule("dependency-gate", cases, {"min_precision": 0.5, "min_fixtures": 1})
        self.assertEqual(result["fp"], 0)
        self.assertEqual(result["tn"], 1)
        self.assertEqual(result["precision"], None)
        self.assertEqual(result["status"], "undefined")

    def test_undefined_precision_has_reason(self):
        cases = [
            {"label": "expected-finding", "findings": []},
            {"label": "expected-clean", "findings": []},
        ]
        result = precision.score_rule("dependency-gate", cases, {"min_precision": 0.5, "min_fixtures": 1})
        self.assertEqual(result["precision"], None)
        self.assertEqual(result["precision_reason"], "no-positive-predictions")
        self.assertEqual(result["status"], "undefined")

    def test_committed_fixture_baseline_passes(self):
        report = precision.build_report(
            ROOT,
            ROOT / "benchmarks" / "guardrail-precision" / "fixtures",
            ROOT / "benchmarks" / "guardrail-precision" / "thresholds.json",
            None,
            True,
        )
        self.assertEqual(report["total_fixtures"], 64)
        self.assertEqual(report["below_threshold_rules"], [])
        self.assertEqual(set(report["rules"]), set(precision.RULES))
        self.assertTrue(all(rule["status"] == "ok" for rule in report["rules"].values()))

    def test_selected_rule_limits_report_scope(self):
        report = precision.build_report(
            ROOT,
            ROOT / "benchmarks" / "guardrail-precision" / "fixtures",
            ROOT / "benchmarks" / "guardrail-precision" / "thresholds.json",
            "dependency-gate",
            True,
        )
        self.assertEqual(set(report["rules"]), {"dependency-gate"})
        self.assertEqual(report["total_fixtures"], 16)

    def test_report_does_not_mutate_fixture_files(self):
        fixtures = sorted((ROOT / "benchmarks" / "guardrail-precision" / "fixtures").rglob("*"))
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in fixtures if path.is_file()}
        precision.build_report(
            ROOT,
            ROOT / "benchmarks" / "guardrail-precision" / "fixtures",
            ROOT / "benchmarks" / "guardrail-precision" / "thresholds.json",
            None,
            True,
        )
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in fixtures if path.is_file()}
        self.assertEqual(before, after)

    def test_higher_threshold_can_fail_without_rule_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            thresholds = json.loads((ROOT / "benchmarks" / "guardrail-precision" / "thresholds.json").read_text(encoding="utf-8"))
            thresholds["rules"]["validation-claim"]["min_precision"] = 0.99
            path = Path(tmp) / "thresholds.json"
            path.write_text(json.dumps(thresholds), encoding="utf-8")
            report = precision.build_report(
                ROOT,
                ROOT / "benchmarks" / "guardrail-precision" / "fixtures",
                path,
                "validation-claim",
                True,
            )
        self.assertEqual(report["below_threshold_rules"], ["validation-claim"])
        self.assertEqual(report["rules"]["validation-claim"]["status"], "below-threshold")


if __name__ == "__main__":
    unittest.main()
