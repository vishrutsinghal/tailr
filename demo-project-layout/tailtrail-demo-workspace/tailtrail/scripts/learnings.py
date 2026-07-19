#!/usr/bin/env python3

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "learnings.md"
DEFAULT_PATH = Path(".tailtrail") / "learnings.md"


def target_path(root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return root / path


def init_learnings(root: Path, path: Path, force: bool) -> Path:
    destination = target_path(root, path)
    if destination.exists() and not force:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    return destination


def add_learning(root: Path, path: Path, section: str, text: str) -> Path:
    destination = init_learnings(root, path, force=False)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = f"\n## Learning: {section}\n\n- Date: {timestamp}\n- Note: {text}\n"
    with destination.open("a", encoding="utf-8") as handle:
        handle.write(entry)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Create and update lightweight TailTrail project learnings.")
    parser.add_argument("action", choices=["init", "add", "show"], help="Learning action.")
    parser.add_argument("text", nargs="*", help="Learning text for the add action.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target project root.")
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH, help="Learning file path relative to root.")
    parser.add_argument("--section", default="general", help="Learning section name for add.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing learning file during init.")
    args = parser.parse_intermixed_args()

    root = args.root.resolve()
    if args.action == "init":
        destination = init_learnings(root, args.path, args.force)
        print(f"TailTrail learnings file ready: {destination}")
    elif args.action == "add":
        if not args.text:
            raise SystemExit("add requires learning text")
        destination = add_learning(root, args.path, args.section, " ".join(args.text))
        print(f"TailTrail learning added: {destination}")
    else:
        destination = target_path(root, args.path)
        if not destination.exists():
            raise SystemExit(f"TailTrail learnings file not found: {destination}")
        print(destination.read_text(encoding="utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
