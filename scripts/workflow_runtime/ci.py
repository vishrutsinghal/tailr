"""Ingest linked CI receipts and advance only policy-approved metadata stages."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from workflow_runtime import compiler, contracts, ownership, storage, task_scope, transitions


LEDGER = ownership.LEDGER
OPERATIONS = {"validation", "evidence-ingestion", "reporting", "closure-readiness"}
FORBIDDEN_ACTIONS = {"write_project", "scan_local", "external_provider", "publish"}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _read_ref(root: Path, ref: str) -> tuple[Path, dict[str, Any]]:
    path, pointer = ownership._resolve_ref(root, ref)
    if pointer:
        raise ValueError("CI policy and receipt references cannot use JSON pointers")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("CI reference must contain one JSON object")
    return path, value


def policy_fingerprint(policy: dict[str, Any]) -> str:
    return _hash({key: value for key, value in policy.items() if key != "policy_fingerprint"})


def receipt_fingerprint(receipt: dict[str, Any]) -> str:
    return _hash(receipt)


def index_path(root: Path, workflow_id: str) -> Path:
    return ownership.binding_path(root.resolve(), workflow_id).parent / "ci-continuation-v1.json"


def _empty(binding: dict[str, Any], policy_ref: str, fingerprint: str) -> dict[str, Any]:
    payload = {"schema_version":"1", "type":"tailtrail-workflow-ci-continuation", "workflow_id":binding["workflow_id"], "tailtrail_run_id":binding["tailtrail_run_id"], "policy_ref":policy_ref, "policy_fingerprint":fingerprint, "receipts":[], "boundary":"Sanitized CI receipt index only. It never runs CI, commands, scanners, providers, source fixes, publication, deployment, merge, or recovery."}
    payload["continuation_fingerprint"] = _hash({key:value for key,value in payload.items() if key != "continuation_fingerprint"})
    return payload


def show(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); path = index_path(root, workflow_id)
    if not path.is_file():
        return {"type":"tailtrail-workflow-ci-continuation-status", "workflow_id":workflow_id, "status":"not-started", "receipts":[], "boundary":"Read-only CI continuation status; no workflow state was created or advanced."}
    value = json.loads(path.read_text(encoding="utf-8")); issues = contracts.validate_artifact(value)
    expected = _hash({key:item for key,item in value.items() if key != "continuation_fingerprint"})
    if value.get("continuation_fingerprint") != expected: issues.append("CI continuation fingerprint differs from its contents")
    return {"artifact":_relative(root,path), **value, "status":"valid" if not issues else "blocked", "valid":not issues, "issues":issues}


def _preflight(root: Path, workflow_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    binding = ownership.show(root, workflow_id); ownership_check = ownership.validate(root, workflow_id)
    if not ownership_check["valid"]: raise ValueError("CI ownership/target binding is invalid: " + "; ".join(ownership_check["issues"]))
    plan_check = compiler.validate(root, workflow_id)
    if not plan_check["valid"]: raise ValueError("CI compiler plan/policy is stale or invalid: " + "; ".join(plan_check["issues"]))
    scope = task_scope.freshness(root, workflow_id)
    if not scope["valid"] or not scope["fresh"]: raise ValueError("CI task scope is stale or invalid")
    return binding, compiler.show(root, workflow_id), task_scope.show(root, workflow_id)


def _policy(root: Path, ref: str, binding: dict[str, Any], plan: dict[str, Any], scope: dict[str, Any]) -> dict[str, Any]:
    _, policy = _read_ref(root, ref); contracts.require_valid(policy)
    if policy["policy_fingerprint"] != policy_fingerprint(policy): raise ValueError("CI policy fingerprint is invalid")
    expected = (binding["workflow_id"], binding["tailtrail_run_id"], plan["revision"], plan["plan_fingerprint"], binding["target_identity_fingerprint"], scope["scope_fingerprint"])
    actual = (policy["workflow_id"], policy["tailtrail_run_id"], policy["revision"], policy["compiler_plan_fingerprint"], policy["target_identity_fingerprint"], policy["scope_fingerprint"])
    if actual != expected: raise ValueError("CI policy is not bound to the current run, target, plan, and scope")
    return policy


def _validate_receipt(root: Path, ref: str, policy_ref: str, policy: dict[str, Any], binding: dict[str, Any], plan: dict[str, Any], scope: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    _, receipt = _read_ref(root, ref); contracts.require_valid(receipt)
    if receipt["policy_ref"] != policy_ref or receipt["policy_fingerprint"] != policy["policy_fingerprint"]: raise ValueError("CI receipt policy binding is missing or stale")
    expected = (binding["workflow_id"], binding["tailtrail_run_id"], plan["revision"], plan["plan_fingerprint"], binding["target_identity_fingerprint"], scope["scope_fingerprint"])
    actual = (receipt["workflow_id"], receipt["tailtrail_run_id"], receipt["compiler_revision"], receipt["compiler_plan_fingerprint"], receipt["target_identity_fingerprint"], receipt["scope_fingerprint"])
    if actual != expected: raise ValueError("CI receipt is not fresh for the current run, target, plan, or scope")
    if set(receipt["requirement_uids"]) - set(binding["requirement_uids"]): raise ValueError("CI receipt references another run's requirement")
    current_head = ownership.TARGET.identity(root).get("git", {}).get("head")
    if not current_head or receipt["commit_sha"] != current_head: raise ValueError("CI receipt commit is missing or differs from the current target commit")
    artifact = root / receipt["artifact_ref"]
    attestation = root / receipt["provenance"]["attestation_ref"]
    for label, path in (("artifact", artifact), ("provenance attestation", attestation)):
        try: path.resolve().relative_to(root)
        except ValueError as error: raise ValueError(f"CI {label} escapes the repository") from error
        if not path.is_file() or not _relative(root, path).startswith(".tailtrail/"): raise ValueError(f"CI {label} must be an existing local .tailtrail artifact")
    if receipt["artifact_hash"] != _file_hash(artifact): raise ValueError("CI artifact hash does not match the linked artifact")
    allowed_provenance = {(row["provider"], row["pipeline_ref"]) for row in policy["trusted_provenance"]}
    provenance = receipt["provenance"]
    if (provenance["provider"], provenance["pipeline_ref"]) not in allowed_provenance: raise ValueError("CI provenance is not explicitly trusted by policy")
    if receipt["environment"] not in policy["allowed_environments"]: raise ValueError("CI environment is not explicitly allowed by policy")
    stage = next((row for row in plan["stages"] if row["stage_id"] == receipt["stage_id"]), None)
    rule = next((row for row in policy["allowed_stages"] if row == {"stage_id":receipt["stage_id"], "operation_kind":receipt["operation_kind"]}), None)
    if stage is None or rule is None: raise ValueError("CI stage and operation are not explicitly allowed by policy")
    action = stage["adapter_action_class"]
    if action in FORBIDDEN_ACTIONS or (receipt["operation_kind"] == "validation" and action != "execute_project") or (receipt["operation_kind"] != "validation" and action not in {"read_local", "write_tailtrail_state"}):
        raise ValueError(f"CI continuation forbids stage action class `{action}` for `{receipt['operation_kind']}`")
    return receipt, stage


def _save(root: Path, binding: dict[str, Any], policy_ref: str, policy: dict[str, Any], receipt: dict[str, Any], disposition: str) -> dict[str, Any]:
    path = LEDGER.state_dir(root, binding["tailtrail_run_id"]) / "ci" / f"{receipt['receipt_id']}.json"
    if not path.is_file(): LEDGER.atomic_json(path, receipt)
    existing = show(root, binding["workflow_id"]); rows = list(existing.get("receipts", [])) if existing.get("type") == "tailtrail-workflow-ci-continuation" else []
    row = {"receipt_id":receipt["receipt_id"], "stage_id":receipt["stage_id"], "attempt":receipt["provenance"]["attempt"], "outcome":receipt["outcome"], "disposition":disposition, "receipt_ref":_relative(root,path), "receipt_fingerprint":receipt_fingerprint(receipt)}
    rows.append(row); payload = _empty(binding, policy_ref, policy["policy_fingerprint"]); payload["receipts"] = rows
    payload["continuation_fingerprint"] = _hash({key:value for key,value in payload.items() if key != "continuation_fingerprint"}); contracts.require_valid(payload); LEDGER.atomic_json(index_path(root,binding["workflow_id"]),payload)
    LEDGER.append_event(root,binding["tailtrail_run_id"],"workflow_ci_receipt_ingested",{"workflow_id":binding["workflow_id"],"stage_id":receipt["stage_id"],"receipt_id":receipt["receipt_id"],"outcome":receipt["outcome"],"disposition":disposition,"artifact":_relative(root,path)})
    return {"receipt":row,"continuation":{"artifact":_relative(root,index_path(root,binding["workflow_id"])),**payload}}


def ingest(root: Path, workflow_id: str, receipt_ref: str, policy_ref: str, approved: bool) -> dict[str, Any]:
    if approved is not True: raise ValueError("CI continuation requires explicit approved: true authority")
    root = root.resolve(); binding, plan, scope = _preflight(root, workflow_id); policy = _policy(root, policy_ref, binding, plan, scope)
    receipt, _stage = _validate_receipt(root, receipt_ref, policy_ref, policy, binding, plan, scope); fingerprint = receipt_fingerprint(receipt); prior = show(root, workflow_id)
    same_id = next((row for row in prior.get("receipts", []) if row["receipt_id"] == receipt["receipt_id"]), None)
    if same_id:
        if same_id["receipt_fingerprint"] != fingerprint: raise ValueError("duplicate CI receipt ID has different contents")
        return {"status":"duplicate-suppressed", "receipt":same_id, "continuation":prior, "boundary":"No duplicate state transition or project action occurred."}
    stage_rows = [row for row in prior.get("receipts", []) if row["stage_id"] == receipt["stage_id"]]
    attempt = receipt["provenance"]["attempt"]
    if stage_rows and attempt <= max(row["attempt"] for row in stage_rows):
        saved = _save(root,binding,policy_ref,policy,receipt,"delayed-ignored"); return {"status":"delayed-ignored",**saved,"boundary":"Delayed/out-of-order receipt was retained as sanitized evidence but did not change state."}
    transitions.ensure_stages(root, workflow_id); projection = storage.status(root,workflow_id)["last_valid_projection"]; current = projection["stages"][receipt["stage_id"]]
    if current["status"] in {"passed","failed","blocked","skipped","cancelled"}:
        saved = _save(root,binding,policy_ref,policy,receipt,"late-terminal-ignored"); return {"status":"late-terminal-ignored",**saved,"boundary":"A terminal stage never regresses from a later CI receipt."}
    incomplete = [item for item in current["prerequisites"] if projection["stages"].get(item,{}).get("status") not in {"passed","skipped"}]
    if incomplete:
        saved = _save(root,binding,policy_ref,policy,receipt,"out-of-order-blocked"); return {"status":"out-of-order-blocked","incomplete_prerequisites":incomplete,**saved,"boundary":"CI cannot bypass frozen stage prerequisites."}
    workflow_status = projection["workflow_status"]
    if workflow_status == "ready": storage.append_event(root,workflow_id,"workflow-started",{"from_state":"ready","to_state":"running","reason_code":"workflow-started","boundary":"CI metadata continuation only; no command was executed."})
    elif workflow_status != "running": raise ValueError(f"CI continuation requires ready/running workflow state, found `{workflow_status}`")
    if current["status"] == "pending": storage.append_event(root,workflow_id,"stage-ready",{"stage_id":receipt["stage_id"],"from_state":"pending","to_state":"ready","reason_code":"stage-ready","boundary":"CI metadata continuation only."}); current={**current,"status":"ready"}
    if current["status"] != "ready": raise ValueError("CI continuation accepts only a dependency-ready pending/ready stage")
    storage.append_event(root,workflow_id,"stage-started",{"stage_id":receipt["stage_id"],"from_state":"ready","to_state":"running","reason_code":"stage-started","approval_id":None,"boundary":"The linked CI receipt proves an already-finished job; TailTrail did not execute it."})
    if receipt["outcome"] == "pass": event,to_state,reason="stage-passed","passed","stage-passed"
    elif receipt["outcome"] == "fail": event,to_state,reason="stage-failed","failed","stage-failed"
    else: event,to_state,reason="stage-blocked","blocked","blocked-missing-evidence"
    storage.append_event(root,workflow_id,event,{"stage_id":receipt["stage_id"],"from_state":"running","to_state":to_state,"reason_code":reason,"approval_id":None,"boundary":"State advanced only from a validated linked CI receipt; no project or external action occurred."})
    if receipt["outcome"] in {"fail","cancelled"}:
        workflow_event,workflow_target,workflow_reason=("workflow-failed","failed","stage-failed") if receipt["outcome"]=="fail" else ("workflow-blocked","blocked","blocked-missing-evidence")
        storage.append_event(root,workflow_id,workflow_event,{"from_state":"running","to_state":workflow_target,"reason_code":workflow_reason,"boundary":"CI failure/cancellation stops continuation and grants no recovery authority."})
    saved = _save(root,binding,policy_ref,policy,receipt,"advanced")
    LEDGER.append_event(root,binding["tailtrail_run_id"],"workflow_ci_continuation_advanced",{"workflow_id":workflow_id,"stage_id":receipt["stage_id"],"outcome":receipt["outcome"],"receipt_id":receipt["receipt_id"]})
    return {"status":"advanced","workflow_status":storage.status(root,workflow_id)["last_valid_projection"]["workflow_status"],"stage_status":to_state,**saved,"boundary":"Policy-backed metadata continuation only; closure still requires the canonical completion boundary."}
