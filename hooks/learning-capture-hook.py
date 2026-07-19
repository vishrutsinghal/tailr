#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LEARNING_AGENT = ROOT / "scripts" / "learning-agent.py"
DEFAULT_STATE = ROOT / ".tailtrail" / "learning-capture-hook-state.json"

TASK_KEYWORDS = {
    "sonar": ["sonar", "static analysis", "quality gate", "rule"],
    "ci": ["ci", "pipeline", "build", "workflow", "job failed"],
    "security": ["security", "vulnerability", "cve", "ghsa", "secret", "sast"],
    "dependency": ["dependency", "package", "library", "upgrade", "version"],
    "bug": ["bug", "fix", "failure", "regression", "exception"],
    "feature": ["feature", "implement", "add support", "new field"],
    "review": ["review", "pr", "pull request"],
}

RISK_KEYWORDS = {
    "auth": ["auth", "authorization", "authentication", "permission"],
    "security": ["security", "vulnerability", "secret", "cve", "ghsa"],
    "dependency": ["dependency", "package", "library", "upgrade"],
    "payment": ["payment", "billing", "invoice"],
    "data": ["data", "database", "migration", "schema"],
    "release": ["release", "deploy", "production"],
}


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return sorted({item.strip() for item in value.split(",") if item.strip()})


def classify(text: str) -> tuple[str, list[str], str]:
    lowered = text.lower()
    task_type = "general"
    tags: list[str] = []
    for name, keywords in TASK_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            tags.append(name)
            if task_type == "general":
                task_type = name
    risk = "normal"
    for name, keywords in RISK_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            risk = name
            break
    return task_type, sorted(set(tags)), risk


def should_capture(summary: str, candidate: str, task_type: str, tags: list[str], force: bool) -> tuple[bool, str]:
    if force:
        return True, "forced by caller"
    if len(summary.split()) < 5:
        return False, "summary is too small to capture safely"
    if not candidate and task_type in {"general", "review"} and not tags:
        return False, "no reusable pattern, issue type, or tag was detected"
    if any(word in summary.lower() for word in ("typo", "formatting only", "comment only", "rename only")):
        return False, "tiny low-risk work should not create learning noise"
    return True, "meaningful reusable work detected"


def build_capture_command(args: argparse.Namespace, summary: str, task_type: str, tags: list[str], risk: str) -> list[str]:
    command = [
        sys.executable,
        LEARNING_AGENT.as_posix(),
        "capture",
        "--root",
        args.root.as_posix(),
        "--type",
        args.type or task_type,
        "--summary",
        summary,
        "--validation-outcome",
        args.validation_outcome,
        "--acceptance",
        args.acceptance,
        "--risk",
        args.risk or risk,
        "--sensitivity",
        args.sensitivity,
    ]
    merged_tags = sorted(set(tags + split_csv(args.tags)))
    if merged_tags:
        command.extend(["--tags", ",".join(merged_tags)])
    if args.prompt_summary:
        command.extend(["--prompt-summary", args.prompt_summary])
    if args.solution:
        command.extend(["--solution", args.solution])
    if args.candidate:
        command.extend(["--candidate", args.candidate])
    for file_path in args.file:
        command.extend(["--file", file_path])
    if args.issue_ids:
        command.extend(["--issue-ids", args.issue_ids])
    for validation_command in args.validation_command:
        command.extend(["--validation-command", validation_command])
    if args.reason:
        command.extend(["--reason", args.reason])
    for approved_change in args.approved_change:
        command.extend(["--approved-change", approved_change])
    for requested_change in args.requested_change:
        command.extend(["--requested-change", requested_change])
    for clarification in args.clarification:
        command.extend(["--clarification", clarification])
    if args.fulfillment_status:
        command.extend(["--fulfillment-status", args.fulfillment_status])
    if args.review_status:
        command.extend(["--review-status", args.review_status])
    if args.user_override:
        command.extend(["--user-override", args.user_override])
    if args.stale_when:
        command.extend(["--stale-when", args.stale_when])
    if args.reused_project_pattern:
        command.append("--reused-project-pattern")
    if args.small_focused_change:
        command.append("--small-focused-change")
    if args.no_new_dependency:
        command.append("--no-new-dependency")
    if args.dependency_gate_applied:
        command.append("--dependency-gate-applied")
    if args.scanner_resolved:
        command.append("--scanner-resolved")
    if args.guardrail_weakened:
        command.append("--guardrail-weakened")
    if args.promote_if_eligible:
        command.append("--promote-if-eligible")
    return command


def shell_preview(command: list[str]) -> str:
    preview: list[str] = []
    for item in command:
        item = str(item)
        if item == sys.executable:
            preview.append("python3")
        elif any(char.isspace() for char in item) or '"' in item:
            preview.append(json.dumps(item))
        else:
            preview.append(item)
    return " ".join(preview)


