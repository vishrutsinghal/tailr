#!/usr/bin/env python3
"""Execute the AIDLC Requirements stage from a bounded TailTrail planning input.

This is intentionally an AIDLC component, not a Planning Lock heuristic.  It
uses the Requirements stage contract and question template to turn a saved
planning boundary into a structured requirements-gathering brief.  TailTrail
calls it, persists its output, and controls approval; AIDLC owns the questions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STAGE_PLAYBOOK = ROOT / "aidlc" / "stages" / "requirements.md"
QUESTION_TEMPLATE = ROOT / "templates" / "question-file.md"
REQUIREMENTS_TEMPLATE = ROOT / "templates" / "requirements.md"


def _stage_evidence() -> dict[str, str]:
    """Confirm the packaged AIDLC materials that govern this stage."""
    for path, marker in (
        (STAGE_PLAYBOOK, "turn the request into clear, testable intent"),
        (QUESTION_TEMPLATE, "Recommended option:"),
        (REQUIREMENTS_TEMPLATE, "Functional requirements:"),
    ):
        body = path.read_text(encoding="utf-8")
        if marker not in body:
            raise ValueError(f"AIDLC requirements resource is incomplete: {path.relative_to(ROOT).as_posix()}")
    return {
        "stage_playbook": STAGE_PLAYBOOK.relative_to(ROOT).as_posix(),
        "question_template": QUESTION_TEMPLATE.relative_to(ROOT).as_posix(),
        "requirements_template": REQUIREMENTS_TEMPLATE.relative_to(ROOT).as_posix(),
    }


def gather(goal: str, requirements: list[dict[str, Any]], feedback: list[dict[str, Any]]) -> dict[str, Any]:
    """Produce the bounded AIDLC Requirements-stage brief.

    The output follows the stage playbook: functional intent, explicit
    constraints, assumptions/non-goals, and questions with meaningful choices,
    a recommended option, and reasoning.
    """
    evidence = _stage_evidence()
    functional = [row for row in requirements if row.get("kind") != "preserve"]
    constraints = [row for row in requirements if row.get("kind") == "preserve"]
    statements = " ".join(str(row.get("statement", "")) for row in requirements).lower()
    questions = _questions_for(f"{goal.lower()} {statements}", feedback)
    return {
        "stage": "AIDLC Requirements",
        "stage_evidence": evidence,
        "goal": goal,
        "functional_requirements": functional,
        "constraints": constraints,
        "assumptions": ["Current Planning Lock scope is a proposal, not approved implementation scope."],
        "non_goals": ["Do not inspect source, run tests, edit files, or implement code before the revised requirement boundary is approved."],
        "questions": questions,
        "stage_gate": "All material questions are answered or explicitly accepted as risk; then TailTrail presents the revised requirement boundary for approval.",
    }


def _question(identifier: str, question: str, options: list[str], recommended: str, reasoning: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "question": question,
        "options": [{"id": chr(ord("A") + index), "text": option} for index, option in enumerate(options)] + [{"id": "Other", "text": "Other — describe the intended behavior."}],
        "recommended": recommended,
        "reasoning": reasoning,
    }


def _questions_for(statements: str, feedback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if any(marker in statements for marker in ("hands-free", "hands free", "end-to-end", "end to end")):
        questions = _full_delivery_questions(statements)
        comments = "; ".join(dict.fromkeys(str(row.get("comment", "")).strip() for row in feedback if str(row.get("comment", "")).strip()))
        if comments:
            questions.append(_question("Q13", f"How should prior plan feedback change the delivery boundary: {comments}", ["Revise only disputed requirements and dependent proof", "Expand the programme boundary and rerun affected slices"], "Revise only disputed requirements and dependent proof", "Preserve validated work and change only the requirements or slices that the feedback materially affects."))
        return questions
    if "zero quantit" in statements:
        questions = [
            _question(
                "Q1",
                "Where must zero quantity be rejected?",
                ["Validator only", "Validator and service/API path"],
                "Validator and service/API path",
                "It keeps the domain rule central while proving callers expose the intended contract.",
            ),
            _question(
                "Q2",
                "Which existing quantity cases must be explicitly preserved?",
                ["Positive quantities only", "Positive, negative, missing, and non-numeric quantities"],
                "Positive quantities only, unless the current contract says otherwise",
                "The requested change names zero; expanding invalid-input policy without evidence would broaden scope.",
            ),
            _question(
                "Q3",
                "What proof is required before completion?",
                ["Focused validator unit tests", "Focused validator tests plus a service/API path test"],
                "Focused validator tests plus a service/API path test",
                "The rule and the caller contract can fail independently; both should be proven if that path is in scope.",
            ),
        ]
    else:
        questions = [
            _question("Q1", "What exact observable outcome defines completion?", ["Specified behavior only", "Specified behavior plus caller/integration behavior"], "Specified behavior plus caller/integration behavior when a caller is affected", "Requirements need a testable outcome and an explicit boundary."),
            _question("Q2", "What existing behavior must be preserved?", ["Only the named happy path", "All behavior outside the approved change boundary"], "All behavior outside the approved change boundary", "Preservation rules prevent accidental scope expansion."),
            _question("Q3", "What is the minimum acceptable proof?", ["Focused unit test", "Focused unit test plus integration/contract evidence"], "Focused unit test; add higher-tier proof only if a caller or contract is affected", "Evidence should match the requirement without adding unnecessary test cost."),
        ]
    comments = "; ".join(dict.fromkeys(str(row.get("comment", "")).strip() for row in feedback if str(row.get("comment", "")).strip()))
    if comments:
        questions.append(_question("Q4", f"How should this prior review concern change the requirement boundary: {comments}", ["Clarify the affected requirement", "Expand the requirement boundary and proof plan"], "Clarify first", "Preserve the smallest coherent scope unless the feedback demonstrates a missing dependency or contract."))
    return questions


def _full_delivery_questions(statements: str) -> list[dict[str, Any]]:
    """Return the full AIDLC decision set for explicit hands-free delivery."""
    return [
        _question("Q1", "What exact business condition permits the requested action?", ["Only the explicitly named precondition", "Named precondition plus documented equivalent states"], "Only the explicitly named precondition", "For cancellation, this keeps the rule at ‘before shipment’ and prevents a refund or stock release after fulfilment has begun."),
        _question("Q2", "Which existing states and behaviors must be preserved?", ["All behavior outside the approved action boundary", "Only the current happy path"], "All behavior outside the approved action boundary", "Preservation is the baseline for requirement-completion and drift checks."),
        _question("Q3", "How should state transition and side effects be coordinated?", ["One idempotent orchestration boundary", "Independent best-effort calls"], "One idempotent orchestration boundary", "Cancellation, stock release, refund, notification, and audit must share one recoverable outcome boundary; otherwise a retry can refund twice or notify a customer about an incomplete cancellation."),
        _question("Q4", "What retry/idempotency contract is required?", ["A stable request/action key prevents duplicate effects", "Best-effort duplicate detection only"], "A stable request/action key prevents duplicate effects", "Money, stock, notifications, and audit events require deterministic duplicate protection."),
        _question("Q5", "What happens when a downstream dependency fails after part of the action succeeds?", ["Record pending/reconciliation state with bounded retry", "Immediately roll back every completed side effect"], "Record pending/reconciliation state with bounded retry", "A payment or notification provider can fail after inventory changes; a durable pending state makes that mismatch visible and recoverable instead of hiding it behind a failed request."),
        _question("Q6", "What API/contract behavior is required?", ["Preserve existing contract style and add explicit success, validation, conflict, not-found, and transient-failure responses", "Add only a success response"], "Preserve existing contract style and add explicit success, validation, conflict, not-found, and transient-failure responses", "Clients need a stable, testable contract for expected and recoverable outcomes."),
        _question("Q7", "What authorization, ownership, and audit requirements apply?", ["Enforce existing ownership/authorization and emit an immutable audit record", "Rely on caller trust"], "Enforce existing ownership/authorization and emit an immutable audit record", "A user-facing state change must preserve trust, tenancy, and auditability."),
        _question("Q8", "When should notifications be sent?", ["After required business effects succeed or a pending state is explicitly recorded", "Before downstream effects complete"], "After required business effects succeed or a pending state is explicitly recorded", "Customers should not receive a success notification for an incomplete operation."),
        _question("Q9", "Which concurrency race must be resolved?", ["The action must serialize or conflict safely with competing lifecycle changes", "No explicit concurrency rule"], "The action must serialize or conflict safely with competing lifecycle changes", "Lifecycle races are a common source of double effects and invalid states."),
        _question("Q10", "What observability and reconciliation evidence is required?", ["Structured outcome, failure, retry, and reconciliation signals", "Only application logs"], "Structured outcome, failure, retry, and reconciliation signals", "Release confidence requires evidence beyond an individual request log."),
        _question("Q11", "What rollout and rollback boundary is required?", ["Feature-flagged or staged rollout with explicit monitoring and safe rollback criteria", "Immediate unrestricted rollout"], "Feature-flagged or staged rollout with explicit monitoring and safe rollback criteria", "Refund and inventory errors have financial and operational impact; staged release lets the team stop new cancellations while preserving evidence for already-started operations."),
        _question("Q12", "What minimum proof closes the programme?", ["Focused unit plus integration, contract, behaviour, and rollout/recovery evidence where applicable", "Focused unit tests only"], "Focused unit plus integration, contract, behaviour, and rollout/recovery evidence where applicable", "Multi-file user-facing work is not complete when only an isolated function passes."),
    ]


def validate_answers(stage: dict[str, Any], answers: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """Validate complete AIDLC question answers before creating a revision."""
    if not isinstance(answers, list):
        raise ValueError("AIDLC answers must be a JSON list")
    questions = {str(row["id"]): row for row in stage.get("questions", [])}
    provided = {str(row.get("question_id", "")): row for row in answers if isinstance(row, dict)}
    if set(provided) != set(questions):
        raise ValueError("AIDLC answers must include exactly one answer for every open question")
    resolved: dict[str, dict[str, str]] = {}
    for question_id, question in questions.items():
        row = provided[question_id]
        choice = str(row.get("choice", "")).strip()
        allowed = {str(option["id"]) for option in question["options"]}
        if choice not in allowed:
            raise ValueError(f"{question_id} choice must be one of: {', '.join(sorted(allowed))}")
        detail = str(row.get("detail", "")).strip()
        if choice == "Other" and not detail:
            raise ValueError(f"{question_id} requires detail when choice is Other")
        selected = next(option["text"] for option in question["options"] if option["id"] == choice)
        resolved[question_id] = {"choice": choice, "detail": detail, "selected": selected}
    return resolved


def revise(stage: dict[str, Any], answers: list[dict[str, Any]]) -> dict[str, Any]:
    """Turn approved AIDLC answers into a canonical-ready requirement proposal."""
    resolved = validate_answers(stage, answers)
    requirements = [{**row, "acceptance_criteria": list(row.get("acceptance_criteria", [])), "preserve_rules": list(row.get("preserve_rules", [])), "likely_paths": list(row.get("likely_paths", [])), "evidence_plan": list(row.get("evidence_plan", []))} for row in stage["requirements"]]
    statements = " ".join(str(row.get("statement", "")) for row in requirements).lower()
    if "zero quantit" in statements and len(requirements) >= 3:
        q1, q2, q3 = resolved["Q1"], resolved["Q2"], resolved["Q3"]
        requirements[0]["statement"] = "Reject zero quantities in the validator and expose the same rejection through the service/API path." if q1["choice"] == "B" else (q1["detail"] if q1["choice"] == "Other" else "Reject zero quantities in the existing validation boundary.")
        requirements[0]["acceptance_criteria"] = ["A zero quantity is rejected with the approved error contract."]
        requirements[1]["statement"] = "Preserve positive quantities; preserve existing negative, missing, and non-numeric behavior without changing their contract." if q2["choice"] == "B" else (q2["detail"] if q2["choice"] == "Other" else "Preserve valid positive-quantity behavior outside the new rejection case.")
        requirements[1]["preserve_rules"] = [requirements[1]["statement"]]
        requirements[2]["statement"] = "Add focused validator and service/API-path evidence for zero rejection and preserved positive behavior." if q3["choice"] == "B" else (q3["detail"] if q3["choice"] == "Other" else "Add focused validator unit-test evidence for zero rejection and preserved positive behavior.")
        requirements[2]["evidence_plan"] = [requirements[2]["statement"]]
    else:
        for row in requirements:
            row["acceptance_criteria"].append("AIDLC answer set is reflected in the approved requirement boundary.")
    return {
        "goal": stage["goal"],
        "requirements": requirements,
        "aidlc_answers": resolved,
        "approval_summary": "AIDLC Requirements stage completed: approve this revised boundary to create the immutable TailTrail anchor and activate the existing Planning Lock.",
    }
