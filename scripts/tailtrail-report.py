#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from collections import Counter
import csv
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any


TAILTRAIL_DIR = Path(".tailtrail")
QUALITY_EVENTS = TAILTRAIL_DIR / "quality-events.jsonl"
QUALITY_SUMMARY = TAILTRAIL_DIR / "quality-summary.md"
OUTCOME_EVENTS = TAILTRAIL_DIR / "outcome-events.jsonl"
OUTCOME_SUMMARY = TAILTRAIL_DIR / "outcome-summary.md"
LEARNING_EVENTS = TAILTRAIL_DIR / "learning-events.jsonl"
LEARNINGS = TAILTRAIL_DIR / "learnings.md"
LEARNING_INDEX = TAILTRAIL_DIR / "learning-index.md"
LEARNING_REFRESH_ACTIONS = TAILTRAIL_DIR / "learning-refresh-actions.json"
TOKEN_USAGE = TAILTRAIL_DIR / "token-usage.jsonl"
REPORT_PATH = TAILTRAIL_DIR / "enterprise-report.md"
VALUE_REPORT_PATH = TAILTRAIL_DIR / "value-report.md"
VALUE_REPORT_CSV = TAILTRAIL_DIR / "value-report.csv"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def month_key(value: str | None) -> str:
    parsed = parse_time(value)
    if not parsed:
        return "unknown"
    return f"{parsed.year:04d}-{parsed.month:02d}"


def read_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise SystemExit(f"Invalid {label} JSON on line {line_number}: {error}") from error
        if isinstance(value, dict):
            records.append(value)
    return records


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def in_scope(record: dict[str, Any], month: str | None, start: datetime | None, end: datetime | None) -> bool:
    timestamp = str(record.get("timestamp") or record.get("created_at") or "")
    parsed = parse_time(timestamp)
    if month and month_key(timestamp) != month:
        return False
    if start and (not parsed or parsed < start):
        return False
    if end and (not parsed or parsed > end):
        return False
    return True


