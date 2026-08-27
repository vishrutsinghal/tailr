"""Build a deterministic, requirement-linked Behaviour Harness plan.

Planning uses only explicit user wording and repository path inventory. It does
not inspect source, claim that a transition exists, or treat a candidate as an
approved edit target.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


BEHAVIOUR_SIGNALS = (
    "behaviour", "behavior", "customer", "journey", "notification", "state",
    "status", "transition", "user-facing", "workflow",
)
DOMAIN_TERMS = {
    "allocation", "cancellation", "inventory", "notification", "payment",
    "refund", "retry", "shipment",
}
UI_SIGNALS = ("ui", "user interface", "frontend", "front end", "screen", "page", "layout", "typography", "responsive", "accessibility")
BACKEND_SIGNALS = ("api", "endpoint", "backend", "service", "database", "server")


def selected_for(goal: str) -> bool:
    lowered = goal.lower()
    return any(signal in lowered for signal in (*BEHAVIOUR_SIGNALS, *UI_SIGNALS)) or " api " in f" {lowered} "


def _ui_only(goal: str) -> bool:
    lowered = goal.lower()
    return any(signal in lowered for signal in UI_SIGNALS) and not any(
        re.search(rf"(?<![a-z0-9_]){re.escape(signal)}(?![a-z0-9_])", lowered)
        for signal in BACKEND_SIGNALS
    )


def _inventory(root: Path, patterns: tuple[str, ...], limit: int = 2) -> list[str]:
    found: list[str] = []
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            try:
                relative_path = path.relative_to(root)
            except ValueError:
                continue
            if not path.is_file() or any(part in {".git", ".tailtrail", "__pycache__", "tailtrail"} for part in relative_path.parts):
                continue
            relative = relative_path.as_posix()
            if relative not in found:
                found.append(relative)
            if len(found) >= limit:
                return found
    return found


def _path_role(path: str) -> str:
    lowered = path.lower().replace("\\", "/")
    name = Path(lowered).name
    suffix = Path(lowered).suffix
    if "/tests/ui/" in f"/{lowered}" or any(marker in name for marker in ("accessibility", "a11y", "visual")): return "UI behaviour evidence"
    if suffix in {".css", ".scss", ".sass", ".less"}: return "UI style / token boundary"
    if suffix in {".html", ".jsx", ".tsx", ".vue", ".svelte"}: return "observable UI surface"
    if "/tests/behaviour/" in f"/{lowered}" or "/tests/behavior/" in f"/{lowered}": return "behaviour evidence"
    if "/tests/integration/" in f"/{lowered}": return "integration evidence"
    if "/tests/contract/" in f"/{lowered}": return "contract evidence"
    if any(word in name for word in ("api", "controller", "endpoint", "route")): return "observable interface"
    if any(word in name for word in ("service", "orchestrat", "workflow")): return "workflow orchestration"
    if any(word in name for word in ("repository", "model", "state")): return "authoritative state"
    if any(word in name for word in ("notification", "publisher", "event")): return "side-effect boundary"
    if any(word in name for word in ("allocation", "inventory")): return "allocation transition"
    if any(word in name for word in ("shipment", "shipping", "fulfil", "fulfill")): return "shipment transition"
    return "supporting candidate"


def filter_weak_suggestions(goal: str, impacted: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Exclude graph-only dependency files when the task does not change setup."""
    lowered = goal.lower()
    dependency_signal = any(word in lowered for word in ("dependency", "package", "build", "test configuration", "test runner"))
    result: list[dict[str, Any]] = []
    for item in impacted:
        path = str(item.get("path", "")); reason = str(item.get("reason", ""))
        name = Path(path.lower()).name
        if not dependency_signal and "suggested by Code Review Graph" in reason and name in {
            "package.json", "pyproject.toml", "requirements.txt", "pom.xml", "go.mod", "cargo.toml",
        }:
            continue
        result.append(item)
    return result


