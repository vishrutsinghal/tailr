"""Build a deterministic, requirement-linked Maintainability Harness plan.

This module uses only explicit goal wording and Navigator path inventory.  It
does not inspect source during Planning Lock and does not claim that duplicate
logic, an abstraction, or an edit target has been confirmed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


SIGNALS = (
    "refactor", "duplicate", "duplication", "consolidate", "reuse",
    "abstraction", "scope creep", "simplify", "cleanup", "maintainability",
)


def selected_for(goal: str) -> bool:
    lowered = goal.lower()
    return any(signal in lowered for signal in SIGNALS)


def _ids(requirements: list[dict[str, Any]], signals: tuple[str, ...]) -> list[str]:
    return list(dict.fromkeys(
        str(row.get("display_id", "REQ"))
        for row in requirements
        if any(signal in str(row.get("statement", "")).lower() for signal in signals)
    ))


def _path_role(path: str) -> str:
    lowered = path.lower().replace("\\", "/")
    name = Path(lowered).name
    if "tests" in Path(lowered).parts or name.startswith("test_"):
        return "preservation evidence"
    if any(word in name for word in ("service", "orchestrat", "workflow")):
        return "candidate orchestration owner"
    if any(word in name for word in ("payment", "notification", "publisher", "adapter")):
        return "existing boundary to reuse"
    if name in {"pyproject.toml", "package.json", "pom.xml", "go.mod", "cargo.toml"}:
        return "dependency manifest; inspect only if dependency scope is approved"
    return "supporting candidate"


def build(
    goal: str,
    impacted: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    selected: bool,
) -> dict[str, Any]:
    if not selected:
        return {"selected": False, "rules": [], "scope_roles": [], "baseline_metrics": [], "post_change_checks": []}

    rules: list[dict[str, Any]] = []

    def add(rule_id: str, requirement_ids: list[str], objective: str, proof: str, failure: str) -> None:
        if requirement_ids:
            rules.append({
                "rule_id": rule_id,
                "requirement_ids": requirement_ids,
                "objective": objective,
                "proof": proof,
                "failure": failure,
            })

    add(
        "MNT-01",
        _ids(requirements, ("duplicate", "duplication", "consolidate", "refactor")),
        "Keep one authoritative orchestration path and reduce confirmed duplicated structure.",
        "Compare the approved pre-edit AST/call-sequence baseline with the post-change assessment and review the focused diff.",
        "Duplication does not decrease, a parallel path remains, or no evidence demonstrates the requested reduction.",
    )
    add(
        "MNT-02",
        _ids(requirements, ("reuse", "existing project boundary", "existing boundary")),
        "Reuse an existing owned project boundary before introducing another layer.",
        "Map the retained boundary and its callers to the requirement; report any new production abstraction and its real call sites.",
        "A second boundary or single-use wrapper is introduced without approved necessity.",
    )
    add(
        "MNT-03",
        _ids(requirements, ("avoid speculative", "abstraction")),
        "Avoid speculative, future-only, or single-use abstraction.",
        "Compare new production symbols and abstraction heuristics with the approved baseline; inspect every newly introduced layer.",
        "A new abstraction has no demonstrated current reuse or only moves unchanged logic behind another name.",
    )
    add(
        "MNT-04",
        _ids(requirements, ("preserve", "public behaviour", "public behavior", "tests")),
        "Preserve observable behaviour and relevant test intent while refactoring structure.",
        "Use requirement-linked preservation receipts; test edits alone cannot prove the production requirement.",
        "Observable behaviour changes, safeguards weaken, or tests are changed to follow incorrect production behaviour.",
    )
    add(
        "MNT-05",
        _ids(requirements, ("unrelated scope", "scope expansion", "scope creep", "do not expand")),
        "Keep actual changes inside the approved refactor boundary.",
        "Reconcile every changed path against approved candidate paths and requirement IDs.",
        "An unrelated path changes without an approved amendment and requirement linkage.",
    )

    scope_roles = [{
        "path": str(item.get("path", "")),
        "role": _path_role(str(item.get("path", ""))),
        "planned_use": (
            "Run as focused preservation proof after implementation."
            if _path_role(str(item.get("path", ""))) == "preservation evidence"
            else "Inspect after approval; edit only if the confirmed refactor path requires it."
        ),
        "confidence": "user/goal target" if any(
            marker in str(item.get("reason", "")) for marker in ("goal-matched", "user-provided")
        ) else "repository-inventory hypothesis",
    } for item in impacted]

    return {
        "selected": True,
        "state": "planning-hypothesis",
        "rules": rules,
        "scope_roles": scope_roles,
        "baseline_timing": "Automatically after explicit Planning Lock approval and before the first source edit.",
        "baseline_metrics": [
            {"metric": "duplicate function-body groups", "use": "detect exact repeated Python structures within approved production candidates"},
            {"metric": "duplicate call-sequence groups", "use": "detect repeated orchestration sequences without interpreting business semantics"},
            {"metric": "production symbols and abstraction candidates", "use": "identify newly introduced layers and single-method abstraction heuristics"},
            {"metric": "approved versus actual changed paths", "use": "detect unrelated scope expansion deterministically"},
            {"metric": "requirement-linked preservation receipts", "use": "separate passing behaviour from code-shape improvement"},
        ],
        "post_change_checks": [
            "Compare the post-change structural snapshot with the immutable pre-edit baseline; do not claim semantic duplication reduction from AST evidence alone.",
            "Confirm one authoritative orchestration path remains and existing payment/notification boundaries are reused where the approved code path supports them.",
            "Inspect every newly introduced production symbol or abstraction candidate for more than one current justified use.",
            "Reconcile actual changed paths with approved requirement IDs; classify unjustified expansion as new drift.",
            "Require production and preservation evidence together; changing only tests is a blocking test-chasing signal.",
        ],
        "completion_states": ["improved", "preserved", "regressed", "evidence-incomplete", "expanded-needs-approval", "unknown"],
        "evidence_boundary": "Planning rules come from explicit user wording and repository path inventory only. Duplicate logic, authoritative ownership, call sites, and edit necessity are verified only after approval through the saved baseline, source review, diff, and receipts.",
    }


def apply_contracts(requirements: list[dict[str, Any]], plan: dict[str, Any]) -> None:
    if not plan.get("selected"):
        return
    rules = plan.get("rules", [])
    candidate_paths = [str(item.get("path", "")) for item in plan.get("scope_roles", []) if item.get("path")]
    for row in requirements:
        requirement_id = str(row.get("display_id", "REQ"))
        linked = [rule for rule in rules if requirement_id in rule.get("requirement_ids", [])]
        row["maintainability_contract"] = {
            "rules": [{key: value for key, value in rule.items() if key != "requirement_ids"} for rule in linked],
            "candidate_paths": candidate_paths,
            "baseline_required": bool(linked),
            "completion_states": list(plan.get("completion_states", [])),
            "evidence_boundary": plan.get("evidence_boundary"),
        }


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown_lines(plan: dict[str, Any], detailed: bool) -> list[str]:
    if not plan.get("selected"):
        return []
    lines = [
        "", "## Maintainability Harness Plan", "",
        f"- State: `{plan.get('state')}`.",
        f"- Baseline: {plan.get('baseline_timing')}",
        f"- Evidence boundary: {plan.get('evidence_boundary')}",
        "", "### Requirement-linked maintainability rules", "",
        "| Rule | Requirement | Objective | Required proof | Failure condition |",
        "| --- | --- | --- | --- | --- |",
    ]
    for rule in plan.get("rules", []):
        values = [rule.get("rule_id"), ", ".join(rule.get("requirement_ids", [])), rule.get("objective"), rule.get("proof"), rule.get("failure")]
        lines.append("| " + " | ".join(_cell(value) for value in values) + " |")
    if detailed:
        lines.extend(["", "### Maintainability scope roles", "", "| Path | Role | Planned use | Confidence |", "| --- | --- | --- | --- |"])
        for item in plan.get("scope_roles", []):
            values = [f"`{item.get('path')}`", item.get("role"), item.get("planned_use"), item.get("confidence")]
            lines.append("| " + " | ".join(_cell(value) for value in values) + " |")
        lines.extend(["", "### Pre-edit baseline metrics", "", "| Metric | Purpose |", "| --- | --- |"])
        for item in plan.get("baseline_metrics", []):
            lines.append(f"| {_cell(item.get('metric'))} | {_cell(item.get('use'))} |")
        lines.extend(["", "### Post-change Maintainability Harness checks", ""])
        lines.extend(f"{index}. {item}" for index, item in enumerate(plan.get("post_change_checks", []), 1))
        lines.extend(["", "- Final state must be one of: " + ", ".join(f"`{state}`" for state in plan.get("completion_states", [])) + "."])
    return lines
