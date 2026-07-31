#!/usr/bin/env python3
"""Render and calibrate deterministic Context Continuity artifacts."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRIGGERS = {
    "implementation-start", "correction-cycle", "unexpected-scope",
    "test-integrity", "recovery", "feature-transition", "proposal-rejection",
}
DELTAS = {"resolved", "improved", "unchanged", "regressed", "new-drift", "needs-decision"}
ASSESSMENTS = {"useful", "not-useful", "unknown"}
UNCERTAINTIES = {"inferred", "uncertain"}
FORBIDDEN_ADVISORY_TERMS = re.compile(r"\b(edit|write|modify|apply|patch|run|test|command|commit|push|approve|amend|deploy)\b", re.IGNORECASE)


def ledger():
    spec = importlib.util.spec_from_file_location("continuity_ledger", ROOT / "scripts" / "run-ledger.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


L = ledger()


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest(directory: Path, pattern: str) -> tuple[Path | None, dict[str, Any] | None]:
    files = sorted(directory.glob(pattern))
    return (files[-1], read(files[-1])) if files else (None, None)


def rel(root: Path, path: Path | None) -> str | None:
    return path.relative_to(root).as_posix() if path else None


def compact(text: str, limit: int) -> str:
    values = text.split()
    return " ".join(values[:limit]) + (" ..." if len(values) > limit else "")


def load_policy(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    policy = read(path)
    if policy.get("type") != "tailtrail-context-continuity-policy" or policy.get("schema_version") != "1":
        raise ValueError("policy must be a Context Continuity policy schema version 1")
    if not isinstance(policy.get("version"), str) or not policy["version"].strip():
        raise ValueError("policy version is required")
    if "max_words" in policy and (not isinstance(policy["max_words"], int) or policy["max_words"] < 80):
        raise ValueError("policy max_words must be an integer of at least 80")
    templates = policy.get("templates", [])
    if not isinstance(templates, list):
        raise ValueError("policy templates must be a list")
    for template in templates:
        if not isinstance(template, dict) or not isinstance(template.get("id"), str):
            raise ValueError("each template requires an id")
        for field in ("triggers", "path_prefixes", "additional_guidance"):
            if field in template and (not isinstance(template[field], list) or not all(isinstance(x, str) for x in template[field])):
                raise ValueError(f"template {template['id']} field {field} must be a string list")
        if "max_words" in template and (not isinstance(template["max_words"], int) or template["max_words"] < 80):
            raise ValueError(f"template {template['id']} max_words must be at least 80")
    return policy


def select_template(requirement: dict[str, Any], trigger: str, policy: dict[str, Any] | None) -> dict[str, Any] | None:
    if not policy:
        return None
    paths = requirement.get("likely_paths", [])
    for template in policy.get("templates", []):
        triggers = template.get("triggers", [])
        prefixes = template.get("path_prefixes", [])
        if triggers and trigger not in triggers:
            continue
        if prefixes and not any(any(path.startswith(prefix) for prefix in prefixes) for path in paths):
            continue
        return template
    return None


def load_selector_policy(path: Path) -> dict[str, Any]:
    policy = read(path)
    if policy.get("type") != "tailtrail-context-continuity-selector-policy" or policy.get("schema_version") != "1":
        raise ValueError("selector policy must be a Context Continuity selector policy schema version 1")
    if policy.get("enabled") is not True or policy.get("approved") is not True:
        raise ValueError("selector policy must set enabled and approved to true")
    if not isinstance(policy.get("version"), str) or not policy["version"].strip():
        raise ValueError("selector policy version is required")
    if not isinstance(policy.get("model"), str) or not policy["model"].strip():
        raise ValueError("selector policy model label is required")
    maximum = policy.get("max_reminder_words", 80)
    if not isinstance(maximum, int) or maximum < 20 or maximum > 120:
        raise ValueError("selector max_reminder_words must be between 20 and 120")
    return policy


def packet_for(root: Path, run: str, uid: str | None, trigger: str | None, max_words: int,
               policy: dict[str, Any] | None = None) -> dict[str, Any]:
    directory = L.state_dir(root, run)
    anchor_path = directory / "anchors" / "approved-v1.json"
    rejection = trigger == "proposal-rejection"
    if not anchor_path.is_file() and not rejection:
        raise ValueError("approved anchor is required")
    if rejection:
        draft_path, draft = latest(directory / "anchors", "draft-v*.json")
        if not draft_path or not draft:
            raise ValueError("proposal-rejection requires a draft anchor")
        anchor_path, anchor = draft_path, draft
    else:
        anchor = read(anchor_path)
    feedback_path, feedback = latest(directory / "feedback", "feedback-*.json")
    review_path, review = latest(directory / "reviews", "review-*.json")
    checkpoint_path, checkpoint = latest(directory / "checkpoints", "checkpoint-*.json")
    impact_path, impact = latest(directory / "impact-maps", "map-*.json")
    correction = feedback.get("packet") if feedback else None
    selected_uid = uid or (correction or {}).get("requirement_uid")
    if not selected_uid:
        raise ValueError("--requirement-uid is required when no correction packet selects one")
    requirement = next((item for item in anchor["requirements"] if item["requirement_uid"] == selected_uid), None)
    if not requirement:
        raise ValueError("requirement_uid is not approved")
    if trigger and trigger not in TRIGGERS:
        raise ValueError("unsupported trigger")
    drift = [item for item in (checkpoint or {}).get("drift", []) if item.get("requirement_uid") == selected_uid]
    automatic = "correction-cycle" if correction else ("unexpected-scope" if any(item.get("classification") == "new-drift" for item in drift) else "implementation-start")
    active_trigger = trigger or automatic
    template = select_template(requirement, active_trigger, policy)
    budget = min(max_words, policy.get("max_words", max_words) if policy else max_words,
                 template.get("max_words", max_words) if template else max_words)
    pointers = [{"kind": "approved-anchor", "path": rel(root, anchor_path)}]
    program_path = directory / "program" / "state.json"
    for kind, path in (("impact-map", impact_path), ("checkpoint", checkpoint_path),
                       ("completion-review", review_path), ("feedback", feedback_path),
                       ("program-state", program_path if program_path.is_file() else None)):
        if path:
            pointers.append({"kind": kind, "path": rel(root, path)})
    previous_gap = (correction or {}).get("evidence") or next(
        (item.get("message", "") for item in (review or {}).get("findings", []) if item.get("requirement_uid") == selected_uid), "")
    next_action = (correction or {}).get("next_validation") or (
        "Inspect the approved paths and add the minimum focused proof."
        if active_trigger == "implementation-start" else "Resolve the cited evidence gap, then rerun focused proof.")
    no_repeat: list[str] = []
    if active_trigger == "correction-cycle" and previous_gap:
        no_repeat.append("Do not repeat the prior incomplete approach; address the cited evidence gap.")
    if active_trigger == "unexpected-scope":
        no_repeat.append("Do not expand scope without an approved anchor amendment.")
    sections = [
        f"Active requirement: {requirement['display_id']} - {requirement['statement']}", "Approved outcome:",
        *[f"- {item}" for item in requirement.get("acceptance_criteria", [])], "Current scope:",
        *[f"- {item}" for item in requirement.get("likely_paths", [])], "Must preserve:",
        *[f"- {item}" for item in requirement.get("preserve_rules", [])],
    ]
    selected_fields = ["requirement", "acceptance_criteria", "likely_paths", "preserve_rules", "artifact_pointers", "next_action"]
    if previous_gap:
        sections.extend(["Previous iteration gap:", f"- {previous_gap}"])
        selected_fields.append("previous_gap")
    if no_repeat:
        sections.extend(["Do not repeat:", *[f"- {item}" for item in no_repeat]])
        selected_fields.append("do_not_repeat")
    if active_trigger == "feature-transition" and program_path.is_file():
        program = read(program_path)
        active = next((item for item in program.get("features", []) if item.get("state") == "active"), None)
        completed = [item.get("id") for item in program.get("features", []) if item.get("state") == "validated"]
        sections.extend(["Program context:", f"- Active feature: {active.get('id') if active else 'none'}", f"- Completed features: {', '.join(completed) if completed else 'none'}"])
        selected_fields.append("program_context")
    if active_trigger == "proposal-rejection":
        events = [item for item in L.read_events(directory / "events.jsonl") if item.get("event_type") == "proposal_rejected"]
        feedback_row = next((item for event in reversed(events) for item in event.get("payload", {}).get("feedback", []) if item.get("requirement_uid") == selected_uid), {})
        sections.extend(["Requirement feedback:", f"- {feedback_row.get('comment', 'Review the rejected requirement before revising it.')} "])
        selected_fields.append("requirement_feedback")
    if template and template.get("additional_guidance"):
        sections.extend(["Project continuity guidance:", *[f"- {item}" for item in template["additional_guidance"]]])
        selected_fields.append("project_template_guidance")
    sections.extend(["Use prior context:", *[f"- {item['path']}" for item in pointers], "Next smallest action:", f"- {next_action}"])
    markdown = compact("\n".join(sections), budget)
    state = {
        "schema_version": "1", "type": "tailtrail-context-continuity-state", "run_id": run,
        "trigger": active_trigger, "requirement_uid": selected_uid,
        "anchor_fingerprint": anchor.get("approved_fingerprint"),
        "checkpoint": checkpoint.get("checkpoint") if checkpoint else None,
        "previous_delta": drift[-1].get("classification") if drift else None,
        "selected_artifacts": pointers, "selected_fields": selected_fields,
        "omitted_fields": ["deep_history"], "policy_version": policy.get("version") if policy else "v1-default",
        "selected_template_id": template.get("id") if template else None, "packet_budget_words": budget,
        "do_not_repeat": no_repeat, "next_action": next_action,
        "packet_fingerprint": "sha256:" + hashlib.sha256(markdown.encode()).hexdigest(),
        "evidence_label": "local-evidence",
    }
    return {"state": state, "packet_markdown": markdown}


def render(root: Path, run: str, uid: str | None, trigger: str | None, max_words: int,
           policy_path: Path | None = None) -> dict[str, Any]:
    if max_words < 80:
        raise ValueError("max words must be at least 80")
    policy = load_policy(policy_path)
    result = packet_for(root, run, uid, trigger, max_words, policy)
    directory = L.state_dir(root, run) / "continuity"
    number = len(list(directory.glob("state-*.json"))) + 1
    state_path, packet_path = directory / f"state-{number}.json", directory / f"packet-{number}.md"
    receipt_path = directory / "interventions" / f"intervention-{number}.json"
    state = {"sequence": number, **result["state"], "intervention_receipt": rel(root, receipt_path)}
    receipt = {
        "schema_version": "1", "type": "tailtrail-context-continuity-intervention", "run_id": run,
        "packet_sequence": number, "trigger": state["trigger"], "requirement_uid": state["requirement_uid"],
        "policy_version": state["policy_version"], "selected_template_id": state["selected_template_id"],
        "words": len(result["packet_markdown"].split()), "selected_fields": state["selected_fields"],
        "omitted_fields": state["omitted_fields"], "next_checkpoint_delta": None, "assessment": "unknown",
        "evidence_label": "local-evidence",
    }
    L.atomic_json(state_path, state)
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(result["packet_markdown"] + "\n", encoding="utf-8")
    L.atomic_json(receipt_path, receipt)
    L.append_event(root, run, "context_continuity_rendered", {
        "artifact": rel(root, state_path), "packet": rel(root, packet_path), "receipt": rel(root, receipt_path),
        "trigger": state["trigger"], "requirement_uid": state["requirement_uid"], "policy_version": state["policy_version"],
    })
    return {"state_path": state_path.as_posix(), "packet_path": packet_path.as_posix(), "receipt_path": receipt_path.as_posix(), "packet_markdown": result["packet_markdown"], **state}


def show(root: Path, run: str, sequence: int | None) -> dict[str, Any]:
    directory = L.state_dir(root, run) / "continuity"
    path = directory / f"state-{sequence}.json" if sequence else latest(directory, "state-*.json")[0]
    if not path or not path.is_file():
        raise ValueError("no continuity state exists")
    state = read(path)
    packet = path.with_name(path.name.replace("state-", "packet-")).with_suffix(".md")
    return {"state_path": path.as_posix(), "packet_path": packet.as_posix(), "packet_markdown": packet.read_text(encoding="utf-8") if packet.is_file() else "", **state}


def calibrate(root: Path, run: str, input_path: Path) -> dict[str, Any]:
    data = read(input_path)
    rows = data.get("interventions")
    if not isinstance(rows, list):
        raise ValueError("calibration input requires an interventions list")
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("packet_sequence"), int):
            raise ValueError("each intervention requires packet_sequence")
        if row.get("next_checkpoint_delta", "needs-decision") not in DELTAS:
            raise ValueError("intervention next_checkpoint_delta is invalid")
        if row.get("assessment", "unknown") not in ASSESSMENTS:
            raise ValueError("intervention assessment is invalid")
    count = len(rows)
    outcomes = Counter(str(row.get("next_checkpoint_delta", "needs-decision")) for row in rows)
    assessments = Counter(str(row.get("assessment", "unknown")) for row in rows)
    word_values = [int(row.get("words", 0)) for row in rows if isinstance(row.get("words", 0), int)]
    report = {
        "schema_version": "1", "type": "tailtrail-context-continuity-calibration", "run_id": run,
        "input": rel(root, input_path), "intervention_count": count,
        "average_packet_words": round(sum(word_values) / len(word_values), 2) if word_values else 0,
        "outcomes": dict(sorted(outcomes.items())), "assessments": dict(sorted(assessments.items())),
        "resolved_or_improved": outcomes["resolved"] + outcomes["improved"],
        "false_interventions": assessments["not-useful"],
        "missed_interventions": int(data.get("missed_interventions", 0)),
        "evidence_label": "local-evidence",
        "interpretation": "Association from saved local artifacts only; this report does not establish causality.",
    }
    directory = L.state_dir(root, run) / "continuity" / "calibration"
    number = len(list(directory.glob("calibration-*.json"))) + 1
    output_path = directory / f"calibration-{number}.json"
    L.atomic_json(output_path, report)
    L.append_event(root, run, "context_continuity_calibrated", {"artifact": rel(root, output_path), "intervention_count": count})
    return {"artifact": output_path.as_posix(), **report}


def validate_proposal(root: Path, proposal: dict[str, Any], state: dict[str, Any], policy: dict[str, Any]) -> tuple[bool, str]:
    allowed = {"intervene", "requirement_uid", "reason", "artifact_pointers", "reminder", "uncertainty", "authority", "model"}
    unexpected = set(proposal) - allowed
    if unexpected:
        return False, "proposal includes forbidden fields"
    if not isinstance(proposal.get("intervene"), bool):
        return False, "proposal intervene must be boolean"
    if proposal.get("requirement_uid") != state["requirement_uid"]:
        return False, "proposal requirement_uid does not match selected state"
    if proposal.get("authority") != "advisory-only":
        return False, "proposal authority must be advisory-only"
    if proposal.get("model") != policy["model"]:
        return False, "proposal model does not match the approved selector policy"
    if proposal.get("uncertainty") not in UNCERTAINTIES:
        return False, "proposal uncertainty is invalid"
    pointers = proposal.get("artifact_pointers", [])
    allowed_pointers = {item["path"] for item in state.get("selected_artifacts", [])}
    if not isinstance(pointers, list) or not all(isinstance(item, str) and item in allowed_pointers for item in pointers):
        return False, "proposal artifact pointers are not in the V1/V2 allowlist"
    if any(not (root / item).is_file() for item in pointers):
        return False, "proposal artifact pointer no longer exists locally"
    if not proposal["intervene"]:
        if proposal.get("reminder") not in {None, ""}:
            return False, "silent proposal cannot contain a reminder"
        return True, "silent"
    reason, reminder = proposal.get("reason"), proposal.get("reminder")
    if not isinstance(reason, str) or not reason.strip() or not isinstance(reminder, str) or not reminder.strip():
        return False, "intervening proposal requires non-empty reason and reminder"
    if len(reminder.split()) > policy.get("max_reminder_words", 80):
        return False, "proposal reminder exceeds approved word limit"
    if FORBIDDEN_ADVISORY_TERMS.search(reason) or FORBIDDEN_ADVISORY_TERMS.search(reminder):
        return False, "proposal contains source-writing or execution language"
    return True, "accepted"


def advise(root: Path, run: str, input_path: Path, policy_path: Path, sequence: int | None, approved: bool) -> dict[str, Any]:
    if not approved:
        raise ValueError("advisory selection requires --approved")
    policy = load_selector_policy(policy_path)
    current = show(root, run, sequence)
    proposal = read(input_path)
    valid, outcome = validate_proposal(root, proposal, current, policy)
    directory = L.state_dir(root, run) / "continuity" / "advisories"
    number = len(list(directory.glob("advisory-*.json"))) + 1
    artifact = directory / f"advisory-{number}.json"
    base = {
        "schema_version": "1", "type": "tailtrail-context-continuity-advisory", "run_id": run,
        "sequence": number, "state_sequence": current["sequence"], "requirement_uid": current["requirement_uid"],
        "selector_policy_version": policy["version"], "model": policy["model"],
        "proposal_path": rel(root, input_path), "policy_path": rel(root, policy_path),
        "evidence_label": "local-evidence", "authority": "advisory-only",
    }
    if not valid:
        record = {**base, "outcome": "fallback", "validation": outcome,
                  "fallback": {"state_path": current["state_path"], "packet_path": current["packet_path"]}}
        L.atomic_json(artifact, record)
        L.append_event(root, run, "context_continuity_advisory_rejected", {"artifact": rel(root, artifact), "reason": outcome})
        return {"artifact": artifact.as_posix(), "advisory_packet": current["packet_markdown"], **record}
    if not proposal["intervene"]:
        record = {**base, "outcome": "silent", "validation": outcome, "artifact_pointers": proposal["artifact_pointers"],
                  "uncertainty": proposal["uncertainty"]}
        L.atomic_json(artifact, record)
        L.append_event(root, run, "context_continuity_advisory_recorded", {"artifact": rel(root, artifact), "outcome": "silent"})
        return {"artifact": artifact.as_posix(), "advisory_packet": None, **record}
    advisory = f"Advisory continuity note ({proposal['uncertainty']}): {proposal['reminder']}\nReason: {proposal['reason']}"
    record = {**base, "outcome": "accepted", "validation": outcome, "artifact_pointers": proposal["artifact_pointers"],
              "uncertainty": proposal["uncertainty"], "advisory_fingerprint": "sha256:" + hashlib.sha256(advisory.encode()).hexdigest()}
    L.atomic_json(artifact, record)
    L.append_event(root, run, "context_continuity_advisory_recorded", {"artifact": rel(root, artifact), "outcome": "accepted"})
    return {"artifact": artifact.as_posix(), "advisory_packet": advisory, **record}


def advisory_show(root: Path, run: str, sequence: int | None) -> dict[str, Any]:
    directory = L.state_dir(root, run) / "continuity" / "advisories"
    path = directory / f"advisory-{sequence}.json" if sequence else latest(directory, "advisory-*.json")[0]
    if not path or not path.is_file():
        raise ValueError("no continuity advisory exists")
    return {"artifact": path.as_posix(), **read(path)}


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("render", "show", "calibrate", "advise", "advisory-show"):
        item = sub.add_parser(action)
        item.add_argument("--root", type=Path, default=Path.cwd())
        item.add_argument("--run-id", required=True)
        if action == "render":
            item.add_argument("--requirement-uid")
            item.add_argument("--trigger", choices=sorted(TRIGGERS))
            item.add_argument("--max-words", type=int, default=220)
            item.add_argument("--policy", type=Path)
        elif action in {"show", "advisory-show"}:
            item.add_argument("--sequence", type=int)
        elif action == "calibrate":
            item.add_argument("--input", type=Path, required=True)
        else:
            item.add_argument("--input", type=Path, required=True)
            item.add_argument("--policy", type=Path, required=True)
            item.add_argument("--sequence", type=int)
            item.add_argument("--approved", action="store_true")
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        if args.action == "render":
            output = render(root, args.run_id, args.requirement_uid, args.trigger, args.max_words,
                            (root / args.policy).resolve() if args.policy and not args.policy.is_absolute() else args.policy)
        elif args.action == "show":
            output = show(root, args.run_id, args.sequence)
        elif args.action == "calibrate":
            input_path = (root / args.input).resolve() if not args.input.is_absolute() else args.input
            output = calibrate(root, args.run_id, input_path)
        elif args.action == "advisory-show":
            output = advisory_show(root, args.run_id, args.sequence)
        else:
            input_path = (root / args.input).resolve() if not args.input.is_absolute() else args.input
            policy_path = (root / args.policy).resolve() if not args.policy.is_absolute() else args.policy
            output = advise(root, args.run_id, input_path, policy_path, args.sequence, args.approved)
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Context continuity error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
