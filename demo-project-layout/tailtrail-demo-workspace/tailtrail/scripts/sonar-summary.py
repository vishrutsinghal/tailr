#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


RULE_PATTERN = re.compile(r"\b([A-Za-z][A-Za-z0-9_-]*:S\d+)\b")
SEVERITY_PATTERN = re.compile(r"\b(BLOCKER|CRITICAL|MAJOR|MINOR|INFO)\b", re.IGNORECASE)
QUALITY_GATE_PATTERN = re.compile(r"quality gate|gate status|failed conditions?", re.IGNORECASE)
FILE_LINE_PATTERN = re.compile(r"(?P<path>[\w./\\-]+\.(?:java|kt|js|jsx|ts|tsx|py|go|cs|rb|php|xml|yml|yaml|json|tf|sql))[:(](?P<line>\d+)?")
SONAR_LINE_PATTERN = re.compile(r"sonar|quality gate|issue|rule|severity|code smell|bug|vulnerab|hotspot", re.IGNORECASE)


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


def summarize(path: Path, max_lines: int) -> dict[str, Any]:
    lines = read_lines(path)
    rules: list[str] = []
    severities: list[str] = []
    gate_lines: list[str] = []
    finding_lines: list[str] = []
    files: list[str] = []

    for line in lines:
        stripped = line.strip()
        rules.extend(RULE_PATTERN.findall(stripped))
        severities.extend(match.upper() for match in SEVERITY_PATTERN.findall(stripped))
        if QUALITY_GATE_PATTERN.search(stripped):
            gate_lines.append(stripped)
        if RULE_PATTERN.search(stripped) or QUALITY_GATE_PATTERN.search(stripped) or (SONAR_LINE_PATTERN.search(stripped) and (FILE_LINE_PATTERN.search(stripped) or SEVERITY_PATTERN.search(stripped))):
            finding_lines.append(stripped)
        file_match = FILE_LINE_PATTERN.search(stripped)
        if file_match:
            files.append(file_match.group(0))

    exact_findings = unique(gate_lines + finding_lines, max_lines)
    return {
        "type": "sonar-summary",
        "source_file": path.as_posix(),
        "line_count": len(lines),
        "quality_gate_lines": unique(gate_lines, max_lines),
        "rules": unique(rules, 16),
        "severities": unique(severities, 8),
        "affected_files": unique(files, 16),
        "first_relevant_findings": exact_findings,
        "next_actions": next_actions(exact_findings, rules, files),
        "notes": [
            "Exact rule IDs, gate lines, severities, and paths are preserved when detected.",
            "This does not query SonarQube or SonarCloud; it summarizes provided local text only.",
        ],
    }


def next_actions(findings: list[str], rules: list[str], files: list[str]) -> list[str]:
    actions = []
    if findings:
        actions.append("Start with the first quality gate or rule finding; later findings may be duplicates or cascades.")
    if rules:
        actions.append("Preserve the exact Sonar rule ID when planning the fix.")
    if files:
        actions.append("Read affected files and nearby tests before changing code.")
    if not actions:
        actions.append("No clear Sonar finding was detected; review the original report for rule IDs, affected files, or quality gate details.")
    return actions


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Sonar Summary",
        "",
        f"- Source file: `{report['source_file']}`",
        f"- Lines scanned: {report['line_count']}",
        "",
        "## Quality Gate Lines",
        "",
    ]
    lines.extend(f"- `{item}`" for item in report["quality_gate_lines"] or ["not detected"])
    lines.extend(["", "## Rule IDs", ""])
    lines.extend(f"- `{item}`" for item in report["rules"] or ["not detected"])
    lines.extend(["", "## Severities", ""])
    lines.extend(f"- `{item}`" for item in report["severities"] or ["not detected"])
    lines.extend(["", "## Affected Files", ""])
    lines.extend(f"- `{item}`" for item in report["affected_files"] or ["not detected"])
    lines.extend(["", "## First Relevant Findings", ""])
    lines.extend(f"- `{item}`" for item in report["first_relevant_findings"] or ["not detected"])
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {item}" for item in report["next_actions"])
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {item}" for item in report["notes"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Sonar/static-analysis output without losing exact rule evidence.")
    parser.add_argument("--file", type=Path, required=True, help="Local Sonar/static-analysis text file.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--max-lines", type=int, default=12, help="Maximum exact finding lines to include.")
    args = parser.parse_args()

    report = summarize(args.file, args.max_lines)
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
