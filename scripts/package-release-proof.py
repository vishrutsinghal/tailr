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


def _bundle_issues(names: list[str], read: Any, prefix: str) -> tuple[list[str], int, dict[str, Any]]:
    """Verify the complete inner bundle inventory inside one publication artifact."""
    issues: list[str] = []
    manifest_name = f"{prefix}aidlc-rules/manifest.json"
    try:
        manifest = json.loads(read(manifest_name))
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as error:
        return [f"bundle manifest error: {error}"], 0, {}
    rows = (manifest.get("integrity") or {}).get("files")
    if (
        manifest.get("schema_version") != "2"
        or manifest.get("type") != "tailtrail-bundled-official-aidlc-pack"
        or not isinstance(rows, list)
        or not rows
    ):
        return ["bundle manifest is not a complete closed schema-v2 inventory"], 0, manifest
    declared: dict[str, str] = {}
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            issues.append(f"bundle integrity entry {index} is malformed")
            continue
        relative = row.get("path")
        expected = row.get("sha256")
        if not isinstance(relative, str) or not relative or relative.startswith("/") or ".." in Path(relative).parts:
            issues.append(f"bundle integrity entry {index} has an unsafe path")
            continue
        if not isinstance(expected, str) or len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
            issues.append(f"bundle integrity entry {index} has an invalid SHA-256")
            continue
        if relative in declared:
            issues.append(f"bundle integrity path is duplicated: {relative}")
            continue
        declared[relative] = expected
    actual = {
        name.removeprefix(f"{prefix}aidlc-rules/")
        for name in names
        if name.startswith(f"{prefix}aidlc-rules/")
        and name != manifest_name
        and not name.endswith("/")
    }
    if actual != set(declared):
        issues.append(
            "bundle inventory mismatch: missing "
            f"{sorted(set(declared) - actual)}, unexpected {sorted(actual - set(declared))}"
        )
    for relative, expected in sorted(declared.items()):
        member = f"{prefix}aidlc-rules/{relative}"
        if member not in names:
            continue
        if sha256(read(member)) != expected:
            issues.append(f"bundle integrity mismatch: {member}")
    return issues, len(declared) + 1, manifest


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
        bundle_issues, bundle_files, bundle_manifest = _bundle_issues(names, archive.read, "tailtrail/")
        issues.extend(bundle_issues)
    return {"artifact": path.as_posix(), "kind": "wheel", "sha256": sha256(path.read_bytes()), "entries": len(names), "integrity_files": len(files), "bundle_files": bundle_files, "bundle_identity": (bundle_manifest.get("official") or {}), "valid": not issues, "issues": issues}


def inspect_sdist(path: Path) -> dict[str, Any]:
    with tarfile.open(path) as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        file_names = [member.name for member in members if member.isfile()]
        issues = _safe_names(names)
        stripped = {"/".join(name.replace("\\", "/").split("/")[1:]) for name in names}
        required = {"setup.py", "pyproject.toml", "package-manifest.json", "scripts/tailtrail.py", "tailtrail/cli.py"}
        for relative in sorted(required - stripped):
            issues.append(f"sdist member missing: {relative}")
        roots = sorted({name.split("/", 1)[0] + "/" for name in names if "/aidlc-rules/manifest.json" in name})
        if len(roots) != 1:
            bundle_issues, bundle_files, bundle_manifest = (["sdist must contain exactly one bundled AIDLC manifest"], 0, {})
        else:
            def read_member(name: str) -> bytes:
                extracted = archive.extractfile(name)
                if extracted is None:
                    raise KeyError(name)
                return extracted.read()
            bundle_issues, bundle_files, bundle_manifest = _bundle_issues(file_names, read_member, roots[0])
        issues.extend(bundle_issues)
    return {"artifact": path.as_posix(), "kind": "sdist", "sha256": sha256(path.read_bytes()), "entries": len(names), "bundle_files": bundle_files, "bundle_identity": (bundle_manifest.get("official") or {}), "valid": not issues, "issues": issues}


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
