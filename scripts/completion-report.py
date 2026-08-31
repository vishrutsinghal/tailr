#!/usr/bin/env python3
"""Render one evidence-backed end-of-task completion report for a TailTrail run."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def ledger() -> Any:
    spec = importlib.util.spec_from_file_location("completion_report_ledger", ROOT / "scripts" / "run-ledger.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def learning_agent() -> Any:
    spec = importlib.util.spec_from_file_location("completion_report_learning", ROOT / "scripts" / "learning-agent.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def canonical_state_module() -> Any:
    spec = importlib.util.spec_from_file_location("completion_report_official_state", ROOT / "scripts" / "official-aidlc-state.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


L = ledger()
STATE = canonical_state_module()


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest(directory: Path, pattern: str) -> tuple[dict[str, Any] | None, str | None]:
    files = sorted(directory.glob(pattern))
    if not files:
        return None, None
    path = files[-1]
    return read(path), path.relative_to(directory.parents[0]).as_posix()


def status(value: bool | None, *, not_selected: bool = False) -> str:
    if not_selected:
        return "not-assessed"
    if value is None:
        return "unavailable"
    return "pass" if value else "fail"


def table_cell(value: Any) -> str:
    """Keep saved evidence safe to render inside a single Markdown table cell."""
    return " ".join(str(value).replace("|", "\\|").split()) or "-"


def failure_summary(directory: Path) -> dict[str, Any]:
    records = [read(path) for path in sorted((directory / "execution-failures").glob("failure-*.json"))]
    unresolved = [item for item in records if item.get("status") != "resolved"]
    return {"status": "none-recorded" if not records else ("unresolved" if unresolved else "resolved"), "count": len(records), "unresolved": [{"failure_id": item.get("failure_id"), "requirement_uid": (item.get("requirement") or {}).get("requirement_uid"), "classification": (item.get("diagnosis") or {}).get("classification")} for item in unresolved]}


def token_usage_summary(root: Path, run_id: str, directory: Path) -> dict[str, Any]:
    """Return only measured usage explicitly linked to this TailTrail run."""
    start_path = directory / "planning" / "start-report-v1.json"
    saved_start = read(start_path) if start_path.is_file() else {}
    start_report = saved_start.get("report", saved_start) if isinstance(saved_start, dict) else {}
    posture = start_report.get("token_posture", {}) if isinstance(start_report, dict) else {}
    estimate = posture.get("used_tokens") if isinstance(posture, dict) else None
    if not isinstance(estimate, int) or isinstance(estimate, bool) or estimate < 0:
        anchor_path = directory / "anchors" / "approved-v1.json"
        anchor = read(anchor_path) if anchor_path.is_file() else {}
        paths = {
            str(path) for row in anchor.get("requirements", []) if isinstance(row, dict)
            for path in row.get("likely_paths", []) if isinstance(path, str)
        }
        estimate = sum((len((root / path).read_text(encoding="utf-8")) + 3) // 4 for path in paths if (root / path).is_file())
    telemetry = root / ".tailtrail" / "token-usage.jsonl"
    records: list[dict[str, Any]] = []
    if telemetry.is_file():
        for line in telemetry.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get("mode") == "measured" and str(item.get("task_id", "")) == run_id:
                records.append(item)
    totals = [item.get("tailtrail", {}).get("total_tokens") for item in records if isinstance(item.get("tailtrail"), dict)]
    measured = bool(records) and all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in totals)
    return {
        "planning_estimate_tokens": estimate,
        "status": "measured" if measured else "unavailable",
        "actual_tailtrail_tokens": sum(totals) if measured else None,
        "telemetry_records": len(records),
        "boundary": "Actual tokens require host/provider telemetry with task_id equal to this run ID; local estimates are never presented as measured usage.",
    }


def drift_learning_observation(directory: Path, payload: dict[str, Any], record: bool) -> dict[str, Any]:
    """Save drift memory for the active run without promoting it to global learning."""
    findings = payload["drift"]["findings"]
    if not findings:
        return {"status": "none", "artifact": None, "boundary": "No unresolved drift was recorded."}
    observation = {
        "schema_version": "1",
        "type": "tailtrail-drift-learning-observation",
        "run_id": payload["run_id"],
        "drift": findings,
        "next_iteration_rule": "Reuse this run's approved boundary and prior drift evidence; do not repeat the same unresolved requirement gap.",
        "promotion": "same-run continuity only; explicit review is required before any cross-run learning promotion",
    }
    if not record:
        return {"status": "preview", "artifact": None, "boundary": observation["promotion"]}
    path = directory / "learning-observations" / "drift-v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    L.atomic_json(path, observation)
    return {"status": "recorded", "artifact": path.relative_to(directory).as_posix(), "boundary": observation["promotion"]}


def completion_learning_intake(root: Path, directory: Path, payload: dict[str, Any], record: bool) -> dict[str, Any]:
    """Capture a deduplicated, sanitized learning candidate from closure gaps only."""
    signals: list[dict[str, str]] = []
    for requirement in payload["requirement_status"]["requirements"]:
        if requirement["status"] != "complete":
            signals.append({"kind": "requirement-incomplete", "requirement_uid": requirement["requirement_uid"]})
        for drift in requirement["drift"]:
            classification = str(drift.get("classification", ""))
            if classification in {"new-drift", "regressed", "needs-decision"}:
                signals.append({"kind": "requirement-drift", "requirement_uid": requirement["requirement_uid"], "classification": classification})
    if payload["tests"]["status"] != "pass":
        signals.append({"kind": "evidence-gap", "status": payload["tests"]["status"]})
    if payload["execution_failures"]["status"] == "unresolved":
        signals.append({"kind": "execution-failure", "status": "unresolved"})
    if not signals:
        return {"status": "not-triggered", "artifact": None, "event_id": None, "boundary": "No unresolved completion gap requires a learning candidate."}

    normalized = sorted(signals, key=lambda item: (item["kind"], item.get("requirement_uid", ""), item.get("classification", ""), item.get("status", "")))
    fingerprint = hashlib.sha256(L.canonical({"run_id": payload["run_id"], "signals": normalized}).encode("utf-8")).hexdigest()[:16]
    observation = {
        "schema_version": "1",
        "type": "tailtrail-completion-learning-observation",
        "run_id": payload["run_id"],
        "fingerprint": fingerprint,
        "signals": normalized,
        "next_iteration_rule": "Reuse the approved boundary and named evidence gaps before another completion claim; do not repeat the same unresolved requirement drift.",
        "promotion": "sanitized candidate only; it cannot alter future behavior without explicit review and current-run evidence",
    }
    if not record:
        return {"status": "preview", "artifact": None, "event_id": f"completion-{fingerprint}", "boundary": observation["promotion"]}

    path = directory / "learning-observations" / "completion-learning-v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    L.atomic_json(path, observation)
    learner = learning_agent()
    learner.ensure_files(root)
    event_id = f"completion-{fingerprint}"
    events = learner.read_events(root)
    if not any(event.get("id") == event_id for event in events):
        changed_paths = [str(item.get("path")) for item in payload["changed_scope"]["changed_paths"] if item.get("path")]
        outcome = "fail" if payload["tests"]["status"] == "fail" else "partial"
        event = {
            "id": event_id,
            "timestamp": L.utc_now(),
            "repo": root.name,
            "task_type": "completion-feedback",
            "tags": ["completion-report", *sorted({item["kind"] for item in normalized})],
            "prompt_summary": "Sanitized TailTrail completion evidence.",
            "files": changed_paths,
            "issue_ids": [item["requirement_uid"] for item in normalized if item.get("requirement_uid")],
            "validation_commands": [],
            "validation_outcome": outcome,
            "solution_summary": "No source or prompt content captured; see the run-local completion-learning observation.",
            "acceptance": "unknown",
            "acceptance_reason": "",
            "approved_changes": [],
            "requested_changes": [item["kind"] for item in normalized],
            "clarifications": [],
            "fulfillment_status": "partially-aligned",
            "learning_candidate": "Do not declare completion while requirement drift, failed evidence, or unresolved execution failures remain.",
            "risk": "normal",
            "sensitivity": "normal",
            "review_status": "changes-requested",
            "user_override": "none",
            "reused_project_pattern": False,
            "small_focused_change": False,
            "no_new_dependency": False,
            "dependency_gate_applied": False,
            "scanner_resolved": False,
            "guardrail_weakened": False,
            "promotion_decision": "not-scored",
            "stale_when": "the TailTrail completion contract, relevant evidence tier, or recovery policy changes",
            "completion_learning_fingerprint": fingerprint,
            "source_run_id": payload["run_id"],
        }
        score = learner.score_event(event)
        event["learning_confidence"] = score.__dict__
        event["promotion_decision"] = "candidate-only"
        learner.append_jsonl(root / learner.EVENTS, event)
        learner.append_jsonl(root / learner.SCORES, {"event_id": event_id, "timestamp": L.utc_now(), **score.__dict__})
        learner.rebuild_index(root)
        status = "captured"
    else:
        status = "reused"
    return {"status": status, "artifact": path.relative_to(directory).as_posix(), "event_id": event_id, "boundary": observation["promotion"]}


def positive_learning_status(directory: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Report eligibility without silently creating or promoting a success rule."""
    candidates = sorted((directory / "positive-learning").glob("success-*.json"))
    if candidates:
        return {"status": "captured-candidate-only", "artifact": candidates[-1].relative_to(directory).as_posix(), "boundary": "A saved candidate still requires explicit learning review before promotion."}
    if payload.get("overall_status") == "complete":
        return {"status": "eligible-awaiting-acceptance", "artifact": None, "boundary": "Use tailtrail closure learn with explicit user or trusted-CI acceptance; completion alone never creates a reusable learning rule."}
    return {"status": "not-eligible", "artifact": None, "boundary": "Positive learning requires complete requirements, passing saved receipts, no unresolved drift/failure, and explicit acceptance."}


