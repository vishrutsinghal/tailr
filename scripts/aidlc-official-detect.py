#!/usr/bin/env python3
"""Read-only compatibility validation for a pinned official AWS AI-DLC pack."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


OFFICIAL_SOURCE = "https://github.com/awslabs/aidlc-workflows"
DEFAULT_MANIFEST = Path(".tailtrail") / "official-aidlc" / "manifest.json"
SUPPORTED_HOSTS = {"codex", "copilot", "claude", "generic"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PINNED_REVISION = re.compile(r"^(?:[0-9a-f]{7,64}|v[0-9][0-9A-Za-z._-]*)$")
PUBLISHED_REVISION = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
FULL_COMMIT = re.compile(r"^[0-9a-f]{40}$")
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
MINIMUM_TAILTRAIL_VERSION = "1.1.0"
MAXIMUM_TAILTRAIL_VERSION_EXCLUSIVE = "2.0.0"
BUNDLE_FORMAT_VERSION = "1"
REQUIRED_REQUIREMENTS_CAPABILITIES = {
    "aws-aidlc-rules/core-workflow.md",
    "aws-aidlc-rule-details/inception/requirements-analysis.md",
    "aws-aidlc-rule-details/common/question-format-guide.md",
    "aws-aidlc-rule-details/common/content-validation.md",
    "aws-aidlc-rule-details/common/session-continuity.md",
}


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


def _relative_manifest_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        return None
    return path.as_posix()


def _actual_inventory(pack_root: Path, manifest_path: Path) -> tuple[dict[str, str], list[str]]:
    inventory: dict[str, str] = {}
    issues: list[str] = []
    for path in sorted(pack_root.rglob("*")):
        relative = path.relative_to(pack_root).as_posix()
        if path == manifest_path:
            continue
        if path.is_symlink():
            issues.append(f"bundle inventory contains a symbolic link: {relative}")
            continue
        if path.is_dir():
            continue
        if not path.is_file():
            issues.append(f"bundle inventory contains a non-regular file: {relative}")
            continue
        inventory[relative] = _sha256(path)
    return inventory, issues


def _validate_integrity(pack_root: Path, manifest_path: Path, value: Any) -> tuple[list[str], dict[str, Any], set[str]]:
    issues: list[str] = []
    details: dict[str, Any] = {"verified_files": 0, "total_files": 0}
    files = value.get("files") if isinstance(value, dict) else None
    if not isinstance(value, dict) or set(value) - {"algorithm", "files"}:
        issues.append("integrity must be a closed object with algorithm and files")
    if not isinstance(value, dict) or value.get("algorithm") != "sha256":
        issues.append("integrity.algorithm must be `sha256`")
    if not isinstance(files, list) or not files:
        issues.append("integrity.files must be a non-empty list")
        files = []
    declared_paths: set[str] = set()
    declared_hashes: dict[str, str] = {}
    for index, entry in enumerate(files, start=1):
        details["total_files"] += 1
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            issues.append(f"integrity file {index} must be an object")
            continue
        path_value = _relative_manifest_path(entry.get("path"))
        expected = entry.get("sha256")
        if path_value is None:
            issues.append(f"integrity file {index} has an unsafe path")
            continue
        if path_value in declared_paths:
            issues.append(f"integrity file {index} has a duplicate path")
            continue
        declared_paths.add(path_value)
        if not isinstance(expected, str) or not SHA256.fullmatch(expected):
            issues.append(f"integrity file {index} must have a lowercase SHA-256 hash")
            continue
        declared_hashes[path_value] = expected
    actual, actual_issues = _actual_inventory(pack_root, manifest_path)
    issues.extend(actual_issues)
    for path in sorted(declared_paths - set(actual)):
        issues.append(f"integrity file is missing: {path}")
    for path in sorted(set(actual) - declared_paths):
        issues.append(f"integrity inventory has an unexpected file: {path}")
    for path in sorted(declared_paths & set(actual)):
        if declared_hashes.get(path) != actual[path]:
            issues.append(f"integrity hash mismatch: {path}")
        else:
            details["verified_files"] += 1
    return issues, details, declared_paths


def _closed_object(value: Any, required: set[str], label: str, *, optional: set[str] | None = None) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(value, dict):
        return {}, [f"{label} must be an object"]
    optional = optional or set()
    issues = [f"{label} has unsupported fields"] if set(value) - required - optional else []
    missing = required - set(value)
    if missing:
        issues.append(f"{label} is missing required fields: {', '.join(sorted(missing))}")
    return value, issues


def _validate_v1(manifest_path: Path, manifest: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    issues: list[str] = []
    if set(manifest) != {"schema_version", "type", "official", "host_adapter", "integrity"}:
        issues.append("schema-v1 manifest must contain only schema_version, type, official, host_adapter, and integrity")
    if manifest.get("type") != "tailtrail-official-aidlc-pack":
        issues.append("manifest type must be `tailtrail-official-aidlc-pack`")
    official, closed = _closed_object(
        manifest.get("official"), {"source", "revision", "license"}, "official", optional={"commit"}
    )
    issues.extend(closed)
    if str(official.get("source", "")).rstrip("/") != OFFICIAL_SOURCE:
        issues.append(f"official source must be `{OFFICIAL_SOURCE}`")
    if not PINNED_REVISION.fullmatch(str(official.get("revision", ""))):
        issues.append("official revision must be a pinned commit hash or version tag, not a branch")
    license_info, closed = _closed_object(
        official.get("license"), {"spdx", "file"}, "official license", optional={"sha256"}
    )
    issues.extend(closed)
    if license_info.get("spdx") != "MIT-0":
        issues.append("official license must declare SPDX `MIT-0`")
    adapter, closed = _closed_object(manifest.get("host_adapter"), {"host", "rules_path"}, "host_adapter")
    issues.extend(closed)
    if adapter.get("host") not in SUPPORTED_HOSTS:
        issues.append("host_adapter.host must be codex, copilot, claude, or generic")
    pack_root = manifest_path.parent
    integrity_issues, details, declared = _validate_integrity(pack_root, manifest_path, manifest.get("integrity"))
    issues.extend(integrity_issues)
    for label, value in (("official license file", license_info.get("file")), ("host_adapter.rules_path", adapter.get("rules_path"))):
        path = _relative_manifest_path(value)
        if path is None:
            issues.append(f"{label} is required and must be a safe relative path")
        elif path not in declared:
            issues.append(f"{label} must be included in integrity.files")
    return issues, details


def _validate_v2(manifest_path: Path, manifest: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    issues: list[str] = []
    required_root = {"schema_version", "type", "bundle", "official", "compatibility", "required_capabilities", "integrity"}
    if set(manifest) != required_root:
        issues.append("schema-v2 manifest must contain exactly the closed bundle contract fields")
    if manifest.get("type") != "tailtrail-bundled-official-aidlc-pack":
        issues.append("schema-v2 manifest type must be `tailtrail-bundled-official-aidlc-pack`")
    bundle, closed = _closed_object(
        manifest.get("bundle"), {"format_version", "tailtrail_version", "bundle_version", "created_from"}, "bundle"
    )
    issues.extend(closed)
    if bundle.get("format_version") != BUNDLE_FORMAT_VERSION:
        issues.append(f"bundle.format_version must be `{BUNDLE_FORMAT_VERSION}`")
    if not SEMVER.fullmatch(str(bundle.get("tailtrail_version", ""))):
        issues.append("bundle.tailtrail_version must be a semantic version")
    if bundle.get("created_from") != "verified-upstream-release":
        issues.append("bundle.created_from must be `verified-upstream-release`")

    official, closed = _closed_object(
        manifest.get("official"), {"source", "revision", "commit", "source_archive_sha256", "license"}, "official"
    )
    issues.extend(closed)
    if official.get("source") != OFFICIAL_SOURCE:
        issues.append(f"official source must be `{OFFICIAL_SOURCE}`")
    if not PUBLISHED_REVISION.fullmatch(str(official.get("revision", ""))):
        issues.append("schema-v2 official revision must be a published version tag")
    if not FULL_COMMIT.fullmatch(str(official.get("commit", ""))):
        issues.append("schema-v2 official commit must be a full lowercase 40-character SHA")
    if not SHA256.fullmatch(str(official.get("source_archive_sha256", ""))):
        issues.append("official.source_archive_sha256 must be a lowercase SHA-256 hash")
    license_info, closed = _closed_object(official.get("license"), {"spdx", "file", "sha256"}, "official license")
    issues.extend(closed)
    if license_info.get("spdx") != "MIT-0" or license_info.get("file") != "LICENSE":
        issues.append("schema-v2 official license must declare SPDX `MIT-0` at `LICENSE`")
    if not SHA256.fullmatch(str(license_info.get("sha256", ""))):
        issues.append("official license sha256 must be a lowercase SHA-256 hash")

    compatibility, closed = _closed_object(
        manifest.get("compatibility"),
        {"minimum_tailtrail_version", "maximum_tailtrail_version_exclusive", "manifest_schema", "supported_hosts"},
        "compatibility",
    )
    issues.extend(closed)
    if compatibility.get("minimum_tailtrail_version") != MINIMUM_TAILTRAIL_VERSION:
        issues.append(f"minimum TailTrail version must be `{MINIMUM_TAILTRAIL_VERSION}`")
    if compatibility.get("maximum_tailtrail_version_exclusive") != MAXIMUM_TAILTRAIL_VERSION_EXCLUSIVE:
        issues.append(f"maximum TailTrail version must be `{MAXIMUM_TAILTRAIL_VERSION_EXCLUSIVE}`")
    if compatibility.get("manifest_schema") != "2":
        issues.append("compatibility.manifest_schema must be `2`")
    hosts = compatibility.get("supported_hosts")
    if not isinstance(hosts, list) or len(hosts) != len(set(hosts)) or set(hosts) != {"codex", "copilot", "claude"}:
        issues.append("schema-v2 supported_hosts must contain codex, copilot, and claude exactly once")

    capabilities, closed = _closed_object(manifest.get("required_capabilities"), {"requirements"}, "required_capabilities")
    issues.extend(closed)
    requirement_paths = capabilities.get("requirements")
    if not isinstance(requirement_paths, list) or any(_relative_manifest_path(path) is None for path in requirement_paths):
        issues.append("required_capabilities.requirements must contain safe relative paths")
        requirement_paths = []
    elif len(requirement_paths) != len(set(requirement_paths)):
        issues.append("required_capabilities.requirements must not contain duplicates")
    elif not REQUIRED_REQUIREMENTS_CAPABILITIES.issubset(requirement_paths):
        issues.append("required_capabilities.requirements is missing a mandatory Requirements file")

    pack_root = manifest_path.parent
    integrity_issues, details, declared = _validate_integrity(pack_root, manifest_path, manifest.get("integrity"))
    issues.extend(integrity_issues)
    for path in ["LICENSE", "PROVENANCE.json", "BUNDLE_VERSION", "VERSION", *requirement_paths]:
        if path not in declared:
            issues.append(f"schema-v2 required file must be included in integrity.files: {path}")
    integrity_value = manifest.get("integrity")
    integrity_files = integrity_value.get("files", []) if isinstance(integrity_value, dict) else []
    if license_info.get("sha256") and license_info.get("sha256") != next(
        (entry.get("sha256") for entry in integrity_files if isinstance(entry, dict) and entry.get("path") == "LICENSE"), None
    ):
        issues.append("official license hash must agree with integrity.files")

    provenance_path = pack_root / "PROVENANCE.json"
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        issues.append(f"PROVENANCE.json could not be read: {error}")
        provenance = {}
    expected_pairs = (
        (official.get("source"), provenance.get("official", {}).get("source"), "official source"),
        (official.get("revision"), provenance.get("official", {}).get("revision"), "official revision"),
        (official.get("commit"), provenance.get("official", {}).get("commit"), "official commit"),
        (official.get("source_archive_sha256"), provenance.get("official", {}).get("archive", {}).get("sha256"), "source archive hash"),
        (license_info.get("sha256"), provenance.get("official", {}).get("license", {}).get("sha256"), "license hash"),
        (bundle.get("format_version"), provenance.get("bundle", {}).get("format_version"), "bundle format version"),
        (compatibility.get("minimum_tailtrail_version"), provenance.get("compatibility", {}).get("minimum_tailtrail_version"), "minimum TailTrail version"),
        (compatibility.get("maximum_tailtrail_version_exclusive"), provenance.get("compatibility", {}).get("maximum_tailtrail_version_exclusive"), "maximum TailTrail version"),
        (hosts, provenance.get("compatibility", {}).get("supported_hosts"), "supported hosts"),
    )
    for manifest_value, provenance_value, label in expected_pairs:
        if manifest_value != provenance_value:
            issues.append(f"manifest and PROVENANCE.json disagree on {label}")
    bundle_version_path = pack_root / "BUNDLE_VERSION"
    try:
        observed_bundle_version = bundle_version_path.read_text(encoding="utf-8").strip()
    except OSError as error:
        issues.append(f"BUNDLE_VERSION could not be read: {error}")
    else:
        if bundle.get("bundle_version") != observed_bundle_version:
            issues.append("manifest bundle_version disagrees with BUNDLE_VERSION")
    return issues, details


def _validate_manifest(root: Path, manifest_path: Path, manifest: Any) -> tuple[list[str], dict[str, Any]]:
    if not isinstance(manifest, dict):
        return ["manifest must be a JSON object"], {"verified_files": 0, "total_files": 0}
    schema_version = manifest.get("schema_version")
    if schema_version == "1":
        return _validate_v1(manifest_path, manifest)
    if schema_version == "2":
        return _validate_v2(manifest_path, manifest)
    return ["manifest schema_version must be `1` or `2`"], {"verified_files": 0, "total_files": 0}


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
    altered = any(issue.startswith((
        "integrity file is missing",
        "integrity hash mismatch",
        "integrity inventory has an unexpected file",
        "bundle inventory contains a symbolic link",
        "bundle inventory contains a non-regular file",
    )) for issue in issues)
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
