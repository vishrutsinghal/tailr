#!/usr/bin/env python3
"""Ground and validate AIDLC questions without becoming a question authority.

Navigator supplies the proposed requirement boundary and repository-inventory
evidence.  Lite AIDLC may generate local questions; Standard and Full AIDLC
remain owned by the verified official pack and the configured host.  This
module provides the shared context, quality, and traceability contract around
both paths.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DECISION_CLASSES = {
    "user-decision",
    "policy-decision",
    "architecture-decision",
    "evidence-decision",
    "extension-opt-in",
}
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "before", "by", "for",
    "from", "how", "in", "is", "it", "must", "of", "on", "or", "the",
    "this", "to", "what", "when", "which", "with",
}
ASSERTED_REPOSITORY_FACT = re.compile(
    r"\b(?:repository|current|existing|already)\b.{0,48}"
    r"\b(?:contains|defines|fields?|installed|limits?|status|structured|uses?)\b",
    re.IGNORECASE,
)


def _has_ungrounded_repository_assertion(value: str) -> bool:
    """Distinguish claimed repository facts from explicitly conditional advice."""
    for sentence in re.split(r"(?<=[.!?])\s+", value):
        lowered = sentence.lower()
        if not ASSERTED_REPOSITORY_FACT.search(sentence):
            continue
        if any(marker in lowered for marker in (" if ", " when ", " unless ", " where available", " where possible")):
            continue
        return True
    return False


def _requirement_id(row: dict[str, Any], index: int) -> str:
    return str(row.get("display_id") or row.get("id") or f"REQ-{index:02d}").strip()


def _tokens(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9][a-z0-9_-]+", value.lower())
        if token not in STOP_WORDS and len(token) > 2
    }


def _unknowns(goal: str, requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    text = " ".join([goal, *(str(row.get("statement", "")) for row in requirements)]).lower()
    candidates = (
        ("normalization", ("normaliz", "canonical"), ["public-behavior", "data-contract"]),
        ("rejection-contract", ("reject", "invalid", "error"), ["public-behavior", "compatibility"]),
        ("backward-compatibility", ("backward", "compatib", "preserve"), ["compatibility", "migration"]),
        ("architecture-ownership", ("api", "service", "caller", "boundary"), ["architecture", "scope"]),
        ("evidence", ("evidence", "test", "proof", "validation"), ["completion", "testing"]),
        ("privacy", ("personal", "address", "pii", "privacy"), ["privacy", "error-contract"]),
        ("release", ("rollout", "rollback", "production", "release"), ["release", "recovery"]),
    )
    return [
        {"topic": topic, "classification": "user-decision", "decision_impact": impact}
        for topic, markers, impact in candidates if any(marker in text for marker in markers)
    ]


def prepare_context(
    run_id: str,
    mode: str,
    goal: str,
    requirements: list[dict[str, Any]],
    start_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact question input contract from saved planning evidence.

    This function does not read source bodies.  Paths and roles are hypotheses
    from Navigator's saved inventory until a separately approved investigation
    or implementation-stage inspection confirms them.
    """
    report = start_report or {}
    navigator = report.get("navigator", {}) if isinstance(report, dict) else {}
    architecture = report.get("architecture_plan", {}) if isinstance(report, dict) else {}
    validation = report.get("focused_validation_plan", {}) if isinstance(report, dict) else {}
    requirement_rows = [
        {
            "requirement_id": _requirement_id(row, index),
            "statement": str(row.get("statement", "")).strip(),
            "kind": str(row.get("kind", "change")).strip() or "change",
        }
        for index, row in enumerate(requirements, start=1)
    ]
    known_facts: list[dict[str, Any]] = []
    for row in requirement_rows:
        known_facts.append({
            "fact_id": f"USER-{row['requirement_id']}",
            "fact": row["statement"],
            "evidence": f"user-requirement:{row['requirement_id']}",
            "confidence": "user-stated",
        })
    scope_rows = architecture.get("scope_roles", []) if isinstance(architecture, dict) else []
    if not scope_rows and isinstance(navigator, dict):
        scope_rows = navigator.get("likely_impacted_files", [])
    for index, item in enumerate(scope_rows or [], start=1):
        if not isinstance(item, dict) or not str(item.get("path", "")).strip():
            continue
        path = str(item["path"]).strip()
        role = str(item.get("role") or item.get("reason") or "planning candidate").strip()
        known_facts.append({
            "fact_id": f"INV-{index:02d}",
            "fact": f"Repository inventory identified `{path}` as {role}.",
            "evidence": path,
            "confidence": "repository-inventory-hypothesis",
        })
    tiers = validation.get("tiers", []) if isinstance(validation, dict) else []
    if isinstance(tiers, list) and tiers:
        known_facts.append({
            "fact_id": "PLAN-EVIDENCE-01",
            "fact": "Navigator selected candidate validation tiers: " + ", ".join(str(tier) for tier in tiers) + ".",
            "evidence": "saved-start-report:focused_validation_plan",
            "confidence": "planning-hypothesis",
        })
    return {
        "schema_version": "1",
        "type": "tailtrail-question-context",
        "run_id": run_id,
        "aidlc_mode": mode,
        "question_authority": "local-lite" if mode == "lite" else "official-ai-dlc-pack",
        "goal": goal,
        "requirements": requirement_rows,
        "known_facts": known_facts,
        "unknowns": _unknowns(goal, requirements),
        "question_policy": {
            "ask_only_material_decisions": True,
            "repository_answerable_items_require_discovery": True,
            "official_authority_preserved": mode in {"standard", "full"},
            "source_bodies_read": False,
            "boundary": "Use saved user wording and repository inventory only. Do not present an inventory hypothesis as confirmed source behavior.",
        },
    }


