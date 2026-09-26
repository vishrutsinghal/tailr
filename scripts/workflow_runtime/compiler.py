"""DWR-1.5 deterministic compiler for a declared workflow capability plan."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from workflow_runtime import adapter_catalog, capabilities, contracts, ownership, templates


LEDGER = ownership.LEDGER
CONFLICTS = ({"aidlc-off", "aidlc-standard"}, {"aidlc-off", "aidlc-full"}, {"aidlc-standard", "aidlc-full"})

FINGERPRINT_SCHEME = "content-sha256-crlf-normalized-v1"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def plan_path(root: Path, workflow_id: str) -> Path:
    return ownership.binding_path(root.resolve(), workflow_id).parent / "compiler-plan-v1.json"


def policy_path(root: Path) -> Path:
    return root.resolve() / ".tailtrail" / "workflow-compiler-policy-v1.json"


def _registry() -> dict[str, dict[str, Any]]:
    payload = json.loads((ownership.ROOT / "tailtrail-registry.json").read_text(encoding="utf-8"))
    return {str(item["id"]): item for item in payload.get("features", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}


def _policy(root: Path) -> dict[str, Any]:
    path = policy_path(root)
    if not path.is_file(): return {"required_capabilities": [], "forbidden_capabilities": [], "stage_prerequisites": {}, "pre_approved_stages": []}
    value = json.loads(path.read_text(encoding="utf-8"))
    allowed = {"schema_version", "type", "required_capabilities", "forbidden_capabilities", "stage_prerequisites", "pre_approved_stages"}
    required_keys = allowed - {"pre_approved_stages"}
    if not isinstance(value, dict) or value.get("type") != "tailtrail-workflow-compiler-policy" or not required_keys <= set(value) or not set(value) <= allowed or value.get("schema_version") != "1":
        raise ValueError("workflow compiler policy is invalid")
    required = value.get("required_capabilities", []); forbidden = value.get("forbidden_capabilities", []); prerequisites = value.get("stage_prerequisites", {})
    preapproved = value.get("pre_approved_stages", [])
    if not all(isinstance(item, str) for item in required + forbidden + preapproved) or not isinstance(prerequisites, dict):
        raise ValueError("workflow compiler policy has invalid capability or prerequisite entries")
    return {"required_capabilities": sorted(set(required)), "forbidden_capabilities": sorted(set(forbidden)), "stage_prerequisites": prerequisites, "pre_approved_stages": sorted(set(preapproved))}


def _policy_guardrail_fingerprint(root: Path, policy: dict[str, Any]) -> str:
    inputs: list[dict[str, str]] = [{"ref": ".tailtrail/workflow-compiler-policy-v1.json", "value": _canonical(policy)}]
    for candidate in (root / "tailtrail-policy.md", root / "GUARDRAILS.md"):
        if candidate.is_file():
            inputs.append({"ref": candidate.relative_to(root).as_posix(), "value": candidate.read_text(encoding="utf-8")})
    return _hash(inputs)


def _repository_identity_fingerprint(root: Path, binding: dict[str, Any]) -> str:
    current = ownership.TARGET.identity(root)
    return _hash({"target_identity_fingerprint": binding["target_identity_fingerprint"], "git": current.get("git", {}), "branch": ownership.TARGET._git(root, "branch", "--show-current")})


def _current_branch(root: Path) -> str:
    try:
        return str(ownership.TARGET._git(root, "branch", "--show-current") or "").strip()
    except (OSError, ValueError):
        return ""


def _canonical_file_bytes(path: Path) -> bytes | None:
    """Read a file for content pinning, or None when unreadable/non-UTF-8.

    Canonical form (LF endings, single trailing newline) keeps fingerprints
    stable across platforms without touching user data.
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return ("\n".join(text.replace("\r\n", "\n").replace("\r", "\n").split("\n")) + "\n").encode("utf-8")


def _scope_file_hashes(root: Path, paths: list[str]) -> dict[str, dict[str, str]]:
    """Fingerprint approved scope file contents (content pinning, not pointers)."""
    root = root.resolve()
    pinned: dict[str, dict[str, str]] = {}
    for rel in sorted(dict.fromkeys(str(item).replace("\\", "/") for item in paths if str(item).strip())):
        data = _canonical_file_bytes(root / rel)
        if data is None:
            pinned[rel] = {"state": "missing-or-unreadable"}
        else:
            pinned[rel] = {"state": "present", "sha256": "sha256:" + hashlib.sha256(data).hexdigest()}
    return pinned


