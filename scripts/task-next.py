#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SECONDS_PER_DAY = 24 * 60 * 60

# Keep these action ids aligned with scripts/task-start.py:next_actions().
ACTION_LABELS = {
    "start": "Start a new TailTrail task.",
    "review": "Review uncommitted changes.",
    "review-finding": "Address the top review finding.",
    "branch-review": "Review branch changes before PR.",
    "value-report": "Publish a local value report.",
    "harness-quick": "Run a quick Meta-Harness fit check.",
    "scan-approval": "Approve exactly one scan command, or decline scans.",
    "learning-approval": "Choose how to handle surfaced learnings.",
    "learning-review": "Review learning refresh actions.",
    "defer-heavy": "Make the workflow leaner.",
}


def run_git(root: Path, args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def newest(paths: list[Path]) -> Path | None:
    existing = [path for path in paths if path.is_file()]
    if not existing:
        return None
    return max(existing, key=lambda path: (path.stat().st_mtime, path.as_posix()))


def newest_plan(root: Path) -> tuple[Path | None, dict[str, Any]]:
    path = newest(sorted((root / ".tailtrail" / "task-starts").glob("*.json")))
    return (path, load_json(path) if path else {})


def git_state(root: Path) -> dict[str, Any]:
    inside_code, inside, _ = run_git(root, ["rev-parse", "--is-inside-work-tree"])
    if inside_code != 0 or inside != "true":
        return {"available": False, "uncommitted": [], "branch": None, "base": None, "head": None, "clean": True}

    status_code, status, _ = run_git(root, ["status", "--porcelain=v1", "-uall"])
    branch_code, branch, _ = run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    origin_code, _, _ = run_git(root, ["rev-parse", "--verify", "origin/main"])
    main_code, _, _ = run_git(root, ["rev-parse", "--verify", "main"])
    head_code, head, _ = run_git(root, ["log", "-1", "--format=%H"])
    base = "origin/main" if origin_code == 0 else "main" if main_code == 0 else None
    uncommitted = [line for line in status.splitlines() if line.strip()] if status_code == 0 else []
    return {
        "available": True,
        "uncommitted": uncommitted,
        "branch": branch if branch_code == 0 else None,
        "base": base,
        "head": head if head_code == 0 else None,
        "clean": not uncommitted,
    }


def artifact_newer(root: Path, plan_path: Path | None, patterns: list[str]) -> Path | None:
    if not plan_path:
        return None
    tailtrail = root / ".tailtrail"
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(tailtrail.glob(pattern))
    newer = [path for path in candidates if path.is_file() and path.stat().st_mtime > plan_path.stat().st_mtime]
    return newest(newer)


def review_finding_count(path: Path | None) -> int:
    if not path:
        return 0
    body = path.read_text(encoding="utf-8", errors="replace")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict):
        findings = data.get("findings")
        if isinstance(findings, list):
            return len(findings)
    counts = [int(value) for value in re.findall(r"\b(?:Critical|Warning|Info):\s*(\d+)", body)]
    if counts:
        return sum(counts)
    markers = [line for line in body.splitlines() if line.lower().startswith(("- severity:", "severity:"))]
    return len(markers)


