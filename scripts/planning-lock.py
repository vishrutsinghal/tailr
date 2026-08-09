#!/usr/bin/env python3
"""Create, approve, inspect, and enforce a local TailTrail Planning Lock."""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
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


def lock_path(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "planning" / "lock-v1.json"


def start_report_path(root: Path, run_id: str) -> Path:
    """Return the immutable planning report that a later approval activates."""
    return L.state_dir(root, run_id) / "planning" / "start-report-v1.json"


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


def create(root: Path, goal: str, run_id: str | None = None, reference_roots: list[str] | None = None) -> dict[str, Any]:
    root = root.resolve()
    selected_run_id = run_id or suggested_run_id(root, goal)
    if Path(selected_run_id).name != selected_run_id:
        raise ValueError("run_id must be a single local run identifier")
    L.init_run(root, selected_run_id, goal)
    payload = {
        "schema_version": "1",
        "type": "tailtrail-planning-lock",
        "run_id": selected_run_id,
        "goal": goal,
        "status": "awaiting-approval",
        "writes_allowed": False,
        "reference_roots": [{"path": value, "access": "read-only"} for value in (reference_roots or [])],
        "approval": None,
        "boundary": "Planning Lock permits read-only planning artifacts only. Source edits, Git mutations, project commands, scanners, and managed patch application require a separate approval for this run.",
    }
    path = lock_path(root, selected_run_id)
    L.atomic_json(path, payload)
    L.append_event(root, selected_run_id, "planning_lock_created", {"artifact": path.relative_to(L.state_dir(root, selected_run_id)).as_posix(), "writes_allowed": False, "reference_roots": payload["reference_roots"]})
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
    L.append_event(root, run_id, "start_report_saved", {"artifact": path.relative_to(root).as_posix()})
    return {"artifact": path.relative_to(root).as_posix(), "run_id": run_id}


def approve(root: Path, run_id: str, approved: bool) -> dict[str, Any]:
    if approved is not True:
        raise ValueError("planning approval requires --approved")
    root = root.resolve()
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
    path = start_report_path(root, run_id)
    if not path.is_file():
        raise ValueError(f"Start report for run `{run_id}` does not exist; run `tailtrail start` again")
    saved = read(path)
    report = saved.get("report", {})
    delivery = report.get("guided_delivery", {}) if isinstance(report, dict) else {}
    if delivery.get("mode") == "lean":
        return None
    plan = report.get("navigator", {}) if isinstance(report, dict) else {}
    matrix = plan.get("requirement_matrix", []) if isinstance(plan, dict) else []
    if not isinstance(matrix, list) or not matrix:
        paths = [item.get("path") for item in plan.get("likely_impacted_files", []) if isinstance(item, dict) and item.get("path")]
        matrix = _goal_requirements(str(saved.get("goal", "")).strip(), paths)
    return {"goal": str(saved.get("goal", "")).strip(), "requirements": matrix}


def _goal_requirements(goal: str, paths: list[str]) -> list[dict[str, Any]]:
    """Create a reviewable minimum requirement boundary when Navigator has none."""
    lowered = goal.lower()
    common = {
        "acceptance_criteria": ["The user-approved behavior is observable on the intended path."],
        "preserve_rules": ["Do not change behavior outside the approved scope."],
        "likely_paths": paths,
        "evidence_plan": ["Run the focused validation selected by the approved Navigator plan."],
    }
    if "zero quantity" in lowered and "validation" in lowered:
        return [
            {"display_id": "REQ-01", "kind": "change", "statement": "Reject zero quantities in the existing validation boundary.", **common},
            {"display_id": "REQ-02", "kind": "preserve", "statement": "Preserve valid positive-quantity behavior outside the new rejection case.", **common},
            {"display_id": "REQ-03", "kind": "change", "statement": "Add focused unit-test evidence for the zero-quantity rule and preserved positive behavior.", **common},
        ]
    return [{"display_id": "REQ-01", "kind": "change", "statement": goal, **common}]


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
    return {
        "run_id": run_id,
        "state": "revision-required" if result["rejected_requirement_uids"] else "ready-for-approval",
        "source_boundary": template["source_boundary"],
        **result,
        "next": "Ask targeted questions or offer AIDLC Requirements mode before revising rejected requirements." if result["next_requirement_mode"] == "ask-targeted-questions-or-offer-aidlc" else ("Use AIDLC Requirements mode before another material proposal." if result["next_requirement_mode"] == "aidlc-requirements-required" else "The complete proposal may be approved with the existing run ID."),
    }


def reject_all(root: Path, run_id: str, reason: str) -> dict[str, Any]:
    """Apply one explicit user reason to every requirement in the active proposal."""
    if not reason.strip():
        raise ValueError("reject-all requires a concrete --reason")
    template = feedback_template(root, run_id)
    feedback = [{"requirement_uid": row["requirement_uid"], "decision": "reject", "comment": reason.strip()} for row in template["requirements"]]
    return record_feedback(root, run_id, json.dumps(feedback))


def request_aidlc_requirements(root: Path, run_id: str) -> dict[str, Any]:
    """Start minimal AIDLC requirement gathering from saved planning evidence only."""
    root = root.resolve()
    template = feedback_template(root, run_id)
    proposal = _proposal_from_start_report(root, run_id)
    if proposal is None:
        proposal = {"goal": str(show(root, run_id).get("goal", "")).strip(), "requirements": _goal_requirements(str(show(root, run_id).get("goal", "")).strip(), [])}
    events = L.read_events(L.state_dir(root, run_id) / "events.jsonl")
    feedback = [row for event in events if event.get("event_type") == "proposal_rejected" for row in event.get("payload", {}).get("feedback", [])]
    stage = _aidlc_requirements_module().gather(proposal["goal"], proposal["requirements"], feedback)
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
        "aidlc_stage": stage,
        "questions": stage["questions"],
        "approval_gate": stage["stage_gate"],
    }
    L.atomic_json(artifact, document)
    payload = {"rejection_number": template["rejection_number"], "reason": "user-selected-aidlc-requirements", "artifact": artifact.relative_to(root).as_posix()}
    L.append_event(root, run_id, "aidlc_requirements_requested", payload)
    return {"run_id": run_id, "state": "aidlc-requirements-gathering", "artifact": artifact.relative_to(root).as_posix(), "source_boundary": template["source_boundary"], "requirements": proposal["requirements"], "questions": stage["questions"], "aidlc_stage": stage, "prior_feedback": feedback, "approval_gate": document["approval_gate"]}


