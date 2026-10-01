#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TAILTRAIL_DIR = Path(".tailtrail")
ROOT = Path(__file__).resolve().parents[1]
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
    spec = importlib.util.spec_from_file_location("tailtrail_refresh_learning_v3", ROOT / "scripts" / "learning-v3.py")
    if spec is None or spec.loader is None:
        raise SystemExit("Unable to load Learning V3 compatibility reader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    try:
        return module.compatible_events(root)
    except module.LearningV3Error as error:
        raise SystemExit(str(error)) from error


def deterministic_stale_reasons(root: Path, event: dict[str, Any]) -> list[str]:
    spec = importlib.util.spec_from_file_location("tailtrail_refresh_v3_state", ROOT / "scripts" / "learning-v3.py")
    if spec is None or spec.loader is None:
        return ["Learning V3 invalidator state is unavailable"]
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    try:
        latest = module.latest_records(module.read_records(root))
    except module.LearningV3Error as error:
        return [f"Learning V3 invalidator state is invalid: {error}"]
    record = latest.get(str(event.get("learning_v3_id") or event.get("id")))
    if not record or record["freshness"]["status"] != "current":
        return []
    saved = record["freshness"].get("invalidator_snapshot")
    if not isinstance(saved, dict):
        return []
    current = module.invalidator_snapshot(root, path_patterns=record["applicability"]["path_patterns"], source_ref=record["provenance"]["source_ref"])
    return [f"{name} content fingerprint changed" for name in record["freshness"]["invalidators"] if saved.get(name) != current.get(name)]


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

    deterministic_reasons = deterministic_stale_reasons(root, event)
    if deterministic_reasons:
        action = "mark-stale"
        reasons.extend(deterministic_reasons)

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


def load_sweep_v3():
    spec = importlib.util.spec_from_file_location("tailtrail_refresh_sweep_v3", ROOT / "scripts" / "learning-v3.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load Learning V3 for sweep")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sweep_v3(root: Path) -> dict[str, Any]:
    """Proactively evaluate every current V3 record against saved fingerprints.

    Read-only: uses the same shared comparison as retrieval gating, so a
    sweep verdict and a later retrieval verdict cannot disagree. Mutations
    stay on the existing approved `apply` path and `revalidate` backfill.
    """
    V3 = load_sweep_v3()
    root = root.resolve()
    if not (root / ".tailtrail" / "learning-v3" / "events.jsonl").is_file():
        return {"schema_version": "1", "type": "tailtrail-learning-refresh-sweep",
                "state": "no-store", "triggered": [], "needs_backfill": [], "clean": 0,
                "boundary": "No V3 store exists yet; learnings accrue from accepted closures."}
    try:
        latest = V3.latest_records(V3.read_records(root))
    except (OSError, ValueError):
        return {"schema_version": "1", "type": "tailtrail-learning-refresh-sweep",
                "state": "no-store", "triggered": [], "needs_backfill": [], "clean": 0,
                "boundary": "No V3 store is readable; nothing was evaluated."}
    triggered: list[dict[str, Any]] = []
    needs_backfill: list[str] = []
    actioned: list[dict[str, Any]] = []
    clean = 0
    usefulness = _usefulness_scores(root)
    blocking = {
        str(item.get("learning_id")): str(item.get("action"))
        for item in load_actions(root).get("actions", [])
        if isinstance(item, dict) and item.get("action") in BLOCKING_ACTIONS
    }
    for learning_id in sorted(latest):
        record = latest[learning_id]
        if record.get("freshness", {}).get("status") != "current":
            continue
        if not isinstance(record.get("freshness", {}).get("invalidator_snapshot"), dict):
            needs_backfill.append(learning_id)
            continue
        reasons, _ = V3.compare_snapshot(root, record)
        deadline = parse_time(record.get("freshness", {}).get("revalidate_after"))
        if deadline and deadline <= datetime.now(timezone.utc):
            reasons = [*reasons, "revalidation deadline has elapsed"]
        if reasons:
            row = {
                "learning_id": learning_id,
                "reasons": sorted(set(reasons)),
            }
            if learning_id in blocking:
                row["action"] = blocking[learning_id]
                row["apply_command"] = (
                    f"tailtrail learn refresh apply --root . --learning-id {learning_id} "
                    f"--action mark-stale --reason \"sweep-detected drift\" --approved"
                )
                actioned.append(row)
                continue
            row["apply_command"] = (
                f"tailtrail learn refresh apply --root . --learning-id {learning_id} "
                f"--action mark-stale --reason \"sweep-detected drift\" --approved"
            )
            triggered.append(row)
        else:
            clean += 1
    for row in triggered:
        score = usefulness.get(row["learning_id"], {})
        row["usefulness"] = {"score": score.get("score"), "band": score.get("band")}
    for row in actioned:
        score = usefulness.get(row["learning_id"], {})
        row["usefulness"] = {"score": score.get("score"), "band": score.get("band")}
    triggered.sort(key=lambda row: (
        row.get("usefulness", {}).get("score") if isinstance(row.get("usefulness", {}).get("score"), int) else 999,
        row["learning_id"],
    ))
    actioned.sort(key=lambda row: row["learning_id"])

    return {"schema_version": "1", "type": "tailtrail-learning-refresh-sweep",
            "state": "evaluated", "triggered": triggered, "actioned": actioned,
            "needs_backfill": sorted(needs_backfill), "clean": clean,
            "usefulness": {key: {"score": value.get("score"), "band": value.get("band")} for key, value in usefulness.items()},
            "backfill_command": "tailtrail learn v3 revalidate --root . --learning-id <id> --reason \"snapshot backfill\" --evidence-ref <file> --approved",
            "boundary": "Read-only evaluation; triggering actions and backfills each require their own explicit approval. Records with an approved blocking refresh action are reported under `actioned`, not `triggered`; retrieval already blocks them."}


def _usefulness_scores(root: Path) -> dict[str, dict[str, Any]]:
    """Load usefulness scores lazily; failures yield an empty map, never a break.

    Scores inform review ordering only — a missing score must not block
    sweep evaluation, which stands on fingerprint comparison alone.
    """
    try:
        import importlib.util as _ilu
        from pathlib import Path as _Path

        here = _Path(__file__).resolve().parent / "learning-use-receipt.py"
        spec = _ilu.spec_from_file_location("tailtrail_refresh_use_scores", here)
        if spec is None or spec.loader is None:
            return {}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        scores = module.scores_by_id(root)
        return dict(scores) if isinstance(scores, dict) else {}
    except Exception:
        return {}


def revalidate_due(root: Path, approved: bool) -> dict[str, Any]:
    """Revalidate clean records whose deadline elapsed (automatic truth gate).

    Only records with unchanged fingerprints qualify: drifted records need
    a mark-stale decision (host/user), never a silent re-snapshot. Records
    without surviving evidence refs are skipped. Requires approved=True,
    mirroring every other mutating path in this file.
    """
    if approved is not True:
        raise ValueError("truth revalidation requires --approved")
    V3 = load_sweep_v3()
    root = root.resolve()
    revalidated: list[str] = []
    skipped: list[str] = []
    try:
        latest = V3.latest_records(V3.read_records(root))
    except (OSError, ValueError) as error:
        raise ValueError(f"Learning V3 store is unreadable: {error}")
    from datetime import datetime, timezone

    for learning_id in sorted(latest):
        record = latest[learning_id]
        if record.get("freshness", {}).get("status") != "current":
            continue
        if not isinstance(record.get("freshness", {}).get("invalidator_snapshot"), dict):
            continue
        reasons, _ = V3.compare_snapshot(root, record)
        if reasons:
            continue
        deadline = parse_time(record.get("freshness", {}).get("revalidate_after"))
        if deadline is not None and deadline > datetime.now(timezone.utc):
            continue
        refs = sorted({
            str(value) for value in (record.get("provenance", {}) or {}).get("evidence_refs", []) or []
            if isinstance(value, str) and value.strip() and (root / value.strip()).is_file()
        })
        if not refs:
            skipped.append(learning_id)
            continue
        V3.revalidate(root, learning_id, reason="automatic truth revalidation: fingerprints unchanged", evidence_refs=refs)
        revalidated.append(learning_id)
    return {"revalidated": sorted(revalidated), "skipped": sorted(skipped)}


def check_sweep_threshold(
    root: Path, max_stale: int = 10, max_ratio: float = 0.5,
) -> dict[str, Any]:
    """Decide whether staleness warrants a sweep (read-only trigger).

    Counts triggered records via sweep_v3 against the evaluated total and
    fires when either the absolute count or the stale ratio crosses its
    line. Returns the verdict plus the exact sweep command to run — the
    nudge, not the sweep. Never mutates.
    """
    result = sweep_v3(root)
    if result.get("state") != "evaluated":
        return {"triggered": False, "reason": f"sweep state is {result.get('state')}",
                "stale": 0, "evaluated": 0, "ratio": 0.0}
    stale = len(result.get("triggered", []) or [])
    clean = int(result.get("clean", 0) or 0)
    total = stale + clean
    ratio = (stale / total) if total else 0.0
    fired = bool((max_stale > 0 and stale >= max_stale) or (total > 0 and ratio >= max_ratio))
    return {
        "triggered": fired,
        "stale": stale,
        "evaluated": total,
        "ratio": round(ratio, 3),
        "max_stale": max_stale,
        "max_ratio": max_ratio,
        "suggestion": "tailtrail learn refresh sweep --root .  # then apply per item with --approved" if fired else None,
    }


def command_sweep(args: argparse.Namespace) -> int:
    result = sweep_v3(args.root)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    print("# TailTrail Learning Refresh Sweep")
    print(f"- State: `{result['state']}`")
    print(f"- Clean: `{result['clean']}`")
    if result["triggered"]:
        print("", "## Triggered", "", sep="\n")
        for row in result["triggered"]:
            print(f"- `{row['learning_id']}`: {'; '.join(row['reasons'])}")
            print(f"  - `{row['apply_command']}`")
    if result["needs_backfill"]:
        print("", "## Needs snapshot backfill", "", sep="\n")
        for learning_id in result["needs_backfill"]:
            print(f"- `{learning_id}`")
        print(f"- `{result['backfill_command']}`")
    if not result["triggered"] and not result["needs_backfill"]:
        print("- No stale learnings detected.")
    return 0


MERGE_QUEUE = Path(".tailtrail") / "learning-merge-queue.jsonl"


def _advice_key(advice: str, tags: list[str]) -> str:
    normalized = re.sub(r"\s+", " ", str(advice or "").strip().lower())
    return normalized + "|" + ",".join(sorted(str(tag) for tag in tags or []))


def _advice_tokens(advice: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", str(advice or "").lower()))


def exact_duplicate_v3_groups(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Group current V3 records by identical normalized advice plus tags.

    Only `current` records participate; terminal ones are already resolved.
    Returns {group_key: [learning_ids]} for groups larger than one.
    """
    groups: dict[str, list[str]] = {}
    for record in records:
        if not isinstance(record, dict) or str(record.get("freshness", {}).get("status", "")) != "current":
            continue
        content = record.get("content", {}) if isinstance(record.get("content"), dict) else {}
        applicability = record.get("applicability", {}) if isinstance(record.get("applicability"), dict) else {}
        key = _advice_key(str(content.get("advice", "")), list(applicability.get("tags", []) or []))
        if key.split("|", 1)[0]:
            groups.setdefault(key, []).append(str(record.get("learning_id", "")))
    return {key: sorted(ids) for key, ids in groups.items() if len([item for item in ids if item]) > 1}


def near_duplicate_proposals(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Propose merges for related-but-not-identical current records.

    Detection is deterministic (Jaccard token overlap >= 0.5 plus a shared
    tag); the decision stays human. Proposals only — nothing here mutates
    the store. Exact-duplicate pairs are excluded (they belong to automatic
    collapse, not judgment).
    """
    current = [
        row for row in records
        if isinstance(row, dict) and str(row.get("freshness", {}).get("status", "")) == "current"
    ]
    exact_keys = {
        _advice_key(
            str((row.get("content", {}) or {}).get("advice", "")),
            list((row.get("applicability", {}) or {}).get("tags", []) or []),
        )
        for row in current
    }
    proposals: list[dict[str, Any]] = []
    for index, left in enumerate(current):
        left_content = left.get("content", {}) if isinstance(left.get("content"), dict) else {}
        left_app = left.get("applicability", {}) if isinstance(left.get("applicability"), dict) else {}
        left_tokens = _advice_tokens(str(left_content.get("advice", "")))
        left_tags = {str(tag) for tag in left_app.get("tags", []) or []}
        if not left_tokens:
            continue
        for right in current[index + 1:]:
            right_content = right.get("content", {}) if isinstance(right.get("content"), dict) else {}
            right_app = right.get("applicability", {}) if isinstance(right.get("applicability"), dict) else {}
            right_tokens = _advice_tokens(str(right_content.get("advice", "")))
            right_tags = {str(tag) for tag in right_app.get("tags", []) or []}
            if not right_tokens or not (left_tags & right_tags):
                continue
            union = left_tokens | right_tokens
            similarity = len(left_tokens & right_tokens) / len(union) if union else 0.0
            pair_key = _advice_key(str(right_content.get("advice", "")), list(right_tags))
            if pair_key in exact_keys and _advice_key(str(left_content.get("advice", "")), list(left_tags)) == pair_key:
                continue
            if similarity >= 0.5:
                first, second = sorted([str(left.get("learning_id", "")), str(right.get("learning_id", ""))])
                proposals.append({
                    "canonical_learning_id": first,
                    "merged_learning_ids": [second],
                    "similarity": round(similarity, 3),
                    "shared_tags": sorted(left_tags & right_tags),
                    "status": "proposed",
                    "boundary": "Host or user approval required; detection never merges.",
                })
    return proposals


def execute_merge_group(
    root: Path,
    canonical_id: str,
    merged_ids: list[str],
    reason: str,
    approved: bool,
) -> dict[str, Any]:
    """Supersede duplicate learnings into one canonical record.

    Mirrors the `apply` convention: `approved` must be True or nothing
    happens. Each merged record gets a V3 `supersede` transition pointing at
    the canonical record, which must itself be current. Failures raise —
    partial merges would leave the group half-resolved.
    """
    if approved is not True:
        raise ValueError("duplicate merge execution requires --approved")
    if not str(reason or "").strip():
        raise ValueError("duplicate merge execution requires a reason")
    V3 = load_sweep_v3()
    root = root.resolve()
    superseded: list[str] = []
    for learning_id in merged_ids:
        if str(learning_id) == str(canonical_id):
            continue
        V3.terminal_transition(root, str(learning_id), "supersede", str(reason), replacement=str(canonical_id))
        superseded.append(str(learning_id))
    return {
        "canonical_learning_id": str(canonical_id),
        "superseded": sorted(superseded),
        "reason": str(reason),
    }


def command_merge_duplicates(args: argparse.Namespace) -> int:
    V3 = load_sweep_v3()
    root = args.root.resolve()
    if args.approved is not True:
        raise SystemExit("merge-duplicates requires --approved")
    try:
        latest = V3.latest_records(V3.read_records(root))
    except (OSError, ValueError) as error:
        raise SystemExit(f"Learning V3 store is unreadable: {error}")
    groups = exact_duplicate_v3_groups(list(latest.values()))
    if not groups:
        print("No exact-duplicate learning groups found.")
        return 0
    by_sequence = {
        learning_id: int(record.get("sequence", 0) or 0)
        for learning_id, record in latest.items()
    }
    executed: list[dict[str, Any]] = []
    for key in sorted(groups):
        ids = sorted(groups[key], key=lambda item: (by_sequence.get(item, 0), item))
        executed.append(execute_merge_group(
            root, ids[0], ids[1:],
            args.reason or "approved exact-duplicate collapse", True,
        ))
    if args.format == "json":
        print(json.dumps({"merged_groups": executed}, indent=2, sort_keys=True))
    else:
        for row in executed:
            print(f"Merged {', '.join(row['superseded'])} into `{row['canonical_learning_id']}`.")
    return 0




def snapshot_store(root: Path) -> dict[str, Any]:
    """Snapshot the V3 learning store before any destructive step.

    Copies the event journal and project frame into a timestamped snapshot
    directory with per-file fingerprints plus a manifest. Restoring is a
    plain file copy back. No ledger event is emitted: snapshots are rollback
    paths, not decisions — the manifest itself is the audit record.
    """
    from datetime import datetime, timezone

    V3 = load_sweep_v3()
    root = root.resolve()
    store = root / ".tailtrail" / "learning-v3" / "events.jsonl"
    frame = root / ".tailtrail" / "learning-v3" / "project-frame.json"
    if not store.is_file():
        raise ValueError("no Learning V3 store exists to snapshot")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = root / ".tailtrail" / "learning-v3" / "snapshots" / stamp
    destination.mkdir(parents=True, exist_ok=False)
    files: dict[str, str] = {}
    for source in (store, frame):
        if not source.is_file():
            continue
        data = source.read_bytes()
        (destination / source.name).write_bytes(data)
        files[source.name] = "sha256:" + hashlib.sha256(data).hexdigest()
    try:
        count = len(V3.read_records(root))
    except (OSError, ValueError):
        count = 0
    manifest = {
        "schema_version": "1",
        "type": "tailtrail-learning-store-snapshot",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
        "record_count": count,
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"snapshot": destination.relative_to(root).as_posix(), **manifest}


def restore_snapshot(root: Path, stamp: str) -> dict[str, Any]:
    """Restore a snapshot over the live store (rollback path).

    Overwrites the journal and frame with byte-exact copies and verifies
    fingerprints after writing. Destructive by nature: callers must confirm
    separately — this function performs, it never asks.
    """
    root = root.resolve()
    destination = root / ".tailtrail" / "learning-v3" / "snapshots" / str(stamp)
    manifest_path = destination / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"learning snapshot `{stamp}` does not exist")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"learning snapshot `{stamp}` manifest is unreadable: {error}")
    restored: list[str] = []
    for name, digest in (manifest.get("files", {}) or {}).items():
        blob = (destination / str(name)).read_bytes()
        if "sha256:" + hashlib.sha256(blob).hexdigest() != digest:
            raise ValueError(f"learning snapshot `{stamp}` file `{name}` fails integrity check")
        target = root / ".tailtrail" / "learning-v3" / str(name)
        target.write_bytes(blob)
        restored.append(str(name))
    return {"snapshot": destination.relative_to(root).as_posix(), "restored": sorted(restored)}


def _read_queue(root: Path) -> list[dict[str, Any]]:
    path = root / MERGE_QUEUE
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except (ValueError, json.JSONDecodeError):
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def queue_merge_proposals(root: Path, proposals: list[dict[str, Any]]) -> dict[str, Any]:
    """Persist near-duplicate merge proposals; decided pairs never requeue.

    Each proposal needs canonical_learning_id + merged_learning_ids. Pairs
    already approved/rejected/executed are skipped (decision history, not
    content, dedupes). Returns queued/skipped counts. Proposals decide
    nothing — execution requires a separate approved decision.
    """
    root = root.resolve()
    decided = set()
    for row in _read_queue(root):
        if row.get("status") in {"approved", "rejected", "executed"}:
            canonical = str(row.get("canonical_learning_id", ""))
            for merged in row.get("merged_learning_ids", []) or []:
                decided.add((canonical, str(merged)))
    queued = 0
    skipped = 0
    path = root / MERGE_QUEUE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for item in proposals or []:
            if not isinstance(item, dict):
                skipped += 1
                continue
            canonical = str(item.get("canonical_learning_id", ""))
            merged = sorted({str(value) for value in item.get("merged_learning_ids", []) or [] if str(value).strip()})
            if not canonical or not merged or canonical in merged:
                skipped += 1
                continue
            if all((canonical, value) in decided for value in merged):
                skipped += 1
                continue
            handle.write(json.dumps({
                "schema_version": "1",
                "type": "tailtrail-learning-merge-proposal",
                "canonical_learning_id": canonical,
                "merged_learning_ids": merged,
                "similarity": item.get("similarity"),
                "shared_tags": list(item.get("shared_tags", []) or []),
                "status": "proposed",
            }, sort_keys=True) + "\n")
            queued += 1
    return {"queued": queued, "skipped": skipped}


def decide_merge_proposal(
    root: Path, canonical_id: str, decision: str, reason: str, approved: bool,
) -> dict[str, Any]:
    """Approve (and execute) or reject a pending merge proposal.

    Approval executes the supersede transitions immediately through
    execute_merge_group, so approved means merged, never pending-forever.
    Rejection records why, which permanently retires the pair from future
    queues. Both paths require approved=True and a reason.
    """
    if approved is not True:
        raise ValueError("merge proposal decisions require --approved")
    if decision not in {"approved", "rejected"}:
        raise ValueError("merge proposal decision must be approved or rejected")
    if not str(reason or "").strip():
        raise ValueError("merge proposal decisions require a reason")
    root = root.resolve()
    pending = [
        row for row in _read_queue(root)
        if row.get("status") == "proposed"
        and str(row.get("canonical_learning_id", "")) == str(canonical_id)
    ]
    if not pending:
        raise ValueError(f"no pending merge proposal for `{canonical_id}`")
    executed: list[dict[str, Any]] = []
    for row in pending:
        merged = [str(value) for value in row.get("merged_learning_ids", []) or []]
        if decision == "approved":
            executed.append(execute_merge_group(
                root, str(canonical_id), merged, str(reason), True))
        path = root / MERGE_QUEUE
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({
                "schema_version": "1",
                "type": "tailtrail-learning-merge-proposal",
                "canonical_learning_id": str(canonical_id),
                "merged_learning_ids": merged,
                "similarity": row.get("similarity"),
                "shared_tags": list(row.get("shared_tags", []) or []),
                "status": "executed" if decision == "approved" else "rejected",
                "reason": str(reason),
            }, sort_keys=True) + "\n")
    return {"canonical_learning_id": str(canonical_id), "decision": decision,
            "executed": executed}


