"""Pure journal-to-projection reducer for the durable workflow runtime."""
from __future__ import annotations

from typing import Any

from workflow_runtime import reason_codes


WORKFLOW_EVENT_STATES = {
    "workflow-created": "draft",
    "workflow-awaiting-approval": "awaiting_approval",
    "workflow-ready": "ready",
    "workflow-started": "running",
    "workflow-resumed": "ready",
    "workflow-paused": "paused",
    "workflow-blocked": "blocked",
    "workflow-failed": "failed",
    "workflow-cancelled": "cancelled",
    "workflow-superseded": "superseded",
    "workflow-completed": "completed",
}
STAGE_EVENT_STATES = {
    "stage-ready": "ready",
    "stage-awaiting-approval": "awaiting_approval",
    "stage-started": "running",
    "stage-passed": "passed",
    "stage-failed": "failed",
    "stage-blocked": "blocked",
    "stage-skipped": "skipped",
    "stage-stale": "stale",
    "stage-cancelled": "cancelled",
}


def initial(binding: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1", "type": "tailtrail-workflow-projection",
        "workflow_id": binding["workflow_id"], "tailtrail_run_id": binding["tailtrail_run_id"],
        "last_sequence": 0, "last_event_hash": None, "artifact_refs": {}, "artifact_hashes": {},
        "state": "initialized", "lifecycle_state": "initialized", "workflow_status": "draft",
        "stages": {}, "current_stage_id": None, "parent_workflow_id": None,
        "successor_workflow_id": None, "workflow_reason_code": None, "terminal_reason_code": None,
        "boundary": "Projection is derived only from the append-only workflow journal; it grants no execution authority.",
    }


def _compatibility_state(status: str) -> str:
    if status == "paused": return "paused"
    if status == "cancelled": return "cancelled"
    if status in {"superseded", "completed", "failed"}: return status
    return "active"


def replay(binding: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    projection = initial(binding)
    for event in events:
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            continue
        event_type = str(event.get("event_type", ""))
        if event_type == "artifact-snapshot-captured":
            projection["artifact_refs"] = payload.get("artifact_refs", {})
            projection["artifact_hashes"] = payload.get("artifact_hashes", {})
            projection["state"] = "captured"
        elif event_type == "stage-registered":
            stage_id = str(payload.get("stage_id", ""))
            if stage_id:
                projection["stages"][stage_id] = {
                    "status": "pending", "prerequisites": list(payload.get("prerequisites", [])),
                    "capability_id": payload.get("capability_id"), "last_reason_code": "stage-registered", "last_approval_id": None,
                }
        elif event_type in STAGE_EVENT_STATES:
            stage_id = str(payload.get("stage_id", ""))
            if stage_id in projection["stages"]:
                projection["stages"][stage_id]["status"] = STAGE_EVENT_STATES[event_type]
                projection["stages"][stage_id]["last_reason_code"] = payload.get("reason_code")
                if payload.get("approval_id"): projection["stages"][stage_id]["last_approval_id"] = payload.get("approval_id")
                projection["current_stage_id"] = stage_id
        elif event_type in WORKFLOW_EVENT_STATES:
            status = WORKFLOW_EVENT_STATES[event_type]
            projection["workflow_status"] = status
            projection["lifecycle_state"] = _compatibility_state(status)
            projection["workflow_reason_code"] = payload.get("reason_code")
            if status in {"cancelled", "superseded", "completed"}:
                projection["terminal_reason_code"] = payload.get("reason_code")
        elif event_type == "workflow-follow-up-linked":
            projection["parent_workflow_id"] = payload.get("parent_workflow_id")
        elif event_type == "workflow-successor-linked":
            projection["successor_workflow_id"] = payload.get("successor_workflow_id")
        projection["last_sequence"] = event["sequence"]
        projection["last_event_hash"] = event["event_hash"]
    return projection


def semantic_issues(events: list[dict[str, Any]]) -> list[str]:
    """Reject a correctly hashed journal whose structured transitions are illegal."""
    workflow_status = "draft"; stages: dict[str, dict[str, Any]] = {}; issues: list[str] = []
    for event in events:
        payload = event.get("payload", {}); event_type = str(event.get("event_type", ""))
        if not isinstance(payload, dict):
            issues.append(f"journal event {event.get('sequence')} payload is not an object"); continue
        if event_type == "stage-registered":
            stage_id = str(payload.get("stage_id", ""))
            if not stage_id or stage_id in stages: issues.append(f"journal event {event.get('sequence')} has an invalid or duplicate stage registration")
            else: stages[stage_id] = {"status": "pending", "prerequisites": list(payload.get("prerequisites", []))}
            continue
        if event_type in WORKFLOW_EVENT_STATES and "from_state" in payload:
            previous = str(payload.get("from_state")); target = str(payload.get("to_state"))
            expected = WORKFLOW_EVENT_STATES[event_type]
            if previous != workflow_status or target != expected or not reason_codes.transition_allowed("workflow", previous, target):
                issues.append(f"journal event {event.get('sequence')} has an illegal workflow transition")
            else: workflow_status = target
            if target == "completed" and any(row["status"] not in {"passed", "skipped"} for row in stages.values()):
                issues.append(f"journal event {event.get('sequence')} completes an unfinished stage graph")
            continue
        if event_type in STAGE_EVENT_STATES:
            stage_id = str(payload.get("stage_id", "")); row = stages.get(stage_id)
            if not row:
                issues.append(f"journal event {event.get('sequence')} references an unknown stage"); continue
            previous = str(payload.get("from_state")); target = str(payload.get("to_state")); expected = STAGE_EVENT_STATES[event_type]
            if previous != row["status"] or target != expected or not reason_codes.transition_allowed("stage", previous, target):
                issues.append(f"journal event {event.get('sequence')} has an illegal stage transition")
            else: row["status"] = target
            if target in {"ready", "awaiting_approval", "running"}:
                incomplete = [item for item in row["prerequisites"] if stages.get(item, {}).get("status") not in {"passed", "skipped"}]
                if incomplete: issues.append(f"journal event {event.get('sequence')} bypasses stage prerequisites")
    return issues
