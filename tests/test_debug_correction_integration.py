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
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module); return module


intake = load("di7_intake", "scripts/debug-intake.py")
reproduction = load("di7_reproduction", "scripts/debug-reproduction.py")
hypothesis = load("di7_hypothesis", "scripts/debug-hypothesis.py")
evidence = load("di7_evidence", "scripts/execution-evidence.py")
correction = load("di7_correction", "scripts/debug-correction.py")
convergence = load("di8_convergence", "scripts/debug-harness-convergence.py")


class DebugCorrectionIntegrationTests(unittest.TestCase):
    def _proven(self, root: Path) -> tuple[str, str]:
        intake.open_intake(root, "di7", "payment retry duplicates effects", None, None, False)
        reproduction.draft(root, "di7", {"domain":"code", "trigger":"timeout after acceptance", "expected":"one payment", "actual":"two payments", "reproduction_method":"local adapter test", "preserve_rules":["successful create-order remains valid"], "safety_boundary":"local adapters only"})
        reproduction.approve(root, "di7"); uid = reproduction.show(root, "di7")["requirement_uid"]
        receipt = evidence.append(root, "di7", {"kind":"command-result", "requirement_uids":[uid], "tier":"integration", "command_label":"payment trace", "command":"python -m unittest payment_trace", "outcome":"fail", "environment":"local", "asserted_behavior":"duplicate payment reproduced"}, True)
        first = hypothesis.add_hypothesis(root, "di7", "code", "retry lacks stable idempotency", 1)
        second = hypothesis.add_hypothesis(root, "di7", "code", "repository commits too late", 2)
        h1, h2 = first["hypotheses"][0]["hypothesis_id"], second["hypotheses"][1]["hypothesis_id"]
        hypothesis.record_experiment(root, "di7", h1, "inspect payment trace", "strengthens", receipt["fingerprint"], True, "retry keys differ")
        hypothesis.record_experiment(root, "di7", h2, "inspect repository timing", "eliminates", receipt["fingerprint"], True, "order state exists before retry")
        hypothesis.prove(root, "di7", h1); return uid, h1

    def test_incomplete_proposal_cannot_grant_implementation_authority(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); _, h1 = self._proven(root)
            proposal = correction.propose(root, "di7", h1, None)
            self.assertTrue(any("Expected changed paths" in item for item in proposal["unresolved_assumptions"]))
            with self.assertRaisesRegex(ValueError, "assumptions are unresolved"):
                correction.approve(root, "di7", True)

    def test_approved_packet_creates_exact_d08_handoff_and_scope_drift_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); uid, h1 = self._proven(root)
            source = {"expected_changed_paths":["src/payments.py", "tests/test_payments.py"], "expected_changed_symbols":[{"path":"src/payments.py", "symbols":["charge"]}], "architecture_constraints":["Reuse the payment adapter."], "validation_tiers":["focused", "integration"], "behaviour_scenarios":["timeout retry creates one effect"], "unresolved_assumptions":[]}
            proposal = correction.propose(root, "di7", h1, None, source)
            schema = json.loads((ROOT / "schemas" / "debug-correction-packet.schema.json").read_text(encoding="utf-8"))
            self.assertEqual(contracts.validate_document(proposal, schema), [])
            approved = correction.approve(root, "di7", True)
            authority = approved["implementation_authority"]
            self.assertEqual(authority["stage_id"], "d-08-correction-implementation")
            self.assertEqual(authority["action_class"], "write_project")
            self.assertEqual(approved["execution_handoff"]["requirement_uid"], uid)
            self.assertNotIn("publish", approved["execution_handoff"]["implementation_authority"])
            evidence.append(root, "di7", {"kind":"harness-result", "requirement_uids":[uid], "classification":"Behaviour Harness: restored"}, True)
            incomplete = convergence.finalize(root, "di7", True)
            convergence_schema = json.loads((ROOT / "schemas" / "debug-harness-convergence.schema.json").read_text(encoding="utf-8"))
            self.assertEqual(contracts.validate_document({key:value for key,value in incomplete.items() if key != "artifact"}, convergence_schema), [])
            behavior_row = next(row for row in incomplete["control_results"] if row["control"] == "Behaviour Harness")
            self.assertEqual(behavior_row["status"], "required-evidence-missing")
            exact = correction.scope_check(root, "di7", ["src/payments.py"], True)
            self.assertEqual(exact["status"], "within-approved-scope")
            drift = correction.scope_check(root, "di7", ["src/payments.py", "src/unrelated.py"], True)
            self.assertEqual(drift["status"], "drift")
            self.assertEqual(drift["unexpected_paths"], ["src/unrelated.py"])


if __name__ == "__main__": unittest.main()
