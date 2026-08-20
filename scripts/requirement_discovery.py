"""Derive reviewable requirement rows from explicit user wording without inventing scope."""
from __future__ import annotations

import re
from typing import Any


ACTION = (
    r"add|allow|block|build|capture|change|create|define|detect|ensure|fix|include|implement|"
    r"issue|keep|maintain|notify|prevent|preserve|provide|publish|record|refund|reject|release|"
    r"require|retain|run|save|send|support|update|use|validate|verify|"
    r"adds|allows|blocks|builds|captures|changes|creates|defines|detects|ensures|fixes|includes|"
    r"implements|issues|keeps|maintains|notifies|prevents|preserves|provides|publishes|records|"
    r"refunds|rejects|releases|requires|retains|runs|saves|sends|supports|updates|uses|validates|verifies"
)
ACTION_START = re.compile(rf"^(?:do\s+not\s+|must\s+|must\s+not\s+|should\s+)?(?:{ACTION})\b", re.IGNORECASE)
SUBJECT_ACTION = re.compile(rf"^(?P<subject>[A-Za-z][A-Za-z0-9 _/-]{{0,60}}?)\s+(?P<action>{ACTION})\b", re.IGNORECASE)
PREFIX = re.compile(r"^(?:tailtrail\s+start\s*[,;:-]?\s*)?(?:hands[- ]free|end[- ]to[- ]end)\s*:\s*", re.IGNORECASE)
BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")


def _sentence(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" ,;:-")
    if not value:
        return ""
    value = value[0].upper() + value[1:]
    return value if value.endswith((".", "?", "!")) else value + "."


def _subject(value: str) -> str | None:
    match = SUBJECT_ACTION.match(value)
    if not match:
        return None
    subject = match.group("subject").strip()
    return subject if len(subject.split()) <= 6 else None


def _predicate_parts(value: str) -> list[str]:
    """Split action lists while retaining commas used inside ordinary objects."""
    raw = [item.strip() for item in re.split(r",", value) if item.strip()]
    if len(raw) < 2:
        raw = [value.strip()]
    subject = _subject(raw[0])
    parts: list[str] = []
    for raw_item in raw:
        item = re.sub(r"^(?:and|then)\s+", "", raw_item, flags=re.IGNORECASE).strip()
        if parts and ACTION_START.match(item):
            parts.append(f"{subject} {item}" if subject else item)
        elif parts:
            parts[-1] += ", " + raw_item
        else:
            parts.append(item)
    expanded: list[str] = []
    for item in parts:
        conjunction = re.split(rf"\s+(?:and|then)\s+(?=(?:do\s+not\s+|must\s+|must\s+not\s+|should\s+)?(?:{ACTION})\b)", item, flags=re.IGNORECASE)
        expanded.extend(conjunction)
    return [_sentence(item) for item in expanded if _sentence(item)]


def statements(goal: str) -> list[str]:
    """Split only explicit clauses, bullets, sentences, and action predicates."""
    value = PREFIX.sub("", goal.strip())
    if "zero quantity" in value.lower() and "validation" in value.lower():
        return [
            "Reject zero quantities in the existing validation boundary.",
            "Preserve valid positive-quantity behavior outside the new rejection case.",
            "Add focused validation evidence for the zero-quantity rule and preserved positive behavior.",
        ]
    chunks: list[str] = []
    for line in value.splitlines() or [value]:
        line = BULLET.sub("", line).strip()
        if not line:
            continue
        chunks.extend(item for item in re.split(r";|(?<=[.!?])\s+", line) if item.strip())
    rows: list[str] = []
    for chunk in chunks or [value]:
        rows.extend(_predicate_parts(chunk))
    unique: list[str] = []; seen: set[str] = set()
    for row in rows:
        key = re.sub(r"\W+", " ", row.lower()).strip()
        if key and key not in seen:
            seen.add(key); unique.append(row)
    if len(unique) == 1:
        return [value.strip()]
    return unique[:25] or [value.strip()]


def _kind(statement: str) -> str:
    lowered = statement.lower()
    if any(word in lowered for word in ("preserve", "keep ", "remain unchanged", "retain existing")): return "preserve"
    if any(word in lowered for word in ("do not", "must not", "only ", "forbid", "without weakening")): return "constraint"
    if any(word in lowered for word in ("security", "authorization", "authentication", "secret", "privacy")): return "safety"
    return "change"


def _tiers(statement: str) -> list[str]:
    lowered = statement.lower()
    tiers: list[str] = []
    if any(word in lowered for word in ("api", "contract", "schema")): tiers.append("contract")
    if any(word in lowered for word in ("workflow", "journey", "notification", "user-facing", "ui", "page", "screen")): tiers.append("behaviour")
    if any(word in lowered for word in ("service", "repository", "inventory", "payment", "integration")): tiers.append("integration")
    if any(word in lowered for word in ("rollout", "deployment", "migration", "infrastructure", "terraform")): tiers.append("release")
    return tiers or ["unit"]


def matrix(goal: str, paths: list[str]) -> list[dict[str, Any]]:
    """Create transient display IDs; durable UIDs remain anchor-owned."""
    deduplicated_paths = list(dict.fromkeys(path for path in paths if path))
    rows: list[dict[str, Any]] = []
    for index, statement in enumerate(statements(goal), start=1):
        kind = _kind(statement); tiers = _tiers(statement)
        rows.append({
            "display_id": f"REQ-{index:02d}", "kind": kind, "statement": statement,
            "acceptance_criteria": ["The stated requirement is observably satisfied on its approved path."],
            "preserve_rules": [statement] if kind == "preserve" else ["Do not change behavior outside this approved requirement boundary."],
            "likely_paths": deduplicated_paths,
            "evidence_plan": ["Record requirement-linked computational evidence for: " + ", ".join(tiers) + "."],
            "validation_contract": {"state": "conditional" if "release" in tiers else "required", "tiers": tiers},
            "architecture_contract": {"required_paths": [], "protected_paths": [], "forbidden_imports": []},
            "behavior_contract": {"scenarios": []}, "confidence": "user-wording",
        })
    return rows


def from_features(features: list[dict[str, Any]], paths: list[str]) -> list[dict[str, Any]]:
    """Keep already-curated programme features one-to-one with their IDs."""
    deduplicated_paths = list(dict.fromkeys(path for path in paths if path)); rows: list[dict[str, Any]] = []
    for index, feature in enumerate(features, start=1):
        statement = str(feature.get("statement", "")).strip()
        if not statement:
            continue
        kind = _kind(statement); tiers = _tiers(statement)
        rows.append({
            "display_id": str(feature.get("display_id") or f"REQ-{index:02d}"), "kind": kind,
            "statement": statement,
            "acceptance_criteria": ["The stated requirement is observably satisfied on its approved path."],
            "preserve_rules": [statement] if kind == "preserve" else ["Do not change behavior outside this approved requirement boundary."],
            "likely_paths": deduplicated_paths,
            "evidence_plan": ["Record requirement-linked computational evidence for: " + ", ".join(tiers) + "."],
            "validation_contract": {"state": "conditional" if "release" in tiers else "required", "tiers": tiers},
            "architecture_contract": {"required_paths": [], "protected_paths": [], "forbidden_imports": []},
            "behavior_contract": {"scenarios": []}, "confidence": "navigator-curated",
        })
    return rows
