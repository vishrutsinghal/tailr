#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if SCRIPT_DIR.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPT_DIR.as_posix())

import navigator_core as core


DEFAULT_EVENTS = Path(".tailtrail") / "token-budget-events.jsonl"
DEFAULT_PROFILE = Path(".tailtrail") / "token-budget-profile.json"


BASE_BUDGETS = {
    "tiny": 3000,
    "repo-overview": 5000,
    "bug": 8000,
    "review": 9000,
    "qa": 10000,
    "refactor": 12000,
    "dependency": 12000,
    "ci-sonar": 15000,
    "security": 16000,
    "handoff": 9000,
    "feature": 18000,
    "implementation": 14000,
    "release": 22000,
}


@dataclass(frozen=True)
class BudgetEstimate:
    budget_tokens: int
    confidence: str
    task_types: list[str]
    graph_status: str
    similar_events: int
    reasons: list[str]
    escalation_rule: str
    evidence_level: str


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def write_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def graph_status(root: Path, changed: list[str]) -> str:
    shared_cache = root / "tailtrail-meta" / "code-graph-cache.json"
    local_cache = root / ".tailtrail" / "code-graph-cache.json"
    cache = shared_cache if shared_cache.exists() else local_cache
    if not cache.exists():
        return "missing"
    try:
        value = json.loads(cache.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "invalid"
    if not isinstance(value, dict):
        return "invalid"
    if not changed:
        return "present"
    source_files = value.get("source_files", {})
    if not isinstance(source_files, dict) and isinstance(value.get("entries"), list):
        covered = set()
        for entry in value["entries"]:
            if isinstance(entry, dict) and isinstance(entry.get("source_files"), dict):
                covered.update(entry["source_files"].keys())
        return "present" if any(item in covered for item in changed) else "missing-scope"
    if isinstance(source_files, dict) and any(item in source_files for item in changed):
        return "present"
    return "missing-scope"


def primary_task(tasks: list[str]) -> str:
    priority = ["security", "ci-sonar", "feature", "implementation", "refactor", "dependency", "qa", "bug", "review", "handoff", "repo-overview"]
    for item in priority:
        if item in tasks:
            return item
    return tasks[0] if tasks else "implementation"


def language_tags(changed: list[str]) -> list[str]:
    suffix_map = {
        ".py": "python",
        ".java": "java",
        ".cs": "dotnet",
        ".sql": "sql",
        ".tf": "terraform",
        ".ts": "node",
        ".tsx": "node",
        ".js": "node",
        ".jsx": "node",
        ".go": "go",
    }
    tags = []
    for item in changed:
        suffix = Path(item).suffix.lower()
        tag = suffix_map.get(suffix)
        if tag and tag not in tags:
            tags.append(tag)
    return tags or ["unknown"]


def similar_events(events: list[dict[str, Any]], task: str, languages: list[str]) -> list[dict[str, Any]]:
    language_set = set(languages)
    matches = []
    for event in events:
        if event.get("task_type") != task:
            continue
        event_languages = set(event.get("languages", [])) if isinstance(event.get("languages"), list) else set()
        if event_languages and language_set and not event_languages.intersection(language_set):
            continue
        if isinstance(event.get("actual_context_tokens"), int):
            matches.append(event)
    return matches


def round_budget(value: int) -> int:
    return max(2000, int(round(value / 500.0) * 500))


def estimate_budget(root: Path, goal: str, changed: list[str], events_path: Path | None = None) -> BudgetEstimate:
    root = root.resolve()
    tasks = core.task_types(goal)
    risks = core.risk_indicators(goal, changed)
    tiny = core.is_tiny(goal, risks, changed)
    if tiny:
        tasks = ["tiny"]
    task = primary_task(tasks)
    graph = graph_status(root, changed)
    languages = language_tags(changed)
    events = read_jsonl(events_path or root / DEFAULT_EVENTS)
    matches = similar_events(events, task, languages)

    budget = BASE_BUDGETS.get(task, BASE_BUDGETS["implementation"])
    reasons = [f"base budget for `{task}` task: {budget}"]

    if len(changed) > 1:
        bump = min(6000, (len(changed) - 1) * 1500)
        budget += bump
        reasons.append(f"changed file count adds {bump} tokens")
    if graph in {"missing", "missing-scope", "invalid"} and not tiny:
        budget += 2500
        reasons.append(f"graph cache is {graph}; allow discovery overhead")
    elif graph == "present":
        budget -= 1000
        reasons.append("graph cache exists for the scope; reduce discovery overhead")
    if any(risk in risks for risk in ("auth/security", "vulnerability scan", "dependency", "regulated", "production")):
        budget += 3000
        reasons.append("risk signal requires extra exact context")

    if matches:
        actuals = [int(item["actual_context_tokens"]) for item in matches]
        median_actual = int(statistics.median(actuals))
        blended = int((budget * 0.55) + (median_actual * 0.45))
        reasons.append(f"{len(matches)} similar approved events found; median actual context {median_actual}")
        budget = blended

    budget = round_budget(budget)
    confidence = "low"
    if matches:
        confidence = "medium" if len(matches) < 4 else "high"
    elif graph == "present" and changed:
        confidence = "medium"

    return BudgetEstimate(
        budget_tokens=budget,
        confidence=confidence,
        task_types=tasks,
        graph_status=graph,
        similar_events=len(matches),
        reasons=reasons,
        escalation_rule=f"If required context appears to exceed {round_budget(int(budget * 1.25))} tokens, pause and ask before loading more.",
        evidence_level="learned_local_events" if matches else "local_estimate",
    )


def estimate_payload(root: Path, goal: str, changed: list[str], events_path: Path | None = None) -> dict[str, Any]:
    estimate = estimate_budget(root, goal, changed, events_path)
    return {
        "schema_version": "1",
        "type": "token-budget-estimate",
        "created_at": now(),
        "root": root.resolve().as_posix(),
        "goal_hash": stable_hash(goal),
        "changed_count": len(changed),
        "changed_files": changed[:10],
        "task_types": estimate.task_types,
        "budget_tokens": estimate.budget_tokens,
        "confidence": estimate.confidence,
        "graph_status": estimate.graph_status,
        "similar_events": estimate.similar_events,
        "evidence_level": estimate.evidence_level,
        "reasons": estimate.reasons,
        "escalation_rule": estimate.escalation_rule,
        "claim_guardrail": "Budget is guidance, not a hard stop. Exact token savings still require model/API telemetry.",
    }


def event_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    goal_hash = stable_hash(args.goal) if args.goal else "not-provided"
    changed = args.changed or []
    tasks = core.task_types(args.goal) if args.goal else [args.task_type]
    task = args.task_type or primary_task(tasks)
    return {
        "schema_version": "1",
        "type": "token-budget-event",
        "created_at": now(),
        "root_hash": stable_hash(root.as_posix()),
        "task_id": args.task_id or stable_hash(f"{goal_hash}:{now()}"),
        "goal_hash": goal_hash,
        "task_type": task,
        "task_types": tasks,
        "languages": language_tags(changed),
        "changed_count": len(changed),
        "graph_status": args.graph_status or graph_status(root, changed),
        "initial_budget_tokens": args.initial_budget,
        "actual_context_tokens": args.actual_context,
        "needed_context_tokens": args.needed_context,
        "escalated": args.escalated,
        "outcome": args.outcome,
        "reason": args.reason or "",
        "privacy": "No raw prompt, source, logs, secrets, PII, PHI, or customer data should be stored in this event.",
    }


def update_profile(root: Path, events_path: Path | None = None, profile_path: Path | None = None) -> dict[str, Any]:
    events_file = events_path or root / DEFAULT_EVENTS
    profile_file = profile_path or root / DEFAULT_PROFILE
    events = read_jsonl(events_file)
    groups: dict[str, list[int]] = {}
    escalations: dict[str, int] = {}
    for event in events:
        task = str(event.get("task_type", "unknown"))
        actual = event.get("actual_context_tokens")
        if not isinstance(actual, int):
            continue
        groups.setdefault(task, []).append(actual)
        if event.get("escalated") == "yes":
            escalations[task] = escalations.get(task, 0) + 1
    profile = {
        "schema_version": "1",
        "type": "token-budget-profile",
        "updated_at": now(),
        "events": sum(len(values) for values in groups.values()),
        "tasks": {},
        "claim_guardrail": "Profile improves future local estimates. It is not exact model/API token usage.",
    }
    for task, values in sorted(groups.items()):
        profile["tasks"][task] = {
            "records": len(values),
            "median_actual_context_tokens": int(statistics.median(values)),
            "p75_actual_context_tokens": int(statistics.quantiles(values, n=4)[2]) if len(values) >= 4 else max(values),
            "escalations": escalations.get(task, 0),
        }
    profile_file.parent.mkdir(parents=True, exist_ok=True)
    profile_file.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return profile


def render_estimate(report: dict[str, Any]) -> str:
    lines = [
        "# Token Budget Coach",
        "",
        f"- Budget: `{report['budget_tokens']}` context tokens",
        f"- Confidence: `{report['confidence']}`",
        f"- Evidence level: `{report['evidence_level']}`",
        f"- Task types: `{', '.join(report['task_types'])}`",
        f"- Graph status: `{report['graph_status']}`",
        f"- Similar events: `{report['similar_events']}`",
        f"- Escalation rule: {report['escalation_rule']}",
        f"- Claim guardrail: {report['claim_guardrail']}",
        "",
        "## Reasons",
    ]
    lines.extend(f"- {item}" for item in report["reasons"])
    return "\n".join(lines) + "\n"


def render_profile(profile: dict[str, Any]) -> str:
    lines = [
        "# Token Budget Profile",
        "",
        f"- Events: `{profile['events']}`",
        f"- Updated at: `{profile['updated_at']}`",
        f"- Claim guardrail: {profile['claim_guardrail']}",
        "",
        "## Task Profiles",
    ]
    tasks = profile.get("tasks", {})
    if not tasks:
        lines.append("- no approved token budget events recorded")
    else:
        for task, item in tasks.items():
            lines.append(
                f"- `{task}`: records `{item['records']}`, median `{item['median_actual_context_tokens']}`, p75 `{item['p75_actual_context_tokens']}`, escalations `{item['escalations']}`"
            )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Learn local token budget estimates from approved context usage events.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    estimate = subparsers.add_parser("estimate", help="Estimate a context token budget for a task.")
    estimate.add_argument("goal", nargs="*", help="Task goal.")
    estimate.add_argument("--root", type=Path, default=Path.cwd())
    estimate.add_argument("--changed", action="append", default=[])
    estimate.add_argument("--events", type=Path, default=None)
    estimate.add_argument("--format", choices=("markdown", "json"), default="markdown")

    record = subparsers.add_parser("record", help="Record an approved token budget outcome.")
    record.add_argument("--root", type=Path, default=Path.cwd())
    record.add_argument("--goal", default="")
    record.add_argument("--task-id", default="")
    record.add_argument("--task-type", default="")
    record.add_argument("--changed", action="append", default=[])
    record.add_argument("--graph-status", default="")
    record.add_argument("--initial-budget", type=int, required=True)
    record.add_argument("--actual-context", type=int, required=True)
    record.add_argument("--needed-context", type=int, default=None)
    record.add_argument("--escalated", choices=("yes", "no"), default="no")
    record.add_argument("--outcome", choices=("sufficient", "underestimated", "overestimated", "unknown"), default="unknown")
    record.add_argument("--reason", default="")
    record.add_argument("--events", type=Path, default=None)
    record.add_argument("--profile", type=Path, default=None)
    record.add_argument("--approved", action="store_true")
    record.add_argument("--format", choices=("markdown", "json"), default="markdown")

    profile = subparsers.add_parser("profile", help="Summarize recorded token budget outcomes.")
    profile.add_argument("--root", type=Path, default=Path.cwd())
    profile.add_argument("--events", type=Path, default=None)
    profile.add_argument("--profile", type=Path, default=None)
    profile.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "estimate":
        goal = " ".join(args.goal).strip()
        report = estimate_payload(args.root, goal, args.changed, args.events)
        print(json.dumps(report, indent=2) if args.format == "json" else render_estimate(report), end="")
        return 0
    if args.command == "record":
        if not args.approved:
            raise SystemExit("Refusing to record token budget event without --approved.")
        if args.initial_budget <= 0 or args.actual_context <= 0:
            raise SystemExit("--initial-budget and --actual-context must be greater than zero.")
        event = event_payload(args)
        write_jsonl(args.events or args.root / DEFAULT_EVENTS, event)
        profile = update_profile(args.root, args.events, args.profile)
        if args.format == "json":
            print(json.dumps({"recorded": event, "profile": profile}, indent=2))
        else:
            print("# Token Budget Event Recorded\n")
            print(f"- Task type: `{event['task_type']}`")
            print(f"- Initial budget: `{event['initial_budget_tokens']}`")
            print(f"- Actual context: `{event['actual_context_tokens']}`")
            print(f"- Escalated: `{event['escalated']}`")
            print("- Privacy: raw prompt/source/log content was not recorded.")
        return 0
    if args.command == "profile":
        profile = update_profile(args.root, args.events, args.profile)
        print(json.dumps(profile, indent=2) if args.format == "json" else render_profile(profile), end="")
        return 0
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
