#!/usr/bin/env python3
"""Dry-run a host requirement interpretation without creating any run.

Reads the goal, requirement artifacts, and a draft (clauses, requirements,
material questions, host), assembles the submission envelope with computed
SHA-256 artifact evidence, and runs the real TailTrail validators locally.

Success prints the base64 submission string on stdout (exit 0) for use with
`tailtrail start --requirement-interpretation-base64`. Failure prints the
named validator errors on stderr (exit 2). This command never writes state,
creates runs, or touches the network.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


# Scaffold rules mirror requirement_discovery term grounding exactly (same
# token pattern, same literal subtraction); the anchor stage additionally
# needs terms of at least three characters, so the scaffold enforces the
# strictest downstream rule up front.
INTENT_TERM_PATTERN = r"[A-Za-z][A-Za-z0-9_-]{1,63}"
MIN_SCAFFOLD_TERM_LENGTH = 3
CONSTRAINT_CUES = ("must", "only ", "never", "always", "without", "capped", "stateless", "fail closed", "required")
CONTEXT_PREFIXES = ("owners ", "note:", "note ", "context:", "for reference", "background:")
UNCERTAIN_CUES = ("maybe", "probably", "possibly", "something", "appropriate", "relevant", "etc", "as needed", "if needed", "where appropriate")
QUOTED_SPAN = re.compile(r'"([^"]{4,160})"|`([^`]{4,160})`')
STOP_WORDS = frozenset({
    "the", "and", "for", "with", "from", "that", "this", "these", "those",
    "are", "was", "were", "has", "have", "had", "will", "would", "can",
    "its", "into", "over", "under", "such", "than", "then", "them",
})


def scaffold_rules() -> list[str]:
    """Render the live scaffold rules from the enforcing constants."""
    return [
        f"term pattern: {INTENT_TERM_PATTERN} (validator tokenization, matched whole)",
        f"min term length: {MIN_SCAFFOLD_TERM_LENGTH} (anchor stage needs >=3; interpretation allows 2)",
        f"constraint cues: {', '.join(CONSTRAINT_CUES)}",
        f"context prefixes: {', '.join(CONTEXT_PREFIXES)}",
        "questions: opt-in via repeatable --question, at most three, default none",
        "uncertain segments: default to outcome; --resolve-uncertain routes hedged segments to question clauses for host resolution",
        "artifacts: clauses matching artifact text verbatim are bound with source_input_id; unbound artifacts fail loudly",
        "guarantee: scaffolded output always passes validate_draft or the command fails loudly",
    ]


def _load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _read_artifact(path: Path, index: int) -> dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, ValueError, UnicodeDecodeError) as error:
        raise ValueError(
            f"requirement artifact is missing or unreadable: {path} ({error})"
        ) from error
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return {"input_id": f"IN-{index:02d}", "sha256": digest, "content": content}


def _build_evidence(
    artifacts: list[dict[str, Any]], clauses: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    evidence = []
    for artifact in artifacts:
        input_id = str(artifact["input_id"])
        source_ids = sorted({
            str(row.get("clause_id", ""))
            for row in clauses
            if isinstance(row, dict) and str(row.get("source_input_id", "")) == input_id
        })
        if not source_ids:
            raise ValueError(
                "artifact evidence must match inspected hashes and artifact-grounded clauses"
                f" [no artifact-grounded clauses reference {input_id}]"
            )
        evidence.append({
            "input_id": input_id,
            "sha256": str(artifact["sha256"]),
            "source_clause_ids": source_ids,
        })
    return evidence


def _scaffold_quoted_literals(goal: str) -> list[str]:
    """Extract normalized quoted spans using the validator's own normalizer."""
    discovery = _load("scaffold_requirement_discovery", "requirement_discovery.py")
    literals: list[str] = []
    for double_quoted, backticked in QUOTED_SPAN.findall(goal):
        normalized = discovery.normalize_quoted_literal(double_quoted or backticked)
        if normalized and normalized not in literals:
            literals.append(normalized)
    return literals[:8]


