"""Issue bounded idempotent retry handoffs only for deterministic low-risk stages."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from workflow_runtime import adapter_catalog, adapters, compiler, contracts, evidence, ownership, storage, transitions


LEDGER = ownership.LEDGER
ELIGIBLE_ACTIONS = {"read_local", "write_tailtrail_state"}
PROHIBITED_ACTIONS = {"write_project", "execute_project", "scan_local", "external_provider", "publish"}


def path(root: Path, workflow_id: str) -> Path:
    return ownership.binding_path(root.resolve(), workflow_id).parent / "retry-attempts-v1.json"


def _relative(root: Path, value: Path) -> str:
    return value.resolve().relative_to(root.resolve()).as_posix()


def _hash(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def _context(root: Path, workflow_id: str, stage_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    plan = compiler.show(root.resolve(), workflow_id); stage = next((row for row in plan["stages"] if row["stage_id"] == stage_id), None)
    if stage is None: raise ValueError("retry references a stage outside the frozen graph")
    return plan, stage


def _empty(root: Path, workflow_id: str) -> dict[str, Any]:
    binding = ownership.show(root, workflow_id)
    return {"schema_version":"1","type":"tailtrail-workflow-retry-attempts","workflow_id":workflow_id,"tailtrail_run_id":binding["tailtrail_run_id"],"attempts":[],"boundary":"Attempt metadata and sanitized typed-result references only. No command, source write, scan, provider, publish, deploy, merge, or recovery action is executed."}


def show(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); destination = path(root, workflow_id); payload = json.loads(destination.read_text(encoding="utf-8")) if destination.is_file() else _empty(root, workflow_id)
    contracts.require_valid(payload)
    return {"artifact":_relative(root, destination) if destination.is_file() else None, **payload}


def _save(root: Path, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    contracts.require_valid(payload); destination = path(root, workflow_id); LEDGER.atomic_json(destination, payload)
    return {"artifact":_relative(root, destination), **payload}


def _operation(plan: dict[str, Any], stage: dict[str, Any]) -> str:
    stable = {"workflow_id":plan["workflow_id"],"revision":plan["revision"],"plan_fingerprint":plan["plan_fingerprint"],"stage_id":stage["stage_id"],"adapter_id":stage["adapter_id"],"action_class":stage["adapter_action_class"]}
    return "wfop-" + _hash(stable).removeprefix("sha256:")[:24]


def register_initial(root: Path, workflow_id: str, stage_id: str, approval_id: str | None, input_ref: str) -> dict[str, Any]:
    root = root.resolve(); plan, stage = _context(root, workflow_id, stage_id); payload = show(root, workflow_id); operation_id = _operation(plan, stage)
    prior = next((row for row in payload["attempts"] if row["operation_id"] == operation_id and row["attempt"] == 0), None)
    if prior: return {"status":"duplicate-suppressed","attempt":prior,"operation_id":operation_id}
    row = {"operation_id":operation_id,"attempt":0,"kind":"initial","stage_id":stage_id,"adapter_id":stage["adapter_id"],"action_class":stage["adapter_action_class"],"status":"prepared","outcome":None,"approval_id":approval_id,"input_ref":input_ref,"result_ref":None,"result_hash":None}
    clean = {key:value for key,value in payload.items() if key != "artifact"}; clean["attempts"].append(row); _save(root, workflow_id, clean)
    return {"status":"recorded","attempt":row,"operation_id":operation_id}


def record_initial_outcome(root: Path, workflow_id: str, stage_id: str, outcome: str, result_ref: str) -> dict[str, Any]:
    root = root.resolve(); plan, stage = _context(root, workflow_id, stage_id); payload = show(root, workflow_id); operation_id = _operation(plan, stage)
    row = next((item for item in payload["attempts"] if item["operation_id"] == operation_id and item["attempt"] == 0), None)
    if row is None: raise ValueError("initial stage dispatch receipt is missing")
    if row["status"] == "completed":
        if row["outcome"] == outcome and row["result_ref"] == result_ref: return {"status":"duplicate-suppressed","attempt":row}
        raise ValueError("initial attempt receipt is immutable after completion")
    row.update({"status":"completed","outcome":outcome,"result_ref":result_ref,"result_hash":_hash(ownership._read_ref(root, result_ref))})
    clean = {key:value for key,value in payload.items() if key != "artifact"}; _save(root, workflow_id, clean)
    return {"status":"recorded","attempt":row}


def _completion_blocks_retry(root: Path, workflow_id: str) -> bool:
    receipt = evidence.receipt_path(root, workflow_id)
    if not receipt.is_file(): return False
    return json.loads(receipt.read_text(encoding="utf-8")).get("state") == "evidence-incomplete-accepted"


def decide(root: Path, workflow_id: str, stage_id: str) -> dict[str, Any]:
    root = root.resolve(); plan, stage = _context(root, workflow_id, stage_id); definition = adapter_catalog.get(stage["adapter_id"]); projection = storage.status(root, workflow_id)["last_valid_projection"]
    current = projection.get("stages", {}).get(stage_id, {}).get("status"); payload = show(root, workflow_id); operation_id = _operation(plan, stage)
    retries = [row for row in payload["attempts"] if row["operation_id"] == operation_id and row["kind"] == "retry"]
    eligible_action = definition["action_class"] in ELIGIBLE_ACTIONS and definition["max_retries"] > 0
    closure_blocked = _completion_blocks_retry(root, workflow_id)
    if closure_blocked: reason = "accepted evidence-incomplete closure never authorizes retry"
    elif definition["action_class"] in PROHIBITED_ACTIONS: reason = "project, execution, scanner, provider, or publish actions never retry automatically"
    elif current not in {"failed","blocked","stale"}: reason = f"stage state `{current}` is not retryable"
    elif len(retries) >= definition["max_retries"]: reason = "retry limit exhausted"
    elif eligible_action: reason = "eligible deterministic low-risk retry"
    else: reason = "action class is not automatically retryable"
    eligible = eligible_action and current in {"failed","blocked","stale"} and len(retries) < definition["max_retries"] and not closure_blocked
    return {"type":"tailtrail-workflow-retry-decision","workflow_id":workflow_id,"stage_id":stage_id,"operation_id":operation_id,"eligible":eligible,"action_class":definition["action_class"],"attempts_used":len(retries),"max_retries":definition["max_retries"],"backoff_category":"immediate-local" if eligible else "none","reason":reason,"boundary":"Decision only. Eligible means a typed host retry handoff may be prepared; TailTrail has not run it."}


def prepare(root: Path, workflow_id: str, stage_id: str) -> dict[str, Any]:
    root = root.resolve(); decision = decide(root, workflow_id, stage_id)
    if not decision["eligible"]: raise ValueError("retry is not eligible: " + decision["reason"])
    plan, stage = _context(root, workflow_id, stage_id); projection = storage.status(root, workflow_id)["last_valid_projection"]; workflow_status = projection["workflow_status"]
    if workflow_status in {"failed","blocked"}: transitions.workflow(root, workflow_id, "ready", "retry-eligible")
    transitions.stage(root, workflow_id, stage_id, "ready", "retry-eligible")
    approval_id = projection["stages"][stage_id].get("last_approval_id")
    transitions.workflow(root, workflow_id, "running", "workflow-started")
    transitions.stage(root, workflow_id, stage_id, "running", "approval-granted" if approval_id else "stage-started", approval_id)
    payload = show(root, workflow_id); attempt_number = decision["attempts_used"] + 1; input_status = adapters.show(root, workflow_id, stage_id); input_ref = (input_status.get("input") or {}).get("artifact")
    row = {"operation_id":decision["operation_id"],"attempt":attempt_number,"kind":"retry","stage_id":stage_id,"adapter_id":stage["adapter_id"],"action_class":stage["adapter_action_class"],"status":"prepared","outcome":None,"approval_id":approval_id,"input_ref":input_ref,"result_ref":None,"result_hash":None}
    clean = {key:value for key,value in payload.items() if key != "artifact"}; clean["attempts"].append(row); saved = _save(root, workflow_id, clean)
    binding = ownership.show(root, workflow_id); LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_retry_prepared", {"workflow_id":workflow_id,"stage_id":stage_id,"operation_id":row["operation_id"],"attempt":attempt_number,"action_class":row["action_class"]})
    return {"schema_version":"1","type":"tailtrail-workflow-retry-handoff","workflow_id":workflow_id,"stage_id":stage_id,"operation_id":row["operation_id"],"attempt":attempt_number,"adapter_id":stage["adapter_id"],"action_class":stage["adapter_action_class"],"input_ref":input_ref,"attempts_ref":saved["artifact"],"boundary":"Typed retry handoff only. The host executes the deterministic low-risk action and must record a factual typed result."}


def record(root: Path, workflow_id: str, stage_id: str, result_ref: str) -> dict[str, Any]:
    root = root.resolve(); plan, stage = _context(root, workflow_id, stage_id); payload = show(root, workflow_id); operation_id = _operation(plan, stage)
    row = next((item for item in reversed(payload["attempts"]) if item["operation_id"] == operation_id and item["kind"] == "retry" and item["status"] == "prepared"), None)
    if row is None: raise ValueError("no prepared retry attempt exists")
    result = ownership._read_ref(root, result_ref)
    if not isinstance(result, dict): raise ValueError("retry result must be a typed JSON object")
    definition = adapters.contract(stage["adapter_id"]); adapters._validate_result(definition, result); outcome = str(result["outcome"])
    if outcome == "skipped": raise ValueError("retry result cannot bypass explicit approved skip")
    row.update({"status":"completed","outcome":outcome,"result_ref":result_ref,"result_hash":_hash(result)})
    clean = {key:value for key,value in payload.items() if key != "artifact"}; _save(root, workflow_id, clean)
    if outcome == "pass": transitions.stage(root, workflow_id, stage_id, "passed", "stage-passed")
    elif outcome == "fail": transitions.stage(root, workflow_id, stage_id, "failed", "stage-failed"); transitions.workflow(root, workflow_id, "failed", "stage-failed")
    else: transitions.stage(root, workflow_id, stage_id, "blocked", "blocked-missing-evidence"); transitions.workflow(root, workflow_id, "blocked", "blocked-missing-evidence")
    binding = ownership.show(root, workflow_id); LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_retry_recorded", {"workflow_id":workflow_id,"stage_id":stage_id,"operation_id":operation_id,"attempt":row["attempt"],"outcome":outcome,"result_ref":result_ref})
    if outcome == "pass":
        from workflow_runtime import executor, freshness
        freshness.checkpoint(root, workflow_id, f"retry-passed:{stage_id}")
        return {"status":"recorded","attempt":row,"execution":executor._complete_or_status(root, workflow_id)}
    from workflow_runtime import correction
    return {"status":"recorded","attempt":row,"decision":decide(root, workflow_id, stage_id),"correction":correction.route(root, workflow_id, stage_id)}


def latest_pass(root: Path, workflow_id: str, stage_id: str) -> bool:
    return any(row["stage_id"] == stage_id and row["kind"] == "retry" and row["status"] == "completed" and row["outcome"] == "pass" for row in show(root.resolve(), workflow_id)["attempts"])
