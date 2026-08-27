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
        or any(marker in name for marker in ("accessibility", "a11y", "visual"))
    )
    if parts & TEST_PARTS and is_test_file and (
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


def _requirement_contract(statement: str) -> dict[str, Any]:
    lowered = statement.lower()
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
        contract = _requirement_contract(str(row.get("statement", "")))
        contracts.append({"requirement_id": row.get("display_id", "REQ"), **contract})
    return {
        **profile,
        "selected": True,
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
            "reuse_boundary": plan.get("reuse_boundary"),
        }
        row["acceptance_criteria"] = [contract["outcome"], f"Applicable states are proven: {contract['states']}." ]
        validation = dict(row.get("validation_contract", {}))
        tiers = [
            tier for tier in validation.get("tiers", [])
            if tier in {"contract", "e2e", "infrastructure", "integration", "release-smoke"}
        ]
        if "component" not in tiers:
            tiers.insert(0, "component")
        row["validation_contract"] = {"state": "required", "tiers": tiers}


def markdown_lines(plan: dict[str, Any], detailed: bool) -> list[str]:
    if not plan.get("selected"):
        return []
    status = str(plan.get("surface_status", "not-discovered"))
    lines = [
        "", "## UI Consistency Plan", "",
        f"- UI implementation surface: **{status}**.",
        f"- Reuse boundary: {plan.get('reuse_boundary')}",
        f"- Edit boundary: {plan.get('edit_boundary')}",
        "", "### Requirement-to-UI contract", "",
        "| Requirement | Observable UI outcome | States / boundaries | Required proof |",
        "| --- | --- | --- | --- |",
    ]
    for item in plan.get("contracts", []):
        values = [item.get("requirement_id"), item.get("outcome"), item.get("states"), item.get("proof")]
        lines.append("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", " ") for value in values) + " |")
    if detailed:
        lines.extend(["", "### UI discovery inventory", "", "| Path | Role | Planning authority |", "| --- | --- | --- |"])
        for item in plan.get("candidates", []):
            authority = "inspect first; edit only when requirement mapping confirms it"
            if item.get("role") == "UI evidence":
                authority = "baseline/focused proof candidate after approval"
            lines.append(f"| `{item.get('path')}` | {item.get('role')} | {authority} |")
        if not plan.get("candidates"):
            lines.append("| not discovered | No repository-owned UI source, convention, or test path was found. | Confirm a UI root or approve bounded discovery before implementation. |")
        lines.extend(["", "### Post-change UI checks", ""])
        lines.extend(f"{index}. {item}" for index, item in enumerate(plan.get("post_change_checks", []), 1))
    return lines