def learning_refresh_status(root: Path, now: float | None = None) -> dict[str, Any]:
    path = root / ".tailtrail" / "learning-refresh-actions.json"
    if not path.is_file():
        return {"exists": False, "stale": False, "unresolved": False, "path": None}
    current = time.time() if now is None else now
    age_days = int((current - path.stat().st_mtime) // SECONDS_PER_DAY)
    data = load_json(path)
    actions = data.get("actions") if isinstance(data.get("actions"), list) else []
    unresolved = any(not bool(item.get("resolved")) for item in actions if isinstance(item, dict))
    return {"exists": True, "stale": age_days > 14, "unresolved": unresolved, "path": path.as_posix(), "age_days": age_days}


def plan_task_types(plan: dict[str, Any]) -> list[str]:
    for key in ("task_types", "task_type"):
        value = plan.get(key)
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            return [value]
    navigator = plan.get("navigator")
    if isinstance(navigator, dict):
        value = navigator.get("task_types")
        if isinstance(value, list):
            return [str(item) for item in value]
    return []


def primary(action: str, command: str, reason: str, confidence: str) -> dict[str, str]:
    return {
        "action": action,
        "label": ACTION_LABELS[action],
        "command": command,
        "reason": reason,
        "confidence": confidence,
    }


def branch_matches_base(branch: str | None, base: str | None) -> bool:
    if not branch:
        return True
    if not base:
        return branch in {"main", "master"}
    return branch == base or branch == base.split("/")[-1]


def choose_primary(root: Path, command_prefix: str, plan_path: Path | None, plan: dict[str, Any], git: dict[str, Any]) -> dict[str, str]:
    refresh = learning_refresh_status(root)
    review_artifact = artifact_newer(root, plan_path, ["review-*.md", "review-*.json"])
    scan_artifact = artifact_newer(root, plan_path, ["sonar-*.md", "quality-*.md", "vulnerability-*.md", "validation-*.md"])
    learning_artifact = artifact_newer(root, plan_path, ["learning-*.md", "learning-*.json", "outcome-events.jsonl"])
    has_plan = bool(plan_path)
    uncommitted = git.get("uncommitted") or []

    if not has_plan and not uncommitted:
        return primary("start", f'{command_prefix} start "<goal>"', "No prior Start plan or obvious task signal was found.", "low")
    if has_plan and uncommitted and not review_artifact:
        return primary("review", f"{command_prefix} review", "Prior Start plan exists and uncommitted changes are present with no newer review artifact.", "high")
    if has_plan and uncommitted and review_artifact and review_finding_count(review_artifact) > 0:
        return primary("review-finding", f"{command_prefix} review", "A review artifact newer than the Start plan has findings; address the top-severity finding first.", "high")
    approvals_pending = bool(plan.get("scan_approval") or plan.get("learning_approval"))
    if has_plan and git.get("clean") and not approvals_pending and not branch_matches_base(git.get("branch"), git.get("base")):
        base = git.get("base") or "main"
        return primary("branch-review", f"{command_prefix} review --scope branch --base {base}", "Working tree is clean and the current branch differs from the base branch.", "high")
    if has_plan and git.get("clean") and not approvals_pending and branch_matches_base(git.get("branch"), git.get("base")):
        task_types = set(plan_task_types(plan))
        if task_types & {"security", "release", "vulnerability", "regulated"}:
            return primary("harness-quick", f"{command_prefix} harness quick --root {json.dumps(root.as_posix())}", "The last plan was risk-sensitive; run a quick TailTrail fit check.", "medium")
        return primary("value-report", f"{command_prefix} report value --month YYYY-MM", "The last plan exists, the working tree is clean, and the branch matches the base.", "medium")
    if has_plan and plan.get("scan_approval") and not scan_artifact:
        return primary("scan-approval", "Review the Scan Approval section of the last Start report.", "The last plan has pending scan approval and no newer scan artifact was found.", "medium")
    if has_plan and plan.get("learning_approval") and not learning_artifact:
        return primary("learning-approval", "Review the Learning Approval section of the last Start report.", "The last plan surfaced learning approval and no newer learning event was found.", "medium")
    if refresh["exists"] and (refresh["stale"] or refresh["unresolved"]):
        return primary("learning-review", f"{command_prefix} learn review --root {json.dumps(root.as_posix())}", "Learning refresh actions exist and are stale or unresolved.", "medium")
    return primary("start", f'{command_prefix} start "<new goal>"', "No higher-confidence continuation signal matched.", "low")


def alternatives_for(primary_action: str, command_prefix: str) -> list[str]:
    options = [
        ("scan-approval", "Approve exactly one scan command, or decline scans."),
        ("learning-approval", "Choose how to handle surfaced learnings."),
        ("defer-heavy", "Make the workflow leaner if this is a narrow fix."),
        ("start", f'Start a new task with `{command_prefix} start "<goal>"`.'),
    ]
    return [text for action, text in options if action != primary_action][:3]


def build_report(root: Path, command_prefix: str) -> dict[str, Any]:
    resolved = root.resolve()
    plan_path, plan = newest_plan(resolved)
    git = git_state(resolved)
    review_artifact = artifact_newer(resolved, plan_path, ["review-*.md", "review-*.json"])
    refresh = learning_refresh_status(resolved)
    chosen = choose_primary(resolved, command_prefix, plan_path, plan, git)
    signals = {
        "last_plan": plan_path.as_posix() if plan_path else None,
        "git.available": git["available"],
        "git.uncommitted": len(git["uncommitted"]),
        "git.branch": git["branch"],
        "git.base": git["base"],
        "review_artifact_newer_than_plan": bool(review_artifact),
        "review_findings": review_finding_count(review_artifact),
        "scan_approval_pending": bool(plan.get("scan_approval")),
        "learning_approval_pending": bool(plan.get("learning_approval")),
        "learning_refresh_stale": bool(refresh["exists"] and refresh["stale"]),
        "learning_refresh_unresolved": bool(refresh["exists"] and refresh["unresolved"]),
        "code_graph_cache": (resolved / "tailtrail-meta" / "code-graph-cache.json").is_file(),
    }
    return {
        "schema_version": "1",
        "type": "tailtrail-next",
        "root": resolved.as_posix(),
        "primary": chosen,
        "alternatives": alternatives_for(chosen["action"], command_prefix),
        "signals": signals,
        "evidence": {
            "plan_path": signals["last_plan"],
            "review_artifact": review_artifact.as_posix() if review_artifact else None,
            "git_head": git.get("head"),
            "learning_refresh_path": refresh.get("path"),
        },
        "boundaries": [
            "Advisory only.",
            "TailTrail did not run scanners, edit files, run tests, mutate git, call network, or capture learning.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    primary_item = report["primary"]
    lines = [
        "# TailTrail Next Step",
        "",
        "## Next Step",
        f"- Action: {primary_item['action']}",
        f"- Command: `{primary_item['command']}`",
        f"- Reason: {primary_item['reason']}",
        f"- Confidence: {primary_item['confidence']}",
        "",
        "## Alternatives",
    ]
    for index, item in enumerate(report["alternatives"], start=1):
        lines.append(f"{index}. {item}")
    if not report["alternatives"]:
        lines.append("None.")
    lines.extend(["", "## Signals Considered"])
    for key, value in report["signals"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Boundaries"])
    for item in report["boundaries"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Recommend one deterministic next TailTrail action.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--command-prefix", default="python3 scripts/tailtrail.py")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    report = build_report(args.root, args.command_prefix)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
