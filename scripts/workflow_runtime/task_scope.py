"""DWR-C task-scoped identity, reservation locking, and freshness checks.

This module never runs a declared workflow stage.  It records only a scoped
fingerprint and an exclusive reservation for a future code-changing runtime.
Freshness is based on approved paths and anchors, never repository dirtiness.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from workflow_runtime import capabilities, ownership


LEDGER = ownership.LEDGER


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _safe_path(root: Path, value: str) -> Path:
    candidate = Path(value)
    if not value or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("scope paths must be safe repository-relative paths")
    resolved = (root.resolve() / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("scope path escapes repository root") from error
    return resolved


def _path_state(root: Path, relative: str) -> dict[str, str]:
    path = _safe_path(root, relative)
    if not path.is_file():
        return {"path": relative, "state": "missing", "fingerprint": "missing"}
    return {"path": relative, "state": "present", "fingerprint": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()}


def _scope_path(root: Path, workflow_id: str) -> Path:
    return ownership.binding_path(root, workflow_id).parent / "scope-v1.json"


def _lock_path(root: Path) -> Path:
    return root.resolve() / ".tailtrail" / "workflow-active-code-change-v1.json"


def _anchor_rows(root: Path, binding: dict[str, Any]) -> list[dict[str, Any]]:
    rows = ownership._read_ref(root, str(binding["requirement_matrix_ref"]))
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("bound requirement matrix is invalid")
    return rows


def _record(root: Path, binding: dict[str, Any], row: dict[str, Any], index: int) -> dict[str, Any]:
    requirement_uid = str(row.get("requirement_uid", ""))
    if not requirement_uid:
        raise ValueError("bound requirement matrix is missing requirement_uid")
    paths = sorted({str(path) for path in row.get("likely_paths", []) if isinstance(path, str) and path})
    states = [_path_state(root, path) for path in paths]
    payload = {
        "requirement_uid": requirement_uid,
        "statement": str(row.get("statement", "")),
        "paths": states,
        "context_anchors": [{"type": "requirement", "value": requirement_uid}],
        "evidence_refs": [f"{binding['approved_anchor_ref']}#/requirements/{index}"],
    }
    return {**payload, "scope_fingerprint": _digest(payload)}


def initialize(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve()
    ownership_check = ownership.validate(root, workflow_id)
    if not ownership_check["valid"]:
        raise ValueError("DWR-C requires a valid DWR-A binding: " + "; ".join(ownership_check["issues"]))
    capability_check = capabilities.validate(root, workflow_id)
    if not capability_check["valid"]:
        raise ValueError("DWR-C requires a valid DWR-B capability plan: " + "; ".join(capability_check["issues"]))
    destination = _scope_path(root, workflow_id)
    if destination.exists():
        raise ValueError("DWR-C scope already exists; later phases own scope amendments")
    binding = ownership.show(root, workflow_id)
    records = [_record(root, binding, row, index) for index, row in enumerate(_anchor_rows(root, binding))]
    payload = {
        "schema_version": "1", "type": "tailtrail-workflow-task-scope", "workflow_id": workflow_id,
        "tailtrail_run_id": binding["tailtrail_run_id"], "ownership_ref": binding["artifact"],
        "approved_anchor_ref": binding["approved_anchor_ref"],
        "target_identity_fingerprint": binding["target_identity_fingerprint"],
        "requirements": records, "state": "captured",
        "boundary": "DWR-C fingerprints only approved requirement scope. Unrelated repository dirtiness is not a freshness signal.",
    }
    payload["scope_fingerprint"] = _digest(payload)
    LEDGER.atomic_json(destination, payload)
    LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_scope_captured", {"workflow_id": workflow_id, "artifact": _relative(root, destination), "requirement_uids": [record["requirement_uid"] for record in records], "scope_fingerprint": payload["scope_fingerprint"]})
    return {"artifact": _relative(root, destination), **payload}


def show(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); path = _scope_path(root, workflow_id)
    if not path.is_file():
        raise ValueError(f"DWR-C task scope does not exist for `{workflow_id}`")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "tailtrail-workflow-task-scope" or payload.get("workflow_id") != workflow_id:
        raise ValueError("DWR-C task scope is invalid")
    return {"artifact": _relative(root, path), **payload}


def freshness(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); issues: list[str] = []; stale: list[dict[str, Any]] = []
    try:
        binding = ownership.show(root, workflow_id)
        ownership_check = ownership.validate(root, workflow_id)
        if not ownership_check["valid"]:
            issues.extend(ownership_check["issues"])
        capability_check = capabilities.validate(root, workflow_id)
        if not capability_check["valid"]:
            issues.extend(capability_check["issues"])
        scope = show(root, workflow_id)
        expected_scope = {key: value for key, value in scope.items() if key not in {"artifact", "scope_fingerprint"}}
        if scope.get("scope_fingerprint") != _digest(expected_scope):
            issues.append("task scope fingerprint differs from its declared contents")
        if scope.get("tailtrail_run_id") != binding.get("tailtrail_run_id") or scope.get("ownership_ref") != binding.get("artifact"):
            issues.append("task scope does not match the canonical workflow binding")
        if scope.get("approved_anchor_ref") != binding.get("approved_anchor_ref") or scope.get("target_identity_fingerprint") != binding.get("target_identity_fingerprint"):
            issues.append("task scope is not bound to the current approved anchor and target identity")
        for record in scope.get("requirements", []):
            if not isinstance(record, dict):
                issues.append("task scope contains an invalid requirement record")
                continue
            expected_record = {key: value for key, value in record.items() if key != "scope_fingerprint"}
            if record.get("scope_fingerprint") != _digest(expected_record):
                issues.append(f"scope record `{record.get('requirement_uid', 'unknown')}` was modified")
                continue
            current_paths = [_path_state(root, str(item.get("path", ""))) for item in record.get("paths", []) if isinstance(item, dict)]
            if current_paths != record.get("paths"):
                stale.append({"requirement_uid": record.get("requirement_uid"), "reason": "approved scoped path fingerprint changed", "expected": record.get("paths"), "current": current_paths})
        if stale:
            checkpoint = ownership.binding_path(root, workflow_id).parent / "operational-checkpoint-v1.json"
            if checkpoint.is_file():
                saved = json.loads(checkpoint.read_text(encoding="utf-8")); snapshot = saved.get("snapshot", {})
                expected = {**snapshot.get("scoped_sources", {}), **snapshot.get("scoped_docs", {})}
                current = {item["path"]: item["fingerprint"] for row in scope.get("requirements", []) for item in [_path_state(root, str(path.get("path", ""))) for path in row.get("paths", []) if isinstance(path, dict)]}
                if expected == current: stale = []
    except (OSError, ValueError, json.JSONDecodeError) as error:
        issues.append(str(error))
    state = "blocked" if issues else ("stale" if stale else "fresh")
    return {"type": "tailtrail-workflow-freshness", "workflow_id": workflow_id, "valid": not issues, "fresh": not issues and not stale, "status": state, "issues": issues, "stale_requirements": stale, "boundary": "Approved scope remains immutable; a versioned Phase 6 operational checkpoint may recognize factual in-scope progress. Git dirtiness outside scope is not a freshness signal."}


def acquire(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); current = freshness(root, workflow_id)
    if not current["valid"] or not current["fresh"]:
        raise ValueError("DWR-C cannot reserve code-changing work until scope is valid and fresh: " + "; ".join(current["issues"] + [str(item.get("reason")) for item in current["stale_requirements"]]))
    destination = _lock_path(root)
    if destination.is_file():
        existing = json.loads(destination.read_text(encoding="utf-8"))
        if existing.get("state") == "active" and existing.get("workflow_id") != workflow_id:
            raise ValueError(f"code-changing workflow reservation is already held by `{existing.get('workflow_id', 'unknown')}`; use read-only status or diagnosis. DWR-C never deletes or replaces this reservation")
        if existing.get("state") == "active":
            return {"artifact": _relative(root, destination), **existing, "status": "already-held"}
    scope = show(root, workflow_id)
    payload = {
        "schema_version": "1", "type": "tailtrail-workflow-code-change-reservation", "workflow_id": workflow_id,
        "tailtrail_run_id": scope["tailtrail_run_id"], "scope_ref": scope["artifact"],
        "scope_fingerprint": scope["scope_fingerprint"], "target_identity_fingerprint": scope["target_identity_fingerprint"],
        "state": "active", "boundary": "Reservation only. It grants no execution, retry, recovery, deletion, or source-edit authority.",
    }
    LEDGER.atomic_json(destination, payload)
    LEDGER.append_event(root, scope["tailtrail_run_id"], "workflow_code_change_lock_acquired", {"workflow_id": workflow_id, "artifact": _relative(root, destination), "scope_fingerprint": scope["scope_fingerprint"]})
    return {"artifact": _relative(root, destination), **payload}


def release(root: Path, workflow_id: str, reason: str = "workflow-cancelled") -> dict[str, Any]:
    """Release only this workflow's reservation after cancellation or verified completion."""
    if reason not in {"workflow-cancelled", "workflow-completed"}: raise ValueError("reservation release reason is unsupported")
    root = root.resolve(); path = _lock_path(root)
    if not path.is_file():
        return {"type": "tailtrail-workflow-code-change-reservation", "status": "unheld", "artifact": None}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("workflow_id") != workflow_id:
        raise ValueError("cannot release a reservation owned by another workflow")
    if payload.get("state") == "released":
        return {"artifact": _relative(root, path), **payload, "status": "already-released"}
    payload["state"] = "released"
    payload["release_reason"] = reason
    payload["boundary"] = "Released after explicit cancellation or evidence-complete template completion. This metadata action did not revert or retry project work."
    LEDGER.atomic_json(path, payload)
    binding = ownership.show(root, workflow_id)
    LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_code_change_lock_released", {"workflow_id": workflow_id, "artifact": _relative(root, path), "reason": reason})
    return {"artifact": _relative(root, path), **payload}


