#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
PYTHON = sys.executable
DEFAULT_READ_ONLY_TOOLS = (
    "navigator_plan",
    "intent_resolve",
    "start_report",
    "guardrail_check",
    "graph_map",
    "install_status",
    "eval_scenario_list",
    "eval_scenario_report",
    "ledger_state",
    "anchor_show",
    "harness_checkpoint_show",
    "completion_feedback_show",
    "profile_view",
    "validation_receipt_show",
    "release_confidence_show",
    "git_readiness",
    "recovery_boundary_show",
    "recovery_reconciliation_show",
    "architecture_assessment_show",
    "maintainability_assessment_show",
    "context_continuity_show",
    "context_continuity_render",
    "context_continuity_advisory_show",
    "completion_report_show",
    "execution_evidence_show",
    "workflow_dashboard_show",
    "planning_lock_show",
    "planning_decision_show",
    "planning_investigation_show",
    "planning_revision_show",
    "planning_authority_show",
    "planning_aidlc_question_show",
    "planning_aidlc_question_clarify",
    "planning_question_context_show",
    "requirement_intake_show",
    "aidlc_official_status",
    "aidlc_official_bridge_show",
    "aidlc_official_state_show",
    "aidlc_official_sanitize_validate",
    "aidlc_official_session_status",
    "host_conformance_report",
    "presentation_conformance",
    "maintainability_inventory",
    "real_evaluation_portfolio_report",
    "adoption_validation_report",
    "enterprise_conformance_report",
    "enterprise_target_policy_inspect",
    "spec_kit_detect",
    "spec_kit_mapping_show",
    "spec_kit_convergence_show",
    "debug_intake_show",
    "debug_reproduction_show",
    "debug_reproduction_attempt_show",
    "debug_orientation_show",
    "debug_hypothesis_ledger_show",
    "debug_correction_show",
    "debug_governance_show",
    "debug_evaluation_report",
    "debug_release_gate",
    "debug_harness_convergence_show",
    "debug_completion_report_show",
    "debug_preflight",
    "tailtrail_session_status",
)
LEGACY_CONTROLLED_TOOLS = ("tailtrail_stop", "tailtrail_resume", "harness_control_check", "planning_aidlc_question_challenge", "planning_aidlc_question_record", "planning_aidlc_question_approve", "source_patch_apply", "planning_lock_start", "planning_investigate", "planning_revision_propose", "planning_revision_approve", "planning_aidlc_standard_propose", "planning_aidlc_standard_approve", "planning_lock_approve", "tailtrail_start", "navigator_scope_proposal_record", "execution_evidence_record", "execution_evidence_run", "spec_kit_import", "spec_kit_amendment_propose", "spec_kit_anchor_approve", "spec_kit_convergence_record", "spec_kit_ci_ingest", "debug_start", "debug_reproduction_draft", "debug_reproduction_revise", "debug_reproduction_reopen", "debug_reproduction_approve", "debug_reproduction_attempt_record", "debug_orientation_create", "debug_hypothesis_add", "debug_hypothesis_reprioritize", "debug_experiment_propose", "debug_experiment_record", "debug_root_cause_prove", "debug_correction_propose", "debug_correction_approve", "debug_correction_scope_check", "debug_harness_convergence_finalize", "debug_closure_finalize", "debug_evaluation_run")
WORKFLOW_READ_ONLY_TOOLS = ("workflow_list", "workflow_show", "workflow_status", "workflow_current", "workflow_compiler_show", "workflow_approvals_show", "workflow_freshness_show", "workflow_evidence_show", "workflow_resume", "workflow_doctor", "workflow_replay", "workflow_ci_show", "workflow_assurance_inspect", "workflow_denials_show", "workflow_retention_show", "workflow_retention_plan", "workflow_release_catalog", "workflow_release_show", "workflow_release_compatibility", "workflow_release_evaluate", "workflow_enterprise_entry", "workflow_enterprise_show", "workflow_enterprise_replay", "workflow_enterprise_observe", "workflow_enterprise_restore_validate", "workflow_enterprise_migration_plan", "workflow_enterprise_conformance")
WORKFLOW_CONTROLLED_TOOLS = ("workflow_create", "workflow_approval_decide", "workflow_state_control", "workflow_adapter_record", "workflow_correction_request", "workflow_closure_finalize", "workflow_ci_ingest", "workflow_retention_cleanup", "workflow_release_scenario_record", "workflow_real_run_record", "workflow_release_retire", "workflow_enterprise_policy_record", "workflow_enterprise_activate", "workflow_enterprise_link", "workflow_enterprise_lease_acquire", "workflow_enterprise_lease_release", "workflow_enterprise_ingest", "workflow_enterprise_backup", "workflow_enterprise_migrate", "workflow_enterprise_rollback")
LEGACY_CONTROLLED_TOOLS = ("requirement_intake_answer", *LEGACY_CONTROLLED_TOOLS)
WORKFLOW_MCP_TOOLS = (*WORKFLOW_READ_ONLY_TOOLS, *WORKFLOW_CONTROLLED_TOOLS)
CONTROLLED_TOOLS = (*LEGACY_CONTROLLED_TOOLS, *WORKFLOW_CONTROLLED_TOOLS)
DENIED_TOOL_TERMS = (
    "apply",
    "build",
    "capture",
    "commit",
    "delete",
    "deploy",
    "edit",
    "fix",
    "install",
    "learn",
    "mutate",
    "push",
    "run",
    "scan",
    "test",
    "update",
    "write",
)


