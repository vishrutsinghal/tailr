from __future__ import annotations
import importlib.util, json, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


intake = load("debug_harness_test_intake", "scripts/debug-intake.py")
reproduction = load("debug_harness_test_reproduction", "scripts/debug-reproduction.py")
hypothesis = load("debug_harness_test_hypothesis", "scripts/debug-hypothesis.py")
correction = load("debug_harness_test_correction", "scripts/debug-correction.py")
completion = load("debug_harness_test_completion", "scripts/debug-completion.py")
evidence = load("debug_harness_test_evidence", "scripts/execution-evidence.py")

CONTRACT_SOURCE = {
    "domain": "code",
    "trigger": "Payment gateway times out after accepting the charge",
    "expected": "One charge and one order",
    "actual": "Retry creates a second charge",
    "reproduction_method": "Integration test with a timeout-after-acceptance adapter double",
    "preserve_rules": ["Successful order creation remains unchanged"],
    "safety_boundary": "Do not call a real payment provider",
}


class DebugHarnessTests(unittest.TestCase):
    def open_and_approve(self, root: Path, run_id: str = "run") -> str:
        """Opens intake, drafts+approves a reproduction contract, and returns the
        approved investigation requirement_uid."""
        intake.open_intake(root, run_id, "Orders double-charge on payment timeout", None, None, False)
        reproduction.draft(root, run_id, CONTRACT_SOURCE)
        reproduction.approve(root, run_id)
        anchor = json.loads((root / ".tailtrail" / "runs" / run_id / "anchors" / "approved-v1.json").read_text(encoding="utf-8"))
        return anchor["requirements"][0]["requirement_uid"]

    def record_command_evidence(self, root: Path, run_id: str, uid: str, outcome: str = "pass") -> str:
        event = {"kind": "command-result", "requirement_uids": [uid], "tier": "integration", "command_label": "trace payment adapter calls", "command": "python3 -m unittest tests.integration.test_payment", "outcome": outcome, "environment": "local", "asserted_behavior": "traced both payment adapter calls"}
        return evidence.append(root, run_id, event, True)["fingerprint"]

    def test_full_happy_path_reaches_domain_ceiling(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.open_and_approve(root)
            fp = self.record_command_evidence(root, "run", uid)
            hypothesis.add_hypothesis(root, "run", "code", "Retry lacks an idempotency key", 1)
            ledger = hypothesis.add_hypothesis(root, "run", "code", "Repository saves order state too late", 2)
            h1, h2 = ledger["hypotheses"][0]["hypothesis_id"], ledger["hypotheses"][1]["hypothesis_id"]
            hypothesis.record_experiment(root, "run", h1, "traced both payment calls, no idempotency key sent", "strengthens", fp, True)
            hypothesis.record_experiment(root, "run", h2, "order state present at retry time", "eliminates", fp, True)
            proven = hypothesis.prove(root, "run", h1)
            self.assertEqual(next(row for row in proven["hypotheses"] if row["hypothesis_id"] == h1)["status"], "proven")
            correction.propose(root, "run", h1, None)
            correction.approve(root, "run", True)
            evidence.append(root, "run", {"kind": "harness-result", "requirement_uids": [uid], "classification": "Behaviour Harness: checkout-with-timeout user journey restored"}, True)
            report = completion.generate(root, "run")
            self.assertEqual(report["confidence_state"], "behavior-restored")
            self.assertEqual(report["acceptance_state"], "accept-user")
            self.assertEqual(report["domains_eliminated"], [])
            self.assertEqual(report["gaps"], [])

    def test_unsupported_domain_is_rejected_at_reproduction_and_hypothesis(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            intake.open_intake(root, "run", "symptom", None, None, False)
            with self.assertRaisesRegex(ValueError, "not supported"):
                reproduction.draft(root, "run", {**CONTRACT_SOURCE, "domain": "cloud-infrastructure"})
            reproduction.draft(root, "run", CONTRACT_SOURCE)
            reproduction.approve(root, "run")
            with self.assertRaisesRegex(ValueError, "not supported"):
                hypothesis.add_hypothesis(root, "run", "network", "a network hypothesis", 1)

    def test_experiment_requires_a_real_execution_evidence_event(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.open_and_approve(root)
            ledger = hypothesis.add_hypothesis(root, "run", "code", "Retry lacks an idempotency key", 1)
            h1 = ledger["hypotheses"][0]["hypothesis_id"]
            with self.assertRaisesRegex(ValueError, "does not match a recorded"):
                hypothesis.record_experiment(root, "run", h1, "unbacked claim", "strengthens", "not-a-real-fingerprint", True)

    def test_prove_requires_supporting_evidence_and_an_eliminated_competitor(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.open_and_approve(root)
            fp = self.record_command_evidence(root, "run", uid)
            ledger = hypothesis.add_hypothesis(root, "run", "code", "Retry lacks an idempotency key", 1)
            h1 = ledger["hypotheses"][0]["hypothesis_id"]
            with self.assertRaisesRegex(ValueError, "no recorded supporting evidence"):
                hypothesis.prove(root, "run", h1)
            hypothesis.record_experiment(root, "run", h1, "traced both payment calls", "strengthens", fp, True)
            with self.assertRaisesRegex(ValueError, "no competing hypothesis has been eliminated"):
                hypothesis.prove(root, "run", h1)

    def test_cycle_limit_blocks_until_replan_approved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid = self.open_and_approve(root)
            fp = self.record_command_evidence(root, "run", uid)
            ledger = hypothesis.add_hypothesis(root, "run", "code", "Retry lacks an idempotency key", 1)
            h1 = ledger["hypotheses"][0]["hypothesis_id"]
            for _ in range(hypothesis.DEFAULT_CYCLE_LIMIT):
                ledger = hypothesis.record_experiment(root, "run", h1, "inconclusive probe", "inconclusive", fp, True)
            self.assertTrue(ledger["investigation_blocked"])
            with self.assertRaisesRegex(ValueError, "investigation is blocked"):
                hypothesis.record_experiment(root, "run", h1, "one more probe", "inconclusive", fp, True)
            with self.assertRaisesRegex(ValueError, "--approved"):
                hypothesis.replan(root, "run", False)
            resumed = hypothesis.replan(root, "run", True)
            self.assertFalse(resumed["investigation_blocked"])
            self.assertEqual(resumed["experiments_since_reset"], 0)

    def test_reproduction_cannot_be_approved_twice(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.open_and_approve(root)
            with self.assertRaisesRegex(ValueError, "already approved"):
                reproduction.approve(root, "run")

    def test_completion_report_caps_at_domain_ceiling(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            intake.open_intake(root, "run", "slow query on checkout", None, None, False)
            reproduction.draft(root, "run", {**CONTRACT_SOURCE, "domain": "database", "trigger": "Slow query on checkout"})
            reproduction.approve(root, "run")
            anchor = json.loads((root / ".tailtrail" / "runs" / "run" / "anchors" / "approved-v1.json").read_text(encoding="utf-8"))
            uid = anchor["requirements"][0]["requirement_uid"]
            fp = self.record_command_evidence(root, "run", uid)
            ledger = hypothesis.add_hypothesis(root, "run", "database", "Missing index on orders.customer_id", 1)
            ledger2 = hypothesis.add_hypothesis(root, "run", "database", "Lock contention on retry", 2)
            h1, h2 = ledger["hypotheses"][0]["hypothesis_id"], ledger2["hypotheses"][1]["hypothesis_id"]
            hypothesis.record_experiment(root, "run", h1, "EXPLAIN shows full table scan", "strengthens", fp, True)
            hypothesis.record_experiment(root, "run", h2, "no lock wait observed", "eliminates", fp, True)
            hypothesis.prove(root, "run", h1)
            correction.propose(root, "run", h1, None)
            correction.approve(root, "run", True)
            evidence.append(root, "run", {"kind": "harness-result", "requirement_uids": [uid], "classification": "Behaviour Harness: checkout-with-timeout user journey restored"}, True)
            report = completion.generate(root, "run")
            self.assertEqual(report["domain_confidence_ceiling"], "regression-validated")
            self.assertEqual(report["confidence_state"], "regression-validated")


if __name__ == "__main__":
    unittest.main()
