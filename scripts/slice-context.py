#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def find_matches(lines: list[str], terms: list[str]) -> list[int]:
    if not terms:
        return [index for index, line in enumerate(lines) if line.lstrip().startswith(("# ", "## ", "### ", "def ", "class "))]
    lowered_terms = [term.lower() for term in terms if term]
    return [index for index, line in enumerate(lines) if any(term in line.lower() for term in lowered_terms)]


def windows(matches: list[int], total: int, before: int, after: int) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for index in matches:
        start = max(0, index - before)
        end = min(total, index + after + 1)
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], end))
        else:
            result.append((start, end))
    return result


def slice_file(path: Path, terms: list[str], before: int, after: int, max_windows: int) -> dict[str, Any]:
    lines = read_lines(path)
    matches = find_matches(lines, terms)
    selected = windows(matches, len(lines), before, after)[:max_windows]
    slices = []
    for start, end in selected:
        slices.append(
            {
                "start_line": start + 1,
                "end_line": end,
                "text": "\n".join(lines[start:end]),
            }
        )
    return {
        "path": path.as_posix(),
        "line_count": len(lines),
        "matched_lines": [index + 1 for index in matches[: max_windows * 4]],
        "slices": slices,
    }


def build(files: list[Path], query: str, before: int, after: int, max_windows: int) -> dict[str, Any]:
    terms = [item for item in re.split(r"[\s,]+", query.strip()) if item]
    return {
        "type": "context-slices",
        "query_terms": terms,
        "files": [slice_file(path, terms, before, after, max_windows) for path in files if path.is_file()],
        "boundary": "Context slices are pointers and excerpts for orientation. Read exact source before editing.",
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Context Slices",
        "",
        f"- Query terms: `{', '.join(report['query_terms']) or 'headings/symbols'}`",
        f"- Boundary: {report['boundary']}",
        "",
    ]
    for item in report["files"]:
        lines.extend([f"## {item['path']}", "", f"- Lines: `{item['line_count']}`", f"- Matched lines: `{', '.join(str(line) for line in item['matched_lines']) or 'none'}`", ""])
        if not item["slices"]:
            lines.append("- no slices selected")
            lines.append("")
            continue
        for chunk in item["slices"]:
            lines.extend(
                [
                    f"### Lines {chunk['start_line']}-{chunk['end_line']}",
                    "",
                    "```text",
                    chunk["text"],
                    "```",
                    "",
                ]
            )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create compact context slices from local files.")
    parser.add_argument("--file", action="append", type=Path, default=[], help="File to slice. Repeat for multiple files.")
    parser.add_argument("--query", default="", help="Terms to match. Empty query slices headings and symbols.")
    parser.add_argument("--before", type=int, default=3)
    parser.add_argument("--after", type=int, default=8)
    parser.add_argument("--max-windows", type=int, default=6)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    report = build(args.file, args.query, max(args.before, 0), max(args.after, 0), max(args.max_windows, 1))
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
