"""Define the closed DWR-0 reason-code and legal-transition vocabulary."""
from __future__ import annotations


REASON_CODES = {
    "approval-granted", "approval-rejected", "approval-expired",
    "blocked-missing-authority", "blocked-missing-evidence", "contract-failure",
    "stage-failed", "stage-skipped-approved", "input-stale", "retry-eligible",
    "replan-required", "recovery-required", "workflow-cancelled",
    "workflow-superseded", "workflow-completed",
    "workflow-created", "workflow-ready", "workflow-started", "workflow-paused",
    "workflow-resumed", "workflow-blocked", "workflow-failed", "follow-up-created",
    "stage-registered", "stage-ready", "stage-started", "stage-passed",
    "stage-awaiting-approval", "stage-blocked", "stage-cancelled", "external-dependency",
}

REJECTION_CODES = {
    "unknown-reason-code", "illegal-workflow-transition", "illegal-stage-transition",
    "unsupported-target-state", "terminal-workflow", "unknown-stage", "prerequisite-incomplete",
    "stage-incomplete-for-completion",
    "reason-target-mismatch",
}

WORKFLOW_TRANSITIONS = {
    "draft": {"awaiting_approval", "cancelled", "superseded"},
    "awaiting_approval": {"ready", "blocked", "cancelled", "superseded"},
    "ready": {"running", "paused", "blocked", "cancelled", "superseded"},
    "running": {"paused", "blocked", "failed", "cancelled", "superseded", "completed"},
    "paused": {"ready", "blocked", "cancelled", "superseded"},
    "blocked": {"ready", "failed", "cancelled", "superseded"},
    "failed": {"ready", "cancelled", "superseded"},
    "cancelled": set(), "superseded": set(), "completed": set(),
}

STAGE_TRANSITIONS = {
    "pending": {"ready", "blocked", "skipped", "cancelled"},
    "ready": {"awaiting_approval", "running", "blocked", "skipped", "stale", "cancelled"},
    "awaiting_approval": {"ready", "running", "blocked", "skipped", "cancelled"},
    "running": {"passed", "failed", "blocked", "stale", "cancelled"},
    "passed": {"stale"}, "failed": {"ready", "blocked", "cancelled"},
    "blocked": {"ready", "skipped", "cancelled"}, "stale": {"ready", "cancelled"},
    "skipped": set(), "cancelled": set(),
}


def transition_allowed(scope: str, previous: str, next_state: str) -> bool:
    table = WORKFLOW_TRANSITIONS if scope == "workflow" else STAGE_TRANSITIONS if scope == "stage" else None
    if table is None or previous not in table:
        return False
    return next_state in table[previous]
