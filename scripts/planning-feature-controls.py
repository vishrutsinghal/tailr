#!/usr/bin/env python3
"""Versioned Expert Plan Customization for an awaiting TailTrail Planning Lock."""
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
BOUNDARY = "Expert Plan Customization changes only versioned TailTrail planning metadata. It never inspects source, runs project commands, or permits implementation before the resulting plan is approved."
LOCKED = {"navigator", "tailtrail navigator", "canonical requirements", "requirement completion harness", "evidence-aware testing"}
KNOWN = {"architecture fitness harness", "behaviour harness", "maintainability harness", "higher-tier testing", "context continuity harness", "safe git recovery", "code review graph lite", "code graph mapper", "token harness", "aidlc"}


def module(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    loaded = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(loaded); return loaded


LOCK = module("expert_controls_lock", "planning-lock.py")
LEDGER = module("expert_controls_ledger", "run-ledger.py")
OFFICIAL_BRIDGE = module("expert_controls_official_bridge", "aidlc-official-bridge.py")


def now() -> str: return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def canonical(value: Any) -> str: return json.dumps(value, sort_keys=True, separators=(",", ":"))
def fingerprint(value: Any) -> str: return "sha256:" + hashlib.sha256(canonical(value).encode()).hexdigest()
def path(root: Path, run_id: str, revision: int) -> Path: return LEDGER.state_dir(root, run_id) / "planning" / "revisions" / f"revision-v{revision}.json"
def report_path(root: Path, run_id: str, revision: int) -> Path: return LEDGER.state_dir(root, run_id) / "planning" / "revisions" / f"start-report-v{revision}.json"


def _rows(container: Any) -> list[dict[str, Any]]: return [item for item in container if isinstance(item, dict) and isinstance(item.get("name"), str)] if isinstance(container, list) else []


def inventory(report: dict[str, Any]) -> list[dict[str, Any]]:
    navigator = report.get("navigator") if isinstance(report.get("navigator"), dict) else {}
    delivery = report.get("guided_delivery") if isinstance(report.get("guided_delivery"), dict) else {}
    states: dict[str, str] = {}
    labels: dict[str, str] = {}
    for state, rows in (("selected", _rows(navigator.get("selected_features"))), ("selected", _rows(delivery.get("selected"))), ("armed", _rows(navigator.get("skipped_features"))), ("armed", _rows(delivery.get("activated_later")))):
        for row in rows:
            key = row["name"].strip().lower(); labels.setdefault(key, row["name"]); states.setdefault(key, state)
    for key in KNOWN: labels.setdefault(key, "AIDLC" if key == "aidlc" else key.title()); states.setdefault(key, "available")
    aidlc = report.get("aidlc_mode") if isinstance(report.get("aidlc_mode"), dict) else {}
    result = []
    for key in sorted(labels):
        value = str((aidlc.get("mode") if key == "aidlc" else states[key]) or "lite")
        result.append({"feature_id": key.replace(" ", "-"), "name": labels[key], "control": "choice" if key == "aidlc" else "state", "current": value, "allowed": ["lite", "standard"] if key == "aidlc" else ([] if key in LOCKED else ["selected", "armed", "disabled"]), "locked": key in LOCKED, "reason": "core planning/evidence safeguard" if key in LOCKED else "Navigator recommendation may be customized before approval"})
    return result


def show(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve(); LOCK.assert_discussion_allowed(root, run_id)
    report = LOCK.active_start_report(root, run_id).get("report", {})
    return {"schema_version": "1", "type": "tailtrail-expert-plan-controls", "run_id": run_id, "controls": inventory(report if isinstance(report, dict) else {}), "boundary": BOUNDARY}


def _text(value: Any, field: str) -> str:
    value = str(value or "").strip()
    if not value or len(value) > 500 or "\x00" in value: raise ValueError(f"feature control needs bounded `{field}`")
    return value


def _set_rows(target: dict[str, Any], name: str, state: str, reason: str) -> None:
    navigator = target.setdefault("navigator", {}); delivery = target.setdefault("guided_delivery", {})
    for key in ("selected_features", "skipped_features"):
        values = _rows(navigator.get(key)); navigator[key] = [row for row in values if row["name"].lower() != name.lower()]
    for key in ("selected", "activated_later"):
        values = _rows(delivery.get(key)); delivery[key] = [row for row in values if row["name"].lower() != name.lower()]
    if state == "selected":
        navigator["selected_features"].append({"name": name, "why": f"user-approved Expert Plan Customization: {reason}"})
        delivery["selected"].append({"name": name, "why": f"user-approved Expert Plan Customization: {reason}"})
    elif state == "armed":
        navigator["skipped_features"].append({"name": name, "why": f"armed by user-approved Expert Plan Customization: {reason}"})
        delivery["activated_later"].append({"name": name, "when": f"armed by user-approved Expert Plan Customization: {reason}"})
    else:
        navigator["skipped_features"].append({"name": name, "why": f"disabled by user-approved Expert Plan Customization: {reason}"})


def propose(root: Path, run_id: str, changes: list[dict[str, Any]], approved_proposal: bool) -> dict[str, Any]:
    if approved_proposal is not True: raise ValueError("feature-control proposal requires --approved-proposal")
    root = root.resolve(); LOCK.assert_discussion_allowed(root, run_id); state = LOCK.revision_state(root, run_id)
    if state.get("pending_revision") is not None: raise ValueError("a plan revision is already awaiting approval")
    saved = LOCK.active_start_report(root, run_id); report = copy.deepcopy(saved.get("report"))
    if not isinstance(report, dict) or not isinstance(changes, list) or not changes: raise ValueError("feature controls require a non-empty JSON change list")
    choices = {item["name"].lower(): item for item in inventory(report)}; normalized = []
    for raw in changes:
        if not isinstance(raw, dict): raise ValueError("each feature control must be an object")
        name, value, reason = _text(raw.get("feature"), "feature"), _text(raw.get("value"), "value").lower(), _text(raw.get("reason"), "reason")
        item = choices.get(name.lower())
        if not item: raise ValueError(f"unknown TailTrail feature `{name}`; run feature-controls-show first")
        if item["locked"]: raise ValueError(f"`{item['name']}` is a locked core safeguard and cannot be disabled or changed")
        if value not in item["allowed"]: raise ValueError(f"`{item['name']}` allows only: {', '.join(item['allowed'])}")
        if item["control"] == "choice":
            if value != "standard": raise ValueError("Expert Plan Customization currently supports only Lite-to-Standard AIDLC; start a new explicit Full AIDLC run for Full mode")
            report["aidlc_mode"] = {"mode": "standard", "selection": "expert-plan-customization-proposal", "state": "awaiting-mode-approval", "boundary": "Standard requirements begin only after this exact customization revision is approved."}
        else: _set_rows(report, item["name"], value, reason)
        normalized.append({"feature": item["name"], "control": item["control"], "value": value, "reason": reason})
    number = int(state.get("active_revision", 1)) + 1
    proposal = {"schema_version": "1", "type": "tailtrail-expert-plan-customization", "run_id": run_id, "revision": number, "base_revision": int(state.get("active_revision", 1)), "state": "awaiting-approval", "changes": normalized, "approval_required": True, "base_report_fingerprint": fingerprint(saved.get("report", {})), "revised_report_fingerprint": fingerprint(report), "boundary": BOUNDARY, "created_at": now(), "proposed_report": report}
    destination = path(root, run_id, number)
    with LEDGER.RunLock(LEDGER.state_dir(root, run_id) / ".lock"):
        LEDGER.atomic_json(destination, proposal); LEDGER.atomic_json(LOCK.revision_state_path(root, run_id), {**state, "pending_revision": number, "pending_artifact": destination.relative_to(root).as_posix()})
    LEDGER.append_event(root, run_id, "planning_feature_controls_proposed", {"revision": number, "artifact": destination.relative_to(root).as_posix(), "features": [item["feature"] for item in normalized]})
    return {**proposal, "artifact": destination.relative_to(root).as_posix()}


def approve(root: Path, run_id: str, revision: int, approved: bool) -> dict[str, Any]:
    if approved is not True: raise ValueError("feature-control approval requires --approved")
    root = root.resolve(); LOCK.assert_discussion_allowed(root, run_id); state = LOCK.revision_state(root, run_id)
    if state.get("pending_revision") != revision: raise ValueError("this is not the current pending feature-control revision")
    proposed = json.loads(path(root, run_id, revision).read_text(encoding="utf-8"))
    if proposed.get("type") != "tailtrail-expert-plan-customization" or proposed.get("revised_report_fingerprint") != fingerprint(proposed.get("proposed_report", {})): raise ValueError("feature-control revision is invalid")
    report = proposed["proposed_report"]; output = report_path(root, run_id, revision); snapshot = {"schema_version": "1", "type": "tailtrail-start-report", "run_id": run_id, "revision": revision, "goal": report.get("goal", ""), "report": report}
    with LEDGER.RunLock(LEDGER.state_dir(root, run_id) / ".lock"):
        LEDGER.atomic_json(output, snapshot); LEDGER.atomic_json(LOCK.revision_state_path(root, run_id), {**state, "active_revision": revision, "active_report": output.relative_to(root).as_posix(), "pending_revision": None, "pending_artifact": None})
    standard = any(item["feature"].lower() == "aidlc" and item["value"] == "standard" for item in proposed["changes"])
    if standard:
        preflight = OFFICIAL_BRIDGE.preflight(root, "standard")
        if preflight["mode"] != "standard":
            report["aidlc_mode"] = {"mode": "lite", "requested_mode": "standard", "selection": "expert-plan-customization-approved", "state": preflight["state"], "boundary": preflight["boundary"]}
            LEDGER.atomic_json(output, {**snapshot, "report": report})
            result = {"state": "tailtrail-lite-fallback", "aidlc_mode": report["aidlc_mode"]}
        else:
            report["aidlc_mode"]["state"] = "official-host-requirements-pending"
            report["official_aidlc_bridge"] = OFFICIAL_BRIDGE.create(root, run_id, str(report.get("goal", "")), mode="standard")
            LEDGER.atomic_json(output, {**snapshot, "report": report})
            requirements = LOCK.request_official_aidlc_requirements(root, run_id); report["aidlc_requirements"] = requirements; LEDGER.atomic_json(output, {**snapshot, "report": report}); result = {"state": requirements["state"], "aidlc_requirements": requirements}
    else: result = {"state": "execution-ready", **LOCK.activate(root, run_id, True)}
    LEDGER.append_event(root, run_id, "planning_feature_controls_approved", {"revision": revision, "artifact": proposed["artifact"] if "artifact" in proposed else output.relative_to(root).as_posix(), "features": [item["feature"] for item in proposed["changes"]]})
    return {"run_id": run_id, "revision": revision, "changes": proposed["changes"], "active_report": output.relative_to(root).as_posix(), **result}


def render(payload: dict[str, Any]) -> str:
    lines = ["# TailTrail Expert Plan Customization", "", f"**Run ID:** `{payload['run_id']}`", f"**Revision:** v{payload['base_revision']} -> v{payload['revision']}", "**State:** awaiting approval — no project source, tests, scanners, Git, or implementation commands were run.", "", "## Requested controls", "", "| Feature | Setting | Reason |", "| --- | --- | --- |", *[f"| {row['feature']} | {row['value']} | {row['reason']} |" for row in payload['changes']], "", "## Approval", "", f"- Approve exactly v{payload['revision']} to apply these feature choices to this same plan.", "- A Standard AIDLC choice starts requirements gathering only; its separate requirement approval still blocks implementation.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    for command in ("show", "propose", "approve"):
        item = sub.add_parser(command); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True)
        if command == "propose": item.add_argument("--changes", required=True); item.add_argument("--approved-proposal", action="store_true")
        if command == "approve": item.add_argument("--revision", type=int, required=True); item.add_argument("--approved", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "show": print(json.dumps(show(args.root, args.run_id), indent=2, sort_keys=True))
        elif args.command == "propose": print(render(propose(args.root, args.run_id, json.loads(args.changes), args.approved_proposal)))
        else:
            result = approve(args.root, args.run_id, args.revision, args.approved)
            print(LOCK.render_aidlc_requirements(result["aidlc_requirements"]) if result["state"] in {"aidlc-requirements-gathering", "official-aidlc-host-generation-required", "official-aidlc-requirements-gathering"} else (json.dumps(result, indent=2, sort_keys=True) if result["state"] == "tailtrail-lite-fallback" else LOCK.render_execution_handoff(result.get("execution_handoff", result))))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error: print(f"Expert Plan Customization error: {error}"); return 2


if __name__ == "__main__": raise SystemExit(main())
