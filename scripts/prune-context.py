#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_DROP = (
    "node_modules",
    ".git",
    "__pycache__",
    "dist/",
    "build/",
    "target/",
    "coverage/",
    ".tailtrail/quality-runs",
    ".tailtrail/vulnerability-runs",
)


def approx_tokens(text: str) -> int:
    return (len(text) + 3) // 4


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def should_drop_line(line: str, drop_terms: tuple[str, ...]) -> bool:
    lowered = line.lower()
    return any(term.lower() in lowered for term in drop_terms)


def prune_file(path: Path, drop_terms: tuple[str, ...], keep_headings: bool) -> dict[str, Any]:
    original = read_text(path)
    kept: list[str] = []
    dropped = 0
    for line in original.splitlines():
        if should_drop_line(line, drop_terms):
            dropped += 1
            continue
        if keep_headings or line.strip():
            kept.append(line)
    pruned = "\n".join(kept) + ("\n" if kept else "")
    return {
        "path": path.as_posix(),
        "original_lines": len(original.splitlines()),
        "kept_lines": len(kept),
        "dropped_lines": dropped,
        "original_approx_tokens": approx_tokens(original),
        "pruned_approx_tokens": approx_tokens(pruned),
        "pruned_text": pruned,
    }


def build(files: list[Path], drop: tuple[str, ...], keep_headings: bool, include_text: bool) -> dict[str, Any]:
    results = [prune_file(path, drop, keep_headings) for path in files if path.is_file()]
    original = sum(item["original_approx_tokens"] for item in results)
    pruned = sum(item["pruned_approx_tokens"] for item in results)
    if not include_text:
        for item in results:
            item.pop("pruned_text", None)
    return {
        "type": "context-prune-report",
        "drop_terms": list(drop),
        "original_approx_tokens": original,
        "pruned_approx_tokens": pruned,
        "estimated_saved_tokens": max(0, original - pruned),
        "files": results,
        "claim_guardrail": "Token values are character-count estimates, not exact model/API token usage.",
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Context Prune Report",
        "",
        f"- Original approx tokens: `{report['original_approx_tokens']}`",
        f"- Pruned approx tokens: `{report['pruned_approx_tokens']}`",
        f"- Estimated saved tokens: `{report['estimated_saved_tokens']}`",
        f"- Claim guardrail: {report['claim_guardrail']}",
        "",
        "## Files",
        "",
    ]
    for item in report["files"]:
        lines.extend(
            [
                f"### {item['path']}",
                "",
                f"- Original lines: `{item['original_lines']}`",
                f"- Kept lines: `{item['kept_lines']}`",
                f"- Dropped lines: `{item['dropped_lines']}`",
                f"- Original approx tokens: `{item['original_approx_tokens']}`",
                f"- Pruned approx tokens: `{item['pruned_approx_tokens']}`",
                "",
            ]
        )
        if "pruned_text" in item:
            lines.extend(["```text", item["pruned_text"], "```", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune noisy local context files with explicit drop terms.")
    parser.add_argument("--file", action="append", type=Path, default=[], help="File to prune. Repeat for multiple files.")
    parser.add_argument("--drop", action="append", default=[], help="Additional line drop term. Repeat for multiple terms.")
    parser.add_argument("--include-text", action="store_true", help="Include pruned text in output.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    report = build(args.file, tuple([*DEFAULT_DROP, *args.drop]), True, args.include_text)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