def build(root: Path, run_id: str, record: bool = True) -> dict[str, Any]:
    directory = L.state_dir(root, run_id)
    canonical_state = STATE.project(root, run_id)
    anchor = read(directory / "anchors" / "approved-v1.json")
    checkpoint, checkpoint_path = latest(directory / "checkpoints", "checkpoint-*.json")
    review, review_path = latest(directory / "reviews", "review-*.json")
    gate, gate_path = latest(directory / "completion-gates", "gate-*.json")
    architecture, architecture_path = latest(directory / "architecture", "assessment-*.json")
    behavior, behavior_path = latest(directory / "behavior", "assessment-*.json")
    maintainability, maintainability_path = latest(directory / "maintainability", "assessment-*.json")
    boundary_path = directory / "recovery" / "boundary.json"
    boundary = read(boundary_path) if boundary_path.is_file() else None
    receipts = [read(path) for path in sorted((directory / "validation-receipts").glob("*.json"))]
    failures = failure_summary(directory)
    debug_section_path = directory / "debug" / "completion" / "debug-closure-section-v1.json"
    debug_section = read(debug_section_path) if debug_section_path.is_file() else None
    debug_run = (directory / "debug" / "intake" / "debug-intake-v1.json").is_file()

    actual = {row.get("requirement_uid"): row for row in (checkpoint or {}).get("requirements", [])}
    findings_by_requirement: dict[str, list[dict[str, Any]]] = {}
    drift_by_requirement: dict[str, list[dict[str, Any]]] = {}
    blocking_drift_by_requirement: dict[str, list[dict[str, Any]]] = {}
    for finding in (review or {}).get("findings", []):
        uid = str(finding.get("requirement_uid", ""))
        findings_by_requirement.setdefault(uid, []).append(finding)
        if finding.get("classification"):
            drift_by_requirement.setdefault(uid, []).append(finding)
            if finding["classification"] in {"new-drift", "regressed", "needs-decision"}:
                blocking_drift_by_requirement.setdefault(uid, []).append(finding)
    for finding in (checkpoint or {}).get("drift", []):
        uid = str(finding.get("requirement_uid", ""))
        if uid:
            drift_by_requirement.setdefault(uid, []).append(finding)
            if finding.get("classification") in {"new-drift", "regressed", "needs-decision"}:
                blocking_drift_by_requirement.setdefault(uid, []).append(finding)
    requirements = []
    for requirement in anchor.get("requirements", []):
        uid = requirement["requirement_uid"]
        observed = actual.get(uid, {})
        validated = (
            observed.get("state") == "validated"
            and not findings_by_requirement.get(uid)
            and not blocking_drift_by_requirement.get(uid)
        )
        requirements.append({
            "requirement_uid": uid,
            "display_id": requirement.get("display_id", uid),
            "statement": requirement.get("statement", ""),
            "status": "complete" if validated else ("incomplete" if checkpoint else "not-evidenced"),
            "evidence": observed.get("evidence", []),
            "findings": findings_by_requirement.get(uid, []),
            "drift": drift_by_requirement.get(uid, []),
        })

    scope_findings = [item for item in (architecture or {}).get("findings", []) if item.get("category") == "scope"]
    unresolved_drift = [
        item for item in (checkpoint or {}).get("drift", [])
        if item.get("classification") in {"new-drift", "regressed", "needs-decision"}
    ] + [
        item for item in (review or {}).get("findings", [])
        if item.get("classification") in {"new-drift", "regressed", "needs-decision"}
    ]
    saved_start = read(directory / "planning" / "start-report-v1.json") if (directory / "planning" / "start-report-v1.json").is_file() else {}
    start_report = saved_start.get("report", saved_start) if isinstance(saved_start, dict) else {}
    handoff = read(directory / "planning" / "execution-handoff-v1.json") if (directory / "planning" / "execution-handoff-v1.json").is_file() else {}
    execution_authority = handoff.get("execution_authority", {}) if isinstance(handoff, dict) else {}
    official_design, official_design_path = latest(directory / "aidlc-official" / "checkpoints", "design-plan-*.json")
    official_evidence, official_evidence_path = latest(directory / "aidlc-official" / "checkpoints", "evidence-checkpoint-*.json")
    official_handoff, official_handoff_path = latest(directory / "aidlc-official" / "checkpoints", "handoff-*.json")
    official_operations = sorted(path.relative_to(directory).as_posix() for path in (directory / "aidlc-official" / "checkpoints").glob("operations-*.json"))
    selected_names = {
        str(row.get("name")) for row in (start_report.get("guided_delivery", {}) or {}).get("selected", [])
        if isinstance(row, dict)
    }
    architecture_required = "Architecture Fitness Harness" in selected_names or any(
        any((row.get("architecture_contract") or {}).get(key) for key in ("required_paths", "protected_paths", "forbidden_imports"))
        for row in anchor.get("requirements", [])
    )
    behavior_required = "Behaviour Harness" in selected_names or behavior is not None
    maintainability_required = "Maintainability Harness" in selected_names
    passed_tiers = sorted({str(item.get("tier")) for item in receipts if item.get("outcome") == "pass"})
    failed_receipts = [item for item in receipts if item.get("outcome") != "pass"]
    receipt_outcomes = {str(item.get("outcome")) for item in receipts}
    if gate and gate.get("complete"):
        test_status = "pass"
    elif receipt_outcomes & {"fail", "timed-out"}:
        test_status = "fail"
    elif "blocked" in receipt_outcomes:
        test_status = "blocked"
    elif "unavailable" in receipt_outcomes:
        test_status = "unavailable"
    else:
        test_status = "not-evidenced"
    requirement_complete = sum(item["status"] == "complete" for item in requirements)

    def harness(name: str, artifact: dict[str, Any] | None, artifact_path: str | None, *, required: bool = False, complete: bool | None = None, basis: str) -> dict[str, Any]:
        if artifact is None:
            return {"name": name, "used": False, "status": "required-evidence-missing" if required else "not-selected", "basis": basis, "artifact": None}
        outcome = complete if complete is not None else artifact.get("complete")
        return {"name": name, "used": True, "status": status(outcome), "basis": basis, "artifact": artifact_path}

    harnesses = [
        harness("Requirement Completion Harness", checkpoint, checkpoint_path, required=True, complete=requirement_complete == len(requirements) and bool(review) and bool(gate) and review.get("complete") and gate.get("complete"), basis="approved anchor + checkpoint + completion review + evidence gate"),
        harness("Architecture Fitness Harness", architecture, architecture_path, required=architecture_required, basis="approved architecture contract or recorded architecture assessment"),
        harness("Behaviour Harness", behavior, behavior_path, basis="recorded approved-scenario assessment"),
        harness("Maintainability Harness", maintainability, maintainability_path, required=maintainability_required, basis="recorded refactor/maintainability assessment"),
        harness("Evidence-Aware Testing", gate, gate_path, required=True, basis="completion gate and validation receipts"),
    ]
    for item in harnesses:
        if item["name"] == "Evidence-Aware Testing" and item["status"] != "pass":
            item["status"] = test_status
        if item["name"] == "Requirement Completion Harness" and test_status in {"blocked", "unavailable"}:
            item["status"] = "incomplete"

    payload = {
        "schema_version": "1",
        "type": "tailtrail-completion-report",
        "run_id": run_id,
        "evidence_label": "local-evidence",
        "requirement_status": {
            "complete": requirement_complete,
            "total": len(requirements),
            "requirements": requirements,
        },
        "harnesses": harnesses,
        "changed_scope": {
            "status": "approved" if checkpoint and not scope_findings else ("changed-beyond-approved" if scope_findings else "not-assessed"),
            "changed_paths": (checkpoint or {}).get("changed_paths", []),
            "findings": scope_findings,
        },
        "architecture": {
            "status": status(architecture.get("complete") if architecture else None, not_selected=not architecture_required and architecture is None),
            "required": architecture_required,
            "findings": (architecture or {}).get("findings", []),
        },
        "behaviour": {
            "status": status(behavior.get("complete") if behavior else None, not_selected=not behavior_required),
            "required": behavior_required,
            "findings": (behavior or {}).get("findings", []),
        },
        "tests": {
            "status": test_status,
            "passed_tiers": passed_tiers,
            "failed_or_unavailable_receipts": failed_receipts,
            "findings": (gate or {}).get("findings", []),
        },
        "drift": {
            "status": "none-unresolved" if checkpoint and not unresolved_drift else ("unresolved" if unresolved_drift else "not-assessed"),
            "findings": unresolved_drift,
        },
        "recovery_checkpoint": {
            "status": "available" if boundary else ("not-needed" if not unresolved_drift and failures["status"] == "none-recorded" else "not-configured"),
            "boundary": boundary,
        },
        "execution_failures": failures,
        "debug": debug_section or {
            "debug_status": "required-evidence-missing" if debug_run else "not-triggered",
            "confidence_state": None, "domain_confidence_ceiling": None,
            "controls": [], "gaps": ["Debug closure section has not been finalized."] if debug_run else [],
            "authority": "section-only",
        },
        "token_usage": token_usage_summary(root, run_id, directory),
        "official_aidlc": {
            "perspectives": (official_design or {}).get("perspectives", []),
            "evidence_checkpoint": official_evidence_path,
            "evidence_status": "pass" if (official_evidence or {}).get("complete") else ("gap" if official_evidence else "not-triggered"),
            "handoff_reference": official_handoff_path,
            "operations_references": official_operations,
            "runtime": canonical_state.get("official_runtime", {"attached": False, "current_stage": None, "transition_count": 0}),
        },
        "canonical_state": {
            "status": canonical_state["status"],
            "valid": canonical_state["valid"],
            "issues": canonical_state["issues"],
        },
        "execution_authority": execution_authority or {
            "route": "not-recorded", "status": "unavailable",
            "auto_granted_action_classes": [], "separate_gate_triggers": [],
            "boundary": "No execution-authority artifact was saved for this run.",
        },
        "source_artifacts": {
            "approved_anchor": "anchors/approved-v1.json",
            "checkpoint": checkpoint_path,
            "completion_review": review_path,
            "completion_gate": gate_path,
            "architecture": architecture_path,
            "behaviour": behavior_path,
            "maintainability": maintainability_path,
            "recovery_boundary": "recovery/boundary.json" if boundary else None,
            "official_design": official_design_path,
            "official_evidence": official_evidence_path,
            "official_handoff": official_handoff_path,
            "debug_closure_section": debug_section_path.relative_to(directory).as_posix() if debug_section else None,
        },
        "boundary": "The report aggregates saved local artifacts. Missing or failed evidence is not reported as a pass.",
    }
    ready = (
        payload["requirement_status"]["complete"] == payload["requirement_status"]["total"]
        and payload["changed_scope"]["status"] == "approved"
        and payload["tests"]["status"] == "pass"
        and payload["drift"]["status"] == "none-unresolved"
        and failures["status"] != "unresolved"
        and payload["architecture"]["status"] in {"pass", "not-assessed"}
        and payload["behaviour"]["status"] in {"pass", "not-assessed"}
        and payload["canonical_state"]["valid"]
        and (not debug_run or payload["debug"]["debug_status"] == "pass")
    )
    payload["overall_status"] = "complete" if ready else "evidence-incomplete"
    execution_blockers: list[dict[str, Any]] = []
    seen_blockers: set[tuple[str, str, str]] = set()
    for item in failed_receipts:
        blocker = {
            "outcome": str(item.get("outcome")),
            "command_label": str(item.get("command_label", item.get("tier", "validation"))),
            "asserted_behavior": str(item.get("asserted_behavior", "Saved validation did not pass.")),
        }
        identity = (blocker["outcome"], blocker["command_label"], blocker["asserted_behavior"])
        if identity not in seen_blockers:
            seen_blockers.add(identity); execution_blockers.append(blocker)
    payload["implementation"] = {
        "status": "complete" if ready else ("blocked" if test_status in {"blocked", "unavailable"} or failures["status"] == "unresolved" else "incomplete"),
        "changed_paths": payload["changed_scope"]["changed_paths"],
        "blockers": execution_blockers,
        "boundary": "Implementation status is derived from saved changed paths, requirement checkpoints, and factual command receipts; it is not inferred from chat narration.",
    }
    payload["drift_learning"] = drift_learning_observation(directory, payload, record)
    payload["completion_learning"] = completion_learning_intake(root, directory, payload, record)
    payload["positive_learning"] = positive_learning_status(directory, payload)
    payload["source_artifacts"]["completion_learning"] = payload["completion_learning"]["artifact"]
    payload["source_artifacts"]["positive_learning"] = payload["positive_learning"]["artifact"]
    token_usage = payload["token_usage"]
    payload["tailtrail_status"] = [
        {
            "control": "Planning Lock and approved anchor",
            "status": "approved",
            "detail": "immutable approved requirement boundary",
        },
        {
            "control": "Execution authority",
            "status": payload["execution_authority"]["status"],
            "detail": f"{payload['execution_authority']['route']}; auto-granted: {', '.join(payload['execution_authority'].get('auto_granted_action_classes', [])) or 'none'}",
        },
        {
            "control": "Implementation delivery",
            "status": payload["implementation"]["status"],
            "detail": f"{len(payload['implementation']['changed_paths'])} changed path(s); {len(payload['implementation']['blockers'])} saved blocker(s)",
        },
        {
            "control": "Official AI-DLC evidence checkpoint",
            "status": payload["official_aidlc"]["evidence_status"],
            "detail": official_evidence_path or "not triggered for this run",
        },
        {
            "control": "Canonical run state",
            "status": payload["canonical_state"]["status"],
            "detail": f"{len(payload['canonical_state']['issues'])} ownership or projection issue(s)",
        },
        {
            "control": "Changed scope",
            "status": payload["changed_scope"]["status"],
            "detail": f"{len(payload['changed_scope']['changed_paths'])} saved changed path(s)",
        },
        *[
            {
                "control": item["name"],
                "status": item["status"],
                "detail": item["basis"],
            }
            for item in harnesses
        ],
        {
            "control": "Drift control",
            "status": payload["drift"]["status"],
            "detail": f"{len(payload['drift']['findings'])} unresolved finding(s)",
        },
        {
            "control": "Context Continuity Harness",
            "status": "recorded" if payload["drift_learning"]["status"] == "recorded" else "not-triggered",
            "detail": payload["drift_learning"]["artifact"] or "no unresolved drift required a correction-memory packet",
        },
        {
            "control": "Safe Git Recovery",
            "status": payload["recovery_checkpoint"]["status"],
            "detail": "task recovery boundary" if boundary else "no recovery boundary was needed or recorded",
        },
        {
            "control": "Execution failure handling",
            "status": failures["status"],
            "detail": f"{failures['count']} saved failure record(s)",
        },
        {
            "control": "Debug Harness closure",
            "status": payload["debug"]["debug_status"],
            "detail": (f"confidence {payload['debug'].get('confidence_state')} / ceiling {payload['debug'].get('domain_confidence_ceiling')}") if debug_run else "not a Debug Harness run",
        },
        {
            "control": "Gap learning",
            "status": "gap-recorded" if payload["completion_learning"]["status"] in {"captured", "reused"} else payload["completion_learning"]["status"],
            "detail": ("incomplete-delivery observation only; " + payload["completion_learning"]["artifact"]) if payload["completion_learning"]["artifact"] else payload["completion_learning"]["boundary"],
        },
        {
            "control": "Guarded positive learning",
            "status": payload["positive_learning"]["status"],
            "detail": payload["positive_learning"]["artifact"] or payload["positive_learning"]["boundary"],
        },
        {
            "control": "Token estimate",
            "status": "estimated" if token_usage["planning_estimate_tokens"] is not None else "unavailable",
            "detail": f"{token_usage['planning_estimate_tokens']} focused tokens" if token_usage["planning_estimate_tokens"] is not None else "the Start plan did not save an estimate",
        },
        {
            "control": "Actual model tokens",
            "status": token_usage["status"],
            "detail": f"{token_usage['actual_tailtrail_tokens']} tokens from {token_usage['telemetry_records']} linked record(s)" if token_usage["status"] == "measured" else "host/provider telemetry was not linked to this run ID",
        },
    ]
    if record:
        reports = directory / "completion-reports"
        reports.mkdir(parents=True, exist_ok=True)
        path = reports / f"report-{len(list(reports.glob('report-*.json'))) + 1}.json"
        L.atomic_json(path, payload)
        L.append_event(root, run_id, "completion_report_created", {
            "artifact": path.relative_to(directory).as_posix(),
            "overall_status": payload["overall_status"],
            "harnesses": [{"name": item["name"], "used": item["used"], "status": item["status"]} for item in harnesses],
            "completion_learning": payload["completion_learning"]["status"],
        })
        payload["run_artifact"] = path.as_posix()
    return payload


