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
        self.assertTrue(result["canonical_state"]["valid"])
        self.assertEqual(result["requirement_status"]["complete"], 1)
        self.assertEqual(result["requirement_status"]["total"], 1)
        self.assertEqual(result["changed_scope"]["status"], "approved")
        self.assertEqual(result["tests"]["passed_tiers"], ["integration", "unit"])
        harnesses = {item["name"]: item for item in result["harnesses"]}
        self.assertEqual(harnesses["Requirement Completion Harness"]["status"], "pass")
        self.assertTrue(harnesses["Maintainability Harness"]["used"])
        self.assertEqual(harnesses["Maintainability Harness"]["status"], "pass")
        self.assertEqual(shown["overall_status"], "complete")
        rendered = report.render(result)
        self.assertIn("## Requirement delivery status", rendered)
        self.assertIn("## TailTrail control status", rendered)
        self.assertIn("| REQ-01 - reject zero claims | complete | 1 saved item(s) | resolved |", rendered)
        self.assertIn("| Requirement Completion Harness | pass |", rendered)
        self.assertIn("| Canonical run state |", rendered)
        self.assertIn("| Actual model tokens | unavailable |", rendered)

    def test_missing_completion_gate_is_an_evidence_gap_not_a_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            self.write_complete_evidence(root, uid)
            (ledger.state_dir(root, "run") / "completion-gates" / "gate-1.json").unlink()
            result = report.build(root, "run")
        self.assertEqual(result["tests"]["status"], "not-evidenced")
        self.assertEqual(result["overall_status"], "evidence-incomplete")

    def test_no_execution_evidence_is_labelled_not_assessed_not_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup_run(root)
            result = report.build(root, "run")
            rendered = report.render(result)

        self.assertEqual(result["requirement_status"]["requirements"][0]["status"], "not-evidenced")
        self.assertEqual(result["changed_scope"]["status"], "not-assessed")
        self.assertEqual(result["drift"]["status"], "not-assessed")
        self.assertEqual(result["tests"]["status"], "not-evidenced")
        self.assertIn("not assessed", rendered)
        controls = {item["control"]: item for item in result["tailtrail_status"]}
        self.assertEqual(controls["Gap learning"]["status"], "gap-recorded")
        self.assertIn("incomplete-delivery observation only", controls["Gap learning"]["detail"])

    def test_report_uses_only_run_linked_measured_token_usage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            self.write_complete_evidence(root, uid)
            planning = ledger.state_dir(root, "run") / "planning"
            planning.mkdir()
            (planning / "start-report-v1.json").write_text(json.dumps({"token_posture": {"used_tokens": 42}}), encoding="utf-8")
            trail = root / ".tailtrail"
            trail.mkdir(exist_ok=True)
            (trail / "token-usage.jsonl").write_text("\n".join([
                json.dumps({"mode": "measured", "task_id": "other", "tailtrail": {"total_tokens": 999}}),
                json.dumps({"mode": "measured", "task_id": "run", "tailtrail": {"total_tokens": 123}}),
            ]) + "\n", encoding="utf-8")
            result = report.build(root, "run")
        self.assertEqual(result["token_usage"]["planning_estimate_tokens"], 42)
        self.assertEqual(result["token_usage"]["status"], "measured")
        self.assertEqual(result["token_usage"]["actual_tailtrail_tokens"], 123)
        self.assertIn("| Actual model tokens | measured | 123 tokens from 1 linked record(s) |", report.render(result))

    def test_report_reads_token_estimate_from_saved_start_report_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            self.write_complete_evidence(root, uid)
            planning = ledger.state_dir(root, "run") / "planning"
            planning.mkdir(exist_ok=True)
            (planning / "start-report-v1.json").write_text(json.dumps({"report": {"token_posture": {"used_tokens": 42}}}), encoding="utf-8")
            result = report.build(root, "run")
        self.assertEqual(result["token_usage"]["planning_estimate_tokens"], 42)

    def test_unresolved_drift_creates_same_run_learning_observation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.setup_run(root)
            self.write_complete_evidence(root, uid)
            checkpoint = ledger.state_dir(root, "run") / "checkpoints" / "checkpoint-1.json"
            data = json.loads(checkpoint.read_text(encoding="utf-8"))
            data["drift"] = [{"requirement_uid": uid, "classification": "new-drift"}]
            checkpoint.write_text(json.dumps(data), encoding="utf-8")
            result = report.build(root, "run")
            observation = ledger.state_dir(root, "run") / "learning-observations" / "drift-v1.json"
            saved = json.loads(observation.read_text(encoding="utf-8"))
            self.assertEqual(result["drift_learning"]["status"], "recorded")
            self.assertEqual(saved["run_id"], "run")
            self.assertEqual(saved["promotion"], "same-run continuity only; explicit review is required before any cross-run learning promotion")
            self.assertEqual(result["requirement_status"]["requirements"][0]["status"], "incomplete")
            self.assertEqual(result["requirement_status"]["requirements"][0]["drift"][0]["classification"], "new-drift")
            self.assertEqual(result["completion_learning"]["status"], "captured")
            events = (root / ".tailtrail" / "learning-events.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(events), 1)
            event = json.loads(events[0])
            self.assertEqual(event["source_run_id"], "run")
            self.assertNotIn("reject zero claims", events[0])
            repeated = report.build(root, "run")
            self.assertEqual(repeated["completion_learning"]["status"], "reused")
            self.assertEqual(len((root / ".tailtrail" / "learning-events.jsonl").read_text(encoding="utf-8").splitlines()), 1)
            self.assertIn("| REQ-01 - reject zero claims | incomplete | 1 saved item(s) | new-drift |", report.render(result))


if __name__ == "__main__":
    unittest.main()
