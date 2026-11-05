#!/usr/bin/env python3
"""Install a pinned official AWS AI-DLC rules pack into one project.

The installer deliberately downloads a specific release archive rather than a
branch.  It extracts only the published rules, records hashes for every file,
and leaves Full mode disabled unless the resulting manifest validates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_SOURCE = "https://github.com/awslabs/aidlc-workflows"
DEFAULT_REVISION = "v1.0.1"
ARCHIVE_PREFIX = "aidlc-rules/"
BUNDLE_FORMAT_VERSION = "1"
MINIMUM_TAILTRAIL_VERSION = "1.1.0"
MAXIMUM_TAILTRAIL_VERSION_EXCLUSIVE = "2.0.0"
RULE_ROOTS = ("aws-aidlc-rules", "aws-aidlc-rule-details")
REQUIRED_REQUIREMENTS_CAPABILITIES = (
    "aws-aidlc-rules/core-workflow.md",
    "aws-aidlc-rule-details/inception/requirements-analysis.md",
    "aws-aidlc-rule-details/common/question-format-guide.md",
    "aws-aidlc-rule-details/common/content-validation.md",
    "aws-aidlc-rule-details/common/session-continuity.md",
)
FULL_COMMIT = re.compile(r"[0-9a-f]{40}")
PUBLISHED_REVISION = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?")


def release_urls(revision: str) -> tuple[str, str]:
    if not PUBLISHED_REVISION.fullmatch(revision):
        raise ValueError("revision must be a published version tag such as v1.0.1")
    version = revision[1:]
    base = f"{OFFICIAL_SOURCE}/releases/download/{revision}/ai-dlc-rules-v{version}.zip"
    license_url = f"https://raw.githubusercontent.com/awslabs/aidlc-workflows/{revision}/LICENSE"
    return base, license_url


def commit_evidence_url(revision: str) -> str:
    if not PUBLISHED_REVISION.fullmatch(revision):
        raise ValueError("revision must be a published version tag such as v1.0.1")
    return f"https://api.github.com/repos/awslabs/aidlc-workflows/commits/{revision}"


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "TailTrail-official-aidlc-installer/1"})
    with urllib.request.urlopen(request, timeout=60) as response:  # nosec B310: fixed official HTTPS source
        return response.read()


def resolve_full_commit(revision: str, evidence: bytes) -> str:
    """Resolve a published tag from GitHub JSON or exact git-ls-remote output."""
    if not PUBLISHED_REVISION.fullmatch(revision):
        raise ValueError("revision must be a published version tag such as v1.0.1")
    try:
        payload = json.loads(evidence)
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = None
    commit = payload.get("sha") if isinstance(payload, dict) else None
    if isinstance(commit, str) and FULL_COMMIT.fullmatch(commit):
        return commit

    try:
        lines = evidence.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise ValueError("official commit evidence is neither GitHub JSON nor UTF-8 git-ls-remote output") from error
    refs: dict[str, str] = {}
    allowed = {f"refs/tags/{revision}", f"refs/tags/{revision}^{{}}"}
    for line in lines:
        columns = line.split("\t")
        if len(columns) != 2 or columns[1] not in allowed:
            continue
        if not FULL_COMMIT.fullmatch(columns[0]):
            raise ValueError("git-ls-remote evidence contains a non-full or non-lowercase commit SHA")
        if columns[1] in refs and refs[columns[1]] != columns[0]:
            raise ValueError("git-ls-remote evidence contains conflicting tag resolutions")
        refs[columns[1]] = columns[0]
    peeled = refs.get(f"refs/tags/{revision}^{{}}")
    direct = refs.get(f"refs/tags/{revision}")
    if peeled:
        return peeled
    if direct:
        return direct
    raise ValueError("official commit evidence does not contain the exact pinned tag and full commit SHA")


def safe_member(name: str) -> PurePosixPath | None:
    path = PurePosixPath(name)
    if not name.startswith(ARCHIVE_PREFIX) or name.endswith("/"):
        return None
    relative = PurePosixPath(*path.parts[1:])
    if not relative.parts or relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"official archive contains an unsafe path: {name}")
    return relative


def _zip_member_is_symlink(member: zipfile.ZipInfo) -> bool:
    return ((member.external_attr >> 16) & 0o170000) == 0o120000


def extract_rules(archive: Path, destination: Path) -> list[str]:
    extracted: list[str] = []
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            relative = safe_member(member.filename)
            if relative is None:
                continue
            if _zip_member_is_symlink(member):
                raise ValueError(f"official archive contains a symbolic link: {member.filename}")
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            extracted.append(relative.as_posix())
    required = "aws-aidlc-rules/core-workflow.md"
    if required not in extracted:
        raise ValueError(f"official archive is missing `{required}`")
    return sorted(extracted)


def _validate_license(content: bytes) -> None:
    normalized = content.lower()
    if not content.strip():
        raise ValueError("downloaded official AI-DLC license is empty")
    if b"mit no attribution" not in normalized and b"mit-0" not in normalized:
        raise ValueError("downloaded official AI-DLC license is not identifiable as MIT-0")


def _rule_inventory(root: Path) -> dict[str, str]:
    inventory: dict[str, str] = {}
    for relative_root in RULE_ROOTS:
        directory = root / relative_root
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError(f"rule inventory root is missing, unsafe, or not a directory: {relative_root}")
        for path in sorted(directory.rglob("*")):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                raise ValueError(f"rule inventory contains a symbolic link: {relative}")
            if path.is_dir():
                continue
            if not path.is_file():
                raise ValueError(f"rule inventory contains a non-regular file: {relative}")
            if relative in inventory:
                raise ValueError(f"rule inventory contains a duplicate path: {relative}")
            inventory[relative] = sha256_bytes(path.read_bytes())
    required = "aws-aidlc-rules/core-workflow.md"
    if required not in inventory:
        raise ValueError(f"rule inventory is missing `{required}`")
    return inventory


def _inventory_delta(current: dict[str, str], official: dict[str, str]) -> dict[str, list[str]]:
    current_paths = set(current)
    official_paths = set(official)
    return {
        "missing": sorted(official_paths - current_paths),
        "unexpected": sorted(current_paths - official_paths),
        "mismatched": sorted(path for path in current_paths & official_paths if current[path] != official[path]),
        "matched": sorted(path for path in current_paths & official_paths if current[path] == official[path]),
    }


def _provenance_receipt(
    *,
    revision: str,
    commit: str,
    archive_url: str,
    archive_bytes: bytes,
    license_url: str,
    license_bytes: bytes,
    commit_url: str,
    commit_method: str,
    commit_evidence: bytes,
    inventory: dict[str, str],
    acquired_at: str,
    legacy_version: str,
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "type": "tailtrail-aidlc-bundle-provenance",
        "authority_boundary": (
            "This receipt records controlled acquisition and byte verification. It is stored with the "
            "bundle and is not an independent publisher or TailTrail release trust anchor."
        ),
        "official": {
            "source": OFFICIAL_SOURCE,
            "revision": revision,
            "commit": commit,
            "archive": {
                "url": archive_url,
                "sha256": sha256_bytes(archive_bytes),
                "acquisition": "github-release-asset-over-https",
            },
            "commit_evidence": {
                "url": commit_url,
                "acquisition": commit_method,
                "sha256": sha256_bytes(commit_evidence),
                "resolved_commit": commit,
            },
            "license": {
                "spdx": "MIT-0",
                "file": "LICENSE",
                "url": license_url,
                "sha256": sha256_bytes(license_bytes),
            },
            "acquired_at": acquired_at,
        },
        "bundle": {
            "format_version": BUNDLE_FORMAT_VERSION,
            "official_version_source": "official.revision",
            "legacy_version": {
                "file": "VERSION",
                "observed_value": legacy_version,
                "authoritative_for_provenance": False,
            },
            "inventory": {
                "algorithm": "sha256",
                "closed_rule_inventory": True,
                "files": [{"path": path, "sha256": inventory[path]} for path in sorted(inventory)],
            },
        },
        "compatibility": {
            "minimum_tailtrail_version": MINIMUM_TAILTRAIL_VERSION,
            "maximum_tailtrail_version_exclusive": MAXIMUM_TAILTRAIL_VERSION_EXCLUSIVE,
            "supported_hosts": ["codex", "copilot", "claude"],
        },
        "decisions": {
            "artifact_trust_anchor": {
                "required_for_authenticated_release": True,
                "chain": [
                    "github-or-sigstore-identity-attestation",
                    "authenticated-wheel-or-sdist-digest",
                    "publication-or-installation-receipt",
                    "package-integrity-inventory",
                    "bundle-manifest-inventory",
                ],
                "phase0_receipt_is_trust_anchor": False,
            },
            "trust_postures": {
                "authenticated-release": "requires the complete authenticated artifact chain",
                "development-local": "source checkout with valid closed bundle inventory; disclosed as local development",
                "corruption-detection-only": "local hashes pass without qualifying artifact identity; production Full is blocked",
                "external-explicit": "explicit user-selected pack validated and frozen by fingerprint",
            },
            "corruption_detection_only": {"production_full_allowed": False},
            "source_checkout": {
                "posture": "development-local",
                "root_resolution": "module-location-plus-repository-sentinels",
                "current_working_directory_dependency": False,
            },
            "schema_compatibility": {
                "bundle_manifest": "v2",
                "legacy_v1_new_full_authority": False,
                "legacy_v1_active_run": "exact frozen bytes and fingerprint only",
                "silent_v1_promotion": False,
            },
            "active_run_upgrade": {
                "retarget_existing_runs": False,
                "selector_scope": "future-runs-only",
                "retention": "preserve all projected packs until an authoritative reference index exists",
            },
            "external_pack": {
                "implicit_substitution": False,
                "requires_explicit_selection": True,
                "requires_same_provenance_license_integrity_compatibility_and_path_safety": True,
            },
            "host_projection": {
                "selection": "host-adapter-contract",
                "allowed_modes": ["reference", "copy"],
                "operator_guess_allowed": False,
                "shared_pack_and_run_receipt_required": True,
                "complete_projection_receipt_required": True,
                "implementation_phase": "4",
            },
        },
    }


def _bundled_manifest(
    *,
    provenance: dict[str, Any],
    bundle_version: str,
    inventory: dict[str, str],
) -> dict[str, Any]:
    """Build the immutable host-neutral schema-v2 bundle manifest."""
    missing_capabilities = sorted(set(REQUIRED_REQUIREMENTS_CAPABILITIES) - set(inventory))
    if missing_capabilities:
        raise ValueError(
            "verified official inventory is missing required Requirements capabilities: "
            + ", ".join(missing_capabilities)
        )
    official = provenance["official"]
    compatibility = provenance["compatibility"]
    return {
        "schema_version": "2",
        "type": "tailtrail-bundled-official-aidlc-pack",
        "bundle": {
            "format_version": provenance["bundle"]["format_version"],
            "tailtrail_version": MINIMUM_TAILTRAIL_VERSION,
            "bundle_version": bundle_version,
            "created_from": "verified-upstream-release",
        },
        "official": {
            "source": official["source"],
            "revision": official["revision"],
            "commit": official["commit"],
            "source_archive_sha256": official["archive"]["sha256"],
            "license": {
                "spdx": official["license"]["spdx"],
                "file": official["license"]["file"],
                "sha256": official["license"]["sha256"],
            },
        },
        "compatibility": {
            "minimum_tailtrail_version": compatibility["minimum_tailtrail_version"],
            "maximum_tailtrail_version_exclusive": compatibility["maximum_tailtrail_version_exclusive"],
            "manifest_schema": "2",
            "supported_hosts": compatibility["supported_hosts"],
        },
        "required_capabilities": {
            "requirements": list(REQUIRED_REQUIREMENTS_CAPABILITIES),
        },
        "integrity": {
            "algorithm": "sha256",
            "files": [
                {"path": path, "sha256": inventory[path]}
                for path in sorted(inventory)
            ],
        },
    }


def _atomic_write_batch(
    writes: dict[Path, bytes],
    *,
    replace: Callable[[str, str], None] = os.replace,
) -> None:
    """Stage all writes first and restore every target if a replace fails."""
    originals: dict[Path, bytes | None] = {path: path.read_bytes() if path.exists() else None for path in writes}
    staged: dict[Path, Path] = {}
    replaced: list[Path] = []
    try:
        for path, content in writes.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
            temporary_path = Path(temporary)
            try:
                with os.fdopen(descriptor, "wb") as output:
                    output.write(content)
                    output.flush()
                    os.fsync(output.fileno())
            except BaseException:
                temporary_path.unlink(missing_ok=True)
                raise
            staged[path] = temporary_path
        for path, temporary_path in staged.items():
            replace(temporary_path.as_posix(), path.as_posix())
            replaced.append(path)
    except BaseException:
        for path in reversed(replaced):
            original = originals[path]
            if original is None:
                path.unlink(missing_ok=True)
                continue
            descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.rollback.", dir=path.parent)
            with os.fdopen(descriptor, "wb") as output:
                output.write(original)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
        raise
    finally:
        for temporary_path in staged.values():
            temporary_path.unlink(missing_ok=True)


def prepare_checked_in_bundle(
    root: Path,
    *,
    revision: str,
    commit: str,
    archive_bytes: bytes,
    license_bytes: bytes,
    commit_evidence: bytes,
    commit_evidence_ref: str | None = None,
    commit_evidence_method: str = "github-commit-api-over-https",
    acquired_at: str | None = None,
    dry_run: bool = False,
    replace: Callable[[str, str], None] = os.replace,
) -> dict[str, Any]:
    """Verify one official release and transactionally prepare checked-in Phase 0 assets."""
    root = root.resolve()
    bundle_root = root / "aidlc-rules"
    archive_url, license_url = release_urls(revision)
    evidence_url = commit_evidence_ref or commit_evidence_url(revision)
    if not FULL_COMMIT.fullmatch(commit):
        raise ValueError("Phase 0 requires the full lowercase 40-character official commit SHA")
    if resolve_full_commit(revision, commit_evidence) != commit:
        raise ValueError("resolved official commit does not match the supplied full commit")
    if not archive_bytes.startswith(b"PK"):
        raise ValueError("downloaded official AI-DLC archive is not a ZIP file")
    _validate_license(license_bytes)
    version_path = bundle_root / "VERSION"
    if version_path.is_symlink() or not version_path.is_file():
        raise ValueError("checked-in aidlc-rules/VERSION inspection input is missing or unsafe")
    legacy_version = version_path.read_text(encoding="utf-8").strip()
    if not legacy_version:
        raise ValueError("checked-in aidlc-rules/VERSION inspection input is empty")

    with tempfile.TemporaryDirectory(prefix="tailtrail-aidlc-phase0-") as temp:
        work = Path(temp)
        archive = work / "official-aidlc.zip"
        extracted = work / "official"
        archive.write_bytes(archive_bytes)
        extract_rules(archive, extracted)
        current_inventory = _rule_inventory(bundle_root)
        official_inventory = _rule_inventory(extracted)
        delta = _inventory_delta(current_inventory, official_inventory)
        if delta["unexpected"]:
            raise ValueError(
                "checked-in rule inventory contains paths absent from the pinned official release; "
                f"Phase 0 will not delete or relabel them (unexpected={delta['unexpected']})"
            )
        final_inventory = dict(official_inventory)
        timestamp = acquired_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        provenance = _provenance_receipt(
            revision=revision,
            commit=commit,
            archive_url=archive_url,
            archive_bytes=archive_bytes,
            license_url=license_url,
            license_bytes=license_bytes,
            commit_url=evidence_url,
            commit_method=commit_evidence_method,
            commit_evidence=commit_evidence,
            inventory=final_inventory,
            acquired_at=timestamp,
            legacy_version=legacy_version,
        )
        verified_changes = [*delta["missing"], *delta["mismatched"]]
        provenance_bytes = (json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode()
        bundle_version_bytes = f"{BUNDLE_FORMAT_VERSION}\n".encode()
        version_bytes = version_path.read_bytes()
        manifest_inventory = dict(final_inventory)
        manifest_inventory.update(
            {
                "BUNDLE_VERSION": sha256_bytes(bundle_version_bytes),
                "LICENSE": sha256_bytes(license_bytes),
                "PROVENANCE.json": sha256_bytes(provenance_bytes),
                "VERSION": sha256_bytes(version_bytes),
            }
        )
        manifest = _bundled_manifest(
            provenance=provenance,
            bundle_version=BUNDLE_FORMAT_VERSION,
            inventory=manifest_inventory,
        )
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
        writes: dict[Path, bytes] = {
            bundle_root / path: (extracted / path).read_bytes() for path in verified_changes
        }
        writes.update(
            {
                bundle_root / "PROVENANCE.json": provenance_bytes,
                bundle_root / "LICENSE": license_bytes,
                bundle_root / "BUNDLE_VERSION": bundle_version_bytes,
                bundle_root / "manifest.json": manifest_bytes,
            }
        )
        if not dry_run:
            _atomic_write_batch(writes, replace=replace)

    return {
        "type": "tailtrail-aidlc-phase0-preparation",
        "state": "verified" if dry_run else "prepared",
        "root": root.as_posix(),
        "bundle_root": bundle_root.relative_to(root).as_posix(),
        "official_source": OFFICIAL_SOURCE,
        "revision": revision,
        "commit": commit,
        "archive_sha256": sha256_bytes(archive_bytes),
        "license_sha256": sha256_bytes(license_bytes),
        "rule_file_count": len(final_inventory),
        "matched_files": delta["matched"],
        "added_files": delta["missing"],
        "replaced_files": delta["mismatched"],
        "generated_files": [
            "aidlc-rules/PROVENANCE.json",
            "aidlc-rules/LICENSE",
            "aidlc-rules/BUNDLE_VERSION",
            "aidlc-rules/manifest.json",
        ],
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "dry_run": dry_run,
    }


def _read_phase0_file(bundle_root: Path, name: str) -> bytes:
    path = bundle_root / name
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"verified Phase 0 input is missing or unsafe: aidlc-rules/{name}")
    return path.read_bytes()


def prepare_bundle_manifest(
    root: Path,
    *,
    dry_run: bool = False,
    replace: Callable[[str, str], None] = os.replace,
) -> dict[str, Any]:
    """Build the v2 manifest offline from verified checked-in Phase 0 inputs."""
    root = root.resolve()
    bundle_root = root / "aidlc-rules"
    provenance_bytes = _read_phase0_file(bundle_root, "PROVENANCE.json")
    license_bytes = _read_phase0_file(bundle_root, "LICENSE")
    bundle_version_bytes = _read_phase0_file(bundle_root, "BUNDLE_VERSION")
    version_bytes = _read_phase0_file(bundle_root, "VERSION")
    try:
        provenance = json.loads(provenance_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"verified Phase 0 PROVENANCE.json is invalid JSON: {error}") from error
    if not isinstance(provenance, dict):
        raise ValueError("verified Phase 0 PROVENANCE.json must be a JSON object")

    try:
        official = provenance["official"]
        provenance_bundle = provenance["bundle"]
        compatibility = provenance["compatibility"]
        provenance_files = provenance_bundle["inventory"]["files"]
    except (KeyError, TypeError) as error:
        raise ValueError(f"verified Phase 0 provenance is incomplete: {error}") from error
    if provenance.get("type") != "tailtrail-aidlc-bundle-provenance":
        raise ValueError("verified Phase 0 provenance has an unsupported type")
    if official.get("source") != OFFICIAL_SOURCE:
        raise ValueError("verified Phase 0 provenance has an unexpected official source")
    if not PUBLISHED_REVISION.fullmatch(str(official.get("revision", ""))):
        raise ValueError("verified Phase 0 provenance does not name a published release tag")
    if not FULL_COMMIT.fullmatch(str(official.get("commit", ""))):
        raise ValueError("verified Phase 0 provenance does not contain a full official commit SHA")
    if provenance_bundle.get("format_version") != BUNDLE_FORMAT_VERSION:
        raise ValueError("verified Phase 0 provenance has an incompatible bundle format version")
    if compatibility.get("minimum_tailtrail_version") != MINIMUM_TAILTRAIL_VERSION or compatibility.get(
        "maximum_tailtrail_version_exclusive"
    ) != MAXIMUM_TAILTRAIL_VERSION_EXCLUSIVE:
        raise ValueError("verified Phase 0 provenance has an incompatible TailTrail version range")
    if compatibility.get("supported_hosts") != ["codex", "copilot", "claude"]:
        raise ValueError("verified Phase 0 provenance has an incompatible supported-host contract")
    if not isinstance(provenance_files, list):
        raise ValueError("verified Phase 0 provenance rule inventory must be a list")

    declared_inventory: dict[str, str] = {}
    for index, entry in enumerate(provenance_files, start=1):
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise ValueError(f"verified Phase 0 provenance inventory entry {index} is malformed")
        path = entry["path"]
        digest = entry["sha256"]
        if not isinstance(path, str) or path in declared_inventory:
            raise ValueError(f"verified Phase 0 provenance inventory entry {index} has an invalid or duplicate path")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"verified Phase 0 provenance inventory entry {index} has an invalid SHA-256 hash")
        declared_inventory[path] = digest

    actual_inventory = _rule_inventory(bundle_root)
    delta = _inventory_delta(actual_inventory, declared_inventory)
    if delta["missing"] or delta["unexpected"] or delta["mismatched"]:
        raise ValueError(
            "checked-in rules do not match the verified Phase 0 provenance inventory "
            f"(missing={delta['missing']}, unexpected={delta['unexpected']}, mismatched={delta['mismatched']})"
        )
    _validate_license(license_bytes)
    expected_license_hash = official.get("license", {}).get("sha256")
    if expected_license_hash != sha256_bytes(license_bytes):
        raise ValueError("checked-in LICENSE does not match verified Phase 0 provenance")
    bundle_version = bundle_version_bytes.decode("utf-8").strip()
    if bundle_version != BUNDLE_FORMAT_VERSION:
        raise ValueError("checked-in BUNDLE_VERSION does not match the supported bundle format")
    legacy_version = version_bytes.decode("utf-8").strip()
    if legacy_version != provenance_bundle.get("legacy_version", {}).get("observed_value"):
        raise ValueError("checked-in VERSION does not match verified Phase 0 provenance")

    manifest_inventory = dict(actual_inventory)
    manifest_inventory.update(
        {
            "BUNDLE_VERSION": sha256_bytes(bundle_version_bytes),
            "LICENSE": sha256_bytes(license_bytes),
            "PROVENANCE.json": sha256_bytes(provenance_bytes),
            "VERSION": sha256_bytes(version_bytes),
        }
    )
    manifest = _bundled_manifest(
        provenance=provenance,
        bundle_version=bundle_version,
        inventory=manifest_inventory,
    )
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    if not dry_run:
        _atomic_write_batch({bundle_root / "manifest.json": manifest_bytes}, replace=replace)
    return {
        "type": "tailtrail-aidlc-bundle-manifest-preparation",
        "state": "verified" if dry_run else "prepared",
        "root": root.as_posix(),
        "bundle_root": bundle_root.relative_to(root).as_posix(),
        "official_source": official["source"],
        "revision": official["revision"],
        "commit": official["commit"],
        "archive_sha256": official["archive"]["sha256"],
        "rule_file_count": len(actual_inventory),
        "manifest_file_count": len(manifest_inventory),
        "generated_files": ["aidlc-rules/manifest.json"],
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "dry_run": dry_run,
    }


def write_manifest(destination: Path, revision: str, files: list[str], host: str, *, commit: str | None = None) -> Path:
    manifest = {
        "schema_version": "1",
        "type": "tailtrail-official-aidlc-pack",
        "official": {
            "source": OFFICIAL_SOURCE,
            "revision": revision,
            "commit": commit or "",
            "license": {"spdx": "MIT-0", "file": "LICENSE"},
        },
        "host_adapter": {"host": host, "rules_path": "aws-aidlc-rules/core-workflow.md"},
        "integrity": {
            "algorithm": "sha256",
            "files": [
                {"path": path, "sha256": sha256_bytes((destination / path).read_bytes())}
                for path in sorted(files)
            ],
        },
    }
    path = destination / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def install(root: Path, *, revision: str, host: str, archive_bytes: bytes, license_bytes: bytes, commit: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    root = root.resolve()
    destination = root / ".tailtrail" / "official-aidlc"
    if destination.exists():
        raise ValueError(f"official AI-DLC destination already exists: {destination}. Validate it with `tailtrail aidlc official status --root .`; do not overwrite a pinned pack.")
    if not archive_bytes.startswith(b"PK"):
        raise ValueError("downloaded official AI-DLC archive is not a ZIP file")
    if not license_bytes.strip():
        raise ValueError("downloaded official AI-DLC license is empty")
    plan = {
        "type": "tailtrail-official-aidlc-install",
        "root": root.as_posix(),
        "destination": destination.relative_to(root).as_posix(),
        "official_source": OFFICIAL_SOURCE,
        "revision": revision,
        "commit": commit or "",
        "host": host,
        "archive_sha256": sha256_bytes(archive_bytes),
        "license_sha256": sha256_bytes(license_bytes),
        "dry_run": dry_run,
    }
    if dry_run:
        return {**plan, "state": "planned"}
    with tempfile.TemporaryDirectory(prefix="tailtrail-aidlc-") as temp:
        work = Path(temp)
        archive = work / "official-aidlc.zip"
        stage = work / "official-aidlc"
        archive.write_bytes(archive_bytes)
        files = extract_rules(archive, stage)
        (stage / "LICENSE").write_bytes(license_bytes)
        files.append("LICENSE")
        write_manifest(stage, revision, files, host, commit=commit)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(stage.as_posix(), destination.as_posix())
    return {**plan, "state": "installed", "manifest": (destination / "manifest.json").relative_to(root).as_posix(), "file_count": len(files)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target project root.")
    parser.add_argument("--revision", default=DEFAULT_REVISION, help="Pinned official release tag (default: v1.0.1).")
    parser.add_argument("--host", choices=("codex", "copilot", "claude", "generic"), default="generic", help="Host that will consume the installed rules.")
    preparation = parser.add_mutually_exclusive_group()
    preparation.add_argument(
        "--prepare-checked-in-bundle",
        action="store_true",
        help="Prepare the repository aidlc-rules Phase 0 provenance, license, bundle version, and verified rule bytes.",
    )
    preparation.add_argument(
        "--prepare-bundle-manifest",
        action="store_true",
        help="Generate aidlc-rules/manifest.json offline from verified checked-in Phase 0 inputs.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Verify inputs and show the installation target without writing it.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    try:
        if args.prepare_bundle_manifest:
            result = prepare_bundle_manifest(args.root, dry_run=args.dry_run)
        else:
            archive_url, license_url = release_urls(args.revision)
            archive = fetch(archive_url)
            license_text = fetch(license_url)
            commit_payload = fetch(commit_evidence_url(args.revision))
            commit = resolve_full_commit(args.revision, commit_payload)
        if args.prepare_checked_in_bundle:
            result = prepare_checked_in_bundle(
                args.root,
                revision=args.revision,
                commit=commit,
                archive_bytes=archive,
                license_bytes=license_text,
                commit_evidence=commit_payload,
                dry_run=args.dry_run,
            )
        elif not args.prepare_bundle_manifest:
            result = install(
                args.root,
                revision=args.revision,
                host=args.host,
                archive_bytes=archive,
                license_bytes=license_text,
                commit=commit,
                dry_run=args.dry_run,
            )
    except (OSError, ValueError, urllib.error.URLError, zipfile.BadZipFile) as error:
        print(f"Official AI-DLC install error: {error}")
        return 2
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            "# TailTrail Official AI-DLC Bundle Preparation"
            if args.prepare_checked_in_bundle or args.prepare_bundle_manifest
            else "# TailTrail Official AI-DLC Install"
        )
        print()
        print(f"**State:** `{result['state']}`")
        print(f"**Release:** `{result['revision']}`" + (f" (`{result['commit']}`)" if result["commit"] else ""))
        print(f"**Archive SHA-256:** `{result['archive_sha256']}`")
        if args.prepare_checked_in_bundle or args.prepare_bundle_manifest:
            print(f"**Bundle root:** `{result['bundle_root']}`")
            print(f"**Verified rule files:** `{result['rule_file_count']}`")
            if args.prepare_checked_in_bundle:
                print(f"**Exact matches preserved:** `{len(result['matched_files'])}`")
                print(f"**Verified missing files added:** `{len(result['added_files'])}`")
                print(f"**Verified mismatches replaced:** `{len(result['replaced_files'])}`")
            else:
                print(f"**Manifest inventory files:** `{result['manifest_file_count']}`")
        else:
            print(f"**Host:** `{result['host']}`")
            print(f"**Destination:** `{result['destination']}`")
        if result["state"] == "installed":
            print(f"**Verified files:** `{result['file_count']}`")
            print()
            print(f"Next: `tailtrail aidlc official status --root {args.root}`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