def _decision_class(question: str) -> str:
    lowered = question.lower()
    if "extension" in lowered or "baseline" in lowered:
        return "extension-opt-in"
    if any(word in lowered for word in ("proof", "evidence", "test")):
        return "evidence-decision"
    if any(word in lowered for word in ("component", "boundary", "own", "api", "service")):
        return "architecture-decision"
    if any(word in lowered for word in ("policy", "privacy", "security", "retain", "log")):
        return "policy-decision"
    return "user-decision"


def _decision_impact(decision_class: str) -> list[str]:
    return {
        "extension-opt-in": ["lifecycle-rules", "validation"],
        "evidence-decision": ["completion", "testing"],
        "architecture-decision": ["architecture", "scope"],
        "policy-decision": ["policy", "safeguards"],
        "user-decision": ["acceptance-criteria", "public-behavior"],
    }[decision_class]


def _mapped_requirements(question: dict[str, Any], context: dict[str, Any]) -> tuple[list[str], bool]:
    valid = {str(row["requirement_id"]) for row in context.get("requirements", [])}
    supplied = [str(value) for value in question.get("requirement_ids", []) if str(value).strip()]
    if supplied:
        unknown = sorted(set(supplied) - valid)
        if unknown:
            raise ValueError(f"{question.get('id', '<question>')} references unknown requirements: {', '.join(unknown)}")
        return list(dict.fromkeys(supplied)), False
    question_tokens = _tokens(" ".join((str(question.get("question", "")), str(question.get("reasoning", "")))))
    scored = []
    for row in context.get("requirements", []):
        score = len(question_tokens & _tokens(str(row.get("statement", ""))))
        if score:
            scored.append((score, str(row["requirement_id"])))
    if scored:
        best = max(score for score, _ in scored)
        return [identifier for score, identifier in scored if score == best], True
    return sorted(valid), True


