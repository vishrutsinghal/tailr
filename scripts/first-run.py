#!/usr/bin/env python3
"""Verify a TailTrail installation and give a new user one safe first action."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def expected(profile: str, pack_dir: str) -> list[str]:
    mapping = {
        "generic": ["AGENTS.md"],
        "codex": ["AGENTS.md"],
        "codex-plugin": ["AGENTS.md", ".codex-plugin/plugin.json", "skills/tailtrail/SKILL.md", "skills/tailtrail-review/SKILL.md"],
        "copilot": [".github/copilot-instructions.md", f"{pack_dir}/.tailtrail-install.json"],
        "aidlc": ["AIDLC.md"],
        "full": [".github/copilot-instructions.md", f"{pack_dir}/.tailtrail-install.json", "AIDLC.md"],
    }
    return mapping.get(profile, [])


def first_action(profile: str) -> dict[str, str]:
    if profile in {"codex", "codex-plugin"}:
        return {"surface": "Codex chat", "command": "Using TailTrail Navigator, plan \"<your task>\" before implementation.", "why": "Codex reads the installed AGENTS guidance and TailTrail skills from the project."}
    return {"surface": "CLI or supported assistant", "command": 'tailtrail start "<your task>"', "why": "Start chooses the smallest TailTrail workflow and asks for approval before implementation."}


def check(target: Path, profile: str, pack_dir: str) -> dict[str, Any]:
    required = expected(profile, pack_dir)
    missing = [item for item in required if not (target / item).is_file()]
    return {"type": "tailtrail-first-run", "target": target.as_posix(), "profile": profile, "required": required, "missing": missing, "installation": "passed" if not missing else "incomplete", "first_action": first_action(profile), "boundary": "The smoke check verifies expected installed files and TailTrail's local hello command. It does not edit the target, run project tests, or invoke an agent."}


def smoke() -> dict[str, Any]:
    result = subprocess.run([sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "hello", "--quiet"], cwd=ROOT, text=True, capture_output=True, check=False)
    return {"command": "tailtrail hello --quiet", "exit_code": result.returncode, "status": "passed" if result.returncode == 0 else "failed"}


def render(payload: dict[str, Any]) -> str:
    action = payload["first_action"]
    lines = ["# TailTrail First Run", "", f"- Installation: **{payload['installation']}**", f"- Profile: `{payload['profile']}`", f"- Smoke test: **{payload['smoke']['status']}**", "", "## Start here", "", f"In **{action['surface']}**:", "", "```text", action["command"], "```", "", action["why"], "", "You do not need to understand anchors, harnesses, policies, or schemas yet. TailTrail will select the relevant controls after it reads the task."]
    if payload["missing"]:
        lines.extend(["", "## Missing install files", "", *[f"- `{item}`" for item in payload["missing"]]])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=Path.cwd())
    parser.add_argument("--profile", default="generic")
    parser.add_argument("--pack-dir", default="tailtrail")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)
    payload = check(args.target.resolve(), args.profile, args.pack_dir)
    payload["smoke"] = smoke()
    print(json.dumps(payload, indent=2, sort_keys=True) if args.format == "json" else render(payload), end="")
    return 0 if payload["installation"] == "passed" and payload["smoke"]["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
