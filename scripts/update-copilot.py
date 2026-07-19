#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INSTALL_COPILOT_PATH = ROOT / "scripts" / "install-copilot.py"
INSTALL_SPEC = importlib.util.spec_from_file_location("tailtrail_install_copilot", INSTALL_COPILOT_PATH)
if INSTALL_SPEC is None or INSTALL_SPEC.loader is None:
    raise SystemExit("Unable to load scripts/install-copilot.py")
install_copilot = importlib.util.module_from_spec(INSTALL_SPEC)
INSTALL_SPEC.loader.exec_module(install_copilot)
MANIFEST_NAME = install_copilot.MANIFEST_NAME
COPILOT_PATH = Path(".github") / "copilot-instructions.md"


@dataclass
class UpdateReport:
    updated: list[str]
    skipped_same: list[str]
    conflicts: list[str]
    missing: list[str]
    backed_up: list[str]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def load_manifest(pack_root: Path) -> dict[str, Any] | None:
    manifest_path = pack_root / MANIFEST_NAME
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def infer_pack_dir(target_root: Path) -> Path:
    copilot = target_root / COPILOT_PATH
    if copilot.exists():
        body = copilot.read_text(encoding="utf-8")
        match = re.search(r"TailTrail support files are installed under `([^`]+)`", body)
        if match:
            value = match.group(1)
            if value == "repository root":
                return Path(".")
            return install_copilot.validate_pack_dir(value)

    candidates = [Path("tailtrail"), Path("tools") / "tailtrail", Path(".")]
    for candidate in candidates:
        pack_root = target_root / candidate
        if (pack_root / MANIFEST_NAME).exists() or (pack_root / "AIDLC.md").exists():
            return candidate
    return Path("tailtrail")


def backup_file(path: Path, target_root: Path, backup_root: Path, report: UpdateReport) -> None:
    if not path.exists():
        return
    destination = backup_root / relative_display(path, target_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)
    report.backed_up.append(relative_display(destination, target_root))


def write_text_file(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def copy_file(path: Path, source: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, path)


def current_was_managed(path: Path, relative_path: str, manifest: dict[str, Any] | None) -> bool:
    if not path.exists():
        return True
    if manifest is None:
        return False
    files = manifest.get("files", {})
    old_entry = files.get(relative_path)
    if not isinstance(old_entry, dict):
        return False
    old_hash = old_entry.get("sha256")
    return bool(old_hash and sha256(path) == old_hash)


def should_update(
    destination: Path,
    relative_path: str,
    source_hash: str,
    manifest: dict[str, Any] | None,
    strategy: str,
    report: UpdateReport,
) -> bool:
    if not destination.exists():
        report.missing.append(relative_path)
        return True
    if sha256(destination) == source_hash:
        report.skipped_same.append(relative_path)
        return False
    if current_was_managed(destination, relative_path, manifest):
        return True
    if strategy == "preserve":
        report.conflicts.append(relative_path)
        return False
    return True


def write_manifest(pack_root: Path, pack_dir: Path) -> None:
    install_copilot.write_manifest(pack_root, pack_dir, [])


def update_file(
    destination: Path,
    source: Path,
    relative_path: str,
    target_root: Path,
    backup_root: Path,
    manifest: dict[str, Any] | None,
    strategy: str,
    dry_run: bool,
    report: UpdateReport,
) -> None:
    source_hash = sha256(source)
    if not should_update(destination, relative_path, source_hash, manifest, strategy, report):
        return
    if destination.exists() and strategy == "backup-overwrite":
        backup_file(destination, target_root, backup_root, report)
    if not dry_run:
        copy_file(destination, source)
    report.updated.append(relative_path)


def update_copilot(
    target_root: Path,
    pack_dir: Path,
    strategy: str,
    dry_run: bool,
) -> UpdateReport:
    pack_root = target_root / pack_dir
    manifest = load_manifest(pack_root)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_root = target_root / ".tailtrail" / "backups" / f"copilot-update-{timestamp}"
    report = UpdateReport(updated=[], skipped_same=[], conflicts=[], missing=[], backed_up=[])

    copilot_body = install_copilot.copilot_body(pack_dir)
    copilot_destination = target_root / COPILOT_PATH
    copilot_hash = hashlib.sha256(copilot_body.encode("utf-8")).hexdigest()
    if should_update(copilot_destination, COPILOT_PATH.as_posix(), copilot_hash, manifest, strategy, report):
        if copilot_destination.exists() and strategy == "backup-overwrite":
            backup_file(copilot_destination, target_root, backup_root, report)
        if not dry_run:
            write_text_file(copilot_destination, copilot_body)
        report.updated.append(COPILOT_PATH.as_posix())

    for relative_path in install_copilot.pack_entries():
        source = ROOT / relative_path
        destination = pack_root / relative_path
        update_file(destination, source, relative_path, target_root, backup_root, manifest, strategy, dry_run, report)

    if not dry_run and not report.conflicts:
        write_manifest(pack_root, pack_dir)
    if dry_run:
        report.updated = [f"{path} (dry-run)" for path in report.updated]
    return report


def print_report(target_root: Path, pack_dir: Path, strategy: str, dry_run: bool, report: UpdateReport) -> None:
    print(f"TailTrail Copilot update target: {target_root}")
    print(f"TailTrail pack folder: {(target_root / pack_dir).resolve()}")
    print(f"Strategy: {strategy}")
    if dry_run:
        print("Mode: dry-run")

    sections = [
        ("Updated", report.updated),
        ("Already current", report.skipped_same),
        ("Local edits preserved", report.conflicts),
        ("Missing files restored", report.missing),
        ("Backed up", report.backed_up),
    ]
    for title, items in sections:
        if items:
            print(f"{title}:")
            for item in items:
                print(f"- {item}")

    if report.conflicts:
        print("Next: review local edits, then rerun with --strategy backup-overwrite if you want TailTrail to refresh those files and keep backups.")
    else:
        print("Next: review git diff in the target project, then commit the TailTrail update.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely update an existing TailTrail GitHub Copilot pack in a target project.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target project root.")
    parser.add_argument("--pack-dir", help="Existing TailTrail pack folder. Defaults to auto-detection.")
    parser.add_argument("--strategy", choices=["preserve", "backup-overwrite"], default="preserve", help="How to handle locally modified TailTrail-managed files.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing files.")
    args = parser.parse_args()

    target_root = args.root.resolve()
    pack_dir = install_copilot.validate_pack_dir(args.pack_dir) if args.pack_dir else infer_pack_dir(target_root)
    report = update_copilot(target_root, pack_dir, args.strategy, args.dry_run)
    print_report(target_root, pack_dir, args.strategy, args.dry_run, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
