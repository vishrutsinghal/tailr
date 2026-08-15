#!/usr/bin/env python3
"""Propose and approve a versioned, pre-implementation TailTrail plan revision."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = (
    "A plan revision changes only versioned TailTrail planning metadata. It does not inspect or edit project "
    "source, run tests, scanners, builds, package managers, Git, or implementation commands."
)
CHANGE_KINDS = {"scope-add", "scope-remove", "requirement-add", "requirement-remove", "requirement-update", "proof-update"}
STANDARD_MODE_FEATURES = {
    "included": [
        "Navigator planning and Planning Lock",
        "Local AIDLC Requirements stage: assumptions, non-goals, questions, recommendations, and answer revision",
        "Canonical approved anchor and requirement-linked execution handoff",
    ],
    "not_included": ["External official engine execution or session attachment"],
}


def module(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    loaded = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(loaded)
    return loaded


LOCK = module("planning_revision_lock", "planning-lock.py")
LEDGER = module("planning_revision_ledger", "run-ledger.py")
ANCHOR = module("planning_revision_anchor", "change-intent-anchor.py")
INTENT_BRIDGE = module("planning_revision_intent_bridge", "spec-kit-bridge.py")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def revision_dir(root: Path, run_id: str) -> Path:
    return LEDGER.state_dir(root, run_id) / "planning" / "revisions"


def revision_path(root: Path, run_id: str, number: int) -> Path:
    return revision_dir(root, run_id) / f"revision-v{number}.json"


def revision_report_path(root: Path, run_id: str, number: int) -> Path:
    return revision_dir(root, run_id) / f"start-report-v{number}.json"


def route_dir(root: Path, run_id: str) -> Path:
    return LEDGER.state_dir(root, run_id) / "planning" / "authority-routes"


def route_path(root: Path, run_id: str, number: int) -> Path:
    return route_dir(root, run_id) / f"route-{number:03d}.json"


def _safe_text(value: Any, field: str, *, required: bool = True) -> str:
    result = str(value or "").strip()
    if required and not result:
        raise ValueError(f"revision change needs `{field}`")
    if len(result) > 500 or "\x00" in result:
        raise ValueError(f"revision change `{field}` must be a bounded safe text value")
    return result


def _safe_path(value: Any) -> str:
    path = Path(_safe_text(value, "path"))
    if path.is_absolute() or ".." in path.parts or path.as_posix() in {"", "."}:
        raise ValueError("revision change path must be repository-relative without parent traversal")
    return path.as_posix()


def _list_of_text(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"revision change `{field}` must be a non-empty list")
    result = [_safe_text(item, field) for item in value]
    return list(dict.fromkeys(result))


def _requirements(report: dict[str, Any], root: Path, run_id: str) -> list[dict[str, Any]]:
    navigator = report.setdefault("navigator", {})
    if not isinstance(navigator, dict):
        raise ValueError("saved Navigator report is invalid")
    matrix = navigator.get("requirement_matrix")
    if not isinstance(matrix, list) or not matrix:
        # The helper reads the current immutable/active report, which is exactly this base revision.
        generated = LOCK._proposal_from_start_report(root, run_id)  # type: ignore[attr-defined]
        matrix = generated.get("requirements", []) if isinstance(generated, dict) else []
        navigator["requirement_matrix"] = matrix
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(matrix, start=1):
        if not isinstance(raw, dict):
            raise ValueError("saved requirement matrix contains an invalid row")
        row = copy.deepcopy(raw)
        statement = _safe_text(row.get("statement"), "statement")
        row["statement"] = statement
        row["display_id"] = _safe_text(row.get("display_id") or f"REQ-{index:02d}", "display_id")
        row["requirement_uid"] = _safe_text(row.get("requirement_uid") or ANCHOR.uid(run_id, statement), "requirement_uid")
        row.setdefault("kind", "change")
        row.setdefault("acceptance_criteria", ["The approved outcome is observable through its named evidence."])
        row.setdefault("preserve_rules", ["Do not change behavior outside the approved scope."])
        row.setdefault("likely_paths", [])
        row.setdefault("evidence_plan", ["Run the focused validation selected by the approved Navigator plan."])
        normalized.append(row)
    navigator["requirement_matrix"] = normalized
    return normalized


def _requirement(rows: list[dict[str, Any]], value: Any) -> dict[str, Any]:
    identifier = _safe_text(value, "requirement_uid")
    matches = [row for row in rows if identifier in {str(row.get("requirement_uid")), str(row.get("display_id"))}]
    if len(matches) != 1:
        raise ValueError(f"revision change references unknown requirement `{identifier}`")
    return matches[0]


def _impact_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    navigator = report.setdefault("navigator", {})
    values = navigator.setdefault("likely_impacted_files", [])
    if not isinstance(values, list):
        raise ValueError("saved Navigator impact list is invalid")
    return values


def _add_impact(report: dict[str, Any], path: str, reason: str) -> None:
    impacts = _impact_rows(report)
    if not any(isinstance(row, dict) and row.get("path") == path for row in impacts):
        impacts.append({"path": path, "reason": f"user-approved planning revision: {reason}"})


def _remove_impact_if_unreferenced(report: dict[str, Any], rows: list[dict[str, Any]], path: str) -> None:
    if any(path in row.get("likely_paths", []) for row in rows):
        return
    navigator = report["navigator"]
    navigator["likely_impacted_files"] = [
        row for row in _impact_rows(report)
        if not (isinstance(row, dict) and row.get("path") == path)
    ]


def _new_display_id(rows: list[dict[str, Any]]) -> str:
    used = {str(row.get("display_id", "")) for row in rows}
    index = 1
    while f"REQ-{index:02d}" in used:
        index += 1
    return f"REQ-{index:02d}"


def _apply_change(report: dict[str, Any], rows: list[dict[str, Any]], change: dict[str, Any], run_id: str) -> dict[str, Any]:
    kind = _safe_text(change.get("kind"), "kind")
    if kind not in CHANGE_KINDS:
        raise ValueError(f"unsupported revision change kind `{kind}`")
    reason = _safe_text(change.get("reason"), "reason")
    normalized: dict[str, Any] = {"kind": kind, "reason": reason}
    if kind in {"scope-add", "scope-remove"}:
        row = _requirement(rows, change.get("requirement_uid"))
        path = _safe_path(change.get("path"))
        paths = [str(item) for item in row.get("likely_paths", []) if isinstance(item, str)]
        if kind == "scope-add":
            if path in paths:
                raise ValueError(f"`{path}` is already in requirement `{row['display_id']}` scope")
            row["likely_paths"] = [*paths, path]
            _add_impact(report, path, reason)
        else:
            if path not in paths:
                raise ValueError(f"`{path}` is not in requirement `{row['display_id']}` scope")
            row["likely_paths"] = [item for item in paths if item != path]
            _remove_impact_if_unreferenced(report, rows, path)
        normalized.update({"requirement_uid": row["requirement_uid"], "display_id": row["display_id"], "path": path})
    elif kind == "requirement-update":
        row = _requirement(rows, change.get("requirement_uid"))
        row["statement"] = _safe_text(change.get("statement"), "statement")
        normalized.update({"requirement_uid": row["requirement_uid"], "display_id": row["display_id"], "statement": row["statement"]})
    elif kind == "proof-update":
        row = _requirement(rows, change.get("requirement_uid"))
        row["evidence_plan"] = _list_of_text(change.get("evidence_plan"), "evidence_plan")
        normalized.update({"requirement_uid": row["requirement_uid"], "display_id": row["display_id"], "evidence_plan": row["evidence_plan"]})
    elif kind == "requirement-add":
        statement = _safe_text(change.get("statement"), "statement")
        display_id = _safe_text(change.get("display_id") or _new_display_id(rows), "display_id")
        if any(row["display_id"] == display_id for row in rows):
            raise ValueError(f"requirement display ID `{display_id}` already exists")
        paths = [_safe_path(item) for item in change.get("likely_paths", [])] if isinstance(change.get("likely_paths", []), list) else []
        row = {
            "requirement_uid": ANCHOR.uid(run_id, statement), "display_id": display_id, "kind": change.get("requirement_kind", "change"),
            "statement": statement, "acceptance_criteria": _list_of_text(change.get("acceptance_criteria"), "acceptance_criteria"),
            "preserve_rules": _list_of_text(change.get("preserve_rules"), "preserve_rules"), "likely_paths": list(dict.fromkeys(paths)),
            "evidence_plan": _list_of_text(change.get("evidence_plan"), "evidence_plan"),
        }
        if row["kind"] not in ANCHOR.KINDS:
            raise ValueError("requirement_kind is not allowed")
        rows.append(row)
        for path in row["likely_paths"]:
            _add_impact(report, path, reason)
        normalized.update({"requirement_uid": row["requirement_uid"], "display_id": display_id, "statement": statement})
    else:  # requirement-remove
        row = _requirement(rows, change.get("requirement_uid"))
        if len(rows) == 1:
            raise ValueError("a plan revision must retain at least one requirement")
        rows.remove(row)
        for path in row.get("likely_paths", []):
            _remove_impact_if_unreferenced(report, rows, str(path))
        normalized.update({"requirement_uid": row["requirement_uid"], "display_id": row["display_id"]})
    return normalized


def _delta(base: list[dict[str, Any]], revised: list[dict[str, Any]]) -> dict[str, Any]:
    base_by_uid = {row["requirement_uid"]: row for row in base}
    revised_by_uid = {row["requirement_uid"]: row for row in revised}
    changed = sorted(uid for uid in set(base_by_uid) & set(revised_by_uid) if canonical(base_by_uid[uid]) != canonical(revised_by_uid[uid]))
    paths_before = {path for row in base for path in row.get("likely_paths", [])}
    paths_after = {path for row in revised for path in row.get("likely_paths", [])}
    proof_changed = sorted(uid for uid in set(base_by_uid) & set(revised_by_uid) if base_by_uid[uid].get("evidence_plan") != revised_by_uid[uid].get("evidence_plan"))
    return {
        "requirements_changed": sorted([*changed, *(uid for uid in revised_by_uid if uid not in base_by_uid), *(uid for uid in base_by_uid if uid not in revised_by_uid)]),
        "scope_added": sorted(paths_after - paths_before),
        "scope_removed": sorted(paths_before - paths_after),
        "proof_changed": proof_changed,
    }


def _route_context(changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Persist only structured revision intent, never raw conversation text."""
    values: list[dict[str, Any]] = []
    for change in changes:
        kind = _safe_text(change.get("kind"), "kind")
        if kind not in CHANGE_KINDS:
            raise ValueError(f"unsupported revision change kind `{kind}`")
        row = {"kind": kind, "reason": _safe_text(change.get("reason"), "reason")}
        for field in ("requirement_uid", "display_id", "path"):
            if change.get(field) is not None:
                row[field] = _safe_text(change.get(field), field)
        values.append(row)
    return values


