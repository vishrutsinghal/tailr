"""Prepare and record typed Deferred Phase 4 capability-adapter exchanges."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workflow_runtime import adapter_catalog, approvals, compiler, contracts, ownership, task_scope


LEDGER = ownership.LEDGER


def _digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _safe_id(value: str, label: str) -> str:
    if not value or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for char in value.lower()):
        raise ValueError(f"{label} contains unsupported characters")
    return value


def _dir(root: Path, workflow_id: str) -> Path:
    return ownership.binding_path(root.resolve(), workflow_id).parent / "adapters"


def input_path(root: Path, workflow_id: str, stage_id: str) -> Path:
    return _dir(root, workflow_id) / f"{_safe_id(stage_id, 'stage-id')}-input-v1.json"


def output_path(root: Path, workflow_id: str, stage_id: str) -> Path:
    return _dir(root, workflow_id) / f"{_safe_id(stage_id, 'stage-id')}-output-v1.json"


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _registry() -> dict[str, dict[str, Any]]:
    value = json.loads((ownership.ROOT / "tailtrail-registry.json").read_text(encoding="utf-8"))
    return {str(item["id"]): item for item in value.get("features", []) if isinstance(item, dict) and item.get("id")}


def catalog() -> dict[str, Any]:
    registered = _registry(); rows = adapter_catalog.list_all(); issues: list[str] = []
    for row in rows:
        feature = registered.get(row["capability_id"])
        if feature is None: issues.append(f"{row['adapter_id']}: unregistered capability `{row['capability_id']}`")
        elif feature.get("status") != "implemented": issues.append(f"{row['adapter_id']}: capability is not implemented")
    return {"type": "tailtrail-workflow-adapter-catalog", "schema_version": "1", "valid": not issues, "status": "valid" if not issues else "blocked", "adapters": rows, "issues": issues, "boundary": "Catalog inspection is read-only and grants no capability execution authority."}


def contract(adapter_id: str) -> dict[str, Any]:
    row = adapter_catalog.get(adapter_id); registered = _registry(); feature = registered.get(row["capability_id"])
    if feature is None or feature.get("status") != "implemented": raise ValueError(f"adapter capability `{row['capability_id']}` is unavailable")
    return {"schema_version": "1", "type": "tailtrail-workflow-adapter-contract", **row,
            "registered_commands": list(feature.get("commands", [])), "registered_scripts": list(feature.get("scripts", [])),
            "boundary": "This typed contract references existing TailTrail entry points; it neither copies business logic nor constructs or executes a shell command."}


def _context(root: Path, workflow_id: str, stage_id: str, adapter_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    binding = ownership.show(root, workflow_id); ownership_check = ownership.validate(root, workflow_id)
    if not ownership_check["valid"]: raise ValueError("adapter requires valid canonical ownership: " + "; ".join(ownership_check["issues"]))
    plan_check = compiler.validate(root, workflow_id)
    if not plan_check["valid"]: raise ValueError("adapter requires a valid frozen compiler plan: " + "; ".join(plan_check["issues"]))
    plan = compiler.show(root, workflow_id); stage = next((item for item in plan["stages"] if item.get("stage_id") == stage_id), None)
    if stage is None: raise ValueError(f"adapter stage `{stage_id}` is not in the frozen compiler graph")
    definition = contract(adapter_id)
    if stage.get("capability_id") != definition["capability_id"] or stage.get("adapter_id") != adapter_id or stage.get("adapter_action_class") != definition["action_class"]:
        raise ValueError(f"adapter `{adapter_id}` maps to `{definition['capability_id']}`, not stage capability `{stage.get('capability_id')}`")
    return binding, plan, stage, definition


def _requirements(root: Path, binding: dict[str, Any]) -> list[dict[str, Any]]:
    rows = ownership._read_ref(root, str(binding["requirement_matrix_ref"]))
    return [{"requirement_uid": row["requirement_uid"], "statement": row.get("statement", ""), "preserve_rules": list(row.get("preserve_rules", [])), "likely_paths": list(row.get("likely_paths", [])), "evidence_plan": list(row.get("evidence_plan", []))} for row in rows]


def prepare(root: Path, workflow_id: str, stage_id: str, adapter_id: str, approval_id: str | None = None) -> dict[str, Any]:
    root = root.resolve(); binding, plan, stage, definition = _context(root, workflow_id, stage_id, adapter_id)
    freshness = task_scope.freshness(root, workflow_id)
    if not freshness["valid"] or not freshness["fresh"]: raise ValueError("adapter inputs are stale or invalid")
    if stage_id.startswith("d-"):
        from workflow_runtime import freshness as operational_freshness
        operational = operational_freshness.assess(root, workflow_id)
        if operational["status"] == "stale" and stage_id in operational["affected_stage_ids"]:
            raise ValueError("debug workflow evidence is stale for this stage; apply freshness classification and resume through correction before another experiment")
    if stage.get("approval_class") != "none" or definition["action_class"] in adapter_catalog.GUARDED_ACTIONS:
        approval = approvals.authorize_stage(root, workflow_id, stage_id, approval_id)
        if approval is None:
            raise ValueError("adapter stage requires exact scoped approval")
        if definition["action_class"] in adapter_catalog.GUARDED_ACTIONS and definition["action_class"] not in approval.get("action_classes", []):
            raise ValueError(f"approval does not cover adapter action class `{definition['action_class']}`")
    requirements = _requirements(root, binding); stable = {"workflow_id": workflow_id, "revision": plan["revision"], "plan_fingerprint": plan["plan_fingerprint"], "stage_id": stage_id, "adapter_id": adapter_id, "capability_id": definition["capability_id"], "action_class": definition["action_class"], "requirement_uids": [row["requirement_uid"] for row in requirements], "scope_fingerprint": task_scope.show(root, workflow_id)["scope_fingerprint"]}
    key = "wfidem-" + _digest(stable).removeprefix("sha256:")[:24]
    destination = input_path(root, workflow_id, stage_id)
    if destination.is_file():
        prior = json.loads(destination.read_text(encoding="utf-8"))
        if prior.get("idempotency_key") != key: raise ValueError("existing adapter input belongs to a different frozen dispatch")
        return {"artifact": _relative(root, destination), **prior, "dispatch_status": "already-prepared"}
    payload = {"schema_version": "1", "type": "tailtrail-workflow-adapter-input", **stable, "authority": definition["authority"], "idempotency_key": key, "approval_id": approval_id, "approved_anchor_ref": binding["approved_anchor_ref"], "scope_ref": task_scope.show(root, workflow_id)["artifact"], "requirements": requirements, "input_refs": [binding["approved_anchor_ref"], task_scope.show(root, workflow_id)["artifact"], plan["artifact"]], "evidence_requirements": list(stage.get("evidence", [])), "freshness": "fresh", "retry": {"max_attempts": definition["max_retries"] + 1, "automatic_retry": definition["max_retries"] > 0}, "timeout_seconds": definition["timeout_seconds"], "status": "prepared", "boundary": "Typed handoff only. The host or existing capability owns execution; this adapter does not run commands, mutate project files, scan, publish, or infer evidence."}
    contracts.require_valid(payload); LEDGER.atomic_json(destination, payload)
    LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_adapter_prepared", {"workflow_id": workflow_id, "stage_id": stage_id, "adapter_id": adapter_id, "capability_id": definition["capability_id"], "idempotency_key": key, "artifact": _relative(root, destination)})
    return {"artifact": _relative(root, destination), **payload, "dispatch_status": "prepared"}


def _validate_result(definition: dict[str, Any], value: dict[str, Any]) -> None:
    if value.get("outcome") not in adapter_catalog.OUTCOMES:
        raise ValueError("adapter result must include a supported categorical outcome")
    missing = [key for key in definition["required_outputs"] if key not in value]
    if missing: raise ValueError("adapter result is missing typed fields: " + ", ".join(missing))
    if definition["adapter_id"] == "clarification-aidlc":
        mode = value.get("aidlc_mode")
        if mode not in {"lite", "standard", "full"}: raise ValueError("AIDLC adapter mode must be lite, standard, or full")
        if mode in {"standard", "full"} and value.get("authority_source") != "official-aidlc-pack": raise ValueError("Standard/Full AIDLC results must come from the official AIDLC authority")
    if definition["adapter_id"] == "graph-discovery" and value.get("evidence_label") == "proof": raise ValueError("heuristic graph evidence cannot be labelled as proof")
    if definition["adapter_id"] == "focused-testing" and not str(value.get("exact_command", "")).strip(): raise ValueError("focused test result must record the exact host-visible command")


def record(root: Path, workflow_id: str, stage_id: str, adapter_id: str, result_ref: str) -> dict[str, Any]:
    root = root.resolve(); binding, _, _, definition = _context(root, workflow_id, stage_id, adapter_id)
    prepared_path = input_path(root, workflow_id, stage_id)
    if not prepared_path.is_file(): raise ValueError("prepare the adapter input before recording a result")
    prepared = json.loads(prepared_path.read_text(encoding="utf-8")); supplied = ownership._read_ref(root, result_ref)
    if not isinstance(supplied, dict): raise ValueError("adapter result source must contain one JSON object")
    _validate_result(definition, supplied)
    outcome = supplied.get("outcome", supplied.get("status"))
    if outcome not in adapter_catalog.OUTCOMES: raise ValueError("adapter result has an unsupported categorical outcome")
    destination = output_path(root, workflow_id, stage_id)
    if destination.is_file():
        prior = json.loads(destination.read_text(encoding="utf-8"))
        if prior.get("idempotency_key") == prepared["idempotency_key"]: return {"artifact": _relative(root, destination), **prior, "record_status": "duplicate-suppressed"}
        raise ValueError("adapter output already exists for a different dispatch")
    payload = {"schema_version": "1", "type": "tailtrail-workflow-adapter-output", "workflow_id": workflow_id, "stage_id": stage_id, "adapter_id": adapter_id, "capability_id": definition["capability_id"], "action_class": definition["action_class"], "authority": definition["authority"], "idempotency_key": prepared["idempotency_key"], "requirement_uids": prepared["requirement_uids"], "outcome": outcome, "result": supplied, "evidence_refs": sorted({str(value) for key, value in supplied.items() if key.endswith("_ref") and isinstance(value, str)} | {str(value) for key, values in supplied.items() if key.endswith("_refs") and isinstance(values, list) for value in values if isinstance(value, str)}), "recorded_at": datetime.now(UTC).isoformat(), "boundary": "Factual typed result only. Raw command output and source bodies are prohibited; recording does not apply fixes, retry a guarded action, publish, deploy, or weaken proof requirements."}
    contracts.require_valid(payload); LEDGER.atomic_json(destination, payload)
    LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_adapter_result_recorded", {"workflow_id": workflow_id, "stage_id": stage_id, "adapter_id": adapter_id, "capability_id": definition["capability_id"], "idempotency_key": prepared["idempotency_key"], "outcome": outcome, "artifact": _relative(root, destination)})
    return {"artifact": _relative(root, destination), **payload, "record_status": "recorded"}


def show(root: Path, workflow_id: str, stage_id: str) -> dict[str, Any]:
    root = root.resolve(); result: dict[str, Any] = {"type": "tailtrail-workflow-adapter-status", "workflow_id": workflow_id, "stage_id": stage_id, "input": None, "output": None}
    for key, path in (("input", input_path(root, workflow_id, stage_id)), ("output", output_path(root, workflow_id, stage_id))):
        if path.is_file(): result[key] = {"artifact": _relative(root, path), **json.loads(path.read_text(encoding="utf-8"))}
    result["status"] = "recorded" if result["output"] else ("prepared" if result["input"] else "not-prepared")
    result["boundary"] = "Read-only adapter status; no capability is invoked."
    return result


def validate(root: Path, workflow_id: str, stage_id: str) -> dict[str, Any]:
    issues: list[str] = []
    try:
        current = show(root.resolve(), workflow_id, stage_id)
        if current["input"] is None: issues.append("adapter input is missing")
        else: issues.extend(contracts.validate_artifact({key: value for key, value in current["input"].items() if key not in {"artifact", "dispatch_status"}}))
        if current["output"] is not None:
            output = {key: value for key, value in current["output"].items() if key not in {"artifact", "record_status"}}
            issues.extend(contracts.validate_artifact(output)); definition = contract(str(output.get("adapter_id", "")))
            _validate_result(definition, output.get("result", {}))
            if current["input"] and output.get("idempotency_key") != current["input"].get("idempotency_key"): issues.append("adapter output idempotency key differs from its input")
    except (OSError, ValueError, json.JSONDecodeError) as error: issues.append(str(error))
    return {"type": "tailtrail-workflow-adapter-validation", "workflow_id": workflow_id, "stage_id": stage_id, "valid": not issues, "status": "valid" if not issues else "blocked", "issues": issues, "boundary": "Validation is read-only and does not repair, dispatch, retry, or approve an adapter."}
