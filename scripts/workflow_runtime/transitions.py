"""Deterministic DWR Phase 2 workflow and stage transition authority."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_runtime import approvals, compiler, reason_codes, storage


WORKFLOW_EVENTS = {
    "awaiting_approval": "workflow-awaiting-approval", "ready": "workflow-ready",
    "running": "workflow-started", "paused": "workflow-paused", "blocked": "workflow-blocked",
    "failed": "workflow-failed", "cancelled": "workflow-cancelled",
    "superseded": "workflow-superseded", "completed": "workflow-completed",
}
STAGE_EVENTS = {
    "ready": "stage-ready", "awaiting_approval": "stage-awaiting-approval",
    "running": "stage-started", "passed": "stage-passed", "failed": "stage-failed",
    "blocked": "stage-blocked", "skipped": "stage-skipped", "stale": "stage-stale",
    "cancelled": "stage-cancelled",
}
WORKFLOW_REASONS = {
    "awaiting_approval": {"workflow-created"},
    "ready": {"approval-granted", "workflow-resumed", "retry-eligible", "replan-required", "recovery-required"},
    "running": {"workflow-started"}, "paused": {"workflow-paused"},
    "blocked": {"workflow-blocked", "blocked-missing-authority", "blocked-missing-evidence", "external-dependency", "contract-failure", "recovery-required"},
    "failed": {"workflow-failed", "stage-failed", "contract-failure"},
    "cancelled": {"workflow-cancelled"}, "superseded": {"workflow-superseded"},
    "completed": {"workflow-completed"},
}
STAGE_REASONS = {
    "ready": {"stage-ready", "approval-granted", "retry-eligible", "replan-required", "recovery-required"},
    "awaiting_approval": {"stage-awaiting-approval", "blocked-missing-authority"},
    "running": {"stage-started", "approval-granted"}, "passed": {"stage-passed"},
    "failed": {"stage-failed", "contract-failure"},
    "blocked": {"stage-blocked", "blocked-missing-authority", "blocked-missing-evidence", "external-dependency", "recovery-required"},
    "skipped": {"stage-skipped-approved"}, "stale": {"input-stale"},
    "cancelled": {"stage-cancelled", "workflow-cancelled"},
}


def _error(scope: str, subject: str, previous: str, next_state: str, code: str) -> ValueError:
    return ValueError(
        f"transition-rejected reason_code={code} scope={scope} subject_id={subject} "
        f"from_state={previous} to_state={next_state}"
    )


def _reason(reason_code: str) -> None:
    if reason_code not in reason_codes.REASON_CODES:
        raise ValueError(f"transition-rejected reason_code=unknown-reason-code supplied={reason_code}")


def _reason_target(scope: str, next_state: str, reason_code: str, subject_id: str, previous: str) -> None:
    allowed = (WORKFLOW_REASONS if scope == "workflow" else STAGE_REASONS).get(next_state, set())
    if reason_code not in allowed:
        raise _error(scope, subject_id, previous, next_state, "reason-target-mismatch")


def ensure_stages(root: Path, workflow_id: str) -> dict[str, Any]:
    """Register a frozen compiler graph once; never infer stages from evidence."""
    projection = storage.status(root, workflow_id)["last_valid_projection"]
    if projection.get("stages"):
        return projection
    try:
        plan = compiler.show(root, workflow_id)
    except ValueError:
        return projection
    for stage in plan.get("stages", []):
        storage.append_event(root, workflow_id, "stage-registered", {
            "stage_id": stage["stage_id"], "capability_id": stage.get("capability_id"),
            "prerequisites": stage.get("prerequisites", []), "reason_code": "stage-registered",
        })
    return storage.status(root, workflow_id)["last_valid_projection"]


def workflow(root: Path, workflow_id: str, next_state: str, reason_code: str) -> dict[str, Any]:
    root = root.resolve(); _reason(reason_code)
    projection = storage.status(root, workflow_id)["last_valid_projection"]
    previous = str(projection.get("workflow_status", "draft"))
    if not reason_codes.transition_allowed("workflow", previous, next_state):
        raise _error("workflow", workflow_id, previous, next_state, "illegal-workflow-transition")
    _reason_target("workflow", next_state, reason_code, workflow_id, previous)
    if next_state == "completed":
        incomplete = [stage_id for stage_id, row in projection.get("stages", {}).items()
                      if row.get("status") not in {"passed", "skipped"}]
        if incomplete:
            raise _error("workflow", workflow_id, previous, next_state, "stage-incomplete-for-completion")
    event_type = WORKFLOW_EVENTS.get(next_state)
    if not event_type:
        raise _error("workflow", workflow_id, previous, next_state, "unsupported-target-state")
    return storage.append_event(root, workflow_id, event_type, {
        "from_state": previous, "to_state": next_state, "reason_code": reason_code,
        "boundary": "Workflow metadata transition only; no project action or rollback occurred.",
    })


def stage(root: Path, workflow_id: str, stage_id: str, next_state: str, reason_code: str, approval_id: str | None = None) -> dict[str, Any]:
    root = root.resolve(); _reason(reason_code); projection = ensure_stages(root, workflow_id)
    workflow_status = str(projection.get("workflow_status", "draft"))
    if workflow_status in {"cancelled", "superseded", "completed"}:
        raise _error("stage", stage_id, "workflow-terminal", next_state, "terminal-workflow")
    current = projection.get("stages", {}).get(stage_id)
    if not current:
        raise _error("stage", stage_id, "unknown", next_state, "unknown-stage")
    previous = str(current.get("status", "pending"))
    if not reason_codes.transition_allowed("stage", previous, next_state):
        raise _error("stage", stage_id, previous, next_state, "illegal-stage-transition")
    _reason_target("stage", next_state, reason_code, stage_id, previous)
    if next_state in {"ready", "running", "awaiting_approval"}:
        incomplete = [item for item in current.get("prerequisites", [])
                      if projection["stages"].get(item, {}).get("status") not in {"passed", "skipped"}]
        if incomplete:
            raise _error("stage", stage_id, previous, next_state, "prerequisite-incomplete")
    authority = approvals.authorize_stage(root, workflow_id, stage_id, approval_id, skip=next_state == "skipped") if next_state in {"running", "skipped"} else None
    event_type = STAGE_EVENTS.get(next_state)
    if not event_type:
        raise _error("stage", stage_id, previous, next_state, "unsupported-target-state")
    return storage.append_event(root, workflow_id, event_type, {
        "stage_id": stage_id, "from_state": previous, "to_state": next_state,
        "reason_code": reason_code, "approval_id": authority.get("approval_id") if authority else None,
        "boundary": "Stage metadata transition only; no capability was executed.",
    })


def transition_contract(scope: str, subject_id: str, previous: str, next_state: str, reason_code: str) -> dict[str, Any]:
    return {"schema_version": "1", "type": "tailtrail-workflow-transition", "scope": scope,
            "subject_id": subject_id, "from_state": previous, "to_state": next_state,
            "reason_code": reason_code, "legal": reason_codes.transition_allowed(scope, previous, next_state)}
