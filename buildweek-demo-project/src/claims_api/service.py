from __future__ import annotations

from .models import Claim
from .validation import validate_claim


def accept_claim(claim: Claim) -> dict[str, str]:
    validate_claim(claim)
    return {
        "claim_id": claim.claim_id,
        "status": "accepted",
    }

