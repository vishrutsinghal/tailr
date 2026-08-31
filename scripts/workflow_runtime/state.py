"""DWR-1 local workflow lifecycle and read-only product surface.

This module is intentionally a control plane over DWR-A ownership and the
DWR-minus append-only journal.  It does not dispatch capability stages,
execute project commands, inspect source, or derive a second task state.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow_runtime import approvals, capabilities, compiler, evidence, ownership, storage, task_scope, transitions


LEDGER = ownership.LEDGER
_LIFECYCLE_EVENT = {
    "workflow-created": "workflow_state_created",
    "workflow-paused": "workflow_state_paused",
    "workflow-resumed": "workflow_state_resumed",
    "workflow-cancelled": "workflow_state_cancelled",
}


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _requirements(root: Path, binding: dict[str, Any]) -> list[dict[str, Any]]:
    rows = ownership._read_ref(root, str(binding["requirement_matrix_ref"]))
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("canonical requirement matrix is invalid")
    return rows


def _optional(operation: Any) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return operation(), None
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return None, str(error)


def _record(root: Path, workflow_id: str, event_type: str) -> dict[str, Any]:
    result = storage.lifecycle(root, workflow_id, event_type)
    binding = ownership.show(root, workflow_id)
    LEDGER.append_event(root, binding["tailtrail_run_id"], _LIFECYCLE_EVENT[event_type], {
        "workflow_id": workflow_id,
        "journal": result["projection"].get("workflow_id") and storage.journal_path(root, workflow_id).relative_to(root).as_posix(),
        "sequence": result["event"]["sequence"],
    })
    return result


def create(root: Path, run_id: str, workflow_id: str | None = None) -> dict[str, Any]:
    """Initialize/read DWR state for an already approved canonical run."""
    root = root.resolve()
    workflow_id = workflow_id or ownership.suggested_id(run_id)
    try:
        binding = ownership.show(root, workflow_id)
        if binding["tailtrail_run_id"] != run_id:
            raise ValueError("existing workflow ID is bound to another TailTrail run")
    except ValueError as error:
        if "does not exist" not in str(error):
            raise
        binding = ownership.bind(root, run_id, workflow_id)
    if not storage.projection_path(root, workflow_id).is_file():
        storage.initialize(root, workflow_id)
    projection = storage.status(root, workflow_id)["last_valid_projection"]
    if projection.get("lifecycle_state") == "initialized":
        _record(root, workflow_id, "workflow-created")
        transitions.workflow(root, workflow_id, "awaiting_approval", "workflow-created")
        transitions.workflow(root, workflow_id, "ready", "approval-granted")
    transitions.ensure_stages(root, workflow_id)
    return show(root, workflow_id)


def list_workflows(root: Path) -> dict[str, Any]:
    root = root.resolve(); directory = root / ".tailtrail" / "workflows"
    rows: list[dict[str, Any]] = []
    if directory.is_dir():
        for item in sorted(directory.iterdir()):
            if not item.is_dir() or not item.name.startswith("ttw-"):
                continue
            result, issue = _optional(lambda item=item: show(root, item.name))
            rows.append({"workflow_id": item.name, "status": result.get("status") if result else "blocked", "workflow_status": result.get("workflow_status") if result else "unknown", "lifecycle_state": result.get("lifecycle_state") if result else "unknown", "issue": issue})
    return {"type": "tailtrail-workflow-list", "workflows": rows, "boundary": "Read-only local product surface. It does not resume or execute workflows."}


def show(root: Path, workflow_id: str) -> dict[str, Any]:
    """Return a compact canonical state view; this has no execution effects."""
    root = root.resolve(); binding = ownership.show(root, workflow_id)
    ownership_check = ownership.validate(root, workflow_id)
    replay, replay_issue = _optional(lambda: storage.replay(root, workflow_id))
    projection = replay.get("last_valid_projection", {}) if replay else {}
    requirements = _requirements(root, binding)
    current = requirements[0] if requirements else {}
    scope, scope_issue = _optional(lambda: task_scope.freshness(root, workflow_id))
    reservation, reservation_issue = _optional(lambda: task_scope.lock_show(root))
    capability, capability_issue = _optional(lambda: capabilities.validate(root, workflow_id))
    evidence_state, evidence_issue = _optional(lambda: evidence.show(root, workflow_id))
    blocked: list[str] = []
    if not ownership_check["valid"]: blocked.extend(ownership_check["issues"])
    if replay_issue: blocked.append(replay_issue)
    elif not replay.get("valid", False): blocked.extend(replay.get("issues", []))
    scope_missing = scope and any("does not exist" in str(item) for item in scope.get("issues", []))
    capability_missing = capability and any("does not exist" in str(item) for item in capability.get("issues", []))
    if scope and not scope.get("fresh", False) and not scope_missing:
        blocked.extend(scope.get("issues", [])); blocked.extend(str(item.get("reason")) for item in scope.get("stale_requirements", []))
    elif scope_issue and "does not exist" not in scope_issue:
        blocked.append(scope_issue)
    lifecycle_state = projection.get("lifecycle_state", "unknown")
    workflow_status = projection.get("workflow_status", "draft")
    status = "blocked" if blocked else workflow_status
    stage_states = projection.get("stages", {})
    current_stage = projection.get("current_stage_id")
    current_stage = current_stage or next((stage_id for stage_id, row in stage_states.items() if row.get("status") in {"ready", "running", "stale", "blocked"}), None)
    current_stage = current_stage or next((stage_id for stage_id, row in stage_states.items() if row.get("status") == "pending"), "not-executing")
    compiled, _compiled_issue = _optional(lambda: compiler.show(root, workflow_id))
    display_names = {str(row["stage_id"]): str(row.get("display_name", row["stage_id"])) for row in (compiled or {}).get("stages", [])}
    return {
        "type": "tailtrail-workflow-state-view", "workflow_id": workflow_id,
        "tailtrail_run_id": binding["tailtrail_run_id"], "status": status,
        "lifecycle_state": lifecycle_state, "workflow_status": workflow_status,
        "canonical_run": {"planning_lock_ref": binding["planning_lock_ref"], "approved_anchor_ref": binding["approved_anchor_ref"], "requirement_matrix_ref": binding["requirement_matrix_ref"]},
        "requirements": [{"requirement_uid": row.get("requirement_uid"), "statement": row.get("statement", "")} for row in requirements],
        "current_requirement": {"requirement_uid": current.get("requirement_uid"), "statement": current.get("statement", "")} if current else None,
        "current_stage": current_stage, "current_stage_display": display_names.get(current_stage, current_stage), "stage_states": stage_states,
        "parent_workflow_id": projection.get("parent_workflow_id"),
        "successor_workflow_id": projection.get("successor_workflow_id"),
        "evidence_refs": (evidence_state or {}).get("artifact_refs", projection.get("artifact_refs", {})),
        "workflow_evidence": {"status": "not-collected" if evidence_issue and "does not exist" in evidence_issue else ("available" if evidence_state else "unavailable"), "stale_stage_ids": [str(row.get("stage_id")) for row in (evidence_state or {}).get("stages", []) if row.get("status") == "stale"], "issue": evidence_issue},
        "blocked_or_stale_reasons": blocked,
        "capability_plan": {"status": "not-declared" if capability_missing else (capability.get("status") if capability else "not-declared"), "issue": capability_issue},
        "scope": {"status": "not-captured" if scope_missing else (scope.get("status") if scope else "not-captured"), "issue": scope_issue},
        "reservation": {"status": reservation.get("state", reservation.get("status")) if reservation else "unavailable", "workflow_id": reservation.get("workflow_id") if reservation else None, "issue": reservation_issue},
        "boundary": "Read-only lifecycle status. It grants no stage execution, source/test/scanner/Git/provider/shell action, recovery, or completion authority.",
    }


def pause(root: Path, workflow_id: str) -> dict[str, Any]:
    current = show(root, workflow_id)
    if current["status"] == "blocked": raise ValueError("cannot pause a blocked workflow state")
    if current["workflow_status"] not in {"ready", "running"}: raise ValueError("only a ready or running workflow may be paused")
    transitions.workflow(root, workflow_id, "paused", "workflow-paused")
    approvals.expire_session(root.resolve(), workflow_id, None, "workflow-paused")
    return show(root, workflow_id)


def resume(root: Path, workflow_id: str) -> dict[str, Any]:
    current = show(root, workflow_id)
    if current["status"] == "blocked": raise ValueError("cannot resume a blocked workflow state")
    if current["workflow_status"] != "paused": raise ValueError("only a paused workflow may be resumed")
    transitions.workflow(root, workflow_id, "ready", "workflow-resumed")
    return show(root, workflow_id)


def cancel(root: Path, workflow_id: str, confirmed: bool) -> dict[str, Any]:
    if not confirmed: raise ValueError("cancellation requires --confirmed; it does not revert any project change")
    transitions.ensure_stages(root.resolve(), workflow_id)
    current = show(root, workflow_id)
    if current["workflow_status"] == "cancelled": return current
    if current["workflow_status"] in {"completed", "superseded"}: raise ValueError("a terminal completed or superseded workflow cannot be cancelled")
    for stage_id, stage_state in current.get("stage_states", {}).items():
        if stage_state.get("status") not in {"passed", "skipped", "cancelled"}:
            transitions.stage(root, workflow_id, stage_id, "cancelled", "stage-cancelled")
    transitions.workflow(root, workflow_id, "cancelled", "workflow-cancelled")
    released, release_issue = _optional(lambda: task_scope.release(root.resolve(), workflow_id, "workflow-cancelled"))
    result = show(root, workflow_id)
    result["reservation_release"] = released or {"status": "not-released", "issue": release_issue}
    return result


def replay(root: Path, workflow_id: str) -> dict[str, Any]:
    return storage.replay(root.resolve(), workflow_id)


def events(root: Path, workflow_id: str) -> dict[str, Any]:
    return storage.events(root.resolve(), workflow_id)


def transition(root: Path, workflow_id: str, next_state: str, reason_code: str) -> dict[str, Any]:
    transitions.workflow(root.resolve(), workflow_id, next_state, reason_code)
    return show(root, workflow_id)


def transition_stage(root: Path, workflow_id: str, stage_id: str, next_state: str, reason_code: str, approval_id: str | None = None) -> dict[str, Any]:
    transitions.stage(root.resolve(), workflow_id, stage_id, next_state, reason_code, approval_id)
    return show(root, workflow_id)


def follow_up(root: Path, parent_workflow_id: str, run_id: str, workflow_id: str | None = None) -> dict[str, Any]:
    """Create a separately approved workflow linked to a completed parent."""
    root = root.resolve(); parent = show(root, parent_workflow_id)
    if parent["workflow_status"] != "completed":
        raise ValueError("follow-up-created requires a completed parent workflow")
    child = create(root, run_id, workflow_id)
    child_id = str(child["workflow_id"])
    storage.append_event(root, child_id, "workflow-follow-up-linked", {
        "parent_workflow_id": parent_workflow_id, "reason_code": "follow-up-created",
    })
    storage.append_event(root, parent_workflow_id, "workflow-successor-linked", {
        "successor_workflow_id": child_id, "reason_code": "follow-up-created",
    })
    return show(root, child_id)


def supersede(root: Path, workflow_id: str, successor_workflow_id: str) -> dict[str, Any]:
    root = root.resolve()
    if workflow_id == successor_workflow_id: raise ValueError("a workflow cannot supersede itself")
    show(root, successor_workflow_id)
    transitions.workflow(root, workflow_id, "superseded", "workflow-superseded")
    storage.append_event(root, workflow_id, "workflow-successor-linked", {
        "successor_workflow_id": successor_workflow_id, "reason_code": "workflow-superseded",
    })
    storage.append_event(root, successor_workflow_id, "workflow-follow-up-linked", {
        "parent_workflow_id": workflow_id, "reason_code": "workflow-superseded",
    })
    return show(root, workflow_id)


def doctor(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); workflow, issue = _optional(lambda: show(root, workflow_id))
    categories: list[str] = []
    if issue: categories.append("corruption")
    if workflow:
        reasons = " ".join(workflow.get("blocked_or_stale_reasons", [])).lower()
        if any(word in reasons for word in ("journal", "hash", "sequence", "projection")): categories.append("corruption")
        if "stale" in reasons or workflow.get("workflow_evidence", {}).get("stale_stage_ids") or any(row.get("status") == "stale" for row in workflow.get("stage_states", {}).values()): categories.append("stale-evidence")
        if "authority" in reasons or workflow.get("workflow_status") == "awaiting_approval": categories.append("missing-authority")
        projection = storage.status(root, workflow_id).get("last_valid_projection", {})
        if "external" in reasons or projection.get("workflow_reason_code") == "external-dependency": categories.append("external-dependency")
        if workflow.get("workflow_status") in {"completed", "cancelled", "superseded"}: categories.append("terminal-state")
        if workflow.get("status") == "blocked" and not categories: categories.append("contract-or-freshness-block")
    return {
        "type": "tailtrail-workflow-doctor", "workflow_id": workflow_id,
        "status": "healthy" if workflow and workflow["status"] not in {"blocked", "failed"} and not categories else "blocked",
        "classifications": categories, "state": workflow, "issues": [] if workflow else [issue],
        "next": "Read the classification and canonical artifacts; doctor does not repair journals, clear state, retry commands, or run recovery.",
        "boundary": "Read-only diagnosis only. No source, test, scanner, Git, provider, shell, retry, or recovery operation occurs.",
    }
