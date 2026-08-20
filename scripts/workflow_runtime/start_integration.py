"""DWR-2 bridge from an approved Start report to existing workflow controls."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow_runtime import approvals, capabilities, compiler, ownership, state


LEDGER = ownership.LEDGER


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def approval_path(root: Path, workflow_id: str) -> Path:
    return approvals.path(root, workflow_id)


def draft(report: dict[str, Any], run_id: str, disabled: bool = False) -> dict[str, Any]:
    """Create an in-report proposal only; it never creates a workflow artifact."""
    if disabled:
        return {"enabled": False, "state": "disabled", "reason": "--no-workflow requested", "boundary": "No DWR workflow artifact, compiler plan, or approval record will be created for this Start run."}
    navigator = report.get("navigator", {}) if isinstance(report, dict) else {}
    projection = navigator.get("registry_workflow", {}) if isinstance(navigator, dict) else {}
    feature_ids = [str(item) for item in projection.get("feature_ids", []) if isinstance(item, str)]
    return {"enabled": True, "state": "draft", "workflow_id": ownership.suggested_id(run_id), "feature_ids": sorted(set(feature_ids)),
            "boundary": "Draft exists only inside the reviewed Start proposal. No .tailtrail/workflows artifact, execution authority, or stage approval exists before canonical Planning Lock approval."}


def _existing_or_bind(root: Path, run_id: str, workflow_id: str) -> dict[str, Any]:
    try:
        binding = ownership.show(root, workflow_id)
    except ValueError as error:
        if "does not exist" not in str(error): raise
        return ownership.bind(root, run_id, workflow_id)
    if binding.get("tailtrail_run_id") != run_id:
        raise ValueError("workflow draft ID is already bound to another TailTrail run")
    return binding


def _existing_or_declare(root: Path, workflow_id: str, feature_ids: list[str]) -> dict[str, Any]:
    try:
        plan = capabilities.show(root, workflow_id)
    except ValueError as error:
        if "does not exist" not in str(error): raise
        return capabilities.propose(root, workflow_id, feature_ids)
    if [stage.get("capability_id") for stage in plan.get("stages", [])] != feature_ids:
        raise ValueError("existing capability declaration differs from the approved Start draft")
    return plan


def apply_policy_preapproval(root: Path, workflow_id: str) -> dict[str, Any] | None:
    policy = compiler._policy(root.resolve()); selected = policy.get("pre_approved_stages", [])
    if not selected: return None
    compiled = compiler.show(root, workflow_id); stages = {str(row["stage_id"]): row for row in compiled["stages"]}
    unknown = sorted(set(selected) - set(stages))
    if unknown: raise ValueError("workflow compiler policy pre_approved_stages are not in the compiled graph: " + ", ".join(unknown))
    policy_ref = compiler.policy_path(root.resolve()).relative_to(root.resolve()).as_posix()
    return approvals.grant_policy(root, workflow_id, selected, policy_ref)


def activate(root: Path, run_id: str, saved_report: dict[str, Any], anchor_artifact: str | None) -> dict[str, Any]:
    """Persist DWR artifacts only after a canonical Start anchor exists."""
    descriptor = saved_report.get("workflow_runtime", {}) if isinstance(saved_report, dict) else {}
    if not isinstance(descriptor, dict) or not descriptor.get("enabled"):
        return {"state": "disabled", "reason": descriptor.get("reason", "legacy report has no workflow draft"), "boundary": "No DWR workflow was created."}
    if not anchor_artifact:
        return {"state": "not-created", "reason": "canonical requirement anchor is not required for this Start mode", "boundary": "DWR-2 never creates a workflow without an approved anchor."}
    workflow_id = str(descriptor.get("workflow_id", "")); feature_ids = [str(item) for item in descriptor.get("feature_ids", []) if isinstance(item, str)]
    if not workflow_id or not feature_ids: raise ValueError("approved Start workflow draft is incomplete")
    binding = _existing_or_bind(root, run_id, workflow_id)
    declared = _existing_or_declare(root, workflow_id, feature_ids)
    lifecycle = state.create(root, run_id, workflow_id)
    compiled = compiler.compile(root, workflow_id)
    initial_approval = approvals.record_initial(root, workflow_id)
    policy_approval = apply_policy_preapproval(root, workflow_id)
    LEDGER.append_event(root, run_id, "workflow_runtime_activated", {"workflow_id": workflow_id, "binding": binding["artifact"], "capability_plan": declared["artifact"], "compiler_plan": compiled["artifact"], "compiler_plan_fingerprint": compiled["plan_fingerprint"]})
    return {"state": "compiled", "workflow_id": workflow_id, "binding": binding["artifact"], "capability_plan": declared["artifact"], "state_view": {"status": lifecycle["status"], "lifecycle_state": lifecycle["lifecycle_state"]}, "compiler": {"artifact": compiled["artifact"], "revision": compiled["revision"], "plan_fingerprint": compiled["plan_fingerprint"], "template_id": compiled["template_id"]}, "initial_plan_approval": initial_approval.get("record"), "policy_preapproval": policy_approval, "next": "The compiled graph is ready for a later execution adapter; DWR-2 has not dispatched a stage.", "boundary": "Activation persists only TailTrail workflow metadata and does not run project work."}


def show_approvals(root: Path, workflow_id: str) -> dict[str, Any]:
    return approvals.show(root, workflow_id)


def grant_session(root: Path, workflow_id: str, action_classes: list[str], approved: bool, session_id: str = "local-session", expires_at: str | None = None) -> dict[str, Any]:
    return approvals.grant_session(root, workflow_id, action_classes, approved, session_id, expires_at)


def validate_approvals(root: Path, workflow_id: str) -> dict[str, Any]:
    return approvals.validate(root, workflow_id)
