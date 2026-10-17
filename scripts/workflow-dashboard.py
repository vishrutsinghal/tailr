#!/usr/bin/env python3
"""Render a read-only local workflow dashboard from an existing TailTrail run."""
from __future__ import annotations

import argparse
import html
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def ledger() -> Any:
    spec = importlib.util.spec_from_file_location("workflow_dashboard_ledger", ROOT / "scripts" / "run-ledger.py")
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def canonical_state_module() -> Any:
    spec = importlib.util.spec_from_file_location("workflow_dashboard_official_state", ROOT / "scripts" / "official-aidlc-state.py")
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


L = ledger()


def anchor_module() -> Any:
    spec = importlib.util.spec_from_file_location("dashboard_anchor", ROOT / "scripts" / "change-intent-anchor.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


ANCHOR = anchor_module()
STATE = canonical_state_module()


def read(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def latest(folder: Path, pattern: str) -> dict[str, Any] | None:
    files = sorted(folder.glob(pattern)); return read(files[-1]) if files else None


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _checklist_item(
    item_id: str, label: str, complete: bool, evidence: list[str], missing: str | None, action: str | None,
    requirement_ids: list[str],
) -> dict[str, Any]:
    """Build a read-only checklist row from facts, never a host assertion."""
    return {
        "item_id": item_id,
        "label": label,
        "status": "complete" if complete else "incomplete",
        "requirement_ids": requirement_ids,
        "evidence": evidence,
        "missing": missing,
        "next_action": action,
        "authority": "projection-only; saved artifacts remain authoritative",
    }


def _checklist(root: Path, run_id: str, directory: Path, anchor: dict[str, Any], checkpoint: dict[str, Any] | None,
               review: dict[str, Any] | None, gate: dict[str, Any] | None, completion: dict[str, Any] | None) -> dict[str, Any]:
    """Project closure readiness from stored artifacts without changing any state."""
    requirement_ids = [str(item.get("display_id")) for item in anchor.get("requirements", []) if item.get("display_id")]
    anchor_path = directory / "anchors" / "approved-v1.json"
    plan = directory / "planning" / "execution-handoff-v1.json"
    closure_paths = sorted((directory / "closure-records").glob("closure-*.json"))
    delivery_path = directory / "delivery-record.md"
    proof_commands = sorted({
        str(command) for requirement in anchor.get("requirements", [])
        for command in (requirement.get("validation_contract") or {}).get("commands", [])
        if isinstance(command, str) and command.strip()
    })
    scope_ready = all((requirement.get("scope_evidence") or {}).get("implementation_owners") for requirement in anchor.get("requirements", []))
    planned_proof = bool(proof_commands)
    validated = bool(checkpoint and review and gate and review.get("complete") and gate.get("complete"))
    closure_recorded = bool(closure_paths)
    completion_generated = completion is not None
    prefix = f"python3 scripts/tailtrail.py"
    items = [
        _checklist_item(
            "approved-plan", "Approved plan", anchor_path.is_file(), [_relative(root, anchor_path)] if anchor_path.is_file() else [],
            None if anchor_path.is_file() else "approved anchor", None if anchor_path.is_file() else f"{prefix} planning activate --root . --run-id {run_id} --approved", requirement_ids,
        ),
        _checklist_item(
            "resolved-scope", "Resolved implementation scope", scope_ready and plan.is_file(), [_relative(root, plan)] if plan.is_file() else [],
            None if scope_ready and plan.is_file() else "approved scope owners or execution handoff", None if scope_ready and plan.is_file() else f"{prefix} planning audit --root . --run-id {run_id}", requirement_ids,
        ),
        _checklist_item(
            "planned-proof", "Executable proof plan", planned_proof, proof_commands,
            None if planned_proof else "approved runnable proof command", None if planned_proof else f"{prefix} planning revise --root . --run-id {run_id} --changes '<proof update>' --approved-proposal", requirement_ids,
        ),
        _checklist_item(
            "validated-proof", "Recorded passing proof", validated,
            [_relative(root, directory / "checkpoints")] if checkpoint else [],
            None if validated else "complete checkpoint, completion review, and evidence gate", None if validated else (proof_commands[0] if proof_commands else f"{prefix} planning audit --root . --run-id {run_id}"), requirement_ids,
        ),
        _checklist_item(
            "completion-report", "Completion report", completion_generated,
            [_relative(root, directory / "completion-reports")] if completion_generated else [],
            None if completion_generated else "completion report", None if completion_generated else f"{prefix} completion-report --root . --run-id {run_id}", requirement_ids,
        ),
        _checklist_item(
            "closure-record", "Closure record", closure_recorded,
            [_relative(root, path) for path in closure_paths[-1:]],
            None if closure_recorded else "closure record", None if closure_recorded else f"{prefix} closure record --root . --run-id {run_id}", requirement_ids,
        ),
        _checklist_item(
            "delivery-record", "Delivery record", delivery_path.is_file(), [_relative(root, delivery_path)] if delivery_path.is_file() else [],
            None if delivery_path.is_file() else "delivery-record.md", None if delivery_path.is_file() else f"{prefix} closure finalize --root . --run-id {run_id}", requirement_ids,
        ),
    ]
    return {
        "type": "tailtrail-host-checklist",
        "run_id": run_id,
        "status": "complete" if all(item["status"] == "complete" for item in items) else "incomplete",
        "items": items,
        "boundary": "Derived only from saved local artifacts. Host assertions never complete an item.",
    }


def _base_dashboard(root: Path, run_id: str) -> dict[str, Any]:
    directory = L.state_dir(root, run_id)
    canonical_state = STATE.project(root, run_id)
    try:
        _, anchor = ANCHOR.latest_approved(root, run_id)
    except (OSError, ValueError):
        raise ValueError("an approved anchor is required for the workflow dashboard")
    checkpoint = latest(directory / "checkpoints", "checkpoint-*.json")
    review = latest(directory / "reviews", "review-*.json")
    gate = latest(directory / "completion-gates", "gate-*.json")
    completion = latest(directory / "completion-reports", "report-*.json")
    architecture = latest(directory / "architecture", "assessment-*.json")
    behaviour = latest(directory / "behavior", "assessment-*.json")
    maintainability = latest(directory / "maintainability", "assessment-*.json")
    official_design = latest(directory / "aidlc-official" / "checkpoints", "design-plan-*.json")
    failure_records = [read(path) for path in sorted((directory / "execution-failures").glob("failure-*.json"))]
    open_failures = [item for item in failure_records if item.get("status") != "resolved"]
    actual = {item.get("requirement_uid"): item for item in (checkpoint or {}).get("requirements", [])}
    rows = []
    for requirement in anchor.get("requirements", []):
        observed = actual.get(requirement["requirement_uid"], {})
        rows.append({"requirement_uid": requirement["requirement_uid"], "display_id": requirement.get("display_id"), "statement": requirement.get("statement"), "state": observed.get("state", "not-started"), "evidence_count": len(observed.get("evidence", []))})
    active = next((row for row in rows if row["state"] != "validated"), None)
    drift = (checkpoint or {}).get("drift", [])
    unresolved = [item for item in drift if item.get("classification") in {"new-drift", "regressed", "needs-decision", "unchanged"}]
    recovery = (directory / "recovery" / "boundary.json").is_file() or bool(list((directory / "recovery").glob("plan-*.json")))
    architecture_required = any(any((item.get("architecture_contract") or {}).get(key) for key in ("required_paths", "protected_paths", "forbidden_imports")) for item in anchor.get("requirements", []))

    def harness(name: str, artifact: dict[str, Any] | None, *, required: bool = False, basis: str) -> dict[str, Any]:
        if artifact is None:
            return {"name": name, "used": False, "status": "required-evidence-missing" if required else "not-selected", "basis": basis}
        return {"name": name, "used": True, "status": "pass" if artifact.get("complete") else "fail", "basis": basis}

    requirement_complete = bool(rows) and all(row["state"] == "validated" for row in rows) and bool(review) and bool(gate) and review.get("complete") and gate.get("complete")
    harnesses = [
        {"name": "Requirement Completion Harness", "used": bool(checkpoint or review or gate), "status": "pass" if requirement_complete else ("in-progress" if checkpoint else "required-evidence-missing"), "basis": "approved anchor + checkpoint + completion review + evidence gate"},
        harness("Architecture Fitness Harness", architecture, required=architecture_required, basis="approved architecture contract or recorded assessment"),
        harness("Behaviour Harness", behaviour, basis="recorded approved-scenario assessment"),
        harness("Maintainability Harness", maintainability, basis="recorded refactor/maintainability assessment"),
        harness("Evidence-Aware Testing", gate, required=True, basis="completion gate and validation receipts"),
    ]
    return {"schema_version": "1", "type": "tailtrail-workflow-dashboard", "run_id": run_id, "goal": anchor.get("goal", ""), "requirements": rows, "harnesses": harnesses, "official_perspectives": (official_design or {}).get("perspectives", []), "canonical_state": {"status": canonical_state["status"], "valid": canonical_state["valid"], "issues": canonical_state["issues"]}, "active_requirement": active, "checkpoint": (checkpoint or {}).get("checkpoint"), "completion_review": "pass" if (review or {}).get("complete") else ("fail" if review else "unavailable"), "evidence_gate": "pass" if (gate or {}).get("complete") else ("fail" if gate else "unavailable"), "drift": {"unresolved": unresolved, "status": "unresolved" if unresolved else ("none-unresolved" if checkpoint else "unavailable")}, "execution_failures": {"status": "none-recorded" if not failure_records else ("unresolved" if open_failures else "resolved"), "open": [{"failure_id": item.get("failure_id"), "requirement_uid": (item.get("requirement") or {}).get("requirement_uid"), "route": (item.get("correction_route") or {}).get("action")} for item in open_failures]}, "recovery": "available" if recovery else "not-configured", "completion": (completion or {}).get("overall_status", "not-generated"), "checklist": _checklist(root, run_id, directory, anchor, checkpoint, review, gate, completion), "boundary": "Read-only summary of saved local run artifacts. It does not run checks, edit source, apply recovery, or create a completion claim."}


def dashboard(root: Path, run_id: str) -> dict[str, Any]:
    """Add concise immutable planning history to the existing dashboard."""
    root = root.resolve()
    payload = _base_dashboard(root, run_id)
    directory = L.state_dir(root, run_id)
    state_path = directory / "planning" / "plan-revision-state-v1.json"
    state = read(state_path) if state_path.is_file() else {"active_revision": 1, "pending_revision": None}
    active_report = root / str(state.get("active_report", ""))
    report = read(active_report).get("report", {}) if active_report.is_file() else {}
    aidlc = report.get("aidlc_mode", {}) if isinstance(report, dict) else {}
    discussion_path = directory / "planning" / "discussion-receipts.jsonl"
    payload["planning"] = {
        "active_revision": state.get("active_revision", 1),
        "pending_revision": state.get("pending_revision"),
        "revision_history_count": len(list((directory / "planning" / "revisions").glob("revision-v*.json"))),
        "discussion_count": len([line for line in discussion_path.read_text(encoding="utf-8").splitlines() if line.strip()]) if discussion_path.is_file() else 0,
        "authority_route_count": len(list((directory / "planning" / "authority-routes").glob("route-*.json"))),
        "aidlc_mode": aidlc.get("mode", "lite") if isinstance(aidlc, dict) else "lite",
        "aidlc_state": aidlc.get("state", "not-selected") if isinstance(aidlc, dict) else "not-selected",
    }
    return payload


def parent_dashboard(root: Path, run_ids: list[str]) -> dict[str, Any]:
    """Aggregate only explicitly named child runs; never discover runs implicitly."""
    unique_ids = list(dict.fromkeys(run_ids))
    if len(unique_ids) < 2:
        raise ValueError("a parent dashboard requires at least two explicit --run-id values")
    children = [dashboard(root, run_id) for run_id in unique_ids]
    incomplete = [child["run_id"] for child in children if child["checklist"]["status"] != "complete"]
    return {
        "schema_version": "1",
        "type": "tailtrail-workflow-parent-dashboard",
        "run_ids": unique_ids,
        "status": "complete" if not incomplete else "incomplete",
        "children": [{
            "run_id": child["run_id"], "goal": child["goal"], "status": child["checklist"]["status"],
            "checklist": child["checklist"],
        } for child in children],
        "incomplete_run_ids": incomplete,
        "boundary": "Aggregates only explicitly supplied run IDs and reads their saved artifacts without mutation.",
    }


def markdown(payload: dict[str, Any]) -> str:
    if payload["type"] == "tailtrail-workflow-parent-dashboard":
        lines = ["# TailTrail Parent Workflow Checklist", "", f"Runs: {', '.join(f'`{run_id}`' for run_id in payload['run_ids'])}", f"Status: **{payload['status']}**", "", "| Run | Status | Next action |", "| --- | --- | --- |"]
        for child in payload["children"]:
            pending = next((item for item in child["checklist"]["items"] if item["status"] != "complete"), None)
            lines.append(f"| `{child['run_id']}` | {child['status']} | {pending['next_action'] if pending else 'none'} |")
        return "\n".join(lines) + "\n"
    active = payload["active_requirement"]
    lines = ["# TailTrail Workflow Dashboard", "", f"Run: `{payload['run_id']}`", f"Goal: {payload['goal'] or 'not recorded'}", "", f"Active requirement: **{active['display_id']} — {active['statement']}**" if active else "Active requirement: **none; all checkpoint requirements validated**", f"Canonical state: **{payload['canonical_state']['status']}**", f"Checkpoint: **{payload['checkpoint'] or 'none'}**", f"Completion review: **{payload['completion_review']}**", f"Evidence gate: **{payload['evidence_gate']}**", f"Drift: **{payload['drift']['status']}**", f"Recovery: **{payload['recovery']}**", f"Completion report: **{payload['completion']}**", "", "| Requirement | State | Evidence |", "| --- | --- | ---: |", *[f"| {row['display_id']} — {row['statement']} | {row['state']} | {row['evidence_count']} |" for row in payload["requirements"]]]
    harness_index = lines.index("| Requirement | State | Evidence |")
    planning = payload.get("planning", {})
    lines[harness_index:harness_index] = [
        "## Interactive plan history", "",
        f"- Active revision: `{planning.get('active_revision', 1)}`",
        f"- Pending revision: `{planning.get('pending_revision') or 'none'}`",
        f"- Saved revisions: `{planning.get('revision_history_count', 0)}`",
        f"- Saved discussions: `{planning.get('discussion_count', 0)}`",
        f"- AIDLC / Intent Bridge authority routes: `{planning.get('authority_route_count', 0)}`", "",
        f"- AIDLC mode: `{planning.get('aidlc_mode', 'lite')}` ({planning.get('aidlc_state', 'not-selected')})", "",
        "## Harness usage", "", "| Harness | Used | Status | Selection / evidence basis |",
        "| --- | --- | --- | --- |",
        *[f"| {item['name']} | {'yes' if item['used'] else 'no'} | {item['status']} | {item['basis']} |" for item in payload["harnesses"]], "",
    ]
    if payload["official_perspectives"]:
        lines[harness_index:harness_index] = ["## Official AI-DLC perspectives", "", "| Perspective | Status | Reason |", "| --- | --- | --- |", *[f"| {item['perspective']} | {item['status']} | {item['reason']} |" for item in payload["official_perspectives"]], ""]
    checklist = payload["checklist"]
    lines.extend(["", "## Host checklist", "", f"Status: **{checklist['status']}**", "", "| Item | Status | Evidence / missing artifact | Next action |", "| --- | --- | --- | --- |"])
    for item in checklist["items"]:
        evidence = ", ".join(f"`{value}`" for value in item["evidence"]) or item["missing"] or "-"
        lines.append(f"| {item['label']} | {item['status']} | {evidence} | {item['next_action'] or '-'} |")
    return "\n".join(lines) + "\n"


def _legacy_html_page(payload: dict[str, Any]) -> str:
    cards = [("Active requirement", f"{payload['active_requirement']['display_id']} — {payload['active_requirement']['statement']}" if payload["active_requirement"] else "All checkpoint requirements validated"), ("Checkpoint", str(payload["checkpoint"] or "none")), ("Completion review", payload["completion_review"]), ("Evidence gate", payload["evidence_gate"]), ("Drift", payload["drift"]["status"]), ("Recovery", payload["recovery"]), ("Completion report", payload["completion"])]
    card_html = "".join(f"<section><h2>{html.escape(label)}</h2><p>{html.escape(value)}</p></section>" for label, value in cards)
    rows = "".join(f"<tr><td>{html.escape(str(row['display_id']))}</td><td>{html.escape(str(row['statement']))}</td><td>{html.escape(str(row['state']))}</td><td>{row['evidence_count']}</td></tr>" for row in payload["requirements"])
    return f"<!doctype html><html><head><meta charset='utf-8'><title>TailTrail Workflow Dashboard</title><style>body{{font-family:system-ui;margin:2rem;background:#10151f;color:#eef3fb}}section{{background:#1a2332;padding:1rem;border-radius:.5rem}}main{{max-width:1100px;margin:auto}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1rem}}h1{{color:#74d4ff}}table{{width:100%;border-collapse:collapse;margin-top:1rem}}td,th{{padding:.6rem;border-bottom:1px solid #34445e;text-align:left}}</style></head><body><main><h1>TailTrail Workflow Dashboard</h1><p>Run: <code>{html.escape(payload['run_id'])}</code></p><p>{html.escape(payload['goal'])}</p><div class='cards'>{card_html}</div><table><thead><tr><th>ID</th><th>Requirement</th><th>State</th><th>Evidence</th></tr></thead><tbody>{rows}</tbody></table></main></body></html>"


def html_page(payload: dict[str, Any]) -> str:
    cards = [
        ("Active requirement", f"{payload['active_requirement']['display_id']} â€” {payload['active_requirement']['statement']}" if payload["active_requirement"] else "All checkpoint requirements validated"),
        ("Canonical state", payload["canonical_state"]["status"]),
        ("Checkpoint", str(payload["checkpoint"] or "none")),
        ("Completion review", payload["completion_review"]),
        ("Evidence gate", payload["evidence_gate"]),
        ("Drift", payload["drift"]["status"]),
        ("Recovery", payload["recovery"]),
        ("Completion report", payload["completion"]),
    ]
    card_html = "".join(f"<section><h2>{html.escape(label)}</h2><p>{html.escape(value)}</p></section>" for label, value in cards)
    harness_rows = "".join(f"<tr><td>{html.escape(item['name'])}</td><td>{'yes' if item['used'] else 'no'}</td><td>{html.escape(item['status'])}</td><td>{html.escape(item['basis'])}</td></tr>" for item in payload["harnesses"])
    requirement_rows = "".join(f"<tr><td>{html.escape(str(row['display_id']))}</td><td>{html.escape(str(row['statement']))}</td><td>{html.escape(str(row['state']))}</td><td>{row['evidence_count']}</td></tr>" for row in payload["requirements"])
    return f"<!doctype html><html><head><meta charset='utf-8'><title>TailTrail Workflow Dashboard</title><style>body{{font-family:system-ui;margin:2rem;background:#10151f;color:#eef3fb}}section{{background:#1a2332;padding:1rem;border-radius:.5rem}}main{{max-width:1100px;margin:auto}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1rem}}h1{{color:#74d4ff}}table{{width:100%;border-collapse:collapse;margin-top:1rem}}td,th{{padding:.6rem;border-bottom:1px solid #34445e;text-align:left}}</style></head><body><main><h1>TailTrail Workflow Dashboard</h1><p>Run: <code>{html.escape(payload['run_id'])}</code></p><p>{html.escape(payload['goal'])}</p><div class='cards'>{card_html}</div><h2>Harness usage</h2><table><thead><tr><th>Harness</th><th>Used</th><th>Status</th><th>Selection / evidence basis</th></tr></thead><tbody>{harness_rows}</tbody></table><h2>Requirements</h2><table><thead><tr><th>ID</th><th>Requirement</th><th>State</th><th>Evidence</th></tr></thead><tbody>{requirement_rows}</tbody></table></main></body></html>"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd()); parser.add_argument("--run-id", action="append", required=True)
    parser.add_argument("--format", choices=("markdown", "json", "html"), default="markdown"); parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = dashboard(args.root.resolve(), args.run_id[0]) if len(args.run_id) == 1 else parent_dashboard(args.root.resolve(), args.run_id)
        output = json.dumps(payload, indent=2, sort_keys=True) if args.format == "json" else (html_page(payload) if args.format == "html" else markdown(payload))
        if args.output: args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(output, encoding="utf-8")
        print(output)
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Workflow dashboard error: {error}"); return 2


if __name__ == "__main__": raise SystemExit(main())
