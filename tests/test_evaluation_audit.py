from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EvaluationAuditTests(unittest.TestCase):
    def run_audit(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "tailtrail.py"), "eval", "audit", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_eval_audit_json_has_expected_feature_groups(self) -> None:
        result = self.run_audit("--format", "json", "--strict")

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        groups = {item["feature_group"] for item in report["features"]}
        self.assertEqual(report["status"], "passed")
        self.assertIn("benchmark-harness", groups)
        self.assertIn("measured-efficacy", groups)
        self.assertIn("guardrail-precision", groups)
        self.assertIn("outcome-telemetry", groups)
        self.assertIn("quality-loop", groups)
        self.assertIn("meta-harness", groups)
        self.assertIn("token-evidence", groups)
        self.assertIn("enterprise-reporting", groups)
        self.assertIn("buildweek-demo-evidence", groups)
        self.assertEqual(report["summary"]["needs_decision"], 0)

    def test_eval_audit_markdown_lists_canonical_mapping(self) -> None:
        result = self.run_audit()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# TailTrail Evaluation Harness EH-0 Audit", result.stdout)
        self.assertIn("## Canonical Mapping", result.stdout)
        self.assertIn("`token-evidence` -> `eval tokens`", result.stdout)
        self.assertIn("`tailtrail token route`", result.stdout)

    def test_eval_audit_write_requires_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "evaluation-audit.py"),
                    "--root",
                    str(root),
                    "--write-report",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--write-report requires --approved", result.stderr)

    def test_eval_audit_write_outputs_reports_when_approved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "evaluation-audit.py"),
                    "--root",
                    str(root),
                    "--write-report",
                    "--approved",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            report_dir = root / "reports" / "evaluation-harness"
            json_report = report_dir / "eh0-audit.json"
            markdown_report = report_dir / "eh0-audit.md"
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json_report.is_file())
            self.assertTrue(markdown_report.is_file())

    def test_future_eval_subcommand_is_pending(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "tailtrail.py"), "eval", "portfolio", "compare"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("planned for EH-5 Portfolio Consolidation", result.stdout)


if __name__ == "__main__":
    unittest.main()