def _is_aidlc_bound(report: dict[str, Any]) -> bool:
    return isinstance(report.get("aidlc_requirements"), dict) or (report.get("aidlc_mode", {}) or {}).get("mode") == "full"


def _official_design_route(context: list[dict[str, Any]]) -> bool:
    text = " ".join(item.get("reason", "") for item in context).lower()
    return any(word in text for word in ("architecture", "architectural", "design", "data model", "public contract"))


def _route_aidlc(root: Path, run_id: str, report: dict[str, Any], context: list[dict[str, Any]]) -> dict[str, Any]:
    full = (report.get("aidlc_mode", {}) or {}).get("mode") == "full"
    route = "official-aidlc-design" if full and _official_design_route(context) else ("official-aidlc-requirements" if full else "aidlc-requirements")
    existing = sorted(route_dir(root, run_id).glob("route-*.json"))
    number = len(existing) + 1
    destination = route_path(root, run_id, number)
    payload = {
        "schema_version": "1", "type": "tailtrail-planning-authority-route", "run_id": run_id,
        "route_id": f"route-{number:03d}", "authority": "official-ai-dlc-pack" if full else "aidlc-requirements",
        "route": route, "state": "authority-refinement-required", "revision_context": context,
        "boundary": "TailTrail did not create a parallel local plan revision. AIDLC owns requirement/design refinement; TailTrail preserves the Planning Lock, evidence, and later anchor controls.",
        "created_at": utc_now(),
    }
    if route == "official-aidlc-design":
        payload["next"] = "Run the verified official AI-DLC Design stage through the configured host, then return its sanitized stage outcome before a new requirement boundary is approved."
        LEDGER.atomic_json(destination, payload)
        LEDGER.append_event(root, run_id, "planning_authority_routed", {"route": route, "artifact": destination.relative_to(root).as_posix()})
        return {**payload, "artifact": destination.relative_to(root).as_posix()}
    refinement = LOCK.request_aidlc_requirements(root, run_id, context)
    payload["refinement_artifact"] = refinement["artifact"]
    payload["next"] = "Answer the AIDLC requirement questions, review its revised boundary, then use the existing AIDLC approval gate."
    LEDGER.atomic_json(destination, payload)
    LEDGER.append_event(root, run_id, "planning_authority_routed", {"route": route, "artifact": destination.relative_to(root).as_posix(), "refinement": refinement["artifact"]})
    return {**payload, "artifact": destination.relative_to(root).as_posix(), "aidlc_refinement": refinement}


