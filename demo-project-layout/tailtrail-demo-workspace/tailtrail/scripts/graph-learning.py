#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1"
TAILTRAIL_DIR = Path(".tailtrail")
EVENTS = TAILTRAIL_DIR / "learning-events.jsonl"
GRAPH_CACHE = TAILTRAIL_DIR / "code-graph-cache.json"
GRAPH_LEARNING_INDEX = TAILTRAIL_DIR / "graph-learning-index.json"
REFRESH_ACTIONS = TAILTRAIL_DIR / "learning-refresh-actions.json"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return sorted({item.strip() for item in value.split(",") if item.strip()})


def rel_path(root: Path, value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()
    return path.as_posix()


def file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


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
    data = read_json(root / REFRESH_ACTIONS)
    actions = data.get("actions", []) if data else []
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


def event_by_id(root: Path, learning_id: str) -> dict[str, Any]:
    for event in read_events(root):
        if event.get("id") == learning_id:
            return event
    raise SystemExit(f"Learning event not found: {learning_id}")


def confidence_band(event: dict[str, Any]) -> str:
    confidence = event.get("learning_confidence", {})
    return str(confidence.get("band", "unknown")) if isinstance(confidence, dict) else "unknown"


def confidence_score(event: dict[str, Any]) -> int:
    confidence = event.get("learning_confidence", {})
    score = confidence.get("score", 0) if isinstance(confidence, dict) else 0
    return int(score) if isinstance(score, int) else 0


def usable_event(event: dict[str, Any], include_sensitive: bool = False, refresh_actions: dict[str, str] | None = None) -> bool:
    if refresh_actions and refresh_actions.get(str(event.get("id"))) in {"mark-stale", "suppress", "archive", "delete"}:
        return False
    if event.get("sensitivity") != "normal" and not include_sensitive:
        return False
    if str(event.get("acceptance", "unknown")) == "rejected":
        return False
    if confidence_band(event) not in {"candidate", "trusted"}:
        return False
    return bool(event.get("learning_candidate"))


def empty_index(root: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": now(),
        "root": root.as_posix(),
        "learning_links": [],
    }


def load_index(root: Path) -> dict[str, Any]:
    path = root / GRAPH_LEARNING_INDEX
    data = read_json(path)
    if not data or data.get("schema_version") != SCHEMA_VERSION:
        return empty_index(root)
    if not isinstance(data.get("learning_links"), list):
        data["learning_links"] = []
    return data


def save_index(root: Path, index: dict[str, Any]) -> Path:
    index["schema_version"] = SCHEMA_VERSION
    index["updated_at"] = now()
    index["root"] = root.as_posix()
    path = root / GRAPH_LEARNING_INDEX
    write_json(path, index)
    return path


def graph_cache(root: Path) -> dict[str, Any] | None:
    return read_json(root / GRAPH_CACHE)


def graph_status(root: Path, cache: dict[str, Any] | None, changed: list[str]) -> dict[str, Any]:
    if not cache:
        return {"status": "missing", "reasons": ["No Code Graph Mapper cache exists."], "scope": changed}
    reasons: list[str] = []
    invalid: list[str] = []
    if cache.get("schema_version") != SCHEMA_VERSION:
        invalid.append("Code graph cache schema version is unsupported.")
    cache_root = cache.get("root")
    if cache_root and Path(str(cache_root)).resolve() != root.resolve():
        invalid.append("Code graph cache root does not match current project root.")
    target_scope = set(changed)
    cached_scope = {str(item) for item in cache.get("scope", []) if item}
    if target_scope and not target_scope.issubset(cached_scope) and not target_scope.intersection(cached_scope):
        reasons.append("Requested files are outside the cached graph scope.")
    for group in ("source_files", "watch_files", "scanner_evidence"):
        values = cache.get(group, {})
        if not isinstance(values, dict):
            invalid.append(f"{group} is not an object.")
            continue
        for rel, metadata in values.items():
            if not isinstance(metadata, dict):
                invalid.append(f"{group}.{rel} metadata is not an object.")
                continue
            expected = metadata.get("sha256")
            if not isinstance(expected, str):
                invalid.append(f"{group}.{rel} has no usable sha256.")
                continue
            actual = file_sha256(root / rel)
            if actual is None:
                reasons.append(f"{rel} is missing.")
            elif actual != expected:
                reasons.append(f"{rel} changed after graph creation.")
    if invalid:
        return {"status": "invalid", "reasons": invalid, "scope": sorted(cached_scope)}
    if reasons:
        return {"status": "stale", "reasons": reasons, "scope": sorted(cached_scope)}
    return {"status": "fresh", "reasons": ["Graph hashes still match."], "scope": sorted(cached_scope)}


def graph_scope(cache: dict[str, Any] | None) -> dict[str, set[str]]:
    graph = cache.get("graph", {}) if isinstance(cache, dict) and isinstance(cache.get("graph"), dict) else {}
    scope: dict[str, set[str]] = {
        "files": set(str(item) for item in cache.get("scope", []) if item) if isinstance(cache, dict) else set(),
        "symbols": set(),
        "rules": set(),
        "endpoints": set(),
        "tables": set(),
        "manifests": set(),
    }
    for key in ("symbols", "call_chains", "type_hierarchy"):
        for item in graph.get(key, []) if isinstance(graph.get(key), list) else []:
            if isinstance(item, dict):
                for field in ("name", "caller", "callee", "type", "inherits"):
                    if item.get(field):
                        scope["symbols"].add(str(item[field]))
                if item.get("file"):
                    scope["files"].add(str(item["file"]))
    for item in graph.get("endpoints", []) if isinstance(graph.get("endpoints"), list) else []:
        if isinstance(item, dict):
            if item.get("route"):
                scope["endpoints"].add(str(item["route"]))
            if item.get("handler"):
                scope["symbols"].add(str(item["handler"]))
            if item.get("file"):
                scope["files"].add(str(item["file"]))
    for item in graph.get("db_tables", []) if isinstance(graph.get("db_tables"), list) else []:
        if isinstance(item, dict) and item.get("table"):
            scope["tables"].add(str(item["table"]))
    for item in graph.get("nearby_manifests", []) if isinstance(graph.get("nearby_manifests"), list) else []:
        scope["manifests"].add(str(item))
        scope["files"].add(str(item))
    for item in graph.get("likely_tests", []) if isinstance(graph.get("likely_tests"), list) else []:
        scope["files"].add(str(item))
    for item in graph.get("likely_callers", []) if isinstance(graph.get("likely_callers"), list) else []:
        scope["files"].add(str(item))
    return scope


def link_hashes(root: Path, files: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for item in files:
        digest = file_sha256(root / item)
        if digest:
            hashes[item] = digest
    return hashes


def link_from_args(root: Path, args: argparse.Namespace, event: dict[str, Any]) -> dict[str, Any]:
    files = sorted({rel_path(root, item) for item in [*args.file, *event.get("files", [])] if item})
    validation_commands = [*event.get("validation_commands", []), *args.validation_command]
    return {
        "learning_id": args.learning_id,
        "learning_file": ".tailtrail/learnings.md",
        "repo_scope": root.name,
        "graph_scope": files,
        "linked_symbols": split_csv(args.symbols),
        "linked_files": files,
        "linked_rules": split_csv(args.rules),
        "linked_tables": split_csv(args.tables),
        "linked_endpoints": split_csv(args.endpoints),
        "linked_manifests": [rel_path(root, item) for item in args.manifest],
        "problem_type": args.problem_type or str(event.get("task_type", "unknown")),
        "accepted_resolution": str(event.get("learning_candidate", "")),
        "validation_commands": sorted(set(str(item) for item in validation_commands if item)),
        "approval_status": "curated" if confidence_band(event) == "trusted" else "candidate",
        "sensitivity": str(event.get("sensitivity", "normal")),
        "score": confidence_score(event),
        "band": confidence_band(event),
        "tags": sorted(set(str(item) for item in event.get("tags", []) + split_csv(args.tags))),
        "file_hashes": link_hashes(root, files),
        "stale_when": split_csv(args.stale_when) or [str(event.get("stale_when") or "linked file, validation command, policy, graph, or scanner rule changes")],
        "created_at": now(),
        "updated_at": now(),
    }


def stale_reasons(root: Path, link: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    hashes = link.get("file_hashes", {})
    if not isinstance(hashes, dict):
        return ["link file_hashes is not an object"]
    for rel, expected in hashes.items():
        actual = file_sha256(root / str(rel))
        if actual is None:
            reasons.append(f"{rel} is missing.")
        elif actual != expected:
            reasons.append(f"{rel} changed after graph-learning link creation.")
    return reasons


def match_score(
    event: dict[str, Any],
    link: dict[str, Any] | None,
    tags: set[str],
    files: set[str],
    symbols: set[str],
    rules: set[str],
    graph_terms: dict[str, set[str]],
    graph_state: str,
) -> tuple[int, list[str]]:
    score = confidence_score(event)
    reasons: list[str] = []
    event_tags = set(str(item) for item in event.get("tags", []))
    event_files = set(str(item) for item in event.get("files", []))
    if tags and tags.intersection(event_tags):
        score += 15
        reasons.append("tag match: " + ", ".join(sorted(tags.intersection(event_tags))))
    if files and any(file in event_files or any(file in existing or existing in file for existing in event_files) for file in files):
        score += 25
        reasons.append("event file match")
    if graph_state == "fresh":
        score += 5
        reasons.append("fresh graph cache")
    elif graph_state in {"stale", "invalid"}:
        score -= 15
        reasons.append(f"graph cache is {graph_state}")
    elif graph_state == "missing":
        score -= 5
        reasons.append("graph cache missing; matched from learning metadata only")
    if link:
        link_files = set(str(item) for item in link.get("linked_files", []))
        link_symbols = set(str(item) for item in link.get("linked_symbols", []))
        link_rules = set(str(item) for item in link.get("linked_rules", []))
        link_tables = set(str(item) for item in link.get("linked_tables", []))
        link_endpoints = set(str(item) for item in link.get("linked_endpoints", []))
        if files and (files.intersection(link_files) or any(file in linked or linked in file for file in files for linked in link_files)):
            score += 30
            reasons.append("linked file match")
        if symbols and symbols.intersection(link_symbols):
            score += 30
            reasons.append("linked symbol match")
        if rules and rules.intersection(link_rules):
            score += 35
            reasons.append("linked scanner rule match")
        if graph_terms["symbols"].intersection(link_symbols):
            score += 20
            reasons.append("graph symbol match")
        if graph_terms["files"].intersection(link_files):
            score += 20
            reasons.append("graph file/test/caller match")
        if graph_terms["tables"].intersection(link_tables):
            score += 20
            reasons.append("graph table match")
        if graph_terms["endpoints"].intersection(link_endpoints):
            score += 20
            reasons.append("graph endpoint match")
        if tags and tags.intersection(set(str(item) for item in link.get("tags", []))):
            score += 10
            reasons.append("linked tag match")
    return max(0, min(150, score)), reasons


def candidate_matches(root: Path, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    refresh_actions = read_refresh_actions(root)
    events = {str(event.get("id")): event for event in read_events(root) if usable_event(event, args.include_sensitive, refresh_actions)}
    index = load_index(root)
    links = [link for link in index.get("learning_links", []) if isinstance(link, dict)]
    cache = graph_cache(root)
    changed = [rel_path(root, item) for item in args.changed]
    status = graph_status(root, cache, changed)
    terms = graph_scope(cache) if status["status"] == "fresh" else {"files": set(changed), "symbols": set(), "rules": set(), "endpoints": set(), "tables": set(), "manifests": set()}
    tags = set(split_csv(args.tags))
    files = set(changed + [rel_path(root, item) for item in args.file])
    symbols = set(split_csv(args.symbols))
    rules = set(split_csv(args.rules))
    matches: list[dict[str, Any]] = []

    linked_ids: set[str] = set()
    for link in links:
        learning_id = str(link.get("learning_id", ""))
        event = events.get(learning_id)
        if not event:
            continue
        if link.get("sensitivity") != "normal" and not args.include_sensitive:
            continue
        stale = stale_reasons(root, link)
        if stale:
            continue
        score, reasons = match_score(event, link, tags, files, symbols, rules, terms, status["status"])
        if reasons:
            linked_ids.add(learning_id)
            matches.append({"event": event, "link": link, "match_score": score, "match_reasons": reasons, "source": "graph-learning-index"})

    for learning_id, event in events.items():
        if learning_id in linked_ids:
            continue
        score, reasons = match_score(event, None, tags, files, symbols, rules, terms, status["status"])
        if reasons:
            matches.append({"event": event, "link": None, "match_score": score, "match_reasons": reasons, "source": "learning-events"})

    matches.sort(key=lambda item: (int(item["match_score"]), confidence_score(item["event"])), reverse=True)
    return matches[: args.limit], status


def render_matches(matches: list[dict[str, Any]], status: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Graph-Aware Learning",
        "",
        "Use these as prior repo patterns only after reading current exact source, policy, scanner, and validation evidence.",
        "",
        "## Graph Status",
        "",
        f"- Status: `{status['status']}`",
        f"- Scope: {', '.join(status.get('scope', [])) if status.get('scope') else 'not provided'}",
        "- Reasons:",
    ]
    lines.extend(f"  - {reason}" for reason in status.get("reasons", []))
    lines.extend(["", "## Matches", ""])
    if not matches:
        lines.append("- No matching graph-aware learnings found.")
    for item in matches:
        event = item["event"]
        link = item.get("link") or {}
        confidence = event.get("learning_confidence", {})
        lines.extend(
            [
                f"### {event.get('id')}",
                "",
                f"- Match score: `{item['match_score']}`",
                f"- Learning score: `{confidence.get('score', 0)} / 100` ({confidence.get('band', 'unknown')})",
                f"- Source: `{item['source']}`",
                f"- Type: `{event.get('task_type', 'unknown')}`",
                f"- Tags: {', '.join(event.get('tags', [])) or 'none'}",
                f"- Files: {', '.join(link.get('linked_files') or event.get('files', [])) or 'not linked'}",
                f"- Learning: {event.get('learning_candidate')}",
                f"- Validation: {', '.join(link.get('validation_commands') or event.get('validation_commands', [])) or 'not recorded'}",
                "- Why matched:",
            ]
        )
        lines.extend(f"  - {reason}" for reason in item["match_reasons"])
        lines.append("")
    lines.extend(
        [
            "## Boundaries",
            "",
            "- Do not apply a learning blindly.",
            "- Do not load raw learning event history during normal implementation.",
            "- Current source, scanner, CI, policy, and guardrail evidence wins over old learning.",
        ]
    )
    return "\n".join(lines) + "\n"


def command_link(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    event = event_by_id(root, args.learning_id)
    if not usable_event(event, include_sensitive=args.include_sensitive):
        raise SystemExit("Learning is not eligible for graph linking because it is low-confidence, rejected, sensitive, or missing a candidate.")
    index = load_index(root)
    link = link_from_args(root, args, event)
    links = [item for item in index.get("learning_links", []) if isinstance(item, dict) and item.get("learning_id") != args.learning_id]
    links.append(link)
    index["learning_links"] = links
    path = save_index(root, index)
    if args.format == "json":
        print(json.dumps({"index": path.as_posix(), "link": link}, indent=2, sort_keys=True))
    else:
        print(f"Linked learning `{args.learning_id}` into {path}")
    return 0


def command_search(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    matches, status = candidate_matches(root, args)
    if args.format == "json":
        print(json.dumps({"graph_status": status, "matches": matches}, indent=2, sort_keys=True))
    else:
        print(render_matches(matches, status), end="")
    return 0


def command_inspect(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    event = event_by_id(root, args.learning_id)
    index = load_index(root)
    links = [link for link in index.get("learning_links", []) if isinstance(link, dict) and link.get("learning_id") == args.learning_id]
    data = {"event": event, "links": links, "stale_reasons": [stale_reasons(root, link) for link in links]}
    if args.format == "json":
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(render_matches([{"event": event, "link": links[0] if links else None, "match_score": confidence_score(event), "match_reasons": ["inspect requested"], "source": "inspect"}], {"status": "inspect", "scope": [], "reasons": ["inspect requested"]}), end="")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    index = load_index(root)
    events = {str(event.get("id")): event for event in read_events(root)}
    problems: list[str] = []
    for link in index.get("learning_links", []):
        if not isinstance(link, dict):
            problems.append("Non-object link in graph-learning index.")
            continue
        learning_id = str(link.get("learning_id", ""))
        event = events.get(learning_id)
        if not event:
            problems.append(f"{learning_id}: linked event does not exist.")
            continue
        if not usable_event(event, include_sensitive=args.include_sensitive, refresh_actions=read_refresh_actions(root)):
            problems.append(f"{learning_id}: linked event is not eligible for automatic retrieval.")
        for reason in stale_reasons(root, link):
            problems.append(f"{learning_id}: {reason}")
    result = {"status": "pass" if not problems else "fail", "problems": problems, "links": len(index.get("learning_links", []))}
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("# TailTrail Graph-Aware Learning Validation")
        print()
        print(f"- Status: `{result['status']}`")
        print(f"- Links: `{result['links']}`")
        if problems:
            print("- Problems:")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print("- Problems: none")
    return 0 if not problems else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Link and search TailTrail learnings using Code Graph Mapper scope.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--root", type=Path, default=Path.cwd(), help="Project root.")
        sub.add_argument("--format", choices=("markdown", "json"), default="markdown")
        sub.add_argument("--include-sensitive", action="store_true", help="Allow explicit sensitive inspection/search.")

    link = subparsers.add_parser("link", help="Link a learning event to graph metadata.")
    common(link)
    link.add_argument("--learning-id", required=True)
    link.add_argument("--file", action="append", default=[])
    link.add_argument("--symbols")
    link.add_argument("--rules")
    link.add_argument("--tables")
    link.add_argument("--endpoints")
    link.add_argument("--manifest", action="append", default=[])
    link.add_argument("--tags")
    link.add_argument("--problem-type")
    link.add_argument("--validation-command", action="append", default=[])
    link.add_argument("--stale-when")

    search = subparsers.add_parser("search", help="Search graph-aware learning matches.")
    common(search)
    search.add_argument("--changed", action="append", default=[])
    search.add_argument("--file", action="append", default=[])
    search.add_argument("--tags")
    search.add_argument("--symbols")
    search.add_argument("--rules")
    search.add_argument("--limit", type=int, default=3)

    inspect = subparsers.add_parser("inspect", help="Inspect one graph-linked learning.")
    common(inspect)
    inspect.add_argument("--learning-id", required=True)

    validate = subparsers.add_parser("validate", help="Validate graph-learning links.")
    common(validate)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "link":
        return command_link(args)
    if args.command == "search":
        return command_search(args)
    if args.command == "inspect":
        return command_inspect(args)
    if args.command == "validate":
        return command_validate(args)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
