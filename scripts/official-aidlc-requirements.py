#!/usr/bin/env python3
"""Official AI-DLC Requirements-stage adapter for a verified Standard or Full run.

The official pack is rule content consumed by the host agent. This adapter
materializes the required stage contract and imports only requirement IDs,
decisions, and references into TailTrail. It never falls back to the local
``aidlc-requirements.py`` implementation for Standard or Full mode.
"""
from __future__ import annotations

import json
import importlib.util
from pathlib import Path
from pathlib import PurePosixPath
import sys
from typing import Any
import re


ROOT = Path(__file__).resolve().parents[1]
if ROOT.as_posix() not in sys.path:
    sys.path.insert(0, ROOT.as_posix())

from tailtrail import aidlc_bundle


OFFICIAL_STAGE = "requirements"


def _stage_goal(goal: str) -> str:
    """Make the external-stage summary safe without changing the Planning Lock.

    The Planning Lock retains the original user request verbatim.  The official
    requirements artifact is a bounded, sanitizer-validated summary, so line
    breaks are collapsed rather than rejected or silently truncated.
    """
    text = re.sub(r"\\(?:r\\n|n|r)", " ", str(goal))
    return " ".join(text.split())


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


def _requirements_candidates(pack: Path) -> dict[str, Path]:
    return {
        "core_workflow": pack / "aws-aidlc-rules" / "core-workflow.md",
        "requirements_analysis": pack / "aws-aidlc-rule-details" / "inception" / "requirements-analysis.md",
        "question_format": pack / "aws-aidlc-rule-details" / "common" / "question-format-guide.md",
        "content_validation": pack / "aws-aidlc-rule-details" / "common" / "content-validation.md",
        "session_continuity": pack / "aws-aidlc-rule-details" / "common" / "session-continuity.md",
    }


def _validate_requirements_pack(root: Path, pack: Path, *, reject_symlinks: bool = False) -> dict[str, str]:
    candidates = _requirements_candidates(pack)
    missing = [
        name
        for name, path in candidates.items()
        if (reject_symlinks and path.is_symlink()) or not path.is_file()
    ]
    if missing:
        raise ValueError("verified official pack is missing Standard/Full requirements rules: " + ", ".join(missing))
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


def stage_contract(root: Path, bridge: dict[str, Any]) -> dict[str, str]:
    """Resolve the pre-run official requirements rules from a legacy bridge."""
    return _validate_requirements_pack(root, _pack_root(root, bridge))


def _resolved_pack_root(root: Path, resolution: dict[str, Any]) -> Path:
    relative = resolution.get("pack_path")
    if not isinstance(relative, str) or not relative or "\\" in relative or "\x00" in relative:
        raise ValueError("official run resolution has no safe pack path")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("official run resolution has no safe pack path")
    root = root.resolve()
    lexical_pack = root / pure
    cursor = root
    for part in pure.parts:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError("official run resolution has no safe pack path")
    pack = lexical_pack.resolve()
    try:
        pack.relative_to(root)
    except ValueError as error:
        raise ValueError("official run resolution has no safe pack path") from error
    if not pack.is_dir():
        raise ValueError("official run resolution has no safe pack directory")
    return pack


def _resolution_failure(resolution: dict[str, Any], label: str) -> ValueError:
    issues = resolution.get("issues")
    details: list[str] = []
    if isinstance(issues, list):
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            category = str(issue.get("category", "resolution-blocked")).strip() or "resolution-blocked"
            detail = str(issue.get("detail", "")).strip()
            details.append(f"{category}: {detail}" if detail else category)
    suffix = "; ".join(details) if details else "resolution-blocked"
    return ValueError(f"{label} failed closed: {suffix}")