def load_registry() -> Any | None:
    path = ROOT / "scripts" / "tailtrail-registry.py"
    spec = importlib.util.spec_from_file_location("tailtrail_registry_for_mcp", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def registry_read_only_tools() -> tuple[str, ...]:
    return DEFAULT_READ_ONLY_TOOLS


LEGACY_READ_ONLY_TOOLS = registry_read_only_tools()
READ_ONLY_TOOLS = (*LEGACY_READ_ONLY_TOOLS, *WORKFLOW_READ_ONLY_TOOLS)
TOOL_ORDER = (*LEGACY_READ_ONLY_TOOLS, *LEGACY_CONTROLLED_TOOLS, *WORKFLOW_MCP_TOOLS)


def script(name: str) -> Path:
    return ROOT / "scripts" / name


def json_schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


def scope_tool_output_schema() -> dict[str, Any]:
    """Describe the shared JSON/Markdown envelope for scope-aware tools."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["tool", "result", "requirement_route", "scope_contract", "host_reasoning_packet", "run_created", "execution"],
        "properties": {
            "tool": {"type": "string"},
            "result": {"type": ["object", "string"]},
            "requirement_route": {
                "type": ["object", "null"],
                "description": "Typed requirement-before-scope projection. A deferred route forbids graph work, owner questions, and Planning Lock creation.",
                "additionalProperties": False,
                "required": [
                    "schema_version", "type", "state", "requirements_state",
                    "route", "scope_question_allowed", "open_material_decision_ids",
                    "intake_id", "reason_code", "boundary"
                ],
                "properties": {
                    "schema_version": {"const": "1"},
                    "type": {"const": "tailtrail-requirement-route-projection"},
                    "state": {"enum": ["eligible", "deferred"]},
                    "requirements_state": {"type": "string"},
                    "route": {"type": ["string", "null"]},
                    "scope_question_allowed": {"type": "boolean"},
                    "open_material_decision_ids": {"type": "array", "items": {"type": "string"}},
                    "intake_id": {"type": ["string", "null"]},
                    "reason_code": {"type": "string"},
                    "boundary": {"type": "string"},
                },
            },
            "scope_contract": {
                "type": ["object", "null"],
                "description": "Canonical v2 scope projection; its normalized decision fingerprint is identical across CLI, MCP, Codex, Copilot, and Claude.",
            },
            "host_reasoning_packet": {
                "type": ["object", "null"],
                "description": "Sanitized, fingerprint-bound packet supplied only when the active host may refine supported alternatives.",
            },
            "run_created": {"type": "boolean"},
            "execution": {"type": "object"},
        },
    }


def workflow_tool_definitions() -> dict[str, dict[str, Any]]:
    read = {"root":{"type":"string"}, "workflow_id":{"type":"string"}}
    controlled = {**read, "approved":{"type":"boolean"}}
    names = {"workflow_list":("List canonical local workflow projections. Read-only.", {"root":{"type":"string"}}), "workflow_show":("Show canonical workflow state. Read-only.",read), "workflow_status":("Show canonical workflow status. Read-only.",read), "workflow_current":("Show current requirement and stage. Read-only.",read), "workflow_compiler_show":("Show frozen compiler plan. Read-only.",read), "workflow_approvals_show":("Show scoped approvals. Read-only.",read), "workflow_freshness_show":("Show freshness and stale reasons. Read-only.",read), "workflow_evidence_show":("Show evidence and completion receipt. Read-only.",read), "workflow_resume":("Show shortest safe resume recommendation. Read-only.",read), "workflow_doctor":("Run local workflow doctor. Read-only.",read), "workflow_replay":("Replay local workflow journal. Read-only.",read), "workflow_ci_show":("Show policy-backed CI continuation receipts. Read-only.",read), "workflow_create":("Create state only from an approved canonical run; requires explicit approval.",{**controlled,"run_id":{"type":"string"}}), "workflow_approval_decide":("Record a scoped stage decision after explicit approval; never executes work.",{**controlled,"stage_ids":{"type":"array","items":{"type":"string"}},"action_classes":{"type":"array","items":{"type":"string"}},"operation_kind":{"type":"string"},"operation_ref":{"type":"string"},"decision":{"enum":["approved","rejected","edited"]},"rationale":{"type":"string"}}), "workflow_state_control":("Pause, resume, cancel, or supersede local workflow state after explicit approval.",{**controlled,"action":{"enum":["pause","resume","cancel","supersede"]},"successor_workflow_id":{"type":"string"}}), "workflow_adapter_record":("Record a typed saved host result after explicit approval; never executes it.",{**controlled,"stage_id":{"type":"string"},"adapter_id":{"type":"string"},"result_ref":{"type":"string"}}), "workflow_correction_request":("Request bounded correction/replan routing after explicit approval.",{**controlled,"stage_id":{"type":"string"},"classification":{"type":"string"},"max_cycles":{"type":"integer","minimum":1,"maximum":2}}), "workflow_closure_finalize":("Finalize canonical workflow closure after explicit approval.",{**controlled,"accept_evidence_incomplete":{"type":"boolean"}}), "workflow_ci_ingest":("Ingest one linked policy-approved CI receipt and advance metadata only.",{**controlled,"receipt_ref":{"type":"string"},"policy_ref":{"type":"string"}})}
    required = {"workflow_create":["run_id","approved"], "workflow_approval_decide":["workflow_id","stage_ids","action_classes","operation_kind","operation_ref","decision","rationale","approved"], "workflow_state_control":["workflow_id","action","approved"], "workflow_adapter_record":["workflow_id","stage_id","adapter_id","result_ref","approved"], "workflow_correction_request":["workflow_id","stage_id","approved"], "workflow_closure_finalize":["workflow_id","approved"], "workflow_ci_ingest":["workflow_id","receipt_ref","policy_ref","approved"]}
    names.update({"workflow_assurance_inspect":("Inspect runtime integrity and privacy categorically. Read-only.",read),"workflow_denials_show":("Show sanitized categorical denial audit. Read-only.",read),"workflow_retention_show":("Show local retention policy without scanning or deleting.",{"root":{"type":"string"},"policy_ref":{"type":"string"}}),"workflow_retention_plan":("Plan count-based terminal retention without deleting.",{"root":{"type":"string"},"policy_ref":{"type":"string"}}),"workflow_retention_cleanup":("Delete exactly one fingerprint-bound terminal retention candidate after explicit approval.",{**controlled,"plan_fingerprint":{"type":"string"},"policy_ref":{"type":"string"}})})
    required.update({"workflow_retention_cleanup":["workflow_id","plan_fingerprint","approved"]})
    names.update({"workflow_release_catalog":("List the closed Phase 11 scenario and template catalog. Read-only.",{"root":{"type":"string"}}),"workflow_release_show":("Show sanitized Phase 11 evidence. Read-only.",{"root":{"type":"string"}}),"workflow_release_compatibility":("Assess migration and compatibility without changing history. Read-only.",{"root":{"type":"string"}}),"workflow_release_evaluate":("Evaluate the fail-closed Phase 11 release gate. Read-only.",{"root":{"type":"string"}}),"workflow_release_scenario_record":("Record one approved linked deterministic scenario observation.",{**controlled,"observation_ref":{"type":"string"}}),"workflow_real_run_record":("Record one approved linked sanitized real-run observation.",{**controlled,"observation_ref":{"type":"string"}}),"workflow_release_retire":("Record separate retirement approval only for an exact passing release gate.",{"root":{"type":"string"},"gate_fingerprint":{"type":"string"},"approved":{"type":"boolean"}})})
    required.update({"workflow_release_scenario_record":["workflow_id","observation_ref","approved"],"workflow_real_run_record":["workflow_id","observation_ref","approved"],"workflow_release_retire":["gate_fingerprint","approved"]})
    names.update({
        "workflow_enterprise_entry":("Assess Phase 12 evidence and governance entry criteria. Read-only.",{"root":{"type":"string"},"policy_id":{"type":"string"}}),
        "workflow_enterprise_show":("Show one optional enterprise binding. Read-only.",read),
        "workflow_enterprise_replay":("Replay sanitized enterprise transport metadata. Read-only.",read),
        "workflow_enterprise_observe":("Show centralized sanitized enterprise projection. Read-only.",read),
        "workflow_enterprise_restore_validate":("Validate a metadata backup without restoring or overwriting state.",{"root":{"type":"string"},"backup_ref":{"type":"string"}}),
        "workflow_enterprise_migration_plan":("Plan local/enterprise continuation migration. Read-only.",{**read,"direction":{"enum":["local-to-enterprise","enterprise-to-local"]}}),
        "workflow_enterprise_conformance":("Evaluate Phase 12 isolation, replay, recovery, migration, cost, privacy, and closure controls. Read-only.",read),
        "workflow_enterprise_policy_record":("Record an approved enterprise entry policy; does not activate it.",{"root":{"type":"string"},"policy_ref":{"type":"string"},"approved":{"type":"boolean"}}),
        "workflow_enterprise_activate":("Bind an eligible canonical workflow to an optional adapter after explicit approval.",{**controlled,"policy_id":{"type":"string"},"tenant_id":{"type":"string"},"repository_id":{"type":"string"},"actor_id":{"type":"string"}}),
        "workflow_enterprise_link":("Record a read-only cross-repository parent/child identity link.",{**controlled,"identity_ref":{"type":"string"},"actor_id":{"type":"string"}}),
        "workflow_enterprise_lease_acquire":("Acquire a bounded tenant/actor lease and new fencing token.",{**controlled,"tenant_id":{"type":"string"},"actor_id":{"type":"string"}}),
        "workflow_enterprise_lease_release":("Release the exact active fenced lease.",{**controlled,"tenant_id":{"type":"string"},"actor_id":{"type":"string"},"lease_id":{"type":"string"},"fencing_token":{"type":"string"}}),
        "workflow_enterprise_ingest":("Ingest one approved ordered sanitized transport receipt.",{**controlled,"receipt_ref":{"type":"string"}}),
        "workflow_enterprise_backup":("Create a bounded verified metadata backup manifest.",controlled),
        "workflow_enterprise_migrate":("Apply an exact approved local/enterprise continuation migration plan.",{**controlled,"direction":{"enum":["local-to-enterprise","enterprise-to-local"]},"migration_fingerprint":{"type":"string"}}),
        "workflow_enterprise_rollback":("Roll back an exact applied enterprise migration to local continuation.",{**controlled,"migration_fingerprint":{"type":"string"}}),
    })
    required.update({
        "workflow_enterprise_entry":["policy_id"],"workflow_enterprise_restore_validate":["backup_ref"],"workflow_enterprise_migration_plan":["workflow_id","direction"],
        "workflow_enterprise_policy_record":["policy_ref","approved"],"workflow_enterprise_activate":["workflow_id","policy_id","tenant_id","repository_id","actor_id","approved"],
        "workflow_enterprise_link":["workflow_id","identity_ref","actor_id","approved"],"workflow_enterprise_lease_acquire":["workflow_id","tenant_id","actor_id","approved"],
        "workflow_enterprise_lease_release":["workflow_id","tenant_id","actor_id","lease_id","fencing_token","approved"],"workflow_enterprise_ingest":["workflow_id","receipt_ref","approved"],
        "workflow_enterprise_backup":["workflow_id","approved"],"workflow_enterprise_migrate":["workflow_id","direction","migration_fingerprint","approved"],
        "workflow_enterprise_rollback":["workflow_id","migration_fingerprint","approved"]})
    return {name:{"name":name,"description":names[name][0],"inputSchema":json_schema(names[name][1], required.get(name, [] if name == "workflow_list" else ["workflow_id"]))} for name in WORKFLOW_MCP_TOOLS}


def tool_definitions() -> dict[str, dict[str, Any]]:
    return {
        "navigator_plan": {
            "name": "navigator_plan",
            "description": "Return a TailTrail Navigator plan plus its canonical v2 scope contract. Read-only; hosts may explain the evidence but cannot reclassify paths, replace the decision fingerprint, implement, scan, or edit files.",
            "inputSchema": json_schema(
                {
                    "goal": {"type": "string"},
                    "root": {"type": "string"},
                    "changed": {"type": "array", "items": {"type": "string"}},
                    "format": {"type": "string", "enum": ["json", "markdown"]},
                },
                ["goal"],
            ),
            "outputSchema": scope_tool_output_schema(),
            "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
        },
        "intent_resolve": {
            "name": "intent_resolve",
            "description": "Resolve loose user words to one typed TailTrail operation. Read-only; never creates a run, infers approval, executes work, or grants authority.",
            "inputSchema": json_schema(
                {
                    "text": {"type": "string", "minLength": 1, "maxLength": 8192},
                    "active_state": {
                        "type": "string",
                        "enum": ["none", "awaiting-approval", "active", "closure-ready", "detached", "ambiguous"],
                    },
                },
                ["text"],
            ),
        },
        "start_report": {
            "name": "start_report",
            "description": "Return a non-persisted TailTrail Start report plus its canonical v2 scope contract. Read-only; does not edit files, create authority, or capture learnings.",
            "inputSchema": json_schema(
                {
                    "goal": {"type": "string"},
                    "root": {"type": "string"},
                    "changed": {"type": "array", "items": {"type": "string"}},
                    "verbose": {"type": "boolean"},
                    "format": {"type": "string", "enum": ["json", "markdown"]},
                },
                ["goal"],
            ),
            "outputSchema": scope_tool_output_schema(),
            "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
        },
        "guardrail_check": {
            "name": "guardrail_check",
            "description": "Run the deterministic guardrail checker on a supplied diff or safe staged diff. Read-only.",
            "inputSchema": json_schema(
                {
                    "root": {"type": "string"},
                    "diff": {"type": "string"},
                    "fail_on": {"type": "array", "items": {"type": "string"}},
                    "enforce": {"type": "boolean"},
                    "format": {"type": "string", "enum": ["json", "markdown"]},
                }
            ),
        },
        "graph_map": {
            "name": "graph_map",
            "description": "Return Code Review Graph Lite read-order guidance. Read-only; does not refresh heavy graph caches.",
            "inputSchema": json_schema(
                {
                    "root": {"type": "string"},
                    "changed": {"type": "array", "items": {"type": "string"}},
                    "format": {"type": "string", "enum": ["json", "markdown"]},
                }
            ),
        },
        "install_status": {
            "name": "install_status",
            "description": "Read TailTrail install manifest state and report Core/Extended/unknown status.",
            "inputSchema": json_schema({"root": {"type": "string"}}),
        },
        "eval_scenario_list": {
            "name": "eval_scenario_list",
            "description": "List committed Evaluation Harness scenarios. Read-only; does not run live agents, scanners, tests, or write reports.",
            "inputSchema": json_schema({"format": {"type": "string", "enum": ["json", "markdown"]}}),
        },
        "eval_scenario_report": {
            "name": "eval_scenario_report",
            "description": "Return a deterministic Evaluation Harness scenario report from committed fixtures. Read-only; does not write result files.",
            "inputSchema": json_schema(
                {
                    "scenario": {"type": "string"},
                    "format": {"type": "string", "enum": ["json", "markdown"]},
                },
                ["scenario"],
            ),
        },
        "ledger_state": {"name": "ledger_state", "description": "Read the append-only local run projection. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "anchor_show": {"name": "anchor_show", "description": "Read an approved local change-intent anchor. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "harness_checkpoint_show": {"name": "harness_checkpoint_show", "description": "Read the latest or named requirement checkpoint. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "checkpoint": {"type": "integer", "minimum": 1}}, ["run_id"])},
        "completion_feedback_show": {"name": "completion_feedback_show", "description": "Read the latest completion review and bounded feedback packet. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "profile_view": {"name": "profile_view", "description": "Validate and display a repository testing profile. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "profile": {"type": "string"}}, ["profile"])},
        "validation_receipt_show": {"name": "validation_receipt_show", "description": "Read a requirement-linked validation receipt by filename. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "receipt": {"type": "string"}}, ["run_id", "receipt"])},
        "release_confidence_show": {"name": "release_confidence_show", "description": "Read the latest tier-labelled release confidence assessment. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "git_readiness": {"name": "git_readiness", "description": "Return the read-only Mode A Git readiness report.", "inputSchema": json_schema({"root": {"type": "string"}})},
        "recovery_boundary_show": {"name": "recovery_boundary_show", "description": "Read the Mode A task recovery boundary. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "recovery_reconciliation_show": {"name": "recovery_reconciliation_show", "description": "Read the latest task recovery conflict classification. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "architecture_assessment_show": {"name": "architecture_assessment_show", "description": "Read the latest Architecture Fitness assessment. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "maintainability_assessment_show": {"name": "maintainability_assessment_show", "description": "Read the latest Maintainability Harness assessment. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "context_continuity_show": {"name": "context_continuity_show", "description": "Read a saved Context Continuity V1 state and packet. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "sequence": {"type": "integer", "minimum": 1}}, ["run_id"])},
        "context_continuity_render": {"name": "context_continuity_render", "description": "Preview a deterministic Context Continuity V1/V2 packet without writing state, editing source, running tests, or calling a model. An optional repository-relative policy can add template guidance only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "requirement_uid": {"type": "string"}, "trigger": {"type": "string"}, "policy": {"type": "string"}}, ["run_id"])},
        "context_continuity_advisory_show": {"name": "context_continuity_advisory_show", "description": "Read a saved Context Continuity V3 advisory validation record. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "sequence": {"type": "integer", "minimum": 1}}, ["run_id"])},
        "completion_report_show": {"name": "completion_report_show", "description": "Read a saved end-of-task TailTrail Completion Report. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "sequence": {"type": "integer", "minimum": 1}}, ["run_id"])},
        "execution_evidence_show": {"name": "execution_evidence_show", "description": "Read the saved run-local execution evidence stream. Read-only; it never runs commands or turns chat text into proof.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "workflow_dashboard_show": {"name": "workflow_dashboard_show", "description": "Read the current local TailTrail requirement, checkpoint, drift, evidence, and recovery dashboard. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "planning_lock_show": {"name": "planning_lock_show", "description": "Read one TailTrail Planning Lock. Read-only; reports whether managed writes are still blocked or approved.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "planning_decision_show": {"name": "planning_decision_show", "description": "Read a compact Interactive Plan decision summary: current lock, discussion count, revision state, and AIDLC/Intent Bridge routes. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "planning_investigation_show": {"name": "planning_investigation_show", "description": "Read a saved sanitized bounded planning investigation receipt. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "sequence": {"type": "integer", "minimum": 1}}, ["run_id"])},
        "planning_revision_show": {"name": "planning_revision_show", "description": "Read the current or named proposed Interactive Plan revision. Read-only; it never activates the plan.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "revision": {"type": "integer", "minimum": 2}}, ["run_id"])},
        "planning_authority_show": {"name": "planning_authority_show", "description": "Read the latest AIDLC or Intent Bridge revision authority route. Read-only; it never changes requirements or source.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "sequence": {"type": "integer", "minimum": 1}}, ["run_id"])},
        "planning_aidlc_question_show": {"name": "planning_aidlc_question_show", "description": "Read one saved AIDLC question, options, recommendation, and reasoning. Read-only planning evidence.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "question_id": {"type": "string"}}, ["run_id", "question_id"])},
        "planning_aidlc_question_clarify": {"name": "planning_aidlc_question_clarify", "description": "Read saved evidence for explaining or plainly rephrasing one AIDLC question. It does not change the question, plan, or source.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "question_id": {"type": "string"}}, ["run_id", "question_id"])},
        "planning_question_context_show": {"name": "planning_question_context_show", "description": "Read the saved Question Orchestrator context, authority, known facts, unresolved decisions, and source boundary for one planning run. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "requirement_intake_show": {"name": "requirement_intake_show", "description": "Read one durable pre-lock requirement intake with its bounded, advisory repository evidence. It grants no scope, Planning Lock, or implementation authority.", "inputSchema": json_schema({"root": {"type": "string"}, "intake_id": {"type": "string"}}, ["intake_id"])},
        "aidlc_official_status": {"name": "aidlc_official_status", "description": "Read and validate a pinned official AWS AI-DLC pack manifest. Read-only; it never installs, attaches, or executes the pack.", "inputSchema": json_schema({"root": {"type": "string"}, "manifest": {"type": "string"}})},
        "aidlc_official_bridge_show": {"name": "aidlc_official_bridge_show", "description": "Read a saved official AI-DLC bridge identity for one TailTrail run. Read-only; Phase B never attaches or executes the official engine.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "aidlc_official_state_show": {"name": "aidlc_official_state_show", "description": "Project canonical run state and report ownership conflicts. Read-only; it never reconciles or rewrites artifacts.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "aidlc_official_sanitize_validate": {"name": "aidlc_official_sanitize_validate", "description": "Validate one repository-local official AI-DLC artifact against the fail-closed sensitive-data boundary. Read-only; rejected values are never returned.", "inputSchema": json_schema({"root": {"type": "string"}, "input": {"type": "string"}, "context": {"type": "string", "enum": ["bridge", "activation", "requirements", "requirements-revision", "checkpoint", "closure", "learning", "evaluation", "runtime-session", "runtime-transition"]}}, ["input", "context"])},
        "aidlc_official_session_status": {"name": "aidlc_official_session_status", "description": "Read the verified official AI-DLC runtime attachment and ordered transition projection. Read-only; it never attaches, imports receipts, or executes the pack.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "host_conformance_report": {"name": "host_conformance_report", "description": "Report instruction and real-host runtime conformance separately for Codex, Copilot, or Claude. Read-only; missing receipts remain not-validated.", "inputSchema": json_schema({"root": {"type": "string"}, "host": {"type": "string", "enum": ["codex", "copilot", "claude"]}})},
        "presentation_conformance": {"name":"presentation_conformance","description":"Validate canonical plan, debug, and closure presentation semantics across CLI, MCP, Codex, Copilot, and Claude fixtures. Read-only; no live-host success is inferred.","inputSchema":json_schema({})},
        "maintainability_inventory": {"name":"maintainability_inventory","description":"Return the deterministic PM-4 registry, module-direction, budget, and documentation-owner inventory. Read-only; no source is executed or rewritten.","inputSchema":json_schema({"root":{"type":"string"}})},
        "real_evaluation_portfolio_report": {"name":"real_evaluation_portfolio_report","description":"Return PM-5 task coverage, retained outcome counts, and the current claim boundary. Read-only; it never runs models or creates observations.","inputSchema":json_schema({"root":{"type":"string"}})},
        "adoption_validation_report": {"name":"adoption_validation_report","description":"Return PM-7 usability-trial coverage, friction metrics, threshold gates, safety posture, and evidence-backed wording/default recommendations. Read-only; it never records trials or edits product defaults.","inputSchema":json_schema({"root":{"type":"string"}})},
        "enterprise_conformance_report": {"name":"enterprise_conformance_report","description":"Return the static PM-6 enterprise control inventory, compatibility matrix, and hosted-evidence boundary. Read-only; local probes and external systems are not run.","inputSchema":json_schema({"root":{"type":"string"}})},
        "enterprise_target_policy_inspect": {"name": "enterprise_target_policy_inspect", "description": "Evaluate a repository-local enterprise target policy against one selected root. Read-only; it never creates a Planning Lock, edits source, or writes an audit receipt.", "inputSchema": json_schema({"root": {"type": "string"}, "policy": {"type": "string"}, "actor": {"type": "string"}, "target_alias": {"type": "string"}}, ["policy"])},
        "spec_kit_detect": {"name": "spec_kit_detect", "description": "Inspect a local Spec Kit feature. Read-only; it never imports or changes Spec Kit artifacts.", "inputSchema": json_schema({"root": {"type": "string"}, "feature": {"type": "string"}}, ["feature"])},
        "spec_kit_mapping_show": {"name": "spec_kit_mapping_show", "description": "Read the active Spec Kit requirement mapping and slices for a TailTrail run.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "spec_kit_convergence_show": {"name": "spec_kit_convergence_show", "description": "Read the latest saved Spec Kit convergence report. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "debug_intake_show": {"name": "debug_intake_show", "description": "Read the saved Debug Harness intake report and failure fingerprint for a run. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "debug_reproduction_show": {"name": "debug_reproduction_show", "description": "Read the saved Debug Harness reproduction contract for a run. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "debug_reproduction_attempt_show": {"name": "debug_reproduction_attempt_show", "description": "Read factual pre-fix/post-fix reproduction attempt state and any sanitized request for missing user input. Read-only; contract approval alone is never reported as reproduction proof.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "debug_orientation_show": {"name": "debug_orientation_show", "description": "Read the versioned Debug Harness project orientation, graph freshness, evidence labels, and refresh proposal. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "debug_hypothesis_ledger_show": {"name": "debug_hypothesis_ledger_show", "description": "Read the saved Debug Harness hypothesis ledger for a run, including cycle-limit and investigation-blocked state. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "debug_correction_show": {"name": "debug_correction_show", "description": "Read the current proposed or approved Debug correction packet. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "debug_governance_show": {"name": "debug_governance_show", "description": "Read the current Debug privacy, token, continuity, and learning-governance receipt. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "debug_evaluation_report": {"name":"debug_evaluation_report","description":"Read the saved ten-scenario deterministic Debug evaluation report. Read-only.","inputSchema":json_schema({"root":{"type":"string"}})},
        "debug_release_gate": {"name":"debug_release_gate","description":"Evaluate the fail-closed Debug release gate from saved deterministic and real-host evidence. Read-only.","inputSchema":json_schema({"root":{"type":"string"}})},
        "debug_harness_convergence_show": {"name": "debug_harness_convergence_show", "description": "Read the saved DI-8 per-requirement selected Harness table, or preview deterministic Harness selection when no convergence exists. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "debug_completion_report_show": {"name": "debug_completion_report_show", "description": "Read the non-authoritative Debug Harness closure section for a run, including its domain-capped confidence_state. The canonical Completion Report retains delivery and acceptance authority. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "debug_preflight": {"name": "debug_preflight", "description": "Create one deterministic, bounded, read-only evidence packet before host-assisted Debug Start. It inspects capped current-source slices, focused tests, configuration, and explicitly referenced local artifacts; it never runs project commands or creates a Planning Lock. An unresolved local helper remains a partial trace with correction scope blocked, but the handoff continues when an artifact or bounded reproduction route exists. Ask for user evidence only when reproduction and external context are unavailable. The active host should perform one reasoning pass over this packet rather than scanning the repository independently.", "inputSchema": json_schema({"goal": {"type": "string"}, "root": {"type": "string"}, "host": {"type": "string", "enum": ["codex", "copilot", "claude"]}}, ["goal", "host"]), "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}},
        "tailtrail_session_status": {"name": "tailtrail_session_status", "description": "Read the current common TailTrail conversation attachment and safe point. It never scans source, attaches a run, or grants authority.", "inputSchema": json_schema({"root": {"type": "string"}, "context_key": {"type": "string"}}), "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}},
        "requirement_intake_answer": {"name": "requirement_intake_answer", "description": "Record bounded user answers as a new pre-lock intake revision. Requires approved: true and grants no delivery authority.", "inputSchema": json_schema({"root": {"type": "string"}, "intake_id": {"type": "string"}, "answers": {"type": "object", "additionalProperties": {"type": "string"}, "maxProperties": 3}, "approved": {"type": "boolean"}}, ["intake_id", "answers", "approved"])},
        "tailtrail_stop": {"name": "tailtrail_stop", "description": "Detach TailTrail routing at the next atomic metadata boundary while preserving the exact run. The host must supply confirmed: true for the explicit user stop request. It never rejects, cancels, approves, executes, or deletes the run.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "context_key": {"type": "string"}, "confirmed": {"type": "boolean"}}, ["confirmed"]), "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}},
        "tailtrail_resume": {"name": "tailtrail_resume", "description": "Reattach one exact saved TailTrail run after integrity and target freshness checks. It never resumes workflow execution, approves a plan, or restores expired authority.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "context_key": {"type": "string"}}, ["run_id"]), "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}},
        "harness_control_check": {"name": "harness_control_check", "description": "Run only the supplied repository-native control list after explicit approval and an approved matching Planning Lock. It cannot edit source or run an arbitrary command.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "controls": {"type": "string"}, "changed": {"type": "array", "items": {"type": "string"}}, "approved": {"type": "boolean"}}, ["run_id", "controls", "approved"])},
        "planning_aidlc_question_challenge": {"name": "planning_aidlc_question_challenge", "description": "Create a sanitized proposal to correct one AIDLC question. It does not change the active question yet.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "question_id": {"type": "string"}, "reason_code": {"type": "string", "enum": ["unclear", "incorrect-assumption", "missing-option", "unclear-reasoning", "other"]}, "approved": {"type": "boolean"}}, ["run_id", "question_id", "reason_code", "approved"])},
        "planning_aidlc_question_record": {"name": "planning_aidlc_question_record", "description": "Record one authority-generated replacement AIDLC question. User approval is still required before it becomes active.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "question": {"type": "object"}, "approved": {"type": "boolean"}}, ["run_id", "question", "approved"])},
        "planning_aidlc_question_approve": {"name": "planning_aidlc_question_approve", "description": "Approve one recorded AIDLC question revision and reopen the current requirements answer set.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "approved": {"type": "boolean"}}, ["run_id", "approved"])},
        "source_patch_apply": {"name": "source_patch_apply", "description": "Apply one supplied unified patch only after explicit approval and an approved matching Planning Lock. Validates patch paths stay inside the repository and, when the run has an active pipeline stage, that each path is allowed by the stage badge; never commits, pushes, or runs arbitrary commands.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "patch": {"type": "string"}, "approved": {"type": "boolean"}}, ["run_id", "patch", "approved"])},
        "planning_lock_start": {"name": "planning_lock_start", "description": "Create an awaiting-approval Planning Lock after the user explicitly asks to start TailTrail. Writes only TailTrail local metadata; it never edits project source or runs project commands.", "inputSchema": json_schema({"goal": {"type": "string"}, "root": {"type": "string"}, "run_id": {"type": "string"}, "reference_roots": {"type": "array", "items": {"type": "string"}}, "approved": {"type": "boolean"}}, ["goal", "approved"])},
        "planning_investigate": {"name": "planning_investigate", "description": "Perform an explicitly approved, path-bounded, read-only source investigation for an awaiting Planning Lock. It writes only a sanitized TailTrail receipt and never edits source, runs tests, scanners, builds, package managers, Git, or plan revisions.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "paths": {"type": "array", "minItems": 1, "items": {"type": "string"}}, "approved": {"type": "boolean"}}, ["run_id", "paths", "approved"])},
        "planning_revision_propose": {"name": "planning_revision_propose", "description": "Persist one explicitly approved, versioned material plan delta for an awaiting Planning Lock. It can preserve and supersede an incorrect unapproved pending revision; it never edits source or runs project commands.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "changes": {"type": "array", "minItems": 1, "items": {"type": "object"}}, "supersede_pending": {"type": "boolean"}, "approved": {"type": "boolean"}}, ["run_id", "changes", "approved"])},
        "planning_revision_approve": {"name": "planning_revision_approve", "description": "Approve exactly one proposed plan revision, freeze its report into the same run's immutable anchor, and activate it. Requires explicit approval; it never edits project source or runs project commands.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "revision": {"type": "integer", "minimum": 2}, "approved": {"type": "boolean"}}, ["run_id", "revision", "approved"])},
        "planning_aidlc_standard_propose": {"name": "planning_aidlc_standard_propose", "description": "Propose a versioned Lite-to-Standard AIDLC mode switch for an awaiting TailTrail run. Requires explicit approval and writes only local planning metadata; it does not begin questions, inspect source, or permit implementation.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "approved": {"type": "boolean"}}, ["run_id", "approved"])},
        "planning_aidlc_standard_approve": {"name": "planning_aidlc_standard_approve", "description": "Approve exactly one Lite-to-Standard mode-switch proposal and begin Standard AIDLC requirements under the same run. It does not approve implementation or run project commands.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "revision": {"type": "integer", "minimum": 2}, "approved": {"type": "boolean"}}, ["run_id", "revision", "approved"])},
        "planning_lock_approve": {"name": "planning_lock_approve", "description": "Explicitly approve one existing Planning Lock run for managed execution. For a saved TailTrail Start report, it also activates that exact plan's canonical requirement anchor. It never edits project source or runs project commands.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "approved": {"type": "boolean"}}, ["run_id", "approved"])},
        "tailtrail_start": {"name": "tailtrail_start", "description": "Atomically inspect and hash-bind declared requirement artifacts and validate typed host requirement interpretation. Agent-host Standard/Full Build Start returns verified official requirement authority before scope and accepts only a proposal bound to the exact official mode, Requirements stage, and governing references; TailTrail maps but never rewrites those official rows. It may consume one fully answered goal/root/host-bound requirement intake. It validates evidence-bound scope, manages reusable graph metadata, and creates a Planning Lock only after requirements and scope pass. Missing, unreadable, unsupported, truncated, unbound, unofficial, or stale required inputs fail before scope. Non-agent clients retain deterministic fallback and the legacy post-lock official stage. Before Debug Start, call debug_preflight and perform one reasoning pass over only that packet, then submit a hash-bound advisory debug_diagnosis with its closed typed proposal and complete behavior graph. Preserve every evidence-backed branch and convergence point. No host proposal may include unrestricted reasoning, invented facts, approval, or execution authority. Use only after the user explicitly asks to start TailTrail.", "inputSchema": json_schema({"goal": {"type": "string"}, "root": {"type": "string"}, "host": {"type": "string", "enum": ["codex", "copilot", "claude"]}, "host_scope_proposal": {"type": "object"}, "debug_diagnosis": {"type": "object"}, "changed": {"type": "array", "items": {"type": "string"}}, "graph": {"type": "string", "enum": ["auto", "reuse", "refresh", "rebuild", "off"]}, "run_id": {"type": "string"}, "reference_roots": {"type": "array", "items": {"type": "string"}}, "requirement_artifacts": {"type": "array", "items": {"type": "string"}}, "workflow": {"type": "string", "enum": ["build", "debug"]}, "error_artifact_supplied": {"type": "boolean"}, "reproduction_command_supplied": {"type": "boolean"}, "requirement_interpretation": {"type": "object"}, "requirement_intake_id": {"type": "string", "pattern": "^intake-[a-f0-9]{16}$"}, "aidlc": {"type": "string", "enum": ["lite", "standard", "medium", "full", "off"]}, "official_aidlc_manifest": {"type": "string"}, "official_intent_id": {"type": "string"}, "official_session_id": {"type": "string"}, "official_stage": {"type": "string", "enum": ["requirements", "design", "implementation", "build-and-test", "handoff", "operations"]}, "visual_artifacts": {"type": "array", "items": {"type": "string"}}, "visual_observations": {"type": "object"}, "verbose": {"type": "boolean"}, "format": {"type": "string", "enum": ["json", "markdown"]}, "approved": {"type": "boolean"}}, ["goal", "approved"]), "outputSchema": scope_tool_output_schema(), "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}},
        "navigator_scope_proposal_record": {"name": "navigator_scope_proposal_record", "description": "Validate and return one host scope proposal against an exact bounded evidence packet. Supply the packet returned by tailtrail_start, or canonical evidence for a full projected decision. Requires explicit approval, writes nothing, creates no run or Planning Lock, and grants no execution authority.", "inputSchema": json_schema({"root": {"type": "string"}, "packet": {"type": "object"}, "evidence": {"type": "object"}, "proposal": {"type": "object"}, "approved": {"type": "boolean"}}, ["proposal", "approved"])},
        "execution_evidence_record": {"name": "execution_evidence_record", "description": "Record one factual, requirement-linked host execution event after explicit approval and an approved matching Planning Lock. The event is schema-validated and stored locally; this tool never executes, reinterprets, or invents command, test, CI, or Harness evidence.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "event": {"type": "object"}, "approved": {"type": "boolean"}}, ["run_id", "event", "approved"])},
        "execution_evidence_run": {"name": "execution_evidence_run", "description": "Execute one exact validation command already approved in the run anchor, then capture its exit code, duration, environment, and bounded redacted stdout/stderr as trusted evidence. It cannot execute an unapproved command or tier.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "requirement_uids": {"type": "array", "minItems": 1, "items": {"type": "string"}}, "tiers": {"type": "array", "minItems": 1, "items": {"type": "string"}}, "changed": {"type": "array", "items": {"type": "string"}}, "command": {"type": "string"}, "command_label": {"type": "string"}, "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 3600}, "approved": {"type": "boolean"}}, ["run_id", "requirement_uids", "tiers", "command", "command_label", "approved"])},
        "spec_kit_import": {"name": "spec_kit_import", "description": "Import one selected local Spec Kit feature as normalized TailTrail metadata only. Requires explicit approval.", "inputSchema": json_schema({"root": {"type": "string"}, "feature": {"type": "string"}, "mode": {"type": "string", "enum": ["review", "planning"]}, "approved": {"type": "boolean"}}, ["feature", "approved"])},
        "spec_kit_amendment_propose": {"name": "spec_kit_amendment_propose", "description": "Write a versioned local amendment proposal from an imported Spec Kit source change. Requires explicit approval.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "approved": {"type": "boolean"}}, ["run_id", "approved"])},
        "spec_kit_anchor_approve": {"name": "spec_kit_anchor_approve", "description": "Approve one material Spec Kit amendment and create amended TailTrail-only anchor state. Requires explicit approval.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "approved": {"type": "boolean"}}, ["run_id", "approved"])},
        "spec_kit_convergence_record": {"name": "spec_kit_convergence_record", "description": "Record a local Spec Kit convergence report after explicit approval. It does not edit Spec Kit files or run tests.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "approved": {"type": "boolean"}}, ["run_id", "approved"])},
        "spec_kit_ci_ingest": {"name": "spec_kit_ci_ingest", "description": "Ingest a supplied local CI receipt into a selected Spec Kit run. Requires explicit approval; it makes no CI network call.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "input": {"type": "string"}, "approved": {"type": "boolean"}}, ["run_id", "input", "approved"])},
        "debug_start": {"name": "debug_start", "description": "Open a Debug Harness intake for a reported symptom (or attach to an existing run). Requires explicit approval; it only captures intake/fingerprint/code-path data and never edits project source.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "symptom": {"type": "string"}, "error": {"type": "string"}, "command": {"type": "string"}, "attach": {"type": "boolean"}, "approved": {"type": "boolean"}}, ["symptom", "approved"])},
        "debug_reproduction_draft": {"name": "debug_reproduction_draft", "description": "Create or revise the local reproduction contract for an approved Debug Start Plan. It writes metadata only and grants no investigation or source-write authority.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "contract": {"type": "object"}, "approved": {"type": "boolean"}}, ["run_id", "contract", "approved"])},
        "debug_reproduction_revise": {"name": "debug_reproduction_revise", "description": "Create a new reproduction draft from one exact unapproved revision. Metadata-only and explicitly approved.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "revision": {"type": "integer", "minimum": 1}, "contract": {"type": "object"}, "approved": {"type": "boolean"}}, ["run_id", "revision", "contract", "approved"])},
        "debug_reproduction_reopen": {"name": "debug_reproduction_reopen", "description": "Create a new separately approvable reproduction revision after factual not-reproduced/inconclusive evidence and user input. Preserves earlier approved revisions and grants no execution authority.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "revision": {"type": "integer", "minimum": 1}, "contract": {"type": "object"}, "approved": {"type": "boolean"}}, ["run_id", "revision", "contract", "approved"])},
        "debug_reproduction_approve": {"name": "debug_reproduction_approve", "description": "Approve one exact reproduction revision and create its immutable investigation anchor and investigation-only handoff. It never approves a correction or source write.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "revision": {"type": "integer", "minimum": 1}, "approved": {"type": "boolean"}}, ["run_id", "revision", "approved"])},
        "debug_reproduction_attempt_record": {"name": "debug_reproduction_attempt_record", "description": "Record one factual host-run pre-fix or post-fix reproduction attempt linked to an existing command-result evidence fingerprint. If the issue is not reproduced, returns a sanitized focused user-input request and blocks hypotheses/correction.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "phase": {"enum": ["pre-fix", "post-fix"]}, "outcome": {"enum": ["reproduced", "not-reproduced", "inconclusive", "restored", "still-reproduced"]}, "evidence_event_id": {"type": "string"}, "observed_summary": {"type": "string"}, "checked_dimensions": {"type": "array", "minItems": 1, "items": {"enum": ["command-or-actions", "input-or-fixture", "runtime-version", "configuration", "environment", "permissions", "timing-or-frequency", "external-dependency", "unknown"]}}, "approved": {"type": "boolean"}}, ["run_id", "phase", "outcome", "evidence_event_id", "observed_summary", "checked_dimensions", "approved"])},
        "debug_orientation_create": {"name": "debug_orientation_create", "description": "Create a local, versioned Debug Harness orientation from the existing Code Graph cache after reproduction approval. Requires explicit approval; never refreshes the graph, reads source bodies, runs project commands, or advances DWR by itself.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "approved": {"type": "boolean"}}, ["run_id", "approved"])},
        "debug_hypothesis_add": {"name": "debug_hypothesis_add", "description": "Add one bounded hypothesis to an approved Debug investigation. Metadata-only.", "inputSchema": json_schema({"root":{"type":"string"},"run_id":{"type":"string"},"domain":{"type":"string","enum":["code","architecture","database","api-integration"]},"statement":{"type":"string"},"rank":{"type":"integer","minimum":1},"approved":{"type":"boolean"}}, ["run_id","domain","statement","rank","approved"])},
        "debug_hypothesis_reprioritize": {"name": "debug_hypothesis_reprioritize", "description": "Save and apply one complete ordering of open Debug hypotheses without deleting history. Metadata-only.", "inputSchema": json_schema({"root":{"type":"string"},"run_id":{"type":"string"},"rankings":{"type":"array","minItems":1,"items":{"type":"object"}},"approved":{"type":"boolean"}}, ["run_id","rankings","approved"])},
        "debug_experiment_propose": {"name": "debug_experiment_propose", "description": "Save a deterministic experiment proposal and expected discriminating signal. It never executes the proposed command.", "inputSchema": json_schema({"root":{"type":"string"},"run_id":{"type":"string"},"hypothesis_id":{"type":"string"},"action":{"type":"string"},"expected_signal":{"type":"string"},"approved":{"type":"boolean"}}, ["run_id","hypothesis_id","action","expected_signal","approved"])},
        "debug_experiment_record": {"name": "debug_experiment_record", "description": "Record one deterministic, requirement-linked Debug Harness experiment. Duplicate probes against an unchanged failure fingerprint are rejected and cycle exhaustion creates preserved Recovery/Replan evidence.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "hypothesis_id": {"type": "string"}, "action": {"type": "string"}, "expected_signal": {"type": "string"}, "outcome": {"type": "string", "enum": ["eliminates", "strengthens", "unchanged", "regressed", "new-drift", "inconclusive"]}, "evidence_event_id": {"type": "string"}, "approved": {"type": "boolean"}}, ["run_id", "hypothesis_id", "action", "expected_signal", "outcome", "evidence_event_id", "approved"])},
        "debug_root_cause_prove": {"name": "debug_root_cause_prove", "description": "Mark one evidence-supported hypothesis as proven after a competing hypothesis was eliminated, binding the proven fault layer to exact saved behavior-trace nodes when a trace exists. Metadata-only.", "inputSchema": json_schema({"root":{"type":"string"},"run_id":{"type":"string"},"hypothesis_id":{"type":"string"},"fault_layer":{"type":"string","enum":["composition","rendering","end-user","cross-layer"]},"trace_node_ids":{"type":"array","minItems":1,"uniqueItems":True,"items":{"type":"string"}},"approved":{"type":"boolean"}}, ["run_id","hypothesis_id","approved"])},
        "debug_correction_propose": {"name": "debug_correction_propose", "description": "Create a DI-7 bounded correction proposal from one proven hypothesis and supplied file/symbol/validation scope. Requires approval and writes TailTrail metadata only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "hypothesis_id": {"type": "string"}, "statement": {"type": "string"}, "correction": {"type": "object"}, "approved": {"type": "boolean"}}, ["run_id", "hypothesis_id", "correction", "approved"])},
        "debug_correction_approve": {"name": "debug_correction_approve", "description": "Approve the proposed Debug Harness correction packet for a run. Requires a separate, explicit approval message before the fix is implemented.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "approved": {"type": "boolean"}}, ["run_id", "approved"])},
        "debug_correction_scope_check": {"name": "debug_correction_scope_check", "description": "Compare actual changed paths with the immutable DI-7 correction scope and record requirement-linked drift evidence. Never edits or reverts files.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "changed": {"type": "array", "items": {"type": "string"}, "minItems": 1}, "approved": {"type": "boolean"}}, ["run_id", "changed", "approved"])},
        "debug_harness_convergence_finalize": {"name": "debug_harness_convergence_finalize", "description": "Converge selected typed Debug Harness evidence after explicit approval. It may run existing deterministic local Architecture/Maintainability assessments but never project commands, source edits, recovery, Git, providers, publish, deploy, or closure acceptance.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "approved": {"type": "boolean"}}, ["run_id", "approved"])},
        "debug_closure_finalize": {"name": "debug_closure_finalize", "description": "Finalize the canonical TailTrail closure for a Debug run from saved evidence. It never runs project commands or accepts delivery.", "inputSchema": json_schema({"root":{"type":"string"},"run_id":{"type":"string"},"approved":{"type":"boolean"}}, ["run_id","approved"])},
        "debug_evaluation_run": {"name":"debug_evaluation_run","description":"Evaluate and save the committed ten-scenario Debug fixture suite. It performs no live host, model, project, network, or scanner execution.","inputSchema":json_schema({"root":{"type":"string"},"approved":{"type":"boolean"}}, ["approved"])},
        **workflow_tool_definitions(),
    }


def tool_list() -> list[dict[str, Any]]:
    return [tool_definitions()[name] for name in TOOL_ORDER]


def ensure_safe_tools() -> list[str]:
    errors: list[str] = []
    definitions = tool_definitions()
    expected_order = TOOL_ORDER
    actual_order = tuple(definitions)
    if actual_order != expected_order:
        index = next(
            (index for index, (actual, expected) in enumerate(zip(actual_order, expected_order)) if actual != expected),
            min(len(actual_order), len(expected_order)),
        )
        expected_name = expected_order[index] if index < len(expected_order) else "<none>"
        actual_name = actual_order[index] if index < len(actual_order) else "<none>"
        errors.append(
            "tool registry order mismatch at index "
            f"{index}: expected `{expected_name}`, got `{actual_name}`"
        )
    for name in definitions:
        if name not in (*CONTROLLED_TOOLS, "install_status") and any(term in name for term in DENIED_TOOL_TERMS):
            errors.append(f"tool name is not read-only: {name}")
    for name in TOOL_ORDER:
        schema = definitions[name].get("inputSchema")
        if not isinstance(schema, dict) or schema.get("type") != "object":
            errors.append(f"{name}: inputSchema must be an object schema")
    return errors


def root_from(args: dict[str, Any]) -> Path:
    value = args.get("root")
    if isinstance(value, str) and value:
        return Path(value).expanduser().resolve()
    return Path.cwd().resolve()


def as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def output_format(args: dict[str, Any]) -> str:
    value = args.get("format")
    return value if value in {"json", "markdown"} else "json"


def command_result(command: list[str], cwd: Path, *, stdin_data: str | None = None) -> dict[str, Any]:
    result = subprocess.run(command, cwd=cwd, text=True, input=stdin_data, capture_output=True, check=False)
    return {
        "command": command,
        "cwd": cwd.as_posix(),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "read_only": True,
    }


def parse_stdout(result: dict[str, Any], fmt: str) -> Any:
    if fmt != "json":
        return result["stdout"]
    try:
        return json.loads(result["stdout"])
    except json.JSONDecodeError:
        return result["stdout"]


def _scope_module() -> Any:
    spec = importlib.util.spec_from_file_location("navigator_scope_contract_mcp", script("navigator_scope.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Navigator scope contract")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def scope_contract(value: Any) -> dict[str, Any] | None:
    """Project canonical scope metadata without weakening invalid evidence."""
    if not isinstance(value, dict):
        return None
    report = value.get("report") if isinstance(value.get("report"), dict) else value
    navigator = report.get("navigator") if isinstance(report, dict) else None
    evidence_present = (
        value.get("type") == "tailtrail-navigator-scope-evidence"
        or isinstance(value.get("scope_evidence"), dict)
        or isinstance(navigator, dict) and isinstance(navigator.get("scope_evidence"), dict)
    )
    if not evidence_present:
        return None
    return _scope_module().normalized_scope_contract(value)


def requirement_route_contract(value: Any) -> dict[str, Any] | None:
    """Project the exact requirement-before-scope decision for every host."""
    if not isinstance(value, dict):
        return None
    report = value.get("report") if isinstance(value.get("report"), dict) else value
    if not isinstance(report, dict):
        return None
    precondition = report.get("scope_question_precondition")
    if not isinstance(precondition, dict):
        navigator = report.get("navigator")
        interpreted = (
            navigator.get("requirement_interpretation")
            if isinstance(navigator, dict)
            else None
        )
        sufficiency = (
            interpreted.get("sufficiency")
            if isinstance(interpreted, dict)
            else None
        )
        if isinstance(sufficiency, dict):
            material = sufficiency.get("material_decisions", [])
            decisions = material if isinstance(material, list) else ["invalid"]
            allowed = sufficiency.get("state") == "sufficient" and not decisions
            precondition = {
                "state": "eligible" if allowed else "deferred",
                "requirements_state": sufficiency.get("state", "unknown"),
                "open_material_decision_ids": [
                    str(row.get("id") or "unidentified-material-decision")
                    if isinstance(row, dict)
                    else "invalid-material-decision-contract"
                    for row in decisions
                ],
                "scope_question_allowed": allowed,
                "reason_code": (
                    "requirements-sufficient"
                    if allowed
                    else "requirements-must-be-resolved-before-scope-question"
                ),
            }
    if not isinstance(precondition, dict):
        if report.get("host_requirement_interpretation_boundary"):
            precondition = {
                "state": "deferred",
                "requirements_state": "host-interpretation-required",
                "open_material_decision_ids": [],
                "scope_question_allowed": False,
                "reason_code": "host-requirement-interpretation-required",
            }
        elif report.get("requirement_artifact_boundary"):
            precondition = {
                "state": "deferred",
                "requirements_state": "required-planning-input-unavailable",
                "open_material_decision_ids": [],
                "scope_question_allowed": False,
                "reason_code": "required-planning-input-unavailable",
            }
        else:
            return None
    route = report.get("recommended_route")
    if not route and report.get("host_requirement_interpretation_boundary"):
        route = "host-interpretation"
    if not route and report.get("requirement_artifact_boundary"):
        route = "requirement-artifact-recovery"
    if not route and precondition.get("scope_question_allowed") is True:
        route = "scope"
    return {
        "schema_version": "1",
        "type": "tailtrail-requirement-route-projection",
        "state": str(precondition.get("state", "deferred")),
        "requirements_state": str(precondition.get("requirements_state", "unknown")),
        "scope_question_allowed": precondition.get("scope_question_allowed") is True,
        "open_material_decision_ids": list(precondition.get("open_material_decision_ids", [])),
        "reason_code": str(precondition.get("reason_code", "requirement-route-not-recorded")),
        "route": route,
        "intake_id": report.get("intake_id"),
        "boundary": "This projection grants no Planning Lock, scope, approval, or execution authority.",
    }


def scope_host_packet(value: Any) -> dict[str, Any] | None:
    """Return only a requested sanitized host packet from a report envelope."""
    if not isinstance(value, dict):
        return None
    report = value.get("report") if isinstance(value.get("report"), dict) else value
    packet = report.get("scope_host_packet") if isinstance(report, dict) else None
    if not isinstance(packet, dict) and isinstance(report, dict):
        navigator = report.get("navigator")
        packet = navigator.get("scope_host_packet") if isinstance(navigator, dict) else None
    route = packet.get("route") if isinstance(packet, dict) else None
    return packet if isinstance(route, dict) and route.get("state") == "requested" else None


def scope_run_created(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    report = value.get("report") if isinstance(value.get("report"), dict) else value
    lock = report.get("planning_lock") if isinstance(report, dict) else None
    return isinstance(lock, dict) and bool(lock.get("run_id"))


def requirement_scope_transport(value: Any) -> dict[str, Any]:
    """Validate one non-contradictory requirement/scope MCP projection."""
    route = requirement_route_contract(value)
    contract = scope_contract(value)
    packet = scope_host_packet(value)
    run_created = scope_run_created(value)
    if isinstance(route, dict) and route.get("state") == "deferred":
        contradictions = [
            name
            for name, present in (
                ("scope-contract", contract is not None),
                ("host-reasoning-packet", packet is not None),
                ("planning-run", run_created),
            )
            if present
        ]
        if contradictions:
            raise ValueError(
                "requirement-before-scope conformance violation: deferred route cannot expose "
                + ", ".join(contradictions)
            )
    if (contract is not None or packet is not None or run_created) and route is None:
        raise ValueError(
            "requirement-before-scope conformance violation: scope state requires a typed requirement route"
        )
    return {
        "requirement_route": route,
        "scope_contract": contract,
        "host_reasoning_packet": packet,
        "run_created": run_created,
    }


def render_transport(tool: str, value: Any, fmt: str, *, verbose: bool = False) -> Any:
    """Render Markdown from the same JSON object used for scope metadata."""
    if fmt != "markdown" or not isinstance(value, dict):
        return value
    if tool == "navigator_plan":
        spec = importlib.util.spec_from_file_location("navigator_render_mcp", script("navigator.py"))
        if spec is None or spec.loader is None:
            raise RuntimeError("unable to load Navigator renderer")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module.markdown(value)
    spec = importlib.util.spec_from_file_location("task_start_render_mcp", script("task-start.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Start renderer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.render_markdown(value, verbose=verbose)


def navigator_plan(args: dict[str, Any]) -> dict[str, Any]:
    goal = str(args.get("goal", "")).strip()
    if not goal:
        raise ValueError("goal is required")
    root = root_from(args)
    fmt = output_format(args)
    command = [PYTHON, script("navigator.py").as_posix(), goal, "--root", root.as_posix(), "--format", "json"]
    for item in as_string_list(args.get("changed")):
        command.extend(["--changed", item])
    if args.get("graph") in {"auto", "reuse", "refresh", "rebuild", "off"}:
        command.extend(["--graph", str(args["graph"])])
    result = command_result(command, root)
    parsed = parse_stdout(result, "json")
    result["transport_format"] = "json"
    result["response_format"] = fmt
    return {"tool": "navigator_plan", "result": render_transport("navigator_plan", parsed, fmt), **requirement_scope_transport(parsed), "execution": result}


def intent_resolve(args: dict[str, Any]) -> dict[str, Any]:
    text = str(args.get("text", ""))
    if not text.strip():
        raise ValueError("text is required")
    active_state = str(args.get("active_state", "none"))
    if active_state not in {"none", "awaiting-approval", "active", "closure-ready", "detached", "ambiguous"}:
        raise ValueError("active_state is invalid")
    root = root_from(args)
    command = [
        PYTHON,
        script("expand-intent.py").as_posix(),
        "resolve",
        text,
        "--active-state",
        active_state,
        "--format",
        "json",
    ]
    result = command_result(command, root)
    if result["exit_code"] != 0:
        raise ValueError("intent resolution failed")
    return {"tool": "intent_resolve", "result": parse_stdout(result, "json"), "execution": result}


def debug_preflight(args: dict[str, Any]) -> dict[str, Any]:
    """Return one bounded, read-only Debug Start evidence packet."""
    goal = str(args.get("goal", "")).strip()
    if not goal:
        raise ValueError("goal is required")
    host = str(args.get("host", "")).strip()
    if host not in {"codex", "copilot", "claude"}:
        raise ValueError("host must be codex, copilot, or claude")
    root = root_from(args)
    command = [
        PYTHON, script("debug-preflight.py").as_posix(),
        "--root", root.as_posix(), "--goal", goal, "--host", host, "--format", "json",
    ]
    result = command_result(command, root)
    parsed = parse_stdout(result, "json")
    result["read_only"] = True
    result["local_metadata_only"] = False
    return {"tool": "debug_preflight", "result": parsed, "execution": result}


def _session_control_module() -> Any:
    spec = importlib.util.spec_from_file_location("tailtrail_mcp_session_control", script("session_control.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load TailTrail session control")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tailtrail_session_status(args: dict[str, Any]) -> dict[str, Any]:
    result = _session_control_module().status(root_from(args), str(args.get("context_key")) if args.get("context_key") else None)
    return {"tool": "tailtrail_session_status", "result": result, "execution": {"read_only": True, "exit_code": 0}}


def tailtrail_stop(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("confirmed") is not True:
        raise ValueError("tailtrail_stop requires confirmed: true after an explicit user stop request")
    result = _session_control_module().stop(
        root_from(args),
        str(args.get("run_id")) if args.get("run_id") else None,
        str(args.get("context_key")) if args.get("context_key") else None,
    )
    return {"tool": "tailtrail_stop", "result": result, "execution": {"read_only": False, "local_metadata_only": True, "requires_confirmation": True, "exit_code": 0}}


def tailtrail_resume(args: dict[str, Any]) -> dict[str, Any]:
    identifier = str(args.get("run_id", "")).strip()
    if not identifier:
        raise ValueError("tailtrail_resume requires one exact run_id")
    result = _session_control_module().resume(
        root_from(args), identifier,
        str(args.get("context_key")) if args.get("context_key") else None,
    )
    exit_code = 0 if result.get("state") not in {"resume-stale", "resume-conflict", "resume-invalid"} else 2
    return {"tool": "tailtrail_resume", "result": result, "execution": {"read_only": False, "local_metadata_only": True, "execution_advanced": False, "exit_code": exit_code}}


def start_report(args: dict[str, Any]) -> dict[str, Any]:
    goal = str(args.get("goal", "")).strip()
    if not goal:
        raise ValueError("goal is required")
    root = root_from(args)
    fmt = output_format(args)
    command = [PYTHON, script("task-start.py").as_posix(), goal, "--root", root.as_posix(), "--format", "json", "--no-planning-lock"]
    for item in as_string_list(args.get("changed")):
        command.extend(["--changed", item])
    if bool(args.get("verbose")):
        command.append("--verbose")
    result = command_result(command, root)
    parsed = parse_stdout(result, "json")
    result["transport_format"] = "json"
    result["response_format"] = fmt
    return {"tool": "start_report", "result": render_transport("start_report", parsed, fmt, verbose=bool(args.get("verbose"))), **requirement_scope_transport(parsed), "execution": result}


def guardrail_check(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args)
    fmt = output_format(args)
    command = [PYTHON, script("guardrail-check.py").as_posix(), "--root", root.as_posix(), "--format", fmt]
    diff_text = args.get("diff")
    temp_path: Path | None = None
    try:
        if isinstance(diff_text, str):
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".diff") as handle:
                handle.write(diff_text)
                temp_path = Path(handle.name)
            command.extend(["--diff", temp_path.as_posix()])
        elif not (root / ".git").exists():
            command.extend(["--diff", "/dev/null"])
        fail_on = as_string_list(args.get("fail_on"))
        if fail_on:
            command.extend(["--fail-on", ",".join(fail_on)])
        if bool(args.get("enforce")):
            command.append("--enforce")
        result = command_result(command, root)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return {"tool": "guardrail_check", "result": parse_stdout(result, fmt), "execution": result}


def graph_map(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args)
    fmt = output_format(args)
    command = [PYTHON, script("review-graph.py").as_posix(), "--root", root.as_posix(), "--format", fmt]
    for item in as_string_list(args.get("changed")):
        command.extend(["--changed", item])
    result = command_result(command, root)
    return {"tool": "graph_map", "result": parse_stdout(result, fmt), "execution": result}


def install_status(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args)
    manifest = root / ".tailtrail-install.json"
    nested = sorted(root.glob("*/.tailtrail-install.json"))
    path = manifest if manifest.exists() else nested[0] if nested else None
    if path is None:
        return {
            "tool": "install_status",
            "result": {
                "surface": "unknown",
                "manifest": None,
                "recommended_next": "python3 scripts/tailtrail.py install local --inspect",
            },
            "execution": {"read_only": True, "exit_code": 0},
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {
            "tool": "install_status",
            "result": {"surface": "unknown", "manifest": path.as_posix(), "error": str(error)},
            "execution": {"read_only": True, "exit_code": 1},
        }
    surface = data.get("surface") if isinstance(data, dict) else "unknown"
    return {
        "tool": "install_status",
        "result": {
            "surface": surface if isinstance(surface, str) else "unknown",
            "manifest": path.as_posix(),
            "pack_dir": data.get("pack_dir") if isinstance(data, dict) else None,
            "recommended_next": "python3 scripts/tailtrail.py install status --target .",
        },
        "execution": {"read_only": True, "exit_code": 0},
    }


def eval_scenario_list(args: dict[str, Any]) -> dict[str, Any]:
    fmt = output_format(args)
    command = [PYTHON, script("evaluation-harness.py").as_posix(), "scenario", "list", "--format", fmt]
    result = command_result(command, ROOT)
    return {"tool": "eval_scenario_list", "result": parse_stdout(result, fmt), "execution": result}


def eval_scenario_report(args: dict[str, Any]) -> dict[str, Any]:
    scenario = str(args.get("scenario", "")).strip()
    if not scenario:
        raise ValueError("scenario is required")
    fmt = output_format(args)
    command = [
        PYTHON,
        script("evaluation-harness.py").as_posix(),
        "scenario",
        "report",
        "--scenario",
        scenario,
        "--format",
        fmt,
    ]
    result = command_result(command, ROOT)
    return {"tool": "eval_scenario_report", "result": parse_stdout(result, fmt), "execution": result}


def run_id(args: dict[str, Any]) -> str:
    value = str(args.get("run_id", "")).strip()
    if not value or Path(value).name != value: raise ValueError("run_id must be a single local run identifier")
    return value


def require_approved_planning_lock(root: Path, identifier: str, action: str, *, source_write: bool = False) -> None:
    command_name = "assert-source-write" if source_write else "assert-write"
    result = command_result(
        [PYTHON, script("planning_lock.py").as_posix(), command_name, "--root", root.as_posix(), "--run-id", identifier],
        root,
    )
    if result["exit_code"] != 0:
        raise ValueError(f"{action} denied by Planning Lock; explicitly approve this exact run before managed execution")


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file(): raise ValueError(f"local artifact does not exist: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_artifact(root: Path, identifier: str, section: str, pattern: str) -> dict[str, Any] | None:
    directory = root / ".tailtrail" / "runs" / identifier / section
    matches = sorted(directory.glob(pattern))
    return read_json(matches[-1]) if matches else None


def ledger_state(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args)
    result = command_result([PYTHON, script("run-ledger.py").as_posix(), "state", "--root", root.as_posix(), "--run-id", identifier], root)
    return {"tool": "ledger_state", "result": parse_stdout(result, "json"), "execution": result}


def anchor_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args)
    return {"tool": "anchor_show", "result": read_json(root / ".tailtrail" / "runs" / identifier / "anchors" / "approved-v1.json"), "execution": {"read_only": True, "exit_code": 0}}


def harness_checkpoint_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args); number = args.get("checkpoint")
    path = root / ".tailtrail" / "runs" / identifier / "checkpoints" / (f"checkpoint-{number}.json" if isinstance(number, int) else "")
    result = read_json(path) if isinstance(number, int) else run_artifact(root, identifier, "checkpoints", "checkpoint-*.json")
    if result is None: raise ValueError("no checkpoint artifact exists")
    return {"tool": "harness_checkpoint_show", "result": result, "execution": {"read_only": True, "exit_code": 0}}


def completion_feedback_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args)
    return {"tool": "completion_feedback_show", "result": {"review": run_artifact(root, identifier, "reviews", "review-*.json"), "feedback": run_artifact(root, identifier, "feedback", "feedback-*.json")}, "execution": {"read_only": True, "exit_code": 0}}


def execution_evidence_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("execution_evidence_mcp", script("execution-evidence.py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {"tool": "execution_evidence_show", "result": module.show(root_from(args), run_id(args)), "execution": {"read_only": True, "exit_code": 0}}


def safe_relative(root: Path, value: Any) -> Path:
    path = Path(str(value))
    if path.is_absolute() or ".." in path.parts: raise ValueError("path must be repository-relative")
    resolved = (root / path).resolve()
    if root not in resolved.parents and resolved != root: raise ValueError("path is outside root")
    return resolved


def profile_view(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); profile = safe_relative(root, args.get("profile", ""))
    result = command_result([PYTHON, script("testing-profile.py").as_posix(), "validate", "--profile", profile.as_posix()], root)
    return {"tool": "profile_view", "result": parse_stdout(result, "json"), "execution": result}


def validation_receipt_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args); receipt = Path(str(args.get("receipt", "")))
    if receipt.name != str(receipt): raise ValueError("receipt must be one receipt filename")
    return {"tool": "validation_receipt_show", "result": read_json(root / ".tailtrail" / "runs" / identifier / "validation-receipts" / receipt), "execution": {"read_only": True, "exit_code": 0}}


def release_confidence_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args); result = run_artifact(root, identifier, "release-confidence", "assessment-*.json")
    if result is None: raise ValueError("no release confidence assessment artifact exists")
    return {"tool": "release_confidence_show", "result": result, "execution": {"read_only": True, "exit_code": 0}}


def git_readiness(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); result = command_result([PYTHON, script("git-readiness.py").as_posix(), "--root", root.as_posix()], root)
    return {"tool": "git_readiness", "result": parse_stdout(result, "json"), "execution": result}


def recovery_boundary_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args)
    return {"tool": "recovery_boundary_show", "result": read_json(root / ".tailtrail" / "runs" / identifier / "recovery" / "boundary.json"), "execution": {"read_only": True, "exit_code": 0}}


def recovery_reconciliation_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args); result = run_artifact(root, identifier, "recovery/reconciliation", "assessment-*.json")
    if result is None: raise ValueError("no recovery reconciliation artifact exists")
    return {"tool": "recovery_reconciliation_show", "result": result, "execution": {"read_only": True, "exit_code": 0}}


def architecture_assessment_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args); result = run_artifact(root, identifier, "architecture", "assessment-*.json")
    if result is None: raise ValueError("no architecture assessment artifact exists")
    return {"tool": "architecture_assessment_show", "result": result, "execution": {"read_only": True, "exit_code": 0}}


def maintainability_assessment_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args); result = run_artifact(root, identifier, "maintainability", "assessment-*.json")
    if result is None: raise ValueError("no maintainability assessment artifact exists")
    return {"tool": "maintainability_assessment_show", "result": result, "execution": {"read_only": True, "exit_code": 0}}


def harness_control_check(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("harness_control_check requires approved: true")
    root = root_from(args); identifier = run_id(args); controls = safe_relative(root, args.get("controls", ""))
    require_approved_planning_lock(root, identifier, "harness_control_check")
    if not controls.is_file(): raise ValueError("controls must name an existing repository control file")
    command = [PYTHON, script("harness-controls.py").as_posix(), "check", "--root", root.as_posix(), "--run-id", identifier, "--controls", controls.as_posix(), "--approved"]
    for item in as_string_list(args.get("changed")): command.extend(["--changed", item])
    result = command_result(command, root); result["read_only"] = False; result["requires_approval"] = True
    return {"tool": "harness_control_check", "result": parse_stdout(result, "json"), "execution": result}


def _patch_touched_paths(patch: str) -> list[str]:
    touched: list[str] = []
    for line in patch.splitlines():
        if line.startswith(("+++ b/", "--- a/")):
            value = line[6:].strip()
            if value and value != "/dev/null" and value not in touched:
                touched.append(value)
    return touched


def _enforce_patch_badge(root: Path, identifier: str, touched: list[str]) -> None:
    """Block patch paths prohibited by the run's active pipeline badge.

    Runs without pipeline state (missing lock or PENDING stage) skip the
    gate unchanged. An active stage with an out-of-badge path raises.
    """
    from pipeline_manager import PipelineManager
    from write_guardian import validate_planned_paths

    try:
        stage = PipelineManager(root, identifier).get_current_stage()
    except Exception:
        return
    if not stage or stage == "PENDING":
        return
    denied = [row for row in validate_planned_paths(root, identifier, touched) if not row["allowed"]]
    if denied:
        detail = "; ".join(f"`{row['path']}`: {row['reason']}" for row in denied)
        raise ValueError(f"source_patch_apply blocked by active {stage} badge: {detail}")


def source_patch_apply(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("source_patch_apply requires approved: true")
    root = root_from(args); identifier = run_id(args); patch = str(args.get("patch", ""))
    require_approved_planning_lock(root, identifier, "source_patch_apply", source_write=True)
    if not patch.startswith("diff --git "): raise ValueError("patch must be a unified git diff")
    touched = _patch_touched_paths(patch)
    for value in touched:
        safe_relative(root, value)
    _enforce_patch_badge(root, identifier, touched)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".patch", dir=root, delete=False) as handle:
        handle.write(patch); patch_path = Path(handle.name)
    try:
        checked = command_result(["git", "apply", "--check", patch_path.as_posix()], root)
        if checked["exit_code"] != 0: raise ValueError("patch did not pass git apply --check")
        applied = command_result(["git", "apply", patch_path.as_posix()], root)
        if applied["exit_code"] != 0: raise ValueError("patch apply failed")
        return {"tool": "source_patch_apply", "result": {"applied": True}, "execution": applied, "read_only": False, "requires_approval": True}
    finally:
        patch_path.unlink(missing_ok=True)


def context_continuity_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("context_continuity_mcp", script("context-continuity.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return {"tool": "context_continuity_show", "result": module.show(root_from(args), run_id(args), args.get("sequence"))}


def planning_lock_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args)
    result = command_result([PYTHON, script("planning_lock.py").as_posix(), "show", "--root", root.as_posix(), "--run-id", identifier], root)
    return {"tool": "planning_lock_show", "result": parse_stdout(result, "json"), "execution": result}


def planning_decision_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("planning_decision_mcp", script("planning-discussion.py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {"tool": "planning_decision_show", "result": module.decision_show(root_from(args), run_id(args)), "execution": {"read_only": True, "exit_code": 0}}


def planning_investigation_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("planning_investigation_mcp", script("planning-investigation.py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {"tool": "planning_investigation_show", "result": module.show(root_from(args), run_id(args), args.get("sequence")), "execution": {"read_only": True, "exit_code": 0}}


def planning_investigate(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True:
        raise ValueError("planning_investigate requires approved: true")
    root = root_from(args)
    paths = as_string_list(args.get("paths"))
    if not paths:
        raise ValueError("planning_investigate requires at least one planned path")
    command = [PYTHON, script("planning-investigation.py").as_posix(), "investigate", "--root", root.as_posix(), "--run-id", run_id(args), "--approved-read-only"]
    for path in paths:
        command.extend(["--path", path])
    result = command_result(command, root)
    result["read_only"] = False
    result["requires_approval"] = True
    result["local_metadata_only"] = True
    return {"tool": "planning_investigate", "result": parse_stdout(result, "json"), "execution": result}


def planning_revision_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("planning_revision_mcp", script("planning-revision.py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {"tool": "planning_revision_show", "result": module.show(root_from(args), run_id(args), args.get("revision")), "execution": {"read_only": True, "exit_code": 0}}


def planning_authority_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("planning_authority_mcp", script("planning-revision.py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {"tool": "planning_authority_show", "result": module.authority_show(root_from(args), run_id(args), args.get("sequence")), "execution": {"read_only": True, "exit_code": 0}}


def _aidlc_question_module() -> Any:
    spec = importlib.util.spec_from_file_location("planning_aidlc_question_mcp", script("planning-aidlc-question.py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def planning_aidlc_question_show(args: dict[str, Any]) -> dict[str, Any]:
    return {"tool": "planning_aidlc_question_show", "result": _aidlc_question_module().show(root_from(args), run_id(args), str(args.get("question_id", ""))), "execution": {"read_only": True, "exit_code": 0}}


def planning_aidlc_question_clarify(args: dict[str, Any]) -> dict[str, Any]:
    return {"tool": "planning_aidlc_question_clarify", "result": _aidlc_question_module().clarify(root_from(args), run_id(args), str(args.get("question_id", ""))), "execution": {"read_only": True, "exit_code": 0}}


def planning_question_context_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("planning_question_context_mcp", script("question-orchestrator.py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {"tool": "planning_question_context_show", "result": module.show(root_from(args), run_id(args)), "execution": {"read_only": True, "exit_code": 0}}


def _requirement_intake_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "requirement_intake_mcp", script("requirement_intake.py")
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def requirement_intake_show(args: dict[str, Any]) -> dict[str, Any]:
    intake_id = str(args.get("intake_id", ""))
    result = _requirement_intake_module().load(root_from(args), intake_id)
    return {
        "tool": "requirement_intake_show",
        "result": result,
        "execution": {"read_only": True, "exit_code": 0},
    }


def requirement_intake_answer(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True:
        raise ValueError("requirement_intake_answer requires approved: true")
    answers = args.get("answers")
    if not isinstance(answers, dict):
        raise ValueError("requirement_intake_answer requires an answers object")
    result = _requirement_intake_module().answer(
        root_from(args),
        str(args.get("intake_id", "")),
        answers,
        command_prefix="tailtrail",
    )
    return {
        "tool": "requirement_intake_answer",
        "result": result,
        "execution": {
            "read_only": False,
            "requires_approval": True,
            "local_metadata_only": True,
            "exit_code": 0,
        },
    }


def _aidlc_question_control(args: dict[str, Any], action: str) -> dict[str, Any]:
    if args.get("approved") is not True:
        raise ValueError(f"{action} requires approved: true")
    module = _aidlc_question_module(); root = root_from(args); identifier = run_id(args)
    if action == "planning_aidlc_question_challenge":
        result = module.challenge(root, identifier, str(args.get("question_id", "")), str(args.get("reason_code", "")))
    elif action == "planning_aidlc_question_record":
        result = module.record(root, identifier, json.dumps(args.get("question"), separators=(",", ":")))
    else:
        result = module.approve(root, identifier, True)
    return {"tool": action, "result": result, "execution": {"read_only": False, "requires_approval": True, "local_metadata_only": True, "exit_code": 0}}


def planning_aidlc_question_challenge(args: dict[str, Any]) -> dict[str, Any]:
    return _aidlc_question_control(args, "planning_aidlc_question_challenge")


def planning_aidlc_question_record(args: dict[str, Any]) -> dict[str, Any]:
    return _aidlc_question_control(args, "planning_aidlc_question_record")


def planning_aidlc_question_approve(args: dict[str, Any]) -> dict[str, Any]:
    return _aidlc_question_control(args, "planning_aidlc_question_approve")


def planning_revision_propose(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True:
        raise ValueError("planning_revision_propose requires approved: true")
    changes = args.get("changes")
    if not isinstance(changes, list) or not changes:
        raise ValueError("planning_revision_propose requires a non-empty changes list")
    root = root_from(args)
    command = [
        PYTHON, script("planning-revision.py").as_posix(), "propose", "--root", root.as_posix(), "--run-id", run_id(args),
        "--changes", json.dumps(changes, separators=(",", ":")), "--approved-proposal",
    ]
    if args.get("supersede_pending") is True:
        command.append("--supersede-pending")
    result = command_result(command, root)
    result["read_only"] = False; result["requires_approval"] = True; result["local_metadata_only"] = True
    return {"tool": "planning_revision_propose", "result": result["stdout"], "execution": result}


def planning_revision_approve(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True:
        raise ValueError("planning_revision_approve requires approved: true")
    revision = args.get("revision")
    if not isinstance(revision, int) or revision < 2:
        raise ValueError("planning_revision_approve requires a revision number of 2 or higher")
    root = root_from(args)
    result = command_result([
        PYTHON, script("planning-revision.py").as_posix(), "approve", "--root", root.as_posix(), "--run-id", run_id(args),
        "--revision", str(revision), "--approved",
    ], root)
    result["read_only"] = False; result["requires_approval"] = True; result["local_metadata_only"] = True
    return {"tool": "planning_revision_approve", "result": result["stdout"], "execution": result}


def planning_aidlc_standard_propose(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True:
        raise ValueError("planning_aidlc_standard_propose requires approved: true")
    root = root_from(args)
    result = command_result([
        PYTHON, script("planning-revision.py").as_posix(), "aidlc-standard", "--root", root.as_posix(), "--run-id", run_id(args), "--approved-proposal",
    ], root)
    result["read_only"] = False; result["requires_approval"] = True; result["local_metadata_only"] = True
    return {"tool": "planning_aidlc_standard_propose", "result": result["stdout"], "execution": result}


def planning_aidlc_standard_approve(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True:
        raise ValueError("planning_aidlc_standard_approve requires approved: true")
    revision = args.get("revision")
    if not isinstance(revision, int) or revision < 2:
        raise ValueError("planning_aidlc_standard_approve requires a revision number of 2 or higher")
    root = root_from(args)
    result = command_result([
        PYTHON, script("planning-revision.py").as_posix(), "aidlc-standard-approve", "--root", root.as_posix(), "--run-id", run_id(args), "--revision", str(revision), "--approved",
    ], root)
    result["read_only"] = False; result["requires_approval"] = True; result["local_metadata_only"] = True
    return {"tool": "planning_aidlc_standard_approve", "result": result["stdout"], "execution": result}


def aidlc_official_status(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("tailtrail_aidlc_official_detect", script("aidlc-official-detect.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load official AIDLC compatibility detector")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.status(root_from(args), args.get("manifest"))
    return {"tool": "aidlc_official_status", "result": result, "execution": {"read_only": True, "exit_code": 0}}


def aidlc_official_bridge_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("tailtrail_aidlc_official_bridge", script("aidlc-official-bridge.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load official AIDLC bridge")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {"tool": "aidlc_official_bridge_show", "result": module.show(root_from(args), run_id(args)), "execution": {"read_only": True, "exit_code": 0}}


def aidlc_official_state_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("aidlc_official_state_mcp", script("official-aidlc-state.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return {"tool": "aidlc_official_state_show", "result": module.project(root_from(args), run_id(args)), "execution": {"read_only": True, "exit_code": 0}}


def aidlc_official_sanitize_validate(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("aidlc_official_sanitize_mcp", script("official-aidlc-sanitize.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    root = root_from(args); path = safe_relative(root, args.get("input", ""))
    return {"tool": "aidlc_official_sanitize_validate", "result": module.validate_artifact(root, read_json(path), str(args.get("context", ""))), "execution": {"read_only": True, "exit_code": 0}}


def aidlc_official_session_status(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("aidlc_official_runtime_mcp", script("official-aidlc-runtime.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return {"tool": "aidlc_official_session_status", "result": module.status(root_from(args), run_id(args)), "execution": {"read_only": True, "exit_code": 0}}


def host_conformance_report(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("host_conformance_report_mcp", script("host-runtime-conformance.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return {"tool": "host_conformance_report", "result": module.report(root_from(args), args.get("host")), "execution": {"read_only": True, "exit_code": 0}}


def planning_lock_start(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True:
        raise ValueError("planning_lock_start requires approved: true after the user explicitly requests TailTrail Start")
    goal = str(args.get("goal", "")).strip()
    if not goal:
        raise ValueError("goal is required")
    root = root_from(args)
    command = [PYTHON, script("planning_lock.py").as_posix(), "start", "--root", root.as_posix(), "--goal", goal]
    run = str(args.get("run_id", "")).strip()
    if run:
        command.extend(["--run-id", run])
    for reference in as_string_list(args.get("reference_roots")):
        command.extend(["--reference-root", reference])
    if args.get("workflow") in {"build", "debug"}:
        command.append("--" + str(args["workflow"]))
    if args.get("error_artifact_supplied") is True:
        command.extend(["--error", "provided-via-mcp"])
    if args.get("reproduction_command_supplied") is True:
        command.extend(["--command", "provided-via-mcp"])
    result = command_result(command, root)
    result["read_only"] = False
    result["requires_approval"] = True
    result["local_metadata_only"] = True
    return {"tool": "planning_lock_start", "result": parse_stdout(result, "json"), "execution": result}


def planning_lock_approve(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True:
        raise ValueError("planning_lock_approve requires approved: true")
    root = root_from(args)
    identifier = run_id(args)
    action = "activate" if (root / ".tailtrail" / "runs" / identifier / "planning" / "start-report-v1.json").is_file() else "approve"
    result = command_result(
        [PYTHON, script("planning_lock.py").as_posix(), action, "--root", root.as_posix(), "--run-id", identifier, "--approved", "--format", "json"] if action == "activate" else [PYTHON, script("planning_lock.py").as_posix(), action, "--root", root.as_posix(), "--run-id", identifier, "--approved"],
        root,
    )
    result["read_only"] = False
    result["requires_approval"] = True
    result["local_metadata_only"] = True
    return {"tool": "planning_lock_approve", "result": parse_stdout(result, "json"), "execution": result}


def tailtrail_start(args: dict[str, Any]) -> dict[str, Any]:
    """Create one persisted planning run and its complete Start report together."""
    if args.get("approved") is not True:
        raise ValueError("tailtrail_start requires approved: true after the user explicitly requests TailTrail Start")
    goal = str(args.get("goal", "")).strip()
    if not goal:
        raise ValueError("goal is required")
    root = root_from(args)
    # Start is a user-facing Planning Lock. Markdown must be the default so a
    # host receives the complete report instead of a JSON object it may compress.
    fmt = output_format(args) if args.get("format") in {"json", "markdown"} else "markdown"
    # Execute Start once as JSON, then render the requested surface from that
    # exact object.  This prevents Markdown and JSON transports from performing
    # separate discovery or receiving different scope fingerprints.
    command = [PYTHON, script("task-start.py").as_posix(), goal, "--root", root.as_posix(), "--format", "json"]
    host = str(args.get("host", "")).strip()
    scope_proposal = args.get("host_scope_proposal")
    if scope_proposal is not None:
        if not isinstance(scope_proposal, dict):
            raise ValueError("host_scope_proposal must be an object")
        if host not in {"codex", "copilot", "claude"}:
            raise ValueError("host_scope_proposal requires the active host")
    if host:
        if host not in {"codex", "copilot", "claude"}:
            raise ValueError("host must be codex, copilot, or claude")
        command.extend(["--host", host])
    if isinstance(scope_proposal, dict):
        command.extend([
            "--host-scope-proposal",
            json.dumps(scope_proposal, separators=(",", ":")),
        ])
    run = str(args.get("run_id", "")).strip()
    if run:
        command.extend(["--planning-run-id", run])
    for item in as_string_list(args.get("changed")):
        command.extend(["--changed", item])
    if args.get("graph") in {"auto", "reuse", "refresh", "rebuild", "off"}:
        command.extend(["--graph", str(args["graph"])])
    for reference in as_string_list(args.get("reference_roots")):
        command.extend(["--reference-root", reference])
    for artifact in as_string_list(args.get("requirement_artifacts")):
        command.extend(["--requirement-artifact", artifact])
    for artifact in as_string_list(args.get("visual_artifacts")):
        command.extend(["--visual-artifact", artifact])
    if isinstance(args.get("visual_observations"), dict):
        command.extend([
            "--visual-observations",
            json.dumps(args["visual_observations"], separators=(",", ":")),
        ])
    if args.get("workflow") in {"build", "debug"}:
        command.append("--" + str(args["workflow"]))
    if args.get("error_artifact_supplied") is True:
        command.extend(["--error", "provided-via-mcp"])
    if args.get("reproduction_command_supplied") is True:
        command.extend(["--command", "provided-via-mcp"])
    if isinstance(args.get("requirement_interpretation"), dict):
        command.extend([
            "--requirement-interpretation",
            json.dumps(args["requirement_interpretation"], separators=(",", ":")),
        ])
    if args.get("requirement_intake_id"):
        command.extend(["--requirement-intake-id", str(args["requirement_intake_id"])])
    diagnosis_stdin: str | None = None
    if isinstance(args.get("debug_diagnosis"), dict):
        command.append("--debug-diagnosis-stdin")
        diagnosis_stdin = json.dumps(args["debug_diagnosis"], separators=(",", ":"))
    if args.get("aidlc") in {"lite", "standard", "medium", "full", "off"}:
        command.extend(["--aidlc", str(args["aidlc"])])
    for argument, flag in (("official_aidlc_manifest", "--official-aidlc-manifest"), ("official_intent_id", "--official-intent-id"), ("official_session_id", "--official-session-id"), ("official_stage", "--official-stage")):
        if args.get(argument):
            command.extend([flag, str(args[argument])])
    if args.get("verbose") is True:
        command.append("--verbose")
    result = command_result(command, root, stdin_data=diagnosis_stdin) if diagnosis_stdin is not None else command_result(command, root)
    result["read_only"] = False
    result["requires_approval"] = True
    result["local_metadata_only"] = True
    result["execution_blocked"] = True
    result["transport_format"] = "json"
    result["response_format"] = fmt
    parsed = parse_stdout(result, "json")
    transport = requirement_scope_transport(parsed)
    return {
        "tool": "tailtrail_start",
        "result": render_transport("tailtrail_start", parsed, fmt, verbose=bool(args.get("verbose"))),
        **transport,
        "execution": result,
    }


def execution_evidence_record(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True:
        raise ValueError("execution_evidence_record requires approved: true")
    event = args.get("event")
    if not isinstance(event, dict):
        raise ValueError("execution_evidence_record requires an event object")
    root = root_from(args)
    identifier = run_id(args)
    require_approved_planning_lock(root, identifier, "execution_evidence_record")
    spec = importlib.util.spec_from_file_location("execution_evidence_mcp", script("execution-evidence.py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.append(root, identifier, event, True)
    return {
        "tool": "execution_evidence_record", "result": result,
        "execution": {"read_only": False, "requires_approval": True, "local_metadata_only": True, "exit_code": 0},
    }


def execution_evidence_run(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True:
        raise ValueError("execution_evidence_run requires approved: true")
    root = root_from(args)
    identifier = run_id(args)
    require_approved_planning_lock(root, identifier, "execution_evidence_run")
    spec = importlib.util.spec_from_file_location("execution_evidence_run_mcp", script("execution-evidence.py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run_command(
        root, identifier, list(args.get("requirement_uids") or []), list(args.get("tiers") or []),
        str(args.get("command", "")), str(args.get("command_label", "")), list(args.get("changed") or []),
        True, int(args.get("timeout_seconds", 900)),
    )
    return {
        "tool": "execution_evidence_run", "result": result,
        "execution": {"read_only": False, "requires_approval": True, "local_metadata_only": False,
                      "command_executed": True, "exit_code": result["exit_code"], "outcome": result["outcome"]},
    }


def context_continuity_render(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("context_continuity_mcp", script("context-continuity.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    root = root_from(args)
    policy = module.load_policy(safe_relative(root, args["policy"])) if args.get("policy") else None
    result = module.packet_for(root, run_id(args), args.get("requirement_uid"), args.get("trigger"), 220, policy)
    return {"tool": "context_continuity_render", "result": result, "read_only": True}


def context_continuity_advisory_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("context_continuity_mcp", script("context-continuity.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return {"tool": "context_continuity_advisory_show", "result": module.advisory_show(root_from(args), run_id(args), args.get("sequence")), "read_only": True}


def completion_report_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("completion_report_mcp", script("completion-report.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return {"tool": "completion_report_show", "result": module.show(root_from(args), run_id(args), args.get("sequence")), "execution": {"read_only": True, "exit_code": 0}}


def workflow_dashboard_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("workflow_dashboard_mcp", script("workflow-dashboard.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return {"tool": "workflow_dashboard_show", "result": module.dashboard(root_from(args), run_id(args)), "execution": {"read_only": True, "exit_code": 0}}


def enterprise_target_policy_inspect(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("enterprise_target_policy_mcp", script("enterprise-target-policy.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    root = root_from(args)
    policy = module.load(safe_relative(root, args["policy"]))
    result = module.evaluate(root, policy, actor=args.get("actor"), selected_alias=args.get("target_alias"))
    return {"tool": "enterprise_target_policy_inspect", "result": result, "execution": {"read_only": True, "exit_code": 0}}


def spec_module(name: str, label: str) -> Any:
    spec = importlib.util.spec_from_file_location(label, script(name)); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def spec_kit_detect(args: dict[str, Any]) -> dict[str, Any]:
    feature = str(args.get("feature", "")).strip()
    if not feature: raise ValueError("feature is required")
    module = spec_module("spec-kit-detect.py", "spec_kit_detect_mcp")
    return {"tool": "spec_kit_detect", "result": module.detect(root_from(args), feature), "execution": {"read_only": True, "exit_code": 0}}


def spec_kit_mapping_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args); module = spec_module("spec-kit-slices.py", "spec_kit_slices_mcp")
    paths = module.paths(root, identifier)
    return {"tool": "spec_kit_mapping_show", "result": {"slices": module.show(root, identifier), "mapping": read_json(paths["mapping"]), "source_lock": read_json(paths["source_lock"])}, "execution": {"read_only": True, "exit_code": 0}}


def spec_kit_convergence_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args); directory = root / ".tailtrail" / "runs" / identifier / "spec-kit"
    matches = sorted(directory.glob("convergence-v*.json"))
    if not matches: raise ValueError("no saved Spec Kit convergence report exists")
    return {"tool": "spec_kit_convergence_show", "result": read_json(matches[-1]), "execution": {"read_only": True, "exit_code": 0}}


def spec_kit_control(args: dict[str, Any], tool: str, command: list[str]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError(f"{tool} requires approved: true")
    root = root_from(args); result = command_result([PYTHON, *[script(item).as_posix() if item.endswith(".py") else item for item in command]], root)
    result["read_only"] = False; result["requires_approval"] = True; result["local_metadata_only"] = True
    return {"tool": tool, "result": parse_stdout(result, "json"), "execution": result}


def spec_kit_import(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); feature = str(args.get("feature", "")).strip()
    if not feature: raise ValueError("feature is required")
    return spec_kit_control(args, "spec_kit_import", ["spec-kit-import.py", "--root", root.as_posix(), "--feature", feature, "--mode", str(args.get("mode", "review"))])


def spec_kit_amendment_propose(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); return spec_kit_control(args, "spec_kit_amendment_propose", ["spec-kit-amendment.py", "propose", "--root", root.as_posix(), "--run-id", run_id(args)])


def spec_kit_anchor_approve(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); return spec_kit_control(args, "spec_kit_anchor_approve", ["spec-kit-amendment.py", "approve", "--root", root.as_posix(), "--run-id", run_id(args), "--approved"])


def spec_kit_convergence_record(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); return spec_kit_control(args, "spec_kit_convergence_record", ["spec-kit-converge.py", "--root", root.as_posix(), "--run-id", run_id(args)])


def spec_kit_ci_ingest(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); input_path = safe_relative(root, str(args.get("input", "")))
    return spec_kit_control(args, "spec_kit_ci_ingest", ["ci-evidence-ingest.py", "--root", root.as_posix(), "--run-id", run_id(args), "--input", input_path.as_posix()])


def _load_debug_module(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, script(filename))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def debug_intake_show(args: dict[str, Any]) -> dict[str, Any]:
    module = _load_debug_module("debug_intake_mcp_show", "debug-intake.py")
    return {"tool": "debug_intake_show", "result": module.show(root_from(args), run_id(args)), "execution": {"read_only": True, "exit_code": 0}}


def debug_reproduction_show(args: dict[str, Any]) -> dict[str, Any]:
    module = _load_debug_module("debug_reproduction_mcp_show", "debug-reproduction.py")
    root = root_from(args)
    result = module.show(root, run_id(args))
    attempt = module.attempt_status(root, run_id(args))
    guidance = module.next_action_guidance(result, module.saved_canonical_requirement_uid(root, run_id(args)), attempt)
    return {"tool": "debug_reproduction_show", "result": result, "attempt_status": attempt, "next_actions": guidance, "execution": {"read_only": True, "exit_code": 0}}


def debug_reproduction_attempt_show(args: dict[str, Any]) -> dict[str, Any]:
    module = _load_debug_module("debug_reproduction_mcp_attempt_show", "debug-reproduction.py")
    result = module.attempt_status(root_from(args), run_id(args))
    return {"tool": "debug_reproduction_attempt_show", "result": result, "next_actions": module.attempt_guidance(result), "execution": {"read_only": True, "exit_code": 0}}


def debug_orientation_show(args: dict[str, Any]) -> dict[str, Any]:
    module = _load_debug_module("debug_orientation_mcp_show", "debug-orientation.py")
    return {"tool": "debug_orientation_show", "result": module.show(root_from(args), run_id(args)), "execution": {"read_only": True, "exit_code": 0}}


def debug_hypothesis_ledger_show(args: dict[str, Any]) -> dict[str, Any]:
    module = _load_debug_module("debug_hypothesis_mcp_show", "debug-hypothesis.py")
    return {"tool": "debug_hypothesis_ledger_show", "result": module.show(root_from(args), run_id(args)), "execution": {"read_only": True, "exit_code": 0}}


def debug_correction_show(args: dict[str, Any]) -> dict[str, Any]:
    module = _load_debug_module("debug_correction_mcp_show", "debug-correction.py")
    return {"tool":"debug_correction_show", "result":module.show(root_from(args), run_id(args)), "execution":{"read_only":True,"exit_code":0}}


def debug_governance_show(args: dict[str, Any]) -> dict[str, Any]:
    module = _load_debug_module("debug_governance_mcp_show", "debug-governance.py")
    return {"tool":"debug_governance_show", "result":module.show(root_from(args), run_id(args)), "execution":{"read_only":True,"exit_code":0}}


def debug_evaluation_report(args: dict[str, Any]) -> dict[str, Any]:
    module = _load_debug_module("debug_evaluation_mcp_report", "debug-evaluation.py")
    root = root_from(args); path = module.results_path(root)
    result = module.read(path) if path.is_file() else {"status":"missing","artifact":None}
    return {"tool":"debug_evaluation_report","result":result,"execution":{"read_only":True,"exit_code":0}}


def debug_release_gate(args: dict[str, Any]) -> dict[str, Any]:
    module = _load_debug_module("debug_evaluation_mcp_gate", "debug-evaluation.py")
    return {"tool":"debug_release_gate","result":module.release_gate(root_from(args)),"execution":{"read_only":True,"exit_code":0}}


def debug_harness_convergence_show(args: dict[str, Any]) -> dict[str, Any]:
    module = _load_debug_module("debug_convergence_mcp_show", "debug-harness-convergence.py")
    return {"tool":"debug_harness_convergence_show", "result":module.show(root_from(args), run_id(args)), "execution":{"read_only":True, "exit_code":0}}


def debug_completion_report_show(args: dict[str, Any]) -> dict[str, Any]:
    module = _load_debug_module("debug_completion_mcp_show", "debug-completion.py")
    return {"tool": "debug_completion_report_show", "result": module.show(root_from(args), run_id(args)), "execution": {"read_only": True, "exit_code": 0}}


def debug_start(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_start requires approved: true")
    symptom = str(args.get("symptom", "")).strip()
    if not symptom: raise ValueError("debug_start requires a non-empty symptom")
    root = root_from(args)
    identifier = args.get("run_id")
    identifier = str(identifier).strip() if isinstance(identifier, str) and identifier.strip() else None
    error_text = args.get("error"); error_text = error_text if isinstance(error_text, str) else None
    command_text = args.get("command"); command_text = command_text if isinstance(command_text, str) else None
    module = _load_debug_module("debug_intake_mcp_start", "debug-intake.py")
    result = module.open_intake(root, identifier, symptom, error_text, command_text, bool(args.get("attach", False)))
    return {"tool": "debug_start", "result": result, "execution": {"read_only": False, "requires_approval": True, "local_metadata_only": True, "exit_code": 0}}


def debug_reproduction_draft(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_reproduction_draft requires approved: true")
    source = args.get("contract")
    if not isinstance(source, dict): raise ValueError("debug_reproduction_draft requires a contract object")
    module = _load_debug_module("debug_reproduction_mcp_draft", "debug-reproduction.py")
    root = root_from(args)
    result = module.draft(root, run_id(args), source)
    guidance = module.next_action_guidance(result, module.saved_canonical_requirement_uid(root, run_id(args)))
    return {"tool": "debug_reproduction_draft", "result": result, "next_actions": guidance, "execution": {"read_only": False, "requires_approval": True, "local_metadata_only": True, "exit_code": 0}}


def debug_reproduction_revise(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_reproduction_revise requires approved: true")
    source = args.get("contract"); revision = args.get("revision")
    if not isinstance(source, dict) or not isinstance(revision, int) or revision < 1:
        raise ValueError("debug_reproduction_revise requires a contract object and positive revision")
    module = _load_debug_module("debug_reproduction_mcp_revise", "debug-reproduction.py")
    root = root_from(args)
    result = module.revise(root, run_id(args), revision, source)
    guidance = module.next_action_guidance(result, module.saved_canonical_requirement_uid(root, run_id(args)))
    return {"tool":"debug_reproduction_revise","result":result,"next_actions":guidance,"execution":{"read_only":False,"requires_approval":True,"local_metadata_only":True,"exit_code":0}}


def debug_reproduction_reopen(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_reproduction_reopen requires approved: true")
    source = args.get("contract"); revision = args.get("revision")
    if not isinstance(source, dict) or not isinstance(revision, int) or revision < 1:
        raise ValueError("debug_reproduction_reopen requires a contract object and positive revision")
    module = _load_debug_module("debug_reproduction_mcp_reopen", "debug-reproduction.py")
    root = root_from(args)
    result = module.reopen(root, run_id(args), revision, source)
    guidance = module.next_action_guidance(result, module.saved_canonical_requirement_uid(root, run_id(args)))
    return {"tool":"debug_reproduction_reopen","result":result,"next_actions":guidance,"execution":{"read_only":False,"requires_approval":True,"local_metadata_only":True,"exit_code":0}}


def debug_reproduction_approve(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_reproduction_approve requires approved: true")
    revision = args.get("revision")
    if not isinstance(revision, int) or revision < 1: raise ValueError("debug_reproduction_approve requires a positive revision")
    module = _load_debug_module("debug_reproduction_mcp_approve", "debug-reproduction.py")
    root = root_from(args)
    result = module.approve(root, run_id(args), revision)
    guidance = module.next_action_guidance(result, module.saved_canonical_requirement_uid(root, run_id(args)))
    return {"tool": "debug_reproduction_approve", "result": result, "next_actions": guidance, "execution": {"read_only": False, "requires_approval": True, "local_metadata_only": True, "exit_code": 0}}


def debug_reproduction_attempt_record(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_reproduction_attempt_record requires approved: true")
    checked = args.get("checked_dimensions")
    if not isinstance(checked, list): raise ValueError("debug_reproduction_attempt_record requires checked_dimensions")
    module = _load_debug_module("debug_reproduction_mcp_attempt_record", "debug-reproduction.py")
    result = module.record_attempt(
        root_from(args), run_id(args), str(args.get("phase", "")), str(args.get("outcome", "")),
        str(args.get("evidence_event_id", "")), str(args.get("observed_summary", "")), checked, True,
    )
    projection = result["status_projection"]
    return {"tool": "debug_reproduction_attempt_record", "result": result, "next_actions": module.attempt_guidance(projection), "execution": {"read_only": False, "requires_approval": True, "local_metadata_only": True, "project_commands_run": False, "exit_code": 0}}


def debug_orientation_create(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_orientation_create requires approved: true")
    module = _load_debug_module("debug_orientation_mcp_create", "debug-orientation.py")
    result = module.create(root_from(args), run_id(args))
    return {"tool": "debug_orientation_create", "result": result, "execution": {"read_only": False, "requires_approval": True, "local_metadata_only": True, "project_commands_run": False, "exit_code": 0}}


def debug_hypothesis_add(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_hypothesis_add requires approved: true")
    rank = args.get("rank")
    if not isinstance(rank, int) or rank < 1: raise ValueError("debug_hypothesis_add requires a positive rank")
    module = _load_debug_module("debug_hypothesis_mcp_add", "debug-hypothesis.py")
    result = module.add_hypothesis(root_from(args), run_id(args), str(args.get("domain", "")), str(args.get("statement", "")), rank)
    return {"tool":"debug_hypothesis_add","result":result,"execution":{"read_only":False,"requires_approval":True,"local_metadata_only":True,"project_commands_run":False,"exit_code":0}}


def debug_hypothesis_reprioritize(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_hypothesis_reprioritize requires approved: true")
    rankings = args.get("rankings")
    if not isinstance(rankings, list) or not rankings: raise ValueError("debug_hypothesis_reprioritize requires rankings")
    module = _load_debug_module("debug_hypothesis_mcp_rank", "debug-hypothesis.py")
    result = module.reprioritize(root_from(args), run_id(args), rankings)
    return {"tool":"debug_hypothesis_reprioritize","result":result,"execution":{"read_only":False,"requires_approval":True,"local_metadata_only":True,"project_commands_run":False,"exit_code":0}}


def debug_experiment_propose(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_experiment_propose requires approved: true")
    module = _load_debug_module("debug_hypothesis_mcp_propose", "debug-hypothesis.py")
    result = module.propose_experiment(root_from(args), run_id(args), str(args.get("hypothesis_id", "")), str(args.get("action", "")), str(args.get("expected_signal", "")))
    return {"tool":"debug_experiment_propose","result":result,"execution":{"read_only":False,"requires_approval":True,"local_metadata_only":True,"project_commands_run":False,"exit_code":0}}


def debug_experiment_record(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_experiment_record requires approved: true")
    hypothesis_id = str(args.get("hypothesis_id", "")).strip()
    action = str(args.get("action", "")).strip()
    expected_signal = str(args.get("expected_signal", "")).strip()
    outcome = args.get("outcome")
    evidence_event_id = str(args.get("evidence_event_id", "")).strip()
    if not hypothesis_id or not action or not expected_signal or not evidence_event_id: raise ValueError("debug_experiment_record requires hypothesis_id, action, expected_signal, and evidence_event_id")
    if outcome not in {"eliminates", "strengthens", "unchanged", "regressed", "new-drift", "inconclusive"}: raise ValueError("debug_experiment_record outcome is unsupported")
    module = _load_debug_module("debug_hypothesis_mcp_experiment", "debug-hypothesis.py")
    result = module.record_experiment(root_from(args), run_id(args), hypothesis_id, action, outcome, evidence_event_id, True, expected_signal)
    return {"tool": "debug_experiment_record", "result": result, "execution": {"read_only": False, "requires_approval": True, "local_metadata_only": True, "exit_code": 0}}


def debug_root_cause_prove(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_root_cause_prove requires approved: true")
    module = _load_debug_module("debug_hypothesis_mcp_prove", "debug-hypothesis.py")
    result = module.prove(
        root_from(args),
        run_id(args),
        str(args.get("hypothesis_id", "")),
        str(args.get("fault_layer", "")) or None,
        [str(value) for value in args.get("trace_node_ids", [])],
    )
    return {"tool":"debug_root_cause_prove","result":result,"execution":{"read_only":False,"requires_approval":True,"local_metadata_only":True,"project_commands_run":False,"exit_code":0}}


def debug_correction_approve(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_correction_approve requires approved: true")
    module = _load_debug_module("debug_correction_mcp_approve", "debug-correction.py")
    result = module.approve(root_from(args), run_id(args), True)
    return {"tool": "debug_correction_approve", "result": result, "execution": {"read_only": False, "requires_approval": True, "local_metadata_only": True, "exit_code": 0}}


def debug_correction_propose(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_correction_propose requires approved: true")
    hypothesis_id = str(args.get("hypothesis_id", "")).strip(); source = args.get("correction")
    if not hypothesis_id or not isinstance(source, dict): raise ValueError("debug_correction_propose requires hypothesis_id and a correction object")
    module = _load_debug_module("debug_correction_mcp_propose", "debug-correction.py")
    result = module.propose(root_from(args), run_id(args), hypothesis_id, str(args.get("statement", "")).strip() or None, source)
    return {"tool":"debug_correction_propose", "result":result, "execution":{"read_only":False, "requires_approval":True, "local_metadata_only":True, "project_commands_run":False, "exit_code":0}}


def debug_correction_scope_check(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_correction_scope_check requires approved: true")
    changed = args.get("changed")
    if not isinstance(changed, list) or not changed or not all(isinstance(item, str) for item in changed): raise ValueError("debug_correction_scope_check requires changed paths")
    module = _load_debug_module("debug_correction_mcp_scope", "debug-correction.py")
    result = module.scope_check(root_from(args), run_id(args), changed, True)
    return {"tool":"debug_correction_scope_check", "result":result, "execution":{"read_only":False, "requires_approval":True, "local_metadata_only":True, "project_files_changed":False, "exit_code":0}}


def debug_harness_convergence_finalize(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_harness_convergence_finalize requires approved: true")
    module = _load_debug_module("debug_convergence_mcp_finalize", "debug-harness-convergence.py")
    result = module.finalize(root_from(args), run_id(args), True)
    return {"tool":"debug_harness_convergence_finalize", "result":result, "execution":{"read_only":False, "requires_approval":True, "local_metadata_only":True, "project_commands_run":False, "project_files_changed":False, "exit_code":0}}


def debug_closure_finalize(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_closure_finalize requires approved: true")
    module = _load_debug_module("debug_closure_mcp_finalize", "closure-finalizer.py")
    result = module.finalize(root_from(args), run_id(args))
    return {"tool":"debug_closure_finalize","result":result,"execution":{"read_only":False,"requires_approval":True,"local_metadata_only":True,"project_commands_run":False,"project_files_changed":False,"acceptance_recorded":False,"exit_code":0}}


def debug_evaluation_run(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("debug_evaluation_run requires approved: true")
    module = _load_debug_module("debug_evaluation_mcp_run", "debug-evaluation.py")
    result = module.run(root_from(args), True)
    return {"tool":"debug_evaluation_run","result":result,"execution":{"read_only":False,"requires_approval":True,"local_metadata_only":True,"project_commands_run":False,"model_calls":False,"network_calls":False,"exit_code":0}}


def workflow_mcp(args: dict[str, Any], name: str) -> dict[str, Any]:
    from workflow_runtime import mcp_bridge
    return mcp_bridge.call(name, args)


def presentation_conformance(_args: dict[str, Any]) -> dict[str, Any]:
    module = spec_module("presentation.py", "presentation_conformance_mcp")
    return module.conformance()


def maintainability_inventory(args: dict[str, Any]) -> dict[str, Any]:
    module = spec_module("product-maintainability.py", "product_maintainability_mcp")
    return module.build(root_from(args))


def real_evaluation_portfolio_report(args: dict[str, Any]) -> dict[str, Any]:
    module = spec_module("real-evaluation-portfolio.py", "real_evaluation_portfolio_mcp")
    return module.report(root_from(args))


def adoption_validation_report(args: dict[str, Any]) -> dict[str, Any]:
    module = spec_module("adoption-validation.py", "adoption_validation_mcp")
    return module.report(root_from(args))


def enterprise_conformance_report(args: dict[str, Any]) -> dict[str, Any]:
    module = spec_module("enterprise-conformance.py", "enterprise_conformance_mcp")
    return module.inspect(root_from(args), run_probes=False)


def navigator_scope_proposal_record(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True:
        raise ValueError("navigator_scope_proposal_record requires approved: true")
    evidence = args.get("evidence")
    packet = args.get("packet")
    proposal = args.get("proposal")
    if not isinstance(proposal, dict):
        raise ValueError("proposal must be an object")
    if isinstance(evidence, dict) == isinstance(packet, dict):
        raise ValueError("supply exactly one of evidence or packet")
    module = _scope_module()
    if isinstance(evidence, dict):
        decision = module.host_proposal_decision(root_from(args), evidence, proposal)
    else:
        decision = module.host_packet_proposal_decision(root_from(args), packet, proposal)
    return {
        "tool": "navigator_scope_proposal_record",
        "persisted": False,
        "execution_blocked": True,
        "run_created": False,
        "result": decision,
    }


HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "navigator_plan": navigator_plan,
    "intent_resolve": intent_resolve,
    "requirement_intake_show": requirement_intake_show,
    "requirement_intake_answer": requirement_intake_answer,
    "debug_preflight": debug_preflight,
    "tailtrail_session_status": tailtrail_session_status,
    "tailtrail_stop": tailtrail_stop,
    "tailtrail_resume": tailtrail_resume,
    "start_report": start_report,
    "guardrail_check": guardrail_check,
    "graph_map": graph_map,
    "install_status": install_status,
    "eval_scenario_list": eval_scenario_list,
    "eval_scenario_report": eval_scenario_report,
    "ledger_state": ledger_state, "anchor_show": anchor_show, "harness_checkpoint_show": harness_checkpoint_show,
    "completion_feedback_show": completion_feedback_show, "profile_view": profile_view,
    "validation_receipt_show": validation_receipt_show, "release_confidence_show": release_confidence_show, "git_readiness": git_readiness,
    "recovery_boundary_show": recovery_boundary_show, "recovery_reconciliation_show": recovery_reconciliation_show, "architecture_assessment_show": architecture_assessment_show,
    "maintainability_assessment_show": maintainability_assessment_show, "context_continuity_show": context_continuity_show, "context_continuity_render": context_continuity_render, "context_continuity_advisory_show": context_continuity_advisory_show, "completion_report_show": completion_report_show, "execution_evidence_show": execution_evidence_show, "workflow_dashboard_show": workflow_dashboard_show, "planning_lock_show": planning_lock_show, "planning_decision_show": planning_decision_show, "planning_investigation_show": planning_investigation_show, "planning_revision_show": planning_revision_show, "planning_authority_show": planning_authority_show, "planning_aidlc_question_show": planning_aidlc_question_show, "planning_aidlc_question_clarify": planning_aidlc_question_clarify, "planning_question_context_show": planning_question_context_show, "aidlc_official_status": aidlc_official_status, "aidlc_official_bridge_show": aidlc_official_bridge_show, "aidlc_official_state_show": aidlc_official_state_show, "aidlc_official_sanitize_validate": aidlc_official_sanitize_validate, "aidlc_official_session_status": aidlc_official_session_status, "host_conformance_report": host_conformance_report, "presentation_conformance": presentation_conformance, "maintainability_inventory": maintainability_inventory, "real_evaluation_portfolio_report": real_evaluation_portfolio_report, "adoption_validation_report": adoption_validation_report, "enterprise_conformance_report": enterprise_conformance_report, "enterprise_target_policy_inspect": enterprise_target_policy_inspect, "harness_control_check": harness_control_check, "source_patch_apply": source_patch_apply, "planning_lock_start": planning_lock_start, "planning_investigate": planning_investigate, "planning_revision_propose": planning_revision_propose, "planning_revision_approve": planning_revision_approve, "planning_aidlc_standard_propose": planning_aidlc_standard_propose, "planning_aidlc_standard_approve": planning_aidlc_standard_approve, "planning_aidlc_question_challenge": planning_aidlc_question_challenge, "planning_aidlc_question_record": planning_aidlc_question_record, "planning_aidlc_question_approve": planning_aidlc_question_approve, "planning_lock_approve": planning_lock_approve, "tailtrail_start": tailtrail_start, "navigator_scope_proposal_record": navigator_scope_proposal_record, "execution_evidence_record": execution_evidence_record,
    "spec_kit_detect": spec_kit_detect, "spec_kit_mapping_show": spec_kit_mapping_show, "spec_kit_convergence_show": spec_kit_convergence_show, "spec_kit_import": spec_kit_import, "spec_kit_amendment_propose": spec_kit_amendment_propose, "spec_kit_anchor_approve": spec_kit_anchor_approve, "spec_kit_convergence_record": spec_kit_convergence_record, "spec_kit_ci_ingest": spec_kit_ci_ingest,
    "debug_intake_show": debug_intake_show, "debug_reproduction_show": debug_reproduction_show, "debug_reproduction_attempt_show": debug_reproduction_attempt_show, "debug_orientation_show": debug_orientation_show, "debug_hypothesis_ledger_show": debug_hypothesis_ledger_show, "debug_correction_show": debug_correction_show, "debug_governance_show": debug_governance_show, "debug_evaluation_report": debug_evaluation_report, "debug_release_gate": debug_release_gate, "debug_harness_convergence_show": debug_harness_convergence_show, "debug_completion_report_show": debug_completion_report_show,
    "debug_start": debug_start, "debug_reproduction_draft": debug_reproduction_draft, "debug_reproduction_revise": debug_reproduction_revise, "debug_reproduction_reopen": debug_reproduction_reopen, "debug_reproduction_approve": debug_reproduction_approve, "debug_reproduction_attempt_record": debug_reproduction_attempt_record, "debug_orientation_create": debug_orientation_create, "debug_hypothesis_add": debug_hypothesis_add, "debug_hypothesis_reprioritize": debug_hypothesis_reprioritize, "debug_experiment_propose": debug_experiment_propose, "debug_experiment_record": debug_experiment_record, "debug_root_cause_prove": debug_root_cause_prove, "debug_correction_propose": debug_correction_propose, "debug_correction_approve": debug_correction_approve, "debug_correction_scope_check": debug_correction_scope_check, "debug_harness_convergence_finalize": debug_harness_convergence_finalize, "debug_closure_finalize": debug_closure_finalize, "debug_evaluation_run": debug_evaluation_run,
}
HANDLERS["execution_evidence_run"] = execution_evidence_run
HANDLERS.update({name: (lambda args, tool=name: workflow_mcp(args, tool)) for name in WORKFLOW_MCP_TOOLS})


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    if name not in HANDLERS:
        raise ValueError(f"Unknown or disallowed MCP tool: {name}")
    return HANDLERS[name](arguments or {})


def mcp_content(value: Any) -> list[dict[str, str]]:
    return [{"type": "text", "text": json.dumps(value, indent=2, sort_keys=True)}]


def response(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")
    params = request.get("params") if isinstance(request.get("params"), dict) else {}
    try:
        if method == "initialize":
            return response(
                request_id,
                {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "tailtrail-mcp", "version": "1"},
                    "capabilities": {"tools": {}},
                },
            )
        if method == "tools/list":
            return response(request_id, {"tools": tool_list()})
        if method == "tools/call":
            name = str(params.get("name", ""))
            arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            value = call_tool(name, arguments)
            return response(request_id, {"content": mcp_content(value), "isError": False})
        if method == "notifications/initialized":
            return None
        return error_response(request_id, -32601, f"Unsupported method: {method}")
    except Exception as error:
        return error_response(request_id, -32000, str(error))


def serve() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as error:
            print(json.dumps(error_response(None, -32700, str(error))), flush=True)
            continue
        if not isinstance(request, dict):
            print(json.dumps(error_response(None, -32600, "request must be a JSON object")), flush=True)
            continue
        result = handle(request)
        if result is not None:
            print(json.dumps(result), flush=True)
    return 0


def render_tools() -> str:
    lines = ["# TailTrail MCP Tools", ""]
    for item in tool_list():
        lines.append(f"- `{item['name']}`: {item['description']}")
    return "\n".join(lines) + "\n"


def doctor() -> int:
    errors = ensure_safe_tools()
    if set(HANDLERS) != set((*READ_ONLY_TOOLS, *CONTROLLED_TOOLS)):
        errors.append("handler registry does not match the MCP tool allowlist")
    if errors:
        print("TailTrail MCP doctor failed.")
        for item in errors:
            print(f"- {item}")
        return 1
    print("TailTrail MCP doctor passed.")
    print(f"Read-only tools: {', '.join(READ_ONLY_TOOLS)}")
    print(f"Controlled tools: {', '.join(CONTROLLED_TOOLS)} (explicit approval required)")
    print("Mode: stdio, local, inspection-first")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run TailTrail's opt-in read-only MCP server.")
    parser.add_argument("action", choices=("serve", "tools", "doctor"))
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    if args.action == "serve":
        return serve()
    if args.action == "tools":
        if args.format == "json":
            print(json.dumps({"tools": tool_list(), "read_only": list(READ_ONLY_TOOLS), "controlled": list(CONTROLLED_TOOLS)}, indent=2, sort_keys=True))
        else:
            print(render_tools(), end="")
        return 0
    return doctor()


if __name__ == "__main__":
    raise SystemExit(main())
