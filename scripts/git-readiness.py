#!/usr/bin/env python3
"""Read-only Git preflight for TailTrail Mode A recovery."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=False)


def output(root: Path, *args: str) -> str | None:
    result = git(root, *args)
    return result.stdout.strip() if result.returncode == 0 else None


def readiness(root: Path) -> dict[str, Any]:
    root = root.resolve()
    repo = output(root, "rev-parse", "--show-toplevel")
    if repo is None:
        return {"schema_version": "1", "type": "tailtrail-git-readiness", "root": root.as_posix(), "ready": False, "issues": ["not a Git repository"], "dirty_paths": []}
    repository = Path(repo)
    head = output(repository, "rev-parse", "HEAD")
    branch = output(repository, "symbolic-ref", "--quiet", "--short", "HEAD")
    identity = output(repository, "var", "GIT_COMMITTER_IDENT")
    status = git(repository, "status", "--porcelain=v1", "--untracked-files=all")
    dirty = [line[3:] for line in status.stdout.splitlines() if line.strip()]
    issues: list[str] = []
    if head is None: issues.append("repository has no current HEAD")
    if branch is None: issues.append("HEAD is detached; a named branch is required")
    if not identity: issues.append("Git committer identity is not configured")
    if dirty: issues.append("worktree is not clean")
    return {"schema_version": "1", "type": "tailtrail-git-readiness", "root": repository.as_posix(), "ready": not issues, "head": head, "branch": branch, "committer_identity": bool(identity), "dirty_paths": dirty, "issues": issues, "mode": "mode-a-local-checkpoints"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Report whether a repository is safe for TailTrail Mode A checkpoints.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        report = readiness(args.root)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ready"] else 1
    except OSError as error:
        print(f"Git readiness error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
