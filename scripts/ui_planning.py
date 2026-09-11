"""Build a deterministic, repository-aware UI Consistency planning contract.

Planning reads path inventory only.  It does not inspect UI source, infer that
an existing screen implements the requested feature, or grant edit authority.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


IGNORED_PARTS = {
    ".git", ".tailtrail", ".video-tools", ".venv", "__pycache__",
    "build", "coverage", "dist", "node_modules", "tailtrail", "venv",
}
STYLE_SUFFIXES = {".css", ".less", ".sass", ".scss"}
SCREEN_SUFFIXES = {".html", ".jsx", ".svelte", ".tsx", ".vue"}
SCRIPT_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"}
UI_PARTS = {"app", "client", "components", "frontend", "pages", "routes", "screens", "ui", "views"}
COMPONENT_PARTS = {"components", "component", "shared", "ui", "widgets"}
STYLE_PARTS = {"design-system", "style", "styles", "theme", "themes", "tokens"}
TEST_PARTS = {"__tests__", "e2e", "test", "tests"}
MANIFESTS = {"package.json", "vite.config.js", "vite.config.ts", "next.config.js", "next.config.mjs"}
UI_TERMS = (
    "ui", "user interface", "frontend", "front end", "screen", "page",
    "component", "layout", "modal", "dialog", "form", "dashboard",
    "button", "typography", "font", "theme", "responsive", "accessibility",
)
# ``repository`` alone usually means the codebase in UI prompts (for example
# "reuse the repository's styles"), not a data-access layer.  Keep only
# unambiguous backend-surface signals here.
BACKEND_TERMS = ("api", "endpoint", "backend", "service", "database", "server")


def _contains(text: str, term: str) -> bool:
    escaped = re.escape(term.lower()).replace(r"\ ", r"\s+")
    return re.search(rf"(?<![a-z0-9_]){escaped}(?![a-z0-9_])", text.lower()) is not None


def selected_for(goal: str, changed: list[str]) -> bool:
    if any(_contains(goal, term) for term in UI_TERMS):
        return True
    return any(_role(path) != "non-ui" for path in changed)


def _role(path: str) -> str:
    value = path.replace("\\", "/").lower()
    relative = Path(value)
    parts = set(relative.parts)
    name, suffix = relative.name, relative.suffix
    if name in MANIFESTS:
        return "frontend manifest"
    is_test_file = (
        name.startswith("test_")
        or ".test." in name
        or ".spec." in name
        or ".cy." in name
        or any(marker in name for marker in ("accessibility", "a11y", "visual"))
    )
    if is_test_file and (
        parts & UI_PARTS
        or suffix in {".jsx", ".tsx", ".vue", ".svelte"}
        or any(marker in name for marker in ("ui", "page", "screen", "visual", "accessibility", "a11y"))
    ):
        return "UI evidence"
    if suffix in STYLE_SUFFIXES or parts & STYLE_PARTS:
        return "style / token source"
    if name == "readme.md" and parts & UI_PARTS:
        return "UI guidance"
    if suffix in SCREEN_SUFFIXES and (parts & UI_PARTS or suffix == ".html"):
        if parts & {"components", "component", "shared", "widgets"}:
            return "shared component candidate"
        return "comparable screen candidate"
    if suffix in SCRIPT_SUFFIXES and parts & UI_PARTS:
        return "UI source candidate"
    return "non-ui"


def _candidate_paths(root: Path) -> list[Path]:
    try:
        import subprocess
        tracked = subprocess.run(["git", "ls-files"], cwd=root, text=True, capture_output=True, check=False)
        if tracked.returncode == 0:
            paths = [line.strip() for line in tracked.stdout.splitlines() if line.strip()]
            untracked = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=root, text=True, capture_output=True, check=False,
            )
            if untracked.returncode == 0:
                paths.extend(line.strip() for line in untracked.stdout.splitlines() if line.strip())
            if paths:
                return [root / line for line in dict.fromkeys(paths)]
    except OSError:
        pass
    return list(root.rglob("*"))[:10_000]


def discover(root: Path, goal: str, changed: list[str]) -> dict[str, Any]:
    """Discover UI structure from filenames and directories, without source reads."""
    domain_terms = [
        word for word in re.findall(r"[a-z][a-z0-9-]{2,}", goal.lower())
        if word not in {"add", "and", "all", "existing", "for", "page", "the", "with"}
    ][:10]
    candidates: list[dict[str, Any]] = []
    for path in _candidate_paths(root):
        if not path.is_file():
            continue
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if any(part.lower() in IGNORED_PARTS for part in relative.parts):
            continue
        rel = relative.as_posix()
        role = _role(rel)
        if role == "non-ui":
            continue
        score = {
            "comparable screen candidate": 60,
            "shared component candidate": 55,
            "style / token source": 50,
            "UI evidence": 45,
            "UI guidance": 40,
            "UI source candidate": 35,
            "frontend manifest": 20,
        }[role]
        score += sum(5 for term in domain_terms if term in rel.lower())
        candidates.append({"path": rel, "role": role, "score": score})
    ranked = sorted(candidates, key=lambda item: (-int(item["score"]), str(item["path"])))
    # Keep useful role diversity before filling the remaining bounded inventory.
    selected: list[dict[str, Any]] = []
    seen_roles: set[str] = set()
    for item in ranked:
        if item["role"] not in seen_roles:
            selected.append(item); seen_roles.add(str(item["role"]))
    for item in ranked:
        if item not in selected and len(selected) < 10:
            selected.append(item)
    explicit_ui = [path for path in changed if _role(path) != "non-ui"]
    discovered_surface = any(item["role"] in {"comparable screen candidate", "shared component candidate", "UI source candidate"} for item in ranked)
    if explicit_ui:
        discovered_surface = True
    return {
        "selected": True,
        "state": "planning-hypothesis",
        "surface_status": "discovered" if discovered_surface else "not-discovered",
        "candidates": selected[:10],
        "explicit_ui_paths": explicit_ui,
        "evidence_boundary": "Repository path inventory only. Files are inspection candidates until approval and source inspection confirm the implementation boundary.",
    }


def refine_impacted(
    goal: str,
    changed: list[str],
    prior: list[dict[str, Any]],
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    """Replace generic backend guesses with UI evidence for UI-first requests."""
    keep_backend = any(_contains(goal, term) for term in BACKEND_TERMS)
    result: list[dict[str, Any]] = []
    if changed:
        for item in prior:
            path = str(item.get("path", ""))
            if path in changed or _role(path) != "non-ui" or keep_backend:
                result.append(item)
    elif keep_backend:
        result.extend(prior)
    for item in profile.get("candidates", []):
        path, role = str(item.get("path", "")), str(item.get("role", "UI candidate"))
        if not path or any(str(existing.get("path", "")) == path for existing in result):
            continue
        authority = "focused proof candidate" if role == "UI evidence" else "inspect first; edit only if the approved UI path requires it"
        result.append({"path": path, "reason": f"{role}; {authority}"})
    return result[:12]


def _requested_ui_surface(statement: str) -> str:
    """Return a bounded user-named UI surface without inventing product terms."""
    match = re.search(
        r"\b(?:from|in|on)\s+(?:the\s+)?([^.;]{1,80}?\b(?:page|screen|view|dialog))\b",
        statement,
        flags=re.IGNORECASE,
    )
    return match.group(1).strip() if match else "requested UI surface"


def _requirement_contract(statement: str, quoted_literals: list[str] | None = None) -> dict[str, Any]:
    lowered = statement.lower()
    if (
        any(_contains(lowered, action) for action in ("remove", "hide", "dismiss", "suppress"))
        and (
            any(_contains(lowered, surface) for surface in ("banner", "toast", "alert"))
            or (
                any(_contains(lowered, surface) for surface in ("message", "warning"))
                and any(_contains(lowered, location) for location in ("page", "screen", "view", "dialog", "ui"))
            )
        )
    ):
        literals = [str(value).strip() for value in (quoted_literals or []) if str(value).strip()]
        named_message = f'"{literals[0]}"' if literals else "named banner or message"
        surface = _requested_ui_surface(statement)
        surface_action = re.sub(r"\s+(?:page|screen|view|dialog)\s*$", "", surface, flags=re.IGNORECASE)
        names_action = bool(re.search(
            r"\b(?:copy|deploy|generate|publish|push|send|submit|validate)\b",
            surface_action,
            flags=re.IGNORECASE,
        ))
        genuine_error_case = (
            "Other genuine deployment errors remain visible."
            if any(term in lowered for term in ("cloudwatch", "deploy", "push to"))
            else "Other genuine errors from the same feature remain visible."
        )
        success_case = (
            f"Successful {surface_action} behavior remains unchanged."
            if names_action
            else f"Successful primary behavior on the {surface} remains unchanged."
        )
        return {
            "outcome": "Do not render the named banner or message on the requested UI surface.",
            "states": "targeted-message absence, successful primary flow, and unrelated error feedback",
            "proof": "page/component proof for targeted absence while preserving the primary flow and other genuine errors",
            "test_cases": [
                f"The exact {named_message} is absent on the {surface}.",
                genuine_error_case,
                success_case,
                "Unrelated warnings and notifications are not suppressed.",
            ],
        }
    if "click" in lowered and "validate" in lowered and any(term in lowered for term in ("move to", "navigate", "advance")):
        return {
            "outcome": "After successful validation, preserve the validation-success message and advance to the requested Validate page or step.",
            "states": "validation success, validation failure, notification visibility, and navigation state",
            "proof": "component interaction proof for success feedback and transition, plus failure no-transition",
        }
    if "click" in lowered and "copy" in lowered and "json" in lowered and any(term in lowered for term in ("move to", "navigate", "advance")):
        return {
            "outcome": "After a successful JSON copy, show the requested copy-success message and advance to Session Summary.",
            "states": "clipboard success, clipboard failure, notification visibility, and navigation state",
            "proof": "component interaction proof for copy feedback and transition, plus failure no-transition",
        }
    if "preserve" in lowered and "generate event flow" in lowered and "transition" in lowered:
        return {
            "outcome": "Preserve the existing Generate Event Flow transition to Event Flow.",
            "states": "successful generation and existing navigation state",
            "proof": "focused preservation assertion for the existing Generate Event Flow transition",
        }
    if "session summary" in lowered:
        return {"outcome": "Render the requested session summary using the established page/card structure.", "states": "populated and absent data", "proof": "focused UI rendering assertion"}
    if "validation status" in lowered:
        return {"outcome": "Expose validation status with semantic text, not color alone.", "states": "pending, valid, invalid, and failure", "proof": "state and accessibility assertions"}
    if "export control" in lowered:
        return {"outcome": "Provide export actions through the existing control pattern.", "states": "enabled, disabled, focus, and export failure", "proof": "interaction and export-result assertions"}
    if "json preview" in lowered:
        return {"outcome": "Render the all-events JSON preview as readable structured content.", "states": "populated, empty, malformed/error, and overflow", "proof": "content, empty/error, and responsive assertions"}
    if "layout" in lowered or "typography" in lowered or "existing ui" in lowered:
        return {"outcome": "Reuse the repository's established UI conventions.", "states": "default, focus, responsive, and accessible interaction", "proof": "baseline UI preservation checks"}
    if "ui library" in lowered:
        return {"outcome": "Keep the approved change dependency-neutral.", "states": "package manifest unchanged unless separately approved", "proof": "manifest diff check"}
    if "unrelated" in lowered and ("screen" in lowered or "redesign" in lowered):
        return {"outcome": "Keep unrelated screens outside the edit boundary.", "states": "unchanged", "proof": "changed-scope reconciliation"}
    return {"outcome": "Render the named page within the existing UI shell.", "states": "default, loading, empty, error, and responsive", "proof": "focused UI and accessibility assertions"}


def build(goal: str, requirements: list[dict[str, Any]], profile: dict[str, Any], selected: bool) -> dict[str, Any]:
    if not selected:
        return {"selected": False, "contracts": [], "candidates": []}
    contracts = []
    for row in requirements:
        contract = _requirement_contract(
            str(row.get("statement", "")),
            [str(value) for value in row.get("quoted_literals", [])],
        )
        contract.setdefault("test_cases", [
            str(contract["outcome"]),
            f"Exercise and prove the applicable states and boundaries: {contract['states']}.",
        ])
        contracts.append({"requirement_id": row.get("display_id", "REQ"), **contract})
    owner_paths = {
        str(path)
        for row in requirements
        if isinstance(row, dict)
        for path in row.get("likely_paths", [])
        if str(path)
    }
    proof_paths = {
        str(path)
        for row in requirements
        if isinstance(row, dict)
        for path in (row.get("scope_evidence", {}) or {}).get("proof_paths", [])
        if str(path)
    }
    scoped_paths = owner_paths | proof_paths
    raw_candidates = list(profile.get("candidates", []))
    known_paths = {str(item.get("path")) for item in raw_candidates if isinstance(item, dict)}
    for path in sorted(scoped_paths - known_paths):
        role = _role(path)
        if role != "non-ui":
            raw_candidates.append({"path": path, "role": role, "score": 100})
    if scoped_paths:
        raw_candidates = [
            item for item in raw_candidates
            if isinstance(item, dict) and str(item.get("path")) in scoped_paths
        ]
    candidates = []
    for raw in raw_candidates:
        item = dict(raw)
        if str(item.get("path")) in owner_paths:
            item["scope_role"] = "implementation owner"
            item["planning_authority"] = "editable only after approval; inspect before the first edit"
        elif str(item.get("path")) in proof_paths:
            item["scope_role"] = "existing requirement-linked proof"
            item["planning_authority"] = "proof-only validation scope; run unchanged or edit after this exact plan is approved, only when the approved validation contract requires assertions"
        elif item.get("role") == "UI evidence":
            item["planning_authority"] = "existing proof convention only; relationship to this requirement is not yet proven"
        else:
            item["planning_authority"] = "inspection candidate only; not editable scope"
        candidates.append(item)
    return {
        **profile,
        "selected": True,
        "candidates": candidates,
        "contracts": contracts,
        "reuse_boundary": "Reuse existing layout, spacing, typography, color tokens, shared controls, breakpoints, accessibility, and interaction-state conventions before adding a new pattern.",
        "dependency_boundary": "Do not introduce a UI library, font, global token set, or parallel visual system without separate approval.",
        "edit_boundary": "Comparable screens, tokens, components, guidance, and tests are inspection candidates; they are not automatic edit targets.",
        "post_change_checks": [
            "Map every changed UI path to an approved requirement ID and reconcile unexpected files as drift.",
            "Verify default, loading, empty, error, focus, and responsive behavior where each state applies.",
            "Run project-owned UI/accessibility proof; do not add a browser or visual-test dependency merely to satisfy the plan.",
            "Confirm unrelated screens and the package manifest remain unchanged unless separately approved.",
        ],
    }


def apply_contracts(requirements: list[dict[str, Any]], plan: dict[str, Any]) -> None:
    if not plan.get("selected"):
        return
    by_id = {str(item.get("requirement_id")): item for item in plan.get("contracts", [])}
    for row in requirements:
        contract = by_id.get(str(row.get("display_id")))
        if not contract:
            continue
        row["ui_contract"] = {
            "surface_status": plan.get("surface_status"),
            "outcome": contract["outcome"],
            "required_states": contract["states"],
            "proof": contract["proof"],
            "test_cases": list(contract.get("test_cases", [])),
            "reuse_boundary": plan.get("reuse_boundary"),
        }
        row["acceptance_criteria"] = list(dict.fromkeys([
            contract["outcome"],
            f"Applicable states are proven: {contract['states']}.",
            *contract.get("test_cases", []),
        ]))
        validation = dict(row.get("validation_contract", {}))
        tiers = [
            tier for tier in validation.get("tiers", [])
            if tier in {"contract", "e2e", "infrastructure", "integration", "release-smoke"}
        ]
        if "component" not in tiers:
            tiers.insert(0, "component")
        validation.update({"state": "required", "tiers": tiers})
        row["validation_contract"] = validation


def contract_lines(plan: dict[str, Any], responsive: bool = False) -> list[str]:
    """Render the approval-critical UI contract without audit inventory noise."""
    if not plan.get("selected"):
        return []
    status = str(plan.get("surface_status", "not-discovered"))
    lines = [
        "", "## Requirement-to-UI contract", "",
        f"- UI implementation surface: **{status}**.",
        f"- Reuse boundary: {plan.get('reuse_boundary')}",
        f"- Edit boundary: {plan.get('edit_boundary')}",
        "",
    ]
    if responsive:
        for item in plan.get("contracts", []):
            lines.extend([
                f"- **{item.get('requirement_id')}**",
                f"  - **Observable outcome:** {item.get('outcome')}",
                f"  - **States / boundaries:** {item.get('states')}",
                f"  - **Required proof:** {item.get('proof')}",
            ])
    else:
        lines.extend([
            "| Requirement | Observable UI outcome | States / boundaries | Required proof |",
            "| --- | --- | --- | --- |",
        ])
        for item in plan.get("contracts", []):
            values = [item.get("requirement_id"), item.get("outcome"), item.get("states"), item.get("proof")]
            lines.append("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", " ") for value in values) + " |")
    return lines


def audit_lines(plan: dict[str, Any], responsive: bool = False) -> list[str]:
    """Render supporting UI discovery and post-change audit detail."""
    if not plan.get("selected"):
        return []
    lines = ["", "## UI consistency details", "", "### UI discovery inventory", ""]
    if responsive:
        for item in plan.get("candidates", []):
            role = item.get("scope_role") or item.get("role")
            authority = item.get("planning_authority") or "inspection candidate only; not editable scope"
            lines.extend([
                f"- **`{item.get('path')}`**",
                f"  - **Role:** {role}",
                f"  - **Planning authority:** {authority}",
            ])
        if not plan.get("candidates"):
            lines.extend([
                "- **Not discovered**",
                "  - **Role:** No repository-owned UI source, convention, or test path was found.",
                "  - **Planning authority:** Confirm a UI root or approve bounded discovery before implementation.",
            ])
    else:
        lines.extend(["| Path | Role | Planning authority |", "| --- | --- | --- |"])
        for item in plan.get("candidates", []):
            role = item.get("scope_role") or item.get("role")
            authority = item.get("planning_authority") or "inspection candidate only; not editable scope"
            lines.append(f"| `{item.get('path')}` | {role} | {authority} |")
        if not plan.get("candidates"):
            lines.append("| not discovered | No repository-owned UI source, convention, or test path was found. | Confirm a UI root or approve bounded discovery before implementation. |")
    lines.extend(["", "### Post-change UI checks", ""])
    lines.extend(f"{index}. {item}" for index, item in enumerate(plan.get("post_change_checks", []), 1))
    return lines


def markdown_lines(plan: dict[str, Any], detailed: bool, responsive: bool = False) -> list[str]:
    """Compatibility composition of the decision contract and optional audit detail."""
    lines = contract_lines(plan, responsive=responsive)
    if detailed and lines:
        lines.extend(audit_lines(plan, responsive=responsive))
    return lines