def _aidlc_artifact(root: Path, run_id: str, name: str) -> Path:
    path = L.state_dir(root, run_id) / "planning" / name
    if not path.is_file():
        raise ValueError(f"AIDLC requirements artifact for run `{run_id}` does not exist; select AIDLC Requirements mode first")
    return path


def submit_aidlc_answers(root: Path, run_id: str, answers_json: str) -> dict[str, Any]:
    """Validate AIDLC answers and persist a revised, still-unapproved boundary."""
    root = root.resolve()
    current = show(root, run_id)
    if current["status"] != "awaiting-approval":
        raise ValueError(f"AIDLC answers are available only while run `{run_id}` is awaiting approval")
    stage_document = read(_aidlc_artifact(root, run_id, "aidlc-requirements-v1.json"))
    answers = json.loads(answers_json)
    engine = _aidlc_requirements_module()
    revision = engine.revise(stage_document, answers)
    revision_path = L.state_dir(root, run_id) / "planning" / "aidlc-revised-requirements-v1.json"
    payload = {"schema_version": "1", "type": "tailtrail-aidlc-revised-requirements", "run_id": run_id, "source_boundary": stage_document["source_boundary"], **revision}
    L.atomic_json(revision_path, payload)
    L.append_event(root, run_id, "aidlc_requirements_answered", {"artifact": revision_path.relative_to(root).as_posix(), "question_ids": sorted(revision["aidlc_answers"]), "status": "revision-ready"})
    return {"run_id": run_id, "state": "aidlc-revision-ready", "artifact": revision_path.relative_to(root).as_posix(), **revision}


def show_aidlc_requirements(root: Path, run_id: str) -> dict[str, Any]:
    """Resume an existing AIDLC requirements brief without creating another event."""
    root = root.resolve()
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
    artifact = L.state_dir(root.resolve(), run_id) / "planning" / "aidlc-requirements-v1.json"
    if artifact.exists():
        return {"cycle_action": "resume-requirements-gathering", **show_aidlc_requirements(root, run_id)}
    return {"cycle_action": "start-requirements-gathering", **request_aidlc_requirements(root, run_id)}


