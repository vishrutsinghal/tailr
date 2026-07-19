#!/usr/bin/env python3
"""Surface-area profiles for TailTrail installers (BL-8).

Core is a deliberately small subset that supports first-run experience:
install -> hello -> start -> guard check -> governance check.
Extended is Core plus every other file currently shipped.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CORE_FILES: tuple[str, ...] = (
    ".cursor/rules/tailtrail.mdc",
    ".github/copilot-instructions.md",
    ".openai/chatgpt-instructions.md",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "GOVERNANCE.md",
    "GUARDRAILS.md",
    "QUICKSTART.md",
    "README.md",
    "ROADMAP.md",
    "TAILTRAIL-COMMANDS.md",
    "pyproject.toml",
    "tailtrail-policy.example.md",
    "tailtrail-registry.json",
    "tailtrail-registry.schema.json",
    "tailtrail_cli.py",
)

CORE_DIRS: tuple[str, ...] = (
    "adapters",
)

CORE_SCRIPTS: tuple[str, ...] = (
    "scripts/bootstrap-snapshot.py",
    "scripts/check-tailtrail.py",
    "scripts/expand-intent.py",
    "scripts/guardrail-check.py",
    "scripts/install-copilot.py",
    "scripts/install-launcher.py",
    "scripts/install-local.py",
    "scripts/install_surfaces.py",
    "scripts/navigator.py",
    "scripts/navigator_core.py",
    "scripts/navigator_render.py",
    "scripts/policy-check.py",
    "scripts/prompt_profile.py",
    "scripts/route-context.py",
    "scripts/sync-adapters.py",
    "scripts/sync-governance.py",
    "scripts/tailtrail-registry.py",
    "scripts/tailtrail.py",
    "scripts/task-start.py",
    "scripts/token_budget_coach.py",
)

CORE_CONTEXT: tuple[str, ...] = (
    "context/TailTrail.map.md",
    "context/guardrail-layers.md",
    "context/intent-aliases.md",
    "context/slices.md",
    "context/token-router.md",
)

CORE_TEMPLATES: tuple[str, ...] = (
    "templates/intent-overrides.json",
)

SURFACES = ("core", "extended")
DEFAULT_SURFACE = "extended"


def core_file_set() -> set[str]:
    return set(CORE_FILES) | set(CORE_CONTEXT) | set(CORE_TEMPLATES)


def registry_surface_entries(surface: str) -> dict[str, set[str]]:
    path = ROOT / "tailtrail-registry.json"
    if not path.is_file():
        return {"files": set(), "scripts": set()}
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"files": set(), "scripts": set()}
    files: set[str] = set()
    scripts: set[str] = set()
    for feature in registry.get("features", []):
        if not isinstance(feature, dict):
            continue
        if feature.get("status") != "implemented" or feature.get("surface") != surface:
            continue
        files.update(item for item in feature.get("docs", []) if isinstance(item, str))
        scripts.update(item for item in feature.get("scripts", []) if isinstance(item, str))
    if surface == "core":
        files.update({"tailtrail-registry.json", "tailtrail-registry.schema.json"})
        scripts.add("scripts/tailtrail-registry.py")
    return {"files": files, "scripts": scripts}


def resolve(surface: str, extended_files, extended_dirs, extended_scripts):
    """Return the (files, dirs, scripts) tuple for the requested surface.

    Extended reproduces the caller's full lists byte-for-byte.
    Core is a strict subset intersected with the caller's lists so upstream
    additions to the extended manifest never leak into Core.
    """
    if surface == "extended":
        return extended_files, extended_dirs, extended_scripts
    if surface == "core":
        registry_entries = registry_surface_entries("core")
        core_files = core_file_set() | registry_entries["files"]
        core_scripts = set(CORE_SCRIPTS) | registry_entries["scripts"]
        files = tuple(sorted({p for p in extended_files if p in core_files} | registry_entries["files"]))
        dirs = tuple(p for p in extended_dirs if p in CORE_DIRS)
        scripts = tuple(sorted({p for p in extended_scripts if p in core_scripts} | registry_entries["scripts"]))
        return files, dirs, scripts
    raise ValueError(f"Unknown surface: {surface}")
