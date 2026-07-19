from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Claim:
    claim_id: str
    member_id: str
    amount: float
    diagnosis_code: str

