"""Route failed Phase 6 stages to bounded correction or preserved-state Recovery/Replan."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from workflow_runtime import adapters, compiler, contracts, evidence, freshness, ownership, retry, storage, task_scope


LEDGER = ownership.LEDGER
RECOVERY_CLASSIFICATIONS = {"ambiguous", "regressed", "new-drift", "needs-decision", "scope-conflict", "same-hunk-overlap"}


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _directory(root: Path, workflow_id: str) -> Path:
    return ownership.binding_path(root.resolve(), workflow_id).parent / "corrections"


def _latest(directory: Path, pattern: str) -> Path | None:
    rows = sorted(directory.glob(pattern)) if directory.is_dir() else []
    return rows[-1] if rows else None


def _ref(root: Path, path: Path | None) -> dict[str, str] | None:
    if path is None or not path.is_file(): return None
    return {"ref":_relative(root, path),"hash":"sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()}


def _recovery_context(root: Path, workflow_id: str) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    binding = ownership.show(root, workflow_id); run_dir = LEDGER.state_dir(root, binding["tailtrail_run_id"]); reconciliation = _latest(run_dir / "recovery" / "reconciliation", "assessment-*.json")
    value = json.loads(reconciliation.read_text(encoding="utf-8")) if reconciliation else None
    candidates = [ownership.binding_path(root, workflow_id), task_scope._scope_path(root, workflow_id), compiler.plan_path(root, workflow_id), evidence.evidence_path(root, workflow_id), retry.path(root, workflow_id), freshness.checkpoint_path(root, workflow_id), ownership.binding_path(root, workflow_id).parent / "template-execution-v1.json", run_dir / "recovery" / "boundary.json", reconciliation]
    return value, [item for item in (_ref(root, path) for path in candidates) if item]


def _classification(root: Path, workflow_id: str, stage_id: str, supplied: str | None) -> str:
    if supplied: return supplied
    output = (adapters.show(root, workflow_id, stage_id).get("output") or {}).get("result", {})
    value = str(output.get("classification", output.get("drift", "actionable")))
    return value if value in RECOVERY_CLASSIFICATIONS | {"actionable","improved","unchanged"} else "actionable"


def _history(root: Path, workflow_id: str) -> list[dict[str, Any]]:
    directory = _directory(root, workflow_id)
    rows = []
    for path in sorted(directory.glob("packet-*.json")) if directory.is_dir() else []:
        value = json.loads(path.read_text(encoding="utf-8")); rows.append({"artifact":_relative(root, path), **value})
    return rows


def show(root: Path, workflow_id: str) -> dict[str, Any]:
    rows = _history(root.resolve(), workflow_id)
    return {"type":"tailtrail-workflow-correction-history","workflow_id":workflow_id,"packets":rows,"latest":rows[-1] if rows else None,"boundary":"Read-only correction/recovery history. No action is applied."}


def route(root: Path, workflow_id: str, stage_id: str, classification: str | None = None, max_cycles: int = 2) -> dict[str, Any]:
    root = root.resolve()
    if max_cycles < 1: raise ValueError("max correction cycles must be at least one")
    plan = compiler.show(root, workflow_id); stage = next((row for row in plan["stages"] if row["stage_id"] == stage_id), None)
    if stage is None: raise ValueError("correction stage is outside the frozen graph")
    projection = storage.status(root, workflow_id)["last_valid_projection"]; current = projection.get("stages", {}).get(stage_id, {}).get("status")
    if current not in {"failed","blocked","stale"}: raise ValueError("correction requires a failed, blocked, or stale stage")
    binding = ownership.show(root, workflow_id); category = _classification(root, workflow_id, stage_id, classification); reconciliation, preservation = _recovery_context(root, workflow_id)
    attempts = retry.show(root, workflow_id)["attempts"]
    latest_attempt = next((row for row in reversed(attempts) if row["stage_id"] == stage_id and row["status"] == "completed"), None)
    stable = {"workflow_id":workflow_id,"plan_fingerprint":plan["plan_fingerprint"],"stage_id":stage_id,"requirement_uids":binding["requirement_uids"],"classification":category,"adapter_id":stage["adapter_id"],"attempt":(latest_attempt or {}).get("attempt"),"result_hash":(latest_attempt or {}).get("result_hash")}; fingerprint = _hash(stable)
    history = [row for row in _history(root, workflow_id) if row["stage_id"] == stage_id]
    duplicate = next((row for row in reversed(history) if row["failure_fingerprint"] == fingerprint), None)
    if duplicate: return {"route_status":"duplicate-suppressed", **duplicate}
    cycle = len(history) + 1
    conflict = str((reconciliation or {}).get("classification", "none")); force_recovery = category in RECOVERY_CLASSIFICATIONS or conflict in RECOVERY_CLASSIFICATIONS or cycle > 1
    exhausted = cycle > max_cycles; status = "needs-decision" if exhausted else "recovery-replan" if force_recovery else "correction-ready"
    retry_decision = retry.decide(root, workflow_id, stage_id)
    passed = [item for item,row in projection.get("stages", {}).items() if row.get("status") == "passed"]
    packet = {"schema_version":"1","type":"tailtrail-workflow-correction-packet","workflow_id":workflow_id,"tailtrail_run_id":binding["tailtrail_run_id"],"stage_id":stage_id,"requirement_uids":binding["requirement_uids"],"failure_fingerprint":fingerprint,"cycle":cycle,"max_cycles":max_cycles,"classification":category,"status":status,"retry":retry_decision,"preserved_passed_stage_ids":passed,"preservation_refs":preservation,"reconciliation":{"classification":conflict,"decision":(reconciliation or {}).get("decision"),"safe_to_apply":bool((reconciliation or {}).get("safe_to_apply", False))},"next_action":"prepare one typed low-risk retry" if retry_decision["eligible"] and not force_recovery else "use one bounded requirement-scoped correction and record fresh evidence" if status == "correction-ready" else "resume Navigator/AIDLC against the same approved anchor and preserved evidence" if status == "recovery-replan" else "request the smallest explicit decision; do not guess or overwrite work","boundary":"Control-plane packet only. It preserves evidence and existing recovery classifications; it does not edit source, retry a command, apply Git recovery, clear history, or mutate the approved anchor."}
    contracts.require_valid(packet); directory = _directory(root, workflow_id); artifact = directory / f"packet-{len(_history(root, workflow_id)) + 1}.json"; LEDGER.atomic_json(artifact, packet)
    event = "workflow_recovery_replan_routed" if status in {"recovery-replan","needs-decision"} else "workflow_correction_packet_created"
    LEDGER.append_event(root, binding["tailtrail_run_id"], event, {"workflow_id":workflow_id,"stage_id":stage_id,"artifact":_relative(root, artifact),"failure_fingerprint":fingerprint,"cycle":cycle,"status":status})
    return {"artifact":_relative(root, artifact), **packet}
