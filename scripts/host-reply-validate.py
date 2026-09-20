#!/usr/bin/env python3
"""Score a host chat reply against TailTrail command stdout.

A compliant host reply copies the tool/CLI output verbatim into the normal
assistant message and stops: same first line, same run ID, same headings,
same fenced blocks, nothing added, nothing removed. Every violation names
the core instruction bullet it breaks so instruction edits can be judged
against golden fixtures instead of hope.

Usage:
    python3 scripts/host-reply-validate.py score --report <stdout-file>
        --reply <reply-file> [--format markdown|json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# Core-bullet references attached to each violation code.
RULES = {
    "report-start": "Start response boundary: the normal assistant message starts with the report stdout itself, outside any panel, with no preamble or narration.",
    "run-id-missing": "Run-ID discipline: the reply must contain the run ID from the Start Report.",
    "lock-claimed": "Scope-quality boundary: never claim a run ID or Planning Lock the report did not create.",
    "heading-dropped": "Selected-features table and required sections are mandatory and may not be renamed or replaced.",
    "fence-altered": "Preserve the command-emitted fenced banner, table pipes, backticks, and spacing; never retype or normalize.",
    "content-added": "Return the report verbatim and stop: no implementation plan, steps, analysis, or guidance after it.",
    "content-removed": "Copy the complete report: no summarizing, trimming, or rewording.",
    "official-questions-missing": "Official exception: for an official run, never end the turn at the Start Report — generate and record the questions, then return the Requirements report in the same turn.",
}

RUN_ID_PATTERN = re.compile(r"^- Run ID: `([^`]+)`", re.MULTILINE)
HEADING_PATTERN = re.compile(r"^(#{1,3} .+?)\s*$", re.MULTILINE)
FENCE_PATTERN = re.compile(r"^```.*$", re.MULTILINE)
RUN_ID_CLAIM_PATTERN = re.compile(r"run.?id\s*:", re.IGNORECASE)
# Rendered stdout never prints the state id; the generation-required report
# is recognized by its directives to the host.
OFFICIAL_GENERATION_MARKER = "must load the recorded official rules"
OFFICIAL_REPORT_MARKER = "Official AI-DLC Requirements"


def _lines(text: str) -> list[str]:
    return text.strip("\n").splitlines()


def detect_kind(stdout: str) -> str:
    first = stdout.lstrip().splitlines()
    head = "\n".join(first[:20])
    if "Hello from TailTrail" in head:
        return "hello"
    return "start"


def run_id_of(stdout: str) -> str | None:
    match = RUN_ID_PATTERN.search(stdout)
    return match.group(1) if match else None


def validate_host_reply(stdout: str, reply: str) -> list[dict[str, str]]:
    """Return one violation dict per broken rule; empty means verbatim."""
    violations: list[dict[str, str]] = []

    def add(code: str, detail: str) -> None:
        violations.append({"code": code, "rule": RULES[code], "detail": detail})

    stdout_lines = _lines(stdout)
    reply_lines = _lines(reply)
    if not stdout_lines:
        return [{"code": "empty-report", "rule": "No report to copy.", "detail": "stdout is empty"}]
    if not reply_lines:
        add("content-removed", "reply is empty; the complete report is missing")
        return violations

    official_required = OFFICIAL_GENERATION_MARKER in stdout
    if official_required and OFFICIAL_REPORT_MARKER not in reply:
        add(
            "official-questions-missing",
            "official run ended at the Start Report without the Official AI-DLC Requirements report",
        )
    # For official runs the Requirements report is appended after the Start
    # stdout; verbatim checks apply to the pre-report lines only.
    if official_required:
        pre_lines = []
        for line in reply_lines:
            if OFFICIAL_REPORT_MARKER in line:
                break
            pre_lines.append(line)
        verbatim_lines = pre_lines
    else:
        verbatim_lines = reply_lines

    if reply_lines[0].strip() != stdout_lines[0].strip():
        add(
            "report-start",
            f"reply starts with {reply_lines[0][:80]!r} instead of {stdout_lines[0][:80]!r}",
        )

    expected_run_id = run_id_of(stdout)
    if expected_run_id is not None:
        if expected_run_id not in reply:
            add("run-id-missing", f"run ID `{expected_run_id}` from the report is absent")
    elif RUN_ID_CLAIM_PATTERN.search(reply) and not RUN_ID_CLAIM_PATTERN.search(stdout):
        add("lock-claimed", "reply claims a run ID the report never created")

    for heading in HEADING_PATTERN.findall(stdout):
        if heading not in reply:
            add("heading-dropped", f"required section missing: {heading[:80]}")

    stdout_fences = FENCE_PATTERN.findall(stdout)
    reply_fences = FENCE_PATTERN.findall(reply)
    if len(reply_fences) != len(stdout_fences) or any(
        fence not in reply for fence in stdout_fences
    ):
        add(
            "fence-altered",
            f"report has {len(stdout_fences)} fenced markers, reply has {len(reply_fences)}",
        )

    stdout_set = set(stdout_lines)
    added = [line for line in verbatim_lines if line not in stdout_set]
    meaningful_added = [line for line in added if line.strip()]
    if meaningful_added:
        shown = "; ".join(line.strip()[:60] for line in meaningful_added[:3])
        add("content-added", f"{len(meaningful_added)} non-report line(s): {shown}")

    reply_set = set(verbatim_lines)
    removed = [line for line in stdout_lines if line not in reply_set]
    meaningful_removed = [line for line in removed if line.strip()]
    if meaningful_removed:
        shown = "; ".join(line.strip()[:60] for line in meaningful_removed[:3])
        add("content-removed", f"{len(meaningful_removed)} report line(s) missing: {shown}")

    return violations


def score_payload(stdout: str, reply: str) -> dict[str, object]:
    violations = validate_host_reply(stdout, reply)
    return {
        "type": "tailtrail-host-reply-score",
        "schema_version": "1",
        "kind": detect_kind(stdout),
        "run_id": run_id_of(stdout),
        "compliant": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def render_markdown(payload: dict[str, object]) -> str:
    lines = ["# TailTrail Host-Reply Score", ""]
    lines.append(f"- Compliant: `{str(bool(payload['compliant'])).lower()}`")
    lines.append(f"- Violations: `{payload['violation_count']}`")
    for violation in payload["violations"]:
        assert isinstance(violation, dict)
        # Console encodings (e.g. Windows cp1252) cannot print every rune a
        # host may paste; keep the terminal render ASCII-safe. The JSON
        # payload retains the exact detail.
        detail = str(violation["detail"]).encode("ascii", "backslashreplace").decode("ascii")
        lines.append(f"- `{violation['code']}`: {detail}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Score a host reply against TailTrail stdout.")
    parser.add_argument("action", choices=["score"])
    parser.add_argument("--report", required=True, help="File holding the tool/CLI stdout.")
    parser.add_argument("--reply", required=True, help="File holding the host chat reply.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    stdout = Path(args.report).read_text(encoding="utf-8")
    reply = Path(args.reply).read_text(encoding="utf-8")
    payload = score_payload(stdout, reply)
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_markdown(payload), end="")
    return 0 if payload["compliant"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