def _route_intent_bridge(root: Path, run_id: str, report: dict[str, Any], context: list[dict[str, Any]]) -> dict[str, Any]:
    source = report["spec_kit_source"]
    feature = str(source.get("feature_id", "")).strip()
    if not feature:
        raise ValueError("Intent Bridge report has no feature identifier")
    current = INTENT_BRIDGE.load(root, feature)
    source_changed = current.get("source_revision") != source.get("source_revision") or current.get("import") != source.get("import")
    existing = sorted(route_dir(root, run_id).glob("route-*.json"))
    number = len(existing) + 1
    destination = route_path(root, run_id, number)
    payload = {
        "schema_version": "1", "type": "tailtrail-planning-authority-route", "run_id": run_id,
        "route_id": f"route-{number:03d}", "authority": "intent-bridge-source", "route": "intent-bridge-amendment",
        "state": "source-amendment-required", "feature_id": feature,
        "saved_source_revision": source.get("source_revision"), "current_source_revision": current.get("source_revision"),
        "source_changed": source_changed, "revision_context": context,
        "boundary": "The imported requirement wording remains source-owned. TailTrail recorded an amendment request only; it did not rewrite imported requirements, source artifacts, or the Start report.",
        "created_at": utc_now(),
    }
    if source_changed:
        payload["next"] = "The imported source changed. Use the existing Intent Bridge amendment workflow for an activated run, or restart pre-approval planning from the newly imported source snapshot; do not apply a local wording revision."
    else:
        payload["next"] = "Update the authoritative requirement source, explicitly import its new snapshot, then create/review planning from that source. The current imported wording remains unchanged."
    LEDGER.atomic_json(destination, payload)
    LEDGER.append_event(root, run_id, "planning_authority_routed", {"route": payload["route"], "artifact": destination.relative_to(root).as_posix(), "source_changed": source_changed})
    return {**payload, "artifact": destination.relative_to(root).as_posix()}


