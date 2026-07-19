#!/usr/bin/env python3

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TAILTRAIL_NAMES = (
    "tailtrail",
    "TailTrail",
    "AIDLC",
    "aidlc",
    "GUARDRAILS.md",
    "DEPENDENCY-GATE.md",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
)

SKIP_DIRS = {
    ".git",
    "__pycache__",
    "aidlc-rules",
}

SHARED_PROJECT_CONTEXT = {
    "AGENTS.md",
    "AIDLC.md",
    "DEPENDENCY-GATE.md",
    "GUARDRAILS.md",
    "tailtrail-policy.md",
    "tailtrail-policy.example.md",
    ".tailtrail/team-policy.md",
    ".tailtrail/learnings.md",
    ".tailtrail/learning-index.md",
    ".tailtrail/graph-learning-index.json",
}

PROJECT_OVERRIDES = {
    ".tailtrail/intent-overrides.json",
    ".tailtrail/policy-overrides.json",
    "tailtrail/intent-overrides.json",
    "tailtrail/tailtrail-policy.md",
}

TEAM_REVIEW_FILES = {
    ".github/copilot-instructions.md",
    ".cursor/rules/tailtrail.mdc",
    ".openai/chatgpt-instructions.md",
    "CLAUDE.md",
    "GEMINI.md",
}

GENERATED_SHAREABLE = {
    "tailtrail-meta/code-graph-cache.json",
    "tailtrail-meta/harness-summary.jsonl",
    "tailtrail-meta/harness-summary.schema.json",
    "tailtrail-meta/README.md",
}

STRICT_LOCAL_INSTALL_FILES = {
    ".github/copilot-instructions.md",
    ".cursor/rules/tailtrail.mdc",
    ".openai/chatgpt-instructions.md",
    "CLAUDE.md",
    "GEMINI.md",
    "AGENTS.md",
    "AIDLC.md",
    "DEPENDENCY-GATE.md",
    "GUARDRAILS.md",
    "GOVERNANCE.md",
    "TOKEN-AUTOPILOT.md",
    "TOKEN-SLICER.md",
    "TAILTRAIL-COMMANDS.md",
    "USEFUL-PROMPTS.md",
    "USER-GUIDE.md",
    "tailtrail-policy.md",
    "tailtrail-policy.example.md",
}

LOCAL_STATE_PATTERNS = (
    ".tailtrail/*",
    "tailtrail/*",
    ".tailtrail/*state*.json",
    ".tailtrail/*events*.jsonl",
    ".tailtrail/*scores*.jsonl",
    ".tailtrail/token-usage.jsonl",
    ".tailtrail/token-budget-profile.json",
    ".tailtrail/context-receipts.jsonl",
    ".tailtrail/token-harness-events.jsonl",
    ".tailtrail/token-harness-events.lock",
    ".tailtrail/enterprise-report.md",
    ".tailtrail/quality-runs/*",
    ".tailtrail/vulnerability-runs/*",
    ".tailtrail/task-starts/*",
    ".tailtrail/quality-events.jsonl",
    ".tailtrail/quality-summary.md",
    ".tailtrail/quality-decisions.md",
    ".tailtrail/harness-review.md",
    ".tailtrail/harness-local-summary.json",
    ".tailtrail/harness-summary.json",
    ".tailtrail/harness-recommendations.json",
    ".tailtrail/harness-events.jsonl",
    ".tailtrail/meta-harness-analysis.json",
    ".tailtrail/meta-harness-analysis.md",
    ".tailtrail/meta-harness-proposal.md",
    ".tailtrail/meta-harness-proposals.jsonl",
    ".tailtrail/code-graph-cache.json",
    ".tailtrail/outcome-events.jsonl",
    ".tailtrail/outcome-summary.md",
    ".tailtrail/learning-events.jsonl",
    ".tailtrail/learning-refresh-actions.jsonl",
    "tailtrail/.tailtrail-install.json",
    "tailtrail/.tailtrail/*",
    "aidlc-docs/*",
)

INSTALLED_PACK_HINTS = (
    "tailtrail/scripts/tailtrail.py",
    "tailtrail/AGENTS.md",
    "tailtrail/.tailtrail-install.json",
    "tailtrail/.codex-plugin/plugin.json",
)

