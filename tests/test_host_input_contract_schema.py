import copy
import json
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "host-input-contract.schema.json"


def _base_contract() -> dict:
    return {
        "schema_version": "1",
        "type": "tailtrail-host-input-contract",
        "run_id": "run-0000000000000001",
        "contract_id": "contract-0000000000000001",
        "private_reasoning_excluded": True,
        "profile": "new feature",
        "change_intent": "new-capability",
        "request_mode": "implementation",
        "behavior_surface": "cli-contract",
        "paths": [
            {"path": "scripts/example.py", "role": "proposed-implementation-owner"},
            {"path": "tests/test_example.py", "role": "proposed-proof-path"},
        ],
        "criteria": {
            "positive": ["The feature emits machine-readable findings."],
            "negative": ["The feature does not modify repository files."],
        },
        "proof": {
            "command": "python3 -m unittest tests.test_example -v",
            "tiers": ["unit"],
        },
    }


def _correction_contract(state: str) -> dict:
    contract = _base_contract()
    contract["change_intent"] = "correction"
    contract["profile"] = "existing-code change"
    contract["proof"] = {
        "reproduction_binding": "proof-binding-repro-1",
        "post_change_binding": "proof-binding-fix-1",
    }
    contract["correction_premise"] = {
        "state": state,
        "public_route": "CLI Start command",
        "expected_behavior": "A valid contract is accepted.",
        "actual_behavior": "An invalid contract is rejected.",
        "observation_source": "host-inspection",
    }
    if state != "not-applicable":
        contract["owner_hypothesis"] = {"path": "scripts/navigator_scope.py", "status": "proposed"}
    return contract


class HostInputContractSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.validator = jsonschema.Draft202012Validator(self.schema)

    def test_schema_itself_is_structurally_valid(self) -> None:
        jsonschema.Draft202012Validator.check_schema(self.schema)

    def test_minimal_new_feature_contract_is_valid(self) -> None:
        errors = list(self.validator.iter_errors(_base_contract()))
        self.assertEqual(errors, [])

    def test_unknown_profile_is_rejected(self) -> None:
        contract = _base_contract()
        contract["profile"] = "not-a-real-profile"
        self.assertTrue(self.validator.is_valid(contract) is False)

    def test_unknown_path_role_is_rejected(self) -> None:
        contract = _base_contract()
        contract["paths"][0]["role"] = "implementation-owned"  # not a contract role (no existing-/proposed- prefix)
        self.assertFalse(self.validator.is_valid(contract))

    def test_non_correction_intent_rejects_correction_premise(self) -> None:
        contract = _base_contract()
        contract["correction_premise"] = {
            "state": "observed-failing",
            "public_route": "x",
            "expected_behavior": "x",
            "actual_behavior": "x",
            "observation_source": "host-inspection",
        }
        self.assertFalse(self.validator.is_valid(contract))

    def test_correction_intent_requires_correction_premise(self) -> None:
        contract = _base_contract()
        contract["change_intent"] = "correction"
        contract["proof"] = {
            "reproduction_binding": "proof-binding-repro-1",
            "post_change_binding": "proof-binding-fix-1",
        }
        self.assertFalse(self.validator.is_valid(contract))

    def test_correction_premise_requires_owner_hypothesis_unless_not_applicable(self) -> None:
        contract = _correction_contract("observed-failing")
        del contract["owner_hypothesis"]
        self.assertFalse(self.validator.is_valid(contract))

        not_applicable = _correction_contract("not-applicable")
        errors = list(self.validator.iter_errors(not_applicable))
        self.assertEqual(errors, [])

    def test_all_five_premise_states_validate_with_owner_hypothesis(self) -> None:
        for state in ("observed-failing", "unverified", "contradicted", "already-satisfied"):
            with self.subTest(state=state):
                errors = list(self.validator.iter_errors(_correction_contract(state)))
                self.assertEqual(errors, [])

    def test_issue_21_already_satisfied_premise_is_schema_representable(self) -> None:
        """Regression for Issues Log 21: TailTrail must be able to *record* an
        already-satisfied premise (so Navigator can route to re-diagnosis)
        without that premise being treated as a defect by the schema itself."""
        contract = _correction_contract("already-satisfied")
        self.assertTrue(self.validator.is_valid(contract))

    def test_proof_binding_requires_either_command_or_both_correction_bindings(self) -> None:
        contract = _base_contract()
        contract["proof"] = {"command": "python3 -m unittest tests.test_example -v"}
        self.assertFalse(self.validator.is_valid(contract))

    def test_proof_binding_rejects_mixing_both_shapes(self) -> None:
        contract = _base_contract()
        contract["proof"] = {
            "command": "python3 -m unittest tests.test_example -v",
            "tiers": ["unit"],
            "reproduction_binding": "proof-binding-repro-1",
            "post_change_binding": "proof-binding-fix-1",
        }
        self.assertFalse(self.validator.is_valid(contract))

    def test_missing_required_top_level_field_is_rejected(self) -> None:
        contract = _base_contract()
        del contract["criteria"]
        self.assertFalse(self.validator.is_valid(contract))

    def test_additional_properties_are_rejected(self) -> None:
        contract = _base_contract()
        contract["unexpected_field"] = "nope"
        self.assertFalse(self.validator.is_valid(contract))

    def test_deep_copy_round_trip_stays_valid(self) -> None:
        contract = copy.deepcopy(_base_contract())
        self.assertTrue(self.validator.is_valid(contract))

    def test_new_file_evidence_with_all_three_claims_is_valid(self) -> None:
        contract = _base_contract()
        contract["paths"][0]["new_file_evidence"] = {
            "collision_claim": "no existing file or symbol named this",
            "convention_cited": "schemas/ already holds one-schema-per-topic files",
            "no_owner_claim": "no existing file owns this responsibility",
        }
        self.assertEqual(list(self.validator.iter_errors(contract)), [])

    def test_new_file_evidence_with_one_claim_is_valid(self) -> None:
        contract = _base_contract()
        contract["paths"][0]["new_file_evidence"] = {"no_owner_claim": "no existing file owns this responsibility"}
        self.assertEqual(list(self.validator.iter_errors(contract)), [])

    def test_new_file_evidence_empty_object_is_rejected(self) -> None:
        contract = _base_contract()
        contract["paths"][0]["new_file_evidence"] = {}
        self.assertFalse(self.validator.is_valid(contract))

    def test_new_file_evidence_unknown_key_is_rejected(self) -> None:
        contract = _base_contract()
        contract["paths"][0]["new_file_evidence"] = {"not_a_real_claim": "nope"}
        self.assertFalse(self.validator.is_valid(contract))

    def test_new_file_evidence_non_string_claim_is_rejected(self) -> None:
        contract = _base_contract()
        contract["paths"][0]["new_file_evidence"] = {"collision_claim": 123}
        self.assertFalse(self.validator.is_valid(contract))


if __name__ == "__main__":
    unittest.main()
