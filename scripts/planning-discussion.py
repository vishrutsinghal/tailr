#!/usr/bin/env python3
"""Record bounded, sanitized Interactive Plan Mode discussion receipts.

This control-plane surface answers from saved planning artifacts only. It does
not inspect source, invoke a graph, execute a project command, or mutate a
Start proposal.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = (
    "Planning discussion records metadata only; it does not persist raw chat or inspect project source, "
    "run tools, or change the approved plan."
)
DISCUSSION_CLASSES = {
    "explain-scope",
    "explain-impact",
    "explain-requirement",
    "explain-authority",
    "explain-assumption",
    "explain-feature",
    "explain-aidlc",
    "explain-testing",
    "explain-drift",
    "explain-token",
    "explain-risk",
    "explain-approval",
    "technical-alternative",
    "requirement-clarification",
    "revision-request",
}
ROUTE_CLASSES = {"rejection", "aidlc-escalation", "aidlc-standard-switch", "feature-customization", "pasted-error-or-log", "ordinary-chat"}
PATH_PATTERN = re.compile(r"(?<![\w.-])(?:[\w.-]+/)+[\w.-]+")
REQUIREMENT_PATTERN = re.compile(r"\b(?:REQ|FR)-\d{1,4}\b", re.IGNORECASE)
ERROR_PATTERN = re.compile(
    r"(?:traceback \(most recent call last\)|\b(?:exception|error|failed|failure)\s*[:\[]|\bat\s+[^\n]+\([^\n]+:\d+|file \"[^\"]+\", line \d+)",
    re.IGNORECASE,
)


def module(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    loaded = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(loaded)
    return loaded


LOCK = module("planning_discussion_lock", "planning-lock.py")
LEDGER = module("planning_discussion_ledger", "run-ledger.py")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def classify(message: str) -> str:
    """Classify message shape only; never use it as authority for implementation."""
    normalized = " ".join(message.lower().split())
    if not normalized:
        return "ordinary-chat"
    if ERROR_PATTERN.search(message) or ("\n" in message and "stack" in normalized):
        return "pasted-error-or-log"
    if re.match(r"^(?:reject|decline|do not approve)\b", normalized):
        return "rejection"
    if (
        re.search(r"\b(?:switch|use|move|change)\b.*\b(?:standard|medium)\s+aidlc\b", normalized)
        or re.search(r"\b(?:standard|medium)\s+aidlc\b.*\b(?:switch|use|move|change)\b", normalized)
    ):
        return "aidlc-standard-switch"
    if re.search(r"\b(?:enable|disable|arm|select|customi[sz]e|configure)\b.*\b(?:harness|aidlc|testing|graph|token)\b", normalized):
        return "feature-customization"
    if "use aidlc" in normalized or "aidlc requirements mode" in normalized:
        return "aidlc-escalation"
    if not re.search(r"\b(why|what|how|which|could|can|clarify|explain|does|will|is|should|update|change|remove|add)\b", normalized):
        return "ordinary-chat"
    if REQUIREMENT_PATTERN.search(message) and not PATH_PATTERN.search(message.replace("\\", "/")):
        return "explain-requirement"
    if "assumption" in normalized or "non-goal" in normalized:
        return "explain-assumption"
    if "authority" in normalized or "authoritative" in normalized:
        return "explain-authority"
    if any(term in normalized for term in ("update the plan", "revise the plan", "change the plan", "remove ", "add ")):
        return "revision-request"
    if any(term in normalized for term in ("must ", "should ", "need to ", "requirement", "preserve ")):
        return "requirement-clarification"
    if any(term in normalized for term in ("dependency", "alternative", "avoid ", "instead of")):
        return "technical-alternative"
    if "aidlc" in normalized:
        return "explain-aidlc"
    if any(term in normalized for term in ("harness", "navigator", "feature", "selected tailtrail")):
        return "explain-feature"
    if any(term in normalized for term in ("test", "validation", "proof", "ci")):
        return "explain-testing"
    if any(term in normalized for term in ("drift", "scope creep", "deviation")):
        return "explain-drift"
    if any(term in normalized for term in ("token", "context", "cost")):
        return "explain-token"
    if any(term in normalized for term in ("risk", "safe", "safety", "rollback", "recovery")):
        return "explain-risk"
    if any(term in normalized for term in ("approve", "approval", "implement", "after approval")):
        return "explain-approval"
    if any(term in normalized for term in ("caller", "call path", "impact", "api", "contract")):
        return "explain-impact"
    return "explain-scope"


def references(message: str) -> list[dict[str, str]]:
    """Keep only bounded identifiers; never retain the message itself."""
    values: list[dict[str, str]] = []
    for requirement in REQUIREMENT_PATTERN.findall(message):
        item = {"kind": "requirement", "value": requirement.upper()}
        if item not in values:
            values.append(item)
    for path in PATH_PATTERN.findall(message.replace("\\", "/")):
        if path.startswith("../") or path.startswith("/") or len(path) > 240:
            continue
        item = {"kind": "path", "value": path}
        if item not in values:
            values.append(item)
    return values


def summary(kind: str) -> str:
    summaries = {
        "explain-scope": "Requested an explanation of the saved plan scope.",
        "explain-impact": "Requested an explanation of a saved impact or caller decision.",
        "explain-requirement": "Requested an explanation of a saved requirement row.",
        "explain-authority": "Requested an explanation of the requirement authority.",
        "explain-assumption": "Requested an explanation of a saved planning assumption or non-goal.",
        "explain-feature": "Requested an explanation of a selected TailTrail control.",
        "explain-aidlc": "Requested an explanation of the selected AIDLC posture.",
        "explain-testing": "Requested an explanation of the planned validation evidence.",
        "explain-drift": "Requested an explanation of the plan drift posture.",
        "explain-token": "Requested an explanation of the local token posture.",
        "explain-risk": "Requested an explanation of the plan risk or recovery posture.",
        "explain-approval": "Requested an explanation of the approval boundary.",
        "technical-alternative": "Requested a planning-level technical alternative.",
        "requirement-clarification": "Provided a possible requirement clarification for later review.",
        "revision-request": "Requested a possible material plan revision for a later revision phase.",
    }
    return summaries[kind]


def _saved_report(root: Path, run_id: str) -> dict[str, Any]:
    """Load the immutable Start report, never project source facts into it."""
    try:
        path = LOCK.active_start_report_path(root, run_id)
    except ValueError:
        return {}
    if not path.is_file():
        return {}
    payload = LOCK.read(path)
    report = payload.get("report")
    return report if isinstance(report, dict) else {}


def _text_list(value: Any) -> list[str]:
    return [str(item) for item in value if isinstance(item, (str, int, float))] if isinstance(value, list) else []


def _answer(status: str, direct: str, evidence: list[dict[str, str]], alternative: str, risk: str, impact: str, next_choice: str) -> dict[str, Any]:
    return {
        "status": status,
        "direct": direct,
        "evidence": evidence,
        "alternative": alternative,
        "risk": risk,
        "impact_on_plan": impact,
        "next_choice": next_choice,
    }


def _unknown(topic: str) -> dict[str, Any]:
    return _answer(
        "unknown",
        f"The saved plan does not contain enough evidence to answer {topic}.",
        [{"label": "planning-lock", "detail": "The Planning Lock permits planning artifacts only; no new source inspection was run."}],
        "Request a bounded read-only plan investigation in a later Interactive Plan Mode phase, or revise/reject the plan.",
        "Treating an unstored inference as proof could expand scope or create a misleading approval decision.",
        "No plan change.",
        "Continue discussion, request revision, reject, or use AIDLC.",
    )


def _feature_rows(report: dict[str, Any], key: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    navigator = report.get("navigator") if isinstance(report.get("navigator"), dict) else {}
    delivery = report.get("guided_delivery") if isinstance(report.get("guided_delivery"), dict) else {}
    for container in (navigator.get(key, []), delivery.get("selected" if key == "selected_features" else "activated_later", [])):
        if isinstance(container, list):
            values.extend(item for item in container if isinstance(item, dict))
    return values


def explain(root: Path, run_id: str, question: str, kind: str | None = None) -> dict[str, Any]:
    """Return an evidence-labelled answer from the saved run artifacts only."""
    report = _saved_report(root, run_id)
    if not report:
        return _unknown("this question because the saved Start Report is unavailable")
    normalized = " ".join(question.lower().split())
    classification = kind or classify(question)
    navigator = report.get("navigator") if isinstance(report.get("navigator"), dict) else {}
    references_found = references(question)
    paths = [item["value"] for item in references_found if item["kind"] == "path"]
    requirements = [item["value"] for item in references_found if item["kind"] == "requirement"]
    impacted = [item for item in navigator.get("likely_impacted_files", []) if isinstance(item, dict)]

    if classification in {"explain-scope", "explain-impact"}:
        matches = [item for item in impacted if not paths or str(item.get("path")) in paths]
        if matches:
            details = [f"`{item.get('path')}`: {item.get('reason', 'saved Navigator impact decision')}" for item in matches[:3]]
            label = "graph-cache" if any("graph" in str(item.get("reason", "")).lower() for item in matches) else "decision-record"
            return _answer(
                "answered",
                "The file is a saved planning inspection target; it is not an approved edit by itself.",
                [{"label": label, "detail": detail} for detail in details],
                "Keep the file read-only unless the approved implementation evidence shows the change is required.",
                "Removing it now may miss a caller, preservation boundary, or focused test; changing it without approval would exceed the plan.",
                "No plan change.",
                "Continue discussion, request revision, reject, or use AIDLC.",
            )
        return _unknown("why that file or relationship was selected")

    if classification == "explain-requirement":
        matrix = navigator.get("requirement_matrix", [])
        rows = [row for row in matrix if isinstance(row, dict) and str(row.get("display_id", row.get("requirement_uid", ""))).upper() in requirements]
        if not rows and isinstance(report.get("spec_kit_source"), dict):
            rows = [row for row in report["spec_kit_source"].get("requirements", []) if isinstance(row, dict) and str(row.get("external_id", "")).upper() in requirements]
        if rows:
            return _answer(
                "answered",
                "The requirement is present in the saved planning boundary.",
                [{"label": "imported-intent" if "external_id" in row else "decision-record", "detail": f"{row.get('display_id', row.get('external_id', row.get('requirement_uid')))}: {row.get('statement', 'saved requirement')}"} for row in rows],
                "Request a revision if its scope, preservation rule, or proof needs to change.",
                "The requirement boundary is planning evidence, not proof that implementation has occurred.",
                "No plan change.",
                "Continue discussion or request revision.",
            )
        return _unknown("that requirement row")

    if classification == "explain-authority":
        imported = report.get("spec_kit_source")
        if isinstance(imported, dict):
            return _answer(
                "answered",
                "The imported requirement source remains authoritative for requirement wording and revisions.",
                [{"label": "imported-intent", "detail": f"Feature `{imported.get('feature_id', 'unknown')}` at source revision `{imported.get('source_revision', 'unknown')}`."}],
                "Use the source amendment route for a requirement wording change; TailTrail may only explain local mappings.",
                "Changing imported wording in TailTrail would create divergent requirement sources.",
                "No plan change.",
                "Continue discussion or request the appropriate source amendment.",
            )
        return _answer(
            "answered",
            "This run uses the saved TailTrail Planning Lock and proposed requirement boundary as its pre-approval authority.",
            [{"label": "planning-lock", "detail": "The lock preserves the reviewed goal and requires approval before implementation."}],
            "Use AIDLC Requirements mode if the requirement boundary needs deeper discovery.",
            "The proposed boundary is not yet an immutable approved anchor.",
            "No plan change.",
            "Continue discussion, request revision, reject, or use AIDLC.",
        )

    if classification == "explain-assumption":
        aidlc = report.get("aidlc_requirements") if isinstance(report.get("aidlc_requirements"), dict) else {}
        stage = aidlc.get("aidlc_stage") if isinstance(aidlc.get("aidlc_stage"), dict) else {}
        assumptions = _text_list(stage.get("assumptions"))
        non_goals = _text_list(stage.get("non_goals"))
        if assumptions or non_goals:
            evidence = [{"label": "decision-record", "detail": f"Assumption: {item}"} for item in assumptions]
            evidence.extend({"label": "decision-record", "detail": f"Non-goal: {item}"} for item in non_goals)
            return _answer(
                "answered",
                "These are saved planning assumptions and non-goals; they are not verified implementation facts.",
                evidence,
                "Clarify, reject, or use AIDLC Requirements mode if an assumption must become a requirement.",
                "Unchallenged assumptions can make an approved scope incomplete or misleading.",
                "No plan change.",
                "Continue discussion, request revision, reject, or use AIDLC.",
            )
        return _unknown("the plan assumptions or non-goals")

    if classification == "explain-feature":
        selected = _feature_rows(report, "selected_features")
        deferred = _feature_rows(report, "skipped_features")
        all_rows = [*selected, *deferred]
        matched = [item for item in all_rows if any(part and part in normalized for part in str(item.get("name", "")).lower().split())]
        rows = matched or selected[:3] or deferred[:3]
        if rows:
            deferred_names = {str(item.get("name")) for item in deferred}
            return _answer(
                "answered",
                "Selected and deferred controls are planning decisions; neither is evidence that a control has already run.",
                [{"label": "decision-record", "detail": f"{item.get('name')}: {item.get('why', item.get('when', 'saved planning decision'))}"} for item in rows],
                "Deferred controls remain available only under their saved activation conditions." if any(str(item.get("name")) in deferred_names for item in rows) else "Request a plan revision if a selected control is not appropriate.",
                "Treating selection as completed evidence would overstate delivery confidence.",
                "No plan change.",
                "Continue discussion or request revision of selected controls.",
            )
        return _unknown("which TailTrail control was selected")

    if classification == "explain-testing":
        commands = _text_list(navigator.get("suggested_commands"))
        test_paths = [str(item.get("path")) for item in impacted if "test" in str(item.get("path", "")).lower()]
        if commands or test_paths:
            facts = ([{"label": "decision-record", "detail": f"Saved suggested validation: `{commands[0]}`"}] if commands else [])
            facts.extend({"label": "decision-record", "detail": f"Saved focused test candidate: `{path}`"} for path in test_paths[:2])
            return _answer(
                "answered",
                "The validation choice is a planned proof target, not a passing test result.",
                facts,
                "Request a plan revision if the proof tier should include a caller, contract, or integration path.",
                "Unit-only proof can miss cross-layer behaviour; TailTrail cannot claim coverage beyond the saved plan.",
                "No plan change.",
                "Continue discussion or request a validation-tier revision.",
            )
        return _unknown("the planned validation path")

    if classification == "explain-aidlc":
        mode = report.get("aidlc_mode") if isinstance(report.get("aidlc_mode"), dict) else {}
        if mode:
            return _answer(
                "answered",
                f"AIDLC mode is `{mode.get('mode', 'unknown')}` for this saved plan.",
                [{"label": "decision-record", "detail": f"Selection: {mode.get('selection', 'not recorded')}"}, {"label": "decision-record", "detail": f"Boundary: {mode.get('boundary', 'not recorded')}"}],
                "Reject the plan or explicitly request a different AIDLC mode if the saved lifecycle depth is not appropriate.",
                "Changing mode can change requirements gathering and approval behaviour; it needs a revised plan rather than a silent switch.",
                "No plan change.",
                "Continue discussion, request revision, reject, or use AIDLC Requirements mode.",
            )
        return _unknown("the AIDLC mode")

    if classification == "explain-token":
        token = report.get("token_posture") if isinstance(report.get("token_posture"), dict) else {}
        if token:
            return _answer(
                "answered",
                f"The saved focused-context estimate is approximately `{token.get('used_tokens', 0)}` tokens; this is not measured model usage.",
                [{"label": "decision-record", "detail": str(token.get("evidence", "Local estimate only."))}],
                "Link host/provider telemetry after execution for actual model-token usage.",
                "Using this estimate as an exact cost or savings claim would be unsupported.",
                "No plan change.",
                "Continue discussion or request a smaller approved scope.",
            )
        return _unknown("the token posture")

    if classification == "explain-drift":
        return _answer(
            "answered",
            "No implementation drift has been measured because this run remains before approval and source changes are blocked.",
            [{"label": "planning-lock", "detail": "The active Planning Lock is awaiting approval and permits planning artifacts only."}],
            "After approved implementation, use checkpoint and harness evidence to assess actual drift.",
            "A planning prediction is not post-change drift evidence.",
            "No plan change.",
            "Continue discussion or request revision of the requirement boundary.",
        )

    if classification == "explain-risk":
        risks = _text_list(navigator.get("risks"))
        if risks:
            return _answer(
                "answered",
                "The saved Navigator risk posture identifies the following planning risks.",
                [{"label": "decision-record", "detail": risk} for risk in risks],
                "Narrow scope or raise the proof tier through a plan revision if these risks are unacceptable.",
                "Risk classification is advisory until source and validation evidence are available.",
                "No plan change.",
                "Continue discussion, request revision, reject, or use AIDLC.",
            )
        return _unknown("the risk classification")

    if classification == "explain-approval":
        lock = LOCK.show(root, run_id)
        return _answer(
            "answered",
            "Approval activates the exact saved Start Report for this run; it is the boundary before managed source work may begin.",
            [{"label": "planning-lock", "detail": str(lock.get("boundary", "Planning Lock boundary recorded."))}],
            "Keep discussing, reject, or use AIDLC Requirements mode if the plan is not ready.",
            "Approval does not prove implementation, validation, or delivery completion.",
            "No plan change.",
            "Approve, continue discussion, reject, or use AIDLC.",
        )

    if classification in {"requirement-clarification", "revision-request"}:
        authority = "imported intent" if isinstance(report.get("spec_kit_source"), dict) else "TailTrail requirement framing"
        detail = "A source amendment is required; imported requirement wording cannot be silently changed." if authority == "imported intent" else "The clarification is recorded as a proposal only; IP-1 does not revise the Start Report."
        return _answer(
            "answered",
            f"This is a material planning request under {authority}.",
            [{"label": "imported-intent" if authority == "imported intent" else "planning-lock", "detail": detail}],
            "Use the later plan-revision path, or reject/use AIDLC Requirements mode now.",
            "Silently changing requirements would make the reviewed plan and approved anchor diverge.",
            "Proposed change only; no plan mutation in IP-1.",
            "Continue discussion, reject, or use AIDLC.",
        )

    if classification == "technical-alternative":
        return _answer(
            "unknown",
            "The saved plan does not prove whether that alternative fits the current implementation.",
            [{"label": "planning-lock", "detail": "No source investigation or alternative decision was recorded during planning."}],
            "Request a later bounded read-only investigation or a plan revision that states the alternative explicitly.",
            "Selecting an alternative without source evidence could violate the approved scope or existing project conventions.",
            "No plan change.",
            "Continue discussion, request revision, reject, or use AIDLC.",
        )

    return _unknown("this planning question")


def _read_receipts(root: Path, run_id: str) -> list[dict[str, Any]]:
    path = LOCK.discussion_receipts_path(root, run_id)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_state(root: Path, run_id: str, count: int) -> dict[str, Any]:
    payload = {
        "schema_version": "1",
        "type": "tailtrail-interactive-plan-state",
        "run_id": run_id,
        "state": "discussing",
        "planning_lock_status": "awaiting-approval",
        "plan_revision": 1,
        "conversations_recorded": count,
        "boundary": BOUNDARY,
        "updated_at": utc_now(),
    }
    LEDGER.atomic_json(LOCK.discussion_state_path(root, run_id), payload)
    return payload


def discuss(root: Path, run_id: str, question: str) -> dict[str, Any]:
    root = root.resolve()
    lock = LOCK.assert_discussion_allowed(root, run_id)
    kind = classify(question)
    base = {
        "schema_version": "1",
        "type": "tailtrail-planning-discussion-route",
        "run_id": run_id,
        "planning_lock_status": lock["status"],
        "classification": kind,
        "source_changed": False,
        "tools_run": [],
        "boundary": BOUNDARY,
    }
    if kind not in DISCUSSION_CLASSES:
        routes = {
            "rejection": "tailtrail planning feedback-template",
            "aidlc-escalation": "tailtrail planning aidlc-requirements",
            "aidlc-standard-switch": "tailtrail planning aidlc-standard --run-id <active-run-id> --approved-proposal",
            "feature-customization": "tailtrail planning feature-controls-show --run-id <active-run-id> (then propose one structured control change)",
            "pasted-error-or-log": "ordinary failure or debugging handling; no Planning Lock discussion receipt was created",
            "ordinary-chat": "ordinary chat guidance; no Planning Lock discussion receipt was created",
        }
        return {**base, "recorded": False, "route": routes[kind]}

    with LEDGER.RunLock(LEDGER.state_dir(root, run_id) / ".lock"):
        receipts = _read_receipts(root, run_id)
        receipt = {
            "schema_version": "1",
            "type": "tailtrail-plan-conversation",
            "conversation_id": f"plan-q-{len(receipts) + 1:03d}",
            "run_id": run_id,
            "plan_revision": 1,
            "classification": kind,
            "references": references(question),
            "evidence_labels": ["planning-lock", "start-report"] if LOCK.start_report_path(root, run_id).is_file() else ["planning-lock"],
            "material_change": kind in {"requirement-clarification", "revision-request"},
            "source_changed": False,
            "sanitized_summary": summary(kind),
            "explanation": explain(root, run_id, question, kind),
            "created_at": utc_now(),
            "boundary": BOUNDARY,
        }
        path = LOCK.discussion_receipts_path(root, run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n")
        state = _write_state(root, run_id, len(receipts) + 1)
    LEDGER.append_event(root, run_id, "planning_discussion_recorded", {
        "conversation_id": receipt["conversation_id"],
        "classification": kind,
        "material_change": receipt["material_change"],
        "artifact": LOCK.discussion_receipts_path(root, run_id).relative_to(LEDGER.state_dir(root, run_id)).as_posix(),
    })
    return {**base, "recorded": True, "receipt": receipt, "answer": receipt["explanation"], "discussion_state": state}


def discussion_show(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    lock = LOCK.show(root, run_id)
    receipts = _read_receipts(root, run_id)
    state_path = LOCK.discussion_state_path(root, run_id)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else None
    return {
        "schema_version": "1",
        "type": "tailtrail-planning-discussion-log",
        "run_id": run_id,
        "planning_lock_status": lock["status"],
        "discussion_state": state,
        "receipts": receipts,
        "boundary": BOUNDARY,
    }


def decision_show(root: Path, run_id: str) -> dict[str, Any]:
    """Return one read-only inventory of saved Interactive Plan decisions."""
    root = root.resolve()
    lock = LOCK.show(root, run_id)
    directory = LEDGER.state_dir(root, run_id)
    revision_path = directory / "planning" / "plan-revision-state-v1.json"
    revision = json.loads(revision_path.read_text(encoding="utf-8")) if revision_path.is_file() else {
        "active_revision": 1,
        "pending_revision": None,
    }
    report = _saved_report(root, run_id)
    aidlc = report.get("aidlc_mode") if isinstance(report.get("aidlc_mode"), dict) else {}
    routes = []
    for path in sorted((directory / "planning" / "authority-routes").glob("route-*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        routes.append({
            "route_id": item.get("route_id"),
            "authority": item.get("authority"),
            "route": item.get("route"),
            "state": item.get("state"),
            "artifact": path.relative_to(root).as_posix(),
        })
    return {
        "schema_version": "1",
        "type": "tailtrail-planning-decision-summary",
        "run_id": run_id,
        "planning_lock_status": lock.get("status"),
        "writes_allowed": lock.get("writes_allowed") is True,
        "discussion_count": len(_read_receipts(root, run_id)),
        "revision": {
            "active": revision.get("active_revision", 1),
            "pending": revision.get("pending_revision"),
            "history_count": len(list((directory / "planning" / "revisions").glob("revision-v*.json"))),
        },
        "aidlc_mode": {
            "mode": aidlc.get("mode", "lite"),
            "state": aidlc.get("state", "not-selected"),
            "selection": aidlc.get("selection", "not-recorded"),
        },
        "authority_routes": routes,
        "boundary": "Read-only summary of saved planning decisions. It does not inspect project source, create a revision, approve a plan, or run implementation commands.",
    }


def render_explanation(payload: dict[str, Any]) -> str:
    """Render the saved-evidence response without exposing the raw question."""
    answer = payload.get("answer", {})
    evidence = answer.get("evidence", []) if isinstance(answer, dict) else []
    lines = [
        "# TailTrail Plan Explanation",
        "",
        f"**Run ID:** `{payload.get('run_id', 'unknown')}`",
        "**State:** awaiting approval — no source, tests, scanners, Git, or implementation commands were run.",
        "",
        "## Answer",
        "",
        str(answer.get("direct", "Unknown.")),
        "",
        "## Evidence",
        "",
    ]
    if evidence:
        for item in evidence:
            lines.append(f"- **{item.get('label', 'saved-evidence')}:** {item.get('detail', '')}")
    else:
        lines.append("- No saved evidence is available.")
    lines.extend([
        "",
        "## Alternative",
        "",
        str(answer.get("alternative", "Continue discussion.")),
        "",
        "## Risk",
        "",
        str(answer.get("risk", "Unknown.")),
        "",
        "## Impact on the plan",
        "",
        str(answer.get("impact_on_plan", "No plan change.")),
        "",
        "## Next choice",
        "",
        str(answer.get("next_choice", "Continue discussion.")),
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    discuss_parser = sub.add_parser("discuss", help="Classify and record a sanitized planning discussion message.")
    discuss_parser.add_argument("--root", type=Path, default=Path.cwd())
    discuss_parser.add_argument("--run-id", required=True)
    discuss_parser.add_argument("--question", required=True)
    explain_parser = sub.add_parser("explain", help="Answer from saved planning evidence and record a sanitized receipt.")
    explain_parser.add_argument("--root", type=Path, default=Path.cwd())
    explain_parser.add_argument("--run-id", required=True)
    explain_parser.add_argument("--question", required=True)
    explain_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    show_parser = sub.add_parser("discussion-show", help="Show sanitized discussion receipts for one run.")
    show_parser.add_argument("--root", type=Path, default=Path.cwd())
    show_parser.add_argument("--run-id", required=True)
    decision_parser = sub.add_parser("decision-show", help="Show one compact, read-only Interactive Plan decision summary.")
    decision_parser.add_argument("--root", type=Path, default=Path.cwd())
    decision_parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        result = discuss(args.root, args.run_id, args.question) if args.command in {"discuss", "explain"} else (decision_show(args.root, args.run_id) if args.command == "decision-show" else discussion_show(args.root, args.run_id))
        if args.command == "explain" and args.format == "markdown" and result.get("recorded"):
            print(render_explanation(result))
        else:
            print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Interactive Plan Mode error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
