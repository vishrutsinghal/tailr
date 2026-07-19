from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TAILTRAIL = [sys.executable, str(ROOT / "scripts" / "tailtrail.py")]


class EvaluationHarnessScenarioTests(unittest.TestCase):
    def run_tailtrail(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*TAILTRAIL, *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_scenario_list_shows_committed_scenarios(self) -> None:
        result = self.run_tailtrail("eval", "scenario", "list", "--format", "json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        scenario_ids = {item["scenario_id"] for item in payload["scenarios"]}
        self.assertEqual(
            scenario_ids,
            {"validation-bug", "dependency-decision", "review-only", "ci-failure", "security-triage", "buildweek-validation"},
        )

    def test_scenario_run_scores_deterministically(self) -> None:
        result = self.run_tailtrail("eval", "scenario", "run", "--scenario", "validation-bug", "--format", "json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["type"], "evaluation-scenario-result")
        self.assertEqual(payload["winner"], "tailtrail")
        self.assertTrue(payload["threshold_passed"])
        self.assertGreater(payload["delta_from_baseline"], 0.15)
        self.assertIn("event", payload)

    def test_scenario_compare_reports_winner_and_delta(self) -> None:
        result = self.run_tailtrail("eval", "scenario", "compare", "--scenario", "dependency-decision")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("## Comparison", result.stdout)
        self.assertIn("Winning variant: `tailtrail`", result.stdout)
        self.assertIn("Delta from baseline", result.stdout)

    def test_scenario_report_includes_claim_boundaries(self) -> None:
        result = self.run_tailtrail("eval", "scenario", "report", "--scenario", "security-triage")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# TailTrail Evaluation Scenario Report", result.stdout)
        self.assertIn("## Claim Boundaries", result.stdout)
        self.assertIn("Security remediation still requires real scanner", result.stdout)

    def test_scenario_write_requires_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "scenario.md"
            blocked = self.run_tailtrail(
                "eval",
                "scenario",
                "report",
                "--scenario",
                "validation-bug",
                "--write-result",
                str(output),
            )
            allowed = self.run_tailtrail(
                "eval",
                "scenario",
                "report",
                "--scenario",
                "validation-bug",
                "--write-result",
                str(output),
                "--approved",
            )
            output_exists = output.is_file()

        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("--write-result requires --approved", blocked.stderr)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertTrue(output_exists)

    def test_buildweek_validation_scenario_report(self) -> None:
        result = self.run_tailtrail("eval", "scenario", "report", "--scenario", "buildweek-validation", "--format", "json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["type"], "evaluation-scenario-result")
        self.assertEqual(payload["scenario_id"], "buildweek-validation")
        self.assertEqual(payload["winner"], "tailtrail")
        self.assertTrue(payload["threshold_passed"])
        self.assertIn("This scenario scores committed demo artifacts only.", payload["claim_boundaries"])
        self.assertGreaterEqual(payload["delta_from_baseline"], 0.2)

    def test_buildweek_validation_write_requires_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "buildweek-scenario.md"
            blocked = self.run_tailtrail(
                "eval",
                "scenario",
                "report",
                "--scenario",
                "buildweek-validation",
                "--write-result",
                str(output),
            )
            output_exists = output.is_file()

        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("--write-result requires --approved", blocked.stderr)
        self.assertFalse(output_exists)

    def test_all_scenarios_pass_expected_thresholds(self) -> None:
        scenarios = ["validation-bug", "dependency-decision", "review-only", "ci-failure", "security-triage", "buildweek-validation"]
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                result = self.run_tailtrail("eval", "scenario", "run", "--scenario", scenario, "--format", "json")
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads(result.stdout)
                self.assertTrue(payload["threshold_passed"])
                self.assertEqual(payload["winner"], "tailtrail")


if __name__ == "__main__":
    unittest.main()
