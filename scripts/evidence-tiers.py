#!/usr/bin/env python3
"""Canonical TailTrail evidence-tier vocabulary and compatibility checks."""
from __future__ import annotations

from typing import Any


CANONICAL_EVIDENCE_TIERS = (
    "unit", "component", "integration", "contract", "behaviour",
    "e2e", "infrastructure", "release-smoke",
)
EVIDENCE_TIER_ALIASES = {"behavior": "behaviour"}


def normalize(value: Any) -> str:
    tier = str(value or "").strip().lower()
    return EVIDENCE_TIER_ALIASES.get(tier, tier)


def normalize_many(values: Any) -> list[str]:
    if not isinstance(values, list):
        raise ValueError("evidence tiers must be a list")
    result: list[str] = []
    for value in values:
        tier = normalize(value)
        if tier not in CANONICAL_EVIDENCE_TIERS:
            raise ValueError(f"unsupported evidence tier: {value}")
        if tier not in result:
            result.append(tier)
    return result


def compile_requirements(requirements: Any) -> dict[str, Any]:
    if not isinstance(requirements, list):
        raise ValueError("resolved requirements must be a list")
    rows: list[dict[str, Any]] = []
    for index, requirement in enumerate(requirements, start=1):
        if not isinstance(requirement, dict):
            raise ValueError("resolved requirements must contain objects")
        contract = dict(requirement.get("validation_contract", {}) or {})
        tiers = normalize_many(contract.get("tiers", ["unit"]))
        contract["tiers"] = tiers
        requirement["validation_contract"] = contract
        rows.append({
            "requirement_id": str(requirement.get("display_id") or f"REQ-{index:02d}"),
            "tiers": tiers,
            "status": "supported",
        })
    return {
        "schema_version": "1",
        "type": "tailtrail-evidence-capability-check",
        "status": "compatible",
        "requirements": rows,
        "canonical_tiers": list(CANONICAL_EVIDENCE_TIERS),
        "aliases": dict(EVIDENCE_TIER_ALIASES),
        "boundary": "Every approved evidence tier is accepted by the recorder and completion controls.",
    }
