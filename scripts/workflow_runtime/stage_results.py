"""PM-1 canonical, immutable results for durable workflow stages."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workflow_runtime import compiler, contracts, ownership, task_scope


LEDGER = ownership.LEDGER


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _stage(root: Path, workflow_id: str, stage_id: str) -> dict[str, Any]:
    plan = compiler.show(root, workflow_id)
    row = next((item for item in plan.get("stages", []) if item.get("stage_id") == stage_id), None)
    if row is None:
        raise ValueError(f"canonical stage result cannot resolve stage `{stage_id}`")
    return row


def _scope_freshness(root: Path, workflow_id: str) -> dict[str, Any]:
    try:
        value = task_scope.freshness(root, workflow_id)
    except ValueError:
        return {"status": "not-required", "scope_fingerprint": None}
    return {
        "status": "fresh" if value.get("fresh") else "stale",
        "scope_fingerprint": value.get("scope_fingerprint") or value.get("approved_scope_fingerprint"),
    }


def _transition(value: dict[str, Any] | None) -> dict[str, str] | None:
    if value is None:
        return None
    event = value.get("event") if isinstance(value.get("event"), dict) else value
    payload = event.get("payload", {}) if isinstance(event, dict) else {}
    required = ("event_id", "event_hash", "event_type")
    if not isinstance(event, dict) or any(not event.get(key) for key in required):
        raise ValueError("canonical transition result requires the exact durable event")
    if not payload.get("from_state") or not payload.get("to_state"):
        raise ValueError("canonical transition result requires from_state and to_state")
    return {key: str(event[key]) for key in required} | {
        "from_state": str(payload["from_state"]), "to_state": str(payload["to_state"])
    }


def record(
    root: Path,
    workflow_id: str,
    stage_id: str,
    *,
    outcome: str,
    reason_code: str,
    idempotency_key: str,
    transition_event: dict[str, Any] | None,
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Record exactly one transition or explicit non-transition result."""
    root = root.resolve()
    ownership_check = ownership.validate(root, workflow_id)
    if not ownership_check["valid"]:
        raise ValueError("canonical stage result requires valid ownership: " + "; ".join(ownership_check["issues"]))
    if not idempotency_key.startswith("wfidem-"):
        raise ValueError("canonical stage result requires a workflow idempotency key")
    binding = ownership.show(root, workflow_id)
    stage = _stage(root, workflow_id, stage_id)
    transition = _transition(transition_event)
    result_kind = "transition" if transition else "non-transition"
    result_id = "wfsr-" + _digest(f"{workflow_id}:{stage_id}:{idempotency_key}:{result_kind}")[:20]
    destination = ownership.binding_path(root, workflow_id).parent / "stage-results" / stage_id / f"{result_id}.json"
    payload = {
        "schema_version": "1", "type": "tailtrail-workflow-stage-result",
        "result_id": result_id, "workflow_id": workflow_id,
        "tailtrail_run_id": binding["tailtrail_run_id"], "stage_id": stage_id,
        "capability_id": stage["capability_id"], "requirement_uids": binding["requirement_uids"],
        "result_kind": result_kind, "outcome": outcome, "reason_code": reason_code,
        "idempotency_key": idempotency_key, "freshness": _scope_freshness(root, workflow_id),
        "transition": transition, "evidence_refs": sorted(set(evidence_refs or [])),
        "recorded_at": datetime.now(UTC).isoformat(),
        "boundary": "Canonical stage outcome only. A transition points to the exact append-only durable event; a non-transition explicitly records why state did not move.",
    }
    contracts.require_valid(payload)
    with LEDGER.RunLock(destination.parent / ".stage-result.lock"):
        if destination.is_file():
            prior = json.loads(destination.read_text(encoding="utf-8"))
            comparable = {key: value for key, value in payload.items() if key != "recorded_at"}
            prior_comparable = {key: value for key, value in prior.items() if key != "recorded_at"}
            if prior_comparable != comparable:
                raise ValueError("idempotency key is already bound to a different stage result")
            return {"artifact": _relative(root, destination), **prior, "record_status": "duplicate-suppressed"}
        LEDGER.atomic_json(destination, payload)
    LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_stage_result_recorded", {
        "workflow_id": workflow_id, "stage_id": stage_id, "result_id": result_id,
        "result_kind": result_kind, "outcome": outcome, "artifact": _relative(root, destination),
    })
    return {"artifact": _relative(root, destination), **payload, "record_status": "recorded"}


def show(root: Path, workflow_id: str, stage_id: str) -> dict[str, Any]:
    directory = ownership.binding_path(root.resolve(), workflow_id).parent / "stage-results" / stage_id
    rows = []
    for path in sorted(directory.glob("wfsr-*.json")) if directory.is_dir() else []:
        rows.append({"artifact": _relative(root.resolve(), path), **json.loads(path.read_text(encoding="utf-8"))})
    return {"type": "tailtrail-workflow-stage-results", "workflow_id": workflow_id, "stage_id": stage_id,
            "results": rows, "boundary": "Read-only canonical stage-result projection; no transition or capability is invoked."}
