#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TAILTRAIL_DIR = Path(".tailtrail")
EVENTS = TAILTRAIL_DIR / "learning-events.jsonl"
INDEX = TAILTRAIL_DIR / "learning-index.md"
LEARNINGS = TAILTRAIL_DIR / "learnings.md"
SCORES = TAILTRAIL_DIR / "learning-scores.jsonl"
POLICY = TAILTRAIL_DIR / "learning-policy.json"
REFRESH_ACTIONS = TAILTRAIL_DIR / "learning-refresh-actions.json"
TEMPLATE = ROOT / "templates" / "learnings.md"

SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|authorization)\s*[:=]\s*\S+"),
    re.compile(r"(?i)bearer\s+[a-z0-9._\-]+"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
]

RISK_THRESHOLDS = {
    "normal": 60,
    "bug": 60,
    "feature": 65,
    "shared-helper": 70,
    "multi-file": 70,
    "dependency": 80,
    "auth": 80,
    "security": 80,
    "payment": 80,
    "data": 80,
    "migration": 80,
    "release": 80,
    "regulated": 85,
    "multi-team": 85,
}


@dataclass(frozen=True)
class Score:
    score: int
    band: str
    status: str
    threshold: int
    positive_factors: list[str]
    negative_factors: list[str]
    promotion_decision: str


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve(root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return root / path


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return sorted({item.strip() for item in value.split(",") if item.strip()})


def redact(text: str) -> str:
    redacted = text
    for pattern in SENSITIVE_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def normalize_text(text: str) -> str:
    return " ".join(redact(text).split())


def event_id(summary: str, timestamp: str) -> str:
    digest = hashlib.sha256(f"{timestamp}:{summary}".encode("utf-8")).hexdigest()[:8]
    return f"{timestamp[:10].replace('-', '')}-{digest}"


def ensure_files(root: Path) -> None:
    tailtrail = root / TAILTRAIL_DIR
    tailtrail.mkdir(parents=True, exist_ok=True)
    learnings = root / LEARNINGS
    if not learnings.exists():
        if TEMPLATE.exists():
            learnings.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            learnings.write_text("# TailTrail Project Learnings\n", encoding="utf-8")
    index = root / INDEX
    if not index.exists():
        index.write_text(render_index([]), encoding="utf-8")
    policy = root / POLICY
    if not policy.exists():
        policy.write_text(
            json.dumps(
                {
                    "capture_enabled": True,
                    "promotion_min_score": 80,
                    "max_search_results": 3,
                    "raw_prompt_capture": False,
                    "sensitive_auto_retrieval": False,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )


def load_policy(root: Path) -> dict[str, Any]:
    ensure_files(root)
    try:
        value = json.loads((root / POLICY).read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        value = {}
    return value if isinstance(value, dict) else {}


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")


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


def read_refresh_actions(root: Path) -> dict[str, str]:
    path = root / REFRESH_ACTIONS
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    actions = value.get("actions", []) if isinstance(value, dict) else []
    result: dict[str, str] = {}
    if isinstance(actions, list):
        for action in actions:
            if not isinstance(action, dict):
                continue
            learning_id = str(action.get("learning_id", ""))
            action_name = str(action.get("action", ""))
            if learning_id and action_name:
                result[learning_id] = action_name
    return result


def find_event(root: Path, wanted: str) -> dict[str, Any]:
    for event in read_events(root):
        if event.get("id") == wanted:
            return event
    raise SystemExit(f"Learning event not found: {wanted}")


def score_event(event: dict[str, Any]) -> Score:
    points = 35
    positive: list[str] = []
    negative: list[str] = []

    acceptance = str(event.get("acceptance", "unknown"))
    if acceptance == "accepted":
        points += 15
        positive.append("user accepted")
    elif acceptance == "partially-accepted":
        points += 8
        positive.append("user partially accepted")
    elif acceptance == "revised":
        points += 5
        positive.append("user revised the solution")
    elif acceptance == "rejected":
        points -= 20
        negative.append("user rejected")
    else:
        negative.append("acceptance unknown")

    validation = str(event.get("validation_outcome", "unknown"))
    if validation == "pass":
        points += 25
        positive.append("validation passed")
    elif validation == "partial":
        points += 10
        positive.append("partial validation evidence")
    elif validation == "fail":
        points -= 25
        negative.append("validation failed")
    elif validation in {"skipped", "not-run"}:
        points -= 10
        negative.append("validation not run")
    else:
        points -= 5
        negative.append("validation unknown")

    if event.get("review_status") == "approved":
        points += 15
        positive.append("review approved")
    elif event.get("review_status") == "changes-requested":
        points -= 15
        negative.append("review requested changes")

    fulfillment = str(event.get("fulfillment_status", "not-evaluated"))
    if fulfillment == "appears-aligned":
        points += 12
        positive.append("implementation appears aligned with requested requirements")
    elif fulfillment == "partially-aligned":
        points += 3
        negative.append("implementation only partially aligned with requested requirements")
    elif fulfillment == "needs-clarification":
        points -= 10
        negative.append("requirement fulfillment needed clarification")

    if event.get("approved_changes"):
        points += min(10, len(event.get("approved_changes", [])) * 3)
        positive.append("approved implementation details recorded")
    if event.get("requested_changes"):
        points -= min(15, len(event.get("requested_changes", [])) * 5)
        negative.append("requested changes recorded")
    if event.get("clarifications"):
        points += min(6, len(event.get("clarifications", [])) * 2)
        positive.append("clarifications captured without raw prompt history")

    if event.get("reused_project_pattern"):
        points += 10
        positive.append("existing project pattern reused")
    if event.get("small_focused_change"):
        points += 10
        positive.append("small focused change")
    if event.get("no_new_dependency"):
        points += 8
        positive.append("no new dependency")
    if event.get("dependency_gate_applied"):
        points += 8
        positive.append("dependency gate applied")
    if event.get("scanner_resolved"):
        points += 15
        positive.append("scanner issue rerun and resolved")
    if event.get("learning_candidate"):
        points += 8
        positive.append("reusable learning candidate")

    risk = str(event.get("risk", "normal"))
    if risk in {"auth", "security", "payment", "data", "migration", "release", "regulated", "multi-team", "dependency"}:
        points -= 12
        negative.append(f"risk-sensitive area: {risk}")
    elif risk in {"shared-helper", "multi-file"}:
        points -= 6
        negative.append(f"broader impact area: {risk}")

    if event.get("sensitivity") != "normal":
        points -= 15
        negative.append("sensitive learning")
    if event.get("user_override") == "proceed-anyway":
        points -= 10
        negative.append("user override proceeded despite risk")
    if event.get("guardrail_weakened"):
        points -= 30
        negative.append("guardrail weakened")
    if event.get("raw_prompt_recorded"):
        points -= 10
        negative.append("raw prompt capture is discouraged")

    score = max(0, min(100, points))
    threshold = RISK_THRESHOLDS.get(risk, 60)
    if score < 40:
        band = "do-not-use"
        status = "do not use"
    elif score < 60:
        band = "weak-note"
        status = "weak historical note"
    elif score < 80:
        band = "candidate"
        status = "candidate learning"
    else:
        band = "trusted"
        status = "trusted reusable repo pattern"

    if score >= threshold and score >= 80 and event.get("sensitivity") == "normal":
        promotion = "eligible"
    elif score >= threshold and score >= 60:
        promotion = "candidate-only"
    else:
        promotion = "not-promoted"

    return Score(score, band, status, threshold, positive, negative, promotion)


def event_from_args(args: argparse.Namespace, root: Path) -> dict[str, Any]:
    policy = load_policy(root)
    if policy.get("capture_enabled") is False:
        raise SystemExit("Learning capture is disabled by .tailtrail/learning-policy.json")

    timestamp = now()
    summary = normalize_text(args.summary)
    candidate = normalize_text(args.candidate or "")
    event = {
        "id": event_id(summary, timestamp),
        "timestamp": timestamp,
        "repo": normalize_text(args.repo or root.name),
        "task_type": args.type,
        "tags": split_csv(args.tags),
        "prompt_summary": normalize_text(args.prompt_summary or summary),
        "files": [Path(item).as_posix() for item in args.file],
        "issue_ids": split_csv(args.issue_ids),
        "validation_commands": [normalize_text(item) for item in args.validation_command],
        "validation_outcome": args.validation_outcome,
        "solution_summary": normalize_text(args.solution or ""),
        "acceptance": args.acceptance,
        "acceptance_reason": normalize_text(args.reason or ""),
        "approved_changes": [normalize_text(item) for item in args.approved_change],
        "requested_changes": [normalize_text(item) for item in args.requested_change],
        "clarifications": [normalize_text(item) for item in args.clarification],
        "fulfillment_status": args.fulfillment_status,
        "learning_candidate": candidate,
        "risk": args.risk,
        "sensitivity": args.sensitivity,
        "review_status": args.review_status,
        "user_override": args.user_override,
        "reused_project_pattern": args.reused_project_pattern,
        "small_focused_change": args.small_focused_change,
        "no_new_dependency": args.no_new_dependency,
        "dependency_gate_applied": args.dependency_gate_applied,
        "scanner_resolved": args.scanner_resolved,
        "guardrail_weakened": args.guardrail_weakened,
        "promotion_decision": "not-scored",
        "stale_when": normalize_text(args.stale_when or ""),
    }
    score = score_event(event)
    event["learning_confidence"] = score.__dict__
    event["promotion_decision"] = score.promotion_decision
    return event


def render_learning_signal(event: dict[str, Any]) -> str:
    confidence = event.get("learning_confidence", {})
    positive = confidence.get("positive_factors", [])
    negative = confidence.get("negative_factors", [])
    lines = [
        "TailTrail Learning Signal",
        f"Event: `{event.get('id')}`",
        f"Score: {confidence.get('score')} / 100",
        f"Status: {confidence.get('status')}",
        f"Promotion: {confidence.get('promotion_decision')}",
        f"Threshold: {confidence.get('threshold')}",
    ]
    if positive:
        lines.append("Why:")
        lines.extend(f"- {item}" for item in positive[:6])
    if negative:
        lines.append("Missing or Risk:")
        lines.extend(f"- {item}" for item in negative[:6])
    if event.get("approved_changes"):
        lines.append("Approved changes:")
        lines.extend(f"- {item}" for item in event.get("approved_changes", [])[:5])
    if event.get("requested_changes"):
        lines.append("Requested changes:")
        lines.extend(f"- {item}" for item in event.get("requested_changes", [])[:5])
    if event.get("clarifications"):
        lines.append("Clarifications:")
        lines.extend(f"- {item}" for item in event.get("clarifications", [])[:5])
    if confidence.get("promotion_decision") == "not-promoted":
        lines.append("Learning action: not added to curated learnings.")
    elif confidence.get("promotion_decision") == "candidate-only":
        lines.append("Learning action: captured as candidate event only.")
    else:
        lines.append("Learning action: eligible for curated promotion.")
    return "\n".join(lines)


def render_index(events: list[dict[str, Any]]) -> str:
    lines = [
        "# TailTrail Learning Index",
        "",
        "This index is the token-safe entry point. Load this before raw learning history.",
        "",
        "| Event | Score | Band | Type | Tags | Files | Candidate |",
        "|---|---:|---|---|---|---|---|",
    ]
    for event in sorted(events, key=lambda item: str(item.get("timestamp", "")), reverse=True):
        confidence = event.get("learning_confidence", {})
        if event.get("sensitivity") != "normal":
            continue
        if confidence.get("band") in {"do-not-use", "weak-note"}:
            continue
        candidate = str(event.get("learning_candidate", ""))
        if not candidate:
            continue
        tags = ", ".join(event.get("tags", []))
        files = ", ".join(event.get("files", [])[:3])
        lines.append(
            f"| `{event.get('id')}` | {confidence.get('score', 0)} | {confidence.get('band', 'unknown')} | "
            f"{event.get('task_type', 'unknown')} | {tags} | {files} | {candidate} |"
        )
    lines.append("")
    return "\n".join(lines)


def rebuild_index(root: Path) -> Path:
    ensure_files(root)
    events = read_events(root)
    path = root / INDEX
    path.write_text(render_index(events), encoding="utf-8")
    return path


def append_curated_learning(root: Path, event: dict[str, Any], score: Score) -> Path:
    ensure_files(root)
    path = root / LEARNINGS
    candidate = str(event.get("learning_candidate", "")).strip()
    if not candidate:
        raise SystemExit("Cannot promote event without a learning candidate.")
    entry = [
        "",
        f"## Learning: {event.get('task_type', 'general')} / {event.get('id')}",
        "",
        f"- Tags: {', '.join(event.get('tags', [])) or 'none'}",
        f"- Score: {score.score} / 100 ({score.band})",
        f"- Files: {', '.join(event.get('files', [])) or 'not specified'}",
        f"- Pattern: {candidate}",
        f"- Evidence: {', '.join(score.positive_factors[:5]) or 'not specified'}",
        f"- Stale when: {event.get('stale_when') or 'related code, validation commands, policy, or ownership changes'}",
    ]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(entry) + "\n")
    return path


def match_event(event: dict[str, Any], tags: set[str], files: set[str], task_type: str | None, refresh_actions: dict[str, str] | None = None) -> bool:
    if refresh_actions and refresh_actions.get(str(event.get("id"))) in {"mark-stale", "suppress", "archive", "delete"}:
        return False
    if event.get("sensitivity") != "normal":
        return False
    confidence = event.get("learning_confidence", {})
    if confidence.get("band") not in {"candidate", "trusted"}:
        return False
    if not event.get("learning_candidate"):
        return False
    event_tags = set(event.get("tags", []))
    event_files = set(event.get("files", []))
    if task_type and event.get("task_type") != task_type:
        return False
    if tags and not tags.intersection(event_tags):
        return False
    if files and not any(file in event_files or any(file in existing or existing in file for existing in event_files) for file in files):
        return False
    return bool(tags or files or task_type)


def search_events(root: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    events = read_events(root)
    refresh_actions = read_refresh_actions(root)
    tags = set(split_csv(args.tags))
    files = {Path(item).as_posix() for item in args.file}
    matches = [event for event in events if match_event(event, tags, files, args.type, refresh_actions)]
    matches.sort(key=lambda event: int(event.get("learning_confidence", {}).get("score", 0)), reverse=True)
    return matches[: args.limit]


def render_search(matches: list[dict[str, Any]]) -> str:
    if not matches:
        return "No matching reusable TailTrail learnings found.\n"
    lines = ["# TailTrail Learning Matches", ""]
    for event in matches:
        confidence = event.get("learning_confidence", {})
        lines.extend(
            [
                f"## {event.get('id')}",
                "",
                f"- Score: {confidence.get('score')} / 100 ({confidence.get('band')})",
                f"- Type: {event.get('task_type')}",
                f"- Tags: {', '.join(event.get('tags', [])) or 'none'}",
                f"- Files: {', '.join(event.get('files', [])) or 'not specified'}",
                f"- Learning: {event.get('learning_candidate')}",
                f"- Use with caution: current source, policy, scanner, and validation evidence wins over this learning.",
                "",
            ]
        )
    return "\n".join(lines)


def render_summary(events: list[dict[str, Any]], month: str | None) -> str:
    if month:
        events = [event for event in events if str(event.get("timestamp", "")).startswith(month)]
    by_type: dict[str, int] = {}
    by_band: dict[str, int] = {}
    for event in events:
        by_type[str(event.get("task_type", "unknown"))] = by_type.get(str(event.get("task_type", "unknown")), 0) + 1
        band = str(event.get("learning_confidence", {}).get("band", "unknown"))
        by_band[band] = by_band.get(band, 0) + 1
    lines = ["# TailTrail Learning Summary", "", f"- Events: `{len(events)}`"]
    if month:
        lines.append(f"- Month: `{month}`")
    lines.extend(["", "## By Type", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(by_type.items()))
    lines.extend(["", "## By Confidence Band", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(by_band.items()))
    return "\n".join(lines) + "\n"


def output(value: Any, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(value, indent=2, sort_keys=True))
    else:
        print(value if isinstance(value, str) else json.dumps(value, indent=2, sort_keys=True))


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target project root.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TailTrail Learning Agent V2.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create learning files.")
    add_common(init)

    capture = subparsers.add_parser("capture", help="Capture a compact scored learning event.")
    add_common(capture)
    capture.add_argument("--repo")
    capture.add_argument("--type", default="general")
    capture.add_argument("--summary", required=True)
    capture.add_argument("--prompt-summary")
    capture.add_argument("--solution")
    capture.add_argument("--candidate")
    capture.add_argument("--tags")
    capture.add_argument("--file", action="append", default=[])
    capture.add_argument("--issue-ids")
    capture.add_argument("--validation-command", action="append", default=[])
    capture.add_argument("--validation-outcome", choices=("pass", "fail", "partial", "skipped", "not-run", "unknown"), default="unknown")
    capture.add_argument("--acceptance", choices=("accepted", "rejected", "revised", "partially-accepted", "unknown"), default="unknown")
    capture.add_argument("--reason")
    capture.add_argument("--approved-change", action="append", default=[])
    capture.add_argument("--requested-change", action="append", default=[])
    capture.add_argument("--clarification", action="append", default=[])
    capture.add_argument("--fulfillment-status", choices=("appears-aligned", "partially-aligned", "needs-clarification", "not-evaluated"), default="not-evaluated")
    capture.add_argument("--risk", default="normal")
    capture.add_argument("--sensitivity", choices=("normal", "internal", "sensitive"), default="normal")
    capture.add_argument("--review-status", choices=("approved", "changes-requested", "none"), default="none")
    capture.add_argument("--user-override", choices=("none", "proceed-anyway", "record-low-confidence-event"), default="none")
    capture.add_argument("--reused-project-pattern", action="store_true")
    capture.add_argument("--small-focused-change", action="store_true")
    capture.add_argument("--no-new-dependency", action="store_true")
    capture.add_argument("--dependency-gate-applied", action="store_true")
    capture.add_argument("--scanner-resolved", action="store_true")
    capture.add_argument("--guardrail-weakened", action="store_true")
    capture.add_argument("--stale-when")
    capture.add_argument("--promote-if-eligible", action="store_true")

    score = subparsers.add_parser("score", help="Score an existing event.")
    add_common(score)
    score.add_argument("--event-id", required=True)

    search = subparsers.add_parser("search", help="Search reusable learning candidates.")
    add_common(search)
    search.add_argument("--tags")
    search.add_argument("--file", action="append", default=[])
    search.add_argument("--type")
    search.add_argument("--limit", type=int, default=3)

    promote = subparsers.add_parser("promote", help="Promote an eligible event into curated learnings.")
    add_common(promote)
    promote.add_argument("--event-id", required=True)
    promote.add_argument("--min-score", type=int)
    promote.add_argument("--force", action="store_true")
    promote.add_argument("--dry-run", action="store_true")

    summarize = subparsers.add_parser("summarize", help="Summarize learning events.")
    add_common(summarize)
    summarize.add_argument("--month")

    prune = subparsers.add_parser("prune", help="Show low-confidence or stale candidates; does not delete events.")
    add_common(prune)
    prune.add_argument("--max-score", type=int, default=39)

    rebuild = subparsers.add_parser("rebuild-index", help="Rebuild the token-safe learning index.")
    add_common(rebuild)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    ensure_files(root)

    if args.command == "init":
        rebuild_index(root)
        output(f"TailTrail Learning Agent V2 ready: {root / TAILTRAIL_DIR}", args.format)
        return 0

    if args.command == "capture":
        event = event_from_args(args, root)
        append_jsonl(root / EVENTS, event)
        append_jsonl(root / SCORES, {"event_id": event["id"], "timestamp": now(), **event["learning_confidence"]})
        rebuild_index(root)
        promoted = None
        if args.promote_if_eligible and event["learning_confidence"]["promotion_decision"] == "eligible":
            promoted = append_curated_learning(root, event, score_event(event)).as_posix()
        if args.format == "json":
            event = {**event, "promoted_to": promoted}
            output(event, args.format)
        else:
            message = render_learning_signal(event)
            if promoted:
                message += f"\nPromoted to: `{promoted}`"
            output(message, args.format)
        return 0

    if args.command == "score":
        event = find_event(root, args.event_id)
        score = score_event(event)
        output(score.__dict__ if args.format == "json" else render_learning_signal({**event, "learning_confidence": score.__dict__}), args.format)
        return 0

    if args.command == "search":
        matches = search_events(root, args)
        output(matches if args.format == "json" else render_search(matches), args.format)
        return 0

    if args.command == "promote":
        event = find_event(root, args.event_id)
        score = score_event(event)
        min_score = args.min_score if args.min_score is not None else max(80, score.threshold)
        if not args.force and (score.score < min_score or score.promotion_decision != "eligible"):
            raise SystemExit(
                f"Not promoted. Score {score.score} is below required {min_score} or decision is {score.promotion_decision}."
            )
        if args.dry_run:
            output(f"Promotion dry run passed for {args.event_id}.", args.format)
            return 0
        path = append_curated_learning(root, event, score)
        rebuild_index(root)
        output(f"Promoted learning into {path}", args.format)
        return 0

    if args.command == "summarize":
        output(render_summary(read_events(root), args.month), args.format)
        return 0

    if args.command == "prune":
        candidates = [
            event
            for event in read_events(root)
            if int(event.get("learning_confidence", {}).get("score", 0)) <= args.max_score
        ]
        output(candidates if args.format == "json" else render_search(candidates), args.format)
        return 0

    if args.command == "rebuild-index":
        path = rebuild_index(root)
        output(f"Rebuilt learning index: {path}", args.format)
        return 0

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
