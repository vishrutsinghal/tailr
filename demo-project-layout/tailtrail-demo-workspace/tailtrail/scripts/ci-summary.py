#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


FAILURE_PATTERNS = (
    "BUILD FAILED",
    "BUILD FAILURE",
    "FAILURE",
    "FAILED",
    "ERROR",
    "Exception",
    "Traceback",
    "AssertionError",
    "Compilation failure",
    "There were failing tests",
    "Tests run:",
)

COMMAND_PATTERN = re.compile(
    r"^\s*(\$|>|Run |Running |Executing )?\s*(mvn|gradle|\.\/gradlew|npm|yarn|pnpm|python|python3|pytest|tox|dotnet|go|make|cargo)\b.*"
)
STAGE_PATTERN = re.compile(r"^\s*(stage|job|step|task|workflow|pipeline)\s*[:=-]\s*(.+)$", re.IGNORECASE)
FILE_LINE_PATTERN = re.compile(r"(?P<path>[\w./\\-]+\.(?:java|kt|js|jsx|ts|tsx|py|go|cs|rb|php|xml|yml|yaml|json|tf|sql))[:(](?P<line>\d+)?")
TEST_PATTERN = re.compile(r"(?:(?:FAIL|FAILED|ERROR)\s+)?(?P<test>[A-Za-z_][\w.$#-]*(?:Test|Spec|Tests)[\w.$#-]*)")


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
    commands: list[str] = []
    stages: list[str] = []
    failures: list[str] = []
    files: list[str] = []
    tests: list[str] = []

    for line in lines:
        stripped = line.strip()
        if COMMAND_PATTERN.search(stripped):
            commands.append(stripped)
        stage_match = STAGE_PATTERN.search(stripped)
        if stage_match:
            stages.append(stripped)
        if any(pattern.lower() in stripped.lower() for pattern in FAILURE_PATTERNS):
            failures.append(stripped)
        file_match = FILE_LINE_PATTERN.search(stripped)
        if file_match:
            files.append(file_match.group(0))
        test_match = TEST_PATTERN.search(stripped)
        if test_match and any(word in stripped.lower() for word in ("fail", "error", "failed")):
            tests.append(test_match.group("test"))

    first_failure = unique(failures, max_lines)
    return {
        "type": "ci-summary",
        "source_file": path.as_posix(),
        "line_count": len(lines),
        "commands": unique(commands, 8),
        "stages": unique(stages, 8),
        "first_relevant_failures": first_failure,
        "failing_tests": unique(tests, 8),
        "affected_files": unique(files, 12),
        "next_actions": next_actions(first_failure, files, tests),
        "notes": [
            "Exact failure lines, commands, paths, and test names are preserved when detected.",
            "This summary is heuristic and should be checked against the original log before remediation.",
        ],
    }


def next_actions(failures: list[str], files: list[str], tests: list[str]) -> list[str]:
    actions = []
    if failures:
        actions.append("Inspect the first relevant failure before later cascading errors.")
    if files:
        actions.append("Read the affected file paths and nearby tests before changing code.")
    if tests:
        actions.append("Run the named failing test or the smallest project-owned test command after the fix.")
    if not actions:
        actions.append("No clear failure line was detected; review the original log around the failing job or final non-zero exit.")
    return actions


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail CI Summary",
        "",
        f"- Source file: `{report['source_file']}`",
        f"- Lines scanned: {report['line_count']}",
        "",
        "## Commands",
        "",
    ]
    lines.extend(f"- `{item}`" for item in report["commands"] or ["not detected"])
    lines.extend(["", "## Stages", ""])
    lines.extend(f"- {item}" for item in report["stages"] or ["not detected"])
    lines.extend(["", "## First Relevant Failures", ""])
    lines.extend(f"- `{item}`" for item in report["first_relevant_failures"] or ["not detected"])
    lines.extend(["", "## Failing Tests", ""])
    lines.extend(f"- `{item}`" for item in report["failing_tests"] or ["not detected"])
    lines.extend(["", "## Affected Files", ""])
    lines.extend(f"- `{item}`" for item in report["affected_files"] or ["not detected"])
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {item}" for item in report["next_actions"])
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {item}" for item in report["notes"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize CI, build, test, or pipeline output without losing exact failures.")
    parser.add_argument("--file", type=Path, required=True, help="Local CI/build/test log file.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--max-lines", type=int, default=12, help="Maximum exact failure lines to include.")
    args = parser.parse_args()

    report = summarize(args.file, args.max_lines)
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
