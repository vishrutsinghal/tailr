#!/usr/bin/env python3

from __future__ import annotations

from typing import Any


def markdown(report: dict[str, Any], view: str = "full") -> str:
    if view == "compact":
        return compact_markdown(report)
    if view == "commands-only":
        return commands_only_markdown(report)
    if report.get("navigator_mode") == "repo_overview":
        return repo_overview_markdown(report)

    lines = [
        "# TailTrail Navigator Plan",
        "",
        "Navigator recommends the smallest useful TailTrail workflow. Review and edit this plan before implementation.",
        "",
        "## Goal",
        "",
        f"- {report['goal']}",
        "",
        "## Classification",
        "",
        "- Task types: " + ", ".join(report["task_types"]),
        "- Risk indicators: " + (", ".join(report["risk_indicators"]) if report["risk_indicators"] else "none detected"),
        "- Workflow: " + " -> ".join(report["recommended_workflow"]),
        "",
        "## Selected Features",
        "",
    ]
    lines.extend(f"- {item['name']}: {item['reason']}" for item in report["selected_features"])
    lines.extend(["", "## Skipped Features", ""])
    lines.extend(f"- {item['name']}: {item['reason']}" for item in report["skipped_features"])
    lines.extend(["", "## Likely Impacted Files", ""])
    if report["likely_impacted_files"]:
        lines.extend(f"- `{item['path']}`: {item['reason']}" for item in report["likely_impacted_files"])
    else:
        lines.append("- No changed files detected. Add `--changed path/to/file` for a stronger plan.")
    lines.extend(["", "## Load", ""])
    lines.extend(f"- {item}" for item in report["load"])
    lines.extend(["", "## Avoid", ""])
    lines.extend(f"- {item}" for item in report["avoid"])
    lines.extend(["", "## Suggested Commands", ""])
    if report["suggested_commands"]:
        lines.extend(f"- `{item}`" for item in report["suggested_commands"])
    else:
        lines.append("- No commands needed before implementation.")
    if report.get("cross_repo_reference"):
        reference = report["cross_repo_reference"]
        lines.extend(["", "## Cross-Repo Reference", ""])
        lines.extend(
            [
                f"- Target: `{reference['target']}`",
                f"- Reference: `{reference['reference']}`",
                f"- Suggested command: `{reference['command']}`",
                "- Boundaries:",
            ]
        )
        lines.extend(f"  - {item}" for item in reference["boundaries"])
    if report.get("graph_cache"):
        graph_cache = report["graph_cache"]
        lines.extend(["", "## Graph Cache", ""])
        lines.extend(
            [
                f"- Status: {graph_cache['status']}",
                f"- Path: `{graph_cache['path']}`",
                f"- Source: `{graph_cache.get('source', 'unknown')}`",
                f"- Scope: {', '.join(graph_cache['scope']) if graph_cache['scope'] else 'not provided'}",
                f"- Graph mode: {graph_cache.get('graph_mode') or 'unspecified'}",
                f"- Confidence: {graph_cache.get('confidence') or 'not recorded'}",
                f"- Recommended action: {graph_cache['recommended_action']}",
                "- Reasons:",
            ]
        )
        lines.extend(f"  - {item}" for item in graph_cache["reasons"])
        if graph_cache.get("suggested_read_order"):
            lines.append("- Cached suggested read order:")
            lines.extend(f"  - `{item}`" for item in graph_cache["suggested_read_order"][:8])
        lines.append("- Note: graph cache freshness reduces repeated source discovery, but exact source must still be inspected before edits.")
    if report.get("bootstrap_snapshot"):
        snapshot = report["bootstrap_snapshot"]
        lines.extend(["", "## Bootstrap Snapshot", ""])
        lines.extend(
            [
                f"- Status: `{snapshot['status']}`",
                f"- Path: `{snapshot.get('path', '.tailtrail/bootstrap-snapshot.json')}`",
                f"- Reason: {snapshot['reason']}",
                f"- Recommended action: {snapshot['recommended_action']}",
            ]
        )
        if snapshot.get("languages"):
            lines.append("- Languages: " + ", ".join(f"`{item}`" for item in snapshot["languages"]))
        if snapshot.get("manifests"):
            lines.append("- Manifests: " + ", ".join(f"`{item}`" for item in snapshot["manifests"][:8]))
        if snapshot.get("status") != "fresh":
            lines.append(f"- Suggested command: `{snapshot['command']}`")
    if report.get("token_budget"):
        budget = report["token_budget"]
        lines.extend(["", "## Token Budget", ""])
        lines.extend(
            [
                f"- Budget: `{budget['budget_tokens']}` context tokens",
                f"- Confidence: `{budget['confidence']}`",
                f"- Evidence level: `{budget['evidence_level']}`",
                f"- Graph status: `{budget['graph_status']}`",
                f"- Similar events: `{budget['similar_events']}`",
                f"- Escalation rule: {budget['escalation_rule']}",
                f"- Claim guardrail: {budget['claim_guardrail']}",
                "- Reasons:",
            ]
        )
        lines.extend(f"  - {item}" for item in budget["reasons"])
    if report.get("context_strategy"):
        strategy = report["context_strategy"]
        lines.extend(["", "## Context Strategy", ""])
        lines.extend(
            [
                f"- Prompt compression profile: `{strategy['profile']}`",
                f"- Budget band: `{strategy['budget_band']}`",
                f"- Graph-first reads: `{strategy['graph_first']}`",
                f"- Graph status: `{strategy['graph_status']}`",
                "- Load order:",
            ]
        )
        lines.extend(f"  - {item}" for item in strategy["load_order"])
        lines.append("- Avoid:")
        lines.extend(f"  - {item}" for item in strategy["avoid"])
        lines.append(f"- Context receipt command after work: `{strategy['receipt_command']}`")
    if report.get("evaluation_harness") and report["evaluation_harness"].get("selected"):
        evaluation = report["evaluation_harness"]
        lines.extend(["", "## Evaluation Harness", ""])
        lines.extend(
            [
                "- Selected: `true`",
                f"- Scenario: `{evaluation['scenario']}`",
                f"- Reason: {evaluation['reason']}",
                f"- Rule: {evaluation['rule']}",
                "- Commands:",
            ]
        )
        lines.extend(f"  - `{item}`" for item in evaluation["commands"])
        lines.extend(
            [
                f"- Optional write command: `{evaluation['write_report_command']}`",
                f"- Optional normalization command: `{evaluation['normalize_command']}`",
            ]
        )
    if report.get("graph_learning"):
        graph_learning = report["graph_learning"]
        graph_status = graph_learning.get("graph_status", {})
        matches = graph_learning.get("matches", [])
        lines.extend(["", "## Graph-Aware Learnings", ""])
        lines.extend(
            [
                f"- Graph status: `{graph_status.get('status', 'unknown')}`",
                "- Rule: use these as prior repo patterns only after reading current exact source.",
            ]
        )
        if matches:
            for item in matches[:3]:
                event = item.get("event", {})
                confidence = event.get("learning_confidence", {}) if isinstance(event, dict) else {}
                reasons = item.get("match_reasons", [])
                lines.extend(
                    [
                        f"- `{event.get('id', 'unknown')}` score `{confidence.get('score', 0)}/100`, match `{item.get('match_score', 0)}`: {event.get('learning_candidate', 'not recorded')}",
                    ]
                )
                for reason in reasons[:4]:
                    lines.append(f"  - Match reason: {reason}")
        else:
            lines.append("- No matching reusable learnings found.")
    elif report.get("graph_learning_skip_reason"):
        lines.extend(["", "## Graph-Aware Learnings", ""])
        lines.append(f"- Skipped: {report['graph_learning_skip_reason']}")
    if report.get("learning_approval"):
        approval = report["learning_approval"]
        lines.extend(["", "## Learning Approval", ""])
        lines.extend(
            [
                f"- Question: {approval['question']}",
                f"- Default: {approval['default']}",
                "- Surfaced learning IDs: " + (", ".join(f"`{item}`" for item in approval["learning_ids"]) if approval["learning_ids"] else "none"),
                f"- Advisory rule: {approval['advisory_rule']}",
                "- Choices:",
            ]
        )
        for item in approval["choices"]:
            lines.append(f"  - {item['choice']}: {item['meaning']}")
    lines.append("- Note: learnings are advisory only; current source, tests, CI, scanner, policy, guardrails, and explicit user instructions always win.")
    if report.get("learning_refresh_awareness"):
        refresh = report["learning_refresh_awareness"]
        lines.extend(["", "## Learning Refresh Awareness", ""])
        lines.extend(
            [
                "- Refresh may be worth reviewing because:",
            ]
        )
        lines.extend(f"  - {item}" for item in refresh["reasons"])
        lines.extend(
            [
                f"- Suggested command: `{refresh['command']}`",
                f"- Rule: {refresh['rule']}",
            ]
        )
    if report.get("meta_harness_hints") and report["meta_harness_hints"].get("hints"):
        harness = report["meta_harness_hints"]
        lines.extend(["", "## Approved Meta-Harness Hints", ""])
        lines.append(f"- Rule: {harness['rule']}")
        for item in harness["hints"]:
            features = ", ".join(f"`{feature}`" for feature in item.get("affected_features", [])) or "`unspecified`"
            lines.append(
                f"- `{item['proposal_id']}` ({item['category']}, evidence `{item['evidence_label']}`, features {features}): {item['hint']}"
            )
    if report.get("review_plan"):
        review = report["review_plan"]
        lines.extend(["", "## Navigator-Led Review", ""])
        lines.extend(
            [
                f"- Intent: {review['intent']}",
                f"- Recommended scope: `{review['scope']}`",
                f"- Default: {review['default']}",
                f"- Reason: {review['reason']}",
                f"- Detail level: `{review['detail_level']}`",
                f"- Suggested command after approval: `{review['command']}`",
                f"- Approval: {review['approval']}",
                "- Finding fields:",
            ]
        )
        lines.extend(f"  - {item}" for item in review["finding_fields"])
        lines.append("- Checked for:")
        lines.extend(f"  - {item}" for item in review["checked_for"])
        lines.append("- Guarded fix loop:")
        lines.extend(f"  - {item}" for item in review["guarded_fix_loop"])
    if report.get("learning_capture_suggestion"):
        capture = report["learning_capture_suggestion"]
        lines.extend(["", "## Post-Task Learning Capture Suggestion", ""])
        lines.extend(
            [
                f"- Mode: {capture['mode']}",
                f"- When: {capture['when']}",
                f"- Safety: {capture['safety']}",
                f"- Suggested command: `{capture['command']}`",
            ]
        )
    if report.get("scan_approval"):
        approval = report["scan_approval"]
        lines.extend(["", "## Scan Approval", ""])
        lines.extend(
            [
                f"- Question: {approval['question']}",
                f"- Default: {approval['default']}",
                f"- Why: {approval['why']}",
                "- Detected signals:",
            ]
        )
        lines.extend(f"  - {item}" for item in approval["signals"])
        lines.append("- Candidate commands:")
        lines.extend(
            f"  - `{item['command']}` ({item['safety']}): {item['reason']}"
            for item in approval["candidate_commands"]
        )
        lines.append("- Approval choices:")
        lines.extend(f"  - {item}" for item in approval["approval_choices"])
    if report.get("vulnerability_evidence"):
        evidence = report["vulnerability_evidence"]
        lines.extend(["", "## Vulnerability Evidence Needed", ""])
        lines.append(f"- {evidence['message']}")
        lines.append("- Useful evidence:")
        lines.extend(f"  - {item}" for item in evidence["examples"])
    lines.extend(["", "## Implementation Plan", ""])
    lines.extend(f"{index}. {item}" for index, item in enumerate(report["implementation_plan"], start=1))
    lines.extend(["", "## Approval", ""])
    lines.extend(f"- {item}" for item in report["approval"])
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {item}" for item in report["notes"])
    return "\n".join(lines) + "\n"


