"""Define the closed Deferred Phase 4 capability-adapter catalog."""
from __future__ import annotations

from typing import Any


def _adapter(capability_id: str, action_class: str, authority: str, outputs: list[str], *, retry: int = 0, timeout: int = 30) -> dict[str, Any]:
    return {
        "capability_id": capability_id,
        "action_class": action_class,
        "authority": authority,
        "required_outputs": outputs,
        "max_retries": retry,
        "timeout_seconds": timeout,
        "freshness_required": True,
        "evidence_required": True,
        "skip_rule": "explicit-approved-skip-only",
        "failure_rule": "record-categorical-outcome-and-stop",
    }


ADAPTERS: dict[str, dict[str, Any]] = {
    "debug-intake": _adapter(
        "debug-harness", "write_tailtrail_state", "approved-debug-run",
        ["reproduction_contract_ref", "requirement_uid", "safety_boundary", "status"],
    ),
    "debug-reproduction": _adapter(
        "debug-harness", "execute_project", "approved-reproduction-contract",
        ["exact_command", "outcome", "reproduction_fingerprint", "artifact_ref", "status"], timeout=900,
    ),
    "debug-hypothesis": _adapter(
        "debug-harness", "write_tailtrail_state", "debug-hypothesis-ledger",
        ["hypothesis_refs", "requirement_uid", "evidence_gaps", "cycle", "status"],
    ),
    "debug-experiment": _adapter(
        "debug-harness", "execute_project", "approved-debug-experiment",
        ["hypothesis_id", "exact_command", "expected_signal", "outcome", "artifact_ref", "cycle"], timeout=900,
    ),
    "debug-root-cause": _adapter(
        "debug-harness", "write_tailtrail_state", "debug-root-cause-proof",
        ["proven_hypothesis", "supporting_evidence_refs", "eliminated_hypothesis_refs", "status"],
    ),
    "debug-correction-proposal": _adapter(
        "debug-harness", "write_tailtrail_state", "debug-correction-authority",
        ["requirement_uid", "root_cause_ref", "bounded_changed_paths", "preserve_rules", "validation_plan", "status"],
    ),
    "debug-closure": _adapter(
        "debug-harness", "write_tailtrail_state", "tailtrail-closure",
        ["requirement_results", "root_cause_ref", "correction_ref", "regression_refs", "drift_status", "status"],
    ),
    "bootstrap": _adapter(
        "canonical-local-state", "read_local", "canonical-run",
        ["target_identity_ref", "repository_readiness", "policy_refs", "manifest_refs", "languages", "host", "canonical_state_refs"], retry=1,
    ),
    "graph-discovery": _adapter(
        "code-graph-mapper", "write_tailtrail_state", "code-graph-mapper",
        ["graph_ref", "graph_version", "inventory_fingerprint", "freshness", "likely_callers", "likely_tests", "read_order", "evidence_label"], retry=1, timeout=60,
    ),
    "clarification-aidlc": _adapter(
        "aidlc", "write_tailtrail_state", "aidlc-mode-authority",
        ["aidlc_mode", "lifecycle_stage", "approved_requirement_refs", "authority_source", "status"], timeout=120,
    ),
    "planning": _adapter(
        "navigator", "write_tailtrail_state", "navigator",
        ["approved_requirement_refs", "impact_map_ref", "implementation_slices", "evidence_requirements", "status"], timeout=60,
    ),
    "implementation-boundary": _adapter(
        "requirement-completion-harness", "write_project", "host-agent",
        ["source_edit_receipt_refs", "changed_paths", "requirement_uids", "preservation_status", "status"], timeout=900,
    ),
    "focused-testing": _adapter(
        "evidence-aware-testing", "execute_project", "repository-approved-test-config",
        ["exact_command", "outcome", "tier", "environment", "asserted_behavior", "artifact_ref"], timeout=900,
    ),
    "review": _adapter(
        "review", "read_local", "tailtrail-review",
        ["finding_refs", "requirement_findings", "severity_counts", "scope_status", "architecture_status", "behavior_status", "maintainability_status", "preservation_status"], retry=1, timeout=120,
    ),
    "requirement-fulfilment": _adapter(
        "requirement-completion-harness", "write_tailtrail_state", "requirement-completion-harness",
        ["requirement_results", "proof_tier_status", "bounded_next_action", "status"], timeout=120,
    ),
    "security": _adapter(
        "security-vulnerability", "scan_local", "security-policy",
        ["control_type", "outcome", "finding_summary", "artifact_ref", "evidence_boundary"], timeout=900,
    ),
    "quality": _adapter(
        "quality-signals", "scan_local", "quality-policy",
        ["control_type", "outcome", "finding_summary", "artifact_ref", "evidence_boundary"], timeout=900,
    ),
    "handoff": _adapter(
        "program-delivery-orchestrator", "write_tailtrail_state", "program-delivery-handoff",
        ["implementation_refs", "validation_refs", "remaining_risks", "rollout_refs", "rollback_refs", "operations_refs", "status"], timeout=60,
    ),
}


GUARDED_ACTIONS = {"write_project", "execute_project", "scan_local", "external_provider", "publish"}
OUTCOMES = {"pass", "fail", "blocked", "skipped", "timeout", "unavailable"}
STAGE_ADAPTERS = {
    "d-01-intake": "debug-intake", "d-02-reproduction": "debug-reproduction",
    "d-03-project-orientation": "graph-discovery", "d-04-hypothesis-generation": "debug-hypothesis",
    "d-05-experiment": "debug-experiment", "d-06-root-cause-proof": "debug-root-cause",
    "d-07-correction-proposal": "debug-correction-proposal", "d-08-correction-implementation": "implementation-boundary",
    "d-09-regression-validation": "focused-testing", "d-10-closure": "debug-closure",
    "bootstrap": "bootstrap", "discover": "graph-discovery", "graph-impact": "graph-discovery",
    "scope-diff": "bootstrap", "graph-freshness": "graph-discovery", "bounded-discovery": "graph-discovery",
    "graph-overlay": "graph-discovery", "clarify": "clarification-aidlc", "plan": "planning",
    "risk-plan": "planning", "fix-plan": "planning", "optional-fix-proposal": "planning",
    "implement": "implementation-boundary", "focused-test": "focused-testing", "focused-validation": "focused-testing",
    "tests": "focused-testing", "review": "review", "root-cause": "review", "architecture-summary": "review",
    "fulfilment": "requirement-fulfilment", "security": "security", "quality": "quality", "handoff": "handoff",
    "ingest-finding": "quality", "finding-recheck": "quality",
}


def get(adapter_id: str) -> dict[str, Any]:
    if adapter_id not in ADAPTERS:
        raise ValueError(f"unknown workflow adapter `{adapter_id}`")
    return {"adapter_id": adapter_id, **ADAPTERS[adapter_id]}


def list_all() -> list[dict[str, Any]]:
    return [get(adapter_id) for adapter_id in ADAPTERS]


def for_stage(stage_id: str, capability_id: str) -> dict[str, Any]:
    adapter_id = STAGE_ADAPTERS.get(stage_id)
    if adapter_id is None:
        matches = [item for item in list_all() if item["capability_id"] == capability_id]
        if len(matches) != 1: raise ValueError(f"no unambiguous adapter exists for stage `{stage_id}` and capability `{capability_id}`")
        return matches[0]
    value = get(adapter_id)
    if value["capability_id"] != capability_id: raise ValueError(f"stage `{stage_id}` capability does not match adapter `{adapter_id}`")
    return value
