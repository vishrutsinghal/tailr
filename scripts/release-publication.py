#!/usr/bin/env python3
"""Observe one GitHub release asset and write a sanitized publication receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


REPOSITORY = "vishrutsinghal/tailr"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observe(version: str, commit: str, artifact: Path, output: Path) -> dict[str, object]:
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise ValueError("commit must be one full lowercase Git SHA")
    if not version or any(part == "" or not part.isdigit() for part in version.split(".")) or len(version.split(".")) != 3:
        raise ValueError("version must be semantic major.minor.patch")
    if not artifact.is_file() or artifact.name != f"tailtrail-{version}-py3-none-any.whl":
        raise ValueError("artifact must be the canonical wheel for --version")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if not run_id.isdigit():
        raise ValueError("GITHUB_RUN_ID is required observed workflow provenance")
    tag = f"v{version}"
    result = subprocess.run(["gh", "release", "view", tag, "--repo", REPOSITORY, "--json", "url,tagName,assets"], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise ValueError((result.stderr or result.stdout).strip() or "GitHub release observation failed")
    remote = json.loads(result.stdout)
    names = {item.get("name") for item in remote.get("assets", []) if isinstance(item, dict)}
    if remote.get("tagName") != tag or artifact.name not in names:
        raise ValueError("published release tag or canonical wheel asset does not match")
    payload = {
        "schema_version": "1",
        "type": "tailtrail-release-publication-receipt",
        "observed": True,
        "provider": "github",
        "repository": REPOSITORY,
        "version": version,
        "commit": commit,
        "release_url": remote["url"],
        "artifact": artifact.name,
        "artifact_sha256": digest(artifact),
        "identity_verified": True,
        "workflow_run_url": f"https://github.com/{REPOSITORY}/actions/runs/{run_id}",
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("observe",))
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = observe(args.version, args.commit, args.artifact, args.output)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(json.dumps({"type": "tailtrail-release-publication-receipt", "observed": False, "issues": [str(error)]}, sort_keys=True))
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