def stage_contract_for_run(root: Path, run_id: str) -> dict[str, str]:
    """Resolve Requirements rules from one immutable existing-run authority.

    This dormant Phase 2B.2 adapter is read-only.  Phase 3 may call it only
    after provisioning and binding have completed through their own authority.
    """
    resolution = aidlc_bundle.resolve_bound_run(root, run_id)
    if resolution.get("state") == "ready" and resolution.get("compatibility_mode") == "bundled-v2":
        return _validate_requirements_pack(
            root.resolve(), _resolved_pack_root(root, resolution), reject_symlinks=True
        )

    issues = resolution.get("issues")
    categories = {
        str(issue.get("category", ""))
        for issue in issues
        if isinstance(issue, dict) and str(issue.get("category", ""))
    } if isinstance(issues, list) else set()
    if categories != {"missing-run-binding"}:
        raise _resolution_failure(resolution, "official bundled run resolution")

    legacy = aidlc_bundle.resolve_legacy_run(aidlc_bundle.LegacyRunInputs(root, run_id))
    if (
        legacy.get("state") != "legacy-read-only"
        or legacy.get("compatibility_mode") != "legacy-v1-bounded-continuation"
        or legacy.get("can_authorize_new_full") is not False
    ):
        raise _resolution_failure(legacy, "official legacy run resolution")
    return _validate_requirements_pack(
        root.resolve(), _resolved_pack_root(root, legacy), reject_symlinks=True
    )


def _question(identifier: str, question: str, options: list[str], recommended: str, reasoning: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "question": question,
        "options": [{"id": chr(ord("A") + index), "text": option} for index, option in enumerate(options)] + [{"id": "Other", "text": "Other — describe the intended behavior."}],
        "recommended": recommended,
        "reasoning": reasoning,
    }


