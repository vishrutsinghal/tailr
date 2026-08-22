"""Deferred Phase 7 learning, evaluation, and Meta-Harness workflow bridge."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workflow_runtime import compiler, context, contracts, evidence, ownership, storage

LEDGER = ownership.LEDGER


def _load(name: str, script: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / script)
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(module)
    return module


LEARNING = _load("dwr7_closure_learning", "closure-learning.py")


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _directory(root: Path, workflow_id: str) -> Path:
    return ownership.binding_path(root.resolve(), workflow_id).parent / "outcomes"


def _receipt(root: Path, workflow_id: str) -> dict[str, Any]:
    path = evidence.receipt_path(root.resolve(), workflow_id)
    if not path.is_file(): raise ValueError("canonical workflow completion receipt is required")
    value = json.loads(path.read_text(encoding="utf-8")); contracts.require_valid(value); return value


def learning(root: Path, workflow_id: str, accepted_by: str) -> dict[str, Any]:
    """Create only a governance-candidate after accepted canonical completion."""
    root = root.resolve(); binding = ownership.show(root, workflow_id); receipt = _receipt(root, workflow_id)
    if receipt["state"] != "completed":
        return {"type":"tailtrail-workflow-learning-result","workflow_id":workflow_id,"status":"not-eligible","learning_kind":"incomplete-delivery" if receipt["state"].startswith("evidence-incomplete") else "unavailable","reason":"positive learning requires canonical completed closure; incomplete delivery remains separate","boundary":"No learning candidate was created or promoted."}
    candidate = LEARNING.capture(root, binding["tailtrail_run_id"], accepted_by)
    payload = {"schema_version":"1","type":"tailtrail-workflow-learning-link","workflow_id":workflow_id,"tailtrail_run_id":binding["tailtrail_run_id"],"completion_receipt_ref":_relative(root,evidence.receipt_path(root,workflow_id)),"learning_kind":"positive","candidate_id":candidate["candidate_id"],"promotion":"candidate-only; existing learning governance promotion required","artifact_fingerprint":"","boundary":"This link follows accepted canonical completion only. It is advisory and cannot override source, policy, tests, CI, scanners, or user instructions."}
    payload["artifact_fingerprint"] = _hash({key:value for key,value in payload.items() if key != "artifact_fingerprint"}); contracts.require_valid(payload)
    path = _directory(root,workflow_id) / "learning-link-v1.json"; LEDGER.atomic_json(path,payload)
    LEDGER.append_event(root,binding["tailtrail_run_id"],"workflow_learning_candidate_linked",{"workflow_id":workflow_id,"candidate_id":candidate["candidate_id"],"artifact":_relative(root,path),"kind":"positive"})
    return {"artifact":_relative(root,path),**payload,"status":"candidate-created","candidate_reused":candidate.get("reused",False)}


def _event(root: Path, workflow_id: str) -> dict[str, Any]:
    binding = ownership.show(root,workflow_id); plan = compiler.show(root,workflow_id); projection = storage.status(root,workflow_id)["last_valid_projection"]
    receipt = _receipt(root,workflow_id); stages = projection.get("stages",{})
    freshness_events = []
    freshness_dir = ownership.binding_path(root,workflow_id).parent / "freshness"
    for path in sorted(freshness_dir.glob("assessment-*.json")) if freshness_dir.is_dir() else []:
        row=json.loads(path.read_text()); freshness_events.extend(row.get("change_types",[]))
    approval_count = len((ownership.binding_path(root,workflow_id).parent / "stage-approvals-v1.json").read_text()) if False else 0
    approvals = ownership.binding_path(root,workflow_id).parent / "stage-approvals-v1.json"
    if approvals.is_file(): approval_count = len(json.loads(approvals.read_text()).get("approvals",[]))
    outcomes={stage_id:row.get("status","pending") for stage_id,row in stages.items()}
    run_events = LEDGER.read_events(LEDGER.state_dir(root, binding["tailtrail_run_id"]) / "events.jsonl")
    return {"schema_version":"1","type":"tailtrail-workflow-evaluation-event","workflow_id":workflow_id,"tailtrail_run_id":binding["tailtrail_run_id"],"template_id":plan["template_id"],"stage_outcomes":outcomes,"stale_recomputation_count":len(freshness_events),"correction_cycle_count":len([item for item in run_events if item.get("event_type") in {"workflow_correction_packet_created", "workflow_recovery_replan_routed"}]),"approval_count":approval_count,"requirement_completion":"complete" if receipt["state"] == "completed" else "incomplete","closure_state":receipt["state"],"event_fingerprint":"","boundary":"Normalized categorical workflow facts only. No prompts, source, logs, repository/user identity, customer data, secrets, commands, or exact token values are emitted."}


def emit(root: Path, workflow_id: str) -> dict[str, Any]:
    root=root.resolve(); event=_event(root,workflow_id); event["event_fingerprint"]=_hash({key:value for key,value in event.items() if key != "event_fingerprint"}); contracts.require_valid(event)
    meta={"schema_version":"1","type":"tailtrail-workflow-meta-harness-signal","workflow_id":workflow_id,"signals":{"workflow_fit":"fit" if event["closure_state"]=="completed" else "incomplete","repeated_failures":"present" if list(event["stage_outcomes"].values()).count("failed") > 1 else "absent","false_intervention":"unknown","missing_evidence":"present" if event["closure_state"] != "completed" else "absent","approval_burden":"high" if event["approval_count"] > 3 else "normal","adapter_quality":"unknown"},"signal_fingerprint":"","boundary":"Sanitized advisory Meta-Harness signals only. They cannot authorize, retry, change policy, or override current source, policy, tests, CI, scanners, or user instructions."}
    meta["signal_fingerprint"]=_hash({key:value for key,value in meta.items() if key != "signal_fingerprint"}); contracts.require_valid(meta)
    directory=_directory(root,workflow_id); event_path=directory / "evaluation-event-v1.json"; meta_path=directory / "meta-harness-signal-v1.json"; LEDGER.atomic_json(event_path,event); LEDGER.atomic_json(meta_path,meta)
    binding=ownership.show(root,workflow_id); LEDGER.append_event(root,binding["tailtrail_run_id"],"workflow_evaluation_emitted",{"workflow_id":workflow_id,"event_ref":_relative(root,event_path),"meta_ref":_relative(root,meta_path),"closure_state":event["closure_state"]})
    return {"event_artifact":_relative(root,event_path),"meta_artifact":_relative(root,meta_path),"event":event,"meta":meta}


def validate(root: Path, workflow_id: str) -> dict[str, Any]:
    root=root.resolve(); issues=[]
    try:
        for path in (_directory(root,workflow_id)/"learning-link-v1.json",_directory(root,workflow_id)/"evaluation-event-v1.json",_directory(root,workflow_id)/"meta-harness-signal-v1.json"):
            if path.is_file(): issues.extend(contracts.validate_artifact(json.loads(path.read_text())))
        context.resume_summary(root,workflow_id)
    except (OSError,ValueError,json.JSONDecodeError) as error: issues.append(str(error))
    return {"type":"tailtrail-workflow-phase-7-validation","workflow_id":workflow_id,"valid":not issues,"status":"valid" if not issues else "blocked","issues":issues,"boundary":"Read-only validation. It does not create learning, evaluation, telemetry, approval, retry, or execution artifacts."}
