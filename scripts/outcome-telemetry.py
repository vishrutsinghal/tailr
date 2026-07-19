#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TAILTRAIL_DIR = Path(".tailtrail")
OUTCOME_EVENTS = TAILTRAIL_DIR / "outcome-events.jsonl"
OUTCOME_SUMMARY = TAILTRAIL_DIR / "outcome-summary.md"

TASK_TYPES = {
    "bug-fix",
    "feature",
    "refactor",
    "review",
    "ci-sonar",
    "vulnerability",
    "dependency",
    "documentation",
    "test",
    "unknown",
}
ACCEPTANCE_VALUES = {"accepted", "partially-accepted", "revised", "rejected", "unknown"}
VALIDATION_VALUES = {"pass", "fail", "not-run", "blocked", "unknown"}
REVIEW_VALUES = {"approved", "changes-requested", "not-reviewed", "not-needed", "unknown"}
DEFECT_VALUES = {"yes", "no", "unknown"}
TIME_SAVED_VALUES = {"none", "lt15m", "15-30m", "30-60m", "1-2h", "2h-plus", "unknown"}
FIT_VALUES = {"too-heavy", "too-light", "correct", "unknown"}
LEARNING_VALUES = {"not-used", "weak", "cautious", "trusted", "refreshed", "unknown"}
SENSITIVITY_VALUES = {"normal", "sensitive"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_text(value: str | None, limit: int = 240) -> str:
    if not value:
        return "not recorded"
    return " ".join(value.strip().split())[:limit]


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def validate_choice(name: str, value: str, allowed: set[str]) -> str:
    if value not in allowed:
        raise SystemExit(f"{name} must be one of: {', '.join(sorted(allowed))}")
    return value


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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
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
            raise SystemExit(f"Invalid outcome event JSON on line {line_number}: {error}") from error
        if isinstance(value, dict):
            records.append(value)
    return records


def write_jsonl(root: Path, event: dict[str, Any]) -> Path:
    path = root / OUTCOME_EVENTS
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return path


def in_scope(record: dict[str, Any], month: str | None) -> bool:
    if not month:
        return True
    return month_key(str(record.get("timestamp", ""))) == month


def scoped(records: list[dict[str, Any]], month: str | None, include_sensitive: bool) -> list[dict[str, Any]]:
    values = [record for record in records if in_scope(record, month)]
    if include_sensitive:
        return values
    return [record for record in values if record.get("sensitivity", "normal") == "normal"]


def count(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        value = record.get(key)
        if isinstance(value, list):
            for item in value:
                counter[str(item)] += 1
        elif value is not None:
            counter[str(value)] += 1
    return dict(counter.most_common())


def bool_count(records: list[dict[str, Any]], key: str) -> int:
    return sum(1 for record in records if record.get(key) is True)


def build_event(args: argparse.Namespace) -> dict[str, Any]:
    task_type = validate_choice("task-type", args.task_type, TASK_TYPES)
    acceptance = validate_choice("acceptance", args.acceptance, ACCEPTANCE_VALUES)
    validation = validate_choice("validation-outcome", args.validation_outcome, VALIDATION_VALUES)
    review = validate_choice("review-outcome", args.review_outcome, REVIEW_VALUES)
    defect = validate_choice("defect-escaped", args.defect_escaped, DEFECT_VALUES)
    time_saved = validate_choice("time-saved", args.time_saved, TIME_SAVED_VALUES)
    fit = validate_choice("fit", args.fit, FIT_VALUES)
    learning_quality = validate_choice("learning-quality", args.learning_quality, LEARNING_VALUES)
    sensitivity = validate_choice("sensitivity", args.sensitivity, SENSITIVITY_VALUES)
    workflows = split_csv(args.workflow)
    return {
        "schema_version": "1",
        "timestamp": now(),
        "task_id": safe_text(args.task_id or f"task-{now()}"),
        "repo": args.repo or args.root.resolve().name,
        "task_type": task_type,
        "workflow_selected": workflows,
        "user_acceptance": acceptance,
        "validation_outcome": validation,
        "review_outcome": review,
        "defect_escaped": defect,
        "time_saved_band": time_saved,
        "tailtrail_fit": fit,
        "learning_quality": learning_quality,
        "plan_edited": bool(args.plan_edited),
        "dependency_gate_used": bool(args.dependency_gate_used),
        "guardrails_used": bool(args.guardrails_used),
        "aidlc_used": "aidlc" in {item.lower() for item in workflows} or bool(args.aidlc_used),
        "quality_or_security_scan_used": bool(args.scan_used),
        "notes": safe_text(args.notes),
        "sensitivity": sensitivity,
        "privacy": "Compact approved outcome only. No raw prompts, raw logs, secrets, PII, PHI, customer data, or source snippets.",
    }


def summarize(root: Path, month: str | None, include_sensitive: bool) -> dict[str, Any]:
    records = scoped(read_jsonl(root / OUTCOME_EVENTS), month, include_sensitive)
    accepted = sum(1 for item in records if item.get("user_acceptance") in {"accepted", "partially-accepted"})
    validation_pass = sum(1 for item in records if item.get("validation_outcome") == "pass")
    reviewed_good = sum(1 for item in records if item.get("review_outcome") == "approved")
    escaped = sum(1 for item in records if item.get("defect_escaped") == "yes")
    total = len(records)
    return {
        "schema_version": "1",
        "created_at": now(),
        "root": root.as_posix(),
        "month": month or "all",
        "events": total,
        "acceptance_rate_percent": round((accepted / total) * 100, 2) if total else 0.0,
        "validation_pass_rate_percent": round((validation_pass / total) * 100, 2) if total else 0.0,
        "review_approval_rate_percent": round((reviewed_good / total) * 100, 2) if total else 0.0,
        "escaped_defect_count": escaped,
        "task_types": count(records, "task_type"),
        "workflows": count(records, "workflow_selected"),
        "acceptance": count(records, "user_acceptance"),
        "validation": count(records, "validation_outcome"),
        "review": count(records, "review_outcome"),
        "defects": count(records, "defect_escaped"),
        "time_saved": count(records, "time_saved_band"),
        "fit": count(records, "tailtrail_fit"),
        "learning_quality": count(records, "learning_quality"),
        "plan_edits": bool_count(records, "plan_edited"),
        "dependency_gate_used": bool_count(records, "dependency_gate_used"),
        "guardrails_used": bool_count(records, "guardrails_used"),
        "aidlc_used": bool_count(records, "aidlc_used"),
        "scan_used": bool_count(records, "quality_or_security_scan_used"),
        "privacy_note": "Local approved outcomes only. Do not store raw prompts, raw logs, secrets, PII, PHI, customer data, or source snippets.",
    }


def render_counter(title: str, values: dict[str, int]) -> list[str]:
    lines = [f"## {title}", ""]
    if values:
        lines.extend(f"- {key}: `{value}`" for key, value in values.items())
    else:
        lines.append("- none")
    lines.append("")
    return lines


def render_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Adoption Outcome Summary",
        "",
        "This summary is local and advisory. It measures whether TailTrail appears to help; it is not surveillance.",
        "",
        "## Scope",
        "",
        f"- Root: `{summary['root']}`",
        f"- Month: `{summary['month']}`",
        f"- Events: `{summary['events']}`",
        "",
        "## Outcome Rates",
        "",
        f"- Acceptance rate: `{summary['acceptance_rate_percent']}%`",
        f"- Validation pass rate: `{summary['validation_pass_rate_percent']}%`",
        f"- Review approval rate: `{summary['review_approval_rate_percent']}%`",
        f"- Escaped defects: `{summary['escaped_defect_count']}`",
        "",
    ]
    for title, key in (
        ("Task Types", "task_types"),
        ("Workflows", "workflows"),
        ("User Acceptance", "acceptance"),
        ("Validation Outcomes", "validation"),
        ("Review Outcomes", "review"),
        ("Escaped Defects", "defects"),
        ("Time Saved Bands", "time_saved"),
        ("TailTrail Fit", "fit"),
        ("Learning Quality", "learning_quality"),
    ):
        lines.extend(render_counter(title, summary[key]))
    lines.extend(
        [
            "## Feature Usage Counters",
            "",
            f"- Plan edits: `{summary['plan_edits']}`",
            f"- Dependency gate used: `{summary['dependency_gate_used']}`",
            f"- Guardrails used: `{summary['guardrails_used']}`",
            f"- AIDLC used: `{summary['aidlc_used']}`",
            f"- Quality/security scan used: `{summary['scan_used']}`",
            "",
            "## Privacy",
            "",
            f"- {summary['privacy_note']}",
            "- Load this summary for retrospectives; do not load raw `.tailtrail/outcome-events.jsonl` into routine coding prompts.",
            "",
        ]
    )
    return "\n".join(lines)


def command_capture(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    event = build_event(args)
    if args.format == "json":
        print(json.dumps({"will_record": args.approved, "event": event}, indent=2, sort_keys=True))
    else:
        print("# TailTrail Outcome Event")
        print("")
        print("Compact approved outcome only. Do not include raw prompts, logs, secrets, PII, PHI, customer data, or source snippets.")
        print("")
        print("```json")
        print(json.dumps(event, indent=2, sort_keys=True))
        print("```")
    if not args.approved:
        print("")
        print("Not recorded. Re-run with `--approved` to append this event to `.tailtrail/outcome-events.jsonl`.")
        return 0
    path = write_jsonl(root, event)
    print(f"Recorded outcome event in {path}")
    return 0


def command_summarize(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    summary = summarize(root, args.month, args.include_sensitive)
    body = json.dumps(summary, indent=2, sort_keys=True) if args.format == "json" else render_summary(summary)
    print(body)
    if args.write_result:
        path = root / OUTCOME_SUMMARY
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body + ("\n" if not body.endswith("\n") else ""), encoding="utf-8")
        print(f"\nWrote outcome summary to {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture and summarize local TailTrail adoption outcome evidence.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser("capture", help="Capture one approved adoption outcome event.")
    capture.add_argument("--root", type=Path, default=Path.cwd())
    capture.add_argument("--repo")
    capture.add_argument("--task-id")
    capture.add_argument("--task-type", default="unknown")
    capture.add_argument("--workflow", default="")
    capture.add_argument("--acceptance", default="unknown")
    capture.add_argument("--validation-outcome", default="unknown")
    capture.add_argument("--review-outcome", default="unknown")
    capture.add_argument("--defect-escaped", default="unknown")
    capture.add_argument("--time-saved", default="unknown")
    capture.add_argument("--fit", default="unknown")
    capture.add_argument("--learning-quality", default="unknown")
    capture.add_argument("--plan-edited", action="store_true")
    capture.add_argument("--dependency-gate-used", action="store_true")
    capture.add_argument("--guardrails-used", action="store_true")
    capture.add_argument("--aidlc-used", action="store_true")
    capture.add_argument("--scan-used", action="store_true")
    capture.add_argument("--notes")
    capture.add_argument("--sensitivity", default="normal")
    capture.add_argument("--approved", action="store_true")
    capture.add_argument("--format", choices=("markdown", "json"), default="markdown")

    summarize_parser = subparsers.add_parser("summarize", help="Summarize approved adoption outcome events.")
    summarize_parser.add_argument("--root", type=Path, default=Path.cwd())
    summarize_parser.add_argument("--month")
    summarize_parser.add_argument("--include-sensitive", action="store_true")
    summarize_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    summarize_parser.add_argument("--write-result", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "capture":
        return command_capture(args)
    if args.command == "summarize":
        return command_summarize(args)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