def propose_aidlc_standard(root: Path, run_id: str, approved_proposal: bool) -> dict[str, Any]:
    """Create a reviewed Lite-to-Standard lifecycle proposal without starting AIDLC."""
    if approved_proposal is not True:
        raise ValueError("AIDLC Standard mode proposal requires --approved-proposal")
    root = root.resolve()
    LOCK.assert_discussion_allowed(root, run_id)
    state = LOCK.revision_state(root, run_id)
    if state.get("pending_revision") is not None:
        raise ValueError(f"plan revision v{state['pending_revision']} is already awaiting approval; approve or supersede it first")
    saved = LOCK.active_start_report(root, run_id)
    report = copy.deepcopy(saved.get("report"))
    if not isinstance(report, dict):
        raise ValueError("active Start report is invalid")
    current = (report.get("aidlc_mode") or {}).get("mode", "lite")
    if current != "lite":
        raise ValueError(f"only an awaiting Lite run may switch to Standard AIDLC; this run is `{current}`")
    if isinstance(report.get("spec_kit_source"), dict):
        raise ValueError("Intent Bridge requirements are source-owned; use its amendment/authority route instead of a local Standard AIDLC switch")
    number = int(state.get("active_revision", 1)) + 1
    report["aidlc_mode"] = {
        "mode": "standard",
        "selection": "interactive-plan-proposal",
        "state": "awaiting-mode-approval",
        "boundary": "The requested Standard AIDLC Requirements stage begins only after this exact mode-switch revision is approved.",
    }
    report["aidlc_mode_features"] = copy.deepcopy(STANDARD_MODE_FEATURES)
    proposal = {
        "schema_version": "1", "type": "tailtrail-aidlc-mode-switch", "run_id": run_id,
        "revision": number, "base_revision": int(state.get("active_revision", 1)), "state": "awaiting-approval",
        "from_mode": "lite", "to_mode": "standard", "approval_required": True,
        "base_report_fingerprint": fingerprint(saved.get("report", {})), "revised_report_fingerprint": fingerprint(report),
        "added_controls": STANDARD_MODE_FEATURES["included"][1:], "not_included": STANDARD_MODE_FEATURES["not_included"],
        "boundary": "This proposal changes only TailTrail planning metadata. It does not start AIDLC questions, inspect project source, run tests, edit source, or permit implementation.",
        "created_at": utc_now(), "proposed_report": report,
    }
    destination = revision_path(root, run_id, number)
    with LEDGER.RunLock(LEDGER.state_dir(root, run_id) / ".lock"):
        LEDGER.atomic_json(destination, proposal)
        LEDGER.atomic_json(LOCK.revision_state_path(root, run_id), {**state, "pending_revision": number, "pending_artifact": destination.relative_to(root).as_posix()})
    LEDGER.append_event(root, run_id, "planning_aidlc_mode_switch_proposed", {"revision": number, "from_mode": "lite", "to_mode": "standard", "artifact": destination.relative_to(root).as_posix()})
    return {**proposal, "artifact": destination.relative_to(root).as_posix()}


