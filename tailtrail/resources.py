"""Package-owned resource location and integrity verification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def package_root() -> Path:
    return Path(__file__).resolve().parent


def _relative_resource(value: Any) -> Path | None:
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path


def verify_package(root: Path | None = None) -> list[str]:
    root = root or package_root()
    integrity_path = root / "package-integrity.json"
    manifest_path = root / "package-manifest.json"
    issues: list[str] = []
    if not manifest_path.is_file():
        return ["missing package resource: package-manifest.json"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ["corrupt package resource: package-manifest.json"]
    runtime_required = manifest.get("runtime_required")
    if not isinstance(runtime_required, list):
        return ["corrupt package resource: package-manifest.json"]
    for value in runtime_required:
        relative = _relative_resource(value)
        if relative is None:
            issues.append("corrupt package resource: package-manifest.json")
        elif not (root / relative).is_file():
            issues.append(f"missing package resource: {relative.as_posix()}")
    if not integrity_path.is_file():
        issues.append("missing package resource: package-integrity.json")
        return issues
    try:
        integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        issues.append("corrupt package resource: package-integrity.json")
        return issues
    if integrity.get("schema_version") != "1" or integrity.get("algorithm") != "sha256":
        issues.append("corrupt package resource: package-integrity.json")
        return issues
    files = integrity.get("files")
    if not isinstance(files, dict):
        issues.append("corrupt package resource: package-integrity.json")
        return issues
    for value, expected in files.items():
        relative = _relative_resource(value)
        if relative is None or not isinstance(expected, str) or len(expected) != 64:
            issues.append("corrupt package resource: package-integrity.json")
            continue
        target = root / relative
        if not target.is_file():
            issues.append(f"missing package resource: {relative.as_posix()}")
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != expected:
            issues.append(f"corrupt package resource: {relative.as_posix()}")
    return issues