GITIGNORE_RECOMMENDATIONS = (
    ".tailtrail/",
    "tailtrail/",
    ".tailtrail/*state*.json",
    ".tailtrail/*events*.jsonl",
    ".tailtrail/*scores*.jsonl",
    ".tailtrail/token-usage.jsonl",
    ".tailtrail/token-budget-profile.json",
    ".tailtrail/context-receipts.jsonl",
    ".tailtrail/token-harness-events.jsonl",
    ".tailtrail/token-harness-events.lock",
    ".tailtrail/quality-runs/",
    ".tailtrail/vulnerability-runs/",
    ".tailtrail/task-starts/",
    ".tailtrail/enterprise-report.md",
    ".tailtrail/outcome-events.jsonl",
    ".tailtrail/outcome-summary.md",
    ".tailtrail/harness-review.md",
    ".tailtrail/harness-local-summary.json",
    ".tailtrail/harness-summary.json",
    ".tailtrail/harness-recommendations.json",
    ".tailtrail/harness-events.jsonl",
    ".tailtrail/meta-harness-analysis.json",
    ".tailtrail/meta-harness-analysis.md",
    ".tailtrail/meta-harness-proposal.md",
    ".tailtrail/meta-harness-proposals.jsonl",
    "tailtrail/.tailtrail-install.json",
    ".github/copilot-instructions.md",
    ".cursor/rules/tailtrail.mdc",
    ".openai/chatgpt-instructions.md",
    "CLAUDE.md",
    "GEMINI.md",
    "AGENTS.md",
    "AIDLC.md",
    "DEPENDENCY-GATE.md",
    "GUARDRAILS.md",
    "GOVERNANCE.md",
    "TOKEN-AUTOPILOT.md",
    "TOKEN-SLICER.md",
    "TAILTRAIL-COMMANDS.md",
    "USEFUL-PROMPTS.md",
    "USER-GUIDE.md",
    "tailtrail-policy.md",
    "tailtrail-policy.example.md",
    "aidlc-docs/",
    "!tailtrail-meta/",
    "!tailtrail-meta/README.md",
    "!tailtrail-meta/code-graph-cache.json",
    "!tailtrail-meta/harness-summary.schema.json",
    "!tailtrail-meta/harness-summary.jsonl",
)


@dataclass(frozen=True)
class Finding:
    path: str
    category: str
    recommendation: str
    reason: str
    tracked: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "category": self.category,
            "recommendation": self.recommendation,
            "reason": self.reason,
            "tracked": self.tracked,
        }


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_git(root: Path, args: list[str]) -> list[str]:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def list_files(root: Path, include_untracked: bool) -> tuple[list[str], set[str]]:
    tracked = set(run_git(root, ["ls-files"]))
    if not include_untracked:
        return sorted(tracked), tracked

    files = set(tracked)
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            rel = relative(path, root)
            if is_tailtrail_like(rel):
                files.add(rel)
    return sorted(files), tracked


def is_tailtrail_like(path: str) -> bool:
    if path.startswith((".tailtrail/", "tailtrail/", "tailtrail-meta/", "aidlc-docs/", "aidlc/")):
        return True
    if path in SHARED_PROJECT_CONTEXT or path in PROJECT_OVERRIDES or path in TEAM_REVIEW_FILES:
        return True
    return any(name in path for name in TAILTRAIL_NAMES)


def matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def is_tailtrail_source_checkout(root: Path) -> bool:
    return (root / ".codex-plugin" / "plugin.json").is_file() and (root / "skills" / "tailtrail" / "SKILL.md").is_file()


