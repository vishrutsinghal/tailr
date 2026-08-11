#!/usr/bin/env python3
"""Read-only compatibility validation for a pinned official AWS AI-DLC pack."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


OFFICIAL_SOURCE = "https://github.com/awslabs/aidlc-workflows"
DEFAULT_MANIFEST = Path(".tailtrail") / "official-aidlc" / "manifest.json"
SUPPORTED_HOSTS = {"codex", "copilot", "claude", "generic"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PINNED_REVISION = re.compile(r"^(?:[0-9a-f]{7,64}|v[0-9][0-9A-Za-z._-]*)$")


def _safe_path(root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("manifest and pack paths must remain inside --root") from error
    return resolved


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _base(root: Path, manifest_path: Path) -> dict[str, Any]:
    return {
        "type": "tailtrail-official-aidlc-compatibility",
        "schema_version": "1",
        "root": root.as_posix(),
        "manifest": _relative(root, manifest_path),
        "read_only": True,
        "official_source": OFFICIAL_SOURCE,
        "issues": [],
    }


def _validate_manifest(root: Path, manifest_path: Path, manifest: Any) -> tuple[list[str], dict[str, Any]]:
    issues: list[str] = []
    details: dict[str, Any] = {"verified_files": 0, "total_files": 0}
    if not isinstance(manifest, dict):
        return ["manifest must be a JSON object"], details
    if manifest.get("schema_version") != "1":
        issues.append("manifest schema_version must be `1`")
    if manifest.get("type") != "tailtrail-official-aidlc-pack":
        issues.append("manifest type must be `tailtrail-official-aidlc-pack`")
    official = manifest.get("official")
    if not isinstance(official, dict):
        issues.append("manifest official metadata is required")
        official = {}
    source = str(official.get("source", "")).rstrip("/")
    if source != OFFICIAL_SOURCE:
        issues.append(f"official source must be `{OFFICIAL_SOURCE}`")
    revision = str(official.get("revision", ""))
    if not PINNED_REVISION.fullmatch(revision):
        issues.append("official revision must be a pinned commit hash or version tag, not a branch")
    license_info = official.get("license")
    if not isinstance(license_info, dict) or license_info.get("spdx") != "MIT-0":
        issues.append("official license must declare SPDX `MIT-0`")
        license_info = {}
    pack_root = manifest_path.parent
    license_file = str(license_info.get("file", ""))
    if not license_file:
        issues.append("official license file is required")
    else:
        try:
            if not _safe_path(pack_root, license_file).is_file():
                issues.append("declared official license file is missing")
        except ValueError:
            issues.append("official license file escapes the pack root")

    adapter = manifest.get("host_adapter")
    if not isinstance(adapter, dict):
        issues.append("host_adapter is required")
        adapter = {}
    host = str(adapter.get("host", ""))
    if host not in SUPPORTED_HOSTS:
        issues.append("host_adapter.host must be codex, copilot, claude, or generic")
    rules_path = str(adapter.get("rules_path", ""))
    if not rules_path:
        issues.append("host_adapter.rules_path is required")
    else:
        try:
            if not _safe_path(pack_root, rules_path).is_file():
                issues.append("declared host adapter rules_path is missing")
        except ValueError:
            issues.append("host_adapter.rules_path escapes the pack root")

    integrity = manifest.get("integrity")
    files = integrity.get("files") if isinstance(integrity, dict) else None
    if not isinstance(integrity, dict) or integrity.get("algorithm") != "sha256":
        issues.append("integrity.algorithm must be `sha256`")
    if not isinstance(files, list) or not files:
        issues.append("integrity.files must be a non-empty list")
        files = []
    seen: set[str] = set()
    declared_paths: set[str] = set()
    for index, entry in enumerate(files, start=1):
        details["total_files"] += 1
        if not isinstance(entry, dict):
            issues.append(f"integrity file {index} must be an object")
            continue
        path_value = str(entry.get("path", ""))
        expected = str(entry.get("sha256", "")).lower()
        if not path_value or path_value in seen:
            issues.append(f"integrity file {index} has a missing or duplicate path")
            continue
        seen.add(path_value)
        declared_paths.add(path_value)
        if not SHA256.fullmatch(expected):
            issues.append(f"integrity file {index} must have a lowercase SHA-256 hash")
            continue
        try:
            target = _safe_path(pack_root, path_value)
        except ValueError:
            issues.append(f"integrity file {index} escapes the pack root")
            continue
        if not target.is_file():
            issues.append(f"integrity file is missing: {path_value}")
            continue
        if _sha256(target) != expected:
            issues.append(f"integrity hash mismatch: {path_value}")
            continue
        details["verified_files"] += 1
    if license_file and license_file not in declared_paths:
        issues.append("official license file must be included in integrity.files")
    if rules_path and rules_path not in declared_paths:
        issues.append("host_adapter.rules_path must be included in integrity.files")
    return issues, details


def status(root: Path, manifest: str | Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    manifest_path = _safe_path(root, manifest or DEFAULT_MANIFEST)
    result = _base(root, manifest_path)
    if not manifest_path.is_file():
        result.update({
            "state": "not-installed",
            "compatible": False,
            "next_action": "Install a pinned official AI-DLC pack, then place its verified manifest at `.tailtrail/official-aidlc/manifest.json`.",
            "issues": ["official AIDLC manifest not found"],
        })
        return result
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        result.update({"state": "incompatible", "compatible": False, "next_action": "Repair or replace the manifest with a valid pinned official-pack manifest.", "issues": [f"manifest could not be read: {error}"]})
        return result
    issues, integrity = _validate_manifest(root, manifest_path, document)
    result.update({
        "official": document.get("official") if isinstance(document, dict) else None,
        "host_adapter": document.get("host_adapter") if isinstance(document, dict) else None,
        "integrity": integrity,
    })
    if not issues:
        result.update({"state": "compatible", "compatible": True, "next_action": "Phase A validation passed. The pack remains detected only; it is not executed or attached to a TailTrail run.", "issues": []})
        return result
    altered = any(issue.startswith(("integrity file is missing", "integrity hash mismatch")) for issue in issues)
    result.update({
        "state": "altered" if altered else "incompatible",
        "compatible": False,
        "next_action": "Restore the pinned official pack from its verified source and regenerate or repair the manifest before enabling a future integration phase.",
        "issues": issues,
    })
    return result


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# TailTrail Official AI-DLC Compatibility", "", f"**State:** `{payload['state']}`", f"**Compatible:** `{str(payload['compatible']).lower()}`", f"**Manifest:** `{payload['manifest']}`", "", "## Integrity", "", f"- Verified files: `{payload.get('integrity', {}).get('verified_files', 0)}` / `{payload.get('integrity', {}).get('total_files', 0)}`"]
    official = payload.get("official")
    if isinstance(official, dict):
        lines.extend(["", "## Official pack", "", f"- Source: `{official.get('source', '')}`", f"- Revision: `{official.get('revision', '')}`", f"- License: `{official.get('license', {}).get('spdx', '') if isinstance(official.get('license'), dict) else ''}`"])
    adapter = payload.get("host_adapter")
    if isinstance(adapter, dict):
        lines.extend([f"- Host adapter: `{adapter.get('host', '')}`", f"- Rules path: `{adapter.get('rules_path', '')}`"])
    lines.extend(["", "## Findings", ""])
    lines.extend([f"- {item}" for item in payload.get("issues", [])] or ["- No compatibility findings."])
    lines.extend(["", "## Next action", "", payload["next_action"], ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    status_parser = sub.add_parser("status", help="Read and validate a pinned official AIDLC pack manifest.")
    status_parser.add_argument("--root", type=Path, default=Path.cwd())
    status_parser.add_argument("--manifest")
    status_parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args()
    try:
        payload = status(args.root, args.manifest)
    except ValueError as error:
        print(f"Official AIDLC compatibility error: {error}")
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True) if args.format == "json" else render_markdown(payload))
    return 0 if payload["state"] in {"compatible", "not-installed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
