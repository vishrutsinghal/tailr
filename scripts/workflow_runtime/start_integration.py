"""DWR-2 bridge from an approved Start report to existing workflow controls."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow_runtime import approvals, capabilities, compiler, ownership, state, task_scope


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


def execution_authority_policy(saved_report: dict[str, Any]) -> dict[str, Any]:
    """Resolve post-plan authority without weakening material approval gates."""
    mode = str((saved_report.get("aidlc_mode", {}) or {}).get("mode", "lite"))
    sensitive = ["dependency", "recovery", "scan_local", "external_provider", "publish", "deploy", "merge"]
    if isinstance(saved_report.get("spec_kit_source"), dict):
        return {
            "mode": mode, "route": "intent-bridge-slice-gated", "status": "material-gates-retained",
            "auto_granted_action_classes": [],
            "separate_gate_triggers": ["source-revision-change", "slice-amendment", *sensitive],
            "boundary": "Intent Bridge source ownership and the active delivery slice remain authoritative. Approval does not silently authorize a changed source revision or material slice amendment.",
        }
    if mode in {"standard", "full"}:
        return {
            "mode": mode, "route": "official-aidlc-stage-gated", "status": "material-gates-retained",
            "auto_granted_action_classes": [],
            "separate_gate_triggers": ["official-material-stage-transition", "requirement-or-design-amendment", *sensitive],
            "boundary": "The pinned official AI-DLC lifecycle owns material stage transitions. Approval within a stage must not become per-command approval, but TailTrail does not infer the next official stage authority.",
        }
    return {
        "mode": mode, "route": "approved-plan-auto-grant", "status": "safe-local-execution-authorized",
        "auto_granted_action_classes": ["read_local", "write_tailtrail_state", "write_project", "execute_project"],
        "separate_gate_triggers": ["material-scope-change", "requirement-contradiction", *sensitive],
        "boundary": "The approved Lite/Off plan grants only hash-bound safe local work inside the immutable anchor. Sensitive or materially divergent actions still require their designated authority.",
    }


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
    authority = execution_authority_policy(saved_report)
    plan_grant = approvals.grant_approved_plan(root, workflow_id) if authority["route"] == "approved-plan-auto-grant" else None
    LEDGER.append_event(root, run_id, "workflow_runtime_activated", {"workflow_id": workflow_id, "binding": binding["artifact"], "capability_plan": declared["artifact"], "compiler_plan": compiled["artifact"], "compiler_plan_fingerprint": compiled["plan_fingerprint"]})
    return {"state": "compiled", "workflow_id": workflow_id, "binding": binding["artifact"], "capability_plan": declared["artifact"], "state_view": {"status": lifecycle["status"], "lifecycle_state": lifecycle["lifecycle_state"]}, "compiler": {"artifact": compiled["artifact"], "revision": compiled["revision"], "plan_fingerprint": compiled["plan_fingerprint"], "template_id": compiled["template_id"]}, "initial_plan_approval": initial_approval.get("record"), "policy_preapproval": policy_approval, "execution_authority": {**authority, "approval_id": (plan_grant or {}).get("record", {}).get("approval_id")}, "next": "The compiled graph is ready for its host adapter. Safe local stages may reuse the plan-derived grant only when execution_authority says so; no stage was dispatched during activation.", "boundary": "Activation persists TailTrail workflow metadata and bounded authority only; it does not run project work."}


def activate_debug(root: Path, run_id: str, reproduction_contract_ref: str) -> dict[str, Any]:
    """Attach an approved reproduction contract to the native debug template.

    Reproduction approval authorizes investigation through correction proposal.
    It deliberately does not authorize correction implementation, regression
    validation, or closure; those stages retain their own evidence/approval
    boundaries.
    """
    root = root.resolve(); workflow_id = ownership.suggested_id(run_id)
    feature_ids = ["debug-harness", "code-graph-mapper", "requirement-completion-harness", "evidence-aware-testing"]
    binding = _existing_or_bind(root, run_id, workflow_id)
    declared = _existing_or_declare(root, workflow_id, feature_ids)
    compiled = compiler.compile(root, workflow_id)
    if compiled["template_id"] != "debug-investigation":
        raise ValueError("approved debug reproduction did not compile to the debug-investigation template")
    try:
        scope = task_scope.show(root, workflow_id)
    except ValueError as error:
        if "does not exist" not in str(error): raise
        scope = task_scope.initialize(root, workflow_id)
    lifecycle = state.create(root, run_id, workflow_id)
    initial_approval = approvals.record_initial(root, workflow_id)
    investigation = approvals.decide(
        root, workflow_id,
        stage_ids=[f"d-{index:02d}-{name}" for index, name in (
            (1, "intake"), (2, "reproduction"), (3, "project-orientation"),
            (4, "hypothesis-generation"), (5, "experiment"),
            (6, "root-cause-proof"), (7, "correction-proposal"),
        )],
        action_classes=["read_local", "write_tailtrail_state", "execute_project"],
        operation_kind="broad-test-build", operation_ref=reproduction_contract_ref,
        decision="approved",
        rationale="The user approved this exact reproduction revision. Authority is limited to bounded local investigation and evidence recording through correction proposal; project source correction remains separately gated.",
    )
    LEDGER.append_event(root, run_id, "workflow_runtime_activated", {
        "workflow_id": workflow_id, "template_id": compiled["template_id"],
        "compiler_plan_fingerprint": compiled["plan_fingerprint"],
        "investigation_approval_id": investigation["record"]["approval_id"],
    })
    view = state.show(root, workflow_id)
    return {
        "state": "compiled", "workflow_id": workflow_id,
        "binding": binding["artifact"], "capability_plan": declared["artifact"], "task_scope": scope["artifact"],
        "compiler": {"artifact": compiled["artifact"], "revision": compiled["revision"], "plan_fingerprint": compiled["plan_fingerprint"], "template_id": compiled["template_id"]},
        "current_stage": view["current_stage"], "current_stage_display": view.get("current_stage_display"),
        "initial_plan_approval": initial_approval.get("record"),
        "investigation_approval": investigation["record"],
        "next": "Begin at D-01 Intake or resume the shortest dependency-ready debug stage.",
        "boundary": "Reproduction approval covers only D-01 through D-07. D-08 source correction requires a separate exact correction approval; later validation and closure require factual stage evidence.",
    }


def show_approvals(root: Path, workflow_id: str) -> dict[str, Any]:
    return approvals.show(root, workflow_id)


def grant_session(root: Path, workflow_id: str, action_classes: list[str], approved: bool, session_id: str = "local-session", expires_at: str | None = None) -> dict[str, Any]:
    return approvals.grant_session(root, workflow_id, action_classes, approved, session_id, expires_at)


def validate_approvals(root: Path, workflow_id: str) -> dict[str, Any]:
    return approvals.validate(root, workflow_id)