def compact_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Navigator Compact Plan",
        "",
        "## Goal",
        "",
        f"- {report['goal']}",
        "",
    ]
    if report.get("navigator_mode") == "repo_overview":
        lines.extend(
            [
                "## Mode",
                "",
                "- Repo Overview / Discovery",
                "",
                "## Plan",
                "",
            ]
        )
        lines.extend(f"{index}. {item}" for index, item in enumerate(report["implementation_plan"], start=1))
        if report.get("optional_deeper_discovery"):
            lines.extend(["", "## Optional Command", "", f"- `{report['optional_deeper_discovery']['command']}`"])
        if report.get("bootstrap_snapshot") and report["bootstrap_snapshot"].get("status") != "fresh":
            lines.extend(["", "## Bootstrap Snapshot", "", f"- `{report['bootstrap_snapshot']['command']}`"])
    else:
        lines.extend(
            [
                "## Workflow",
                "",
                "- " + " -> ".join(report["recommended_workflow"]),
                "",
                "## Selected Features",
                "",
            ]
        )
        lines.extend(f"- {item['name']}" for item in report["selected_features"])
        lines.extend(["", "## Suggested Commands", ""])
        if report["suggested_commands"]:
            lines.extend(f"- `{item}`" for item in report["suggested_commands"])
        else:
            lines.append("- none")
        if report.get("token_budget"):
            budget = report["token_budget"]
            lines.extend(
                [
                    "",
                    "## Token Budget",
                    "",
                    f"- Budget: `{budget['budget_tokens']}` context tokens",
                    f"- Confidence: `{budget['confidence']}`",
                    f"- Escalation: {budget['escalation_rule']}",
                ]
            )
        if report.get("context_strategy"):
            strategy = report["context_strategy"]
            lines.extend(
                [
                    "",
                    "## Context Strategy",
                    "",
                    f"- Profile: `{strategy['profile']}`",
                    f"- Graph-first: `{strategy['graph_first']}`",
                    "- Use graph/read-order and summaries before exact source reads.",
                    "- Avoid raw learning history and broad source scans unless approved.",
                ]
            )
        if report.get("evaluation_harness") and report["evaluation_harness"].get("selected"):
            evaluation = report["evaluation_harness"]
            lines.extend(
                [
                    "",
                    "## Evaluation Harness",
                    "",
                    f"- Scenario: `{evaluation['scenario']}`",
                    f"- Run: `{evaluation['commands'][1]}`",
                    f"- Report: `{evaluation['commands'][2]}`",
                    "- It uses committed fixtures and does not run live agents or model/API calls.",
                ]
            )
        if report.get("bootstrap_snapshot"):
            snapshot = report["bootstrap_snapshot"]
            lines.extend(
                [
                    "",
                    "## Bootstrap Snapshot",
                    "",
                    f"- Status: `{snapshot['status']}`",
                    f"- Action: {snapshot['recommended_action']}",
                ]
            )
            if snapshot.get("status") != "fresh":
                lines.append(f"- Command: `{snapshot['command']}`")
        if report.get("meta_harness_hints") and report["meta_harness_hints"].get("hints"):
            lines.extend(["", "## Approved Meta-Harness Hints", ""])
            for item in report["meta_harness_hints"]["hints"]:
                lines.append(f"- `{item['proposal_id']}`: {item['hint']}")
        if report.get("scan_approval"):
            lines.extend(["", "## Approval Needed", "", "- Scan/test/build/audit commands require explicit approval; default is no."])
        if report.get("review_plan"):
            review = report["review_plan"]
            lines.extend(
                [
                    "",
                    "## Review",
                    "",
                    f"- Scope: `{review['scope']}` ({review['default']})",
                    f"- Approval: {review['approval']}",
                    f"- Command: `{review['command']}`",
                ]
            )
        if report.get("vulnerability_evidence"):
            lines.extend(["", "## Evidence Needed", "", f"- {report['vulnerability_evidence']['message']}"])
        if report.get("learning_capture_suggestion"):
            capture = report["learning_capture_suggestion"]
            lines.extend(
                [
                    "",
                    "## Post-Task Learning Capture",
                    "",
                    f"- When: {capture['when']}",
                    f"- Safety: {capture['safety']}",
                    f"- Command: `{capture['command']}`",
                ]
            )
        lines.extend(["", "## Next Steps", ""])
        lines.extend(f"{index}. {item}" for index, item in enumerate(report["implementation_plan"][:4], start=1))
    lines.extend(["", "## Approval", ""])
    lines.extend(f"- {item}" for item in report["approval"])
    return "\n".join(lines) + "\n"


