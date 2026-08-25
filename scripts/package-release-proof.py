#!/usr/bin/env python3
"""Inspect TailTrail wheel and sdist inventories without executing artifact code."""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
import zipfile
from pathlib import Path
from typing import Any


FORBIDDEN_FRAGMENTS = (
    ".DS_Store", "__pycache__", ".idea/", ".tailtrail/",
    "AI-MODE-INSPIRED-ADDITIONS.md", "DURABLE-WORKFLOW-RUNTIME.local-backup.md",
)
SECRET_NAMES = {".env", "id_rsa", "id_ed25519"}
SECRET_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_names(names: list[str]) -> list[str]:
    issues: list[str] = []
    for name in names:
        normalized = name.replace("\\", "/")
        parts = [part for part in normalized.split("/") if part]
        if any(fragment in normalized for fragment in FORBIDDEN_FRAGMENTS):
            issues.append(f"forbidden artifact path: {normalized}")
        if any(part in SECRET_NAMES or Path(part).suffix.lower() in SECRET_SUFFIXES for part in parts):
            issues.append(f"secret-like artifact path: {normalized}")
    return issues


def inspect_wheel(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        issues = _safe_names(names)
        try:
            package_manifest = json.loads(archive.read("tailtrail/package-manifest.json"))
            integrity = json.loads(archive.read("tailtrail/package-integrity.json"))
        except (KeyError, json.JSONDecodeError) as error:
            return {"artifact": path.as_posix(), "kind": "wheel", "valid": False, "issues": [f"manifest error: {error}"]}
        files = integrity.get("files", {})
        if not isinstance(files, dict):
            issues.append("integrity files must be an object")
            files = {}
        for relative, expected in files.items():
            member = f"tailtrail/{relative}"
            try:
                actual = sha256(archive.read(member))
            except KeyError:
                issues.append(f"integrity member missing: {member}")
                continue
            if actual != expected:
                issues.append(f"integrity mismatch: {member}")
        for relative in package_manifest.get("runtime_required", []):
            if f"tailtrail/{relative}" not in names:
                issues.append(f"runtime member missing: tailtrail/{relative}")
    return {"artifact": path.as_posix(), "kind": "wheel", "sha256": sha256(path.read_bytes()), "entries": len(names), "integrity_files": len(files), "valid": not issues, "issues": issues}


def inspect_sdist(path: Path) -> dict[str, Any]:
    with tarfile.open(path) as archive:
        names = archive.getnames()
        issues = _safe_names(names)
        stripped = {"/".join(name.replace("\\", "/").split("/")[1:]) for name in names}
        required = {"setup.py", "pyproject.toml", "package-manifest.json", "scripts/tailtrail.py", "tailtrail/cli.py"}
        for relative in sorted(required - stripped):
            issues.append(f"sdist member missing: {relative}")
    return {"artifact": path.as_posix(), "kind": "sdist", "sha256": sha256(path.read_bytes()), "entries": len(names), "valid": not issues, "issues": issues}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--sdist", type=Path, required=True)
    args = parser.parse_args()
    reports = [inspect_wheel(args.wheel), inspect_sdist(args.sdist)]
    payload = {"schema_version": "1", "type": "tailtrail-package-release-proof", "valid": all(item["valid"] for item in reports), "artifacts": reports}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