def _relevant_facts(question: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    question_tokens = _tokens(" ".join((
        str(question.get("question", "")),
        str(question.get("recommended", "")),
        str(question.get("reasoning", "")),
    )))
    ranked = []
    for fact in context.get("known_facts", []):
        score = len(question_tokens & _tokens(str(fact.get("fact", ""))))
        if score:
            ranked.append((score, fact))
    return [fact for _, fact in sorted(ranked, key=lambda item: (-item[0], str(item[1].get("fact_id", ""))))[:3]]


def evaluate_questions(
    questions: list[dict[str, Any]],
    context: dict[str, Any],
    authority: str,
) -> dict[str, Any]:
    """Enrich questions with traceability and enforce deterministic quality rules."""
    if not isinstance(questions, list) or not questions:
        raise ValueError("question orchestrator requires a non-empty question list")
    errors: list[str] = []
    warnings: list[str] = []
    seen_questions: set[str] = set()
    enriched: list[dict[str, Any]] = []
    traceability: list[dict[str, Any]] = []
    for item in questions:
        identifier = str(item.get("id", "")).strip()
        text = str(item.get("question", "")).strip()
        normalized_text = " ".join(re.findall(r"[a-z0-9]+", text.lower()))
        if normalized_text in seen_questions:
            errors.append(f"{identifier}: duplicates another question")
        seen_questions.add(normalized_text)
        options = item.get("options", [])
        option_text = [" ".join(str(option.get("text", "")).lower().split()) for option in options if isinstance(option, dict)]
        if len(option_text) != len(set(option_text)):
            errors.append(f"{identifier}: contains duplicate options")
        requirement_ids, inferred = _mapped_requirements(item, context)
        if inferred:
            warnings.append(f"{identifier}: requirement mapping was inferred; the active authority should provide it explicitly")
        decision_class = str(item.get("decision_class", "")).strip() or _decision_class(text)
        if decision_class not in DECISION_CLASSES:
            errors.append(f"{identifier}: unsupported decision_class `{decision_class}`")
        impacts = [str(value) for value in item.get("decision_impact", []) if str(value).strip()] or _decision_impact(decision_class)
        facts = _relevant_facts(item, context)
        known_context = [str(value) for value in item.get("known_context", []) if str(value).strip()] or [str(fact["fact"]) for fact in facts]
        evidence_refs = [str(value) for value in item.get("evidence_refs", []) if str(value).strip()] or [str(fact["evidence"]) for fact in facts]
        recommendation_claim = " ".join((
            str(item.get("recommended", "")),
            str(item.get("reasoning", "")),
        ))
        if _has_ungrounded_repository_assertion(recommendation_claim) and not item.get("evidence_refs"):
            errors.append(f"{identifier}: repository-specific recommendation needs explicit evidence_refs")
        enriched_item = {
            **item,
            "authority": authority,
            "requirement_ids": requirement_ids,
            "decision_class": decision_class,
            "decision_impact": impacts,
            "known_context": known_context,
            "evidence_refs": evidence_refs,
        }
        enriched.append(enriched_item)
        traceability.append({
            "question_id": identifier,
            "requirement_ids": requirement_ids,
            "decision_class": decision_class,
            "decision_impact": impacts,
            "evidence_refs": evidence_refs,
        })
    if errors:
        raise ValueError("question quality gate failed: " + "; ".join(errors))
    return {
        "questions": enriched,
        "quality": {
            "status": "passed",
            "authority": authority,
            "question_count": len(enriched),
            "warnings": warnings,
            "checks": [
                "unique questions and options",
                "valid requirement mapping",
                "material decision classification",
                "decision-impact traceability",
                "repository-claim grounding",
            ],
        },
        "traceability": traceability,
    }


def show(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    planning = root / ".tailtrail" / "runs" / run_id / "planning"
    candidates = sorted(
        planning.glob("question-context-v*.json"),
        key=lambda item: int(item.stem.rsplit("v", 1)[-1]),
    )
    if not candidates:
        raise ValueError(f"question context for run `{run_id}` does not exist")
    path = candidates[-1]
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "tailtrail-question-context" or payload.get("run_id") != run_id:
        raise ValueError(f"question context for run `{run_id}` is invalid")
    return {**payload, "artifact": path.relative_to(root).as_posix()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect TailTrail's saved AIDLC Question Orchestrator context.")
    sub = parser.add_subparsers(dest="command", required=True)
    show_parser = sub.add_parser("show")
    show_parser.add_argument("--root", type=Path, default=Path.cwd())
    show_parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        payload = show(args.root, args.run_id)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
