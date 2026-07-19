from __future__ import annotations

import unittest
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if ROOT.as_posix() not in sys.path:
    sys.path.insert(0, ROOT.as_posix())

from src.claims_api.models import Claim
from src.claims_api.service import accept_claim
from src.claims_api.validation import ClaimValidationError, validate_claim_amount


class ClaimValidationTests(unittest.TestCase):
    def test_accepts_valid_claim(self) -> None:
        claim = Claim(
            claim_id="CLM-100",
            member_id="MBR-42",
            amount=125.50,
            diagnosis_code="J10",
        )

        self.assertEqual(accept_claim(claim)["status"], "accepted")

    def test_rejects_negative_amount(self) -> None:
        with self.assertRaises(ClaimValidationError):
            validate_claim_amount(-1)

    def test_rejects_zero_amount(self) -> None:
        with self.assertRaises(ClaimValidationError):
            validate_claim_amount(0)


if __name__ == "__main__":
    unittest.main()
