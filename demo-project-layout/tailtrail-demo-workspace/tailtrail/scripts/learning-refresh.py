#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TAILTRAIL_DIR = Path(".tailtrail")
EVENTS = TAILTRAIL_DIR / "learning-events.jsonl"
GRAPH_LEARNING_INDEX = TAILTRAIL_DIR / "graph-learning-index.json"
REFRESH_ACTIONS = TAILTRAIL_DIR / "learning-refresh-actions.json"
REFRESH_REPORT = TAILTRAIL_DIR / "learning-refresh-report.md"

BLOCKING_ACTIONS = {"mark-stale", "suppress", "archive", "delete"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def split_csv(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    import hashlib

    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


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
            raise SystemExit(f"Invalid learning event JSON on line {line_number}: {error}") from error
        if isinstance(value, dict):
            events.append(value)
    return events


def load_graph_links(root: Path) -> list[dict[str, Any]]:
    data = read_json(root / GRAPH_LEARNING_INDEX)
    if not data:
        return []
    links = data.get("learning_links", [])
    return [item for item in links if isinstance(item, dict)] if isinstance(links, list) else []


def load_actions(root: Path) -> dict[str, Any]:
    data = read_json(root / REFRESH_ACTIONS)
    if not data:
        return {"schema_version": "1", "updated_at": now(), "actions": []}
    if not isinstance(data.get("actions"), list):
        data["actions"] = []
    return data


def active_actions(root: Path) -> dict[str, list[dict[str, Any]]]:
    actions = load_actions(root)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for action in actions.get("actions", []):
        if not isinstance(action, dict):
            continue
        learning_id = str(action.get("learning_id", ""))
        if learning_id:
            grouped.setdefault(learning_id, []).append(action)
    return grouped


def confidence(event: dict[str, Any]) -> dict[str, Any]:
    value = event.get("learning_confidence", {})
    return value if isinstance(value, dict) else {}


def score(event: dict[str, Any]) -> int:
    value = confidence(event).get("score", 0)
    return int(value) if isinstance(value, int) else 0


def band(event: dict[str, Any]) -> str:
    return str(confidence(event).get("band", "unknown"))


def graph_stale_reasons(root: Path, links: list[dict[str, Any]]) -> list[str]:
    reasons: list[str] = []
    for link in links:
        hashes = link.get("file_hashes", {})
        if not isinstance(hashes, dict):
            reasons.append("graph-learning link has invalid file_hashes")
            continue
        for rel, expected in hashes.items():
            actual = file_sha256(root / str(rel))
            if actual is None:
                reasons.append(f"{rel} is missing")
            elif actual != expected:
                reasons.append(f"{rel} changed after graph-learning link creation")
    return reasons


def policy_changed_after(root: Path, event_time: datetime | None) -> list[str]:
    if not event_time:
        return []
    reasons: list[str] = []
    for name in ("tailtrail-policy.md", "DEPENDENCY-GATE.md", "GUARDRAILS.md", "sonar-project.properties"):
        path = root / name
        if path.is_file():
            modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            if modified > event_time:
                reasons.append(f"{name} changed after learning capture")
    return reasons


def duplicate_groups(events: list[dict[str, Any]]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for event in events:
        candidate = str(event.get("learning_candidate", "")).strip().lower()
        candidate = re.sub(r"\s+", " ", candidate)
        if not candidate:
            continue
        key = candidate + "|" + ",".join(sorted(str(tag) for tag in event.get("tags", [])))
        groups.setdefault(key, []).append(str(event.get("id", "")))
    return {key: ids for key, ids in groups.items() if len([item for item in ids if item]) > 1}


def recommend_event(
    root: Path,
    event: dict[str, Any],
    links_by_id: dict[str, list[dict[str, Any]]],
    action_map: dict[str, list[dict[str, Any]]],
    duplicate_ids: set[str],
    days: int,
) -> dict[str, Any]:
    learning_id = str(event.get("id", "unknown"))
    reasons: list[str] = []
    action = "keep"
    event_score = score(event)
    event_band = band(event)
    timestamp = parse_time(str(event.get("timestamp", "")))
    age_days = None
    if timestamp:
        age_days = (datetime.now(timezone.utc) - timestamp).days

    if action_map.get(learning_id):
        recent = action_map[learning_id][-1]
        action = str(recent.get("action", "keep"))
        reasons.append(f"existing refresh action: {action}")
    if event.get("sensitivity") != "normal":
        action = "suppress"
        reasons.append("sensitive learning should not auto-surface")
    if event.get("acceptance") == "rejected":
        action = "suppress"
        reasons.append("user rejected the solution")
    if event_score < 40:
        action = "suppress"
        reasons.append("confidence score is below 40")
    elif event_score < 60 and action not in BLOCKING_ACTIONS:
        action = "demote"
        reasons.append("confidence score is weak")
    elif event_score < 80 and action == "keep":
        action = "improve"
        reasons.append("candidate learning needs stronger evidence before trusted reuse")
    if event.get("validation_outcome") in {"fail", "not-run", "skipped"} and action not in BLOCKING_ACTIONS:
        action = "improve" if event_score >= 60 else "demote"
        reasons.append(f"validation outcome is {event.get('validation_outcome')}")
    if event.get("user_override") in {"proceed-anyway", "record-low-confidence-event"} and action not in BLOCKING_ACTIONS:
        action = "demote"
        reasons.append(f"user override recorded: {event.get('user_override')}")

    graph_reasons = graph_stale_reasons(root, links_by_id.get(learning_id, []))
    if graph_reasons:
        action = "mark-stale"
        reasons.extend(graph_reasons)

    policy_reasons = policy_changed_after(root, timestamp)
    if policy_reasons and action not in BLOCKING_ACTIONS:
        action = "improve"
        reasons.extend(policy_reasons)

    if age_days is not None and age_days >= days and action == "keep":
        action = "improve"
        reasons.append(f"learning is {age_days} days old")

    if learning_id in duplicate_ids and action == "keep":
        action = "merge"
        reasons.append("duplicate learning candidate detected")

    if not reasons:
        reasons.append("high-confidence learning has no stale signals")

    return {
        "learning_id": learning_id,
        "action": action,
        "score": event_score,
        "band": event_band,
        "task_type": event.get("task_type", "unknown"),
        "tags": event.get("tags", []),
        "candidate": event.get("learning_candidate", ""),
        "reasons": reasons,
        "age_days": age_days,
    }


def build_report(root: Path, tags: set[str], days: int, include_sensitive: bool) -> dict[str, Any]:
    events = read_events(root)
    if tags:
        events = [event for event in events if tags.intersection(set(str(tag) for tag in event.get("tags", [])))]
    if not include_sensitive:
        events = [event for event in events if event.get("sensitivity") == "normal"]

    links_by_id: dict[str, list[dict[str, Any]]] = {}
    for link in load_graph_links(root):
        learning_id = str(link.get("learning_id", ""))
        if learning_id:
            links_by_id.setdefault(learning_id, []).append(link)

    duplicates = duplicate_groups(events)
    duplicate_ids = {learning_id for ids in duplicates.values() for learning_id in ids}
    action_map = active_actions(root)
    recommendations = [recommend_event(root, event, links_by_id, action_map, duplicate_ids, days) for event in events]

    summary: dict[str, int] = {
        "events_checked": len(events),
        "trusted": sum(1 for event in events if band(event) == "trusted"),
        "candidate": sum(1 for event in events if band(event) == "candidate"),
        "weak_note": sum(1 for event in events if band(event) == "weak-note"),
        "do_not_use": sum(1 for event in events if band(event) == "do-not-use"),
        "linked_graph_learnings": sum(1 for item in links_by_id.values() for _ in item),
        "duplicates": len(duplicates),
    }
    for recommendation in recommendations:
        key = "action_" + recommendation["action"].replace("-", "_")
        summary[key] = summary.get(key, 0) + 1

    return {
        "created_at": now(),
        "root": root.as_posix(),
        "tags": sorted(tags),
        "days": days,
        "summary": summary,
        "recommendations": recommendations,
        "duplicates": duplicates,
        "report_path": (root / REFRESH_REPORT).as_posix(),
        "note": "Advisory report only. No learning files are changed unless apply --approved is used.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Learning Refresh Report",
        "",
        "This report is advisory. Review recommendations before applying any refresh action.",
        "",
        "## Summary",
        "",
    ]
    for key, value in sorted(report["summary"].items()):
        lines.append(f"- {key.replace('_', ' ').title()}: `{value}`")
    lines.extend(["", "## Recommended Actions", ""])
    recommendations = report.get("recommendations", [])
    if not recommendations:
        lines.append("- No learning events found for the selected scope.")
    for item in recommendations:
        lines.extend(
            [
                f"### {item['learning_id']}",
                "",
                f"- Action: `{item['action']}`",
                f"- Score: `{item['score']} / 100` ({item['band']})",
                f"- Type: `{item['task_type']}`",
                f"- Tags: {', '.join(item.get('tags', [])) or 'none'}",
                f"- Candidate: {item.get('candidate') or 'not recorded'}",
                "- Reasons:",
            ]
        )
        lines.extend(f"  - {reason}" for reason in item.get("reasons", []))
        lines.append("")
    lines.extend(
        [
            "## Approval",
            "",
            "- No learning files were changed by this report.",
            "- Use `python3 scripts/tailtrail.py learn refresh apply --action mark-stale --learning-id ID --approved` to record an approved refresh action.",
            "- Current source, CI, scanner, policy, and guardrail evidence wins over old learning.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(root: Path, report: dict[str, Any], fmt: str) -> Path:
    path = root / REFRESH_REPORT
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(report, indent=2, sort_keys=True) if fmt == "json" else render_markdown(report)
    path.write_text(body + "\n", encoding="utf-8")
    return path


def command_recommend(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    report = build_report(root, split_csv(args.tags), args.days, args.include_sensitive)
    if args.write_result:
        write_report(root, report, args.format)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report))
    return 0


def command_inspect(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    return command_recommend(args)


def command_stale(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    report = build_report(root, split_csv(args.tags), args.days, args.include_sensitive)
    report["recommendations"] = [
        item for item in report["recommendations"] if item["action"] in {"mark-stale", "suppress", "archive", "demote"} or (item.get("age_days") is not None and item["age_days"] >= args.days)
    ]
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report))
    return 0


def command_apply(args: argparse.Namespace) -> int:
    if not args.approved:
        raise SystemExit("apply requires --approved")
    root = args.root.resolve()
    actions = load_actions(root)
    entry = {
        "learning_id": args.learning_id,
        "action": args.action,
        "reason": args.reason or "approved learning refresh action",
        "approved": True,
        "created_at": now(),
    }
    existing = [item for item in actions.get("actions", []) if isinstance(item, dict)]
    existing.append(entry)
    actions["actions"] = existing
    actions["updated_at"] = now()
    path = root / REFRESH_ACTIONS
    write_json(path, actions)
    if args.format == "json":
        print(json.dumps({"path": path.as_posix(), "action": entry}, indent=2, sort_keys=True))
    else:
        print(f"Recorded refresh action `{args.action}` for `{args.learning_id}` in {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect and recommend TailTrail learning refresh actions.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--root", type=Path, default=Path.cwd())
        sub.add_argument("--tags")
        sub.add_argument("--days", type=int, default=90)
        sub.add_argument("--include-sensitive", action="store_true")
        sub.add_argument("--format", choices=("markdown", "json"), default="markdown")
        sub.add_argument("--write-result", action="store_true")

    inspect = subparsers.add_parser("inspect", help="Inspect learning freshness.")
    common(inspect)
    recommend = subparsers.add_parser("recommend", help="Recommend refresh actions.")
    common(recommend)
    stale = subparsers.add_parser("stale", help="Show stale or suppressed learning candidates.")
    common(stale)

    apply = subparsers.add_parser("apply", help="Record an approved refresh action.")
    apply.add_argument("--root", type=Path, default=Path.cwd())
    apply.add_argument("--learning-id", required=True)
    apply.add_argument("--action", choices=("keep", "improve", "demote", "mark-stale", "suppress", "archive", "merge", "delete"), required=True)
    apply.add_argument("--reason")
    apply.add_argument("--approved", action="store_true")
    apply.add_argument("--format", choices=("markdown", "json"), default="markdown")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "inspect":
        return command_inspect(args)
    if args.command == "recommend":
        return command_recommend(args)
    if args.command == "stale":
        return command_stale(args)
    if args.command == "apply":
        return command_apply(args)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
