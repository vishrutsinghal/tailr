#!/usr/bin/env python3
"""Official AI-DLC Requirements-stage adapter for a verified Full-mode run.

The official pack is rule content consumed by the host agent. This adapter
materializes the required stage contract and imports only requirement IDs,
decisions, and references into TailTrail. It never falls back to the local
``aidlc-requirements.py`` implementation for Full mode.
"""
from __future__ import annotations

import json
import importlib.util
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_STAGE = "requirements"


def _stage_goal(goal: str) -> str:
    """Make the external-stage summary safe without changing the Planning Lock.

    The Planning Lock retains the original user request verbatim.  The official
    requirements artifact is a bounded, sanitizer-validated summary, so line
    breaks are collapsed rather than rejected or silently truncated.
    """
    return " ".join(str(goal).split())


def _sanitizer() -> Any:
    spec = importlib.util.spec_from_file_location("official_aidlc_requirements_sanitizer", ROOT / "scripts" / "official-aidlc-sanitize.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _pack_root(root: Path, bridge: dict[str, Any]) -> Path:
    manifest = Path(str(bridge.get("compatibility_manifest", "")))
    if not manifest or manifest.is_absolute() or ".." in manifest.parts:
        raise ValueError("official bridge has no safe compatibility manifest reference")
    path = (root / manifest).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("official compatibility manifest escapes project root") from error
    if not path.is_file():
        raise ValueError("official compatibility manifest is unavailable")
    return path.parent


def stage_contract(root: Path, bridge: dict[str, Any]) -> dict[str, str]:
    """Resolve the official requirements rules that must govern this stage."""
    pack = _pack_root(root, bridge)
    candidates = {
        "core_workflow": pack / "aws-aidlc-rules" / "core-workflow.md",
        "requirements_analysis": pack / "aws-aidlc-rule-details" / "inception" / "requirements-analysis.md",
        "question_format": pack / "aws-aidlc-rule-details" / "common" / "question-format-guide.md",
        "content_validation": pack / "aws-aidlc-rule-details" / "common" / "content-validation.md",
        "session_continuity": pack / "aws-aidlc-rule-details" / "common" / "session-continuity.md",
    }
    missing = [name for name, path in candidates.items() if not path.is_file()]
    if missing:
        raise ValueError("verified official pack is missing Full-mode requirements rules: " + ", ".join(missing))
    required_markers = {
        "core_workflow": "Requirements Analysis",
        "requirements_analysis": "Generate Clarifying Questions",
        "question_format": "Other",
        "content_validation": "Content Validation",
        "session_continuity": "Session",
    }
    for name, marker in required_markers.items():
        if marker.lower() not in candidates[name].read_text(encoding="utf-8", errors="ignore").lower():
            raise ValueError(f"official requirements rule is incomplete: {name}")
    return {name: path.relative_to(root).as_posix() for name, path in candidates.items()}


def _question(identifier: str, question: str, options: list[str], recommended: str, reasoning: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "question": question,
        "options": [{"id": chr(ord("A") + index), "text": option} for index, option in enumerate(options)] + [{"id": "Other", "text": "Other — describe the intended behavior."}],
        "recommended": recommended,
        "reasoning": reasoning,
    }


def _questions(goal: str, requirements: list[dict[str, Any]], feedback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    text = f"{goal} " + " ".join(str(row.get("statement", "")) for row in requirements)
    questions = [
        _question("OQ1", "What observable functional outcome must the delivered capability provide?", ["Only the stated outcome", "The stated outcome plus explicitly named caller/API behavior"], "The stated outcome plus explicitly named caller/API behavior when one is in scope", "Official requirements analysis requires testable functional behavior and clear system boundaries."),
        _question("OQ2", "Which non-functional constraints are mandatory for this delivery?", ["Use existing repository standards only", "Explicitly include security, reliability, performance, auditability, and accessibility where applicable"], "Explicitly include applicable quality constraints", "The official requirements stage requires non-functional requirements to be assessed rather than assumed away."),
        _question("OQ3", "Which user, API, failure, and edge scenarios must be accepted before implementation?", ["Named happy path only", "Happy path, errors, edge cases, and recovery/side-effect scenarios"], "Happy path, errors, edge cases, and recovery/side-effect scenarios", "Requirement completeness needs scenarios beyond the easiest success case."),
        _question("OQ4", "What system boundaries, integrations, and data constraints apply?", ["Change the named component only", "Trace affected callers, contracts, persistence, and external dependencies"], "Trace affected callers, contracts, persistence, and external dependencies", "The official stage requires technical context and integration boundaries before implementation planning."),
        _question("OQ5", "What evidence is required to approve this requirements stage?", ["Focused unit proof", "Requirement-linked unit, integration, contract, behavior, and release proof where applicable"], "Requirement-linked evidence at every applicable tier", "Approval must be based on the delivery risk and observable behavior, not a generic test claim."),
    ]
    if any(word in text.lower() for word in ("security", "auth", "payment", "personal", "terraform", "production", "release")):
        questions.append(_question("OQ6", "Which official extension or delivery risk must be explicitly enabled and governed?", ["Use baseline repository controls", "Enable applicable security, compliance, infrastructure, or operations requirements"], "Enable and record every applicable official extension", "Full mode must preserve the official pack's opt-in and mandatory-risk discipline."))
    comments = "; ".join(dict.fromkeys(str(item.get("comment", "")).strip() for item in feedback if str(item.get("comment", "")).strip()))
    if comments:
        questions.append(_question(f"OQ{len(questions) + 1}", f"How should official requirements address prior feedback: {comments}", ["Revise only disputed requirements and dependent evidence", "Escalate the affected boundary to official design"], "Revise only disputed requirements and dependent evidence unless an architecture decision is required", "Preserve approved evidence and route material design concerns to the official design stage."))
    return questions


def _question_markdown(goal: str, questions: list[dict[str, Any]], contract: dict[str, str]) -> str:
    lines = ["# Official AI-DLC Requirements Clarification Questions", "", "This file is governed by the verified official AI-DLC requirements and question-format rules.", "", f"## Requested outcome", "", goal, "", "## Governing rule references", ""]
    lines.extend(f"- `{path}`" for path in contract.values())
    for index, question in enumerate(questions, start=1):
        lines.extend(["", f"## Question {index} ({question['id']})", question["question"], ""])
        lines.extend(f"{option['id']}) {option['text']}" for option in question["options"])
        lines.extend(["", "[Answer]: ", ""])
    return "\n".join(lines)


def gather(root: Path, bridge: dict[str, Any], goal: str, requirements: list[dict[str, Any]], feedback: list[dict[str, Any]]) -> dict[str, Any]:
    contract = stage_contract(root, bridge)
    stage_goal = _stage_goal(goal)
    questions = _questions(stage_goal, requirements, feedback)
    payload = {
        "stage": "Official AI-DLC Requirements Analysis",
        "authority": "official-ai-dlc-pack",
        "official_stage": OFFICIAL_STAGE,
        "official_references": contract,
        "official_intent_id": bridge["official_intent_id"],
        "official_session_id": bridge["official_session_id"],
        "goal": stage_goal,
        "requirements": requirements,
        "questions": questions,
        "question_markdown": _question_markdown(stage_goal, questions, contract),
        "stage_gate": "The official Requirements Analysis questions and requirement boundary must be explicitly approved before TailTrail freezes its anchor.",
    }
    _sanitizer().validate_artifact(root.resolve(), payload, "requirements")
    return payload


def validate_answers(stage: dict[str, Any], answers: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    if not isinstance(answers, list):
        raise ValueError("official AIDLC answers must be a JSON list")
    questions = {str(row["id"]): row for row in stage.get("questions", [])}
    supplied = {str(row.get("question_id", "")): row for row in answers if isinstance(row, dict)}
    if set(supplied) != set(questions):
        raise ValueError("official AIDLC answers must include exactly one answer for every open question")
    resolved: dict[str, dict[str, str]] = {}
    for identifier, question in questions.items():
        row = supplied[identifier]
        choice = str(row.get("choice", "")).strip()
        options = {str(option["id"]): str(option["text"]) for option in question["options"]}
        if choice not in options:
            raise ValueError(f"{identifier} choice must be one of: {', '.join(sorted(options))}")
        detail = str(row.get("detail", "")).strip()
        if choice == "Other" and not detail:
            raise ValueError(f"{identifier} requires detail when choice is Other")
        resolved[identifier] = {"choice": choice, "detail": detail, "selected": options[choice]}
    return resolved


def revise(stage: dict[str, Any], answers: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = validate_answers(stage, answers)
    rows = []
    for index, requirement in enumerate(stage["requirements"], start=1):
        row = {**requirement}
        row["official_requirement_ref"] = f"{stage['official_intent_id']}:REQ-{index:02d}"
        row["official_stage"] = OFFICIAL_STAGE
        row["acceptance_criteria"] = list(row.get("acceptance_criteria", [])) + ["Official requirements decisions are reflected in this approved boundary."]
        rows.append(row)
    payload = {
        "goal": stage.get("goal", ""),
        "requirements": rows,
        "official_decisions": decisions,
        "official_stage": OFFICIAL_STAGE,
        "authority": "official-ai-dlc-pack",
        "approval_summary": "Official AI-DLC Requirements Analysis is ready for explicit stage approval. That approval freezes the TailTrail anchor for this same run.",
    }
    # Stage references were already resolved from the project root during gather;
    # revision validates the imported decision content without persisting raw answers.
    _sanitizer().validate_input(payload, "requirements-revision")
    return payload
