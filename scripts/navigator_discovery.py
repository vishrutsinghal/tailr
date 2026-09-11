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
import navigator_scope as scope
import requirement_discovery


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
MAX_REVIEW_GRAPH_ARGUMENT_CHARS = 8_000
MAX_REVIEW_GRAPH_CHANGED_PATHS = 50
GOAL_DISCOVERY_SUFFIXES = {".cs", ".css", ".feature", ".go", ".html", ".java", ".js", ".jsx", ".kt", ".py", ".rb", ".rs", ".scss", ".svelte", ".ts", ".tsx", ".vue"}
GOAL_DISCOVERY_STOP_WORDS = {"add", "all", "and", "are", "bug", "code", "defect", "details", "fix", "focused", "for", "free", "hands", "mode", "refer", "see", "the", "there", "this", "validation", "want", "with"}
GOAL_DISCOVERY_EXCLUDED_PARTS = {".git", ".tailtrail", ".venv", "__pycache__", "build", "dist", "node_modules", "tailtrail", "venv"}
REPOSITORY_DISCOVERY_MANIFESTS = {"package.json", "pyproject.toml", "pom.xml", "build.gradle", "build.gradle.kts", "go.mod", "cargo.toml", "composer.json", "gemfile"}
REPOSITORY_DISCOVERY_EXCLUDED_NAMES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock"}
TAILTRAIL_MANAGED_PATH_PREFIXES = (".tailtrail/", "tailtrail/", "skills/tailtrail", "skills/tailtrail-review", "skills/tailtrail-start", ".codex-plugin/", ".github/copilot-instructions.md", ".github/prompts/tailtrail-", ".cursor/rules/tailtrail", ".openai/chatgpt-instructions.md", ".claude/commands/tailtrail", "AGENTS.md", "AIDLC.md", "GUARDRAILS.md", "DEPENDENCY-GATE.md", "TAILTRAIL-COMMANDS.md", "TOKEN-AUTOPILOT.md", "TOKEN-SLICER.md")


def _literal_value(value: str) -> str:
    """Normalize only presentation wrappers around one literal.

    Markdown emphasis is host presentation, not part of the user-visible text
    that can occur in source.  Keep punctuation and interior characters exact
    while removing balanced wrappers used by the supported chat hosts.
    """
    return requirement_discovery.normalize_quoted_literal(value).casefold()


def _without_inline_presentation(value: str) -> str:
    """Remove balanced inline Markdown wrappers before contextual parsing."""
    return requirement_discovery.normalize_literal_presentation(value)


def exact_goal_phrases(goal: str, canonical_literals: list[str] | tuple[str, ...] | None = None) -> list[str]:
    """Return bounded user-provided literals without inventing search text.

    Canonical requirement literals take precedence over re-parsing a rendered
    prompt.  Raw parsing remains for callers that have not yet created a
    requirement frame and treats common Markdown wrappers equivalently.
    """
    phrases: list[str] = []
    for literal in canonical_literals or ():
        value = _literal_value(str(literal))
        if 4 <= len(value) <= 160 and value not in phrases:
            phrases.append(value)
    if phrases:
        return phrases[:8]
    for pattern in (
        r"`([^`\n]+)`",
        r"\*\*([^*\n]+)\*\*",
        r"__([^_\n]+)__",
        r"(?<!\*)\*(?!\s)([^*\n]*?\S)\*(?!\*)",
        r"(?<!\w)_(?!\s)([^_\n]*?\S)_(?!\w)",
        r"'([^'\n]+)'",
        r'"([^"\n]+)"',
    ):
        for match in re.finditer(pattern, goal):
            value = _literal_value(match.group(1))
            if 4 <= len(value) <= 160 and value not in phrases:
                phrases.append(value)
    contextual_goal = _without_inline_presentation(goal)
    for match in re.finditer(
        r"\b(?:banner|error|message|warning)\b\s*(?:says?|shows?|showing|is|reads?|:|-)?\s*"
        r"([^\n]{4,160}?)(?=\.\s+(?:we|it|this|that|please|remove|since)\b|\n|$)",
        contextual_goal,
        re.IGNORECASE,
    ):
        value = _literal_value(match.group(1).strip(" .'\""))
        if 4 <= len(value) <= 160 and value not in phrases:
            phrases.append(value)
    return phrases[:8]


