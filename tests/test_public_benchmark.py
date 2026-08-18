from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "tailtrail.py"


class PublicBenchmarkTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, CLI.as_posix(), "benchmark", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_public_fixture_portfolio_is_deterministic_and_offline(self) -> None:
        result = self.run_cli("run-public", "--format", "json")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["evidence_label"], "fixture-scored")
        self.assertEqual(report["model_calls"], "not-run")
        self.assertEqual(report["scenario_count"], 6)
        self.assertTrue(all(item["tailtrail"]["score"] == item["tailtrail"]["total"] for item in report["scenarios"]))

        committed = json.loads((ROOT / "benchmarks" / "results" / "public-benchmark-2026-08.json").read_text(encoding="utf-8"))
        self.assertEqual(committed["evidence_label"], "fixture-scored")
        self.assertEqual(committed["model_calls"], "not-run")
        self.assertEqual({item["id"] for item in committed["scenarios"]}, {item["id"] for item in report["scenarios"]})

    def test_capture_requires_explicit_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            receipt = folder / "receipt.json"
            receipt.write_text(json.dumps({
                "type": "tailtrail-model-run-receipt", "schema_version": "1",
                "scenario_id": "validation-zero-quantity", "provider": "example",
                "model": "example-v1", "sanitized": True, "consent": "approved",
            }), encoding="utf-8")
            baseline = folder / "baseline.md"
            tailtrail = folder / "tailtrail.md"
            baseline.write_text("baseline", encoding="utf-8")
            tailtrail.write_text("tailtrail", encoding="utf-8")
            result = self.run_cli("capture-model-run", "--scenario", "validation-zero-quantity", "--receipt", str(receipt), "--baseline", str(baseline), "--tailtrail", str(tailtrail))
            self.assertEqual(result.returncode, 2)
            self.assertIn("without --approved", result.stdout)

    def test_capture_rejects_raw_data_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            receipt = folder / "receipt.json"
            receipt.write_text(json.dumps({
                "type": "tailtrail-model-run-receipt", "schema_version": "1",
                "scenario_id": "validation-zero-quantity", "provider": "example",
                "model": "example-v1", "sanitized": True, "consent": "approved",
                "prompt": "private prompt must not be stored",
            }), encoding="utf-8")
            baseline = folder / "baseline.md"
            tailtrail = folder / "tailtrail.md"
            baseline.write_text("baseline", encoding="utf-8")
            tailtrail.write_text("tailtrail", encoding="utf-8")
            result = self.run_cli("capture-model-run", "--scenario", "validation-zero-quantity", "--receipt", str(receipt), "--baseline", str(baseline), "--tailtrail", str(tailtrail), "--approved")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("prohibited raw-data", result.stderr)

    def test_capture_records_hashes_and_honest_unmeasured_label(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            receipt = folder / "receipt.json"
            receipt.write_text(json.dumps({
                "type": "tailtrail-model-run-receipt", "schema_version": "1",
                "scenario_id": "validation-zero-quantity", "provider": "example",
                "model": "example-v1", "recorded_at": "2026-08-17",
                "sanitized": True, "consent": "approved",
            }), encoding="utf-8")
            baseline = folder / "baseline.md"
            tailtrail = folder / "tailtrail.md"
            output = folder / "captured.json"
            baseline.write_text("baseline", encoding="utf-8")
            tailtrail.write_text("tailtrail", encoding="utf-8")
            result = self.run_cli("capture-model-run", "--scenario", "validation-zero-quantity", "--receipt", str(receipt), "--baseline", str(baseline), "--tailtrail", str(tailtrail), "--output", str(output), "--approved")
            self.assertEqual(result.returncode, 0, result.stderr)
            captured = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(captured["evidence_label"], "model-run-unmeasured")
            self.assertIn("baseline", captured["artifact_sha256"])
            self.assertNotIn("prompt", captured)

    def test_complete_supplied_telemetry_is_labeled_benchmark_measured(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            receipt = folder / "receipt.json"
            receipt.write_text(json.dumps({
                "type": "tailtrail-model-run-receipt", "schema_version": "1",
                "scenario_id": "validation-zero-quantity", "provider": "example",
                "model": "example-v1", "sanitized": True, "consent": "approved",
                "telemetry": {"baseline_total_tokens": 1000, "tailtrail_total_tokens": 800},
            }), encoding="utf-8")
            baseline, tailtrail, output = folder / "baseline.md", folder / "tailtrail.md", folder / "captured.json"
            baseline.write_text("baseline", encoding="utf-8")
            tailtrail.write_text("tailtrail", encoding="utf-8")
            result = self.run_cli("capture-model-run", "--scenario", "validation-zero-quantity", "--receipt", str(receipt), "--baseline", str(baseline), "--tailtrail", str(tailtrail), "--output", str(output), "--approved")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["evidence_label"], "benchmark-measured")

    def test_model_run_report_lists_only_saved_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            (runs / "run.json").write_text(json.dumps({
                "type": "tailtrail-public-model-run", "scenario_id": "api-endpoint",
                "provider": "example", "model": "example-v1", "evidence_label": "model-run-unmeasured",
            }), encoding="utf-8")
            result = self.run_cli("model-runs", "--runs", str(runs))
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["record_count"], 1)
            self.assertNotIn("artifact_sha256", report["records"][0])
