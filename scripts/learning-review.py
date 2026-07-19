#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TAILTRAIL_DIR = Path(".tailtrail")
EVENTS = TAILTRAIL_DIR / "learning-events.jsonl"
INDEX = TAILTRAIL_DIR / "learning-index.md"
LEARNINGS = TAILTRAIL_DIR / "learnings.md"
REFRESH_ACTIONS = TAILTRAIL_DIR / "learning-refresh-actions.json"
REVIEW_REPORT = TAILTRAIL_DIR / "learning-governance-review.md"

BLOCKING_ACTIONS = {"mark-stale", "suppress", "archive", "delete"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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
            raise SystemExit(f"Invalid learning JSON on line {line_number}: {error}") from error
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


def score(event: dict[str, Any]) -> int:
    confidence = event.get("learning_confidence", {})
    value = confidence.get("score", 0) if isinstance(confidence, dict) else 0
    return value if isinstance(value, int) else 0


def band(event: dict[str, Any]) -> str:
    confidence = event.get("learning_confidence", {})
    return str(confidence.get("band", "unknown")) if isinstance(confidence, dict) else "unknown"


def validation_missing(event: dict[str, Any]) -> bool:
    return str(event.get("validation_outcome", "unknown")) in {"unknown", "skipped", "not-run", ""}


def action_items(root: Path) -> list[dict[str, Any]]:
    data = read_json(root / REFRESH_ACTIONS)
    if not data:
        return []
    actions = data.get("actions", [])
    return [item for item in actions if isinstance(item, dict)] if isinstance(actions, list) else []


def duplicate_candidates(events: list[dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for event in events:
        candidate = " ".join(str(event.get("learning_candidate", "")).strip().lower().split())
        if not candidate:
            continue
        tags = ",".join(sorted(str(tag) for tag in event.get("tags", [])))
        grouped[f"{candidate}|{tags}"].append(str(event.get("id", "")))
    return {key: ids for key, ids in grouped.items() if len([item for item in ids if item]) > 1}


def normalized_candidate(event: dict[str, Any]) -> str:
    return " ".join(str(event.get("learning_candidate", "")).strip().lower().split())


def action_targets(action: dict[str, Any]) -> set[str]:
    targets: set[str] = set()
    for key in ("event_id", "learning_id", "id"):
        value = action.get(key)
        if value:
            targets.add(str(value))
    for key in ("candidate", "learning_candidate", "pattern"):
        value = action.get(key)
        if value:
            targets.add(" ".join(str(value).strip().lower().split()))
    return targets


def conflicting_candidates(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        candidate = normalized_candidate(event)
        if candidate:
            grouped[candidate].append(event)
    conflicts: list[dict[str, Any]] = []
    for candidate, values in grouped.items():
        acceptances = {str(item.get("acceptance", "unknown")) for item in values}
        bands = {band(item) for item in values}
        validations = {str(item.get("validation_outcome", "unknown")) for item in values}
        overrides = {str(item.get("user_override", "")) for item in values if item.get("user_override")}
        if "accepted" in acceptances and "rejected" in acceptances:
            conflicts.append({"candidate": candidate, "reason": "accepted and rejected history both exist", "event_ids": [str(item.get("id", "")) for item in values], "conflict_type": "acceptance"})
        if "trusted" in bands and ("do-not-use" in bands or "weak-note" in bands):
            conflicts.append({"candidate": candidate, "reason": "trusted and weak/do-not-use confidence bands both exist", "event_ids": [str(item.get("id", "")) for item in values], "conflict_type": "confidence"})
        if "pass" in validations and validations.intersection({"fail", "failed", "not-run", "skipped", "unknown"}):
            conflicts.append({"candidate": candidate, "reason": "validated pass history conflicts with failed/missing validation history", "event_ids": [str(item.get("id", "")) for item in values], "conflict_type": "validation"})
        if overrides.intersection({"proceed-anyway", "record-low-confidence-event"}) and "trusted" in bands:
            conflicts.append({"candidate": candidate, "reason": "trusted learning also has low-confidence override history", "event_ids": [str(item.get("id", "")) for item in values], "conflict_type": "override"})
    return conflicts


def stale_pattern_conflicts(events: list[dict[str, Any]], actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocking = [action for action in actions if action.get("action") in BLOCKING_ACTIONS]
    if not blocking:
        return []
    conflicts: list[dict[str, Any]] = []
    for event in events:
        event_id = str(event.get("id", ""))
        candidate = normalized_candidate(event)
        if not event_id and not candidate:
            continue
        if band(event) not in {"trusted", "suggest-with-caution"} and event.get("acceptance") != "accepted":
            continue
        for action in blocking:
            targets = action_targets(action)
            if (event_id and event_id in targets) or (candidate and candidate in targets):
                conflicts.append(
                    {
                        "candidate": candidate or event_id,
                        "reason": f"learning still appears reusable but has `{action.get('action')}` refresh history",
                        "event_ids": [event_id] if event_id else [],
                        "conflict_type": "stale-pattern",
                        "refresh_action": action.get("action"),
                    }
                )
                break
    return conflicts


def build_report(root: Path, weak_threshold: int, rejected_threshold: int, missing_validation_threshold: int) -> dict[str, Any]:
    events = read_jsonl(root / EVENTS)
    actions = action_items(root)
    bands = Counter(band(event) for event in events)
    acceptances = Counter(str(event.get("acceptance", "unknown")) for event in events)
    validations = Counter(str(event.get("validation_outcome", "unknown")) for event in events)
    refresh_counts = Counter(str(action.get("action", "unknown")) for action in actions)
    duplicates = duplicate_candidates(events)
    conflicts = [*conflicting_candidates(events), *stale_pattern_conflicts(events, actions)]

    weak_events = [event for event in events if band(event) in {"weak-note", "do-not-use"}]
    rejected_events = [event for event in events if event.get("acceptance") == "rejected"]
    missing_validation = [event for event in events if validation_missing(event)]
    guardrail_risk = [event for event in events if event.get("guardrail_weakened")]
    override_risk = [event for event in events if event.get("user_override") in {"proceed-anyway", "record-low-confidence-event"}]
    blocking_actions = [action for action in actions if action.get("action") in BLOCKING_ACTIONS]

    recommendations: list[dict[str, Any]] = []
    if len(weak_events) >= weak_threshold:
        recommendations.append(
            {
                "area": "weak-confidence-noise",
                "severity": "medium",
                "finding": f"{len(weak_events)} weak or do-not-use learning events exist.",
                "next_step": "Run `python3 scripts/tailtrail.py learn refresh stale --root .` and suppress or demote noisy events with explicit approval.",
            }
        )
    if len(rejected_events) >= rejected_threshold:
        recommendations.append(
            {
                "area": "rejected-patterns",
                "severity": "medium",
                "finding": f"{len(rejected_events)} rejected learning events exist.",
                "next_step": "Keep rejected events out of retrieval; capture them only as avoid-history when the reason is clear.",
            }
        )
    if len(missing_validation) >= missing_validation_threshold:
        recommendations.append(
            {
                "area": "missing-validation",
                "severity": "high",
                "finding": f"{len(missing_validation)} learning events have missing, skipped, or unknown validation.",
                "next_step": "Do not promote these until validation evidence is added or the events are marked weak historical notes.",
            }
        )
    if conflicts:
        recommendations.append(
            {
                "area": "conflicting-learnings",
                "severity": "high",
                "finding": f"{len(conflicts)} candidate learning conflicts detected.",
                "next_step": "Review conflicts and record an approved refresh action for stale or rejected candidates.",
            }
        )
    if guardrail_risk:
        recommendations.append(
            {
                "area": "guardrail-risk",
                "severity": "high",
                "finding": f"{len(guardrail_risk)} events indicate guardrails were weakened.",
                "next_step": "Suppress these unless an owner explicitly documents why the guardrail change was correct.",
            }
        )
    if override_risk:
        recommendations.append(
            {
                "area": "user-override-risk",
                "severity": "medium",
                "finding": f"{len(override_risk)} events used low-confidence or proceed-anyway overrides.",
                "next_step": "Keep overrides as execution history only; do not promote without stronger evidence.",
            }
        )
    if blocking_actions:
        recommendations.append(
            {
                "area": "blocking-refresh-actions",
                "severity": "low",
                "finding": f"{len(blocking_actions)} blocking refresh actions are recorded.",
                "next_step": "Verify suppressed, stale, archived, or deleted learnings are not resurfacing in Navigator.",
            }
        )
    if not recommendations:
        recommendations.append(
            {
                "area": "learning-hygiene",
                "severity": "low",
                "finding": "No major learning hygiene risks were detected for the selected thresholds.",
                "next_step": "Keep learnings advisory and rerun this review monthly or before broad reuse.",
            }
        )

    return {
        "schema_version": "1",
        "created_at": now(),
        "root": root.as_posix(),
        "artifacts": {
            "events": (root / EVENTS).as_posix(),
            "index": (root / INDEX).as_posix(),
            "curated_learnings": (root / LEARNINGS).as_posix(),
            "refresh_actions": (root / REFRESH_ACTIONS).as_posix(),
        },
        "summary": {
            "events": len(events),
            "curated_index_exists": (root / INDEX).is_file(),
            "curated_learnings_exists": (root / LEARNINGS).is_file(),
            "refresh_actions": len(actions),
            "weak_or_do_not_use_events": len(weak_events),
            "rejected_events": len(rejected_events),
            "missing_validation_events": len(missing_validation),
            "guardrail_risk_events": len(guardrail_risk),
            "override_risk_events": len(override_risk),
            "duplicate_candidate_groups": len(duplicates),
            "conflicting_candidate_groups": len(conflicts),
        },
        "confidence_bands": dict(bands.most_common()),
        "acceptance": dict(acceptances.most_common()),
        "validation": dict(validations.most_common()),
        "refresh_action_counts": dict(refresh_counts.most_common()),
        "duplicates": duplicates,
        "conflicts": conflicts,
        "recommendations": recommendations,
        "decision_boundary": "Learning review is advisory. Do not edit, suppress, promote, or delete learnings without explicit approval.",
        "privacy_note": "This report reads compact local learning metadata. It does not need raw prompts, raw logs, secrets, PII, PHI, customer data, or source snippets.",
    }


def render_counter(title: str, values: dict[str, int]) -> list[str]:
    lines = [f"## {title}", ""]
    if values:
        lines.extend(f"- {key}: `{value}`" for key, value in values.items())
    else:
        lines.append("- none")
    lines.append("")
    return lines


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Learning Governance Review",
        "",
        "This report reviews whether local learnings are safe to reuse. It is advisory and approval-first.",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key.replace('_', ' ').title()}: `{value}`")
    lines.append("")
    lines.extend(render_counter("Confidence Bands", report["confidence_bands"]))
    lines.extend(render_counter("Acceptance", report["acceptance"]))
    lines.extend(render_counter("Validation", report["validation"]))
    lines.extend(render_counter("Refresh Actions", report["refresh_action_counts"]))
    lines.extend(["## Recommended Improvements", ""])
    for item in report["recommendations"]:
        lines.extend(
            [
                f"### {item['area']}",
                "",
                f"- Severity: `{item['severity']}`",
                f"- Finding: {item['finding']}",
                f"- Recommended next step: {item['next_step']}",
                "",
            ]
        )
    if report["conflicts"]:
        lines.extend(["## Conflicts", ""])
        for conflict in report["conflicts"][:10]:
            lines.extend(
                [
                    f"- Candidate: `{conflict['candidate']}`",
                    f"  Reason: {conflict['reason']}",
                    f"  Events: {', '.join(conflict['event_ids'])}",
                ]
            )
        lines.append("")
    lines.extend(
        [
            "## Decision Boundary",
            "",
            f"- {report['decision_boundary']}",
            f"- {report['privacy_note']}",
            "- Current source, tests, CI, scanner evidence, local policy, and guardrails override old learnings.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(root: Path, report: dict[str, Any], fmt: str) -> Path:
    path = root / REVIEW_REPORT
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(report, indent=2, sort_keys=True) if fmt == "json" else render_markdown(report)
    path.write_text(body + "\n", encoding="utf-8")
    return path


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review TailTrail learning governance and hygiene.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--weak-threshold", type=int, default=3)
    parser.add_argument("--rejected-threshold", type=int, default=2)
    parser.add_argument("--missing-validation-threshold", type=int, default=2)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--write-result", action="store_true")
    return parser


def main() -> int:
    args = parser().parse_args()
    root = args.root.resolve()
    report = build_report(root, args.weak_threshold, args.rejected_threshold, args.missing_validation_threshold)
    if args.write_result:
        write_report(root, report, args.format)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