def classify(path: str, tracked: bool, root: Path) -> tuple[str, str, str]:
    source_checkout = is_tailtrail_source_checkout(root)
    if path.startswith("tailtrail-meta/"):
        if path in GENERATED_SHAREABLE:
            return (
                "generated-but-shareable metadata",
                "team decision",
                "Generated metadata may be useful when intentionally shared, but it should be reviewed for freshness and sensitivity.",
            )
        return (
            "unknown TailTrail-like files",
            "review manually",
            "Only reviewed TailTrail metadata belongs in tailtrail-meta/.",
        )
    if path.startswith(".tailtrail/"):
        return (
            "local runtime state",
            "do not commit",
            "TailTrail dot-folder files are local runtime/setup state by default. Commit only reviewed tailtrail-meta/ metadata.",
        )
    if path.startswith("tailtrail/") or path.startswith("aidlc-docs/") or (path in STRICT_LOCAL_INSTALL_FILES and not source_checkout):
        return (
            "local TailTrail install files",
            "do not commit unless the repo explicitly opts into shared TailTrail setup",
            "TailTrail setup files should stay local by default. Commit only reviewed tailtrail-meta/ metadata.",
        )
    if path in SHARED_PROJECT_CONTEXT or path.startswith("aidlc-docs/"):
        return (
            "shared project context",
            "preserve",
            "Shared guidance or lifecycle context can be committed when the team intentionally owns it.",
        )
    if path in PROJECT_OVERRIDES:
        return (
            "project overrides",
            "preserve and review before update",
            "Overrides are local project/team choices and should not be overwritten silently.",
        )
    if path in TEAM_REVIEW_FILES:
        return (
            "team review files",
            "preserve and review",
            "Assistant adapter instructions are usually shared repo guidance.",
        )
    if matches_any(path, LOCAL_STATE_PATTERNS):
        return (
            "local runtime state",
            "do not commit",
            "Runtime state, event logs, run output, telemetry, and local install manifests belong to the current user/session.",
        )
    if path in INSTALLED_PACK_HINTS or path.startswith("tailtrail/scripts/") or path.startswith("tailtrail/context/") or path.startswith("tailtrail/skills/"):
        return (
            "installed TailTrail pack",
            "update only with dry-run then approval",
            "Managed pack files should be updated through TailTrail updater instead of manual overwrite.",
        )
    if is_tailtrail_like(path):
        return (
            "unknown TailTrail-like files",
            "review manually",
            "The file looks TailTrail-related but does not match a known safe category.",
        )
    return ("not TailTrail", "ignore", "Not included in TailTrail setup scan.")


def gitignore_missing(root: Path) -> list[str]:
    gitignore = root / ".gitignore"
    lines = []
    if gitignore.is_file():
        lines = [line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]
    missing: list[str] = []
    for pattern in GITIGNORE_RECOMMENDATIONS:
        if is_tailtrail_source_checkout(root) and (
            pattern in STRICT_LOCAL_INSTALL_FILES
            or pattern.startswith("aidlc-docs")
            or pattern.startswith("!")
            or pattern == "tailtrail/"
            or pattern.startswith("tailtrail/")
        ):
            continue
        if not gitignore_covers(pattern, lines):
            missing.append(pattern)
    return missing


def gitignore_covers(pattern: str, lines: list[str]) -> bool:
    if pattern in lines:
        return True
    if pattern.startswith(".tailtrail/") and ".tailtrail/" in lines:
        return True
    if pattern.startswith("tailtrail/.tailtrail") and "tailtrail/.tailtrail/" in lines:
        return True
    return False


def detect_pack(root: Path) -> dict[str, Any]:
    pack_root = root / "tailtrail"
    manifest = pack_root / ".tailtrail-install.json"
    return {
        "present": pack_root.exists(),
        "path": "tailtrail" if pack_root.exists() else "",
        "manifest_present": manifest.is_file(),
        "update_dry_run": "python3 tailtrail/scripts/tailtrail.py update --root . --dry-run" if pack_root.exists() else "",
        "install_dry_run": "python3 /path/to/tailtrail/scripts/install-local.py --target . --profile full --dry-run",
    }


