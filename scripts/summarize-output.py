#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


COMMAND_PATTERN = re.compile(r"^\s*(?:\$|>|Run |Running |Executing )\s*([\w./-]+)(?:\s+.*)?$")
BARE_COMMAND_PATTERN = re.compile(r"^\s*(?:python3?|mvn|gradle|./gradlew|npm|yarn|pnpm|pytest|dotnet|sonar-scanner|trivy|semgrep|make)\b(?:\s+.*)?$")
PATH_PATTERN = re.compile(r"[\w./\\-]+\.(?:java|kt|js|jsx|ts|tsx|py|go|cs|rb|php|xml|yml|yaml|json|tf|sql|lock|toml|gradle|csproj|sln)(?::\d+)?")
IMPORTANT_PATTERN = re.compile(
    r"fail|failed|failure|error|exception|traceback|assertion|warning|quality gate|sonar|cve-|ghsa-|vulnerab|secret|critical|high|medium|low|rule|severity",
    re.IGNORECASE,
)
SENSITIVE_PATTERN = re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|authorization|bearer)\s*[:=]\s*\S+")


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def redact(line: str) -> str:
    return SENSITIVE_PATTERN.sub("[REDACTED]", line)


def unique(values: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = redact(value.strip())
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
    important: list[str] = []
    files: list[str] = []
    for line in lines:
        stripped = line.strip()
        if COMMAND_PATTERN.search(stripped) or BARE_COMMAND_PATTERN.search(stripped):
            commands.append(stripped)
        if IMPORTANT_PATTERN.search(stripped):
            important.append(stripped)
        files.extend(match.group(0) for match in PATH_PATTERN.finditer(stripped))
    return {
        "type": "output-summary",
        "source_file": path.as_posix(),
        "line_count": len(lines),
        "commands": unique(commands, 10),
        "important_lines": unique(important, max_lines),
        "affected_files": unique(files, 24),
        "recommended_next_steps": next_steps(important, files),
        "notes": [
            "This is a compact local text summary; verify against the original output before remediation.",
            "Potential secrets in key/value or bearer-token shapes are redacted.",
            "Use CI, Sonar, or vulnerability-specific summarizers when the output type is known.",
        ],
    }


def next_steps(important: list[str], files: list[str]) -> list[str]:
    steps: list[str] = []
    if important:
        steps.append("Start from the first preserved important line before later cascading output.")
    if files:
        steps.append("Read affected files and nearby tests before editing.")
    if not important and not files:
        steps.append("No obvious failure or affected file was detected; inspect the original output around the final non-zero exit.")
    return steps


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Output Summary",
        "",
        f"- Source file: `{report['source_file']}`",
        f"- Lines scanned: `{report['line_count']}`",
        "",
        "## Commands",
        "",
    ]
    lines.extend(f"- `{item}`" for item in report["commands"] or ["not detected"])
    lines.extend(["", "## Important Lines", ""])
    lines.extend(f"- `{item}`" for item in report["important_lines"] or ["not detected"])
    lines.extend(["", "## Affected Files", ""])
    lines.extend(f"- `{item}`" for item in report["affected_files"] or ["not detected"])
    lines.extend(["", "## Recommended Next Steps", ""])
    lines.extend(f"- {item}" for item in report["recommended_next_steps"])
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {item}" for item in report["notes"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize noisy local command output into compact evidence.")
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--max-lines", type=int, default=24)
    args = parser.parse_args()
    report = summarize(args.file, max(args.max_lines, 1))
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
