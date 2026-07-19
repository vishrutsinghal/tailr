#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".tailtrail",
    "__pycache__",
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
    "bin",
    "obj",
}

LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".java": "java",
    ".cs": "dotnet",
    ".sql": "sql",
    ".tf": "terraform",
    ".tfvars": "terraform",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
}

MANIFEST_NAMES = {
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "gradle.properties",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "tox.ini",
    "pytest.ini",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "go.mod",
    "go.sum",
    "sonar-project.properties",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
}

MANIFEST_SUFFIXES = {".csproj", ".sln", ".props", ".targets"}


@dataclass(frozen=True)
class RepoSignal:
    path: str
    exists: bool
    is_repo: bool
    role: str
    relationship: str
    warnings: list[str]
    languages: dict[str, int]
    manifests: list[str]
    sample_files: list[str]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def is_skipped(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def safe_relative(path: Path, root: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def relationship_to_target(path: Path, target: Path) -> str:
    resolved_path = path.resolve()
    resolved_target = target.resolve()
    if resolved_path == resolved_target:
        return "same-as-target"
    try:
        resolved_path.relative_to(resolved_target)
        return "inside-target"
    except ValueError:
        pass
    try:
        resolved_target.relative_to(resolved_path)
        return "contains-target"
    except ValueError:
        pass
    if resolved_path.parent == resolved_target.parent:
        return "sibling"
    return "external"


def collect_signals(path: Path, target: Path, role: str, limit: int) -> RepoSignal:
    resolved = path.resolve()
    warnings: list[str] = []
    if not resolved.exists():
        return RepoSignal(
            path=resolved.as_posix(),
            exists=False,
            is_repo=False,
            role=role,
            relationship="missing",
            warnings=["Path does not exist or is not available to the current workspace."],
            languages={},
            manifests=[],
            sample_files=[],
        )

    if not resolved.is_dir():
        return RepoSignal(
            path=resolved.as_posix(),
            exists=True,
            is_repo=False,
            role=role,
            relationship=relationship_to_target(resolved, target),
            warnings=["Path exists but is not a directory."],
            languages={},
            manifests=[],
            sample_files=[],
        )

    relationship = relationship_to_target(resolved, target)
    if role == "reference" and relationship in {"same-as-target", "inside-target", "contains-target"}:
        warnings.append("Reference path overlaps the target repo; confirm read/write boundaries before using it as reference.")

    is_repo = (resolved / ".git").exists()
    if not is_repo:
        warnings.append("No .git directory detected; this may be a folder, submodule worktree, or restricted path rather than a repo root.")

    languages: dict[str, int] = {}
    manifests: list[str] = []
    sample_files: list[str] = []
    scanned = 0
    for item in resolved.rglob("*"):
        if scanned >= max(limit, 1):
            warnings.append(f"Scan stopped at {limit} files/directories to keep reference planning light.")
            break
        scanned += 1
        if is_skipped(item):
            continue
        if not item.is_file():
            continue
        relative = safe_relative(item, resolved)
        if not relative:
            continue
        language = LANGUAGE_EXTENSIONS.get(item.suffix)
        if language:
            languages[language] = languages.get(language, 0) + 1
            if len(sample_files) < 12:
                sample_files.append(relative)
        if item.name in MANIFEST_NAMES or item.suffix in MANIFEST_SUFFIXES:
            manifests.append(relative)

    return RepoSignal(
        path=resolved.as_posix(),
        exists=True,
        is_repo=is_repo,
        role=role,
        relationship=relationship,
        warnings=warnings,
        languages=dict(sorted(languages.items())),
        manifests=sorted(manifests)[:20],
        sample_files=sample_files,
    )


def reference_name(path: Path) -> str:
    name = path.resolve().name or "reference-repo"
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", name).strip("-") or "reference-repo"


def plan(args: argparse.Namespace) -> dict[str, Any]:
    target = args.target.resolve()
    references = [item.resolve() for item in args.reference]
    target_signal = collect_signals(target, target, "target", args.limit)
    reference_signals = [collect_signals(item, target, "reference", args.limit) for item in references]

    commands: list[str] = []
    for signal in reference_signals:
        if signal.exists and Path(signal.path).is_dir():
            name = reference_name(Path(signal.path))
            commands.append(
                "python3 scripts/tailtrail.py graph map "
                f"--root {json.dumps(signal.path)} "
                f"--cache {json.dumps((target / '.tailtrail' / 'reference-graphs' / f'{name}.json').as_posix())}"
            )

    boundaries = [
        "Only edit files under the target repo.",
        "Treat reference repos as read-only pattern sources.",
        "Do not copy source code verbatim from a reference repo; extract conventions, naming, validation style, tests, and architecture intent.",
        "Inspect exact target source before changing it; reference summaries are not source truth.",
        "If a reference path is unavailable, ask the user to open the parent workspace or provide a compact repo map.",
    ]
    load = [
        "target repo exact files to change",
        "reference repo manifests and compact graph/summary only",
        "matching validation, naming, test, API, dependency, or config patterns",
    ]
    avoid = [
        "editing reference repo files",
        "bulk-loading entire sibling repos",
        "copying implementation code from reference repos",
        "using stale reference summaries without checking freshness",
    ]
    return {
        "type": "tailtrail-cross-repo-reference-plan",
        "generated_at": now_utc(),
        "goal": args.goal,
        "target": target_signal.__dict__,
        "references": [item.__dict__ for item in reference_signals],
        "read_write_boundaries": boundaries,
        "load": load,
        "avoid": avoid,
        "suggested_commands": commands,
        "implementation_plan": [
            "Confirm the target repo and reference repo roles.",
            "Use reference repos only for patterns, not for direct code copying.",
            "Generate or reuse a compact reference graph when repeated cross-repo reads are likely.",
            "Read exact target files and implement the smallest maintainable change.",
            "Validate in the target repo only unless the user explicitly approves broader checks.",
        ],
        "approval": [
            "Review these boundaries before implementation.",
            "Edit the target/reference paths if Navigator guessed incorrectly.",
            "Approve only after the reference repos are confirmed read-only.",
        ],
    }


def markdown(data: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Cross-Repo Reference Plan",
        "",
        "Use this plan when one repo is the implementation target and one or more sibling repos are read-only references.",
        "",
        "## Goal",
        "",
        f"- {data['goal'] or 'not provided'}",
        "",
        "## Target Repo",
        "",
    ]
    target = data["target"]
    lines.extend(
        [
            f"- Path: `{target['path']}`",
            f"- Exists: `{target['exists']}`",
            f"- Git repo: `{target['is_repo']}`",
            "- Languages: " + (", ".join(f"{key}={value}" for key, value in target["languages"].items()) or "none detected"),
            "- Manifests: " + (", ".join(f"`{item}`" for item in target["manifests"][:8]) or "none detected"),
        ]
    )
    if target["warnings"]:
        lines.append("- Warnings:")
        lines.extend(f"  - {item}" for item in target["warnings"])

    lines.extend(["", "## Reference Repos", ""])
    for reference in data["references"]:
        lines.extend(
            [
                f"### `{reference['path']}`",
                "",
                f"- Exists: `{reference['exists']}`",
                f"- Git repo: `{reference['is_repo']}`",
                f"- Relationship to target: `{reference['relationship']}`",
                "- Languages: " + (", ".join(f"{key}={value}" for key, value in reference["languages"].items()) or "none detected"),
                "- Manifests: " + (", ".join(f"`{item}`" for item in reference["manifests"][:8]) or "none detected"),
            ]
        )
        if reference["sample_files"]:
            lines.append("- Sample source files:")
            lines.extend(f"  - `{item}`" for item in reference["sample_files"][:8])
        if reference["warnings"]:
            lines.append("- Warnings:")
            lines.extend(f"  - {item}" for item in reference["warnings"])
        lines.append("")

    lines.extend(["## Read/Write Boundaries", ""])
    lines.extend(f"- {item}" for item in data["read_write_boundaries"])
    lines.extend(["", "## Load", ""])
    lines.extend(f"- {item}" for item in data["load"])
    lines.extend(["", "## Avoid", ""])
    lines.extend(f"- {item}" for item in data["avoid"])
    lines.extend(["", "## Suggested Commands", ""])
    if data["suggested_commands"]:
        lines.extend(f"- `{item}`" for item in data["suggested_commands"])
    else:
        lines.append("- No graph command suggested because no readable reference directory was found.")
    lines.extend(["", "## Implementation Plan", ""])
    lines.extend(f"{index}. {item}" for index, item in enumerate(data["implementation_plan"], start=1))
    lines.extend(["", "## Approval", ""])
    lines.extend(f"- {item}" for item in data["approval"])
    lines.append("")
    return "\n".join(lines)


def write_summary(data: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix == ".json":
        output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    else:
        output.write_text(markdown(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan safe read-only cross-repo reference usage.")
    parser.add_argument("--target", type=Path, default=Path.cwd(), help="Repo that may be edited.")
    parser.add_argument("--reference", type=Path, action="append", required=True, help="Read-only reference repo. Repeat for multiple repos.")
    parser.add_argument("--goal", default="", help="Task goal for the reference plan.")
    parser.add_argument("--limit", type=int, default=2000, help="Maximum files/directories to scan per repo.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--write-summary", type=Path, help="Optional output path under the target repo, such as .tailtrail/reference-context/service-b.md.")
    args = parser.parse_args()

    data = plan(args)
    if args.write_summary:
        write_summary(data, args.write_summary)
    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        print(markdown(data), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
