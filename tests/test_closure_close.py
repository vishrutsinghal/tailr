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
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ledger = load("closure_close_ledger_test", "scripts/run-ledger.py")
anchor = load("closure_close_anchor_test", "scripts/change-intent-anchor.py")
lock = load("closure_close_lock_test", "scripts/planning-lock.py")
recorder = load("closure_close_recorder_test", "scripts/closure-recorder.py")
close = load("closure_close_test", "scripts/closure-close.py")


class ClosureCloseTests(unittest.TestCase):
    def setup_complete_run(self, root: Path) -> str:
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "service.py").write_text("def cancel():\n    return True\n", encoding="utf-8")
        (root / "tests" / "test_service.py").write_text("# focused test\n", encoding="utf-8")
        lock.create(root, "cancel an order", "run")
        proposal = root / "proposal.json"
        proposal.write_text(json.dumps({"requirements": [{
            "statement": "Cancel an eligible order exactly once.", "acceptance_criteria": ["cancelled once"],
            "preserve_rules": ["shipped orders remain rejected"],
            "likely_paths": ["src/service.py", "tests/test_service.py"], "evidence_plan": [],
            "validation_contract": {"state": "required", "tiers": ["unit"]},
            "architecture_contract": {"required_paths": [], "protected_paths": [], "forbidden_imports": []},
            "behavior_contract": {"scenarios": [{
                "scenario_id": "eligible-cancellation", "preconditions": ["eligible order"],
                "action": "cancel order", "expected_outcome": "one cancellation", "preservation": ["shipped orders reject"],
                "evidence": [{"tier": "unit", "asserted_behavior": "Eligible order cancellation is idempotent."}],
            }]},
        }]}), encoding="utf-8")
        anchor.draft(root, "run", proposal)
        uid = anchor.approve(root, "run")["requirements"][0]["requirement_uid"]
        lock.approve(root, "run", True)
        run = ledger.state_dir(root, "run")
        (run / "planning").mkdir(exist_ok=True)
        (run / "planning" / "execution-handoff-v1.json").write_text(json.dumps({"closure": {"selected_harnesses": [
            "Architecture Fitness Harness", "Behaviour Harness", "Maintainability Harness",
        ]}}), encoding="utf-8")
        input_path = root / "closure-input.json"
        input_path.write_text(json.dumps({
            "schema_version": "1", "type": "tailtrail-execution-closure-input", "run_id": "run",
            "changed_paths": ["src/service.py", "tests/test_service.py"],
            "receipts": [{"requirement_uids": [uid], "tier": "unit", "command_label": "cancellation unit proof",
                "command": "tailtrail-never-execute-close-sentinel", "outcome": "pass", "environment": "local",
                "asserted_behavior": "Eligible order cancellation is idempotent."}],
        }), encoding="utf-8")
        recorder.record(root, input_path)
        return uid

    def test_complete_close_prompts_before_acceptance_and_persists_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup_complete_run(root)
            result = close.close(root, "run")
            baseline = root / result["baseline"]
            decision = root / result["acceptance_record"]["artifact"]
            baseline_exists = baseline.is_file()
            decision_exists = decision.is_file()
            boundary = json.loads(baseline.read_text(encoding="utf-8"))["boundary"]

        self.assertEqual(result["state"], "awaiting-acceptance")
        self.assertEqual(result["acceptance_prompt"]["options"], ["accept-user", "wait-ci", "reopen"])
        self.assertTrue(baseline_exists)
        self.assertTrue(decision_exists)
        self.assertIn("pre-implementation approved anchor", boundary)

    def test_user_acceptance_creates_candidate_learning_and_paired_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup_complete_run(root)
            result = close.close(root, "run", "accept-user")
            decision = root / result["acceptance_record"]["artifact"]
            decision_exists = decision.is_file()

        self.assertEqual(result["state"], "accepted")
        self.assertEqual(result["positive_learning"]["promotion"], "candidate-only; explicit learning review required")
        self.assertEqual(result["evaluation"]["mode"], "paired")
        self.assertTrue(decision_exists)

    def test_incomplete_close_cannot_offer_or_create_positive_learning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup_complete_run(root)
            checkpoints = ledger.state_dir(root, "run") / "checkpoints"
            checkpoint_path = next(checkpoints.glob("checkpoint-*.json"))
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            checkpoint["requirements"][0]["state"] = "incomplete"
            checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
            result = close.close(root, "run")
            learning_exists = (root / ".tailtrail" / "runs" / "run" / "positive-learning").exists()

        self.assertEqual(result["state"], "evidence-incomplete")
        self.assertNotIn("acceptance_prompt", result)
        self.assertFalse(learning_exists)


if __name__ == "__main__":
    unittest.main()