def exact_phrase_paths(
    root: Path,
    goal: str,
    limit: int = 16,
    canonical_literals: list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Search explicit user-provided literals before filename ranking.

    This is a metadata-only bounded source scan. It records paths and hashes,
    never source bodies. Oversized, generated, managed, and sensitive files are
    excluded by the same scope helpers used by Navigator investigation.
    """
    phrases = exact_goal_phrases(goal, canonical_literals)
    if not phrases:
        return []
    rows: list[tuple[int, str, dict[str, Any]]] = []
    total_bytes = 0
    max_total = max(scope.LIMITS["max_total_read_bytes"], 16 * 1024 * 1024)
    for path in _candidates(root):
        if not path.is_file() or path.suffix.lower() not in GOAL_DISCOVERY_SUFFIXES:
            continue
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            continue
        if any(part.lower() in GOAL_DISCOVERY_EXCLUDED_PARTS for part in Path(relative).parts):
            continue
        body, rejection, content_fingerprint = scope.safe_text(root, relative)
        if rejection or body is None or content_fingerprint is None:
            continue
        total_bytes += len(body.encode("utf-8"))
        if total_bytes > max_total:
            break
        lowered = body.casefold()
        matches = [phrase for phrase in phrases if phrase in lowered]
        if not matches:
            continue
        seed = scope.ScopeSeed(
            path=relative,
            seed_sources=("lexical-body",),
            reason_codes=("exact-phrase-in-bounded-body",),
            matched_terms=tuple(matches),
            score=120 * len(matches),
            content_fingerprint=content_fingerprint,
        ).as_dict()
        rows.append((len(matches), relative, seed))
        if len(rows) >= limit:
            break
    return [row for _, _, row in sorted(rows, key=lambda item: (-item[0], item[1]))]


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
    # Match the 24-term budget callers already apply; a smaller cap here
    # silently dropped later, more specific terms in long/conversational goals.
    return terms[:24]


def _candidates(root: Path) -> list[Path]:
    def eligible(path: Path) -> bool:
        try:
            relative = path.relative_to(root)
        except ValueError:
            return False
        return not any(part.lower() in GOAL_DISCOVERY_EXCLUDED_PARTS for part in relative.parts)

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
                return [
                    path for line in dict.fromkeys(paths)
                    if eligible(path := root / line)
                ][:scope.LIMITS["candidate_files"]]
    except OSError:
        pass
    candidates: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and eligible(path):
            candidates.append(path)
            if len(candidates) >= scope.LIMITS["candidate_files"]:
                break
    return candidates


def goal_discovered_paths(
    root: Path,
    goal: str,
    limit: int = 2,
    query_terms: list[str] | None = None,
    canonical_literals: list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Return weak lexical seeds, never selected implementation paths."""
    exact = exact_phrase_paths(root, goal, limit=limit, canonical_literals=canonical_literals)
    if exact:
        return exact
    terms = list(dict.fromkeys(query_terms or goal_discovery_terms(goal)))[:24]
    exact_phrases = exact_goal_phrases(goal, canonical_literals)
    if not terms:
        return []
    inventory: list[tuple[int, str, Path, set[str]]] = []
    for path in _candidates(root):
        if not path.is_file() or path.suffix.lower() not in GOAL_DISCOVERY_SUFFIXES:
            continue
        try:
            relative = path.relative_to(root)
            if any(part.lower() in GOAL_DISCOVERY_EXCLUDED_PARTS for part in relative.parts):
                continue
        except (OSError, ValueError):
            continue
        relative_text, parts = relative.as_posix().lower(), {part.lower() for part in relative.parts}
        score = (12 if "src" in parts else 0) + (9 if any(part in {"test", "tests"} for part in parts) else 0)
        for term in terms:
            # "test"/"tests" already scored above via path membership; counting
            # them again here just because "test" is a substring of the
            # "tests" directory name manufactures false ties with every file
            # in any test folder, drowning out real path-term signal.
            if term in {"test", "tests"}:
                continue
            score += 10 if term in relative_text else 0
        if "validation" in goal.lower() and "validation" in relative_text:
            score += 8
        if "validation" in goal.lower() and any(part in {"test", "tests"} for part in parts):
            score += 5
        inventory.append((score, relative.as_posix(), path, parts))

    ranked: list[tuple[int, str, dict[str, Any]]] = []
    total_bytes = 0
    # A path-only prefilter cannot discriminate well once many files share the
    # same directory/term signal (e.g. every file under `tests/`); reading only
    # the shared global default (20) then arbitrarily drops most of a tied
    # group in alphabetical order. When the whole candidate pool is small, read
    # all of it instead so real content match still decides; large repos keep
    # a bounded ceiling so this stays cheap.
    read_budget = max(scope.LIMITS["initial_file_reads"], min(len(inventory), 200))
    for path_score, relative, _path, _parts in sorted(inventory, key=lambda item: (-item[0], item[1]))[:read_budget]:
        body, rejection, content_fingerprint = scope.safe_text(root, relative)
        if rejection or body is None:
            continue
        total_bytes += len(body.encode("utf-8"))
        if total_bytes > scope.LIMITS["max_total_read_bytes"]:
            break
        lowered_body = body.lower()
        path_matches = [term for term in terms if term in relative.lower()]
        body_matches = [term for term in terms if term in lowered_body]
        phrase_matches = [phrase for phrase in exact_phrases if phrase in lowered_body]
        score = path_score + 4 * len(body_matches) + 120 * len(phrase_matches)
        if score < 14:
            continue
        sources = []
        reasons = []
        if path_matches:
            sources.append("lexical-path")
            reasons.append("query-term-in-path")
        if body_matches:
            sources.append("lexical-body")
            reasons.append("query-term-in-bounded-body")
        if phrase_matches:
            if "lexical-body" not in sources:
                sources.append("lexical-body")
            reasons.append("exact-phrase-in-bounded-body")
        if not sources:
            continue
        row = scope.ScopeSeed(
            path=relative,
            seed_sources=tuple(sources),
            reason_codes=tuple(reasons),
            matched_terms=tuple(sorted(set(path_matches + body_matches + phrase_matches))),
            score=score,
            content_fingerprint=content_fingerprint,
        ).as_dict()
        ranked.append((score, relative, row))
    return [row for _, _, row in sorted(ranked, key=lambda item: (-item[0], item[1]))[:limit]]


def repository_discovered_paths(root: Path, goal: str, limit: int = 5, query_terms: list[str] | None = None) -> list[dict[str, Any]]:
    """Return repository-structure seeds with explicit, weak provenance."""
    ui_requested = core.ui_change_requested(goal, [])
    terms = list(dict.fromkeys(query_terms or goal_discovery_terms(goal)))[:24]
    ranked: list[tuple[int, str]] = []
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
    return [
        scope.seed(path, "repository-structure", "repository-structure-ranking", score=score)
        for score, path in sorted(ranked, key=lambda item: (-item[0], item[1]))[:limit]
    ]


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
