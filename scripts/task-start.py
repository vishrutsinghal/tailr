#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
NAVIGATOR_PATH = ROOT / "scripts" / "navigator.py"
SPEC = importlib.util.spec_from_file_location("tailtrail_navigator", NAVIGATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("Unable to load scripts/navigator.py")
navigator = importlib.util.module_from_spec(SPEC)
sys.modules["tailtrail_navigator"] = navigator
SPEC.loader.exec_module(navigator)

APPROX_CHARS_PER_TOKEN = 4
LARGE_CONTEXT_FILES = (
    "ROADMAP.md",
    "USER-GUIDE.md",
    "ENTERPRISE-REVIEW.md",
    "DESIGN.md",
    "TOKEN-SLICER.md",
)
EVALUATION_TRIGGER_WORDS = {
    "benchmark",
    "demo",
    "evidence",
    "eval",
    "evaluation",
    "harness",
    "metric",
    "metrics",
    "pitch",
    "proof",
    "regression",
    "report",
    "scenario",
}


def approx_tokens(chars: int) -> int:
    if chars <= 0:
        return 0
    return math.ceil(chars / APPROX_CHARS_PER_TOKEN)


def file_chars(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return 0


def existing_file_tokens(root: Path, paths: list[str]) -> tuple[int, list[dict[str, Any]]]:
    total = 0
    files: list[dict[str, Any]] = []
    for item in paths:
        path = root / item
        if not path.is_file():
            continue
        chars = file_chars(path)
        tokens = approx_tokens(chars)
        total += tokens
        files.append({"path": item, "chars": chars, "approx_tokens": tokens})
    return total, files


def avoided_context_from_plan(root: Path, plan: dict[str, Any]) -> list[str]:
    avoid_text = " ".join(str(item) for item in plan.get("avoid", []))
    avoided = [item for item in LARGE_CONTEXT_FILES if item in avoid_text and (root / item).is_file()]
    return avoided


def likely_used_files(plan: dict[str, Any]) -> list[str]:
    files = []
    for item in plan.get("likely_impacted_files", []):
        if isinstance(item, dict) and item.get("path"):
            files.append(str(item["path"]))
    return list(dict.fromkeys(files))


def token_posture(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    used_paths = likely_used_files(plan)
    avoided_paths = avoided_context_from_plan(root, plan)
    used_tokens, used_files = existing_file_tokens(root, used_paths)
    avoided_tokens, avoided_files = existing_file_tokens(root, avoided_paths)
    baseline = used_tokens + avoided_tokens
    saved = avoided_tokens
    reduction = round((saved / baseline) * 100, 2) if baseline else 0.0
    return {
        "mode": "local_estimate",
        "evidence": "Approximate file character count only. Do not claim exact model/API token savings.",
        "used_tokens": used_tokens,
        "avoided_tokens": avoided_tokens,
        "baseline_tokens": baseline,
        "estimated_saved_tokens": saved,
        "estimated_reduction_percent": reduction,
        "used_files": used_files,
        "avoided_files": avoided_files,
    }


def learning_quality(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    tailtrail = root / ".tailtrail"
    events = tailtrail / "learning-events.jsonl"
    index = tailtrail / "learning-index.md"
    refresh_actions = tailtrail / "learning-refresh-actions.json"
    matches = []
    graph_learning = plan.get("graph_learning")
    if isinstance(graph_learning, dict):
        raw_matches = graph_learning.get("matches", [])
        if isinstance(raw_matches, list):
            matches = raw_matches[:3]
    action_count = 0
    blocking_actions = 0
    if refresh_actions.is_file():
        try:
            data = json.loads(refresh_actions.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        raw_actions = data.get("actions", []) if isinstance(data, dict) else []
        if isinstance(raw_actions, list):
            action_count = sum(1 for item in raw_actions if isinstance(item, dict))
            blocking_actions = sum(
                1
                for item in raw_actions
                if isinstance(item, dict) and item.get("action") in {"mark-stale", "suppress", "archive", "delete"}
            )
    review_recommended = False
    review_reason = "no learning index or events detected"
    if index.is_file() and events.is_file() and not refresh_actions.is_file():
        review_recommended = True
        review_reason = "learning index and events exist but no refresh actions have been recorded"
    elif blocking_actions:
        review_recommended = True
        review_reason = "blocking learning refresh actions exist and should be checked before reuse"
    elif matches and not refresh_actions.is_file():
        review_recommended = True
        review_reason = "learning matches surfaced without a refresh-action history"
    return {
        "index_exists": index.is_file(),
        "events_exist": events.is_file(),
        "refresh_actions_exist": refresh_actions.is_file(),
        "refresh_action_count": action_count,
        "blocking_refresh_actions": blocking_actions,
        "surfaced_matches": len(matches),
        "approval_required": bool(plan.get("learning_approval")),
        "review_recommended": review_recommended,
        "review_reason": review_reason,
        "review_command": "python3 scripts/tailtrail.py learn review --root .",
        "rule": "Learnings are advisory only. Use, ignore, or edit surfaced learnings before implementation.",
    }


def setup_posture(root: Path, command_prefix: str) -> dict[str, Any]:
    source_checkout = (ROOT / ".codex-plugin").exists()
    installed_manifest = root / ".tailtrail-install.json"
    nested_manifests = sorted(root.glob("*/.tailtrail-install.json"))
    installed = installed_manifest.is_file() or bool(nested_manifests)
    if installed:
        update_command = f"{command_prefix} update --root {json.dumps(root.as_posix())} --dry-run"
    else:
        update_command = f"{command_prefix} install local --inspect"
    return {
        "source_checkout": source_checkout,
        "installed_pack_detected": installed,
        "recommended_check": f"{command_prefix} doctor",
        "recommended_update_check": update_command,
        "note": "Run update checks as dry-run first. Preserve local edits unless the user approves backup-overwrite.",
    }


def review_posture(plan: dict[str, Any], command_prefix: str) -> dict[str, Any]:
    review_plan = plan.get("review_plan") if isinstance(plan.get("review_plan"), dict) else {}
    selected = plan.get("selected_features", [])
    selected_names = {item.get("name") for item in selected if isinstance(item, dict)}
    review_selected = bool({"Review Lens", "Navigator-Led Review", "QA / CI-Sonar Lens", "Security Review"} & selected_names)
    scope = str(review_plan.get("default") or "uncommitted changes")
    return {
        "selected": review_selected,
        "scope": scope,
        "command": f"{command_prefix} review",
        "prompt": "After implementation and focused validation, run TailTrail review on the changed scope. Show severity, file, function, line, impact, fix, validation, confidence, and safe-fix status. Do not apply fixes without approval.",
        "rule": "Review checks code health and requirement fulfillment against the approved plan or user request.",
    }


def harness_posture(root: Path, command_prefix: str) -> dict[str, Any]:
    shared_path = root / "tailtrail-meta" / "harness-summary.jsonl"
    return {
        "command": f"{command_prefix} harness quick --root {json.dumps(root.as_posix())}",
        "confidence_command": f"{command_prefix} harness confidence --root {json.dumps(root.as_posix())}",
        "shared_dry_run_command": f"{command_prefix} harness shared-summary --root {json.dumps(root.as_posix())} --dry-run",
        "shared_status_command": f"{command_prefix} harness shared-status --root {json.dumps(root.as_posix())}",
        "shared_metadata_exists": shared_path.is_file(),
        "rule": "Meta-Harness is post-task advisory. It reviews TailTrail behavior and can dry-run sanitized shared metadata; it does not upload, commit, or change rules automatically.",
    }


def bootstrap_posture(plan: dict[str, Any], command_prefix: str) -> dict[str, Any]:
    snapshot = plan.get("bootstrap_snapshot") if isinstance(plan.get("bootstrap_snapshot"), dict) else None
    if not snapshot:
        return {
            "selected": False,
            "status": "skipped",
            "command": f"{command_prefix} bootstrap status --root .",
            "rule": "Bootstrap Snapshot is skipped for tiny or low-signal prompts.",
        }
    return {
        "selected": True,
        "status": snapshot.get("status", "unknown"),
        "command": snapshot.get("command") or f"{command_prefix} bootstrap status --root .",
        "rule": "Bootstrap Snapshot captures safe repo/runtime facts before broad Navigator planning; it does not read source bodies or execute project code.",
    }


def evaluation_posture(goal: str, plan: dict[str, Any], command_prefix: str) -> dict[str, Any]:
    lowered_goal = goal.lower()
    task_types = {str(item).lower() for item in plan.get("task_types", [])}
    triggered_terms = sorted(word for word in EVALUATION_TRIGGER_WORDS if word in lowered_goal)
    selected_by_goal = bool(triggered_terms)
    selected_by_task = bool({"review", "qa", "ci", "security"} & task_types) and any(word in lowered_goal for word in {"proof", "metrics", "evidence", "report"})
    selected = selected_by_goal or selected_by_task
    scenario = "validation-bug"
    if "dependency" in lowered_goal:
        scenario = "dependency-decision"
    elif "review" in lowered_goal:
        scenario = "review-only"
    elif "ci" in lowered_goal or "sonar" in lowered_goal:
        scenario = "ci-failure"
    elif "security" in lowered_goal or "vulnerability" in lowered_goal:
        scenario = "security-triage"
    return {
        "selected": selected,
        "reason": "triggered by " + ", ".join(triggered_terms) if triggered_terms else "not selected for this task",
        "scenario": scenario,
        "list_command": f"{command_prefix} eval scenario list",
        "run_command": f"{command_prefix} eval scenario run --scenario {scenario}",
        "report_command": f"{command_prefix} eval scenario report --scenario {scenario}",
        "write_report_command": f"{command_prefix} eval scenario report --scenario {scenario} --write-result --approved",
        "normalize_command": f"{command_prefix} eval normalize --source benchmark --input benchmarks/evaluation/results/{scenario}-scenario-report.json --dry-run",
        "rule": "Evaluation Harness reads committed fixtures and compact evidence only. It does not run live agents, tests, CI, scanners, package managers, model/API calls, or hidden telemetry.",
    }


def code_intelligence_policy(command_prefix: str) -> dict[str, Any]:
    return {
        "default": "local-only",
        "default_engine_path": ["lite", "v1", "v2"],
        "default_command": f"{command_prefix} graph ast --changed path/to/file --depth v1",
        "v2_command": f"{command_prefix} graph ast --changed path/to/file --depth v2",
        "v3_command": f"{command_prefix} graph ast --changed path/to/file --depth v3 --provider-output tailtrail-meta/providers/semantic.json --approved",
        "levels": [
            {"name": "lite", "meaning": "Fast selected-file symbol map.", "when": "Use when you only need to know which symbols exist."},
            {"name": "v1", "meaning": "Normal local impact map.", "when": "Use before most edits to see references, calls, hierarchy, endpoints, DB/config clues, likely tests, and changed-symbol impact."},
            {"name": "v2", "meaning": "Richer local semantic metadata.", "when": "Use when V1 is not enough and you need symbol index, import/module edges, endpoint-to-handler links, data-flow-lite hints, or provider readiness."},
            {"name": "v3", "meaning": "Provider-backed metadata ingestion.", "when": "Use only when provider-backed semantic intelligence is requested or an approved provider-output file exists."},
        ],
        "v3_rule": "V3 is never default and requires explicit --depth v3 plus --provider-output, plus --approved or local policy enablement.",
        "navigator_rule": "Navigator may recommend V3 only when provider-backed semantic intelligence is requested or an approved provider-output file exists for the task.",
        "auto_run_rule": "TailTrail must not auto-run JDT, Roslyn, LSP/language servers, SCIP, tree-sitter, SQL parsers, Terraform parsers, MCP providers, networked services, or repo-owned extractors.",
        "evidence_rule": "Provider-backed metadata is advisory. Exact source, tests, CI, scanner evidence, policy, guardrails, and explicit user direction still win.",
    }


def next_actions(plan: dict[str, Any]) -> list[dict[str, str]]:
    actions = [
        {
            "action": "review",
            "label": "Review the plan first.",
            "when": "Always.",
            "prompt": "Review this TailTrail Start report. I will approve or edit the plan before implementation.",
        },
        {
            "action": "approve",
            "label": "Approve implementation.",
            "when": "Use when selected features, impacted files, and validation look right.",
            "prompt": "Approve this plan. Implement the smallest maintainable change and run or name the focused validation.",
        },
        {
            "action": "edit",
            "label": "Edit the plan.",
            "when": "Use when the plan is too heavy, too light, missing files, or recommending the wrong command.",
            "prompt": "Edit the plan: keep the useful selected features, skip anything too heavy, add the missing files, and use the repo-approved validation command.",
        },
        {
            "action": "validation",
            "label": "Confirm focused validation.",
            "when": "Use before or after implementation when the validation command needs to be explicit.",
            "prompt": "Use this focused validation only: REPLACE_WITH_EXACT_COMMAND. If it cannot run, explain why and name the closest manual check.",
        },
    ]
    if plan.get("scan_approval"):
        actions.append(
            {
                "action": "scan-approval",
                "label": "Approve exactly one scan command, or decline scans.",
                "when": "Use only after reviewing the Scan Approval section.",
                "prompt": "Approve only this command: REPLACE_WITH_EXACT_COMMAND. Do not run any other scanner, audit, build, or networked command.",
            }
        )
    if plan.get("learning_approval"):
        actions.append(
            {
                "action": "learning-approval",
                "label": "Choose how to handle surfaced learnings.",
                "when": "Use when Graph-Aware Learning matches appear.",
                "prompt": "Use learnings as advisory context only. Current source, tests, scanner evidence, policy, and guardrails win.",
            }
        )
    if plan.get("review_plan"):
        review = plan["review_plan"]
        actions.append(
            {
                "action": "review-after-implementation",
                "label": "Approve post-implementation review.",
                "when": "Use after implementation and focused validation when you want TailTrail to review the changed scope.",
                "prompt": f"Approve TailTrail review of {review['default']}. Show findings with severity, file, function, line, impact, fix, validation, confidence, and safe-fix status. Do not apply fixes without approval.",
            }
        )
    actions.append(
        {
            "action": "defer-heavy",
            "label": "Make the workflow leaner.",
            "when": "Use when this is a narrow fix or docs-only task.",
            "prompt": "This is too heavy. Use lean mode: read only the target file and focused test, make the smallest change, and do not run broad scanners.",
        }
    )
    return actions


def build_report(goal: str, root: Path, changed: list[str], command_prefix: str) -> dict[str, Any]:
    plan = navigator.decide(goal, root, changed, command_prefix)
    return {
        "goal": goal,
        "root": root.as_posix(),
        "navigator": plan,
        "next_actions": next_actions(plan),
        "token_posture": token_posture(root, plan),
        "learning_quality": learning_quality(root, plan),
        "setup_posture": setup_posture(root, command_prefix),
        "review_posture": review_posture(plan, command_prefix),
        "harness_posture": harness_posture(root, command_prefix),
        "bootstrap_posture": bootstrap_posture(plan, command_prefix),
        "evaluation_posture": evaluation_posture(goal, plan, command_prefix),
        "code_intelligence": code_intelligence_policy(command_prefix),
        "next_step": "Review the plan, choose one next action, then approve or edit before implementation.",
    }


def render_markdown(report: dict[str, Any], verbose: bool = False) -> str:
    plan = report["navigator"]
    token = report["token_posture"]
    learning = report["learning_quality"]
    setup = report["setup_posture"]
    review = report["review_posture"]
    harness = report["harness_posture"]
    bootstrap = report["bootstrap_posture"]
    evaluation = report["evaluation_posture"]
    code_intel = report["code_intelligence"]
    selected = plan.get("selected_features", [])
    skipped = plan.get("skipped_features", [])
    actions = report.get("next_actions", [])
    lines = [
        "# TailTrail Start Report",
        "",
        "Navigator-first plan. Review or edit this before implementation.",
        "",
        "## Start Here",
        "",
        f"- Next step: {report['next_step']}",
        "- Nothing has been implemented, scanned, captured, learned, or changed by this report.",
        f"- Post-change review: {'selected' if review['selected'] else 'available'} for `{review['scope']}`.",
        f"- Bootstrap Snapshot: `{bootstrap['status']}`.",
        "- Meta-Harness: available after work to review TailTrail behavior and metric confidence.",
        f"- Evaluation Harness: {'selected' if evaluation['selected'] else 'available'} for deterministic proof scenarios.",
        "",
        "## Goal",
        "",
        f"- {report['goal']}",
        "",
        "## Recommended Path",
        "",
        "- Workflow: " + " -> ".join(plan.get("recommended_workflow", [])),
        "- Task types: " + ", ".join(plan.get("task_types", [])),
        "- Risks: " + (", ".join(plan.get("risk_indicators", [])) if plan.get("risk_indicators") else "none detected"),
        f"- Impacted files: `{len(plan.get('likely_impacted_files', []))}`",
        f"- Selected features: `{', '.join(item['name'] for item in selected[:5]) if selected else 'none'}`",
    ]

    if len(selected) > 5:
        lines.append(f"- More selected features: `{len(selected) - 5}` hidden in compact view; use `--verbose` for full detail.")
    if skipped:
        lines.append(f"- Skipped features: `{len(skipped)}` hidden in compact view.")
    if plan.get("scan_approval"):
        lines.append("- Scan approval: required before any broad scanner, audit, build, or vulnerability command.")

    impacted = plan.get("likely_impacted_files", [])
    if impacted:
        lines.extend(["", "## Files To Inspect First", ""])
        for item in impacted[:6]:
            if isinstance(item, dict):
                lines.append(f"- `{item.get('path')}`: {item.get('reason')}")
        if len(impacted) > 6:
            lines.append(f"- ...and `{len(impacted) - 6}` more in verbose Navigator output.")

    commands = plan.get("suggested_commands", [])
    lines.extend(["", "## Key Commands", ""])
    for command in commands[:5]:
        lines.append(f"- `{command}`")
    lines.extend(
        [
            f"- Review after implementation: `{review['command']}`",
            f"- Meta-Harness quick check: `{harness['command']}`",
            f"- Meta-Harness confidence: `{harness['confidence_command']}`",
        ]
    )
    if bootstrap["command"] not in commands[:5]:
        lines.append(f"- Bootstrap Snapshot: `{bootstrap['command']}`")
    if evaluation["selected"]:
        lines.extend(
            [
                f"- Evaluation scenarios: `{evaluation['list_command']}`",
                f"- Evaluation run: `{evaluation['run_command']}`",
                f"- Evaluation report: `{evaluation['report_command']}`",
            ]
        )
    if len(commands) > 5:
        lines.append(f"- ...and `{len(commands) - 5}` more suggested command(s) in verbose view.")

    lines.extend(
        [
            "",
            "## Code Intelligence",
            "",
            "- Default engine path: local-only `lite`, `v1`, and `v2`.",
            "- `lite`: fast selected-file symbols.",
            "- `v1`: normal local impact map before edits.",
            "- `v2`: richer local semantic metadata when V1 is not enough.",
            "- `v3`: provider-backed metadata only; never default.",
            f"- V3 rule: {code_intel['v3_rule']}",
            f"- Navigator rule: {code_intel['navigator_rule']}",
            f"- Auto-run rule: {code_intel['auto_run_rule']}",
            f"- Local example: `{code_intel['default_command']}`",
            f"- V3 example: `{code_intel['v3_command']}`",
            "",
            "## Token And Evidence",
            "",
            f"- Approx focused tokens: `{token['used_tokens']}`",
            f"- Approx avoided tokens: `{token['avoided_tokens']}`",
            f"- Approx reduction: `{token['estimated_reduction_percent']}%`",
            "- Evidence: local estimate only; exact savings require model/API telemetry.",
            f"- Learning review: `{'recommended' if learning['review_recommended'] else 'not needed now'}` ({learning['review_reason']})",
            f"- Setup check: `{setup['recommended_check']}`",
        ]
    )
    if evaluation["selected"]:
        lines.extend(
            [
                "",
                "## Evaluation Harness",
                "",
                f"- Selected: `true` ({evaluation['reason']})",
                f"- Scenario: `{evaluation['scenario']}`",
                f"- Run: `{evaluation['run_command']}`",
                f"- Report: `{evaluation['report_command']}`",
                f"- Write report: `{evaluation['write_report_command']}`",
                f"- Rule: {evaluation['rule']}",
            ]
        )

    lines.extend(
        [
            "",
            "## After Implementation",
            "",
            f"- Review: {review['rule']}",
            f"- Review prompt: `{review['prompt']}`",
            f"- Meta-Harness: {harness['rule']}",
            f"- Shared metadata dry run: `{harness['shared_dry_run_command']}`",
            f"- Shared metadata status: `{harness['shared_status_command']}`",
            f"- Bootstrap Snapshot: {bootstrap['rule']}",
            f"- Evaluation Harness: {evaluation['rule']}",
            "- Learning capture remains approval-only after outcome is known.",
        ]
    )

    lines.extend(["", "## Approval", ""])
    for item in actions[:4]:
        lines.extend(
            [
                f"- {item['label']} `{item['prompt']}`",
            ]
        )
    if len(actions) > 4:
        lines.append(f"- Additional approval options hidden in compact view: `{len(actions) - 4}`.")

    if not verbose:
        lines.extend(
            [
                "",
                "## More Detail",
                "",
                "- Re-run with `--verbose` for the full decision menu, learning/setup details, and full Navigator plan.",
            ]
        )
        return "\n".join(lines) + "\n"

    lines.extend(
        [
        "",
        "## Decision Menu",
        "",
        ]
    )
    for item in actions:
        lines.extend(
            [
                f"### {item['label']}",
                "",
                f"- When: {item['when']}",
                f"- Prompt: `{item['prompt']}`",
                "",
            ]
        )
    lines.extend([f"For a lean next-step reminder later, run: `{report.get('command_prefix', 'python3 scripts/tailtrail.py')} next`.", ""])
    lines.extend(
        [
        "",
        "## Goal",
        "",
        f"- {report['goal']}",
        "",
        "## Navigator Summary",
        "",
        "- Workflow: " + " -> ".join(plan.get("recommended_workflow", [])),
        "- Task types: " + ", ".join(plan.get("task_types", [])),
        "- Risks: " + (", ".join(plan.get("risk_indicators", [])) if plan.get("risk_indicators") else "none detected"),
        f"- Selected features: `{len(selected)}`",
        f"- Skipped features: `{len(skipped)}`",
        f"- Likely impacted files: `{len(plan.get('likely_impacted_files', []))}`",
        "",
        "Top selected features:",
        ]
    )
    for item in selected[:6]:
        lines.append(f"- {item['name']}: {item['reason']}")
    if plan.get("scan_approval"):
        lines.extend(
            [
                "",
                "Scan approval is required before running broad quality, Sonar, vulnerability, audit, test, or build commands.",
            ]
        )
    lines.extend(
        [
            "",
            "## Token Posture",
            "",
            f"- Mode: `{token['mode']}`",
            f"- Approx baseline tokens: `{token['baseline_tokens']}`",
            f"- Approx TailTrail focused tokens: `{token['used_tokens']}`",
            f"- Approx saved tokens: `{token['estimated_saved_tokens']}`",
            f"- Approx reduction: `{token['estimated_reduction_percent']}%`",
            f"- Evidence: {token['evidence']}",
        ]
    )
    if token["used_files"]:
        lines.append("- Used file estimates:")
        lines.extend(f"  - `{item['path']}`: ~{item['approx_tokens']} tokens" for item in token["used_files"][:8])
    if token["avoided_files"]:
        lines.append("- Avoided broad context estimates:")
        lines.extend(f"  - `{item['path']}`: ~{item['approx_tokens']} tokens" for item in token["avoided_files"][:8])
    lines.extend(
        [
            "",
            "## Guarded Learning Quality",
            "",
            f"- Learning index exists: `{learning['index_exists']}`",
            f"- Learning events exist: `{learning['events_exist']}`",
            f"- Refresh actions exist: `{learning['refresh_actions_exist']}`",
            f"- Refresh action count: `{learning['refresh_action_count']}`",
            f"- Blocking refresh actions: `{learning['blocking_refresh_actions']}`",
            f"- Surfaced matches: `{learning['surfaced_matches']}`",
            f"- Learning approval required: `{learning['approval_required']}`",
            f"- Learning review recommended: `{learning['review_recommended']}`",
            f"- Learning review reason: {learning['review_reason']}",
            f"- Learning review command: `{learning['review_command']}`",
            f"- Rule: {learning['rule']}",
            "",
            "## Evaluation Harness Details",
            "",
            f"- Selected: `{evaluation['selected']}`",
            f"- Reason: {evaluation['reason']}",
            f"- Scenario: `{evaluation['scenario']}`",
            f"- List scenarios: `{evaluation['list_command']}`",
            f"- Run scenario: `{evaluation['run_command']}`",
            f"- Report scenario: `{evaluation['report_command']}`",
            f"- Write approved report: `{evaluation['write_report_command']}`",
            f"- Normalize scenario event dry run: `{evaluation['normalize_command']}`",
            f"- Rule: {evaluation['rule']}",
            "",
            "## Install And Update Posture",
            "",
            f"- Source checkout: `{setup['source_checkout']}`",
            f"- Installed pack detected in target root: `{setup['installed_pack_detected']}`",
            f"- Recommended check: `{setup['recommended_check']}`",
            f"- Recommended update check: `{setup['recommended_update_check']}`",
            f"- Note: {setup['note']}",
            "",
            "## Next Step",
            "",
            f"- {report['next_step']}",
            "- Recommended default: approve only after editing any incorrect feature, file, command, scan, or learning choice.",
            "",
            "## Code Intelligence Details",
            "",
            f"- Default: `{code_intel['default']}`",
            "- Default engine path: " + ", ".join(f"`{item}`" for item in code_intel["default_engine_path"]),
            f"- V1/default command: `{code_intel['default_command']}`",
            f"- V2 command: `{code_intel['v2_command']}`",
            f"- V3 command: `{code_intel['v3_command']}`",
            f"- V3 rule: {code_intel['v3_rule']}",
            f"- Navigator rule: {code_intel['navigator_rule']}",
            f"- Auto-run rule: {code_intel['auto_run_rule']}",
            f"- Evidence rule: {code_intel['evidence_rule']}",
        ]
    )
    for level in code_intel["levels"]:
        lines.append(f"- `{level['name']}`: {level['meaning']} When: {level['when']}")
    lines.extend(
        [
            "",
            "## Full Navigator Plan",
            "",
            navigator.markdown(plan).rstrip(),
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Start a TailTrail task with Navigator-first plan, metrics, setup posture, and learning quality.")
    parser.add_argument("goal", nargs="*", help="User goal or task description.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to inspect.")
    parser.add_argument("--changed", action="append", default=[], help="Changed or target file path. Repeat for multiple files.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--command-prefix", default="python3 scripts/tailtrail.py", help="Command prefix to show in suggested commands.")
    parser.add_argument("--verbose", action="store_true", help="Include full decision menu, posture details, and Navigator output.")
    args = parser.parse_args()

    goal = " ".join(args.goal).strip()
    if not goal:
        parser.error("goal is required")
    report = build_report(goal, args.root.resolve(), args.changed, args.command_prefix)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report, verbose=args.verbose), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