def approved_scope_paths(root: Path, workflow_id: str) -> list[str]:
    """Collect approved scope file paths from the run anchor requirements."""
    binding = ownership.show(root.resolve(), workflow_id)
    anchor_path = LEDGER.state_dir(root.resolve(), binding["tailtrail_run_id"]) / "anchors" / "approved-v1.json"
    try:
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return []
    paths: list[str] = []
    requirements = anchor.get("requirements", [])
    if isinstance(requirements, list):
        for row in requirements:
            if isinstance(row, dict):
                for path in row.get("likely_paths", []) or []:
                    if isinstance(path, str) and path.strip():
                        paths.append(path.replace("\\", "/"))
    return sorted(dict.fromkeys(paths))


def _validate_features(feature_ids: set[str], registry: dict[str, dict[str, Any]], policy: dict[str, Any]) -> None:
    for conflict in CONFLICTS:
        if conflict <= feature_ids: raise ValueError("contradictory workflow features: " + ", ".join(sorted(conflict)))
    unknown = sorted(feature_ids - set(registry))
    if unknown: raise ValueError("workflow compiler found unavailable feature IDs: " + ", ".join(unknown))
    unavailable = sorted(item for item in feature_ids if registry[item].get("status") != "implemented")
    if unavailable: raise ValueError("workflow compiler found disabled/unavailable features: " + ", ".join(unavailable))
    forbidden = sorted(feature_ids & set(policy["forbidden_capabilities"]))
    if forbidden: raise ValueError("workflow compiler policy forbids capabilities: " + ", ".join(forbidden))


