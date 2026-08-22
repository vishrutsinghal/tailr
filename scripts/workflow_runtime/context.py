"""Deferred Phase 7 context and linked-token telemetry bridge.

This module stores compact, sanitized workflow-local receipts.  It never
compresses source/history itself, calls a provider, or converts estimates into
measured usage.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workflow_runtime import compiler, contracts, ownership

LEDGER = ownership.LEDGER
EXACTNESS = {"must-be-exact", "structured-lossless", "categorical-summary"}
REDUCTION = {"not-requested", "reduced", "unavailable", "not-applicable"}
FORBIDDEN = {"prompt", "source", "log", "secret", "credential", "customer", "user", "repository"}


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _safe_ref(value: str) -> bool:
    return contracts.safe_relative(value) and value.startswith(".tailtrail/")


def _safe_text(value: str) -> bool:
    return len(value) <= 160 and not any(word in value.lower() for word in FORBIDDEN)


def _directory(root: Path, workflow_id: str, kind: str) -> Path:
    return ownership.binding_path(root.resolve(), workflow_id).parent / kind


def receipt_path(root: Path, workflow_id: str, stage_id: str) -> Path:
    return _directory(root, workflow_id, "context") / f"{stage_id}-receipt-v1.json"


def telemetry_path(root: Path, workflow_id: str, stage_id: str) -> Path:
    return _directory(root, workflow_id, "telemetry") / f"{stage_id}-usage-v1.json"


def _stage(root: Path, workflow_id: str, stage_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    binding = ownership.show(root.resolve(), workflow_id)
    stage = next((row for row in compiler.show(root.resolve(), workflow_id)["stages"] if row["stage_id"] == stage_id), None)
    if stage is None:
        raise ValueError("context receipt references a stage outside the frozen compiler plan")
    return binding, stage


def record(root: Path, workflow_id: str, stage_id: str, budget_tokens: int, selected_refs: list[str],
           exactness: str, reduction_status: str, retrieval_refs: list[str]) -> dict[str, Any]:
    root = root.resolve(); binding, _ = _stage(root, workflow_id, stage_id)
    if budget_tokens < 0 or isinstance(budget_tokens, bool): raise ValueError("context budget must be a non-negative integer")
    if exactness not in EXACTNESS or reduction_status not in REDUCTION: raise ValueError("unsupported exactness or reduction status")
    refs = sorted(set(selected_refs)); retrieval = sorted(set(retrieval_refs))
    if not refs or any(not _safe_ref(ref) for ref in [*refs, *retrieval]): raise ValueError("context references must be safe .tailtrail references")
    payload = {"schema_version":"1", "type":"tailtrail-workflow-context-receipt", "workflow_id":workflow_id,
               "stage_id":stage_id, "selected_refs":refs, "avoided_categories":["raw-prompt", "source-body", "raw-log", "identity", "secret"],
               "exactness":exactness, "token_posture":"estimated", "context_budget_tokens":budget_tokens,
               "reduction_status":reduction_status, "retrieval_refs":retrieval,
               "receipt_fingerprint":"", "boundary":"Estimated context posture only. Resume retrieves compact references; this receipt contains no prompt, source, log, identity, or provider usage."}
    payload["receipt_fingerprint"] = _hash({key:value for key, value in payload.items() if key != "receipt_fingerprint"})
    contracts.require_valid(payload); path = receipt_path(root, workflow_id, stage_id)
    if path.is_file() and json.loads(path.read_text()).get("receipt_fingerprint") == payload["receipt_fingerprint"]:
        return {"artifact":_relative(root, path), **payload, "reused":True}
    LEDGER.atomic_json(path, payload)
    LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_context_recorded", {"workflow_id":workflow_id, "stage_id":stage_id, "artifact":_relative(root,path), "token_posture":"estimated"})
    return {"artifact":_relative(root, path), **payload, "reused":False}


def record_telemetry(root: Path, workflow_id: str, stage_id: str, source_ref: str) -> dict[str, Any]:
    """Accept one pre-existing host/provider telemetry object only when fully linked."""
    root = root.resolve(); binding, _ = _stage(root, workflow_id, stage_id)
    if not _safe_ref(source_ref): raise ValueError("telemetry source must be a safe .tailtrail reference")
    source = ownership._read_ref(root, source_ref)
    if not isinstance(source, dict): raise ValueError("telemetry source must contain one JSON object")
    required = {"workflow_id", "tailtrail_run_id", "stage_id", "provider", "usage"}
    if not required <= set(source): raise ValueError("measured telemetry must link workflow_id, tailtrail_run_id, stage_id, provider, and usage")
    if source["workflow_id"] != workflow_id or source["tailtrail_run_id"] != binding["tailtrail_run_id"] or source["stage_id"] != stage_id:
        raise ValueError("measured telemetry linkage does not match this workflow/run/stage")
    usage = source["usage"]
    if not isinstance(usage, dict) or not isinstance(usage.get("total_tokens"), int) or isinstance(usage["total_tokens"], bool) or usage["total_tokens"] < 0:
        raise ValueError("measured telemetry usage must include a non-negative integer total_tokens")
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in usage.values()): raise ValueError("measured telemetry usage values must be non-negative integers")
    if any(not _safe_text(str(value)) for key, value in source.items() if key not in {"workflow_id", "tailtrail_run_id", "stage_id", "provider", "usage"}): raise ValueError("telemetry contains unsupported unsanitized fields")
    stable = {"workflow_id":workflow_id,"tailtrail_run_id":binding["tailtrail_run_id"],"stage_id":stage_id,"provider":str(source["provider"]),"usage":usage,"source_ref":source_ref}
    payload = {"schema_version":"1","type":"tailtrail-workflow-token-telemetry","measured":True,**stable,"telemetry_fingerprint":_hash(stable),"recorded_at":datetime.now(UTC).isoformat(),"boundary":"Measured label is allowed only for this linked host/provider telemetry receipt. No baseline, savings, prompt, source, log, identity, or secret is stored."}
    contracts.require_valid(payload); path = telemetry_path(root, workflow_id, stage_id)
    if path.is_file() and json.loads(path.read_text()).get("telemetry_fingerprint") == payload["telemetry_fingerprint"]: return {"artifact":_relative(root,path),**payload,"reused":True}
    LEDGER.atomic_json(path,payload); LEDGER.append_event(root,binding["tailtrail_run_id"],"workflow_token_telemetry_recorded",{"workflow_id":workflow_id,"stage_id":stage_id,"artifact":_relative(root,path),"token_posture":"measured"})
    return {"artifact":_relative(root,path),**payload,"reused":False}


def resume_summary(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); compiler.show(root, workflow_id)
    rows: list[dict[str, Any]] = []
    for stage in compiler.show(root, workflow_id)["stages"]:
        path = receipt_path(root, workflow_id, stage["stage_id"])
        if path.is_file():
            receipt = json.loads(path.read_text()); rows.append({"stage_id":stage["stage_id"],"artifact":_relative(root,path),"selected_refs":receipt["selected_refs"],"retrieval_refs":receipt.get("retrieval_refs",[]),"exactness":receipt["exactness"],"reduction_status":receipt.get("reduction_status"),"token_posture":"measured" if telemetry_path(root,workflow_id,stage["stage_id"]).is_file() else "estimated"})
    return {"type":"tailtrail-workflow-resume-context","workflow_id":workflow_id,"stages":rows,"boundary":"Resume uses these compact receipts and retrieval references only; it does not replay prompt history, source bodies, or raw logs."}
