#!/usr/bin/env python3
"""Mechanically build and self-validate a tailtrail-host-requirement-interpretation JSON.

A host otherwise hand-writes this envelope and discovers its grounding rules
only by submitting to `tailtrail start` and reading the rejection: a clause's
text must be an exact substring of the goal, an intent term must be a literal
substring of the goal (not just of its clause), and a code-identifier-looking
token named in a clause (a flag, a function name, a snake_case symbol) should
also appear in that requirement's intent_terms. This tool checks all three
locally, against a plain spec, before anything is submitted.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

NAMED_TARGET_PATTERN = re.compile(
    r"--[a-z][a-z0-9-]*"           # CLI flags
    r"|\b[A-Za-z_][A-Za-z0-9_]*\(\)"  # function()
    r"|\b[A-Za-z_][A-Za-z0-9_]*\.py\b"  # file.py
    r"|\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b"  # snake_case
)


def named_targets(text: str) -> set[str]:
    found = set()
    for match in NAMED_TARGET_PATTERN.finditer(text):
        token = match.group(0)
        found.add(token[:-2] if token.endswith("()") else token)
    return found


def validate_spec(spec: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Check grounding locally. Returns (hard_failures, warnings).

    Hard failures are grounding rules this tool can check with certainty
    (exact substring checks). Warnings flag TailTrail's named-target rule,
    which this tool approximates with a regex and cannot check with full
    certainty -- a submission may still be rejected even with zero warnings,
    or may still succeed despite one.
    """
    problems: list[str] = []
    warnings: list[str] = []
    goal = str(spec.get("goal", ""))
    if not goal.strip():
        problems.append("spec needs a non-empty `goal`")
        return problems
    clauses = spec.get("clauses", [])
    if not isinstance(clauses, list) or not clauses:
        problems.append("spec needs a non-empty `clauses` list")
    clause_ids = set()
    for index, clause in enumerate(clauses, 1):
        text = str(clause.get("text", ""))
        clause_id = str(clause.get("clause_id") or f"C{index}")
        clause_ids.add(clause_id)
        if not text.strip():
            problems.append(f"clause {clause_id}: empty text")
        elif text not in goal:
            problems.append(f"clause {clause_id}: text is not an exact substring of goal -- {text!r}")
        if clause.get("role") not in {"context", "outcome", "constraint", "evidence", "scope", "question"}:
            problems.append(f"clause {clause_id}: role must be one of context/outcome/constraint/evidence/scope/question")
    requirements = spec.get("requirements", [])
    if not isinstance(requirements, list) or not requirements:
        problems.append("spec needs a non-empty `requirements` list")
    for requirement in requirements:
        display_id = str(requirement.get("display_id", "REQ-?"))
        statement = str(requirement.get("statement", ""))
        if not statement.strip():
            problems.append(f"{display_id}: empty statement")
        source_ids = requirement.get("source_clause_ids", [])
        if not source_ids:
            problems.append(f"{display_id}: needs at least one source_clause_id")
        unknown = [cid for cid in source_ids if cid not in clause_ids]
        if unknown:
            problems.append(f"{display_id}: source_clause_ids not defined in clauses: {unknown}")
        intent_terms = [str(term) for term in requirement.get("intent_terms", [])]
        if not intent_terms:
            problems.append(f"{display_id}: needs at least one intent_term")
        for term in intent_terms:
            if term not in goal:
                problems.append(f"{display_id}: intent_term {term!r} is not a literal substring of the goal")
        source_text = " ".join(
            str(c.get("text", "")) for c in clauses if str(c.get("clause_id")) in source_ids
        )
        targets = named_targets(source_text)
        missing_in_terms = sorted(t for t in targets if t not in intent_terms)
        missing_in_statement = sorted(t for t in targets if t not in statement)
        if missing_in_terms:
            warnings.append(
                f"{display_id}: named target(s) from its clause are not in intent_terms yet: {missing_in_terms}"
            )
        if missing_in_statement:
            warnings.append(
                f"{display_id}: named target(s) from its clause are not in the statement text yet: {missing_in_statement}"
            )
    return problems, warnings


def build(spec: dict[str, Any], host: str) -> dict[str, Any]:
    clauses = [
        {
            "clause_id": str(clause.get("clause_id") or f"C{index}"),
            "role": clause["role"],
            "text": clause["text"],
        }
        for index, clause in enumerate(spec.get("clauses", []), 1)
    ]
    requirements = [
        {
            "display_id": requirement["display_id"],
            "statement": requirement["statement"],
            "kind": requirement.get("kind", "change"),
            "source_clause_ids": requirement["source_clause_ids"],
            "intent_terms": [str(term) for term in requirement.get("intent_terms", [])],
        }
        for requirement in spec.get("requirements", [])
    ]
    return {
        "schema_version": "1",
        "type": "tailtrail-host-requirement-interpretation",
        "host": host,
        "goal": spec["goal"],
        "private_reasoning_excluded": True,
        "clauses": clauses,
        "requirements": requirements,
        "material_questions": list(spec.get("material_questions", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True, help="Plain-English spec JSON: {goal, clauses: [{clause_id, role, text}], requirements: [{display_id, statement, kind, source_clause_ids, intent_terms}], material_questions}.")
    parser.add_argument("--host", choices=("codex", "claude", "copilot"), required=True)
    parser.add_argument("--out", type=Path, help="Write the built interpretation JSON here instead of stdout.")
    args = parser.parse_args()
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"host-interpretation-builder error: could not read --spec: {error}")
        return 2
    problems, warnings = validate_spec(spec)
    if problems:
        print("host-interpretation-builder found grounding problems:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    if warnings:
        print("host-interpretation-builder warnings (TailTrail's named-target rule is approximated here, not guaranteed):", file=sys.stderr)
        for warning in warnings:
            print(f"  - {warning}", file=sys.stderr)
    result = build(spec, args.host)
    text = json.dumps(result, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
