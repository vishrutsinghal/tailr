from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from workflow_runtime import contracts


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module); return module


evaluation = load("di12_evaluation", "scripts/debug-evaluation.py")


class DebugEvaluationTests(unittest.TestCase):
    def test_exact_ten_scenarios_generate_calibrated_honest_report(self) -> None:
        report = evaluation.evaluate()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(len(report["scenario_results"]), 10)
        self.assertEqual({row["scenario_id"] for row in report["scenario_results"]}, evaluation.EXPECTED)
        self.assertEqual(report["metrics"]["false_debug_routes"], 0)
        self.assertEqual(report["metrics"]["token_estimate_calibration"]["status"], "unavailable")
        sensitive = next(row for row in report["scenario_results"] if row["scenario_id"] == "sensitive-error-log")
        self.assertEqual(sensitive["observations"]["sensitive_values_retained"], 0)
        schema = json.loads((ROOT / "schemas" / "debug-evaluation-report.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(contracts.validate_document(report, schema), [])

    def test_run_is_dry_by_default_and_approved_write_is_local(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            preview = evaluation.run(root, False)
            self.assertIsNone(preview["artifact"])
            self.assertFalse((root / ".tailtrail").exists())
            saved = evaluation.run(root, True)
            self.assertTrue((root / saved["artifact"]).is_file())

    def test_release_gate_is_blocked_without_real_host_and_vertical_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); evaluation.run(root, True)
            gate = evaluation.release_gate(root)
            self.assertEqual(gate["status"], "blocked")
            self.assertEqual(gate["deterministic_evaluation"], "passed")
            self.assertEqual(set(gate["host_runtime_conformance"].values()), {"not-validated"})
            self.assertTrue(any("Codex" in reason or "codex" in reason for reason in gate["blocking_reasons"]))
            schema = json.loads((ROOT / "schemas" / "debug-release-gate.schema.json").read_text(encoding="utf-8"))
            self.assertEqual(contracts.validate_document(gate, schema), [])


if __name__ == "__main__": unittest.main()
