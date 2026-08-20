"""DWR-minus append-only workflow storage proof.

The journal stores only local artifact references and SHA-256 hashes. It never
persists source, prompts, command text, or raw execution output. A projection is
written atomically after each durable journal append; if that second step is
interrupted, the last projection stays readable and validation fails closed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from workflow_runtime import contracts, ownership, projection as projector


LEDGER = ownership.LEDGER
EVENT_TYPE = "tailtrail-workflow-storage-event"
ALLOWED_EVENTS = {
    "workflow-initialized", "artifact-snapshot-captured", "workflow-created",
    "workflow-awaiting-approval", "workflow-ready", "workflow-started", "workflow-paused",
    "workflow-resumed", "workflow-blocked", "workflow-failed", "workflow-cancelled",
    "workflow-superseded", "workflow-completed", "workflow-follow-up-linked",
    "workflow-successor-linked", "stage-registered", "stage-ready",
    "stage-awaiting-approval", "stage-started", "stage-passed", "stage-failed",
    "stage-blocked", "stage-skipped", "stage-stale", "stage-cancelled",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _workflow_dir(root: Path, workflow_id: str) -> Path:
    return ownership.binding_path(root.resolve(), workflow_id).parent


def journal_path(root: Path, workflow_id: str) -> Path:
    return _workflow_dir(root, workflow_id) / "journal-v1.jsonl"


def projection_path(root: Path, workflow_id: str) -> Path:
    return _workflow_dir(root, workflow_id) / "projection-v1.json"


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _read_projection(root: Path, workflow_id: str) -> dict[str, Any]:
    path = projection_path(root, workflow_id)
    if not path.is_file():
        raise ValueError(f"DWR-minus projection does not exist for `{workflow_id}`")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "tailtrail-workflow-projection" or payload.get("workflow_id") != workflow_id:
        raise ValueError("workflow projection is invalid")
    return payload


def _event_hash(event: dict[str, Any]) -> str:
    return _hash({key: value for key, value in event.items() if key != "event_hash"})


def _read_journal(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.is_file():
        return [], ["workflow journal is missing"]
    events: list[dict[str, Any]] = []; issues: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            issues.append(f"journal has a blank/interrupted line at {line_number}")
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            issues.append(f"journal has invalid JSON at line {line_number}")
            continue
        if not isinstance(payload, dict):
            issues.append(f"journal event at line {line_number} is not an object")
            continue
        events.append(payload)
    return events, issues


def _validate_events(events: list[dict[str, Any]], workflow_id: str, run_id: str) -> list[str]:
    issues: list[str] = []; previous: str | None = None
    for sequence, event in enumerate(events, start=1):
        if event.get("type") != EVENT_TYPE:
            issues.append(f"journal event {sequence} has an invalid type")
        if event.get("workflow_id") != workflow_id or event.get("tailtrail_run_id") != run_id:
            issues.append(f"journal event {sequence} belongs to another workflow or run")
        if event.get("sequence") != sequence:
            issues.append(f"journal sequence gap or duplicate at {sequence}")
        if event.get("event_type") not in ALLOWED_EVENTS:
            issues.append(f"journal event {sequence} has an unsupported event type")
        expected_id = "wfe-" + hashlib.sha256(f"{workflow_id}:{sequence}:{event.get('event_type')}".encode("utf-8")).hexdigest()[:16]
        if event.get("event_id") != expected_id:
            issues.append(f"journal event {sequence} has an invalid deterministic ID")
        if event.get("previous_event_hash") != previous:
            issues.append(f"journal event {sequence} previous hash does not match")
        if event.get("event_hash") != _event_hash(event):
            issues.append(f"journal event {sequence} hash does not match")
        previous = str(event.get("event_hash"))
    issues.extend(projector.semantic_issues(events))
    return issues


def _safe_artifact(root: Path, path: Path) -> tuple[str, str] | None:
    if not path.is_file():
        return None
    relative = _relative(root, path)
    if not relative.startswith(".tailtrail/"):
        raise ValueError("workflow storage may capture only local .tailtrail artifact references")
    return relative, _file_hash(path)


def _artifact_snapshot(root: Path, workflow_id: str, binding: dict[str, Any]) -> dict[str, dict[str, str]]:
    candidates = {
        "ownership": ownership.binding_path(root, workflow_id),
        "capability_plan": _workflow_dir(root, workflow_id) / "capability-plan-v1.json",
        "task_scope": _workflow_dir(root, workflow_id) / "scope-v1.json",
        "compiler_plan": _workflow_dir(root, workflow_id) / "compiler-plan-v1.json",
        "stage_approvals": _workflow_dir(root, workflow_id) / "stage-approvals-v1.json",
        "evidence": _workflow_dir(root, workflow_id) / "evidence-v1.json",
        "completion_receipt": _workflow_dir(root, workflow_id) / "completion-receipt-v1.json",
        "code_change_reservation": root / ".tailtrail" / "workflow-active-code-change-v1.json",
    }
    refs: dict[str, str] = {}; hashes: dict[str, str] = {}
    for name, path in candidates.items():
        item = _safe_artifact(root, path)
        if item is not None:
            refs[name], hashes[name] = item
    return {"artifact_refs": refs, "artifact_hashes": hashes}


def _append(root: Path, workflow_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if event_type not in ALLOWED_EVENTS:
        raise ValueError(f"unsupported DWR-minus event `{event_type}`")
    binding = ownership.show(root, workflow_id)
    path = journal_path(root, workflow_id); projection_file = projection_path(root, workflow_id)
    with LEDGER.RunLock(_workflow_dir(root, workflow_id) / ".storage.lock"):
        events, issues = _read_journal(path)
        if event_type == "workflow-initialized" and issues == ["workflow journal is missing"]:
            issues = []
        if issues:
            raise ValueError("cannot append to an invalid workflow journal: " + "; ".join(issues))
        event_issues = _validate_events(events, workflow_id, binding["tailtrail_run_id"])
        if event_issues:
            raise ValueError("cannot append to a corrupt workflow journal: " + "; ".join(event_issues))
        sequence = len(events) + 1; previous = events[-1]["event_hash"] if events else None
        event = {
            "schema_version": "1", "type": EVENT_TYPE, "workflow_id": workflow_id,
            "tailtrail_run_id": binding["tailtrail_run_id"], "sequence": sequence,
            "event_id": "wfe-" + hashlib.sha256(f"{workflow_id}:{sequence}:{event_type}".encode("utf-8")).hexdigest()[:16],
            "event_type": event_type, "previous_event_hash": previous, "payload": payload,
        }
        event["event_hash"] = _event_hash(event)
        contracts.require_valid(event)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical(event) + "\n"); handle.flush(); os.fsync(handle.fileno())
        projection = projector.replay(binding, [*events, event])
        contracts.require_valid(projection)
        LEDGER.atomic_json(projection_file, projection)
    return {"event": event, "projection": projection}


def initialize(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); valid = ownership.validate(root, workflow_id)
    if not valid["valid"]:
        raise ValueError("DWR-minus requires a valid DWR-A binding: " + "; ".join(valid["issues"]))
    if journal_path(root, workflow_id).exists() or projection_path(root, workflow_id).exists():
        raise ValueError("DWR-minus storage already exists; it is append-only and cannot be reinitialized")
    binding = ownership.show(root, workflow_id)
    result = _append(root, workflow_id, "workflow-initialized", {"ownership_ref": binding["artifact"], "ownership_hash": _file_hash(ownership.binding_path(root, workflow_id))})
    LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_storage_initialized", {"workflow_id": workflow_id, "journal": _relative(root, journal_path(root, workflow_id)), "projection": _relative(root, projection_path(root, workflow_id))})
    return {"journal": _relative(root, journal_path(root, workflow_id)), "projection": _relative(root, projection_path(root, workflow_id)), **result}


def capture(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); valid = ownership.validate(root, workflow_id)
    if not valid["valid"]:
        raise ValueError("DWR-minus requires a valid DWR-A binding: " + "; ".join(valid["issues"]))
    binding = ownership.show(root, workflow_id); snapshot = _artifact_snapshot(root, workflow_id, binding)
    result = _append(root, workflow_id, "artifact-snapshot-captured", snapshot)
    LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_storage_snapshot_captured", {"workflow_id": workflow_id, "artifact_refs": snapshot["artifact_refs"], "artifact_hashes": snapshot["artifact_hashes"]})
    return {"journal": _relative(root, journal_path(root, workflow_id)), "projection": _relative(root, projection_path(root, workflow_id)), **result}


def lifecycle(root: Path, workflow_id: str, event_type: str) -> dict[str, Any]:
    """Append one DWR-1 lifecycle event without invoking any workflow stage."""
    if event_type not in {"workflow-created", "workflow-paused", "workflow-resumed", "workflow-cancelled"}:
        raise ValueError("unsupported workflow lifecycle event")
    root = root.resolve()
    if not projection_path(root, workflow_id).is_file():
        raise ValueError("DWR-1 requires initialized DWR-minus storage")
    return _append(root, workflow_id, event_type, {"boundary": "Lifecycle control only; no source, test, scanner, Git, provider, publish, or shell action was invoked."})


def append_event(root: Path, workflow_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Append a sanitized state-machine event through the guarded journal."""
    return _append(root.resolve(), workflow_id, event_type, payload)