def delete_learning(root: Path, learning_id: str, reason: str, approved: bool) -> dict[str, Any]:
    """Revoke a dead learning with a tombstone reason (no silent deletes).

    Requires a pre-existing snapshot (destructive acts need a rollback
    path) and approval. Revocation is terminal and history-preserving: the
    record stays in the chain marked revoked, so nothing is unhappened,
    only retired with attribution.
    """
    if approved is not True:
        raise ValueError("learning deletion requires --approved")
    if not str(reason or "").strip():
        raise ValueError("learning deletion requires a reason")
    root = root.resolve()
    snapshots = root / ".tailtrail" / "learning-v3" / "snapshots"
    if not snapshots.is_dir() or not any(snapshots.iterdir()):
        raise ValueError("learning deletion requires a prior store snapshot; snapshot first, then delete")
    V3 = load_sweep_v3()
    record = V3.terminal_transition(root, str(learning_id), "revoke", str(reason))
    return {"learning_id": str(learning_id), "status": "revoked",
            "record_id": record.get("record_id"), "reason": str(reason)}


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

    sweep = subparsers.add_parser("sweep", help="Proactively evaluate V3 record freshness.")
    sweep.add_argument("--root", type=Path, default=Path.cwd())
    sweep.add_argument("--format", choices=("markdown", "json"), default="markdown")


    merge_duplicates = subparsers.add_parser("merge-duplicates", help="Supersede exact-duplicate learnings into their earliest record.")
    merge_duplicates.add_argument("--root", type=Path, default=Path.cwd())
    merge_duplicates.add_argument("--reason", default=None)
    merge_duplicates.add_argument("--approved", action="store_true")
    merge_duplicates.add_argument("--format", choices=("markdown", "json"), default="markdown")

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
    if args.command == "sweep":
        return command_sweep(args)
    if args.command == "merge-duplicates":
        return command_merge_duplicates(args)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