def _stage(stage: dict[str, Any], registry: dict[str, dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    capability = str(stage["capability_id"]); feature = registry[capability]
    additions = policy["stage_prerequisites"].get(stage["stage_id"], [])
    if not isinstance(additions, list) or not all(isinstance(item, str) for item in additions):
        raise ValueError(f"workflow compiler policy prerequisites for `{stage['stage_id']}` are invalid")
    action_class = "read-only" if feature.get("read_only") is True else "tailtrail-state"
    control_kind = stage.get("control_kind")
    adapter = {"adapter_id": "runtime-approval-gate", "action_class": "write_tailtrail_state"} if control_kind == "approval-gate" else adapter_catalog.for_stage(str(stage["stage_id"]), capability)
    return {**stage, "prerequisites": sorted(set(stage.get("prerequisites", [])) | set(additions)),
            "approval_class": "stage-approval" if control_kind == "approval-gate" else ("canonical-approval" if feature.get("requires_approval") else "none"),
            "action_class": action_class, "adapter_id": adapter["adapter_id"], "adapter_action_class": adapter["action_class"],
            "execution_authority": "typed-adapter-executor"}


def _compile(binding: dict[str, Any], declared: list[str], registry: dict[str, dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    selected = set(declared) | set(policy["required_capabilities"])
    _validate_features(selected, registry, policy)
    template_id = templates.select_template(selected)
    stages = [_stage(stage, registry, policy) for stage in templates.TEMPLATES[template_id]]
    stages = templates.resolve_graph(templates.merge_stages(stages))
    resolved = selected | {str(stage["capability_id"]) for stage in stages}
    _validate_features(resolved, registry, policy)
    return {"template_id": template_id, "selected_capability_ids": sorted(resolved), "stages": stages}


def compile(root: Path, workflow_id: str) -> dict[str, Any]:
    """Freeze a non-executable compiler plan from valid DWR-A/DWR-B artifacts."""
    root = root.resolve(); binding = ownership.show(root, workflow_id); ownership_check = ownership.validate(root, workflow_id)
    if not ownership_check["valid"]: raise ValueError("DWR-1.5 requires valid DWR-A ownership: " + "; ".join(ownership_check["issues"]))
    declared_check = capabilities.validate(root, workflow_id)
    if not declared_check["valid"]: raise ValueError("DWR-1.5 requires valid DWR-B declaration: " + "; ".join(declared_check["issues"]))
    declared_plan = capabilities.show(root, workflow_id); registry = _registry(); policy = _policy(root)
    declared = [str(stage["capability_id"]) for stage in declared_plan["stages"]]
    compiled = _compile(binding, declared, registry, policy)
    stable = {"workflow_id": workflow_id, "tailtrail_run_id": binding["tailtrail_run_id"], "ownership_ref": binding["artifact"], "capability_plan_ref": declared_plan["artifact"], "capability_plan_fingerprint": declared_plan["plan_fingerprint"], "target_identity_fingerprint": binding["target_identity_fingerprint"], "repository_identity_fingerprint": _repository_identity_fingerprint(root, binding), "repository_branch": _current_branch(root), "scope_content": {"scheme": FINGERPRINT_SCHEME, "files": _scope_file_hashes(root, approved_scope_paths(root, workflow_id))}, "policy_fingerprint": _policy_guardrail_fingerprint(root, policy), **compiled}
    fingerprint = _hash(stable); destination = plan_path(root, workflow_id); revision = 1
    prior: dict[str, Any] | None = None
    if destination.is_file():
        prior = json.loads(destination.read_text(encoding="utf-8")); revision = int(prior.get("revision", 0)) + (prior.get("plan_fingerprint") != fingerprint)
        if prior.get("plan_fingerprint") == fingerprint: return {"artifact": destination.relative_to(root).as_posix(), **prior, "status": "unchanged"}
    payload = {"schema_version": "1", "type": "tailtrail-workflow-compiler-plan", "revision": revision, **stable, "plan_fingerprint": fingerprint,
               "compiler_trace": ["validate-plan", "resolve-features", "reject-conflicts", "select-template", "apply-policy", "resolve-graph", "merge-duplicates", "approval-classes", "attach-references", "freeze-hash", "approval-questions", "execution-boundary"],
               "approval_questions": ["Approve the compiled stage graph before any later runtime phase attaches it to execution."],
               "state": "compiled", "boundary": "DWR-1.5 compiles a deterministic non-executable graph only. It does not invoke source edits, tests, scanners, Git, providers, shell commands, recovery, or completion."}
    contracts.require_valid(payload)
    LEDGER.atomic_json(destination, payload)
    if prior is not None and prior.get("plan_fingerprint") != fingerprint:
        from workflow_runtime import approvals
        approvals.expire_session(root, workflow_id, None, "material-plan-revision")
    LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_compiler_plan_created", {"workflow_id": workflow_id, "artifact": destination.relative_to(root).as_posix(), "revision": revision, "plan_fingerprint": fingerprint, "template_id": compiled["template_id"]})
    return {"artifact": destination.relative_to(root).as_posix(), **payload, "status": "compiled"}


def show(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); path = plan_path(root, workflow_id)
    if not path.is_file(): raise ValueError(f"DWR-1.5 compiler plan does not exist for `{workflow_id}`")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "tailtrail-workflow-compiler-plan" or payload.get("workflow_id") != workflow_id:
        raise ValueError("DWR-1.5 compiler plan is invalid")
    return {"artifact": path.relative_to(root).as_posix(), **payload}


def scope_drift(root: Path, workflow_id: str) -> dict[str, Any]:
    """Compare live scope file contents against the frozen baseline (Stage 5+).

    Informational only: drift is reported for audit and closure adjudication,
    never as an execution gate. Unrelated files are ignored by construction.
    """
    root = root.resolve()
    plan = show(root, workflow_id)
    frozen = plan.get("scope_content", {}) if isinstance(plan.get("scope_content"), dict) else {}
    frozen_files = frozen.get("files", {}) if isinstance(frozen.get("files"), dict) else {}
    current = _scope_file_hashes(root, list(frozen_files))
    changed: list[dict[str, str]] = []
    for path in sorted(set(frozen_files) | set(current)):
        before = frozen_files.get(path, {})
        after = current.get(path, {})
        if not isinstance(before, dict) or not isinstance(after, dict):
            continue
        if before.get("sha256") != after.get("sha256") or before.get("state") != after.get("state"):
            changed.append({
                "path": path,
                "before": str(before.get("sha256") or before.get("state", "?")),
                "after": str(after.get("sha256") or after.get("state", "?")),
            })
    return {
        "type": "tailtrail-workflow-scope-drift",
        "workflow_id": workflow_id,
        "scheme": frozen.get("scheme", FINGERPRINT_SCHEME),
        "files_tracked": len(frozen_files),
        "changed": changed,
        "in_sync": not changed,
        "boundary": "Informational drift report. It blocks nothing; closure adjudicates scope changes against approvals.",
    }


def rebase(root: Path, workflow_id: str, confirmed: bool = False) -> dict[str, Any]:
    """Re-verify scope content and, on explicit confirmation, re-freeze the plan.

    Without confirmation this only reports the delta. With confirmation it
    re-freezes scope content plus the repository branch/identity in place
    (bumping revision and expiring session approvals) instead of recompiling
    from scratch. The in-place path deliberately bypasses the ownership and
    capability revalidation gates: those bind the unchanged Planning Lock and
    anchor, while exactly the drift being adopted is what trips them. Stages,
    features, and policy are preserved, so continuation re-approves the same
    graph against current state.
    """
    root = root.resolve()
    drift = scope_drift(root, workflow_id)
    if drift["in_sync"]:
        return {"state": "in-sync", **drift}
    if not confirmed:
        return {"state": "rebase-required", **drift,
                "next": "Review the delta, then re-run with explicit confirmation to re-freeze."}
    plan = show(root, workflow_id)
    binding = ownership.show(root, workflow_id)
    content = {"scheme": FINGERPRINT_SCHEME, "files": _scope_file_hashes(root, approved_scope_paths(root, workflow_id))}
    stable = {key: value for key, value in plan.items() if key not in {"artifact", "schema_version", "type", "revision", "plan_fingerprint", "compiler_trace", "approval_questions", "state", "boundary"}}
    stable["scope_content"] = content
    stable["repository_branch"] = _current_branch(root)
    stable["repository_identity_fingerprint"] = _repository_identity_fingerprint(root, binding)
    fingerprint = _hash(stable)
    payload = {key: value for key, value in plan.items() if key != "artifact"}
    payload.update({"scope_content": content, "repository_branch": stable["repository_branch"], "repository_identity_fingerprint": stable["repository_identity_fingerprint"],
                    "revision": int(plan.get("revision", 1)) + 1, "plan_fingerprint": fingerprint, "state": "compiled"})
    contracts.require_valid(payload)
    destination = plan_path(root, workflow_id)
    LEDGER.atomic_json(destination, payload)
    from workflow_runtime import approvals
    approvals.expire_session(root, workflow_id, None, "material-plan-rebase")
    LEDGER.append_event(root, binding["tailtrail_run_id"], "workflow_compiler_plan_rebased", {"workflow_id": workflow_id, "artifact": destination.relative_to(root).as_posix(), "revision": payload["revision"], "plan_fingerprint": fingerprint, "changed": drift["changed"]})
    return {"state": "rebased", **drift, "revision": payload["revision"],
            "plan_fingerprint": payload["plan_fingerprint"],
            "boundary": "Re-frozen at current state; session approvals expired and must be re-granted."}


def validate(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); issues: list[str] = []
    try:
        plan = show(root, workflow_id); registry = _registry(); policy = _policy(root)
        issues.extend(contracts.validate_artifact({key: value for key, value in plan.items() if key != "artifact"}))
        stable = {key: value for key, value in plan.items() if key not in {"artifact", "schema_version", "type", "revision", "plan_fingerprint", "compiler_trace", "approval_questions", "state", "boundary"}}
        if plan.get("plan_fingerprint") != _hash(stable): issues.append("compiler plan fingerprint differs from frozen graph")
        binding = ownership.show(root, workflow_id)
        if plan.get("policy_fingerprint") != _policy_guardrail_fingerprint(root, policy): issues.append("compiler plan policy fingerprint differs from the active policy/guardrails")
        frozen_branch = str(plan.get("repository_branch") or "")
        if frozen_branch and frozen_branch != _current_branch(root):
            issues.append(f"compiler plan branch switched from `{frozen_branch}`; rebase before continuing")
        _validate_features(set(plan.get("selected_capability_ids", [])), registry, policy)
        resolved = templates.resolve_graph(templates.merge_stages(plan.get("stages", [])))
        if resolved != plan.get("stages"): issues.append("compiler stage graph is not in deterministic resolved order")
        if len(plan.get("compiler_trace", [])) != 12: issues.append("compiler trace does not contain all twelve deterministic steps")
        if any(stage.get("execution_authority") != "typed-adapter-executor" for stage in plan.get("stages", [])): issues.append("compiler plan does not bind the Phase 5 typed adapter executor")
    except (OSError, ValueError, json.JSONDecodeError) as error: issues.append(str(error))
    return {"type": "tailtrail-workflow-compiler-validation", "workflow_id": workflow_id, "valid": not issues, "status": "valid" if not issues else "blocked", "issues": issues, "boundary": "Validation is read-only and does not compile, repair, execute, or approve a workflow."}