def commands_only_markdown(report: dict[str, Any]) -> str:
    lines = ["# TailTrail Navigator Commands", ""]
    commands = list(report.get("suggested_commands", []))
    if report.get("optional_deeper_discovery"):
        commands.append(report["optional_deeper_discovery"]["command"])
    if report.get("bootstrap_snapshot") and report["bootstrap_snapshot"].get("status") != "fresh":
        commands.insert(0, report["bootstrap_snapshot"]["command"])
    commands = list(dict.fromkeys(commands))
    if commands:
        lines.extend(f"- `{item}`" for item in commands)
    else:
        lines.append("- No commands recommended before approval.")
    if report.get("scan_approval"):
        lines.extend(["", "## Approval Required", ""])
        lines.append("- Do not run scan/test/build/audit commands until the user approves one exact command.")
    if report.get("review_plan"):
        lines.extend(["", "## Review", ""])
        lines.append(f"- `{report['review_plan']['command']}`")
    if report.get("evaluation_harness") and report["evaluation_harness"].get("selected"):
        lines.extend(["", "## Evaluation Harness", ""])
        lines.extend(f"- `{item}`" for item in report["evaluation_harness"]["commands"])
    if report.get("meta_harness_hints") and report["meta_harness_hints"].get("hints"):
        lines.extend(["", "## Approved Meta-Harness Hints", ""])
        lines.extend(f"- `{item['proposal_id']}`: {item['hint']}" for item in report["meta_harness_hints"]["hints"])
    if report.get("vulnerability_evidence"):
        lines.extend(["", "## Evidence Needed", ""])
        lines.append(f"- {report['vulnerability_evidence']['message']}")
    return "\n".join(lines) + "\n"


