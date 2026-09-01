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
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
    return module


intake = load("di6_intake", "scripts/debug-intake.py")
reproduction = load("di6_reproduction", "scripts/debug-reproduction.py")
hypothesis = load("di6_hypothesis", "scripts/debug-hypothesis.py")
evidence = load("di6_evidence", "scripts/execution-evidence.py")


class DebugHypothesisIntegrationTests(unittest.TestCase):
    def _run(self, root: Path) -> tuple[str, str, str]:
        intake.open_intake(root, "di6", "payment retry duplicates effects", None, None, False)
        reproduction.draft(root, "di6", {"domain":"code", "trigger":"timeout after payment acceptance", "expected":"one effect", "actual":"two effects", "reproduction_method":"local deterministic adapter test", "preserve_rules":["successful payment remains valid"], "safety_boundary":"local adapters only"})
        reproduction.approve(root, "di6")
        uid = reproduction.show(root, "di6")["requirement_uid"]
        event = evidence.append(root, "di6", {"kind":"command-result", "requirement_uids":[uid], "tier":"integration", "command_label":"timeout adapter", "command":"python -m unittest timeout_adapter", "outcome":"fail", "environment":"local", "asserted_behavior":"duplicate effect reproduced"}, True)
        ledger = hypothesis.add_hypothesis(root, "di6", "code", "retry lacks stable idempotency", 1)
        return uid, event["fingerprint"], ledger["hypotheses"][0]["hypothesis_id"]

    def test_experiment_is_requirement_and_failure_linked_and_duplicate_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); uid, event_id, hypothesis_id = self._run(root)
            result = hypothesis.record_experiment(root, "di6", hypothesis_id, "inspect retry key trace", "strengthens", event_id, True, "retry keys differ")
            saved = json.loads(hypothesis.experiments_path(root, "di6").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(saved["requirement_uid"], uid)
            self.assertTrue(saved["failure_fingerprint"].startswith("sha256:"))
            self.assertEqual(saved["cycle"], 1)
            self.assertEqual(result["cycle_limit"], 3)
            experiment_schema = json.loads((ROOT / "schemas" / "debug-experiment.schema.json").read_text(encoding="utf-8"))
            ledger_schema = json.loads((ROOT / "schemas" / "hypothesis-ledger.schema.json").read_text(encoding="utf-8"))
            self.assertEqual(contracts.validate_document(saved, experiment_schema), [])
            self.assertEqual(contracts.validate_document(result, ledger_schema), [])
            with self.assertRaisesRegex(ValueError, "identical experiment"):
                hypothesis.record_experiment(root, "di6", hypothesis_id, "inspect retry key trace", "strengthens", event_id, True, "retry keys differ")

    def test_proposal_and_reprioritization_are_versioned_metadata_only_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); uid, _, first_id = self._run(root)
            ledger = hypothesis.add_hypothesis(root, "di6", "architecture", "caller bypasses adapter", 2)
            second_id = ledger["hypotheses"][1]["hypothesis_id"]
            proposal = hypothesis.propose_experiment(root, "di6", first_id, "compare retry keys", "keys differ only on retry")
            ranking = hypothesis.reprioritize(root, "di6", [
                {"hypothesis_id": second_id, "rank": 1},
                {"hypothesis_id": first_id, "rank": 2},
            ])
            self.assertEqual(proposal["requirement_uid"], uid)
            self.assertIn("proposal only", proposal["boundary"].lower())
            self.assertIn("separately approve", proposal["boundary"].lower())
            self.assertEqual([row["hypothesis_id"] for row in ranking["rankings"]], [second_id, first_id])
            proposal_schema = json.loads((ROOT / "schemas" / "debug-experiment-proposal.schema.json").read_text(encoding="utf-8"))
            ranking_schema = json.loads((ROOT / "schemas" / "debug-hypothesis-ranking.schema.json").read_text(encoding="utf-8"))
            self.assertEqual(contracts.validate_document({key:value for key,value in proposal.items() if key != "artifact"}, proposal_schema), [])
            self.assertEqual(contracts.validate_document({key:value for key,value in ranking.items() if key != "artifact"}, ranking_schema), [])

    def test_advisory_observations_are_saved_and_rendered_without_becoming_proof(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); _, _, hypothesis_id = self._run(root)
            result = hypothesis.annotate_hypothesis(root, "di6", hypothesis_id, {
                "advisory_evidence": [{
                    "direction": "supports", "label": "local-source-observation",
                    "summary": "Retry request keys differ by attempt.",
                    "artifact_ref": "src/payment.py#retry",
                }],
                "evidence_gaps": ["No request-key experiment has run."],
                "discriminating_signal": "Two different request keys strengthen this hypothesis.",
            })
            row = result["hypotheses"][0]
            self.assertEqual(row["supporting_evidence"], [])
            self.assertEqual(row["advisory_evidence"][0]["direction"], "supports")
            markdown = hypothesis.render_markdown(result)
            self.assertIn("| Hypothesis | Supporting evidence | Contradicting evidence | Saved rank |", markdown)
            self.assertIn("[local-source-observation]", markdown)
            self.assertIn("Two different request keys", markdown)
            ledger_schema = json.loads((ROOT / "schemas" / "hypothesis-ledger.schema.json").read_text(encoding="utf-8"))
            self.assertEqual(contracts.validate_document(result, ledger_schema), [])

    def test_cycle_exhaustion_preserves_recovery_and_continuity_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); _, event_id, hypothesis_id = self._run(root)
            for number in range(1, 4):
                ledger = hypothesis.record_experiment(root, "di6", hypothesis_id, f"probe {number}", "unchanged", event_id, True, f"distinct signal {number}")
            self.assertTrue(ledger["investigation_blocked"])
            self.assertTrue((root / ledger["recovery_replan_ref"]).is_file())
            recovery = json.loads((root / ledger["recovery_replan_ref"]).read_text(encoding="utf-8"))
            self.assertEqual(recovery["requirement_uid"], ledger["requirement_uid"])
            self.assertEqual(len(recovery["preserved_experiment_refs"]), 3)
            self.assertTrue(list((root / ".tailtrail" / "runs" / "di6" / "continuity").glob("state-*.json")))
            resumed = hypothesis.replan(root, "di6", True)
            self.assertEqual(resumed["cycle"], 2)
            self.assertFalse(resumed["investigation_blocked"])


if __name__ == "__main__":
    unittest.main()
