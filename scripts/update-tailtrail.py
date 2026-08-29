#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPORT_ROOT = ROOT.parent if (ROOT / "__init__.py").is_file() else ROOT
try:
    sys.path.remove(IMPORT_ROOT.as_posix())
except ValueError:
    pass
sys.path.insert(0, IMPORT_ROOT.as_posix())
UPDATE_COPILOT_PATH = ROOT / "scripts" / "update-copilot.py"
SPEC = importlib.util.spec_from_file_location("tailtrail_update_copilot", UPDATE_COPILOT_PATH)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("Unable to load scripts/update-copilot.py")
update_copilot = importlib.util.module_from_spec(SPEC)
sys.modules["tailtrail_update_copilot"] = update_copilot
SPEC.loader.exec_module(update_copilot)


def main() -> int:
    parser = argparse.ArgumentParser(description="Update an installed TailTrail pack in a target project.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target project root.")
    parser.add_argument("--pack-dir", help="Existing TailTrail pack folder. Defaults to auto-detection.")
    parser.add_argument("--strategy", choices=["preserve", "backup-overwrite"], default="preserve", help="How to handle locally modified TailTrail-managed files.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing files.")
    args = parser.parse_args()
    from tailtrail.install.cli import main as installer_main

    forwarded = ["update", "--host", "all", "--target", args.root.resolve().as_posix()]
    if args.strategy == "backup-overwrite":
        forwarded.append("--force")
    if args.dry_run:
        forwarded.append("--dry-run")
    status = installer_main(forwarded)
    if status != 0:
        return status

    # Projects installed before the transactional host adapters keep their
    # executable pack in <target>/<pack-dir>. Host payload updates alone do not
    # refresh that launcher, so update the manifest-owned legacy pack too.
    target = args.root.resolve()
    pack_dir = update_copilot.install_copilot.validate_pack_dir(args.pack_dir) if args.pack_dir else update_copilot.infer_pack_dir(target)
    if (target / pack_dir / update_copilot.install_copilot.MANIFEST_NAME).is_file():
        report = update_copilot.update_copilot(target, pack_dir, args.strategy, args.dry_run)
        update_copilot.print_report(target, pack_dir, args.strategy, args.dry_run, report)
        if report.conflicts:
            return 2
    return status


if __name__ == "__main__":
    raise SystemExit(main())