def scoped(records: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    start = parse_time(args.start) if args.start else None
    end = parse_time(args.end) if args.end else None
    return [record for record in records if in_scope(record, args.month, start, end)]


def safe_records(records: list[dict[str, Any]], include_sensitive: bool) -> list[dict[str, Any]]:
    if include_sensitive:
        return records
    return [record for record in records if record.get("sensitivity", "normal") == "normal"]


def count_values(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        value = record.get(key)
        if isinstance(value, list):
            for item in value:
                counter[str(item)] += 1
        elif value is not None:
            counter[str(value)] += 1
    return dict(counter.most_common())


def count_matching(values: dict[str, int], fragments: tuple[str, ...]) -> int:
    total = 0
    for key, count in values.items():
        lowered = key.lower()
        if any(fragment in lowered for fragment in fragments):
            total += count
    return total


def count_tags(records: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        for tag in record.get("tags", []):
            counter[str(tag)] += 1
    return dict(counter.most_common(12))


def confidence_band(event: dict[str, Any]) -> str:
    confidence = event.get("learning_confidence", {})
    if isinstance(confidence, dict):
        return str(confidence.get("band", "unknown"))
    return "unknown"


def learning_hygiene(events: list[dict[str, Any]], refresh_actions: list[dict[str, Any]]) -> dict[str, Any]:
    weak_or_blocked = sum(1 for event in events if confidence_band(event) in {"weak-note", "do-not-use"})
    rejected = sum(1 for event in events if event.get("acceptance") == "rejected")
    missing_validation = sum(1 for event in events if str(event.get("validation_outcome", "unknown")) in {"unknown", "skipped", "not-run", ""})
    guardrail_risk = sum(1 for event in events if event.get("guardrail_weakened"))
    override_risk = sum(1 for event in events if event.get("user_override") in {"proceed-anyway", "record-low-confidence-event"})
    blocking_refresh = sum(1 for action in refresh_actions if action.get("action") in {"mark-stale", "suppress", "archive", "delete"})
    review_recommended = any(
        (
            weak_or_blocked >= 3,
            rejected >= 2,
            missing_validation >= 2,
            guardrail_risk > 0,
            override_risk > 0,
            blocking_refresh > 0,
        )
    )
    return {
        "weak_or_do_not_use_events": weak_or_blocked,
        "rejected_events": rejected,
        "missing_validation_events": missing_validation,
        "guardrail_risk_events": guardrail_risk,
        "override_risk_events": override_risk,
        "blocking_refresh_actions": blocking_refresh,
        "review_recommended": review_recommended,
        "recommended_command": "python3 scripts/tailtrail.py learn review --root .",
        "rule": "Learning hygiene is advisory. Suppress, promote, or delete learnings only with explicit approval.",
    }


def outcome_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(events)
    accepted = sum(1 for event in events if event.get("user_acceptance") in {"accepted", "partially-accepted"})
    validation_pass = sum(1 for event in events if event.get("validation_outcome") == "pass")
    review_approved = sum(1 for event in events if event.get("review_outcome") == "approved")
    escaped = sum(1 for event in events if event.get("defect_escaped") == "yes")
    return {
        "events": total,
        "acceptance_rate_percent": round((accepted / total) * 100, 2) if total else 0.0,
        "validation_pass_rate_percent": round((validation_pass / total) * 100, 2) if total else 0.0,
        "review_approval_rate_percent": round((review_approved / total) * 100, 2) if total else 0.0,
        "escaped_defect_count": escaped,
        "task_types": count_values(events, "task_type"),
        "workflows": count_values(events, "workflow_selected"),
        "acceptance": count_values(events, "user_acceptance"),
        "validation": count_values(events, "validation_outcome"),
        "review": count_values(events, "review_outcome"),
        "defects": count_values(events, "defect_escaped"),
        "time_saved": count_values(events, "time_saved_band"),
        "fit": count_values(events, "tailtrail_fit"),
        "learning_quality": count_values(events, "learning_quality"),
    }


def token_total(block: Any) -> int | None:
    if not isinstance(block, dict):
        return None
    total = block.get("total_tokens")
    if isinstance(total, int):
        return total
    input_tokens = block.get("input_tokens")
    output_tokens = block.get("output_tokens")
    if isinstance(input_tokens, int) and isinstance(output_tokens, int):
        return input_tokens + output_tokens
    return None


def measured_token_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    measured = []
    ignored = 0
    for record in records:
        if record.get("mode") != "measured":
            ignored += 1
            continue
        baseline = token_total(record.get("baseline"))
        tailtrail = token_total(record.get("tailtrail"))
        if baseline is None or tailtrail is None:
            ignored += 1
            continue
        saved = max(0, baseline - tailtrail)
        measured.append(
            {
                "task_id": str(record.get("task_id", "unknown")),
                "baseline_tokens": baseline,
                "tailtrail_tokens": tailtrail,
                "saved_tokens": saved,
            }
        )
    baseline_total = sum(item["baseline_tokens"] for item in measured)
    tailtrail_total = sum(item["tailtrail_tokens"] for item in measured)
    saved_total = max(0, baseline_total - tailtrail_total)
    reduction = round((saved_total / baseline_total) * 100, 2) if baseline_total else 0.0
    return {
        "evidence_level": "api_usage_metadata" if measured else "missing_measured_telemetry",
        "records": len(measured),
        "ignored_records": ignored,
        "baseline_tokens": baseline_total,
        "tailtrail_tokens": tailtrail_total,
        "saved_tokens": saved_total,
        "reduction_percent": reduction,
        "claim_guardrail": (
            "Measured token reduction is allowed only for the records counted here."
            if measured
            else "Exact token savings are unavailable because no measured model/API telemetry was provided."
        ),
    }


def approximate_context_report(root: Path) -> dict[str, Any]:
    files = [QUALITY_SUMMARY, LEARNING_INDEX, LEARNINGS]
    available = []
    total_chars = 0
    for relative in files:
        path = root / relative
        if not path.exists():
            continue
        try:
            chars = len(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        total_chars += chars
        available.append({"path": relative.as_posix(), "chars": chars, "approx_tokens": (chars + 3) // 4})
    return {
        "evidence_level": "local_approximation",
        "files": available,
        "approx_tokens": (total_chars + 3) // 4,
        "claim_guardrail": "Approximate context size only. Do not present this as exact token savings.",
    }


def load_refresh_actions(root: Path) -> list[dict[str, Any]]:
    data = read_json(root / LEARNING_REFRESH_ACTIONS)
    if not data:
        return []
    actions = data.get("actions", [])
    return [item for item in actions if isinstance(item, dict)] if isinstance(actions, list) else []


def aidlc_summary(root: Path) -> dict[str, Any]:
    docs = root / "aidlc-docs"
    if not docs.exists():
        return {"included": False, "files": 0, "validation_handoffs": 0, "handoffs": 0}
    files = [path for path in docs.rglob("*") if path.is_file()]
    return {
        "included": True,
        "files": len(files),
        "validation_handoffs": sum(1 for path in files if "validation" in path.name.lower()),
        "handoffs": sum(1 for path in files if "handoff" in path.name.lower()),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    quality = safe_records(scoped(read_jsonl(root / QUALITY_EVENTS, "quality event"), args), args.include_sensitive)
    outcomes = safe_records(scoped(read_jsonl(root / OUTCOME_EVENTS, "outcome event"), args), args.include_sensitive)
    learning = safe_records(scoped(read_jsonl(root / LEARNING_EVENTS, "learning event"), args), args.include_sensitive)
    token_path = Path(args.token_telemetry) if args.token_telemetry else root / TOKEN_USAGE
    if not token_path.is_absolute():
        token_path = root / token_path
    token_records = scoped(read_jsonl(token_path, "token telemetry"), args) if token_path.exists() else []
    refresh_actions = load_refresh_actions(root)

    quality_summary = {
        "events": len(quality),
        "workflow_fit": count_values(quality, "workflow_fit"),
        "outcomes": count_values(quality, "user_acceptance"),
        "validation": count_values(quality, "validation_outcome"),
        "workflows": count_values(quality, "workflow_selected"),
        "guardrails_applied": count_values(quality, "guardrails_applied"),
        "exact_materials_preserved": count_values(quality, "exact_materials_preserved"),
        "checks_run": count_values(quality, "checks_run"),
        "overlap_flags": count_values(quality, "overlap_flags"),
        "missed_gate_flags": count_values(quality, "missed_gate_flags"),
    }
    learning_summary = {
        "events": len(learning),
        "acceptance": count_values(learning, "acceptance"),
        "validation": count_values(learning, "validation_outcome"),
        "task_types": count_values(learning, "task_type"),
        "tags": count_tags(learning),
        "confidence_bands": dict(Counter(confidence_band(event) for event in learning).most_common()),
        "dependency_gate_applied": sum(1 for event in learning if event.get("dependency_gate_applied")),
        "no_new_dependency": sum(1 for event in learning if event.get("no_new_dependency")),
    }
    hygiene = learning_hygiene(learning, refresh_actions)
    return {
        "schema_version": "1",
        "created_at": now(),
        "root": root.as_posix(),
        "scope": {
            "month": args.month or "all",
            "start": args.start,
            "end": args.end,
            "include_sensitive": args.include_sensitive,
        },
        "quality": quality_summary,
        "outcomes": outcome_summary(outcomes),
        "learning": learning_summary,
        "learning_hygiene": hygiene,
        "learning_refresh": {
            "actions": len(refresh_actions),
            "action_counts": count_values(refresh_actions, "action"),
        },
        "aidlc": aidlc_summary(root) if args.include_aidlc else {"included": False},
        "token_savings": measured_token_report(token_records) if token_records else approximate_context_report(root),
        "source_files": {
            "quality_events": (root / QUALITY_EVENTS).as_posix(),
            "outcome_events": (root / OUTCOME_EVENTS).as_posix(),
            "learning_events": (root / LEARNING_EVENTS).as_posix(),
            "token_telemetry": token_path.as_posix(),
        },
        "privacy_note": "Local report only. Raw prompts, secrets, PII, PHI, customer data, and raw logs are not included by default.",
        "decision_note": "Use this report to decide which TailTrail rules, Navigator paths, guardrails, or policy packs should change. Do not treat it as surveillance.",
    }


def section_allowed(section: str, only: list[str] | None) -> bool:
    return not only or section in only


def evidence_confidence(report: dict[str, Any]) -> str:
    events = int(report["quality"]["events"]) + int(report["outcomes"]["events"]) + int(report["learning"]["events"])
    measured_tokens = report["token_savings"]["evidence_level"] == "api_usage_metadata"
    if events >= 10 and measured_tokens:
        return "high-local-evidence"
    if events >= 5 or measured_tokens:
        return "medium-local-evidence"
    if events > 0:
        return "low-local-evidence"
    return "no-local-evidence"


def build_value_surface(report: dict[str, Any]) -> dict[str, Any]:
    missed = report["quality"]["missed_gate_flags"]
    overlap = report["quality"]["overlap_flags"]
    guardrails = report["quality"]["guardrails_applied"]
    exact_materials = report["quality"]["exact_materials_preserved"]
    checks_run = report["quality"]["checks_run"]
    outcomes = report["outcomes"]
    learning = report["learning"]
    token = report["token_savings"]
    dependency_gate_used = sum(
        int(value) for key, value in outcomes.get("workflows", {}).items() if "dependency" in str(key).lower()
    )
    dependency_gate_used += int(learning.get("dependency_gate_applied", 0))
    dependency_gate_used += count_matching(guardrails, ("dependency",))
    dependencies_avoided = int(learning.get("no_new_dependency", 0))
    validation_truth_signals = count_matching(missed, ("validation", "evidence", "claim", "test"))
    validation_truth_signals += count_matching(guardrails, ("validation", "evidence", "claim"))
    safeguard_signals = sum(int(value) for value in guardrails.values())
    safeguard_signals += sum(int(value) for value in exact_materials.values())
    diff_size_signals = count_matching(guardrails, ("small", "diff", "scope"))
    workflow_overlap_signals = sum(int(value) for value in overlap.values())
    focused_validation_signals = sum(int(value) for value in checks_run.values())
    measured_tokens = token["evidence_level"] == "api_usage_metadata"
    return {
        "schema_version": "1",
        "created_at": report["created_at"],
        "root": report["root"],
        "scope": report["scope"],
        "evidence_confidence": evidence_confidence(report),
        "evidence_counts": {
            "quality_events": report["quality"]["events"],
            "outcome_events": outcomes["events"],
            "learning_events": learning["events"],
            "learning_refresh_actions": report["learning_refresh"]["actions"],
            "measured_token_records": token.get("records", 0) if measured_tokens else 0,
        },
        "governance_outcomes": {
            "dependency_gate_or_avoidance_signals": dependency_gate_used + dependencies_avoided,
            "dependencies_avoided": dependencies_avoided,
            "dependency_gate_signals": dependency_gate_used,
            "safeguard_preservation_signals": safeguard_signals,
            "validation_truth_signals": validation_truth_signals,
            "focused_validation_signals": focused_validation_signals,
            "diff_size_or_scope_discipline_signals": diff_size_signals,
            "workflow_overlap_signals": workflow_overlap_signals,
            "escaped_defects": outcomes["escaped_defect_count"],
        },
        "adoption_outcomes": {
            "acceptance_rate_percent": outcomes["acceptance_rate_percent"],
            "validation_pass_rate_percent": outcomes["validation_pass_rate_percent"],
            "review_approval_rate_percent": outcomes["review_approval_rate_percent"],
            "time_saved_bands": outcomes["time_saved"],
            "fit": outcomes["fit"],
        },
        "learning_hygiene": report["learning_hygiene"],
        "token_savings": token,
        "recommendations": value_recommendations(report),
        "claim_guardrail": (
            "This value view is local and advisory. Use counts as evidence of governed behavior, not as exact ROI."
            " Exact token savings are allowed only for measured model/API telemetry records."
        ),
        "privacy_note": report["privacy_note"],
    }


def value_recommendations(report: dict[str, Any]) -> list[str]:
    recommendations: list[str] = []
    value = {
        "missed": report["quality"]["missed_gate_flags"],
        "fit": report["quality"]["workflow_fit"],
        "token": report["token_savings"],
        "hygiene": report["learning_hygiene"],
        "outcomes": report["outcomes"],
    }
    if int(value["fit"].get("too-heavy", 0)) > 0:
        recommendations.append("Review Navigator routes marked too-heavy before adding more workflow steps.")
    if int(value["fit"].get("too-light", 0)) > 0:
        recommendations.append("Review risky tasks marked too-light and strengthen the relevant guardrail layer.")
    if value["missed"]:
        recommendations.append("Review missed gate flags and decide whether Navigator or local policy should route those prompts earlier.")
    if value["hygiene"].get("review_recommended"):
        recommendations.append(f"Run `{value['hygiene']['recommended_command']}` before relying on stale or weak learnings.")
    if value["token"]["evidence_level"] != "api_usage_metadata":
        recommendations.append("Supply measured token telemetry before making exact token-savings claims.")
    if int(value["outcomes"].get("events", 0)) == 0:
        recommendations.append("Capture approved outcome events after real tasks to make value reporting meaningful.")
    if not recommendations:
        recommendations.append("No immediate value-surface action crossed the local threshold; keep collecting compact approved evidence.")
    return recommendations


def render_counter(title: str, values: dict[str, int]) -> list[str]:
    lines = [f"## {title}", ""]
    if values:
        lines.extend(f"- {key}: `{value}`" for key, value in values.items())
    else:
        lines.append("- none")
    lines.append("")
    return lines


def token_records_by_month(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(month_key(str(record.get("timestamp") or record.get("created_at") or "")), []).append(record)
    return {month: measured_token_report(values) for month, values in sorted(grouped.items())}


def build_trend(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    quality = safe_records(read_jsonl(root / QUALITY_EVENTS, "quality event"), args.include_sensitive)
    outcomes = safe_records(read_jsonl(root / OUTCOME_EVENTS, "outcome event"), args.include_sensitive)
    learning = safe_records(read_jsonl(root / LEARNING_EVENTS, "learning event"), args.include_sensitive)
    token_path = Path(args.token_telemetry) if args.token_telemetry else root / TOKEN_USAGE
    if not token_path.is_absolute():
        token_path = root / token_path
    token_records = read_jsonl(token_path, "token telemetry") if token_path.exists() else []
    months = sorted(
        set(
            month_key(str(record.get("timestamp") or record.get("created_at") or ""))
            for record in [*quality, *outcomes, *learning, *token_records]
        )
        - {"unknown"}
    )
    rows: list[dict[str, Any]] = []
    token_by_month = token_records_by_month(token_records)
    for month in months:
        q = [record for record in quality if month_key(str(record.get("timestamp") or record.get("created_at") or "")) == month]
        o = [record for record in outcomes if month_key(str(record.get("timestamp") or record.get("created_at") or "")) == month]
        l = [record for record in learning if month_key(str(record.get("timestamp") or record.get("created_at") or "")) == month]
        token = token_by_month.get(month, measured_token_report([]))
        outcome = outcome_summary(o)
        hygiene = learning_hygiene(l, load_refresh_actions(root))
        rows.append(
            {
                "month": month,
                "quality_events": len(q),
                "outcome_events": len(o),
                "learning_events": len(l),
                "acceptance_rate_percent": outcome["acceptance_rate_percent"],
                "validation_pass_rate_percent": outcome["validation_pass_rate_percent"],
                "review_approval_rate_percent": outcome["review_approval_rate_percent"],
                "learning_review_recommended": hygiene["review_recommended"],
                "weak_or_do_not_use_events": hygiene["weak_or_do_not_use_events"],
                "measured_token_records": token.get("records", 0),
                "saved_tokens": token.get("saved_tokens", 0),
                "token_reduction_percent": token.get("reduction_percent", 0.0),
            }
        )
    return {
        "schema_version": "1",
        "created_at": now(),
        "root": root.as_posix(),
        "rows": rows,
        "claim_guardrail": "Trend data is local and advisory. Token trends are exact only for measured model/API telemetry records.",
    }


def render_bar(value: int, scale: int = 5) -> str:
    return "#" * max(0, min(40, (value + scale - 1) // scale))


def render_trend_markdown(trend: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Metrics Trend",
        "",
        "This trend uses local TailTrail artifacts only.",
        "",
        "| Month | Quality | Outcomes | Learnings | Acceptance | Validation | Measured Token Records | Saved Tokens |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in trend["rows"]:
        lines.append(
            f"| {row['month']} | {row['quality_events']} | {row['outcome_events']} | {row['learning_events']} | "
            f"{row['acceptance_rate_percent']}% | {row['validation_pass_rate_percent']}% | "
            f"{row['measured_token_records']} | {row['saved_tokens']} |"
        )
    lines.extend(["", "## Event Volume Chart", ""])
    for row in trend["rows"]:
        total = int(row["quality_events"]) + int(row["outcome_events"]) + int(row["learning_events"])
        lines.append(f"- `{row['month']}` {render_bar(total)} `{total}`")
    lines.extend(["", "## Claim Boundary", "", f"- {trend['claim_guardrail']}", ""])
    return "\n".join(lines)


def render_trend_csv(trend: dict[str, Any]) -> str:
    output = StringIO()
    fields = [
        "month",
        "quality_events",
        "outcome_events",
        "learning_events",
        "acceptance_rate_percent",
        "validation_pass_rate_percent",
        "review_approval_rate_percent",
        "learning_review_recommended",
        "weak_or_do_not_use_events",
        "measured_token_records",
        "saved_tokens",
        "token_reduction_percent",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(trend["rows"])
    return output.getvalue().rstrip()


def build_aggregate(report_paths: list[Path]) -> dict[str, Any]:
    reports = [load_report(path) for path in report_paths]
    repos: list[dict[str, Any]] = []
    totals = Counter()
    saved_tokens = 0
    baseline_tokens = 0
    tailtrail_tokens = 0
    for path, report in zip(report_paths, reports):
        value = report if "governance_outcomes" in report else build_value_surface(report)
        evidence = value["evidence_counts"]
        token = value["token_savings"]
        totals["quality_events"] += int(evidence.get("quality_events", 0))
        totals["outcome_events"] += int(evidence.get("outcome_events", 0))
        totals["learning_events"] += int(evidence.get("learning_events", 0))
        saved_tokens += int(token.get("saved_tokens", 0) or 0)
        baseline_tokens += int(token.get("baseline_tokens", 0) or 0)
        tailtrail_tokens += int(token.get("tailtrail_tokens", 0) or 0)
        repos.append(
            {
                "report": path.as_posix(),
                "root": value.get("root", "unknown"),
                "month": value.get("scope", {}).get("month", "unknown"),
                "evidence_confidence": value.get("evidence_confidence", "unknown"),
                "quality_events": evidence.get("quality_events", 0),
                "outcome_events": evidence.get("outcome_events", 0),
                "learning_events": evidence.get("learning_events", 0),
                "acceptance_rate_percent": value.get("adoption_outcomes", {}).get("acceptance_rate_percent", 0.0),
                "validation_pass_rate_percent": value.get("adoption_outcomes", {}).get("validation_pass_rate_percent", 0.0),
                "saved_tokens": token.get("saved_tokens", 0),
            }
        )
    return {
        "schema_version": "1",
        "created_at": now(),
        "reports": len(reports),
        "totals": dict(totals),
        "token_totals": {
            "baseline_tokens": baseline_tokens,
            "tailtrail_tokens": tailtrail_tokens,
            "saved_tokens": saved_tokens,
            "reduction_percent": round((saved_tokens / baseline_tokens) * 100, 2) if baseline_tokens else 0.0,
        },
        "repos": repos,
        "claim_guardrail": "Aggregate uses only provided local reports. It is not workspace telemetry or automatic monitoring.",
    }


def render_aggregate_markdown(aggregate: dict[str, Any]) -> str:
    totals = aggregate["totals"]
    token = aggregate["token_totals"]
    lines = [
        "# TailTrail Multi-Repo Aggregate",
        "",
        "This aggregate uses only local report files explicitly provided by the user.",
        "",
        f"- Reports: `{aggregate['reports']}`",
        f"- Quality events: `{totals.get('quality_events', 0)}`",
        f"- Outcome events: `{totals.get('outcome_events', 0)}`",
        f"- Learning events: `{totals.get('learning_events', 0)}`",
        f"- Measured saved tokens: `{token['saved_tokens']}`",
        f"- Measured token reduction: `{token['reduction_percent']}%`",
        "",
        "## Repos",
        "",
    ]
    for repo in aggregate["repos"]:
        lines.append(
            f"- `{repo['root']}` `{repo['month']}` confidence `{repo['evidence_confidence']}`; "
            f"quality `{repo['quality_events']}`, outcomes `{repo['outcome_events']}`, learnings `{repo['learning_events']}`"
        )
    lines.extend(["", "## Claim Boundary", "", f"- {aggregate['claim_guardrail']}", ""])
    return "\n".join(lines)


def render_aggregate_csv(aggregate: dict[str, Any]) -> str:
    output = StringIO()
    fields = [
        "report",
        "root",
        "month",
        "evidence_confidence",
        "quality_events",
        "outcome_events",
        "learning_events",
        "acceptance_rate_percent",
        "validation_pass_rate_percent",
        "saved_tokens",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(aggregate["repos"])
    return output.getvalue().rstrip()


def build_pr_summary(report: dict[str, Any], only: list[str] | None) -> dict[str, Any]:
    value = build_value_surface(report)
    sections: dict[str, Any] = {}
    if section_allowed("quality", only):
        sections["quality"] = {
            "events": report["quality"]["events"],
            "missed_gate_flags": report["quality"]["missed_gate_flags"],
            "workflow_fit": report["quality"]["workflow_fit"],
        }
    if section_allowed("outcomes", only):
        sections["outcomes"] = value["adoption_outcomes"]
    if section_allowed("learning", only):
        sections["learning"] = value["learning_hygiene"]
    if section_allowed("tokens", only):
        sections["tokens"] = value["token_savings"]
    return {
        "schema_version": "1",
        "created_at": now(),
        "root": report["root"],
        "scope": report["scope"],
        "evidence_confidence": value["evidence_confidence"],
        "sections": sections,
        "recommendations": value["recommendations"],
        "claim_guardrail": "PR summary is local and advisory. Do not paste raw prompts, secrets, PII, PHI, customer data, or raw logs.",
    }


def render_pr_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "## TailTrail PR Summary",
        "",
        f"- Evidence confidence: `{summary['evidence_confidence']}`",
        f"- Scope month: `{summary['scope']['month']}`",
        "",
    ]
    sections = summary["sections"]
    if "quality" in sections:
        lines.extend(["### Quality", "", f"- Events: `{sections['quality']['events']}`", f"- Missed gates: `{len(sections['quality']['missed_gate_flags'])}`", ""])
    if "outcomes" in sections:
        outcomes = sections["outcomes"]
        lines.extend(["### Outcomes", "", f"- Acceptance: `{outcomes['acceptance_rate_percent']}%`", f"- Validation pass: `{outcomes['validation_pass_rate_percent']}%`", ""])
    if "learning" in sections:
        learning = sections["learning"]
        lines.extend(["### Learning", "", f"- Review recommended: `{learning['review_recommended']}`", f"- Weak/do-not-use events: `{learning['weak_or_do_not_use_events']}`", ""])
    if "tokens" in sections:
        token = sections["tokens"]
        lines.extend(["### Token Evidence", "", f"- Evidence level: `{token['evidence_level']}`", f"- Claim guardrail: {token['claim_guardrail']}", ""])
    lines.extend(["### Recommended Actions", ""])
    lines.extend(f"- {item}" for item in summary["recommendations"])
    lines.extend(["", "### Boundary", "", f"- {summary['claim_guardrail']}", ""])
    return "\n".join(lines)


def render_value_markdown(value: dict[str, Any]) -> str:
    outcomes = value["governance_outcomes"]
    adoption = value["adoption_outcomes"]
    evidence = value["evidence_counts"]
    token = value["token_savings"]
    lines = [
        "# TailTrail Value Report",
        "",
        "This report shows local evidence of governed behavior. It is not an exact ROI statement.",
        "",
        "## Scope",
        "",
        f"- Root: `{value['root']}`",
        f"- Month: `{value['scope']['month']}`",
        f"- Start: `{value['scope']['start'] or 'not set'}`",
        f"- End: `{value['scope']['end'] or 'not set'}`",
        f"- Evidence confidence: `{value['evidence_confidence']}`",
        "",
        "## Evidence Counts",
        "",
        f"- Quality events: `{evidence['quality_events']}`",
        f"- Outcome events: `{evidence['outcome_events']}`",
        f"- Learning events: `{evidence['learning_events']}`",
        f"- Learning refresh actions: `{evidence['learning_refresh_actions']}`",
        f"- Measured token records: `{evidence['measured_token_records']}`",
        "",
        "## Governance Outcomes",
        "",
        f"- Dependency gate or avoidance signals: `{outcomes['dependency_gate_or_avoidance_signals']}`",
        f"- Dependencies avoided: `{outcomes['dependencies_avoided']}`",
        f"- Dependency gate signals: `{outcomes['dependency_gate_signals']}`",
        f"- Safeguard preservation signals: `{outcomes['safeguard_preservation_signals']}`",
        f"- Validation truth signals: `{outcomes['validation_truth_signals']}`",
        f"- Focused validation signals: `{outcomes['focused_validation_signals']}`",
        f"- Diff-size or scope-discipline signals: `{outcomes['diff_size_or_scope_discipline_signals']}`",
        f"- Workflow overlap signals: `{outcomes['workflow_overlap_signals']}`",
        f"- Escaped defects: `{outcomes['escaped_defects']}`",
        "",
        "## Adoption Outcomes",
        "",
        f"- Acceptance rate: `{adoption['acceptance_rate_percent']}%`",
        f"- Validation pass rate: `{adoption['validation_pass_rate_percent']}%`",
        f"- Review approval rate: `{adoption['review_approval_rate_percent']}%`",
        "",
    ]
    lines.extend(render_counter("Time Saved Bands", adoption["time_saved_bands"]))
    lines.extend(render_counter("TailTrail Fit", adoption["fit"]))
    lines.extend(
        [
            "## Learning Hygiene",
            "",
            f"- Review recommended: `{value['learning_hygiene']['review_recommended']}`",
            f"- Weak or do-not-use events: `{value['learning_hygiene']['weak_or_do_not_use_events']}`",
            f"- Missing validation events: `{value['learning_hygiene']['missing_validation_events']}`",
            f"- Guardrail risk events: `{value['learning_hygiene']['guardrail_risk_events']}`",
            f"- Recommended command: `{value['learning_hygiene']['recommended_command']}`",
            "",
            "## Token Evidence",
            "",
            f"- Evidence level: `{token['evidence_level']}`",
            f"- Claim guardrail: {token['claim_guardrail']}",
        ]
    )
    if token["evidence_level"] == "api_usage_metadata":
        lines.extend(
            [
                f"- Baseline tokens: `{token['baseline_tokens']}`",
                f"- TailTrail tokens: `{token['tailtrail_tokens']}`",
                f"- Saved tokens: `{token['saved_tokens']}`",
                f"- Reduction: `{token['reduction_percent']}%`",
            ]
        )
    else:
        lines.append(f"- Approx curated context tokens: `{token['approx_tokens']}`")
    lines.extend(["", "## Recommended Actions", ""])
    lines.extend(f"- {item}" for item in value["recommendations"])
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- {value['claim_guardrail']}",
            f"- Privacy: {value['privacy_note']}",
            "",
        ]
    )
    return "\n".join(lines)


def flatten_value(value: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "created_at": value["created_at"],
        "root": value["root"],
        "month": value["scope"]["month"],
        "evidence_confidence": value["evidence_confidence"],
    }
    for group in ("evidence_counts", "governance_outcomes", "adoption_outcomes"):
        for key, item in value[group].items():
            if isinstance(item, dict):
                row[f"{group}.{key}"] = json.dumps(item, sort_keys=True)
            else:
                row[f"{group}.{key}"] = item
    token = value["token_savings"]
    for key in ("evidence_level", "records", "baseline_tokens", "tailtrail_tokens", "saved_tokens", "reduction_percent"):
        row[f"token_savings.{key}"] = token.get(key, "")
    row["learning_hygiene.review_recommended"] = value["learning_hygiene"].get("review_recommended")
    row["recommendations"] = " | ".join(value["recommendations"])
    return row


def render_value_csv(value: dict[str, Any]) -> str:
    row = flatten_value(value)
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(row.keys()))
    writer.writeheader()
    writer.writerow(row)
    return output.getvalue().rstrip()


def render_markdown(report: dict[str, Any], only: list[str] | None = None) -> str:
    lines = [
        "# TailTrail Enterprise Report",
        "",
        "This report is local, advisory, and intended for retrospectives, platform improvement, and governance review.",
        "",
        "## Scope",
        "",
        f"- Root: `{report['root']}`",
        f"- Month: `{report['scope']['month']}`",
        f"- Start: `{report['scope']['start'] or 'not set'}`",
        f"- End: `{report['scope']['end'] or 'not set'}`",
        f"- Include sensitive: `{report['scope']['include_sensitive']}`",
        "",
        "## Executive Summary",
        "",
        f"- Quality events: `{report['quality']['events']}`",
        f"- Outcome events: `{report['outcomes']['events']}`",
        f"- Outcome acceptance rate: `{report['outcomes']['acceptance_rate_percent']}%`",
        f"- Outcome validation pass rate: `{report['outcomes']['validation_pass_rate_percent']}%`",
        f"- Learning events: `{report['learning']['events']}`",
        f"- Learning hygiene review recommended: `{report['learning_hygiene']['review_recommended']}`",
        f"- Learning refresh actions: `{report['learning_refresh']['actions']}`",
        f"- Token evidence: `{report['token_savings']['evidence_level']}`",
        f"- Privacy: {report['privacy_note']}",
        "",
    ]
    if section_allowed("quality", only):
        lines.extend(render_counter("Workflow Fit", report["quality"]["workflow_fit"]))
        lines.extend(render_counter("User Outcomes", report["quality"]["outcomes"]))
        lines.extend(render_counter("Validation Outcomes", report["quality"]["validation"]))
        lines.extend(render_counter("Workflows Used", report["quality"]["workflows"]))
        lines.extend(render_counter("Overlap Flags", report["quality"]["overlap_flags"]))
        lines.extend(render_counter("Missed Gate Flags", report["quality"]["missed_gate_flags"]))
    if section_allowed("outcomes", only):
        lines.extend(
            [
                "## Adoption Outcome Rates",
                "",
                f"- Acceptance rate: `{report['outcomes']['acceptance_rate_percent']}%`",
                f"- Validation pass rate: `{report['outcomes']['validation_pass_rate_percent']}%`",
                f"- Review approval rate: `{report['outcomes']['review_approval_rate_percent']}%`",
                f"- Escaped defects: `{report['outcomes']['escaped_defect_count']}`",
                "",
            ]
        )
        lines.extend(render_counter("Outcome Task Types", report["outcomes"]["task_types"]))
        lines.extend(render_counter("Outcome Workflows", report["outcomes"]["workflows"]))
        lines.extend(render_counter("Outcome Acceptance", report["outcomes"]["acceptance"]))
        lines.extend(render_counter("Outcome Validation", report["outcomes"]["validation"]))
        lines.extend(render_counter("Outcome Review", report["outcomes"]["review"]))
        lines.extend(render_counter("Outcome Time Saved", report["outcomes"]["time_saved"]))
        lines.extend(render_counter("Outcome TailTrail Fit", report["outcomes"]["fit"]))
        lines.extend(render_counter("Outcome Learning Quality", report["outcomes"]["learning_quality"]))
    if section_allowed("learning", only):
        lines.extend(render_counter("Learning Acceptance", report["learning"]["acceptance"]))
        lines.extend(render_counter("Learning Confidence Bands", report["learning"]["confidence_bands"]))
        lines.extend(render_counter("Learning Task Types", report["learning"]["task_types"]))
        lines.extend(render_counter("Common Learning Tags", report["learning"]["tags"]))
        lines.extend(
            [
                "## Learning Hygiene",
                "",
                f"- Weak or do-not-use events: `{report['learning_hygiene']['weak_or_do_not_use_events']}`",
                f"- Rejected events: `{report['learning_hygiene']['rejected_events']}`",
                f"- Missing validation events: `{report['learning_hygiene']['missing_validation_events']}`",
                f"- Guardrail risk events: `{report['learning_hygiene']['guardrail_risk_events']}`",
                f"- Override risk events: `{report['learning_hygiene']['override_risk_events']}`",
                f"- Blocking refresh actions: `{report['learning_hygiene']['blocking_refresh_actions']}`",
                f"- Review recommended: `{report['learning_hygiene']['review_recommended']}`",
                f"- Recommended command: `{report['learning_hygiene']['recommended_command']}`",
                f"- Rule: {report['learning_hygiene']['rule']}",
                "",
                "## Dependency Discipline",
                "",
                f"- Dependency gate applied: `{report['learning']['dependency_gate_applied']}`",
                f"- No new dependency recorded: `{report['learning']['no_new_dependency']}`",
                "",
            ]
        )
        lines.extend(render_counter("Learning Refresh Actions", report["learning_refresh"]["action_counts"]))
    if report["aidlc"].get("included"):
        lines.extend(
            [
                "## AIDLC Artifacts",
                "",
                f"- Files: `{report['aidlc']['files']}`",
                f"- Validation handoffs: `{report['aidlc']['validation_handoffs']}`",
                f"- Handoffs: `{report['aidlc']['handoffs']}`",
                "",
            ]
        )
    if section_allowed("tokens", only):
        token = report["token_savings"]
        lines.extend(
            [
                "## Token And Context Savings",
                "",
                f"- Evidence level: `{token['evidence_level']}`",
                f"- Claim guardrail: {token['claim_guardrail']}",
            ]
        )
        if token["evidence_level"] == "api_usage_metadata":
            lines.extend(
                [
                    f"- Records: `{token['records']}`",
                    f"- Baseline tokens: `{token['baseline_tokens']}`",
                    f"- TailTrail tokens: `{token['tailtrail_tokens']}`",
                    f"- Saved tokens: `{token['saved_tokens']}`",
                    f"- Reduction: `{token['reduction_percent']}%`",
                ]
            )
        else:
            lines.append(f"- Approx curated context tokens: `{token['approx_tokens']}`")
    lines.extend(
        [
            "",
            "## Recommended Review Questions",
            "",
            "- Are too-heavy or too-light workflow signals recurring?",
            "- Are dependency changes consistently using Dependency Gate?",
            "- Are validation gaps concentrated in one workflow or team area?",
            "- Are accepted learnings high-confidence enough to reuse?",
            "- Are stale learning actions increasing?",
            "- Is token-savings language backed by measured telemetry or only local estimates?",
            "",
            "## Decision Boundary",
            "",
            f"- {report['decision_note']}",
            "- Recommended changes require explicit review before editing TailTrail rules, prompts, Navigator logic, guardrails, or local policy.",
            "",
        ]
    )
    return "\n".join(lines)


def render_key_value_csv(report: dict[str, Any]) -> str:
    rows = [
        ("created_at", report["created_at"]),
        ("root", report["root"]),
        ("month", report["scope"]["month"]),
        ("quality_events", report["quality"]["events"]),
        ("outcome_events", report["outcomes"]["events"]),
        ("learning_events", report["learning"]["events"]),
        ("acceptance_rate_percent", report["outcomes"]["acceptance_rate_percent"]),
        ("validation_pass_rate_percent", report["outcomes"]["validation_pass_rate_percent"]),
        ("learning_review_recommended", report["learning_hygiene"]["review_recommended"]),
        ("token_evidence_level", report["token_savings"]["evidence_level"]),
        ("token_saved_tokens", report["token_savings"].get("saved_tokens", "")),
        ("token_reduction_percent", report["token_savings"].get("reduction_percent", "")),
    ]
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["metric", "value"])
    writer.writerows(rows)
    return output.getvalue().rstrip()


def load_report(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Unable to read JSON report {path}: {error}") from error
    if not isinstance(data, dict):
        raise SystemExit(f"Report must be a JSON object: {path}")
    return data


def compare_values(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    previous_value = previous if "governance_outcomes" in previous else build_value_surface(previous)
    current_value = current if "governance_outcomes" in current else build_value_surface(current)
    deltas: dict[str, Any] = {}
    for section in ("evidence_counts", "governance_outcomes"):
        deltas[section] = {}
        for key, current_item in current_value[section].items():
            previous_item = previous_value[section].get(key, 0)
            if isinstance(current_item, (int, float)) and isinstance(previous_item, (int, float)):
                deltas[section][key] = current_item - previous_item
    for key in ("acceptance_rate_percent", "validation_pass_rate_percent", "review_approval_rate_percent"):
        current_item = current_value["adoption_outcomes"].get(key, 0)
        previous_item = previous_value["adoption_outcomes"].get(key, 0)
        if isinstance(current_item, (int, float)) and isinstance(previous_item, (int, float)):
            deltas[f"adoption_outcomes.{key}"] = round(current_item - previous_item, 2)
    return {
        "schema_version": "1",
        "created_at": now(),
        "previous_scope": previous_value["scope"],
        "current_scope": current_value["scope"],
        "previous_confidence": previous_value["evidence_confidence"],
        "current_confidence": current_value["evidence_confidence"],
        "deltas": deltas,
        "claim_guardrail": "Comparison is local and advisory. Differences depend on explicitly supplied local reports only.",
    }


def render_compare_markdown(compare: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Value Comparison",
        "",
        "This comparison uses only the two local JSON reports supplied by the user.",
        "",
        f"- Previous month: `{compare['previous_scope']['month']}`",
        f"- Current month: `{compare['current_scope']['month']}`",
        f"- Previous evidence confidence: `{compare['previous_confidence']}`",
        f"- Current evidence confidence: `{compare['current_confidence']}`",
        "",
        "## Deltas",
        "",
    ]
    for section, values in compare["deltas"].items():
        if isinstance(values, dict):
            lines.append(f"### {section}")
            lines.append("")
            lines.extend(f"- {key}: `{value:+}`" for key, value in values.items())
            lines.append("")
        else:
            lines.append(f"- {section}: `{values:+}`")
    lines.extend(["", "## Claim Boundary", "", f"- {compare['claim_guardrail']}", ""])
    return "\n".join(lines)


def write_report(root: Path, body: str, path: Path | None) -> Path:
    output = path or root / REPORT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(body + ("\n" if not body.endswith("\n") else ""), encoding="utf-8")
    return output


def default_output_path(root: Path, action: str, output_format: str) -> Path:
    if action == "trend" and output_format == "json":
        return root / TAILTRAIL_DIR / "metrics-trend.json"
    if action == "trend" and output_format == "csv":
        return root / TAILTRAIL_DIR / "metrics-trend.csv"
    if action == "trend":
        return root / TAILTRAIL_DIR / "metrics-trend.md"
    if action == "aggregate" and output_format == "json":
        return root / TAILTRAIL_DIR / "multi-repo-aggregate.json"
    if action == "aggregate" and output_format == "csv":
        return root / TAILTRAIL_DIR / "multi-repo-aggregate.csv"
    if action == "aggregate":
        return root / TAILTRAIL_DIR / "multi-repo-aggregate.md"
    if action == "pr" and output_format == "json":
        return root / TAILTRAIL_DIR / "pr-summary.json"
    if action == "pr":
        return root / TAILTRAIL_DIR / "pr-summary.md"
    if action == "compare" and output_format == "json":
        return root / TAILTRAIL_DIR / "value-comparison.json"
    if action == "compare" and output_format == "csv":
        return root / TAILTRAIL_DIR / "value-comparison.csv"
    if action == "compare":
        return root / TAILTRAIL_DIR / "value-comparison.md"
    if action == "value" and output_format == "json":
        return root / TAILTRAIL_DIR / "value-report.json"
    if action == "value" and output_format == "csv":
        return root / VALUE_REPORT_CSV
    if action == "value":
        return root / VALUE_REPORT_PATH
    if output_format == "json":
        return root / TAILTRAIL_DIR / "enterprise-report.json"
    if output_format == "csv":
        return root / TAILTRAIL_DIR / "enterprise-report.csv"
    return root / REPORT_PATH


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a local TailTrail enterprise report from local artifacts.")
    parser.add_argument("action", nargs="?", choices=("enterprise", "value", "compare", "trend", "aggregate", "pr"), default="enterprise")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--month", help="YYYY-MM scope filter.")
    parser.add_argument("--start", help="ISO timestamp/date lower bound.")
    parser.add_argument("--end", help="ISO timestamp/date upper bound.")
    parser.add_argument("--include-sensitive", action="store_true")
    parser.add_argument("--include-aidlc", action="store_true")
    parser.add_argument("--token-telemetry", help="Optional measured token telemetry JSONL.")
    parser.add_argument("--previous-report", type=Path, help="Previous JSON report for `compare`.")
    parser.add_argument("--current-report", type=Path, help="Current JSON report for `compare`.")
    parser.add_argument("--report-file", action="append", type=Path, default=[], help="Local JSON report file for `aggregate`. Repeat for multiple repos.")
    parser.add_argument("--only", action="append", choices=("quality", "outcomes", "learning", "tokens"), help="Render only selected sections. Repeat for multiple sections.")
    parser.add_argument("--format", choices=("markdown", "json", "csv"), default="markdown")
    parser.add_argument("--write-result", nargs="?", const="", help="Write report to path or .tailtrail/enterprise-report.md.")
    return parser


def main() -> int:
    args = parser().parse_args()
    if args.action == "trend":
        trend = build_trend(args)
        if args.format == "csv":
            body = render_trend_csv(trend)
        elif args.format == "json":
            body = json.dumps(trend, indent=2, sort_keys=True)
        else:
            body = render_trend_markdown(trend)
        print(body)
        if args.write_result is not None:
            destination = Path(args.write_result) if args.write_result else default_output_path(args.root.resolve(), args.action, args.format)
            path = write_report(args.root.resolve(), body, destination)
            print(f"\nWrote metrics trend to {path}")
        return 0
    if args.action == "aggregate":
        if not args.report_file:
            raise SystemExit("report aggregate requires at least one --report-file")
        aggregate = build_aggregate(args.report_file)
        if args.format == "csv":
            body = render_aggregate_csv(aggregate)
        elif args.format == "json":
            body = json.dumps(aggregate, indent=2, sort_keys=True)
        else:
            body = render_aggregate_markdown(aggregate)
        print(body)
        if args.write_result is not None:
            destination = Path(args.write_result) if args.write_result else default_output_path(args.root.resolve(), args.action, args.format)
            path = write_report(args.root.resolve(), body, destination)
            print(f"\nWrote multi-repo aggregate to {path}")
        return 0
    if args.action == "compare":
        if not args.previous_report or not args.current_report:
            raise SystemExit("report compare requires --previous-report and --current-report")
        comparison = compare_values(load_report(args.previous_report), load_report(args.current_report))
        if args.format == "csv":
            rows = []
            for section, values in comparison["deltas"].items():
                if isinstance(values, dict):
                    rows.extend({"metric": f"{section}.{key}", "delta": value} for key, value in values.items())
                else:
                    rows.append({"metric": section, "delta": values})
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=["metric", "delta"])
            writer.writeheader()
            writer.writerows(rows)
            body = output.getvalue().rstrip()
        elif args.format == "json":
            body = json.dumps(comparison, indent=2, sort_keys=True)
        else:
            body = render_compare_markdown(comparison)
        print(body)
        if args.write_result is not None:
            destination = Path(args.write_result) if args.write_result else default_output_path(args.root.resolve(), args.action, args.format)
            path = write_report(args.root.resolve(), body, destination)
            print(f"\nWrote value comparison to {path}")
        return 0

    report = build_report(args)
    if args.action == "pr":
        summary = build_pr_summary(report, args.only)
        if args.format == "json":
            body = json.dumps(summary, indent=2, sort_keys=True)
        elif args.format == "csv":
            raise SystemExit("report pr supports markdown or json")
        else:
            body = render_pr_markdown(summary)
        print(body)
        if args.write_result is not None:
            destination = Path(args.write_result) if args.write_result else default_output_path(args.root.resolve(), args.action, args.format)
            path = write_report(args.root.resolve(), body, destination)
            print(f"\nWrote PR summary to {path}")
        return 0
    if args.action == "value":
        value = build_value_surface(report)
        if args.format == "json":
            body = json.dumps(value, indent=2, sort_keys=True)
        elif args.format == "csv":
            body = render_value_csv(value)
        else:
            body = render_value_markdown(value)
    elif args.format == "json":
        body = json.dumps(report, indent=2, sort_keys=True)
    elif args.format == "csv":
        body = render_key_value_csv(report)
    else:
        body = render_markdown(report, args.only)
    print(body)
    if args.write_result is not None:
        destination = Path(args.write_result) if args.write_result else default_output_path(args.root.resolve(), args.action, args.format)
        path = write_report(args.root.resolve(), body, destination)
        print(f"\nWrote {args.action} report to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
