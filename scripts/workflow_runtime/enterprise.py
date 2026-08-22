"""Phase 12 optional enterprise adapter governance, binding, and identity."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from workflow_runtime import compiler, contracts, ownership, release, storage

LEDGER = ownership.LEDGER
CONTROL_NAMES = {"operational_ownership", "threat_model", "tenancy", "retention", "backup", "disaster_recovery", "audit", "availability", "cost"}
POLICY_INPUT = {"policy_id", "adapter_id", "need", "evidence_refs", "controls", "tenants", "limits"}
TENANT_INPUT = {"tenant_id", "actor_ids", "repository_ids"}
LIMIT_INPUT = {"lease_seconds", "max_events_per_workflow", "max_backups", "retained_events"}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    data = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    return digest(path.read_bytes())


def directory(root: Path) -> Path:
    return root.resolve() / ".tailtrail" / "enterprise"


def _read_ref(root: Path, ref: str) -> tuple[Path, dict[str, Any]]:
    if not contracts.safe_relative(ref):
        raise ValueError("enterprise reference must be safe and repository-relative")
    path = (root.resolve() / ref).resolve()
    try: path.relative_to(root.resolve())
    except ValueError as error: raise ValueError("enterprise reference escapes the repository") from error
    if not path.is_file() or path.stat().st_size > contracts.MAX_ARTIFACT_BYTES:
        raise ValueError("enterprise reference is missing or oversized")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or contracts.privacy_issues(value):
        raise ValueError("enterprise reference must contain one privacy-safe JSON object")
    return path, value


def policy_path(root: Path, policy_id: str) -> Path:
    return directory(root) / "policies" / f"{policy_id}.json"


def binding_path(root: Path, workflow_id: str) -> Path:
    return directory(root) / "bindings" / f"{workflow_id}.json"


def _policy(root: Path, policy_id: str) -> dict[str, Any]:
    path = policy_path(root, policy_id)
    if not path.is_file(): raise ValueError(f"enterprise policy does not exist: {policy_id}")
    value = json.loads(path.read_text(encoding="utf-8")); contracts.require_valid(value)
    expected = digest({key: item for key, item in value.items() if key != "policy_fingerprint"})
    if value["policy_fingerprint"] != expected: raise ValueError("enterprise policy fingerprint is invalid")
    return value


def _binding(root: Path, workflow_id: str) -> dict[str, Any]:
    path = binding_path(root, workflow_id)
    if not path.is_file(): raise ValueError(f"enterprise binding does not exist: {workflow_id}")
    value = json.loads(path.read_text(encoding="utf-8")); contracts.require_valid(value)
    expected = digest({key: item for key, item in value.items() if key != "binding_fingerprint"})
    if value["binding_fingerprint"] != expected: raise ValueError("enterprise binding fingerprint is invalid")
    policy = _policy(root, Path(value["policy_ref"]).stem)
    owner_path = root.resolve() / value["canonical_ownership_ref"]
    if file_hash(policy_path(root, policy["policy_id"])) != value["policy_hash"] or not owner_path.is_file() or file_hash(owner_path) != value["canonical_ownership_hash"]:
        raise ValueError("enterprise binding is stale relative to policy or canonical ownership")
    return value


def record_policy(root: Path, policy_ref: str, approved: bool) -> dict[str, Any]:
    if approved is not True: raise ValueError("enterprise policy recording requires explicit approval")
    root = root.resolve(); _path, source = _read_ref(root, policy_ref)
    if set(source) != POLICY_INPUT: raise ValueError("enterprise policy fields do not match the closed contract")
    if source.get("need") not in {"long-running", "cross-repository", "both"}: raise ValueError("enterprise need is unsupported")
    controls = source.get("controls"); limits = source.get("limits"); tenants = source.get("tenants")
    if not isinstance(controls, dict) or set(controls) != CONTROL_NAMES or any(value is not True for value in controls.values()): raise ValueError("every enterprise operational control requires affirmative approval")
    if not isinstance(limits, dict) or set(limits) != LIMIT_INPUT: raise ValueError("enterprise limits do not match the closed contract")
    if not all(isinstance(limits[key], int) and not isinstance(limits[key], bool) for key in LIMIT_INPUT): raise ValueError("enterprise limits must be integers")
    if not 30 <= limits["lease_seconds"] <= 3600 or not 1 <= limits["max_backups"] <= 100 or not 1 <= limits["max_events_per_workflow"] <= 100000 or not 1 <= limits["retained_events"] <= limits["max_events_per_workflow"]: raise ValueError("enterprise limits are outside safe bounds")
    if not isinstance(tenants, list) or not tenants or len(tenants) > 50: raise ValueError("enterprise policy requires bounded tenants")
    ids = set()
    for tenant in tenants:
        if not isinstance(tenant, dict) or set(tenant) != TENANT_INPUT or not isinstance(tenant["actor_ids"], list) or not isinstance(tenant["repository_ids"], list) or not tenant["actor_ids"] or not tenant["repository_ids"]: raise ValueError("enterprise tenant entry is invalid")
        if tenant["tenant_id"] in ids or len(set(tenant["actor_ids"])) != len(tenant["actor_ids"]) or len(set(tenant["repository_ids"])) != len(tenant["repository_ids"]): raise ValueError("enterprise tenant identities must be unique")
        ids.add(tenant["tenant_id"])
    refs = source.get("evidence_refs")
    if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) for ref in refs): raise ValueError("enterprise need requires evidence references")
    for ref in refs: _read_ref(root, ref)
    payload = {"schema_version":"1", "type":"tailtrail-workflow-enterprise-policy", **source, "state":"approved", "policy_fingerprint":"", "boundary":"Approved enterprise entry controls only. This policy does not activate an adapter, contact a provider, upload data, or change canonical local runtime state."}
    payload["policy_fingerprint"] = digest({key: item for key, item in payload.items() if key != "policy_fingerprint"}); contracts.require_valid(payload)
    destination = policy_path(root, source["policy_id"])
    if destination.exists(): raise ValueError("enterprise policy is immutable; record a new policy ID")
    LEDGER.atomic_json(destination, payload)
    return {"artifact": destination.relative_to(root).as_posix(), **payload}


def entry(root: Path, policy_id: str) -> dict[str, Any]:
    root = root.resolve(); issues = []
    try: policy = _policy(root, policy_id)
    except (OSError, ValueError, json.JSONDecodeError):
        payload={"schema_version":"1","type":"tailtrail-workflow-enterprise-entry", "policy_id":policy_id, "status":"blocked", "local_default":True, "issues":["policy-invalid"], "boundary":"Read-only entry assessment; no adapter or provider action occurred."}; contracts.require_valid(payload); return payload
    gate = release.evaluate(root)
    if gate["status"] != "passed": issues.append("phase11-release-gate-blocked")
    if set(policy["controls"]) != CONTROL_NAMES or any(value is not True for value in policy["controls"].values()): issues.append("operational-controls-incomplete")
    payload={"schema_version":"1","type":"tailtrail-workflow-enterprise-entry", "policy_id":policy_id, "status":"eligible" if not issues else "blocked", "local_default":True, "need":policy["need"], "release_gate_fingerprint":gate["gate_fingerprint"], "issues":issues, "boundary":"Read-only entry assessment. Eligibility never activates distributed continuation and local mode remains default."}; contracts.require_valid(payload); return payload


def tenant(root: Path, binding: dict[str, Any]) -> dict[str, Any]:
    policy = _policy(root, Path(binding["policy_ref"]).stem)
    return next(row for row in policy["tenants"] if row["tenant_id"] == binding["tenant_id"])


def authorize(root: Path, workflow_id: str, tenant_id: str, actor_id: str) -> dict[str, Any]:
    binding = _binding(root, workflow_id)
    if binding["state"] != "active" or binding["tenant_id"] != tenant_id: raise ValueError("enterprise tenant boundary is invalid")
    row = tenant(root, binding)
    if actor_id not in row["actor_ids"] or binding["repository_id"] not in row["repository_ids"]: raise ValueError("enterprise actor or repository is not authorized for tenant")
    return binding


def activate(root: Path, workflow_id: str, policy_id: str, tenant_id: str, repository_id: str, actor_id: str, approved: bool) -> dict[str, Any]:
    if approved is not True: raise ValueError("enterprise activation requires explicit approval")
    root = root.resolve(); assessment = entry(root, policy_id)
    if assessment["status"] != "eligible": raise ValueError("enterprise entry criteria are blocked: " + ", ".join(assessment["issues"]))
    if binding_path(root, workflow_id).exists(): raise ValueError("enterprise workflow binding already exists")
    if not ownership.validate(root, workflow_id)["valid"] or not compiler.validate(root, workflow_id)["valid"] or not storage.validate(root, workflow_id)["valid"]: raise ValueError("enterprise activation requires valid canonical local ownership, compiler, and replay")
    policy = _policy(root, policy_id); row = next((item for item in policy["tenants"] if item["tenant_id"] == tenant_id), None)
    if not row or actor_id not in row["actor_ids"] or repository_id not in row["repository_ids"]: raise ValueError("enterprise activation actor, tenant, or repository is unauthorized")
    owner = ownership.show(root, workflow_id); owner_path = ownership.binding_path(root, workflow_id)
    payload = {"schema_version":"1", "type":"tailtrail-workflow-enterprise-binding", "workflow_id":workflow_id, "tailtrail_run_id":owner["tailtrail_run_id"], "tenant_id":tenant_id, "repository_id":repository_id, "adapter_id":policy["adapter_id"], "policy_ref":policy_path(root, policy_id).relative_to(root).as_posix(), "policy_hash":file_hash(policy_path(root, policy_id)), "canonical_ownership_ref":owner_path.relative_to(root).as_posix(), "canonical_ownership_hash":file_hash(owner_path), "continuation_mode":"local", "state":"active", "binding_fingerprint":"", "boundary":"Optional adapter binding only. Canonical local ownership, approvals, evidence, recovery, and completion remain authoritative; distributed continuation is not yet selected."}
    payload["binding_fingerprint"] = digest({key: item for key, item in payload.items() if key != "binding_fingerprint"}); contracts.require_valid(payload)
    destination = binding_path(root, workflow_id); LEDGER.atomic_json(destination, payload); LEDGER.append_event(root, owner["tailtrail_run_id"], "workflow_enterprise_adapter_activated", {"workflow_id":workflow_id, "artifact":destination.relative_to(root).as_posix(), "tenant_id":tenant_id, "adapter_id":policy["adapter_id"]})
    return {"artifact":destination.relative_to(root).as_posix(), **payload}


def show(root: Path, workflow_id: str) -> dict[str, Any]:
    return {"artifact":binding_path(root, workflow_id).relative_to(root.resolve()).as_posix(), **_binding(root.resolve(), workflow_id)}


def update_mode(root: Path, workflow_id: str, mode: str, state_value: str = "active") -> dict[str, Any]:
    value = _binding(root, workflow_id); value["continuation_mode"] = mode; value["state"] = state_value; value["binding_fingerprint"] = ""; value["binding_fingerprint"] = digest({key:item for key,item in value.items() if key != "binding_fingerprint"}); contracts.require_valid(value); LEDGER.atomic_json(binding_path(root, workflow_id), value); return value


def link(root: Path, parent_workflow_id: str, identity_ref: str, actor_id: str, approved: bool) -> dict[str, Any]:
    if approved is not True: raise ValueError("enterprise parent/child link requires explicit approval")
    root = root.resolve(); binding = _binding(root, parent_workflow_id); authorize(root, parent_workflow_id, binding["tenant_id"], actor_id); _path, child = _read_ref(root, identity_ref)
    required = {"child_workflow_id", "child_run_id", "child_repository_id", "tenant_id"}
    if set(child) != required or child["tenant_id"] != binding["tenant_id"] or child["child_repository_id"] not in tenant(root, binding)["repository_ids"]: raise ValueError("enterprise child identity is invalid or crosses tenant authority")
    payload = {"schema_version":"1", "type":"tailtrail-workflow-enterprise-link", "parent_workflow_id":parent_workflow_id, "parent_run_id":binding["tailtrail_run_id"], "parent_repository_id":binding["repository_id"], **child, "relationship":"parent-child", "authority":"read-only-reference", "link_fingerprint":"", "boundary":"Cross-repository identity link only. It grants no child or parent repository write, approval, execution, recovery, or completion authority."}
    payload["link_fingerprint"] = digest({key:item for key,item in payload.items() if key != "link_fingerprint"}); contracts.require_valid(payload)
    destination = directory(root)/"links"/f"{parent_workflow_id}-{child['child_workflow_id']}.json"; LEDGER.atomic_json(destination,payload); LEDGER.append_event(root,binding["tailtrail_run_id"],"workflow_enterprise_child_linked",{"workflow_id":parent_workflow_id,"artifact":destination.relative_to(root).as_posix()}); return {"artifact":destination.relative_to(root).as_posix(),**payload}
