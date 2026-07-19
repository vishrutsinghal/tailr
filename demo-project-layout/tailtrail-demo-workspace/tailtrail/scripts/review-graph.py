#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".tailtrail",
    "__pycache__",
    "aidlc-rules",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    "coverage",
    ".next",
    ".nuxt",
    ".venv",
    "venv",
}

SOURCE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".md",
    ".mjs",
    ".py",
    ".rb",
    ".rs",
    ".scala",
    ".sh",
    ".sql",
    ".swift",
    ".ts",
    ".tsx",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
}

MANIFEST_NAMES = {
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "requirements.txt",
    "pyproject.toml",
    "poetry.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "go.mod",
    "go.sum",
    "Cargo.toml",
    "Cargo.lock",
    "Gemfile",
    "Gemfile.lock",
    "Dockerfile",
}

CONFIG_NAMES = {
    ".github",
    ".gitlab-ci.yml",
    "Jenkinsfile",
    "sonar-project.properties",
    "tsconfig.json",
    "eslint.config.js",
    ".eslintrc",
    "pytest.ini",
    "tox.ini",
}

TEST_PARTS = {"test", "tests", "__tests__", "spec", "specs"}
SHARED_PARTS = {"shared", "common", "util", "utils", "helper", "helpers", "lib", "core"}
RISK_TERMS = {
    "auth": "auth-sensitive path",
    "authorization": "authorization-sensitive path",
    "permission": "permission-sensitive path",
    "validation": "validation path",
    "validator": "validation path",
    "security": "security-sensitive path",
    "password": "credential-sensitive path",
    "token": "token-sensitive path",
    "payment": "payment-sensitive path",
    "migration": "data migration path",
    "schema": "data shape path",
    "sonar": "CI/Sonar path",
    "workflow": "CI workflow path",
    "pipeline": "CI pipeline path",
}

IMPORT_PATTERNS = [
    re.compile(r"^\s*from\s+([\w.]+)\s+import\s+", re.MULTILINE),
    re.compile(r"^\s*import\s+([\w.]+)", re.MULTILINE),
    re.compile(r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"),
    re.compile(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)"),
    re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE),
    re.compile(r"^\s*using\s+([\w.]+)\s*;", re.MULTILINE),
]


def relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def is_skipped(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def is_text_candidate(path: Path) -> bool:
    return path.is_file() and not is_skipped(path) and (path.suffix in SOURCE_EXTENSIONS or path.name in MANIFEST_NAMES)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def list_candidates(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if is_text_candidate(path))


def git_changed(root: Path) -> list[str]:
    command = ["git", "diff", "--name-only", "HEAD"]
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def normalize_changed(root: Path, changed: list[str]) -> list[Path]:
    paths: list[Path] = []
    for item in changed:
        path = (root / item).resolve()
        if path.exists() and path.is_file() and root.resolve() in path.parents:
            paths.append(path)
    return sorted(set(paths))


def tokens_for(path: Path, root: Path) -> set[str]:
    rel = relative(path, root)
    stem = path.stem
    no_ext = rel[: -len(path.suffix)] if path.suffix else rel
    dotted = no_ext.replace("/", ".")
    slash = no_ext
    kebab = stem.replace("_", "-")
    snake = stem.replace("-", "_")
    return {token for token in {rel, path.name, stem, dotted, slash, kebab, snake} if len(token) >= 3}


def extract_imports(path: Path) -> set[str]:
    body = read_text(path)
    imports: set[str] = set()
    for pattern in IMPORT_PATTERNS:
        imports.update(match.group(1) for match in pattern.finditer(body))
    return {item for item in imports if item and not item.startswith(".")}


def looks_like_test(path: Path) -> bool:
    lowered_name = path.name.lower()
    lowered_parts = {part.lower() for part in path.parts}
    return bool(TEST_PARTS & lowered_parts) or lowered_name.startswith("test_") or lowered_name.endswith(("_test.py", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", ".test.js", ".spec.js"))


def looks_shared(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    return bool(SHARED_PARTS & parts)


def risk_tags(path: Path, body: str) -> list[str]:
    del body
    haystack = path.as_posix().lower()
    tags = {label for term, label in RISK_TERMS.items() if term in haystack}
    if path.name in MANIFEST_NAMES:
        tags.add("dependency/config manifest")
    if ".github" in path.parts or path.name in CONFIG_NAMES:
        tags.add("CI/config path")
    if looks_like_test(path):
        tags.add("test path")
    if looks_shared(path):
        tags.add("shared helper path")
    return sorted(tags)


def find_likely_tests(changed: Path, candidates: list[Path], root: Path, limit: int) -> list[dict[str, str]]:
    changed_tokens = tokens_for(changed, root)
    changed_stem = changed.stem.lower().replace("test_", "")
    matches: list[dict[str, str]] = []
    for path in candidates:
        if path == changed or not looks_like_test(path):
            continue
        rel = relative(path, root)
        lowered = rel.lower()
        reason = ""
        if changed_stem and changed_stem in lowered:
            reason = "test name/path matches changed file"
        elif any(token.lower() in lowered for token in changed_tokens):
            reason = "test path references changed file token"
        else:
            body = read_text(path).lower()
            if any(token.lower() in body for token in changed_tokens):
                reason = "test content references changed file token"
        if reason:
            matches.append({"path": rel, "reason": reason})
    return matches[:limit]


def find_likely_callers(changed: Path, candidates: list[Path], root: Path, limit: int) -> list[dict[str, str]]:
    changed_tokens = tokens_for(changed, root)
    matches: list[dict[str, str]] = []
    for path in candidates:
        if path == changed or looks_like_test(path):
            continue
        body = read_text(path)
        if not body:
            continue
        lowered = body.lower()
        reason = ""
        if any(token.lower() in lowered for token in changed_tokens):
            reason = "text/import reference to changed file token"
        if reason:
            matches.append({"path": relative(path, root), "reason": reason})
    return matches[:limit]


def find_related_helpers(changed: Path, candidates: list[Path], root: Path, limit: int) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    for path in candidates:
        if path == changed or not looks_shared(path):
            continue
        rel = relative(path, root)
        body = read_text(path).lower()
        if any(part.lower() in body for part in changed.parts if len(part) > 3):
            matches.append({"path": rel, "reason": "shared helper references changed path token"})
    return matches[:limit]


def nearby_manifests(root: Path, changed_files: list[Path]) -> list[dict[str, str]]:
    found: dict[str, str] = {}
    for changed in changed_files:
        for parent in [changed.parent, *changed.parents]:
            if root.resolve() not in parent.resolve().parents and parent.resolve() != root.resolve():
                continue
            for name in MANIFEST_NAMES:
                candidate = parent / name
                if candidate.is_file():
                    found[relative(candidate, root)] = "near changed file"
            if parent == root:
                break
    return [{"path": path, "reason": reason} for path, reason in sorted(found.items())]


def graph(root: Path, changed_items: list[str], limit: int) -> dict[str, Any]:
    changed_files = normalize_changed(root, changed_items or git_changed(root))
    candidates = list_candidates(root)
    per_file = []
    all_risks: set[str] = set()
    read_order: list[str] = []

    for changed in changed_files:
        body = read_text(changed)
        risks = risk_tags(changed, body)
        all_risks.update(risks)
        tests = find_likely_tests(changed, candidates, root, limit)
        callers = find_likely_callers(changed, candidates, root, limit)
        helpers = find_related_helpers(changed, candidates, root, limit)
        rel = relative(changed, root)
        per_file.append({
            "path": rel,
            "risks": risks,
            "imports": sorted(extract_imports(changed))[:limit],
            "likely_tests": tests,
            "likely_callers": callers,
            "related_helpers": helpers,
        })
        read_order.append(rel)
        read_order.extend(item["path"] for item in tests[:2])
        read_order.extend(item["path"] for item in callers[:3])
        read_order.extend(item["path"] for item in helpers[:2])

    manifests = nearby_manifests(root, changed_files)
    read_order.extend(item["path"] for item in manifests[:3])
    compact_order = list(dict.fromkeys(read_order))

    return {
        "root": root.as_posix(),
        "changed": [relative(path, root) for path in changed_files],
        "review_note": "This is an explainable impact map, not a complete call graph. Review suggested files before relying on it.",
        "signals": [
            "imports",
            "file naming conventions",
            "test proximity",
            "local text search",
            "manifest/config proximity",
        ],
        "future_candidates_not_used": [
            "full AST engine",
            "semantic vector database",
            "background indexing service",
        ],
        "files": per_file,
        "nearby_manifests": manifests,
        "risks": sorted(all_risks),
        "suggested_read_order": compact_order[: limit * 4],
    }


def markdown(data: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Code Review Graph Lite",
        "",
        data["review_note"],
        "",
        "## Changed Files",
        "",
    ]
    if data["changed"]:
        lines.extend(f"- `{path}`" for path in data["changed"])
    else:
        lines.append("- No changed files detected. Pass `--changed path/to/file` or run from a git worktree with changes.")

    lines.extend(["", "## Suggested Read Order", ""])
    if data["suggested_read_order"]:
        lines.extend(f"- `{path}`" for path in data["suggested_read_order"])
    else:
        lines.append("- No read order available.")

    lines.extend(["", "## Per-File Impact", ""])
    for item in data["files"]:
        lines.extend([f"### `{item['path']}`", ""])
        lines.append("Risks: " + (", ".join(item["risks"]) if item["risks"] else "none detected"))
        lines.append("")
        lines.append("Likely tests:")
        if item["likely_tests"]:
            lines.extend(f"- `{test['path']}`: {test['reason']}" for test in item["likely_tests"])
        else:
            lines.append("- none detected")
        lines.append("")
        lines.append("Likely callers:")
        if item["likely_callers"]:
            lines.extend(f"- `{caller['path']}`: {caller['reason']}" for caller in item["likely_callers"])
        else:
            lines.append("- none detected")
        lines.append("")
        lines.append("Related shared helpers:")
        if item["related_helpers"]:
            lines.extend(f"- `{helper['path']}`: {helper['reason']}" for helper in item["related_helpers"])
        else:
            lines.append("- none detected")
        lines.append("")
        if item["imports"]:
            lines.append("Import signals:")
            lines.extend(f"- `{import_name}`" for import_name in item["imports"])
            lines.append("")

    lines.extend(["## Nearby Manifests / Config", ""])
    if data["nearby_manifests"]:
        lines.extend(f"- `{item['path']}`: {item['reason']}" for item in data["nearby_manifests"])
    else:
        lines.append("- none detected")

    lines.extend(["", "## Signals Used", ""])
    lines.extend(f"- {signal}" for signal in data["signals"])
    lines.extend(["", "## Future Candidates Not Used In Lite", ""])
    lines.extend(f"- {candidate}" for candidate in data["future_candidates_not_used"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a compact TailTrail review impact graph.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to scan.")
    parser.add_argument("--changed", action="append", default=[], help="Changed file path. Repeat for multiple files.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format.")
    parser.add_argument("--limit", type=int, default=8, help="Maximum matches per section.")
    args = parser.parse_args()

    root = args.root.resolve()
    data = graph(root, args.changed, max(args.limit, 1))
    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        print(markdown(data), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
