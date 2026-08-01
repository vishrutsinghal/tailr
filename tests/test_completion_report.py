from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ledger = load("completion_report_ledger", "scripts/run-ledger.py")
anchor = load("completion_report_anchor", "scripts/change-intent-anchor.py")
report = load("completion_report_script", "scripts/completion-report.py")


class CompletionReportTests(unittest.TestCase):
    def setup_run(self, root: Path) -> str:
        ledger.init_run(root, "run", "claim validation")
        proposal = root / "proposal.json"
        proposal.write_text(json.dumps({"requirements": [{
            "statement": "reject zero claims", "acceptance_criteria": ["zero rejected"],
            "preserve_rules": ["positive claims remain valid"], "likely_paths": ["src/validation.py"],
            "evidence_plan": ["focused + integration"],
        }]}), encoding="utf-8")
        anchor.draft(root, "run", proposal)
        return anchor.approve(root, "run")["requirements"][0]["requirement_uid"]

    def write_complete_evidence(self, root: Path, uid: str) -> None:
        run = ledger.state_dir(root, "run")
        (run / "checkpoints").mkdir(parents=True)
        (run / "reviews").mkdir()
        (run / "completion-gates").mkdir()
        (run / "validation-receipts").mkdir()
        (run / "maintainability").mkdir()
        (run / "checkpoints" / "checkpoint-1.json").write_text(json.dumps({
            "checkpoint": 1, "requirements": [{"requirement_uid": uid, "state": "validated", "evidence": [{"outcome": "pass"}]}],
            "changed_paths": [{"path": "src/validation.py", "fingerprint": "sha256:test"}], "drift": [{"requirement_uid": uid, "classification": "resolved"}],
        }), encoding="utf-8")
        (run / "reviews" / "review-1.json").write_text(json.dumps({"complete": True, "findings": []}), encoding="utf-8")
        (run / "completion-gates" / "gate-1.json").write_text(json.dumps({"complete": True, "findings": []}), encoding="utf-8")
        for tier in ("unit", "integration"):
            (run / "validation-receipts" / f"{tier}.json").write_text(json.dumps({"requirement_uid": uid, "tier": tier, "outcome": "pass"}), encoding="utf-8")
        (run / "maintainability" / "assessment-1.json").write_text(json.dumps({"complete": True}), encoding="utf-8")

    def test_single_report_summarizes_complete_local_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            self.write_complete_evidence(root, uid)
            result = report.build(root, "run")
            shown = report.show(root, "run")
        self.assertEqual(result["overall_status"], "complete")
        self.assertEqual(result["requirement_status"]["complete"], 1)
        self.assertEqual(result["requirement_status"]["total"], 1)
        self.assertEqual(result["changed_scope"]["status"], "approved")
        self.assertEqual(result["tests"]["passed_tiers"], ["integration", "unit"])
        harnesses = {item["name"]: item for item in result["harnesses"]}
        self.assertEqual(harnesses["Requirement Completion Harness"]["status"], "pass")
        self.assertTrue(harnesses["Maintainability Harness"]["used"])
        self.assertEqual(harnesses["Maintainability Harness"]["status"], "pass")
        self.assertEqual(shown["overall_status"], "complete")
        self.assertIn("## Harness usage", report.render(result))
        self.assertIn("Requirement status: **1/1 complete**", report.render(result))

    def test_missing_completion_gate_is_an_evidence_gap_not_a_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            self.write_complete_evidence(root, uid)
            (ledger.state_dir(root, "run") / "completion-gates" / "gate-1.json").unlink()
            result = report.build(root, "run")
        self.assertEqual(result["tests"]["status"], "unavailable")
        self.assertEqual(result["overall_status"], "evidence-incomplete")


if __name__ == "__main__":
    unittest.main()
