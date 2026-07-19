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


def summarize_paths(root: Path, paths: list[str]) -> list[dict[str, Any]]:
    return [{"path": item, "approx_tokens": approx_tokens_for_path(root, item)} for item in paths]


def total(items: list[dict[str, Any]]) -> int:
    return sum(int(item.get("approx_tokens", 0)) for item in items)


def capture_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    loaded = summarize_paths(root, args.loaded or [])
    avoided = summarize_paths(root, args.avoided or [])
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
    return {
        "schema_version": "1",
        "type": "context-receipt-summary",
        "root": root.resolve().as_posix(),
        "receipts": len(rows),
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
    lines.extend(["", "## Avoided"])
    lines.extend(f"- `{item['path']}` approx `{item['approx_tokens']}`" for item in payload["avoided"] or [{"path": "none", "approx_tokens": 0}])
    if payload.get("reason"):
        lines.extend(["", "## Reason", payload["reason"]])
    return "\n".join(lines) + "\n"


def render_summary(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Context Receipt Summary",
            "",
            f"- Receipts: `{payload['receipts']}`",
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
    args = parser.parse_args()

    if args.command == "capture":
        if not args.approved:
            raise SystemExit("Refusing to write context receipt without --approved.")
        payload = capture_payload(args)
        write_jsonl(args.receipts or args.root / DEFAULT_RECEIPTS, payload)
        print(json.dumps(payload, indent=2) if args.format == "json" else render_receipt(payload), end="")
        return 0
    payload = summary_payload(args.root, args.receipts or args.root / DEFAULT_RECEIPTS)
    print(json.dumps(payload, indent=2) if args.format == "json" else render_summary(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
