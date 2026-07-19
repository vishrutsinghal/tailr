#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START = "<!-- tailtrail-governance:start -->"
END = "<!-- tailtrail-governance:end -->"

TARGETS = (
    "AGENTS.md",
    "context/guardrail-layers.md",
    "adapters/claude.md",
    "adapters/copilot-instructions.md",
    "adapters/cursor.mdc",
    "adapters/chatgpt-instructions.md",
    "adapters/gemini.md",
)


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def write(relative_path: str, body: str) -> None:
    (ROOT / relative_path).write_text(body, encoding="utf-8")


def extract_block(body: str, path: str) -> str:
    start = body.find(START)
    end = body.find(END)
    if start < 0 or end < 0 or end < start:
        raise ValueError(f"{path}: missing governance sync markers")
    return body[start : end + len(END)]


def replace_block(body: str, block: str, path: str) -> str:
    start = body.find(START)
    end = body.find(END)
    if start < 0 or end < 0 or end < start:
        raise ValueError(f"{path}: missing governance sync markers")
    return body[:start] + block + body[end + len(END) :]


def canonical_block() -> str:
    return extract_block(read("GOVERNANCE.md"), "GOVERNANCE.md")


def check() -> list[str]:
    errors: list[str] = []
    canonical = canonical_block()
    guardrails = read("GUARDRAILS.md")
    for phrase in (
        "Do not act with more certainty than the evidence supports.",
        "Do not claim tests passed unless they were run and succeeded.",
        "Token saving must not hide material facts.",
        "Do not remove or weaken safeguards",
    ):
        if phrase not in guardrails:
            errors.append(f"GUARDRAILS.md missing canonical source phrase: {phrase}")
    for target in TARGETS:
        try:
            current = extract_block(read(target), target)
        except ValueError as error:
            errors.append(str(error))
            continue
        if current != canonical:
            errors.append(f"{target}: governance block is not synced with GOVERNANCE.md")
    return errors


def sync() -> None:
    canonical = canonical_block()
    for target in TARGETS:
        write(target, replace_block(read(target), canonical, target))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or sync TailTrail repeated governance text.")
    parser.add_argument("action", choices=["check", "sync"], help="Check drift or rewrite marked governance blocks.")
    args = parser.parse_args()

    if args.action == "sync":
        sync()

    errors = check()
    if errors:
        for error in errors:
            print(f"Governance sync failed: {error}", file=sys.stderr)
        return 1

    print("Governance sync passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
