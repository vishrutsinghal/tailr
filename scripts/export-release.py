#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PUBLIC_ONLY_FILES = {
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/docs_feedback.md",
    ".github/ISSUE_TEMPLATE/feature_request.md",
    ".github/ISSUE_TEMPLATE/security_note.md",
    ".github/pull_request_template.md",
    ".github/workflows/tailtrail-ci.yml",
    "ARCHITECTURE.md",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "DEMO.md",
    "LICENSE",
    "NOTICE.md",
    "PUBLIC-CLAIMS.md",
    "PUBLIC-RELEASE-METADATA.md",
    "PUBLIC-ROADMAP.md",
    "RELEASE-CHECKLIST.md",
    "SECURITY.md",
    "SUPPORT.md",
    "VERSIONING.md",
    "scripts/public-doc-audit.py",
    "scripts/release-check.py",
    "scripts/smoke-test.py",
}

ADMIN_ONLY_FILES = {
    "ADMIN-RELEASE-MODES.md",
    "DESIGN.md",
    "scripts/export-release.py",
}

INTERNAL_EXCLUDED_FILES = {
    *PUBLIC_ONLY_FILES,
    *ADMIN_ONLY_FILES,
    "ENTERPRISE-REVIEW.md",
    "HONEST-REVIEW.md",
    "HONEST-REVIEW-IMPLEMENTATION-PLAN.md",
    "ROADMAP.md",
    "scripts/check-tailtrail.py",
    "V2-IMPLEMENTATION-GUIDE.md",
}

INTERNAL_EXCLUDED_PREFIXES = (
    ".github/",
    "benchmarks/results/",
)

PUBLIC_EXCLUDED_FILES = {
    *ADMIN_ONLY_FILES,
}

PUBLIC_MARKER = ".tailtrail-public-release"
INTERNAL_MARKER = ".tailtrail-internal-release"


def git_files() -> list[str]:
    result = subprocess.run(["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise SystemExit(result.stderr or "git ls-files failed")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def should_include(path: str, mode: str) -> bool:
    if ".tailtrail" in Path(path).parts:
        return False
    if "__pycache__" in Path(path).parts:
        return False
    if mode == "internal":
        if path in INTERNAL_EXCLUDED_FILES:
            return False
        if any(path.startswith(prefix) for prefix in INTERNAL_EXCLUDED_PREFIXES):
            return False
    if mode == "public" and path in PUBLIC_EXCLUDED_FILES:
        return False
    return True


def copy_file(relative_path: str, target: Path) -> None:
    source = ROOT / relative_path
    destination = target / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def write_internal_manifest(target: Path) -> None:
    manifest = target / ".codex-plugin" / "plugin.json"
    if not manifest.exists():
        return
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["license"] = "Internal-Use-Only"
    data["description"] = data.get("description", "TailTrail").replace("public", "internal")
    manifest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_marker(target: Path, mode: str) -> None:
    marker = target / (PUBLIC_MARKER if mode == "public" else INTERNAL_MARKER)
    marker.write_text(f"TailTrail {mode} distribution marker.\n", encoding="utf-8")


def export(mode: str, target: Path, force: bool) -> list[str]:
    if target.exists():
        if not force:
            raise SystemExit(f"Target already exists: {target}. Re-run with --force to replace it.")
        if target.resolve() == ROOT:
            raise SystemExit("Refusing to overwrite the source repository.")
        shutil.rmtree(target)
    target.mkdir(parents=True)

    copied: list[str] = []
    for relative_path in git_files():
        if should_include(relative_path, mode):
            copy_file(relative_path, target)
            copied.append(relative_path)

    if mode == "internal":
        write_internal_manifest(target)
    write_marker(target, mode)
    copied.append(PUBLIC_MARKER if mode == "public" else INTERNAL_MARKER)
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description="Admin-only TailTrail release mode exporter.")
    parser.add_argument("--mode", choices=("internal", "public"), required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--list", action="store_true", help="List files that would be included without writing.")
    args = parser.parse_args()

    selected = [path for path in git_files() if should_include(path, args.mode)]
    marker = PUBLIC_MARKER if args.mode == "public" else INTERNAL_MARKER
    if args.list:
        print(f"TailTrail {args.mode} release files:")
        for path in [*selected, marker]:
            print(path)
        return 0

    copied = export(args.mode, args.target.resolve(), args.force)
    print(f"Exported TailTrail {args.mode} distribution to {args.target.resolve()}")
    print(f"Files written: {len(copied)}")
    if args.mode == "internal":
        print("Internal distribution excludes public release, license, contribution, conduct, security, release-check, roadmap, and admin files.")
    else:
        print("Public distribution includes public release files and enables release-check through the public marker.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
