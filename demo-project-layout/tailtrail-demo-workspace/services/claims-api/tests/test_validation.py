from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, (ROOT / "src" / "claims_api").as_posix())

from validation import acceptance_status, validate_claim


def valid_claim() -> dict[str, object]:
    return {
        "claim_id": "CLM-1001",
        "member_id": "MBR-2001",
        "claim_type": "medical",
        "amount": 125.5,
    }


class ClaimValidationTests(unittest.TestCase):
    def test_accepts_valid_claim(self) -> None:
        result = validate_claim(valid_claim())
        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])

    def test_rejects_missing_member_id(self) -> None:
        claim = valid_claim()
        claim["member_id"] = ""
        result = validate_claim(claim)
        self.assertFalse(result.valid)
        self.assertIn("member_id is required", result.errors)

    def test_rejects_unsupported_claim_type(self) -> None:
        claim = valid_claim()
        claim["claim_type"] = "travel"
        result = validate_claim(claim)
        self.assertFalse(result.valid)
        self.assertIn("claim_type is not supported", result.errors)

    @unittest.expectedFailure
    def test_rejects_zero_amount_demo_bug(self) -> None:
        claim = valid_claim()
        claim["amount"] = 0
        result = validate_claim(claim)
        self.assertFalse(result.valid)
        self.assertIn("amount must be greater than zero", result.errors)

    def test_acceptance_status_uses_validation_result(self) -> None:
        self.assertEqual(acceptance_status(valid_claim()), "accepted")


if __name__ == "__main__":
    unittest.main()

