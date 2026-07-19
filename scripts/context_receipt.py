#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RECEIPTS = Path(".tailtrail") / "context-receipts.jsonl"
DEFAULT_CHARS_PER_TOKEN = 4
SKIP_DIRS = {".git", ".tailtrail", "__pycache__", "node_modules", ".venv", "venv", "target", "build", "dist"}
EXACTNESS_CLASSES = {"must-be-exact", "structure-exact", "summary-safe", "reduce-safe", "skip-reduction"}
UNSAFE_EXACT_STRATEGY_TERMS = ("summary", "summarize", "compress", "drop", "drop-lines", "paraphrase", "reduce")
UNSAFE_TEXT_MARKERS = ("BEGIN PRIVATE KEY", "BEGIN RSA PRIVATE KEY", "AKIA", "ghp_", "xoxb-", "password=", "secret=")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def approx_tokens_for_path(root: Path, value: str, chars_per_token: int = DEFAULT_CHARS_PER_TOKEN) -> int:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        return 0
    files = [path] if path.is_file() else [item for item in path.rglob("*") if item.is_file() and not any(part in SKIP_DIRS for part in item.parts)]
    chars = 0
    for file in files:
        try:
            chars += len(file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
    return math.ceil(chars / chars_per_token) if chars else 0


def default_retrieval(path: str) -> dict[str, str]:
    return {"type": "path", "command": f"cat {json.dumps(path)}"}


def pick(values: list[str] | None, index: int, default: str) -> str:
    if not values:
        return default
    if index < len(values):
        return values[index]
    if len(values) == 1:
        return values[0]
    return default


def safe_text(value: str, field: str) -> None:
    if len(value) > 240 or "\n" in value or "\r" in value:
        raise SystemExit(f"Refusing receipt field `{field}` because it looks like raw content.")
    upper = value.upper()
    lowered = value.lower()
    if any(marker.upper() in upper for marker in UNSAFE_TEXT_MARKERS) or "token=" in lowered:
        raise SystemExit(f"Refusing receipt field `{field}` because it may contain a secret.")


def summarize_paths(
    root: Path,
    paths: list[str],
    exactness_values: list[str] | None = None,
    strategy_values: list[str] | None = None,
    preserve_values: list[str] | None = None,
    retrieval_values: list[str] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(paths):
        exactness = pick(exactness_values, index, "skip-reduction")
        strategy = pick(strategy_values, index, "skip-reduction")
        if exactness not in EXACTNESS_CLASSES:
            raise SystemExit(f"Unknown exactness class `{exactness}` for `{item}`.")
        for value, field in [(strategy, "strategy"), *[(entry, "preserve") for entry in preserve_values or []]]:
            safe_text(value, field)
        retrieval_command = pick(retrieval_values, index, default_retrieval(item)["command"])
        safe_text(retrieval_command, "retrieval")
        rows.append(
            {
                "path": item,
                "approx_tokens": approx_tokens_for_path(root, item),
                "exactness_class": exactness,
                "strategy": strategy,
                "preserve": preserve_values or ["retrieval pointer"],
                "retrieval": {"type": "path", "command": retrieval_command},
            }
        )
    return rows


def summarize_simple_paths(root: Path, paths: list[str]) -> list[dict[str, Any]]:
    return [{"path": item, "approx_tokens": approx_tokens_for_path(root, item)} for item in paths]


def total(items: list[dict[str, Any]]) -> int:
    return sum(int(item.get("approx_tokens", 0)) for item in items)


def capture_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    legacy_mode = not any(
        hasattr(args, name)
        for name in (
            "loaded_exactness",
            "avoided_exactness",
            "loaded_strategy",
            "avoided_strategy",
            "preserve",
            "preserved_evidence",
            "retrieval",
            "route_source",
            "reduction_strategy",
        )
    )
    if legacy_mode:
        loaded = summarize_simple_paths(root, args.loaded or [])
        avoided = summarize_simple_paths(root, args.avoided or [])
        loaded_tokens = args.loaded_tokens if args.loaded_tokens is not None else total(loaded)
        avoided_tokens = args.avoided_tokens if args.avoided_tokens is not None else total(avoided)
        baseline = loaded_tokens + avoided_tokens
        return {
            "schema_version": "1",
            "type": "context-receipt",
            "created_at": now(),
            "root": root.as_posix(),
            "task": args.task or "not provided",
            "profile": args.profile,
            "budget_tokens": args.budget,
            "loaded": loaded,
            "avoided": avoided,
            "loaded_tokens": loaded_tokens,
            "avoided_tokens": avoided_tokens,
            "baseline_tokens": baseline,
            "estimated_reduction_percent": round((avoided_tokens / baseline) * 100, 2) if baseline else 0.0,
            "graph_first": args.graph_first,
            "budget_escalated": args.budget_escalated,
            "reason": args.reason or "",
            "claim_guardrail": "Context receipt uses local approximate counts unless explicit measured telemetry is supplied separately.",
            "privacy": "Do not include raw prompts, source snippets, logs, secrets, PII, PHI, or customer data.",
        }
    preserve_args = getattr(args, "preserve", [])
    loaded = summarize_paths(
        root,
        args.loaded or [],
        getattr(args, "loaded_exactness", []),
        getattr(args, "loaded_strategy", []),
        preserve_args,
        getattr(args, "retrieval", []),
    )
    avoided = summarize_paths(
        root,
        args.avoided or [],
        getattr(args, "avoided_exactness", []),
        getattr(args, "avoided_strategy", []),
        preserve_args,
        None,
    )
    loaded_tokens = args.loaded_tokens if args.loaded_tokens is not None else total(loaded)
    avoided_tokens = args.avoided_tokens if args.avoided_tokens is not None else total(avoided)
    baseline = loaded_tokens + avoided_tokens
    preserved = getattr(args, "preserved_evidence", []) or preserve_args or []
    reduction_strategy = getattr(args, "reduction_strategy", "")
    route_source = getattr(args, "route_source", "")
    for value in [reduction_strategy, route_source, *preserved]:
        if value:
            safe_text(value, "receipt metadata")
    payload = {
        "schema_version": "2",
        "type": "tailtrail-context-receipt",
        "created_at": now(),
        "root": root.as_posix(),
        "task": args.task or "not provided",
        "profile": args.profile,
        "budget_tokens": args.budget,
        "loaded": loaded,
        "avoided": avoided,
        "loaded_tokens": loaded_tokens,
        "avoided_tokens": avoided_tokens,
        "baseline_tokens": baseline,
        "estimated_reduction_percent": round((avoided_tokens / baseline) * 100, 2) if baseline else 0.0,
        "preserved_evidence": preserved,
        "reduction_strategy": reduction_strategy or "not provided",
        "route_source": route_source or "manual",
        "graph_first": args.graph_first,
        "budget_escalated": args.budget_escalated,
        "reason": args.reason or "",
        "claim_guardrail": "Context receipt uses local approximate counts unless explicit measured telemetry is supplied separately.",
        "privacy": "Do not include raw prompts, source snippets, logs, secrets, PII, PHI, or customer data.",
    }
    validate_receipt(payload)
    return payload


def validate_receipt(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != "2":
        return
    issues: list[str] = []
    for collection in ("loaded", "avoided"):
        for item in payload.get(collection, []):
            exactness = item.get("exactness_class")
            strategy = str(item.get("strategy", ""))
            if exactness not in EXACTNESS_CLASSES:
                issues.append(f"{collection} item `{item.get('path', 'unknown')}` has invalid exactness `{exactness}`")
            if exactness == "must-be-exact" and any(term in strategy.lower() for term in UNSAFE_EXACT_STRATEGY_TERMS):
                issues.append(f"{collection} item `{item.get('path', 'unknown')}` uses unsafe strategy `{strategy}` for must-be-exact content")
            retrieval = item.get("retrieval")
            if not isinstance(retrieval, dict) or not retrieval.get("command"):
                issues.append(f"{collection} item `{item.get('path', 'unknown')}` has no retrieval command")
            for value in item.get("preserve", []):
                if not isinstance(value, str):
                    issues.append(f"{collection} item `{item.get('path', 'unknown')}` has non-string preserve entry")
    if issues:
        raise SystemExit("Context receipt v2 validation failed:\n- " + "\n- ".join(issues))


def write_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def summary_payload(root: Path, receipts: Path) -> dict[str, Any]:
    rows = read_jsonl(receipts)
    loaded = sum(int(row.get("loaded_tokens", 0)) for row in rows)
    avoided = sum(int(row.get("avoided_tokens", 0)) for row in rows)
    baseline = loaded + avoided
    schema_counts: dict[str, int] = {}
    exactness_counts: dict[str, int] = {}
    strategy_counts: dict[str, int] = {}
    retrieval_items = 0
    for row in rows:
        schema = str(row.get("schema_version", "unknown"))
        schema_counts[schema] = schema_counts.get(schema, 0) + 1
        for item in [*(row.get("loaded", []) or []), *(row.get("avoided", []) or [])]:
            if not isinstance(item, dict):
                continue
            exactness = str(item.get("exactness_class", "unknown"))
            strategy = str(item.get("strategy", "unknown"))
            exactness_counts[exactness] = exactness_counts.get(exactness, 0) + 1
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            if isinstance(item.get("retrieval"), dict) and item["retrieval"].get("command"):
                retrieval_items += 1
    return {
        "schema_version": "2",
        "type": "context-receipt-summary",
        "root": root.resolve().as_posix(),
        "receipts": len(rows),
        "schema_counts": schema_counts,
        "exactness_counts": exactness_counts,
        "strategy_counts": strategy_counts,
        "retrieval_items": retrieval_items,
        "loaded_tokens": loaded,
        "avoided_tokens": avoided,
        "baseline_tokens": baseline,
        "estimated_reduction_percent": round((avoided / baseline) * 100, 2) if baseline else 0.0,
        "claim_guardrail": "Summary is approximate context accounting, not exact model/API token usage.",
    }


def render_receipt(payload: dict[str, Any]) -> str:
    lines = [
        "# Context Receipt",
        "",
        f"- Task: {payload['task']}",
        f"- Profile: `{payload['profile']}`",
        f"- Budget: `{payload['budget_tokens']}`",
        f"- Loaded approx tokens: `{payload['loaded_tokens']}`",
        f"- Avoided approx tokens: `{payload['avoided_tokens']}`",
        f"- Estimated reduction: `{payload['estimated_reduction_percent']}%`",
        f"- Graph-first: `{payload['graph_first']}`",
        f"- Budget escalated: `{payload['budget_escalated']}`",
        f"- Claim guardrail: {payload['claim_guardrail']}",
        "",
        "## Loaded",
    ]
    lines.extend(f"- `{item['path']}` approx `{item['approx_tokens']}`" for item in payload["loaded"] or [{"path": "none", "approx_tokens": 0}])
    if payload.get("schema_version") == "2":
        for item in payload["loaded"]:
            lines.append(f"  - exactness `{item['exactness_class']}`, strategy `{item['strategy']}`, retrieval `{item['retrieval']['command']}`")
    lines.extend(["", "## Avoided"])
    lines.extend(f"- `{item['path']}` approx `{item['approx_tokens']}`" for item in payload["avoided"] or [{"path": "none", "approx_tokens": 0}])
    if payload.get("schema_version") == "2":
        for item in payload["avoided"]:
            lines.append(f"  - exactness `{item['exactness_class']}`, strategy `{item['strategy']}`, retrieval `{item['retrieval']['command']}`")
        lines.extend(["", "## Reversibility", f"- Route source: `{payload['route_source']}`", f"- Reduction strategy: `{payload['reduction_strategy']}`"])
        if payload["preserved_evidence"]:
            lines.append("- Preserved evidence:")
            lines.extend(f"  - {item}" for item in payload["preserved_evidence"])
    if payload.get("reason"):
        lines.extend(["", "## Reason", payload["reason"]])
    return "\n".join(lines) + "\n"


def render_summary(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Context Receipt Summary",
            "",
            f"- Receipts: `{payload['receipts']}`",
            f"- Schema counts: `{payload['schema_counts']}`",
            f"- Retrieval-backed items: `{payload['retrieval_items']}`",
            f"- Loaded approx tokens: `{payload['loaded_tokens']}`",
            f"- Avoided approx tokens: `{payload['avoided_tokens']}`",
            f"- Estimated reduction: `{payload['estimated_reduction_percent']}%`",
            f"- Claim guardrail: {payload['claim_guardrail']}",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture local context receipts for TailTrail token evidence.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    capture = subparsers.add_parser("capture", help="Capture an approved context receipt.")
    capture.add_argument("--root", type=Path, default=Path.cwd())
    capture.add_argument("--task", default="")
    capture.add_argument("--profile", default="lean")
    capture.add_argument("--budget", type=int, default=0)
    capture.add_argument("--loaded", action="append", default=[])
    capture.add_argument("--avoided", action="append", default=[])
    capture.add_argument("--loaded-exactness", action="append", default=[])
    capture.add_argument("--avoided-exactness", action="append", default=[])
    capture.add_argument("--loaded-strategy", action="append", default=[])
    capture.add_argument("--avoided-strategy", action="append", default=[])
    capture.add_argument("--preserve", action="append", default=[])
    capture.add_argument("--preserved-evidence", action="append", default=[])
    capture.add_argument("--retrieval", action="append", default=[])
    capture.add_argument("--route-source", default="")
    capture.add_argument("--reduction-strategy", default="")
    capture.add_argument("--loaded-tokens", type=int, default=None)
    capture.add_argument("--avoided-tokens", type=int, default=None)
    capture.add_argument("--graph-first", choices=("yes", "no"), default="no")
    capture.add_argument("--budget-escalated", choices=("yes", "no"), default="no")
    capture.add_argument("--reason", default="")
    capture.add_argument("--receipts", type=Path, default=None)
    capture.add_argument("--approved", action="store_true")
    capture.add_argument("--format", choices=("markdown", "json"), default="markdown")
    summary = subparsers.add_parser("summary", help="Summarize context receipts.")
    summary.add_argument("--root", type=Path, default=Path.cwd())
    summary.add_argument("--receipts", type=Path, default=None)
    summary.add_argument("--format", choices=("markdown", "json"), default="markdown")
    retrieve = subparsers.add_parser("retrieve", help="Show a retrieval command for an original context path.")
    retrieve.add_argument("--root", type=Path, default=Path.cwd())
    retrieve.add_argument("--path", required=True)
    retrieve.add_argument("--receipts", type=Path, default=None)
    retrieve.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()

    if args.command == "capture":
        if not args.approved:
            raise SystemExit("Refusing to write context receipt without --approved.")
        payload = capture_payload(args)
        write_jsonl(args.receipts or args.root / DEFAULT_RECEIPTS, payload)
        print(json.dumps(payload, indent=2) if args.format == "json" else render_receipt(payload), end="")
        return 0
    if args.command == "summary":
        payload = summary_payload(args.root, args.receipts or args.root / DEFAULT_RECEIPTS)
        print(json.dumps(payload, indent=2) if args.format == "json" else render_summary(payload), end="")
        return 0
    rows = read_jsonl(args.receipts or args.root / DEFAULT_RECEIPTS)
    command = default_retrieval(args.path)["command"]
    found = False
    for row in reversed(rows):
        for item in [*(row.get("loaded", []) or []), *(row.get("avoided", []) or [])]:
            if isinstance(item, dict) and item.get("path") == args.path:
                retrieval = item.get("retrieval") if isinstance(item.get("retrieval"), dict) else {}
                command = str(retrieval.get("command") or command)
                found = True
                break
        if found:
            break
    payload = {"schema_version": "2", "type": "context-receipt-retrieval", "path": args.path, "found_in_receipts": found, "command": command}
    print(json.dumps(payload, indent=2) if args.format == "json" else f"# Context Receipt Retrieval\n\n- Path: `{args.path}`\n- Found in receipts: `{str(found).lower()}`\n- Command: `{command}`\n", end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
