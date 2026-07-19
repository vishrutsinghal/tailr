#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TAILTRAIL_DIR = Path(".tailtrail")
EVENTS = TAILTRAIL_DIR / "quality-events.jsonl"
SUMMARY = TAILTRAIL_DIR / "quality-summary.md"
DECISIONS = TAILTRAIL_DIR / "quality-decisions.md"

FIT_VALUES = {"too-heavy", "too-light", "correct", "unknown"}
OUTCOME_VALUES = {"accepted", "rejected", "revised", "partially-accepted", "unknown"}
VALIDATION_VALUES = {"pass", "fail", "not-run", "unknown"}
SENSITIVITY_VALUES = {"normal", "sensitive"}
APPROVAL_VALUES = {"proposed", "approved", "rejected", "deferred"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def month_key(value: str | None) -> str:
    parsed = parse_time(value)
    if not parsed:
        return "unknown"
    return f"{parsed.year:04d}-{parsed.month:02d}"


def safe_text(value: str, limit: int = 240) -> str:
    text = " ".join(value.strip().split())
    return text[:limit]


def read_events(root: Path) -> list[dict[str, Any]]:
    path = root / EVENTS
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise SystemExit(f"Invalid quality event JSON on line {line_number}: {error}") from error
        if isinstance(value, dict):
            events.append(value)
    return events


def append_event(root: Path, event: dict[str, Any]) -> Path:
    path = root / EVENTS
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return path


def write_text(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def validate_choice(name: str, value: str, allowed: set[str]) -> str:
    if value not in allowed:
        raise SystemExit(f"{name} must be one of: {', '.join(sorted(allowed))}")
    return value


def build_event(args: argparse.Namespace) -> dict[str, Any]:
    fit = validate_choice("fit", args.fit, FIT_VALUES)
    outcome = validate_choice("outcome", args.outcome, OUTCOME_VALUES)
    validation_outcome = validate_choice("validation-outcome", args.validation_outcome, VALIDATION_VALUES)
    sensitivity = validate_choice("sensitivity", args.sensitivity, SENSITIVITY_VALUES)
    approval_status = validate_choice("approval-status", args.approval_status, APPROVAL_VALUES)
    return {
        "schema_version": "1",
        "timestamp": now(),
        "repo": args.repo or args.root.resolve().name,
        "task_type": args.task_type,
        "goal_summary": safe_text(args.goal_summary or "not recorded"),
        "workflow_selected": split_csv(args.workflow),
        "workflow_skipped": split_csv(args.skipped),
        "recommendation_source": args.source,
        "guardrails_applied": split_csv(args.guardrails),
        "docs_loaded": split_csv(args.docs_loaded),
        "exact_materials_preserved": split_csv(args.exact_materials),
        "checks_run": split_csv(args.checks),
        "validation_outcome": validation_outcome,
        "validation_summary": safe_text(args.validation_summary or "not recorded"),
        "user_acceptance": outcome,
        "workflow_fit": fit,
        "overlap_flags": split_csv(args.overlap_flags),
        "missed_gate_flags": split_csv(args.missed_gate_flags),
        "improvement_suggestion": safe_text(args.suggestion or "not recorded"),
        "sensitivity": sensitivity,
        "approval_status": approval_status,
        "notes": safe_text(args.notes or "compact quality event only; no raw prompt, logs, secrets, PII, or PHI recorded"),
    }


def filter_events(events: list[dict[str, Any]], month: str | None, include_sensitive: bool) -> list[dict[str, Any]]:
    filtered = [event for event in events if include_sensitive or event.get("sensitivity") == "normal"]
    if month:
        filtered = [event for event in filtered if month_key(str(event.get("timestamp", ""))) == month]
    return filtered


def summarize_events(root: Path, month: str | None, include_sensitive: bool) -> dict[str, Any]:
    events = filter_events(read_events(root), month, include_sensitive)
    workflow_counts: Counter[str] = Counter()
    skipped_counts: Counter[str] = Counter()
    fit_counts: Counter[str] = Counter()
    outcome_counts: Counter[str] = Counter()
    validation_counts: Counter[str] = Counter()
    overlap_counts: Counter[str] = Counter()
    missed_gate_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    suggestions: list[dict[str, str]] = []

    for event in events:
        for workflow in event.get("workflow_selected", []):
            workflow_counts[str(workflow)] += 1
        for workflow in event.get("workflow_skipped", []):
            skipped_counts[str(workflow)] += 1
        for flag in event.get("overlap_flags", []):
            overlap_counts[str(flag)] += 1
        for flag in event.get("missed_gate_flags", []):
            missed_gate_counts[str(flag)] += 1
        fit_counts[str(event.get("workflow_fit", "unknown"))] += 1
        outcome_counts[str(event.get("user_acceptance", "unknown"))] += 1
        validation_counts[str(event.get("validation_outcome", "unknown"))] += 1
        source_counts[str(event.get("recommendation_source", "unknown"))] += 1
        suggestion = str(event.get("improvement_suggestion", "")).strip()
        if suggestion and suggestion != "not recorded":
            suggestions.append(
                {
                    "timestamp": str(event.get("timestamp", "")),
                    "task_type": str(event.get("task_type", "unknown")),
                    "suggestion": suggestion,
                }
            )

    return {
        "created_at": now(),
        "root": root.as_posix(),
        "month": month or "all",
        "events_checked": len(events),
        "workflow_counts": dict(workflow_counts.most_common()),
        "skipped_counts": dict(skipped_counts.most_common()),
        "fit_counts": dict(fit_counts.most_common()),
        "outcome_counts": dict(outcome_counts.most_common()),
        "validation_counts": dict(validation_counts.most_common()),
        "overlap_counts": dict(overlap_counts.most_common()),
        "missed_gate_counts": dict(missed_gate_counts.most_common()),
        "source_counts": dict(source_counts.most_common()),
        "recent_suggestions": suggestions[-10:],
        "note": "Quality summary is advisory. Routine coding prompts should not load raw quality-events.jsonl.",
    }


def recommendation(area: str, issue: str, evidence: str, files: list[str], prompt_change: str) -> dict[str, Any]:
    return {
        "area": area,
        "issue": issue,
        "evidence": evidence,
        "proposed_files_may_be_impacted": files,
        "prompt_or_rule_change": prompt_change,
        "review_note": "Recommended change only. Review before editing TailTrail files, prompts, Navigator rules, or local policy.",
    }


def propose_improvements(summary: dict[str, Any]) -> list[dict[str, Any]]:
    total = int(summary.get("events_checked", 0))
    if total == 0:
        return [
            recommendation(
                "quality-loop",
                "No quality events recorded yet.",
                "There is no local evidence to tune TailTrail behavior.",
                ["USER-GUIDE.md", "TAILTRAIL-COMMANDS.md"],
                "Ask teams to record a few approved quality events after meaningful TailTrail usage before changing rules.",
            )
        ]

    fit_counts = summary.get("fit_counts", {})
    outcome_counts = summary.get("outcome_counts", {})
    missed_gate_counts = summary.get("missed_gate_counts", {})
    overlap_counts = summary.get("overlap_counts", {})
    workflow_counts = summary.get("workflow_counts", {})
    proposals: list[dict[str, Any]] = []

    too_heavy = int(fit_counts.get("too-heavy", 0))
    too_light = int(fit_counts.get("too-light", 0))
    rejected = int(outcome_counts.get("rejected", 0)) + int(outcome_counts.get("revised", 0))
    if too_heavy / total > 0.2:
        proposals.append(
            recommendation(
                "navigator",
                "TailTrail may be choosing heavy workflows too often.",
                f"{too_heavy} of {total} events were marked too-heavy.",
                ["scripts/navigator.py", "context/navigator.md", "ROADMAP.md"],
                "Tighten tiny/small-task routing so AIDLC, handoff, broad review, and graph cache checks are skipped unless risk signals are present.",
            )
        )
    if too_light / total > 0.2:
        proposals.append(
            recommendation(
                "guardrails",
                "TailTrail may be skipping important gates for risky work.",
                f"{too_light} of {total} events were marked too-light.",
                ["GUARDRAILS.md", "context/guardrail-layers.md", "scripts/navigator.py"],
                "Strengthen risk detection for auth, dependency, CI/Sonar, vulnerability, migration, and regulated-work prompts.",
            )
        )
    if rejected >= 3:
        proposals.append(
            recommendation(
                "prompting",
                "Users are rejecting or revising TailTrail outputs repeatedly.",
                f"{rejected} of {total} events were rejected or revised.",
                ["context/navigator.md", "TAILTRAIL-COMMANDS.md", "USER-GUIDE.md"],
                "Make Navigator ask for plan edits earlier and keep implementation plans shorter until user approval is clear.",
            )
        )
    if int(missed_gate_counts.get("dependency-gate", 0)) > 1:
        proposals.append(
            recommendation(
                "dependency-gate",
                "Dependency work missed the dependency gate more than once.",
                f"dependency-gate missed {missed_gate_counts.get('dependency-gate')} times.",
                ["DEPENDENCY-GATE.md", "scripts/navigator.py", "context/guardrail-layers.md"],
                "Route package, dependency, CVE, transitive dependency, and version-change prompts through Dependency Gate by default.",
            )
        )
    if overlap_counts:
        flag, count = next(iter(overlap_counts.items()))
        if int(count) > 1:
            proposals.append(
                recommendation(
                    "workflow-overlap",
                    "TailTrail workflows appear to overlap.",
                    f"`{flag}` appeared {count} times.",
                    ["context/flow-catalog.md", "context/navigator.md", "scripts/navigator.py"],
                    "Clarify which feature owns the work and which features should be skipped for the same goal.",
                )
            )
    if int(workflow_counts.get("learning", 0)) == 0 and total >= 5:
        proposals.append(
            recommendation(
                "learning",
                "Reusable outcomes may not be captured.",
                "No events selected a learning workflow across at least five quality events.",
                ["context/learning-agent.md", "context/navigator.md", "USER-GUIDE.md"],
                "Suggest post-task learning capture only for accepted, reusable CI/Sonar, dependency, validation, and bug-fix patterns.",
            )
        )
    if not proposals:
        proposals.append(
            recommendation(
                "quality-loop",
                "No recurring quality issue crossed the local threshold.",
                "Workflow fit, user outcome, overlap, and missed-gate counts look acceptable for the selected scope.",
                ["No file changes recommended"],
                "Keep observing with compact approved events; do not tune TailTrail rules yet.",
            )
        )
    return proposals


def render_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Quality Summary",
        "",
        "This summary is advisory. It is for TailTrail tuning and should not be loaded into routine coding prompts.",
        "",
        "## Scope",
        "",
        f"- Root: `{summary['root']}`",
        f"- Month: `{summary['month']}`",
        f"- Events checked: `{summary['events_checked']}`",
        "",
    ]
    sections = [
        ("Workflow Counts", "workflow_counts"),
        ("Skipped Counts", "skipped_counts"),
        ("Workflow Fit", "fit_counts"),
        ("User Outcomes", "outcome_counts"),
        ("Validation Outcomes", "validation_counts"),
        ("Overlap Flags", "overlap_counts"),
        ("Missed Gate Flags", "missed_gate_counts"),
        ("Recommendation Sources", "source_counts"),
    ]
    for title, key in sections:
        lines.extend([f"## {title}", ""])
        values = summary.get(key, {})
        if values:
            lines.extend(f"- {name}: `{count}`" for name, count in values.items())
        else:
            lines.append("- none")
        lines.append("")
    lines.extend(["## Recent Suggestions", ""])
    suggestions = summary.get("recent_suggestions", [])
    if suggestions:
        for item in suggestions:
            lines.append(f"- `{item['timestamp']}` {item['task_type']}: {item['suggestion']}")
    else:
        lines.append("- none")
    lines.extend(["", "## Token Safety", "", "- Do not load `.tailtrail/quality-events.jsonl` into routine coding prompts.", "- Use this summary only during quality review, Navigator tuning, or local policy review.", ""])
    return "\n".join(lines)


def render_proposals(summary: dict[str, Any], proposals: list[dict[str, Any]]) -> str:
    lines = [
        "# TailTrail Quality Improvement Proposals",
        "",
        "These are recommended changes only. Review before editing TailTrail files, prompts, Navigator rules, or local policy.",
        "",
        f"- Source summary month: `{summary['month']}`",
        f"- Events checked: `{summary['events_checked']}`",
        "",
    ]
    for index, item in enumerate(proposals, start=1):
        lines.extend(
            [
                f"## {index}. {item['area']}",
                "",
                f"- Issue: {item['issue']}",
                f"- Evidence: {item['evidence']}",
                "- Files may be impacted:",
            ]
        )
        lines.extend(f"  - `{path}`" for path in item["proposed_files_may_be_impacted"])
        lines.extend(
            [
                f"- Prompt/rule change: {item['prompt_or_rule_change']}",
                f"- Note: {item['review_note']}",
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
        print("# TailTrail Quality Event")
        print("")
        print("This is a compact behavior event. It must not contain raw prompts, secrets, PII, PHI, or raw logs.")
        print("")
        print("```json")
        print(json.dumps(event, indent=2, sort_keys=True))
        print("```")
    if not args.approved:
        print("")
        print("Not recorded. Re-run with `--approved` to append this event to `.tailtrail/quality-events.jsonl`.")
        return 0
    path = append_event(root, event)
    print(f"Recorded quality event in {path}")
    return 0


def command_summarize(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    summary = summarize_events(root, args.month, args.include_sensitive)
    if args.write_result:
        write_text(root / SUMMARY, render_summary(summary))
    if args.format == "json":
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(render_summary(summary))
    return 0


def command_review(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    summary = summarize_events(root, args.month, args.include_sensitive)
    proposals = propose_improvements(summary)
    if args.area:
        proposals = [item for item in proposals if item["area"] == args.area]
    report = {
        "created_at": now(),
        "root": root.as_posix(),
        "summary": summary,
        "proposals": proposals,
        "note": "Review-only. No TailTrail files or policy files were changed.",
    }
    if args.write_result:
        write_text(root / SUMMARY, render_summary(summary))
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_summary(summary))
        print("")
        print(render_proposals(summary, proposals))
    return 0


def command_propose(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    summary = summarize_events(root, args.month, args.include_sensitive)
    proposals = propose_improvements(summary)
    if args.area:
        proposals = [item for item in proposals if item["area"] == args.area]
    if args.format == "json":
        print(json.dumps({"created_at": now(), "summary": summary, "proposals": proposals}, indent=2, sort_keys=True))
    else:
        print(render_proposals(summary, proposals))
    return 0


def command_decide(args: argparse.Namespace) -> int:
    if not args.approved:
        raise SystemExit("decide requires --approved")
    root = args.root.resolve()
    status = validate_choice("status", args.status, APPROVAL_VALUES)
    entry = [
        f"## {now()}",
        "",
        f"- Status: `{status}`",
        f"- Area: `{args.area}`",
        f"- Decision: {safe_text(args.decision, 500)}",
        f"- Reason: {safe_text(args.reason or 'not recorded', 500)}",
        "",
    ]
    path = root / DECISIONS
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else "# TailTrail Quality Decisions\n\nApproved or rejected changes to TailTrail usage rules and local policy.\n\n"
    path.write_text(existing.rstrip() + "\n\n" + "\n".join(entry), encoding="utf-8")
    print(f"Recorded quality decision in {path}")
    return 0


def add_scope_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--month")
    parser.add_argument("--area")
    parser.add_argument("--include-sensitive", action="store_true")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--write-result", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture and review TailTrail behavior quality signals.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser("capture", help="Record a compact approved quality event.")
    capture.add_argument("--root", type=Path, default=Path.cwd())
    capture.add_argument("--repo")
    capture.add_argument("--task-type", default="unknown")
    capture.add_argument("--goal-summary")
    capture.add_argument("--workflow", default="")
    capture.add_argument("--skipped", default="")
    capture.add_argument("--source", default="manual")
    capture.add_argument("--guardrails", default="")
    capture.add_argument("--docs-loaded", default="")
    capture.add_argument("--exact-materials", default="")
    capture.add_argument("--checks", default="")
    capture.add_argument("--validation-outcome", default="unknown")
    capture.add_argument("--validation-summary")
    capture.add_argument("--outcome", default="unknown")
    capture.add_argument("--fit", default="unknown")
    capture.add_argument("--overlap-flags", default="")
    capture.add_argument("--missed-gate-flags", default="")
    capture.add_argument("--suggestion")
    capture.add_argument("--sensitivity", default="normal")
    capture.add_argument("--approval-status", default="proposed")
    capture.add_argument("--notes")
    capture.add_argument("--approved", action="store_true")
    capture.add_argument("--format", choices=("markdown", "json"), default="markdown")

    summarize = subparsers.add_parser("summarize", help="Summarize quality events.")
    add_scope_args(summarize)

    review = subparsers.add_parser("review", help="Summarize and propose reviewable improvements.")
    add_scope_args(review)

    propose = subparsers.add_parser("propose", help="Propose TailTrail tuning recommendations.")
    add_scope_args(propose)

    decide = subparsers.add_parser("decide", help="Record an approved quality-loop decision.")
    decide.add_argument("--root", type=Path, default=Path.cwd())
    decide.add_argument("--area", required=True)
    decide.add_argument("--decision", required=True)
    decide.add_argument("--reason")
    decide.add_argument("--status", choices=sorted(APPROVAL_VALUES), default="approved")
    decide.add_argument("--approved", action="store_true")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "capture":
        return command_capture(args)
    if args.command == "summarize":
        return command_summarize(args)
    if args.command == "review":
        return command_review(args)
    if args.command == "propose":
        return command_propose(args)
    if args.command == "decide":
        return command_decide(args)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
