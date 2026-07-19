from __future__ import annotations

from .models import Claim


class ClaimValidationError(ValueError):
    pass


def validate_claim_amount(amount: float) -> None:
    if amount < 0:
        raise ClaimValidationError("claim amount must be positive")


def validate_claim(claim: Claim) -> None:
    if not claim.claim_id.strip():
        raise ClaimValidationError("claim id is required")
    if not claim.member_id.strip():
        raise ClaimValidationError("member id is required")
    if not claim.diagnosis_code.strip():
        raise ClaimValidationError("diagnosis code is required")
    validate_claim_amount(claim.amount)

