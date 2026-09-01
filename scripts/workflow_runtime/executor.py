"""Advance Deferred Phase 5 template stages only from approved typed adapter evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from workflow_runtime import adapters, approvals, compiler, contracts, correction, freshness, ownership, retry, stage_results, state, storage, task_scope, transitions


LEDGER = ownership.LEDGER


def path(root: Path, workflow_id: str) -> Path:
    return ownership.binding_path(root.resolve(), workflow_id).parent / "template-execution-v1.json"


def _relative(root: Path, value: Path) -> str:
    return value.resolve().relative_to(root.resolve()).as_posix()


def _plan_stage(root: Path, workflow_id: str, stage_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    check = compiler.validate(root, workflow_id)
    if not check["valid"]: raise ValueError("template execution requires a valid frozen plan: " + "; ".join(check["issues"]))
    plan = compiler.show(root, workflow_id); stage = next((row for row in plan["stages"] if row["stage_id"] == stage_id), None)
    if stage is None: raise ValueError(f"template stage `{stage_id}` is not in the frozen graph")
    return plan, stage


def _ensure_scope(root: Path, workflow_id: str) -> None:
    try: task_scope.show(root, workflow_id)
    except ValueError as error:
        if "does not exist" not in str(error): raise
        task_scope.initialize(root, workflow_id)


def _projection(root: Path, workflow_id: str) -> dict[str, Any]:
    transitions.ensure_stages(root, workflow_id)
    return storage.status(root, workflow_id)["last_valid_projection"]


def _start_workflow(root: Path, workflow_id: str) -> None:
    projection = _projection(root, workflow_id); status = projection["workflow_status"]
    if status == "ready": transitions.workflow(root, workflow_id, "running", "workflow-started")
    elif status != "running": raise ValueError(f"template execution requires ready/running workflow, found `{status}`")


def _approval(root: Path, workflow_id: str, approval_id: str) -> dict[str, Any]:
    rows = approvals.show(root, workflow_id).get("approvals", [])
    row = next((item for item in rows if item.get("approval_id") == approval_id), None)
    if row is None: raise ValueError("template execution cannot resolve the exact approval record")
    return row


def _risk_classes(root: Path, workflow_id: str) -> set[str]:
    binding = ownership.show(root, workflow_id); rows = ownership._read_ref(root, binding["requirement_matrix_ref"])
    text = " ".join(str(row.get("statement", "")) for row in rows).lower(); found: set[str] = set()
    words = {"dependency": ("dependency", "package", "library"), "migration": ("migration", "schema change"),
             "privacy": ("privacy", "pii", "personal data"), "auth": ("authentication", "authorization", " auth "),
             "secret": ("secret", "credential", "api key", "access token"), "infrastructure": ("infrastructure", "terraform", "kubernetes")}
    padded = f" {text} "
    for risk, signals in words.items():
        if any(signal in padded for signal in signals): found.add(risk)
    return found


def _risk_authority(root: Path, workflow_id: str) -> None:
    required = _risk_classes(root, workflow_id)
    if not required: return
    status = adapters.show(root, workflow_id, "risk-plan"); output = status.get("output") or {}; result = output.get("result", {})
    declared = set(result.get("risk_classes", [])); refs = result.get("authority_refs", [])
    if not required <= declared: raise ValueError("risk plan does not classify every approved dependency/migration/privacy/auth/secret/infrastructure signal")
    covered: set[str] = set()
    for ref in refs:
        artifact = ownership._read_ref(root, str(ref))
        if not isinstance(artifact, dict) or artifact.get("type") != "tailtrail-workflow-risk-authority" or artifact.get("status") != "approved":
            raise ValueError("risk authority reference is missing, invalid, or not approved")
        issues = contracts.validate_artifact(artifact)
        if issues: raise ValueError("risk authority reference fails its closed contract: " + "; ".join(issues))
        covered.update(str(item) for item in artifact.get("risk_classes", []))
    if not required <= covered: raise ValueError("approved risk authority does not cover: " + ", ".join(sorted(required - covered)))


def _ci_boundary(stage_id: str, result: dict[str, Any]) -> None:
    if stage_id != "ingest-finding": return
    boundary = result.get("evidence_boundary")
    if boundary not in {"saved-ci-receipt", "saved-scanner-receipt"}:
        raise ValueError("finding intake requires a saved CI/scanner receipt; live provider action needs separate external-provider authority")


def _receipt(root: Path, workflow_id: str, *, persist: bool) -> dict[str, Any]:
    plan = compiler.show(root, workflow_id); projection = _projection(root, workflow_id); binding = ownership.show(root, workflow_id)
    rows: list[dict[str, Any]] = []
    for stage in plan["stages"]:
        stage_id = stage["stage_id"]; current = projection["stages"].get(stage_id, {}); adapter = adapters.show(root, workflow_id, stage_id) if stage.get("control_kind") is None else None
        adapter_input = (adapter or {}).get("input") or {}
        adapter_output = (adapter or {}).get("output") or {}
        rows.append({"stage_id": stage_id, "capability_id": stage["capability_id"], "adapter_id": stage["adapter_id"], "status": current.get("status", "pending"), "required_evidence": stage.get("evidence", []), "input_ref": adapter_input.get("artifact"), "output_ref": adapter_output.get("artifact"), "approval_id": current.get("last_approval_id")})
    terminal = projection["workflow_status"] in {"completed", "failed", "blocked", "cancelled", "superseded"}
    payload = {"schema_version":"1", "type":"tailtrail-workflow-template-execution", "workflow_id":workflow_id, "tailtrail_run_id":binding["tailtrail_run_id"], "template_id":plan["template_id"], "plan_fingerprint":plan["plan_fingerprint"], "requirement_uids":binding["requirement_uids"], "workflow_status":projection["workflow_status"], "stages":rows, "next_stage_id":next((row["stage_id"] for row in rows if row["status"] not in {"passed", "skipped"}), None), "terminal":terminal, "boundary":"Receipt is derived from the frozen graph, journal, approvals, and typed adapter artifacts. It does not invent evidence or execute a capability."}
    contracts.require_valid(payload); destination = path(root, workflow_id)
    if persist:
        LEDGER.atomic_json(destination, payload)
    return {"artifact": _relative(root, destination), **payload}


def _write_receipt(root: Path, workflow_id: str) -> dict[str, Any]:
    return _receipt(root, workflow_id, persist=True)


def status(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve()
    replay = storage.replay(root, workflow_id)
    if not replay["valid"]: raise ValueError("template execution journal cannot be replayed: " + "; ".join(replay["issues"]))
    return _receipt(root, workflow_id, persist=False)


def start(root: Path, workflow_id: str, stage_id: str | None, approval_id: str | None) -> dict[str, Any]:
    root = root.resolve(); _ensure_scope(root, workflow_id); freshness_result = freshness.apply(root, workflow_id)
    if freshness_result["status"] == "stale":
        next_action = freshness_result.get("terminal_boundary", "Use workflow resume plan; do not dispatch against changed inputs.")
        selected = stage_id or status(root, workflow_id).get("next_stage_id")
        result = None
        if selected:
            stale_key = hashlib.sha256(json.dumps({
                "workflow_id": workflow_id, "stage_id": selected,
                "checkpoint_fingerprint": freshness_result.get("checkpoint_fingerprint"),
                "change_types": freshness_result.get("change_types", []),
                "affected_stage_ids": freshness_result.get("affected_stage_ids", []),
            }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            result = stage_results.record(root, workflow_id, selected, outcome="stale", reason_code="input-stale",
                idempotency_key="wfidem-" + stale_key,
                transition_event=None, evidence_refs=[freshness_result["artifact"]] if freshness_result.get("artifact") else [])
        return {"execution":status(root, workflow_id),"status":"freshness-stale","freshness":freshness_result,"stage_result":result,"next":next_action}
    plan = compiler.show(root, workflow_id); current = status(root, workflow_id)
    selected = stage_id or current["next_stage_id"]
    if not selected: return current
    _plan, stage = _plan_stage(root, workflow_id, selected); projection = _projection(root, workflow_id); stage_status = projection["stages"][selected]["status"]
    if stage_status in {"passed", "skipped"}: raise ValueError("passed/skipped stages are never dispatched again")
    if stage_status not in {"pending", "ready", "awaiting_approval"}: raise ValueError(f"stage `{selected}` cannot start from `{stage_status}`")
    _start_workflow(root, workflow_id)
    if stage_status == "pending": transitions.stage(root, workflow_id, selected, "ready", "stage-ready")
    if stage.get("approval_class") != "none" and not approval_id:
        transitions.stage(root, workflow_id, selected, "awaiting_approval", "blocked-missing-authority")
        return {"execution": _write_receipt(root, workflow_id), "status": "awaiting-approval", "required_action_class": stage["adapter_action_class"]}
    if stage.get("control_kind") == "approval-gate":
        transitions.stage(root, workflow_id, selected, "running", "approval-granted", approval_id)
        transition = transitions.stage(root, workflow_id, selected, "passed", "stage-passed")
        stage_results.record(root, workflow_id, selected, outcome="pass", reason_code="stage-passed",
            idempotency_key="wfidem-" + hashlib.sha256(f"{workflow_id}:{selected}:{approval_id}:control".encode()).hexdigest(),
            transition_event=transition, evidence_refs=[])
        return _complete_or_status(root, workflow_id)
    if plan["template_id"] == "repository-discovery" and stage["adapter_action_class"] not in {"read_local", "write_tailtrail_state"}:
        raise ValueError("repository-discovery is read-only; project action requires a separately approved follow-up workflow")
    if plan["template_id"] == "risk-sensitive" and selected == "implement":
        try: _risk_authority(root, workflow_id)
        except ValueError:
            transitions.stage(root, workflow_id, selected, "blocked", "blocked-missing-authority")
            transitions.workflow(root, workflow_id, "blocked", "blocked-missing-authority")
            _write_receipt(root, workflow_id)
            raise
    if selected == "implement": task_scope.acquire(root, workflow_id)
    prepared = adapters.prepare(root, workflow_id, selected, stage["adapter_id"], approval_id)
    retry.register_initial(root, workflow_id, selected, approval_id, prepared["artifact"])
    transitions.stage(root, workflow_id, selected, "running", "approval-granted" if approval_id else "stage-started", approval_id)
    return {"execution": _write_receipt(root, workflow_id), "adapter_input": prepared}


def _complete_or_status(root: Path, workflow_id: str) -> dict[str, Any]:
    plan = compiler.show(root, workflow_id); projection = _projection(root, workflow_id)
    if all(row.get("status") in {"passed", "skipped"} for row in projection["stages"].values()):
        for stage in plan["stages"]:
            if stage.get("control_kind") is None and projection["stages"][stage["stage_id"]]["status"] == "passed":
                check = adapters.validate(root, workflow_id, stage["stage_id"])
                if not check["valid"]: raise ValueError("workflow completion found missing/invalid adapter evidence: " + "; ".join(check["issues"]))
                output = adapters.show(root, workflow_id, stage["stage_id"]).get("output")
                if (output or {}).get("outcome") != "pass" and not retry.latest_pass(root, workflow_id, stage["stage_id"]):
                    raise ValueError("workflow completion requires a passing initial or bounded-retry result for every passed stage")
        transitions.workflow(root, workflow_id, "completed", "workflow-completed")
        task_scope.release(root, workflow_id, "workflow-completed")
        receipt = _write_receipt(root, workflow_id)
        binding = ownership.show(root, workflow_id); LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_template_completed", {"workflow_id":workflow_id, "template_id":plan["template_id"], "execution_ref":_relative(root, path(root, workflow_id))})
        return receipt
    return _write_receipt(root, workflow_id)


def finish(root: Path, workflow_id: str, stage_id: str) -> dict[str, Any]:
    root = root.resolve(); plan, stage = _plan_stage(root, workflow_id, stage_id)
    if stage.get("control_kind"): raise ValueError("control approval stages finish atomically during start")
    projection = _projection(root, workflow_id)
    if projection["stages"][stage_id]["status"] != "running": raise ValueError("only a running adapter stage can finish")
    check = adapters.validate(root, workflow_id, stage_id)
    if not check["valid"]: raise ValueError("stage result is missing or invalid: " + "; ".join(check["issues"]))
    output = adapters.show(root, workflow_id, stage_id)["output"]; result = output["result"]
    try: _ci_boundary(stage_id, result)
    except ValueError:
        transitions.stage(root, workflow_id, stage_id, "blocked", "blocked-missing-authority")
        transitions.workflow(root, workflow_id, "blocked", "blocked-missing-authority")
        _write_receipt(root, workflow_id)
        raise
    outcome = output["outcome"]
    retry.record_initial_outcome(root, workflow_id, stage_id, outcome, output["artifact"])
    transition = None
    reason_code = "stage-passed"
    if outcome == "pass": transition = transitions.stage(root, workflow_id, stage_id, "passed", "stage-passed")
    elif outcome == "fail":
        reason_code = "stage-failed"; transition = transitions.stage(root, workflow_id, stage_id, "failed", reason_code); transitions.workflow(root, workflow_id, "failed", reason_code)
    elif outcome in {"blocked", "timeout", "unavailable"}:
        reason_code = "blocked-missing-evidence"; transition = transitions.stage(root, workflow_id, stage_id, "blocked", reason_code); transitions.workflow(root, workflow_id, "blocked", reason_code)
    else: raise ValueError("skipped results cannot bypass the explicit approved skip transition")
    stage_results.record(root, workflow_id, stage_id, outcome=outcome, reason_code=reason_code,
        idempotency_key=output["idempotency_key"], transition_event=transition,
        evidence_refs=[output["artifact"], *output.get("evidence_refs", [])])
    binding = ownership.show(root, workflow_id); LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_template_stage_advanced", {"workflow_id":workflow_id, "template_id":plan["template_id"], "stage_id":stage_id, "outcome":outcome, "adapter_output_ref":output["artifact"]})
    if outcome == "pass": freshness.checkpoint(root, workflow_id, f"stage-passed:{stage_id}")
    else: correction.route(root, workflow_id, stage_id)
    return _complete_or_status(root, workflow_id)


def skip(root: Path, workflow_id: str, stage_id: str, approval_id: str) -> dict[str, Any]:
    root = root.resolve(); _ensure_scope(root, workflow_id); _plan, _stage = _plan_stage(root, workflow_id, stage_id); _start_workflow(root, workflow_id)
    current = _projection(root, workflow_id)["stages"][stage_id]["status"]
    if current == "pending": transitions.stage(root, workflow_id, stage_id, "ready", "stage-ready")
    transition = transitions.stage(root, workflow_id, stage_id, "skipped", "stage-skipped-approved", approval_id)
    stage_results.record(root, workflow_id, stage_id, outcome="skipped", reason_code="stage-skipped-approved",
        idempotency_key="wfidem-" + hashlib.sha256(f"{workflow_id}:{stage_id}:{approval_id}:skip".encode()).hexdigest(),
        transition_event=transition, evidence_refs=[])
    return _complete_or_status(root, workflow_id)