def _scaffold_clauses(goal: str, resolve_uncertain: bool = False) -> list[dict[str, Any]]:
    """Split goal text into conservative clauses; uncertain segments stay outcomes.

    Scope paths come from discovery's own extractor. Only explicit cue
    words divert a segment to constraint/question/context, so a missed cue
    keeps the behavior as a requirement instead of silently dropping it.
    With resolve_uncertain, hedged segments become question clauses so the
    host agent resolves them through the intake conversation instead.
    """
    discovery = _load("scaffold_requirement_discovery", "requirement_discovery.py")
    without_paths, scopes = discovery._extract_scope_paths(goal)
    clauses = [dict(row) for row in scopes]
    segments = [part.strip(" .") for part in re.split(r"\s*;\s*", without_paths) if part.strip(" .")]
    for index, segment in enumerate(segments, start=1):
        lowered = segment.casefold()
        if segment.endswith("?"):
            role = "question"
        elif any(segment.lower().startswith(prefix) for prefix in CONTEXT_PREFIXES):
            role = "context"
        elif any(cue in lowered for cue in CONSTRAINT_CUES):
            role = "constraint"
        elif resolve_uncertain and any(cue in lowered for cue in UNCERTAIN_CUES):
            role = "question"
        else:
            role = "outcome"
        clauses.append({"clause_id": f"C-{index:02d}", "role": role, "text": segment})
    return clauses


def _scaffold_terms(statement: str, goal: str, quoted_literals: list[str]) -> list[str]:
    """Derive grounded intent terms with the validator's grounding semantics.

    Tokenization reuses discovery's own grounding normalizer; quoted spans
    are blanked first so literal words never leak into semantic terms.
    Stop-words and sub-three-character tokens are dropped for the anchor
    stage and downstream search; an emptied term list fails loudly in
    validation instead of emitting an ungrounded requirement.
    """
    discovery = _load("scaffold_requirement_discovery", "requirement_discovery.py")
    blanked = goal
    for literal in quoted_literals:
        blanked = re.sub(re.escape(literal), " ", blanked, flags=re.IGNORECASE)
    grounded = set(discovery._grounding_text(blanked).split(" "))
    grounded.update(re.findall(INTENT_TERM_PATTERN, blanked.casefold()))
    terms: list[str] = []
    for term in re.findall(INTENT_TERM_PATTERN, statement.casefold()):
        if term in grounded and len(term) >= MIN_SCAFFOLD_TERM_LENGTH and term not in STOP_WORDS and term not in terms:
            terms.append(term)
    return terms


def scaffold_draft(goal: str, host: str | None, questions: list[str], resolve_uncertain: bool = False, artifact_paths: list[str | Path] | None = None) -> dict[str, Any]:
    """Build a goal-derived draft; the caller must still run validate_draft.

    Statements stay verbatim to their source clause so exact named targets
    survive, and every outcome/constraint clause gets exactly one
    requirement for coverage. Clause text found verbatim in a requirement
    artifact is bound to it with source_input_id (mechanical containment
    only — never a support judgment); artifacts backing no clause fail
    loudly in validation.
    """
    if len(questions) > 3:
        raise ValueError("scaffold supports at most three material questions")
    discovery = _load("scaffold_requirement_discovery", "requirement_discovery.py")
    artifacts = [
        _read_artifact(Path(value).expanduser(), index)
        for index, value in enumerate(artifact_paths or [], start=2)
    ]
    quoted = _scaffold_quoted_literals(goal)
    clauses = _scaffold_clauses(goal, resolve_uncertain)
    for clause in clauses:
        grounded = discovery._grounding_text(str(clause.get("text", "")))
        for artifact in artifacts:
            if grounded and grounded in discovery._grounding_text(str(artifact["content"])):
                clause["source_input_id"] = str(artifact["input_id"])
                break
    requirements: list[dict[str, Any]] = []
    orphan_literals = list(quoted)
    for clause in clauses:
        if clause.get("role") not in {"outcome", "constraint"}:
            continue
        statement = str(clause.get("text", ""))
        attached = [literal for literal in quoted if literal.casefold() in statement.casefold()]
        for literal in attached:
            if literal in orphan_literals:
                orphan_literals.remove(literal)
        requirements.append({
            "display_id": f"REQ-{len(requirements) + 1:02d}",
            "statement": statement,
            "kind": "constraint" if clause.get("role") == "constraint" else "change",
            "source_clause_ids": [str(clause.get("clause_id", ""))],
            "intent_terms": _scaffold_terms(statement, goal, quoted),
            "quoted_literals": attached,
            "intent_class": "general",
            "confidence": "medium",
        })
    if not requirements:
        raise ValueError("scaffold found no outcome or constraint clause in the goal")
    if orphan_literals and requirements:
        requirements[0]["quoted_literals"] = sorted(dict.fromkeys([*requirements[0]["quoted_literals"], *orphan_literals]))
    return {
        "host": host,
        "clauses": clauses,
        "requirements": requirements,
        "material_questions": [str(value) for value in questions],
    }