def approve_aidlc_requirements(root: Path, run_id: str, approved: bool) -> dict[str, Any]:
    """Create the immutable TailTrail anchor and activate the existing run."""
    if approved is not True:
        raise ValueError("AIDLC requirements approval requires --approved")
    root = root.resolve()
    current = show(root, run_id)
    if current["status"] != "awaiting-approval":
        raise ValueError(f"AIDLC requirements cannot activate run `{run_id}` from status `{current['status']}`")
    revision_path = _aidlc_artifact(root, run_id, "aidlc-revised-requirements-v1.json")
    revision = read(revision_path)
    anchor = _anchor_module()
    anchor.draft(root, run_id, revision_path)
    approved_anchor = anchor.approve(root, run_id)
    lock = approve(root, run_id, True)
    saved = read(start_report_path(root, run_id)).get("report", {})
    delivery = saved.get("guided_delivery", {}) if isinstance(saved, dict) else {}
    plan = saved.get("navigator", {}) if isinstance(saved, dict) else {}
    handoff = {
        "run_id": run_id,
        "state": "execution-ready",
        "anchor": (L.state_dir(root, run_id) / "anchors" / "approved-v1.json").relative_to(root).as_posix(),
        "active_requirements": [{"requirement_uid": row["requirement_uid"], "display_id": row["display_id"], "statement": row["statement"]} for row in approved_anchor["requirements"]],
        "workflow": delivery.get("stages", ["inspect approved scope", "implement", "validate", "review", "report completion"]),
        "selected_features": delivery.get("selected", []),
        "likely_paths": [row.get("path") for row in plan.get("likely_impacted_files", []) if isinstance(row, dict) and row.get("path")],
        "execution_boundary": "Implementation may begin only within the activated AIDLC-approved anchor. TailTrail remains responsible for scope, evidence, drift, recovery, and completion controls.",
    }
    handoff_path = L.state_dir(root, run_id) / "planning" / "execution-handoff-v1.json"
    L.atomic_json(handoff_path, handoff)
    L.append_event(root, run_id, "aidlc_requirements_approved", {"revision": revision_path.relative_to(root).as_posix(), "anchor": handoff["anchor"], "handoff": handoff_path.relative_to(root).as_posix()})
    L.append_event(root, run_id, "planning_activated", {"anchor": {"status": "created-from-aidlc", "artifact": handoff["anchor"]}})
    return {"planning_lock": lock, **handoff, "artifact": handoff_path.relative_to(root).as_posix()}


def render_aidlc_requirements(payload: dict[str, Any]) -> str:
    """Render the actionable AIDLC handoff for a chat host."""
    lines = [
        "# TailTrail AIDLC Requirements",
        "",
        f"**Run ID:** `{payload['run_id']}`",
        "**Stage:** requirements gathering — planning only; no source inspection or implementation has run.",
        "",
        "## Current requirement boundary",
        "",
        "| ID | Proposed requirement |",
        "| --- | --- |",
    ]
    for index, row in enumerate(payload["requirements"], start=1):
        lines.append(f"| {row.get('display_id', f'REQ-{index:02d}')} | {row.get('statement', '')} |")
    lines.extend(["", "## Questions to resolve", ""])
    for row in payload["questions"]:
        lines.extend([f"### {row['id']}", "", row["question"]])
        for option in row["options"]:
            lines.append(f"- **{option['id']}:** {option['text']}")
        lines.extend([f"- **Recommended:** {row['recommended']}", f"- **Reasoning:** {row['reasoning']}", ""])
    lines.extend([
        "",
        "## Next response",
        "",
        "- Reply with `Q1: ...`, `Q2: ...`, and `Q3: ...` (and `Q4` when present), or state that a question is not applicable.",
        "- TailTrail will then present a revised requirement boundary for approval. It will not inspect source or implement work until that revised boundary is approved.",
        "",
    ])
    return "\n".join(lines)


