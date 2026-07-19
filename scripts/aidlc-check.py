#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path


REQUIRED_STATE_FIELDS = [
    "Project:",
    "Lifecycle depth:",
    "Current phase:",
    "Current stage:",
    "Status:",
    "Next step:",
    "Last updated:",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_required_file(errors: list[str], path: Path) -> None:
    if not path.exists():
        errors.append(f"missing {path}")


def check_state(errors: list[str], state_path: Path) -> None:
    if not state_path.exists():
        errors.append(f"missing {state_path}")
        return
    body = read(state_path)
    for field in REQUIRED_STATE_FIELDS:
        if field not in body:
            errors.append(f"{state_path} missing field {field}")


def check_questions(errors: list[str], docs_dir: Path, strict_answers: bool) -> None:
    for path in sorted(docs_dir.glob("*questions*.md")):
        body = read(path)
        if "[Answer]:" not in body:
            errors.append(f"{path} has no answer tags")
        if "Recommended option:" not in body:
            errors.append(f"{path} has no recommended option field")
        if "Reasoning:" not in body:
            errors.append(f"{path} has no reasoning field")
        if strict_answers:
            for match in re.finditer(r"\[Answer\]:\s*$", body, flags=re.MULTILINE):
                line = body.count("\n", 0, match.start()) + 1
                errors.append(f"{path}:{line} has an empty answer")


def check_stage_gates(errors: list[str], docs_dir: Path) -> None:
    for path in sorted(docs_dir.glob("*stage-gate*.md")):
        body = read(path)
        if "Decision:" not in body:
            errors.append(f"{path} missing Decision field")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate portable AIDLC docs in a target project.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target project root.")
    parser.add_argument(
        "--strict-answers",
        action="store_true",
        help="Fail when question files contain empty [Answer]: fields.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    docs_dir = root / "aidlc-docs"
    errors: list[str] = []

    if not docs_dir.exists():
        errors.append(f"missing {docs_dir}")
    else:
        check_state(errors, docs_dir / "aidlc-state.md")
        check_required_file(errors, docs_dir / "audit.md")
        check_questions(errors, docs_dir, args.strict_answers)
        check_stage_gates(errors, docs_dir)

    if errors:
        for error in errors:
            print(f"AIDLC check failed: {error}")
        return 1

    print("AIDLC check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
