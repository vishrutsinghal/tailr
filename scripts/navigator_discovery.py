"""Deterministic local discovery helpers used by the Navigator.

This module intentionally owns only filesystem, Git, and local graph discovery.
It does not classify a task or decide a workflow, keeping Navigator policy in
``navigator.py`` while making discovery independently testable.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import navigator_core as core


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
MAX_REVIEW_GRAPH_ARGUMENT_CHARS = 8_000
MAX_REVIEW_GRAPH_CHANGED_PATHS = 50
GOAL_DISCOVERY_SUFFIXES = {".cs", ".css", ".go", ".html", ".java", ".js", ".jsx", ".kt", ".py", ".rb", ".rs", ".scss", ".svelte", ".ts", ".tsx", ".vue"}
GOAL_DISCOVERY_STOP_WORDS = {"add", "and", "bug", "code", "defect", "fix", "focused", "for", "the", "this", "validation", "with"}
GOAL_DISCOVERY_EXCLUDED_PARTS = {".git", ".tailtrail", ".venv", "__pycache__", "build", "dist", "node_modules", "tailtrail", "venv"}
REPOSITORY_DISCOVERY_MANIFESTS = {"package.json", "pyproject.toml", "pom.xml", "build.gradle", "build.gradle.kts", "go.mod", "cargo.toml", "composer.json", "gemfile"}
REPOSITORY_DISCOVERY_EXCLUDED_NAMES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock"}
TAILTRAIL_MANAGED_PATH_PREFIXES = (".tailtrail/", "tailtrail/", "skills/tailtrail", "skills/tailtrail-review", "skills/tailtrail-start", ".codex-plugin/", ".github/copilot-instructions.md", ".github/prompts/tailtrail-", ".cursor/rules/tailtrail", ".openai/chatgpt-instructions.md", ".claude/commands/tailtrail", "AGENTS.md", "AIDLC.md", "GUARDRAILS.md", "DEPENDENCY-GATE.md", "TAILTRAIL-COMMANDS.md", "TOKEN-AUTOPILOT.md", "TOKEN-SLICER.md")


def is_actionable_changed_path(root: Path, path: str) -> bool:
    relative = Path(path)
    if "__pycache__" in relative.parts:
        return False
    posix = relative.as_posix()
    if any(posix == prefix.rstrip("/") or posix.startswith(prefix) for prefix in TAILTRAIL_MANAGED_PATH_PREFIXES):
        return False
    return not (relative.parts and (root / relative.parts[0] / ".tailtrail-install.json").is_file())


def git_changed(root: Path) -> list[str]:
    result = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return []
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=root, text=True, capture_output=True, check=False)
    if untracked.returncode == 0:
        files.extend(line.strip() for line in untracked.stdout.splitlines() if line.strip())
    return sorted(dict.fromkeys(path for path in files if is_actionable_changed_path(root, path)))


def goal_discovery_terms(goal: str) -> list[str]:
    terms: list[str] = []
    for term in re.findall(r"[a-zA-Z][a-zA-Z0-9_]{2,}", goal.lower()):
        if term not in GOAL_DISCOVERY_STOP_WORDS and term not in terms:
            terms.append(term)
    return terms[:6]


def _candidates(root: Path) -> list[Path]:
    try:
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


def goal_discovered_paths(root: Path, goal: str, limit: int = 2) -> list[str]:
    terms = goal_discovery_terms(goal)
    if not terms:
        return []
    ranked: list[tuple[int, str]] = []
    for path in _candidates(root):
        if not path.is_file() or path.suffix.lower() not in GOAL_DISCOVERY_SUFFIXES:
            continue
        try:
            relative = path.relative_to(root)
            if any(part.lower() in GOAL_DISCOVERY_EXCLUDED_PARTS for part in relative.parts):
                continue
            body = path.read_text(encoding="utf-8", errors="ignore")[:131_072].lower()
        except (OSError, ValueError):
            continue
        relative_text, parts = relative.as_posix().lower(), {part.lower() for part in relative.parts}
        score = (12 if "src" in parts else 0) + (9 if any(part in {"test", "tests"} for part in parts) else 0)
        for term in terms:
            score += 10 if term in relative_text else 0
            score += 4 if term in body else 0
        if "validation" in goal.lower() and "validation" in relative_text:
            score += 8
        if "validation" in goal.lower() and any(part in {"test", "tests"} for part in parts):
            score += 5
        if score >= 14:
            ranked.append((score, relative.as_posix()))
    return [path for _, path in sorted(ranked, key=lambda item: (-item[0], item[1]))[:limit]]


def repository_discovered_paths(root: Path, goal: str, limit: int = 5) -> list[str]:
    ui_requested, terms, ranked = core.ui_change_requested(goal, []), goal_discovery_terms(goal), []
    for path in _candidates(root):
        if not path.is_file():
            continue
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if any(part.lower() in GOAL_DISCOVERY_EXCLUDED_PARTS for part in relative.parts):
            continue
        name, suffix = relative.name.lower(), relative.suffix.lower()
        manifest = name in REPOSITORY_DISCOVERY_MANIFESTS
        if name in REPOSITORY_DISCOVERY_EXCLUDED_NAMES or (suffix not in GOAL_DISCOVERY_SUFFIXES and not manifest):
            continue
        parts, relative_text = {part.lower() for part in relative.parts}, relative.as_posix().lower()
        score = (20 if manifest else 0) + (12 if "src" in parts or "app" in parts else 0) + (8 if any(part in {"test", "tests", "__tests__"} for part in parts) else 0)
        if ui_requested:
            score += 22 if suffix in {".jsx", ".tsx", ".vue", ".svelte", ".css", ".scss", ".html"} else 0
            score += 16 if any(part in core.UI_PATH_PARTS for part in parts) else 0
        score += sum(5 for term in terms if term in relative_text)
        if score:
            ranked.append((score, relative.as_posix()))
    return [path for _, path in sorted(ranked, key=lambda item: (-item[0], item[1]))[:limit]]


def bounded_review_graph_paths(changed: list[str]) -> list[str]:
    selected: list[str] = []
    argument_chars = 0
    for path in changed:
        next_chars = len("--changed") + len(path) + 2
        if len(selected) >= MAX_REVIEW_GRAPH_CHANGED_PATHS or argument_chars + next_chars > MAX_REVIEW_GRAPH_ARGUMENT_CHARS:
            break
        selected.append(path)
        argument_chars += next_chars
    return selected


def run_review_graph(root: Path, changed: list[str]) -> dict[str, Any] | None:
    graph_paths = bounded_review_graph_paths(changed)
    if not graph_paths:
        return None
    command = [PYTHON, (ROOT / "scripts" / "review-graph.py").as_posix(), "--root", root.as_posix(), "--format", "json"]
    for item in graph_paths:
        command.extend(["--changed", item])
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    try:
        return json.loads(result.stdout) if result.returncode == 0 else None
    except json.JSONDecodeError:
        return None


def run_graph_learning(root: Path, changed: list[str], tasks: list[str], risks: list[str]) -> dict[str, Any] | None:
    if not ((root / ".tailtrail" / "learning-index.md").exists() or (root / ".tailtrail" / "graph-learning-index.json").exists()):
        return None
    tags = sorted(set(tasks + [risk.replace("/", "-").replace(" ", "-") for risk in risks]))
    command = [PYTHON, (ROOT / "scripts" / "graph-learning.py").as_posix(), "search", "--root", root.as_posix(), "--format", "json", "--limit", "3"]
    for item in changed[:5]:
        command.extend(["--changed", item])
    if tags:
        command.extend(["--tags", ",".join(tags)])
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    try:
        value = json.loads(result.stdout) if result.returncode == 0 else None
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None