def build_report(root: Path, include_untracked: bool) -> dict[str, Any]:
    files, tracked_files = list_files(root, include_untracked)
    findings: list[Finding] = []
    for path in files:
        if not is_tailtrail_like(path):
            continue
        category, recommendation, reason = classify(path, path in tracked_files, root)
        if category == "not TailTrail":
            continue
        findings.append(Finding(path, category, recommendation, reason, path in tracked_files))

    categories: dict[str, list[dict[str, Any]]] = {}
    for finding in findings:
        categories.setdefault(finding.category, []).append(finding.as_dict())

    warnings: list[str] = []
    tracked_local_state = [finding.path for finding in findings if finding.category == "local runtime state" and finding.tracked]
    if tracked_local_state:
        warnings.append("Tracked local runtime state detected. Review whether these files should be removed from git and ignored.")
    tracked_install_files = [finding.path for finding in findings if finding.category == "local TailTrail install files" and finding.tracked]
    if tracked_install_files:
        warnings.append("Tracked TailTrail install files detected. Default hygiene is to keep setup files local and commit only reviewed tailtrail-meta/ metadata.")
    overrides = [finding.path for finding in findings if finding.category == "project overrides"]
    if overrides:
        warnings.append("Project overrides detected. Preserve them during install/update unless a reviewer approves a change.")
    if any(finding.category == "installed TailTrail pack" for finding in findings):
        warnings.append("Installed TailTrail pack detected. Use update dry-run before applying newer TailTrail files.")

    missing_gitignore = gitignore_missing(root)
    next_commands = [
        "python3 scripts/tailtrail.py policy check --root .",
        "python3 scripts/tailtrail.py setup-scan --root . --format json",
    ]
    pack = detect_pack(root)
    if pack["present"]:
        next_commands.append(str(pack["update_dry_run"]))
    else:
        next_commands.append("python3 /path/to/tailtrail/scripts/install-local.py --target . --profile full --dry-run")

    return {
        "type": "tailtrail-setup-scan",
        "schema_version": "1",
        "created_at": now_utc(),
        "root": root.as_posix(),
        "include_untracked": include_untracked,
        "pack": pack,
        "summary": {category: len(items) for category, items in sorted(categories.items())},
        "categories": categories,
        "warnings": warnings,
        "gitignore_recommendations": missing_gitignore,
        "next_commands": next_commands,
        "boundaries": [
            "setup-scan is read-only and does not install, update, delete, move, or ignore files.",
            "Shared context and overrides are preserved by default.",
            "Local runtime state is flagged because it usually belongs to one user/session.",
            "Use dry-run update/install commands before changing TailTrail-managed files.",
        ],
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Setup Scan",
        "",
        f"- Root: `{report['root']}`",
        f"- Include untracked: `{str(report['include_untracked']).lower()}`",
        "",
        "## Summary",
        "",
    ]
    summary = report["summary"]
    if summary:
        for category, count in summary.items():
            lines.append(f"- {category}: `{count}`")
    else:
        lines.append("- No TailTrail files detected.")

    lines.extend(["", "## Categories", ""])
    categories = report["categories"]
    if not categories:
        lines.append("- none")
    for category, items in categories.items():
        lines.extend([f"### {display_category(category)}", ""])
        for item in items:
            tracked = "tracked" if item["tracked"] else "untracked"
            lines.append(f"- `{item['path']}` ({tracked})")
            lines.append(f"  Recommendation: {item['recommendation']}")
            lines.append(f"  Reason: {item['reason']}")
        lines.append("")

    lines.extend(["## Warnings", ""])
    for warning in report["warnings"] or ["none"]:
        lines.append(f"- {warning}")

    lines.extend(["", "## .gitignore Recommendations", ""])
    for pattern in report["gitignore_recommendations"] or ["none"]:
        lines.append(f"- `{pattern}`")

    lines.extend(["", "## Installed Pack", ""])
    pack = report["pack"]
    lines.append(f"- Present: `{str(pack['present']).lower()}`")
    if pack["path"]:
        lines.append(f"- Path: `{pack['path']}`")
        lines.append(f"- Manifest present: `{str(pack['manifest_present']).lower()}`")

    lines.extend(["", "## Next Commands", ""])
    for command in report["next_commands"]:
        lines.append(f"- `{command}`")

    lines.extend(["", "## Boundaries", ""])
    for boundary in report["boundaries"]:
        lines.append(f"- {boundary}")
    return "\n".join(lines) + "\n"


def display_category(category: str) -> str:
    names = {
        "shared project context": "Shared Project Context",
        "project overrides": "Project Overrides",
        "team review files": "Team Review Files",
        "installed TailTrail pack": "Installed TailTrail Pack",
        "local TailTrail install files": "Local TailTrail Install Files",
        "local runtime state": "Local Runtime State",
        "generated-but-shareable metadata": "Generated-But-Shareable Metadata",
        "unknown TailTrail-like files": "Unknown TailTrail-Like Files",
    }
    return names.get(category, category.title())


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify TailTrail files in a cloned or existing repo.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target project root.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--tracked-only", action="store_true", help="Only inspect git-tracked files.")
    args = parser.parse_args()

    root = args.root.resolve()
    report = build_report(root, include_untracked=not args.tracked_only)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
