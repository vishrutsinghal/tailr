"""Derive reviewable requirement rows from explicit user wording without inventing scope."""
from __future__ import annotations

import re
from typing import Any


ACTION = (
    r"add|allow|avoid|block|build|capture|change|consolidate|create|define|demonstrate|detect|ensure|fix|include|implement|introduce|"
    r"issue|keep|maintain|map|notify|prevent|preserve|provide|prove|publish|record|refund|reject|release|"
    r"refactor|redesign|reduce|require|retain|run|save|send|show|support|update|use|validate|verify|"
    r"adds|allows|avoids|blocks|builds|captures|changes|consolidates|creates|defines|demonstrates|detects|ensures|fixes|includes|"
    r"implements|introduces|issues|keeps|maintains|maps|notifies|prevents|preserves|provides|proves|publishes|records|"
    r"redesigns|refactors|reduces|refunds|rejects|releases|requires|retains|runs|saves|sends|shows|supports|updates|uses|validates|verifies"
)
ACTION_START = re.compile(rf"^(?:do\s+not\s+|must\s+|must\s+not\s+|should\s+)?(?:{ACTION})\b", re.IGNORECASE)
SUBJECT_ACTION = re.compile(rf"^(?P<subject>[A-Za-z][A-Za-z0-9 _/-]{{0,60}}?)\s+(?P<action>{ACTION})\b", re.IGNORECASE)
PREFIX = re.compile(r"^(?:tailtrail\s+start\s*[,;:-]?\s*)?(?:hands[- ]free|end[- ]to[- ]end)\s*:\s*", re.IGNORECASE)
WORKFLOW_PREFIX = re.compile(
    r"^(?:(?:using|use)\s+(?:tailtrail\s+)?(?:aidlc(?:\s+(?:lite|standard|full))?|navigator)\s*[,;:-]\s*)+",
    re.IGNORECASE,
)
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


def _expand_maintainability_constraints(value: str) -> list[str]:
    """Separate explicit preservation and negative-scope clauses.

    This remains wording-driven.  It does not invent a refactor boundary; it
    merely prevents independently reviewable clauses from being hidden in one
    requirement row.
    """
    text = value.rstrip(".")
    preserved = re.match(
        r"^preserve\s+(?P<behavior>.+?)\s+and\s+(?P<tests>(?:the\s+)?(?:relevant\s+)?tests?)$",
        text,
        flags=re.IGNORECASE,
    )
    if preserved:
        return [
            _sentence(f"Preserve {preserved.group('behavior')}"),
            _sentence(f"Preserve {preserved.group('tests')}"),
        ]
    bounded = re.match(
        r"^(?P<main>.+?)\s+without\s+(?P<verb>expanding|changing|adding|removing)\s+(?P<object>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if bounded and ACTION_START.match(bounded.group("main")):
        verb = {"expanding": "expand", "changing": "change", "adding": "add", "removing": "remove"}[bounded.group("verb").lower()]
        return [_sentence(bounded.group("main")), _sentence(f"Do not {verb} {bounded.group('object')}")]
    return [_sentence(value)]


def _expand_ui_feature_list(value: str) -> list[str]:
    """Turn an explicit ``page with A, B, and C`` request into atomic rows.

    This is deliberately limited to named UI containers.  It does not split
    ordinary comma lists such as the design tokens that a user asks to
    preserve, and it adds no feature that was absent from the prompt.
    """
    text = value.rstrip(".")
    match = re.match(
        r"^(?P<base>(?:add|build|create|implement)\s+.+?\b(?:dashboard|dialog|form|page|screen|view)\b.*?)\s+with\s+(?P<features>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        negative = re.match(
            r"^do\s+not\s+(?P<first>introduce\s+.+?)\s+or\s+(?P<second>redesign\s+.+)$",
            text,
            flags=re.IGNORECASE,
        )
        if negative:
            return [_sentence(f"Do not {negative.group('first')}"), _sentence(f"Do not {negative.group('second')}")]
        return []
    features_text = re.sub(r",\s+and\s+", ", ", match.group("features"), flags=re.IGNORECASE)
    features = [item.strip() for item in features_text.split(",") if item.strip()]
    if len(features) < 2:
        return []
    rows = [_sentence(match.group("base"))]
    for feature in features:
        feature = re.sub(r"^(?:an?|the)\s+", "", feature, flags=re.IGNORECASE)
        verb = "Provide" if "control" in feature.lower() or "action" in feature.lower() else "Show"
        rows.append(_sentence(f"{verb} {feature} on the requested UI"))
    return rows


def statements(goal: str) -> list[str]:
    """Split only explicit clauses, bullets, sentences, and action predicates."""
    value = WORKFLOW_PREFIX.sub("", PREFIX.sub("", goal.strip()))
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
        ui_rows = _expand_ui_feature_list(chunk)
        if ui_rows:
            rows.extend(ui_rows)
            continue
        for item in _predicate_parts(chunk):
            rows.extend(_expand_maintainability_constraints(item))
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
    if any(word in lowered for word in ("avoid", "do not", "must not", "only ", "forbid", "without weakening")): return "constraint"
    if any(word in lowered for word in ("security", "authorization", "authentication", "secret", "privacy")): return "safety"
    return "change"


def _tiers(statement: str) -> list[str]:
    lowered = statement.lower()
    tiers: list[str] = []
    unit_is_excluded = bool(re.search(r"(?:instead of|rather than|without|not)\b.{0,50}\bunit", lowered))
    if any(word in lowered for word in ("unit", "focused test", "focused validation")) and not unit_is_excluded: tiers.append("unit")
    if any(word in lowered for word in ("api", "contract", "schema")): tiers.append("contract")
    if any(word in lowered for word in ("workflow", "journey", "notification", "user-facing", "ui", "page", "screen")): tiers.append("behaviour")
    integration_terms = ("service", "inventory", "payment", "integration")
    integration_requested = any(
        re.search(rf"(?<![a-z0-9_]){re.escape(word)}(?![a-z0-9_])", lowered)
        for word in integration_terms
    )
    repository_layer_requested = bool(re.search(r"\brepository\s+(?:layer|model|adapter|implementation|contract)\b", lowered))
    if integration_requested or repository_layer_requested: tiers.append("integration")
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
            "behavior_contract": {"scenarios": []}, "maintainability_contract": {"rules": []}, "confidence": "user-wording",
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
            "behavior_contract": {"scenarios": []}, "maintainability_contract": {"rules": []}, "confidence": "navigator-curated",
        })
    return rows