def propose(root: Path, run_id: str, changes_json: str, approved_proposal: bool) -> dict[str, Any]:
    if approved_proposal is not True:
        raise ValueError("planning revision proposal requires --approved-proposal")
    root = root.resolve()
    LOCK.assert_discussion_allowed(root, run_id)
    state = LOCK.revision_state(root, run_id)
    if state.get("pending_revision") is not None:
        raise ValueError(f"plan revision v{state['pending_revision']} is already awaiting approval; approve or supersede it first")
    payload = LOCK.active_start_report(root, run_id)
    report = copy.deepcopy(payload.get("report"))
    if not isinstance(report, dict):
        raise ValueError("active Start report is invalid")
    try:
        changes = json.loads(changes_json)
    except json.JSONDecodeError as error:
        raise ValueError(f"revision changes must be valid JSON: {error}") from error
    if not isinstance(changes, list) or not changes:
        raise ValueError("revision changes must be a non-empty JSON list")
    if not all(isinstance(item, dict) for item in changes):
        raise ValueError("every revision change must be an object")
    context = _route_context(changes)
    if isinstance(report.get("spec_kit_source"), dict):
        return _route_intent_bridge(root, run_id, report, context)
    if _is_aidlc_bound(report):
        return _route_aidlc(root, run_id, report, context)
    rows = _requirements(report, root, run_id)
    base_rows = copy.deepcopy(rows)
    normalized_changes = [_apply_change(report, rows, item, run_id) for item in changes]
    navigator = report.setdefault("navigator", {})
    navigator["requirement_matrix"] = rows
    # Hands-free v1 anchors normally derive rows from their feature program.
    # A reviewed IP-3 delta is the explicit replacement boundary for this run.
    navigator["revision_requirement_matrix"] = True
    number = int(state.get("active_revision", 1)) + 1
    proposed = {
        "schema_version": "1", "type": "tailtrail-plan-revision", "run_id": run_id,
        "revision": number, "base_revision": int(state.get("active_revision", 1)), "state": "awaiting-approval",
        "changes": normalized_changes, "delta_summary": _delta(base_rows, rows), "approval_required": True,
        "base_report_fingerprint": fingerprint(payload.get("report", {})), "revised_report_fingerprint": fingerprint(report),
        "requirement_continuity": [{"requirement_uid": row["requirement_uid"], "display_id": row["display_id"], "statement": row["statement"]} for row in rows],
        "rationale": [{"kind": item["kind"], "requirement_uid": item.get("requirement_uid"), "reason": item["reason"]} for item in normalized_changes],
        "boundary": BOUNDARY, "created_at": utc_now(), "proposed_report": report,
    }
    with LEDGER.RunLock(LEDGER.state_dir(root, run_id) / ".lock"):
        destination = revision_path(root, run_id, number)
        if destination.exists():
            raise ValueError(f"plan revision v{number} already exists")
        LEDGER.atomic_json(destination, proposed)
        next_state = {**state, "pending_revision": number, "pending_artifact": destination.relative_to(root).as_posix()}
        LEDGER.atomic_json(LOCK.revision_state_path(root, run_id), next_state)
    LEDGER.append_event(root, run_id, "planning_revision_proposed", {
        "revision": number, "base_revision": proposed["base_revision"], "artifact": destination.relative_to(root).as_posix(),
        "requirement_uids": [item["requirement_uid"] for item in normalized_changes if item.get("requirement_uid")],
    })
    return {**proposed, "artifact": destination.relative_to(root).as_posix()}


