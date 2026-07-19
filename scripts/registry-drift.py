#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FEATURE_IMPACT_PREFIXES = (
    "scripts/",
    "skills/",
    "benchmarks/",
    "adapters/",
    "context/",
    "hooks/",
    "templates/",
)
FEATURE_IMPACT_FILES = {
    "tailtrail-registry.json",
    "tailtrail-registry.schema.json",
    "ROADMAP.md",
    "README.md",
    "USER-GUIDE.md",
    "TAILTRAIL-COMMANDS.md",
    "PUBLIC-CLAIMS.md",
    "TAILTRAIL-PITCH.md",
    "PITCH-PLAN.md",
}
PUBLIC_DOCS = ("PUBLIC-CLAIMS.md", "TAILTRAIL-PITCH.md", "README.md", "USER-GUIDE.md")
RISKY_CLAIMS = (
    "guarantees token savings",
    "guaranteed token savings",
    "replaces ci",
    "replaces tests",
    "replaces code review",
    "replaces security review",
    "fully automatic compliance",
    "proves vulnerabilities are fixed",
)


def load_script(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


tailtrail_registry = load_script("tailtrail_registry_drift", ROOT / "scripts" / "tailtrail-registry.py")


def read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def git_changed_files(root: Path, since: str) -> list[str]:
    command = ["git", "diff", "--name-only", since]
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return []
    return sorted(line.strip() for line in result.stdout.splitlines() if line.strip())


def is_feature_impacting(path: str) -> bool:
    return path in FEATURE_IMPACT_FILES or path.startswith(FEATURE_IMPACT_PREFIXES)


def changelog_has_unreleased(root: Path) -> bool:
    body = read_text(root / "CHANGELOG.md").lower()
    return "## unreleased" in body


def registry_commands(registry: dict[str, Any]) -> list[str]:
    commands: list[str] = []
    for feature in tailtrail_registry.features(registry):
        for command in feature.get("commands", []):
            if isinstance(command, str):
                commands.append(command)
    return sorted(set(commands))


def command_root(command: str) -> str:
    parts = command.split()
    if len(parts) >= 2 and parts[0] == "tailtrail":
        return parts[1]
    return command


def command_doc_issues(root: Path, registry: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    docs = read_text(root / "TAILTRAIL-COMMANDS.md")
    for command in registry_commands(registry):
        root_command = command_root(command)
        if root_command in {"admin"}:
            continue
        if command in docs or f"tailtrail.py {command.removeprefix('tailtrail ')}" in docs:
            continue
        if root_command and root_command in docs:
            continue
        issues.append(f"command `{command}` is registered but not documented in TAILTRAIL-COMMANDS.md")
    return issues


def stale_roadmap_issues(root: Path, registry: dict[str, Any]) -> list[str]:
    body = read_text(root / "ROADMAP.md")
    issues: list[str] = []
    commands = registry_commands(registry)
    for line_number, line in enumerate(body.splitlines(), start=1):
        lowered = line.lower()
        if "not implemented" not in lowered:
            continue
        for command in commands:
            variants = {command, command.replace("tailtrail ", "tailtrail.py ")}
            if any(variant.lower() in lowered for variant in variants):
                issues.append(f"ROADMAP.md:{line_number} may be stale: implemented command appears on a `not implemented` line")
    return sorted(set(issues))


def public_claim_issues(root: Path) -> list[str]:
    issues: list[str] = []
    for relative in PUBLIC_DOCS:
        body = read_text(root / relative).lower()
        if not body:
            continue
        for claim in RISKY_CLAIMS:
            if claim in body:
                # PUBLIC-CLAIMS.md intentionally lists disallowed examples.
                if relative == "PUBLIC-CLAIMS.md":
                    continue
                issues.append(f"{relative} contains risky public claim wording: `{claim}`")
    return issues


def changelog_issues(root: Path, changed_files: list[str]) -> list[str]:
    if not changed_files:
        return []
    impacted = [path for path in changed_files if is_feature_impacting(path)]
    if not impacted:
        return []
    if "CHANGELOG.md" in changed_files or changelog_has_unreleased(root):
        return []
    return [
        "feature-impacting files changed without a CHANGELOG.md update or `## Unreleased` section: "
        + ", ".join(impacted[:8])
    ]


def collect_drift(root: Path = ROOT, *, since: str = "HEAD", changed_files: list[str] | None = None) -> dict[str, Any]:
    registry = tailtrail_registry.load_registry(root / "tailtrail-registry.json")
    changed = changed_files if changed_files is not None else git_changed_files(root, since)
    issues: list[dict[str, str]] = []

    for issue in tailtrail_registry.validate_registry(registry, root):
        issues.append({"category": "registry", "severity": "high", "message": issue})
    for issue in command_doc_issues(root, registry):
        issues.append({"category": "command-docs", "severity": "medium", "message": issue})
    for issue in stale_roadmap_issues(root, registry):
        issues.append({"category": "roadmap", "severity": "medium", "message": issue})
    for issue in changelog_issues(root, changed):
        issues.append({"category": "changelog", "severity": "medium", "message": issue})
    for issue in public_claim_issues(root):
        issues.append({"category": "claims", "severity": "high", "message": issue})

    return {
        "schema_version": "1",
        "type": "tailtrail-registry-drift-report",
        "root": root.as_posix(),
        "since": since,
        "changed_files": changed,
        "status": "failed" if issues else "passed",
        "issues": issues,
        "summary": {
            "issue_count": len(issues),
            "categories": sorted({issue["category"] for issue in issues}),
        },
        "recommendations": recommendations(issues),
    }


def recommendations(issues: list[dict[str, str]]) -> list[str]:
    result: list[str] = []
    categories = {issue["category"] for issue in issues}
    if "registry" in categories:
        result.append("Update tailtrail-registry.json so registered docs, scripts, tests, dependencies, and commands match the source tree.")
    if "command-docs" in categories:
        result.append("Add or correct command examples in TAILTRAIL-COMMANDS.md.")
    if "roadmap" in categories:
        result.append("Update stale ROADMAP.md wording so implemented features are not described as missing.")
    if "changelog" in categories:
        result.append("Add a CHANGELOG.md Unreleased entry describing the feature-impacting change.")
    if "claims" in categories:
        result.append("Revise public docs to use allowed evidence labels and avoid unsupported claims.")
    return result


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Registry Drift Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Since: `{report['since']}`",
        f"- Changed files: `{len(report['changed_files'])}`",
        f"- Issues: `{report['summary']['issue_count']}`",
        "",
    ]
    if report["issues"]:
        lines.extend(["## Issues", ""])
        for issue in report["issues"]:
            lines.append(f"- {issue['severity']} / {issue['category']}: {issue['message']}")
        lines.append("")
    if report["recommendations"]:
        lines.extend(["## Recommended Fixes", ""])
        lines.extend(f"- {item}" for item in report["recommendations"])
        lines.append("")
    if not report["issues"]:
        lines.append("No registry drift detected.")
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect TailTrail registry, command, roadmap, changelog, and public-claim drift.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--since", default="HEAD")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = collect_drift(args.root.resolve(), since=args.since)
    print(json.dumps(report, indent=2, sort_keys=True) if args.format == "json" else render_markdown(report), end="")
    return 1 if args.strict and report["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
