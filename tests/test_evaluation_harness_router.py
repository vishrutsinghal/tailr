from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TAILTRAIL = [sys.executable, str(ROOT / "scripts" / "tailtrail.py")]


class EvaluationHarnessRouterTests(unittest.TestCase):
    def run_tailtrail(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*TAILTRAIL, *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_eval_help_lists_eh2_and_scenario_routes(self) -> None:
        result = self.run_tailtrail("eval")

        self.assertEqual(result.returncode, 2)
        self.assertIn("Implemented in EH-2", result.stdout)
        self.assertIn("eval tokens route|reduce|receipt|ledger|proof|telemetry|savings|budget|bridge", result.stdout)
        self.assertIn("eval scenario list|run|compare|report", result.stdout)

    def test_eval_audit_delegates_to_audit_script(self) -> None:
        result = self.run_tailtrail("eval", "audit", "--format", "json", "--strict")

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["type"], "evaluation-harness-audit")
        self.assertEqual(report["status"], "passed")

    def test_eval_scenario_list_is_implemented(self) -> None:
        result = self.run_tailtrail("eval", "scenario", "list")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("TailTrail Evaluation Scenarios", result.stdout)

    def test_eval_portfolio_run_delegates_to_efficacy_runner(self) -> None:
        result = self.run_tailtrail("eval", "portfolio", "run", "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: efficacy-run.py", result.stdout)

    def test_eval_guardrails_precision_delegates_to_precision_runner(self) -> None:
        result = self.run_tailtrail("eval", "guardrails", "precision", "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: guardrail-precision.py", result.stdout)

    def test_eval_tokens_route_delegates_to_token_harness(self) -> None:
        result = self.run_tailtrail("eval", "tokens", "route", "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: token-harness.py route", result.stdout)

    def test_eval_meta_quick_delegates_to_harness_review(self) -> None:
        result = self.run_tailtrail("eval", "meta", "quick", "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: harness-review.py quick", result.stdout)

    def test_eval_outcome_summarize_delegates_to_outcome_telemetry(self) -> None:
        result = self.run_tailtrail("eval", "outcome", "summarize", "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: outcome-telemetry.py summarize", result.stdout)

    def test_unknown_eval_route_returns_usage(self) -> None:
        result = self.run_tailtrail("eval", "unknown")

        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage: tailtrail eval", result.stdout)

    def test_existing_efficacy_command_still_works(self) -> None:
        result = self.run_tailtrail("efficacy", "run", "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: efficacy-run.py", result.stdout)


if __name__ == "__main__":
    unittest.main()
