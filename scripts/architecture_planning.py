"""Build a deterministic, requirement-linked Architecture Fitness plan.

This module is deliberately planning-only. It uses explicit user wording and
repository path inventory; it does not read source, claim caller relationships,
or decide that a candidate path must be edited before approval.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


GENERIC_TOKENS = {
    "add", "and", "api", "behaviour", "behavior", "create", "existing",
    "focused", "handling", "implementation", "integration", "order", "proof",
    "requirement", "reuse", "service", "src", "submission", "task", "tasks",
    "test", "tests", "the", "with",
}
DEPENDENCY_FILES = {
    "cargo.toml", "composer.json", "go.mod", "package.json", "pom.xml",
    "pyproject.toml", "requirements.txt",
}
DOMAIN_TERMS = {
    "allocation", "cancellation", "inventory", "notification", "payment",
    "refund", "retry", "shipment",
}


def tokens(value: str) -> set[str]:
    return {
        item for item in re.findall(r"[a-z][a-z0-9]+", value.lower())
        if len(item) > 2 and item not in GENERIC_TOKENS
    }


def role(path: str) -> str:
    lowered = path.lower().replace("\\", "/")
    name = Path(lowered).name
    wrapped = f"/{lowered}"
    if "/tests/unit/" in wrapped or "/test/unit/" in wrapped: return "unit evidence"
    if "/tests/integration/" in wrapped or "/test/integration/" in wrapped: return "integration evidence"
    if "/tests/contract/" in wrapped: return "contract evidence"
    if "/tests/behaviour/" in wrapped or "/tests/behavior/" in wrapped: return "behaviour evidence"
    if "/tests/" in wrapped or name.startswith("test_"): return "test evidence"
    if lowered.startswith("specs/") or "/specs/" in wrapped or name in {"requirements.md", "design.md", "tasks.md"}: return "requirement source"
    if name in DEPENDENCY_FILES or name.endswith((".lock", ".csproj", ".fsproj")): return "dependency boundary"
    if any(part in name for part in ("api", "controller", "endpoint", "route")): return "interface boundary"
    if any(part in name for part in ("service", "orchestrat", "use_case", "usecase")): return "orchestration boundary"
    if any(part in name for part in ("validation", "validator")): return "validation boundary"
    if any(part in name for part in ("payment", "gateway", "adapter", "repository", "inventory", "notification", "audit")): return "domain/integration boundary"
    if lowered.startswith("infra/") or name.endswith(".tf"): return "infrastructure boundary"
    return "implementation candidate"


def filter_weak_suggestions(goal: str, impacted: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop graph-suggested requirement documents unrelated to this feature."""
    goal_tokens = tokens(goal)
    result: list[dict[str, Any]] = []
    for item in impacted:
        path = str(item.get("path", ""))
        reason = str(item.get("reason", ""))
        if role(path) == "requirement source" and "suggested by Code Review Graph" in reason:
            feature_tokens = tokens(path)
            if feature_tokens and not feature_tokens.intersection(goal_tokens):
                continue
        result.append(item)
    return result


def _inventory(root: Path, patterns: tuple[str, ...], limit: int = 4) -> list[str]:
    found: list[str] = []
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            try:
                relative_path = path.relative_to(root)
            except ValueError:
                continue
            relative = relative_path.as_posix()
            if not path.is_file() or any(part in {".git", ".tailtrail", "tailtrail"} for part in relative_path.parts):
                continue
            if relative not in found:
                found.append(relative)
            if len(found) >= limit:
                return found
    return found


