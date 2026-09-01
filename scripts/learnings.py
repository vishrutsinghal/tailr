#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "learnings.md"
DEFAULT_PATH = Path(".tailtrail") / "learnings.md"


def load_v3():
    spec = importlib.util.spec_from_file_location("tailtrail_legacy_learning_v3", ROOT / "scripts" / "learning-v3.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load Learning V3")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V3 = load_v3()


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
    timestamp_value = datetime.now(timezone.utc)
    timestamp = timestamp_value.strftime("%Y-%m-%d")
    normalized = V3.clean_text(text)
    learning_id = "lrn-" + hashlib.sha256(f"{timestamp_value.isoformat()}:{section}:{normalized}".encode("utf-8")).hexdigest()[:16]
    record = V3.build_record(
        root,
        learning_id=learning_id,
        learning_class="project-convention",
        summary=f"Explicit curated learning in section {V3.clean_text(section, limit=80)}",
        advice=normalized,
        source_kind="legacy-curated-command",
        source_ref=path.as_posix(),
        source_fingerprint="sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        captured_by="Learning Governance compatibility writer",
        tags=[V3.clean_text(section, limit=80)],
        confidence_score=80,
        reason="explicit curated learning add",
        curated=True,
    )
    V3.append_record(root, record)
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
