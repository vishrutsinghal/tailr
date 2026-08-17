#!/usr/bin/env python3

from __future__ import annotations

import argparse
import io
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_NAMES = {".DS_Store", ".git", ".idea", ".tailtrail", ".video-tools", "__MACOSX", "__pycache__", "aidlc-rules"}


def ignore(directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in SKIP_NAMES}


def run(root: Path, args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run([sys.executable, *args], cwd=root, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout, result.stderr


def run_external(root: Path, args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(args, cwd=root, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout, result.stderr


def fresh_clone(source: Path, destination: Path) -> str:
    """Create a clone-like tracked snapshot without copying local runtime state."""
    archive = subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=source, capture_output=True, check=False)
    if archive.returncode == 0:
        destination.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as bundle:
            members = [
                member
                for member in bundle.getmembers()
                if "__MACOSX" not in Path(member.name).parts and Path(member.name).name not in {".DS_Store"}
            ]
            if any(Path(member.name).is_absolute() or ".." in Path(member.name).parts for member in members):
                raise RuntimeError("git archive produced an unsafe member path")
            bundle.extractall(destination, members=members)
        return "git-archive"
    shutil.copytree(source, destination, ignore=ignore)
    return "copytree-fallback"


def smoke(root: Path) -> list[str]:
    failures: list[str] = []
    commands = [
        ["tailtrail_cli.py", "hello"],
        ["scripts/tailtrail.py", "help"],
        ["scripts/tailtrail.py", "hello"],
        ["scripts/tailtrail.py", "start", "fix Sonar issue", "--changed", "missing-file.py"],
        ["scripts/tailtrail.py", "graph", "--changed", "scripts/tailtrail.py"],
        ["scripts/tailtrail.py", "quality", "scan", "--root", "."],
        ["scripts/tailtrail.py", "test", "plan", "--root", ".", "--changed", "scripts/tailtrail.py"],
        ["scripts/release-check.py"],
        ["scripts/tailtrail.py", "doctor"],
    ]
    for command in commands:
        code, stdout, stderr = run(root, command)
        if code != 0:
            failures.append(f"{' '.join(command)} failed with {code}: {(stderr or stdout).strip()[:500]}")
    installed_tailtrail = shutil.which("tailtrail")
    if installed_tailtrail:
        code, stdout, stderr = run_external(root, [installed_tailtrail, "hello"])
        if code != 0:
            failures.append(f"tailtrail hello failed with {code}: {(stderr or stdout).strip()[:500]}")
    else:
        print("tailtrail executable not found on PATH; skipping installed entry point smoke check.")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a dependency-free fresh-clone smoke test for TailTrail.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Source checkout to copy into a temporary fresh-clone directory.")
    parser.add_argument("--keep-temp", action="store_true", help="Keep the temporary fresh-clone directory for debugging.")
    args = parser.parse_args()

    source = args.root.resolve()
    if not (source / "scripts" / "tailtrail.py").is_file():
        print(f"Not a TailTrail checkout: {source}", file=sys.stderr)
        return 2

    temp_root = Path(tempfile.mkdtemp(prefix="tailtrail-smoke-"))
    clone = temp_root / "tailtrail"
    snapshot_method = fresh_clone(source, clone)
    failures = smoke(clone)

    if failures:
        print(f"TailTrail smoke test failed in {clone}", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        if not args.keep_temp:
            shutil.rmtree(temp_root, ignore_errors=True)
        return 1

    print("TailTrail smoke test passed.")
    print(f"Snapshot method: {snapshot_method}")
    print(f"Fresh clone path: {clone}")
    if args.keep_temp:
        print("Temporary directory kept for inspection.")
    else:
        shutil.rmtree(temp_root, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
