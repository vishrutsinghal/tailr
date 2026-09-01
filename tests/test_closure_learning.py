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


ledger = load("closure_learning_ledger_test", "scripts/run-ledger.py")
anchor = load("closure_learning_anchor_test", "scripts/change-intent-anchor.py")
lock = load("closure_learning_lock_test", "scripts/planning-lock.py")
recorder = load("closure_learning_recorder_test", "scripts/closure-recorder.py")
finalizer = load("closure_learning_finalizer_test", "scripts/closure-finalizer.py")
learning = load("closure_learning_test", "scripts/closure-learning.py")
evaluation = load("closure_evaluation_test", "scripts/closure-evaluation.py")
close = load("closure_close_test", "scripts/closure-close.py")


class ClosureLearningTests(unittest.TestCase):
    def setup_run(self, root: Path, outcome: str = "pass") -> str:
        (root / "src").mkdir(); (root / "tests").mkdir()
        (root / "src" / "service.py").write_text("def cancel():\n    return True\n", encoding="utf-8")
        (root / "tests" / "test_service.py").write_text("# focused proof\n", encoding="utf-8")
        lock.create(root, "cancel eligible order", "run")
        proposal = root / "proposal.json"
        proposal.write_text(json.dumps({"requirements": [{
            "statement": "Cancel an eligible order exactly once.", "acceptance_criteria": ["cancelled once"],
            "preserve_rules": ["shipped orders remain rejected"], "likely_paths": ["src/service.py", "tests/test_service.py"],
            "evidence_plan": [], "validation_contract": {"state": "required", "tiers": ["unit"]},
            "architecture_contract": {"required_paths": [], "protected_paths": [], "forbidden_imports": []}, "behavior_contract": {"scenarios": []},
        }]}), encoding="utf-8")
        anchor.draft(root, "run", proposal)
        uid = anchor.approve(root, "run")["requirements"][0]["requirement_uid"]
        lock.approve(root, "run", True)
        run = ledger.state_dir(root, "run")
        (run / "planning").mkdir(exist_ok=True)
        (run / "planning" / "execution-handoff-v1.json").write_text(json.dumps({"closure": {"selected_harnesses": []}}), encoding="utf-8")
        closure = root / "closure.json"
        closure.write_text(json.dumps({"schema_version": "1", "type": "tailtrail-execution-closure-input", "run_id": "run", "changed_paths": ["src/service.py", "tests/test_service.py"], "receipts": [{"requirement_uids": [uid], "tier": "unit", "command_label": "unit proof", "command": "never-run-sentinel", "outcome": outcome, "environment": "local", "asserted_behavior": "eligible cancellation is idempotent"}]}), encoding="utf-8")
        recorder.record(root, closure)
        finalizer.finalize(root, "run")
        return uid

    def test_accepted_complete_run_creates_sanitized_candidate_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup_run(root)
            first = learning.capture(root, "run", "trusted-ci")
            second = learning.capture(root, "run", "trusted-ci")
            activity = ledger.projection(root, "run")["activity"]
            v3_exists = (root / ".tailtrail" / "learning-v3" / "events.jsonl").is_file()
        self.assertFalse(first["reused"])
        self.assertTrue(second["reused"])
        self.assertEqual(first["promotion"], "candidate-only; explicit learning review required")
        self.assertNotIn("service.py", json.dumps(first))
        self.assertEqual(activity["closure_positive_learning_captured"], 1)
        self.assertTrue(v3_exists)

    def test_incomplete_run_cannot_become_positive_learning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup_run(root, "fail")
            with self.assertRaisesRegex(ValueError, "not eligible"):
                learning.capture(root, "run", "user")
        self.assertFalse((root / ".tailtrail" / "runs" / "run" / "positive-learning").exists())

    def test_paired_evaluation_is_saved_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup_run(root)
            baseline = root / "baseline.json"
            baseline.write_text(json.dumps({"type": "tailtrail-closure-baseline", "requirements_complete": 0, "requirements_total": 1, "unresolved_drift": 1, "tests_pass": False}), encoding="utf-8")
            first = evaluation.evaluate(root, "run", baseline)
            second = evaluation.evaluate(root, "run", baseline)
            activity = ledger.projection(root, "run")["activity"]
        self.assertEqual(first["mode"], "paired")
        self.assertEqual(first["comparison"]["requirement_completion_delta"], 1)
        self.assertTrue(second["reused"])
        self.assertEqual(activity["closure_evaluation_calibrated"], 1)

    def test_close_shows_report_before_acceptance_then_automates_user_closeout(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup_run(root)
            preview = close.close(root, "run")
            accepted = close.close(root, "run", "accept-user")
        self.assertEqual(preview["state"], "awaiting-acceptance")
        self.assertEqual(preview["acceptance_prompt"]["options"], ["accept-user", "wait-ci", "reopen"])
        self.assertEqual(accepted["state"], "accepted")
        self.assertEqual(accepted["evaluation"]["mode"], "paired")

    def test_close_requires_run_id_when_no_closure_is_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "no approved"):
                close.resolve_run(root, None)

    def test_close_refuses_a_canonical_state_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup_run(root)
            checkpoint = sorted((ledger.state_dir(root, "run") / "checkpoints").glob("checkpoint-*.json"))[-1]
            payload = json.loads(checkpoint.read_text(encoding="utf-8"))
            payload["run_id"] = "different-run"
            checkpoint.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "canonical run state has unresolved conflicts"):
                close.close(root, "run")

    def test_official_closure_links_references_without_copying_artifact_bodies(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.setup_run(root)
            official = ledger.state_dir(root, "run") / "aidlc-official"
            official.mkdir(parents=True)
            (official / "bridge-v1.json").write_text(json.dumps({"official_intent_id": "intent-1", "official_session_id": "session-1", "official_revision": "v2"}), encoding="utf-8")
            checkpoints = official / "checkpoints"; checkpoints.mkdir()
            (checkpoints / "handoff-v1.json").write_text(json.dumps({"secret_receipt_body": "do-not-copy"}), encoding="utf-8")
            preview = close.close(root, "run")
            link = preview["official_aidlc"]
        self.assertEqual(link["official_intent_id"], "intent-1")
        self.assertIn("handoff-v1.json", link["official_handoff_reference"])
        self.assertNotIn("secret_receipt_body", json.dumps(link))

    def test_ci_acceptance_requires_linked_ingestion_and_then_learns(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.setup_run(root)
            receipt = ledger.state_dir(root, "run") / "ci-ingestion" / "ingestion-1.json"; receipt.parent.mkdir()
            receipt.write_text(json.dumps({"type": "tailtrail-ci-evidence-ingestion", "run_id": "run", "provenance": {"run_id": "ci-1"}, "receipts": [{"outcome": "pass"}]}), encoding="utf-8")
            accepted = close.close(root, "run", "accept-ci", ci_receipt=receipt)
        self.assertEqual(accepted["accepted_by"], "trusted-ci")
        self.assertEqual(accepted["positive_learning"]["acceptance"]["accepted_by"], "trusted-ci")


if __name__ == "__main__":
    unittest.main()
