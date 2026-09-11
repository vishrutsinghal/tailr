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
    def _proven(
        self,
        root: Path,
        diagnosis: dict | None = None,
        fault_layer: str | None = None,
        trace_node_ids: list[str] | None = None,
    ) -> tuple[str, str]:
        intake.open_intake(root, "di7", "payment retry duplicates effects", None, None, False)
        reproduction.draft(root, "di7", {"domain":"code", "trigger":"timeout after acceptance", "expected":"one payment", "actual":"two payments", "reproduction_method":"local adapter test", "preserve_rules":["successful create-order remains valid"], "safety_boundary":"local adapters only"})
        reproduction.approve(root, "di7"); uid = reproduction.show(root, "di7")["requirement_uid"]
        receipt = evidence.append(root, "di7", {"kind":"command-result", "requirement_uids":[uid], "tier":"integration", "command_label":"payment trace", "command":"python -m unittest payment_trace", "outcome":"fail", "environment":"local", "asserted_behavior":"duplicate payment reproduced"}, True)
        reproduction.record_attempt(root, "di7", "pre-fix", "reproduced", receipt["fingerprint"], "The approved duplicate-payment signature was observed.", ["command-or-actions", "input-or-fixture"], True)
        first = hypothesis.add_hypothesis(root, "di7", "code", "retry lacks stable idempotency", 1)
        second = hypothesis.add_hypothesis(root, "di7", "code", "repository commits too late", 2)
        h1, h2 = first["hypotheses"][0]["hypothesis_id"], second["hypotheses"][1]["hypothesis_id"]
        hypothesis.record_experiment(root, "di7", h1, "inspect payment trace", "strengthens", receipt["fingerprint"], True, "retry keys differ")
        hypothesis.record_experiment(root, "di7", h2, "inspect repository timing", "eliminates", receipt["fingerprint"], True, "order state exists before retry")
        if diagnosis is not None:
            report_path = root / ".tailtrail" / "runs" / "di7" / "planning" / "start-report-v1.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps({"report": {"debug_plan": {"behavior_trace": diagnosis["behavior_trace"], "host_diagnosis": diagnosis}}}), encoding="utf-8")
        hypothesis.prove(root, "di7", h1, fault_layer, trace_node_ids); return uid, h1

    def _diagnosis(self, layer: str) -> tuple[dict, list[str], list[str]]:
        nodes = []
        tests = []
        selected = []
        expected_boundaries = []
        if layer in {"composition", "cross-layer"}:
            nodes.append({"id": "TRACE-COMPOSE", "role": "data-producer"})
            selected.append("TRACE-COMPOSE")
            expected_boundaries.append("composition")
            tests.append({"id": "TEST-COMPOSE", "path": "tests/test_composition.py", "command": "pytest tests/test_composition.py -q", "tier": "unit", "proof_boundaries": ["composition"]})
        if layer in {"rendering", "cross-layer"}:
            nodes.append({"id": "TRACE-RENDER", "role": "output-renderer"})
            selected.append("TRACE-RENDER")
            expected_boundaries.append("renderer")
            tests.append({"id": "TEST-RENDER", "path": "tests/test_renderer.py", "command": "pytest tests/test_renderer.py -q", "tier": "component", "proof_boundaries": ["renderer"]})
        if layer == "end-user":
            nodes.append({"id": "TRACE-OUTPUT", "role": "observed-output"})
            selected.append("TRACE-OUTPUT")
            expected_boundaries.append("final-output")
            tests.append({"id": "TEST-OUTPUT", "path": "tests/test_output.py", "command": "pytest tests/test_output.py -q", "tier": "behaviour", "proof_boundaries": ["final-output"]})
        return {"behavior_trace": {"state": "resolved-to-producer", "nodes": nodes, "edges": []}, "test_cases": tests}, selected, expected_boundaries

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

    def test_proof_is_selected_from_each_proven_fault_layer(self):
        for layer in ("composition", "rendering", "end-user", "cross-layer"):
            with self.subTest(layer=layer), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                diagnosis, node_ids, boundaries = self._diagnosis(layer)
                _, h1 = self._proven(root, diagnosis, layer, node_ids)
                proposal = correction.propose(
                    root,
                    "di7",
                    h1,
                    None,
                    {"expected_changed_paths": ["src/fix.py"], "validation_tiers": [], "unresolved_assumptions": []},
                )

                alignment = proposal["proof_alignment"]
                self.assertEqual(alignment["state"], "matched")
                self.assertEqual(alignment["fault_layer"], layer)
                self.assertEqual(alignment["required_boundaries"], sorted(boundaries))
                self.assertEqual(
                    {boundary for row in alignment["selected_tests"] for boundary in row["boundaries"]},
                    set(boundaries),
                )
                self.assertEqual(len(proposal["validation_plan"]["commands"]), len(boundaries))

    def test_missing_fault_layer_proof_blocks_correction_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diagnosis, node_ids, _ = self._diagnosis("rendering")
            diagnosis["test_cases"] = []
            _, h1 = self._proven(root, diagnosis, "rendering", node_ids)
            proposal = correction.propose(
                root,
                "di7",
                h1,
                None,
                {"expected_changed_paths": ["src/render.py"], "unresolved_assumptions": []},
            )
            self.assertEqual(proposal["proof_alignment"]["state"], "missing-proof")
            self.assertEqual(proposal["proof_alignment"]["missing_boundaries"], ["renderer"])
            with self.assertRaisesRegex(ValueError, "No focused `renderer` proof"):
                correction.approve(root, "di7", True)

    def test_root_cause_rejects_a_fault_layer_that_conflicts_with_trace_nodes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diagnosis, node_ids, _ = self._diagnosis("composition")
            with self.assertRaisesRegex(ValueError, "does not match selected trace nodes"):
                self._proven(root, diagnosis, "rendering", node_ids)

    def test_convergence_requires_the_exact_fault_layer_proof_command(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diagnosis, node_ids, _ = self._diagnosis("composition")
            uid, h1 = self._proven(root, diagnosis, "composition", node_ids)
            correction.propose(
                root,
                "di7",
                h1,
                None,
                {"expected_changed_paths": ["src/compose.py"], "validation_tiers": [], "unresolved_assumptions": []},
            )
            correction.approve(root, "di7", True)
            evidence.append(root, "di7", {"kind": "source-edit", "requirement_uids": [uid], "changed_paths": ["src/compose.py"]}, True)
            correction.scope_check(root, "di7", ["src/compose.py"], True)
            before = convergence.finalize(root, "di7", True)
            before_alignment = next(row for row in before["control_results"] if row["control"] == "Fault-Layer Proof Alignment")
            self.assertEqual(before_alignment["status"], "required-evidence-missing")
            evidence.append(root, "di7", {
                "kind": "command-result",
                "requirement_uids": [uid],
                "tier": "unit",
                "command_label": "composition proof",
                "command": "pytest tests/test_composition.py -q",
                "outcome": "pass",
                "environment": "local",
                "asserted_behavior": "composition no longer duplicates steps",
            }, True)
            after = convergence.finalize(root, "di7", True)
            after_alignment = next(row for row in after["control_results"] if row["control"] == "Fault-Layer Proof Alignment")
            self.assertEqual(after_alignment["status"], "pass")
            self.assertEqual(len(after_alignment["evidence"]), 1)


if __name__ == "__main__": unittest.main()