def render(payload: dict[str, Any]) -> str:
    requirements = payload["requirement_status"]
    tests = payload["tests"]
    tiers = " + ".join(tests["passed_tiers"]) or "no passing test receipt recorded"
    lines = [
        "# TailTrail Completion Report",
        "",
        f"Run: `{payload['run_id']}`",
        f"Overall: **{payload['overall_status']}**",
        f"Implementation: **{payload['implementation']['status']}**",
        "",
        f"Requirement delivery: **{requirements['complete']}/{requirements['total']} complete**",
        f"Overall evidence: **tests {tests['status']} ({tiers}); drift {payload['drift']['status']}**",
        "",
        "## Requirement delivery status",
        "",
        "| Requirement | Status | Proof | Drift |",
        "| --- | --- | --- | --- |",
    ]
    for requirement in requirements["requirements"]:
        proof = f"{len(requirement['evidence'])} saved item(s)"
        drift = ", ".join(sorted({str(item.get("classification")) for item in requirement["drift"] if item.get("classification")})) or ("not assessed" if payload["drift"]["status"] == "not-assessed" else "none recorded")
        lines.append(f"| {table_cell(requirement['display_id'])} - {table_cell(requirement['statement'])} | {table_cell(requirement['status'])} | {table_cell(proof)} | {table_cell(drift)} |")
    if payload.get("debug", {}).get("debug_status") != "not-triggered":
        lines.extend(["", "## Debug investigation status", "", f"Debug confidence: **{table_cell(payload['debug'].get('confidence_state'))}** (domain ceiling: **{table_cell(payload['debug'].get('domain_confidence_ceiling'))}**)", "", "| Debug control | Status | Evidence / boundary |", "| --- | --- | --- |"])
        for control in payload["debug"].get("controls", []):
            lines.append(f"| {table_cell(control.get('control'))} | {table_cell(control.get('status'))} | {table_cell(control.get('detail'))} |")
    if payload["implementation"]["blockers"]:
        lines.extend(["", "## Execution blockers", "", "| Outcome | Check | Boundary |", "| --- | --- | --- |"])
        for blocker in payload["implementation"]["blockers"]:
            lines.append(f"| {table_cell(blocker['outcome'])} | {table_cell(blocker['command_label'])} | {table_cell(blocker['asserted_behavior'])} |")
    lines.extend([
        "",
        "## TailTrail control status",
        "",
        "| Control | Status | Evidence / boundary |",
        "| --- | --- | --- |",
    ])
    for control in payload["tailtrail_status"]:
        lines.append(f"| {table_cell(control['control'])} | {table_cell(control['status'])} | {table_cell(control['detail'])} |")
    return "\n".join(lines) + "\n"


def show(root: Path, run_id: str, sequence: int | None = None) -> dict[str, Any]:
    directory = L.state_dir(root, run_id) / "completion-reports"
    reports = sorted(directory.glob("report-*.json"))
    if not reports:
        raise ValueError("no completion report exists")
    if sequence is None:
        return read(reports[-1])
    path = directory / f"report-{sequence}.json"
    if not path.is_file():
        raise ValueError(f"completion report {sequence} does not exist")
    return read(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--show", action="store_true", help="Read the latest saved report without creating one.")
    parser.add_argument("--sequence", type=int)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    try:
        result = show(args.root.resolve(), args.run_id, args.sequence) if args.show else build(args.root.resolve(), args.run_id)
        print(json.dumps(result, indent=2, sort_keys=True) if args.format == "json" else render(result), end="")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Completion report error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