def write_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_capture(command: list[str]) -> tuple[int, str, str]:
    result = subprocess.run([str(item) for item in command], cwd=ROOT, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout, result.stderr


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Learning Capture Hook",
        "",
        f"- Action: `{payload['action']}`",
        f"- Reason: {payload['reason']}",
        f"- Type: `{payload['task_type']}`",
        f"- Risk: `{payload['risk']}`",
        f"- Tags: `{', '.join(payload['tags']) or 'none'}`",
        "",
    ]
    if payload["action"] == "suggest":
        lines.extend(
            [
                "Suggested capture command:",
                "",
                "```bash",
                payload["capture_command"],
                "```",
                "",
                "Review before running. Add `--approved` to this hook only when the user agrees to record the event.",
            ]
        )
    elif payload["action"] == "captured":
        lines.extend(["Captured event output:", "", payload.get("capture_output", "").strip()])
    else:
        lines.append("No learning event was captured.")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Suggest or capture TailTrail learning events from post-task summaries.")
    parser.add_argument("summary", nargs="*", help="Compact post-task summary.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target project root for learning files.")
    parser.add_argument("--type", help="Task type override.")
    parser.add_argument("--tags", help="Comma-separated tags.")
    parser.add_argument("--prompt-summary", help="Prompt summary, not raw prompt.")
    parser.add_argument("--solution", help="Compact solution summary.")
    parser.add_argument("--candidate", help="Reusable learning candidate.")
    parser.add_argument("--file", action="append", default=[], help="Touched file or module.")
    parser.add_argument("--issue-ids", help="Comma-separated ticket, rule, or scanner IDs.")
    parser.add_argument("--validation-command", action="append", default=[], help="Validation command that was run.")
    parser.add_argument("--validation-outcome", choices=("pass", "fail", "partial", "skipped", "not-run", "unknown"), default="unknown")
    parser.add_argument("--acceptance", choices=("accepted", "rejected", "revised", "partially-accepted", "unknown"), default="unknown")
    parser.add_argument("--reason", help="Explicit acceptance/rejection reason.")
    parser.add_argument("--approved-change", action="append", default=[], help="Compact summary of an approved implementation detail.")
    parser.add_argument("--requested-change", action="append", default=[], help="Compact summary of a user/reviewer requested change.")
    parser.add_argument("--clarification", action="append", default=[], help="Compact clarification that resolved implementation ambiguity.")
    parser.add_argument("--fulfillment-status", choices=("appears-aligned", "partially-aligned", "needs-clarification", "not-evaluated"))
    parser.add_argument("--risk", help="Risk override.")
    parser.add_argument("--sensitivity", choices=("normal", "internal", "sensitive"), default="normal")
    parser.add_argument("--review-status", choices=("approved", "changes-requested", "none"))
    parser.add_argument("--user-override", choices=("none", "proceed-anyway", "record-low-confidence-event"))
    parser.add_argument("--stale-when")
    parser.add_argument("--reused-project-pattern", action="store_true")
    parser.add_argument("--small-focused-change", action="store_true")
    parser.add_argument("--no-new-dependency", action="store_true")
    parser.add_argument("--dependency-gate-applied", action="store_true")
    parser.add_argument("--scanner-resolved", action="store_true")
    parser.add_argument("--guardrail-weakened", action="store_true")
    parser.add_argument("--promote-if-eligible", action="store_true")
    parser.add_argument("--force", action="store_true", help="Suggest capture even when heuristics would skip.")
    parser.add_argument("--approved", action="store_true", help="Actually capture the event.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--no-state", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = " ".join(args.summary).strip()
    if not summary:
        raise SystemExit("learning-capture-hook requires a compact post-task summary")

    inferred_type, inferred_tags, inferred_risk = classify(summary)
    task_type = args.type or inferred_type
    risk = args.risk or inferred_risk
    capture, reason = should_capture(summary, args.candidate or "", task_type, inferred_tags, args.force)
    command = build_capture_command(args, summary, task_type, inferred_tags, risk)
    payload: dict[str, Any] = {
        "kind": "learning-capture-hook",
        "action": "suggest" if capture else "skip",
        "reason": reason,
        "summary": summary,
        "task_type": task_type,
        "risk": risk,
        "tags": sorted(set(inferred_tags + split_csv(args.tags))),
        "capture_command": shell_preview(command),
        "approved": args.approved,
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }

    exit_code = 0
    if capture and args.approved:
        code, stdout, stderr = run_capture(command)
        exit_code = code
        payload["action"] = "captured" if code == 0 else "capture-failed"
        payload["capture_output"] = stdout
        payload["capture_error"] = stderr

    if not args.no_state:
        write_state(args.state, payload)

    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_markdown(payload))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
