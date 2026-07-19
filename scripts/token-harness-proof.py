#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_LEDGER = Path(".tailtrail") / "token-harness-events.jsonl"
DEFAULT_TELEMETRY = Path(".tailtrail") / "token-usage.jsonl"
SENSITIVE_CLASSES = {"security", "vulnerability", "release", "regulated", "production-incident", "auth", "permission", "permissions"}
PRICING_FIELDS = {"cost", "cost_usd", "price", "pricing", "dollars", "usd", "amount_usd"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_jsonl(path: Path, *, strict: bool = False) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    if not path.is_file():
        return rows, issues
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError as error:
            issue = {"file": path.as_posix(), "line": line_number, "reason": f"invalid JSON: {error.msg}"}
            issues.append(issue)
            continue
        if not isinstance(value, dict):
            issues.append({"file": path.as_posix(), "line": line_number, "reason": "record is not an object"})
            continue
        value["_line_number"] = line_number
        rows.append(value)
    if strict and issues:
        rendered = "; ".join(f"{item['file']}:{item['line']} {item['reason']}" for item in issues)
        raise SystemExit("strict mode: invalid proof input rejected: " + rendered)
    return rows, issues


def pricing_paths(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            current = f"{path}.{key}" if path else str(key)
            if str(key).lower() in PRICING_FIELDS:
                found.append(current)
            found.extend(pricing_paths(child, current))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(pricing_paths(child, f"{path}[{index}]"))
    return found


def total_tokens(block: Any) -> int | None:
    if not isinstance(block, dict):
        return None
    total = block.get("total_tokens")
    if isinstance(total, int) and not isinstance(total, bool):
        return total
    input_tokens = block.get("input_tokens")
    output_tokens = block.get("output_tokens")
    if isinstance(input_tokens, int) and not isinstance(input_tokens, bool) and isinstance(output_tokens, int) and not isinstance(output_tokens, bool):
        return input_tokens + output_tokens
    return None


def percent(saved: int, baseline: int) -> float:
    if baseline <= 0:
        return 0.0
    return round((saved / baseline) * 100, 2)


def ledger_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    events = [row for row in rows if row.get("type") == "tailtrail-token-harness-event"]
    before = sum(int(row.get("tokens_before", 0)) for row in events if isinstance(row.get("tokens_before"), int))
    after = sum(int(row.get("tokens_after", 0)) for row in events if isinstance(row.get("tokens_after"), int))
    quality_passed = sum(1 for row in events if row.get("event_type") == "quality_result" and row.get("validation_outcome") == "pass")
    quality_failed = sum(1 for row in events if row.get("event_type") == "quality_result" and row.get("validation_outcome") == "fail")
    event_types: dict[str, int] = {}
    for row in events:
        event_type = str(row.get("event_type", "unknown"))
        event_types[event_type] = event_types.get(event_type, 0) + 1
    return {
        "events": len(events),
        "event_types": event_types,
        "tokens_before": before,
        "tokens_after": after,
        "tokens_saved": max(0, before - after),
        "reduction_percent": percent(max(0, before - after), before),
        "quality_passed": quality_passed,
        "quality_failed": quality_failed,
        "pricing_fields": [path for row in events for path in pricing_paths(row)],
    }


def telemetry_summary(rows: list[dict[str, Any]], *, strict: bool) -> dict[str, Any]:
    measured: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    half_populated: list[dict[str, Any]] = []
    pricing = [path for row in rows for path in pricing_paths(row)]
    for row in rows:
        if row.get("mode") != "measured":
            ignored.append({"line": row.get("_line_number"), "reason": "mode is not measured"})
            continue
        baseline = total_tokens(row.get("baseline"))
        tailtrail = total_tokens(row.get("tailtrail"))
        if baseline is None or tailtrail is None:
            issue = {"line": row.get("_line_number"), "task_id": str(row.get("task_id", "unknown")), "reason": "missing baseline or TailTrail token totals"}
            ignored.append(issue)
            half_populated.append(issue)
            continue
        saved = max(0, baseline - tailtrail)
        measured.append(
            {
                "task_id": str(row.get("task_id", "unknown")),
                "provider": str(row.get("provider", "unknown")),
                "model": str(row.get("model", "unknown")),
                "baseline_tokens": baseline,
                "tailtrail_tokens": tailtrail,
                "saved_tokens": saved,
                "reduction_percent": percent(saved, baseline),
            }
        )
    if strict and half_populated:
        raise SystemExit("strict mode: half-populated measured telemetry rejected")
    baseline_total = sum(row["baseline_tokens"] for row in measured)
    tailtrail_total = sum(row["tailtrail_tokens"] for row in measured)
    saved_total = max(0, baseline_total - tailtrail_total)
    reductions = [float(row["reduction_percent"]) for row in measured]
    return {
        "records": len(rows),
        "measured_records": len(measured),
        "ignored_records": len(ignored),
        "ignored": ignored,
        "measured": measured,
        "baseline_tokens": baseline_total,
        "tailtrail_tokens": tailtrail_total,
        "saved_tokens": saved_total,
        "reduction_percent": percent(saved_total, baseline_total),
        "mean_reduction_percent": round(sum(reductions) / len(reductions), 2) if reductions else 0.0,
        "min_reduction_percent": min(reductions) if reductions else 0.0,
        "max_reduction_percent": max(reductions) if reductions else 0.0,
        "confidence_width": confidence_width(reductions),
        "pricing_fields": pricing,
    }


def confidence_width(values: list[float]) -> float:
    if len(values) < 2:
        return 100.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    stderr = math.sqrt(variance) / math.sqrt(len(values))
    return round(3.92 * stderr, 2)


def confidence_gate(telemetry: dict[str, Any], ledger: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    reasons: list[str] = []
    if telemetry["measured_records"] < args.min_measured_records:
        reasons.append(f"measured record count {telemetry['measured_records']} is below minimum {args.min_measured_records}")
    if telemetry["baseline_tokens"] <= 0:
        reasons.append("measured baseline token total is zero")
    if telemetry["tailtrail_tokens"] >= telemetry["baseline_tokens"] and telemetry["baseline_tokens"] > 0:
        reasons.append("TailTrail measured token total is not lower than baseline")
    if ledger["quality_failed"] > 0:
        reasons.append("quality result failure recorded in Token Harness ledger")
    if telemetry["confidence_width"] > args.max_confidence_width and telemetry["measured_records"] >= 2:
        reasons.append(f"confidence width {telemetry['confidence_width']} exceeds maximum {args.max_confidence_width}")
    if telemetry["pricing_fields"] or ledger["pricing_fields"]:
        reasons.append("pricing/cost fields are not allowed in TH-5 proof inputs")
    return {"passed": not reasons, "reasons": reasons or ["measured telemetry complete and confidence gate passed"]}


def final_label(ledger: dict[str, Any], telemetry: dict[str, Any], gate: dict[str, Any], benchmark_passed: bool) -> tuple[str, bool, str]:
    if gate["passed"] and telemetry["measured_records"] > 0:
        if benchmark_passed:
            return "benchmark-measured", True, "measured telemetry, benchmark evidence, and confidence gate passed"
        return "measured", True, "measured telemetry and confidence gate passed"
    if ledger["events"] > 0:
        return "local-evidence", False, "Token Harness ledger exists but measured proof gate did not pass"
    return "estimated", False, "no Token Harness ledger or complete measured telemetry supplied"


def report_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    ledger_path = args.ledger or root / DEFAULT_LEDGER
    telemetry_path = args.telemetry or root / DEFAULT_TELEMETRY
    ledger_rows, ledger_issues = read_jsonl(ledger_path, strict=args.strict)
    telemetry_rows, telemetry_issues = read_jsonl(telemetry_path, strict=args.strict)
    ledger = ledger_summary(ledger_rows)
    telemetry = telemetry_summary(telemetry_rows, strict=args.strict)
    gate = confidence_gate(telemetry, ledger, args)
    label, measured_allowed, reason = final_label(ledger, telemetry, gate, args.benchmark_passed)
    return {
        "schema_version": "1",
        "type": "tailtrail-token-harness-proof-report",
        "created_at": now(),
        "root": root.as_posix(),
        "ledger_path": ledger_path.as_posix(),
        "telemetry_path": telemetry_path.as_posix(),
        "evidence_label": label,
        "measured_claim_allowed": measured_allowed,
        "reason": reason,
        "ledger": ledger,
        "telemetry": telemetry,
        "confidence": gate,
        "input_issues": {"ledger": ledger_issues, "telemetry": telemetry_issues},
        "claim_guardrail": "Exact model/API savings require complete measured telemetry and confidence gate pass. Local ledger evidence is not enough for measured claims.",
    }


def holdout_payload(args: argparse.Namespace) -> dict[str, Any]:
    task_class = args.task_class.strip().lower().replace("_", "-").replace(" ", "-")
    if task_class in SENSITIVE_CLASSES:
        holdout = False
        reason = "sensitive task class excluded from holdout"
    else:
        key = f"{args.repo_id}|{args.task_id}|{args.holdout_salt}".encode("utf-8")
        bucket = int(hashlib.sha256(key).hexdigest()[:8], 16) % 100
        holdout = bucket < args.holdout_rate
        reason = "deterministic hash selected holdout run" if holdout else "deterministic hash selected shaped run"
    return {
        "schema_version": "1",
        "type": "tailtrail-token-harness-holdout-decision",
        "task_id": args.task_id,
        "task_class": task_class,
        "repo_id": args.repo_id,
        "holdout": holdout,
        "reason": reason,
        "holdout_rate": args.holdout_rate,
        "holdout_salt": args.holdout_salt,
    }


def render_report(payload: dict[str, Any]) -> str:
    ledger = payload["ledger"]
    telemetry = payload["telemetry"]
    confidence = payload["confidence"]
    lines = [
        "# Token Harness Proof Report",
        "",
        f"- Evidence label: `{payload['evidence_label']}`",
        f"- Measured claim allowed: `{str(payload['measured_claim_allowed']).lower()}`",
        f"- Reason: {payload['reason']}",
        f"- Claim guardrail: {payload['claim_guardrail']}",
        "",
        "## Ledger Evidence",
        "",
        f"- Events: `{ledger['events']}`",
        f"- Event types: `{ledger['event_types']}`",
        f"- Local before: `{ledger['tokens_before']}`",
        f"- Local after: `{ledger['tokens_after']}`",
        f"- Local estimated saved: `{ledger['tokens_saved']}`",
        f"- Local estimated reduction: `{ledger['reduction_percent']}%`",
        f"- Quality passed: `{ledger['quality_passed']}`",
        f"- Quality failed: `{ledger['quality_failed']}`",
        "",
        "## Measured Telemetry",
        "",
        f"- Records: `{telemetry['records']}`",
        f"- Measured records: `{telemetry['measured_records']}`",
        f"- Ignored records: `{telemetry['ignored_records']}`",
        f"- Baseline tokens: `{telemetry['baseline_tokens']}`",
        f"- TailTrail tokens: `{telemetry['tailtrail_tokens']}`",
        f"- Saved tokens: `{telemetry['saved_tokens']}`",
        f"- Reduction: `{telemetry['reduction_percent']}%`",
        f"- Mean reduction: `{telemetry['mean_reduction_percent']}%`",
        f"- Confidence width: `{telemetry['confidence_width']}`",
        "",
        "## Confidence Gate",
        "",
        f"- Passed: `{str(confidence['passed']).lower()}`",
    ]
    lines.extend(f"- {reason}" for reason in confidence["reasons"])
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Produce Token Harness proof reports and deterministic holdout decisions.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    report = subparsers.add_parser("report", help="Produce a Token Harness proof report.")
    report.add_argument("--root", type=Path, default=Path.cwd())
    report.add_argument("--ledger", type=Path)
    report.add_argument("--telemetry", type=Path)
    report.add_argument("--min-measured-records", type=int, default=3)
    report.add_argument("--max-confidence-width", type=float, default=40.0)
    report.add_argument("--benchmark-passed", action="store_true")
    report.add_argument("--strict", action="store_true")
    report.add_argument("--format", choices=("markdown", "json"), default="markdown")
    holdout = subparsers.add_parser("holdout", help="Make a deterministic Token Harness holdout decision.")
    holdout.add_argument("--task-id", required=True)
    holdout.add_argument("--task-class", default="general")
    holdout.add_argument("--repo-id", default="local")
    holdout.add_argument("--holdout-rate", type=int, default=10)
    holdout.add_argument("--holdout-salt", default="tailtrail-token-harness-v1")
    holdout.add_argument("--format", choices=("markdown", "json"), default="json")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "holdout":
        payload = holdout_payload(args)
        if args.format == "json":
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"# Token Harness Holdout\n\n- Task: `{payload['task_id']}`\n- Holdout: `{str(payload['holdout']).lower()}`\n- Reason: {payload['reason']}\n")
        return 0
    payload = report_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True) if args.format == "json" else render_report(payload))
    return 1 if payload["confidence"]["passed"] is False and args.strict and payload["telemetry"]["measured_records"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
