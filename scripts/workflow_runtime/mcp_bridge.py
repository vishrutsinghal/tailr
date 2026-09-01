"""Bridge Deferred workflow controls, including policy-backed CI, to MCP."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from workflow_runtime import adapters, approvals, assurance, ci, compiler, contracts, correction, denials, enterprise, enterprise_recovery, enterprise_transport, evidence, freshness, ownership, release, resume, retention, start_integration, state, storage, task_scope

READ_ONLY = {
    "workflow_list": {"root"}, "workflow_show": {"root", "workflow_id"}, "workflow_status": {"root", "workflow_id"},
    "workflow_current": {"root", "workflow_id"}, "workflow_compiler_show": {"root", "workflow_id"},
    "workflow_approvals_show": {"root", "workflow_id"}, "workflow_freshness_show": {"root", "workflow_id"},
    "workflow_evidence_show": {"root", "workflow_id"}, "workflow_resume": {"root", "workflow_id"},
    "workflow_doctor": {"root", "workflow_id"}, "workflow_replay": {"root", "workflow_id"}, "workflow_ci_show": {"root", "workflow_id"},
    "workflow_assurance_inspect": {"root", "workflow_id"}, "workflow_denials_show": {"root", "workflow_id"},
    "workflow_retention_show": {"root", "policy_ref"}, "workflow_retention_plan": {"root", "policy_ref"},
    "workflow_release_catalog": {"root"}, "workflow_release_show": {"root"}, "workflow_release_compatibility": {"root"}, "workflow_release_evaluate": {"root"},
    "workflow_enterprise_entry": {"root", "policy_id"}, "workflow_enterprise_show": {"root", "workflow_id"},
    "workflow_enterprise_replay": {"root", "workflow_id"}, "workflow_enterprise_observe": {"root", "workflow_id"},
    "workflow_enterprise_restore_validate": {"root", "backup_ref"}, "workflow_enterprise_migration_plan": {"root", "workflow_id", "direction"},
    "workflow_enterprise_conformance": {"root", "workflow_id"},
}
CONTROLLED = {
    "workflow_create": {"root", "run_id", "workflow_id", "approved"},
    "workflow_approval_decide": {"root", "workflow_id", "stage_ids", "action_classes", "operation_kind", "operation_ref", "decision", "rationale", "approved"},
    "workflow_state_control": {"root", "workflow_id", "action", "successor_workflow_id", "approved"},
    "workflow_adapter_record": {"root", "workflow_id", "stage_id", "adapter_id", "result_ref", "approved"},
    "workflow_correction_request": {"root", "workflow_id", "stage_id", "classification", "max_cycles", "approved"},
    "workflow_closure_finalize": {"root", "workflow_id", "accept_evidence_incomplete", "approved"},
    "workflow_ci_ingest": {"root", "workflow_id", "receipt_ref", "policy_ref", "approved"},
    "workflow_retention_cleanup": {"root", "workflow_id", "plan_fingerprint", "policy_ref", "approved"},
    "workflow_release_scenario_record": {"root", "workflow_id", "observation_ref", "approved"},
    "workflow_real_run_record": {"root", "workflow_id", "observation_ref", "approved"},
    "workflow_release_retire": {"root", "gate_fingerprint", "approved"},
    "workflow_enterprise_policy_record": {"root", "policy_ref", "approved"},
    "workflow_enterprise_activate": {"root", "workflow_id", "policy_id", "tenant_id", "repository_id", "actor_id", "approved"},
    "workflow_enterprise_link": {"root", "workflow_id", "identity_ref", "actor_id", "approved"},
    "workflow_enterprise_lease_acquire": {"root", "workflow_id", "tenant_id", "actor_id", "approved"},
    "workflow_enterprise_lease_release": {"root", "workflow_id", "tenant_id", "actor_id", "lease_id", "fencing_token", "approved"},
    "workflow_enterprise_ingest": {"root", "workflow_id", "receipt_ref", "approved"},
    "workflow_enterprise_backup": {"root", "workflow_id", "approved"},
    "workflow_enterprise_migrate": {"root", "workflow_id", "direction", "migration_fingerprint", "approved"},
    "workflow_enterprise_rollback": {"root", "workflow_id", "migration_fingerprint", "approved"},
}


def root_from(args: dict[str, Any]) -> Path:
    value = args.get("root")
    return Path(value).expanduser().resolve() if isinstance(value, str) and value else Path.cwd().resolve()


def _required(args: dict[str, Any], *names: str) -> None:
    missing = [name for name in names if args.get(name) in (None, "", [])]
    if missing: raise ValueError("missing required MCP field(s): " + ", ".join(missing))


def validate_call(name: str, args: dict[str, Any]) -> None:
    allowed = READ_ONLY.get(name) or CONTROLLED.get(name)
    if allowed is None: raise ValueError("unknown workflow MCP tool")
    unknown = sorted(set(args) - allowed)
    if unknown: raise ValueError("unknown MCP field(s): " + ", ".join(unknown))
    if name in CONTROLLED and args.get("approved") is not True: raise ValueError(f"{name} requires approved: true")
    if "root" in args and not isinstance(args["root"], str): raise ValueError("root must be a string")
    if "accept_evidence_incomplete" in args and not isinstance(args["accept_evidence_incomplete"], bool): raise ValueError("accept_evidence_incomplete must be a boolean")
    for field in ("stage_ids", "action_classes"):
        if field in args and (not isinstance(args[field], list) or not all(isinstance(item, str) and item for item in args[field])): raise ValueError(f"{field} must be an array of non-empty strings")
    for field in ("operation_kind", "operation_ref", "decision", "rationale", "result_ref", "classification", "action", "plan_fingerprint", "observation_ref", "gate_fingerprint", "policy_id", "tenant_id", "repository_id", "actor_id", "lease_id", "fencing_token", "direction", "migration_fingerprint"):
        if field in args and args[field] is not None and (not isinstance(args[field], str) or not args[field].strip()): raise ValueError(f"{field} must be a non-empty string")
    if "max_cycles" in args and (not isinstance(args["max_cycles"], int) or isinstance(args["max_cycles"], bool) or args["max_cycles"] not in {1,2}): raise ValueError("max_cycles must be 1 or 2")
    if "decision" in args and args["decision"] not in {"approved","rejected","edited"}: raise ValueError("decision is unsupported")
    if "action" in args and args["action"] not in {"pause","resume","cancel","supersede"}: raise ValueError("action is unsupported")
    if "direction" in args and args["direction"] not in {"local-to-enterprise","enterprise-to-local"}: raise ValueError("direction is unsupported")
    for field in ("workflow_id", "run_id", "stage_id", "adapter_id", "successor_workflow_id"):
        if field in args and args[field] is not None and (not isinstance(args[field], str) or not args[field].strip()): raise ValueError(f"{field} must be a non-empty string")
    for field in ("operation_ref", "result_ref", "receipt_ref", "policy_ref", "observation_ref", "identity_ref", "backup_ref"):
        if field in args and args[field] is not None and (not isinstance(args[field], str) or not contracts.safe_relative(args[field])): raise ValueError(f"{field} must be a safe relative reference")


def _preflight(root: Path, workflow_id: str) -> None:
    ownership_check = ownership.validate(root, workflow_id)
    if not ownership_check["valid"]: raise ValueError("MCP canonical ownership/target preflight failed: " + "; ".join(ownership_check["issues"]))
    plan_check = compiler.validate(root, workflow_id)
    if not plan_check["valid"]: raise ValueError("MCP frozen plan/policy preflight failed: " + "; ".join(plan_check["issues"]))
    scope_check = task_scope.freshness(root, workflow_id)
    if not scope_check["valid"] or not scope_check["fresh"]:
        reasons = [*scope_check["issues"], *(str(row.get("reason")) for row in scope_check["stale_requirements"])]
        raise ValueError("MCP scope/freshness preflight failed: " + "; ".join(reasons))


def _create(root: Path, run_id: str, requested_workflow_id: str | None) -> dict[str, Any]:
    """Finish the saved Start activation; never manufacture a parallel run."""
    lock = ownership.LOCK.show(root, run_id)
    if lock.get("status") != "approved" or lock.get("writes_allowed") is not True:
        raise ValueError(f"workflow_create requires an approved Planning Lock for run `{run_id}`")
    saved = ownership.LOCK.active_start_report(root, run_id).get("report", {})
    descriptor = saved.get("workflow_runtime", {}) if isinstance(saved, dict) else {}
    if not isinstance(descriptor, dict) or descriptor.get("enabled") is not True:
        raise ValueError("workflow_create requires the approved Start report's enabled workflow draft")
    workflow_id = str(descriptor.get("workflow_id", ""))
    if not workflow_id:
        raise ValueError("approved Start workflow draft has no canonical workflow ID")
    if requested_workflow_id is not None and requested_workflow_id != workflow_id:
        raise ValueError("requested workflow ID differs from the approved Start workflow draft")
    anchor_path = ownership.LEDGER.state_dir(root, run_id) / "anchors" / "approved-v1.json"
    if not anchor_path.is_file():
        raise ValueError("workflow_create requires the immutable approved canonical anchor")
    if ownership.binding_path(root, workflow_id).is_file():
        ownership_check = ownership.validate(root, workflow_id)
        if not ownership_check["valid"]:
            raise ValueError("MCP canonical ownership/target preflight failed: " + "; ".join(ownership_check["issues"]))
        if compiler.plan_path(root, workflow_id).is_file():
            plan_check = compiler.validate(root, workflow_id)
            if not plan_check["valid"]:
                raise ValueError("MCP frozen plan/policy preflight failed: " + "; ".join(plan_check["issues"]))
        try:
            task_scope.show(root, workflow_id)
        except ValueError as error:
            if "does not exist" not in str(error):
                raise
        else:
            scope_check = task_scope.freshness(root, workflow_id)
            if not scope_check["valid"] or not scope_check["fresh"]:
                reasons = [*scope_check["issues"], *(str(row.get("reason")) for row in scope_check["stale_requirements"])]
                raise ValueError("MCP scope/freshness preflight failed: " + "; ".join(reasons))
    activation = start_integration.activate(root, run_id, saved, anchor_path.relative_to(root).as_posix())
    try:
        task_scope.show(root, workflow_id)
    except ValueError as error:
        if "does not exist" not in str(error):
            raise
        task_scope.initialize(root, workflow_id)
    _preflight(root, workflow_id)
    return {"activation": activation, "state_view": state.show(root, workflow_id), "boundary": "MCP completed only the approved saved Start workflow draft and passed canonical ownership, target, plan, policy, scope, and freshness validation."}


def _finalize(root: Path, workflow_id: str, accept_incomplete: bool) -> dict[str, Any]:
    binding = ownership.show(root, workflow_id)
    script = Path(__file__).resolve().parents[1] / "closure-finalizer.py"
    spec = importlib.util.spec_from_file_location("workflow_mcp_closure_finalizer", script)
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(module)
    report = module.finalize(root, binding["tailtrail_run_id"])
    receipt = evidence.close(root, workflow_id, accept_incomplete, True)
    return {"completion_report":report, "workflow_receipt":receipt, "boundary":"Canonical closure finalizer ran before the workflow completion receipt was linked."}


def _read(name: str, args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); workflow_id = str(args.get("workflow_id", ""))
    if name == "workflow_list": return state.list_workflows(root)
    if name == "workflow_retention_show": return retention.show(root,args.get("policy_ref"))
    if name == "workflow_retention_plan": return retention.plan(root,args.get("policy_ref"))
    if name == "workflow_release_catalog": return release.catalog()
    if name == "workflow_release_show": return release.show(root)
    if name == "workflow_release_compatibility": return release.compatibility(root)
    if name == "workflow_release_evaluate": return release.evaluate(root)
    if name == "workflow_enterprise_entry": _required(args,"policy_id"); return enterprise.entry(root,str(args["policy_id"]))
    if name == "workflow_enterprise_restore_validate": _required(args,"backup_ref"); return enterprise_recovery.restore_validate(root,str(args["backup_ref"]))
    _required(args, "workflow_id")
    if name == "workflow_show": return state.show(root, workflow_id)
    if name == "workflow_status": return state.show(root, workflow_id)
    if name == "workflow_compiler_show": return compiler.show(root, workflow_id)
    if name == "workflow_approvals_show": return approvals.show(root, workflow_id)
    if name == "workflow_freshness_show": return freshness.show(root, workflow_id)
    if name == "workflow_evidence_show":
        collected = evidence.show(root, workflow_id, missing_ok=True)
        receipt_path = evidence.receipt_path(root, workflow_id)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.is_file() else None
        return {"workflow_id":workflow_id,"evidence":collected,"completion_receipt":receipt,"status":"available" if collected else "not-collected","boundary":"Read-only canonical evidence and completion receipt references."}
    if name == "workflow_resume": return resume.plan(root, workflow_id)
    if name == "workflow_doctor": return state.doctor(root, workflow_id)
    if name == "workflow_replay": return storage.replay(root, workflow_id)
    if name == "workflow_ci_show": return ci.show(root, workflow_id)
    if name == "workflow_assurance_inspect": return assurance.inspect(root,workflow_id)
    if name == "workflow_denials_show": return denials.show(root,workflow_id)
    if name == "workflow_enterprise_show": return enterprise.show(root,workflow_id)
    if name == "workflow_enterprise_replay": return enterprise_transport.replay(root,workflow_id)
    if name == "workflow_enterprise_observe": return enterprise_transport.observe(root,workflow_id)
    if name == "workflow_enterprise_migration_plan": _required(args,"direction"); return enterprise_recovery.migration_plan(root,workflow_id,str(args["direction"]))
    if name == "workflow_enterprise_conformance": return enterprise_recovery.conformance(root,workflow_id)
    projection = storage.status(root, workflow_id)["last_valid_projection"]
    current = next((stage_id for stage_id,row in projection.get("stages",{}).items() if row.get("status") not in {"passed","skipped"}), None)
    return {"workflow_id":workflow_id,"workflow_status":projection["workflow_status"],"current_stage_id":current,"requirement_uids":ownership.show(root,workflow_id)["requirement_uids"],
        "advancement_posture":"artifact-projection-only",
        "advancement_explanation":"Debug artifacts may be drafted ahead of the canonical stage. The stage advances only from a linked workflow adapter/stage result recorded with matching authority; read-only inspection never advances it.",
        "boundary":"Read-only canonical workflow state. No artifact presence was treated as stage-transition evidence."}


def _controlled(name: str, args: dict[str, Any]) -> dict[str, Any]:
    root=root_from(args)
    if name == "workflow_release_retire":
        _required(args,"gate_fingerprint"); return release.retire(root,str(args["gate_fingerprint"]),True)
    if name == "workflow_enterprise_policy_record":
        _required(args,"policy_ref"); return enterprise.record_policy(root,str(args["policy_ref"]),True)
    if name == "workflow_create":
        _required(args,"run_id"); return _create(root,str(args["run_id"]),args.get("workflow_id"))
    _required(args,"workflow_id"); workflow_id=str(args["workflow_id"]); _preflight(root, workflow_id)
    if name == "workflow_enterprise_activate":
        _required(args,"policy_id","tenant_id","repository_id","actor_id"); return enterprise.activate(root,workflow_id,str(args["policy_id"]),str(args["tenant_id"]),str(args["repository_id"]),str(args["actor_id"]),True)
    if name == "workflow_enterprise_link": _required(args,"identity_ref","actor_id"); return enterprise.link(root,workflow_id,str(args["identity_ref"]),str(args["actor_id"]),True)
    if name == "workflow_enterprise_lease_acquire": _required(args,"tenant_id","actor_id"); return enterprise_transport.acquire(root,workflow_id,str(args["tenant_id"]),str(args["actor_id"]),True)
    if name == "workflow_enterprise_lease_release": _required(args,"tenant_id","actor_id","lease_id","fencing_token"); return enterprise_transport.release_lease(root,workflow_id,str(args["tenant_id"]),str(args["actor_id"]),str(args["lease_id"]),str(args["fencing_token"]),True)
    if name == "workflow_enterprise_ingest": _required(args,"receipt_ref"); return enterprise_transport.ingest(root,workflow_id,str(args["receipt_ref"]),True)
    if name == "workflow_enterprise_backup": return enterprise_recovery.backup(root,workflow_id,True)
    if name == "workflow_enterprise_migrate": _required(args,"direction","migration_fingerprint"); return enterprise_recovery.migrate(root,workflow_id,str(args["direction"]),str(args["migration_fingerprint"]),True)
    if name == "workflow_enterprise_rollback": _required(args,"migration_fingerprint"); return enterprise_recovery.rollback(root,workflow_id,str(args["migration_fingerprint"]),True)
    if name == "workflow_approval_decide":
        _required(args,"stage_ids","action_classes","operation_kind","operation_ref","decision","rationale")
        return approvals.decide(root,workflow_id,stage_ids=list(args["stage_ids"]),action_classes=list(args["action_classes"]),operation_kind=str(args["operation_kind"]),operation_ref=str(args["operation_ref"]),decision=str(args["decision"]),rationale=str(args["rationale"]))
    if name == "workflow_state_control":
        action=args.get("action"); _required(args,"action")
        if action == "pause": return state.pause(root,workflow_id)
        if action == "resume": return state.resume(root,workflow_id)
        if action == "cancel": return state.cancel(root,workflow_id,True)
        if action == "supersede":
            _required(args,"successor_workflow_id"); return state.supersede(root,workflow_id,str(args["successor_workflow_id"]))
        raise ValueError("action must be pause, resume, cancel, or supersede")
    if name == "workflow_adapter_record":
        _required(args,"stage_id","adapter_id","result_ref"); return adapters.record(root,workflow_id,str(args["stage_id"]),str(args["adapter_id"]),str(args["result_ref"]))
    if name == "workflow_correction_request":
        _required(args,"stage_id"); return correction.route(root,workflow_id,str(args["stage_id"]),args.get("classification"),int(args.get("max_cycles",2)))
    if name == "workflow_ci_ingest":
        _required(args,"receipt_ref","policy_ref"); return ci.ingest(root,workflow_id,str(args["receipt_ref"]),str(args["policy_ref"]),True)
    if name == "workflow_retention_cleanup":
        _required(args,"plan_fingerprint"); return retention.cleanup(root,workflow_id,str(args["plan_fingerprint"]),args.get("policy_ref"),True)
    if name == "workflow_release_scenario_record":
        _required(args,"observation_ref"); return release.record_scenario(root,workflow_id,str(args["observation_ref"]),True)
    if name == "workflow_real_run_record":
        _required(args,"observation_ref"); return release.record_real_run(root,workflow_id,str(args["observation_ref"]),True)
    return _finalize(root,workflow_id,bool(args.get("accept_evidence_incomplete")))


def call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    try:
        validate_call(name,args); result = _read(name,args) if name in READ_ONLY else _controlled(name,args)
    except (OSError,ValueError,json.JSONDecodeError) as error:
        if name in CONTROLLED: denials.best_effort(root_from(args),args.get("workflow_id"),name,str(error),"mcp")
        raise
    return {"tool":name,"result":result,"execution":{"read_only":name in READ_ONLY,"requires_approval":name in CONTROLLED,"local_metadata_only":name in CONTROLLED,"exit_code":0},"boundary":"MCP bridges canonical runtime controls only; it cannot forge planning, AIDLC, dependency, recovery, or closure authority."}
