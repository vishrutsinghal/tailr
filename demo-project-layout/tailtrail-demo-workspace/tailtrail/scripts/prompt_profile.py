#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from typing import Any


PROFILES: dict[str, dict[str, Any]] = {
    "lean": {
        "budget_band": "2k-5k",
        "load": ["exact user request", "exact target file only when needed"],
        "avoid": ["AIDLC docs", "broad repo scans", "roadmap/pitch docs", "raw learning history"],
        "use_when": "tiny or low-risk changes",
    },
    "review": {
        "budget_band": "5k-12k",
        "load": ["exact diff or changed files", "Code Review Graph Lite", "relevant guardrail layer", "likely tests"],
        "avoid": ["full documentation pack", "unrelated feature docs", "raw learning history"],
        "use_when": "bug fixes, refactors, code review, safeguard checks",
    },
    "testing": {
        "budget_band": "5k-12k",
        "load": ["changed files", "likely test files", "test helpers/fixtures", "Test Precision Planner output"],
        "avoid": ["broad test tree reads before likely tests are known", "scanner logs unless the task asks for them"],
        "use_when": "unit tests, regression tests, validation confidence, before-PR checks",
    },
    "aidlc": {
        "budget_band": "12k-30k",
        "load": ["AIDLC state", "active stage playbook", "requirements/workflow/implementation docs", "local policy"],
        "avoid": ["unrelated lifecycle stages", "raw learning history", "full repo scans without graph/read-order first"],
        "use_when": "broad, regulated, multi-team, release, migration, or multi-step work",
    },
    "security": {
        "budget_band": "8k-20k",
        "load": ["exact security diff/source", "security guardrail layer", "scanner evidence summary", "dependency gate when relevant"],
        "avoid": ["lossy summaries of secrets, policies, configs, scanner evidence, or auth rules"],
        "use_when": "auth, secrets, CVE/GHSA, SAST, dependency, permission, or vulnerability work",
    },
    "handoff": {
        "budget_band": "4k-10k",
        "load": ["changed behavior summary", "validation evidence", "risk notes", "diff handoff template"],
        "avoid": ["implementation chat history", "raw prompt history", "unrelated roadmap docs"],
        "use_when": "PR prep, release notes, reviewer transfer, ownership handoff",
    },
}


ALIASES = {
    "qa": "testing",
    "test": "testing",
    "tests": "testing",
    "ci-sonar": "testing",
    "vulnerability": "security",
    "dependency": "security",
    "release": "handoff",
}


def normalize(name: str) -> str:
    return ALIASES.get(name, name)


def profile_payload(name: str) -> dict[str, Any]:
    normalized = normalize(name)
    if normalized not in PROFILES:
        raise SystemExit(f"Unknown prompt compression profile: {name}. Use one of: {', '.join(sorted(PROFILES))}")
    return {"schema_version": "1", "profile": normalized, **PROFILES[normalized]}


def choose_profile(task_types: list[str], risks: list[str]) -> str:
    if any(task in task_types for task in ("security", "dependency")) or any(risk in risks for risk in ("auth/security", "vulnerability scan", "secrets")):
        return "security"
    if any(task in task_types for task in ("feature", "implementation", "release")):
        return "aidlc" if "release" in task_types else "review"
    if any(task in task_types for task in ("qa", "ci-sonar")):
        return "testing"
    if "handoff" in task_types:
        return "handoff"
    if any(task in task_types for task in ("bug", "review", "refactor")):
        return "review"
    return "lean"


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Prompt Compression Profile",
        "",
        f"- Profile: `{payload['profile']}`",
        f"- Budget band: `{payload['budget_band']}`",
        f"- Use when: {payload['use_when']}",
        "",
        "## Load",
    ]
    lines.extend(f"- {item}" for item in payload["load"])
    lines.extend(["", "## Avoid"])
    lines.extend(f"- {item}" for item in payload["avoid"])
    lines.extend(
        [
            "",
            "## Rule",
            "- Load this profile instead of the full TailTrail docs. Add more context only through an explicit budget escalation.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Show compact TailTrail prompt compression profiles.")
    parser.add_argument("profile", nargs="?", default="lean", help="Profile name: lean, review, testing, aidlc, security, handoff.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    payload = profile_payload(args.profile)
    print(json.dumps(payload, indent=2) if args.format == "json" else render_markdown(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
