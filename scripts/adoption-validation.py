#!/usr/bin/env python3
"""PM-7 privacy-safe usability trial capture, gates, and improvement evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "benchmarks" / "evaluation" / "adoption" / "v1.json"
STATE_ROOT = Path(".tailtrail/evaluation/adoption")
TRIAL_INPUT_FIELDS = {
    "schema_version", "type", "trial_id", "cohort", "scenario_id", "participant_ref",
    "evidence_kind", "observer_attested", "started_at", "valid_plan_at", "completed_at",
    "outcome", "approval_count", "redundant_approval_count", "intervention_count",
    "false_intervention_count", "completion_comprehension", "safety_checks",
    "feedback_signals", "evidence_refs",
}
RECEIPT_FIELDS = (TRIAL_INPUT_FIELDS - {"type"}) | {
    "schema_version", "type", "catalog", "time_to_plan_ms", "created_at", "privacy", "integrity",
}
DECISION_FIELDS = {
    "schema_version", "type", "proposal_id", "recommendation_id", "report_digest",
    "signal_id", "kind", "target", "action", "supporting_trial_ids", "participant_count",
    "created_at", "authority", "decision", "reason_code", "change_ref", "validation_ref",
    "boundary", "integrity",
}
CATALOG_FIELDS = {
    "schema_version", "type", "catalog_version", "evidence_label", "cohorts", "thresholds",
    "safety_boundaries", "feedback_signals", "decision_reason_codes", "claim_boundaries",
    "privacy", "integrity",
}
RAW_MARKERS = (
    "raw_prompt", "prompt_raw", "raw_source", "source_code", "raw_log", "raw_ci",
    "raw_scanner", "secret", "password", "token_value", "customer_data", "email",
    "person_name", "user_name",
)
PRIVACY = {
    "sanitized": True,
    "raw_prompt": False,
    "raw_source": False,
    "raw_log": False,
    "identity_fields": False,
}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.as_posix()} must contain one JSON object")
    return value


def canonical_digest(value: dict[str, Any]) -> str:
    body = {key: item for key, item in value.items() if key != "integrity"}
    rendered = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def sealed(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result["integrity"] = {
        "algorithm": "sha256",
        "canonicalization": "sorted compact JSON excluding integrity",
        "digest": canonical_digest(result),
    }
    return result


def seal_valid(value: dict[str, Any]) -> bool:
    integrity = value.get("integrity")
    return (
        isinstance(integrity, dict)
        and integrity.get("algorithm") == "sha256"
        and integrity.get("canonicalization") == "sorted compact JSON excluding integrity"
        and integrity.get("digest") == canonical_digest(value)
    )


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: Any, name: str, *, nullable: bool = False) -> datetime | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an RFC 3339 timestamp" + (" or null" if nullable else ""))
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be an RFC 3339 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include a timezone")
    return parsed


def contains_raw_field(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in RAW_MARKERS):
                return str(key)
            nested = contains_raw_field(item)
            if nested:
                return nested
    elif isinstance(value, list):
        for item in value:
            nested = contains_raw_field(item)
            if nested:
                return nested
    return None


def safe_reference(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 160:
        raise ValueError(f"{name} must be a non-empty sanitized reference of at most 160 characters")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:/#-")
    if any(character not in allowed for character in value) or ".." in value or "\\" in value:
        raise ValueError(f"{name} must be a sanitized reference, not content or a traversal path")
    return value


def catalog_errors(value: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if set(value) != CATALOG_FIELDS:
        issues.append("catalog must use the closed field set")
    if value.get("schema_version") != "1" or value.get("type") != "tailtrail-adoption-validation-catalog":
        issues.append("catalog contract is incompatible")
    if value.get("evidence_label") != "evaluation-protocol":
        issues.append("catalog must be labeled `evaluation-protocol`")
    if not seal_valid(value):
        issues.append("catalog integrity seal is invalid")
    cohorts = value.get("cohorts")
    if not isinstance(cohorts, list) or {row.get("id") for row in cohorts if isinstance(row, dict)} != {"new-user", "experienced-user"}:
        issues.append("catalog must define exactly the new-user and experienced-user cohorts")
    else:
        for row in cohorts:
            if not isinstance(row, dict):
                issues.append("cohort entries must be objects")
                continue
            if row.get("minimum_trials", 0) < 5 or row.get("minimum_unique_participants", 0) < 5:
                issues.append(f"{row.get('id')}: needs at least five trials and independent participants")
            scenarios = row.get("scenarios")
            if not isinstance(scenarios, list) or len(scenarios) < row.get("minimum_scenarios", 3) or len(scenarios) != len(set(scenarios)):
                issues.append(f"{row.get('id')}: scenario coverage is incomplete or duplicated")
    boundaries = value.get("safety_boundaries")
    if not isinstance(boundaries, list) or len(boundaries) < 5 or len(boundaries) != len(set(boundaries)):
        issues.append("catalog needs five unique safety boundaries")
    signals = value.get("feedback_signals")
    signal_ids = [row.get("id") for row in signals if isinstance(row, dict)] if isinstance(signals, list) else []
    if not signal_ids or len(signal_ids) != len(set(signal_ids)):
        issues.append("feedback signals must be non-empty and unique")
    thresholds = value.get("thresholds")
    if not isinstance(thresholds, dict) or thresholds.get("safety_boundary_weakening_count_max") != 0:
        issues.append("safety weakening threshold must be exactly zero")
    return issues


def load_catalog() -> dict[str, Any]:
    value = read_json(CATALOG_PATH)
    issues = catalog_errors(value)
    if issues:
        raise ValueError("; ".join(issues))
    return value


def cohort_map(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["id"]): row for row in catalog["cohorts"]}


def feedback_map(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["id"]): row for row in catalog["feedback_signals"]}


def validate_input(source: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    if raw := contains_raw_field(source):
        raise ValueError(f"trial input contains prohibited raw or identity field: {raw}")
    missing = sorted(TRIAL_INPUT_FIELDS - set(source))
    extra = sorted(set(source) - TRIAL_INPUT_FIELDS)
    if missing or extra:
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("unsupported: " + ", ".join(extra))
        raise ValueError("trial input must use the closed contract (" + "; ".join(details) + ")")
    if source.get("schema_version") != "1" or source.get("type") != "tailtrail-adoption-trial-input":
        raise ValueError("trial input contract is incompatible")
    trial_id = source.get("trial_id")
    if not isinstance(trial_id, str) or len(trial_id) < 8 or len(trial_id) > 64 or not trial_id[0].isalnum() or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-" for ch in trial_id):
        raise ValueError("trial_id must be 8-64 lowercase letters, digits, or hyphens")
    participant = source.get("participant_ref")
    if not isinstance(participant, str) or not participant.startswith("anon-") or len(participant) > 53 or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-" for ch in participant[5:]):
        raise ValueError("participant_ref must be a random study-local `anon-...` alias")
    cohorts = cohort_map(catalog)
    cohort = source.get("cohort")
    if cohort not in cohorts:
        raise ValueError("cohort must be new-user or experienced-user")
    if source.get("scenario_id") not in cohorts[cohort]["scenarios"]:
        raise ValueError("scenario_id is not assigned to the selected cohort")
    evidence_kind = source.get("evidence_kind")
    if evidence_kind not in {"protocol-fixture", "moderated-observation", "unmoderated-observation"}:
        raise ValueError("evidence_kind is unsupported")
    if not isinstance(source.get("observer_attested"), bool):
        raise ValueError("observer_attested must be a boolean")
    evidence_refs = source.get("evidence_refs")
    if not isinstance(evidence_refs, list) or len(evidence_refs) != len(set(map(str, evidence_refs))):
        raise ValueError("evidence_refs must be a unique array")
    clean_refs = [safe_reference(item, "evidence_ref") for item in evidence_refs]
    if evidence_kind != "protocol-fixture" and (source["observer_attested"] is not True or not clean_refs):
        raise ValueError("observed trials require observer_attested true and at least one sanitized evidence_ref")
    started = parse_time(source.get("started_at"), "started_at")
    valid_plan = parse_time(source.get("valid_plan_at"), "valid_plan_at", nullable=True)
    completed = parse_time(source.get("completed_at"), "completed_at", nullable=True)
    if valid_plan and valid_plan < started:
        raise ValueError("valid_plan_at cannot precede started_at")
    if completed and completed < (valid_plan or started):
        raise ValueError("completed_at cannot precede the plan or start")
    outcome = source.get("outcome")
    if outcome not in {"completed", "abandoned"}:
        raise ValueError("outcome must be completed or abandoned")
    if outcome == "completed" and (valid_plan is None or completed is None):
        raise ValueError("completed trials require valid_plan_at and completed_at")
    if outcome == "abandoned" and completed is not None:
        raise ValueError("abandoned trials cannot have completed_at")
    for name in ("approval_count", "redundant_approval_count", "intervention_count", "false_intervention_count"):
        value = source.get(name)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
    if source["redundant_approval_count"] > source["approval_count"]:
        raise ValueError("redundant_approval_count cannot exceed approval_count")
    if source["false_intervention_count"] > source["intervention_count"]:
        raise ValueError("false_intervention_count cannot exceed intervention_count")
    comprehension = source.get("completion_comprehension")
    if not isinstance(comprehension, dict) or set(comprehension) != {"correct", "total"}:
        raise ValueError("completion_comprehension must contain exactly correct and total")
    correct, total = comprehension.get("correct"), comprehension.get("total")
    if not all(isinstance(item, int) and not isinstance(item, bool) and item >= 0 for item in (correct, total)) or correct > total:
        raise ValueError("completion comprehension counts are invalid")
    if outcome == "completed" and total < 1:
        raise ValueError("completed trials require at least one comprehension check")
    if outcome == "abandoned" and (correct != 0 or total != 0):
        raise ValueError("abandoned trials cannot claim completion comprehension")
    safety = source.get("safety_checks")
    if not isinstance(safety, dict) or set(safety) != set(catalog["safety_boundaries"]) or not all(isinstance(item, bool) for item in safety.values()):
        raise ValueError("safety_checks must contain exactly every catalog safety boundary as booleans")
    feedback = source.get("feedback_signals")
    if not isinstance(feedback, list) or len(feedback) != len(set(map(str, feedback))) or not set(feedback) <= set(feedback_map(catalog)):
        raise ValueError("feedback_signals must be a unique subset of the closed catalog")
    return {**source, "evidence_refs": clean_refs}


def build_receipt(source: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    clean = validate_input(source, catalog)
    started = parse_time(clean["started_at"], "started_at")
    valid_plan = parse_time(clean["valid_plan_at"], "valid_plan_at", nullable=True)
    time_to_plan_ms = round((valid_plan - started).total_seconds() * 1000) if valid_plan else None
    value = {
        "schema_version": "1",
        "type": "tailtrail-adoption-trial-receipt",
        "trial_id": clean["trial_id"],
        "catalog": {"version": catalog["catalog_version"], "digest": catalog["integrity"]["digest"]},
        "cohort": clean["cohort"],
        "scenario_id": clean["scenario_id"],
        "participant_ref": clean["participant_ref"],
        "evidence_kind": clean["evidence_kind"],
        "observer_attested": clean["observer_attested"],
        "started_at": clean["started_at"],
        "valid_plan_at": clean["valid_plan_at"],
        "completed_at": clean["completed_at"],
        "outcome": clean["outcome"],
        "time_to_plan_ms": time_to_plan_ms,
        "approval_count": clean["approval_count"],
        "redundant_approval_count": clean["redundant_approval_count"],
        "intervention_count": clean["intervention_count"],
        "false_intervention_count": clean["false_intervention_count"],
        "completion_comprehension": clean["completion_comprehension"],
        "safety_checks": clean["safety_checks"],
        "feedback_signals": clean["feedback_signals"],
        "evidence_refs": clean["evidence_refs"],
        "created_at": now(),
        "privacy": PRIVACY,
    }
    return sealed(value)


def receipt_errors(value: dict[str, Any], catalog: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if set(value) != RECEIPT_FIELDS:
        issues.append("receipt must use the closed field set")
    if raw := contains_raw_field({key: item for key, item in value.items() if key != "privacy"}):
        issues.append(f"receipt contains prohibited raw or identity field: {raw}")
    if value.get("type") != "tailtrail-adoption-trial-receipt" or value.get("schema_version") != "1":
        issues.append("receipt contract is incompatible")
    if not seal_valid(value):
        issues.append("receipt integrity seal is invalid")
    if value.get("catalog") != {"version": catalog["catalog_version"], "digest": catalog["integrity"]["digest"]}:
        issues.append("receipt catalog identity is stale or incompatible")
    source = {field: value.get(field) for field in TRIAL_INPUT_FIELDS}
    source["type"] = "tailtrail-adoption-trial-input"
    try:
        clean = validate_input(source, catalog)
        started = parse_time(clean["started_at"], "started_at")
        valid_plan = parse_time(clean["valid_plan_at"], "valid_plan_at", nullable=True)
        expected_ms = round((valid_plan - started).total_seconds() * 1000) if valid_plan else None
        if value.get("time_to_plan_ms") != expected_ms:
            issues.append("derived time_to_plan_ms does not match timestamps")
    except ValueError as error:
        issues.append(str(error))
    if value.get("privacy") != PRIVACY:
        issues.append("receipt privacy boundary is incompatible")
    try:
        parse_time(value.get("created_at"), "created_at")
    except ValueError as error:
        issues.append(str(error))
    return issues


def write_immutable(path: Path, value: dict[str, Any]) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != rendered:
            raise ValueError(f"refusing to overwrite immutable artifact {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(rendered)
    except FileExistsError:
        if path.read_text(encoding="utf-8") != rendered:
            raise ValueError(f"refusing to overwrite immutable artifact {path.name}")


def safe_path(root: Path, supplied: Path) -> Path:
    base = root.resolve()
    path = (base / supplied).resolve() if not supplied.is_absolute() else supplied.resolve()
    try:
        path.relative_to(base)
    except ValueError as error:
        raise ValueError("artifact path must remain inside the selected project root") from error
    return path


def record(root: Path, input_path: Path, approved: bool) -> dict[str, Any]:
    if not approved:
        raise ValueError("record requires --approved")
    catalog = load_catalog()
    source = read_json(safe_path(root, input_path))
    receipt = build_receipt(source, catalog)
    target = root.resolve() / STATE_ROOT / "trials" / f"{receipt['trial_id']}.json"
    write_immutable(target, receipt)
    return {**receipt, "artifact": target.relative_to(root.resolve()).as_posix()}


def percentile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def gate(identifier: str, observed: Any, threshold: Any, passed: bool) -> dict[str, Any]:
    return {"id": identifier, "observed": observed, "threshold": threshold, "passed": bool(passed)}


def metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    plans = [row["time_to_plan_ms"] for row in rows if isinstance(row.get("time_to_plan_ms"), int)]
    approvals = [row["approval_count"] for row in rows]
    comprehension_correct = sum(row["completion_comprehension"]["correct"] for row in rows if row["outcome"] == "completed")
    comprehension_total = sum(row["completion_comprehension"]["total"] for row in rows if row["outcome"] == "completed")
    return {
        "trial_count": len(rows),
        "unique_participants": len({row["participant_ref"] for row in rows}),
        "scenario_count": len({row["scenario_id"] for row in rows}),
        "completed_count": sum(row["outcome"] == "completed" for row in rows),
        "abandoned_count": sum(row["outcome"] == "abandoned" for row in rows),
        "abandonment_rate": ratio(sum(row["outcome"] == "abandoned" for row in rows), len(rows)),
        "time_to_plan_p75_ms": percentile(plans, 0.75),
        "approval_count_p75": percentile(approvals, 0.75),
        "approval_count": sum(approvals),
        "redundant_approval_count": sum(row["redundant_approval_count"] for row in rows),
        "redundant_approval_rate": ratio(sum(row["redundant_approval_count"] for row in rows), sum(approvals)) if sum(approvals) else 0.0,
        "intervention_count": sum(row["intervention_count"] for row in rows),
        "false_intervention_count": sum(row["false_intervention_count"] for row in rows),
        "false_intervention_rate": ratio(sum(row["false_intervention_count"] for row in rows), sum(row["intervention_count"] for row in rows)) if sum(row["intervention_count"] for row in rows) else 0.0,
        "completion_comprehension_correct": comprehension_correct,
        "completion_comprehension_total": comprehension_total,
        "completion_comprehension_rate": ratio(comprehension_correct, comprehension_total),
        "safety_boundary_weakening_count": sum(not passed for row in rows for passed in row["safety_checks"].values()),
    }


def decision_errors(value: dict[str, Any], catalog: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if set(value) != DECISION_FIELDS:
        issues.append("improvement decision must use the closed field set")
    if raw := contains_raw_field(value):
        issues.append(f"improvement decision contains prohibited raw or identity field: {raw}")
    if value.get("type") != "tailtrail-adoption-improvement-decision" or value.get("schema_version") != "1":
        issues.append("improvement decision contract is incompatible")
    if not seal_valid(value):
        issues.append("improvement decision integrity seal is invalid")
    if value.get("authority") != "human-approved-adoption-improvement-record":
        issues.append("improvement decision authority is incompatible")
    if value.get("reason_code") is not None and value.get("reason_code") not in catalog["decision_reason_codes"]:
        issues.append("improvement decision reason code is unsupported")
    decision = value.get("decision")
    if decision not in {"proposed", "applied", "rejected", "deferred"}:
        issues.append("improvement decision state is unsupported")
    elif decision == "proposed" and any(value.get(name) is not None for name in ("reason_code", "change_ref", "validation_ref")):
        issues.append("proposed improvements cannot claim a decision, change, or validation")
    elif decision != "proposed" and value.get("reason_code") not in catalog["decision_reason_codes"]:
        issues.append("decided improvements require a closed reason code")
    signal = feedback_map(catalog).get(str(value.get("signal_id", "")))
    if signal is None or any(value.get(name) != signal.get(name) for name in ("kind", "target", "action")):
        issues.append("improvement decision signal, kind, target, or action is not catalog-bound")
    for name, prefix in (("proposal_id", "adopt-proposal-"), ("recommendation_id", "adopt-rec-")):
        identifier = value.get(name)
        if not isinstance(identifier, str) or not identifier.startswith(prefix) or len(identifier) != len(prefix) + 16 or any(character not in "0123456789abcdef" for character in identifier[-16:]):
            issues.append(f"{name} is invalid")
    report_digest = value.get("report_digest")
    if not isinstance(report_digest, str) or len(report_digest) != 64 or any(character not in "0123456789abcdef" for character in report_digest):
        issues.append("report_digest must be one SHA-256 digest")
    supporting = value.get("supporting_trial_ids")
    if not isinstance(supporting, list) or len(supporting) < 3 or len(supporting) != len(set(map(str, supporting))):
        issues.append("improvement decision needs three unique supporting trials")
    if not isinstance(value.get("participant_count"), int) or isinstance(value.get("participant_count"), bool) or value.get("participant_count", 0) < 3:
        issues.append("improvement decision needs three independent participants")
    try:
        parse_time(value.get("created_at"), "created_at")
    except ValueError as error:
        issues.append(str(error))
    if decision == "applied" and (not value.get("change_ref") or not value.get("validation_ref")):
        issues.append("applied improvements require change_ref and validation_ref")
    for name in ("change_ref", "validation_ref"):
        if value.get(name) is not None:
            try:
                safe_reference(value[name], name)
            except ValueError as error:
                issues.append(str(error))
    return issues


def load_decisions(root: Path, catalog: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    issues: list[str] = []
    for directory in ("proposals", "decisions"):
        for path in sorted((root.resolve() / STATE_ROOT / directory).glob("*.json")):
            try:
                value = read_json(path)
            except (OSError, json.JSONDecodeError, ValueError) as error:
                issues.append(f"{path.name}: {error}")
                continue
            problems = decision_errors(value, catalog)
            if problems:
                issues.extend(f"{path.name}: {problem}" for problem in problems)
            else:
                records.append(value)
    latest: dict[str, dict[str, Any]] = {}
    decided: dict[str, int] = defaultdict(int)
    for row in records:
        proposal_id = str(row["proposal_id"])
        if row["decision"] != "proposed":
            decided[proposal_id] += 1
        if proposal_id not in latest or row["decision"] != "proposed":
            latest[proposal_id] = row
    for proposal_id, count in decided.items():
        if count > 1:
            issues.append(f"{proposal_id}: conflicting immutable improvement decisions")
    return sorted(latest.values(), key=lambda row: row["proposal_id"]), issues


def build_recommendations(rows: list[dict[str, Any]], catalog: dict[str, Any]) -> list[dict[str, Any]]:
    signal_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for signal in row["feedback_signals"]:
            signal_rows[signal].append(row)
    minimum = catalog["thresholds"]["recommendation_minimum_unique_participants"]
    recommendations: list[dict[str, Any]] = []
    for signal_id, definition in sorted(feedback_map(catalog).items()):
        supporting = signal_rows.get(signal_id, [])
        participants = {row["participant_ref"] for row in supporting}
        safety_intact = all(all(row["safety_checks"].values()) for row in supporting)
        core = [catalog["integrity"]["digest"], signal_id, sorted(row["trial_id"] for row in supporting)]
        identifier = "adopt-rec-" + hashlib.sha256(json.dumps(core, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        recommendations.append({
            "recommendation_id": identifier,
            "signal_id": signal_id,
            "kind": definition["kind"],
            "target": definition["target"],
            "action": definition["action"],
            "trial_count": len(supporting),
            "participant_count": len(participants),
            "supporting_trial_ids": sorted(row["trial_id"] for row in supporting),
            "eligible": len(participants) >= minimum and safety_intact,
            "boundary": "Eligibility proposes human review only; it never changes wording, defaults, or safety controls.",
        })
    return recommendations


def report(root: Path) -> dict[str, Any]:
    catalog = load_catalog()
    trials: list[dict[str, Any]] = []
    issues: list[str] = []
    seen_ids: set[str] = set()
    for path in sorted((root.resolve() / STATE_ROOT / "trials").glob("*.json")):
        try:
            value = read_json(path)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            issues.append(f"{path.name}: {error}")
            continue
        problems = receipt_errors(value, catalog)
        if value.get("trial_id") in seen_ids:
            problems.append("duplicate trial_id")
        seen_ids.add(str(value.get("trial_id", "")))
        if problems:
            issues.extend(f"{path.name}: {problem}" for problem in problems)
        else:
            trials.append(value)
    observed = [row for row in trials if row["evidence_kind"] != "protocol-fixture"]
    fixtures = [row for row in trials if row["evidence_kind"] == "protocol-fixture"]
    overall = metric_summary(observed)
    thresholds = catalog["thresholds"]
    gates: list[dict[str, Any]] = []
    cohort_reports: list[dict[str, Any]] = []
    for definition in catalog["cohorts"]:
        rows = [row for row in observed if row["cohort"] == definition["id"]]
        metrics = metric_summary(rows)
        cohort_gates = [
            gate(f"{definition['id']}.minimum-trials", metrics["trial_count"], definition["minimum_trials"], metrics["trial_count"] >= definition["minimum_trials"]),
            gate(f"{definition['id']}.unique-participants", metrics["unique_participants"], definition["minimum_unique_participants"], metrics["unique_participants"] >= definition["minimum_unique_participants"]),
            gate(f"{definition['id']}.scenario-coverage", metrics["scenario_count"], definition["minimum_scenarios"], metrics["scenario_count"] >= definition["minimum_scenarios"]),
            gate(f"{definition['id']}.time-to-plan-p75-ms", metrics["time_to_plan_p75_ms"], definition["time_to_plan_p75_ms_max"], metrics["time_to_plan_p75_ms"] is not None and metrics["time_to_plan_p75_ms"] <= definition["time_to_plan_p75_ms_max"]),
            gate(f"{definition['id']}.approval-count-p75", metrics["approval_count_p75"], definition["approval_count_p75_max"], metrics["approval_count_p75"] is not None and metrics["approval_count_p75"] <= definition["approval_count_p75_max"]),
            gate(f"{definition['id']}.completion-comprehension", metrics["completion_comprehension_rate"], thresholds["cohort_completion_comprehension_rate_min"], metrics["completion_comprehension_rate"] is not None and metrics["completion_comprehension_rate"] >= thresholds["cohort_completion_comprehension_rate_min"]),
        ]
        gates.extend(cohort_gates)
        cohort_reports.append({"cohort": definition["id"], **metrics, "gates_passed": all(item["passed"] for item in cohort_gates)})
    overall_gates = [
        gate("overall.abandonment-rate", overall["abandonment_rate"], thresholds["overall_abandonment_rate_max"], overall["abandonment_rate"] is not None and overall["abandonment_rate"] <= thresholds["overall_abandonment_rate_max"]),
        gate("overall.redundant-approval-rate", overall["redundant_approval_rate"], thresholds["redundant_approval_rate_max"], overall["redundant_approval_rate"] is not None and overall["redundant_approval_rate"] <= thresholds["redundant_approval_rate_max"]),
        gate("overall.false-intervention-rate", overall["false_intervention_rate"], thresholds["false_intervention_rate_max"], overall["false_intervention_rate"] is not None and overall["false_intervention_rate"] <= thresholds["false_intervention_rate_max"]),
        gate("overall.completion-comprehension", overall["completion_comprehension_rate"], thresholds["overall_completion_comprehension_rate_min"], overall["completion_comprehension_rate"] is not None and overall["completion_comprehension_rate"] >= thresholds["overall_completion_comprehension_rate_min"]),
        gate("overall.safety-boundary-weakening", overall["safety_boundary_weakening_count"], 0, overall["safety_boundary_weakening_count"] == 0),
    ]
    gates.extend(overall_gates)
    decisions, decision_issues = load_decisions(root, catalog)
    issues.extend(decision_issues)
    if issues:
        status = "invalid"
    elif observed and all(item["passed"] for item in gates):
        status = "qualified"
    elif observed and all(
        metrics["trial_count"] >= definition["minimum_trials"]
        for metrics, definition in zip(cohort_reports, catalog["cohorts"])
    ):
        status = "thresholds-not-met"
    elif observed:
        status = "collecting"
    elif fixtures:
        status = "fixture-only"
    else:
        status = "protocol-ready"
    value = {
        "schema_version": "1",
        "type": "tailtrail-adoption-validation-report",
        "catalog": {"version": catalog["catalog_version"], "digest": catalog["integrity"]["digest"]},
        "status": status,
        "claim_status": "scenario-scoped-adoption-evidence" if status == "qualified" else "no-adoption-claim",
        "evidence": {
            "total_receipts": len(trials),
            "qualifying_observations": len(observed),
            "protocol_fixtures": len(fixtures),
            "moderated_observations": sum(row["evidence_kind"] == "moderated-observation" for row in observed),
            "unmoderated_observations": sum(row["evidence_kind"] == "unmoderated-observation" for row in observed),
        },
        "overall": overall,
        "cohorts": cohort_reports,
        "gates": gates,
        "recommendations": build_recommendations(observed, catalog),
        "improvement_decisions": decisions,
        "issues": issues,
        "claim_boundaries": catalog["claim_boundaries"],
        "privacy": PRIVACY,
    }
    return sealed(value)


def validate_catalog() -> dict[str, Any]:
    catalog = read_json(CATALOG_PATH)
    issues = catalog_errors(catalog)
    return {
        "schema_version": "1",
        "type": "tailtrail-adoption-validation-catalog-check",
        "status": "passed" if not issues else "failed",
        "catalog_version": catalog.get("catalog_version"),
        "cohorts": len(catalog.get("cohorts", [])),
        "scenario_count": sum(len(row.get("scenarios", [])) for row in catalog.get("cohorts", []) if isinstance(row, dict)),
        "issues": issues,
        "evidence_label": "evaluation-protocol",
    }


def template(cohort: str, scenario: str | None) -> dict[str, Any]:
    catalog = load_catalog()
    definitions = cohort_map(catalog)
    if cohort not in definitions:
        raise ValueError("cohort must be new-user or experienced-user")
    selected = scenario or definitions[cohort]["scenarios"][0]
    if selected not in definitions[cohort]["scenarios"]:
        raise ValueError("scenario is not assigned to the selected cohort")
    return {
        "schema_version": "1",
        "type": "tailtrail-adoption-trial-input",
        "trial_id": "replace-trial-id",
        "cohort": cohort,
        "scenario_id": selected,
        "participant_ref": "anon-random-alias",
        "evidence_kind": "moderated-observation",
        "observer_attested": True,
        "started_at": "2026-09-01T00:00:00Z",
        "valid_plan_at": "2026-09-01T00:03:00Z",
        "completed_at": "2026-09-01T00:10:00Z",
        "outcome": "completed",
        "approval_count": 1,
        "redundant_approval_count": 0,
        "intervention_count": 0,
        "false_intervention_count": 0,
        "completion_comprehension": {"correct": 4, "total": 4},
        "safety_checks": {boundary: True for boundary in catalog["safety_boundaries"]},
        "feedback_signals": [],
        "evidence_refs": ["study/session-receipt-id"],
    }


def propose(root: Path, recommendation_id: str, approved: bool) -> dict[str, Any]:
    if not approved:
        raise ValueError("propose requires --approved")
    current = report(root)
    if current["status"] == "invalid":
        raise ValueError("cannot propose from an invalid adoption report")
    recommendation = next((row for row in current["recommendations"] if row["recommendation_id"] == recommendation_id), None)
    if recommendation is None:
        raise ValueError("unknown recommendation_id for the current report")
    if not recommendation["eligible"]:
        raise ValueError("recommendation lacks repeated independent evidence or has a safety weakening")
    core = [recommendation_id, current["integrity"]["digest"]]
    proposal_id = "adopt-proposal-" + hashlib.sha256(json.dumps(core).encode("utf-8")).hexdigest()[:16]
    value = sealed({
        "schema_version": "1",
        "type": "tailtrail-adoption-improvement-decision",
        "proposal_id": proposal_id,
        "recommendation_id": recommendation_id,
        "report_digest": current["integrity"]["digest"],
        "signal_id": recommendation["signal_id"],
        "kind": recommendation["kind"],
        "target": recommendation["target"],
        "action": recommendation["action"],
        "supporting_trial_ids": recommendation["supporting_trial_ids"],
        "participant_count": recommendation["participant_count"],
        "created_at": now(),
        "authority": "human-approved-adoption-improvement-record",
        "decision": "proposed",
        "reason_code": None,
        "change_ref": None,
        "validation_ref": None,
        "boundary": "This approved evidence record proposes review only; it does not edit source or alter a safety boundary.",
    })
    path = root.resolve() / STATE_ROOT / "proposals" / f"{proposal_id}.json"
    write_immutable(path, value)
    return {**value, "artifact": path.relative_to(root.resolve()).as_posix()}


def decide(root: Path, proposal_path: Path, decision: str, reason_code: str, change_ref: str | None, validation_ref: str | None, approved: bool) -> dict[str, Any]:
    if not approved:
        raise ValueError("decide requires --approved")
    catalog = load_catalog()
    if decision not in {"applied", "rejected", "deferred"}:
        raise ValueError("decision must be applied, rejected, or deferred")
    if reason_code not in catalog["decision_reason_codes"]:
        raise ValueError("reason_code is not in the closed catalog")
    proposal = read_json(safe_path(root, proposal_path))
    if problems := decision_errors(proposal, catalog):
        raise ValueError("; ".join(problems))
    if proposal.get("decision") != "proposed":
        raise ValueError("selected artifact is not an undecided proposal")
    clean_change = safe_reference(change_ref, "change_ref") if change_ref else None
    clean_validation = safe_reference(validation_ref, "validation_ref") if validation_ref else None
    if decision == "applied" and (not clean_change or not clean_validation):
        raise ValueError("applied decisions require --change-ref and --validation-ref")
    value = sealed({
        **{key: proposal[key] for key in (
            "schema_version", "type", "proposal_id", "recommendation_id", "report_digest",
            "signal_id", "kind", "target", "action", "supporting_trial_ids", "participant_count", "authority",
        )},
        "created_at": now(),
        "decision": decision,
        "reason_code": reason_code,
        "change_ref": clean_change,
        "validation_ref": clean_validation,
        "boundary": "A decision records human-reviewed evidence. Source changes and their validation remain separately observable facts.",
    })
    path = root.resolve() / STATE_ROOT / "decisions" / f"{proposal['proposal_id']}-{decision}.json"
    existing = sorted((root.resolve() / STATE_ROOT / "decisions").glob(f"{proposal['proposal_id']}-*.json"))
    if any(item != path for item in existing):
        raise ValueError("proposal already has an immutable decision")
    write_immutable(path, value)
    return {**value, "artifact": path.relative_to(root.resolve()).as_posix()}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="action", required=True)
    commands.add_parser("validate")
    command = commands.add_parser("template")
    command.add_argument("--cohort", choices=("new-user", "experienced-user"), required=True)
    command.add_argument("--scenario")
    command = commands.add_parser("record")
    command.add_argument("--root", type=Path, default=Path.cwd())
    command.add_argument("--input", type=Path, required=True)
    command.add_argument("--approved", action="store_true")
    for action in ("report", "gate"):
        command = commands.add_parser(action)
        command.add_argument("--root", type=Path, default=Path.cwd())
    command = commands.add_parser("propose")
    command.add_argument("--root", type=Path, default=Path.cwd())
    command.add_argument("--recommendation-id", required=True)
    command.add_argument("--approved", action="store_true")
    command = commands.add_parser("decide")
    command.add_argument("--root", type=Path, default=Path.cwd())
    command.add_argument("--proposal", type=Path, required=True)
    command.add_argument("--decision", choices=("applied", "rejected", "deferred"), required=True)
    command.add_argument("--reason-code", required=True)
    command.add_argument("--change-ref")
    command.add_argument("--validation-ref")
    command.add_argument("--approved", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.action == "validate":
            value = validate_catalog()
        elif args.action == "template":
            value = template(args.cohort, args.scenario)
        elif args.action == "record":
            value = record(args.root, args.input, args.approved)
        elif args.action in {"report", "gate"}:
            value = report(args.root)
        elif args.action == "propose":
            value = propose(args.root, args.recommendation_id, args.approved)
        else:
            value = decide(args.root, args.proposal, args.decision, args.reason_code, args.change_ref, args.validation_ref, args.approved)
        print(json.dumps(value, indent=2, sort_keys=True))
        if args.action == "gate":
            return 0 if value.get("status") == "qualified" else 2
        return 2 if value.get("status") in {"failed", "invalid"} else 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"TailTrail adoption validation error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