def events(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); binding = ownership.show(root, workflow_id)
    rows, issues = _read_journal(journal_path(root, workflow_id))
    issues.extend(_validate_events(rows, workflow_id, binding["tailtrail_run_id"]))
    return {"type": "tailtrail-workflow-events", "workflow_id": workflow_id,
            "valid": not issues, "status": "valid" if not issues else "blocked",
            "events": rows if not issues else [], "issues": issues,
            "boundary": "Read-only sanitized journal; no state is changed or repaired."}


def status(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); projection = _read_projection(root, workflow_id)
    return {"type": "tailtrail-workflow-storage-status", "workflow_id": workflow_id, "journal": _relative(root, journal_path(root, workflow_id)), "projection": _relative(root, projection_path(root, workflow_id)), "last_valid_projection": projection, "boundary": "Status reads the last atomic projection even if later journal data is corrupt."}


def replay(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); binding = ownership.show(root, workflow_id); events, issues = _read_journal(journal_path(root, workflow_id))
    issues.extend(_validate_events(events, workflow_id, binding["tailtrail_run_id"]))
    projection = projector.replay(binding, events) if not issues else None
    saved = _read_projection(root, workflow_id)
    if projection is not None and saved != projection:
        issues.append("saved projection does not match deterministic journal replay")
    return {"type": "tailtrail-workflow-storage-replay", "workflow_id": workflow_id, "valid": not issues, "status": "valid" if not issues else "blocked", "issues": issues, "replayed_projection": projection, "last_valid_projection": saved, "boundary": "Replay is read-only; it does not repair, truncate, delete, or rewrite journal/projection state."}


def validate(root: Path, workflow_id: str) -> dict[str, Any]:
    return replay(root, workflow_id)