def _questions(goal: str, requirements: list[dict[str, Any]], feedback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raise RuntimeError(
        "Deprecated local question templates cannot be used for Standard or Full official AIDLC. "
        "The configured host must generate the official stage artifact."
    )
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


def stage_request(root: Path, bridge: dict[str, Any], goal: str, requirements: list[dict[str, Any]], feedback: list[dict[str, Any]], question_context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Describe an official Requirements Analysis stage for the host to execute.

    The official pack is a rule pack.  It does not contain a Python question
    generator, so TailTrail must not pretend that its own templates are official
    questions.  The configured host reads the pinned rules and submits a
    validated question artifact through TailTrail's control plane.
    """
    if bridge.get("compatibility_mode") == "bundled-v2":
        contract = stage_contract_for_run(root, str(bridge.get("tailtrail_run_id", "")))
    else:
        contract = stage_contract(root, bridge)
    return {
        "stage": "Official AI-DLC Requirements Analysis",
        "authority": "official-ai-dlc-pack",
        "official_stage": OFFICIAL_STAGE,
        "official_references": contract,
        "official_intent_id": bridge["official_intent_id"],
        "official_session_id": bridge["official_session_id"],
        "goal": _stage_goal(goal),
        "requirements": requirements,
        "prior_feedback": feedback,
        "question_context": (question_context or {}).get("artifact"),
        "host_action": "Read the listed official rules and the saved Question Orchestrator context. Generate only material unresolved decisions with meaningful mutually exclusive options including Other. Every question must include requirement_ids, decision_class, decision_impact, known_context, evidence_refs, a TailTrail advisory recommendation, and evidence-grounded reasoning. Repository-specific claims require explicit saved evidence; do not replace official AIDLC authority with a local questionnaire.",
        "stage_gate": "The host-generated official Requirements Analysis questions, answers, and revised requirement boundary must be explicitly approved before TailTrail freezes its anchor.",
    }


def validate_host_questions(questions: Any) -> list[dict[str, Any]]:
    if not isinstance(questions, list) or not questions:
        raise ValueError("official host questions must be a non-empty JSON list")
    validated: list[dict[str, Any]] = []
    ids: set[str] = set()
    for item in questions:
        if not isinstance(item, dict):
            raise ValueError("each official host question must be an object")
        identifier = str(item.get("id", "")).strip()
        question = str(item.get("question", "")).strip()
        options = item.get("options")
        recommended = str(item.get("recommended", "")).strip()
        reasoning = str(item.get("reasoning", "")).strip()
        if not identifier or identifier in ids or not question or not recommended or not reasoning:
            raise ValueError("official host questions require unique id, question, recommended, and reasoning")
        if not isinstance(options, list) or len(options) < 3:
            raise ValueError(f"{identifier} requires at least two meaningful options plus Other")
        normalized: list[dict[str, str]] = []
        for option in options:
            if not isinstance(option, dict) or not str(option.get("id", "")).strip() or not str(option.get("text", "")).strip():
                raise ValueError(f"{identifier} options require id and text")
            normalized.append({"id": str(option["id"]).strip(), "text": str(option["text"]).strip()})
        if normalized[-1]["id"].lower() not in {"other", "x"} or "other" not in normalized[-1]["text"].lower():
            raise ValueError(f"{identifier} must end with an Other option as required by the official question format")
        if recommended not in {option["text"] for option in normalized}:
            raise ValueError(f"{identifier} recommended value must exactly match one option text")
        traceability_keys = (
            "requirement_ids",
            "decision_class",
            "decision_impact",
            "known_context",
            "evidence_refs",
        )
        supplied_traceability = [key for key in traceability_keys if key in item]
        if supplied_traceability and len(supplied_traceability) != len(traceability_keys):
            missing = ", ".join(key for key in traceability_keys if key not in item)
            raise ValueError(f"{identifier} traceability metadata is incomplete; missing: {missing}")
        traceability: dict[str, Any] = {}
        if supplied_traceability:
            for key in ("requirement_ids", "decision_impact", "known_context", "evidence_refs"):
                values = item[key]
                if not isinstance(values, list) or not values or any(not isinstance(value, str) or not value.strip() for value in values):
                    raise ValueError(f"{identifier} {key} must be a non-empty string list")
                traceability[key] = list(dict.fromkeys(value.strip() for value in values))
            decision_class = item["decision_class"]
            if not isinstance(decision_class, str) or not decision_class.strip():
                raise ValueError(f"{identifier} decision_class must be a non-empty string")
            traceability["decision_class"] = decision_class.strip()
        ids.add(identifier)
        validated.append({
            "id": identifier,
            "question": question,
            "options": normalized,
            "recommended": recommended,
            "reasoning": reasoning,
            "recommendation_origin": "tailtrail-advisory",
            **traceability,
        })
    return validated


def _question_markdown(goal: str, questions: list[dict[str, Any]], contract: dict[str, str]) -> str:
    lines = ["# Official AI-DLC Requirements Clarification Questions", "", "This file is governed by the verified official AI-DLC requirements and question-format rules.", "", f"## Requested outcome", "", goal, "", "## Governing rule references", ""]
    lines.extend(f"- `{path}`" for path in contract.values())
    for index, question in enumerate(questions, start=1):
        lines.extend(["", f"## Question {index} ({question['id']})", question["question"], ""])
        lines.extend(f"{option['id']}) {option['text']}" for option in question["options"])
        lines.extend(["", "[Answer]: ", ""])
    return "\n".join(lines)


def gather(root: Path, bridge: dict[str, Any], goal: str, requirements: list[dict[str, Any]], feedback: list[dict[str, Any]]) -> dict[str, Any]:
    raise RuntimeError(
        "Official AI-DLC questions must be generated by the configured host after it loads the pinned official rules. "
        "Use stage_request() and record the host artifact through TailTrail instead."
    )


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
        resolved[identifier] = {
            "choice": choice,
            "detail": detail,
            "selected": options[choice],
            "requirement_ids": list(question.get("requirement_ids", [])),
            "decision_class": question.get("decision_class"),
            "decision_impact": list(question.get("decision_impact", [])),
            "evidence_refs": list(question.get("evidence_refs", [])),
        }
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