def lock_show(root: Path) -> dict[str, Any]:
    root = root.resolve(); path = _lock_path(root)
    if not path.is_file():
        return {"type": "tailtrail-workflow-code-change-reservation", "status": "unheld", "artifact": None, "boundary": "Read-only status only."}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {"artifact": _relative(root, path), **payload}


def diagnose(root: Path, workflow_id: str) -> dict[str, Any]:
    """Read-only stale-lock diagnosis. It does not delete, release, or retry."""
    root = root.resolve(); current = freshness(root, workflow_id); reservation = lock_show(root)
    held_by_other = reservation.get("artifact") is not None and reservation.get("workflow_id") != workflow_id
    if held_by_other:
        reason = "another workflow holds the code-changing reservation"
    elif not current["valid"]:
        reason = "canonical binding or declared capability plan is invalid"
    elif not current["fresh"]:
        reason = "approved scoped state changed"
    else:
        reason = "no stale condition detected"
    return {"type": "tailtrail-workflow-stale-diagnosis", "workflow_id": workflow_id, "status": "blocked" if held_by_other or not current["valid"] else ("stale" if not current["fresh"] else "fresh"), "reason": reason, "freshness": current, "reservation": reservation, "next": "Keep the reservation intact and use the canonical correction/recovery flow when it exists; DWR-C does not delete locks or retry project actions.", "boundary": "Read-only diagnosis only. No lock deletion, source mutation, command retry, or recovery action occurs."}
