from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_ALLOWED_TYPES = {"medical", "dental", "vision"}
DEFAULT_MAX_AMOUNT = 50000


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[str]


def validate_claim(payload: dict[str, Any], allowed_types: set[str] | None = None, max_amount: float = DEFAULT_MAX_AMOUNT) -> ValidationResult:
    errors: list[str] = []
    claim_types = allowed_types or DEFAULT_ALLOWED_TYPES

    if not payload.get("claim_id"):
        errors.append("claim_id is required")
    if not payload.get("member_id"):
        errors.append("member_id is required")

    claim_type = payload.get("claim_type")
    if claim_type not in claim_types:
        errors.append("claim_type is not supported")

    amount = payload.get("amount")
    if not isinstance(amount, (int, float)):
        errors.append("amount must be numeric")
    elif amount < 0:
        # Intentional demo bug: zero should also be rejected.
        errors.append("amount must be greater than zero")
    elif amount > max_amount:
        errors.append("amount exceeds maximum allowed amount")

    return ValidationResult(valid=not errors, errors=errors)


def acceptance_status(payload: dict[str, Any]) -> str:
    result = validate_claim(payload)
    return "accepted" if result.valid else "rejected"

