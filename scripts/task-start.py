#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import importlib.util
import json
import re
import os
import sys
from pathlib import Path
from typing import Any

import target_workspace
import start_posture
import requirement_discovery
import requirement_evidence
import requirement_intake
import architecture_planning
import behaviour_planning
import maintainability_planning
import navigator_scope
import navigator_graph_lifecycle
import ui_planning
import session_control


ROOT = Path(__file__).resolve().parents[1]
NAVIGATOR_PATH = ROOT / "scripts" / "navigator.py"
SPEC = importlib.util.spec_from_file_location("tailtrail_navigator", NAVIGATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("Unable to load scripts/navigator.py")
navigator = importlib.util.module_from_spec(SPEC)
sys.modules["tailtrail_navigator"] = navigator
SPEC.loader.exec_module(navigator)

PLANNING_LOCK_PATH = ROOT / "scripts" / "planning_lock.py"
LOCK_SPEC = importlib.util.spec_from_file_location("tailtrail_planning_lock", PLANNING_LOCK_PATH)
if LOCK_SPEC is None or LOCK_SPEC.loader is None:
    raise SystemExit("Unable to load scripts/planning_lock.py")
planning_lock = importlib.util.module_from_spec(LOCK_SPEC)
sys.modules["tailtrail_planning_lock"] = planning_lock
LOCK_SPEC.loader.exec_module(planning_lock)

BRIDGE_SPEC = importlib.util.spec_from_file_location("tailtrail_official_aidlc_bridge", ROOT / "scripts" / "aidlc-official-bridge.py")
if BRIDGE_SPEC is None or BRIDGE_SPEC.loader is None:
    raise SystemExit("Unable to load scripts/aidlc-official-bridge.py")
official_aidlc_bridge = importlib.util.module_from_spec(BRIDGE_SPEC)
sys.modules["tailtrail_official_aidlc_bridge"] = official_aidlc_bridge
BRIDGE_SPEC.loader.exec_module(official_aidlc_bridge)

OFFICIAL_REQUIREMENTS_SPEC = importlib.util.spec_from_file_location(
    "tailtrail_start_official_aidlc_requirements",
    ROOT / "scripts" / "official-aidlc-requirements.py",
)
if OFFICIAL_REQUIREMENTS_SPEC is None or OFFICIAL_REQUIREMENTS_SPEC.loader is None:
    raise SystemExit("Unable to load scripts/official-aidlc-requirements.py")
official_aidlc_requirements = importlib.util.module_from_spec(OFFICIAL_REQUIREMENTS_SPEC)
sys.modules["tailtrail_start_official_aidlc_requirements"] = official_aidlc_requirements
OFFICIAL_REQUIREMENTS_SPEC.loader.exec_module(official_aidlc_requirements)

WORKFLOW_START_SPEC = importlib.util.spec_from_file_location("tailtrail_workflow_start_integration", ROOT / "scripts" / "workflow_runtime" / "start_integration.py")
if WORKFLOW_START_SPEC is None or WORKFLOW_START_SPEC.loader is None:
    raise SystemExit("Unable to load scripts/workflow_runtime/start_integration.py")
workflow_start_integration = importlib.util.module_from_spec(WORKFLOW_START_SPEC)
sys.modules["tailtrail_workflow_start_integration"] = workflow_start_integration
WORKFLOW_START_SPEC.loader.exec_module(workflow_start_integration)

SPEC_KIT_BRIDGE_SPEC = importlib.util.spec_from_file_location("tailtrail_spec_kit_bridge", ROOT / "scripts" / "spec-kit-bridge.py")
if SPEC_KIT_BRIDGE_SPEC is None or SPEC_KIT_BRIDGE_SPEC.loader is None:
    raise SystemExit("Unable to load scripts/spec-kit-bridge.py")
spec_kit_bridge = importlib.util.module_from_spec(SPEC_KIT_BRIDGE_SPEC)
sys.modules["tailtrail_spec_kit_bridge"] = spec_kit_bridge
SPEC_KIT_BRIDGE_SPEC.loader.exec_module(spec_kit_bridge)

HOST_WORKSPACE_SPEC = importlib.util.spec_from_file_location("tailtrail_host_workspace_adapter", ROOT / "scripts" / "host-workspace-adapter.py")
if HOST_WORKSPACE_SPEC is None or HOST_WORKSPACE_SPEC.loader is None:
    raise SystemExit("Unable to load scripts/host-workspace-adapter.py")
host_workspace_adapter = importlib.util.module_from_spec(HOST_WORKSPACE_SPEC)
sys.modules["tailtrail_host_workspace_adapter"] = host_workspace_adapter
HOST_WORKSPACE_SPEC.loader.exec_module(host_workspace_adapter)

ENTERPRISE_POLICY_SPEC = importlib.util.spec_from_file_location("tailtrail_enterprise_target_policy", ROOT / "scripts" / "enterprise-target-policy.py")
if ENTERPRISE_POLICY_SPEC is None or ENTERPRISE_POLICY_SPEC.loader is None:
    raise SystemExit("Unable to load scripts/enterprise-target-policy.py")
enterprise_target_policy = importlib.util.module_from_spec(ENTERPRISE_POLICY_SPEC)
sys.modules["tailtrail_enterprise_target_policy"] = enterprise_target_policy
ENTERPRISE_POLICY_SPEC.loader.exec_module(enterprise_target_policy)

DEBUG_DIAGNOSIS_SPEC = importlib.util.spec_from_file_location(
    "tailtrail_debug_host_diagnosis", ROOT / "scripts" / "debug-host-diagnosis.py"
)
if DEBUG_DIAGNOSIS_SPEC is None or DEBUG_DIAGNOSIS_SPEC.loader is None:
    raise SystemExit("Unable to load scripts/debug-host-diagnosis.py")
debug_host_diagnosis = importlib.util.module_from_spec(DEBUG_DIAGNOSIS_SPEC)
sys.modules["tailtrail_debug_host_diagnosis"] = debug_host_diagnosis
DEBUG_DIAGNOSIS_SPEC.loader.exec_module(debug_host_diagnosis)

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


def display_prose(value: Any) -> str:
    """Normalize host-escaped prose for stable, single-line Markdown display.

    Canonical artifacts retain the original user text. Only host-facing prose
    is normalized, so Windows paths and exact evidence fields are not altered.
    """
    text = re.sub(r"\\(?:r\\n|n|r)", " ", str(value))
    text = " ".join(text.split())
    return text.translate(str.maketrans({"\u2013": "-", "\u2014": "-", "\u2212": "-", "\ufffd": "-"}))


REQUIREMENT_KIND_LABELS = {
    "constraint": "constraint on other requirements, not independently completable",
    "preserve": "preserve existing behavior, not new work",
    "safety": "safety constraint",
}
FEATURE_WHEN_OVERRIDES = {
    "Question Orchestrator": "Planning now",
    # The requirement matrix rendered in this same report is already the
    # frozen canonical set; "After approval" would claim work not yet done.
    "Canonical requirements": "Planning now",
    # The Scope section's likely_impacted_files already reflect an initial
    # mapping attempt; only its post-approval confirmation is still pending.
    "Requirement-to-Impact Map": "Planning now (initial); confirmed after approval",
}


def feature_when(name: str, explicit: str | None = None) -> str:
    """Report when a selected TailTrail control actually ran, not a generic guess."""
    if explicit:
        return explicit
    return FEATURE_WHEN_OVERRIDES.get(name, "After approval")


def code_review_graph_lite_why(impacted: list[dict[str, Any]]) -> str | None:
    """Describe what the Code Review Graph candidates actually established, not a fixed claim."""
    graph_items = [item for item in impacted if "Code Review Graph" in str(item.get("reason", ""))]
    if not graph_items:
        return None
    if any(item.get("status") == "included" for item in graph_items):
        return "identified likely callers and focused validation context"
    return "supplied cached repository candidates for this goal; none were confirmed as an implementation owner, caller, or validation path"


def requirement_line(item: dict[str, Any], default_id: str = "REQ") -> str:
    """Render one requirement row, flagging a non-`change` kind so it is not mistaken for independently completable work."""
    display_id = item.get("display_id", default_id)
    statement = display_prose(item.get("statement", ""))
    label = REQUIREMENT_KIND_LABELS.get(str(item.get("kind") or "change"))
    if label:
        return f"- **{display_id}** _({label})_: {statement}"
    return f"- **{display_id}:** {statement}"


def append_requirement_interpretation(lines: list[str], plan: dict[str, Any]) -> None:
    """Explain how prose became requirement rows without exposing host reasoning."""
    interpreted = plan.get("requirement_interpretation") if isinstance(plan, dict) else None
    if not isinstance(interpreted, dict):
        return
    source = str(interpreted.get("source", "deterministic-fallback"))
    if interpreted.get("authority") == "official-ai-dlc-pack":
        label = (
            f"official AI-DLC `{interpreted.get('authority_mode')}` Requirements authority "
            f"through `{interpreted.get('host')}`"
        )
    elif source == "host-assisted":
        label = f"host-assisted by `{interpreted.get('host', 'unknown')}`"
    else:
        label = "deterministic normalization"
    non_requirement_roles = {
        str(row.get("role"))
        for row in interpreted.get("clauses", [])
        if isinstance(row, dict) and row.get("role") in {"context", "evidence", "question"}
    }
    boundary = (
        "; context/evidence wording was retained as traceability, not promoted to a separate requirement"
        if non_requirement_roles
        else ""
    )
    artifact_count = len(interpreted.get("artifact_evidence", []))
    artifact_boundary = f"; {artifact_count} inspected requirement artifact(s) hash-bound" if artifact_count else ""
    lines.append(f"**Interpretation evidence:** {label}; exact-goal-bound{artifact_boundary}{boundary}.")
    if source == "host-assisted" and not artifact_count:
        lines.append(
            "- No requirement artifacts were supplied or hash-bound for this interpretation; "
            "any file or document mentioned in the goal was not verified as read."
        )
    lines.append("")


def append_stacked_records(
    lines: list[str],
    records: list[tuple[str, list[tuple[str, str]]]],
) -> None:
    """Render prose-heavy report data without host-dependent table widths."""
    for title, fields in records:
        lines.append(f"- **{title}**")
        for label, value in fields:
            lines.append(f"  - **{label}:** {value}")


def pipeline_badge_lines(lock: dict[str, Any] | None, *, compact: bool = False) -> list[str]:
    """Render the run's badge-gated pipeline stage for Start reports."""
    pipeline = lock.get("pipeline", {}) if isinstance(lock, dict) else {}
    active = str(pipeline.get("active_stage") or "PENDING")
    info = planning_lock.PIPELINE_STAGE_BADGES.get(active)
    if info is None:
        if compact:
            return ["- Pipeline badges: `unbadged` (no stage write gates apply)."]
        return ["", "## Pipeline badges", "", "- Status: `unbadged` (no stage write gates apply)."]
    if compact:
        return [f"- Pipeline badge: `{active}` (`{info['badge']}`; may write {info['may_write']}; {info['blocked']} blocked)."]
    completed = [str(stage) for stage in pipeline.get("completed_stages", []) if str(stage).strip()]
    return [
        "", "## Pipeline badges", "",
        f"- Active stage: `{active}` (`{info['badge']}`).",
        f"- May write: {info['may_write']}; blocked: {info['blocked']}.",
        f"- Completed stages: `{', '.join(completed) or 'none'}`.",
        "- Managed patch writes outside the active badge are blocked; advance stages only through approved handoffs.",
    ]


def append_testing_plan(lines: list[str], plan: dict[str, Any]) -> None:
    """Render assertion-level proof as a compact, host-stable checklist."""
    if not isinstance(plan, dict) or not plan.get("selected"):
        return
    lines.extend(["", "## Testing plan", "", "### Required test cases", ""])
    cases = [item for item in plan.get("test_cases", []) if isinstance(item, dict)]
    if cases:
        for index, item in enumerate(cases, start=1):
            lines.append(
                f"{index}. **{display_prose(item.get('test_case_id', f'TC-{index:02d}'))}** "
                f"(covers `{display_prose(item.get('requirement_id', 'REQ'))}`): "
                f"{display_prose(item.get('assertion', ''))}"
            )
    else:
        lines.append("- No UI-specific assertion was derived; resolve the proof contract before the first source edit.")
    lines.extend(["", "### Proof maintenance", ""])
    for path in plan.get("existing_proof_paths", []):
        lines.append(f"- Existing linked proof: `{path}`.")
    for path in plan.get("proposed_proof_paths", []):
        lines.append(f"- Proposed proof addition: `{path}`.")
    lines.append(f"- {display_prose(plan.get('proof_action', ''))}")
    lines.extend(["", "### Commands after implementation", ""])
    commands = [item for item in plan.get("commands", []) if isinstance(item, dict)]
    if commands:
        for index, item in enumerate(commands, start=1):
            lines.append(
                f"{index}. {display_prose(item.get('purpose', 'Run validation'))}: "
                f"`{item.get('command', '')}`"
            )
    else:
        lines.append("- Resolve the exact project-owned validation commands before the first source edit.")
    lines.append(f"- {display_prose(plan.get('boundary', ''))}")


def scope_edge_phrase(row: dict[str, Any], edge: dict[str, Any]) -> str:
    """Describe a relationship from the displayed path's point of view."""
    kind = str(edge.get("kind", "relationship"))
    candidate_id = str(row.get("candidate_id", ""))
    source_is_row = candidate_id == str(edge.get("from_candidate_id", ""))
    directional = {
        "imports-module": (
            "imports a related module",
            "is imported by a related repository path",
        ),
        "loads-module": (
            "loads a related module",
            "is loaded by a related repository path",
        ),
        "calls-symbol": (
            "calls a symbol in a related module",
            "provides a symbol called by the implementation owner",
        ),
        "captures-returned-value": (
            "captures a value returned by a related module",
            "returns a value captured by the implementation owner",
        ),
        "renders-returned-value": (
            "renders a value returned by a related module",
            "produces a value rendered by the UI owner",
        ),
        "catches-error": (
            "catches an error from a related module",
            "raises an error caught by the implementation owner",
        ),
        "writes-ui-state": (
            "writes UI state from related-module output",
            "provides output written into UI state by the implementation owner",
        ),
        "renders-ui-state": (
            "renders UI state derived from a related module",
            "provides output rendered through UI state by the implementation owner",
        ),
        "renders-caught-error": (
            "renders a caught error from a related module",
            "raises an error rendered by the UI owner",
        ),
        "tested-by": (
            "is covered by a linked proof path",
            "provides linked proof for the implementation owner",
        ),
    }
    if kind in directional:
        return directional[kind][0 if source_is_row else 1]
    return kind.replace("-", " ")


def scope_state_summary(
    projection: dict[str, Any],
    evidence: dict[str, Any],
) -> str:
    """Explain a resolved scope using only canonical saved evidence."""
    state = str(projection.get("state", "unknown"))
    if state != "resolved":
        return f"- Scope state: `{state}`."

    owners = [
        row
        for row in projection.get("implementation_owners", [])
        if isinstance(row, dict)
    ]
    resolved_rows = owners or [
        row
        for key in ("proof_paths", "inspection_paths")
        for row in projection.get(key, [])
        if isinstance(row, dict)
    ]
    if not resolved_rows:
        return (
            "- Scope state: `resolved` - the canonical saved scope satisfies its "
            "requirement boundary; no unresolved owner conflict remains."
        )
    requirement_ids = sorted({
        str(requirement_id)
        for row in resolved_rows
        for requirement_id in row.get("requirement_ids", [])
        if str(requirement_id)
    })
    owner_edge_ids = {
        str(edge_id)
        for row in owners
        for edge_id in row.get("evidence_edge_ids", [])
        if str(edge_id)
    }
    edges_by_id = {
        str(row.get("edge_id")): row
        for row in evidence.get("edges", [])
        if isinstance(row, dict) and row.get("edge_id")
    }
    strong_edge_count = sum(
        str(edges_by_id[edge_id].get("strength")) == "strong"
        for edge_id in owner_edge_ids
        if edge_id in edges_by_id
    )
    high_confidence = bool(resolved_rows) and all(
        str(row.get("confidence")) == "high" for row in resolved_rows
    )
    owner_count = len(owners)
    if owners:
        role_count = owner_count
        role_phrase = (
            f"{role_count} {'high-confidence' if high_confidence else 'evidence-backed'} "
            f"implementation owner{'s' if role_count != 1 else ''}"
        )
    else:
        role_count = len(resolved_rows)
        role_phrase = (
            f"{role_count} {'high-confidence' if high_confidence else 'evidence-backed'} "
            f"approved-scope path{'s' if role_count != 1 else ''}"
        )
    requirement_phrase = (
        ", ".join(f"`{requirement_id}`" for requirement_id in requirement_ids)
        if requirement_ids
        else "the saved requirement boundary"
    )
    edge_phrase = (
        f"{strong_edge_count} strong relationship edge"
        f"{'s' if strong_edge_count != 1 else ''} support the saved decision"
        if strong_edge_count
        else "canonical owner-qualification evidence supports the saved decision"
    )
    return (
        f"- Scope state: `resolved` - {role_phrase} cover{'s' if role_count == 1 else ''} "
        f"{requirement_phrase}; {edge_phrase}; no unresolved owner conflict remains."
    )


def append_v2_scope_projection(
    lines: list[str],
    plan: dict[str, Any],
    *,
    verbose: bool = False,
    responsive: bool = False,
) -> bool:
    """Render the canonical v2 roles without flattening authority boundaries."""
    evidence = plan.get("scope_evidence") if isinstance(plan, dict) else None
    if not isinstance(evidence, dict) or str(evidence.get("schema_version")) != "2":
        return False
    projection = navigator_scope.role_projection(evidence, include_excluded=verbose)
    investigation = projection.get("investigation", {})
    cache = investigation.get("cache", {}) if isinstance(investigation, dict) else {}
    cache_reasons = set(cache.get("reason_codes", [])) if isinstance(cache, dict) else set()
    cache_status = str(cache.get("status", "not-checked")) if isinstance(cache, dict) else "not-checked"
    if "bounded-ephemeral-graph-built" in cache_reasons:
        graph_source = "bounded in-memory graph"
        graph_result = "implementation owner resolved" if projection.get("state") == "resolved" else f"scope remained {projection.get('state')}"
        graph_note = f"`{graph_source}`; persistent cache `{cache_status}`; {graph_result}; not persisted."
    elif cache_status == "fresh":
        graph_note = "fresh persistent graph cache; freshness verified against repository identity and inventory."
    else:
        graph_note = f"no usable relationship graph; persistent cache `{cache_status}`."
    lines.extend([
        scope_state_summary(projection, evidence),
        f"- Decision fingerprint: `{projection.get('decision_fingerprint')}`.",
        f"- Scope evidence source: {graph_note}",
    ])
    lifecycle = plan.get("graph_lifecycle") if isinstance(plan.get("graph_lifecycle"), dict) else None
    if lifecycle:
        lines.append(
            f"- Navigator graph management: `{lifecycle.get('action')}`; "
            f"cache `{lifecycle.get('after_status', {}).get('status', 'unknown')}`; "
            f"metadata write `{'yes' if lifecycle.get('written') else 'no'}`."
        )
    candidate_paths = {
        str(row.get("candidate_id")): str(row.get("path"))
        for row in evidence.get("candidates", [])
        if isinstance(row, dict)
    }
    edges_by_id = {
        str(row.get("edge_id")): row
        for row in evidence.get("edges", [])
        if isinstance(row, dict)
    }
    rendered_edge_ids: set[str] = set()
    groups = (
        ("Implementation owners", "implementation_owners", "Editable only after approval."),
        (
            "Inspection paths",
            "inspection_paths",
            "Read-only context; never automatic edit scope; status=inspection-only.",
        ),
        (
            "Existing proof paths",
            "proof_paths",
            "Existing requirement-linked validation scope; after this exact plan is approved, run it unchanged or edit it only for approved proof assertions; status=proof-only.",
        ),
    )
    for title, key, boundary in groups:
        lines.extend(["", f"### {title}", "", f"- {boundary}", ""])
        rows = projection.get(key, [])
        if rows:
            records: list[tuple[str, list[tuple[str, str]]]] = []
            if not responsive:
                lines.extend(["| Path | Requirements | Confidence | Evidence |", "| --- | --- | --- | --- |"])
            for row in rows:
                edge_ids = [str(value) for value in row.get("evidence_edge_ids", []) if str(value)]
                selected_edges = [edges_by_id[edge_id] for edge_id in edge_ids if edge_id in edges_by_id]
                behavior_priority = {
                    "renders-returned-value": 0,
                    "renders-ui-state": 0,
                    "renders-caught-error": 0,
                    "captures-returned-value": 1,
                    "writes-ui-state": 1,
                    "catches-error": 1,
                    "calls-symbol": 2,
                    "imports-module": 3,
                    "loads-module": 3,
                    "tested-by": 4,
                }
                selected_edges.sort(key=lambda edge: behavior_priority.get(str(edge.get("kind")), 2))
                rendered_edge_ids.update(edge_ids)
                kinds = list(dict.fromkeys(scope_edge_phrase(row, edge) for edge in selected_edges if edge.get("kind")))
                strong = sum(str(edge.get("strength")) == "strong" for edge in selected_edges)
                if selected_edges:
                    relationship_text = "; ".join(kinds)
                    evidence_text = (
                        f"{strong} strong relationship edge(s) across "
                        f"{len(kinds)} distinct relationship type(s)"
                    )
                else:
                    relationship_text = "none"
                    evidence_text = ", ".join(row.get("reason_codes", [])) or "saved decision"
                if responsive:
                    fields = [
                        ("Requirements", ", ".join(row.get("requirement_ids", [])) or "none"),
                        ("Confidence", f"`{row.get('confidence')}`"),
                        ("Evidence", display_prose(evidence_text)),
                    ]
                    if selected_edges:
                        fields.append(("Relationship types", display_prose(relationship_text)))
                    if verbose and edge_ids:
                        fields.append(("Evidence edge IDs", ", ".join(f"`{edge_id}`" for edge_id in edge_ids)))
                    records.append((
                        f"`{row.get('path')}`",
                        fields,
                    ))
                else:
                    table_evidence = evidence_text
                    if selected_edges:
                        table_evidence += f"; relationship types: {relationship_text}"
                    lines.append(
                        f"| `{row.get('path')}` | {', '.join(row.get('requirement_ids', [])) or 'none'} | "
                        f"`{row.get('confidence')}` | {display_prose(table_evidence)} |"
                    )
            if responsive:
                append_stacked_records(lines, records)
        else:
            if responsive:
                append_stacked_records(lines, [("None assigned", [("Requirements", "none"), ("Confidence", "`none`"), ("Evidence", "no path assigned")])])
            else:
                lines.extend(["| Path | Requirements | Confidence | Evidence |", "| --- | --- | --- | --- |", "| none | none | `none` | no path assigned |"])
    proposed_proof: dict[str, dict[str, set[str]]] = {}
    for requirement in plan.get("requirement_matrix", []):
        if not isinstance(requirement, dict):
            continue
        requirement_id = str(requirement.get("display_id", "REQ"))
        contract = requirement.get("validation_contract", {})
        if not isinstance(contract, dict):
            continue
        commands = {str(value) for value in contract.get("commands", []) if str(value)}
        for path in contract.get("proposed_paths", []):
            if not str(path):
                continue
            entry = proposed_proof.setdefault(str(path), {"requirements": set(), "commands": set()})
            entry["requirements"].add(requirement_id)
            entry["commands"].update(commands)
    if proposed_proof:
        lines.extend([
            "", "### Proposed proof additions", "",
            "- Proposed new proof files; they become editable only after this exact plan is approved and only for validation evidence.",
            "",
        ])
        records = []
        for path, details in proposed_proof.items():
            records.append((
                f"`{path}`",
                [
                    ("Requirements", ", ".join(sorted(details["requirements"]))),
                    ("Access after approval", "create or edit as proof-only scope"),
                    ("Runnable command", " or ".join(f"`{value}`" for value in sorted(details["commands"]))),
                ],
            ))
        append_stacked_records(lines, records)
    if verbose:
        if rendered_edge_ids:
            lines.extend(["", "### Scope evidence details", ""])
            for edge_id in sorted(rendered_edge_ids):
                edge = edges_by_id.get(edge_id)
                if not isinstance(edge, dict):
                    continue
                source = candidate_paths.get(str(edge.get("from_candidate_id")), "unknown")
                target = candidate_paths.get(str(edge.get("to_candidate_id")), "unknown")
                reasons = ", ".join(str(value).replace("-", " ") for value in edge.get("reason_codes", []))
                kind = str(edge.get("kind", "relationship")).replace("-", " ")
                if source == target:
                    lines.append(
                        f"- `{edge_id}`: **in-file behavior evidence** - {kind} "
                        f"(`{edge.get('strength', 'unknown')}`) in `{source}`"
                        + (f"; {reasons}." if reasons else ".")
                    )
                else:
                    lines.append(
                        f"- `{edge_id}`: **{kind}** (`{edge.get('strength', 'unknown')}`), "
                        f"`{source}` -> `{target}`"
                        + (f"; {reasons}." if reasons else ".")
                    )
        lines.extend(["", "### Excluded candidates", ""])
        excluded = projection.get("excluded_candidates", [])
        if excluded:
            if responsive:
                append_stacked_records(lines, [
                    (
                        f"`{row.get('path')}`",
                        [
                            ("Repository role", f"`{row.get('candidate_role')}`"),
                            ("Status", f"`{row.get('status')}`"),
                            ("Reasons", display_prose(", ".join(row.get("reason_codes", [])) or "no saved reason")),
                        ],
                    )
                    for row in excluded
                ])
            else:
                lines.extend(["| Path | Repository role | Status | Reasons |", "| --- | --- | --- | --- |"])
                for row in excluded:
                    lines.append(
                        f"| `{row.get('path')}` | `{row.get('candidate_role')}` | `{row.get('status')}` | "
                        f"{display_prose(', '.join(row.get('reason_codes', [])) or 'no saved reason')} |"
                    )
        else:
            if responsive:
                lines.append("- No excluded candidates.")
            else:
                lines.extend(["| Path | Repository role | Status | Reasons |", "| --- | --- | --- | --- |", "| none | none | none | no excluded candidate |"])
        limits = projection.get("limits", {})
        limit_state = investigation.get("limit_state", {}) if isinstance(investigation.get("limit_state"), dict) else {}
        lines.extend([
            "",
            "### Investigation limits",
            "",
            f"- Files read: `{investigation.get('files_read', 0)}`; bytes read: `{investigation.get('bytes_read', 0)}`; relationship hops: `{investigation.get('relationship_hops', 0)}`.",
            f"- Decision reason: `{investigation.get('decision_reason', investigation.get('stop_reason', 'not-recorded'))}`; resolution failure: `{investigation.get('resolution_failure_reason') or 'none'}`.",
            f"- Read-loop termination: `{limit_state.get('termination_reason', 'not-recorded')}`; limit state: `{limit_state.get('state', 'not-recorded')}`.",
            f"- Read budgets: cache validation `{limit_state.get('cache_validation_files_read', 0)}`; broad `{limit_state.get('broad_files_read', 0)}/{limit_state.get('broad_file_limit', 'unknown')}`; relationship `{limit_state.get('relationship_files_read', 0)}/{limit_state.get('relationship_file_limit', 'unknown')}`; resolver config `{limit_state.get('config_files_read', 0)}/{limit_state.get('config_file_limit', 'unknown')}`.",
            f"- Graph source: `{graph_source if 'bounded-ephemeral-graph-built' in cache_reasons else 'persistent graph cache' if cache_status == 'fresh' else 'none'}`; persistent cache: `{cache_status}`; persistence: `{'not persisted' if 'ephemeral-graph-not-persisted' in cache_reasons else 'existing cache reused' if cache_status == 'fresh' else 'not applicable'}`.",
            f"- Caps: candidates `{limits.get('candidate_files', 'unknown')}`, initial reads `{limits.get('initial_file_reads', 'unknown')}`, escalation reads `{limits.get('escalation_file_reads', 'unknown')}`, cache validation reads `{limits.get('cache_validation_file_reads', 'unknown')}`, relationship reads `{limits.get('relationship_file_reads', 'unknown')}`, retained owners `{limits.get('retained_owners', 'unknown')}`, question options `{limits.get('scope_question_options', 'unknown')}`.",
            f"- Byte caps: per file `{limits.get('max_file_bytes', 'unknown')}`, total `{limits.get('max_total_read_bytes', 'unknown')}`.",
        ])
    return True

def target_root_from_goal(goal: str) -> str | None:
    """Extract one explicit local target root from user wording.

    URLs and relative document references are deliberately not roots.  A path
    is accepted only when nearby wording says it is where the change belongs;
    this prevents a reference repository or a document path from silently
    becoming the editable project.
    """
    return target_workspace.prompt_candidate(goal)


def resolve_target_root(goal: str, supplied_root: Path | None, host_workspace: Path | None = None, alias: str | None = None, aliases: dict[str, Path] | None = None) -> dict[str, Any]:
    """Resolve the planning root before Navigator discovers any files."""
    return target_workspace.resolve(goal, explicit_root=supplied_root, host_workspace=host_workspace, alias=alias, aliases=aliases)


def target_boundary_report(goal: str, resolution: dict[str, Any], command_prefix: str) -> dict[str, Any]:
    """Return a non-persisted report when the requested target cannot be read."""
    return {
        "goal": goal,
        "root": None,
        "command_prefix": command_prefix,
        "target_root": resolution,
        "target_boundary": True,
        "next_step": "Open the target repository in this host or rerun Start with an accessible --root path.",
    }


def render_host_interpretation_required_report(goal: str, resolved_host: str, command_prefix: str) -> dict[str, Any]:
    """Return a non-persisted report when a trusted agent host is active but no interpretation was provided.
    
    This blocks the Start process before scope discovery to prevent silent degradation to deterministic planning.
    """
    return {
        "goal": goal,
        "root": None,
        "command_prefix": command_prefix,
        "target_root": {
            "requested": "Agent-Host Contract",
            "status": "blocked",
            "reason": f"The active host `{resolved_host}` requires a typed host interpretation to proceed. No such interpretation was provided in the request.",
        },
        "target_boundary": True,
        "next_step": f"The agent must provide a typed host interpretation for `{resolved_host}` before a Planning Lock can be created.",
    }



def render_target_boundary_report(report: dict[str, Any]) -> str:
    target = report["target_root"]
    requested = str(target["requested"])
    return "\n".join(
        [
            "# TailTrail Start Plan",
            "",
            f"**Goal:** {display_prose(report['goal'])}",
            "",
            "## Target repository boundary",
            "",
            f"- Requested target: `{requested}`",
            f"- Status: **{target['status']}** - {display_prose(target['reason'])}.",
            "- No Planning Lock was created and no repository files, Git state, tests, scanners, or project commands were used.",
            "",
            "## Next step",
            "",
            "- Open that repository in the current host, or rerun with an accessible path:",
            f"  `{report['command_prefix']} start \"your goal\" --root \"{requested}\"`",
            "- If it is a reference-only repository, provide an accessible editable target with `--root` and keep the reference read-only.",
            "",
        ]
    )


def requested_technical_scope(goal: str) -> list[str]:
    """Return user-named delivery areas without claiming repository paths."""
    lowered = goal.lower()
    cues = (
        (("api", "contract"), "API and public contract"),
        (("service", "orchestration"), "service orchestration"),
        (("repository", "model"), "repository and authoritative state model"),
        (("inventory", "reservation", "allocation"), "inventory, allocation, and reservation effects"),
        (("payment", "charge", "refund"), "payment charge/refund idempotency"),
        (("notification", "publish"), "notification ordering and deduplication"),
        (("audit",), "immutable audit evidence"),
        (("unit", "integration", "contract", "behaviour", "behavior"), "unit, integration, contract, and behaviour proof"),
        (("metric", "observability"), "operational metrics and observability"),
        (("ci",), "CI evidence"),
        (("migration", "compatibility"), "migration and compatibility"),
        (("rollout", "rollback"), "rollout and rollback safety"),
        (("terraform", "infrastructure"), "infrastructure boundary: plan only; do not apply"),
    )
    return [label for terms, label in cues if any(term in lowered for term in terms)]


def target_fit_boundary_report(
    goal: str,
    root: Path,
    fit: dict[str, Any],
    command_prefix: str,
    planned: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a non-persisted, target-agnostic plan for a low-confidence workspace."""
    planned = planned or {}
    delivery = planned.get("guided_delivery", {}) if isinstance(planned, dict) else {}
    navigator_plan = planned.get("navigator", {}) if isinstance(planned, dict) else {}
    program = delivery.get("hands_free_program") if isinstance(delivery, dict) else None
    requirements = program.get("feature_requirements", []) if isinstance(program, dict) else navigator_plan.get("requirement_matrix", [])
    return {
        "goal": goal,
        "root": root.as_posix(),
        "command_prefix": command_prefix,
        "target_fit": fit,
        "target_fit_boundary": True,
        "requirements": requirements if isinstance(requirements, list) else [],
        "program": program if isinstance(program, dict) else None,
        "aidlc_mode": planned.get("aidlc_mode", {}) if isinstance(planned, dict) else {},
        "selected_features": delivery.get("selected", []) if isinstance(delivery, dict) else [],
        "technical_scope": requested_technical_scope(goal),
    }


def render_target_fit_boundary_report(report: dict[str, Any]) -> str:
    fit = report["target_fit"]
    root = str(report["root"])
    lines = [
        "# TailTrail Pre-Target Start Plan",
        "",
        f"**Goal:** {display_prose(report['goal'])}",
        "",
        "## Target confirmation",
        "",
        f"- Current workspace: `{root}`",
        f"- Status: **{fit['status']}** - {display_prose(fit['reason'])}.",
        "- TailTrail rejected the discovered file scope, but preserved the target-independent requirements and delivery design below.",
        "- No Planning Lock was created. Full AIDLC, implementation, tests, scanners, and Git changes have not started.",
    ]
    requirements = [item for item in report.get("requirements", []) if isinstance(item, dict)]
    if requirements:
        lines.extend(["", "## Requirement bifurcation", ""])
        for item in requirements:
            lines.append(requirement_line(item))
    technical_scope = [str(item) for item in report.get("technical_scope", [])]
    if technical_scope:
        lines.extend(["", "## Intended technical scope", ""])
        lines.extend(f"- {display_prose(item)}" for item in technical_scope)
    aidlc = report.get("aidlc_mode", {})
    if isinstance(aidlc, dict) and aidlc:
        mode = str(aidlc.get("mode", "unknown"))
        route_text = {
            "lite": "After target confirmation, local AIDLC Lite remains the requirement-clarification route; no official lifecycle stage is implied.",
            "off": "After target confirmation, AIDLC remains disabled and the approved Navigator requirement boundary governs implementation.",
            "standard": "After target confirmation, the pinned official Requirements Analysis stage owns questions and approved decisions.",
            "full": "After target confirmation, the pinned official lifecycle owns requirements, design, implementation, build/test, and handoff stages.",
        }.get(mode, "After target confirmation, TailTrail preserves the selected AIDLC authority route.")
        lines.extend([
            "",
            "## AIDLC route",
            "",
            f"- Requested mode: **{display_prose(mode)}**.",
            f"- Preflight state: `{aidlc.get('state', 'unavailable')}`.",
            f"- {route_text}",
            "- Question Orchestrator validates relevance and requirement traceability; TailTrail does not replace the official questionnaire.",
        ])
    features = [item for item in report.get("selected_features", []) if isinstance(item, dict)]
    if features:
        lines.extend(["", "## Selected TailTrail features", "", "| Feature | Use after target confirmation |", "| --- | --- |"])
        for item in features:
            lines.append(f"| {display_prose(item.get('name', 'TailTrail control'))} | {display_prose(item.get('why', 'Selected for this task.'))} |")
    program = report.get("program")
    if isinstance(program, dict):
        lines.extend(["", "## End-to-end delivery program", "", "Proposed dependency order:"])
        for index, stage in enumerate(program.get("dependency_order", []), start=1):
            lines.append(f"{index}. {display_prose(stage)}")
        lines.extend([
            "",
            f"- First active slice: {display_prose(program.get('first_active_slice', 'requirements only'))}",
            f"- Approval gate: {display_prose(program.get('approval_gate', 'target and requirements approval required'))}",
        ])
    candidates = fit.get("discovered_candidates", [])
    if candidates:
        lines.extend(["", "## Rejected workspace matches", ""])
        lines.append("- These paths were not accepted as implementation scope: " + ", ".join(f"`{path}`" for path in candidates) + ".")
    missing_changed = fit.get("missing_changed_paths", [])
    if missing_changed:
        lines.extend(["", "## Invalid explicit paths", ""])
        lines.append("- These `--changed` paths do not exist in the selected repository: " + ", ".join(f"`{path}`" for path in missing_changed) + ".")
    lines.extend([
        "",
        "## Next action",
        "",
        "- Open the application repository and rerun this same Start request there.",
        "- Or append an explicit target to the command you just ran:",
        "  `--root \"D:/absolute/path/to/target-project\"`",
        "- Once the target is confirmed, TailTrail reruns read-only impact mapping there, creates the Planning Lock, and continues through the selected AIDLC route.",
        "",
    ])
    return "\n".join(lines)


def delivery_run_signals(root: Path, run_id: str | None) -> dict[str, Any]:
    if not run_id:
        return {"status": "not-requested", "run_id": None, "correction_cycle": False, "recovery_risk": False, "drift": []}
    if Path(run_id).name != run_id:
        raise ValueError("run_id must be a single local run identifier; pass one exact `--run-id` value as returned by `tailtrail start \"<goal>\"`")
    directory = root / ".tailtrail" / "runs" / run_id
    if not directory.is_dir():
        return {"status": "missing", "run_id": run_id, "correction_cycle": False, "recovery_risk": False, "drift": []}
    feedback = sorted((directory / "feedback").glob("feedback-*.json"))
    checkpoints = sorted((directory / "checkpoints").glob("checkpoint-*.json"))
    drift: list[str] = []
    if checkpoints:
        try:
            checkpoint = json.loads(checkpoints[-1].read_text(encoding="utf-8"))
            drift = sorted({str(item.get("classification")) for item in checkpoint.get("drift", []) if isinstance(item, dict) and item.get("classification") in {"unchanged", "regressed", "new-drift", "needs-decision"}})
        except (OSError, json.JSONDecodeError):
            drift = ["unreadable-checkpoint"]
    recovery_paths = list((directory / "recovery").glob("plan-*.json")) + list((directory / "recovery" / "reconciliation").glob("assessment-*.json"))
    return {
        "status": "found", "run_id": run_id, "correction_cycle": bool(feedback) or bool(drift),
        "recovery_risk": bool(recovery_paths), "drift": drift,
        "evidence": [path.relative_to(root).as_posix() for path in [feedback[-1] if feedback else None, checkpoints[-1] if checkpoints else None, *recovery_paths] if path],
    }


def hands_free_requirements(goal: str) -> list[dict[str, str]]:
    """Turn a broad hands-free goal into an approval-ready, local requirement boundary."""
    lowered = goal.lower()

    # Choose the requested capability before interpreting preservation wording.
    # A programme that says "preserve cancellation" must not become a
    # cancellation programme merely because it also mentions inventory, refunds,
    # notifications, or audit records.
    amendment_cues = (
        "order amendment", "order-amendment", "amend order", "amendment",
        "change quantity", "change the quantity", "change delivery address",
        "delivery address", "order revision", "expected revision",
    )
    if any(cue in lowered for cue in amendment_cues):
        statements = [
            "Define amendment eligibility by fulfilment stage and preserve existing create-order and cancellation behavior.",
            "Maintain one authoritative order revision and reject stale concurrent amendment attempts.",
            "Allow only the approved quantity transition for each fulfilment stage and release only excess reserved inventory.",
            "Allow an authorized post-shipment delivery-address correction only with an audit reason while preserving product and quantity immutability.",
            "Recalculate the amendment amount and issue an additional charge or partial refund exactly once through an idempotent amendment action.",
            "Persist an immutable before/after amendment audit record with actor, reason, and revision identifiers.",
            "Send one customer amendment notification only after all required durable effects succeed.",
            "Update the API contract with explicit amendment success, validation, conflict, forbidden, and transient-failure behavior.",
            "Add focused unit, integration, contract, and behaviour evidence for amendment, concurrency, side-effect ordering, and preserved flows.",
        ]
        if any(word in lowered for word in ("migration", "compatibility", "legacy")):
            statements.append("Preserve compatible legacy order records and provide migration evidence for the revised order model.")
        if any(word in lowered for word in ("rollout", "terraform", "release", "operations", "metrics", "ci")):
            statements.append("Provide operational metrics, CI/reconciliation evidence, and staged rollout/rollback criteria without applying infrastructure in the local demo.")
        return [{"display_id": f"REQ-{index:02d}", "statement": statement} for index, statement in enumerate(statements, start=1)]

    statements: list[str] = []
    if "cancel" in lowered:
        statements.append("Define the cancellation eligibility rule and preserve non-cancellable order behavior.")
    if "stock" in lowered or "inventory" in lowered or "restock" in lowered:
        statements.append("Release inventory exactly once after an eligible cancellation succeeds.")
    if "refund" in lowered or "payment" in lowered:
        statements.append("Issue one refund for an eligible cancellation and preserve payment failure handling.")
    if "notification" in lowered or "notify" in lowered:
        statements.append("Send one cancellation notification only after the required cancellation effects succeed.")
    if "audit" in lowered:
        statements.append("Record an audit event with the cancellation outcome and relevant identifiers.")
    if "api" in lowered or "contract" in lowered or "endpoint" in lowered:
        statements.append("Update the API contract without weakening existing order behavior outside cancellation.")
    if "test" in lowered or "validation" in lowered:
        statements.append("Add focused unit, integration, contract, and behaviour evidence appropriate to the changed paths.")
    if "rollout" in lowered or "terraform" in lowered or "release" in lowered:
        statements.append("Provide rollout, rollback, and infrastructure-impact evidence; do not apply infrastructure in the local demo.")
    if not statements:
        statements = [
            "Break the requested outcome into independently verifiable feature requirements.",
            "Map each approved requirement to code paths, preservation rules, and computational evidence.",
        ]
    return [{"display_id": f"REQ-{index:02d}", "statement": statement} for index, statement in enumerate(statements, start=1)]


def _aidlc_intent(lowered: str) -> str:
    """Classify explicit natural-language AIDLC mode without relying on word order.

    This intentionally recognizes only a mode qualifier next to AIDLC. Generic
    words such as ``complete`` or ``no`` elsewhere in a product request must
    not silently change the lifecycle mode.
    """
    normalized = lowered.replace("ai-dlc", "aidlc")
    if "aidlc" not in normalized:
        return "none"
    if re.search(r"\b(without|skip|disable|no)\s+aidlc\b|\baidlc\s+(off|disabled)\b", normalized):
        return "opt-out"
    if re.search(r"\b(full|official|enterprise)\s+aidlc\b|\baidlc\s+(full|official|enterprise)\b", normalized):
        return "full"
    if re.search(r"\b(standard|medium|normal|regular)\s+aidlc\b|\baidlc\s+(standard|medium|normal|regular)\b", normalized):
        return "standard"
    return "requested"


NAVIGATOR_STANDARD_SIGNALS = (
    "regulated", "compliance", "multi-team", "production", "release",
    "rollout", "migration", "infrastructure", "terraform", "security",
    "operations", "programme", "program",
)
NAVIGATOR_CRITICAL_RISKS = {"regulated", "compliance", "production", "security", "migration"}


def navigator_standard_evidence(goal: str, plan: dict[str, Any]) -> dict[str, Any]:
    """Return a conservative, public explanation for Standard selection."""
    lowered = goal.casefold()
    risk_rows = [str(item).casefold() for item in plan.get("risk_indicators", [])]
    signals = sorted({
        word
        for word in NAVIGATOR_STANDARD_SIGNALS
        if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", lowered)
        or any(re.search(rf"(?<!\w){re.escape(word)}(?!\w)", row) for row in risk_rows)
    })
    critical_risks = sorted({
        marker
        for marker in NAVIGATOR_CRITICAL_RISKS
        if any(marker in row for row in risk_rows)
    })
    sufficiency = plan.get("requirement_sufficiency")
    if not isinstance(sufficiency, dict):
        sufficiency = plan.get("sufficiency") if isinstance(plan.get("sufficiency"), dict) else {}
    decisions = [
        row for row in sufficiency.get("material_decisions", [])
        if isinstance(row, dict)
    ]
    selected = (
        len(signals) >= 2
        or len(critical_risks) >= 2
        or (len(decisions) >= 2 and bool(signals or critical_risks))
    )
    return {
        "selected": selected,
        "signals": signals,
        "critical_risks": critical_risks,
        "material_decision_ids": [str(row.get("id")) for row in decisions if row.get("id")],
        "reason": (
            "Navigator found multiple consequential requirement or risk signals."
            if selected
            else "The task has at most one isolated material decision or consequential signal."
        ),
    }


def navigator_requirement_route(
    goal: str,
    requested: str | None,
    sufficiency: dict[str, Any],
    existing_route: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Choose scope, Lite questions, or Standard before scope discovery.
    
    If an existing_route is provided (e.g. from an automatic hands-free escalation),
    it is preserved to prevent silent degradation after interpretation.
    """
    routed = dict(sufficiency)
    decisions = list(routed.get("material_decisions", []))
    if not decisions:
        routed["state"] = "sufficient"
        routed["recommended_route"] = "scope"
        routed["routing_evidence"] = navigator_standard_evidence(
            goal, {"requirement_sufficiency": routed}
        )
        return routed
    
    # Preserve automatic routing if already decided
    if existing_route and existing_route.get("selection") in {"navigator-hands-free-escalation", "navigator-risk-routing"}:
        routed["recommended_route"] = existing_route["recommended_route"]
        routed["routing_selection"] = existing_route["routing_selection"]
        routed["routing_evidence"] = existing_route["routing_evidence"]
        routed["state"] = (
            "full-recommended" if routed["recommended_route"] == "aidlc-full"
            else "standard-recommended" if routed["recommended_route"] == "aidlc-standard"
            else "clarification-required"
        )
        return routed

    normalized = "standard" if requested == "medium" else requested
    evidence = navigator_standard_evidence(goal, {"requirement_sufficiency": routed})
    hands_free = any(
        phrase in goal.casefold()
        for phrase in ("hands-free", "hands free", "end-to-end", "end to end")
    )
    if normalized in {"off", "lite"}:
        route = "lite-questions"
        selection = "explicit-mode"
    elif normalized == "full":
        route = "aidlc-full"
        selection = "explicit-mode"
    elif normalized == "standard":
        route = "aidlc-standard"
        selection = "explicit-mode"
    elif hands_free and evidence["selected"]:
        route = "aidlc-full"
        selection = "navigator-hands-free-escalation"
    elif evidence["selected"]:
        route = "aidlc-standard"
        selection = "navigator-risk-routing"
    else:
        route = "lite-questions"
        selection = "navigator-bounded-clarification"
    routed["state"] = (
        "full-recommended"
        if route == "aidlc-full"
        else "standard-recommended"
        if route == "aidlc-standard"
        else "clarification-required"
    )
    routed["recommended_route"] = route
    routed["routing_selection"] = selection
    routed["routing_evidence"] = evidence
    return routed


def official_requirement_authority(
    root: Path,
    mode: dict[str, Any],
) -> dict[str, Any] | None:
    """Return the verified pre-scope official Requirements authority.

    The official pack owns requirement wording in Standard/Full mode.  This
    receipt is computed before repository scope work and later used to verify
    that a host proposal actually consumed the pinned governing rules.
    """
    selected = str(mode.get("mode", ""))
    compatibility = mode.get("compatibility")
    if selected not in {"standard", "full"} or not isinstance(compatibility, dict):
        return None
    manifest = compatibility.get("manifest")
    if not isinstance(manifest, str) or not manifest:
        raise ValueError("official AIDLC requirement authority has no verified compatibility manifest; run `tailtrail start \"<goal>\" --aidlc standard` for a new official run")
    references = official_aidlc_requirements.stage_contract(
        root,
        {"compatibility_manifest": manifest},
    )
    official = compatibility.get("official") if isinstance(compatibility.get("official"), dict) else {}
    return {
        "authority": "official-ai-dlc-pack",
        "mode": selected,
        "stage": "requirements",
        "references": references,
        "source": official.get("source"),
        "revision": official.get("revision"),
        "boundary": (
            "The verified official Requirements Analysis rules own requirement wording and material decisions. "
            "Navigator may map those requirements to local scope only after this receipt is satisfied."
        ),
    }


def validate_official_requirement_interpretation(
    interpreted: dict[str, Any],
    authority: dict[str, Any] | None,
) -> None:
    if authority is None:
        return
    if interpreted.get("authority") != "official-ai-dlc-pack":
        raise ValueError("Standard/Full AIDLC requires official Requirements authority before scope discovery; resubmit the same `tailtrail start \"<goal>\"` with `authority: official-ai-dlc-pack` matching the receipt")
    if interpreted.get("authority_mode") != authority["mode"]:
        raise ValueError("official AIDLC requirement interpretation mode does not match Navigator routing; resubmit the same `tailtrail start \"<goal>\"` with the mode from the receipt")
    if interpreted.get("authority_stage") != authority["stage"]:
        raise ValueError("official AIDLC requirement interpretation is not bound to the Requirements stage; resubmit the same `tailtrail start \"<goal>\"` with the stage from the receipt")
    if interpreted.get("authority_references") != authority["references"]:
        raise ValueError("official AIDLC requirement interpretation does not match the verified governing rules; resubmit the same `tailtrail start \"<goal>\"` with byte-identical `authority_references`")


def scope_question_precondition(
    interpreted_requirements: dict[str, Any] | None,
) -> dict[str, Any]:
    """Prove that implementation-scope questions are eligible to be shown.

    Scope clarification is downstream of requirement clarification.  Keeping
    this as a typed, reusable decision prevents a new Start exit or renderer
    from accidentally asking the user to choose an owner while material
    requirement decisions are still open.
    """
    interpreted = (
        interpreted_requirements
        if isinstance(interpreted_requirements, dict)
        else {}
    )
    sufficiency = interpreted.get("sufficiency")
    if not isinstance(sufficiency, dict):
        sufficiency = {}
    raw_decisions = sufficiency.get("material_decisions", [])
    if not isinstance(raw_decisions, list):
        raw_decisions = ["invalid-material-decision-contract"]
    decisions = [
        str(row.get("id") or "unidentified-material-decision")
        if isinstance(row, dict)
        else "invalid-material-decision-contract"
        for row in raw_decisions
    ]
    state = str(sufficiency.get("state") or interpreted.get("state") or "unknown")
    allowed = state == "sufficient" and not decisions
    return {
        "state": "eligible" if allowed else "deferred",
        "requirements_state": state,
        "open_material_decision_ids": decisions,
        "scope_question_allowed": allowed,
        "reason_code": (
            "requirements-sufficient"
            if allowed
            else "requirements-must-be-resolved-before-scope-question"
        ),
        "boundary": (
            "Implementation-scope investigation and questions may begin."
            if allowed
            else "Finish the saved requirement intake or AIDLC requirements route before implementation-scope investigation or questions."
        ),
    }


def aidlc_mode_selection(goal: str, requested: str | None, root: Path, plan: dict[str, Any], manifest: str | None) -> dict[str, Any]:
    """Choose the smallest lifecycle mode from explicit wording and task evidence.

    A user-provided flag wins. Standard and Full are official-pack-backed when
    available; an unavailable pack falls back transparently to TailTrail Lite.

    R1 calibration runway: the dual-gate decision is appended to
    .tailtrail/aidlc-mode-decisions.jsonl (best-effort, never fails Start).
    """
    calibration: dict[str, Any] = {}
    selected = _aidlc_mode_selection_inner(goal, requested, root, plan, manifest, calibration)
    if calibration:
        try:
            from metrics_extractor import append_mode_decision, build_mode_decision_entry

            append_mode_decision(
                root,
                build_mode_decision_entry(goal, requested, calibration, selected),
            )
        except Exception:  # noqa: BLE001 — calibration logging must never break Start
            pass
    return selected


def _aidlc_mode_selection_inner(goal: str, requested: str | None, root: Path, plan: dict[str, Any], manifest: str | None, calibration: dict[str, Any]) -> dict[str, Any]:
    """Dual-gate mode routing; publishes decision signals via ``calibration``.

    The calibration dict stays empty for explicit-flag / opt-out / explicit
    full / explicit standard paths (they do not exercise the quantitative
    thresholds, so they are excluded from the R1 calibration runway).
    """
    lowered = goal.lower()
    hands_free = any(phrase in lowered for phrase in ("hands-free", "hands free", "end-to-end", "end to end"))
    if requested:
        normalized = "standard" if requested == "medium" else requested
        selected = official_aidlc_bridge.preflight(root, normalized, manifest)
        selected["selection"] = "explicit-flag"
        selected["full_escalation"] = {"state": "not-evaluated", "reason": "An explicit mode flag takes precedence."}
        return selected
    intent = _aidlc_intent(lowered)
    if intent == "opt-out":
        selected = official_aidlc_bridge.preflight(root, "off", manifest)
        selected["selection"] = "explicit-natural-language-opt-out"
        selected["full_escalation"] = {"state": "not-evaluated", "reason": "The request explicitly opted out of AIDLC."}
        return selected
    if intent == "full":
        selected = official_aidlc_bridge.preflight(root, "full", manifest)
        selected["selection"] = "explicit-natural-language-full"
        selected["full_escalation"] = {"state": "selected", "reason": "The request explicitly asked for Full official AIDLC."}
        return selected
    if intent == "standard":
        selected = official_aidlc_bridge.preflight(root, "standard", manifest)
        selected["selection"] = "explicit-natural-language-standard"
        selected["full_escalation"] = {"state": "not-eligible", "reason": "The request explicitly asked for Standard AIDLC mode."}
        return selected
    routing = navigator_standard_evidence(goal, plan)
    signals = routing["signals"]

    # --- Dual-gate Dimension 2: quantitative scope-complexity metrics ---
    # Single definition shared with compute_re_evaluation (Phase 6):
    # evaluate_scope_signal owns every threshold comparison so the two
    # decision points cannot drift apart.
    from metrics_extractor import compute_complexity, evaluate_scope_signal

    complexity = compute_complexity(
        plan.get("likely_impacted_files", []),
        plan.get("scope_evidence"),
        root,
    )
    scope_signal, scope_floor_lite = evaluate_scope_signal(complexity)
    # Derive host-agent intent signal: when _aidlc_intent returns "requested" or "standard",
    # the user's natural-language goal already contains an AIDLC mode request
    # (the host agent reliably captures this; the keyword table is retired).
    keyword_signal = intent in ("requested", "standard")
    # R1 calibration runway: publish the decision signals for the mode-decision log.
    calibration.update({
        "intent": intent,
        "hands_free": hands_free,
        "keyword_signal": keyword_signal,
        "scope_signal": scope_signal,
        "scope_floor_lite": scope_floor_lite,
        "routing_selected": routing["selected"],
        "complexity": complexity,
    })
    # Dual-gate routing: host-agent intent OR quantitative scope signal → Standard.
    # scope_floor_lite stays published to calibration and the Phase 6
    # re-evaluation hook; it no longer vetoes an explicit mode request here.
    if intent == "none" and not hands_free and not routing["selected"] and not scope_signal:
        selected = official_aidlc_bridge.preflight(root, "lite", manifest)
        selected["selection"] = "default"
        selected["routing_evidence"] = routing
        selected["full_escalation"] = {"state": "not-eligible", "reason": "Navigator found no material evidence requiring stronger AIDLC routing."}
        return selected
    if hands_free and (routing["selected"] or scope_signal):
        selected = official_aidlc_bridge.preflight(root, "full", manifest)
        if selected.get("state") == "official-pack-unavailable-fallback":
            selected["full_escalation"] = {
                "state": "eligible-awaiting-compatible-pack",
                "signals": signals,
                "reason": "Navigator found programme-scale signals or scope-complexity evidence, but no compatible pinned official pack is installed; TailTrail Lite remains active. Full mode requires a verified pack and a new Full-mode Planning Lock; this run cannot be silently upgraded.",
            }
            return selected
        else:
            selected["selection"] = "navigator-hands-free-escalation"
            selected["full_escalation"] = {
                "state": "selected",
                "signals": signals,
                "reason": "Navigator found programme-scale signals or scope-complexity evidence and a compatible pinned official pack; Full execution still requires a new Full-mode Planning Lock and cannot silently upgrade an existing run.",
            }
            return selected
    # Dual-gate routing: host-agent intent OR quantitative scope signal → Standard.
    # An explicit bare "using AIDLC" request always counts: the scope floor only
    # tempers inferred escalation, never an explicit mode request. Without a
    # compatible pack the Standard preflight still falls back to Lite
    # transparently (requested_mode/state record the request).
    if keyword_signal:
        selected = official_aidlc_bridge.preflight(root, "standard", manifest)
        selected["selection"] = "explicit-natural-language-standard"
        selected["full_escalation"] = {"state": "not-eligible", "signals": signals, "reason": "Standard mode covers the requested AIDLC depth without a Full official lifecycle transition."}
    elif routing["selected"]:
        selected = official_aidlc_bridge.preflight(root, "standard", manifest)
        selected["selection"] = "navigator-risk-routing"
        selected["full_escalation"] = {"state": "not-eligible", "signals": signals, "reason": "Navigator found multiple consequential requirement or risk signals; Standard mode covers this depth without a Full official lifecycle transition."}
    elif scope_signal:
        selected = official_aidlc_bridge.preflight(root, "standard", manifest)
        selected["selection"] = "scope-complexity-standard"
        selected["full_escalation"] = {"state": "not-eligible", "signals": signals, "reason": "Quantitative scope-complexity metrics exceeded the Standard escalation threshold; Standard mode covers this depth without a Full official lifecycle transition."}
    elif hands_free:
        selected = official_aidlc_bridge.preflight(root, "standard", manifest)
        selected["selection"] = "hands-free-default"
        selected["full_escalation"] = {"state": "not-eligible", "signals": signals, "reason": "Hands-free mode selected Standard AIDLC; no programme-scale signals were found for Full escalation."}
    else:
        selected = official_aidlc_bridge.preflight(root, "lite", manifest)
        selected["selection"] = "default"
        selected["full_escalation"] = {"state": "not-eligible", "signals": signals, "reason": routing["reason"]}
    selected["routing_evidence"] = routing
    selected["complexity_metrics"] = complexity
    return selected


def aidlc_mode_features(mode: str) -> dict[str, list[str]]:
    """Describe the mode-owned controls; task-selected harnesses remain separate."""
    common = [
        "Navigator planning and Planning Lock",
        "Task-selected impact, requirement, testing, and review controls",
        "Explicit approval before implementation",
    ]
    if mode == "lite":
        return {"included": [*common, "Local AIDLC Lifecycle Lite only when Navigator selects it", "Question Orchestrator context, quality, and requirement traceability"], "not_included": ["Mandatory AIDLC requirements workshop", "Official pack verification or bridge identity"]}
    if mode == "standard":
        return {"included": [*common, "Verified official AI-DLC Requirements Analysis rules loaded by the host", "Question Orchestrator grounding, quality, and requirement traceability", "Host-generated official questions with options, TailTrail recommendations, and reasoning", "Canonical approved anchor and requirement-linked execution handoff"], "not_included": ["Full official lifecycle stages after requirements"]}
    if mode == "full":
        return {"included": [*common, "Phase A pinned-pack compatibility verification", "Full official AI-DLC lifecycle rules loaded by the host", "Question Orchestrator grounding, quality, and requirement traceability", "Host-generated official questions with options, TailTrail recommendations, and reasoning", "TailTrail anchor frozen from approved official requirement references and decisions", "After approval: receipt-driven official runtime attachment with ordered resume, redo, jump, and recovery history"], "not_included": ["TailTrail-generated substitute questions or silent local fallback"]}
    return {"included": [*common, "AIDLC lifecycle routing disabled for this run"], "not_included": ["Local AIDLC Requirements stage", "Official pack verification and bridge identity"]}


def guided_delivery(plan: dict[str, Any], goal: str, changed: list[str], root: Path, run_id: str | None = None) -> dict[str, Any]:
    """Choose the smallest delivery harness sequence after Navigator planning.

    This is a local routing decision, not an executor. The host/agent remains
    responsible for implementation after the user approves the plan.
    """
    lowered = goal.lower()
    tasks = {str(item).lower() for item in plan.get("task_types", [])}
    risks = {str(item).lower() for item in plan.get("risk_indicators", [])}
    hands_free = any(phrase in lowered for phrase in ("hands-free", "hands free", "end-to-end", "end to end"))
    canonical_requirement_set = plan.get("canonical_requirements", {}) if isinstance(plan.get("canonical_requirements"), dict) else {}
    interpretation = plan.get("requirement_interpretation", {}) if isinstance(plan.get("requirement_interpretation"), dict) else {}
    # A deterministic parse always produces some placeholder requirement rows
    # even for a bare "task 1 and task 2" hands-free goal; only a host-assisted
    # interpretation backed by an actually-inspected artifact means the
    # requirements (and the source document) are genuinely already processed.
    canonical_requirements_resolved = interpretation.get("source") == "host-assisted" and bool(interpretation.get("artifact_evidence"))
    multiple_requirements = len(plan.get("requirement_matrix", [])) > 1
    ui_change = navigator.core.ui_change_requested(goal, changed)
    scope_projection = navigator_scope.role_projection(plan.get("scope_evidence", {}))
    implementation_owners = [
        str(row.get("path"))
        for row in scope_projection.get("implementation_owners", [])
        if isinstance(row, dict) and row.get("path")
    ]
    cohesive_ui_slice = multiple_requirements and ui_change and len(implementation_owners) == 1
    tiny = plan.get("recommended_workflow") == ["lean"] and not hands_free and not multiple_requirements
    semantic_goal = lowered
    frame = plan.get("requirement_query_frame", {}) if isinstance(plan, dict) else {}
    if isinstance(frame, dict):
        for requirement in frame.get("requirements", []):
            if not isinstance(requirement, dict):
                continue
            for literal in requirement.get("quoted_literals", []):
                semantic_goal = re.sub(re.escape(str(literal).casefold()), " ", semantic_goal)
    broad = hands_free or len(changed) > 1 or any(
        word in semantic_goal
        for word in ("feature", "implement", "workflow", "service", "endpoint", "api", "migration")
    )
    user_facing = behaviour_planning.selected_for(goal, plan.get("likely_impacted_files", []))
    run = delivery_run_signals(root, run_id)
    selected: list[dict[str, str]] = []
    later: list[dict[str, str]] = []

    def add(name: str, why: str) -> None:
        selected.append({"name": name, "why": why})

    def defer(name: str, when: str) -> None:
        later.append({"name": name, "when": when})

    if tiny:
        add("Lean delivery", "narrow, low-risk task; preserve the existing small-diff workflow")
        stages = ["inspect the exact target", "implement the smallest change", "run focused proof", "report completion"]
    else:
        add("Canonical requirements", "freeze the requirement boundary approved in this Start Plan before source changes")
        interpreted = plan.get("requirement_interpretation", {})
        if (
            "aidlc_requirements" in plan.get("recommended_workflow", [])
            or (isinstance(interpreted, dict) and interpreted.get("source") == "host-assisted")
        ):
            add("Question Orchestrator", "trace requirement interpretation and surface material questions before approval; after approval it may trace implementation questions but cannot rewrite approved requirements")
        add("Requirement Completion Harness", "map the requirement to code, preservation rules, and proof")
        if changed or broad:
            add("Requirement-to-Impact Map", "trace likely files, callers, and focused tests before implementation")
        add("Evidence-Aware Testing", "choose focused proof before claiming the requirement is complete")
        if "test_precision" in plan.get("recommended_workflow", []):
            add("Test Precision Planner", "select the focused regression path, runnable command, negative cases, and preservation proof required by this workflow")
        if broad:
            add("Architecture Fitness Harness", "multi-file or service/API scope can miss callers or change the wrong layer")
        if user_facing:
            add("Behaviour Harness", "the task names a user-facing/API/workflow outcome that needs flow evidence")
        if ui_change:
            add("UI Consistency Guardrail", "UI work must reuse the repository's existing components, tokens, layout, responsive, and accessibility conventions")
        if "refactor" in tasks:
            add("Maintainability Harness", "confirm the change did not add duplicate logic or unnecessary abstraction")
        if hands_free:
            add("Program Delivery Harness", "explicit hands-free/end-to-end request needs feature ordering and resume state")
        stages = [
            "approve requirements and scope",
            "inspect the approved implementation owner and inspection paths to confirm the exact behavior branch",
            "implement the approved smallest change",
            "run the approved validation commands",
            "issue one completion report",
        ]
        if cohesive_ui_slice:
            stages = [
                "approve the requirement matrix and shared UI scope",
                f"treat all linked requirements as one cohesive UI slice owned by {implementation_owners[0]}",
                "inspect the existing UI system and nearest comparable screen; reuse its established patterns",
                "create the approved page-level proof and use its resolved runnable command",
                "implement the shared UI behavior atomically while retaining requirement-level traceability",
                "run the linked proof against every requirement and preservation rule",
                "reconcile the cohesive slice in one completion report",
            ]
        elif multiple_requirements:
            stages = ["approve the segregated requirement matrix and scope", "order requirements by dependency and select the first active requirement", "map and implement one approved requirement at a time", "record requirement-linked proof and drift at each checkpoint", "reconcile every requirement row in one completion report"]
        if ui_change and not cohesive_ui_slice:
            stages.insert(2, "inspect the approved UI implementation and reuse its established patterns")
            stages.insert(3, "resolve the exact project-owned component or behaviour test and command before the first source edit")
        if hands_free:
            stages = (
                [
                    "confirm the already-resolved requirement set and dependency order",
                    "map and implement one approved requirement at a time",
                    "run selected computational checks at each checkpoint",
                    "reconcile against the full approved requirement set",
                ]
                if canonical_requirements_resolved
                else ["propose feature requirements and dependency order", "approve the program anchor and first active slice", "map and implement one approved slice at a time", "run selected computational checks at each checkpoint", "reconcile against the full approved program anchor"]
            )

    if run["correction_cycle"]:
        add("Context Continuity Harness", "the selected run has a feedback packet or unresolved checkpoint drift: " + ", ".join(run["drift"] or ["feedback packet"]))
        add("Bounded Correction", "use the active requirement and evidence gap for one correction cycle before re-checking completion")
        stages = ["load current requirement evidence", "render continuity packet", "apply one bounded correction", "rerun selected computational checks", "issue updated completion report"]
    if run["recovery_risk"]:
        add("Git Readiness / Recovery Boundary", "the selected run has a recovery plan or reconciliation assessment; preserve task ownership before any recovery action")
        stages.insert(0, "verify the task recovery boundary")

    if not run["correction_cycle"]:
        defer("Context Continuity Harness", "a correction cycle, repeated evidence gap, scope drift, recovery, feature transition, or rejected requirement occurs; pass --run-id to evaluate that run")
    if not run["recovery_risk"]:
        defer("Safe Git Recovery", "the selected task has recovery risk, a failed bounded correction, or explicit rollback need; pass --run-id to evaluate that run")
    defer("Higher-Tier Testing", "the selected evidence profile requires integration, contract, E2E, infrastructure, or release confidence")
    if not hands_free:
        defer("Program Delivery Harness", "the user explicitly asks for hands-free or end-to-end multi-feature delivery")
    if not user_facing:
        defer("Behaviour Harness", "the approved requirement includes a user-facing, API, or journey contract")
    if ui_change:
        defer("Visual Regression Evidence", "the repository already has a project-owned visual test, or the approved task explicitly requires browser/screenshot proof; TailTrail will not add a visual-test dependency by default")
    if not broad:
        defer("Architecture Fitness Harness", "the approved scope expands beyond a narrow one-file change or adds callers/layers")
    if not risks.intersection({"auth/security", "secrets", "security", "secrets/token", "dependency", "production", "regulated", "data migration"}):
        defer("Security / release controls", "the approved task introduces auth, secrets, dependency, migration, production, or release risk")

    hands_free_program = None
    if hands_free:
        canonical = canonical_requirement_set
        canonical_features = [
            dict(row)
            for row in canonical.get("requirements", [])
            if isinstance(row, dict) and row.get("statement")
        ]
        hands_free_program = {
            "status": "proposed",
            "source_goal": goal,
            "canonical_requirement_set_fingerprint": str(canonical.get("fingerprint", "")),
            "feature_requirements": canonical_features,
            "dependency_order": (
                [
                    "Map and implement the first approved requirement",
                    "Continue through the remaining approved requirements in dependency order",
                    "Cross-requirement integration proof and completion reconciliation",
                ]
                if canonical_requirements_resolved
                else [
                    "Requirement and acceptance breakdown",
                    "Read-only impact mapping and reusable-pattern discovery",
                    "First independently verifiable implementation slice",
                    "Remaining slices in dependency order",
                    "Cross-slice integration proof and completion reconciliation",
                ]
            ),
            "first_active_slice": (
                "Requirements are already resolved from the approved interpretation; the first active slice implements the smallest independently verifiable requirement in that set, not requirement gathering."
                if canonical_requirements_resolved
                else "Requirement gathering and program-anchor proposal only; no source implementation is active yet."
            ),
            "approval_gate": (
                "Approve the already-resolved requirement set, dependency order, and first active slice before implementation begins."
                if canonical_requirements_resolved
                else "Approve the proposed feature requirements, dependency order, and first active slice before implementation begins."
            ),
        }

    return {
        "mode": "lean" if tiny else "guided-delivery",
        "selected": selected,
        "required_later": [
            {
                "name": "Focused testing and validation",
                "when": "after every approved implementation or correction, before completion",
                "why": "prove the changed behavior, required preservation cases, and regression boundary with factual computational evidence",
            },
            {
                "name": "Canonical completion and closure",
                "when": "after all required tests and selected Harness checks have factual results",
                "why": "prevent completion while required evidence is missing, unavailable, or failing",
            },
        ],
        "conditional_controls": later,
        "activated_later": later,
        "stages": stages,
        "run_signals": run,
        "approval_required": True,
        "approval_prompt": "Approve this guided delivery plan. Implement only the approved scope, run the selected proof, and return one completion report with unresolved evidence clearly named.",
        "execution_boundary": "Start selects and sequences TailTrail controls. It does not itself edit source, run tests, or invoke an implementation agent; those actions begin only after explicit approval.",
        "hands_free_program": hands_free_program,
        "slice_strategy": {
            "mode": "cohesive-ui-slice" if cohesive_ui_slice else "requirement-sequenced" if multiple_requirements else "single-requirement",
            "implementation_owner": implementation_owners[0] if cohesive_ui_slice else None,
            "requirement_ids": [
                str(row.get("display_id"))
                for row in plan.get("requirement_matrix", [])
                if isinstance(row, dict) and row.get("display_id")
            ],
            "boundary": (
                "Requirements sharing one proven UI owner are implemented atomically as one slice while evidence and closure remain requirement-linked."
                if cohesive_ui_slice
                else "Requirement ordering remains explicit because one shared implementation owner was not proven."
            ),
        },
    }


def approx_tokens(chars: int) -> int:
    return start_posture.approx_tokens(chars, APPROX_CHARS_PER_TOKEN)


def file_chars(path: Path) -> int:
    return start_posture.file_chars(path)


def existing_file_tokens(root: Path, paths: list[str]) -> tuple[int, list[dict[str, Any]]]:
    return start_posture.existing_file_tokens(root, paths, APPROX_CHARS_PER_TOKEN)


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


def apply_requirement_scope_evidence(
    plan: dict[str, Any],
    authority: dict[str, Any] | None = None,
) -> None:
    """Project one verified scope decision into each authority requirement.

    The requirement row remains authority-owned. TailTrail adds a path-role
    mapping by reference and never rewrites imported/official IDs, wording, or
    source revisions.
    """
    evidence = plan.get("scope_evidence", {})
    matrix = plan.get("requirement_matrix", [])
    if not isinstance(evidence, dict) or not isinstance(matrix, list):
        return
    # Some advisory-only Navigator routes (for example an Evaluation Harness
    # evidence query in an empty repository) intentionally have no local scope
    # decision.  Preserve that legacy no-scope path when no external authority
    # is being mapped.  Imported/official requirements must never silently lose
    # their local scope binding, so those routes remain strict.
    if not evidence:
        if authority is not None:
            raise ValueError("authority requirement mapping requires valid v2 scope evidence; run `tailtrail start \"<goal>\" --aidlc standard` for a new official run")
        return
    mappings = navigator_scope.authority_requirement_mappings(
        evidence,
        [row for row in matrix if isinstance(row, dict)],
        authority=authority,
    )
    by_authority_id = {
        str(row.get("authority_requirement_id")): row for row in mappings
    }
    quality = plan.get("scope_quality", {}) if isinstance(plan.get("scope_quality"), dict) else {}
    for index, row in enumerate(matrix, start=1):
        if not isinstance(row, dict):
            continue
        authority_id = str(row.get("display_id") or row.get("requirement_id") or f"REQ-{index:02d}")
        scope = by_authority_id.get(authority_id)
        if not isinstance(scope, dict):
            continue
        owners = [str(value) for value in scope.get("implementation_owners", []) if str(value)]
        inspection = [str(value) for value in scope.get("inspection_paths", []) if str(value)]
        proof = [str(value) for value in scope.get("proof_paths", []) if str(value)]
        accepted = [str(value) for value in quality.get("accepted_paths", []) if str(value)]
        if quality.get("mode") == "supporting-assets-only":
            query_terms = {str(value).lower() for value in scope.get("query_terms", [])}
            wanted_role = "test" if query_terms & {"test", "tests", "regression", "coverage"} else "documentation" if query_terms & {"readme", "documentation", "docs", "changelog", "markdown"} else None
            candidate_roles = {
                str(candidate.get("path")): str(candidate.get("role"))
                for candidate in plan.get("scope_candidates", []) if isinstance(candidate, dict)
            }
            editable = [path for path in accepted if wanted_role is None or candidate_roles.get(path) == wanted_role]
        elif quality.get("mode") in {"test-only", "documentation-only"}:
            editable = accepted
        else:
            editable = owners
        row["likely_paths"] = list(dict.fromkeys(editable))
        row["scope_evidence"] = {
            "state": "resolved" if scope.get("mapping_state") == "mapped" and editable else "unresolved",
            "implementation_owners": owners,
            "inspection_paths": inspection,
            "proof_paths": proof,
            "decision_fingerprint": evidence.get("decision_fingerprint"),
            "authority_requirement_id": scope.get("authority_requirement_id"),
            "local_scope_requirement_ids": list(scope.get("local_scope_requirement_ids", [])),
            "mapping_reason": scope.get("mapping_reason"),
            "authority": dict(scope.get("authority", {})),
            "boundary": scope.get("boundary"),
        }
        contract = row.setdefault("validation_contract", {"state": "required", "tiers": ["unit"]})
        if isinstance(contract, dict):
            contract["candidate_paths"] = proof
        evidence_plan = row.setdefault("evidence_plan", [])
        if isinstance(evidence_plan, list) and proof:
            statement = "Run focused proof: " + ", ".join(proof)
            if statement not in evidence_plan:
                evidence_plan.append(statement)
    if authority is not None:
        unresolved = [
            str(row.get("authority_requirement_id"))
            for row in mappings
            if row.get("mapping_state") != "mapped" or not row.get("implementation_owners")
        ]
        plan["authority_scope"] = {
            "schema_version": "1",
            "type": "tailtrail-authority-scope-mapping",
            "authority": dict(authority),
            "decision_fingerprint": evidence.get("decision_fingerprint"),
            "status": "resolved" if not unresolved else "unresolved",
            "blocking": bool(unresolved),
            "unresolved_requirement_ids": unresolved,
            "requirements": mappings,
            "boundary": "The external requirement authority remains unchanged. TailTrail maps only evidence-backed local path roles and blocks implementation handoff when that mapping is unresolved.",
        }


def token_posture(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    return start_posture.token_posture(root, plan, LARGE_CONTEXT_FILES, APPROX_CHARS_PER_TOKEN)


def token_estimate_lines(token: dict[str, Any], *, detailed: bool = True) -> list[str]:
    """Render a compact planning estimate, with accounting only in verbose mode."""
    if token.get("estimate_available") is False:
        return [
            f"- **Token estimate unavailable** \u2014 implementation-ownership scope is `{token.get('scope_state', 'unresolved')}`, not resolved; an estimate over the wrong or incomplete file set would not be trustworthy.",
            "- Major techniques: none evidenced until scope is resolved.",
        ]
    if token.get("forecast_available"):
        lines = [
            f"- Planned TailTrail working set: approximately "
            f"`{token.get('planned_working_set_tokens', 0)}` tokens "
            f"(`{token.get('forecast_confidence', 'medium')}` confidence)."
        ]
        lines.append(
            f"- Estimated reduction versus full scoped files: "
            f"`{token.get('estimated_reduction_percent', 0)}%`."
        )
    else:
        lines = [
            "- Planned TailTrail working set: **not calculable** (`low` confidence).",
            f"- Full scoped-file ceiling: approximately `{token.get('scoped_file_ceiling_tokens', token.get('used_tokens', 0))}` tokens.",
        ]
    techniques = [str(value) for value in token.get("saving_techniques", []) if str(value)]
    lines.append(
        f"- Major techniques: {', '.join(techniques) if techniques else 'none evidenced for this plan'}."
    )
    if not detailed:
        return lines

    if token.get("forecast_confidence") == "medium":
        lines.append(
            f"- Confidence reason: {token.get('forecast_confidence_reason', 'one or more bounded slices lack an exact behavior-and-symbol anchor')}."
        )

    if token.get("forecast_available"):
        # The compact section above already showed the ceiling when a forecast
        # was not available; repeating it here (next to a breakdown that only
        # covers bounded slices, not full file bodies) made the two numbers
        # look like they should match when they measure different things.
        lines.extend([
            f"- Full scoped-file ceiling: approximately `{token.get('scoped_file_ceiling_tokens', token.get('baseline_tokens', 0))}` tokens "
            f"across `{token.get('used_file_count', len(token.get('used_files', [])))}` scoped file(s).",
            "- Purpose breakdown: " + ", ".join(
                f"{purpose} `{tokens}`"
                for purpose, tokens in token.get("purpose_breakdown", {}).items()
                if int(tokens) > 0
            ) + ".",
        ])
    largest = token.get("largest_used_file")
    if isinstance(largest, dict) and largest.get("path"):
        sliced_paths = {str(row.get("path")) for row in token.get("context_slices", []) if isinstance(row, dict)}
        note = (
            "" if str(largest["path"]) in sliced_paths
            else " (no planned slice recorded for it yet; it is counted at its full body size until a bounded slice is resolved)"
        )
        lines.append(
            f"- Largest scoped file: `{largest['path']}` at approximately "
            f"`{largest.get('approx_tokens', 0)}` tokens{note}."
        )
    lines.extend([
        f"- Repository inventory ceiling (informational only): approximately `{token.get('repository_ceiling_tokens', 0)}` tokens "
        f"across `{token.get('repository_file_count', 0)}` relevant file(s).",
        f"- Repository boundary: {token.get('repository_boundary')}",
    ])
    slices = [row for row in token.get("context_slices", []) if isinstance(row, dict)]
    if slices:
        lines.extend(["", "### Planned context slices", ""])
        for row in slices:
            location = (
                f"lines `{row.get('start_line')}-{row.get('end_line')}`"
                if row.get("start_line") is not None and row.get("end_line") is not None
                else "range unresolved"
            )
            symbols = ", ".join(f"`{value}`" for value in row.get("symbols", [])) or "none"
            lines.append(
                f"- `{row.get('path')}` - {location}; purpose `{row.get('purpose')}`; "
                f"confidence `{row.get('confidence')}`; symbols {symbols}."
            )
            if row.get("confidence") == "medium":
                lines.append(
                    "  - Confidence reason: "
                    + str(
                        row.get("confidence_reason")
                        or "a bounded range was resolved, but exact behavior-and-symbol anchoring is incomplete"
                    )
                )
            lines.append(f"  - Expansion: {row.get('expansion_trigger')}")
    lines.append(
        "- Exact run usage: not knowable during planning. The Completion Report shows the "
        "host/API token total when telemetry is linked to this run."
    )
    lines.append(
        "- Baseline comparison: optional. It requires a separately recorded run of the same task "
        "without TailTrail or with AIDLC, using the same provider/model; TailTrail does not create that baseline automatically."
    )
    lines.append(
        "- Evidence: planned slices are local context accounting, not actual model/API usage."
    )
    return lines


def learning_quality(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    tailtrail = root / ".tailtrail"
    events = tailtrail / "learning-events.jsonl"
    v3_events = tailtrail / "learning-v3" / "events.jsonl"
    index = tailtrail / "learning-index.md"
    refresh_actions = tailtrail / "learning-refresh-actions.json"
    matches = []
    use_proposal = plan.get("learning_use_proposal")
    if isinstance(use_proposal, dict):
        raw_matches = use_proposal.get("matches", [])
        if isinstance(raw_matches, list):
            matches = raw_matches[:3]
    elif isinstance(plan.get("graph_learning"), dict):
        raw_matches = plan["graph_learning"].get("matches", [])
        if isinstance(raw_matches, list):
            matches = raw_matches[:3]
    proposal_approval = use_proposal.get("approval", {}) if isinstance(use_proposal, dict) else {}
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
    if index.is_file() and (events.is_file() or v3_events.is_file()) and not refresh_actions.is_file():
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
        "events_exist": events.is_file() or v3_events.is_file(),
        "refresh_actions_exist": refresh_actions.is_file(),
        "refresh_action_count": action_count,
        "blocking_refresh_actions": blocking_actions,
        "surfaced_matches": len(matches),
        "approval_required": bool(proposal_approval.get("required") or plan.get("learning_approval")),
        "review_recommended": review_recommended,
        "review_reason": review_reason,
        "review_command": "python3 scripts/tailtrail.py learn review --root .",
        "rule": "Learnings are advisory only. Use, ignore, or edit surfaced learnings before implementation.",
    }


def setup_posture(root: Path, command_prefix: str) -> dict[str, Any]:
    return start_posture.setup_posture(root, command_prefix, ROOT)


def review_posture(plan: dict[str, Any], command_prefix: str) -> dict[str, Any]:
    return start_posture.review_posture(plan, command_prefix)


def harness_posture(root: Path, command_prefix: str) -> dict[str, Any]:
    return start_posture.harness_posture(root, command_prefix)


def bootstrap_posture(plan: dict[str, Any], command_prefix: str) -> dict[str, Any]:
    return start_posture.bootstrap_posture(plan, command_prefix)


def evaluation_posture(goal: str, plan: dict[str, Any], command_prefix: str) -> dict[str, Any]:
    return start_posture.evaluation_posture(goal, plan, command_prefix, EVALUATION_TRIGGER_WORDS)


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
    use_proposal = plan.get("learning_use_proposal")
    proposal_approval = use_proposal.get("approval", {}) if isinstance(use_proposal, dict) else {}
    if plan.get("learning_approval") or proposal_approval.get("required"):
        actions.append(
            {
                "action": "learning-approval",
                "label": "Choose whether the surfaced Learning V3 proposal may influence the plan.",
                "when": "Use only when a project-framed Learning Use Proposal has eligible matches.",
                "prompt": "Choose use selected learnings, ignore all learnings, or edit selected learning IDs. Default to do-not-use. Current source, tests, scanner evidence, policy, and guardrails win.",
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


def deterministic_requirement_parser_contract(goal: str) -> dict[str, Any] | None:
    """Return a concrete contract for the known multiline REQ split defect."""
    lowered = goal.lower()
    if not all(term in lowered for term in ("multiline", "requirement", "split")):
        return None
    normalized_example = re.sub(r"[`*]+", "", goal)
    normalized_example = re.sub(r"(?m)^\s*[-*]\s*", "", normalized_example)
    observed_match = re.search(
        r"\bREQ-01\b\s*:?\s*(?P<first>.+?)\s+(?:and\s+)?\bREQ-02\b\s*:?\s*(?P<second>.+?)(?=\s+(?:Expected\s+one\s+requirement|There\s+are\s+2\s+requirements|These\s+should\s+be\s+one\s+requirement|##)|$)",
        normalized_example,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if observed_match:
        first = observed_match.group("first").strip(" \t\r\n-:")
        second = observed_match.group("second").strip(" \t\r\n-:")
    else:
        first = "Add delivery-address validation without breaking valid."
        second = "Addresses."
    return {
        "profile": "deterministic-requirement-parser",
        "input": first + "\n" + second,
        "observed": [first, second],
        "expected": [f"{first} {second}"],
        "preservation_cases": [
            "Explicit Markdown bullets remain separate requirements.",
            "Explicit numbered items remain separate requirements.",
            "Blank-line-separated paragraphs remain separate requirements.",
            "Semicolon-separated and same-line completed requirement sentences retain their existing boundaries.",
        ],
    }


def generated_output_duplication_profile(goal: str) -> dict[str, Any] | None:
    """Tailor Debug planning when generated or rendered content repeats.

    This profile is evidence framing only. It never treats the supplied output
    reference as inspected evidence or guesses an implementation owner.
    """
    lowered = goal.lower()
    output_terms = ("report", "output", "render", "rendered", "html", "document", "page")
    duplication_terms = ("repeat", "repeating", "repeated", "duplicate", "duplicated", "duplication")
    if not any(term in lowered for term in output_terms) or not any(term in lowered for term in duplication_terms):
        return None
    subject = "generated report" if "report" in lowered else "generated output"
    numbered = re.search(r"\b(?:first\s+)?(?P<count>\d+)\s+(?P<unit>steps?|rows?|items?|entries?|records?)\b", goal, re.IGNORECASE)
    if numbered:
        count = numbered.group("count")
        unit = numbered.group("unit").lower()
        item_boundary = f"the first {count} {unit}"
    else:
        item_boundary = "each intended item"
    reference_supplied = bool(
        re.search(r"\bfile://\S+", goal, re.IGNORECASE)
        or re.search(r"\b[^\s]+\.(?:html?|json|xml|txt|log)(?:\?\S+)?", goal, re.IGNORECASE)
    )
    sorting_supplied = bool(re.search(r"[?&]sort=", goal, re.IGNORECASE))
    preservation = [
        f"Preserve all non-repeated {subject} content, ordering, result/status values, and details.",
    ]
    if sorting_supplied:
        preservation.append("Preserve the supplied report view's supported sorting behavior.")
    preservation.append("Do not call production systems or external providers during planning.")
    return {
        "profile": "generated-output-duplication",
        "subject": subject,
        "item_boundary": item_boundary,
        "reference_supplied": reference_supplied,
        "statement": (
            f"Prove and correct why {item_boundary} repeat in the {subject} so they appear exactly once, "
            "while preserving all other report content and behavior."
        ),
        "expected_boundary": f"{item_boundary.capitalize()} appear exactly once in the {subject}.",
        "acceptance_criteria": [
            f"An approved reproduction demonstrates that {item_boundary} repeat in the {subject}.",
            f"After correction, {item_boundary} appear exactly once and retain their intended order.",
            "All non-repeated content, result/status values, details, and supported view behavior remain unchanged.",
            "The proven cause is supported by saved experiment evidence before correction scope is approved.",
        ],
        "preserve_rules": preservation,
        "material_unknowns": [
            f"the exact labels and repetition count for {item_boundary}",
            f"the deterministic generator command, fixture, or bounded procedure that produced the {subject}",
            "whether duplication begins in input data, aggregation, generation, or rendering",
            "the confirmed implementation owner and direct proof path",
        ],
        "reproduction_questions": [
            f"Confirm the exact labels in {item_boundary} and how many times each appears in the failing {subject}.",
            (
                f"Approve the supplied {subject} reference as a pre-fix clue and provide the smallest command, fixture, or bounded procedure that regenerates it."
                if reference_supplied
                else f"Provide the smallest command, fixture, or bounded procedure that deterministically generates the failing {subject}."
            ),
            "Confirm that the corrected report must keep every non-repeated step, order, result/status value, detail, and supported view behavior unchanged.",
        ],
        "validation_rows": [
            {"tier": "Reproduction", "proof_target": f"The supplied or regenerated {subject} contains a repetition of {item_boundary}.", "candidate_evidence": f"Approved {subject} artifact plus an exact generator command-result receipt.", "activation_gate": "After reproduction-contract approval.", "pass_condition": f"The approved procedure recreates the same repetition of {item_boundary}."},
            {"tier": "Root cause", "proof_target": "One input, aggregation, generation, or rendering hypothesis explains the duplication and a relevant alternative is eliminated.", "candidate_evidence": "Approved experiment result linked to an Execution Evidence fingerprint.", "activation_gate": "After hypothesis ranking and experiment approval.", "pass_condition": "Saved evidence proves the responsible layer and eliminates a competing layer."},
            {"tier": "Regression", "proof_target": f"The corrected {subject} contains exactly one instance of every intended item.", "candidate_evidence": "Reproduction rerun plus focused report-generation assertions.", "activation_gate": "After separate correction approval and implementation.", "pass_condition": f"{item_boundary.capitalize()} appear once and all later or unrelated items remain present in order."},
            {"tier": "Behaviour", "proof_target": "Non-repeated content, result/status values, details, ordering, and supported view behavior remain unchanged.", "candidate_evidence": "Focused preservation assertions linked to the approved requirement.", "activation_gate": "During selected-Harness convergence.", "pass_condition": "Preservation assertions pass with no unresolved report-content drift."},
        ],
    }


def intent_bridge_requirement_interpretation(
    goal: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    """Project imported requirements into the same pre-scope canonical path."""
    clauses: list[dict[str, Any]] = []
    requirements: list[dict[str, Any]] = []
    for index, row in enumerate(source.get("requirements", []), start=1):
        clause_id = f"INTENT-{index:02d}"
        statement = str(row.get("statement", "")).strip()
        clauses.append({"clause_id": clause_id, "role": "outcome", "text": statement})
        requirements.append({
            "display_id": str(row.get("external_id") or f"REQ-{index:02d}"),
            "statement": statement,
            "kind": requirement_discovery._kind(statement),
            "source_clause_ids": [clause_id],
            "intent_terms": requirement_discovery.query_terms(statement),
            "quoted_literals": [],
            "intent_class": requirement_discovery.inferred_intent_class(statement),
            "confidence": "high",
            "source_reference": {
                "source_uid": source["source_uid"],
                "source_revision": source["source_revision"],
                "path": row["source_path"],
                "locator": row["source_locator"],
                "external_id": row["external_id"],
            },
        })
    sufficiency = requirement_discovery.requirement_sufficiency_contract(
        clauses,
        requirements,
        [],
        source="intent-bridge",
    )
    return {
        "schema_version": "1",
        "type": "tailtrail-requirement-interpretation",
        "source": "intent-bridge",
        "host": None,
        "goal_fingerprint": requirement_discovery.goal_fingerprint(goal),
        "private_reasoning_excluded": True,
        "clauses": clauses,
        "requirements": requirements,
        "material_questions": [],
        "state": "sufficient",
        "sufficiency": sufficiency,
        "intent_bridge_source": {
            "feature_id": source["feature_id"],
            "source_uid": source["source_uid"],
            "source_revision": source["source_revision"],
        },
    }


def resolve_host_identity(args_host: str | None) -> tuple[str | None, str]:
    """Resolve host identity with priority: explicit flag > trusted launcher > absent.
    
    Returns: (resolved_host, source)
    """
    launcher_host = os.environ.get("TAILTRAIL_ACTIVE_HOST")
    
    if args_host and launcher_host:
        if args_host != launcher_host:
            raise ValueError(
                f"Host identity conflict: explicit flag `{args_host}` mismatches "
                f"installed launcher identity `{launcher_host}`; omit `--host` or match the launcher in `tailtrail start \"<goal>\"`."
            )
        return args_host, "explicit-flag"
    
    if args_host:
        return args_host, "explicit-flag"
    
    if launcher_host:
        return launcher_host, "installed-launcher"
    
    return None, "absent"


def build_report(
    goal: str,
    root: Path,
    changed: list[str],
    command_prefix: str,
    run_id: str | None = None,
    aidlc_mode: str = "",
    official_manifest: str | None = None,
    spec_kit_feature: str | None = None,
    workflow_override: str | None = None,
    has_error_artifact: bool = False,
    has_reproduction_command: bool = False,
    graph_mode: str = "auto",
    requirement_interpretation: dict[str, Any] | None = None,
    debug_diagnosis: dict[str, Any] | None = None,
    host_override: str | None = None,
) -> dict[str, Any]:
    command_prefix = normalize_command_prefix(root, command_prefix)
    
    # Resolve host identity and source
    try:
        resolved_host, host_source = resolve_host_identity(host_override)
    except ValueError as error:
        raise SystemExit(f"Host identity error: {error}")
    
    spec_kit_source = spec_kit_bridge.load(root, spec_kit_feature) if spec_kit_feature else None
    
    # Enforce Agent-Host Contract: if a trusted host is active, a typed interpretation is mandatory
    if resolved_host and not requirement_interpretation:
        return render_host_interpretation_required_report(goal, resolved_host, command_prefix)

    if spec_kit_source is not None:
        requirement_interpretation = intent_bridge_requirement_interpretation(
            goal,
            spec_kit_source,
        )
    
    # First pass: determine routing and requirements
    # We use a dummy plan for initial routing evidence if needed
    initial_plan = {"likely_impacted_files": []} 
    
    # Determine initial routing
    # In a real run, navigator.decide() does this, but we need the route to pass to it
    # and then to potentially re-verify it.
    
    resolved_requirement_interpretation = (
        requirement_interpretation or requirement_discovery.interpretation(goal)
    )
    
    # To fix TT-CUR-03, we must ensure that if navigator.decide selects a route, 
    # any subsequent calls to route resolution preserve it.
    plan = navigator.decide(
        goal,
        root,
        changed,
        command_prefix,
        workflow_override=workflow_override,
        has_error_artifact=has_error_artifact,
        has_reproduction_command=has_reproduction_command,
        graph_mode=graph_mode,
        requirement_interpretation=resolved_requirement_interpretation,
        debug_diagnosis=debug_diagnosis,
    )
    classification = plan.get("workflow_classification", {})
    if classification.get("workflow_type") == "debug-investigation":
        parser_contract = deterministic_requirement_parser_contract(goal)
        output_duplication = generated_output_duplication_profile(goal)
        impacted = [item for item in plan.get("likely_impacted_files", []) if isinstance(item, dict)]
        scope_evidence = plan.get("scope_evidence") if isinstance(plan.get("scope_evidence"), dict) else None
        static_orientation = (
            navigator_scope.role_projection(scope_evidence, include_excluded=True)
            if isinstance(scope_evidence, dict)
            else {
                "schema_version": "legacy",
                "decision_fingerprint": None,
                "state": "unresolved",
                "implementation_owners": [],
                "inspection_paths": [],
                "proof_paths": [],
                "excluded_candidates": [],
                "investigation": {},
                "limits": {},
            }
        )
        if debug_diagnosis:
            diagnosed_rows = []
            for row in debug_diagnosis.get("evidence", []):
                diagnosed_rows.append({
                    "path": row["path"],
                    "requirement_ids": ["REQ-DEBUG-01"],
                    "confidence": "high",
                    "status": "orientation-candidate",
                    "reason_codes": ["hash-bound-host-diagnosis", row["kind"]],
                    "evidence_ids": [row["id"]],
                    "diagnosed_role": row["role"],
                })
            role_names = {
                "implementation-owner": "implementation_owners",
                "inspection": "inspection_paths",
                "configuration": "inspection_paths",
                "proof": "proof_paths",
            }
            projection = {"implementation_owners": [], "inspection_paths": [], "proof_paths": []}
            for row in diagnosed_rows:
                projection[role_names[row.pop("diagnosed_role")]].append(row)
            fingerprint_input = json.dumps(projection, sort_keys=True, separators=(",", ":"))
            static_orientation = {
                "schema_version": "host-diagnosis-v1",
                "decision_fingerprint": "sha256:" + hashlib.sha256(fingerprint_input.encode("utf-8")).hexdigest(),
                "state": "resolved" if projection["implementation_owners"] else "unresolved",
                **projection,
                "excluded_candidates": [],
                "investigation": {"source": "bounded-host-diagnosis"},
                "limits": {},
            }
        diagnosis_token = (debug_diagnosis or {}).get("token_estimate", {})
        estimated_tokens = int(
            diagnosis_token.get("planned_working_set_tokens")
            or (plan.get("token_budget", {}) or {}).get("budget_tokens", 4000)
        )
        refinement = (debug_diagnosis or {}).get("requirement_refinement") or {}
        requirement_statement = (
            str(refinement["statement"])
            if refinement.get("statement")
            else
            "Prove and correct the multiline requirement-splitting defect so soft-wrapped prose remains one requirement while explicit requirement boundaries remain separate."
            if parser_contract
            else str(output_duplication["statement"])
            if output_duplication
            else "Prove the reported symptom's root cause while preserving unaffected behaviour and blocking correction until separately approved."
        )
        requirement = {
            "display_id": "REQ-DEBUG-01",
            "kind": "debug-investigation",
            "statement": requirement_statement,
            "acceptance_criteria": list(refinement.get("acceptance_criteria") or output_duplication["acceptance_criteria"]) if output_duplication else list(refinement.get("acceptance_criteria") or [
                "A deterministic or explicitly bounded intermittent reproduction is approved.",
                "The proven cause is supported by saved experiment evidence and a competing hypothesis is eliminated.",
                "No correction or source write occurs before separate approval.",
            ]),
            "preserve_rules": list(refinement.get("preserve_rules") or output_duplication["preserve_rules"]) if output_duplication else list(refinement.get("preserve_rules") or [
                "Preserve current successful behaviour outside the reproduced failure path.",
                "Do not call production systems or external providers during planning.",
            ]),
            "likely_paths": (
                [str(item.get("path")) for item in static_orientation.get("implementation_owners", []) if item.get("path")]
                if debug_diagnosis
                else [str(item.get("path")) for item in impacted if item.get("path")]
            ),
            "validation_contract": {"tiers": ["reproduction", "root-cause", "regression", "behaviour"]},
            "confidence": "planning-evidence-only",
        }
        requirement_facets = [
            {"id": "REQ-DEBUG-01.A", "objective": "Reproduce the reported failure under an approved, bounded procedure.", "proof": "A saved command-result receipt matches the approved actual outcome."},
            {"id": "REQ-DEBUG-01.B", "objective": ("Preserve non-repeated report content and supported report behavior." if output_duplication else "Preserve unaffected behaviour outside the reproduced failure path."), "proof": "Focused preservation evidence passes after the correction."},
            {"id": "REQ-DEBUG-01.C", "objective": "Prove one root cause and eliminate a relevant competing hypothesis.", "proof": "Requirement-linked experiment receipts support the root-cause decision."},
            {"id": "REQ-DEBUG-01.D", "objective": "Keep any correction within separately approved file and symbol scope.", "proof": "The post-edit scope check reports no unresolved unexpected path."},
        ]
        plan["requirement_matrix"] = [requirement]
        validation_rows = list(output_duplication["validation_rows"]) if output_duplication else [
            {"tier": "Reproduction", "proof_target": "The approved trigger produces the saved failure signature.", "candidate_evidence": "Approved reproduction command plus exact command-result receipt.", "activation_gate": "After reproduction-contract approval.", "pass_condition": "Observed actual outcome matches the approved contract repeatably or within its bounded intermittent rule."},
            {"tier": "Root cause", "proof_target": "One hypothesis explains the failure and a relevant alternative is eliminated.", "candidate_evidence": "Approved experiment result linked to an Execution Evidence fingerprint.", "activation_gate": "After hypothesis ranking and experiment approval.", "pass_condition": "Saved evidence strengthens the selected cause and eliminates a competing hypothesis."},
            {"tier": "Regression", "proof_target": "The corrected path no longer produces the approved failure signature.", "candidate_evidence": "Reproduction rerun plus a focused regression-test receipt.", "activation_gate": "After separate correction approval and implementation.", "pass_condition": "The original failure is absent and the focused regression check passes."},
            {"tier": "Behaviour", "proof_target": "Approved successful and unaffected behaviour remains intact.", "candidate_evidence": "Approved behaviour scenario and requirement-linked receipt.", "activation_gate": "During selected-Harness convergence.", "pass_condition": "Preservation scenario passes with no unresolved behaviour drift."},
        ]
        if debug_diagnosis:
            # Keep one canonical validation row per evidence tier. Host test
            # cases enrich those rows instead of duplicating the entire plan.
            tests_by_tier: dict[str, list[dict[str, Any]]] = {}
            for row in debug_diagnosis.get("test_cases", []):
                tests_by_tier.setdefault(str(row.get("tier", "")).casefold(), []).append(row)
            non_reproduction_commands = {
                str(row.get("command"))
                for tier, rows in tests_by_tier.items()
                if tier != "reproduction"
                for row in rows
                if row.get("command")
            }
            rendered_commands: set[str] = set()
            reproduction_candidate = str(
                (debug_diagnosis.get("reproduction") or {}).get("candidate_command") or ""
            )
            for validation in validation_rows:
                tier = str(validation.get("tier", "")).casefold()
                matching = tests_by_tier.get(tier, [])
                if tier == "reproduction":
                    if reproduction_candidate and reproduction_candidate not in non_reproduction_commands:
                        validation["command"] = reproduction_candidate
                    continue
                commands = list(dict.fromkeys(
                    str(row.get("command")) for row in matching if row.get("command")
                ))
                command = next((value for value in commands if value not in rendered_commands), None)
                if command:
                    validation["command"] = command
                    rendered_commands.add(command)
                if matching:
                    ids = ", ".join(f"`{row['id']}`" for row in matching)
                    validation["candidate_evidence"] = (
                        f"Host-diagnosed focused proof {ids}"
                        + (f" at `{matching[0].get('path')}`" if matching[0].get("path") else "")
                        + "."
                    )
        token_parts = {
            "planning_and_reproduction": round(estimated_tokens * 0.20),
            "orientation_and_hypotheses": round(estimated_tokens * 0.20),
            "bounded_experiments": round(estimated_tokens * 0.25),
            "correction_and_scope_check": round(estimated_tokens * 0.15),
        }
        token_parts["validation_and_closure"] = estimated_tokens - sum(token_parts.values())
        delivery = {
            "mode": "debug-investigation",
            "selected": ([
                {"name": "Host-assisted Debug Diagnosis", "why": "use bounded current source, caller, test, configuration, and supplied-artifact evidence to improve the first plan"},
            ] if debug_diagnosis else []) + [
                {"name": "Debug Harness", "why": "turn the saved symptom into reproduction and root-cause evidence before correction"},
                {"name": "Reproduction Contract", "why": "freeze the expected failure, command boundary, and success criteria before experiments"},
                {"name": "Durable Workflow Runtime", "why": "preserve investigation state, approvals, evidence, retries, and resume position under one run"},
                {"name": "Hypothesis Ledger and Bounded Experiment Loop", "why": "rank falsifiable causes and reject unsupported or repeated probes"},
                {"name": "Execution Evidence", "why": "link real command outcomes to the active requirement and experiment"},
                {"name": "Token Harness", "why": "keep future logs and traces bounded while preserving exact failure evidence"},
            ],
            "activated_later": [
                {"name": "Code Graph orientation", "when": "after reproduction approval; reuse the saved static-orientation decision and refresh only when graph evidence is absent or stale"},
                {"name": "Context Continuity", "when": "after an unchanged, regressed, repeated, or cycle-exhausting experiment"},
                {"name": "Correction Scope and Drift Check", "when": "after root cause proof and separate correction approval"},
                {"name": "Requirement Completion, Architecture, Behaviour, Maintainability, and Evidence-Aware Testing", "when": "after correction implementation produces factual execution evidence"},
                {"name": "Canonical Closure and Debug Governance", "when": "after selected Harness convergence"},
                {"name": "Evaluation and governed learning", "when": "after Completion Report generation and trusted acceptance"},
            ],
            "required_later": [
                {"name": "Approved reproduction execution", "when": "after exact reproduction-revision approval and before hypotheses", "why": "confirm the reported failure with a factual command-result receipt"},
                {"name": "Project orientation and root-cause experiments", "when": "after factual reproduction and before any correction proposal", "why": "prove the responsible boundary and eliminate a meaningful competing cause"},
                {"name": "Correction scope and drift control", "when": "after root-cause proof and separate correction approval", "why": "limit implementation to the proven file and symbol boundary"},
                {"name": "Regression, preservation, and selected Harness testing", "when": "after correction implementation and before completion", "why": "rerun the original reproduction, prove restored behavior, preserve explicit requirement boundaries, and reject regressions"},
                {"name": "Canonical completion and closure", "when": "after every required test and selected Harness has factual evidence", "why": "block success when reproduction, restoration, preservation, scope, or test evidence is incomplete"},
            ],
            "conditional_controls": [
                {"name": "Code Graph refresh", "when": "only when the saved graph is absent or stale after reproduction approval"},
                {"name": "Context Continuity", "when": "after an unchanged, regressed, repeated, or cycle-exhausting experiment"},
                {"name": "Evaluation and governed learning", "when": "after Completion Report generation and trusted acceptance"},
            ],
            "stages": ([
                "approve the Debug Planning Lock, then persist the displayed proposal as a versioned reproduction draft for separate exact-revision approval",
                "after exact reproduction approval, run the multiline fixture and record the two-row failure",
                "confirm the normalization and splitting owner from runtime-call and focused-test evidence",
                "prove the boundary rule causing the false split and separately approve the bounded correction",
                "change only the proven owner and its focused regression tests",
                "prove soft wrapping yields one requirement while explicit multiple requirements remain separate",
                "finalize normal evidence, scope convergence, and canonical closure",
            ] if parser_contract else [
                "approve the Debug Planning Lock, then draft the versioned reproduction contract",
                "approve and run that exact reproduction, recording factual Execution Evidence",
                "confirm the diagnosed owner and proof path against the approved reproduction, rank competing hypotheses, and approve one discriminating experiment",
                "run the approved experiment and prove or reject the root cause from saved evidence",
                "separately approve file and symbol correction scope, implement it, and check scope drift",
                "rerun the original reproduction plus focused regression and preservation evidence",
                "converge the selected Harnesses and finalize canonical closure",
            ]),
            "execution_boundary": (
                "This Start run records validated, bounded host diagnosis as planning evidence only. It does not open Debug Intake, execute reproduction or project checks, approve experiments, edit code, or grant correction authority."
                if debug_diagnosis
                else "This Start run creates planning metadata only. It does not open Debug Intake, inspect source, execute reproduction, approve experiments, edit code, or grant correction authority."
            ),
            "hands_free_program": None,
        }
        material_unknowns = (
            [
                "approved reproduction execution and a factual receipt confirming the displayed two-row failure",
                "the proven normalization or splitting boundary rule that causes the false requirement break",
                "separately approved correction file and symbol scope after root-cause proof",
            ]
            if parser_contract
            else list(debug_diagnosis.get("unknowns", [])) + [
                "approved reproduction execution and factual evidence are still required before root-cause proof",
                "the preliminary diagnosis remains advisory until one hypothesis is proven and correction scope is separately approved",
            ]
            if debug_diagnosis
            else list(output_duplication["material_unknowns"])
            if output_duplication
            else list(classification.get("unknown_evidence", []))
        )
        scope_seed_sources = sorted({
            str(source)
            for candidate in plan.get("scope_candidates", [])
            if isinstance(candidate, dict)
            for source in candidate.get("seed_sources", [])
            if source
        })
        return {
            "goal": goal,
            "root": root.as_posix(),
            "command_prefix": command_prefix,
            "navigator": plan,
            "guided_delivery": delivery,
            "debug_plan": {
                "workflow_type": "debug-investigation",
                "classification_reason_code": classification.get("reason_code"),
                "classification_reason": classification.get("reason"),
                "known_symptom": classification.get("known_symptom") or goal,
                "material_unknowns": material_unknowns,
                "classification_evidence": {
                    "explicit_override": workflow_override == "debug",
                    "debug_command_form_detected": bool(re.match(r"^\s*debug\b", goal, re.IGNORECASE)),
                    "error_artifact_supplied": has_error_artifact,
                    "output_reference_supplied": bool(output_duplication and output_duplication.get("reference_supplied")),
                    "reproduction_command_supplied": has_reproduction_command,
                },
                "reproduction_questions": (
                    (["Provide or approve the smallest deterministic reproduction command, fixture, artifact, or bounded intermittent procedure."] if debug_diagnosis.get("safe_fallback", {}).get("user_input") == "required" else ["Approve the proposed bounded reproduction procedure and its expected exit or observable outcome."])
                    + (["Confirm the successful or unaffected behaviour and safety boundary that must remain unchanged."] if not requirement.get("preserve_rules") else [])
                    if debug_diagnosis
                    else list(output_duplication["reproduction_questions"]) if output_duplication else [
                    "Confirm the exact observable failure signature and restored-behaviour result, including relevant counts, status, output, or error boundary.",
                    ("Confirm that the supplied reproduction procedure is the smallest safe discriminating probe and define its expected exit status or bounded outcome." if has_reproduction_command else "Provide or approve the smallest deterministic reproduction command, fixture, or bounded intermittent procedure."),
                    "Confirm the successful or unaffected behaviour, preservation boundaries, safety limits, and data that must remain unchanged during investigation.",
                ]),
                "reproduction_steps": (list(debug_diagnosis.get("reproduction", {}).get("proposed_steps", [])) + [
                    "Record the exact approved attempt as factual execution evidence and compare it with the saved failure signature.",
                    "After an approved correction, rerun the same boundary and preservation cases before closure.",
                ] if debug_diagnosis and debug_diagnosis.get("reproduction", {}).get("proposed_steps") else [
                    "Freeze the exact trigger, expected behavior, observed failure signature, environment, and safety boundary in a versioned reproduction contract.",
                    "After separate approval of that exact revision, run only the approved local command or bounded user-action procedure without changing project source.",
                    "Record the exact command, environment, categorical exit outcome, observable behavior, and requirement-linked evidence receipt.",
                    "Compare the observation with the approved failure signature; only a match advances to project orientation and hypotheses.",
                    "If the issue is absent or inconclusive, inspect bounded input, runtime, configuration, environment, permission, dependency, and timing differences, then ask the user only for the missing sanitized reproduction details.",
                    "After an approved correction, rerun the same reproduction boundary and preservation cases before closure.",
                ]),
                "reproduction_contract": parser_contract,
                "symptom_profile": output_duplication,
                "requirement_facets": requirement_facets,
                "evidence_tiers": ["reproduction", "root-cause", "regression", "behaviour"],
                "validation_rows": validation_rows,
                "host_diagnosis": debug_diagnosis,
                "behavior_trace": (debug_diagnosis or {}).get("behavior_trace"),
                "safe_fallback": (debug_diagnosis or {}).get("safe_fallback"),
                "token_breakdown": token_parts,
                "token_estimate_confidence": str(diagnosis_token.get("confidence", "low")),
                "token_estimate_reason": (
                    str(diagnosis_token.get("basis"))
                    if debug_diagnosis
                    else "No approved reproduction or implementation/proof slices exist yet, so a focused total would be misleading."
                ),
                "static_orientation": {
                    **static_orientation,
                    "role_label": "orientation-candidate",
                    "boundary": "Bounded local text reads and static relationships only. These roles identify investigation candidates; they do not prove root cause, select correction scope, approve reproduction, or grant source-write authority.",
                },
                "safety_boundary": (
                    "The active host performed bounded, hash-bound source/artifact inspection only. No project runtime, test, build, scanner, package-manager, external-provider, or Git operation ran; no reproduction, root-cause claim, correction scope, or source-write authority was created."
                    if debug_diagnosis
                    else "Planning may perform bounded local text reads and static relationship extraction only. It runs no project, test, graph-helper, scanner, package-manager, external-provider, or Git command; it creates no reproduction approval, root-cause claim, correction scope, or source-write authority."
                ),
                "exactness_posture": "The symptom, run identity, target identity, supplied evidence-presence flags, and future receipts remain exact. No raw error or command content is copied into this plan.",
                "scope_source": "bounded-host-diagnosis" if debug_diagnosis else "bounded-static-orientation" if scope_evidence else "unresolved",
                "scope_seed_sources": scope_seed_sources,
                "orientation_method": "host-preflight-and-one-pass-diagnosis" if debug_diagnosis else "bounded-static-orientation" if scope_evidence else "unresolved",
            },
            "architecture_plan": {"selected": False, "status": "deferred-until-reproduction"},
            "behaviour_plan": {"selected": False, "status": "deferred-until-correction"},
            "maintainability_plan": {"selected": False, "status": "deferred-until-correction"},
            "ui_plan": {"selected": False, "surface_status": "not-selected"},
            "ui_consistency": {"selected": False},
            "aidlc_mode": {"mode": "off", "selection": "debug-investigation", "state": "not-selected", "boundary": "AIDLC is not selected by DI-2; requirement/reproduction authority is handled by later debug phases."},
            "aidlc_mode_features": {"included": [], "not_included": ["AIDLC lifecycle during Debug Start planning"]},
            "spec_kit_source": None,
            "next_actions": [],
            "token_posture": {
                "used_tokens": estimated_tokens,
                "baseline_tokens": estimated_tokens,
                "avoided_tokens": 0,
                "estimated_reduction_percent": 0,
            },
            "learning_quality": {},
            "setup_posture": {},
            "review_posture": {"selected": False, "scope": "debug correction only after implementation"},
            "harness_posture": {},
            "bootstrap_posture": {},
            "evaluation_posture": {},
            "code_intelligence": {"mode": "saved-only", "external_providers": "not-run"},
            "next_step": (
                "Review and approve this Debug Start Plan before persisting the displayed proposal as a versioned reproduction draft."
                if parser_contract
                else "Review and approve this Debug Start Plan before drafting a reproduction contract."
            ),
        }
    behaviour_selected = behaviour_planning.selected_for(goal, plan.get("likely_impacted_files", []))
    ui_change = navigator.core.ui_change_requested(goal, changed)
    ui_profile = ui_planning.discover(root, goal, changed) if ui_change else {"selected": False, "surface_status": "not-selected", "candidates": []}
    # Navigator already performed the capped NS-3 investigation. Rebuilding
    # its decision from architecture/behaviour filename suggestions here used
    # to discard relationship edges and could promote weak matches immediately
    # before Planning Lock persistence. Downstream planners consume the exact
    # typed projection; they may not redefine ownership.
    if isinstance(plan.get("scope_evidence"), dict):
        if not navigator_scope.verify_decision_fingerprint(plan["scope_evidence"]):
            raise ValueError("Navigator scope evidence fingerprint is invalid before Start composition; run `tailtrail start \"<goal>\"` for a new run")
        plan["likely_impacted_files"] = navigator_scope.project_likely_impacted(
            plan.get("scope_candidates", [])
        )
        plan["scope_quality"] = navigator_scope.assess_scope_quality(
            root, goal, plan.get("task_types", []), plan["scope_evidence"]
        )
    initial_paths = [str(item.get("path")) for item in plan.get("likely_impacted_files", []) if isinstance(item, dict) and item.get("path")]
    plan.setdefault("requirement_interpretation", resolved_requirement_interpretation)
    if not plan.get("revision_requirement_matrix"):
        plan["requirement_matrix"] = requirement_discovery.matrix(
            goal,
            initial_paths,
            plan.get("requirement_interpretation"),
        )
    canonical_requirements = plan.get("canonical_requirements")
    if not isinstance(canonical_requirements, dict):
        canonical_requirements = requirement_discovery.canonical_set(
            goal,
            plan["requirement_interpretation"],
        )
        plan["canonical_requirements"] = canonical_requirements
    requirement_discovery.bind_canonical_matrix(
        plan.get("requirement_matrix", []),
        canonical_requirements,
    )
    delivery = guided_delivery(plan, goal, changed, root, run_id)
    scope_authority: dict[str, Any] | None = None
    requirement_interpretation = plan.get("requirement_interpretation", {})
    official_requirement_source = (
        requirement_interpretation
        if isinstance(requirement_interpretation, dict)
        and requirement_interpretation.get("authority") == "official-ai-dlc-pack"
        else None
    )
    if spec_kit_source:
        scope_authority = {
            "type": "intent-bridge",
            "feature_id": spec_kit_source["feature_id"],
            "source_uid": spec_kit_source["source_uid"],
            "source_revision": spec_kit_source["source_revision"],
            "snapshot_version": spec_kit_source["snapshot_version"],
        }
        plan["selected_features"] = [
            {"name": "Intent Bridge", "why": f"use imported `{spec_kit_feature}` requirements without regeneration or source writes"},
            *plan.get("selected_features", []),
        ]
        delivery["selected"] = [
            {"name": "Intent Bridge", "why": f"preserve {len(spec_kit_source['requirements'])} imported requirements and source revision through approval"},
            *delivery["selected"],
        ]
    elif official_requirement_source is not None:
        scope_authority = {
            "type": "official-ai-dlc-pack",
            "mode": official_requirement_source.get("authority_mode"),
            "stage": official_requirement_source.get("authority_stage"),
            "references": dict(official_requirement_source.get("authority_references", {})),
        }
        plan["selected_features"] = [
            {
                "name": "Official AI-DLC Requirements",
                "why": "preserve the official pre-scope requirement boundary while Navigator maps local ownership",
            },
            *plan.get("selected_features", []),
        ]
        delivery["selected"] = [
            {
                "name": "Official AI-DLC Requirements",
                "when": "Planning now",
                "why": "official Requirements Analysis owns requirement wording and material decisions before scope",
            },
            *delivery["selected"],
        ]
    requirement_discovery.bind_canonical_matrix(
        plan.get("requirement_matrix", []),
        canonical_requirements,
    )
    # Establish canonical owner, inspection, and proof roles before downstream
    # planners derive UI contracts or validation candidates from the matrix.
    apply_requirement_scope_evidence(plan, scope_authority)
    architecture_selected = any(
        item.get("name") == "Architecture Fitness Harness"
        for item in delivery.get("selected", [])
        if isinstance(item, dict)
    )
    architecture_plan = architecture_planning.build(
        goal,
        plan.get("likely_impacted_files", []),
        plan.get("requirement_matrix", []),
        architecture_selected,
    )
    architecture_planning.apply_contracts(plan.get("requirement_matrix", []), architecture_plan)
    ui_plan = ui_planning.build(
        goal,
        plan.get("requirement_matrix", []),
        ui_profile,
        ui_change,
    )
    ui_planning.apply_contracts(plan.get("requirement_matrix", []), ui_plan)
    behaviour_selected = any(
        item.get("name") == "Behaviour Harness"
        for item in delivery.get("selected", [])
        if isinstance(item, dict)
    )
    behaviour_plan = behaviour_planning.build(
        goal,
        plan.get("likely_impacted_files", []),
        plan.get("requirement_matrix", []),
        behaviour_selected,
    )
    behaviour_planning.apply_contracts(plan.get("requirement_matrix", []), behaviour_plan)
    maintainability_selected = any(
        item.get("name") == "Maintainability Harness"
        for item in delivery.get("selected", [])
        if isinstance(item, dict)
    )
    maintainability_plan = maintainability_planning.build(
        goal,
        plan.get("likely_impacted_files", []),
        plan.get("requirement_matrix", []),
        maintainability_selected,
    )
    maintainability_planning.apply_contracts(plan.get("requirement_matrix", []), maintainability_plan)
    # Harness planners may refine tiers and preservation contracts. Reapply
    # the verified NS-4 roles so no planner can replace or drop canonical
    # editable, inspection, or proof paths.
    requirement_discovery.bind_canonical_matrix(
        plan.get("requirement_matrix", []),
        canonical_requirements,
    )
    apply_requirement_scope_evidence(plan, scope_authority)
    focused_validation = focused_validation_plan(
        root,
        [item for item in plan.get("likely_impacted_files", []) if isinstance(item, dict)],
        [item for item in plan.get("requirement_matrix", []) if isinstance(item, dict)],
        command_prefix,
    )
    approved_owner_paths = list(dict.fromkeys(
        str(path)
        for requirement in plan.get("requirement_matrix", [])
        if isinstance(requirement, dict)
        for path in requirement.get("likely_paths", [])
        if str(path)
    ))
    focused_validation.extend(static_validation_plan(root, approved_owner_paths))
    attach_focused_validation_contracts(plan.get("requirement_matrix", []), focused_validation)
    testing_plan = build_testing_plan(ui_plan, focused_validation)
    attribute_test_precision_planning(delivery, testing_plan, focused_validation)
    proof_rows = [row for row in focused_validation if row.get("check_kind") != "static"]
    proof_ready = bool(proof_rows) and all(
        row.get("candidate_state") == "existing" and row.get("command")
        for row in proof_rows
    )
    proof_proposed = any(row.get("candidate_state") == "proposed" for row in proof_rows)
    if ui_plan.get("selected"):
        proof_stage = (
            "use the approved page/component proof and its resolved runnable command"
            if proof_ready
            else "create the approved page-level proof and use its resolved runnable command"
            if proof_proposed
            else "resolve the exact project-owned page/component proof path and runnable command before the first source edit"
        )
        delivery["stages"] = [
            proof_stage
            if (
                "resolve the exact project-owned component or behaviour test" in stage
                or "resolve the exact project-owned page/component proof" in stage
                or "create the approved page-level proof" in stage
            )
            else stage
            for stage in delivery.get("stages", [])
        ]
    validation_commands = list(dict.fromkeys(
        str(row.get("command")) for row in focused_validation if str(row.get("command", ""))
    ))
    if validation_commands:
        command_stage = "run the approved validation commands: " + "; ".join(validation_commands)
        delivery["stages"] = [
            (
                "run the approved validation commands against every requirement and preservation rule: "
                + "; ".join(validation_commands)
                if stage.startswith("run the linked proof against every requirement")
                else command_stage
            )
            if stage in {"run selected computational checks", "run the approved validation commands"}
            or stage.startswith("run the linked proof against every requirement")
            else stage
            for stage in delivery.get("stages", [])
        ]
    mode = aidlc_mode_selection(goal, aidlc_mode, root, plan, official_manifest)
    if mode["mode"] == "off":
        delivery["selected"] = [item for item in delivery["selected"] if item.get("name") != "AIDLC"]
        plan["selected_features"] = [item for item in plan.get("selected_features", []) if item.get("name") != "AIDLC"]
        delivery["activated_later"].append({"name": "AIDLC", "when": "disabled explicitly with --aidlc off for this Start run"})
    token_plan = start_posture.token_posture(
        root, plan, LARGE_CONTEXT_FILES, APPROX_CHARS_PER_TOKEN
    )
    # Numbers computed mostly from unresolved/wrong scope candidates are not
    # trustworthy; say so plainly instead of presenting a confident-looking estimate.
    token_scope_state = str((plan.get("scope_evidence") or {}).get("state", "unresolved"))
    token_plan["scope_state"] = token_scope_state
    token_plan["estimate_available"] = token_scope_state == "resolved"
    plan["context_slices"] = list(token_plan.get("context_slices", []))
    return {
        "goal": goal,
        "root": root.as_posix(),
        "command_prefix": command_prefix,
        "navigator": plan,
        "guided_delivery": delivery,
        "architecture_plan": architecture_plan,
        "behaviour_plan": behaviour_plan,
        "maintainability_plan": maintainability_plan,
        "ui_plan": ui_plan,
        "testing_plan": testing_plan,
        "focused_validation": focused_validation,
        "ui_consistency": {
            "selected": ui_change,
            "surface_status": ui_plan.get("surface_status", "not-selected"),
            "command": f"{command_prefix} ui discover --root {json.dumps(root.as_posix())}" + "".join(f" --changed {path}" for path in changed[:5]),
            "boundary": "Reuse existing components, styles, tokens, layout, responsive behavior, and accessibility patterns. Preserve the established UI system; do not introduce a UI library, font, global token set, or unrelated redesign without explicit approval.",
        },
        "aidlc_mode": mode,
        "aidlc_mode_features": aidlc_mode_features(mode["mode"]),
        "spec_kit_source": spec_kit_source,
        "next_actions": next_actions(plan),
        "token_posture": token_plan,
        "learning_quality": learning_quality(root, plan),
        "setup_posture": start_posture.setup_posture(root, command_prefix, ROOT),
        "review_posture": start_posture.review_posture(plan, command_prefix),
        "harness_posture": start_posture.harness_posture(root, command_prefix),
        "bootstrap_posture": start_posture.bootstrap_posture(plan, command_prefix),
        "evaluation_posture": start_posture.evaluation_posture(goal, plan, command_prefix, EVALUATION_TRIGGER_WORDS),
        "code_intelligence": code_intelligence_policy(command_prefix),
        "next_step": "Review the guided delivery plan, then approve or edit before implementation.",
    }


def normalize_command_prefix(root: Path, command_prefix: str) -> str:
    """Render commands relative to the target project, not the agent's cwd."""
    normalized = command_prefix.replace("\\", "/")
    if "tailtrail.py" not in normalized:
        return command_prefix
    if "tailtrail/scripts/tailtrail.py" in normalized:
        return command_prefix
    if "scripts/tailtrail.py" in normalized:
        if (root / "tailtrail" / "scripts" / "tailtrail.py").is_file():
            return command_prefix.replace("scripts/tailtrail.py", "tailtrail/scripts/tailtrail.py").replace("scripts\\tailtrail.py", "tailtrail\\scripts\\tailtrail.py")
        return command_prefix
    runner = command_prefix.split("tailtrail.py", 1)[0].strip()
    if not runner:
        return command_prefix
    if (root / "tailtrail" / "scripts" / "tailtrail.py").is_file():
        return f"{runner} tailtrail/scripts/tailtrail.py"
    if (root / "scripts" / "tailtrail.py").is_file():
        return f"{runner} scripts/tailtrail.py"
    return command_prefix


def focused_validation_command(root: Path, impacted: list[dict[str, Any]], command_prefix: str) -> str | None:
    """Suggest one runnable focused test command when the local convention is clear."""
    test_paths = [
        str(item.get("path", ""))
        for item in impacted
        if isinstance(item, dict)
        and (
            item.get("role") == "test"
            or item.get("status") == "proof-only"
            or "test" in str(item.get("path", "")).lower()
            or any(marker in Path(str(item.get("path", ""))).name.lower() for marker in (".cy.", ".spec."))
        )
    ]
    if not test_paths:
        return None
    # Package markers discover no tests; prefer a real test module so the
    # suggested command cannot pass vacuously with zero tests.
    test_paths = sorted(test_paths, key=lambda path: Path(path).name == "__init__.py")
    test_path = Path(test_paths[0])
    candidate = root / test_path
    try:
        body = candidate.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    # The project path can itself contain "tailtrail" (for example
    # D:/PD/TailTrail_Test/tailtrail/scripts/tailtrail.py), so never derive
    # the interpreter by splitting the full launcher path.
    lowered = command_prefix.lower().lstrip()
    if lowered.startswith("py -3 "):
        runner = "py -3"
    elif lowered.startswith("python3 "):
        runner = "python3"
    elif lowered.startswith("python "):
        runner = "python"
    else:
        runner = "python3"
    if "import unittest" in body or "from unittest" in body:
        return f"{runner} -m unittest discover -s {test_path.parent.as_posix()} -p {test_path.name} -v"
    if test_path.suffix == ".py":
        return f"{runner} -m pytest {test_path.as_posix()}"
    node_command = node_focused_proof_command(root, test_path.as_posix())
    if node_command:
        return node_command
    return None


def node_package_scripts(root: Path) -> dict[str, str]:
    """Read only the project-owned Node script catalog used for proof commands."""
    try:
        package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    scripts = package.get("scripts", {}) if isinstance(package, dict) else {}
    return {
        str(name): str(command)
        for name, command in scripts.items()
        if isinstance(name, str) and isinstance(command, str)
    } if isinstance(scripts, dict) else {}


def node_script_invocation(root: Path, script_name: str, arguments: list[str]) -> str:
    quoted_arguments = " ".join(
        value if re.fullmatch(r"--?[A-Za-z0-9][A-Za-z0-9-]*", value) else json.dumps(value)
        for value in arguments
    )
    if (root / "pnpm-lock.yaml").is_file():
        base = f"pnpm run {script_name}"
    elif (root / "yarn.lock").is_file():
        base = f"yarn {script_name}"
        if not quoted_arguments:
            return base
        return f"{base} {quoted_arguments}".rstrip()
    else:
        base = f"npm run {script_name}"
    if not quoted_arguments:
        return base
    return f"{base} -- {quoted_arguments}".rstrip()


def node_focused_proof_command(root: Path, test_path: str) -> str | None:
    """Resolve an exact project-owned command for an existing or proposed Node proof."""
    scripts = node_package_scripts(root)
    lowered_path = test_path.lower()
    if ".cy." in lowered_path:
        component = next(
            (
                name for name, command in scripts.items()
                if "cypress" in command.lower() and "--component" in command.lower()
            ),
            None,
        )
        if component:
            return node_script_invocation(root, component, ["--spec", test_path])
    test_script = next(
        (
            name for name, command in scripts.items()
            if name == "test" or any(tool in command.lower() for tool in ("vitest", "jest", "mocha"))
        ),
        None,
    )
    if test_script:
        return node_script_invocation(root, test_script, [test_path])
    return None


def static_validation_plan(root: Path, owner_paths: list[str]) -> list[dict[str, Any]]:
    """Select project-owned lint plus one build/type check for code changes.

    The command is taken only from the package script catalog. TailTrail does
    not invent a linter, type checker, build tool, or dependency.
    """
    code_suffixes = {".js", ".jsx", ".ts", ".tsx"}
    if not any(Path(path).suffix.lower() in code_suffixes for path in owner_paths):
        return []
    scripts = node_package_scripts(root)
    selected: list[tuple[str, str]] = []
    if "lint" in scripts:
        selected.append(("lint", "lint"))
    build_precedence = (
        ("typecheck", "type check"),
        ("type-check", "type check"),
        ("check:types", "type check"),
        ("build", "build/type check"),
    )
    build_check = next(
        ((script_name, label) for script_name, label in build_precedence if script_name in scripts),
        None,
    )
    if build_check:
        selected.append(build_check)
    return [
        {
            "tier": "static analysis",
            "tiers": ["static"],
            "candidate": f"package.json#scripts.{script_name}",
            "command": node_script_invocation(root, script_name, []),
            "status": f"required project-owned {label} after implementation",
            "candidate_state": "existing",
            "check_kind": "static",
            "required": True,
        }
        for script_name, label in selected
    ]


def build_testing_plan(
    ui_plan: dict[str, Any],
    validation_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Bind concrete UI assertions, proof maintenance, and runnable commands."""
    if not ui_plan.get("selected"):
        return {"selected": False, "test_cases": [], "commands": []}
    test_cases: list[dict[str, str]] = []
    for contract in ui_plan.get("contracts", []):
        if not isinstance(contract, dict):
            continue
        requirement_id = str(contract.get("requirement_id", "REQ"))
        for assertion in contract.get("test_cases", []):
            normalized = {"requirement_id": requirement_id, "assertion": str(assertion)}
            if any(
                item.get("requirement_id") == normalized["requirement_id"]
                and item.get("assertion") == normalized["assertion"]
                for item in test_cases
            ):
                continue
            test_cases.append({
                "test_case_id": f"TC-{len(test_cases) + 1:02d}",
                **normalized,
            })

    proof_rows = [row for row in validation_rows if row.get("check_kind") != "static"]
    existing = list(dict.fromkeys(
        str(row.get("candidate"))
        for row in proof_rows
        if row.get("candidate_state") == "existing" and str(row.get("candidate", ""))
    ))
    proposed = list(dict.fromkeys(
        str(row.get("candidate"))
        for row in proof_rows
        if row.get("candidate_state") == "proposed" and str(row.get("candidate", ""))
    ))
    if existing:
        proof_action = (
            "After approval, update the existing linked page/component proof when any required "
            "assertion is missing; otherwise run it unchanged."
        )
    elif proposed:
        proof_action = "After approval, create the approved page/component proof with every required assertion."
    else:
        proof_action = "Resolve a project-owned page/component proof and runnable command before the first source edit."

    commands: list[dict[str, str]] = []
    for row in validation_rows:
        command = str(row.get("command", ""))
        if not command:
            continue
        candidate = str(row.get("candidate", "")).lower()
        if row.get("check_kind") != "static":
            purpose = "Run the focused page/component proof"
        elif "lint" in candidate:
            purpose = "Run project lint"
        else:
            purpose = "Run the project build/type check"
        item = {"purpose": purpose, "command": command}
        if item not in commands:
            commands.append(item)
    return {
        "selected": True,
        "test_cases": test_cases,
        "existing_proof_paths": existing,
        "proposed_proof_paths": proposed,
        "proof_action": proof_action,
        "commands": commands,
        "boundary": "These checks run after implementation; this Planning Lock records no test result.",
    }


def attribute_test_precision_planning(
    delivery: dict[str, Any],
    testing_plan: dict[str, Any],
    validation_rows: list[dict[str, Any]],
) -> None:
    """Declare Test Precision when Start actually creates precise test guidance."""
    has_assertion_plan = bool(testing_plan.get("test_cases"))
    has_focused_proof = any(
        row.get("check_kind") != "static"
        and bool(row.get("command"))
        and row.get("candidate_state") in {"existing", "proposed"}
        for row in validation_rows
        if isinstance(row, dict)
    )
    if not (has_assertion_plan or has_focused_proof):
        return

    selected = delivery.setdefault("selected", [])
    feature = next(
        (
            item
            for item in selected
            if isinstance(item, dict) and item.get("name") == "Test Precision Planner"
        ),
        None,
    )
    if feature is None:
        feature = {"name": "Test Precision Planner"}
        insertion_index = next(
            (
                index + 1
                for index, item in enumerate(selected)
                if isinstance(item, dict) and item.get("name") == "Evidence-Aware Testing"
            ),
            len(selected),
        )
        selected.insert(insertion_index, feature)
    feature.update({
        "when": "Planning now and after implementation",
        "why": (
            "mapped requirements to assertion-level test cases and resolved the focused proof path and "
            "runnable command; after implementation it requires that approved proof before completion"
        ),
    })


def proposed_ui_proof(root: Path, owner_paths: list[str]) -> tuple[str, str] | None:
    """Propose one page/component-level proof only when the local runner is proven."""
    scripts = node_package_scripts(root)
    has_cypress_component = any(
        "cypress" in command.lower() and "--component" in command.lower()
        for command in scripts.values()
    )
    if not has_cypress_component or not any((root / name).is_file() for name in ("cypress.config.ts", "cypress.config.js", "cypress.config.mjs")):
        return None
    for owner in owner_paths:
        path = Path(owner)
        if path.suffix.lower() not in {".js", ".jsx", ".ts", ".tsx"}:
            continue
        candidates = [
            path.with_name(f"{path.stem}.cy{path.suffix}"),
            path.with_name(f"{path.stem}.test{path.suffix}"),
            path.with_name(f"{path.stem}.spec{path.suffix}"),
        ]
        selected = next((candidate for candidate in candidates if (root / candidate).is_file()), candidates[0])
        command = node_focused_proof_command(root, selected.as_posix())
        if command:
            return selected.as_posix(), command
    return None


def coalesce_focused_validation_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse one executable proof covering multiple requested evidence tiers."""
    grouped: list[dict[str, Any]] = []
    by_proof: dict[tuple[str, str, str], dict[str, Any]] = {}
    for source in rows:
        row = dict(source)
        tier = str(row.get("tier", "unit"))
        row["tiers"] = [tier]
        key = (
            str(row.get("candidate", "")),
            str(row.get("command", "")),
            str(row.get("candidate_state", "unresolved")),
        )
        mergeable = bool(key[0] and key[1] and key[2] in {"existing", "proposed"})
        existing = by_proof.get(key) if mergeable else None
        if existing is None:
            grouped.append(row)
            if mergeable:
                by_proof[key] = row
            continue
        existing["tiers"].append(tier)
        existing["tier"] = " + ".join(existing["tiers"])
        if existing.get("candidate_state") == "proposed":
            existing["status"] = (
                "proposed one page-level proof covering "
                + " and ".join(existing["tiers"])
                + "; create it after approval and execute the resolved command after implementation"
            )
        else:
            existing["status"] = "one existing proof covers " + " and ".join(existing["tiers"])
    return grouped


def focused_validation_plan(
    root: Path,
    impacted: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    command_prefix: str,
) -> list[dict[str, Any]]:
    """Return every requested validation tier without inventing a passing test.

    When ownership is resolved but no linked test exists, the plan states the
    required proof-selection step explicitly.  This is stronger than silently
    deferring testing while still avoiding a fabricated file or command.
    """
    requested: list[str] = []
    for row in requirements:
        contract = row.get("validation_contract", {}) if isinstance(row, dict) else {}
        for tier in contract.get("tiers", []) if isinstance(contract, dict) else []:
            if isinstance(tier, str) and tier not in requested:
                requested.append(tier)
    proof_paths = list(dict.fromkeys(
        str(path)
        for row in requirements if isinstance(row, dict)
        for path in ((row.get("scope_evidence", {}) or {}).get("proof_paths", []))
        if str(path)
    ))
    impacted_by_path = {
        str(item.get("path")): item
        for item in impacted
        if isinstance(item, dict) and item.get("path")
    }
    test_items = [
        impacted_by_path.get(path, {"path": path, "role": "test", "status": "proof-only"})
        for path in proof_paths
    ] or [
        item for item in impacted
        if isinstance(item, dict) and (
            item.get("role") == "test"
            or item.get("status") == "proof-only"
            or "test" in str(item.get("path", "")).lower()
            or any(marker in Path(str(item.get("path", ""))).name.lower() for marker in (".cy.", ".spec."))
        )
    ]
    owner_paths = list(dict.fromkeys(
        str(path)
        for row in requirements if isinstance(row, dict)
        for path in row.get("likely_paths", [])
        if str(path)
    ))
    ui_proof = proposed_ui_proof(root, owner_paths)
    rows: list[dict[str, str]] = []
    for tier in requested or ["unit"]:
        tier_paths = [
            item for item in test_items
            if f"/{tier}/" in "/" + str(item.get("path", "")).lower().replace("\\", "/") + "/"
        ]
        if tier in {"component", "behaviour"} and not tier_paths:
            tier_paths = [
                item for item in test_items
                if "/tests/ui/" in "/" + str(item.get("path", "")).lower().replace("\\", "/")
                or any(
                    marker in str(item.get("path", "")).lower()
                    for marker in (".cy.", ".spec.", ".component.", "accessibility", "a11y", "visual")
                )
            ]
        # A repository's focused unit test does not need to live in a literal
        # ``tests/unit`` folder. Generic proof paths are valid unit candidates,
        # but a path explicitly nested under a higher-tier folder must not be
        # relabelled as unit proof.
        higher_tier_markers = ("/integration/", "/contract/", "/component/", "/e2e/", "/infrastructure/", "/release-smoke/")
        generic_unit_items = [
            item for item in test_items
            if not any(marker in "/" + str(item.get("path", "")).lower().replace("\\", "/") + "/" for marker in higher_tier_markers)
        ]
        candidate_items = tier_paths or (generic_unit_items if tier == "unit" else [])
        command = focused_validation_command(root, candidate_items[:1], command_prefix) if candidate_items else None
        if candidate_items:
            candidate = str(candidate_items[0].get("path"))
            status = "planned after approval" if command else "required proof path identified; resolve its project-owned command before the first edit"
            candidate_state = "existing"
        elif tier in {"component", "behaviour", "e2e"} and ui_proof:
            candidate, command = ui_proof
            exists = (root / candidate).is_file()
            candidate_state = "existing" if exists else "proposed"
            status = (
                "planned after approval"
                if exists
                else "proposed page-level Cypress component proof; create this approved proof path and execute it after implementation"
            )
        elif tier in {"component", "behaviour", "e2e"} and owner_paths:
            candidate = f"new or existing focused UI test for {owner_paths[0]}"
            status = "required: select the repository-owned test convention and runnable command before the first edit; execute after implementation"
            candidate_state = "unresolved"
        else:
            candidate = "not resolved from planning evidence"
            status = "required: resolve a project-owned proof path and runnable command before the first edit"
            candidate_state = "unresolved"
        rows.append({
            "tier": tier,
            "candidate": candidate,
            "command": command or "",
            "status": status,
            "candidate_state": candidate_state,
        })
    return coalesce_focused_validation_rows(rows)


def attach_focused_validation_contracts(
    requirements: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> None:
    """Persist exact proof paths and commands in the approval/closure contract."""
    for requirement in requirements:
        contract = requirement.get("validation_contract", {}) if isinstance(requirement, dict) else {}
        if not isinstance(contract, dict):
            continue
        tiers = {str(value) for value in contract.get("tiers", [])}
        linked = [
            row for row in rows
            if tiers.intersection(
                str(value) for value in row.get("tiers", [row.get("tier")]) if str(value)
            )
        ]
        paths = [
            str(row.get("candidate")) for row in linked
            if row.get("candidate_state") in {"existing", "proposed"}
        ]
        proposed = [
            str(row.get("candidate")) for row in linked
            if row.get("candidate_state") == "proposed"
        ]
        required_static = [
            row for row in rows
            if row.get("check_kind") == "static" and row.get("required") and str(row.get("command", ""))
        ]
        contract["tiers"] = list(dict.fromkeys([
            *[str(value) for value in contract.get("tiers", []) if str(value)],
            *[
                str(value)
                for row in linked
                for value in row.get("tiers", [row.get("tier")])
                if str(value)
            ],
            *("static" for _row in required_static),
        ]))
        commands = [
            str(row.get("command"))
            for row in [*linked, *required_static]
            if str(row.get("command", ""))
        ]
        existing = [str(value) for value in contract.get("candidate_paths", []) if str(value)]
        contract["candidate_paths"] = list(dict.fromkeys([*existing, *paths]))
        contract["proposed_paths"] = list(dict.fromkeys(proposed))
        contract["editable_paths"] = list(dict.fromkeys(paths))
        contract["commands"] = list(dict.fromkeys(commands))
        checks = []
        for proof in linked:
            command = str(proof.get("command", ""))
            if not command:
                continue
            checks.append({
                "kind": "proof",
                "command": command,
                "tiers": [str(value) for value in proof.get("tiers", [proof.get("tier")]) if str(value)],
                "candidate_paths": [str(proof.get("candidate"))] if proof.get("candidate") else [],
            })
        for static in required_static:
            checks.append({
                "kind": "static",
                "command": str(static["command"]),
                "tiers": ["static"],
                "candidate_paths": [],
            })
        contract["checks"] = list({item["command"]: item for item in checks}.values())


def short_trigger(value: str) -> str:
    """Keep conditional-control cells readable; detailed rules remain in verbose artifacts."""
    lowered = value.lower()
    if "context continuity" in lowered or "correction cycle" in lowered:
        return "After incomplete work, drift, rejection, failed correction, or slice transition."
    if "git recovery" in lowered or "rollback" in lowered or "recovery risk" in lowered:
        return "After recovery risk, repeated failure, conflict, or explicit rollback need."
    if "higher-tier" in lowered or "integration" in lowered or "contract" in lowered:
        return "When the approved proof needs integration, contract, behaviour, infrastructure, or release evidence."
    return value.split(";")[0].rstrip(".") + "."


def required_later_rows(delivery: dict[str, Any]) -> list[dict[str, str]]:
    """Return mandatory later-stage proof, including for legacy saved reports."""
    rows = [row for row in delivery.get("required_later", []) if isinstance(row, dict)]
    if rows:
        return rows
    return [
        {
            "name": "Focused testing and validation",
            "when": "after every approved implementation or correction, before completion",
            "why": "prove changed behavior, preservation cases, and regression boundaries with factual evidence",
        },
        {
            "name": "Canonical completion and closure",
            "when": "after all required tests and selected Harness checks have factual results",
            "why": "prevent completion while required evidence is missing, unavailable, or failing",
        },
    ]


def conditional_control_rows(delivery: dict[str, Any]) -> list[dict[str, str]]:
    """Keep conditional controls distinct from mandatory lifecycle work."""
    source = delivery.get("conditional_controls")
    if not isinstance(source, list):
        source = delivery.get("activated_later", [])
    return [row for row in source if isinstance(row, dict)]


def append_later_lifecycle_sections(lines: list[str], delivery: dict[str, Any], *, compact: bool = False) -> None:
    """Render mandatory work as required and reserve conditional wording for triggers."""
    lines.extend(["", "## Required later in this run", "", "These controls are mandatory before TailTrail can report completion; they are scheduled after the relevant approved implementation stage, not deferred or optional.", ""])
    for row in required_later_rows(delivery):
        when = short_trigger(str(row.get("when", ""))) if compact else display_prose(row.get("when"))
        why = display_prose(row.get("why", "required before completion"))
        lines.append(f"- **{row.get('name')}:** {str(when).rstrip('.')}. **Why:** {str(why).rstrip('.')}.")
    conditional = conditional_control_rows(delivery)
    lines.extend(["", "## Conditional TailTrail controls", ""])
    if conditional:
        for row in conditional:
            when = short_trigger(str(row.get("when", ""))) if compact else display_prose(row.get("when"))
            lines.append(f"- **{row.get('name')}:** {when}")
    else:
        lines.append("- None. All selected controls are already scheduled in this run.")


def debug_start_report(report: dict[str, Any], verbose: bool = False) -> str:
    """Render one canonical, planning-only Debug Start report."""
    plan = report["navigator"]
    debug_plan = report["debug_plan"]
    delivery = report["guided_delivery"]
    lock = report.get("planning_lock")
    impacted = [item for item in plan.get("likely_impacted_files", []) if isinstance(item, dict)]
    requirements = [item for item in plan.get("requirement_matrix", []) if isinstance(item, dict)]
    reproduction_contract = debug_plan.get("reproduction_contract")
    host_diagnosis = debug_plan.get("host_diagnosis") if isinstance(debug_plan.get("host_diagnosis"), dict) else None
    scope_seed_sources = [str(value) for value in debug_plan.get("scope_seed_sources", [])]
    lines = ["# TailTrail Debug Start Plan", ""]
    lines.extend(["## Planning Lock", ""])
    if lock:
        lines.extend([
            f"- Run ID: `{lock['run_id']}`",
            f"- Target identity: `{lock.get('target_identity', {}).get('fingerprint', 'legacy lock')}`.",
            f"- State: **{lock['status']}**; managed writes allowed: **{str(lock['writes_allowed']).lower()}**.",
            f"- Saved plan: `{report.get('planning_report', {}).get('artifact', 'saved with this run')}`.",
        ])
    else:
        lines.append("- No persisted Planning Lock is attached to this rendered report.")
    lines.extend(pipeline_badge_lines(lock if isinstance(lock, dict) else None))
    lines.extend([
        "",
        "## Start Here",
        "",
        (
            "- Review the symptom boundary, resolved orientation, proposed reproduction contract, remaining unknowns, and safety controls."
            if isinstance(reproduction_contract, dict)
            else "- Review the symptom boundary, unknowns, proposed reproduction questions, and safety controls."
        ),
        (
            "- This report includes bounded host-assisted preliminary diagnosis; it does not reproduce the issue, prove root cause, execute project checks, or change the project."
            if host_diagnosis
            else "- Nothing in this report reproduces, diagnoses, or changes the project."
        ),
        "",
        "## Navigator Decision",
        "",
        f"- Workflow type: `{debug_plan['workflow_type']}`",
        f"- Reason: `{debug_plan.get('classification_reason_code')}` - {display_prose(debug_plan.get('classification_reason'))}",
        f"- Known symptom: {display_prose(debug_plan.get('known_symptom'))}",
        "- Material unknowns:",
    ])
    lines.extend(f"  - {display_prose(item)}" for item in debug_plan.get("material_unknowns", []))
    if host_diagnosis:
        preflight = host_diagnosis.get("preflight") or {}
        lines.append(
            f"- Pre-plan diagnosis: `host-assisted` by `{host_diagnosis.get('host')}`; "
            f"`{len(host_diagnosis.get('evidence', []))}` bounded evidence row(s), "
            f"`{len(host_diagnosis.get('findings', []))}` preliminary finding(s), and "
            f"`{len(host_diagnosis.get('test_cases', []))}` test case(s)."
        )
        if preflight:
            lines.append(
                f"- Debug preflight: `{preflight.get('files_read', 0)}` bounded file read(s), "
                f"`{preflight.get('estimated_tokens', 0)}` estimated context tokens, "
                f"`{preflight.get('elapsed_ms', 0)} ms`, one host reasoning pass; "
                f"stop reason `{preflight.get('termination_reason')}`."
            )
    evidence = debug_plan.get("classification_evidence", {})
    lines.extend([
        f"- Debug route evidence: explicit command form detected `{str(evidence.get('debug_command_form_detected', False)).lower()}`; forced `--debug` override supplied `{str(evidence.get('explicit_override', False)).lower()}`.",
        f"- Supplied evidence: attached error artifact `{str(evidence.get('error_artifact_supplied', False)).lower()}`; local report/output reference in the goal `{str(evidence.get('output_reference_supplied', False)).lower()}`; reproduction command `{str(evidence.get('reproduction_command_supplied', False)).lower()}`.",
        f"- Approval posture: {plan.get('workflow_classification', {}).get('approval_posture')}",
        "",
        "## Scope",
        "",
        f"- Target repository: `{report['root']}`",
        f"- Scope source: `{debug_plan.get('scope_source')}`.",
        "- Candidate seed sources: " + (
            ", ".join(f"`{value}`" for value in scope_seed_sources)
            if scope_seed_sources
            else "none"
        ) + ".",
        f"- Orientation method: `{debug_plan.get('orientation_method', 'legacy')}`.",
    ])
    orientation = debug_plan.get("static_orientation", {}) if isinstance(debug_plan.get("static_orientation"), dict) else {}
    orientation_rows = [
        ("likely-owner", row) for row in orientation.get("implementation_owners", [])
    ] + [
        ("inspection", row) for row in orientation.get("inspection_paths", [])
    ] + [
        ("proof", row) for row in orientation.get("proof_paths", [])
    ]
    if orientation_rows:
        lines.extend([
            f"- Static orientation state: `{orientation.get('state', 'unresolved')}`; decision fingerprint: `{orientation.get('decision_fingerprint', 'not-recorded')}`.",
            "- Every path below is an **orientation candidate**, never correction scope or root-cause proof.",
        ])
        seed_sources = set(scope_seed_sources)
        if "explicit-path" in seed_sources:
            lines.append("- The paths below were supplied by the user as inspection candidates; orientation must confirm their roles before correction scope is approved.")
        if "saved-graph" in seed_sources:
            lines.append("- Saved graph paths were advisory seeds only; the bounded static relationship decision above is the decisive scope evidence.")
        investigation = orientation.get("investigation", {}) if isinstance(orientation.get("investigation"), dict) else {}
        limit_state = investigation.get("limit_state", {}) if isinstance(investigation.get("limit_state"), dict) else {}
        if orientation.get("state") == "blocked-by-limits":
            ownership = investigation.get("ownership_selection", {}) if isinstance(investigation.get("ownership_selection"), dict) else {}
            lines.append(
                "- Orientation limit: `" + str(limit_state.get("termination_reason", investigation.get("stop_reason", "limit-reached")))
                + "` after `" + str(limit_state.get("broad_files_read", "unknown")) + "` of `"
                + str(limit_state.get("broad_file_limit", "unknown"))
                + "` allowed broad reads; owner-qualified candidates: `"
                + str(ownership.get("qualified_candidates", 0)) + "`."
            )
            lines.append("- Impact: orientation remains incomplete. Low-confidence paths below are starting points only, not likely fixes or correction scope.")
        lines.append("")
        orientation_records = []
        for role, item in orientation_rows if verbose else orientation_rows[:8]:
            orientation_records.append((
                f"`{item.get('path')}`",
                [
                    ("Evidence role", f"`{role}`"),
                    ("Requirement", ", ".join(item.get("requirement_ids", [])) or "none"),
                    ("Confidence", f"`{item.get('confidence', 'none')}`"),
                ],
            ))
        append_stacked_records(lines, orientation_records)
        if verbose:
            excluded = orientation.get("excluded_candidates", [])
            if excluded:
                lines.extend(["", "### Excluded static candidates", ""])
                append_stacked_records(lines, [
                    (
                        f"`{item.get('path')}`",
                        [
                            ("Status", f"`{item.get('status')}`"),
                            ("Reason", display_prose(", ".join(item.get("reason_codes", [])))),
                        ],
                    )
                    for item in excluded
                ])
        lines.append(f"- Boundary: {orientation.get('boundary')}")
    elif impacted:
        lines.append("- Legacy paths are orientation candidates only; they are not correction scope or root-cause proof.")
        for item in impacted if verbose else impacted[:6]:
            lines.append(f"- Orientation candidate `{item.get('path')}` - {display_prose(item.get('reason'))}")
    else:
        lines.append("- Static orientation is unresolved. No file is invented; the later approved orientation stage may gather additional evidence under the same reproduction gate.")
    lines.extend(["", "## Requirements", ""])
    for item in requirements:
        lines.append(requirement_line(item))
        if verbose:
            lines.append("  - Preserve:")
            lines.extend(f"    - {display_prose(rule)}" for rule in item.get("preserve_rules", []))
            lines.append("  - Acceptance:")
            lines.extend(f"    - {display_prose(rule)}" for rule in item.get("acceptance_criteria", []))
    facets = [item for item in debug_plan.get("requirement_facets", []) if isinstance(item, dict)]
    if facets:
        lines.extend(["", "### Requirement facets", ""])
        append_stacked_records(lines, [
            (
                display_prose(facet.get("id")),
                [
                    ("Investigation objective", display_prose(facet.get("objective"))),
                    ("Required proof", display_prose(facet.get("proof"))),
                ],
            )
            for facet in facets
        ])
    if host_diagnosis:
        lines.extend(["", "## Preliminary debug analysis", ""])
        lines.append("The active host inspected bounded current source/artifact context before Start. Findings remain observations or hypotheses—not root-cause proof.")
        completeness = host_diagnosis.get("evidence_completeness") or {}
        lines.append(
            f"- Evidence completeness: `{completeness.get('status', 'unavailable')}`. "
            "TailTrail validates freshness, role consistency, coverage, and traceability; semantic interpretation remains host-owned."
        )
        for gap in completeness.get("gaps", []):
            lines.append(f"  - Gap: {display_prose(gap)}")
        proposal = host_diagnosis.get("proposal") or {}
        if proposal:
            lines.append(
                f"- Typed host proposal: `{proposal.get('route')}` for `{proposal.get('requirement_id')}`; "
                "ID-bound and advisory only."
            )
        safe_fallback = host_diagnosis.get("safe_fallback") or {}
        if safe_fallback:
            lines.append(
                f"- Safe fallback: `{safe_fallback.get('state')}`; trace `{safe_fallback.get('trace_state')}`; "
                f"correction scope `{safe_fallback.get('correction_scope')}`; user input `{safe_fallback.get('user_input')}`."
            )
            lines.append(f"  - Next: {display_prose(safe_fallback.get('next_action'))}")
        lines.extend(["", "### Checks performed", ""])
        for action in host_diagnosis.get("checks_performed", []):
            lines.append(f"- `{action}`")
        lines.extend(["", "### Diagnosed repository roles", ""])
        append_stacked_records(lines, [
            (
                f"`{row.get('path')}`",
                [
                    ("Role", f"`{row.get('role')}`"),
                    ("Behavior roles", ", ".join(f"`{item}`" for item in row.get("behavior_roles", [])) or "legacy role only"),
                    ("Evidence", f"`{row.get('id')}` / `{row.get('kind')}` / lines `{row.get('start_line')}-{row.get('end_line')}`"),
                    ("Symbols", ", ".join(f"`{item}`" for item in row.get("symbols", [])) or "none resolved"),
                    ("Finding", display_prose(row.get("finding"))),
                ],
            )
            for row in host_diagnosis.get("evidence", [])
        ])
        behavior_trace = host_diagnosis.get("behavior_trace")
        if isinstance(behavior_trace, dict):
            trace_nodes = {str(row.get("id")): row for row in behavior_trace.get("nodes", []) if isinstance(row, dict)}
            topology = behavior_trace.get("topology") or {}
            lines.extend(["", "### Backward behavior graph", ""])
            lines.append(
                f"- State: `{behavior_trace.get('state')}`; shape: `{topology.get('shape', 'unavailable')}`; "
                f"paths: `{topology.get('path_count', 0)}`; direction: `{behavior_trace.get('direction')}`."
            )
            for edge in behavior_trace.get("edges", []):
                source = trace_nodes.get(str(edge.get("from")), {})
                target = trace_nodes.get(str(edge.get("to")), {})
                lines.append(
                    f"- `{source.get('path', edge.get('from'))}` → `{target.get('path', edge.get('to'))}`: "
                    f"{display_prose(edge.get('relationship'))}."
                )
            lines.append(f"- Boundary: {display_prose(behavior_trace.get('boundary'))}")
        lines.extend(["", "### Preliminary findings", ""])
        append_stacked_records(lines, [
            (
                display_prose(row.get("id")),
                [
                    ("State", f"`{row.get('state')}`"),
                    ("Confidence", f"`{row.get('confidence')}`"),
                    ("Finding", display_prose(row.get("statement"))),
                    ("Evidence", ", ".join(f"`{item}`" for item in row.get("evidence_ids", []))),
                ],
            )
            for row in host_diagnosis.get("findings", [])
        ])
        reproduction = host_diagnosis.get("reproduction", {})
        lines.extend(["", "### Reproduction diagnosis", ""])
        lines.extend([
            f"- Status: `{reproduction.get('status', 'not-run')}` — inspecting an artifact is not reproducing it.",
            f"- Observed: {display_prose(reproduction.get('observation'))}",
            f"- Expected: {display_prose(reproduction.get('expected'))}",
        ])
        if reproduction.get("candidate_command"):
            lines.append(f"- Candidate command after approval: `{reproduction.get('candidate_command')}`")
        lines.extend(["", "## Required test cases", ""])
        for row in host_diagnosis.get("test_cases", []):
            lines.append(f"{row.get('id')}. **{row.get('tier')} / {row.get('state')}:** {display_prose(row.get('statement'))}")
            boundaries = ", ".join(f"`{value}`" for value in row.get("proof_boundaries", []))
            lines.append(f"   - Proof boundary: {boundaries or '`unresolved`'}")
            if row.get("path"):
                lines.append(f"   - Path: `{row.get('path')}`")
            if row.get("command"):
                lines.append(f"   - Command after approval: `{row.get('command')}`")
    lines.extend(["", "## Selected TailTrail features", ""])
    debug_feature_records = [("Navigator", [("When", "Planning now"), ("Why", "classified the symptom-first workflow and created the canonical Planning Lock")])]
    for item in delivery.get("selected", []):
        when = "Before Planning Lock" if item.get("name") == "Host-assisted Debug Diagnosis" else "Planning / after approval"
        debug_feature_records.append((display_prose(item.get("name")), [("When", when), ("Why", display_prose(item.get("why")))]))
    append_stacked_records(lines, debug_feature_records)
    append_later_lifecycle_sections(lines, delivery)
    if isinstance(reproduction_contract, dict):
        lines.extend([
            "",
            "## Proposed reproduction contract",
            "",
            "The supplied symptom is concrete enough to propose this bounded contract without generic discovery questions. It is planning evidence only until DI-3 persists a versioned draft and that exact revision receives separate approval.",
            "",
            "### Proposed concrete contract",
            "",
            "```text",
            str(reproduction_contract.get("input", "")),
            "```",
            "",
            "- Observed: " + "; ".join(
                f"`REQ-{index:02d}: {display_prose(value)}`"
                for index, value in enumerate(reproduction_contract.get("observed", []), start=1)
            ),
            "- Expected: exactly one requirement row: " + " ".join(
                f"`{display_prose(value)}`" for value in reproduction_contract.get("expected", [])
            ),
            "- Preservation proof:",
        ])
        lines.extend(
            f"  - {display_prose(value)}"
            for value in reproduction_contract.get("preservation_cases", [])
        )
    else:
        lines.extend(["", "## Proposed reproduction questions", ""])
        for index, question in enumerate(debug_plan.get("reproduction_questions", []), start=1):
            lines.append(f"{index}. {display_prose(question)}")
    lines.extend(["", "## Proposed reproduction steps", ""])
    for index, step in enumerate(debug_plan.get("reproduction_steps", []), start=1):
        lines.append(f"{index}. {display_prose(step)}")
    lines.extend([
        "",
        "- Evidence state: **not run** during Planning Lock.",
        "- Failure handling: a not-reproduced or inconclusive attempt enters `awaiting-reproduction-input`, blocks hypotheses and correction, preserves the run, and returns a focused sanitized input request to the user.",
    ])
    lines.extend(["", "## Plan", ""])
    for index, stage in enumerate(delivery.get("stages", []), start=1):
        lines.append(f"{index}. {display_prose(stage)}")
    guided_contract_boundary = (
        "- The proposal above is not yet a persisted or approved Debug reproduction artifact. After Planning Lock approval, DI-3 may persist it as a versioned draft; exact-revision approval remains separate."
        if isinstance(reproduction_contract, dict)
        else "- The Debug Intake artifact and reproduction contract are not created or approved by this Start command."
    )
    lines.extend(["", "## Guided delivery", "", f"- Boundary: {delivery.get('execution_boundary')}", guided_contract_boundary])
    lines.extend([
        "", "## Focused validation", "",
        "No validation has run during Planning Lock. The records below define the approved evidence path instead of implying a result.", "",
    ])
    append_stacked_records(lines, [
        (
            display_prose(row.get("tier")),
            [
                ("What it must prove", display_prose(row.get("proof_target"))),
                ("Candidate evidence", display_prose(row.get("candidate_evidence"))),
                ("Activation gate", display_prose(row.get("activation_gate"))),
                ("Pass condition", display_prose(row.get("pass_condition"))),
                *(([("Command after approval", f"`{row.get('command')}`")]) if row.get("command") else []),
            ],
        )
        for row in debug_plan.get("validation_rows", [])
    ])
    token = report["token_posture"]
    token_confidence = str(debug_plan.get("token_estimate_confidence", "low"))
    lines.extend(["", "## Token estimate", ""])
    if token_confidence == "low":
        lines.extend([
            "- Focused context estimate: **not claimed yet**.",
            f"- Confidence: **low** — {display_prose(debug_plan.get('token_estimate_reason'))}",
            "- A working-set estimate becomes available after reproduction and implementation-owner slices are resolved; actual model tokens still require run-linked host/provider telemetry.",
        ])
    else:
        lines.extend([
            f"- Estimated focused context budget: approximately `{token['used_tokens']}` tokens.",
            f"- Confidence: **{token_confidence}** — {display_prose(debug_plan.get('token_estimate_reason'))}",
            "- Evidence: local planning estimate only; actual model tokens require run-linked host/provider telemetry.",
        ])
        if host_diagnosis:
            estimate = host_diagnosis.get("token_estimate", {})
            lines.extend([
                f"- Full diagnosed-file ceiling: approximately `{estimate.get('full_scoped_file_ceiling_tokens', 0)}` tokens.",
                f"- Estimated scoped-context reduction: `{estimate.get('estimated_context_reduction_percent', 0)}%`.",
            ])
    breakdown = debug_plan.get("token_breakdown", {})
    if breakdown and token_confidence != "low":
        lines.append("")
        for label, key in (
            ("Planning and reproduction", "planning_and_reproduction"),
            ("Orientation and hypotheses", "orientation_and_hypotheses"),
            ("Bounded experiments", "bounded_experiments"),
            ("Correction and scope check", "correction_and_scope_check"),
            ("Validation and closure", "validation_and_closure"),
        ):
            lines.append(f"- **{label}:** `{breakdown.get(key, 0)}` estimated tokens.")
    lines.extend([
        "",
        "## Evidence posture",
        "",
        f"- Exactness: {debug_plan.get('exactness_posture')}",
        f"- Safety: {debug_plan.get('safety_boundary')}",
        (
            "- Bounded host source/artifact reads and static searches: **recorded**; project runtime commands, tests, builds, scanners, package managers, Git operations, external providers, Debug Intake, reproduction, and correction execution: **not run**."
            if host_diagnosis
            else "- Project commands, tests, graph helpers, scanners, Git commands, external providers, Debug Intake, reproduction, and correction execution: **not run**."
        ),
        "",
        "## Approval",
        "",
        (
            "- Approve this exact Debug Start Plan to allow DI-3 to persist the displayed proposal as a versioned reproduction draft under the same run ID; this does not approve that reproduction revision or execute it."
            if isinstance(reproduction_contract, dict)
            else "- Approve this exact Debug Start Plan to allow DI-3 to draft a reproduction contract under the same run ID."
        ),
        "- Reject or revise the symptom, scope, questions, evidence tiers, or safety boundary while keeping this run awaiting approval.",
        "- Use `--build` in a new Start request only if this should be treated as an implementation requirement instead of an unexplained symptom.",
        "",
    ])
    return "\n".join(lines)


def compact_behavior_trace_steps(trace: dict[str, Any]) -> list[str]:
    """Return the first actual output-to-producer path for legacy callers."""
    paths = compact_behavior_graph_paths(trace)
    if paths:
        return paths[0]
    nodes = {str(row.get("id")): row for row in trace.get("nodes", []) if isinstance(row, dict)}
    ordered: list[dict[str, Any]] = []
    for role in ("observed-output", "output-renderer", "data-transfer", "data-producer"):
        node = next((row for row in nodes.values() if row.get("role") == role), None)
        if node and node not in ordered:
            ordered.append(node)
    result: list[str] = []
    for node in ordered:
        label = str(node.get("path", ""))
        symbols = [str(value) for value in node.get("symbols", []) if value]
        if symbols:
            label += "::" + ",".join(symbols)
        if label and (not result or result[-1] != label):
            result.append(label)
    return result


def compact_behavior_graph_paths(trace: dict[str, Any], maximum: int = 6) -> list[list[str]]:
    """Enumerate bounded behavior-flow paths without flattening graph branches."""
    nodes = {str(row.get("id")): row for row in trace.get("nodes", []) if isinstance(row, dict)}
    edges = [
        row for row in trace.get("edges", [])
        if isinstance(row, dict) and row.get("relationship") != "exercises"
    ]
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in nodes}
    for edge in edges:
        source, target = str(edge.get("from")), str(edge.get("to"))
        if source in nodes and target in nodes:
            outgoing[source].append(target)
    topology = trace.get("topology") if isinstance(trace.get("topology"), dict) else {}
    entries = [str(value) for value in topology.get("entry_node_ids", []) if str(value) in nodes]
    if not entries:
        entries = [node_id for node_id, row in nodes.items() if row.get("role") == "observed-output"]
    paths: list[list[str]] = []

    def label(node_id: str) -> str:
        node = nodes[node_id]
        value = str(node.get("path", ""))
        symbols = [str(item) for item in node.get("symbols", []) if item]
        return value + ("::" + ",".join(symbols) if symbols else "")

    def visit(node_id: str, active: set[str], path: list[str]) -> None:
        if len(paths) >= maximum or node_id in active:
            return
        following = sorted(set(outgoing.get(node_id, [])))
        next_path = [*path, label(node_id)]
        if not following:
            paths.append(next_path)
            return
        for target in following:
            visit(target, active | {node_id}, next_path)

    for entry in entries:
        visit(entry, set(), [])
    unique: list[list[str]] = []
    for path in paths:
        collapsed = [value for index, value in enumerate(path) if value and (index == 0 or value != path[index - 1])]
        if collapsed and collapsed not in unique:
            unique.append(collapsed)
    return unique


def compact_debug_owner_summaries(
    owners: list[dict[str, Any]],
    host_diagnosis: dict[str, Any],
) -> list[str]:
    """Group repeated owner slices by path while retaining symbol-role evidence."""
    grouped: dict[str, list[str]] = {}
    for row in owners:
        path = str(row.get("path", ""))
        if not path:
            continue
        evidence_ids = grouped.setdefault(path, [])
        for evidence_id in row.get("evidence_ids", []):
            value = str(evidence_id)
            if value and value not in evidence_ids:
                evidence_ids.append(value)

    evidence_by_id = {
        str(row.get("id")): row
        for row in host_diagnosis.get("evidence", [])
        if isinstance(row, dict) and row.get("id")
    }
    summaries: list[str] = []
    for path, evidence_ids in grouped.items():
        details: list[str] = []
        matched = [evidence_by_id[value] for value in evidence_ids if value in evidence_by_id]
        if not matched:
            matched = [
                row
                for row in evidence_by_id.values()
                if row.get("path") == path and row.get("role") == "implementation-owner"
            ]
        for evidence in matched:
            roles = "/".join(
                str(value).replace("-", " ")
                for value in evidence.get("behavior_roles", [])
                if value
            )
            for symbol in evidence.get("symbols", []):
                detail = f"`{symbol}`"
                if roles:
                    detail += f" ({roles})"
                if detail not in details:
                    details.append(detail)
        summary = f"`{path}`"
        if details:
            summary += " — " + "; ".join(details)
        summaries.append(summary)
    return summaries


def compact_debug_start_report(report: dict[str, Any]) -> str:
    """Render the approval-critical Debug contract without audit repetition."""
    plan = report["navigator"]
    debug_plan = report["debug_plan"]
    delivery = report["guided_delivery"]
    lock = report.get("planning_lock")
    requirements = [row for row in plan.get("requirement_matrix", []) if isinstance(row, dict)]
    orientation = debug_plan.get("static_orientation", {}) if isinstance(debug_plan.get("static_orientation"), dict) else {}
    host = debug_plan.get("host_diagnosis") if isinstance(debug_plan.get("host_diagnosis"), dict) else {}
    reproduction = host.get("reproduction", {}) if isinstance(host.get("reproduction"), dict) else {}
    lines = ["# TailTrail Debug Start Plan", "", "## Planning Lock", ""]
    if lock:
        lines.extend([
            f"- Run ID: `{lock['run_id']}`",
            f"- State: **{lock['status']}**; managed writes allowed: **{str(lock['writes_allowed']).lower()}**.",
            "- Planning only: no reproduction, tests, source edits, or Git commands ran.",
        ])
    else:
        lines.append("- Not persisted; this report grants no implementation authority.")
    lines.extend(pipeline_badge_lines(lock if isinstance(lock, dict) else None, compact=True))

    lines.extend(["", "## Requirements", ""])
    for row in requirements:
        lines.append(requirement_line(row, "REQ-DEBUG-01"))
    if not requirements:
        lines.append("- Prove the reported symptom before approving a correction.")

    lines.extend(["", "## Scope", "", f"- Target: `{report['root']}`"])
    owners = [row for row in orientation.get("implementation_owners", []) if isinstance(row, dict)]
    proofs = [row for row in orientation.get("proof_paths", []) if isinstance(row, dict)]
    if owners:
        lines.append("- Likely owner: " + "; ".join(compact_debug_owner_summaries(owners, host)) + ".")
    else:
        lines.append("- Likely owner: unresolved; reproduction must resolve it before correction approval.")
    if proofs:
        lines.append("- Focused proof: " + ", ".join(f"`{row.get('path')}`" for row in proofs) + ".")
    else:
        lines.append("- Focused proof: unresolved.")
    lines.append("- These are orientation roles only, not approved correction scope.")

    lines.extend(["", "## Preliminary debug analysis", ""])
    completeness = host.get("evidence_completeness") if isinstance(host.get("evidence_completeness"), dict) else {}
    if completeness:
        lines.append(
            f"- **Evidence completeness:** `{completeness.get('status', 'unavailable')}` — "
            "TailTrail checks coverage and traceability; the host owns semantic interpretation."
        )
    proposal = host.get("proposal") if isinstance(host.get("proposal"), dict) else {}
    if proposal:
        lines.append(
            f"- **Typed host proposal:** `{proposal.get('route')}` for `{proposal.get('requirement_id')}`; "
            "references validated IDs only and grants no authority."
        )
    safe_fallback = debug_plan.get("safe_fallback") if isinstance(debug_plan.get("safe_fallback"), dict) else {}
    if safe_fallback:
        lines.append(
            f"- **Safe fallback:** `{safe_fallback.get('state')}`; correction scope `{safe_fallback.get('correction_scope')}`; "
            f"user input `{safe_fallback.get('user_input')}`. {display_prose(safe_fallback.get('next_action'))}"
        )
    findings = [row for row in host.get("findings", []) if isinstance(row, dict)]
    if findings:
        for row in findings[:3]:
            lines.append(
                f"- **{str(row.get('state', 'finding')).title()}:** "
                f"{display_prose(row.get('statement'))} (`{row.get('confidence', 'unknown')}`)"
            )
    else:
        lines.append("- No host diagnosis is attached; the approved reproduction must establish the first evidence.")
    if reproduction:
        lines.append(f"- Reproduction status: `{reproduction.get('status', 'not-run')}`; expected: {display_prose(reproduction.get('expected'))}")
    trace = debug_plan.get("behavior_trace") if isinstance(debug_plan.get("behavior_trace"), dict) else {}
    graph_paths = compact_behavior_graph_paths(trace)
    topology = trace.get("topology") if isinstance(trace.get("topology"), dict) else {}
    if graph_paths and topology.get("shape", "linear") != "linear":
        lines.append(
            f"- Backward behavior graph (`{trace.get('state', 'partial')}`, `{topology.get('shape')}`): "
            f"{topology.get('path_count', len(graph_paths))} bounded path(s)."
        )
        for index, path in enumerate(graph_paths, start=1):
            lines.append(f"  - Path {index}: " + " ← ".join(path) + ".")
    elif graph_paths:
        lines.append(f"- Backward trace (`{trace.get('state', 'partial')}`): " + " ← ".join(graph_paths[0]) + ".")

    lines.extend(["", "## Selected TailTrail features", ""])
    features = ["Navigator", *(
        str(row.get("name")) for row in delivery.get("selected", [])
        if isinstance(row, dict) and row.get("name")
    )]
    lines.append("- " + "; ".join(dict.fromkeys(features)) + ".")
    lines.append("- Mandatory path: reproduce → prove root cause → approve correction scope → validate → close.")

    lines.extend(["", "## Plan", ""])
    for index, stage in enumerate((
        "approve this Planning Lock and freeze one versioned reproduction",
        "run the approved reproduction and record factual evidence",
        "prove one root cause and eliminate a competing explanation",
        "approve and implement only the proven correction scope",
        "rerun reproduction, regression, preservation, and closure checks",
    ), start=1):
        lines.append(f"{index}. {stage}")

    lines.extend(["", "## Focused validation", ""])
    validation_rows = [row for row in debug_plan.get("validation_rows", []) if isinstance(row, dict)]
    seen_commands: set[str] = set()
    reproduction_command = next(
        (str(row.get("command")) for row in validation_rows if str(row.get("tier", "")).casefold() == "reproduction" and row.get("command")),
        "",
    )
    if reproduction_command:
        lines.append(f"- **Real reproduction:** `{reproduction_command}`")
        seen_commands.add(reproduction_command)
    else:
        proposed_steps = [
            display_prose(value)
            for value in reproduction.get("proposed_steps", [])
            if str(value).strip()
        ][:3]
        procedure = " → ".join(str(value).rstrip(".") for value in proposed_steps)
        fallback_requires_input = safe_fallback.get("user_input") == "required"
        guidance = (
            f" Proposed procedure: {procedure}."
            if procedure
            else " Provide the smallest command, artifact, or external observation needed to define a bounded reproduction."
            if fallback_requires_input
            else " Approve a bounded procedure that regenerates the failing artifact."
        )
        lines.append(
            "- **Real reproduction:** exact command unresolved."
            + guidance
            + (" Correction remains blocked until that input is available." if fallback_requires_input else " TailTrail continues through the approved Debug investigation without guessing correction scope.")
        )
    displayed_assertions: set[str] = set()
    for row in host.get("test_cases", []):
        tier = str(row.get("tier", "")).casefold()
        statement = str(display_prose(row.get("statement")))
        if tier == "reproduction" or not statement or statement in displayed_assertions:
            continue
        boundaries = ", ".join(str(value) for value in row.get("proof_boundaries", [])) or "unresolved boundary"
        lines.append(f"- **{row.get('id')} — {tier.title()} assertion ({boundaries}):** {statement}")
        displayed_assertions.add(statement)
    for row in validation_rows:
        command = str(row.get("command") or "")
        if command and command not in seen_commands:
            detail = "existing proof path; add the proposed assertion if it is missing" if str(row.get("tier", "")).casefold() in {"regression", "behaviour", "behavior"} else "focused proof"
            lines.append(f"- **{display_prose(row.get('tier'))}:** `{command}` ({detail}).")
            seen_commands.add(command)
    lines.append("- Preservation: keep genuine steps, order, statuses, details, and supported report behavior unchanged.")
    lines.append("- No validation has run during Planning Lock.")

    token = report["token_posture"]
    confidence = str(debug_plan.get("token_estimate_confidence", "low"))
    lines.extend(["", "## Token estimate", ""])
    if confidence == "low":
        lines.append("- Focused estimate unavailable until owner and proof slices are resolved.")
    else:
        lines.append(f"- Approximately `{token['used_tokens']}` focused-context tokens (context-estimate confidence: `{confidence}`; this is not root-cause confidence).")

    lines.extend([
        "", "## Approval", "",
        "- Approval freezes this planning boundary and creates the reproduction draft only; it runs no command and grants no source-edit authority.",
        f"- Next: review and separately approve the exact reproduction revision. Prompt: `Approve plan {lock['run_id']}`." if lock else "- Approve only after a persisted run ID is available.",
        "- Use `--verbose` only for complete evidence, lifecycle, and token-accounting detail.",
    ])
    return "\n".join(lines) + "\n"


def compact_start_report(report: dict[str, Any]) -> str:
    """Keep the normal Start response short enough to approve confidently."""
    plan = report["navigator"]
    delivery = report["guided_delivery"]
    lock = report.get("planning_lock")
    impacted = [item for item in plan.get("likely_impacted_files", []) if isinstance(item, dict)]
    root = Path(str(report["root"]))
    goal = display_prose(report["goal"])
    lowered_goal = goal.lower()
    requirement_rows = [item for item in plan.get("requirement_matrix", []) if isinstance(item, dict)]
    lines = ["# TailTrail Start Plan", "", f"**Goal:** {goal}", ""]
    if lock:
        lines.extend(
            [
                "## Planning Lock",
                "",
                f"- Run ID: `{lock['run_id']}`",
                f"- Target identity: `{lock.get('target_identity', {}).get('fingerprint', 'legacy lock')}`.",
                "- Status: **awaiting approval** - no source files, tests, scanners, or Git changes were run.",
                "",
            ]
        )
        if isinstance(lock.get("scope_decision"), dict):
            lines.append(f"- Scope decision: `{lock['scope_decision'].get('decision_fingerprint')}` (v2, evidence-bound).")
        host = lock.get("host_workspace")
        if isinstance(host, dict) and host.get("host"):
            lines.append(f"- Host workspace: `{host.get('host')}` / `{host.get('status')}` ({host.get('mapping', 'not-mapped')}).")
        policy = lock.get("enterprise_policy")
        if isinstance(policy, dict):
            lines.append(f"- Enterprise target policy: `{policy.get('status', 'not-configured')}`.")
    workflow_runtime = report.get("workflow_runtime", {})
    if isinstance(workflow_runtime, dict) and workflow_runtime.get("enabled"):
        lines.extend(["", "## Workflow runtime", "", f"- Draft: `{workflow_runtime.get('workflow_id')}` - no durable workflow artifacts exist before approval.", "- After approval: bind the canonical anchor, declare selected capabilities, and freeze the non-executing compiler graph."])
    lines.extend(["", "## Requirements", ""])
    append_requirement_interpretation(lines, plan)
    for item in requirement_rows:
        lines.append(requirement_line(item))
    if not requirement_rows:
        lines.append("- Implement the approved goal with the smallest maintainable change.")
    lines.extend(["", "## Scope", ""])
    target = report.get("target_root")
    if isinstance(target, dict) and target.get("requested"):
        lines.append(f"- Target repository: `{target['requested']}` ({target.get('status', 'verified')}).")
    v2_rendered = append_v2_scope_projection(lines, plan, responsive=True)
    if not v2_rendered:
        for item in impacted[:4]:
            lines.append(f"- `{item['path']}` - {display_prose(item['reason'])}")
    if not v2_rendered and not impacted:
        if report.get("ui_plan", {}).get("selected"):
            lines.append("- UI implementation surface not discovered. Confirm the frontend/UI root or approve bounded read-only UI discovery; backend files were not substituted as UI scope.")
        else:
            lines.append("- Scope unresolved: no reliable repository file matched this goal. Add `--changed path/to/file` or approve read-only discovery; unrelated Git changes were not used.")
    roles = report.get("input_roles", {})
    if isinstance(roles, dict):
        read_only_count = max(0, len(roles.get("inputs", [])) - 1)
        lines.extend(["", "## Input roles", "", f"- Target: `{roles.get('target_root', root.as_posix())}` - editable only after approval.", f"- Read-only inputs: {read_only_count}. References, design, requirements, and evidence cannot become implementation scope."])
    lines.extend(ui_planning.contract_lines(report.get("ui_plan", {}), responsive=True))
    hands_free_program = delivery.get("hands_free_program")
    spec_kit_source = report.get("spec_kit_source")
    if isinstance(spec_kit_source, dict):
        lines.extend(["", "## Requirement authority", "", f"- Source: `{spec_kit_source['feature_id']}` / `{spec_kit_source['source_revision']}` (imported snapshot v{spec_kit_source['snapshot_version']})."])
    aidlc = report.get("aidlc_requirements")
    if isinstance(aidlc, dict):
        stage = aidlc.get("aidlc_stage", {})
        if aidlc.get("state") == "official-aidlc-host-generation-required":
            lines.extend(["", "## Official AIDLC requirements", "", "- The verified official Requirements Analysis stage is ready for the configured host.", "- The host must load the recorded official rules and saved Question Orchestrator context, then generate material questions with requirement traceability, options, TailTrail advisory recommendations, and evidence-grounded reasoning before implementation can be approved.", "- TailTrail validates grounding and persists that official stage artifact under this same run ID; it will not fabricate a local substitute questionnaire.", ""])
        elif aidlc.get("state") == "authority-bound-in-start-plan":
            lines.extend([
                "",
                "## Official AIDLC requirement authority",
                "",
                "- Status: `authority-bound-before-scope`.",
                f"- Mode: `{aidlc.get('mode')}`; stage: `{aidlc.get('stage')}`.",
                f"- {aidlc.get('boundary')}",
                f"- Approval gate: {aidlc.get('approval_gate')}",
            ])
        else:
            lines.extend(["", "## AIDLC requirements and recommendations", "", "- Assumption: " + "; ".join(stage.get("assumptions", [])), "- Non-goal: " + "; ".join(stage.get("non_goals", [])), ""])
            for question in aidlc.get("questions", []):
                lines.extend([f"### {question.get('id', 'Question')} - {display_prose(question.get('question', ''))}", f"- **Recommended:** {display_prose(question.get('recommended', ''))}", f"- **Reasoning:** {display_prose(question.get('reasoning', ''))}", ""])
    aidlc_mode = report.get("aidlc_mode", {})
    if isinstance(aidlc_mode, dict):
        lines.extend(["", "## AIDLC mode", "", f"- Selected mode: `{aidlc_mode.get('mode')}`", f"- Selection: `{aidlc_mode.get('selection')}`", f"- State: `{aidlc_mode.get('state')}`", f"- Boundary: {aidlc_mode.get('boundary')}"])
        requested_mode = aidlc_mode.get("requested_mode")
        if requested_mode and requested_mode != aidlc_mode.get("mode"):
            lines.append(f"- Requested mode: `{requested_mode}` (fell back to `{aidlc_mode.get('mode')}`)")
        escalation = aidlc_mode.get("full_escalation", {})
        if isinstance(escalation, dict): lines.append(f"- Full escalation: `{escalation.get('state')}` - {display_prose(escalation.get('reason'))}")
        if aidlc_mode.get("mode") in {"standard", "full"}:
            lines.append("- Official stage: verified official Requirements Analysis rules govern these questions; the host generates them and TailTrail validates/imports approved decisions before freezing the anchor.")
    mode_features = report.get("aidlc_mode_features", {})
    if isinstance(mode_features, dict):
        lines.extend(["", "## AIDLC mode features", "", "### Included", ""])
        included = mode_features.get("included", []); excluded = mode_features.get("not_included", [])
        lines.extend(f"- {display_prose(item)}" for item in included)
        if not included:
            lines.append("- None.")
        lines.extend(["", "### Not included in this mode", ""])
        lines.extend(f"- {display_prose(item)}" for item in excluded)
        if not excluded:
            lines.append("- None.")
    selected = [item for item in delivery.get("selected", []) if isinstance(item, dict)]
    feature_rows = [("Navigator", "Planning now", "created this scoped Planning Lock and approval gate")]
    graph_why = code_review_graph_lite_why(impacted)
    if graph_why:
        feature_rows.append(("Code Review Graph Lite", "Planning now", graph_why))
    feature_rows.extend(
        (
            str(item.get("name", "TailTrail control")),
            feature_when(str(item.get("name", "")), item.get("when")),
            str(item.get("why", "Selected for this task.")),
        )
        for item in selected
    )
    if feature_rows:
        lines.extend(["", "## Selected TailTrail features", ""])
        append_stacked_records(lines, [
            (display_prose(name), [("When", display_prose(when)), ("Used for this task", display_prose(why))])
            for name, when, why in feature_rows
        ])
    lines.extend(architecture_planning.markdown_lines(report.get("architecture_plan", {}), detailed=False, responsive=True))
    lines.extend(behaviour_planning.markdown_lines(report.get("behaviour_plan", {}), detailed=False, responsive=True))
    lines.extend(maintainability_planning.markdown_lines(report.get("maintainability_plan", {}), detailed=False, responsive=True))
    lines.extend(["", "## Plan", ""])
    for index, stage in enumerate(delivery.get("stages", []), start=1):
        lines.append(f"{index}. {display_prose(stage)}")
    if report.get("ui_consistency", {}).get("selected"):
        lines.append(f"- UI discovery: `{report['ui_consistency']['command']}`")
        lines.append(f"- Preserve: {report['ui_consistency']['boundary']}")
    if hands_free_program:
        lines.append("")
        lines.append("- Proposed dependency order:")
        for index, stage in enumerate(hands_free_program["dependency_order"], start=1):
            lines.append(f"  {index}. {stage}")
        lines.append(f"- First active slice: {hands_free_program['first_active_slice']}")
        lines.append(f"- Program approval gate: {hands_free_program['approval_gate']}")
    lines.extend(pipeline_badge_lines(lock if isinstance(lock, dict) else None))
    append_testing_plan(lines, report.get("testing_plan", {}))
    lines.extend(["", "## Required later in this run", ""])
    for row in required_later_rows(delivery):
        lines.append(f"- **{row.get('name')}:** {display_prose(row.get('when'))}. This is mandatory before completion.")
    validation_rows = report.get("focused_validation") or focused_validation_plan(root, impacted, requirement_rows, str(report["command_prefix"]))
    lines.extend(["", "## Validation", "", "### Focused validation", ""])
    validation_records = []
    for item in validation_rows:
        detail = f"`{item['command']}`" if item["command"] else item["status"]
        validation_records.append((display_prose(item["tier"]), [("Candidate", f"`{item['candidate']}` ({item.get('candidate_state', 'unknown')})"), ("Status / command", detail)]))
    append_stacked_records(lines, validation_records)
    token = report["token_posture"]
    lines.extend(["", "## Token posture", ""])
    lines.extend(token_estimate_lines(token, detailed=False))
    lines.extend(["", "## Approval", ""])
    if isinstance(aidlc, dict) and aidlc.get("state") == "official-aidlc-host-generation-required":
        lines.append("- The official Requirements Analysis questions must be generated, answered, and explicitly approved before TailTrail can freeze the anchor or begin implementation.")
    else:
        lines.append("- Approve this AIDLC-backed plan to accept its recommendations and begin implementation, or reject it for deeper AIDLC refinement." if isinstance(aidlc, dict) else "- Approve this plan to begin implementation, or name any file/scope change before approval.")
    if delivery.get("hands_free_program"):
        lines.append("- This is a hands-free request; approve the proposed program slices before implementation begins.")
    if report.get("ui_plan", {}).get("surface_status") == "not-discovered":
        lines.append("- UI scope must be confirmed before implementation approval; TailTrail will not treat backend candidates as the missing UI surface.")
    lines.extend(["", "Run with `--verbose` for advanced harness, token, code-intelligence, recovery, and product-metrics detail.", ""])
    return "\n".join(lines)


def quick_start_report(report: dict[str, Any]) -> str:
    """Render the concise complete contract for a new or occasional user."""
    plan = report["navigator"]
    delivery = report["guided_delivery"]
    lock = report.get("planning_lock")
    root = Path(str(report["root"]))
    impacted = [item for item in plan.get("likely_impacted_files", []) if isinstance(item, dict)]
    requirements = [item for item in plan.get("requirement_matrix", []) if isinstance(item, dict)]
    aidlc_mode = report.get("aidlc_mode", {}) if isinstance(report.get("aidlc_mode"), dict) else {}
    token = report["token_posture"]
    lines = ["# TailTrail Start Plan", "", "## Planning Lock", ""]
    if lock:
        lines.extend([
            f"- Run ID: `{lock['run_id']}`",
            f"- State: **{lock['status']}**; managed writes allowed: **{str(lock['writes_allowed']).lower()}**.",
            "- No source files, tests, scanners, or Git changes were run.",
        ])
        if isinstance(lock.get("scope_decision"), dict):
            lines.append(f"- Scope decision: `{lock['scope_decision'].get('decision_fingerprint')}` (v2, evidence-bound).")
    else:
        lines.append("- Not persisted; this output does not grant implementation authority.")
    lines.extend(["", "## Goal", "", f"- {display_prose(report['goal'])}", "", "## Requirements", ""])
    append_requirement_interpretation(lines, plan)
    for item in requirements:
        lines.append(requirement_line(item))
    if not requirements:
        lines.append("- Implement the approved goal and preserve existing behavior.")
    lines.extend(["", "## Scope", ""])
    v2_rendered = append_v2_scope_projection(lines, plan, responsive=True)
    if not v2_rendered and impacted:
        for item in impacted[:3]:
            lines.append(f"- `{item.get('path')}` - {display_prose(item.get('reason'))}")
        if len(impacted) > 3:
            lines.append(f"- `{len(impacted) - 3}` additional candidate path(s) remain in the saved plan.")
    elif not v2_rendered:
        lines.append("- Scope is unresolved; bounded discovery is required after approval.")
    lines.extend(ui_planning.contract_lines(report.get("ui_plan", {}), responsive=True))
    lines.extend([
        "", "## AIDLC mode", "",
        f"- `{aidlc_mode.get('mode', 'lite')}` - {display_prose(aidlc_mode.get('boundary', 'The saved plan remains the authority.'))}",
        "", "## Selected TailTrail features", "",
        "- **Navigator**",
        "  - **Why:** Scoped the Planning Lock and approval boundary.",
    ])
    for item in delivery.get("selected", []):
        if isinstance(item, dict):
            lines.extend([
                f"- **{display_prose(item.get('name'))}**",
                f"  - **Why:** {display_prose(item.get('why'))}",
            ])
    lines.extend(["", "## Plan", ""])
    for index, stage in enumerate(delivery.get("stages", []), start=1):
        lines.append(f"{index}. {display_prose(stage)}")
    append_testing_plan(lines, report.get("testing_plan", {}))
    lines.extend(["", "## Required later in this run", ""])
    for row in required_later_rows(delivery):
        lines.append(f"- **{row.get('name')}:** {display_prose(row.get('when'))}. This is mandatory before completion.")
    lines.extend(["", "## Focused validation", ""])
    validation_rows = report.get("focused_validation") or focused_validation_plan(root, impacted, requirements, str(report["command_prefix"]))
    for row in validation_rows:
        proof = f"`{row['command']}`" if row["command"] else row["status"]
        lines.append(f"- **{row['tier']}:** {proof}")
    lines.extend([
        "- No validation has run during Planning Lock.",
        "", "## Token estimate", "",
    ])
    lines.extend(token_estimate_lines(token, detailed=False))
    lines.extend([
        "", "## Approval", "",
        "- Approve this exact plan, discuss or revise it. Use `--verbose` only when the complete audit projection is needed.",
    ])
    return "\n".join(lines) + "\n"


def scope_quality_boundary_report(report: dict[str, Any]) -> dict[str, Any]:
    plan = report.get("navigator", {}) if isinstance(report, dict) else {}
    scope_evidence = plan.get("scope_evidence", {}) if isinstance(plan.get("scope_evidence"), dict) else {}
    lifecycle = report.get("graph_lifecycle") if isinstance(report.get("graph_lifecycle"), dict) else {}
    graph_written = bool(lifecycle.get("written"))
    precondition = report.get("scope_question_precondition")
    if not isinstance(precondition, dict):
        precondition = scope_question_precondition(
            plan.get("requirement_interpretation")
        )
    quality = dict(plan.get("scope_quality", {}))
    if not precondition.get("scope_question_allowed"):
        quality["question"] = None
        quality["question_validation"] = {
            "state": "deferred-until-requirements-sufficient",
            "eligible_options": 0,
            "offered_options": 0,
            "rejected_candidates": 0,
            "truncated": False,
        }
    return {
        "goal": report.get("goal", ""),
        "root": report.get("root", ""),
        "command_prefix": report.get("command_prefix", "tailtrail"),
        "scope_quality_boundary": True,
        "scope_quality": quality,
        "scope_question_precondition": precondition,
        "scope_evidence": scope_evidence,
        "scope_host_packet": plan.get("scope_host_packet"),
        "host_scope_proposal_decision": report.get("host_scope_proposal_decision"),
        "investigation": scope_evidence.get("investigation", {}),
        "requirements": (plan.get("requirement_query_frame", {}) or {}).get("requirements", []),
        "requirement_interpretation": plan.get("requirement_interpretation", {}),
        "candidates": [
            {
                "path": row.get("path"),
                "role": row.get("role"),
                "status": row.get("status"),
                "confidence": row.get("confidence"),
                "reason_codes": row.get("reason_codes", []),
            }
            for row in plan.get("scope_candidates", [])
            if isinstance(row, dict) and row.get("status") not in {"rejected"}
        ],
        "target_identity_assessment": report.get("target_identity_assessment", report.get("target_fit", {})),
        "graph_lifecycle": lifecycle,
        "boundary": (
            "Navigator updated TailTrail graph metadata, but no Planning Lock, workflow, target receipt, learning receipt, or implementation authority was created."
            if graph_written
            else "No Planning Lock, workflow, target receipt, learning receipt, graph-cache write, or implementation authority was created."
        ),
    }


def render_scope_quality_boundary_report(report: dict[str, Any], *, verbose: bool = False) -> str:
    quality = report.get("scope_quality", {})
    investigation = report.get("investigation", {}) if isinstance(report.get("investigation"), dict) else {}
    cache = investigation.get("cache", {}) if isinstance(investigation.get("cache"), dict) else {}
    host_packet = report.get("scope_host_packet") if isinstance(report.get("scope_host_packet"), dict) else {}
    host_route = host_packet.get("route") if isinstance(host_packet.get("route"), dict) else {}
    host_decision = report.get("host_scope_proposal_decision") if isinstance(report.get("host_scope_proposal_decision"), dict) else {}
    precondition = report.get("scope_question_precondition") if isinstance(report.get("scope_question_precondition"), dict) else {}
    decision_reason = str(
        investigation.get("decision_reason")
        or quality.get("primary_reason")
        or investigation.get("stop_reason", "scope-unresolved")
    )
    reason_explanations = {
        "multiple-evidence-backed-owners": "More than one implementation owner has strong evidence; TailTrail needs the runtime path that reproduces the behavior.",
        "multiple-complete-renderer-chains": "More than one complete renderer chain remains; TailTrail cannot safely choose one editable UI owner.",
        "renderer-behavior-chain-incomplete": "The source module was found, but its value could not be followed through a complete call-to-render chain.",
        "renderer-edge-ambiguous-module-alias": "The relevant module alias resolves to multiple repository files, so the renderer edge is ambiguous.",
        "renderer-edge-unresolved-module-alias": "The relevant renderer import could not be resolved with the repository's bounded module configuration.",
        "renderer-caller-edge-not-found": "The message source was found, but no direct renderer or caller edge was proven.",
        "implementation-owner-evidence-not-found-before-limit": "The bounded investigation exhausted an applicable read budget before proving an implementation owner.",
        "implementation-owner-evidence-not-found": "The bounded repository evidence did not prove an implementation owner.",
    }
    actionable_reason = reason_explanations.get(
        decision_reason,
        "Repository evidence did not prove one safe editable boundary for every requirement.",
    )
    lines = [
        "# TailTrail Scope Confirmation Required",
        "",
        f"**Goal:** {display_prose(report.get('goal', ''))}",
        "",
        "## Scope-quality gate",
        "",
        f"- Status: **{quality.get('status', 'blocked')}**.",
        f"- Evidence state: `{quality.get('evidence_state', 'unresolved')}`.",
        f"- Request mode: `{quality.get('mode', 'code-change')}`.",
        f"- Requirement-to-scope precedence: `{precondition.get('state', 'unknown')}` ({precondition.get('reason_code', 'not-recorded')}).",
        f"- Actionable reason: {actionable_reason}",
        f"- {report.get('boundary')}",
        "",
        "## Why TailTrail stopped",
        "",
        f"- {actionable_reason}",
        f"- Graph evidence: `{cache.get('status', 'not-checked')}` persistent cache; bounded source relationships were checked independently.",
        f"- Active-host reasoning: `{host_route.get('state', 'unavailable')}` ({host_route.get('reason_code', 'host-reasoning-route-not-recorded')}).",
        "- Candidate paths remain advisory evidence; none grants implementation authority.",
        "",
        "## Requirements",
        "",
    ]
    lifecycle = report.get("graph_lifecycle") if isinstance(report.get("graph_lifecycle"), dict) else {}
    if lifecycle:
        lines.insert(10, f"- Navigator graph management: `{lifecycle.get('action', 'unknown')}`; cache `{lifecycle.get('after_status', {}).get('status', 'unknown')}`.")
    append_requirement_interpretation(lines, {"requirement_interpretation": report.get("requirement_interpretation", {})})
    for row in report.get("requirements", []):
        if isinstance(row, dict):
            lines.append(requirement_line(row))
    if verbose:
        limit_state = investigation.get("limit_state", {}) if isinstance(investigation.get("limit_state"), dict) else {}
        module_resolution = investigation.get("module_resolution", {}) if isinstance(investigation.get("module_resolution"), dict) else {}
        behavior_chains = investigation.get("behavior_chains", {}) if isinstance(investigation.get("behavior_chains"), dict) else {}
        question_validation = quality.get("question_validation", {}) if isinstance(quality.get("question_validation"), dict) else {}
        lines.extend([
            "",
            "## Complete scope diagnostics",
            "",
            f"- Decision reason: `{decision_reason}`.",
            f"- Resolution failure: `{investigation.get('resolution_failure_reason') or 'none'}`.",
            f"- Read-loop termination: `{limit_state.get('termination_reason', 'not-recorded')}`; limit state: `{limit_state.get('state', 'not-recorded')}`.",
            f"- Read budgets: cache validation `{limit_state.get('cache_validation_files_read', 0)}`; broad `{limit_state.get('broad_files_read', 0)}/{limit_state.get('broad_file_limit', 'unknown')}`; relationship `{limit_state.get('relationship_files_read', 0)}/{limit_state.get('relationship_file_limit', 'unknown')}` from `{limit_state.get('relationship_candidates', 0)}` targeted candidates; resolver config `{limit_state.get('config_files_read', 0)}/{limit_state.get('config_file_limit', 'unknown')}`.",
            f"- Bytes and hops: `{investigation.get('bytes_read', 0)}` bytes; `{investigation.get('relationship_hops', 0)}` relationship hops.",
            f"- Module resolution: `{module_resolution.get('state', 'not-recorded')}`; resolved `{module_resolution.get('resolved', 0)}`, ambiguous `{module_resolution.get('ambiguous', 0)}`, unresolved `{module_resolution.get('unresolved', 0)}`.",
            f"- Behavior chain: `{behavior_chains.get('state', 'not-recorded')}`.",
            f"- Host proposal: `{host_decision.get('status', 'not-submitted')}`; packet `{host_packet.get('packet_fingerprint', 'not-recorded')}`.",
            "- Scope reason codes: " + ", ".join(f"`{value}`" for value in quality.get("reason_codes", [])) + ".",
            "- Limit reason codes: " + ", ".join(f"`{value}`" for value in limit_state.get("reason_codes", [])) + ".",
            "- Resolver reason codes: " + ", ".join(f"`{value}`" for value in module_resolution.get("reason_codes", [])) + ".",
            "- Cache reason codes: " + ", ".join(f"`{value}`" for value in cache.get("reason_codes", [])) + ".",
            f"- Scope-question validation: `{question_validation.get('state', 'not-recorded')}`; eligible `{question_validation.get('eligible_options', 0)}`, offered `{question_validation.get('offered_options', 0)}`, rejected `{question_validation.get('rejected_candidates', 0)}`, truncated `{str(question_validation.get('truncated', False)).lower()}`.",
        ])
        candidates = [row for row in report.get("candidates", []) if isinstance(row, dict)]
        lines.extend(["", "### Candidate diagnostics", ""])
        if candidates:
            append_stacked_records(lines, [
                (
                    f"`{row.get('path')}`",
                    [
                        ("Role", f"`{row.get('role', 'unknown')}`"),
                        ("Status", f"`{row.get('status', 'unknown')}`"),
                        ("Confidence", f"`{row.get('confidence', 'none')}`"),
                        ("Reasons", display_prose(", ".join(row.get("reason_codes", [])) or "none")),
                    ],
                )
                for row in candidates
            ])
        else:
            lines.append("- No safe candidate rows were retained.")
    question = quality.get("question") if precondition.get("scope_question_allowed") is True else None
    if isinstance(question, dict):
        lines.extend(["", "## One bounded scope question", "", f"**{question.get('question_id')}:** {display_prose(question.get('question', ''))}"])
        option_details = {
            str(row.get("path")): row
            for row in question.get("option_evidence", [])
            if isinstance(row, dict)
        }
        for option in question.get("options", []):
            detail = option_details.get(str(option), {})
            lines.append(f"- `{option}`")
            if detail:
                lines.append(f"  - Evidence: {display_prose(detail.get('evidence', 'strong owner evidence'))}.")
                lines.append(f"  - Missing discriminator: {display_prose(detail.get('missing_discriminator', 'runtime ownership'))}.")
        question_validation = quality.get("question_validation", {})
        if isinstance(question_validation, dict) and question_validation.get("truncated"):
            hidden = max(
                0,
                int(question_validation.get("eligible_options", 0))
                - int(question_validation.get("offered_options", 0)),
            )
            lines.append(
                f"- `{hidden}` additional evidence-backed alternative(s) were omitted by the question-size cap; provide a different known owner path if needed."
            )
        lines.extend(["", f"- Response format: {display_prose(question.get('answer_format', ''))}", f"- {display_prose(question.get('boundary', ''))}"])
    elif precondition.get("scope_question_allowed") is True:
        lines.extend([
            "",
            "## Next action",
            "",
            "- Provide one implementation-owner path with `--changed <path>`, or clarify that the request is tests-only or documentation-only.",
            "- TailTrail will rerun the same bounded investigation before creating a Planning Lock.",
        ])
    else:
        lines.extend([
            "",
            "## Requirement intake first",
            "",
            f"- {display_prose(precondition.get('boundary', 'Resolve material requirement decisions before scope discovery.'))}",
            "- No implementation-owner question is eligible at this stage.",
        ])
    return "\n".join(lines) + "\n"


def scope_investigation_boundary_report(goal: str, root: Path, status: dict[str, Any], command_prefix: str) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "type": "tailtrail-scope-investigation-unavailable",
        "goal": goal,
        "root": root.as_posix(),
        "command_prefix": command_prefix,
        "scope_investigation_boundary": True,
        "status": "scope-investigation-unavailable",
        "source": status["source"],
        "reason_code": status["reason_code"],
        "policy_path": status["policy_path"],
        "fallback": "none",
        "planning_lock": None,
        "boundary": "No repository investigation, Planning Lock, workflow, target receipt, learning receipt, graph cache, or implementation authority was created. Lexical-only scope is not available as a fallback.",
    }


def render_scope_investigation_boundary_report(report: dict[str, Any]) -> str:
    return "\n".join([
        "# TailTrail Scope Investigation Unavailable",
        "",
        f"**Goal:** {display_prose(report.get('goal', ''))}",
        "",
        "## Release safety boundary",
        "",
        "- Status: `scope-investigation-unavailable`.",
        f"- Source: `{report.get('source', 'unknown')}`.",
        f"- Reason code: `{report.get('reason_code', 'unknown')}`.",
        f"- Policy: `{report.get('policy_path', navigator_scope.SCOPE_POLICY_PATH.as_posix())}`.",
        "- Fallback: `none`; lexical-only scope and scope-gate bypass are disabled.",
        "- Planning Lock: not created.",
        "",
        "## Recovery",
        "",
        f"- Diagnose: `{report.get('command_prefix', 'tailtrail')} eval scope rollback-status --root . --format json`",
        "- Re-enable only after the v2 investigation failure is diagnosed and the packaged release is verified.",
        "",
        f"- {report.get('boundary')}",
    ]) + "\n"


def debug_diagnosis_boundary_report(goal: str, root: Path, host: str, command_prefix: str) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "type": "tailtrail-debug-diagnosis-required",
        "goal": goal,
        "root": root.as_posix(),
        "host": host,
        "command_prefix": command_prefix,
        "debug_diagnosis_boundary": True,
        "aidlc_mode": {"mode": "off"},
        "planning_lock": None,
        "schema": "schemas/debug-host-diagnosis.schema.json",
        "required_checks": [
            "bounded relevant source and owning symbols",
            "direct callers and configuration involved in the symptom",
            "focused existing or proposed proof paths and concrete test cases",
            "explicitly supplied local error/report artifacts when safely readable",
        ],
        "boundary": "No Planning Lock, reproduction, project command, test, build, scanner, Git operation, correction authority, or source write was created.",
    }


def host_requirement_interpretation_boundary_report(
    goal: str,
    root: Path,
    host: str,
    command_prefix: str,
    artifact_inputs: list[dict[str, Any]] | None = None,
    official_authority: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Require the active agent host to interpret ordinary Build requirements."""
    return {
        "schema_version": "1",
        "type": "tailtrail-host-requirement-interpretation-required",
        "goal": goal,
        "root": root.as_posix(),
        "host": host,
        "command_prefix": command_prefix,
        "host_requirement_interpretation_boundary": True,
        "status": "awaiting-host-interpretation",
        "planning_lock": None,
        "schema": "schemas/requirement-interpretation.schema.json",
        "contract": {
            "clauses": ["context", "outcome", "constraint", "evidence", "scope", "question"],
            "maximum_material_questions": 3,
            "private_reasoning_excluded": True,
            "exact_goal_bound": True,
            "authority": (
                "official-ai-dlc-pack"
                if official_authority is not None
                else "interpretation-only"
            ),
        },
        "requirement_artifacts": [
            {
                "input_id": item["input_id"],
                "locator": item["locator"],
                "sha256": item["sha256"],
                "size_bytes": item["size_bytes"],
                "status": "inspected",
            }
            for item in (artifact_inputs or [])
        ],
        "official_requirement_authority": official_authority,
        "boundary": (
            "No deterministic fallback, graph lifecycle, scope decision, Planning Lock, workflow, "
            "or implementation authority was created for this agent-host Build request."
        ),
    }


def render_host_requirement_interpretation_boundary_report(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Host Requirement Interpretation Required",
        "",
        f"**Goal:** {display_prose(report.get('goal', ''))}",
        "",
        "## State",
        "",
        f"- Active host: `{report.get('host')}`.",
        "- Status: `awaiting-host-interpretation`.",
        "- Planning Lock: not created.",
        "",
        "## Required host action",
        "",
        "- Classify only the exact current goal into context, outcome, constraint, evidence, scope, or question clauses.",
        "- Read every inspected requirement artifact listed below and bind each artifact-derived clause with its input ID and exact SHA-256.",
        "- Create requirement rows only from outcome, constraint, or scope clauses.",
        "- Return at most three material questions when implementation-affecting decisions remain.",
        "- Keep quoted UI or error text out of semantic intent terms.",
        "- Exclude private reasoning and invent no behavior, path, fact, approval, or authority beyond the supplied verified receipt.",
        f"- Validate against `{report.get('schema')}` and resubmit through MCP `requirement_interpretation` or CLI `--requirement-interpretation`.",
    ]
    artifacts = report.get("requirement_artifacts", [])
    if artifacts:
        lines.extend(["", "## Required planning inputs", ""])
        for item in artifacts:
            lines.extend([
                f"- `{item['input_id']}`: `{item['locator']}`",
                f"  - Status: `inspected`; SHA-256: `{item['sha256']}`; bytes: `{item['size_bytes']}`.",
            ])
    authority = report.get("official_requirement_authority")
    if isinstance(authority, dict):
        lines.extend([
            "",
            "## Official requirement authority",
            "",
            f"- Mode: `{authority.get('mode')}`; stage: `{authority.get('stage')}`.",
            f"- Source revision: `{authority.get('revision')}`.",
            "- Read every governing rule below before producing the typed requirement interpretation:",
        ])
        lines.extend(
            f"  - `{name}`: `{path}`"
            for name, path in authority.get("references", {}).items()
        )
        lines.extend([
            "- Set `authority` to `official-ai-dlc-pack`, bind the exact mode and Requirements stage, and return the exact `authority_references` mapping.",
            "- The official requirement rows and unresolved material decisions must be established before Navigator performs repository scope discovery.",
        ])
    lines.extend(["", f"- {report.get('boundary')}"])
    return "\n".join(lines) + "\n"


def requirement_artifact_boundary_report(
    goal: str,
    root: Path,
    preparation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "type": "tailtrail-required-planning-input-unavailable",
        "goal": goal,
        "root": root.as_posix(),
        "status": "required-planning-input-unavailable",
        "requirement_artifact_boundary": True,
        "planning_lock": None,
        "inputs": preparation.get("blocking", []),
        "input_roles": preparation.get("registry", {}),
        "boundary": "Requirement sufficiency, scope discovery, graph lifecycle, and Planning Lock creation did not run.",
    }


def render_requirement_artifact_boundary_report(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Required Planning Input Unavailable",
        "",
        f"**Goal:** {display_prose(report.get('goal', ''))}",
        "",
        "## Why planning stopped",
        "",
        "- One or more declared requirement artifacts could not be inspected completely as bounded UTF-8 text.",
    ]
    for item in report.get("inputs", []):
        lines.append(
            f"- `{item.get('input_id')}`: `{item.get('status')}` (`{item.get('reason_code')}`)."
        )
    lines.extend([
        "",
        "## Recovery",
        "",
        "- Provide an existing readable `.md`, `.txt`, `.text`, `.rst`, `.adoc`, `.json`, `.yaml`, or `.yml` requirement artifact within the bounded read limit.",
        "- Then rerun the same Start request; the artifact will be hash-bound before requirements or scope are accepted.",
        "",
        f"- {report.get('boundary')}",
    ])
    return "\n".join(lines) + "\n"


def render_debug_diagnosis_boundary_report(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Debug Diagnosis Required",
        "",
        f"**Goal:** {display_prose(report.get('goal', ''))}",
        "",
        "## Why the plan was not created",
        "",
        f"- Active host: `{report.get('host')}`.",
        "- Debug Start requires bounded host-assisted diagnosis before it can create a useful Planning Lock.",
        f"- Contract: `{report.get('schema')}`.",
        "",
        "## Diagnose first",
        "",
    ]
    lines.extend(f"- {display_prose(item)}" for item in report.get("required_checks", []))
    lines.extend([
        "",
        "## Next action",
        "",
        "- Run the deterministic Debug Preflight first; do not independently scan the repository.",
        f"- CLI: `{report.get('command_prefix')} debug preflight --root {json.dumps(report.get('root'))} --goal {json.dumps(report.get('goal'))} --host {report.get('host')} --format json`",
        "- Perform exactly one host reasoning pass over that packet and return only the schema's closed typed proposal, public observations, hypotheses, repository roles, complete behavior graph, concrete tests, and requirement wording.",
        "- Preserve every evidence-backed branch and convergence point; do not flatten the graph to one preferred trace.",
        "- The proposal may only select validated evidence, graph-node, finding, and test IDs and route to reproduction preparation or a request for more evidence; it grants no authority.",
        "- Submit the typed contract through MCP `debug_diagnosis` or CLI `--debug-diagnosis` with the same exact goal and root.",
        "- TailTrail will validate current hashes, calculate slice-based context tokens, and create the complete Debug Start Plan.",
        "",
        f"- {report.get('boundary')}",
    ])
    return "\n".join(lines) + "\n"


def presentation_policy(
    report: dict[str, Any],
    *,
    verbose: bool = False,
    compatibility_override: str | None = None,
) -> dict[str, str | bool]:
    """Select one automatic detail level from the lifecycle authority route."""
    if compatibility_override not in {None, "quick", "guided", "expert"}:
        raise ValueError(f"unsupported presentation mode: {compatibility_override}")
    if verbose:
        return {"level": "full", "source": "verbose", "full_harness_detail": True}
    if compatibility_override:
        return {
            "level": compatibility_override,
            "source": "compatibility-override",
            "full_harness_detail": False,
        }
    aidlc = report.get("aidlc_mode", {}) if isinstance(report.get("aidlc_mode"), dict) else {}
    mode = str(aidlc.get("mode", "lite"))
    delivery = report.get("guided_delivery", {}) if isinstance(report.get("guided_delivery"), dict) else {}
    if mode in {"standard", "full"} or delivery.get("hands_free_program") or report.get("spec_kit_source"):
        return {"level": "full", "source": "authority-route", "full_harness_detail": True}
    if mode == "off":
        return {"level": "quick", "source": "aidlc-off", "full_harness_detail": False}
    return {"level": "expert", "source": "aidlc-lite", "full_harness_detail": False}


def annotate_presentation(rendered: str, policy: dict[str, str | bool]) -> str:
    """Label automatic detail without changing canonical task authority."""
    lines = rendered.splitlines()
    reason = {
        "verbose": "requested by `--verbose`",
        "authority-route": "automatic for Standard/Full, hands-free, or Intent Bridge authority",
        "aidlc-off": "automatic for AIDLC Off",
        "aidlc-lite": "automatic for AIDLC Lite",
        "compatibility-override": "legacy compatibility override",
    }[str(policy["source"])]
    marker = f"**Plan detail:** `{str(policy['level']).title()}` ({reason})"
    insert_at = 2 if len(lines) > 1 and not lines[1] else 1
    lines[insert_at:insert_at] = [marker, ""]
    return "\n".join(lines) + ("\n" if rendered.endswith("\n") else "")


def verbose_start_report(
    report: dict[str, Any],
    *,
    include_architecture_behaviour: bool = True,
    include_scope_audit: bool = True,
    include_token_details: bool = True,
) -> str:
    """Render a detailed but bounded Start report that chat hosts can reproduce."""
    plan = report["navigator"]
    delivery = report["guided_delivery"]
    lock = report.get("planning_lock")
    root = Path(str(report["root"]))
    impacted = [item for item in plan.get("likely_impacted_files", []) if isinstance(item, dict)]
    selected = [item for item in delivery.get("selected", []) if isinstance(item, dict)]
    requirement_rows = [item for item in plan.get("requirement_matrix", []) if isinstance(item, dict)]
    goal = display_prose(report["goal"])
    lowered_goal = goal.lower()
    code_intel = report["code_intelligence"]
    token = report["token_posture"]
    review = report["review_posture"]
    lines = ["# TailTrail Start Report", "", "Navigator-first plan. Review or edit this before implementation.", ""]
    lines.extend(["## Planning Lock", ""])
    if lock:
        lines.extend(
            [
                f"- Run ID: `{lock['run_id']}`",
                f"- Target identity: `{lock.get('target_identity', {}).get('fingerprint', 'legacy lock')}`.",
                f"- State: **{lock['status']}**; managed writes allowed: **{str(lock['writes_allowed']).lower()}**.",
                "- No source files, tests, scanners, or Git changes were run.",
            ]
        )
        if isinstance(lock.get("scope_decision"), dict):
            lines.append(f"- Scope decision: `{lock['scope_decision'].get('decision_fingerprint')}` (v2, evidence-bound).")
        host = lock.get("host_workspace")
        if isinstance(host, dict) and host.get("host"):
            lines.append(f"- Host workspace: `{host.get('host')}` / `{host.get('status')}` ({host.get('mapping', 'not-mapped')}).")
        policy = lock.get("enterprise_policy")
        if isinstance(policy, dict):
            lines.append(f"- Enterprise target policy: `{policy.get('status', 'not-configured')}`.")
    else:
        lines.append("- No persisted Planning Lock is attached to this rendered report.")
    workflow_runtime = report.get("workflow_runtime", {})
    if isinstance(workflow_runtime, dict) and workflow_runtime.get("enabled"):
        lines.extend(["", "## Workflow runtime", "", f"- Draft workflow ID: `{workflow_runtime.get('workflow_id')}`.", "- Boundary: this remains a report-only draft until the exact Planning Lock is approved; no workflow artifact or stage execution has occurred."])
    lines.extend([
        "", "## Start Here", "",
        "- Review the requirements, editable scope, behavior contract, and proof before approval.",
        "- Nothing in this report implements the task.",
        "", "## Goal", "", f"- {goal}",
        "", "## Requirements", "",
    ])
    append_requirement_interpretation(lines, plan)
    for item in requirement_rows:
        lines.append(requirement_line(item))
    if not requirement_rows:
        lines.append("- Implement the approved goal with the smallest maintainable change.")
    lines.extend(["", "## Scope", ""])
    target = report.get("target_root")
    if isinstance(target, dict) and target.get("requested"):
        lines.append(f"- Target repository: `{target['requested']}` ({target.get('status', 'verified')}).")
    # Verbose is the escape hatch for compact Start output. Never repeat a
    # compact-mode truncation hint here: show every discovered file instead.
    v2_rendered = append_v2_scope_projection(
        lines,
        plan,
        verbose=include_scope_audit,
        responsive=True,
    )
    if not v2_rendered and impacted:
        lines.append("")
        append_stacked_records(lines, [
            (f"`{item.get('path')}`", [("Planning evidence", display_prose(item.get("reason")))])
            for item in impacted
        ])
    if not v2_rendered and not impacted:
        lines.append("")
        if report.get("ui_plan", {}).get("selected"):
            append_stacked_records(lines, [("UI surface not discovered", [("Planning evidence", "Confirm the frontend/UI root or approve bounded read-only UI discovery. Backend files were not substituted as UI scope.")])])
        else:
            append_stacked_records(lines, [("Scope unresolved", [("Planning evidence", "Add `--changed path/to/file` or approve read-only discovery. Unrelated Git changes were not used.")])])
    roles = report.get("input_roles", {})
    if isinstance(roles, dict):
        lines.extend(["", "## Input roles", ""])
        role_records = []
        for item in roles.get("inputs", []):
            if isinstance(item, dict):
                role_records.append((
                    f"`{item.get('locator')}`",
                    [
                        ("Role", display_prose(item.get("role"))),
                        ("Access", display_prose(item.get("access"))),
                        ("Status", display_prose(item.get("status"))),
                    ],
                ))
        append_stacked_records(lines, role_records)
    lines.extend(ui_planning.contract_lines(report.get("ui_plan", {}), responsive=True))
    lines.extend(["", "## Plan", ""])
    for index, stage in enumerate(delivery["stages"], start=1):
        lines.append(f"{index}. {stage}")
    append_testing_plan(lines, report.get("testing_plan", {}))
    lines.extend(["", "## Validation", "", "### Focused validation", ""])
    validation_rows = report.get("focused_validation") or focused_validation_plan(
        root,
        impacted,
        requirement_rows,
        str(report["command_prefix"]),
    )
    validation_records = []
    for item in validation_rows:
        detail = f"`{item['command']}`" if item["command"] else item["status"]
        validation_records.append((
            display_prose(item["tier"]),
            [
                ("Candidate", f"`{item['candidate']}` ({item.get('candidate_state', 'unknown')})"),
                ("Status / command", detail),
            ],
        ))
    append_stacked_records(lines, validation_records)
    lines.append("- Tests and validation run only after approval.")
    lines.extend([
        "", "## Navigator Decision", "",
        "- Workflow: " + " -> ".join(plan.get("recommended_workflow", [])),
        "- Task types: " + ", ".join(plan.get("task_types", [])),
        "- Risks: " + (", ".join(plan.get("risk_indicators", [])) if plan.get("risk_indicators") else "none detected"),
        f"- Post-change review: {'selected' if review['selected'] else 'available'} for `{review['scope']}`.",
    ])
    hands_free_program = delivery.get("hands_free_program")
    spec_kit_source = report.get("spec_kit_source")
    if isinstance(spec_kit_source, dict):
        lines.extend(["", "## Requirement authority", "", f"- Source: `{spec_kit_source['feature_id']}` / `{spec_kit_source['source_revision']}` (imported snapshot v{spec_kit_source['snapshot_version']})."])
    aidlc = report.get("aidlc_requirements")
    if isinstance(aidlc, dict):
        stage = aidlc.get("aidlc_stage", {})
        if aidlc.get("state") == "official-aidlc-host-generation-required":
            lines.extend(["", "## Official AIDLC requirements", "", "- The verified official Requirements Analysis stage is ready for the configured host.", "- The host must load the recorded official rules and saved Question Orchestrator context, then generate material questions with requirement traceability, options, TailTrail advisory recommendations, and evidence-grounded reasoning before implementation can be approved.", "- TailTrail validates grounding and persists that official stage artifact under this same run ID; it will not fabricate a local substitute questionnaire.", "", f"- Stage gate: {stage.get('stage_gate', '')}"])
        elif aidlc.get("state") == "authority-bound-in-start-plan":
            lines.extend([
                "",
                "## Official AIDLC requirement authority",
                "",
                "- Status: `authority-bound-before-scope`.",
                f"- Mode: `{aidlc.get('mode')}`; stage: `{aidlc.get('stage')}`.",
                f"- {aidlc.get('boundary')}",
                f"- Approval gate: {aidlc.get('approval_gate')}",
            ])
        else:
            lines.extend(["", "## AIDLC requirements and recommendations", "", "### Assumptions", ""])
            lines.extend(f"- {item}" for item in stage.get("assumptions", []))
            lines.extend(["", "### Non-goals", ""])
            lines.extend(f"- {item}" for item in stage.get("non_goals", []))
            lines.extend(["", "### Questions", ""])
            for question in aidlc.get("questions", []):
                lines.extend([f"#### {question.get('id', 'Question')} - {display_prose(question.get('question', ''))}", f"- **Recommended:** {display_prose(question.get('recommended', ''))}", f"- **Reasoning:** {display_prose(question.get('reasoning', ''))}", ""])
            lines.extend(["", f"- Stage gate: {stage.get('stage_gate', '')}"])
    aidlc_mode = report.get("aidlc_mode", {})
    if isinstance(aidlc_mode, dict):
        lines.extend(["", "## AIDLC mode", "", f"- Selected mode: `{aidlc_mode.get('mode')}`", f"- Selection: `{aidlc_mode.get('selection')}`", f"- State: `{aidlc_mode.get('state')}`", f"- Boundary: {aidlc_mode.get('boundary')}"])
        requested_mode = aidlc_mode.get("requested_mode")
        if requested_mode and requested_mode != aidlc_mode.get("mode"):
            lines.append(f"- Requested mode: `{requested_mode}` (fell back to `{aidlc_mode.get('mode')}`)")
        escalation = aidlc_mode.get("full_escalation", {})
        if isinstance(escalation, dict): lines.append(f"- Full escalation: `{escalation.get('state')}` - {display_prose(escalation.get('reason'))}")
    mode_features = report.get("aidlc_mode_features", {})
    if isinstance(mode_features, dict):
        lines.extend(["", "## AIDLC mode features", "", "### Included", ""])
        included = mode_features.get("included", []); excluded = mode_features.get("not_included", [])
        lines.extend(f"- {display_prose(item)}" for item in included)
        if not included:
            lines.append("- None.")
        lines.extend(["", "### Not included in this mode", ""])
        lines.extend(f"- {display_prose(item)}" for item in excluded)
        if not excluded:
            lines.append("- None.")
    lines.extend(["", "## Selected TailTrail features", ""])
    feature_records = [("Navigator", [("When", "Planning now"), ("Why", "created this scoped Planning Lock and approval gate")])]
    graph_why = code_review_graph_lite_why(impacted)
    if graph_why:
        feature_records.append(("Code Review Graph Lite", [("When", "Planning now"), ("Why", graph_why)]))
    for item in selected:
        when = feature_when(str(item.get("name", "")), item.get("when"))
        feature_records.append((display_prose(item.get("name")), [("When", when), ("Why", display_prose(item.get("why")))]))
    append_stacked_records(lines, feature_records)
    if include_architecture_behaviour:
        architecture_lines = architecture_planning.markdown_lines(report.get("architecture_plan", {}), detailed=True, responsive=True)
        behaviour_lines = behaviour_planning.markdown_lines(report.get("behaviour_plan", {}), detailed=True, responsive=True)
        lines.extend(architecture_lines or [
            "", "## Architecture Fitness Plan", "",
            "- State: `not-selected`.",
            "- Reason: the approved planning evidence does not currently require a dedicated architecture assessment; its conditional activation rule remains visible below.",
        ])
        lines.extend(behaviour_lines or [
            "", "## Behaviour Harness Plan", "",
            "- State: `not-selected`.",
            "- Reason: the approved planning evidence does not currently name a user-facing, API, or journey contract; its conditional activation rule remains visible below.",
        ])
    lines.extend(maintainability_planning.markdown_lines(report.get("maintainability_plan", {}), detailed=True, responsive=True))
    lines.extend(ui_planning.audit_lines(report.get("ui_plan", {}), responsive=True))
    append_later_lifecycle_sections(lines, delivery, compact=True)
    lines.extend(["", "## Guided Delivery", "", f"- Mode: `{delivery['mode']}`", "- After approval:"])
    for index, stage in enumerate(delivery["stages"], start=1):
        lines.append(f"  {index}. {stage}")
    if hands_free_program:
        lines.append("- Program dependency order: " + " -> ".join(hands_free_program["dependency_order"]))
        lines.append(f"- First active slice: {hands_free_program['first_active_slice']}")
        lines.append(f"- Program approval gate: {hands_free_program['approval_gate']}")
    if report.get("ui_consistency", {}).get("selected"):
        lines.extend(["- UI discovery before implementation: `" + str(report["ui_consistency"]["command"]) + "`", "- UI preservation boundary: " + str(report["ui_consistency"]["boundary"])])
    lines.extend([f"- Boundary: {delivery['execution_boundary']}"])
    lines.extend(pipeline_badge_lines(lock if isinstance(lock, dict) else None))
    lines.extend(["", "## Token estimate", ""])
    lines.extend(token_estimate_lines(token, detailed=include_token_details))
    lines.extend(["", "## Evidence posture", "", "- Code intelligence: local-only `lite`, `v1`, and `v2`; provider-backed V3 is not default.", "- Evidence: local upper bound only; no exact token-savings claim.", "", "## Approval", ""])
    if isinstance(aidlc, dict) and aidlc.get("state") == "official-aidlc-host-generation-required":
        lines.append("- The official Requirements Analysis questions must be generated, answered, and explicitly approved before TailTrail can freeze the anchor or begin implementation.")
    else:
        lines.append("- Approve this plan to begin implementation, or name any file/scope change before approval.")
    if report.get("ui_plan", {}).get("surface_status") == "not-discovered":
        lines.append("- UI scope must be confirmed before implementation approval; TailTrail will not treat backend candidates as the missing UI surface.")
    return "\n".join(lines) + "\n"


def render_markdown(report: dict[str, Any], verbose: bool = False, presentation_mode: str | None = None) -> str:
    policy = presentation_policy(report, verbose=verbose, compatibility_override=presentation_mode)
    level = str(policy["level"])
    if report.get("requirement_artifact_boundary"):
        return annotate_presentation(render_requirement_artifact_boundary_report(report), policy)
    if report.get("host_requirement_interpretation_boundary"):
        return annotate_presentation(render_host_requirement_interpretation_boundary_report(report), policy)
    if report.get("debug_diagnosis_boundary"):
        return annotate_presentation(render_debug_diagnosis_boundary_report(report), policy)
    if report.get("scope_investigation_boundary"):
        return annotate_presentation(render_scope_investigation_boundary_report(report), policy)
    if report.get("target_boundary"):
        return annotate_presentation(render_target_boundary_report(report), policy)
    if report.get("target_fit_boundary"):
        return annotate_presentation(render_target_fit_boundary_report(report), policy)
    if report.get("scope_quality_boundary"):
        return annotate_presentation(
            render_scope_quality_boundary_report(
                report,
                verbose=bool(policy.get("source") == "verbose"),
            ),
            policy,
        )
    if report.get("debug_plan"):
        rendered = (
            compact_debug_start_report(report)
            if level == "quick"
            else debug_start_report(report, verbose=level in {"expert", "full"})
        )
        return annotate_presentation(rendered, policy)
    plan = report["navigator"]
    lock = report.get("planning_lock")
    lock_lines = []
    if lock:
        lock_lines = [
            "## Planning Lock",
            "",
            f"- Run ID: `{lock['run_id']}`",
            f"- State: **{lock['status']}**; managed writes allowed: **{str(lock['writes_allowed']).lower()}**.",
            f"- Saved plan: `{report.get('planning_report', {}).get('artifact', 'saved with this run')}`.",
            "- Source edits, Git mutations, Terraform/Sonar execution, scanners, and managed patch application are blocked until a separate approval.",
            f"- Approve and activate this exact plan later: `{report['command_prefix']} planning activate --root . --run-id {lock['run_id']} --approved`",
            "",
        ]
    if plan.get("navigator_request", {}).get("explicit"):
        # An explicit Navigator invocation already has a concise decision and
        # separate approval gate. Do not bury it in the broader Start report.
        return annotate_presentation("\n".join(lock_lines) + navigator.markdown(plan), policy)
    if level == "full":
        return annotate_presentation(
            verbose_start_report(
                report,
                include_scope_audit=policy.get("source") == "verbose",
            ),
            policy,
        )
    if level == "expert":
        return annotate_presentation(
            verbose_start_report(
                report,
                include_architecture_behaviour=False,
                include_scope_audit=False,
                include_token_details=False,
            ),
            policy,
        )
    token = report["token_posture"]
    learning = report["learning_quality"]
    setup = report["setup_posture"]
    review = report["review_posture"]
    harness = report["harness_posture"]
    bootstrap = report["bootstrap_posture"]
    evaluation = report["evaluation_posture"]
    code_intel = report["code_intelligence"]
    delivery = report["guided_delivery"]
    hands_free_program = delivery.get("hands_free_program")
    run_signals = delivery["run_signals"]
    selected = plan.get("selected_features", [])
    skipped = plan.get("skipped_features", [])
    actions = report.get("next_actions", [])
    if level == "quick":
        return annotate_presentation(quick_start_report(report), policy)
    if level == "guided":
        return annotate_presentation(compact_start_report(report), policy)
    lines = [
        "# TailTrail Start Report",
        "",
        "Navigator-first plan. Review or edit this before implementation.",
        "",
        *lock_lines,
        "## Start Here",
        "",
        f"- Next step: {report['next_step']}",
        "- Nothing has been implemented, scanned, captured, learned, or changed by this report.",
        f"- Post-change review: {'selected' if review['selected'] else 'available'} for `{review['scope']}`.",
        f"- Bootstrap Snapshot: `{bootstrap['status']}`.",
        "- Meta-Harness: available after work to review TailTrail behavior and metric confidence.",
        f"- Evaluation Harness: {'selected' if evaluation['selected'] else 'available'} for deterministic proof scenarios.",
        "- The guided delivery sequence below is the default path after approval; advanced harnesses activate only when their trigger occurs.",
        "",
        "## Guided Delivery",
        "",
        f"- Mode: `{delivery['mode']}`",
        "- After approval: " + " -> ".join(delivery["stages"]),
        "- Selected controls: " + ", ".join(item["name"] for item in delivery["selected"]),
        f"- Run evidence: `{run_signals['status']}`" + (f" for `{run_signals['run_id']}`" if run_signals["run_id"] else "; no prior-run state was inferred."),
        f"- Boundary: {delivery['execution_boundary']}",
        "- Approval: `" + delivery["approval_prompt"] + "`",
        "",
        "## Goal",
        "",
        f"- {display_prose(report['goal'])}",
        "",
        "## Navigator Decision",
        "",
        "- Workflow: " + " -> ".join(plan.get("recommended_workflow", [])),
        "- Task types: " + ", ".join(plan.get("task_types", [])),
        "- Risks: " + (", ".join(plan.get("risk_indicators", [])) if plan.get("risk_indicators") else "none detected"),
        f"- Likely impacted files: `{len(plan.get('likely_impacted_files', []))}`",
        "",
        "## Selected TailTrail features",
        "",
        "| Feature | When | Why |",
        "| --- | --- | --- |",
        "| Navigator | Planning now | created this scoped Planning Lock and approval gate |",
        *[
            f"| {item['name']} | {feature_when(str(item.get('name', '')), item.get('when'))} | {item['why']} |"
            for item in delivery["selected"]
        ],
        "",
        "## Required later in this run",
        "",
        "These controls are mandatory before completion; their later lifecycle position does not make them optional.",
        "",
        "| Required control | Runs when | Why it cannot be skipped |",
        "| --- | --- | --- |",
        *[f"| {item['name']} | {item['when']} | {item.get('why', 'required before completion')} |" for item in required_later_rows(delivery)],
        "",
        "## Conditional TailTrail controls",
        "",
        "| Control | Activates when |",
        "| --- | --- |",
        *[f"| {item['name']} | {item['when']} |" for item in conditional_control_rows(delivery)],
        "",
        "## Recommended Path",
        "",
        "- Workflow: " + " -> ".join(plan.get("recommended_workflow", [])),
        "- Task types: " + ", ".join(plan.get("task_types", [])),
        "- Risks: " + (", ".join(plan.get("risk_indicators", [])) if plan.get("risk_indicators") else "none detected"),
        f"- Impacted files: `{len(plan.get('likely_impacted_files', []))}`",
        f"- Selected features: `{', '.join(item['name'] for item in selected[:5]) if selected else 'none'}`",
    ]

    spec_kit_source = report.get("spec_kit_source")
    if isinstance(spec_kit_source, dict):
        lines.extend(["", "## Intent Bridge requirement source", "", f"- Feature: `{spec_kit_source['feature_id']}`", f"- Source revision: `{spec_kit_source['source_revision']}`", f"- Imported snapshot: `{spec_kit_source['import']}`", f"- Imported requirements: `{len(spec_kit_source['requirements'])}`; stories: `{len(spec_kit_source['stories'])}`; tasks: `{len(spec_kit_source['tasks'])}`.", f"- Boundary: {spec_kit_source['boundary']}"])

    if hands_free_program:
        lines.extend(
            [
                "",
                "## Hands-Free Program Plan",
                "",
                "- Status: `proposed`; no implementation slice is active yet.",
                "- Feature requirements: " + "; ".join(f"{item['display_id']} {item['statement']}" for item in hands_free_program["feature_requirements"]),
                "- Proposed dependency order: " + " -> ".join(hands_free_program["dependency_order"]),
                f"- First active slice: {hands_free_program['first_active_slice']}",
                f"- Approval gate: {hands_free_program['approval_gate']}",
            ]
        )

    if len(selected) > 5:
        lines.append(f"- More selected features: `{len(selected) - 5}` hidden in compact view; use `--verbose` for full detail.")
    if skipped:
        lines.append(f"- Skipped features: `{len(skipped)}` hidden in compact view.")
    required_later = required_later_rows(delivery)
    if required_later:
        lines.append("- Required later: " + "; ".join(f"{item['name']} ({item['when']})" for item in required_later[:3]))
    conditional = conditional_control_rows(delivery)
    if conditional:
        lines.append("- Conditional controls: " + "; ".join(f"{item['name']} ({item['when']})" for item in conditional[:3]))
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
    lines.extend(["", "## Validation", "", "### Focused validation", ""])
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
            "## Evidence posture",
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
        f"- {display_prose(report['goal'])}",
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
    lines.extend(["", "## Guided Delivery Details", ""])
    lines.extend(f"- {item['name']}: {item['why']}" for item in delivery["selected"])
    lines.extend(f"- Required later - {item['name']}: {display_prose(item['when'])}" for item in required_later_rows(delivery))
    lines.extend(f"- Conditional - {item['name']}: {display_prose(item['when'])}" for item in conditional_control_rows(delivery))
    if run_signals.get("evidence"):
        lines.append("- Run evidence pointers: " + ", ".join(f"`{item}`" for item in run_signals["evidence"]))
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


def _parse_json_flag(flag: str, raw: str | None, raw_base64: str | None) -> dict[str, Any] | None:
    """Parse a --flag/--flag-base64 JSON pair, raising a friendly ValueError instead of a raw JSON/base64 error."""
    if raw is not None:
        source = raw
    elif raw_base64 is not None:
        try:
            source = base64.b64decode(raw_base64, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as error:
            raise ValueError(f"{flag}-base64 could not be decoded as UTF-8 base64: {error}") from error
    else:
        return None
    try:
        return json.loads(source)
    except json.JSONDecodeError as error:
        raise ValueError(f"{flag} must be valid JSON: {error}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description="Start a TailTrail task with Navigator-first plan, metrics, setup posture, and learning quality.")
    parser.add_argument("goal", nargs="*", help="User goal or task description.")
    parser.add_argument("--root", type=Path, default=None, help="Project root to inspect. Overrides a target repository explicitly named in the goal.")
    parser.add_argument("--host", choices=("codex", "copilot", "claude"), help="Optional host supplying the active workspace identity.")
    parser.add_argument("--host-workspace", help="Workspace path reported by the selected host. It overrides a prompt path but never an explicit --root.")
    parser.add_argument("--host-platform", choices=("auto", "windows", "macos", "linux", "wsl", "container"), default="auto", help="Platform shape of --host-workspace for safe local mapping.")
    parser.add_argument("--enterprise-policy", type=Path, help="Optional local enterprise target policy JSON. Enforced before repository discovery.")
    parser.add_argument("--target-alias", help="Optional target alias from the supplied enterprise target policy.")
    parser.add_argument("--actor", help="Optional declared actor label for a policy that requires target ownership. This is not authentication.")
    parser.add_argument("--changed", action="append", default=[], help="Changed or target file path. Repeat for multiple files.")
    parser.add_argument(
        "--graph", choices=("auto", "reuse", "refresh", "rebuild", "off"), default="auto",
        help="Navigator graph lifecycle override. Default auto reuses, creates, or refreshes metadata as needed.",
    )
    workflow_group = parser.add_mutually_exclusive_group()
    workflow_group.add_argument("--debug", action="store_true", help="Force Navigator to classify this Start run as a debug investigation.")
    workflow_group.add_argument("--build", action="store_true", help="Force Navigator to classify this Start run as a normal build workflow.")
    parser.add_argument("--error", help="Declare that a failure artifact is available. The path/content is not copied into the DI-2 plan.")
    parser.add_argument("--command", dest="reproduction_command", help="Declare that a reproduction command is available. Its content is not copied into the DI-2 plan.")
    parser.add_argument("--run-id", help="Optional exact TailTrail run ID. Enables evidence-driven correction and recovery routing for that run only.")
    parser.add_argument("--planning-run-id", help="Optional new Planning Lock run ID. Defaults to a generated run ID.")
    parser.add_argument("--reference-root", action="append", default=[], help="Read-only reference repository path for this plan. Repeat for multiple references.")
    parser.add_argument("--related-repo", action="append", default=[], help="Read-only sibling/related repository path. Repeat as needed.")
    parser.add_argument("--design-reference", action="append", default=[], help="Read-only local or external design reference. Repeat as needed.")
    parser.add_argument("--requirement-artifact", action="append", default=[], help="Read-only local requirement/specification artifact. Repeat as needed.")
    requirement_interpretation_group = parser.add_mutually_exclusive_group()
    requirement_interpretation_group.add_argument(
        "--requirement-interpretation",
        help="Typed host requirement interpretation JSON bound to the exact goal.",
    )
    requirement_interpretation_group.add_argument(
        "--requirement-interpretation-base64",
        help="Base64 UTF-8 typed host requirement interpretation JSON for native-shell safety.",
    )
    requirement_interpretation_group.add_argument(
        "--requirement-intake-id",
        help="Resume one fully answered, exact goal/root/host-bound pre-lock requirement intake.",
    )
    debug_diagnosis_group = parser.add_mutually_exclusive_group()
    debug_diagnosis_group.add_argument(
        "--debug-diagnosis",
        help="Typed, hash-bound host-assisted Debug Start diagnosis JSON.",
    )
    debug_diagnosis_group.add_argument(
        "--debug-diagnosis-base64",
        help="Base64 UTF-8 host-assisted Debug Start diagnosis JSON for native-shell safety.",
    )
    debug_diagnosis_group.add_argument(
        "--debug-diagnosis-stdin",
        action="store_true",
        help="Read the UTF-8 host-assisted Debug Start diagnosis JSON from standard input.",
    )
    host_scope_group = parser.add_mutually_exclusive_group()
    host_scope_group.add_argument(
        "--host-scope-proposal",
        help="Typed active-host scope proposal JSON bound to the current Navigator evidence packet.",
    )
    host_scope_group.add_argument(
        "--host-scope-proposal-base64",
        help="Base64 UTF-8 active-host scope proposal JSON for native-shell safety.",
    )
    parser.add_argument("--evidence-artifact", action="append", default=[], help="Read-only local CI, scan, or validation artifact. Repeat as needed.")
    parser.add_argument("--aidlc", choices=("lite", "standard", "medium", "full", "off"), default=None, help="Optional AIDLC override. Without it: normal Start uses Lite, 'using AIDLC' uses Standard, hands-free uses Standard with eligible Full escalation, and full/official wording requires Full.")
    parser.add_argument("--official-aidlc-manifest", help="Optional in-root official AIDLC compatibility manifest used only with --aidlc full.")
    parser.add_argument("--official-intent-id", help="Optional official AIDLC intent identity to map to this TailTrail run in full mode.")
    parser.add_argument("--official-session-id", help="Optional official AIDLC host session identity to map to this TailTrail run in full mode.")
    parser.add_argument("--official-stage", choices=("requirements", "design", "implementation", "build-and-test", "handoff", "operations"), default="requirements", help="Initial official AIDLC stage identity for full mode.")
    parser.add_argument("--intent-feature", "--spec-kit-feature", dest="spec_kit_feature", help="Explicitly use one already-imported Intent Bridge feature as the authoritative requirement source for this Planning Lock.")
    parser.add_argument("--no-planning-lock", action="store_true", help="Advanced compatibility escape hatch; does not create the local planning artifact.")
    parser.add_argument("--no-workflow", action="store_true", help="Compatibility escape hatch; keep this Start run outside the DWR workflow runtime.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument(
        "--presentation", "--presentation-mode",
        choices=("quick", "guided", "expert"),
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--command-prefix", default="python3 scripts/tailtrail.py", help="Command prefix to show in suggested commands.")
    parser.add_argument("--verbose", action="store_true", help="Include full decision menu, posture details, and Navigator output.")
    args = parser.parse_args()

    goal = " ".join(args.goal).strip()
    if not goal:
        parser.error("goal is required")
    try:
        loaded_policy = enterprise_target_policy.load(args.enterprise_policy)
        policy_aliases = enterprise_target_policy.aliases(loaded_policy)
        if args.host_workspace and not args.host:
            parser.error("--host-workspace requires --host codex, copilot, or claude")
        host_resolution = host_workspace_adapter.resolve(args.host or "codex", args.host_workspace, host_platform=args.host_platform) if args.host else None
        if args.root is None and isinstance(host_resolution, dict) and host_resolution.get("status") not in {"verified", "not-provided"}:
            report = target_boundary_report(goal, host_resolution, args.command_prefix)
            if args.format == "json":
                print(json.dumps(report, indent=2, sort_keys=True, default=str))
            else:
                print(render_markdown(report, verbose=args.verbose, presentation_mode=args.presentation), end="")
            return 2
        host_root = Path(str(host_resolution["root"])) if isinstance(host_resolution, dict) and host_resolution.get("status") == "verified" else None
        target = resolve_target_root(goal, args.root, host_root, args.target_alias, policy_aliases)
        if target["status"] != "verified":
            report = target_boundary_report(goal, target, args.command_prefix)
            if args.format == "json":
                print(json.dumps(report, indent=2, sort_keys=True, default=str))
            else:
                print(render_markdown(report, verbose=args.verbose, presentation_mode=args.presentation), end="")
            return 2
        root = target["root"]
        applied_alias = args.target_alias if target.get("source") == "alias" else None
        policy_result = enterprise_target_policy.evaluate(root, loaded_policy, actor=args.actor, selected_alias=applied_alias)
        if policy_result["blocking"]:
            report = target_boundary_report(goal, {"requested": root.as_posix(), "status": "blocked", "source": "enterprise-policy", "reason": "; ".join(policy_result["issues"])}, args.command_prefix)
            if args.format == "json":
                print(json.dumps(report, indent=2, sort_keys=True, default=str))
            else:
                print(render_markdown(report, verbose=args.verbose, presentation_mode=args.presentation), end="")
            return 2
        declared_input_roles = target_workspace.input_roles(
            root,
            reference_roots=args.reference_root,
            related_repos=args.related_repo,
            design_references=args.design_reference,
            requirement_artifacts=args.requirement_artifact,
            evidence_artifacts=args.evidence_artifact,
        )
        artifact_preparation = target_workspace.inspect_requirement_artifacts(
            declared_input_roles
        )
        input_roles_registry = artifact_preparation["registry"]
        requirement_artifact_inputs = artifact_preparation["planning_inputs"]
        if not artifact_preparation["ready"]:
            report = requirement_artifact_boundary_report(
                goal, root, artifact_preparation
            )
            if args.format == "json":
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                print(
                    render_markdown(
                        report,
                        verbose=args.verbose,
                        presentation_mode=args.presentation,
                    ),
                    end="",
                )
            return 2
        requested_spec_kit_feature = args.spec_kit_feature or spec_kit_bridge.feature_from_goal(goal)
        intent_requested = "intent bridge" in goal.lower() or "spec kit" in goal.lower()
        if intent_requested and not requested_spec_kit_feature:
            parser.error("Select an imported Intent Bridge feature with --intent-feature <feature>; TailTrail will not guess or auto-import a requirement source.")
        intent_bridge_source = (
            spec_kit_bridge.load(root, requested_spec_kit_feature)
            if requested_spec_kit_feature
            else None
        )
        workflow_override = "debug" if args.debug else "build" if args.build else None
        workflow_preview = navigator.core.classify_workflow_intent(
            goal,
            override=workflow_override,
            has_error_artifact=bool(args.error),
            has_reproduction_command=bool(args.reproduction_command),
        )
        saved_requirement_intake: dict[str, Any] | None = None
        effective_official_manifest = args.official_aidlc_manifest
        resumed_aidlc_mode: str | None = None
        if args.requirement_intake_id:
            if workflow_preview.workflow_type != "build" or intent_requested:
                parser.error("a requirement intake can resume only an ordinary Build Start")
            saved_requirement_intake = requirement_intake.load(
                root, args.requirement_intake_id
            )
            intake_identity = saved_requirement_intake.get("identity", {})
            expected_host = args.host or "none"
            saved_host = intake_identity.get("host", "none")
            # A saved intake created without --host may later resume with a
            # concrete --host (needed for a host scope proposal); it never
            # switches between two different already-recorded hosts.
            host_mismatch = saved_host != "none" and saved_host != expected_host
            if (
                intake_identity.get("root") != root.resolve().as_posix()
                or intake_identity.get("goal") != goal
                or host_mismatch
            ):
                parser.error(
                    "requirement intake does not match the exact current goal, root, and host"
                )
            resumed_aidlc_mode = {
                "lite-questions": "lite",
                "aidlc-standard": "standard",
                "aidlc-full": "full",
            }.get(str(intake_identity.get("route")))
            if resumed_aidlc_mode is None:
                parser.error("requirement intake has an unsupported continuation route")
            requested_mode = "standard" if args.aidlc == "medium" else args.aidlc
            if requested_mode is not None and requested_mode != resumed_aidlc_mode:
                parser.error(
                    "requirement intake must resume its saved AIDLC route without downgrade or escalation"
                )
            if effective_official_manifest is None:
                compatibility = (
                    saved_requirement_intake.get("route_posture", {}) or {}
                ).get("compatibility", {})
                saved_manifest = compatibility.get("manifest")
                if isinstance(saved_manifest, str) and saved_manifest:
                    effective_official_manifest = saved_manifest
        pre_scope_mode = aidlc_mode_selection(
            goal,
            resumed_aidlc_mode or args.aidlc,
            root,
            {"risk_indicators": [], "requirement_sufficiency": {}},
            effective_official_manifest,
        )
        # Agent hosts can consume the verified official rules and therefore
        # must establish AIDLC requirement authority before scope. A raw CLI
        # client has no reasoning host, so it retains the existing post-lock
        # official stage rather than pretending deterministic wording is
        # official.
        required_official_authority = (
            official_requirement_authority(root, pre_scope_mode)
            if args.host
            else None
        )
        host_requirement_proposal = _parse_json_flag(
            "--requirement-interpretation", args.requirement_interpretation, args.requirement_interpretation_base64
        )
        if host_requirement_proposal and (
            workflow_preview.workflow_type == "debug-investigation"
            or (
                args.aidlc in {"standard", "medium", "full"}
                and required_official_authority is None
                and not requirement_artifact_inputs
            )
            or intent_requested
        ):
            parser.error("host requirement interpretation is only accepted for ordinary Lite/Off Build Start")
        explicit_aidlc_intent = _aidlc_intent(goal.casefold())
        hands_free = any(
            phrase in goal.casefold()
            for phrase in ("hands-free", "hands free", "end-to-end", "end to end")
        )
        ordinary_agent_build = (
            workflow_preview.workflow_type == "build"
            and bool(args.host)
            and not intent_requested
            and args.aidlc not in {"standard", "medium", "full"}
            and explicit_aidlc_intent not in {"requested", "standard", "full"}
            and not hands_free
        )
        artifact_interpretation_required = (
            workflow_preview.workflow_type == "build"
            and bool(requirement_artifact_inputs)
            and host_requirement_proposal is None
            and saved_requirement_intake is None
            and not intent_requested
        )
        official_interpretation_required = (
            workflow_preview.workflow_type == "build"
            and required_official_authority is not None
            and host_requirement_proposal is None
            and saved_requirement_intake is None
            and not intent_requested
        )
        if (
            (
                ordinary_agent_build
                or artifact_interpretation_required
                or official_interpretation_required
            )
            and host_requirement_proposal is None
            and saved_requirement_intake is None
        ):
            report = host_requirement_interpretation_boundary_report(
                goal,
                root,
                str(args.host or "unconfigured"),
                args.command_prefix,
                requirement_artifact_inputs,
                required_official_authority,
            )
            if args.format == "json":
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                print(render_markdown(report, verbose=args.verbose, presentation_mode=args.presentation), end="")
            return 2
        raw_debug_diagnosis = _parse_json_flag(
            "--debug-diagnosis", args.debug_diagnosis, args.debug_diagnosis_base64
        )
        if raw_debug_diagnosis is None and args.debug_diagnosis_stdin:
            try:
                raw_debug_diagnosis = json.load(sys.stdin)
            except json.JSONDecodeError as error:
                raise ValueError(f"--debug-diagnosis-stdin must be valid JSON: {error}") from error
        validated_debug_diagnosis: dict[str, Any] | None = None
        if raw_debug_diagnosis is not None:
            if workflow_preview.workflow_type != "debug-investigation":
                parser.error("host debug diagnosis is accepted only for Debug Start")
            if not args.host:
                parser.error("host debug diagnosis requires --host codex, copilot, or claude")
            validated_debug_diagnosis = debug_host_diagnosis.validate(
                root, goal, raw_debug_diagnosis, args.host
            )
        if workflow_preview.workflow_type == "debug-investigation" and args.host and validated_debug_diagnosis is None:
            report = debug_diagnosis_boundary_report(goal, root, args.host, args.command_prefix)
            if args.format == "json":
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                print(render_markdown(report, verbose=args.verbose, presentation_mode=args.presentation), end="")
            return 2
        host_scope_proposal = _parse_json_flag(
            "--host-scope-proposal", args.host_scope_proposal, args.host_scope_proposal_base64
        )
        if host_scope_proposal is not None:
            if not args.host:
                parser.error("a host scope proposal requires --host codex, copilot, or claude")
            if host_scope_proposal.get("host") != args.host:
                parser.error("host scope proposal host does not match the active --host")
        interpreted_requirements = (
            requirement_intake.resolved_interpretation(saved_requirement_intake)
            if saved_requirement_intake is not None
            else intent_bridge_requirement_interpretation(goal, intent_bridge_source)
            if intent_bridge_source is not None
            else requirement_discovery.interpretation(
                goal,
                host_requirement_proposal,
                args.host or (str(host_requirement_proposal.get("host")) if host_requirement_proposal else None),
                requirement_artifact_inputs,
            )
        )
        if required_official_authority is not None:
            validate_official_requirement_interpretation(
                interpreted_requirements,
                required_official_authority,
            )
        sufficiency = interpreted_requirements.get("sufficiency")
        if isinstance(sufficiency, dict):
            sufficiency = navigator_requirement_route(
                goal, resumed_aidlc_mode or args.aidlc, sufficiency
            )
            interpreted_requirements["sufficiency"] = sufficiency
            interpreted_requirements["state"] = sufficiency["state"]
        requirement_state = interpreted_requirements.get("state")
        if requirement_state in {"clarification-required", "standard-recommended", "full-recommended"}:
            official_route = requirement_state in {"standard-recommended", "full-recommended"}
            full_route = requirement_state == "full-recommended"
            route = (
                sufficiency.get("recommended_route")
                if isinstance(sufficiency, dict)
                else "lite-questions"
            )
            gathered_evidence = requirement_evidence.gather(root, goal, sufficiency or {})
            route_posture = (
                official_aidlc_bridge.preflight(
                    root,
                    "full" if route == "aidlc-full" else "standard",
                    effective_official_manifest,
                )
                if route in {"aidlc-standard", "aidlc-full"}
                else None
            )
            intake = requirement_intake.create(
                root,
                goal,
                interpreted_requirements,
                route=route,
                host=args.host,
                requested_mode=args.aidlc,
                command_prefix=args.command_prefix,
                evidence=gathered_evidence,
                route_posture=route_posture,
            )
            report = {
                "type": (
                    "tailtrail-aidlc-full-routing"
                    if full_route
                    else "tailtrail-aidlc-standard-routing"
                    if official_route
                    else "tailtrail-requirement-clarification"
                ),
                "state": intake["state"],
                "routing_state": requirement_state,
                "intake_id": intake["intake_id"],
                "revision": intake["revision"],
                "goal": goal,
                "root": root.as_posix(),
                "requirements": interpreted_requirements.get("requirements", []),
                "material_questions": interpreted_requirements.get("material_questions", []),
                "requirement_sufficiency": sufficiency,
                "scope_question_precondition": scope_question_precondition(
                    interpreted_requirements
                ),
                "requirement_evidence": intake["requirement_evidence"],
                "recommended_route": route,
                "intake_stage": "navigator-prelock-requirement-intake",
                "post_intake_route": route,
                "route_posture": intake.get("route_posture"),
                "continuation": intake["continuation"],
                "authority": intake["authority"],
                "boundary": intake["boundary"],
            }
            if args.format == "json":
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                print(
                    "# TailTrail Full AIDLC Routing\n"
                    if full_route
                    else "# TailTrail Standard AIDLC Routing\n"
                    if official_route
                    else "# TailTrail Requirement Clarification\n"
                )
                print(report["boundary"] + "\n")
                print(f"- **Intake ID:** `{report['intake_id']}`")
                print(f"- **Route:** `{report['recommended_route']}`")
                print("- **Scope questions:** deferred until requirements are sufficient.")
                if isinstance(report.get("route_posture"), dict):
                    print(
                        f"- **Official pack posture:** "
                        f"`{report['route_posture'].get('state')}`"
                    )
                for index, question in enumerate(report["material_questions"], start=1):
                    print(f"- **Q{index}:** {question}")
                print("")
                print("\n".join(requirement_intake.evidence_lines(report["requirement_evidence"], intake.get("answers"))), end="")
                print(f"- **Continue:** {report['continuation']['prompt']}")
            return 0
        scope_precondition = scope_question_precondition(interpreted_requirements)
        if scope_precondition["scope_question_allowed"] is not True:
            parser.error(
                "internal requirement-routing error: scope investigation cannot begin before requirement sufficiency"
            )
        scope_release = navigator_scope.scope_release_status(root)
        if scope_release["state"] != navigator_scope.SCOPE_AVAILABLE:
            report = scope_investigation_boundary_report(goal, root, scope_release, args.command_prefix)
            report["scope_question_precondition"] = scope_precondition
            if args.format == "json":
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                print(render_markdown(report, verbose=args.verbose, presentation_mode=args.presentation), end="")
            return 2
        graph_mode = args.graph
        if workflow_preview.workflow_type == "debug-investigation":
            if graph_mode in {"refresh", "rebuild"}:
                parser.error("Debug Start cannot refresh or rebuild graph metadata before reproduction approval; use --graph reuse/off or refresh during approved Debug orientation")
            if graph_mode == "auto":
                graph_mode = "reuse"
        graph_attempt_id = args.planning_run_id or planning_lock.suggested_run_id(root, goal)
        graph_lifecycle = navigator_graph_lifecycle.manage(
            root,
            goal,
            args.changed,
            mode=graph_mode,
            attempt_id=graph_attempt_id,
            phase="debug-start" if workflow_preview.workflow_type == "debug-investigation" else "start",
            canonical_literals=[
                str(literal)
                for requirement in interpreted_requirements.get("requirements", [])
                for literal in requirement.get("quoted_literals", [])
                if str(literal).strip()
            ],
        )
        report = build_report(
            goal,
            root,
            args.changed,
            args.command_prefix,
            args.run_id,
            resumed_aidlc_mode or args.aidlc or "",
            effective_official_manifest,
            requested_spec_kit_feature,
            workflow_override,
            bool(args.error),
            bool(args.reproduction_command),
            graph_mode,
            interpreted_requirements,
            validated_debug_diagnosis,
        )
        report["graph_lifecycle"] = graph_lifecycle
        report["scope_question_precondition"] = scope_precondition
        if required_official_authority is not None:
            report["requirement_authority"] = required_official_authority
        if saved_requirement_intake is not None:
            report["requirement_intake_resolution"] = interpreted_requirements[
                "intake_resolution"
            ]
        if isinstance(report.get("navigator"), dict):
            report["navigator"]["graph_lifecycle"] = graph_lifecycle
            if host_scope_proposal is not None:
                scope_evidence = report["navigator"].get("scope_evidence")
                if not isinstance(scope_evidence, dict):
                    parser.error("host scope proposal requires canonical Navigator scope evidence")
                host_decision = navigator_scope.host_proposal_decision(
                    root, scope_evidence, host_scope_proposal
                )
                updated_evidence = host_decision["scope_evidence"]
                report["navigator"]["scope_evidence"] = updated_evidence
                report["navigator"]["scope_host_packet"] = navigator_scope.host_reasoning_packet(
                    updated_evidence
                )
                report["navigator"]["scope_quality"] = navigator_scope.assess_scope_quality(
                    root,
                    goal,
                    report["navigator"].get("task_types", []),
                    updated_evidence,
                )
                report["navigator"]["scope_candidates"] = updated_evidence.get("candidates", [])
                report["navigator"]["likely_impacted_files"] = navigator_scope.project_likely_impacted(
                    updated_evidence.get("candidates", [])
                )
                report["host_scope_proposal_decision"] = {
                    key: value for key, value in host_decision.items()
                    if key not in {"scope_evidence", "scope_contract"}
                }
        selected_presentation = presentation_policy(
            report,
            verbose=bool(args.verbose),
            compatibility_override=args.presentation,
        )
        report["presentation"] = {
            "mode": selected_presentation["level"],
            "selection": selected_presentation["source"],
            "full_harness_detail": selected_presentation["full_harness_detail"],
            "verbose": bool(args.verbose),
            "boundary": "Plan detail is selected automatically from AIDLC and authority routing. It never changes requirements, scope, controls, approval, or workflow authority.",
        }
        report["target_root"] = {key: value for key, value in target.items() if key != "root"}
        fit = target_workspace.assess_plan_fit(
            goal,
            root,
            report.get("navigator", {}).get("likely_impacted_files", []),
            resolution_source=str(target.get("source", "unknown")),
            changed=args.changed,
        )
        report["target_fit"] = fit
        report["target_identity_assessment"] = fit
        if fit["blocking"]:
            boundary = target_fit_boundary_report(goal, root, fit, args.command_prefix, report)
            if args.format == "json":
                print(json.dumps(boundary, indent=2, sort_keys=True, default=str))
            else:
                print(render_markdown(boundary, verbose=args.verbose, presentation_mode=args.presentation), end="")
            return 2
        navigator_plan = report.get("navigator", {}) if isinstance(report.get("navigator"), dict) else {}
        scope_quality = navigator_plan.get("scope_quality", {})
        scope_gate_applies = isinstance(navigator_plan.get("scope_evidence"), dict) and not report.get("debug_plan")
        if scope_gate_applies and (not isinstance(scope_quality, dict) or scope_quality.get("blocking") is not False):
            boundary = scope_quality_boundary_report(report)
            if args.format == "json":
                print(json.dumps(boundary, indent=2, sort_keys=True, default=str))
            else:
                print(render_markdown(boundary, verbose=args.verbose, presentation_mode=args.presentation), end="")
            return 2
        authority_scope = navigator_plan.get("authority_scope", {})
        if isinstance(authority_scope, dict) and authority_scope.get("blocking") is True:
            boundary = scope_quality_boundary_report(report)
            boundary["scope_quality"] = {
                "status": "blocked",
                "evidence_state": "authority-scope-unresolved",
                "mode": "authority-owned-code-change",
                "reason_codes": ["authority-requirement-owner-required"],
                "missing_requirement_ids": authority_scope.get("unresolved_requirement_ids", []),
                "question": None,
            }
            boundary["requirements"] = navigator_plan.get("requirement_matrix", [])
            if args.format == "json":
                print(json.dumps(boundary, indent=2, sort_keys=True, default=str))
            else:
                print(render_markdown(boundary, verbose=args.verbose, presentation_mode=args.presentation), end="")
            return 2
        if isinstance(host_resolution, dict):
            report["host_workspace"] = {key: value for key, value in host_resolution.items() if key != "root"}
        report["enterprise_policy"] = policy_result
        report["input_roles"] = input_roles_registry
        effective_aidlc_mode = report["aidlc_mode"]["mode"]
        if (
            required_official_authority is not None
            and effective_aidlc_mode != required_official_authority["mode"]
        ):
            raise ValueError(
                "Navigator changed the AIDLC mode after official requirement authority was bound; restart with `tailtrail start \"<goal>\" --aidlc <standard|full>` for the selected mode"
            )
        if required_official_authority is not None:
            report["aidlc_requirements"] = {
                "state": "authority-bound-in-start-plan",
                "authority": "official-ai-dlc-pack",
                "mode": effective_aidlc_mode,
                "stage": "requirements",
                "official_references": required_official_authority["references"],
                "requirements": report.get("navigator", {}).get("requirement_matrix", []),
                "approval_gate": (
                    "Explicit approval of this Start Plan freezes the official AIDLC requirement boundary and its evidence-bound local scope mapping."
                ),
                "boundary": required_official_authority["boundary"],
            }

        # Phase 6: Post-discovery re-evaluation hook.
        # Re-applies the same scope_signal / scope_floor_lite thresholds as the
        # initial selection. Escalation-only (Lite -> Standard); does NOT fire
        # for off / full / explicit-standard. Does NOT auto-change the mode —
        # records the suggestion in the lock draft for explicit user approval.
        if effective_aidlc_mode == "lite":
            from metrics_extractor import compute_re_evaluation
            _navigator_block = report.get("navigator", {}) if isinstance(report.get("navigator"), dict) else {}
            _scope_quality = _navigator_block.get("scope_quality", {})
            _post_complexity = None
            if isinstance(_scope_quality, dict):
                _post_complexity = _scope_quality.get("complexity_metrics")
            _re_eval_suggestion = compute_re_evaluation(
                "lite",
                _post_complexity,
                scope_quality_blocking=bool(_scope_quality.get("blocking")) if isinstance(_scope_quality, dict) else False,
                complexity_available=bool(_post_complexity.get("available")) if isinstance(_post_complexity, dict) else False,
            )
            if _re_eval_suggestion is not None:
                report["aidlc_mode"]["re_evaluation_suggestion"] = _re_eval_suggestion

        if not args.no_planning_lock:
            created_run_id: str | None = None
            try:
                target_identity = target_workspace.identity(root)
                scope_decision = None
                if isinstance(report.get("navigator", {}).get("scope_evidence"), dict):
                    scope_decision = navigator_scope.decision_binding(
                        root, report["navigator"]["scope_evidence"], target_identity
                    )
                    scope_decision["graph_lifecycle"] = {
                        "fingerprint": graph_lifecycle.get("fingerprint"),
                        "cache_fingerprint": graph_lifecycle.get("cache_fingerprint"),
                        "action": graph_lifecycle.get("action"),
                        "status": graph_lifecycle.get("after_status", {}).get("status"),
                    }
                report["planning_lock"] = planning_lock.create(
                    root, goal, graph_attempt_id, args.reference_root,
                    target_identity=target_identity,
                    input_roles=report["input_roles"],
                    host_workspace=host_resolution,
                    enterprise_policy=policy_result,
                    scope_decision=scope_decision,
                    re_evaluation_suggestion=report.get("aidlc_mode", {}).get("re_evaluation_suggestion"),
                    pipeline_stage=planning_lock.initial_pipeline_stage(effective_aidlc_mode, bool(report.get("debug_plan"))),
                )
                created_run_id = report["planning_lock"]["run_id"]
                report["workflow_runtime"] = workflow_start_integration.draft(
                    report,
                    created_run_id,
                    disabled=args.no_workflow or bool(report.get("debug_plan")),
                )
                if report.get("debug_plan") and not args.no_workflow:
                    debug_scope_binding = report["workflow_runtime"].get("scope_binding")
                    report["workflow_runtime"] = {
                        "enabled": False,
                        "state": "deferred-to-di-4",
                        "reason": "The canonical debug-investigation DWR template is introduced in DI-4.",
                        "scope_binding": debug_scope_binding,
                        "boundary": "DI-2 creates only the canonical Planning Lock and saved Debug Start report.",
                    }
                report["target_resolution_receipt"] = enterprise_target_policy.receipt(root, created_run_id, target_identity=report["planning_lock"]["target_identity"], input_roles=report["input_roles"], policy_result=policy_result, host_workspace=host_resolution)
                if effective_aidlc_mode in {"standard", "full"}:
                    report["official_aidlc_bridge"] = official_aidlc_bridge.create(
                        root, created_run_id, goal,
                        manifest=effective_official_manifest,
                        official_intent_id=args.official_intent_id,
                        official_session_id=args.official_session_id,
                        official_stage=args.official_stage,
                        mode=effective_aidlc_mode,
                    )
                report["planning_report"] = planning_lock.save_start_report(root, created_run_id, report)
                if (
                    effective_aidlc_mode in {"standard", "full"}
                    and required_official_authority is not None
                ):
                    report["planning_report"] = planning_lock.enrich_start_report(
                        root, created_run_id, report
                    )
                elif effective_aidlc_mode == "standard" and not report.get("spec_kit_source"):
                    report["aidlc_requirements"] = planning_lock.request_official_aidlc_requirements(root, created_run_id)
                    report["planning_report"] = planning_lock.enrich_start_report(root, created_run_id, report)
                elif effective_aidlc_mode == "standard" and report.get("spec_kit_source"):
                    report["aidlc_requirements"] = {"state": "not-run", "reason": "Imported Intent Bridge requirements are the authoritative boundary; TailTrail must not generate a parallel requirement questionnaire."}
                    report["planning_report"] = planning_lock.enrich_start_report(root, created_run_id, report)
                elif effective_aidlc_mode == "full":
                    report["aidlc_requirements"] = planning_lock.request_official_aidlc_requirements(root, created_run_id)
                    report["planning_report"] = planning_lock.enrich_start_report(root, created_run_id, report)
                session_control.attach(root, created_run_id, reason_code="tailtrail-start")
            except Exception:
                if created_run_id is not None:
                    planning_lock.rollback_new_start(root, created_run_id)
                raise
        elif args.no_workflow:
            report["workflow_runtime"] = workflow_start_integration.draft(report, "not-persisted", disabled=True)
    except ValueError as error:
        parser.error(str(error))
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report, verbose=args.verbose, presentation_mode=args.presentation), end="")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        raise
    except Exception as error:  # noqa: BLE001 - last-resort: never exit silently
        print(f"tailtrail start: internal error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    raise SystemExit(exit_code)
