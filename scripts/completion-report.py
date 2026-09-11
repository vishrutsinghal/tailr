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


def learning_receipts_module() -> Any:
    spec = importlib.util.spec_from_file_location("completion_report_learning_receipts", ROOT / "scripts" / "learning-use-receipt.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


L = ledger()
STATE = canonical_state_module()
RECEIPTS = learning_receipts_module()


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest(directory: Path, pattern: str) -> tuple[dict[str, Any] | None, str | None]:
    files = list(directory.glob(pattern))
    if not files:
        return None, None
    path = max(files, key=lambda value: (value.stat().st_mtime_ns, value.name))
    return read(path), path.relative_to(directory.parents[0]).as_posix()


def latest_closure_receipts(root: Path, directory: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Read only the receipts selected by the newest checkpointed closure record.

    Validation receipt files are append-only audit history. Aggregating every
    historical file makes a corrected rerun inherit stale failures and can also
    turn one host assertion into many apparent results. The closure record is
    the canonical snapshot for one assessment.
    """
    records: list[tuple[int, int, Path, dict[str, Any]]] = []
    for path in (directory / "closure-records").glob("closure-*.json"):
        item = read(path)
        if item.get("type") != "tailtrail-closure-record":
            continue
        checkpoint = str(item.get("checkpoint", ""))
        digits = "".join(character for character in Path(checkpoint).stem if character.isdigit())
        records.append((int(digits or 0), path.stat().st_mtime_ns, path, item))
    if not records:
        return [], []
    _, _, _, selected = max(records, key=lambda row: (row[0], row[1], row[2].name))
    refs = [str(value) for value in selected.get("receipt_artifacts", []) if isinstance(value, str)]
    receipts = [read(root / reference) for reference in refs if (root / reference).is_file()]
    return receipts, refs


def receipt_tiers(receipt: dict[str, Any]) -> list[str]:
    values = receipt.get("tiers")
    if isinstance(values, list):
        return [str(value) for value in values if value]
    return [str(receipt["tier"])] if receipt.get("tier") else []


def receipt_requirement_uids(receipt: dict[str, Any]) -> list[str]:
    values = receipt.get("requirement_uids")
    if isinstance(values, list):
        return [str(value) for value in values if value]
    return [str(receipt["requirement_uid"])] if receipt.get("requirement_uid") else []


def consolidated_receipts(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge requirement-fanned copies of one validation observation.

    Legacy closure recording wrote one receipt per requirement even when a
    single command covered the full slice. The append-only files remain
    untouched, while the human report presents that observation once and
    lists every affected requirement.
    """
    grouped: list[dict[str, Any]] = []
    by_observation: dict[tuple[Any, ...], dict[str, Any]] = {}
    for source in receipts:
        tiers = tuple(receipt_tiers(source))
        key = (
            source.get("command_label"), source.get("command"), tiers,
            source.get("outcome"), source.get("evidence_quality"),
            source.get("exit_code"), source.get("started_at"), source.get("finished_at"),
            source.get("stdout_sha256"), source.get("stderr_sha256"),
            source.get("stdout_artifact"), source.get("stderr_artifact"), source.get("artifact_path"),
        )
        current = by_observation.get(key)
        if current is None:
            current = dict(source)
            current["tiers"] = list(tiers)
            current["requirement_uids"] = []
            current["source_receipt_count"] = 0
            grouped.append(current)
            by_observation[key] = current
        for uid in receipt_requirement_uids(source):
            if uid not in current["requirement_uids"]:
                current["requirement_uids"].append(uid)
        current["source_receipt_count"] += 1
    return grouped


def required_validation_checks(anchor: dict[str, Any]) -> list[dict[str, Any]]:
    """Return one approved validation check with all covered requirements."""
    grouped: list[dict[str, Any]] = []
    by_command: dict[str, dict[str, Any]] = {}
    for requirement in anchor.get("requirements", []):
        if not isinstance(requirement, dict):
            continue
        contract = requirement.get("validation_contract")
        if not isinstance(contract, dict) or contract.get("state") == "not-required":
            continue
        saved_checks = [row for row in contract.get("checks", []) if isinstance(row, dict)]
        if saved_checks:
            checks = [{
                "command": str(row.get("command", "")),
                "tiers": [str(value) for value in row.get("tiers", []) if value],
                "candidate_paths": [str(value) for value in row.get("candidate_paths", []) if value],
            } for row in saved_checks if row.get("command")]
        else:
            checks = [{
                "command": str(command),
                "tiers": [str(value) for value in contract.get("tiers", []) if value],
                "candidate_paths": [str(value) for value in contract.get("candidate_paths", []) if value],
            } for command in contract.get("commands", []) if command]
        uid = str(requirement.get("requirement_uid", ""))
        for check in checks:
            command = check["command"]
            current = by_command.get(command)
            if current is None:
                current = {"command": command, "tiers": [], "requirement_uids": [], "candidate_paths": []}
                grouped.append(current)
                by_command[command] = current
            for tier in check["tiers"]:
                if tier not in current["tiers"]:
                    current["tiers"].append(tier)
            if uid and uid not in current["requirement_uids"]:
                current["requirement_uids"].append(uid)
            for path in check["candidate_paths"]:
                if path and str(path) not in current["candidate_paths"]:
                    current["candidate_paths"].append(str(path))
    return grouped


def aggregate_tiers(receipts: list[dict[str, Any]]) -> dict[str, str]:
    """Collapse current authoritative evidence with non-pass precedence."""
    tiers = sorted({tier for receipt in receipts for tier in receipt_tiers(receipt)})
    result: dict[str, str] = {}
    precedence = ("fail", "timed-out", "blocked", "unavailable")
    for tier in tiers:
        matching = [receipt for receipt in receipts if tier in receipt_tiers(receipt)]
        authoritative = [receipt for receipt in matching if receipt.get("evidence_quality") in {"trusted", "attested"}]
        outcomes = {str(receipt.get("outcome")) for receipt in authoritative}
        reported_outcomes = {str(receipt.get("outcome")) for receipt in matching}
        result[tier] = next((value for value in precedence if value in reported_outcomes), "pass" if "pass" in outcomes else "unverified" if matching else "not-evidenced")
    return result


def status(value: bool | None, *, not_selected: bool = False) -> str:
    if not_selected:
        return "not-assessed"
    if value is None:
        return "unavailable"
    return "pass" if value else "fail"


def report_text(value: Any) -> str:
    """Render saved evidence as one safe line without table-specific escaping."""
    if value is None:
        return "-"
    return " ".join(str(value).split()) or "-"


def append_records(
    lines: list[str],
    records: list[tuple[str, list[tuple[str, str]]]],
    *,
    empty: str | None = None,
) -> None:
    """Render responsive report records that remain readable in narrow hosts.

    Markdown tables size every row against the widest prose cell. Completion
    evidence contains paths, commands, and boundaries, so those tables wrap
    unpredictably in Codex, Claude, and Copilot panes. A labelled stack keeps
    each record together and gives wrapped text a stable hanging indentation.
    """
    if not records:
        if empty:
            lines.append(f"- {empty}")
        return
    for title, fields in records:
        lines.append(f"- **{report_text(title)}**")
        for label, value in fields:
            lines.append(f"  - **{report_text(label)}:** {value}")


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
    tailtrail_totals: list[int] = []
    tailtrail_identities: set[tuple[str, str]] = set()
    baseline_totals: dict[str, list[int]] = {"loose-prompt": [], "aidlc": []}
    baseline_identities: dict[str, set[tuple[str, str]]] = {"loose-prompt": set(), "aidlc": set()}

    def measured_total(value: Any) -> int | None:
        total = value.get("total_tokens") if isinstance(value, dict) else None
        return total if isinstance(total, int) and not isinstance(total, bool) and total >= 0 else None

    def identity(item: dict[str, Any]) -> tuple[str, str] | None:
        provider = str(item.get("provider", "")).strip()
        model = str(item.get("model", "")).strip()
        if not provider or not model or model == "unknown":
            return None
        return provider, model

    for item in records:
        variant = str(item.get("variant", ""))
        item_identity = identity(item)
        if variant in {"tailtrail", "loose-prompt", "aidlc"}:
            total = measured_total(item.get("usage"))
            if total is None:
                continue
            if variant == "tailtrail":
                tailtrail_totals.append(total)
                if item_identity:
                    tailtrail_identities.add(item_identity)
            else:
                baseline_totals[variant].append(total)
                if item_identity:
                    baseline_identities[variant].add(item_identity)
            continue

        # Backward-compatible paired telemetry. Older records represent a
        # loose-prompt comparison unless they explicitly name AIDLC.
        tailtrail_total = measured_total(item.get("tailtrail"))
        baseline_total = measured_total(item.get("baseline"))
        if tailtrail_total is not None:
            tailtrail_totals.append(tailtrail_total)
            if item_identity:
                tailtrail_identities.add(item_identity)
        if baseline_total is not None:
            baseline_kind = "aidlc" if str(item.get("baseline_kind", "")) == "aidlc" else "loose-prompt"
            baseline_totals[baseline_kind].append(baseline_total)
            if item_identity:
                baseline_identities[baseline_kind].add(item_identity)

    measured = bool(tailtrail_totals)
    actual = sum(tailtrail_totals) if measured else None
    context_estimate = {
        "status": (
            "estimated"
            if isinstance(posture.get("repository_ceiling_tokens"), int)
            and isinstance(posture.get("estimated_saved_tokens"), int)
            else "unavailable"
        ),
        "comparison_basis": (
            "scoped-files"
            if isinstance(posture.get("planned_working_set_tokens"), int)
            and isinstance(posture.get("scoped_file_ceiling_tokens"), int)
            else "legacy-repository-ceiling"
        ),
        "planned_working_set_tokens": posture.get("planned_working_set_tokens"),
        "scoped_file_ceiling_tokens": posture.get("scoped_file_ceiling_tokens"),
        "forecast_confidence": posture.get("forecast_confidence"),
        "repository_ceiling_tokens": posture.get("repository_ceiling_tokens"),
        "repository_file_count": posture.get("repository_file_count"),
        "scoped_tokens": estimate,
        "estimated_saved_tokens": posture.get("estimated_saved_tokens"),
        "estimated_reduction_percent": posture.get("estimated_reduction_percent"),
        "saving_techniques": list(posture.get("saving_techniques", [])) if isinstance(posture.get("saving_techniques"), list) else [],
        "boundary": posture.get("repository_boundary"),
    }
    comparisons: dict[str, dict[str, Any]] = {}
    for baseline_kind in ("loose-prompt", "aidlc"):
        values = baseline_totals[baseline_kind]
        if not measured:
            comparisons[baseline_kind] = {
                "status": "unavailable",
                "reason": "TailTrail host/API usage is not linked to this run.",
            }
        elif not values:
            comparisons[baseline_kind] = {
                "status": "unavailable",
                "reason": f"No paired {baseline_kind} host/API baseline is linked to this run.",
            }
        elif (
            tailtrail_identities
            and baseline_identities[baseline_kind]
            and tailtrail_identities != baseline_identities[baseline_kind]
        ):
            comparisons[baseline_kind] = {
                "status": "incomparable",
                "reason": "The baseline and TailTrail usage use different provider/model identities.",
            }
        else:
            baseline = sum(values)
            saved = baseline - int(actual)
            comparisons[baseline_kind] = {
                "status": "measured",
                "baseline_tokens": baseline,
                "tailtrail_tokens": actual,
                "saved_tokens": saved,
                "reduction_percent": round((saved / baseline) * 100, 2) if baseline else None,
                "baseline_records": len(values),
            }
    return {
        "planning_estimate_tokens": estimate,
        "status": "measured" if measured else "unavailable",
        "actual_tailtrail_tokens": actual,
        "telemetry_records": len(tailtrail_totals),
        "comparisons": comparisons,
        "context_estimate": context_estimate,
        "boundary": "Exact usage comes only from host/provider metadata linked to this run ID. Exact savings additionally require a paired loose-prompt or AIDLC baseline for the same provider and model.",
    }


def reconcile_learning_saving_evidence(
    token_usage: dict[str, Any], learning_use: dict[str, Any]
) -> None:
    """Claim learning reuse only when an applied receipt proves it."""
    context = token_usage.get("context_estimate")
    if not isinstance(context, dict):
        return
    techniques = [
        str(value)
        for value in context.get("saving_techniques", [])
        if str(value) and str(value) != "Project learning reuse"
    ]
    applied = [
        row
        for row in learning_use.get("receipts", [])
        if isinstance(row, dict) and row.get("decision") == "applied"
    ]
    artifact = str(learning_use.get("artifact") or "").strip()
    references = [
        f"{artifact}#{row.get('receipt_id')}"
        for row in applied
        if artifact and row.get("receipt_id")
    ]
    if references:
        techniques.append("Project learning reuse")
    context["saving_techniques"] = list(dict.fromkeys(techniques))
    context["learning_evidence_references"] = list(dict.fromkeys(references))


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
        learner.V3.capture_legacy_event(root, event, captured_by="Completion Report")
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
    receipts, receipt_refs = latest_closure_receipts(root, directory)
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
        implementation_state = observed.get("implementation_state", "implemented" if observed.get("state") in {"validated", "implemented-not-validated", "implemented-unverified"} else "not-evidenced")
        requirements.append({
            "requirement_uid": uid,
            "display_id": requirement.get("display_id", uid),
            "statement": requirement.get("statement", ""),
            "status": "complete" if validated else ("implemented-unverified" if implementation_state == "implemented" else "not-evidenced"),
            "implementation_status": implementation_state,
            "verification_status": observed.get("verification_state", "pass" if observed.get("state") == "validated" else "not-evidenced"),
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
    tier_results = aggregate_tiers(receipts)
    passed_tiers = sorted(tier for tier, outcome in tier_results.items() if outcome == "pass")
    failed_receipts = [item for item in receipts if item.get("evidence_quality") in {"trusted", "attested"} and item.get("outcome") != "pass"]
    unverified_receipts = [item for item in receipts if item.get("evidence_quality") not in {"trusted", "attested"}]
    receipt_outcomes = set(tier_results.values())
    if gate and gate.get("complete"):
        test_status = "pass"
    elif receipt_outcomes & {"fail", "timed-out"}:
        test_status = "fail"
    elif "blocked" in receipt_outcomes:
        test_status = "blocked"
    elif "unavailable" in receipt_outcomes:
        test_status = "unavailable"
    elif "unverified" in receipt_outcomes:
        test_status = "unverified"
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
            "tier_results": tier_results,
            "required_checks": required_validation_checks(anchor),
            "receipts": receipts,
            "receipt_refs": receipt_refs,
            "failed_or_unavailable_receipts": failed_receipts,
            "unverified_receipts": unverified_receipts,
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
            "reproduction_proof": {
                "status": "evidence-incomplete" if debug_run else "not-triggered",
                "approved_revision": None,
                "trigger": None,
                "steps": [],
                "pre_fix": None,
                "post_fix": None,
                "boundary": "Debug closure has not yet recorded factual before-and-after reproduction evidence." if debug_run else "Not a Debug Harness run.",
            },
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
    for item in [*failed_receipts, *unverified_receipts]:
        blocker = {
            "outcome": str(item.get("outcome")) if item not in unverified_receipts else (f"reported-{item.get('outcome')} (unverified)" if item.get("outcome") != "pass" else "unverified"),
            "command_label": str(item.get("command_label", item.get("tier", "validation"))),
            "asserted_behavior": str(item.get("asserted_behavior", "Saved validation did not pass.")),
            "command": str(item.get("command", "")),
            "exit_code": item.get("exit_code"),
            "duration_ms": item.get("duration_ms"),
            "evidence_quality": str(item.get("evidence_quality", "declared")),
            "stdout_artifact": item.get("stdout_artifact"),
            "stderr_artifact": item.get("stderr_artifact"),
        }
        identity = (blocker["outcome"], blocker["command_label"], blocker["asserted_behavior"])
        if identity not in seen_blockers:
            seen_blockers.add(identity); execution_blockers.append(blocker)
    changed_paths = payload["changed_scope"]["changed_paths"]
    implementation_status = "implemented" if changed_paths and payload["changed_scope"]["status"] == "approved" else ("scope-drift" if changed_paths else "not-evidenced")
    payload["implementation"] = {
        "status": implementation_status,
        "changed_paths": payload["changed_scope"]["changed_paths"],
        "blockers": execution_blockers,
        "boundary": "Implementation presence is derived from saved changed-path evidence and approved scope. Verification is reported separately and only authoritative command evidence can establish correctness.",
    }
    reports = directory / "completion-reports"
    report_path = reports / f"report-{len(list(reports.glob('report-*.json'))) + 1}.json"
    report_ref = report_path.relative_to(root).as_posix()
    payload["learning_use"] = RECEIPTS.attribute_completion(
        root, run_id, payload, record=record, completion_ref=report_ref,
    )
    reconcile_learning_saving_evidence(payload["token_usage"], payload["learning_use"])
    payload["drift_learning"] = drift_learning_observation(directory, payload, record)
    payload["completion_learning"] = completion_learning_intake(root, directory, payload, record)
    payload["positive_learning"] = positive_learning_status(directory, payload)
    payload["source_artifacts"]["completion_learning"] = payload["completion_learning"]["artifact"]
    payload["source_artifacts"]["positive_learning"] = payload["positive_learning"]["artifact"]
    payload["source_artifacts"]["learning_use_receipts"] = "learning/use-receipts.jsonl" if payload["learning_use"]["artifact"] else None
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
            "control": "Learning use attribution",
            "status": payload["learning_use"]["status"],
            "detail": f"{payload['learning_use']['attributed']} requirement-linked receipt(s); observed association only",
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
        reports.mkdir(parents=True, exist_ok=True)
        L.atomic_json(report_path, payload)
        L.append_event(root, run_id, "completion_report_created", {
            "artifact": report_path.relative_to(directory).as_posix(),
            "overall_status": payload["overall_status"],
            "harnesses": [{"name": item["name"], "used": item["used"], "status": item["status"]} for item in harnesses],
            "completion_learning": payload["completion_learning"]["status"],
            "learning_use": payload["learning_use"]["status"],
        })
        payload["run_artifact"] = report_path.as_posix()
    return payload


def render(payload: dict[str, Any]) -> str:
    requirements = payload["requirement_status"]
    tests = payload["tests"]
    tiers = " + ".join(tests["passed_tiers"]) or "none"
    implemented = sum(requirement.get("implementation_status") == "implemented" for requirement in requirements["requirements"])
    receipts = consolidated_receipts(tests.get("receipts", []))
    required_checks = tests.get("required_checks", [])
    requirement_ids = {
        str(requirement.get("requirement_uid")): str(requirement.get("display_id"))
        for requirement in requirements["requirements"]
    }

    def check_state(check: dict[str, Any]) -> str:
        matching = [item for item in receipts if item.get("command") == check.get("command")]
        required_tiers = set(str(value) for value in check.get("tiers", []))
        passing_tiers = {
            tier for item in matching
            if item.get("outcome") == "pass" and item.get("evidence_quality") in {"trusted", "attested"}
            for tier in receipt_tiers(item)
        }
        if required_tiers and required_tiers.issubset(passing_tiers):
            return "pass"
        for outcome in ("fail", "timed-out", "blocked", "unavailable"):
            authoritative = next((item for item in matching if item.get("outcome") == outcome and item.get("evidence_quality") in {"trusted", "attested"}), None)
            if authoritative:
                return outcome
            declared = next((item for item in matching if item.get("outcome") == outcome), None)
            if declared:
                return f"reported-{outcome} (unverified)"
        return "unverified" if matching else "not-evidenced"

    required_results = [(check, check_state(check)) for check in required_checks]
    incomplete_checks = [(check, state) for check, state in required_results if state != "pass"]
    lines = [
        "# TailTrail Completion Report",
        "",
        f"Run: `{payload['run_id']}`",
        f"Overall: **{payload['overall_status']}**",
        f"Implementation: **{payload['implementation']['status']}**",
        "Detail: **comprehensive** (closure is never reduced by the Start-plan detail level)",
        "",
        f"Implementation coverage: **{implemented}/{requirements['total']} requirements have approved changed-path evidence**",
        f"Verified delivery: **{requirements['complete']}/{requirements['total']} requirements complete**",
        f"Verification: **{tests['status']}**; passing tiers: **{tiers}**; drift: **{payload['drift']['status']}**",
    ]

    lines.extend(["", "## What needs attention", ""])
    attention: list[str] = []
    if payload["overall_status"] == "complete":
        attention.append("No closure blocker remains; every required tier has authoritative passing evidence.")
    else:
        if incomplete_checks:
            attention.append(f"{len(incomplete_checks)} approved validation command(s) still need authoritative passing evidence.")
        elif not required_checks and tests.get("status") != "pass":
            attention.append("No runnable approved validation command is saved; resolve the proof command before claiming completion.")
        if payload.get("behaviour", {}).get("status") == "fail":
            attention.append(f"Behaviour proof has {len(payload['behaviour'].get('findings', []))} unresolved finding(s).")
        if payload.get("changed_scope", {}).get("status") != "approved":
            attention.append(f"Changed scope is {report_text(payload['changed_scope'].get('status'))}.")
        if payload.get("drift", {}).get("status") == "unresolved":
            attention.append(f"{len(payload['drift'].get('findings', []))} unresolved drift finding(s) remain.")
    lines.extend(f"- {item}" for item in attention)

    lines.extend(["", "## Requirement status", ""])
    requirement_records = []
    for requirement in requirements["requirements"]:
        drift = ", ".join(sorted({str(item.get("classification")) for item in requirement["drift"] if item.get("classification")})) or ("not assessed" if payload["drift"]["status"] == "not-assessed" else "none recorded")
        requirement_records.append((
            report_text(requirement["display_id"]),
            [
                ("Requirement", report_text(requirement["statement"])),
                ("Implementation", f"**{report_text(requirement.get('implementation_status', 'not-evidenced'))}**"),
                ("Verification", f"**{report_text(requirement.get('verification_status', 'not-evidenced'))}**"),
                ("Delivery", f"**{report_text(requirement['status'])}**"),
                ("Drift", report_text(drift)),
            ],
        ))
    append_records(lines, requirement_records, empty="No canonical requirement was recorded.")
    if payload.get("debug", {}).get("debug_status") != "not-triggered":
        lines.extend(["", "## Debug investigation status", "", f"Debug confidence: **{report_text(payload['debug'].get('confidence_state'))}** (domain ceiling: **{report_text(payload['debug'].get('domain_confidence_ceiling'))}**)", ""])
        append_records(lines, [
            (
                report_text(control.get("control")),
                [
                    ("Status", f"**{report_text(control.get('status'))}**"),
                    ("Evidence / boundary", report_text(control.get("detail"))),
                ],
            )
            for control in payload["debug"].get("controls", [])
        ], empty="No Debug control record was saved.")
        reproduction = payload["debug"].get("reproduction_proof") or {}
        lines.extend([
            "",
            "## Reproduction proof",
            "",
            f"Status: **{report_text(reproduction.get('status', 'evidence-incomplete'))}**.",
            f"Approved revision: **{report_text(reproduction.get('approved_revision'))}**.",
            f"Trigger: {report_text(reproduction.get('trigger'))}",
            "",
            "### Sequential reproduction steps",
            "",
        ])
        steps = reproduction.get("steps") if isinstance(reproduction.get("steps"), list) else []
        if steps:
            lines.extend(f"{index}. {report_text(step)}" for index, step in enumerate(steps, start=1))
        else:
            lines.append("1. No approved reproduction sequence has been recorded yet.")
        for heading, key in (("Before-fix attempt", "pre_fix"), ("Post-fix rerun", "post_fix")):
            attempt = reproduction.get(key)
            lines.extend(["", f"### {heading}", ""])
            if not isinstance(attempt, dict):
                lines.append("- No factual attempt has been recorded.")
                continue
            lines.extend([
                f"- Attempt: **{report_text(attempt.get('attempt'))}**",
                f"- Outcome: **{report_text(attempt.get('outcome'))}**",
                f"- Evidence event: `{report_text(attempt.get('evidence_event_id'))}`",
                f"- Evidence fingerprint: `{report_text(attempt.get('evidence_fingerprint'))}`",
                f"- Observed: {report_text(attempt.get('observed_summary'))}",
                "- Exact command:",
                "",
                f"    {report_text(attempt.get('command'))}",
            ])
        lines.extend(["", f"Boundary: {report_text(reproduction.get('boundary'))}"])
    lines.extend([
        "",
        "## Changed files",
        "",
        f"Status: **{report_text(payload['changed_scope']['status'])}**.",
        "",
    ])
    for item in payload["changed_scope"].get("changed_paths", []):
        if isinstance(item, dict):
            lines.append(f"- `{report_text(item.get('path'))}`")
        else:
            lines.append(f"- `{report_text(item)}`")
    if not payload["changed_scope"].get("changed_paths"):
        lines.append("- No changed path receipt was recorded.")
    lines.extend([
        "",
        "## Validation evidence",
        "",
        f"Verification status: **{report_text(tests['status'])}**. Passing tiers: **{report_text(tiers)}**.",
        "",
    ])
    command_records = []
    required_commands = {str(check.get("command")) for check in required_checks}
    displayed_receipts = [
        receipt for receipt in receipts
        if str(receipt.get("command")) in required_commands
        or (
            receipt.get("evidence_quality") in {"trusted", "attested"}
            and receipt.get("outcome") != "pass"
        )
    ]
    supporting_receipts = [receipt for receipt in receipts if receipt not in displayed_receipts]
    for receipt in displayed_receipts:
        receipt_tier_text = ", ".join(receipt_tiers(receipt)) or "-"
        uids = receipt_requirement_uids(receipt)
        affected = ", ".join(sorted((requirement_ids.get(uid, uid) for uid in uids))) or "not linked"
        quality = str(receipt.get("evidence_quality", "declared"))
        outcome = str(receipt.get("outcome", "not-evidenced"))
        displayed_outcome = outcome if quality in {"trusted", "attested"} else f"reported {outcome}; unverified"
        telemetry = (
            f"exit {receipt.get('exit_code')}; {receipt.get('duration_ms')} ms"
            if receipt.get("exit_code") is not None and receipt.get("duration_ms") is not None
            else "not captured"
        )
        fields = [
            ("Role", "required proof" if str(receipt.get("command")) in required_commands else "supporting check"),
            ("Requirements", report_text(affected)),
            ("Tiers", report_text(receipt_tier_text)),
            ("Result", f"**{report_text(displayed_outcome)}**"),
            ("Telemetry", report_text(telemetry)),
            ("Evidence quality", report_text(quality)),
        ]
        if receipt.get("command"):
            fields.insert(4, ("Command", f"`{report_text(receipt.get('command'))}`"))
        artifacts = ", ".join(value for value in (receipt.get("stdout_artifact"), receipt.get("stderr_artifact")) if value) or receipt.get("artifact_path")
        if artifacts:
            fields.append(("Output", report_text(artifacts)))
        if int(receipt.get("source_receipt_count", 1)) > 1:
            fields.append(("Consolidated legacy receipts", report_text(receipt["source_receipt_count"])))
        label = receipt.get("command_label") or (f"{receipt_tier_text} validation" if receipt_tier_text != "-" else "Validation evidence")
        command_records.append((report_text(label), fields))
    append_records(lines, command_records, empty="No required proof or authoritative failure needs detailed display.")
    if supporting_receipts:
        authoritative_failures = sum(
            item.get("evidence_quality") in {"trusted", "attested"} and item.get("outcome") != "pass"
            for item in supporting_receipts
        )
        lines.extend([
            "",
            f"Supporting checks: **{len(supporting_receipts)} consolidated observation(s)** retained in JSON; "
            f"authoritative failures: **{authoritative_failures}**.",
        ])

    lines.extend(["", "### Harness result", ""])
    used_harnesses = [item for item in payload["harnesses"] if item.get("used") or item.get("status") == "required-evidence-missing"]
    for harness in used_harnesses:
        artifact = f"; `{report_text(harness.get('artifact'))}`" if harness.get("artifact") else ""
        lines.append(f"- **{report_text(harness['name'])}:** {report_text(harness['status'])}{artifact}")
    if not used_harnesses:
        lines.append("- No Harness assessment was selected.")

    receipt_refs = tests.get("receipt_refs", [])
    if receipt_refs:
        parents = {Path(str(reference)).parent.as_posix() for reference in receipt_refs}
        archive = next(iter(parents)) if len(parents) == 1 else "multiple validation-receipt directories"
        lines.extend(["", f"Audit archive: **{len(receipt_refs)} receipt file(s)** retained under `{archive}`. Exact references remain in the JSON report."])
    else:
        lines.extend(["", "Audit archive: no validation receipt file was recorded."])

    learning_use = payload["learning_use"]
    learning_receipts = [item for item in learning_use.get("receipts", []) if isinstance(item, dict)]
    if learning_receipts:
        lines.extend(["", "## Learning use and closure attribution", ""])
        learning_records: list[tuple[str, list[tuple[str, str]]]] = []
        for receipt in learning_receipts:
            learning_records.append((
                f"{report_text(receipt.get('decision_type'))}: {report_text(receipt.get('decision'))}",
                [
                    ("Requirements", ", ".join(report_text(value) for value in receipt.get("requirement_uids", [])) or "-"),
                    ("Observed association", report_text(receipt.get("association"))),
                    ("Utility delta", report_text(receipt.get("utility_delta"))),
                ],
            ))
        append_records(lines, learning_records)
        lines.append("- Attribution is an observed association, not a causal claim or execution authority.")

    token_usage = payload["token_usage"]
    lines.extend(["", "## Token impact", ""])
    if token_usage.get("status") == "measured":
        lines.append(
            f"- **TailTrail:** {report_text(token_usage.get('actual_tailtrail_tokens'))} exact tokens "
            f"from {report_text(token_usage.get('telemetry_records'))} linked host/API record(s)."
        )
    else:
        lines.append("- **TailTrail:** exact host/API usage is not linked to this run.")
    comparison_labels = {"loose-prompt": "Loose-prompt baseline", "aidlc": "AIDLC baseline"}
    for comparison_kind, label in comparison_labels.items():
        comparison = token_usage.get("comparisons", {}).get(comparison_kind, {})
        if comparison.get("status") != "measured":
            lines.append(
                f"- **{label}:** {report_text(comparison.get('status', 'unavailable'))} - "
                f"{report_text(comparison.get('reason', 'no paired host/API baseline is linked'))}"
            )
            continue
        saved = int(comparison.get("saved_tokens", 0))
        delta_label = "saved" if saved >= 0 else "additional"
        reduction = comparison.get("reduction_percent")
        reduction_text = f"{abs(reduction)}%" if isinstance(reduction, (int, float)) else "not calculable"
        lines.append(
            f"- **{label}:** {report_text(comparison.get('baseline_tokens'))} exact tokens; "
            f"TailTrail {delta_label} {abs(saved)} tokens ({reduction_text})."
        )
    context_estimate = token_usage.get("context_estimate", {})
    if context_estimate.get("status") == "estimated":
        if context_estimate.get("comparison_basis") == "scoped-files":
            lines.append(
                f"- **Planning forecast:** approximately {report_text(context_estimate.get('planned_working_set_tokens'))} "
                f"tokens from a {report_text(context_estimate.get('forecast_confidence'))}-confidence working set; "
                f"full scoped-file ceiling {report_text(context_estimate.get('scoped_file_ceiling_tokens'))} tokens "
                f"({report_text(context_estimate.get('estimated_reduction_percent'))}% reduction)."
            )
            lines.append(
                f"- **Repository inventory:** approximately {report_text(context_estimate.get('repository_ceiling_tokens'))} "
                f"tokens across {report_text(context_estimate.get('repository_file_count'))} relevant file(s); informational only."
            )
        else:
            lines.append(
                f"- **Repository context:** approximately {report_text(context_estimate.get('repository_ceiling_tokens'))} "
                f"tokens across {report_text(context_estimate.get('repository_file_count'))} relevant file(s); "
                f"approximately {report_text(context_estimate.get('estimated_saved_tokens'))} tokens excluded "
                f"({report_text(context_estimate.get('estimated_reduction_percent'))}%)."
            )
        techniques = [report_text(value) for value in context_estimate.get("saving_techniques", []) if value]
        if techniques:
            lines.append(f"- **Major techniques:** {', '.join(techniques)}.")
        learning_references = [
            report_text(value)
            for value in context_estimate.get("learning_evidence_references", [])
            if value
        ]
        if learning_references:
            lines.append(
                "- **Project learning evidence:** "
                + ", ".join(f"`{value}`" for value in learning_references)
                + "."
            )
    lines.append(f"- **Boundary:** {report_text(token_usage.get('boundary'))}")

    lines.extend([
        "",
        "## Audit summary",
        "",
    ])
    recorded_sources = {name: reference for name, reference in payload.get("source_artifacts", {}).items() if reference}
    lines.extend([
        f"- **Authority:** {report_text(payload['execution_authority'].get('status'))} / {report_text(payload['execution_authority'].get('route'))}",
        f"- **Canonical state:** {report_text(payload['canonical_state'].get('status'))}",
        f"- **Scope:** {report_text(payload['changed_scope'].get('status'))}",
        f"- **Drift:** {report_text(payload['drift'].get('status'))}",
        f"- **Recovery:** {report_text(payload['recovery_checkpoint'].get('status'))}",
        f"- **Learning attribution:** {report_text(learning_use.get('status'))}; {report_text(learning_use.get('attributed'))} requirement-linked receipt(s)",
        f"- **Recorded source artifacts:** {len(recorded_sources)}; exact references remain in the JSON report",
        f"- **Actual model tokens:** "
        + (
            f"{report_text(payload['token_usage'].get('actual_tailtrail_tokens'))} from {report_text(payload['token_usage'].get('telemetry_records'))} linked record(s)"
            if payload["token_usage"].get("status") == "measured"
            else report_text(payload["token_usage"].get("status"))
        ),
    ])
    if payload["official_aidlc"].get("evidence_status") != "not-triggered":
        lines.append(f"- **Official AI-DLC:** {report_text(payload['official_aidlc'].get('evidence_status'))}")
    if payload["overall_status"] != "complete":
        lines.extend(["", "## Next actions", ""])
        if incomplete_checks:
            lines.append("1. Run the approved required proof through TailTrail managed execution:")
            for check, state in incomplete_checks:
                affected = ", ".join(requirement_ids.get(uid, uid) for uid in check.get("requirement_uids", [])) or "unlinked"
                lines.append(f"   - `{report_text(check.get('command'))}` — {report_text(state)}; covers {affected}; tiers: {', '.join(check.get('tiers', [])) or 'not specified'}")
            lines.append(f"2. Finalize the same run: `tailtrail closure finalize --root . --run-id {report_text(payload['run_id'])}`")
            lines.append("3. Generate the Completion Report again.")
        else:
            lines.append("1. Resolve the evidence or drift item listed above.")
            lines.append(f"2. Finalize the same run: `tailtrail closure finalize --root . --run-id {report_text(payload['run_id'])}`")
        lines.append("- Completion remains unverified until every required tier has authoritative passing evidence.")
    lines.extend(["", "## Closure boundary", "", payload["boundary"]])
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
