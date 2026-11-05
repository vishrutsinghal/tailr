"""Offline resolution of TailTrail's bundled official AIDLC rules.

This module owns provider discovery, integrity validation, and the atomic
projection of a verified bundle into a target repository.  It never contacts
the network or executes bundle content.  Run binding remains a later phase.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import errno
import shutil
import time
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

try:  # pragma: no cover - platform selected at runtime
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore[assignment]

try:  # pragma: no cover - platform selected at runtime
    import msvcrt
except ImportError:  # pragma: no cover - POSIX
    msvcrt = None  # type: ignore[assignment]

from . import __version__


OFFICIAL_SOURCE = "https://github.com/awslabs/aidlc-workflows"
SUPPORTED_HOSTS = frozenset({"codex", "copilot", "claude"})
REQUIRED_CAPABILITIES = frozenset(
    {
        "aws-aidlc-rules/core-workflow.md",
        "aws-aidlc-rule-details/inception/requirements-analysis.md",
        "aws-aidlc-rule-details/common/question-format-guide.md",
        "aws-aidlc-rule-details/common/content-validation.md",
        "aws-aidlc-rule-details/common/session-continuity.md",
    }
)
SHA256 = re.compile(r"^[0-9a-f]{64}$")
FULL_COMMIT = re.compile(r"^[0-9a-f]{40}$")
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")
WINDOWS_DEVICES = frozenset(
    {"CON", "PRN", "AUX", "NUL", *(f"COM{index}" for index in range(1, 10)), *(f"LPT{index}" for index in range(1, 10))}
)


@dataclass(frozen=True)
class ResolverInputs:
    """Execution-context inputs for bundled-pack resolution.

    ``module_path`` and ``environment`` are injectable so installed, managed,
    and source layouts can be proven without changing the process CWD.
    ``managed_shared_root`` is an explicit launcher-owned context, not a user
    selected external pack.
    """

    host: str
    requested_mode: str = "full"
    module_path: Path | None = None
    managed_shared_root: Path | None = None
    managed_ownership_manifest: Path | None = None
    artifact_identity_receipt: Mapping[str, Any] | Path | None = None
    running_version: str = __version__
    environment: Mapping[str, str] | None = None


@dataclass(frozen=True)
class ProjectionInputs:
    """Inputs for one offline project-pack projection operation."""

    resolution_receipt: Mapping[str, Any]
    target_root: Path
    lock_timeout_seconds: float = 5.0
    lock_poll_seconds: float = 0.05
    running_version: str = __version__
    fault: Callable[[str], None] | None = None


@dataclass(frozen=True)
class RecoveryInputs:
    """Explicit authority for one validated stale-staging removal."""

    target_root: Path
    staging_name: str
    staging_fingerprint: str
    lock_timeout_seconds: float = 5.0
    lock_poll_seconds: float = 0.05


@dataclass(frozen=True)
class BindingInputs:
    """Inputs for freezing one active run to one verified project pack."""

    target_root: Path
    run_id: str
    projection_result: Mapping[str, Any]
    lock_timeout_seconds: float = 5.0
    lock_poll_seconds: float = 0.05


@dataclass(frozen=True)
class LegacyRunInputs:
    """Existing authority required for bounded schema-v1 continuation."""

    target_root: Path
    run_id: str


@dataclass(frozen=True)
class StatusInputs:
    """Read-only status inputs; status never provisions or repairs state."""

    target_root: Path
    resolution_receipt: Mapping[str, Any] | None = None
    run_id: str | None = None
    running_version: str = __version__


@dataclass(frozen=True)
class _Provider:
    name: str
    root: Path
    bundle_root: Path
    trust_posture: str
    ownership_manifest: Path | None = None


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _issue(category: str, detail: str) -> dict[str, str]:
    return {"category": category, "detail": detail}


def _safe_relative(value: Any) -> str | None:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        return None
    if value.startswith("//") or WINDOWS_DRIVE.match(value) or unicodedata.normalize("NFC", value) != value:
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        return None
    for part in path.parts:
        if part.endswith((".", " ")) or part.split(".", 1)[0].upper() in WINDOWS_DEVICES:
            return None
    return path.as_posix()


def _read_json(path: Path, label: str) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    if path.is_symlink() or not path.is_file():
        return None, [_issue("missing-or-unsafe", f"{label} is missing, not regular, or a symbolic link: {path}")]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return None, [_issue("unreadable", f"{label} could not be read: {error}")]
    if not isinstance(value, dict):
        return None, [_issue("incompatible", f"{label} must contain a JSON object")]
    return value, []


def _inventory(root: Path, *, exclude: frozenset[str] = frozenset()) -> tuple[dict[str, str], list[dict[str, str]]]:
    result: dict[str, str] = {}
    issues: list[dict[str, str]] = []
    if root.is_symlink() or not root.is_dir():
        return result, [_issue("missing-or-unsafe", f"bundle root is missing, not a directory, or a symbolic link: {root}")]
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            issues.append(_issue("unsafe-path", f"bundle inventory contains a symbolic link: {relative}"))
            continue
        if path.is_dir():
            continue
        if not path.is_file():
            issues.append(_issue("unsafe-path", f"bundle inventory contains a non-regular file: {relative}"))
            continue
        safe = _safe_relative(relative)
        if safe is None:
            issues.append(_issue("unsafe-path", f"bundle inventory contains an unsafe path: {relative}"))
            continue
        if safe in exclude:
            continue
        result[safe] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result, issues


def _version_tuple(value: str) -> tuple[int, int, int] | None:
    if not SEMVER.fullmatch(value):
        return None
    core = value.split("-", 1)[0].split("+", 1)[0]
    return tuple(int(part) for part in core.split("."))  # type: ignore[return-value]


def _validate_bundle(bundle_root: Path, host: str, running_version: str) -> tuple[dict[str, Any] | None, dict[str, str], list[dict[str, str]]]:
    manifest_path = bundle_root / "manifest.json"
    manifest, issues = _read_json(manifest_path, "bundle manifest")
    if manifest is None:
        return None, {}, issues
    if manifest.get("schema_version") != "2" or manifest.get("type") != "tailtrail-bundled-official-aidlc-pack":
        issues.append(_issue("incompatible-schema", "new Full resolution requires the closed schema-v2 bundled manifest; legacy v1 cannot authorize it"))

    official = manifest.get("official")
    compatibility = manifest.get("compatibility")
    capabilities = manifest.get("required_capabilities")
    integrity = manifest.get("integrity")
    if not isinstance(official, dict):
        issues.append(_issue("incompatible", "bundle manifest official metadata is missing"))
        official = {}
    if official.get("source") != OFFICIAL_SOURCE or not FULL_COMMIT.fullmatch(str(official.get("commit", ""))):
        issues.append(_issue("incompatible", "bundle official source or full commit identity is invalid"))
    if not isinstance(compatibility, dict):
        issues.append(_issue("incompatible", "bundle compatibility metadata is missing"))
        compatibility = {}
    hosts = compatibility.get("supported_hosts")
    if not isinstance(hosts, list) or set(hosts) != SUPPORTED_HOSTS or len(hosts) != len(SUPPORTED_HOSTS):
        issues.append(_issue("incompatible", "bundle supported_hosts must contain codex, copilot, and claude exactly once"))
    elif host not in hosts:
        issues.append(_issue("unsupported-host", f"bundle does not support host: {host}"))
    current = _version_tuple(running_version)
    minimum = _version_tuple(str(compatibility.get("minimum_tailtrail_version", "")))
    maximum = _version_tuple(str(compatibility.get("maximum_tailtrail_version_exclusive", "")))
    if current is None or minimum is None or maximum is None or not (minimum <= current < maximum):
        issues.append(_issue("incompatible-version", "running TailTrail version is outside the bundle compatibility range"))
    requirements = capabilities.get("requirements") if isinstance(capabilities, dict) else None
    if not isinstance(requirements, list) or any(_safe_relative(value) is None for value in requirements):
        issues.append(_issue("incompatible", "required_capabilities.requirements must be a safe path list"))
        requirements = []
    if not REQUIRED_CAPABILITIES.issubset(requirements):
        issues.append(_issue("incomplete", "bundle is missing mandatory Requirements capabilities"))

    entries = integrity.get("files") if isinstance(integrity, dict) and integrity.get("algorithm") == "sha256" else None
    declared: dict[str, str] = {}
    if not isinstance(entries, list) or not entries:
        issues.append(_issue("incomplete", "bundle integrity inventory is missing or empty"))
        entries = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            issues.append(_issue("incompatible", f"bundle integrity entry {index} is not a closed path/hash object"))
            continue
        path = _safe_relative(entry.get("path"))
        digest = entry.get("sha256")
        if path is None or not isinstance(digest, str) or not SHA256.fullmatch(digest):
            issues.append(_issue("unsafe-path", f"bundle integrity entry {index} has an unsafe path or invalid hash"))
            continue
        if path in declared:
            issues.append(_issue("duplicate-path", f"bundle integrity contains a duplicate path: {path}"))
            continue
        declared[path] = digest
    actual, inventory_issues = _inventory(bundle_root, exclude=frozenset({"manifest.json"}))
    issues.extend(inventory_issues)
    for path in sorted(set(declared) - set(actual)):
        issues.append(_issue("missing-file", f"bundle integrity file is missing: {path}"))
    for path in sorted(set(actual) - set(declared)):
        issues.append(_issue("unexpected-file", f"bundle integrity has an unexpected file: {path}"))
    for path in sorted(set(actual) & set(declared)):
        if actual[path] != declared[path]:
            issues.append(_issue("hash-mismatch", f"bundle integrity hash mismatch: {path}"))
    for required in {"LICENSE", "PROVENANCE.json", "BUNDLE_VERSION", "VERSION", *requirements}:
        if required not in declared:
            issues.append(_issue("incomplete", f"required bundle file is not integrity-bound: {required}"))

    provenance, provenance_issues = _read_json(bundle_root / "PROVENANCE.json", "bundle provenance")
    issues.extend(provenance_issues)
    if provenance is not None:
        provenance_official = provenance.get("official") if isinstance(provenance.get("official"), dict) else {}
        for key in ("source", "revision", "commit"):
            if official.get(key) != provenance_official.get(key):
                issues.append(_issue("provenance-conflict", f"manifest and provenance disagree on official {key}"))
    try:
        bundle_version = (bundle_root / "BUNDLE_VERSION").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as error:
        issues.append(_issue("unreadable", f"BUNDLE_VERSION could not be read: {error}"))
    else:
        bundle = manifest.get("bundle") if isinstance(manifest.get("bundle"), dict) else {}
        if bundle.get("bundle_version") != bundle_version:
            issues.append(_issue("provenance-conflict", "manifest bundle version disagrees with BUNDLE_VERSION"))
    return manifest, actual, issues


def _validate_package_outer(package_root: Path, bundle_inventory: dict[str, str]) -> tuple[str | None, list[dict[str, str]]]:
    integrity_path = package_root / "package-integrity.json"
    document, issues = _read_json(integrity_path, "package integrity")
    if document is None:
        return None, issues
    files = document.get("files")
    if document.get("schema_version") != "1" or document.get("algorithm") != "sha256" or not isinstance(files, dict):
        return None, issues + [_issue("incompatible", "package integrity contract is invalid")]
    declared: dict[str, str] = {}
    for value, digest in files.items():
        safe = _safe_relative(value)
        if safe is None or not isinstance(digest, str) or not SHA256.fullmatch(digest):
            issues.append(_issue("unsafe-path", "package integrity contains an unsafe path or invalid hash"))
            continue
        if safe.startswith("aidlc-rules/"):
            declared[safe.removeprefix("aidlc-rules/")] = digest
    if set(declared) != {"manifest.json", *bundle_inventory}:
        issues.append(_issue("outer-inventory-mismatch", "package integrity AIDLC inventory does not exactly match the packaged bundle"))
    manifest_path = package_root / "aidlc-rules" / "manifest.json"
    expected = {**bundle_inventory, "manifest.json": hashlib.sha256(manifest_path.read_bytes()).hexdigest()} if manifest_path.is_file() else bundle_inventory
    for path in sorted(set(declared) & set(expected)):
        if declared[path] != expected[path]:
            issues.append(_issue("outer-hash-mismatch", f"package integrity hash mismatch: aidlc-rules/{path}"))
    return _file_fingerprint(integrity_path), issues


def _validate_source_outer(source_root: Path, bundle_inventory: dict[str, str]) -> tuple[str | None, list[dict[str, str]]]:
    issues: list[dict[str, str]] = []
    required = ("pyproject.toml", "package-manifest.json")
    for name in required:
        path = source_root / name
        if path.is_symlink() or not path.is_file():
            issues.append(_issue("ambiguous-source-root", f"source-checkout sentinel is missing or unsafe: {name}"))
    package_manifest, manifest_issues = _read_json(source_root / "package-manifest.json", "source package manifest")
    issues.extend(manifest_issues)
    if package_manifest is not None:
        directories = package_manifest.get("required_directories")
        if not isinstance(directories, list) or "aidlc-rules" not in directories:
            issues.append(_issue("incomplete", "source package manifest does not require aidlc-rules"))
    evidence = {
        "kind": "source-checkout-direct-inventory",
        "sentinels": {name: _file_fingerprint(source_root / name) for name in required if (source_root / name).is_file()},
        "bundle_inventory": bundle_inventory,
    }
    return _fingerprint(evidence), issues


def _validate_managed_outer(provider: _Provider, bundle_inventory: dict[str, str], host: str) -> tuple[str | None, list[dict[str, str]]]:
    manifest_path = provider.ownership_manifest
    if manifest_path is None:
        return None, [_issue("missing-ownership", "managed payload has no host ownership manifest")]
    manifest, issues = _read_json(manifest_path, "managed ownership manifest")
    if manifest is None:
        return None, issues
    if (
        manifest.get("schema_version") != "1"
        or manifest.get("tool") != "tailtrail"
        or manifest.get("host") != host
        or manifest.get("profile") != "extended"
        or manifest.get("ownership") != "tailtrail-managed"
        or str(manifest.get("version")) != provider.root.name
        or not isinstance(manifest.get("files"), dict)
    ):
        issues.append(_issue("invalid-ownership", "managed ownership manifest does not bind this host, version, and extended payload"))
        return _file_fingerprint(manifest_path), issues
    prefix = f".tailtrail/install/payload/common/{provider.root.name}/aidlc-rules/"
    selected = {key.removeprefix(prefix): value for key, value in manifest["files"].items() if isinstance(key, str) and key.startswith(prefix)}
    expected_paths = {"manifest.json", *bundle_inventory}
    if set(selected) != expected_paths:
        issues.append(_issue("outer-inventory-mismatch", "managed ownership AIDLC inventory does not exactly match the shared bundle"))
    for relative in sorted(set(selected) & expected_paths):
        record = selected[relative]
        path = provider.bundle_root / relative
        if not isinstance(record, dict) or record.get("owner") != "tailtrail" or record.get("sha256") != hashlib.sha256(path.read_bytes()).hexdigest() or record.get("size") != path.stat().st_size:
            issues.append(_issue("outer-hash-mismatch", f"managed ownership mismatch: {relative}"))
    return _file_fingerprint(manifest_path), issues


def _load_identity_receipt(value: Mapping[str, Any] | Path | None) -> tuple[dict[str, Any] | None, str]:
    if value is None:
        return None, "not-provided"
    if isinstance(value, Mapping):
        return dict(value), "provided"
    document, issues = _read_json(value, "artifact identity receipt")
    return (document, "provided") if document is not None and not issues else (None, "invalid")


def _identity_status(receipt: dict[str, Any] | None, outer_fingerprint: str | None) -> tuple[str, str | None]:
    if receipt is None:
        return "not-provided", None
    if receipt.get("identity_verified") is not True or receipt.get("payload_fingerprint") != outer_fingerprint:
        return "unbound", None
    reference = receipt.get("receipt_id") or receipt.get("artifact") or _fingerprint(receipt)
    return "verified", str(reference)


def _discover(inputs: ResolverInputs) -> tuple[_Provider | None, list[dict[str, str]]]:
    module_path = (inputs.module_path or Path(__file__)).resolve()
    package_root = module_path.parent
    environment = inputs.environment if inputs.environment is not None else os.environ
    managed_value = inputs.managed_shared_root or (Path(environment["TAILTRAIL_SOURCE_COMPAT_ROOT"]) if environment.get("TAILTRAIL_SOURCE_COMPAT_ROOT") else None)
    if managed_value is not None:
        shared = managed_value.resolve()
        try:
            module_path.relative_to(shared)
        except ValueError:
            return None, [_issue("ambiguous-provider", "managed payload was declared but the running resolver is outside that shared root")]
        install_root = shared.parents[2] if len(shared.parents) >= 3 else shared
        ownership = inputs.managed_ownership_manifest or install_root / "manifests" / f"{inputs.host}.json"
        return _Provider("managed-payload", shared, shared / "aidlc-rules", "corruption-detection-only", ownership.resolve()), []

    installed = (package_root / "package-integrity.json").is_file() and (package_root / "aidlc-rules" / "manifest.json").is_file()
    source_root = package_root.parent
    source = all((source_root / name).is_file() for name in ("pyproject.toml", "package-manifest.json")) and (source_root / "aidlc-rules" / "manifest.json").is_file()
    if installed and source:
        return None, [_issue("ambiguous-provider", "both installed-package and source-checkout contexts are complete; launcher ownership is unresolved")]
    if installed:
        return _Provider("installed-package", package_root, package_root / "aidlc-rules", "corruption-detection-only"), []
    if source:
        return _Provider("source-checkout", source_root, source_root / "aidlc-rules", "development-local"), []
    return None, [_issue("provider-unavailable", "no complete installed-package, managed-payload, or source-checkout bundle context was found")]


def _seal_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    return {**receipt, "receipt_fingerprint": _fingerprint(receipt)}


def _blocked(inputs: ResolverInputs, issues: list[dict[str, str]], provider: _Provider | None = None) -> dict[str, Any]:
    return _seal_receipt(
        {
            "schema_version": "1",
            "type": "tailtrail-official-aidlc-resolution",
            "state": "blocked",
            "requested_mode": inputs.requested_mode,
            "effective_mode": None,
            "source_kind": "tailtrail-bundled",
            "resource_provider": provider.name if provider else None,
            "trust_posture": provider.trust_posture if provider else None,
            "artifact_identity_status": "not-verified",
            "artifact_identity_receipt": None,
            "network_used": False,
            "host": inputs.host,
            "verified_root": None,
            "official_source": None,
            "official_revision": None,
            "official_commit": None,
            "bundle_manifest_fingerprint": None,
            "package_integrity_fingerprint": None,
            "issues": issues,
            "boundary": "Verified rule data only; no pack script was executed and no source or destination state was changed.",
        }
    )


def resolve(inputs: ResolverInputs) -> dict[str, Any]:
    """Resolve and validate the bundle for this execution context.

    A blocked receipt is returned for expected unsafe or incompatible states;
    callers do not need to catch validation exceptions.  Programmer type errors
    remain exceptions.
    """

    if inputs.requested_mode.lower() != "full":
        return _blocked(inputs, [_issue("unsupported-mode", "this resolver accepts explicit Full mode only")])
    if inputs.host not in SUPPORTED_HOSTS:
        return _blocked(inputs, [_issue("unsupported-host", f"unsupported host: {inputs.host}")])
    provider, discovery_issues = _discover(inputs)
    if provider is None:
        return _blocked(inputs, discovery_issues)
    manifest, bundle_inventory, issues = _validate_bundle(provider.bundle_root, inputs.host, inputs.running_version)
    if provider.name == "installed-package":
        outer_fingerprint, outer_issues = _validate_package_outer(provider.root, bundle_inventory)
    elif provider.name == "managed-payload":
        outer_fingerprint, outer_issues = _validate_managed_outer(provider, bundle_inventory, inputs.host)
    else:
        outer_fingerprint, outer_issues = _validate_source_outer(provider.root, bundle_inventory)
    issues.extend(outer_issues)
    identity_receipt, supplied_status = _load_identity_receipt(inputs.artifact_identity_receipt)
    identity_status, identity_reference = _identity_status(identity_receipt, outer_fingerprint)
    if supplied_status == "invalid":
        identity_status = "invalid"
    trust_posture = provider.trust_posture
    if provider.name != "source-checkout" and identity_status == "verified":
        trust_posture = "authenticated-release"
    if issues or manifest is None or outer_fingerprint is None:
        return _blocked(inputs, issues or [_issue("integrity-unavailable", "provider integrity could not be established")], provider)
    official = manifest["official"]
    return _seal_receipt(
        {
            "schema_version": "1",
            "type": "tailtrail-official-aidlc-resolution",
            "state": "ready",
            "requested_mode": "full",
            "effective_mode": "full",
            "source_kind": "tailtrail-bundled",
            "resource_provider": provider.name,
            "trust_posture": trust_posture,
            "artifact_identity_status": identity_status,
            "artifact_identity_receipt": identity_reference,
            "network_used": False,
            "host": inputs.host,
            "verified_root": provider.bundle_root.resolve().as_posix(),
            "official_source": official["source"],
            "official_revision": official["revision"],
            "official_commit": official["commit"],
            "bundle_manifest_fingerprint": _file_fingerprint(provider.bundle_root / "manifest.json"),
            "package_integrity_fingerprint": outer_fingerprint,
            "issues": [],
            "boundary": "Verified rule data only; no pack script was executed and no source or destination state was changed.",
        }
    )


class _ProjectionFailure(RuntimeError):
    def __init__(self, category: str, detail: str):
        super().__init__(detail)
        self.category = category


class _BoundedFileLock:
    """One cross-platform advisory lock with bounded acquisition."""

    def __init__(self, path: Path, timeout: float, poll: float) -> None:
        self.path = path
        self.timeout = max(0.0, float(timeout))
        self.poll = max(0.001, float(poll))
        self.descriptor: int | None = None

    def __enter__(self) -> "_BoundedFileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise _ProjectionFailure("unsafe-target", f"provision lock is a symbolic link: {self.path}")
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            self.descriptor = os.open(self.path, flags, 0o600)
        except OSError as error:
            raise _ProjectionFailure("lock-unavailable", f"provision lock could not be opened: {error}") from error
        if os.name == "nt":  # locking() requires one addressable byte.
            if os.fstat(self.descriptor).st_size == 0:
                os.write(self.descriptor, b"0")
                os.fsync(self.descriptor)
            os.lseek(self.descriptor, 0, os.SEEK_SET)
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                if fcntl is not None:
                    fcntl.flock(self.descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                elif msvcrt is not None:
                    os.lseek(self.descriptor, 0, os.SEEK_SET)
                    msvcrt.locking(self.descriptor, msvcrt.LK_NBLCK, 1)
                else:  # pragma: no cover - every supported platform has one
                    raise _ProjectionFailure("lock-unavailable", "no supported OS file-lock implementation is available")
                return self
            except _ProjectionFailure:
                self._close()
                raise
            except OSError as error:
                if error.errno not in {errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK}:
                    self._close()
                    raise _ProjectionFailure("lock-unavailable", f"provision lock failed: {error}") from error
                if time.monotonic() >= deadline:
                    self._close()
                    raise _ProjectionFailure("lock-timeout", "timed out waiting for the bounded provision lock") from error
                time.sleep(min(self.poll, max(0.0, deadline - time.monotonic())))

    def _close(self) -> None:
        if self.descriptor is not None:
            os.close(self.descriptor)
            self.descriptor = None

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.descriptor is None:
            return
        try:
            if fcntl is not None:
                fcntl.flock(self.descriptor, fcntl.LOCK_UN)
            elif msvcrt is not None:
                os.lseek(self.descriptor, 0, os.SEEK_SET)
                msvcrt.locking(self.descriptor, msvcrt.LK_UNLCK, 1)
        finally:
            self._close()


def _sealed_document(payload: dict[str, Any], field: str) -> dict[str, Any]:
    return {**payload, field: _fingerprint(payload)}


def _valid_seal(payload: Mapping[str, Any], field: str) -> bool:
    value = dict(payload)
    fingerprint = value.pop(field, None)
    return isinstance(fingerprint, str) and fingerprint == _fingerprint(value)


def _sync_directory(path: Path) -> None:
    """Best-effort directory durability; unsupported platforms remain honest."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _atomic_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary.open("xb") as stream:
            stream.write(json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def _projection_blocked(
    issues: list[dict[str, str]],
    *,
    pack_fingerprint: str | None = None,
    pack_path: str | None = None,
    stale_staging: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return _seal_receipt({
        "schema_version": "1",
        "type": "tailtrail-official-aidlc-project-projection-result",
        "state": "blocked",
        "status": None,
        "pack_fingerprint": pack_fingerprint,
        "pack_path": pack_path,
        "network_used": False,
        "stale_staging": list(stale_staging or []),
        "issues": issues,
    })


def _target_layout(target_root: Path) -> tuple[Path, Path, Path, Path, Path]:
    requested = Path(target_root)
    if requested.is_symlink() or not requested.exists() or not requested.is_dir():
        raise _ProjectionFailure("unsafe-target", f"project target must be an existing non-symlink directory: {requested}")
    target = requested.resolve()
    if target == Path(target.anchor):
        raise _ProjectionFailure("unsafe-target", "project projection into a filesystem root is forbidden")
    official = target / ".tailtrail" / "official-aidlc"
    packs = official / "packs"
    locks = official / "locks"
    markers = official / "staging-markers"
    for path in (target / ".tailtrail", official, packs, locks, markers):
        if path.exists() and (path.is_symlink() or not path.is_dir()):
            raise _ProjectionFailure("unsafe-target", f"managed projection ancestor is unsafe: {path}")
    for path in (target / ".tailtrail", official, packs, locks, markers):
        path.mkdir(exist_ok=True)
        if path.is_symlink() or not path.is_dir():
            raise _ProjectionFailure("unsafe-target", f"managed projection ancestor became unsafe: {path}")
    return target, official, packs, locks, markers


def _validated_source(
    receipt_value: Mapping[str, Any], running_version: str
) -> tuple[dict[str, Any], Path, dict[str, str], str, str]:
    receipt = dict(receipt_value)
    if not _valid_seal(receipt, "receipt_fingerprint"):
        raise _ProjectionFailure("invalid-resolution", "Phase 2A.1 resolution receipt failed its integrity seal")
    if (
        receipt.get("state") != "ready"
        or receipt.get("effective_mode") != "full"
        or receipt.get("network_used") is not False
        or receipt.get("source_kind") != "tailtrail-bundled"
    ):
        raise _ProjectionFailure("invalid-resolution", "projection requires one ready offline bundled Full resolution receipt")
    root_value = receipt.get("verified_root")
    if not isinstance(root_value, str):
        raise _ProjectionFailure("invalid-resolution", "resolution receipt has no verified bundle root")
    bundle_root = Path(root_value)
    if bundle_root.is_symlink() or not bundle_root.is_dir() or bundle_root.resolve().as_posix() != root_value:
        raise _ProjectionFailure("unsafe-source", "verified bundle root is missing, unsafe, or no longer canonical")
    manifest, inventory, issues = _validate_bundle(
        bundle_root, str(receipt.get("host", "")), running_version
    )
    if issues or manifest is None:
        raise _ProjectionFailure("source-changed", "verified bundle no longer validates: " + "; ".join(item["detail"] for item in issues))
    manifest_fingerprint = _file_fingerprint(bundle_root / "manifest.json")
    if manifest_fingerprint != receipt.get("bundle_manifest_fingerprint"):
        raise _ProjectionFailure("source-changed", "bundle manifest fingerprint changed after Phase 2A.1 resolution")
    official = manifest.get("official") if isinstance(manifest.get("official"), dict) else {}
    for key, receipt_key in (
        ("source", "official_source"), ("revision", "official_revision"), ("commit", "official_commit")
    ):
        if official.get(key) != receipt.get(receipt_key):
            raise _ProjectionFailure("source-changed", f"bundle official {key} changed after resolution")
    complete_inventory = {"manifest.json": hashlib.sha256((bundle_root / "manifest.json").read_bytes()).hexdigest(), **inventory}
    identity = {
        "official_source": receipt["official_source"],
        "official_revision": receipt["official_revision"],
        "official_commit": receipt["official_commit"],
        "bundle_manifest_fingerprint": manifest_fingerprint,
        "inventory": [{"path": path, "sha256": complete_inventory[path]} for path in sorted(complete_inventory)],
        "tailtrail_compatibility_version": running_version,
    }
    return receipt, bundle_root, complete_inventory, _fingerprint(identity), _fingerprint(identity["inventory"])


def _projection_receipt(
    source_receipt: dict[str, Any],
    inventory: dict[str, str],
    pack_fingerprint: str,
    inventory_fingerprint: str,
    pack_path: str,
    target: Path,
) -> dict[str, Any]:
    payload = {
        "schema_version": "1",
        "type": "tailtrail-official-aidlc-project-projection",
        "state": "created",
        "source_resolution_fingerprint": source_receipt["receipt_fingerprint"],
        "source_manifest_fingerprint": source_receipt["bundle_manifest_fingerprint"],
        "source_kind": source_receipt["source_kind"],
        "resource_provider": source_receipt["resource_provider"],
        "trust_posture": source_receipt["trust_posture"],
        "artifact_identity_status": source_receipt["artifact_identity_status"],
        "official_source": source_receipt["official_source"],
        "official_revision": source_receipt["official_revision"],
        "official_commit": source_receipt["official_commit"],
        "pack_fingerprint": pack_fingerprint,
        "pack_path": pack_path,
        "project_identity_fingerprint": _fingerprint({"root": target.as_posix()}),
        "inventory_fingerprint": inventory_fingerprint,
        "inventory": [
            {"path": path, "sha256": inventory[path]}
            for path in sorted(inventory)
        ],
        "network_used": False,
    }
    return _sealed_document(payload, "projection_fingerprint")


def _validate_project_pack(
    pack: Path,
    inventory: dict[str, str],
    expected_receipt: dict[str, Any],
) -> list[dict[str, str]]:
    if pack.is_symlink() or not pack.is_dir():
        return [_issue("altered-destination", f"content-addressed pack is missing or unsafe: {pack}")]
    actual, inventory_issues = _inventory(pack, exclude=frozenset({"projection-receipt.json"}))
    issues = list(inventory_issues)
    if actual != inventory:
        issues.append(_issue("altered-destination", "content-addressed pack inventory or hashes do not match the verified source"))
    projection, projection_issues = _read_json(pack / "projection-receipt.json", "project projection receipt")
    issues.extend(projection_issues)
    if projection != expected_receipt or projection is None or not _valid_seal(projection, "projection_fingerprint"):
        issues.append(_issue("altered-destination", "project projection receipt is missing, altered, or inconsistent"))
    return issues


def _selector(pack_fingerprint: str, pack_path: str, projection_fingerprint: str) -> dict[str, Any]:
    return _sealed_document({
        "schema_version": "1",
        "type": "tailtrail-official-aidlc-current-selector",
        "selection_scope": "future-runs-only",
        "pack_fingerprint": pack_fingerprint,
        "pack_path": pack_path,
        "projection_fingerprint": projection_fingerprint,
    }, "selector_fingerprint")


def _validate_selector(selector: Mapping[str, Any]) -> list[dict[str, str]]:
    required = {
        "schema_version", "type", "selection_scope", "pack_fingerprint", "pack_path",
        "projection_fingerprint", "selector_fingerprint",
    }
    if set(selector) != required or not _valid_seal(selector, "selector_fingerprint"):
        return [_issue("invalid-selector", "future-run selector is malformed or failed its integrity seal")]
    fingerprint = str(selector.get("pack_fingerprint", ""))
    expected_path = ".tailtrail/official-aidlc/packs/" + fingerprint.removeprefix("sha256:")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", fingerprint) or selector.get("pack_path") != expected_path:
        return [_issue("invalid-selector", "future-run selector has an unsafe or inconsistent pack identity")]
    return []


def _staging_rows(packs: Path, markers: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(packs.glob(".staging-*")):
        marker_path = markers / f"{path.name}.json"
        marker, issues = _read_json(marker_path, "staging ownership marker")
        fingerprint = marker.get("staging_fingerprint") if marker and _valid_seal(marker, "staging_fingerprint") else None
        rows.append({
            "path": path.name,
            "staging_fingerprint": fingerprint,
            "state": "managed-stale" if fingerprint and not issues and path.is_dir() and not path.is_symlink() else "unverified-stale",
        })
    return rows


def _copy_inventory(source: Path, staging: Path, inventory: dict[str, str]) -> None:
    for relative in sorted(inventory):
        safe = _safe_relative(relative)
        if safe is None:
            raise _ProjectionFailure("unsafe-source", f"verified inventory contains an unsafe path: {relative}")
        source_path = source / safe
        if source_path.is_symlink() or not source_path.is_file():
            raise _ProjectionFailure("source-changed", f"verified source file became unsafe: {relative}")
        data = source_path.read_bytes()
        if hashlib.sha256(data).hexdigest() != inventory[relative]:
            raise _ProjectionFailure("source-changed", f"verified source file changed during projection: {relative}")
        destination = staging / safe
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    for directory in sorted({path.parent for path in staging.rglob("*")}, key=lambda item: len(item.parts), reverse=True):
        _sync_directory(directory)


def _rename_staging(staging: Path, destination: Path) -> None:
    transient = {errno.EACCES, errno.EPERM, errno.EBUSY}
    for attempt in range(3):
        try:
            os.rename(staging, destination)
            _sync_directory(destination.parent)
            return
        except OSError as error:
            if error.errno not in transient or attempt == 2:
                raise
            time.sleep(0.025 * (attempt + 1))


def _discard_owned_staging(staging: Path | None, marker_path: Path | None) -> None:
    """Clean an operation's own staging after a handled failure.

    Process-level interruptions deliberately bypass this helper so a later
    explicit recovery can inspect the sealed ownership marker before removing
    anything.
    """
    if staging is not None and staging.exists() and not staging.is_symlink():
        shutil.rmtree(staging)
    if marker_path is not None and marker_path.is_file() and not marker_path.is_symlink():
        marker_path.unlink()


def _safe_run_id(run_id: str) -> str:
    value = str(run_id).strip()
    if (
        value in {"", ".", ".."}
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value)
        or ".." in value
    ):
        raise _ProjectionFailure("unsafe-run-id", "run identity must be one bounded local identifier")
    return value


def _binding_relative(run_id: str) -> Path:
    digest = hashlib.sha256(run_id.encode("utf-8")).hexdigest()
    return Path(".tailtrail") / "official-aidlc" / "run-bindings" / f"{digest}.json"


def _readonly_target(target_root: Path) -> Path:
    requested = Path(target_root)
    if requested.is_symlink() or not requested.exists() or not requested.is_dir():
        raise _ProjectionFailure("unsafe-target", f"project target must be an existing non-symlink directory: {requested}")
    target = requested.resolve()
    if target == Path(target.anchor):
        raise _ProjectionFailure("unsafe-target", "project projection into a filesystem root is forbidden")
    return target


def _safe_managed_path(target: Path, relative: str, *, category: str) -> Path:
    safe = _safe_relative(relative)
    if safe is None:
        raise _ProjectionFailure(category, f"managed path is unsafe: {relative}")
    path = target / safe
    try:
        path.resolve().relative_to(target)
    except (OSError, ValueError) as error:
        raise _ProjectionFailure(category, f"managed path escapes the project root: {relative}") from error
    cursor = target
    for part in PurePosixPath(safe).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise _ProjectionFailure(category, f"managed path contains a symbolic link: {relative}")
    return path


def _inventory_from_projection(receipt: Mapping[str, Any]) -> dict[str, str]:
    rows = receipt.get("inventory")
    if not isinstance(rows, list) or not rows:
        raise _ProjectionFailure("invalid-projection", "projection receipt has no closed inventory")
    inventory: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise _ProjectionFailure("invalid-projection", "projection inventory entry is malformed")
        path = _safe_relative(row.get("path"))
        digest = row.get("sha256")
        if path is None or not isinstance(digest, str) or not SHA256.fullmatch(digest) or path in inventory:
            raise _ProjectionFailure("invalid-projection", "projection inventory is unsafe, duplicated, or malformed")
        inventory[path] = digest
    return inventory


def _load_project_pack(
    target: Path,
    pack_path: str,
    *,
    expected_pack_fingerprint: str | None = None,
    expected_projection_fingerprint: str | None = None,
    issue_category: str = "invalid-projection",
) -> tuple[Path, dict[str, Any], dict[str, str]]:
    fingerprint = str(expected_pack_fingerprint or "")
    if fingerprint and not re.fullmatch(r"sha256:[0-9a-f]{64}", fingerprint):
        raise _ProjectionFailure(issue_category, "pack fingerprint is malformed")
    if fingerprint:
        expected_path = ".tailtrail/official-aidlc/packs/" + fingerprint.removeprefix("sha256:")
        if pack_path != expected_path:
            raise _ProjectionFailure(issue_category, "pack path does not match its content identity")
    pack = _safe_managed_path(target, pack_path, category=issue_category)
    if pack.is_symlink() or not pack.is_dir():
        raise _ProjectionFailure(issue_category, "bound content-addressed pack is missing or unsafe")
    projection_path = pack / "projection-receipt.json"
    projection, issues = _read_json(projection_path, "project projection receipt")
    if issues or projection is None or not _valid_seal(projection, "projection_fingerprint"):
        raise _ProjectionFailure(issue_category, "project projection receipt is missing or failed its integrity seal")
    if projection.get("pack_path") != pack_path:
        raise _ProjectionFailure(issue_category, "project projection receipt names a different pack path")
    if fingerprint and projection.get("pack_fingerprint") != fingerprint:
        raise _ProjectionFailure(issue_category, "project projection receipt names a different pack fingerprint")
    if expected_projection_fingerprint and projection.get("projection_fingerprint") != expected_projection_fingerprint:
        raise _ProjectionFailure(issue_category, "project projection fingerprint does not match the frozen identity")
    if projection.get("project_identity_fingerprint") != _fingerprint({"root": target.as_posix()}):
        raise _ProjectionFailure(issue_category, "project projection receipt belongs to a different project root")
    inventory = _inventory_from_projection(projection)
    pack_issues = _validate_project_pack(pack, inventory, projection)
    if pack_issues:
        raise _ProjectionFailure(issue_category, "; ".join(item["detail"] for item in pack_issues))
    return pack, projection, inventory


def _projection_identity(target: Path, value: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    result = dict(value)
    if not _valid_seal(result, "receipt_fingerprint"):
        raise _ProjectionFailure("invalid-projection", "Phase 2A.2 projection result failed its integrity seal")
    if result.get("state") != "ready" or result.get("status") not in {"created", "reused"}:
        raise _ProjectionFailure("invalid-projection", "run binding requires one ready Phase 2A.2 projection result")
    if result.get("network_used") is not False:
        raise _ProjectionFailure("invalid-projection", "projection result does not preserve the offline boundary")
    pack_path = str(result.get("pack_path", ""))
    _, projection, _ = _load_project_pack(
        target,
        pack_path,
        expected_pack_fingerprint=str(result.get("pack_fingerprint", "")),
        expected_projection_fingerprint=str(result.get("projection_fingerprint", "")),
    )
    if projection.get("source_resolution_fingerprint") != result.get("source_resolution_fingerprint"):
        raise _ProjectionFailure("invalid-projection", "projection result and receipt disagree on their source resolution")
    return result, projection


def _binding_blocked(run_id: str, issues: list[dict[str, str]]) -> dict[str, Any]:
    return _sealed_document({
        "schema_version": "1",
        "type": "tailtrail-official-aidlc-run-binding-result",
        "state": "blocked",
        "run_id": run_id,
        "selector_consulted": False,
        "network_used": False,
        "issues": issues,
    }, "receipt_fingerprint")


def provision(inputs: ProjectionInputs) -> dict[str, Any]:
    """Atomically create or reuse one verified content-addressed project pack."""
    try:
        source_receipt, source_root, inventory, pack_fingerprint, inventory_fingerprint = _validated_source(
            inputs.resolution_receipt, inputs.running_version
        )
        target, official, packs, locks, markers = _target_layout(inputs.target_root)
    except _ProjectionFailure as error:
        return _projection_blocked([_issue(error.category, str(error))])

    pack_name = pack_fingerprint.removeprefix("sha256:")
    pack_path = f".tailtrail/official-aidlc/packs/{pack_name}"
    destination = target / pack_path
    projection_receipt = _projection_receipt(
        source_receipt, inventory, pack_fingerprint, inventory_fingerprint, pack_path, target
    )
    expected_selector = _selector(
        pack_fingerprint, pack_path, projection_receipt["projection_fingerprint"]
    )
    stale_staging: list[dict[str, Any]] = []
    staging: Path | None = None
    marker_path: Path | None = None
    try:
        with _BoundedFileLock(
            locks / "provision.lock", inputs.lock_timeout_seconds, inputs.lock_poll_seconds
        ):
            if inputs.fault:
                inputs.fault("after-lock")
            stale_staging = _staging_rows(packs, markers)
            selector_path = official / "current.json"
            if selector_path.exists():
                selector_value, selector_issues = _read_json(selector_path, "future-run selector")
                selector_issues.extend(_validate_selector(selector_value or {}))
                if selector_issues:
                    raise _ProjectionFailure("invalid-selector", "; ".join(item["detail"] for item in selector_issues))
                if selector_value != expected_selector:
                    raise _ProjectionFailure(
                        "selector-conflict",
                        "future-run selector already names a different pack; explicit migration approval is required",
                    )

            if destination.exists():
                destination_issues = _validate_project_pack(destination, inventory, projection_receipt)
                if destination_issues:
                    return _projection_blocked(
                        destination_issues,
                        pack_fingerprint=pack_fingerprint,
                        pack_path=pack_path,
                        stale_staging=stale_staging,
                    )
                status = "reused"
            else:
                operation_id = uuid.uuid4().hex
                staging = packs / f".staging-{operation_id}"
                staging.mkdir()
                marker_payload = {
                    "schema_version": "1",
                    "type": "tailtrail-official-aidlc-staging-marker",
                    "staging_name": staging.name,
                    "pack_fingerprint": pack_fingerprint,
                    "source_resolution_fingerprint": source_receipt["receipt_fingerprint"],
                    "project_identity_fingerprint": _fingerprint({"root": target.as_posix()}),
                }
                marker = _sealed_document(marker_payload, "staging_fingerprint")
                marker_path = markers / f"{staging.name}.json"
                _atomic_json_file(marker_path, marker)
                if inputs.fault:
                    inputs.fault("after-staging-marker")
                _copy_inventory(source_root, staging, inventory)
                _atomic_json_file(staging / "projection-receipt.json", projection_receipt)
                staging_issues = _validate_project_pack(staging, inventory, projection_receipt)
                if staging_issues:
                    raise _ProjectionFailure("staging-invalid", "; ".join(item["detail"] for item in staging_issues))
                if inputs.fault:
                    inputs.fault("before-rename")
                _rename_staging(staging, destination)
                staging = None
                marker_path.unlink()
                marker_path = None
                status = "created"

            if not selector_path.exists():
                _atomic_json_file(selector_path, expected_selector)
            final_issues = _validate_project_pack(destination, inventory, projection_receipt)
            if final_issues:
                return _projection_blocked(
                    final_issues,
                    pack_fingerprint=pack_fingerprint,
                    pack_path=pack_path,
                    stale_staging=stale_staging,
                )
            return _seal_receipt({
                "schema_version": "1",
                "type": "tailtrail-official-aidlc-project-projection-result",
                "state": "ready",
                "status": status,
                "pack_fingerprint": pack_fingerprint,
                "pack_path": pack_path,
                "projection_fingerprint": projection_receipt["projection_fingerprint"],
                "selector_fingerprint": expected_selector["selector_fingerprint"],
                "source_resolution_fingerprint": source_receipt["receipt_fingerprint"],
                "trust_posture": source_receipt["trust_posture"],
                "network_used": False,
                "stale_staging": stale_staging,
                "issues": [],
            })
    except _ProjectionFailure as error:
        _discard_owned_staging(staging, marker_path)
        return _projection_blocked(
            [_issue(error.category, str(error))],
            pack_fingerprint=pack_fingerprint,
            pack_path=pack_path,
            stale_staging=stale_staging,
        )
    except Exception as error:
        _discard_owned_staging(staging, marker_path)
        return _projection_blocked(
            [_issue("projection-io-failure", f"project projection failed: {error}")],
            pack_fingerprint=pack_fingerprint,
            pack_path=pack_path,
            stale_staging=stale_staging,
        )


def bind_run(inputs: BindingInputs) -> dict[str, Any]:
    """Freeze one run to a verified Phase 2A.2 pack without using the selector."""
    run_id = str(inputs.run_id)
    try:
        run_id = _safe_run_id(run_id)
        target = _readonly_target(inputs.target_root)
        projection_result, projection = _projection_identity(target, inputs.projection_result)
        _, official, _, locks, _ = _target_layout(target)
        bindings = official / "run-bindings"
        if bindings.exists() and (bindings.is_symlink() or not bindings.is_dir()):
            raise _ProjectionFailure("unsafe-target", "run-binding root is unsafe")
        bindings.mkdir(exist_ok=True)
        binding_path = target / _binding_relative(run_id)
        payload = _sealed_document({
            "schema_version": "1",
            "type": "tailtrail-official-aidlc-run-binding",
            "state": "ready",
            "run_id": run_id,
            "compatibility_mode": "bundled-v2",
            "pack_path": projection_result["pack_path"],
            "pack_fingerprint": projection_result["pack_fingerprint"],
            "projection_fingerprint": projection_result["projection_fingerprint"],
            "source_resolution_fingerprint": projection_result["source_resolution_fingerprint"],
            "project_identity_fingerprint": projection["project_identity_fingerprint"],
            "trust_posture": projection["trust_posture"],
            "artifact_identity_status": projection["artifact_identity_status"],
            "network_used": False,
            "selector_consulted": False,
            "can_authorize_new_full": True,
        }, "binding_fingerprint")
        with _BoundedFileLock(locks / "provision.lock", inputs.lock_timeout_seconds, inputs.lock_poll_seconds):
            if binding_path.exists():
                existing, issues = _read_json(binding_path, "active-run binding")
                if issues or existing is None or not _valid_seal(existing, "binding_fingerprint"):
                    raise _ProjectionFailure("altered-run-binding", "existing active-run binding is missing or altered")
                if existing != payload:
                    raise _ProjectionFailure("run-binding-conflict", "active run is already frozen to a different identity")
                result_status = "reused"
            else:
                _atomic_json_file(binding_path, payload)
                result_status = "created"
        return {
            **payload,
            "status": result_status,
            "binding_path": binding_path.relative_to(target).as_posix(),
            "issues": [],
        }
    except _ProjectionFailure as error:
        return _binding_blocked(run_id, [_issue(error.category, str(error))])
    except Exception as error:
        return _binding_blocked(run_id, [_issue("binding-io-failure", f"active-run binding failed: {error}")])


def resolve_bound_run(target_root: Path, run_id: str) -> dict[str, Any]:
    """Resolve one active run exclusively through its frozen binding."""
    requested_run_id = str(run_id)
    try:
        safe_run_id = _safe_run_id(requested_run_id)
        target = _readonly_target(target_root)
        binding_path = target / _binding_relative(safe_run_id)
        if binding_path.is_symlink() or not binding_path.is_file():
            raise _ProjectionFailure("missing-run-binding", "active run has no safe frozen pack binding")
        binding, issues = _read_json(binding_path, "active-run binding")
        if issues or binding is None or not _valid_seal(binding, "binding_fingerprint"):
            raise _ProjectionFailure("altered-run-binding", "active-run binding failed its integrity seal")
        if (
            binding.get("type") != "tailtrail-official-aidlc-run-binding"
            or binding.get("state") != "ready"
            or binding.get("run_id") != safe_run_id
            or binding.get("compatibility_mode") != "bundled-v2"
            or binding.get("network_used") is not False
            or binding.get("selector_consulted") is not False
        ):
            raise _ProjectionFailure("incompatible-run-binding", "active-run binding is incomplete or incompatible")
        _, projection, _ = _load_project_pack(
            target,
            str(binding.get("pack_path", "")),
            expected_pack_fingerprint=str(binding.get("pack_fingerprint", "")),
            expected_projection_fingerprint=str(binding.get("projection_fingerprint", "")),
            issue_category="altered-bound-pack",
        )
        comparisons = {
            "source_resolution_fingerprint": projection.get("source_resolution_fingerprint"),
            "project_identity_fingerprint": projection.get("project_identity_fingerprint"),
            "trust_posture": projection.get("trust_posture"),
            "artifact_identity_status": projection.get("artifact_identity_status"),
        }
        if any(binding.get(key) != value for key, value in comparisons.items()):
            raise _ProjectionFailure("incompatible-run-binding", "active-run binding conflicts with its projection receipt")
        return {
            **binding,
            "binding_path": binding_path.relative_to(target).as_posix(),
            "selector_consulted": False,
            "issues": [],
        }
    except _ProjectionFailure as error:
        return _binding_blocked(requested_run_id, [_issue(error.category, str(error))])
    except Exception as error:
        return _binding_blocked(requested_run_id, [_issue("binding-io-failure", f"active-run resolution failed: {error}")])


def _validate_legacy_manifest(pack: Path) -> dict[str, Any]:
    manifest, issues = _read_json(pack / "manifest.json", "legacy official pack manifest")
    if issues or manifest is None:
        raise _ProjectionFailure("legacy-pack-invalid", "legacy manifest is missing or malformed")
    if manifest.get("schema_version") != "1" or manifest.get("type") != "tailtrail-official-aidlc-pack":
        raise _ProjectionFailure("legacy-pack-incompatible", "bounded continuation requires a schema-v1 project pack")
    official = manifest.get("official")
    adapter = manifest.get("host_adapter")
    integrity = manifest.get("integrity")
    if (
        not isinstance(official, dict)
        or official.get("source") != OFFICIAL_SOURCE
        or not isinstance(adapter, dict)
        or not isinstance(integrity, dict)
        or integrity.get("algorithm") != "sha256"
        or not isinstance(integrity.get("files"), list)
    ):
        raise _ProjectionFailure("legacy-pack-invalid", "legacy manifest lacks its closed compatibility boundary")
    declared: dict[str, str] = {}
    for row in integrity["files"]:
        if not isinstance(row, dict):
            raise _ProjectionFailure("legacy-pack-invalid", "legacy integrity inventory is malformed")
        relative = _safe_relative(row.get("path"))
        digest = row.get("sha256")
        if relative is None or not isinstance(digest, str) or not SHA256.fullmatch(digest) or relative in declared:
            raise _ProjectionFailure("legacy-pack-invalid", "legacy integrity inventory is unsafe or duplicated")
        path = pack / relative
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise _ProjectionFailure("legacy-pack-altered", f"legacy pack file failed integrity: {relative}")
        declared[relative] = digest
    actual, actual_issues = _inventory(pack, exclude=frozenset({"manifest.json"}))
    if actual_issues or actual != declared:
        raise _ProjectionFailure("legacy-pack-altered", "legacy pack inventory differs from its manifest")
    return manifest


def resolve_legacy_run(inputs: LegacyRunInputs) -> dict[str, Any]:
    """Continue an already-approved v1 run without minting new Full authority."""
    requested_run_id = str(inputs.run_id)
    try:
        run_id = _safe_run_id(requested_run_id)
        target = _readonly_target(inputs.target_root)
        authority_root = f".tailtrail/runs/{run_id}/aidlc-official"
        bridge_relative = f"{authority_root}/bridge-v1.json"
        activation_relative = f"{authority_root}/activation-v1.json"
        bridge_path = _safe_managed_path(target, bridge_relative, category="legacy-authority-missing")
        activation_path = _safe_managed_path(target, activation_relative, category="legacy-authority-missing")
        bridge, bridge_issues = _read_json(bridge_path, "legacy official bridge")
        activation, activation_issues = _read_json(activation_path, "legacy official activation")
        if bridge_issues or activation_issues or bridge is None or activation is None:
            raise _ProjectionFailure("legacy-authority-missing", "saved legacy bridge or activation authority is missing or malformed")
        if (
            bridge.get("schema_version") != "1"
            or bridge.get("type") != "tailtrail-official-aidlc-bridge"
            or bridge.get("tailtrail_run_id") != run_id
            or activation.get("schema_version") != "1"
            or activation.get("type") != "tailtrail-official-aidlc-bridge-activation"
            or activation.get("tailtrail_run_id") != run_id
            or activation.get("state") != "approved-awaiting-host-attachment"
            or activation.get("bridge_artifact") != bridge_relative
        ):
            raise _ProjectionFailure("legacy-authority-missing", "legacy continuation requires matching existing bridge and activation authority")
        manifest_relative = str(bridge.get("compatibility_manifest", ""))
        if manifest_relative != ".tailtrail/official-aidlc/manifest.json":
            raise _ProjectionFailure("legacy-authority-missing", "legacy bridge does not name the bounded project manifest")
        manifest_path = _safe_managed_path(target, manifest_relative, category="legacy-pack-invalid")
        pack = manifest_path.parent
        manifest = _validate_legacy_manifest(pack)
        return _sealed_document({
            "schema_version": "1",
            "type": "tailtrail-official-aidlc-legacy-run-resolution",
            "state": "legacy-read-only",
            "run_id": run_id,
            "compatibility_mode": "legacy-v1-bounded-continuation",
            "pack_path": pack.relative_to(target).as_posix(),
            "official_revision": (manifest.get("official") or {}).get("revision"),
            "can_authorize_new_full": False,
            "selector_consulted": False,
            "network_used": False,
            "issues": [],
        }, "receipt_fingerprint")
    except _ProjectionFailure as error:
        return _binding_blocked(requested_run_id, [_issue(error.category, str(error))])
    except Exception as error:
        return _binding_blocked(requested_run_id, [_issue("legacy-resolution-failure", f"legacy continuation failed: {error}")])


def status(inputs: StatusInputs) -> dict[str, Any]:
    """Return a non-mutating projection of bundle, selector, pack, and run state."""
    try:
        target = _readonly_target(inputs.target_root)
    except _ProjectionFailure as error:
        return _sealed_document({
            "schema_version": "1", "type": "tailtrail-official-aidlc-status",
            "state": "blocked", "network_used": False, "provisioning_required": None,
            "issues": [_issue(error.category, str(error))],
        }, "status_fingerprint")

    package: dict[str, Any] = {"state": "not-supplied"}
    if inputs.resolution_receipt is not None:
        try:
            receipt, _, _, _, _ = _validated_source(inputs.resolution_receipt, inputs.running_version)
            package = {
                "state": "ready",
                "resource_provider": receipt["resource_provider"],
                "trust_posture": receipt["trust_posture"],
                "receipt_fingerprint": receipt["receipt_fingerprint"],
            }
        except _ProjectionFailure as error:
            package = {"state": "blocked", "issues": [_issue(error.category, str(error))]}

    official = target / ".tailtrail" / "official-aidlc"
    selector_state: dict[str, Any] = {"state": "missing"}
    projection_state: dict[str, Any] = {"state": "missing"}
    legacy_state: dict[str, Any] = {"state": "not-detected"}
    issues: list[dict[str, str]] = []
    if official.exists():
        if official.is_symlink() or not official.is_dir():
            issues.append(_issue("unsafe-target", "official AIDLC project root is unsafe"))
        else:
            selector_path = official / "current.json"
            if selector_path.is_file() and not selector_path.is_symlink():
                selector, selector_issues = _read_json(selector_path, "future-run selector")
                selector_issues.extend(_validate_selector(selector or {}))
                if selector_issues:
                    selector_state = {"state": "blocked", "issues": selector_issues}
                    issues.extend(selector_issues)
                else:
                    selector_state = {
                        "state": "ready",
                        "pack_fingerprint": selector["pack_fingerprint"],
                        "pack_path": selector["pack_path"],
                        "selector_fingerprint": selector["selector_fingerprint"],
                    }
                    try:
                        _, projection, _ = _load_project_pack(
                            target,
                            str(selector["pack_path"]),
                            expected_pack_fingerprint=str(selector["pack_fingerprint"]),
                            expected_projection_fingerprint=str(selector["projection_fingerprint"]),
                        )
                        projection_state = {
                            "state": "ready",
                            "pack_fingerprint": projection["pack_fingerprint"],
                            "projection_fingerprint": projection["projection_fingerprint"],
                        }
                    except _ProjectionFailure as error:
                        projection_state = {"state": "blocked", "issues": [_issue(error.category, str(error))]}
                        issues.extend(projection_state["issues"])
            legacy_manifest = official / "manifest.json"
            if legacy_manifest.is_file() and not legacy_manifest.is_symlink():
                try:
                    legacy = _validate_legacy_manifest(official)
                    legacy_state = {
                        "state": "legacy-v1-readable-only",
                        "official_revision": (legacy.get("official") or {}).get("revision"),
                        "can_authorize_new_full": False,
                    }
                except _ProjectionFailure as error:
                    legacy_state = {"state": "blocked", "issues": [_issue(error.category, str(error))]}

    frozen: dict[str, Any] = {"state": "not-requested"}
    if inputs.run_id is not None:
        frozen = resolve_bound_run(target, inputs.run_id)
        if frozen.get("state") == "blocked" and any(
            item.get("category") != "missing-run-binding" for item in frozen.get("issues", [])
        ):
            issues.extend(frozen.get("issues", []))

    provisioning_required = projection_state.get("state") != "ready"
    if issues or package.get("state") == "blocked":
        overall = "blocked"
    elif provisioning_required:
        overall = "provision-required"
    elif inputs.run_id is not None and frozen.get("state") != "ready":
        overall = "binding-required"
    else:
        overall = "ready"
    return _sealed_document({
        "schema_version": "1",
        "type": "tailtrail-official-aidlc-status",
        "state": overall,
        "package": package,
        "future_selector": selector_state,
        "project_projection": projection_state,
        "frozen_run": frozen,
        "legacy_project": legacy_state,
        "provisioning_required": provisioning_required,
        "network_used": False,
        "issues": issues,
        "boundary": "Read-only status; no directory, selector, binding, pack, or recovery state was created or changed.",
    }, "status_fingerprint")


def recover_staging(inputs: RecoveryInputs) -> dict[str, Any]:
    """Remove exactly one fingerprint-matched managed stale staging directory."""
    try:
        target, official, packs, locks, markers = _target_layout(inputs.target_root)
        if not re.fullmatch(r"\.staging-[0-9a-f]{32}", inputs.staging_name):
            raise _ProjectionFailure("invalid-recovery-target", "staging name is not a managed projection staging identity")
        staging = packs / inputs.staging_name
        marker_path = markers / f"{inputs.staging_name}.json"
        with _BoundedFileLock(
            locks / "provision.lock", inputs.lock_timeout_seconds, inputs.lock_poll_seconds
        ):
            marker, marker_issues = _read_json(marker_path, "staging ownership marker")
            if marker_issues or marker is None or not _valid_seal(marker, "staging_fingerprint"):
                raise _ProjectionFailure("unverified-staging", "staging ownership marker is missing or invalid")
            if marker.get("staging_name") != inputs.staging_name or marker.get("staging_fingerprint") != inputs.staging_fingerprint:
                raise _ProjectionFailure("unverified-staging", "staging recovery fingerprint does not match the saved marker")
            if marker.get("project_identity_fingerprint") != _fingerprint({"root": target.as_posix()}):
                raise _ProjectionFailure("unverified-staging", "staging marker belongs to a different project root")
            if staging.is_symlink() or not staging.is_dir():
                raise _ProjectionFailure("unverified-staging", "staging target is missing, unsafe, or not a directory")
            for path in staging.rglob("*"):
                if path.is_symlink() or (not path.is_dir() and not path.is_file()):
                    raise _ProjectionFailure("unverified-staging", f"staging target contains an unsafe entry: {path.name}")
            shutil.rmtree(staging)
            marker_path.unlink()
            recovery = _sealed_document({
                "schema_version": "1",
                "type": "tailtrail-official-aidlc-staging-recovery",
                "state": "recovered",
                "staging_name": inputs.staging_name,
                "staging_fingerprint": inputs.staging_fingerprint,
                "project_identity_fingerprint": _fingerprint({"root": target.as_posix()}),
                "network_used": False,
            }, "recovery_fingerprint")
            recovery_path = official / "recovery" / f"{inputs.staging_fingerprint.removeprefix('sha256:')}.json"
            _atomic_json_file(recovery_path, recovery)
            return recovery
    except _ProjectionFailure as error:
        return _sealed_document({
            "schema_version": "1",
            "type": "tailtrail-official-aidlc-staging-recovery",
            "state": "blocked",
            "staging_name": inputs.staging_name,
            "staging_fingerprint": inputs.staging_fingerprint,
            "network_used": False,
            "issues": [_issue(error.category, str(error))],
        }, "recovery_fingerprint")


__all__ = [
    "BindingInputs", "LegacyRunInputs", "ProjectionInputs", "RecoveryInputs",
    "ResolverInputs", "StatusInputs", "bind_run", "provision", "recover_staging",
    "resolve", "resolve_bound_run", "resolve_legacy_run", "status",
]
