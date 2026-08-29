"""Canonical DWR Phase 3 approval records and guarded-stage authority checks."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from workflow_runtime import compiler, contracts, ownership, storage, task_scope


LEDGER = ownership.LEDGER
LOW_RISK = {"read_local", "write_tailtrail_state"}
ACTION_CLASSES = LOW_RISK | {"write_project", "execute_project", "scan_local", "external_provider", "publish"}
OPERATION_KINDS = {"initial-plan", "dependency", "broad-test-build", "scanner", "security-sensitive", "external-provider", "fix-application", "publish", "deploy", "merge", "other-guarded", "skip"}
SKIP_REASONS = {"not-applicable", "superseded-by-approved-stage", "duplicate-proof", "policy-exempt", "user-declined"}
OPERATION_CLASSES = {"initial-plan": {"write_tailtrail_state"}, "broad-test-build": {"execute_project"}, "scanner": {"scan_local"},
                     "external-provider": {"external_provider"}, "fix-application": {"write_project"},
                     "publish": {"publish"}, "deploy": {"publish"}, "merge": {"publish"}, "skip": {"write_tailtrail_state"}}


def path(root: Path, workflow_id: str) -> Path:
    return ownership.binding_path(root.resolve(), workflow_id).parent / "stage-approvals-v1.json"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _time(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("approval expiry must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError("approval expiry must include a timezone")
    return parsed.astimezone(timezone.utc)


def _relative(root: Path, value: str) -> str:
    if not contracts.safe_relative(value):
        raise ValueError("approval references must be safe repository-relative paths")
    return value


def _policy_fingerprint(root: Path) -> tuple[str, list[str]]:
    rows: list[dict[str, str]] = []
    for candidate in (compiler.policy_path(root), root / "tailtrail-policy.md", root / "GUARDRAILS.md"):
        if candidate.is_file():
            rows.append({"ref": candidate.relative_to(root).as_posix(), "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest()})
    return _digest(rows), [row["ref"] for row in rows]


def _stage_graph_fingerprint(plan: dict[str, Any]) -> str:
    return _digest([{"stage_id": row["stage_id"], "prerequisites": row.get("prerequisites", []), "approval_class": row.get("approval_class"), "action_class": row.get("action_class"), "adapter_id": row.get("adapter_id"), "adapter_action_class": row.get("adapter_action_class")} for row in plan["stages"]])


def _scope(root: Path, workflow_id: str, binding: dict[str, Any]) -> tuple[str, str, list[str]]:
    # The approved anchor is the stable approval scope. DWR-C may later add a
    # file-level operational scope; capturing that derived detail must not by
    # itself revoke a valid decision.
    return str(binding["approved_anchor_ref"]), str(binding["approved_anchor_fingerprint"]), list(binding["requirement_uids"])


def _context(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); binding = ownership.show(root, workflow_id); plan = compiler.show(root, workflow_id)
    if plan.get("tailtrail_run_id") != binding.get("tailtrail_run_id"):
        raise ValueError("compiler plan and workflow binding use different TailTrail runs")
    scope_ref, scope_fingerprint, requirement_uids = _scope(root, workflow_id, binding)
    policy_fingerprint, policy_refs = _policy_fingerprint(root)
    return {"binding": binding, "plan": plan, "scope_ref": scope_ref, "scope_fingerprint": scope_fingerprint,
            "requirement_uids": requirement_uids, "policy_fingerprint": policy_fingerprint,
            "policy_refs": policy_refs, "stage_graph_fingerprint": _stage_graph_fingerprint(plan)}


def _empty(context: dict[str, Any]) -> dict[str, Any]:
    binding = context["binding"]
    return {"schema_version": "1", "type": "tailtrail-workflow-stage-approvals",
            "workflow_id": binding["workflow_id"], "tailtrail_run_id": binding["tailtrail_run_id"],
            "approvals": [], "boundary": "Approval metadata only. Runtime approval cannot replace Planning Lock, AIDLC, dependency-gate, recovery, closure acceptance, or host safety authority."}


def _load(root: Path, workflow_id: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    destination = path(root, workflow_id)
    if not destination.is_file():
        return _empty(context or _context(root, workflow_id))
    payload = json.loads(destination.read_text(encoding="utf-8"))
    if payload.get("workflow_id") != workflow_id or payload.get("type") != "tailtrail-workflow-stage-approvals":
        raise ValueError("workflow approval ledger is invalid")
    return payload


def _record_id(record: dict[str, Any]) -> str:
    stable = {key: value for key, value in record.items() if key not in {"approval_id", "expired_at", "expiry_reason"}}
    return "wfauth-" + hashlib.sha256(_canonical(stable).encode("utf-8")).hexdigest()[:24]


def _record(root: Path, workflow_id: str, *, stage_ids: list[str], action_classes: list[str], operation_kind: str,
            operation_ref: str, decision: str, source: str, rationale: str, expires_at: str | None = None,
            session_id: str | None = None, policy_ref: str | None = None, skip_reason_code: str | None = None) -> dict[str, Any]:
    root = root.resolve(); context = _context(root, workflow_id); plan = context["plan"]
    known = {str(row["stage_id"]) for row in plan["stages"]}; stages = sorted(set(stage_ids)); classes = sorted(set(action_classes))
    if not stages or not set(stages) <= known: raise ValueError("approval stage IDs must exist in the current compiler graph")
    if not classes or not set(classes) <= ACTION_CLASSES: raise ValueError("approval contains an unknown action class")
    if operation_kind not in OPERATION_KINDS: raise ValueError("approval contains an unknown guarded operation kind")
    if decision not in {"approved", "rejected", "edited"}: raise ValueError("approval decision must be approved, rejected, or edited")
    if source not in {"interactive", "plan-derived", "session", "policy"}: raise ValueError("approval source is invalid")
    if source in {"session", "policy"} and not set(classes) <= LOW_RISK: raise ValueError("session/policy pre-approval cannot authorize project execution, scan, provider, or publish actions")
    required_classes = OPERATION_CLASSES.get(operation_kind, set())
    if not required_classes <= set(classes): raise ValueError(f"{operation_kind} approval requires action class: " + ", ".join(sorted(required_classes)))
    if operation_kind == "security-sensitive" and not set(classes) & {"execute_project", "scan_local"}: raise ValueError("security-sensitive approval requires execute_project or scan_local")
    if operation_kind == "skip" and skip_reason_code not in SKIP_REASONS: raise ValueError("skip approval requires a categorical skip reason code")
    if operation_kind != "skip" and skip_reason_code is not None: raise ValueError("skip reason is valid only for an explicit skip approval")
    if operation_kind == "dependency" and not policy_ref: raise ValueError("dependency stage approval requires a separate dependency-decision reference")
    if operation_kind == "dependency" and policy_ref:
        decision_path, _pointer = ownership._resolve_ref(root, policy_ref)
        dependency = json.loads(decision_path.read_text(encoding="utf-8"))
        if dependency.get("type") != "tailtrail-dependency-decision" or dependency.get("status") != "approved":
            raise ValueError("dependency runtime approval requires a separately approved Dependency Gate decision artifact")
    expiry = _time(expires_at)
    if source == "session" and expiry is None: expiry = _now() + timedelta(hours=8)
    if expiry is not None and expiry <= _now(): raise ValueError("approval expiry must be in the future when recorded")
    created_at = _now().isoformat(); record = {
        "schema_version": "1", "type": "tailtrail-workflow-approval-record", "workflow_id": workflow_id,
        "tailtrail_run_id": plan["tailtrail_run_id"], "revision": int(plan["revision"]),
        "compiler_plan_fingerprint": plan["plan_fingerprint"], "stage_graph_fingerprint": context["stage_graph_fingerprint"],
        "target_identity_fingerprint": plan["target_identity_fingerprint"], "approved_anchor_fingerprint": context["binding"]["approved_anchor_fingerprint"],
        "stage_ids": stages, "action_classes": classes, "operation_kind": operation_kind,
        "bounded_operation_ref": _relative(root, operation_ref), "scope_ref": context["scope_ref"],
        "scope_fingerprint": context["scope_fingerprint"], "requirement_uids": context["requirement_uids"],
        "decision": decision, "source": source, "created_at": created_at,
        "expires_at": expiry.isoformat() if expiry else None, "session_id": session_id,
        "policy_ref": _relative(root, policy_ref) if policy_ref else None,
        "policy_fingerprint": context["policy_fingerprint"], "rationale": rationale.strip(),
        "skip_reason_code": skip_reason_code, "reason_code": "approval-granted" if decision == "approved" else "approval-rejected",
        "authority_boundary": "This decision authorizes only the named runtime stage/operation metadata. Separate Planning Lock, AIDLC, dependency, recovery, closure, and host-safety authority remains mandatory.",
    }
    if not record["rationale"]: raise ValueError("approval requires a rationale")
    record["approval_id"] = _record_id(record); contracts.require_valid(record)
    ledger = _load(root, workflow_id, context)
    if any(row.get("approval_id") == record["approval_id"] for row in ledger["approvals"]):
        return {"artifact": path(root, workflow_id).relative_to(root).as_posix(), **ledger, "status": "unchanged"}
    ledger["approvals"].append(record); contracts.require_valid(ledger); LEDGER.atomic_json(path(root, workflow_id), ledger)
    LEDGER.append_event(root, plan["tailtrail_run_id"], "workflow_stage_approval_recorded", {"workflow_id": workflow_id, "approval_id": record["approval_id"], "decision": decision, "source": source, "stage_ids": stages, "action_classes": classes, "operation_kind": operation_kind})
    return {"artifact": path(root, workflow_id).relative_to(root).as_posix(), **ledger, "status": "recorded", "record": record}


def record_initial(root: Path, workflow_id: str) -> dict[str, Any]:
    context = _context(root.resolve(), workflow_id); plan = context["plan"]
    return _record(root, workflow_id, stage_ids=[str(row["stage_id"]) for row in plan["stages"]], action_classes=["write_tailtrail_state"],
                   operation_kind="initial-plan", operation_ref=str(context["binding"]["planning_lock_ref"]), decision="approved", source="interactive",
                   rationale="Canonical Planning Lock and immutable approved anchor were approved for this exact run, target, compiler graph, and scope.")


def grant_approved_plan(root: Path, workflow_id: str) -> dict[str, Any]:
    """Derive safe local execution authority from one approved Lite/Off plan."""
    context = _context(root.resolve(), workflow_id)
    safe_classes = {"read_local", "write_tailtrail_state", "write_project", "execute_project"}
    stages = [str(row["stage_id"]) for row in context["plan"]["stages"] if str(row.get("adapter_action_class")) in safe_classes]
    classes = sorted({str(row.get("adapter_action_class")) for row in context["plan"]["stages"] if str(row.get("stage_id")) in stages})
    return _record(
        root, workflow_id, stage_ids=stages, action_classes=classes,
        operation_kind="other-guarded", operation_ref=str(context["plan"]["artifact"]),
        decision="approved", source="plan-derived",
        rationale="The user approved this exact Lite/Off Planning Lock and immutable anchor; safe local inspection, scoped implementation, focused validation, review, and TailTrail-state stages inherit that bounded authority.",
    )


def decide(root: Path, workflow_id: str, **values: Any) -> dict[str, Any]:
    return _record(root, workflow_id, source="interactive", **values)


def grant_session(root: Path, workflow_id: str, action_classes: list[str], approved: bool, session_id: str = "local-session", expires_at: str | None = None) -> dict[str, Any]:
    if not approved: raise ValueError("session stage approval requires --approved")
    if storage.status(root.resolve(), workflow_id)["last_valid_projection"].get("workflow_status") == "paused": raise ValueError("session approval cannot be granted while the workflow is paused")
    context = _context(root.resolve(), workflow_id); canonical = {"read-only": "read_local", "tailtrail-state": "write_tailtrail_state", **{item: item for item in ACTION_CLASSES}}
    requested = sorted({canonical.get(item, "unknown") for item in action_classes})
    if not requested or not set(requested) <= LOW_RISK: raise ValueError("session stage approval supports only read_local/write_tailtrail_state")
    stages = [str(row["stage_id"]) for row in context["plan"]["stages"] if canonical.get(str(row.get("action_class"))) in requested]
    return _record(root, workflow_id, stage_ids=stages, action_classes=requested, operation_kind="other-guarded",
                   operation_ref=str(context["plan"]["artifact"]), decision="approved", source="session", rationale="Explicit low-risk approval for this host session only.", expires_at=expires_at, session_id=session_id)


def grant_policy(root: Path, workflow_id: str, stage_ids: list[str], policy_ref: str) -> dict[str, Any]:
    context = _context(root.resolve(), workflow_id); mapping = {"read-only": "read_local", "tailtrail-state": "write_tailtrail_state"}
    rows = {str(row["stage_id"]): row for row in context["plan"]["stages"]}
    classes = sorted({mapping.get(str(rows[item].get("action_class")), "unknown") for item in stage_ids if item in rows})
    return _record(root, workflow_id, stage_ids=stage_ids, action_classes=classes, operation_kind="other-guarded", operation_ref=policy_ref,
                   decision="approved", source="policy", rationale="Low-risk stage pre-approved by the active compiler policy.", policy_ref=policy_ref)


def expire_session(root: Path, workflow_id: str, session_id: str | None, reason: str) -> dict[str, Any]:
    root = root.resolve()
    if not path(root, workflow_id).is_file():
        return {"type": "tailtrail-workflow-session-approval-expiry", "workflow_id": workflow_id, "expired": 0, "reason": reason, "boundary": "No session approval ledger exists; no project or canonical state changed."}
    ledger = _load(root, workflow_id); count = 0
    for row in ledger["approvals"]:
        if row.get("source") == "session" and (session_id is None or row.get("session_id") == session_id) and row.get("decision") == "approved" and not row.get("expired_at"):
            row["expired_at"] = _now().isoformat(); row["expiry_reason"] = reason; count += 1
    if count:
        contracts.require_valid(ledger); LEDGER.atomic_json(path(root, workflow_id), ledger)
        binding = ownership.show(root, workflow_id)
        LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_stage_approval_expired", {"workflow_id": workflow_id, "source": "session", "session_id": session_id, "reason": reason, "count": count})
    return {"type": "tailtrail-workflow-session-approval-expiry", "workflow_id": workflow_id, "expired": count, "reason": reason, "boundary": "Only session approval metadata expired; no project action or canonical approval changed."}


def _integrity_issues(workflow_id: str, row: dict[str, Any], context: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if row.get("approval_id") != _record_id(row): issues.append("forged or modified approval ID")
    if row.get("workflow_id") != workflow_id or row.get("tailtrail_run_id") != context["plan"].get("tailtrail_run_id"): issues.append("cross-run or cross-workflow approval")
    known = {str(item["stage_id"]) for item in context["plan"]["stages"]}
    if not set(row.get("stage_ids", [])) <= known: issues.append("approval references an unknown compiler stage")
    if not set(row.get("action_classes", [])) <= ACTION_CLASSES: issues.append("approval references an unknown action class")
    return issues


def _issues(root: Path, workflow_id: str, row: dict[str, Any], context: dict[str, Any]) -> list[str]:
    issues = _integrity_issues(workflow_id, row, context)
    lock = ownership._read_ref(root, str(context["binding"]["planning_lock_ref"]))
    identity = ownership.TARGET.verify_identity(lock.get("target_identity", {}) if isinstance(lock, dict) else {}, root)
    if row.get("target_identity_fingerprint") != context["plan"].get("target_identity_fingerprint") or not ownership.validate(root, workflow_id)["valid"] or identity.get("status") not in {"matched", "legacy"}: issues.append("cross-target or stale target approval")
    if row.get("revision") != context["plan"].get("revision") or row.get("compiler_plan_fingerprint") != context["plan"].get("plan_fingerprint") or row.get("stage_graph_fingerprint") != context["stage_graph_fingerprint"]: issues.append("approval belongs to a stale compiler revision or stage graph")
    if row.get("scope_fingerprint") != context["scope_fingerprint"] or row.get("approved_anchor_fingerprint") != context["binding"].get("approved_anchor_fingerprint"): issues.append("approval scope or approved anchor is stale")
    try:
        scoped = task_scope.freshness(root, workflow_id)
        missing = any("does not exist" in str(item) for item in scoped.get("issues", []))
        if not missing and (not scoped.get("valid") or not scoped.get("fresh")): issues.append("approved operational task scope is stale")
    except ValueError as error:
        if "does not exist" not in str(error): issues.append("operational task scope cannot be validated")
    if row.get("policy_fingerprint") != context["policy_fingerprint"]: issues.append("approval is stale for the policy/guardrail hash")
    if row.get("source") in {"session", "policy"} and not set(row.get("action_classes", [])) <= LOW_RISK: issues.append("over-broad session/policy approval")
    if row.get("expired_at") or (_time(row.get("expires_at")) and _time(row.get("expires_at")) <= _now()): issues.append("approval is expired")
    if row.get("decision") != "approved": issues.append(f"approval decision is {row.get('decision')}")
    return issues


def show(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); ledger = _load(root, workflow_id); context = _context(root, workflow_id)
    effective = [{"approval_id": row.get("approval_id"), "effective": not _issues(root, workflow_id, row, context), "issues": _issues(root, workflow_id, row, context)} for row in ledger["approvals"]]
    return {"artifact": path(root, workflow_id).relative_to(root).as_posix() if path(root, workflow_id).is_file() else None, **ledger, "status": "recorded" if ledger["approvals"] else "none", "effective_status": effective}


def validate(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); issues: list[str] = []
    try:
        ledger = _load(root, workflow_id); issues.extend(contracts.validate_artifact(ledger)); context = _context(root, workflow_id)
        for row in ledger["approvals"]:
            issues.extend(f"{row.get('approval_id', 'unknown')}: {item}" for item in _integrity_issues(workflow_id, row, context))
    except (OSError, ValueError, json.JSONDecodeError) as error: issues.append(str(error))
    return {"type": "tailtrail-workflow-stage-approval-validation", "workflow_id": workflow_id, "valid": not issues, "status": "valid" if not issues else "blocked", "issues": issues, "boundary": "Read-only authority validation; no decision is inferred and no stage is dispatched."}


def authorize_stage(root: Path, workflow_id: str, stage_id: str, approval_id: str | None, *, skip: bool = False) -> dict[str, Any] | None:
    context = _context(root.resolve(), workflow_id); stage = next((row for row in context["plan"]["stages"] if row["stage_id"] == stage_id), None)
    if not stage: raise ValueError("guarded transition references an unknown compiler stage")
    guarded = stage.get("approval_class") != "none" or skip
    if not guarded: return None
    if not approval_id: raise ValueError("transition-rejected reason_code=blocked-missing-authority approval_id=required")
    ledger = _load(root.resolve(), workflow_id); matches = [row for row in ledger["approvals"] if row.get("approval_id") == approval_id]
    if len(matches) != 1: raise ValueError("transition-rejected reason_code=blocked-missing-authority approval_id=unknown-or-forged")
    record = matches[0]; issues = _issues(root.resolve(), workflow_id, record, context)
    canonical = {"read-only": "read_local", "tailtrail-state": "write_tailtrail_state"}
    required_class = stage.get("adapter_action_class") or canonical.get(str(stage.get("action_class")))
    if required_class and required_class not in record.get("action_classes", []): issues.append("approval does not cover the compiler stage action class")
    if stage_id not in record.get("stage_ids", []): issues.append("approval does not cover this stage")
    if record.get("operation_kind") == "initial-plan": issues.append("initial Planning Lock approval cannot substitute for stage approval")
    if skip and record.get("operation_kind") != "skip": issues.append("stage skip requires an explicit skip approval")
    if not skip and record.get("operation_kind") == "skip": issues.append("skip approval cannot start a stage")
    if issues: raise ValueError("transition-rejected reason_code=blocked-missing-authority " + "; ".join(issues))
    return record