def show(root: Path, run_id: str, revision: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    state = LOCK.revision_state(root, run_id)
    number = revision if revision is not None else state.get("pending_revision")
    if number is None:
        raise ValueError(f"no proposed plan revision exists for run `{run_id}`")
    path = revision_path(root, run_id, int(number))
    if not path.is_file():
        raise ValueError(f"plan revision v{number} does not exist for run `{run_id}`")
    return {**json.loads(path.read_text(encoding="utf-8")), "artifact": path.relative_to(root).as_posix()}


def authority_show(root: Path, run_id: str, sequence: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    available = sorted(route_dir(root, run_id).glob("route-*.json"))
    if not available:
        raise ValueError(f"no AIDLC or Intent Bridge authority route exists for run `{run_id}`")
    path = route_path(root, run_id, sequence) if sequence is not None else available[-1]
    if not path.is_file():
        raise ValueError(f"authority route `{sequence}` does not exist for run `{run_id}`")
    return {**json.loads(path.read_text(encoding="utf-8")), "artifact": path.relative_to(root).as_posix()}


def approve(root: Path, run_id: str, revision: int, approved: bool) -> dict[str, Any]:
    if approved is not True:
        raise ValueError("plan revision approval requires --approved")
    root = root.resolve()
    LOCK.assert_discussion_allowed(root, run_id)
    state = LOCK.revision_state(root, run_id)
    if state.get("pending_revision") != revision:
        raise ValueError(f"plan revision v{revision} is not the current pending revision for run `{run_id}`")
    proposed = show(root, run_id, revision)
    if proposed["base_revision"] != state.get("active_revision"):
        raise ValueError("plan revision base no longer matches the active reviewed revision")
    if proposed["revised_report_fingerprint"] != fingerprint(proposed.get("proposed_report", {})):
        raise ValueError("plan revision artifact fingerprint does not match its proposed report")
    snapshot = {"schema_version": "1", "type": "tailtrail-start-report", "run_id": run_id, "revision": revision, "goal": proposed["proposed_report"].get("goal", ""), "report": proposed["proposed_report"]}
    report_path = revision_report_path(root, run_id, revision)
    old_state = copy.deepcopy(state)
    next_state = {**state, "active_revision": revision, "active_report": report_path.relative_to(root).as_posix(), "pending_revision": None, "pending_artifact": None}
    with LEDGER.RunLock(LEDGER.state_dir(root, run_id) / ".lock"):
        LEDGER.atomic_json(report_path, snapshot)
        LEDGER.atomic_json(LOCK.revision_state_path(root, run_id), next_state)
    try:
        activated = LOCK.activate(root, run_id, True)
    except Exception:
        LEDGER.atomic_json(LOCK.revision_state_path(root, run_id), old_state)
        raise
    LEDGER.append_event(root, run_id, "planning_revision_approved", {
        "revision": revision, "artifact": proposed["artifact"], "active_report": report_path.relative_to(root).as_posix(),
        "anchor": (activated.get("anchor") or {}).get("artifact"),
    })
    return {"run_id": run_id, "revision": revision, "state": "execution-ready", "revision_artifact": proposed["artifact"], "active_report": report_path.relative_to(root).as_posix(), **activated}


def approve_aidlc_standard(root: Path, run_id: str, revision: int, approved: bool) -> dict[str, Any]:
    """Accept the lifecycle revision and begin Standard AIDLC requirements in-place."""
    if approved is not True:
        raise ValueError("AIDLC Standard mode approval requires --approved")
    root = root.resolve()
    LOCK.assert_discussion_allowed(root, run_id)
    state = LOCK.revision_state(root, run_id)
    if state.get("pending_revision") != revision:
        raise ValueError(f"AIDLC Standard revision v{revision} is not the current pending revision for run `{run_id}`")
    proposed = show(root, run_id, revision)
    if proposed.get("type") != "tailtrail-aidlc-mode-switch" or proposed.get("to_mode") != "standard":
        raise ValueError(f"plan revision v{revision} is not a Lite-to-Standard AIDLC mode proposal")
    if proposed.get("base_revision") != state.get("active_revision") or proposed.get("revised_report_fingerprint") != fingerprint(proposed.get("proposed_report", {})):
        raise ValueError("AIDLC Standard mode proposal no longer matches the active reviewed plan")
    report = copy.deepcopy(proposed["proposed_report"])
    report["aidlc_mode"]["selection"] = "interactive-plan-approved-mode-switch"
    report["aidlc_mode"]["state"] = "requirements-gathering"
    report_path = revision_report_path(root, run_id, revision)
    snapshot = {"schema_version": "1", "type": "tailtrail-start-report", "run_id": run_id, "revision": revision, "goal": report.get("goal", ""), "report": report}
    with LEDGER.RunLock(LEDGER.state_dir(root, run_id) / ".lock"):
        LEDGER.atomic_json(report_path, snapshot)
        LEDGER.atomic_json(LOCK.revision_state_path(root, run_id), {**state, "active_revision": revision, "active_report": report_path.relative_to(root).as_posix(), "pending_revision": None, "pending_artifact": None})
    requirements = LOCK.request_aidlc_requirements(root, run_id)
    report["aidlc_requirements"] = requirements
    LEDGER.atomic_json(report_path, {**snapshot, "report": report})
    LEDGER.append_event(root, run_id, "planning_aidlc_mode_switch_approved", {"revision": revision, "from_mode": "lite", "to_mode": "standard", "artifact": proposed["artifact"], "active_report": report_path.relative_to(root).as_posix(), "requirements": requirements["artifact"]})
    return {"run_id": run_id, "revision": revision, "state": "aidlc-requirements-gathering", "revision_artifact": proposed["artifact"], "active_report": report_path.relative_to(root).as_posix(), "aidlc_requirements": requirements, "boundary": "The run remains awaiting approval. Answer and approve the Standard AIDLC requirements boundary before implementation."}


def render(payload: dict[str, Any]) -> str:
    lines = ["# TailTrail Plan Revision", "", f"**Run ID:** `{payload['run_id']}`", f"**Revision:** v{payload['base_revision']} -> v{payload['revision']}", "**State:** awaiting approval — no project source, tests, scanners, Git, or implementation commands were run.", "", "## Changed requirements", ""]
    for item in payload["changes"]:
        target = item.get("display_id", item.get("requirement_uid", "plan"))
        lines.append(f"- **{target}:** `{item['kind']}` — {item['reason']}")
    delta = payload["delta_summary"]
    lines.extend(["", "## Delta", "", f"- Requirement rows changed: {len(delta['requirements_changed'])}", f"- Scope added: {', '.join(f'`{item}`' for item in delta['scope_added']) or 'none'}", f"- Scope removed: {', '.join(f'`{item}`' for item in delta['scope_removed']) or 'none'}", f"- Proof rows changed: {', '.join(f'`{item}`' for item in delta['proof_changed']) or 'none'}", "", "## Approval", "", f"- Approve exactly v{payload['revision']} to freeze this revised plan into the immutable anchor and activate this same run.", "- A v1 approval cannot activate this v2-or-later proposal.", ""])
    return "\n".join(lines)


def render_aidlc_standard(payload: dict[str, Any]) -> str:
    lines = ["# TailTrail AIDLC Mode Switch", "", f"**Run ID:** `{payload['run_id']}`", f"**Revision:** v{payload['base_revision']} -> v{payload['revision']}", "**Mode:** `lite` -> `standard`", "**State:** awaiting approval — no AIDLC questions, project source, tests, scanners, Git, or implementation commands were run.", "", "## Added Standard AIDLC controls", ""]
    lines.extend(f"- {item}" for item in payload.get("added_controls", []))
    lines.extend(["", "## Still not included", ""])
    lines.extend(f"- {item}" for item in payload.get("not_included", []))
    lines.extend(["", "## Approval", "", f"- Approve exactly v{payload['revision']} to begin Standard AIDLC requirements under this same run ID.", "- This does not approve implementation. A separate AIDLC requirement-boundary approval remains required.", ""])
    return "\n".join(lines)


def render_authority_route(payload: dict[str, Any]) -> str:
    state = str(payload.get("state", "authority-refinement-required")).replace("-", " ")
    lines = ["# TailTrail Authority Route", "", f"**Run ID:** `{payload['run_id']}`", f"**Authority:** `{payload['authority']}`", f"**Route:** `{payload['route']}`", f"**State:** {state} — no project source, tests, scanners, Git, or implementation commands were run.", "", "## Requested material change", ""]
    for item in payload.get("revision_context", []):
        target = item.get("requirement_uid", item.get("display_id", "requirement boundary"))
        lines.append(f"- **{target}:** `{item['kind']}` — {item['reason']}")
    lines.extend(["", "## Next", "", f"- {payload['next']}", "", "## Boundary", "", f"- {payload['boundary']}", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    propose_parser = sub.add_parser("propose", help="Persist one explicitly authorized proposed plan revision.")
    propose_parser.add_argument("--root", type=Path, default=Path.cwd())
    propose_parser.add_argument("--run-id", required=True)
    source = propose_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--changes", help="JSON list of material revision changes.")
    source.add_argument("--changes-base64", help="Base64 UTF-8 JSON changes for Windows shell safety.")
    propose_parser.add_argument("--approved-proposal", action="store_true")
    show_parser = sub.add_parser("show", help="Show one saved plan revision.")
    show_parser.add_argument("--root", type=Path, default=Path.cwd())
    show_parser.add_argument("--run-id", required=True)
    show_parser.add_argument("--revision", type=int)
    authority_parser = sub.add_parser("authority-show", help="Show the latest AIDLC or Intent Bridge authority route.")
    authority_parser.add_argument("--root", type=Path, default=Path.cwd())
    authority_parser.add_argument("--run-id", required=True)
    authority_parser.add_argument("--sequence", type=int)
    mode_parser = sub.add_parser("aidlc-standard", help="Propose a versioned Lite-to-Standard AIDLC switch for an awaiting run.")
    mode_parser.add_argument("--root", type=Path, default=Path.cwd())
    mode_parser.add_argument("--run-id", required=True)
    mode_parser.add_argument("--approved-proposal", action="store_true")
    mode_approve_parser = sub.add_parser("aidlc-standard-approve", help="Approve the exact Lite-to-Standard revision and begin requirements gathering.")
    mode_approve_parser.add_argument("--root", type=Path, default=Path.cwd())
    mode_approve_parser.add_argument("--run-id", required=True)
    mode_approve_parser.add_argument("--revision", type=int, required=True)
    mode_approve_parser.add_argument("--approved", action="store_true")
    approve_parser = sub.add_parser("approve", help="Approve the exact proposed revision and activate the same run.")
    approve_parser.add_argument("--root", type=Path, default=Path.cwd())
    approve_parser.add_argument("--run-id", required=True)
    approve_parser.add_argument("--revision", type=int, required=True)
    approve_parser.add_argument("--approved", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "propose":
            changes = args.changes
            if args.changes_base64 is not None:
                import base64
                changes = base64.b64decode(args.changes_base64, validate=True).decode("utf-8")
            result = propose(args.root, args.run_id, str(changes), args.approved_proposal)
            print(render_authority_route(result) if result.get("type") == "tailtrail-planning-authority-route" else render(result))
        elif args.command == "show":
            print(json.dumps(show(args.root, args.run_id, args.revision), indent=2, sort_keys=True))
        elif args.command == "authority-show":
            print(json.dumps(authority_show(args.root, args.run_id, args.sequence), indent=2, sort_keys=True))
        elif args.command == "aidlc-standard":
            print(render_aidlc_standard(propose_aidlc_standard(args.root, args.run_id, args.approved_proposal)))
        elif args.command == "aidlc-standard-approve":
            result = approve_aidlc_standard(args.root, args.run_id, args.revision, args.approved)
            print(LOCK.render_aidlc_requirements(result["aidlc_requirements"]))
        else:
            result = approve(args.root, args.run_id, args.revision, args.approved)
            handoff = result.get("execution_handoff")
            print(LOCK.render_execution_handoff(handoff if isinstance(handoff, dict) else result))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Planning revision error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
