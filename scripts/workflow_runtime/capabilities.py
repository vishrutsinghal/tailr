"""DWR-B declarative capability and approval bridge.

The runtime may describe only registered TailTrail capabilities.  It never
stores shell command text or dispatches a capability; existing TailTrail
controls remain the only possible execution surface.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workflow_runtime import ownership


ROOT = ownership.ROOT
LEDGER = ownership.LEDGER
LOCK = ownership.LOCK

ACTION_CLASSES = {"read-only", "tailtrail-state", "managed-execution"}
PREAPPROVABLE_CLASSES = {"read-only", "tailtrail-state"}


def _json_digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(body).hexdigest()}"


def _registry() -> dict[str, dict[str, Any]]:
    payload = json.loads((ROOT / "tailtrail-registry.json").read_text(encoding="utf-8"))
    return {str(item["id"]): item for item in payload.get("features", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}


def _workflow_dir(root: Path, workflow_id: str) -> Path:
    return ownership.binding_path(root, workflow_id).parent


def capability_plan_path(root: Path, workflow_id: str) -> Path:
    return _workflow_dir(root.resolve(), workflow_id) / "capability-plan-v1.json"


def preapproval_path(root: Path, workflow_id: str) -> Path:
    return _workflow_dir(root.resolve(), workflow_id) / "preapproval-v1.json"


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _canonical_approval(root: Path, binding: dict[str, Any]) -> dict[str, Any]:
    run_id = str(binding["tailtrail_run_id"])
    lock = LOCK.show(root, run_id)
    if lock.get("status") != "approved" or lock.get("writes_allowed") is not True:
        raise ValueError("DWR-B requires the bound Planning Lock to remain approved")
    official = LEDGER.state_dir(root, run_id) / "aidlc-official" / "requirements" / "approval-v1.json"
    return {
        "type": "official-ai-dlc-requirements" if official.is_file() else "planning-lock",
        "run_id": run_id,
        "planning_lock_ref": binding["planning_lock_ref"],
        "official_stage_approval_ref": _relative(root, official) if official.is_file() else None,
        "status": "approved",
        "boundary": "References the canonical approval only; this bridge creates no second implementation approval.",
    }


def _action_class(feature: dict[str, Any]) -> str:
    # DWR-B does not attach an executor. Non-read-only registered features can
    # therefore only be declared as TailTrail-state controls at this layer.
    return "read-only" if feature.get("read_only") is True else "tailtrail-state"


def _stage(root: Path, binding: dict[str, Any], feature: dict[str, Any], index: int) -> dict[str, Any]:
    capability_id = str(feature["id"])
    action_class = _action_class(feature)
    return {
        "stage_id": f"stage-{index:02d}-{capability_id}",
        "capability_id": capability_id,
        "action_class": action_class,
        "requires_canonical_approval": bool(feature.get("requires_approval")),
        "inputs": {
            "requirement_uids": list(binding["requirement_uids"]),
            "approved_anchor_ref": binding["approved_anchor_ref"],
            "target_identity_fingerprint": binding["target_identity_fingerprint"],
        },
        "declared_evidence_outputs": {
            "evidence_label": feature.get("evidence_label", "none"),
            "registered_mcp_tools": list(feature.get("mcp_tools", [])),
        },
        "execution_authority": "not-implemented",
        "boundary": "Declaration only. Commands are resolved only by existing TailTrail adapters under their own policy and approval checks.",
    }


def _validate_stage(stage: Any, registry: dict[str, dict[str, Any]], binding: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not isinstance(stage, dict):
        return ["stage must be an object"]
    capability_id = stage.get("capability_id")
    feature = registry.get(str(capability_id))
    if feature is None:
        return [f"stage lists unregistered capability `{capability_id}`"]
    action_class = stage.get("action_class")
    if action_class not in ACTION_CLASSES or action_class != _action_class(feature):
        issues.append(f"stage `{capability_id}` action_class does not match registered capability policy")
    if stage.get("requires_canonical_approval") is not bool(feature.get("requires_approval")):
        issues.append(f"stage `{capability_id}` approval requirement does not match the registry")
    if stage.get("execution_authority") != "not-implemented":
        issues.append(f"stage `{capability_id}` attempts to grant unsupported execution authority")
    if "command" in stage or "shell" in stage or "command_text" in stage:
        issues.append(f"stage `{capability_id}` contains prohibited command text")
    inputs = stage.get("inputs")
    if not isinstance(inputs, dict) or inputs.get("requirement_uids") != binding.get("requirement_uids"):
        issues.append(f"stage `{capability_id}` does not bind the approved requirement IDs")
    if not isinstance(inputs, dict) or inputs.get("approved_anchor_ref") != binding.get("approved_anchor_ref"):
        issues.append(f"stage `{capability_id}` does not bind the approved anchor")
    if not isinstance(inputs, dict) or inputs.get("target_identity_fingerprint") != binding.get("target_identity_fingerprint"):
        issues.append(f"stage `{capability_id}` does not bind the target identity")
    return issues


def propose(root: Path, workflow_id: str, capability_ids: list[str]) -> dict[str, Any]:
    root = root.resolve()
    binding = ownership.show(root, workflow_id)
    validation = ownership.validate(root, workflow_id)
    if not validation["valid"]:
        raise ValueError("DWR-B requires a valid DWR-A ownership binding: " + "; ".join(validation["issues"]))
    if not capability_ids:
        raise ValueError("declare at least one registered --capability")
    if len(capability_ids) != len(set(capability_ids)):
        raise ValueError("capabilities must not be repeated in one declarative plan")
    registry = _registry()
    unknown = [item for item in capability_ids if item not in registry]
    if unknown:
        raise ValueError("unregistered capability IDs: " + ", ".join(unknown))
    destination = capability_plan_path(root, workflow_id)
    if destination.exists():
        raise ValueError("a DWR-B capability plan already exists; DWR-C+ owns versioned amendments")
    stages = [_stage(root, binding, registry[capability_id], index) for index, capability_id in enumerate(capability_ids, start=1)]
    payload = {
        "schema_version": "1",
        "type": "tailtrail-workflow-capability-plan",
        "workflow_id": workflow_id,
        "tailtrail_run_id": binding["tailtrail_run_id"],
        "ownership_ref": binding["artifact"],
        "ownership_fingerprint": _json_digest({key: value for key, value in binding.items() if key != "artifact"}),
        "canonical_approval": _canonical_approval(root, binding),
        "stages": stages,
        "state": "declared",
        "boundary": "DWR-B is declarative only. It cannot invoke source edits, tests, scanners, Git, providers, publishing, or arbitrary shell commands.",
    }
    payload["plan_fingerprint"] = _json_digest(payload)
    LEDGER.atomic_json(destination, payload)
    LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_capability_plan_declared", {"workflow_id": workflow_id, "artifact": _relative(root, destination), "capability_ids": capability_ids, "plan_fingerprint": payload["plan_fingerprint"]})
    return {"artifact": _relative(root, destination), **payload}


def show(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve()
    path = capability_plan_path(root, workflow_id)
    if not path.is_file():
        raise ValueError(f"DWR-B capability plan does not exist for `{workflow_id}`")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "tailtrail-workflow-capability-plan" or payload.get("workflow_id") != workflow_id:
        raise ValueError("workflow capability plan is invalid")
    return {"artifact": _relative(root, path), **payload}


def validate(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); issues: list[str] = []
    try:
        binding = ownership.show(root, workflow_id)
        ownership_result = ownership.validate(root, workflow_id)
        if not ownership_result["valid"]:
            issues.extend(ownership_result["issues"])
        plan = show(root, workflow_id)
        if plan.get("tailtrail_run_id") != binding.get("tailtrail_run_id"):
            issues.append("capability plan is bound to a different TailTrail run")
        if plan.get("ownership_ref") != binding.get("artifact"):
            issues.append("capability plan does not reference the canonical ownership binding")
        expected_ownership = _json_digest({key: value for key, value in binding.items() if key != "artifact"})
        if plan.get("ownership_fingerprint") != expected_ownership:
            issues.append("capability plan ownership fingerprint differs from the canonical binding")
        expected_plan = {key: value for key, value in plan.items() if key not in {"artifact", "plan_fingerprint"}}
        if plan.get("plan_fingerprint") != _json_digest(expected_plan):
            issues.append("capability plan fingerprint differs from its declared contents")
        approval = _canonical_approval(root, binding)
        if plan.get("canonical_approval") != approval:
            issues.append("canonical approval reference is stale or mismatched")
        stages = plan.get("stages")
        if not isinstance(stages, list) or not stages:
            issues.append("capability plan must declare at least one stage")
        else:
            registry = _registry()
            ids = [stage.get("stage_id") for stage in stages if isinstance(stage, dict)]
            if len(ids) != len(stages) or len(ids) != len(set(ids)):
                issues.append("capability stage IDs must be unique")
            for stage in stages:
                issues.extend(_validate_stage(stage, registry, binding))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        issues.append(str(error))
    return {"type": "tailtrail-workflow-capability-validation", "workflow_id": workflow_id, "valid": not issues, "status": "valid" if not issues else "blocked", "issues": issues, "boundary": "Validation is read-only. A valid declaration does not grant source, test, scanner, Git, provider, publish, or shell execution authority."}


def grant_preapproval(root: Path, workflow_id: str, stage_ids: list[str], expires_at: str) -> dict[str, Any]:
    root = root.resolve()
    result = validate(root, workflow_id)
    if not result["valid"]:
        raise ValueError("DWR-B cannot grant pre-approval for an invalid plan: " + "; ".join(result["issues"]))
    plan = show(root, workflow_id)
    try:
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("expires-at must be an ISO-8601 timestamp") from error
    if expiry.tzinfo is None or expiry <= datetime.now(UTC):
        raise ValueError("expires-at must be a future timezone-aware timestamp")
    stages = {str(stage["stage_id"]): stage for stage in plan["stages"]}
    if not stage_ids:
        raise ValueError("pre-approval requires at least one --stage-id")
    unknown = [stage_id for stage_id in stage_ids if stage_id not in stages]
    if unknown:
        raise ValueError("unknown stage IDs: " + ", ".join(unknown))
    prohibited = [stage_id for stage_id in stage_ids if stages[stage_id]["action_class"] not in PREAPPROVABLE_CLASSES]
    if prohibited:
        raise ValueError("pre-approval is limited to read-only or TailTrail-state stages: " + ", ".join(prohibited))
    destination = preapproval_path(root, workflow_id)
    payload = {
        "schema_version": "1", "type": "tailtrail-workflow-preapproval", "workflow_id": workflow_id,
        "tailtrail_run_id": plan["tailtrail_run_id"], "plan_fingerprint": plan["plan_fingerprint"],
        "target_identity_fingerprint": plan["stages"][0]["inputs"]["target_identity_fingerprint"],
        "stage_ids": stage_ids, "action_classes": sorted({stages[item]["action_class"] for item in stage_ids}),
        "expires_at": expiry.isoformat(), "state": "active",
        "boundary": "Pre-approval applies only to declared read-only or TailTrail-state actions. It cannot authorize source edits, tests, scanners, Git, providers, publishing, or shell commands.",
    }
    LEDGER.atomic_json(destination, payload)
    LEDGER.append_event(root, plan["tailtrail_run_id"], "workflow_preapproval_granted", {"workflow_id": workflow_id, "artifact": _relative(root, destination), "stage_ids": stage_ids, "expires_at": payload["expires_at"]})
    return {"artifact": _relative(root, destination), **payload}


def show_preapproval(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); path = preapproval_path(root, workflow_id)
    if not path.is_file():
        raise ValueError(f"DWR-B pre-approval does not exist for `{workflow_id}`")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {"artifact": _relative(root, path), **payload}


def validate_preapproval(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); issues: list[str] = []
    try:
        plan_validation = validate(root, workflow_id)
        if not plan_validation["valid"]:
            issues.extend(plan_validation["issues"])
        plan = show(root, workflow_id); grant = show_preapproval(root, workflow_id)
        if grant.get("plan_fingerprint") != plan.get("plan_fingerprint"):
            issues.append("pre-approval is not bound to the current capability plan")
        if grant.get("target_identity_fingerprint") != plan["stages"][0]["inputs"]["target_identity_fingerprint"]:
            issues.append("pre-approval target identity does not match the capability plan")
        if set(grant.get("action_classes", [])) - PREAPPROVABLE_CLASSES:
            issues.append("pre-approval includes a prohibited action class")
        if datetime.fromisoformat(str(grant.get("expires_at", "")).replace("Z", "+00:00")) <= datetime.now(UTC):
            issues.append("pre-approval has expired")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        issues.append(str(error))
    return {"type": "tailtrail-workflow-preapproval-validation", "workflow_id": workflow_id, "valid": not issues, "status": "valid" if not issues else "blocked", "issues": issues, "boundary": "A valid pre-approval remains non-executable and cannot bypass canonical TailTrail gates."}
