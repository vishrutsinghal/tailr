#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ADAPTERS = {
    "claude": ("adapters/claude.md", "CLAUDE.md"),
    "cursor": ("adapters/cursor.mdc", ".cursor/rules/tailtrail.mdc"),
    "copilot": ("adapters/copilot-instructions.md", ".github/copilot-instructions.md"),
    "chatgpt": ("adapters/chatgpt-instructions.md", ".openai/chatgpt-instructions.md"),
    "gemini": ("adapters/gemini.md", "GEMINI.md"),
}

REQUIRED_CONTRACT_PHRASES = {
    "navigator-first": "Navigator-first",
    "approval-before-implementation": "approval before implementation",
    "post-change-review": "post-change review",
    "scanner-approval": "scanner approval",
    "learning-advisory": "learnings as advisory",
    "token-claim-boundary": "estimated unless measured telemetry",
    "evidence-labels": "heuristic, local-ast, provider-backed, measured/validated",
    "local-policy": "tailtrail-policy.md",
}


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def write(relative_path: str, body: str) -> None:
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def check() -> list[str]:
    errors: list[str] = []
    for name, (source, target) in ADAPTERS.items():
        source_path = ROOT / source
        target_path = ROOT / target
        if not source_path.exists():
            errors.append(f"{name}: missing source {source}")
            continue
        if not target_path.exists():
            errors.append(f"{name}: missing target {target}")
            continue
        if read(source) != read(target):
            errors.append(f"{name}: {target} is not synced with {source}")
        errors.extend(check_contract(name, source, read(source)))
    return errors


def check_contract(name: str, source: str, body: str) -> list[str]:
    errors: list[str] = []
    lowered = body.lower()
    for contract, phrase in REQUIRED_CONTRACT_PHRASES.items():
        if phrase.lower() not in lowered:
            errors.append(f"{name}: {source} missing adapter contract phrase `{contract}` ({phrase})")
    return errors


def sync() -> None:
    for source, target in ADAPTERS.values():
        write(target, read(source))


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync TailTrail adapter source files to tool-specific target files.")
    parser.add_argument("--check", action="store_true", help="Check whether target files match adapter sources.")
    parser.add_argument("--write", action="store_true", help="Write target files from adapter sources.")
    args = parser.parse_args()

    if args.write:
        sync()

    errors = check()
    if errors:
        for error in errors:
            print(f"Adapter sync failed: {error}", file=sys.stderr)
        return 1

    print("Adapter sync passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
