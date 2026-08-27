#!/usr/bin/env python3
"""Read-only discovery of a repository's existing UI system."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


IGNORED_DIRS = {".git", ".tailtrail", ".video-tools", "node_modules", "dist", "build", "coverage", ".next", "__pycache__", "venv", ".venv"}
STYLE_SUFFIXES = {".css", ".scss", ".sass", ".less"}
COMPONENT_SUFFIXES = {".jsx", ".tsx", ".vue", ".svelte"}
SCREEN_SUFFIXES = COMPONENT_SUFFIXES | {".html"}
COMPONENT_DIR_NAMES = {"components", "component", "ui", "widgets", "shared"}
SCREEN_DIR_NAMES = {"pages", "screens", "views", "routes", "app"}
STYLE_DIR_NAMES = {"styles", "style", "theme", "themes", "tokens", "design-system"}


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            yield path


def limited(values: Iterable[str], limit: int = 12) -> list[str]:
    return sorted(dict.fromkeys(values))[:limit]


def package_evidence(root: Path) -> list[str]:
    package = root / "package.json"
    if not package.is_file():
        return []
    try:
        payload = json.loads(package.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ["package.json (present but not parseable)"]
    dependencies: dict[str, object] = {}
    for field in ("dependencies", "devDependencies", "peerDependencies"):
        value = payload.get(field, {})
        if isinstance(value, dict):
            dependencies.update(value)
    known = ("react", "next", "vue", "nuxt", "@angular", "svelte", "tailwind", "@mui", "antd", "chakra", "storybook", "playwright", "cypress")
    return [name for name in sorted(dependencies) if any(marker in name.lower() for marker in known)]


def discover(root: Path, changed: list[str]) -> dict[str, object]:
    components: list[str] = []
    screens: list[str] = []
    styles: list[str] = []
    visual_tests: list[str] = []
    for path in files(root):
        rel = relative(root, path)
        parts = {part.lower() for part in path.relative_to(root).parts}
        suffix = path.suffix.lower()
        name = path.name.lower()
        if suffix in COMPONENT_SUFFIXES and parts & COMPONENT_DIR_NAMES:
            components.append(rel)
        if suffix in SCREEN_SUFFIXES and (parts & SCREEN_DIR_NAMES or "ui" in parts):
            screens.append(rel)
        if suffix in STYLE_SUFFIXES or parts & STYLE_DIR_NAMES or name in {"tailwind.config.js", "tailwind.config.ts", "theme.ts", "theme.js", "tokens.json", "design-tokens.json"}:
            styles.append(rel)
        if (
            "storybook" in rel.lower()
            or "playwright" in rel.lower()
            or "cypress" in rel.lower()
            or "visual" in rel.lower()
            or ("tests/ui/" in rel.lower() and (name.startswith("test_") or ".test." in name or ".spec." in name))
            or "accessibility" in rel.lower()
            or "a11y" in rel.lower()
        ):
            visual_tests.append(rel)
    surface_status = "discovered" if components or screens or styles else "not-discovered"
    return {
        "type": "tailtrail-ui-consistency-profile",
        "root": root.as_posix(),
        "changed_paths": changed,
        "surface_status": surface_status,
        "shared_component_candidates": limited(components),
        "similar_screen_candidates": limited(screens),
        "style_and_token_candidates": limited(styles),
        "package_evidence": package_evidence(root),
        "visual_test_candidates": limited(visual_tests),
        "preservation_boundary": [
            "Reuse existing shared components, styles, tokens, and layout conventions before adding new patterns.",
            "Preserve the spacing/grid, typography, colors/theme, responsive breakpoints, accessibility states, and interaction conventions already present.",
            "Do not add a UI library, font, global token set, or unrelated redesign unless the approved requirement and existing system make it necessary.",
        ],
        "evidence_limit": "Local repository-structure and manifest evidence only; this does not prove pixel-level equivalence. Use an existing project-owned visual test when available.",
    }


def markdown(profile: dict[str, object]) -> str:
    lines = ["# TailTrail UI Consistency Profile", "", "Read-only local discovery. No files were changed.", "", f"- UI implementation surface: **{profile.get('surface_status', 'not-discovered')}**.", ""]
    for heading, key in (("Shared component candidates", "shared_component_candidates"), ("Comparable screen candidates", "similar_screen_candidates"), ("Style / token candidates", "style_and_token_candidates"), ("Frontend package evidence", "package_evidence"), ("Existing visual-test candidates", "visual_test_candidates")):
        values = profile[key]
        lines.extend([f"## {heading}", ""])
        lines.extend([f"- `{value}`" for value in values] if isinstance(values, list) and values else ["- None found by this local structural pass."])
        lines.append("")
    lines.extend(["## Required preservation boundary", ""])
    lines.extend(f"- {item}" for item in profile["preservation_boundary"])
    lines.extend(["", "## Evidence limit", "", f"- {profile['evidence_limit']}", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover existing repository UI conventions without changing files.")
    parser.add_argument("action", choices=("discover",))
    parser.add_argument("--root", default=".")
    parser.add_argument("--changed", action="append", default=[])
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        parser.error(f"root does not exist: {root}")
    profile = discover(root, args.changed)
    print(json.dumps(profile, indent=2, sort_keys=True) if args.format == "json" else markdown(profile), end="" if args.format == "markdown" else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
