"""Evidence and operational posture builders for TailTrail Start.

These helpers are deliberately side-effect free. They assemble local planning
metadata only; execution and report rendering remain in ``task-start.py``.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def approx_tokens(chars: int, chars_per_token: int) -> int:
    return math.ceil(chars / chars_per_token) if chars > 0 else 0


def file_chars(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return 0


def existing_file_tokens(root: Path, paths: list[str], chars_per_token: int) -> tuple[int, list[dict[str, Any]]]:
    total, files = 0, []
    for item in paths:
        path = root / item
        if not path.is_file():
            continue
        chars = file_chars(path)
        tokens = approx_tokens(chars, chars_per_token)
        total += tokens
        files.append({"path": item, "chars": chars, "approx_tokens": tokens})
    return total, files


def token_posture(root: Path, plan: dict[str, Any], large_context_files: tuple[str, ...], chars_per_token: int) -> dict[str, Any]:
    used_paths = list(dict.fromkeys(str(item["path"]) for item in plan.get("likely_impacted_files", []) if isinstance(item, dict) and item.get("path")))
    avoid_text = " ".join(str(item) for item in plan.get("avoid", []))
    avoided_paths = [item for item in large_context_files if item in avoid_text and (root / item).is_file()]
    used_tokens, used_files = existing_file_tokens(root, used_paths, chars_per_token)
    avoided_tokens, avoided_files = existing_file_tokens(root, avoided_paths, chars_per_token)
    baseline = used_tokens + avoided_tokens
    return {"mode": "local_estimate", "evidence": "Approximate file character count only. Do not claim exact model/API token savings.", "used_tokens": used_tokens, "avoided_tokens": avoided_tokens, "baseline_tokens": baseline, "estimated_saved_tokens": avoided_tokens, "estimated_reduction_percent": round((avoided_tokens / baseline) * 100, 2) if baseline else 0.0, "used_files": used_files, "avoided_files": avoided_files}


def setup_posture(root: Path, command_prefix: str, source_root: Path) -> dict[str, Any]:
    installed = (root / ".tailtrail-install.json").is_file() or bool(list(root.glob("*/.tailtrail-install.json")))
    packaged = (source_root / "package-integrity.json").is_file()
    return {"source_checkout": not packaged and (source_root / ".codex-plugin").exists(), "installed_package": packaged, "installed_pack_detected": installed, "recommended_check": f"{command_prefix} doctor", "recommended_update_check": f"{command_prefix} update --root {json.dumps(root.as_posix())} --dry-run" if installed else f"{command_prefix} install local --inspect", "note": "Run update checks as dry-run first. Preserve local edits unless the user approves backup-overwrite."}


def review_posture(plan: dict[str, Any], command_prefix: str) -> dict[str, Any]:
    review_plan = plan.get("review_plan") if isinstance(plan.get("review_plan"), dict) else {}
    names = {item.get("name") for item in plan.get("selected_features", []) if isinstance(item, dict)}
    return {"selected": bool({"Review Lens", "Navigator-Led Review", "QA / CI-Sonar Lens", "Security Review"} & names), "scope": str(review_plan.get("default") or "uncommitted changes"), "command": f"{command_prefix} review", "prompt": "After implementation and focused validation, run TailTrail review on the changed scope. Show severity, file, function, line, impact, fix, validation, confidence, and safe-fix status. Do not apply fixes without approval.", "rule": "Review checks code health and requirement fulfillment against the approved plan or user request."}


def harness_posture(root: Path, command_prefix: str) -> dict[str, Any]:
    shared_path = root / "tailtrail-meta" / "harness-summary.jsonl"
    return {"command": f"{command_prefix} harness quick --root {json.dumps(root.as_posix())}", "confidence_command": f"{command_prefix} harness confidence --root {json.dumps(root.as_posix())}", "shared_dry_run_command": f"{command_prefix} harness shared-summary --root {json.dumps(root.as_posix())} --dry-run", "shared_status_command": f"{command_prefix} harness shared-status --root {json.dumps(root.as_posix())}", "shared_metadata_exists": shared_path.is_file(), "rule": "Meta-Harness is post-task advisory. It reviews TailTrail behavior and can dry-run sanitized shared metadata; it does not upload, commit, or change rules automatically."}


def bootstrap_posture(plan: dict[str, Any], command_prefix: str) -> dict[str, Any]:
    snapshot = plan.get("bootstrap_snapshot") if isinstance(plan.get("bootstrap_snapshot"), dict) else None
    if not snapshot:
        return {"selected": False, "status": "skipped", "command": f"{command_prefix} bootstrap status --root .", "rule": "Bootstrap Snapshot is skipped for tiny or low-signal prompts."}
    return {"selected": True, "status": snapshot.get("status", "unknown"), "command": snapshot.get("command") or f"{command_prefix} bootstrap status --root .", "rule": "Bootstrap Snapshot captures safe repo/runtime facts before broad Navigator planning; it does not read source bodies or execute project code."}


def evaluation_posture(goal: str, plan: dict[str, Any], command_prefix: str, trigger_words: set[str]) -> dict[str, Any]:
    lowered_goal = goal.lower()
    task_types = {str(item).lower() for item in plan.get("task_types", [])}
    triggered_terms = sorted(word for word in trigger_words if word in lowered_goal)
    selected = bool(triggered_terms) or (bool({"review", "qa", "ci", "security"} & task_types) and any(word in lowered_goal for word in {"proof", "metrics", "evidence", "report"}))
    scenario = "dependency-decision" if "dependency" in lowered_goal else "review-only" if "review" in lowered_goal else "ci-failure" if "ci" in lowered_goal or "sonar" in lowered_goal else "security-triage" if "security" in lowered_goal or "vulnerability" in lowered_goal else "validation-bug"
    return {"selected": selected, "reason": "triggered by " + ", ".join(triggered_terms) if triggered_terms else "not selected for this task", "scenario": scenario, "list_command": f"{command_prefix} eval scenario list", "run_command": f"{command_prefix} eval scenario run --scenario {scenario}", "report_command": f"{command_prefix} eval scenario report --scenario {scenario}", "write_report_command": f"{command_prefix} eval scenario report --scenario {scenario} --write-result --approved", "normalize_command": f"{command_prefix} eval normalize --source benchmark --input benchmarks/evaluation/results/{scenario}-scenario-report.json --dry-run", "rule": "Evaluation Harness reads committed fixtures and compact evidence only. It does not run live agents, tests, CI, scanners, package managers, model/API calls, or hidden telemetry."}
