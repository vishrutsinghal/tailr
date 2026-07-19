#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


FAILURE_PATTERN = re.compile(r"BUILD FAILED|BUILD FAILURE|FAILED|ERROR|Exception|Traceback|quality gate|CVE-|GHSA-|[A-Za-z][A-Za-z0-9_-]*:S\d+", re.IGNORECASE)
FILE_LINE_PATTERN = re.compile(r"[\w./\\-]+\.(?:java|kt|js|jsx|ts|tsx|py|go|cs|rb|php|xml|yml|yaml|json|tf|sql)[:(]\d*")


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def unique(values: list[str], limit: int) -> list[str]:
    seen = set()
    result = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
        if len(result) >= limit:
            break
    return result


def extract(path: Path, label: str, max_lines: int) -> dict[str, Any]:
    lines = read_lines(path)
    evidence: list[str] = []
    files: list[str] = []
    for line in lines:
        stripped = line.strip()
        if FAILURE_PATTERN.search(stripped):
            evidence.append(stripped)
        files.extend(FILE_LINE_PATTERN.findall(stripped))
    return {
        "label": label,
        "source_file": path.as_posix(),
        "line_count": len(lines),
        "exact_evidence": unique(evidence, max_lines),
        "affected_files": unique(files, 16),
    }


def summarize(ci: Path | None, sonar: Path | None, max_lines: int) -> dict[str, Any]:
    sections = []
    if ci:
        sections.append(extract(ci, "ci", max_lines))
    if sonar:
        sections.append(extract(sonar, "sonar", max_lines))
    affected: list[str] = []
    evidence: list[str] = []
    for section in sections:
        affected.extend(section["affected_files"])
        evidence.extend(section["exact_evidence"])
    return {
        "type": "validation-summary",
        "sections": sections,
        "combined_exact_evidence": unique(evidence, max_lines * 2),
        "combined_affected_files": unique(affected, 24),
        "handoff": {
            "status": "review required" if evidence else "no exact failure detected",
            "validation_truth": "Only claim pass/fail for commands represented by the provided files.",
            "next_action": "Use exact evidence lines to choose the smallest remediation and rerun the relevant command.",
        },
    }


def markdown(report: dict[str, Any]) -> str:
    lines = ["# TailTrail Validation Summary", ""]
    for section in report["sections"]:
        lines.extend(
            [
                f"## {section['label'].upper()}",
                "",
                f"- Source file: `{section['source_file']}`",
                f"- Lines scanned: {section['line_count']}",
                "- Exact evidence:",
            ]
        )
        lines.extend(f"  - `{item}`" for item in section["exact_evidence"] or ["not detected"])
        lines.append("- Affected files:")
        lines.extend(f"  - `{item}`" for item in section["affected_files"] or ["not detected"])
        lines.append("")
    lines.extend(["## Combined Evidence", ""])
    lines.extend(f"- `{item}`" for item in report["combined_exact_evidence"] or ["not detected"])
    lines.extend(["", "## Combined Affected Files", ""])
    lines.extend(f"- `{item}`" for item in report["combined_affected_files"] or ["not detected"])
    lines.extend(
        [
            "",
            "## Handoff",
            "",
            f"- Status: {report['handoff']['status']}",
            f"- Validation truth: {report['handoff']['validation_truth']}",
            f"- Next action: {report['handoff']['next_action']}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Combine CI and Sonar summaries into a validation handoff.")
    parser.add_argument("--ci", type=Path, help="Local CI/build/test log file.")
    parser.add_argument("--sonar", type=Path, help="Local Sonar/static-analysis log file.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--max-lines", type=int, default=12, help="Maximum exact evidence lines per section.")
    args = parser.parse_args()

    if not args.ci and not args.sonar:
        parser.error("provide --ci, --sonar, or both")
    report = summarize(args.ci, args.sonar, args.max_lines)
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
