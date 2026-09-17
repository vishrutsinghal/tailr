"""Durable TailTrail conversation attachment, stop, and exact resume control.

Attachment state is deliberately separate from Planning Lock and workflow
state.  The service writes only bounded TailTrail metadata and never advances,
approves, rejects, executes, or repairs a run.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow_runtime import approvals, ownership, state as workflow_state, task_scope, transitions


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
BOUNDARY = (
    "Conversation-routing metadata only. This record grants no planning, "
    "approval, implementation, execution, retry, recovery, or closure authority."
)


def _module(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {filename}")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


LEDGER = ownership.LEDGER
LOCK = _module("tailtrail_session_planning_lock", "planning_lock.py")
TARGET = _module("tailtrail_session_target", "target_workspace.py")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _context_value(context_key: str | None = None) -> str:
    return context_key or os.environ.get("TAILTRAIL_CONTEXT_KEY") or "workspace-default"


def context_hash(context_key: str | None = None) -> str:
    return "sha256:" + hashlib.sha256(_context_value(context_key).encode("utf-8")).hexdigest()


def attachment_path(root: Path, context_key: str | None = None) -> Path:
    root = root.resolve()
    digest = context_hash(context_key).removeprefix("sha256:")
    return root / ".tailtrail" / "session-attachments" / f"{digest}.json"


def _safe_run_id(run_id: str) -> str:
    if not RUN_ID.fullmatch(run_id) or Path(run_id).name != run_id:
        raise ValueError("run ID must be one safe local identifier")
    return run_id


def _fingerprint_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key != "fingerprint"}


def validate(record: dict[str, Any], *, expected_context_hash: str | None = None) -> list[str]:
    required = {
        "schema_version", "type", "target_workspace_identity_fingerprint", "context_key_hash",
        "state", "run_id", "workflow_id", "canonical_run_status", "last_logical_point",
        "saved_artifact_refs", "temporary_approvals", "reservation_release", "reason_code",
        "generation", "previous_record_fingerprint", "fingerprint", "created_at", "updated_at", "boundary",
    }
    issues = [f"missing `{key}`" for key in sorted(required - set(record))]
    if record.get("schema_version") != "1" or record.get("type") != "tailtrail-session-attachment":
        issues.append("attachment type or schema version is invalid")
    if record.get("state") not in {"attached", "stop-pending", "detached", "resume-check"}:
        issues.append("attachment state is invalid")
    if not isinstance(record.get("generation"), int) or int(record.get("generation", 0)) < 1:
        issues.append("attachment generation must be a positive integer")
    run_id = record.get("run_id")
    if run_id is not None and (not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id)):
        issues.append("attachment run ID is invalid")
    supplied_context = record.get("context_key_hash")
    if expected_context_hash and supplied_context != expected_context_hash:
        issues.append("attachment context does not match this client context")
    if not isinstance(supplied_context, str) or not re.fullmatch(r"sha256:[a-f0-9]{64}", supplied_context):
        issues.append("attachment context hash is invalid")
    expected = _digest(_fingerprint_payload(record))
    if record.get("fingerprint") != expected:
        issues.append("attachment fingerprint is invalid")
    if record.get("boundary") != BOUNDARY:
        issues.append("attachment authority boundary is invalid")
    return issues


def read(root: Path, context_key: str | None = None) -> dict[str, Any] | None:
    path = attachment_path(root, context_key)
    if not path.is_file():
        return None
    if path.is_symlink():
        raise ValueError("session attachment must not be a symlink")
    record = json.loads(path.read_text(encoding="utf-8"))
    issues = validate(record, expected_context_hash=context_hash(context_key))
    if issues:
        raise ValueError("invalid session attachment: " + "; ".join(issues))
    return record


def _write(root: Path, record: dict[str, Any], context_key: str | None = None) -> dict[str, Any]:
    record["fingerprint"] = _digest(_fingerprint_payload(record))
    issues = validate(record, expected_context_hash=context_hash(context_key))
    if issues:
        raise ValueError("refusing invalid session attachment: " + "; ".join(issues))
    LEDGER.atomic_json(attachment_path(root, context_key), record)
    return record


def _lock(root: Path, run_id: str) -> dict[str, Any]:
    return LOCK.show(root.resolve(), _safe_run_id(run_id))


def _workflow_id(root: Path, run_id: str) -> str | None:
    workflow_id = ownership.suggested_id(run_id)
    return workflow_id if ownership.binding_path(root.resolve(), workflow_id).is_file() else None


def _run_integrity_issues(root: Path, run_id: str) -> list[str]:
    events = LEDGER.read_events(LEDGER.state_dir(root.resolve(), run_id) / "events.jsonl")
    return [issue for index, event in enumerate(events, 1) for issue in LEDGER.validate_event(event, index)]


def _artifact_refs(root: Path, run_id: str) -> list[str]:
    directory = LEDGER.state_dir(root.resolve(), run_id)
    candidates = (
        directory / "planning" / "lock-v1.json",
        directory / "planning" / "start-report-v1.json",
        directory / "anchors" / "approved-v1.json",
    )
    return [path.relative_to(root.resolve()).as_posix() for path in candidates if path.is_file()]


def _logical_point(lock: dict[str, Any], workflow: dict[str, Any] | None = None) -> str:
    if workflow:
        stage = workflow.get("current_stage")
        return f"workflow-{workflow.get('workflow_status', 'unknown')}" + (f":{stage}" if stage else "")
    status = str(lock.get("status", "unknown"))
    return "planning-lock-awaiting-approval" if status == "awaiting-approval" else f"planning-lock-{status}"


def _base_record(
    root: Path,
    run_id: str,
    state: str,
    reason_code: str,
    previous: dict[str, Any] | None,
    context_key: str | None,
    *,
    workflow: dict[str, Any] | None = None,
    approvals_status: str = "none",
    reservation_status: str = "not-held",
) -> dict[str, Any]:
    lock = _lock(root, run_id)
    now = _now()
    return {
        "schema_version": "1",
        "type": "tailtrail-session-attachment",
        "target_workspace_identity_fingerprint": (lock.get("target_identity") or {}).get("fingerprint"),
        "context_key_hash": context_hash(context_key),
        "state": state,
        "run_id": run_id,
        "workflow_id": _workflow_id(root, run_id),
        "canonical_run_status": str(lock.get("status", "unknown")),
        "last_logical_point": _logical_point(lock, workflow),
        "saved_artifact_refs": _artifact_refs(root, run_id),
        "temporary_approvals": approvals_status,
        "reservation_release": reservation_status,
        "reason_code": reason_code,
        "generation": int((previous or {}).get("generation", 0)) + 1,
        "previous_record_fingerprint": (previous or {}).get("fingerprint"),
        "fingerprint": "",
        "created_at": (previous or {}).get("created_at", now),
        "updated_at": now,
        "boundary": BOUNDARY,
    }


def attach(root: Path, run_id: str, context_key: str | None = None, reason_code: str = "tailtrail-start") -> dict[str, Any]:
    root = root.resolve(); run_id = _safe_run_id(run_id); _lock(root, run_id)
    previous = read(root, context_key)
    if previous and previous.get("state") == "attached" and previous.get("run_id") == run_id:
        return previous
    record = _base_record(root, run_id, "attached", reason_code, previous, context_key)
    saved = _write(root, record, context_key)
    LEDGER.append_event(root, run_id, "tailtrail_session_attached", {
        "context_key_hash": saved["context_key_hash"], "generation": saved["generation"],
        "reason_code": reason_code, "fingerprint": saved["fingerprint"],
    })
    return saved


def _legacy_single_run(root: Path) -> str | None:
    directory = root.resolve() / ".tailtrail" / "runs"
    if not directory.is_dir():
        return None
    candidates: list[str] = []
    for item in sorted(directory.iterdir()):
        if not item.is_dir() or not RUN_ID.fullmatch(item.name):
            continue
        try:
            status = str(LOCK.show(root.resolve(), item.name).get("status", ""))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if status in {"awaiting-approval", "approved"}:
            candidates.append(item.name)
    if len(candidates) > 1:
        raise ValueError("multiple TailTrail runs are eligible; provide --run-id: " + ", ".join(candidates))
    return candidates[0] if candidates else None


def _pause_workflow(root: Path, workflow_id: str) -> tuple[dict[str, Any] | None, str, str]:
    current = workflow_state.show(root, workflow_id)
    workflow_status = str(current.get("workflow_status", "unknown"))
    approvals_status = "none"
    reservation_status = "not-held"
    if workflow_status == "running":
        stage_id = current.get("current_stage")
        stage_row = (current.get("stage_states") or {}).get(stage_id, {}) if stage_id else {}
        if stage_id and stage_row.get("status") == "running":
            transitions.stage(root, workflow_id, str(stage_id), "stale", "user-stop-before-result")
        current = workflow_state.pause(root, workflow_id)
        approvals_status = "expired"
    elif workflow_status == "ready":
        current = workflow_state.pause(root, workflow_id)
        approvals_status = "expired"
    elif workflow_status == "paused":
        expired = approvals.expire_session(root, workflow_id, None, "tailtrail-stop")
        approvals_status = "expired" if expired.get("expired", 0) else "none"
    if workflow_status in {"ready", "running", "paused"}:
        released = task_scope.release(root, workflow_id, "user-stop")
        reservation_status = str(released.get("status", released.get("state", "released")))
        if reservation_status == "unheld":
            reservation_status = "not-held"
    return current, approvals_status, reservation_status


def stop(root: Path, run_id: str | None = None, context_key: str | None = None) -> dict[str, Any]:
    root = root.resolve(); previous = read(root, context_key)
    if previous and previous.get("state") == "detached" and (run_id is None or previous.get("run_id") == run_id):
        return _stop_result(previous, idempotent=True)
    selected = _safe_run_id(run_id) if run_id else (
        str(previous.get("run_id")) if previous and previous.get("run_id") else _legacy_single_run(root)
    )
    if not selected:
        return {
            "type": "tailtrail-stop-result", "state": "detached", "run_id": None,
            "idempotent": True, "report": _render_no_run_stop(),
            "boundary": BOUNDARY,
        }
    lock = _lock(root, selected)
    pending = _base_record(root, selected, "stop-pending", "user-stop-requested", previous, context_key)
    pending = _write(root, pending, context_key)
    LEDGER.append_event(root, selected, "tailtrail_stop_requested", {
        "context_key_hash": pending["context_key_hash"], "generation": pending["generation"],
        "canonical_run_status": lock.get("status"),
    })
    workflow_id = _workflow_id(root, selected)
    workflow = None; approvals_status = "none"; reservation_status = "not-held"
    if workflow_id:
        workflow, approvals_status, reservation_status = _pause_workflow(root, workflow_id)
    detached = _base_record(
        root, selected, "detached", "user-stop-complete", pending, context_key,
        workflow=workflow, approvals_status=approvals_status, reservation_status=reservation_status,
    )
    detached = _write(root, detached, context_key)
    LEDGER.append_event(root, selected, "tailtrail_session_detached", {
        "context_key_hash": detached["context_key_hash"], "generation": detached["generation"],
        "logical_point": detached["last_logical_point"], "fingerprint": detached["fingerprint"],
        "temporary_approvals": approvals_status, "reservation_release": reservation_status,
    })
    return _stop_result(detached, idempotent=False)


def _render_no_run_stop() -> str:
    return (
        "# TailTrail Stopped\n\n"
        "- Run ID: `none`\n"
        "- Saved at: `no-attached-run`\n"
        "- Canonical run: none\n"
        "- Workflow: not activated\n"
        "- Temporary approvals: none\n"
        "- Code-change reservation: not held\n"
        "- TailTrail routing: detached\n"
        "- Regular agent mode: active\n"
        "- Resume: start a new run with `tailtrail start <goal>`\n"
    )


def _stop_result(record: dict[str, Any], *, idempotent: bool) -> dict[str, Any]:
    workflow = "paused" if record.get("workflow_id") and "paused" in str(record.get("last_logical_point")) else ("preserved" if record.get("workflow_id") else "not activated")
    run_id = str(record.get("run_id"))
    report = (
        "# TailTrail Stopped\n\n"
        f"- Run ID: `{run_id}`\n"
        f"- Saved at: `{record.get('last_logical_point')}`\n"
        f"- Canonical run: preserved (`{record.get('canonical_run_status')}`)\n"
        f"- Workflow: {workflow}\n"
        f"- Temporary approvals: {record.get('temporary_approvals')}\n"
        f"- Code-change reservation: {str(record.get('reservation_release')).replace('-', ' ')}\n"
        "- TailTrail routing: detached\n"
        "- Regular agent mode: active\n"
        f"- Resume: `tailtrail resume --run-id {run_id}`\n"
    )
    return {"type": "tailtrail-stop-result", "state": "detached", "run_id": run_id, "idempotent": idempotent, "attachment": record, "report": report, "boundary": BOUNDARY}


def resume(root: Path, run_id: str, context_key: str | None = None) -> dict[str, Any]:
    root = root.resolve(); run_id = _safe_run_id(run_id); lock = _lock(root, run_id)
    previous = read(root, context_key)
    if previous and previous.get("state") == "attached" and previous.get("run_id") == run_id:
        return _resume_result(previous, "resumed-awaiting-approval" if lock.get("status") == "awaiting-approval" else "resumed-attached", idempotent=True)
    checking = _base_record(root, run_id, "resume-check", "explicit-exact-run-resume", previous, context_key)
    checking = _write(root, checking, context_key)
    ledger_issues = _run_integrity_issues(root, run_id)
    if ledger_issues:
        blocked = _base_record(root, run_id, "detached", "resume-integrity-invalid", checking, context_key)
        blocked = _write(root, blocked, context_key)
        LEDGER.append_event(root, run_id, "tailtrail_resume_blocked", {
            "context_key_hash": blocked["context_key_hash"], "generation": blocked["generation"],
            "reason_code": "resume-integrity-invalid", "fingerprint": blocked["fingerprint"],
        })
        return _resume_result(blocked, "resume-invalid", idempotent=False, issue="; ".join(ledger_issues))
    identity = TARGET.verify_identity(lock.get("target_identity", {}), root)
    if identity.get("blocking"):
        blocked = _base_record(root, run_id, "detached", "resume-target-stale", checking, context_key)
        blocked = _write(root, blocked, context_key)
        LEDGER.append_event(root, run_id, "tailtrail_resume_blocked", {
            "context_key_hash": blocked["context_key_hash"], "generation": blocked["generation"],
            "reason_code": "resume-target-stale", "fingerprint": blocked["fingerprint"],
        })
        return _resume_result(blocked, "resume-stale", idempotent=False, issue=str(identity.get("reason")))
    workflow_id = _workflow_id(root, run_id)
    workflow = workflow_state.show(root, workflow_id) if workflow_id else None
    if workflow and workflow.get("status") == "blocked":
        blocked = _base_record(root, run_id, "detached", "resume-workflow-stale", checking, context_key, workflow=workflow)
        blocked = _write(root, blocked, context_key)
        LEDGER.append_event(root, run_id, "tailtrail_resume_blocked", {
            "context_key_hash": blocked["context_key_hash"], "generation": blocked["generation"],
            "reason_code": "resume-workflow-stale", "fingerprint": blocked["fingerprint"],
        })
        reasons = "; ".join(str(item) for item in workflow.get("blocked_or_stale_reasons", [])) or "workflow freshness is blocked"
        return _resume_result(blocked, "resume-stale", idempotent=False, issue=reasons)
    reservation = task_scope.lock_show(root)
    if reservation.get("state") == "active" and reservation.get("workflow_id") not in {None, workflow_id}:
        blocked = _base_record(root, run_id, "detached", "resume-reservation-conflict", checking, context_key, workflow=workflow)
        blocked = _write(root, blocked, context_key)
        LEDGER.append_event(root, run_id, "tailtrail_resume_blocked", {
            "context_key_hash": blocked["context_key_hash"], "generation": blocked["generation"],
            "reason_code": "resume-reservation-conflict", "fingerprint": blocked["fingerprint"],
        })
        return _resume_result(blocked, "resume-conflict", idempotent=False, issue=f"reservation is held by `{reservation.get('workflow_id')}`")
    if str(lock.get("status")) not in {"awaiting-approval", "approved"}:
        terminal = _base_record(root, run_id, "detached", "resume-terminal", checking, context_key, workflow=workflow)
        terminal = _write(root, terminal, context_key)
        return _resume_result(terminal, "resume-terminal", idempotent=False)
    resumed = _base_record(root, run_id, "attached", "explicit-exact-run-resume", checking, context_key, workflow=workflow)
    resumed = _write(root, resumed, context_key)
    LEDGER.append_event(root, run_id, "tailtrail_session_resumed", {
        "context_key_hash": resumed["context_key_hash"], "generation": resumed["generation"],
        "logical_point": resumed["last_logical_point"], "fingerprint": resumed["fingerprint"],
    })
    outcome = "resumed-paused-workflow" if workflow and workflow.get("workflow_status") == "paused" else ("resumed-awaiting-approval" if lock.get("status") == "awaiting-approval" else "resumed-approved-run")
    return _resume_result(resumed, outcome, idempotent=False)


def _resume_result(record: dict[str, Any], outcome: str, *, idempotent: bool, issue: str | None = None) -> dict[str, Any]:
    run_id = str(record.get("run_id")); attached = record.get("state") == "attached"
    report = (
        "# TailTrail Resume Report\n\n"
        f"- Run ID: `{run_id}`\n"
        f"- Outcome: `{outcome}`\n"
        f"- Saved at: `{record.get('last_logical_point')}`\n"
        f"- Canonical run: `{record.get('canonical_run_status')}`\n"
        f"- TailTrail routing: {'attached' if attached else 'detached'}\n"
        "- Temporary approvals: expired approvals remain expired\n"
        "- Execution advanced: no\n"
        + (f"- Issue: {issue}\n" if issue else "")
        + ("- Next: review the saved run state and choose its next explicit action.\n" if attached else "- Next: resolve the reported condition or start a new run.\n")
    )
    return {"type": "tailtrail-resume-result", "state": outcome, "run_id": run_id, "idempotent": idempotent, "attachment": record, "report": report, "boundary": BOUNDARY}


def status(root: Path, context_key: str | None = None) -> dict[str, Any]:
    record = read(root.resolve(), context_key)
    if not record:
        return {"type": "tailtrail-session-status", "state": "none", "run_id": None, "attachment": None, "boundary": BOUNDARY}
    return {"type": "tailtrail-session-status", "state": record["state"], "run_id": record.get("run_id"), "attachment": record, "boundary": BOUNDARY}


def attached_run(root: Path, context_key: str | None = None) -> str | None:
    record = read(root.resolve(), context_key)
    return str(record["run_id"]) if record and record.get("state") == "attached" and record.get("run_id") else None


def require_generation(root: Path, expected_generation: int, context_key: str | None = None) -> dict[str, Any]:
    """Reject late host results produced under an older attachment generation."""
    record = read(root.resolve(), context_key)
    if not record or record.get("state") != "attached":
        raise ValueError("TailTrail session is not attached; late result cannot mutate the run")
    if record.get("generation") != expected_generation:
        raise ValueError("TailTrail attachment generation changed; late result is stale")
    return record