def repo_overview_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Navigator Plan",
        "",
        "Navigator selected a compact read-only repo overview path.",
        "",
        "## Goal",
        "",
        f"- {report['goal']}",
        "",
        "## Mode",
        "",
        "- Repo Overview / Discovery",
        "- No implementation until approval.",
        "- No scans, tests, builds, learning capture, AIDLC, review, or handoff unless you ask for them.",
        "",
        "## Plan",
        "",
    ]
    lines.extend(f"{index}. {item}" for index, item in enumerate(report["implementation_plan"], start=1))
    lines.extend(["", "## Load", ""])
    lines.extend(f"- {item}" for item in report["load"])
    lines.extend(["", "## Avoid", ""])
    lines.extend(f"- {item}" for item in report["avoid"])
    if report.get("bootstrap_snapshot"):
        snapshot = report["bootstrap_snapshot"]
        lines.extend(["", "## Bootstrap Snapshot", ""])
        lines.extend(
            [
                f"- Status: `{snapshot['status']}`",
                f"- Path: `{snapshot.get('path', '.tailtrail/bootstrap-snapshot.json')}`",
                f"- Reason: {snapshot['reason']}",
                f"- Recommended action: {snapshot['recommended_action']}",
            ]
        )
        if snapshot.get("languages"):
            lines.append("- Languages: " + ", ".join(f"`{item}`" for item in snapshot["languages"]))
        if snapshot.get("manifests"):
            lines.append("- Manifests: " + ", ".join(f"`{item}`" for item in snapshot["manifests"][:8]))
        if snapshot.get("status") != "fresh":
            lines.append(f"- Command: `{snapshot['command']}`")
    if report.get("meta_harness_hints") and report["meta_harness_hints"].get("hints"):
        lines.extend(["", "## Approved Meta-Harness Hints", ""])
        lines.append(f"- Rule: {report['meta_harness_hints']['rule']}")
        lines.extend(f"- `{item['proposal_id']}`: {item['hint']}" for item in report["meta_harness_hints"]["hints"])
    if report.get("optional_deeper_discovery"):
        discovery = report["optional_deeper_discovery"]
        lines.extend(["", "## Optional Deeper Discovery", ""])
        lines.extend(
            [
                f"- Feature: {discovery['name']}",
                f"- Default: {discovery['default']}",
                f"- Creates: `{discovery['creates']}`",
                f"- Why: {discovery['why']}",
                f"- Command: `{discovery['command']}`",
                "- Use when:",
            ]
        )
        lines.extend(f"  - {item}" for item in discovery["use_when"])
    lines.extend(["", "## Approval", ""])
    lines.extend(f"- {item}" for item in report["approval"])
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {item}" for item in report["notes"])
    return "\n".join(lines) + "\n"