def add_role_candidates(root: Path, goal: str, impacted: list[dict[str, Any]], selected: bool) -> list[dict[str, Any]]:
    if not selected:
        return impacted
    # UI planning owns UI path discovery.  Generic service/repository patterns
    # would otherwise fabricate a backend scope for a page-only request.
    if _ui_only(goal):
        return impacted
    lowered = goal.lower(); existing = {str(item.get("path", "")) for item in impacted}
    existing_roles = {_path_role(path) for path in existing}; additions: list[dict[str, str]] = []
    roles: list[tuple[bool, str, str, tuple[str, ...]]] = [
        (True, "workflow orchestration", "behaviour workflow", ("src/**/service.py", "src/**/*service*.py", "app/**/*service*")),
        (any(word in lowered for word in ("status", "state", "journey", "transition")), "authoritative state", "authoritative state", ("src/**/repository.py", "src/**/models.py", "src/**/*state*.py", "app/**/*repository*")),
        ("allocation" in lowered, "allocation transition", "allocation transition", ("src/**/*allocation*.py", "src/**/inventory.py")),
        (any(word in lowered for word in ("shipment", "fulfil", "fulfill")), "shipment transition", "shipment transition", ("src/**/*shipment*.py", "src/**/shipping.py", "src/**/*fulfil*.py", "src/**/*fulfill*.py")),
        ("notification" in lowered, "side-effect boundary", "notification side effect", ("src/**/*notification*.py", "src/**/*publisher*.py", "src/**/*event*.py")),
        (True, "behaviour evidence", "behaviour evidence", ("tests/behaviour/test*.py", "tests/behavior/test*.py")),
        ("integration" in lowered, "integration evidence", "integration evidence", ("tests/integration/test*.py", "test/integration/test*.py")),
        ("api" in lowered or "response" in lowered or "contract" in lowered, "contract evidence", "API preservation evidence", ("tests/contract/test*.py", "test/contract/test*.py")),
    ]
    for active, expected_role, label, patterns in roles:
        if not active or expected_role in existing_roles:
            continue
        for path in _inventory(root, patterns, limit=1):
            if path not in existing:
                additions.append({"path": path, "reason": f"behaviour role candidate for {label}; verify after approval"})
                existing.add(path); existing_roles.add(expected_role)
    return [*impacted, *additions]


def _ids(requirements: list[dict[str, Any]], signals: tuple[str, ...]) -> list[str]:
    matched = [
        str(row.get("display_id", "REQ")) for row in requirements
        if any(signal in str(row.get("statement", "")).lower() for signal in signals)
    ]
    return list(dict.fromkeys(matched))


def _evidence(tiers: list[str], asserted: str) -> list[dict[str, str]]:
    return [{"tier": tier, "asserted_behavior": asserted} for tier in tiers]


