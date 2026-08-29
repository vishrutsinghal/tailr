from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


tiers = load("tailtrail_evidence_tiers_test", "scripts/evidence-tiers.py")
contract = load("tailtrail_closure_contract_tiers_test", "scripts/closure-contract.py")


class EvidenceTierContractTests(unittest.TestCase):
    def test_behaviour_is_a_canonical_recordable_tier(self) -> None:
        self.assertIn("behaviour", tiers.CANONICAL_EVIDENCE_TIERS)
        self.assertIn("behaviour", contract.TIERS)

    def test_american_behavior_alias_normalizes_to_canonical_tier(self) -> None:
        self.assertEqual("behaviour", tiers.normalize("behavior"))

    def test_requirement_compiler_rejects_unsupported_tier_before_approval(self) -> None:
        requirements = [{"display_id": "REQ-01", "validation_contract": {"tiers": ["model-opinion"]}}]
        with self.assertRaisesRegex(ValueError, "unsupported evidence tier"):
            tiers.compile_requirements(requirements)

    def test_requirement_compiler_accepts_behaviour_plan(self) -> None:
        requirements = [{"display_id": "REQ-01", "validation_contract": {"tiers": ["behavior", "integration"]}}]
        result = tiers.compile_requirements(requirements)
        self.assertEqual("compatible", result["status"])
        self.assertEqual(["behaviour", "integration"], requirements[0]["validation_contract"]["tiers"])


if __name__ == "__main__":
    unittest.main()
