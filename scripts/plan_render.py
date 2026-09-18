#!/usr/bin/env python3
"""Render the compact human-readable Start plan from a saved start report.

Consumes the persisted start-report envelope
(``.tailtrail/runs/<run_id>/planning/start-report-v1.json``) and renders the
finalized plan design:

- the TailTrail ASCII banner (reused from ``scripts/tailtrail.py``)
- the active AIDLC mode (lite/standard/full) with its selection reason
- the TailTrail features used, one line each (``--verbose`` adds one
  explanation line per feature and lists skipped features)
- token usage and estimated reduction, with the honest evidence label
- the requirement matrix when one was drafted (approve requirements, not
  just the plan)
- the pipeline plan (stage sequence and badge boundaries from the Planning
  Lock, contracts reused from ``scripts/navigator_scope.py``)
- the drift-gate preview (what will block the stage handoff, and what
  happens on block)
- concrete validation commands and next actions

The renderer is read-only: it never edits files, runs commands, or grants
authority. It renders ``REPLACE_WITH_*`` placeholders as explicit
``<you decide: ...>`` markers so no non-executable command looks runnable.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

_LINE = "─" * 68
_HEAVY = "═" * 68

# One extra explanation line per known feature for verbose mode. Unknown
# features fall back to the generic advisory boundary.
_FEATURE_NOTES = {
    "Navigator Planning": "Reads discovery metadata only; never edits files or runs implementation.",
    "AIDLC": "Lifecycle state and approval gates; requirement wording stays with its authority.",
    "Code Graph Mapper": "Metadata-only cache; stale or invalid caches fail closed and must be refreshed.",
    "Code Review Graph Lite": "Bounded caller/test/helper map; candidates are not ownership proof.",
    "Requirement Impact Map": "Local AST evidence only — candidates, not completion proof.",
    "Test Precision Planner": "Plans regression/negative/boundary cases before any command runs.",
    "Drift Analysis": "Fail-closed gate: missing anchor or evidence is drift, never a pass.",
    "Review Lens": "Advisory code-health check; does not apply fixes without approval.",
    "Focused QA Lens": "Targeted regression and preservation checks for the changed behavior.",
    "Token Autopilot": "Local estimates only; exact savings require provider telemetry.",
    "Bootstrap Snapshot": "Captures safe repo/runtime facts; no source bodies, no execution.",
    "Learning Capture Trigger": "Prepares capture only; nothing is written until you approve it.",
}
_GENERIC_NOTE = "Advisory control; it does not edit files, run commands, or grant authority."

_DRIFT_GATE_LINES = (
    "✓ Scope:     changed paths must stay inside the approved editable union",
    "✓ Coverage:  production changes must map to a requirement",
    "✓ Implement: every change requirement needs ≥1 changed path in scope",
    "✓ Fulfill:   every change requirement needs authoritative, passing,",
    "             tier-linked evidence — unlinked green tests are not proof",
    "On block: named finding → bounded regression loop (max 3) → manual",
    "design review after 3 strikes.",
)

_STAGE_BADGES = {
    "IMPLEMENTATION": ("impl-badge", "production source + supporting assets", "tests, managed tooling"),
    "TESTING": ("test-badge", "test/proof paths", "all production source"),
    "INFRA": ("infra-badge", "configuration + manifests", "production source, tests"),
}


def _load_module(relative: str, name: str) -> Any | None:
    """Load a sibling script in both import contexts; None if unavailable."""
    try:
        return __import__(name)
    except Exception:
        pass
    try:
        spec = importlib.util.spec_from_file_location(name, ROOT / relative)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


def _banner_lines() -> list[str]:
    """Reuse the canonical banner from scripts/tailtrail.py when loadable."""
    tailtrail = _load_module("scripts/tailtrail.py", "plan_render_tailtrail")
    if tailtrail is not None and hasattr(tailtrail, "startup_banner_lines"):
        try:
            return list(tailtrail.startup_banner_lines())
        except Exception:
            pass
    return [
        "+--------------------------------------------+",
        "| TAILTRAIL                                  |",
        "| Requirement completion and drift control   |",
        "| for AI-assisted delivery                   |",
        "+--------------------------------------------+",
    ]


def _scope_module() -> Any | None:
    return _load_module("scripts/navigator_scope.py", "plan_render_navigator_scope")


def _clean_command(command: str) -> str:
    """Make REPLACE_WITH placeholders visibly non-executable."""
    return command.replace("REPLACE_WITH_", "<you decide: ").replace(
        " ", " ", 1
    ) if "REPLACE_WITH_" not in command else command


def _deplaceholderize(text: str) -> str:
    if "REPLACE_WITH_" not in text:
        return text
    cleaned = text
    for token in ("REPLACE_WITH_FILE", "REPLACE_WITH_exactness", "REPLACE_WITH_strategy",
                  "REPLACE_WITH_preserved_evidence", "REPLACE_WITH_pass_or_fail_or_not_run",
                  "REPLACE_WITH_EXACT_COMMAND", "REPLACE_WITH_SHORT_TASK_SUMMARY",
                  "REPLACE_WITH_REUSABLE_PATTERN_OR_DECISION", "REPLACE_WITH_EXPLICIT_REASON"):
        cleaned = cleaned.replace(token, "<you decide>")
    return cleaned


def _fmt_int(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def _section(lines: list[str], title: str) -> None:
    lines.append("")
    lines.append(f" {title}")
    lines.append(f"{_LINE}")


def _render_aidlc(lines: list[str], report: dict[str, Any]) -> None:
    mode = report.get("aidlc_mode") or {}
    _section(lines, "AIDLC MODE")
    mode_name = str(mode.get("mode") or "lite")
    selection = str(mode.get("selection") or "default")
    lines.append(f" Mode:      {mode_name:<10} (selected: {selection})")
    escalation = mode.get("full_escalation") or {}
    if escalation.get("state") == "not-eligible":
        lines.append(f" Full mode: not eligible — {escalation.get('reason', 'not requested')}")
    else:
        lines.append(f" Full mode: {escalation.get('state', 'unknown')}")
    lines.append(" Boundary:  requirement wording stays with its authority; TailTrail adds")
    lines.append("            scope, evidence, drift, and closure controls.")


def _render_features(lines: list[str], navigator: dict[str, Any], verbose: bool) -> None:
    _section(lines, "TAILTRAIL FEATURES USED" + (" (verbose)" if verbose else ""))
    selected = navigator.get("selected_features") or []
    if not selected:
        lines.append(" (none selected)")
    for feature in selected:
        name = str(feature.get("name") or "unknown")
        reason = _deplaceholderize(str(feature.get("reason") or ""))
        lines.append(f" {name:<26} {reason}")
        if verbose:
            lines.append(f"   ↳ {_FEATURE_NOTES.get(name, _GENERIC_NOTE)}")
    if verbose:
        skipped = navigator.get("skipped_features") or []
        if skipped:
            lines.append("")
            lines.append(" Skipped features:")
            for feature in skipped:
                name = str(feature.get("name") or "unknown")
                reason = _deplaceholderize(str(feature.get("reason") or ""))
                lines.append(f" {name:<26} {reason}")


def _render_tokens(lines: list[str], report: dict[str, Any]) -> None:
    posture = report.get("token_posture") or {}
    if not posture:
        return
    navigator = report.get("navigator") or {}
    budget = navigator.get("token_budget") or {}
    _section(lines, "TOKEN USAGE")
    lines.append(f" Baseline (load-everything): {_fmt_int(posture.get('baseline_tokens'))} tokens  (est.)")
    lines.append(f" Planned context:            {_fmt_int(posture.get('used_tokens'))} tokens  (est.)")
    lines.append(f" Avoided:                    {_fmt_int(posture.get('avoided_tokens'))} tokens  (est.)")
    reduction = posture.get("estimated_reduction_percent")
    if reduction is not None:
        lines.append(f" Estimated reduction:        {reduction}%")
    lines.append(f" Evidence: {posture.get('evidence', 'local estimate only')}")
    if budget:
        band = budget.get("budget_band")
        escalation = budget.get("escalation_rule")
        if band:
            lines.append(f" Budget band: {band}")
        if escalation:
            lines.append(f" Escalation: {_deplaceholderize(str(escalation))}")


def _render_requirements(lines: list[str], report: dict[str, Any]) -> None:
    navigator = report.get("navigator") or {}
    matrix = report.get("requirement_matrix") or navigator.get("requirement_matrix") or []
    _section(lines, "REQUIREMENTS (approve these, not just the plan)")
    if not matrix:
        lines.append(" No requirement matrix drafted yet — approve requirements before")
        lines.append(" implementation; the drift gate cannot validate a vague anchor.")
        return
    for row in matrix:
        if not isinstance(row, dict):
            continue
        display = str(row.get("display_id") or row.get("requirement_uid") or "REQ")
        kind = str(row.get("kind") or "change")
        statement = str(row.get("statement") or "")
        lines.append(f" {display}  {kind:<9} {statement}")
        for criterion in row.get("acceptance_criteria", []) or []:
            lines.append(f"         Accept:   {criterion}")
        paths = [str(p) for p in row.get("likely_paths", []) or [] if str(p)]
        if paths:
            lines.append(f"         Paths:    {', '.join(paths)}")
        tiers = (row.get("validation_contract") or {}).get("tiers") or []
        if tiers:
            lines.append(f"         Proof:    {', '.join(str(t) for t in tiers)}")


def _render_pipeline(lines: list[str], lock: dict[str, Any] | None) -> None:
    _section(lines, "PIPELINE PLAN")
    pipeline = (lock or {}).get("pipeline") or {}
    sequence = pipeline.get("stage_sequence") or ["IMPLEMENTATION", "TESTING", "INFRA"]
    active = pipeline.get("active_stage", "PENDING")
    scope = _scope_module()
    for stage in sequence:
        contract_info = _STAGE_BADGES.get(stage, (f"{stage.lower()}-badge", "stage scope", "out-of-scope roles"))
        allowed = contract_info[1]
        blocked = contract_info[2]
        if scope is not None and hasattr(scope, "WORKER_CONTRACTS") and stage in scope.WORKER_CONTRACTS:
            contract = scope.WORKER_CONTRACTS[stage]
            allowed = ", ".join(sorted(contract.allowed_write_roles)) or allowed
            blocked = ", ".join(sorted(contract.prohibited_write_roles)) or blocked
        marker = "▶" if stage == active else " "
        lines.append(f" {marker} {stage:<15} {contract_info[0]:<12} may write: {allowed}")
        lines.append(f"                               blocked: {blocked}")
    lines.append(" Write-gate: out-of-scope writes raise SecurityBoundaryError.")


def _render_drift_gate(lines: list[str]) -> None:
    _section(lines, "DRIFT GATE (enforced at stage handoffs)")
    for line in _DRIFT_GATE_LINES:
        lines.append(f" {line}")


def _render_commands(lines: list[str], navigator: dict[str, Any]) -> None:
    commands = navigator.get("suggested_commands") or []
    validation = [
        _deplaceholderize(str(command))
        for command in commands
        if any(word in str(command) for word in ("test plan", "pytest", "quality run", "validation"))
    ]
    if not validation:
        validation = [_deplaceholderize(str(command)) for command in commands[:2]]
    if validation:
        _section(lines, "VALIDATION")
        for command in validation[:3]:
            lines.append(f" {command}")


def _render_next(lines: list[str], report: dict[str, Any]) -> None:
    actions = report.get("next_actions") or []
    if not actions:
        return
    _section(lines, "NEXT")
    choices = " | ".join(str(action.get("action") or action.get("label") or "") for action in actions[:5])
    lines.append(f" {choices}")


def render_plan(envelope: dict[str, Any], *, verbose: bool = False, lock: dict[str, Any] | None = None) -> str:
    """Render the compact human plan view from a saved start-report envelope."""
    report = envelope.get("report") or {}
    navigator = report.get("navigator") or {}
    planning_lock = report.get("planning_lock") or {}
    lines: list[str] = []
    # Fence the banner so chat surfaces cannot collapse its fixed-width
    # spacing the way hello's fenced banner is preserved. Raw CLI bytes
    # are unchanged apart from the two fence markers.
    lines.append("```text")
    lines.extend(_banner_lines())
    lines.append("```")
    lines.append("")
    lines.append(_HEAVY)
    lines.append(f" TAILTRAIL START PLAN — run {envelope.get('run_id', 'unknown')}")
    lines.append(_HEAVY)
    lines.append(f" Goal:    {envelope.get('goal', report.get('goal', ''))}")
    status = planning_lock.get("status") or "unknown"
    if status == "awaiting-approval":
        lines.append(" Status:  AWAITING APPROVAL — no source edits until you approve")
    else:
        lines.append(f" Status:  {status}")

    _render_aidlc(lines, report)
    _render_features(lines, navigator, verbose)
    _render_tokens(lines, report)
    _render_requirements(lines, report)
    _render_pipeline(lines, lock if lock is not None else planning_lock)
    _render_drift_gate(lines)
    _render_commands(lines, navigator)
    _render_next(lines, report)
    lines.append("")
    return "\n".join(lines)


def _load_lock_for(report_path: Path) -> dict[str, Any] | None:
    lock_path = report_path.parent / "lock-v1.json"
    if not lock_path.is_file():
        return None
    try:
        return json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render the compact human-readable Start plan from a saved start report."
    )
    parser.add_argument("--report", type=Path, required=True, help="Path to start-report-v1.json")
    parser.add_argument("--verbose", action="store_true", help="Add one explanation line per feature and list skipped features.")
    args = parser.parse_args()
    try:
        envelope = json.loads(args.report.read_text(encoding="utf-8"))
        lock = _load_lock_for(args.report.resolve())
        print(render_plan(envelope, verbose=args.verbose, lock=lock))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Plan render error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())