def _scenarios(goal: str, requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if _ui_only(goal):
        return _ui_scenarios(requirements)
    lowered = goal.lower(); scenarios: list[dict[str, Any]] = []
    journey_ids = _ids(requirements, ("journey", "workflow", "status", "state", "transition", "creation", "allocation", "shipment"))
    preserve_ids = _ids(requirements, ("preserve", "existing api", "response", "contract", "unchanged"))
    explicit_notification_delivery = bool(re.search(
        r"\b(?:no|prevent|avoid)\s+duplicate\s+notifications?\b|"
        r"\bduplicate\s+notifications?\b|"
        r"\bnotifications?\b.{0,45}\b(?:exactly[- ]once|idempotent|deduplicat(?:e|ed|ion)|must not duplicate)\b|"
        r"\b(?:exactly[- ]once|idempotent|deduplicat(?:e|ed|ion))\b.{0,45}\bnotifications?\b",
        lowered,
    ))
    notification_ids = _ids(requirements, ("notification", "exactly once", "idempotent", "deduplicate")) if explicit_notification_delivery else []
    explicit_states = [name for name in ("creation", "allocation", "shipment") if name in lowered]
    journey = " -> ".join(explicit_states) if len(explicit_states) > 1 else "the approved user-visible workflow"
    if journey_ids:
        scenarios.append({
            "scenario_id": "BHV-01", "requirement_ids": journey_ids,
            "scenario": f"Observe {journey} through the approved interface.",
            "preconditions": ["The starting state and actor are confirmed after approval."],
            "action": f"Execute {journey} using the existing application boundaries.",
            "expected_outcome": "Each authoritative transition is observable in order through the customer/API surface.",
            "preservation": ["No transition is skipped, reordered, or reported from a non-authoritative state."],
            "evidence": _evidence(["behaviour", "integration"], "The approved user-visible journey completes with authoritative ordered states."),
        })
    if preserve_ids:
        api_specific = any(word in lowered for word in ("api", "response", "contract", "endpoint"))
        if api_specific:
            scenarios.append({
                "scenario_id": "BHV-02", "requirement_ids": preserve_ids,
                "scenario": "Exercise the existing API response at each affected workflow stage.",
                "preconditions": ["The current response contract is captured before implementation."],
                "action": "Compare the affected API responses before and after the approved change.",
                "expected_outcome": "Existing fields, meanings, and status behavior remain compatible.",
                "preservation": ["Do not silently remove, rename, or reinterpret an existing response field."],
                "evidence": _evidence(["contract", "integration"], "Existing API responses remain compatible across the affected workflow."),
            })
        else:
            scenarios.append({
                "scenario_id": "BHV-02", "requirement_ids": preserve_ids,
                "scenario": "Exercise the affected existing public behaviour before and after the refactor.",
                "preconditions": ["The observable behaviour and its existing proof path are confirmed after approval."],
                "action": "Compare the approved observable behaviour through the existing project boundary before and after the change.",
                "expected_outcome": "The refactor changes internal structure without changing approved observable behaviour.",
                "preservation": ["Do not infer an API contract or notification-delivery rule that the user did not request."],
                "evidence": _evidence(["behaviour", "integration"], "Affected existing public behaviour remains unchanged after the refactor."),
            })
    if notification_ids:
        scenarios.append({
            "scenario_id": "BHV-03", "requirement_ids": notification_ids,
            "scenario": "Replay or retry the logical transition that publishes a notification.",
            "preconditions": ["A logical transition identity and notification observation point are confirmed."],
            "action": "Deliver the same logical transition more than once through the approved path.",
            "expected_outcome": "The customer receives no duplicate notification for the same logical transition.",
            "preservation": ["The first valid notification is still published."],
            "evidence": _evidence(["integration", "behaviour"], "A replayed logical transition publishes no duplicate customer notification."),
        })
    return scenarios


def _ui_scenarios(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create UI-observable scenarios only from explicit requirement rows."""
    scenarios: list[dict[str, Any]] = []
    definitions = (
        (("session summary",), "Render the requested page and session summary.", "The requested summary is visible in the established page structure.", "populated and absent data"),
        (("validation status",), "Render each applicable validation status.", "Status is conveyed semantically and not by color alone.", "pending, valid, invalid, and failure"),
        (("export control",), "Operate each approved export control.", "The control exposes the correct enabled, disabled, focus, success, and failure behavior.", "enabled, disabled, focus, success, and failure"),
        (("json preview",), "Render the all-events JSON preview.", "Structured content remains readable for populated, empty, error, and overflowing data.", "populated, empty, malformed/error, and overflow"),
    )
    for index, (signals, scenario, outcome, states) in enumerate(definitions, start=1):
        ids = _ids(requirements, signals)
        if not ids:
            continue
        scenarios.append({
            "scenario_id": f"BHV-UI-{index:02d}",
            "requirement_ids": ids,
            "scenario": scenario,
            "preconditions": ["The repository-owned UI shell, tokens, and interaction conventions are confirmed after approval."],
            "action": "Exercise the named UI outcome through the project-owned interface.",
            "expected_outcome": outcome,
            "preservation": [f"Cover applicable states: {states}", "Preserve existing responsive and accessibility conventions."],
            "evidence": _evidence(["behaviour"], outcome),
        })
    page_ids = _ids(requirements, ("page", "screen", "view"))
    if page_ids and not scenarios:
        scenarios.append({
            "scenario_id": "BHV-UI-01", "requirement_ids": page_ids,
            "scenario": "Render the requested UI within the existing project shell.",
            "preconditions": ["The nearest comparable UI and shared conventions are confirmed after approval."],
            "action": "Open the requested interface at its approved route or entry point.",
            "expected_outcome": "The named UI outcome is observable without introducing a parallel visual system.",
            "preservation": ["Preserve loading, empty, error, focus, responsive, and accessibility behavior where applicable."],
            "evidence": _evidence(["behaviour"], "The requested UI renders within the existing project conventions."),
        })
    return scenarios


def build(goal: str, impacted: list[dict[str, Any]], requirements: list[dict[str, Any]], selected: bool) -> dict[str, Any]:
    if not selected:
        return {"selected": False, "scenarios": [], "scope_roles": [], "post_change_checks": []}
    ui_only = _ui_only(goal)
    scenarios = _scenarios(goal, requirements)
    roles = [{
        "path": str(item.get("path", "")), "role": _path_role(str(item.get("path", ""))),
        "planned_use": "Required proof candidate; run only after approval." if "evidence" in _path_role(str(item.get("path", ""))) else "Inspect after approval; edit only when the confirmed behaviour path requires it.",
        "confidence": "user/goal target" if any(marker in str(item.get("reason", "")) for marker in ("goal-matched", "user-provided")) else "repository-inventory hypothesis",
    } for item in impacted]
    return {
        "selected": True, "state": "planning-hypothesis", "scenarios": scenarios,
        "scope_roles": roles,
        "required_tiers": list(dict.fromkeys(tier for scenario in scenarios for item in scenario["evidence"] for tier in [item["tier"]])),
        "post_change_checks": [
            "Confirm the comparable UI, shared conventions, applicable states, and observable interface before the first edit.",
            "Map each rendered outcome and interaction to an approved UI scenario and requirement ID.",
            "Reconcile actual changed paths with the approved UI roles; justify or correct unexpected scope.",
            "Require project-owned behaviour/accessibility receipts; a unit assertion alone cannot prove the visible journey.",
            "Report unresolved UI states as evidence-incomplete or drifted, never as a generic pass.",
        ] if ui_only else [
            "Confirm the actor, starting state, authoritative state owner, and observable interface before the first edit.",
            "Map each actual transition and side effect to an approved behaviour scenario and requirement ID.",
            "Reconcile actual changed paths with the approved behaviour roles; justify or correct unexpected scope.",
            "Require matching behaviour and integration receipts; unit evidence alone cannot complete the Behaviour Harness.",
            "Report unresolved scenarios as evidence-incomplete or drifted, never as a generic pass.",
        ],
        "completion_states": ["preserved", "failed", "evidence-incomplete", "expanded-needs-approval", "unknown"],
        "evidence_boundary": "Derived from explicit user wording and repository UI path inventory only. Actual rendering, states, interactions, accessibility behavior, and edit necessity remain unconfirmed until after approval." if ui_only else "Derived from explicit user wording and repository path inventory only. Actual states, transitions, side effects, responses, and edit necessity remain unconfirmed until after approval.",
    }


def apply_contracts(requirements: list[dict[str, Any]], plan: dict[str, Any]) -> None:
    if not plan.get("selected"):
        return
    scenarios = plan.get("scenarios", [])
    for row in requirements:
        requirement_id = str(row.get("display_id", "REQ"))
        linked = [scenario for scenario in scenarios if requirement_id in scenario.get("requirement_ids", [])]
        contract = dict(row.get("behavior_contract", {}))
        contract["scenarios"] = [{key: value for key, value in scenario.items() if key != "requirement_ids"} for scenario in linked]
        contract["completion_states"] = list(plan.get("completion_states", []))
        contract["evidence_boundary"] = plan.get("evidence_boundary")
        row["behavior_contract"] = contract
        tiers = list((row.get("validation_contract", {}) or {}).get("tiers", []))
        for scenario in linked:
            for evidence in scenario.get("evidence", []):
                tier = str(evidence.get("tier", ""))
                if tier and tier not in tiers:
                    tiers.append(tier)
        row["validation_contract"] = {"state": "required", "tiers": tiers or ["behaviour"]}


def markdown_lines(plan: dict[str, Any], detailed: bool) -> list[str]:
    if not plan.get("selected"):
        return []
    lines = [
        "", "## Behaviour Harness Plan", "",
        f"- State: `{plan.get('state')}`.",
        f"- Evidence boundary: {plan.get('evidence_boundary')}",
        "", "### Requirement-linked behaviour scenarios", "",
        "| Requirement | Scenario | Observable result | Preservation rule | Required proof |",
        "| --- | --- | --- | --- | --- |",
    ]
    for scenario in plan.get("scenarios", []):
        proof = ", ".join(str(item.get("tier")) for item in scenario.get("evidence", []))
        values = [", ".join(scenario.get("requirement_ids", [])), scenario.get("scenario", ""), scenario.get("expected_outcome", ""), "; ".join(scenario.get("preservation", [])), proof]
        lines.append("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", " ") for value in values) + " |")
    if not plan.get("scenarios"):
        lines.append("| unresolved | The user-facing scenario must be clarified before approval. | No behavioural outcome inferred. | Existing behaviour remains authoritative. | evidence-incomplete |")
    if detailed:
        lines.extend(["", "### Behaviour scope roles", "", "| Path | Role | Planned use | Confidence |", "| --- | --- | --- | --- |"])
        for item in plan.get("scope_roles", []):
            values = [f"`{item.get('path')}`", item.get("role"), item.get("planned_use"), item.get("confidence")]
            lines.append("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", " ") for value in values) + " |")
        lines.extend(["", "### Post-change Behaviour Harness checks", ""])
        lines.extend(f"{index}. {item}" for index, item in enumerate(plan.get("post_change_checks", []), 1))
        lines.extend(["", "- Final state must be one of: " + ", ".join(f"`{state}`" for state in plan.get("completion_states", [])) + "."])
    return lines