def add_explicit_role_candidates(root: Path, goal: str, impacted: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add explicitly named architecture roles using only file inventory."""
    lowered = goal.lower()
    existing = {str(item.get("path", "")) for item in impacted}
    additions: list[dict[str, str]] = []
    requested: list[tuple[bool, str, tuple[str, ...]]] = [
        ("api" in lowered, "API/interface", ("src/**/api.py", "src/**/*api*.py", "app/**/api.py", "app/**/*controller*")),
        ("service" in lowered or "caller" in lowered, "service/orchestration", ("src/**/service.py", "src/**/*service*.py", "app/**/*service*")),
        ("validat" in lowered, "validation", ("src/**/validation.py", "src/**/*validator*.py", "src/**/*validation*.py", "app/**/*validator*", "app/**/*validation*")),
        (
            "validat" in lowered and any(term in lowered for term in ("focused", "evidence", "proof", "test")),
            "unit evidence",
            ("tests/unit/test*validat*.py", "test/unit/test*validat*.py", "tests/test*validat*.py"),
        ),
    ]
    existing_roles = {role(path) for path in existing}
    for active, label, patterns in requested:
        expected_role = {
            "API/interface": "interface boundary",
            "service/orchestration": "orchestration boundary",
            "validation": "validation boundary",
            "unit evidence": "unit evidence",
        }[label]
        if not active or expected_role in existing_roles:
            continue
        for path in _inventory(root, patterns):
            if path not in existing:
                additions.append({"path": path, "reason": f"architecture role candidate from explicit {label} wording; verify after approval"})
                existing.add(path)
                existing_roles.add(expected_role)
    return [*impacted, *additions]


def _requirement_ids(requirements: list[dict[str, Any]], value: str) -> list[str]:
    wanted = tokens(value)
    matches = [
        str(row.get("display_id", "REQ")) for row in requirements
        if wanted.intersection(tokens(str(row.get("statement", ""))))
    ]
    return matches or [str(row.get("display_id", "REQ")) for row in requirements if row.get("kind") != "preserve"][:1]


def _invariants(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(signal: str, invariant: str, guidance: str, proof: str) -> None:
        if invariant in seen:
            return
        seen.add(invariant)
        result.append({
            "requirement_ids": _requirement_ids(requirements, signal),
            "invariant": invariant,
            "implementation_guidance": guidance,
            "planned_proof": proof,
            "confidence": "inferred-from-user-wording",
        })

    joined = " ".join(str(row.get("statement", "")) for row in requirements).lower()
    if "retry" in joined:
        add("idempotent retry payment", "Retries must not duplicate payment or order-submission side effects.", "Keep retry/idempotency coordination at the existing service/payment boundary; do not create caller-specific retry logic.", "Focused idempotency unit evidence plus order-submission integration evidence.")
    elif "idempotent" in joined:
        add("idempotent", "Repeated execution must not duplicate approved side effects.", "Keep idempotency at the confirmed authoritative boundary rather than adding caller-specific duplicate handling.", "Focused repeated-execution evidence plus integration proof for the affected side effects.")
    if "existing" in joined and "adapter" in joined:
        add("existing adapter", "The existing adapter remains the authoritative external-payment boundary.", "Extend or reuse that adapter and its established call path; do not bypass it from the API or service.", "Changed-symbol/import review and caller-path integration evidence.")
    if "caller" in joined or "map every" in joined:
        add("caller service api", "Every material service and API caller must be assessed before the implementation boundary is finalized.", "Treat caller paths as inspection candidates, not automatic edit targets; update only callers whose approved contract requires change.", "Requirement-linked Code Graph receipt plus changed-scope reconciliation.")
    if "preserve" in joined or "unchanged" in joined:
        add("preserve behaviour", "Behaviour outside the approved change boundary remains compatible.", "Reuse the confirmed authoritative boundaries and avoid special-case behavior in individual callers.", "Existing preservation-path evidence plus focused regression proof.")
    if "dependency" in joined and ("do not" in joined or "without" in joined or "no new" in joined):
        add("dependency", "Dependency manifests and lock files remain unchanged.", "Use the standard library and installed project capabilities; route any unavoidable dependency through a new approved plan.", "Changed-path dependency-manifest check.")
    if "second" in joined and ("abstraction" in joined or "adapter" in joined or "client" in joined):
        add("second abstraction adapter", "No parallel payment adapter, client, or orchestration boundary is introduced.", "Modify the existing boundary instead of creating a V2/new/retry-specific payment abstraction.", "Changed-symbol/path review and Maintainability/Architecture assessment.")
    if not result:
        add("architecture", "The implementation must follow the existing repository boundaries discovered after approval.", "Confirm layer ownership and callers before editing; keep actual changed scope within the approved impact map.", "Changed-scope comparison plus the repository's focused tests.")
    return result


def build(goal: str, impacted: list[dict[str, Any]], requirements: list[dict[str, Any]], selected: bool) -> dict[str, Any]:
    if not selected:
        return {"selected": False, "invariants": [], "scope_roles": [], "post_change_checks": []}
    invariants = _invariants(requirements)
    scope_roles: list[dict[str, Any]] = []
    for item in impacted:
        path = str(item.get("path", "")); path_role = role(path); reason = str(item.get("reason", ""))
        if path_role.endswith("evidence"):
            planned_use = "Run only when its tier proves an approved requirement."
        elif path_role == "requirement source":
            planned_use = "Read-only requirement context; never implementation scope without an explicit source-owned link."
        elif "candidate" in reason or "suggested" in reason:
            planned_use = "Inspect after approval; edit only if the confirmed architecture contract requires it."
        else:
            planned_use = "Primary implementation candidate, subject to post-approval source and caller confirmation."
        scope_roles.append({
            "path": path, "role": path_role, "planned_use": planned_use,
            "requirement_ids": _requirement_ids(requirements, path),
            "confidence": "user/goal target" if "target" in reason and "suggested" not in reason else "repository-inventory hypothesis",
        })
    checks = [
        "Confirm the authoritative boundary and material callers before the first edit.",
        "Compare actual changed files and symbols with the approved impact map; justify or correct every unexpected path.",
        "Detect missed callers, caller-specific business logic, wrong-layer placement, and public-contract drift.",
        "Check dependency manifests and imports when the approved contract forbids a new dependency.",
        "Run every requirement-linked validation tier and preserve unresolved evidence as a gap, not a pass.",
    ]
    plan = {
        "selected": True,
        "state": "planning-hypothesis",
        "invariants": invariants,
        "scope_roles": scope_roles,
        "post_change_checks": checks,
        "evidence_boundary": "Derived from explicit user wording and repository path inventory only. Source, caller relationships, and edit necessity are not confirmed until after approval.",
    }
    _assert_relevant(goal, impacted, plan)
    return plan


def _assert_relevant(goal: str, impacted: list[dict[str, Any]], plan: dict[str, Any]) -> None:
    """Fail before persistence when a domain-specific invariant leaks across runs."""
    source = " ".join([goal, *[str(item.get("path", "")) for item in impacted]]).lower()
    generated = " ".join(
        str(item.get(field, ""))
        for item in plan.get("invariants", [])
        for field in ("invariant", "implementation_guidance", "planned_proof")
    ).lower()
    foreign = sorted(term for term in DOMAIN_TERMS if term in generated and term not in source)
    if foreign:
        raise ValueError("Architecture planning relevance check rejected foreign domain terms: " + ", ".join(foreign))


def apply_contracts(requirements: list[dict[str, Any]], plan: dict[str, Any]) -> None:
    if not plan.get("selected"):
        return
    roles = plan.get("scope_roles", [])
    for row in requirements:
        display_id = str(row.get("display_id", "REQ"))
        row_invariants = [item for item in plan.get("invariants", []) if display_id in item.get("requirement_ids", [])]
        inspection = [item["path"] for item in roles if display_id in item.get("requirement_ids", [])]
        contract = dict(row.get("architecture_contract", {}))
        contract.setdefault("required_paths", [])
        contract.setdefault("protected_paths", [])
        contract.setdefault("forbidden_imports", [])
        contract.update({
            "inspection_paths": list(dict.fromkeys(inspection)),
            "implementation_candidates": [item["path"] for item in roles if item["path"] in inspection and "evidence" not in item["role"] and item["role"] != "requirement source"],
            "invariants": [item["invariant"] for item in row_invariants],
            "post_change_checks": list(plan.get("post_change_checks", [])),
            "requires_caller_map": any("caller" in item["invariant"].lower() for item in row_invariants),
            "no_new_dependencies": any("dependency" in item["invariant"].lower() for item in row_invariants),
            "no_parallel_boundary": any("parallel" in item["invariant"].lower() for item in row_invariants),
            "evidence_boundary": plan.get("evidence_boundary"),
        })
        row["architecture_contract"] = contract


def markdown_lines(plan: dict[str, Any], detailed: bool) -> list[str]:
    if not plan.get("selected"):
        return []
    lines = [
        "", "## Architecture Fitness Plan", "",
        f"- State: `{plan.get('state')}`.",
        f"- Evidence boundary: {plan.get('evidence_boundary')}",
        "", "### Requirement-linked architecture contract", "",
        "| Requirement | Architecture invariant | Implementation guidance | Planned proof |",
        "| --- | --- | --- | --- |",
    ]
    for item in plan.get("invariants", []):
        cells = [
            ", ".join(item.get("requirement_ids", [])), item.get("invariant", ""),
            item.get("implementation_guidance", ""), item.get("planned_proof", ""),
        ]
        lines.append("| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", " ") for cell in cells) + " |")
    if detailed:
        lines.extend(["", "### Architecture scope roles", "", "| Path | Role | Planned use | Confidence |", "| --- | --- | --- | --- |"])
        for item in plan.get("scope_roles", []):
            cells = [f"`{item.get('path')}`", item.get("role"), item.get("planned_use"), item.get("confidence")]
            lines.append("| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", " ") for cell in cells) + " |")
        lines.extend(["", "### Post-change Architecture Fitness checks", ""])
        lines.extend(f"{index}. {item}" for index, item in enumerate(plan.get("post_change_checks", []), 1))
        lines.extend(["", "- Final state must be `preserved`, `drifted`, `expanded-needs-approval`, or `unknown`; TailTrail must not report a generic architecture pass without the named evidence."])
    return lines
