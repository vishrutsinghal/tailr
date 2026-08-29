#!/usr/bin/env python3
"""Create, approve, inspect, and enforce a local TailTrail Planning Lock."""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def ledger() -> Any:
    spec = importlib.util.spec_from_file_location("planning_lock_ledger", ROOT / "scripts" / "run-ledger.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


L = ledger()


def _display_prose(value: Any) -> str:
    """Normalize host-escaped prose without mutating canonical artifacts."""
    text = re.sub(r"\\(?:r\\n|n|r)", " ", str(value))
    text = " ".join(text.split())
    return text.translate(str.maketrans({"\u2013": "-", "\u2014": "-", "\u2212": "-", "\ufffd": "-"}))


def target_workspace() -> Any:
    spec = importlib.util.spec_from_file_location("planning_lock_target_workspace", ROOT / "scripts" / "target_workspace.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def enterprise_target_policy() -> Any:
    spec = importlib.util.spec_from_file_location("planning_lock_enterprise_target_policy", ROOT / "scripts" / "enterprise-target-policy.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def spec_kit_bridge() -> Any:
    spec = importlib.util.spec_from_file_location("planning_lock_spec_kit_bridge", ROOT / "scripts" / "spec-kit-bridge.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def spec_kit_slices() -> Any:
    spec = importlib.util.spec_from_file_location("planning_lock_spec_kit_slices", ROOT / "scripts" / "spec-kit-slices.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def spec_kit_evidence() -> Any:
    spec = importlib.util.spec_from_file_location("planning_lock_spec_kit_evidence", ROOT / "scripts" / "spec-kit-evidence.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def workflow_start_integration() -> Any:
    scripts_root = str(ROOT / "scripts")
    if scripts_root not in sys.path:
        sys.path.insert(0, scripts_root)
    spec = importlib.util.spec_from_file_location("planning_lock_workflow_start_integration", ROOT / "scripts" / "workflow_runtime" / "start_integration.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def requirement_discovery() -> Any:
    spec = importlib.util.spec_from_file_location("planning_lock_requirement_discovery", ROOT / "scripts" / "requirement_discovery.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def lock_path(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "planning" / "lock-v1.json"


def start_report_path(root: Path, run_id: str) -> Path:
    """Return the immutable planning report that a later approval activates."""
    return L.state_dir(root, run_id) / "planning" / "start-report-v1.json"


def revision_state_path(root: Path, run_id: str) -> Path:
    """Return the active/pending revision pointer without replacing v1 evidence."""
    return L.state_dir(root, run_id) / "planning" / "plan-revision-state-v1.json"


def revision_state(root: Path, run_id: str) -> dict[str, Any]:
    """Read revision state while keeping pre-IP-3 Planning Locks compatible."""
    root = root.resolve()
    path = revision_state_path(root, run_id)
    if path.is_file():
        payload = read(path)
        if payload.get("type") != "tailtrail-plan-revision-state" or payload.get("run_id") != run_id:
            raise ValueError(f"plan revision state for run `{run_id}` is invalid")
        return payload
    return {
        "schema_version": "1",
        "type": "tailtrail-plan-revision-state",
        "run_id": run_id,
        "active_revision": 1,
        "active_report": start_report_path(root, run_id).relative_to(root).as_posix(),
        "pending_revision": None,
        "pending_artifact": None,
    }


def active_start_report_path(root: Path, run_id: str) -> Path:
    """Return the reviewed report selected by the current approved revision."""
    root = root.resolve()
    state = revision_state(root, run_id)
    value = Path(str(state.get("active_report", "")))
    if value.is_absolute() or ".." in value.parts:
        raise ValueError(f"plan revision state for run `{run_id}` has an unsafe active report path")
    path = (root / value).resolve()
    try:
        path.relative_to(L.state_dir(root, run_id).resolve())
    except ValueError as error:
        raise ValueError(f"plan revision state for run `{run_id}` has an out-of-run active report path") from error
    if not path.is_file():
        raise ValueError(f"active Start report for run `{run_id}` does not exist")
    return path


def active_start_report(root: Path, run_id: str) -> dict[str, Any]:
    return read(active_start_report_path(root, run_id))


def assert_no_pending_revision(root: Path, run_id: str) -> None:
    state = revision_state(root.resolve(), run_id)
    if state.get("pending_revision") is not None:
        raise ValueError(
            f"plan revision v{state['pending_revision']} is awaiting approval for run `{run_id}`; "
            "approve or supersede that exact revision before activation"
        )


def discussion_receipts_path(root: Path, run_id: str) -> Path:
    """Return the sanitized Interactive Plan Mode receipt log for one run."""
    return L.state_dir(root, run_id) / "planning" / "plan-conversations.jsonl"


def discussion_state_path(root: Path, run_id: str) -> Path:
    """Return the derived, non-authoritative discussion state for one run."""
    return L.state_dir(root, run_id) / "planning" / "discussion-state-v1.json"


def assert_discussion_allowed(root: Path, run_id: str) -> dict[str, Any]:
    """Keep planning discussion bounded to a pre-implementation run.

    The canonical lock remains awaiting approval. Discussion state is a
    separate projection so existing approval and activation paths stay stable.
    """
    payload = show(root.resolve(), run_id)
    if payload["status"] != "awaiting-approval":
        raise ValueError(
            "Interactive Plan Mode is available only while the Planning Lock is awaiting approval; "
            f"run `{run_id}` is `{payload['status']}`"
        )
    return payload


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def suggested_run_id(root: Path, goal: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    digest = hashlib.sha256(goal.encode("utf-8")).hexdigest()[:6]
    base = f"start-{stamp}-{digest}"
    candidate = base
    index = 2
    while L.state_dir(root, candidate).exists():
        candidate = f"{base}-{index}"
        index += 1
    return candidate


def create(root: Path, goal: str, run_id: str | None = None, reference_roots: list[str] | None = None, target_identity: dict[str, Any] | None = None, input_roles: dict[str, Any] | None = None, host_workspace: dict[str, Any] | None = None, enterprise_policy: dict[str, Any] | None = None) -> dict[str, Any]:
    root = root.resolve()
    selected_run_id = run_id or suggested_run_id(root, goal)
    if Path(selected_run_id).name != selected_run_id:
        raise ValueError("run_id must be a single local run identifier")
    L.init_run(root, selected_run_id, goal)
    payload = {
        "schema_version": "2",
        "type": "tailtrail-planning-lock",
        "run_id": selected_run_id,
        "goal": goal,
        "status": "awaiting-approval",
        "writes_allowed": False,
        "reference_roots": [{"path": value, "access": "read-only"} for value in (reference_roots or [])],
        "target_identity": target_identity or target_workspace().identity(root),
        "input_roles": input_roles or target_workspace().input_roles(root, reference_roots=reference_roots),
        "host_workspace": host_workspace,
        "enterprise_policy": enterprise_policy or {"status": "not-configured", "blocking": False},
        "approval": None,
        "boundary": "Planning Lock permits read-only planning artifacts only. Source edits, Git mutations, project commands, scanners, and managed patch application require a separate approval for this run.",
    }
    path = lock_path(root, selected_run_id)
    L.atomic_json(path, payload)
    role_check = target_workspace().validate_input_roles(payload["input_roles"], root)
    L.append_event(root, selected_run_id, "planning_lock_created", {"artifact": path.relative_to(L.state_dir(root, selected_run_id)).as_posix(), "writes_allowed": False, "reference_roots": payload["reference_roots"], "target_fingerprint": payload["target_identity"]["fingerprint"], "input_roles": {"read_only_inputs": role_check["read_only_inputs"]}})
    return {**payload, "artifact": path.relative_to(root).as_posix()}


def show(root: Path, run_id: str) -> dict[str, Any]:
    path = lock_path(root.resolve(), run_id)
    if not path.is_file():
        raise ValueError(f"planning lock for run `{run_id}` does not exist")
    return {**read(path), "artifact": path.relative_to(root.resolve()).as_posix()}


def save_start_report(root: Path, run_id: str, report: dict[str, Any]) -> dict[str, Any]:
    """Persist the exact Start proposal before the user can approve it.

    Approval must activate the plan the user reviewed, not a new Navigator
    decision calculated after repository state has changed.
    """
    root = root.resolve()
    show(root, run_id)
    path = start_report_path(root, run_id)
    if path.exists():
        raise ValueError(f"Start report for run `{run_id}` already exists")
    payload = {
        "schema_version": "1",
        "type": "tailtrail-start-report",
        "run_id": run_id,
        "goal": report.get("goal", ""),
        "report": report,
    }
    L.atomic_json(path, payload)
    state_path = revision_state_path(root, run_id)
    if not state_path.exists():
        L.atomic_json(state_path, {
            "schema_version": "1",
            "type": "tailtrail-plan-revision-state",
            "run_id": run_id,
            "active_revision": 1,
            "active_report": path.relative_to(root).as_posix(),
            "pending_revision": None,
            "pending_artifact": None,
        })
    L.append_event(root, run_id, "start_report_saved", {"artifact": path.relative_to(root).as_posix()})
    return {"artifact": path.relative_to(root).as_posix(), "run_id": run_id}


def enrich_start_report(root: Path, run_id: str, report: dict[str, Any]) -> dict[str, Any]:
    """Replace the pre-approval report only to attach deterministic planning artifacts."""
    root = root.resolve()
    current = show(root, run_id)
    if current["status"] != "awaiting-approval":
        raise ValueError("Start report can be enriched only before approval")
    state = revision_state(root, run_id)
    if state.get("active_revision") != 1 or state.get("pending_revision") is not None:
        raise ValueError("Start report cannot be enriched after a plan revision has been proposed")
    path = start_report_path(root, run_id)
    if not path.is_file():
        raise ValueError(f"Start report for run `{run_id}` does not exist")
    L.atomic_json(path, {"schema_version": "1", "type": "tailtrail-start-report", "run_id": run_id, "goal": report.get("goal", ""), "report": report})
    return {"artifact": path.relative_to(root).as_posix(), "run_id": run_id}


def approve(root: Path, run_id: str, approved: bool) -> dict[str, Any]:
    if approved is not True:
        raise ValueError("planning approval requires --approved")
    root = root.resolve()
    assert_no_pending_revision(root, run_id)
    path = lock_path(root, run_id)
    payload = show(root, run_id)
    if payload["status"] == "approved":
        return payload
    if payload["status"] != "awaiting-approval":
        raise ValueError(f"planning lock is not approvable from status `{payload['status']}`")
    payload["status"] = "approved"
    payload["writes_allowed"] = True
    payload["approval"] = {"kind": "explicit-command", "run_id": run_id}
    payload.pop("artifact", None)
    L.atomic_json(path, payload)
    L.append_event(root, run_id, "planning_lock_approved", {"artifact": path.relative_to(L.state_dir(root, run_id)).as_posix(), "writes_allowed": True})
    return show(root, run_id)


def _proposal_from_start_report(root: Path, run_id: str) -> dict[str, Any] | None:
    """Turn the saved Navigator proposal into the smallest durable anchor."""
    saved = active_start_report(root, run_id)
    report = saved.get("report", {})
    delivery = report.get("guided_delivery", {}) if isinstance(report, dict) else {}
    if delivery.get("mode") == "lean":
        return None
    plan = report.get("navigator", {}) if isinstance(report, dict) else {}
    matrix = plan.get("requirement_matrix", []) if isinstance(plan, dict) else []
    program = delivery.get("hands_free_program", {}) if isinstance(delivery, dict) else {}
    if isinstance(program, dict) and isinstance(program.get("feature_requirements"), list) and not plan.get("revision_requirement_matrix"):
        paths = [item.get("path") for item in plan.get("likely_impacted_files", []) if isinstance(item, dict) and item.get("path")]
        matrix = _hands_free_requirement_matrix(program["feature_requirements"], paths)
    if not isinstance(matrix, list) or not matrix:
        paths = [item.get("path") for item in plan.get("likely_impacted_files", []) if isinstance(item, dict) and item.get("path")]
        matrix = _goal_requirements(str(saved.get("goal", "")).strip(), paths)
    return {"goal": str(saved.get("goal", "")).strip(), "requirements": matrix}


def _hands_free_requirement_matrix(features: list[dict[str, Any]], paths: list[str]) -> list[dict[str, Any]]:
    """Persist the displayed hands-free feature boundary as independently provable rows.

    `likely_paths` remain navigator hints, not an allow-list. The deterministic
    contracts below tell later harnesses which evidence tier is needed for each
    requirement without inventing repository-specific implementation details.
    """
    tier_by_topic = (
        ("eligibility", ["unit", "integration"]),
        ("inventory", ["integration"]),
        ("refund", ["integration"]),
        ("notification", ["e2e"]),
        ("audit", ["integration"]),
        ("api contract", ["contract"]),
        ("focused unit", ["unit", "integration", "contract", "e2e"]),
    )
    rows: list[dict[str, Any]] = []
    for index, feature in enumerate(features, start=1):
        statement = str(feature.get("statement", "")).strip()
        if not statement:
            continue
        lowered = statement.lower()
        tiers = next((value for topic, value in tier_by_topic if topic in lowered), [])
        conditional = "rollout" in lowered or "infrastructure" in lowered
        rows.append({
            "display_id": str(feature.get("display_id") or f"REQ-{index:02d}"),
            "kind": "preserve" if "preserve" in lowered else "change",
            "statement": statement,
            "acceptance_criteria": ["The stated outcome is observable through its named local evidence."],
            "preserve_rules": ["Preserve behavior outside this approved feature boundary."],
            "likely_paths": list(dict.fromkeys(paths)),
            "evidence_plan": ["Run the requirement-linked computational evidence for the selected tier(s)."],
            "validation_contract": {"state": "conditional" if conditional else "required", "tiers": tiers or ["unit"]},
            "architecture_contract": {"required_paths": [], "protected_paths": [], "forbidden_imports": []},
            "behavior_contract": {"scenarios": []},
            "maintainability_contract": {"rules": []},
            "ui_contract": {},
        })
    return rows


def _goal_requirements(goal: str, paths: list[str]) -> list[dict[str, Any]]:
    """Create a reviewable minimum requirement boundary when Navigator has none."""
    return requirement_discovery().matrix(goal, paths)


def _anchor_module() -> Any:
    """Load the requirement-anchor implementation without importing a package."""
    spec = importlib.util.spec_from_file_location("planning_lock_anchor", ROOT / "scripts" / "change-intent-anchor.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _aidlc_requirements_module() -> Any:
    """Load the AIDLC Requirements-stage engine owned by the lifecycle layer."""
    spec = importlib.util.spec_from_file_location("planning_lock_aidlc_requirements", ROOT / "scripts" / "aidlc-requirements.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _question_orchestrator_module() -> Any:
    """Load the shared context/quality layer without changing AIDLC authority."""
    spec = importlib.util.spec_from_file_location("planning_lock_question_orchestrator", ROOT / "scripts" / "question-orchestrator.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _official_aidlc_bridge_module() -> Any:
    """Load the Phase B identity bridge without attaching an external engine."""
    spec = importlib.util.spec_from_file_location("planning_lock_official_aidlc_bridge", ROOT / "scripts" / "aidlc-official-bridge.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _official_aidlc_requirements_module() -> Any:
    """Load the Full-mode adapter; it is intentionally separate from local AIDLC."""
    spec = importlib.util.spec_from_file_location("planning_lock_official_aidlc_requirements", ROOT / "scripts" / "official-aidlc-requirements.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _official_aidlc_state_module() -> Any:
    """Load the canonical run-state projector used by Phase G consumers."""
    spec = importlib.util.spec_from_file_location("planning_lock_official_aidlc_state", ROOT / "scripts" / "official-aidlc-state.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _maintainability_harness_module() -> Any:
    """Load the deterministic baseline capture without creating a package dependency."""
    spec = importlib.util.spec_from_file_location("planning_lock_maintainability_harness", ROOT / "scripts" / "maintainability-harness.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _evidence_tiers_module() -> Any:
    spec = importlib.util.spec_from_file_location("planning_lock_evidence_tiers", ROOT / "scripts" / "evidence-tiers.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _planning_renderer_module(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _ensure_evidence_capability(path: Path, revision: dict[str, Any]) -> dict[str, Any]:
    capability = revision.get("evidence_capability")
    if not isinstance(capability, dict):
        capability = _evidence_tiers_module().compile_requirements(revision.get("requirements", []))
        revision["evidence_capability"] = capability
        L.atomic_json(path, revision)
    if capability.get("status") != "compatible":
        raise ValueError("AIDLC requirements cannot be approved until the evidence capability check passes")
    return capability


def _resolved_aidlc_plan(root: Path, run_id: str, revision: dict[str, Any]) -> dict[str, Any]:
    """Project the saved Navigator plan through resolved AIDLC decisions."""
    report = _saved_start_report(root, run_id)
    navigator = report.get("navigator", {}) or {}
    delivery = report.get("guided_delivery", {}) or {}
    impacted = [row for row in navigator.get("likely_impacted_files", []) if isinstance(row, dict)]
    validation: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for requirement in revision.get("requirements", []):
        for tier in (requirement.get("validation_contract", {}) or {}).get("tiers", []):
            candidates = [str(row.get("path")) for row in impacted if f"/tests/{tier}/" in f"/{str(row.get('path', '')).replace(chr(92), '/')}" or (tier == "behaviour" and "/tests/behavior/" in f"/{str(row.get('path', '')).replace(chr(92), '/')}")]
            if not candidates:
                candidates = [str(row.get("path")) for row in impacted if str(row.get("path", "")).replace("\\", "/").startswith("tests/")]
            candidate = candidates[0] if candidates else "approved evidence receipt"
            key = (str(tier), candidate)
            if key in seen:
                continue
            seen.add(key)
            if candidate.startswith("tests/"):
                path = Path(candidate)
                command = f"{report.get('command_prefix', 'python3')} -m unittest discover -s {path.parent.as_posix()} -p {path.name} -v"
            else:
                command = "Record a requirement-linked approved evidence receipt."
            validation.append({"tier": str(tier), "candidate": candidate, "command": command})
    return {
        "navigator_decision": {
            "workflow": list(navigator.get("recommended_workflow", [])),
            "task_types": list(navigator.get("task_types", [])),
            "risks": list(navigator.get("risk_indicators", [])),
        },
        "scope": impacted,
        "selected_features": [row for row in delivery.get("selected", []) if isinstance(row, dict)],
        "deferred_features": [row for row in delivery.get("activated_later", []) if isinstance(row, dict)],
        "guided_delivery": delivery,
        "architecture_plan": report.get("architecture_plan", {}),
        "behaviour_plan": report.get("behaviour_plan", {}),
        "maintainability_plan": report.get("maintainability_plan", {}),
        "ui_plan": report.get("ui_plan", {}),
        "validation": validation,
        "token_posture": report.get("token_posture", {}),
        "evidence_posture": {
            "code_intelligence": "local-only lite, v1, and v2; provider-backed V3 is not default",
            "exactness": "local estimate only; exact model/API usage requires linked provider telemetry",
        },
    }


def _saved_start_report(root: Path, run_id: str) -> dict[str, Any]:
    return active_start_report(root, run_id).get("report", {})


def _is_full_official_run(root: Path, run_id: str) -> bool:
    report = _saved_start_report(root, run_id)
    return isinstance(report, dict) and (report.get("aidlc_mode", {}) or {}).get("mode") == "full"


def _is_official_aidlc_run(root: Path, run_id: str) -> bool:
    report = _saved_start_report(root, run_id)
    return isinstance(report, dict) and (report.get("aidlc_mode", {}) or {}).get("mode") in {"standard", "full"}


def _prepare_question_context(root: Path, run_id: str, proposal: dict[str, Any], mode: str) -> dict[str, Any]:
    """Persist one shared input contract for Lite and official requirements."""
    context = _question_orchestrator_module().prepare_context(
        run_id,
        mode,
        proposal["goal"],
        proposal["requirements"],
        _saved_start_report(root, run_id),
    )
    planning = L.state_dir(root, run_id) / "planning"
    existing = sorted(
        planning.glob("question-context-v*.json"),
        key=lambda item: int(item.stem.rsplit("v", 1)[-1]),
    )
    if existing and read(existing[-1]) == context:
        return {**context, "artifact": existing[-1].relative_to(root).as_posix()}
    version = int(existing[-1].stem.rsplit("v", 1)[-1]) + 1 if existing else 1
    path = planning / f"question-context-v{version}.json"
    L.atomic_json(path, context)
    L.append_event(root, run_id, "question_context_prepared", {
        "artifact": path.relative_to(root).as_posix(),
        "aidlc_mode": mode,
        "question_authority": context["question_authority"],
        "known_fact_count": len(context["known_facts"]),
        "unknown_count": len(context["unknowns"]),
    })
    return {**context, "artifact": path.relative_to(root).as_posix()}


def _official_bridge(root: Path, run_id: str) -> dict[str, Any]:
    path = L.state_dir(root, run_id) / "aidlc-official" / "bridge-v1.json"
    if not path.is_file():
        raise ValueError("Official AIDLC Standard or Full run has no verified bridge artifact")
    return read(path)


def execution_handoff(root: Path, run_id: str, saved_report: dict[str, Any], anchor_artifact: str | None) -> dict[str, Any]:
    """Persist the execution and closure contract for every anchored Start run."""
    delivery = saved_report.get("guided_delivery", {}) if isinstance(saved_report, dict) else {}
    plan = saved_report.get("navigator", {}) if isinstance(saved_report, dict) else {}
    anchor_path = root / anchor_artifact if anchor_artifact else None
    approved_anchor = read(anchor_path) if anchor_path and anchor_path.is_file() else {}
    bridge = saved_report.get("official_aidlc_bridge") if isinstance(saved_report, dict) else None
    handoff = {
        "run_id": run_id,
        "state": "execution-ready",
        "anchor": anchor_artifact,
        "active_requirements": [{
            "requirement_uid": row["requirement_uid"],
            "display_id": row["display_id"],
            "statement": row["statement"],
            "likely_paths": row.get("likely_paths", []),
            "preserve_rules": row.get("preserve_rules", []),
            "validation_contract": row.get("validation_contract", {}),
            "architecture_contract": row.get("architecture_contract", {}),
            "behavior_contract": row.get("behavior_contract", {}),
            "maintainability_contract": row.get("maintainability_contract", {}),
            "ui_contract": row.get("ui_contract", {}),
        } for row in approved_anchor.get("requirements", [])],
        "workflow": delivery.get("stages", ["inspect approved scope", "implement", "validate", "review", "report completion"]),
        "selected_features": delivery.get("selected", []),
        "architecture_plan": saved_report.get("architecture_plan", {}),
        "behaviour_plan": saved_report.get("behaviour_plan", {}),
        "maintainability_plan": saved_report.get("maintainability_plan", {}),
        "ui_plan": saved_report.get("ui_plan", {}),
        "likely_paths": [row.get("path") for row in plan.get("likely_impacted_files", []) if isinstance(row, dict) and row.get("path")],
        "execution_boundary": "Implementation may begin only within this activated approved anchor. TailTrail remains responsible for scope, evidence, drift, recovery, and completion controls.",
        "official_aidlc": bridge if isinstance(bridge, dict) else {"mode": (saved_report.get("aidlc_mode", {}) or {}).get("mode", "lite"), "state": "not-attached"},
        "closure": {
            "required": bool(anchor_artifact),
            "command": f"tailtrail completion-report --root . --run-id {run_id}",
            "command_arguments": ["completion-report", "--root", ".", "--run-id", run_id],
            "response_rule": "Before the final assistant response, execute this command through the same resolved TailTrail CLI used for Start and return its stdout verbatim. Do not substitute a generic changes-made or validation summary.",
            "evidence_rule": "If checkpoints, review, gates, receipts, or selected harness assessments are missing, return the evidence-incomplete Completion Report; never invent a successful closure.",
            "input_contract": {
                "schema": "schemas/execution-receipt.schema.json",
                "phase": "1",
                "validate_command": "tailtrail closure validate --root . --input closure-input.json",
                "record_command": "tailtrail closure record --root . --input closure-input.json",
                "required_fields": ["changed_paths", "requirement_uids", "tier", "command_label", "command", "outcome", "environment", "asserted_behavior"],
                "boundary": "Validation is read-only. The approved recorder persists only supplied validated evidence; it never runs listed commands, edits source, commits, pushes, deploys, or finalizes completion.",
            },
            "selected_harnesses": [row.get("name") for row in delivery.get("selected", []) if isinstance(row, dict) and row.get("name")],
        },
    }
    selected_harnesses = handoff["closure"]["selected_harnesses"]
    if "Maintainability Harness" in selected_harnesses and anchor_artifact:
        baseline = _maintainability_harness_module().capture_baseline(root, run_id)
        handoff["maintainability_baseline"] = {
            "state": "captured" if baseline.get("complete") else "evidence-incomplete",
            "artifact": baseline.get("run_artifact"),
            "inspected_paths": baseline.get("snapshot", {}).get("inspected_paths", []),
            "boundary": baseline.get("boundary"),
        }
    return handoff


def _rejection_count(root: Path, run_id: str) -> int:
    events = L.read_events(L.state_dir(root, run_id) / "events.jsonl")
    return sum(event.get("event_type") == "proposal_rejected" for event in events)


def feedback_template(root: Path, run_id: str) -> dict[str, Any]:
    """Return the required per-requirement review form without reading source.

    This deliberately operates on the saved Start report and local run ledger
    only.  A rejected plan must not become permission to inspect the project.
    """
    root = root.resolve()
    current = show(root, run_id)
    if current["status"] != "awaiting-approval":
        raise ValueError(f"planning feedback is available only while run `{run_id}` is awaiting approval")
    proposal = _proposal_from_start_report(root, run_id)
    if proposal is None:
        proposal = {
            "goal": str(current.get("goal", "")).strip(),
            "requirements": _goal_requirements(str(current.get("goal", "")).strip(), []),
        }
    anchor = _anchor_module()
    normalized = anchor.normalize_draft(run_id, proposal, _rejection_count(root, run_id) + 1)
    prior_rejections = _rejection_count(root, run_id)
    return {
        "run_id": run_id,
        "state": "feedback-required",
        "source_boundary": "Read only the saved TailTrail Planning Lock and Start report; no project source, tests, scanners, Git, or implementation commands were run.",
        "rejection_number": prior_rejections + 1,
        "aidlc": "required" if prior_rejections >= 1 else "optional",
        "instructions": "Provide exactly one approve or reject decision for every requirement. Every rejected requirement must include a specific comment.",
        "requirements": [{
            "requirement_uid": row["requirement_uid"],
            "display_id": row["display_id"],
            "statement": row["statement"],
            "decision": "pending",
            "comment": "",
        } for row in normalized["requirements"]],
        "next": "Revise only rejected requirements after feedback. Preserve this run and its prior evidence; do not start a new planning run.",
    }


def record_feedback(root: Path, run_id: str, feedback_json: str) -> dict[str, Any]:
    """Persist complete review feedback for the existing Start proposal."""
    root = root.resolve()
    template = feedback_template(root, run_id)
    anchor = _anchor_module()
    directory = L.state_dir(root, run_id) / "anchors"
    if not list(directory.glob("draft-v*.json")):
        proposal = _proposal_from_start_report(root, run_id)
        if proposal is None:
            proposal = {
                "goal": str(show(root, run_id).get("goal", "")).strip(),
                "requirements": _goal_requirements(str(show(root, run_id).get("goal", "")).strip(), []),
            }
        proposal_path = L.state_dir(root, run_id) / "planning" / "anchor-proposal-v1.json"
        L.atomic_json(proposal_path, proposal)
        anchor.draft(root, run_id, proposal_path)
    result = anchor.feedback(root, run_id, feedback_json)
    payload = {
        "run_id": run_id,
        "state": "revision-required" if result["rejected_requirement_uids"] else "ready-for-approval",
        "source_boundary": template["source_boundary"],
        **result,
        "next": "Ask targeted questions or offer AIDLC Requirements mode before revising rejected requirements." if result["next_requirement_mode"] == "ask-targeted-questions-or-offer-aidlc" else ("Use AIDLC Requirements mode before another material proposal." if result["next_requirement_mode"] == "aidlc-requirements-required" else "The complete proposal may be approved with the existing run ID."),
    }
    saved = active_start_report(root, run_id).get("report", {})
    hands_free = bool((saved.get("guided_delivery", {}) if isinstance(saved, dict) else {}).get("hands_free_program"))
    if _is_official_aidlc_run(root, run_id) and result["rejected_requirement_uids"]:
        comments = " ".join(str(row.get("comment", "")) for row in result.get("feedback", [])).lower()
        route = "official-design" if any(word in comments for word in ("design", "architecture", "architectural", "boundary")) else "official-requirements"
        route_path = L.state_dir(root, run_id) / "aidlc-official" / "revisions" / "route-v1.json"
        L.atomic_json(route_path, {"schema_version": "1", "type": "tailtrail-official-aidlc-revision-route", "run_id": run_id, "route": route, "authority": "official-ai-dlc-pack", "reason": "user-rejected requirement boundary", "next": "Run the official design stage before a new anchor." if route == "official-design" else "Regather official requirements for the same run."})
        L.append_event(root, run_id, "official_aidlc_revision_routed", {"route": route, "artifact": route_path.relative_to(root).as_posix()})
        payload["state"] = "official-aidlc-refinement-required"
        payload["official_revision_route"] = route
        payload["aidlc_refinement"] = request_official_aidlc_requirements(root, run_id)
        payload["next"] = "Complete the official AI-DLC Design stage before a revised requirements boundary." if route == "official-design" else "Answer the official AI-DLC Requirements Analysis questions, then approve the revised boundary."
        return payload
    if hands_free and result["rejected_requirement_uids"]:
        payload["state"] = "aidlc-refinement-required"
        payload["aidlc_refinement"] = request_aidlc_requirements(root, run_id)
        payload["next"] = "Answer the expanded AIDLC refinement questions, then approve the revised boundary before implementation."
    return payload


def reject_all(root: Path, run_id: str, reason: str) -> dict[str, Any]:
    """Apply one explicit user reason to every requirement in the active proposal."""
    if not reason.strip():
        raise ValueError("reject-all requires a concrete --reason")
    template = feedback_template(root, run_id)
    feedback = [{"requirement_uid": row["requirement_uid"], "decision": "reject", "comment": reason.strip()} for row in template["requirements"]]
    return record_feedback(root, run_id, json.dumps(feedback))


def request_aidlc_requirements(root: Path, run_id: str, revision_context: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Start minimal AIDLC requirement gathering from saved planning evidence only."""
    root = root.resolve()
    if _is_official_aidlc_run(root, run_id):
        return request_official_aidlc_requirements(root, run_id, revision_context)
    template = feedback_template(root, run_id)
    proposal = _proposal_from_start_report(root, run_id)
    if proposal is None:
        proposal = {"goal": str(show(root, run_id).get("goal", "")).strip(), "requirements": _goal_requirements(str(show(root, run_id).get("goal", "")).strip(), [])}
    events = L.read_events(L.state_dir(root, run_id) / "events.jsonl")
    feedback = [row for event in events if event.get("event_type") == "proposal_rejected" for row in event.get("payload", {}).get("feedback", [])]
    context = revision_context or []
    feedback.extend({"comment": str(row.get("reason", "")).strip()} for row in context if str(row.get("reason", "")).strip())
    question_context = _prepare_question_context(root, run_id, proposal, "lite")
    stage = _aidlc_requirements_module().gather(proposal["goal"], proposal["requirements"], feedback, question_context)
    artifact = L.state_dir(root, run_id) / "planning" / "aidlc-requirements-v1.json"
    document = {
        "schema_version": "1",
        "type": "tailtrail-aidlc-requirements",
        "run_id": run_id,
        "goal": proposal["goal"],
        "stage": "requirements-gathering",
        "source_boundary": template["source_boundary"],
        "requirements": proposal["requirements"],
        "prior_feedback": feedback,
        "revision_context": context,
        "aidlc_stage": stage,
        "questions": stage["questions"],
        "question_context": question_context["artifact"],
        "question_quality": stage["question_quality"],
        "question_traceability": stage["question_traceability"],
        "question_revision": 1,
        "approval_gate": stage["stage_gate"],
    }
    L.atomic_json(artifact, document)
    payload = {"rejection_number": template["rejection_number"], "reason": "user-selected-aidlc-requirements", "artifact": artifact.relative_to(root).as_posix(), "revision_context_count": len(context)}
    L.append_event(root, run_id, "aidlc_requirements_requested", payload)
    return {"run_id": run_id, "state": "aidlc-requirements-gathering", "artifact": artifact.relative_to(root).as_posix(), "source_boundary": template["source_boundary"], "requirements": proposal["requirements"], "questions": stage["questions"], "question_context": question_context["artifact"], "question_quality": stage["question_quality"], "question_traceability": stage["question_traceability"], "aidlc_stage": stage, "prior_feedback": feedback, "revision_context": context, "approval_gate": document["approval_gate"]}


def request_official_aidlc_requirements(root: Path, run_id: str, revision_context: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Run the verified official Requirements Analysis stage for a Full run.

    This deliberately does not call ``aidlc-requirements.py``.  The only
    imported material is the reviewed requirement boundary, official rule
    references, and later the explicit official decisions.
    """
    root = root.resolve()
    if not _is_official_aidlc_run(root, run_id):
        raise ValueError("official requirements are available only for Standard or Full AIDLC runs")
    template = feedback_template(root, run_id)
    proposal = _proposal_from_start_report(root, run_id)
    if proposal is None:
        proposal = {"goal": str(show(root, run_id).get("goal", "")).strip(), "requirements": _goal_requirements(str(show(root, run_id).get("goal", "")).strip(), [])}
    events = L.read_events(L.state_dir(root, run_id) / "events.jsonl")
    feedback = [row for event in events if event.get("event_type") == "proposal_rejected" for row in event.get("payload", {}).get("feedback", [])]
    context = revision_context or []
    feedback.extend({"comment": str(row.get("reason", "")).strip()} for row in context if str(row.get("reason", "")).strip())
    saved = _saved_start_report(root, run_id)
    mode = str((saved.get("aidlc_mode", {}) or {}).get("mode", "standard"))
    question_context = _prepare_question_context(root, run_id, proposal, mode)
    stage = _official_aidlc_requirements_module().stage_request(root, _official_bridge(root, run_id), proposal["goal"], proposal["requirements"], feedback, question_context)
    artifact = L.state_dir(root, run_id) / "planning" / "official-aidlc-requirements-v1.json"
    document = {
        "schema_version": "1", "type": "tailtrail-official-aidlc-requirements", "run_id": run_id,
        "goal": proposal["goal"], "stage": "requirements-gathering", "source_boundary": template["source_boundary"],
        "requirements": proposal["requirements"], "prior_feedback": feedback, "revision_context": context, "official_stage": stage,
        "questions": [], "question_revision": 1, "approval_gate": stage["stage_gate"],
        "official_questions": None, "question_context": question_context["artifact"], "question_quality": None, "question_traceability": [],
    }
    L.atomic_json(artifact, document)
    L.append_event(root, run_id, "official_aidlc_requirements_requested", {"artifact": artifact.relative_to(root).as_posix(), "official_references": stage["official_references"], "host_action_required": True})
    return _official_requirements_payload(root, run_id, document, artifact)


def _official_requirements_payload(root: Path, run_id: str, document: dict[str, Any], artifact: Path) -> dict[str, Any]:
    stage = document["official_stage"]
    pending = not document.get("questions")
    return {"run_id": run_id, "state": "official-aidlc-host-generation-required" if pending else "official-aidlc-requirements-gathering", "authority": "official-ai-dlc-pack", "artifact": artifact.relative_to(root).as_posix(), "official_questions": document["official_questions"], "source_boundary": document["source_boundary"], "requirements": document["requirements"], "questions": document["questions"], "question_context": document.get("question_context"), "question_quality": document.get("question_quality"), "question_traceability": document.get("question_traceability", []), "aidlc_stage": stage, "prior_feedback": document.get("prior_feedback", []), "revision_context": document.get("revision_context", []), "approval_gate": document["approval_gate"], "host_action": stage.get("host_action") if pending else None}


def record_official_aidlc_questions(root: Path, run_id: str, questions_json: str) -> dict[str, Any]:
    """Persist questions generated by a host that loaded the pinned official rules."""
    root = root.resolve()
    if not _is_official_aidlc_run(root, run_id):
        raise ValueError("official host questions require Standard or Full AIDLC")
    artifact = _official_aidlc_artifact(root, run_id, "official-aidlc-requirements-v1.json")
    document = read(artifact)
    normalized = _official_aidlc_requirements_module().validate_host_questions(json.loads(questions_json))
    context_path = root / str(document.get("question_context", ""))
    if not context_path.is_file():
        raise ValueError("official AIDLC question context is unavailable")
    question_context = read(context_path)
    evaluated = _question_orchestrator_module().evaluate_questions(normalized, question_context, "official-ai-dlc-pack")
    questions = evaluated["questions"]
    document["questions"] = questions
    document["question_quality"] = evaluated["quality"]
    document["question_traceability"] = evaluated["traceability"]
    document["official_questions"] = (L.state_dir(root, run_id) / "aidlc-official" / "requirements" / "questions-v1.json").relative_to(root).as_posix()
    questions_path = root / document["official_questions"]
    questions_path.parent.mkdir(parents=True, exist_ok=True)
    L.atomic_json(questions_path, {"type": "official-ai-dlc-host-questions", "run_id": run_id, "official_references": document["official_stage"]["official_references"], "question_context": document["question_context"], "quality": evaluated["quality"], "traceability": evaluated["traceability"], "questions": questions})
    L.atomic_json(artifact, document)
    L.append_event(root, run_id, "official_aidlc_host_questions_recorded", {"artifact": document["official_questions"], "question_ids": [item["id"] for item in questions]})
    L.append_event(root, run_id, "question_quality_validated", {"artifact": document["official_questions"], "status": evaluated["quality"]["status"], "question_count": len(questions), "authority": "official-ai-dlc-pack"})
    return _official_requirements_payload(root, run_id, document, artifact)


def _official_aidlc_artifact(root: Path, run_id: str, name: str) -> Path:
    path = L.state_dir(root, run_id) / "planning" / name
    if not path.is_file():
        raise ValueError(f"Official AIDLC Requirements artifact for run `{run_id}` does not exist; select or start Standard or Full AIDLC mode first")
    return path


def submit_official_aidlc_answers(root: Path, run_id: str, answers_json: str) -> dict[str, Any]:
    root = root.resolve()
    if show(root, run_id)["status"] != "awaiting-approval":
        raise ValueError(f"official AIDLC answers are available only while run `{run_id}` is awaiting approval")
    document = read(_official_aidlc_artifact(root, run_id, "official-aidlc-requirements-v1.json"))
    if not document.get("questions"):
        raise ValueError("The configured host must first record official Requirements Analysis questions with `official-aidlc-questions`; TailTrail will not substitute a local questionnaire.")
    stage = {**document["official_stage"], "requirements": document["requirements"], "questions": document["questions"]}
    revision = _official_aidlc_requirements_module().revise(stage, json.loads(answers_json))
    evidence_capability = _evidence_tiers_module().compile_requirements(revision["requirements"])
    revision_path = L.state_dir(root, run_id) / "planning" / "official-aidlc-revised-requirements-v1.json"
    payload = {"schema_version": "1", "type": "tailtrail-official-aidlc-revised-requirements", "run_id": run_id, "source_boundary": document["source_boundary"], "question_revision": document.get("question_revision", 1), "official_references": document["official_stage"]["official_references"], "evidence_capability": evidence_capability, "resolved_plan": _resolved_aidlc_plan(root, run_id, revision), **revision}
    L.atomic_json(revision_path, payload)
    L.append_event(root, run_id, "official_aidlc_requirements_answered", {"artifact": revision_path.relative_to(root).as_posix(), "question_ids": sorted(revision["official_decisions"]), "status": "official-revision-ready"})
    return {"state": "official-aidlc-revision-ready", "artifact": revision_path.relative_to(root).as_posix(), **payload}


def show_official_aidlc_requirements(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    artifact = _official_aidlc_artifact(root, run_id, "official-aidlc-requirements-v1.json")
    return _official_requirements_payload(root, run_id, read(artifact), artifact)


def approve_official_aidlc_requirements(root: Path, run_id: str, approved: bool) -> dict[str, Any]:
    """Map one official stage approval to an immutable TailTrail anchor."""
    if approved is not True:
        raise ValueError("official AIDLC requirements approval requires --approved")
    root = root.resolve()
    if show(root, run_id)["status"] != "awaiting-approval":
        raise ValueError(f"official AIDLC requirements cannot activate run `{run_id}` from its current state")
    revision_path = _official_aidlc_artifact(root, run_id, "official-aidlc-revised-requirements-v1.json")
    revision = read(revision_path)
    _ensure_evidence_capability(revision_path, revision)
    questions = read(_official_aidlc_artifact(root, run_id, "official-aidlc-requirements-v1.json"))
    if revision.get("question_revision", 1) != questions.get("question_revision", 1):
        raise ValueError("official AIDLC answers are stale because a question revision was approved; answer the current question set again")
    gate_path = L.state_dir(root, run_id) / "aidlc-official" / "requirements" / "approval-v1.json"
    gate = {"schema_version": "1", "type": "tailtrail-official-aidlc-stage-approval", "run_id": run_id, "stage": "requirements", "authority": "official-ai-dlc-pack", "approved": True, "official_references": revision["official_references"], "official_decisions": revision["official_decisions"], "boundary": "This explicit official Requirements Analysis approval is the only approval that freezes the TailTrail anchor for this run."}
    L.atomic_json(gate_path, gate)
    anchor = _anchor_module()
    anchor.draft(root, run_id, revision_path)
    anchor.approve(root, run_id)
    lock = approve(root, run_id, True)
    saved = _saved_start_report(root, run_id)
    anchor_artifact = (L.state_dir(root, run_id) / "anchors" / "approved-v1.json").relative_to(root).as_posix()
    workflow_runtime = workflow_start_integration().activate(root, run_id, saved, anchor_artifact)
    handoff = execution_handoff(root, run_id, saved, anchor_artifact)
    handoff["workflow_runtime"] = workflow_runtime
    handoff["execution_authority"] = workflow_runtime.get("execution_authority", {})
    handoff["execution_boundary"] = "Implementation may begin only within the anchor frozen after official AIDLC Requirements Analysis approval."
    handoff_path = L.state_dir(root, run_id) / "planning" / "execution-handoff-v1.json"
    L.atomic_json(handoff_path, handoff)
    bridge_activation = _official_aidlc_bridge_module().activate(root, run_id)
    canonical_state = _official_aidlc_state_module().assert_consistent(root, run_id)
    L.append_event(root, run_id, "official_aidlc_requirements_approved", {"revision": revision_path.relative_to(root).as_posix(), "official_approval": gate_path.relative_to(root).as_posix(), "anchor": anchor_artifact, "handoff": handoff_path.relative_to(root).as_posix()})
    L.append_event(root, run_id, "planning_activated", {"anchor": {"status": "created-from-official-aidlc", "artifact": anchor_artifact}, "official_aidlc_bridge_activation": bridge_activation["artifact"], "workflow_runtime": workflow_runtime.get("state")})
    return {"planning_lock": lock, **handoff, "official_stage_approval": gate_path.relative_to(root).as_posix(), "official_aidlc_bridge_activation": bridge_activation, "canonical_state": {"status": canonical_state["status"], "valid": canonical_state["valid"], "issues": canonical_state["issues"]}, "artifact": handoff_path.relative_to(root).as_posix()}


def _aidlc_artifact(root: Path, run_id: str, name: str) -> Path:
    path = L.state_dir(root, run_id) / "planning" / name
    if not path.is_file():
        raise ValueError(f"AIDLC requirements artifact for run `{run_id}` does not exist; select AIDLC Requirements mode first")
    return path


def submit_aidlc_answers(root: Path, run_id: str, answers_json: str) -> dict[str, Any]:
    """Validate AIDLC answers and persist a revised, still-unapproved boundary."""
    root = root.resolve()
    if _is_official_aidlc_run(root, run_id):
        return submit_official_aidlc_answers(root, run_id, answers_json)
    current = show(root, run_id)
    if current["status"] != "awaiting-approval":
        raise ValueError(f"AIDLC answers are available only while run `{run_id}` is awaiting approval")
    stage_document = read(_aidlc_artifact(root, run_id, "aidlc-requirements-v1.json"))
    answers = json.loads(answers_json)
    engine = _aidlc_requirements_module()
    revision = engine.revise(stage_document, answers)
    evidence_capability = _evidence_tiers_module().compile_requirements(revision["requirements"])
    revision_path = L.state_dir(root, run_id) / "planning" / "aidlc-revised-requirements-v1.json"
    payload = {"schema_version": "1", "type": "tailtrail-aidlc-revised-requirements", "run_id": run_id, "source_boundary": stage_document["source_boundary"], "question_revision": stage_document.get("question_revision", 1), "evidence_capability": evidence_capability, "resolved_plan": _resolved_aidlc_plan(root, run_id, revision), **revision}
    L.atomic_json(revision_path, payload)
    L.append_event(root, run_id, "aidlc_requirements_answered", {"artifact": revision_path.relative_to(root).as_posix(), "question_ids": sorted(revision["aidlc_answers"]), "status": "revision-ready"})
    return {"state": "aidlc-revision-ready", "artifact": revision_path.relative_to(root).as_posix(), **payload}


def show_aidlc_requirements(root: Path, run_id: str) -> dict[str, Any]:
    """Resume an existing AIDLC requirements brief without creating another event."""
    root = root.resolve()
    if _is_official_aidlc_run(root, run_id):
        return show_official_aidlc_requirements(root, run_id)
    document = read(_aidlc_artifact(root, run_id, "aidlc-requirements-v1.json"))
    return {
        "run_id": run_id,
        "state": "aidlc-requirements-gathering",
        "artifact": _aidlc_artifact(root, run_id, "aidlc-requirements-v1.json").relative_to(root).as_posix(),
        "source_boundary": document["source_boundary"],
        "requirements": document["requirements"],
        "questions": document["questions"],
        "aidlc_stage": document["aidlc_stage"],
        "prior_feedback": document.get("prior_feedback", []),
        "revision_context": document.get("revision_context", []),
        "approval_gate": document["approval_gate"],
    }


def aidlc_cycle(root: Path, run_id: str, answers_json: str | None = None, approved: bool = False) -> dict[str, Any]:
    """Run exactly one safe AIDLC control-plane transition for an active run.

    It deliberately batches only metadata operations.  Material activation still
    requires the explicit ``--approved`` flag and remains a separate user gate.
    """
    if approved and answers_json is not None:
        raise ValueError("aidlc-cycle accepts either --answers or --approved, not both")
    if approved:
        return {"cycle_action": "activate-approved-boundary", **approve_aidlc_requirements(root, run_id, True)}
    if answers_json is not None:
        return {"cycle_action": "record-answers-and-render-revision", **submit_aidlc_answers(root, run_id, answers_json)}
    artifact_name = "official-aidlc-requirements-v1.json" if _is_official_aidlc_run(root.resolve(), run_id) else "aidlc-requirements-v1.json"
    artifact = L.state_dir(root.resolve(), run_id) / "planning" / artifact_name
    if artifact.exists():
        return {"cycle_action": "resume-requirements-gathering", **show_aidlc_requirements(root, run_id)}
    return {"cycle_action": "start-requirements-gathering", **request_aidlc_requirements(root, run_id)}


def approve_aidlc_requirements(root: Path, run_id: str, approved: bool) -> dict[str, Any]:
    """Create the immutable TailTrail anchor and activate the existing run."""
    if approved is not True:
        raise ValueError("AIDLC requirements approval requires --approved")
    root = root.resolve()
    if _is_official_aidlc_run(root, run_id):
        return approve_official_aidlc_requirements(root, run_id, approved)
    current = show(root, run_id)
    if current["status"] != "awaiting-approval":
        raise ValueError(f"AIDLC requirements cannot activate run `{run_id}` from status `{current['status']}`")
    revision_path = _aidlc_artifact(root, run_id, "aidlc-revised-requirements-v1.json")
    revision = read(revision_path)
    _ensure_evidence_capability(revision_path, revision)
    questions = read(_aidlc_artifact(root, run_id, "aidlc-requirements-v1.json"))
    if revision.get("question_revision", 1) != questions.get("question_revision", 1):
        raise ValueError("AIDLC answers are stale because a question revision was approved; answer the current question set again")
    anchor = _anchor_module()
    anchor.draft(root, run_id, revision_path)
    anchor.approve(root, run_id)
    lock = approve(root, run_id, True)
    saved = active_start_report(root, run_id).get("report", {})
    anchor_artifact = (L.state_dir(root, run_id) / "anchors" / "approved-v1.json").relative_to(root).as_posix()
    workflow_runtime = workflow_start_integration().activate(root, run_id, saved, anchor_artifact)
    handoff = execution_handoff(root, run_id, saved, anchor_artifact)
    handoff["workflow_runtime"] = workflow_runtime
    handoff["execution_authority"] = workflow_runtime.get("execution_authority", {})
    handoff["execution_boundary"] = "Implementation may begin only within the activated AIDLC-approved anchor. TailTrail remains responsible for scope, evidence, drift, recovery, and completion controls."
    handoff_path = L.state_dir(root, run_id) / "planning" / "execution-handoff-v1.json"
    L.atomic_json(handoff_path, handoff)
    L.append_event(root, run_id, "aidlc_requirements_approved", {"revision": revision_path.relative_to(root).as_posix(), "anchor": handoff["anchor"], "handoff": handoff_path.relative_to(root).as_posix()})
    L.append_event(root, run_id, "planning_activated", {"anchor": {"status": "created-from-aidlc", "artifact": handoff["anchor"]}, "workflow_runtime": workflow_runtime.get("state")})
    return {"planning_lock": lock, **handoff, "artifact": handoff_path.relative_to(root).as_posix()}


def render_aidlc_requirements(payload: dict[str, Any]) -> str:
    """Render the actionable AIDLC handoff for a chat host."""
    official = payload.get("authority") == "official-ai-dlc-pack"
    lines = [
        "# TailTrail AIDLC Requirements",
        "",
        f"**Run ID:** `{payload['run_id']}`",
        "**Stage:** requirements gathering - planning only; no source inspection or implementation has run.",
        "",
        "## Current requirement boundary",
        "",
        "| ID | Proposed requirement |",
        "| --- | --- |",
    ]
    for index, row in enumerate(payload["requirements"], start=1):
        lines.append(f"| {row.get('display_id', f'REQ-{index:02d}')} | {_display_prose(row.get('statement', ''))} |")
    if official:
        lines[0] = "# TailTrail Official AI-DLC Requirements"
        lines[3] = "**Stage:** official Requirements Analysis; planning only, with no source inspection or implementation."
        lines.extend(["", "## Official rule references", ""])
        lines.extend(f"- `{path}`" for path in payload["aidlc_stage"]["official_references"].values())
    if official and not payload["questions"]:
        lines.extend(["", "## Question Orchestrator", "", f"- Context: `{payload.get('question_context')}`.", "- Authority: official AI-DLC Requirements Analysis; TailTrail validates grounding and traceability but does not generate a substitute questionnaire.", "", "## Official host action required", "", "- Read the listed pinned official rules and the saved Question Orchestrator context.", "- Generate only material unresolved decisions. Each question needs meaningful options including Other, requirement IDs, decision class and impact, known context, evidence references, a TailTrail advisory recommendation, and evidence-grounded reasoning.", "- Repository-specific claims require explicit saved evidence; inventory hypotheses must remain labelled as hypotheses.", "- Record exhaustive questionnaires with `tailtrail planning official-aidlc-questions --root . --run-id <run-id> --questions-stdin`; use `--questions-base64` for smaller Windows-safe payloads or `--questions '<json>'` where quoting is safe.", "- The recommendation is TailTrail advisory guidance; the user may select any official option or Other with detail.", "- No source inspection, implementation, tests, scanners, or Git actions are permitted while gathering requirements.", ""])
        return "\n".join(lines)
    quality = payload.get("question_quality") or {}
    lines.extend(["", "## Question Orchestrator", "", f"- Context: `{payload.get('question_context')}`.", f"- Authority: `{quality.get('authority', 'unknown')}`.", f"- Quality gate: `{quality.get('status', 'unavailable')}` for {quality.get('question_count', len(payload['questions']))} question(s).", "- Every question is mapped to requirement IDs and a material decision impact; repository hypotheses are not confirmed source facts."])
    lines.extend(["", "## Questions to resolve", ""])
    extension_heading_added = False
    for row in payload["questions"]:
        if row.get("decision_class") == "extension-opt-in" and not extension_heading_added:
            lines.extend(["## Optional official extensions", ""])
            extension_heading_added = True
        lines.extend([f"### {row['id']}", "", _display_prose(row["question"])])
        for option in row["options"]:
            lines.append(f"- **{option['id']}:** {_display_prose(option['text'])}")
        lines.extend([f"- **Recommended:** {_display_prose(row['recommended'])}", f"- **Reasoning:** {_display_prose(row['reasoning'])}", f"- **Affects:** {', '.join(row.get('requirement_ids', [])) or 'unmapped'}", f"- **Decision:** {row.get('decision_class', 'unclassified')} - {', '.join(row.get('decision_impact', [])) or 'impact unavailable'}", ""])
    lines.extend([
        "",
        "## Next response",
        "",
        (
            f"- Reply with one answer for every question, `{payload['questions'][0]['id']}` through "
            f"`{payload['questions'][-1]['id']}`. Choose one listed option for each question; use `Other` with details when needed."
        ),
        "- TailTrail will then present a revised requirement boundary for approval. It will not inspect source or implement work until that revised boundary is approved.",
        "",
    ])
    if official:
        lines[-2] = "- Official stage approval freezes the TailTrail anchor for this same run; it does not create a parallel TailTrail questionnaire."
    return "\n".join(lines)


def render_aidlc_revision(payload: dict[str, Any]) -> str:
    official = payload.get("authority") == "official-ai-dlc-pack"
    lines = ["# TailTrail AIDLC Revised Requirements", "", f"**Run ID:** `{payload['run_id']}`", "**State:** awaiting AIDLC approval - no source inspection or implementation has run.", "", "## Revised requirement boundary", "", "| ID | Requirement |", "| --- | --- |"]
    for row in payload["requirements"]:
        lines.append(f"| {row.get('display_id')} | {_display_prose(row.get('statement'))} |")
    lines.extend(["", "## Recorded AIDLC decisions", ""])
    if official:
        lines[0] = "# TailTrail Official AI-DLC Revised Requirements"
        lines[3] = "**State:** awaiting official Requirements Analysis approval; no source inspection or implementation has run."
    for question_id, answer in payload.get("official_decisions", payload.get("aidlc_answers", {})).items():
        lines.append(f"- **{question_id}:** {answer['selected']}")
    capability = payload.get("evidence_capability", {}) or {}
    lines.extend(["", "## Evidence capability check", "", f"- Status: `{capability.get('status', 'unavailable')}`."])
    for row in capability.get("requirements", []):
        lines.append(f"- **{row.get('requirement_id')}:** {', '.join(row.get('tiers', [])) or 'no required tier'} - `{row.get('status')}`")
    resolved = payload.get("resolved_plan", {}) or {}
    decision = resolved.get("navigator_decision", {}) or {}
    lines.extend([
        "", "## Navigator Decision", "",
        "- Workflow: " + " -> ".join(decision.get("workflow", [])),
        "- Task types: " + (", ".join(decision.get("task_types", [])) or "not classified"),
        "- Risks: " + (", ".join(decision.get("risks", [])) or "none detected"),
        "", "## Scope", "", "| Path | Planning evidence |", "| --- | --- |",
    ])
    for row in resolved.get("scope", []):
        lines.append(f"| `{row.get('path')}` | {_display_prose(row.get('reason', ''))} |")
    lines.extend(["", "## Selected TailTrail features", "", "| Feature | When | Why |", "| --- | --- | --- |", "| Navigator | Planning resolved | reconciled the saved plan with approved AIDLC decisions |"])
    for row in resolved.get("selected_features", []):
        lines.append(f"| {row.get('name')} | After approval | {_display_prose(row.get('why', ''))} |")
    architecture = _planning_renderer_module("planning_lock_architecture_render", "architecture_planning.py")
    behaviour = _planning_renderer_module("planning_lock_behaviour_render", "behaviour_planning.py")
    maintainability = _planning_renderer_module("planning_lock_maintainability_render", "maintainability_planning.py")
    ui = _planning_renderer_module("planning_lock_ui_render", "ui_planning.py")
    lines.extend(architecture.markdown_lines(resolved.get("architecture_plan", {}), detailed=True))
    lines.extend(behaviour.markdown_lines(resolved.get("behaviour_plan", {}), detailed=True))
    lines.extend(maintainability.markdown_lines(resolved.get("maintainability_plan", {}), detailed=True))
    lines.extend(ui.markdown_lines(resolved.get("ui_plan", {}), detailed=True))
    lines.extend(["", "## Deferred TailTrail features", ""])
    for row in resolved.get("deferred_features", []):
        lines.append(f"- **{row.get('name')}:** {_display_prose(row.get('when', ''))}")
    delivery = resolved.get("guided_delivery", {}) or {}
    lines.extend(["", "## Guided Delivery", "", f"- Mode: `{delivery.get('mode', 'guided-delivery')}`", "- After approval:"])
    for index, stage in enumerate(delivery.get("stages", []), start=1):
        lines.append(f"  {index}. {stage}")
    if delivery.get("execution_boundary"):
        lines.append(f"- Boundary: {delivery.get('execution_boundary')}")
    lines.extend(["", "## Validation", "", "| Tier | Candidate | Command |", "| --- | --- | --- |"])
    for row in resolved.get("validation", []):
        lines.append(f"| {row.get('tier')} | `{row.get('candidate')}` | `{row.get('command')}` |")
    token = resolved.get("token_posture", {}) or {}
    lines.extend([
        "", "## Token estimate", "",
        f"- Estimated focused context: approximately `{token.get('used_tokens', 0)}` tokens.",
        f"- Estimated baseline context: approximately `{token.get('baseline_tokens', 0)}` tokens.",
        f"- Estimated avoided context: approximately `{token.get('avoided_tokens', 0)}` tokens (`{token.get('estimated_reduction_percent', 0)}%` reduction).",
        "- Actual model tokens remain unavailable without linked host/provider telemetry.",
        "", "## Evidence posture", "",
        f"- Code intelligence: {resolved.get('evidence_posture', {}).get('code_intelligence', 'unavailable')}.",
        f"- Exactness: {resolved.get('evidence_posture', {}).get('exactness', 'unavailable')}.",
    ])
    lines.extend(["", "## Approval", "", "- Approve this AIDLC boundary to create the immutable TailTrail anchor and activate this same run for scoped implementation.", ""])
    if official:
        lines[-2] = "- Approve this official Requirements Analysis boundary to freeze the immutable TailTrail anchor and activate this same run."
    return "\n".join(lines)


def render_execution_handoff(payload: dict[str, Any]) -> str:
    lines = ["# TailTrail Execution Handoff", "", f"**Run ID:** `{payload['run_id']}`", "**State:** execution ready - AIDLC requirements are approved and the existing Planning Lock is activated.", "", "## Active requirements", ""]
    for row in payload["active_requirements"]:
        lines.append(f"- **{row['display_id']}:** {_display_prose(row['statement'])}")
    lines.extend(["", "## Selected TailTrail controls", ""])
    for row in payload.get("selected_features", []):
        lines.append(f"- **{row.get('name')}:** {row.get('why')}")
    runtime = payload.get("workflow_runtime")
    if isinstance(runtime, dict):
        lines.extend(["", "## Workflow runtime", ""])
        if runtime.get("state") == "compiled":
            lines.append(f"- Workflow: `{runtime.get('workflow_id')}`; compiler template: `{runtime.get('compiler', {}).get('template_id')}`.")
            lines.append("- State: compiled and non-executing. Runtime adapters consume only the authority recorded below.")
        else:
            lines.append(f"- State: `{runtime.get('state')}` - {_display_prose(runtime.get('reason', 'no runtime action was taken'))}.")
    authority = payload.get("execution_authority")
    if isinstance(authority, dict):
        lines.extend(["", "## Execution authority", "", f"- Route: `{authority.get('route')}`; status: `{authority.get('status')}`."])
        granted = ", ".join(authority.get("auto_granted_action_classes", [])) or "none"
        lines.append(f"- Automatically granted action classes: `{granted}`.")
        lines.append(f"- Separate gates remain for: {', '.join(authority.get('separate_gate_triggers', [])) or 'none recorded'}.")
        lines.append(f"- {authority.get('boundary')}")
    lines.extend(["", "## Execution boundary", "", f"- {payload['execution_boundary']}", "- Next: inspect only the approved paths, implement the smallest compliant change, and run the selected evidence.", ""])
    baseline = payload.get("maintainability_baseline")
    if isinstance(baseline, dict):
        lines.extend([
            "## Maintainability baseline",
            "",
            f"- State: `{baseline.get('state')}`; artifact: `{baseline.get('artifact')}`.",
            f"- Inspected approved production candidates: {len(baseline.get('inspected_paths', []))}.",
            f"- {baseline.get('boundary')}",
            "",
        ])
    closure = payload.get("closure", {})
    if closure.get("required"):
        lines.extend([
            "## Mandatory closure",
            "",
            f"- Run: `{closure['command']}`",
            f"- {closure['response_rule']}",
            f"- {closure['evidence_rule']}",
            "",
        ])
    return "\n".join(lines)


def render_feedback_template(payload: dict[str, Any]) -> str:
    """Render a small host-facing form instead of exposing implementation JSON."""
    lines = [
        "# TailTrail Plan Feedback",
        "",
        f"**Run ID:** `{payload['run_id']}`",
        "**State:** feedback required - no project source, tests, scanners, Git, or implementation commands were run.",
        "",
        "## Review each requirement",
        "",
        "| ID | Requirement | Decision | Feedback if rejected |",
        "| --- | --- | --- | --- |",
    ]
    for row in payload["requirements"]:
        lines.append(f"| {row['display_id']} | {row['statement']} | approve / reject | required for reject |")
    lines.extend([
        "",
        "## Revision path",
        "",
        "Choose one path; TailTrail does not write feedback on your behalf:",
        "",
        "1. **Review individually:** reply with `REQ-01: approve` or `REQ-01: reject - <reason>` for every row.",
        "2. **Reject all:** reply `Reject all - <one concrete reason>`.",
        "3. **Use AIDLC now:** reply `Use AIDLC Requirements mode`.",
        "",
        "- Individual review needs a decision for every row. Rejected rows need a concrete comment.",
        "- Keep this run ID; TailTrail revises only rejected requirements and preserves prior planning evidence.",
        "- " + ("AIDLC Requirements mode is required before another material proposal." if payload["aidlc"] == "required" else "This is the first material rejection: TailTrail can ask targeted questions or use AIDLC Requirements mode."),
        "",
    ])
    return "\n".join(lines)


def activate(root: Path, run_id: str, approved: bool) -> dict[str, Any]:
    """Approve a saved Start report and create its required immutable anchor.

    Lean tasks retain the lightweight Planning Lock only. Guided-delivery and
    hands-free tasks receive the canonical requirement anchor before managed
    execution starts.
    """
    if approved is not True:
        raise ValueError("planning activation requires --approved")
    root = root.resolve()
    assert_no_pending_revision(root, run_id)
    current = show(root, run_id)
    identity_check = target_workspace().verify_identity(current.get("target_identity", {}), root)
    if identity_check["blocking"]:
        raise ValueError(f"Target identity mismatch for run `{run_id}`: {identity_check['reason']}. Refresh or recreate the Planning Lock before implementation.")
    role_check = target_workspace().validate_input_roles(current.get("input_roles", {}), root)
    policy_check = enterprise_target_policy().verify_bound(current.get("enterprise_policy"), root)
    if policy_check.get("blocking"):
        raise ValueError(f"Enterprise target policy blocks activation for run `{run_id}`: {policy_check.get('reason', '; '.join(policy_check.get('issues', [])))}")
    saved_report = active_start_report(root, run_id).get("report", {})
    source = saved_report.get("spec_kit_source") if isinstance(saved_report, dict) else None
    if isinstance(source, dict):
        current_source = spec_kit_bridge().load(root, str(source.get("feature_id", "")))
        if current_source.get("source_revision") != source.get("source_revision") or current_source.get("import") != source.get("import"):
            raise ValueError("Intent Bridge source/import identity changed after this plan; create an amendment review before activation")
    if _is_official_aidlc_run(root, run_id):
        revision = L.state_dir(root, run_id) / "planning" / "official-aidlc-revised-requirements-v1.json"
        if not revision.is_file():
            raise ValueError("Full AIDLC requires answers and explicit official Requirements Analysis approval before TailTrail can freeze the anchor")
        return approve_official_aidlc_requirements(root, run_id, True)
    hands_free = bool((saved_report.get("guided_delivery", {}) if isinstance(saved_report, dict) else {}).get("hands_free_program"))
    stage_path = L.state_dir(root, run_id) / "planning" / "aidlc-requirements-v1.json"
    revision_path = L.state_dir(root, run_id) / "planning" / "aidlc-revised-requirements-v1.json"
    if hands_free and stage_path.is_file():
        if not revision_path.is_file():
            stage_document = read(stage_path)
            stage = stage_document["aidlc_stage"]
            answers = []
            for question in stage.get("questions", []):
                recommendation = str(question.get("recommended", "")).lower()
                options = [item for item in question.get("options", []) if item.get("id") != "Other"]
                choice = max(options, key=lambda item: len(set(str(item.get("text", "")).lower().split()) & set(recommendation.split())), default=None)
                if choice is None:
                    raise ValueError("AIDLC recommendation could not be mapped to an approved option; revise the requirement plan instead")
                answers.append({"question_id": question["id"], "choice": choice["id"]})
            revision = _aidlc_requirements_module().revise(stage_document, answers)
            L.atomic_json(revision_path, {"schema_version": "1", "type": "tailtrail-aidlc-revised-requirements", "run_id": run_id, "source_boundary": stage_document["source_boundary"], **revision})
            L.append_event(root, run_id, "aidlc_recommendations_accepted", {"revision": revision_path.relative_to(root).as_posix(), "question_ids": [item["question_id"] for item in answers]})
        return approve_aidlc_requirements(root, run_id, True)
    proposal = _proposal_from_start_report(root, run_id)
    anchor_result: dict[str, Any] | None = None
    if proposal is not None:
        approved_path = L.state_dir(root, run_id) / "anchors" / "approved-v1.json"
        if approved_path.is_file():
            anchor_result = {"status": "existing", "artifact": approved_path.relative_to(root).as_posix()}
        else:
            module = _anchor_module()
            proposal_path = L.state_dir(root, run_id) / "planning" / "anchor-proposal-v1.json"
            L.atomic_json(proposal_path, proposal)
            module.draft(root, run_id, proposal_path)
            created = module.approve(root, run_id)
            anchor_result = {"status": "created", "artifact": Path(created["path"]).relative_to(root).as_posix(), "requirements": [row["requirement_uid"] for row in created["requirements"]]}
    spec_kit_slice_result: dict[str, Any] | None = None
    spec_kit_evidence_result: dict[str, Any] | None = None
    if anchor_result and isinstance(source, dict):
        spec_kit_slice_result = spec_kit_slices().initialize(root, run_id)
        spec_kit_evidence_result = spec_kit_evidence().plan(root, run_id)
    lock = current if current["status"] == "approved" else approve(root, run_id, True)
    anchor_state = anchor_result or {"status": "not-required", "reason": "lean Start runs do not create canonical requirement state"}
    workflow_runtime = workflow_start_integration().activate(root, run_id, saved_report, str(anchor_result["artifact"]) if anchor_result and anchor_result.get("artifact") else None)
    handoff: dict[str, Any] | None = None
    handoff_artifact: str | None = None
    if anchor_result and anchor_result.get("artifact"):
        handoff = execution_handoff(root, run_id, saved_report, str(anchor_result["artifact"]))
        handoff["workflow_runtime"] = workflow_runtime
        handoff["execution_authority"] = workflow_runtime.get("execution_authority", {
            "route": "legacy-no-runtime-authority", "status": "host-boundary-applies",
            "auto_granted_action_classes": [], "separate_gate_triggers": ["all-managed-execution"],
            "boundary": "This legacy or disabled workflow has no durable runtime authority artifact; the host approval boundary still applies.",
        })
        if spec_kit_slice_result:
            handoff["spec_kit_slice"] = {
                "active_slice": spec_kit_slice_result["active_slice"],
                "guard_command": f"tailtrail spec-kit slices assert-active --root . --run-id {run_id} --requirement-uid <approved-requirement-uid>",
                "boundary": "Only the active Spec Kit slice may execute; advance after verified completion with explicit approval.",
            }
        handoff_path = L.state_dir(root, run_id) / "planning" / "execution-handoff-v1.json"
        L.atomic_json(handoff_path, handoff)
        handoff_artifact = handoff_path.relative_to(root).as_posix()
    bridge_activation: dict[str, Any] | None = None
    bridge = saved_report.get("official_aidlc_bridge") if isinstance(saved_report, dict) else None
    if isinstance(bridge, dict) and bridge.get("mode") == "full":
        bridge_activation = _official_aidlc_bridge_module().activate(root, run_id)
    L.append_event(root, run_id, "planning_activated", {
        "anchor": anchor_state,
        "handoff": "planning/execution-handoff-v1.json" if handoff else None,
        "official_aidlc_bridge_activation": bridge_activation.get("artifact") if bridge_activation else None,
        "target_identity_status": identity_check["status"],
        "input_role_status": role_check["status"],
        "enterprise_policy_status": policy_check["status"],
        "workflow_runtime": workflow_runtime.get("state"),
    })
    return {
        "planning_lock": lock,
        "anchor": anchor_state,
        "execution_handoff": handoff,
        "execution_handoff_artifact": handoff_artifact,
        "official_aidlc_bridge_activation": bridge_activation,
        "spec_kit_slices": spec_kit_slice_result,
        "spec_kit_evidence": spec_kit_evidence_result,
        "target_identity": identity_check,
        "input_roles": role_check,
        "enterprise_policy": policy_check,
        "workflow_runtime": workflow_runtime,
    }


def assert_write_allowed(root: Path, run_id: str) -> dict[str, Any]:
    payload = show(root, run_id)
    if payload.get("status") != "approved" or payload.get("writes_allowed") is not True:
        raise ValueError(f"Planning Lock for run `{run_id}` is `{payload.get('status')}`; explicit approval is required before managed source changes")
    identity_check = target_workspace().verify_identity(payload.get("target_identity", {}), root.resolve())
    if identity_check["blocking"]:
        raise ValueError(f"Target identity mismatch for run `{run_id}`: {identity_check['reason']}. Managed source changes are blocked.")
    payload["target_identity_check"] = identity_check
    payload["input_roles_check"] = target_workspace().validate_input_roles(payload.get("input_roles", {}), root.resolve())
    payload["enterprise_policy_check"] = enterprise_target_policy().verify_bound(payload.get("enterprise_policy"), root.resolve())
    if payload["enterprise_policy_check"].get("blocking"):
        raise ValueError(f"Enterprise target policy blocks managed source changes for run `{run_id}`: {payload['enterprise_policy_check'].get('reason', '; '.join(payload['enterprise_policy_check'].get('issues', [])))}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start", help="Create a planning-only lock and local run.")
    start.add_argument("--root", type=Path, default=Path.cwd())
    start.add_argument("--goal", required=True)
    start.add_argument("--run-id")
    start.add_argument("--reference-root", action="append", default=[])
    start.add_argument("--related-repo", action="append", default=[])
    start.add_argument("--design-reference", action="append", default=[])
    start.add_argument("--requirement-artifact", action="append", default=[])
    start.add_argument("--evidence-artifact", action="append", default=[])
    approve_parser = sub.add_parser("approve", help="Explicitly allow managed writes for one planning run.")
    approve_parser.add_argument("--root", type=Path, default=Path.cwd())
    approve_parser.add_argument("--run-id", required=True)
    approve_parser.add_argument("--approved", action="store_true")
    activate_parser = sub.add_parser("activate", help="Approve the saved Start report and create its required requirement anchor.")
    activate_parser.add_argument("--root", type=Path, default=Path.cwd())
    activate_parser.add_argument("--run-id", required=True)
    activate_parser.add_argument("--approved", action="store_true")
    activate_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    feedback_template_parser = sub.add_parser("feedback-template", help="Show mandatory requirement-by-requirement feedback for a rejected Start plan.")
    feedback_template_parser.add_argument("--root", type=Path, default=Path.cwd())
    feedback_template_parser.add_argument("--run-id", required=True)
    feedback_template_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    feedback_parser = sub.add_parser("feedback", help="Record complete requirement-by-requirement feedback for an awaiting Start plan.")
    feedback_parser.add_argument("--root", type=Path, default=Path.cwd())
    feedback_parser.add_argument("--run-id", required=True)
    feedback_parser.add_argument("--feedback", required=True, help="JSON list with every requirement_uid, decision, and rejection comment.")
    reject_all_parser = sub.add_parser("reject-all", help="Reject every requirement in an awaiting Start plan with one explicit reason.")
    reject_all_parser.add_argument("--root", type=Path, default=Path.cwd())
    reject_all_parser.add_argument("--run-id", required=True)
    reject_all_parser.add_argument("--reason", required=True)
    aidlc_parser = sub.add_parser("aidlc-requirements", help="Start planning-only AIDLC requirement gathering for an awaiting Start plan.")
    aidlc_parser.add_argument("--root", type=Path, default=Path.cwd())
    aidlc_parser.add_argument("--run-id", required=True)
    aidlc_answer_parser = sub.add_parser("aidlc-answer", help="Record complete AIDLC Requirements-stage answers and render a revised boundary.")
    aidlc_answer_parser.add_argument("--root", type=Path, default=Path.cwd())
    aidlc_answer_parser.add_argument("--run-id", required=True)
    aidlc_answer_parser.add_argument("--answers", required=True, help="JSON list of question_id, choice, and optional detail.")
    aidlc_approve_parser = sub.add_parser("aidlc-approve", help="Approve revised AIDLC requirements and activate the existing Planning Lock.")
    aidlc_approve_parser.add_argument("--root", type=Path, default=Path.cwd())
    aidlc_approve_parser.add_argument("--run-id", required=True)
    aidlc_approve_parser.add_argument("--approved", action="store_true")
    official_questions_parser = sub.add_parser("official-aidlc-questions", help="Record questions generated by the host from the pinned official AI-DLC rules.")
    official_questions_parser.add_argument("--root", type=Path, default=Path.cwd())
    official_questions_parser.add_argument("--run-id", required=True)
    official_question_source = official_questions_parser.add_mutually_exclusive_group(required=True)
    official_question_source.add_argument("--questions", help="JSON list of official host-generated questions, options, recommendations, and reasoning.")
    official_question_source.add_argument("--questions-base64", help="UTF-8 question JSON encoded as Base64; use on Windows hosts where native argument quoting strips JSON quotes.")
    official_question_source.add_argument("--questions-stdin", action="store_true", help="Read one complete UTF-8 JSON line from standard input; preferred for exhaustive questionnaires that exceed Windows command-line limits.")
    aidlc_cycle_parser = sub.add_parser("aidlc-cycle", help="Run one safe AIDLC Requirements control-plane transition for an existing run.")
    aidlc_cycle_parser.add_argument("--root", type=Path, default=Path.cwd())
    aidlc_cycle_parser.add_argument("--run-id", required=True)
    answer_source = aidlc_cycle_parser.add_mutually_exclusive_group()
    answer_source.add_argument("--answers", help="JSON list of complete question_id, choice, and optional detail answers.")
    answer_source.add_argument("--answers-base64", help="UTF-8 JSON answers encoded as Base64; use on Windows hosts where native argument quoting strips JSON quotes.")
    aidlc_cycle_parser.add_argument("--approved", action="store_true", help="Activate an already revised AIDLC boundary.")
    for name in ("show", "assert-write"):
        item = sub.add_parser(name)
        item.add_argument("--root", type=Path, default=Path.cwd())
        item.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        if args.command == "start":
            roles = target_workspace().input_roles(args.root, reference_roots=args.reference_root, related_repos=args.related_repo, design_references=args.design_reference, requirement_artifacts=args.requirement_artifact, evidence_artifacts=args.evidence_artifact)
            payload = create(args.root, args.goal, args.run_id, args.reference_root, input_roles=roles)
        elif args.command == "approve":
            payload = approve(args.root, args.run_id, args.approved)
        elif args.command == "activate":
            payload = activate(args.root, args.run_id, args.approved)
        elif args.command == "feedback-template":
            payload = feedback_template(args.root, args.run_id)
        elif args.command == "feedback":
            payload = record_feedback(args.root, args.run_id, args.feedback)
        elif args.command == "reject-all":
            payload = reject_all(args.root, args.run_id, args.reason)
        elif args.command == "aidlc-requirements":
            payload = request_aidlc_requirements(args.root, args.run_id)
        elif args.command == "aidlc-answer":
            payload = submit_aidlc_answers(args.root, args.run_id, args.answers)
        elif args.command == "aidlc-approve":
            payload = approve_aidlc_requirements(args.root, args.run_id, args.approved)
        elif args.command == "official-aidlc-questions":
            questions_json = args.questions
            if args.questions_base64 is not None:
                try:
                    questions_json = base64.b64decode(args.questions_base64, validate=True).decode("utf-8")
                except (ValueError, UnicodeDecodeError) as error:
                    raise ValueError(f"--questions-base64 must be valid Base64-encoded UTF-8 JSON: {error}") from error
            elif args.questions_stdin:
                questions_json = sys.stdin.readline()
                if not questions_json.strip():
                    raise ValueError("--questions-stdin requires a non-empty UTF-8 JSON document on standard input")
            payload = record_official_aidlc_questions(args.root, args.run_id, questions_json)
        elif args.command == "aidlc-cycle":
            answers_json = args.answers
            if args.answers_base64 is not None:
                try:
                    answers_json = base64.b64decode(args.answers_base64, validate=True).decode("utf-8")
                except (ValueError, UnicodeDecodeError) as error:
                    raise ValueError(f"--answers-base64 must be valid Base64-encoded UTF-8 JSON: {error}") from error
            payload = aidlc_cycle(args.root, args.run_id, answers_json, args.approved)
        elif args.command == "show":
            payload = show(args.root, args.run_id)
        else:
            payload = assert_write_allowed(args.root, args.run_id)
        if args.command == "feedback-template" and args.format == "markdown":
            print(render_feedback_template(payload))
        elif args.command == "aidlc-requirements":
            print(render_aidlc_requirements(payload))
        elif args.command == "aidlc-answer":
            print(render_aidlc_revision(payload))
        elif args.command == "aidlc-approve":
            print(render_execution_handoff(payload))
        elif args.command == "official-aidlc-questions":
            print(render_aidlc_requirements(payload))
        elif args.command == "aidlc-cycle" and payload["cycle_action"] in {"start-requirements-gathering", "resume-requirements-gathering"}:
            print(render_aidlc_requirements(payload))
        elif args.command == "aidlc-cycle" and payload["cycle_action"] == "record-answers-and-render-revision":
            print(render_aidlc_revision(payload))
        elif args.command == "aidlc-cycle":
            print(render_execution_handoff(payload))
        elif args.command == "activate" and args.format == "markdown" and (payload.get("execution_handoff") or payload.get("state") == "execution-ready"):
            handoff = payload.get("execution_handoff") if isinstance(payload, dict) else None
            print(render_execution_handoff(handoff if isinstance(handoff, dict) else payload))
        else:
            print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Planning Lock error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
