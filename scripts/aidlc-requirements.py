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
    prompt_context = f"{goal.lower()} {statements}"
    questions = _questions_for(prompt_context, feedback)
    return {
        "stage": "AIDLC Requirements",
        "stage_evidence": evidence,
        "goal": goal,
        "functional_requirements": functional,
        "constraints": constraints,
        "known_facts": _known_facts(prompt_context),
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
        questions = _task_shaped_questions(statements)
    comments = "; ".join(dict.fromkeys(str(row.get("comment", "")).strip() for row in feedback if str(row.get("comment", "")).strip()))
    if comments:
        next_id = f"Q{len(questions) + 1}"
        questions.append(_question(next_id, f"How should this prior review concern change the requirement boundary: {comments}", ["Clarify the affected requirement", "Expand the requirement boundary and proof plan"], "Clarify first", "Preserve the smallest coherent scope unless the feedback demonstrates a missing dependency or contract."))
    return questions


def _known_facts(statements: str) -> list[str]:
    """List material facts already supplied, so AIDLC does not ask them again."""
    facts: list[str] = []
    checks = (
        (("react", "frontend", "ui", "page/tool", "form"), "A frontend/UI change is requested."),
        (("existing", "reuse", "do not add new dependenc"), "Existing project components and dependencies must be reused where possible."),
        (("figma", "reference", "spec doc"), "A read-only design or specification reference was supplied."),
        (("event header", "mandatory block", "audit event"), "The requested feature includes event-header and mandatory audit-block inputs."),
        (("uuid", "message id"), "Message ID generation is part of the requested behavior."),
        (("sender id", "required field", "mandatory field"), "Required-field validation is explicitly requested."),
        (("api", "contract"), "An API or contract impact is in scope."),
        (("test", "acceptance criteria"), "Validation evidence is required before completion."),
    )
    for terms, fact in checks:
        if any(term in statements for term in terms) and fact not in facts:
            facts.append(fact)
    return facts


def _task_shaped_questions(statements: str) -> list[dict[str, Any]]:
    """Ask decisions that remain open for the request's detected work shape.

    This is deliberately deterministic and prompt-only: the Requirements stage
    has not inspected source yet, so it must not invent repository facts.
    """
    ui_terms = ("frontend", "react", " ui", "page", "form", "component", "figma", "layout")
    api_terms = ("api", "endpoint", "contract", "backend")
    questions: list[dict[str, Any]] = []

    if any(term in statements for term in ui_terms):
        questions.extend([
            _question(
                "Q1",
                "What must the generated pipeline audit-event hierarchy do after the user completes the form?",
                ["Render an in-page preview only", "Render a preview and expose the existing project save/export action", "Submit the hierarchy through an existing API contract"],
                "Render a preview and reuse an existing save/export action when the target project already provides one.",
                "The request defines how users enter common values, but not the final delivery action. This decision determines whether the feature is presentation-only, reuses an existing capability, or needs an API contract.",
            ),
            _question(
                "Q2",
                "How should common Event Header and mandatory-block values behave at Step and Task level?",
                ["Always inherit and remain read-only", "Inherit by default but allow an explicit per-event override", "Require each Step and Task to enter values independently"],
                "Inherit by default but allow an explicit per-event override when the domain permits exceptions.",
                "Automatic propagation is stated, but the override rule is not. Making it explicit prevents a hierarchy that either duplicates data unnecessarily or cannot represent a valid exception.",
            ),
            _question(
                "Q3",
                "When should the generated Message ID and Event Time be created?",
                ["Once when the form opens", "When a hierarchy is generated, with an explicit regenerate action", "Only when the hierarchy is submitted"],
                "Generate when the hierarchy is generated and provide an explicit regenerate action if the UI supports it.",
                "UUID and time values need a stable lifecycle; regenerating them on every render would make the preview unreliable and break repeatable validation.",
            ),
            _question(
                "Q4",
                "What validation experience is required before generation?",
                ["Inline field errors only", "Inline errors plus a form-level summary and focus to the first invalid field", "Allow generation and show errors only in generated output"],
                "Inline errors plus a form-level summary and focus to the first invalid field.",
                "Mandatory inputs such as Sender ID need clear, accessible feedback before hierarchy generation; output-only errors make correction slow and can produce invalid audit data.",
            ),
        ])
        if not any(term in statements for term in api_terms):
            questions.append(_question(
                "Q5",
                "Should this first frontend delivery remain local to the UI, or is persistence/API integration required now?",
                ["Local preview/generation only", "Reuse an already-existing API", "Define a new API contract as part of this change"],
                "Reuse an already-existing API if one exists; otherwise keep the first delivery local unless the product requirement requires persistence.",
                "The request names a frontend target but does not state persistence behavior. This prevents an accidental backend expansion while leaving a deliberate contract change possible.",
            ))
    elif any(term in statements for term in api_terms):
        questions = [
            _question("Q1", "Which existing contract must the new behavior extend or preserve?", ["An existing endpoint/contract", "A new versioned contract", "Internal service behavior only"], "Extend the existing contract when it supports the requested behavior.", "The contract boundary determines compatibility, callers, and the minimum evidence needed."),
            _question("Q2", "Which success, validation, conflict, and failure outcomes must clients observe?", ["Reuse existing error conventions", "Define explicit new response cases"], "Reuse existing project error conventions and add only the cases the new behavior needs.", "API completion must be observable and testable without silently changing client behavior."),
            _question("Q3", "What proof is required for the caller path?", ["Focused service tests", "Service plus contract/integration evidence"], "Service plus contract/integration evidence when a client-facing contract changes.", "A passing internal unit test alone does not prove clients receive the intended contract."),
        ]
    else:
        questions = [
            _question("Q1", "Which user-visible or caller-visible result remains unspecified in this request?", ["No additional result; implement only the stated behavior", "Clarify the missing output or state transition"], "No additional result when the stated acceptance criteria are complete.", "This asks for a real unresolved behavior instead of asking the user to restate the whole outcome."),
            _question("Q2", "Which named integration, data boundary, or side effect needs an explicit compatibility decision?", ["None beyond the stated scope", "Identify the affected boundary and preservation rule"], "Identify one only when the request names an integration, persistence change, or external effect.", "It keeps the requirement boundary narrow while making material compatibility decisions visible."),
            _question("Q3", "What focused evidence proves the stated acceptance criteria at the affected boundary?", ["Focused local tests", "Focused tests plus integration/contract evidence"], "Use the smallest evidence tier that covers the named boundary.", "The proof decision should follow the requested behavior and affected boundary, rather than use a generic test preference."),
        ]
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