def validate_draft(
    goal: str,
    artifact_paths: list[str | Path],
    draft: dict[str, Any],
    host: str | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Validate one draft with the real validators; pure function, no I/O.

    Returns (envelope, []) on success or (None, [error messages]) on
    failure. Reading artifact files may raise ValueError.
    """
    if not isinstance(draft, dict):
        return None, ["draft must be a JSON object"]
    artifacts = [
        _read_artifact(Path(value).expanduser(), index)
        for index, value in enumerate(artifact_paths, start=2)
    ]
    proposal = {
        "schema_version": "1",
        "type": "tailtrail-host-requirement-interpretation",
        "host": host or draft.get("host"),
        "goal": goal,
        "private_reasoning_excluded": True,
        "clauses": draft.get("clauses", []),
        "artifact_evidence": _build_evidence(artifacts, draft.get("clauses", [])),
        "requirements": draft.get("requirements", []),
        "material_questions": draft.get("material_questions", []),
    }
    discovery = _load("draft_requirement_discovery", "requirement_discovery.py")
    try:
        discovery.interpretation(
            goal,
            proposal,
            host or proposal.get("host"),
            [{"input_id": item["input_id"], "sha256": item["sha256"], "content": item["content"]}
             for item in artifacts],
        )
    except ValueError as error:
        return None, [str(error)]
    return proposal, []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dry-run or scaffold a requirement interpretation (no side effects).")
    parser.add_argument("--goal", default=None, help="Exact goal string the draft is bound to.")
    parser.add_argument("--requirement-artifact", action="append", default=[],
                        help="Requirement artifact file. Repeatable; bound as IN-02, IN-03, .... With --scaffold, clauses matching artifact text verbatim are bound automatically.")
    parser.add_argument("--draft", type=Path, default=None,
                        help="Draft JSON with host, clauses, requirements, and material_questions.")
    parser.add_argument("--scaffold", action="store_true",
                        help="Build the draft from the goal string with the validator's own rules, then validate it. Fails loudly on any gap.")
    parser.add_argument("--question", action="append", default=[],
                        help="Material question for a scaffolded draft (opt-in; at most three). Repeat for each question.")
    parser.add_argument("--resolve-uncertain", action="store_true",
                        help="Route hedged segments to question clauses for host resolution through intake instead of defaulting them to outcomes.")
    parser.add_argument("--show-rules", action="store_true",
                        help="Print the live scaffold rules and exit without building anything.")
    parser.add_argument("--host", default=None, choices=("codex", "copilot", "claude"),
                        help="Active host; defaults to the draft host field.")
    args = parser.parse_args(argv)

    if args.show_rules:
        print("\n".join(scaffold_rules()))
        return 0
    if not args.goal:
        parser.error("the following arguments are required: --goal")
    if args.scaffold == bool(args.draft):
        print("dry-run error: provide exactly one of --draft or --scaffold", file=sys.stderr)
        return 2
    if args.scaffold:
        try:
            draft = scaffold_draft(args.goal, args.host, list(args.question), args.resolve_uncertain, list(args.requirement_artifact))
        except ValueError as error:
            print(f"dry-run error: {error}", file=sys.stderr)
            return 2
    else:
        assert args.draft is not None
        try:
            draft = json.loads(args.draft.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            print(f"dry-run error: cannot read draft {args.draft} ({error})", file=sys.stderr)
            return 2
    try:
        proposal, errors = validate_draft(args.goal, args.requirement_artifact, draft, args.host)
    except ValueError as error:
        print(f"dry-run error: {error}", file=sys.stderr)
        return 2
    if proposal is None:
        for message in errors:
            print(f"dry-run error: {message}", file=sys.stderr)
        return 2
    if args.scaffold:
        print(json.dumps(draft, indent=2, sort_keys=True))
    else:
        print(base64.b64encode(json.dumps(proposal, separators=(",", ":")).encode("utf-8")).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
