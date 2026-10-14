import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
STATE_SCHEMA_PATH = ROOT / "schemas" / "host-question-flow-state.schema.json"
TRANSITIONS_PATH = ROOT / "schemas" / "host-question-flow-transitions.json"
PACKET_VIEW_SCHEMA_PATH = ROOT / "schemas" / "host-question-flow-packet-view.schema.json"
PROOF_BINDING_SCHEMA_PATH = ROOT / "schemas" / "proof-binding.schema.json"
REDACTION_SCHEMA_PATH = ROOT / "schemas" / "host-question-flow-redaction-policy.schema.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _state_enum(schema: dict) -> list[str]:
    return schema["$defs"]["state"]["enum"]


class RunStateSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = _load(STATE_SCHEMA_PATH)
        self.validator = jsonschema.Draft202012Validator(self.schema)
        self.transitions = _load(TRANSITIONS_PATH)

    def test_schema_itself_is_structurally_valid(self) -> None:
        jsonschema.Draft202012Validator.check_schema(self.schema)

    def test_minimal_record_is_valid(self) -> None:
        record = {
            "schema_version": "1",
            "type": "tailtrail-host-question-flow-run-state",
            "run_id": "run-1",
            "current_state": "intake",
        }
        self.assertEqual(list(self.validator.iter_errors(record)), [])

    def test_unknown_state_is_rejected(self) -> None:
        record = {
            "schema_version": "1",
            "type": "tailtrail-host-question-flow-run-state",
            "run_id": "run-1",
            "current_state": "not-a-real-state",
        }
        self.assertFalse(self.validator.is_valid(record))

    def test_every_transition_endpoint_is_a_known_state(self) -> None:
        known = set(_state_enum(self.schema))
        for edge in self.transitions["edges"]:
            with self.subTest(edge=edge):
                self.assertIn(edge["from"], known)
                self.assertIn(edge["to"], known)

    def test_design_doc_main_sequence_is_present(self) -> None:
        """Regression: the linear sequence from the design doc's
        'Resumable States' diagram must be transcribed edge-for-edge."""
        expected_sequence = [
            "intake", "profiling", "awaiting-host-answers", "due-diligence",
            "awaiting-clarification", "awaiting-reproduction-input",
            "premise-validated", "awaiting-user-decision",
            "requirements-finalized", "internal-due-diligence",
            "internal-clarification-routed-to-navigator", "awaiting-approval",
            "approved", "activated",
        ]
        edges = {(edge["from"], edge["to"]) for edge in self.transitions["edges"]}
        for left, right in zip(expected_sequence, expected_sequence[1:]):
            with self.subTest(left=left, right=right):
                self.assertIn((left, right), edges)

    def test_activated_can_reach_invalidated_false_premise(self) -> None:
        edges = {(edge["from"], edge["to"]) for edge in self.transitions["edges"]}
        self.assertIn(("activated", "invalidated-false-premise"), edges)

    def test_pause_expire_abandon_resume_sub_lifecycle_is_present(self) -> None:
        edges = {(edge["from"], edge["to"]) for edge in self.transitions["edges"]}
        for pair in [
            ("awaiting-host-answers", "paused"),
            ("paused", "expired"),
            ("expired", "abandoned"),
            ("abandoned", "resumed"),
        ]:
            with self.subTest(pair=pair):
                self.assertIn(pair, edges)

    def test_no_fabricated_edges_beyond_the_design_doc(self) -> None:
        """Exact edge count guards against silently inventing additional
        transitions (e.g. a tempting but unspecified paused->resumed
        shortcut) beyond what the design doc's diagrams literally show."""
        self.assertEqual(len(self.transitions["edges"]), 18)


class PacketViewSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = _load(PACKET_VIEW_SCHEMA_PATH)
        self.validator = jsonschema.Draft202012Validator(self.schema)

    def _base(self) -> dict:
        return {
            "schema_version": "1",
            "type": "tailtrail-host-question-flow-packet-view",
            "packet_view_id": "view-1",
            "run_id": "run-1",
            "contract_id": "contract-1",
            "anchor_version": "anchor-v3",
            "status": "materialized",
            "requirement_projections": [
                {"requirement_uid": "req-1", "consumer_component_id": "navigator", "projection_kind": "scope"}
            ],
        }

    def test_schema_itself_is_structurally_valid(self) -> None:
        jsonschema.Draft202012Validator.check_schema(self.schema)

    def test_minimal_materialized_view_is_valid(self) -> None:
        self.assertEqual(list(self.validator.iter_errors(self._base())), [])

    def test_packet_view_has_no_independent_version_counter(self) -> None:
        """Regression for the single-version-chain rule: a packet view must
        not accept its own revision/version field, only an anchor_version
        pointer."""
        view = self._base()
        view["packet_version"] = 2
        self.assertFalse(self.validator.is_valid(view))

    def test_malformed_anchor_version_is_rejected(self) -> None:
        view = self._base()
        view["anchor_version"] = "v3"
        self.assertFalse(self.validator.is_valid(view))

    def test_invalidated_view_requires_a_reason(self) -> None:
        view = self._base()
        view["status"] = "invalidated"
        self.assertFalse(self.validator.is_valid(view))
        view["invalidated_reason"] = "anchor corrected to v4"
        self.assertTrue(self.validator.is_valid(view))

    def test_unknown_projection_kind_is_rejected(self) -> None:
        view = self._base()
        view["requirement_projections"][0]["projection_kind"] = "not-a-real-kind"
        self.assertFalse(self.validator.is_valid(view))


class ProofBindingSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = _load(PROOF_BINDING_SCHEMA_PATH)
        self.validator = jsonschema.Draft202012Validator(self.schema)

    def test_schema_itself_is_structurally_valid(self) -> None:
        jsonschema.Draft202012Validator.check_schema(self.schema)

    def test_reproduction_binding_is_valid_without_preservation_boundaries(self) -> None:
        binding = {
            "schema_version": "1",
            "type": "tailtrail-proof-binding",
            "proof_binding_id": "proof-binding-repro-7",
            "requirement_uid": "req-1",
            "kind": "reproduction",
            "command": "python3 -m unittest tests.test_example -v",
            "asserted_behaviors": ["The proposed Copilot hook path can own its requirement."],
        }
        self.assertEqual(list(self.validator.iter_errors(binding)), [])

    def test_post_change_binding_requires_preservation_boundaries(self) -> None:
        binding = {
            "schema_version": "1",
            "type": "tailtrail-proof-binding",
            "proof_binding_id": "proof-binding-fix-8",
            "requirement_uid": "req-1",
            "kind": "post-change",
            "command": "python3 -m unittest tests.test_example -v",
            "asserted_behaviors": ["The corrected behavior is in place."],
        }
        self.assertFalse(self.validator.is_valid(binding))
        binding["preservation_boundaries"] = ["Existing callers remain compatible."]
        self.assertTrue(self.validator.is_valid(binding))

    def test_reproduction_binding_rejects_preservation_boundaries(self) -> None:
        binding = {
            "schema_version": "1",
            "type": "tailtrail-proof-binding",
            "proof_binding_id": "proof-binding-repro-7",
            "requirement_uid": "req-1",
            "kind": "reproduction",
            "command": "python3 -m unittest tests.test_example -v",
            "asserted_behaviors": ["x"],
            "preservation_boundaries": ["should not be here"],
        }
        self.assertFalse(self.validator.is_valid(binding))

    def test_missing_asserted_behavior_is_rejected(self) -> None:
        binding = {
            "schema_version": "1",
            "type": "tailtrail-proof-binding",
            "proof_binding_id": "proof-binding-repro-7",
            "requirement_uid": "req-1",
            "kind": "reproduction",
            "command": "python3 -m unittest tests.test_example -v",
            "asserted_behaviors": [],
        }
        self.assertFalse(self.validator.is_valid(binding))


class RedactionPolicySchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = _load(REDACTION_SCHEMA_PATH)
        self.validator = jsonschema.Draft202012Validator(self.schema)

    def _base(self) -> dict:
        return {
            "schema_version": "1",
            "type": "tailtrail-host-question-flow-redaction-policy",
            "artifact_class": "observation",
            "redaction": {
                "stage": "ingestion",
                "shape_catalog": ["AWS access key", "GitHub token"],
            },
            "retention": {
                "duration": "run-lifetime",
                "storage_boundary": ".tailtrail/runs/<run_id>",
            },
        }

    def test_schema_itself_is_structurally_valid(self) -> None:
        jsonschema.Draft202012Validator.check_schema(self.schema)

    def test_minimal_policy_is_valid(self) -> None:
        self.assertEqual(list(self.validator.iter_errors(self._base())), [])

    def test_report_rendering_stage_is_rejected(self) -> None:
        """Regression for 'Redact at ingestion, not only during report
        rendering' (design doc Implementation Risks)."""
        policy = self._base()
        policy["redaction"]["stage"] = "report-rendering"
        self.assertFalse(self.validator.is_valid(policy))

    def test_shape_catalog_enum_matches_quality_loop_secret_shapes(self) -> None:
        """Regression for Review Resolution #3: this schema's shape_name enum
        must stay in sync with the real, shipped scripts/quality-loop.py
        SECRET_SHAPES catalog rather than drifting into its own list."""
        spec = importlib.util.spec_from_file_location(
            "quality_loop_for_redaction_test", ROOT / "scripts" / "quality-loop.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        real_shape_names = {shape for shape, _pattern in module.SECRET_SHAPES}
        schema_enum = set(
            self.schema["properties"]["redaction"]["properties"]["shape_catalog"]["items"]["enum"]
        )
        self.assertEqual(real_shape_names, schema_enum)

    def test_unknown_shape_name_is_rejected(self) -> None:
        policy = self._base()
        policy["redaction"]["shape_catalog"] = ["made-up shape"]
        self.assertFalse(self.validator.is_valid(policy))


if __name__ == "__main__":
    unittest.main()