def render_aidlc_revision(payload: dict[str, Any]) -> str:
    lines = ["# TailTrail AIDLC Revised Requirements", "", f"**Run ID:** `{payload['run_id']}`", "**State:** awaiting AIDLC approval — no source inspection or implementation has run.", "", "## Revised requirement boundary", "", "| ID | Requirement |", "| --- | --- |"]
    for row in payload["requirements"]:
        lines.append(f"| {row.get('display_id')} | {row.get('statement')} |")
    lines.extend(["", "## Recorded AIDLC decisions", ""])
    for question_id, answer in payload["aidlc_answers"].items():
        lines.append(f"- **{question_id}:** {answer['selected']}")
    lines.extend(["", "## Approval", "", "- Approve this AIDLC boundary to create the immutable TailTrail anchor and activate this same run for scoped implementation.", ""])
    return "\n".join(lines)


def render_execution_handoff(payload: dict[str, Any]) -> str:
    lines = ["# TailTrail Execution Handoff", "", f"**Run ID:** `{payload['run_id']}`", "**State:** execution ready — AIDLC requirements are approved and the existing Planning Lock is activated.", "", "## Active requirements", ""]
    for row in payload["active_requirements"]:
        lines.append(f"- **{row['display_id']}:** {row['statement']}")
    lines.extend(["", "## Selected TailTrail controls", ""])
    for row in payload.get("selected_features", []):
        lines.append(f"- **{row.get('name')}:** {row.get('why')}")
    lines.extend(["", "## Execution boundary", "", f"- {payload['execution_boundary']}", "- Next: inspect only the approved paths, implement the smallest compliant change, run the selected evidence, then issue one completion report.", ""])
    return "\n".join(lines)


def render_feedback_template(payload: dict[str, Any]) -> str:
    """Render a small host-facing form instead of exposing implementation JSON."""
    lines = [
        "# TailTrail Plan Feedback",
        "",
        f"**Run ID:** `{payload['run_id']}`",
        "**State:** feedback required — no project source, tests, scanners, Git, or implementation commands were run.",
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
        "1. **Review individually:** reply with `REQ-01: approve` or `REQ-01: reject — <reason>` for every row.",
        "2. **Reject all:** reply `Reject all — <one concrete reason>`.",
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
    current = show(root, run_id)
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
    lock = current if current["status"] == "approved" else approve(root, run_id, True)
    L.append_event(root, run_id, "planning_activated", {"anchor": anchor_result or {"status": "not-required"}})
    return {"planning_lock": lock, "anchor": anchor_result or {"status": "not-required", "reason": "lean Start runs do not create canonical requirement state"}}


def assert_write_allowed(root: Path, run_id: str) -> dict[str, Any]:
    payload = show(root, run_id)
    if payload.get("status") != "approved" or payload.get("writes_allowed") is not True:
        raise ValueError(f"Planning Lock for run `{run_id}` is `{payload.get('status')}`; explicit approval is required before managed source changes")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start", help="Create a planning-only lock and local run.")
    start.add_argument("--root", type=Path, default=Path.cwd())
    start.add_argument("--goal", required=True)
    start.add_argument("--run-id")
    start.add_argument("--reference-root", action="append", default=[])
    approve_parser = sub.add_parser("approve", help="Explicitly allow managed writes for one planning run.")
    approve_parser.add_argument("--root", type=Path, default=Path.cwd())
    approve_parser.add_argument("--run-id", required=True)
    approve_parser.add_argument("--approved", action="store_true")
    activate_parser = sub.add_parser("activate", help="Approve the saved Start report and create its required requirement anchor.")
    activate_parser.add_argument("--root", type=Path, default=Path.cwd())
    activate_parser.add_argument("--run-id", required=True)
    activate_parser.add_argument("--approved", action="store_true")
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
            payload = create(args.root, args.goal, args.run_id, args.reference_root)
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
        elif args.command == "aidlc-cycle" and payload["cycle_action"] in {"start-requirements-gathering", "resume-requirements-gathering"}:
            print(render_aidlc_requirements(payload))
        elif args.command == "aidlc-cycle" and payload["cycle_action"] == "record-answers-and-render-revision":
            print(render_aidlc_revision(payload))
        elif args.command == "aidlc-cycle":
            print(render_execution_handoff(payload))
        else:
            print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Planning Lock error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
