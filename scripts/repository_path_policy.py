#!/usr/bin/env python3
"""Central managed-workspace path policy for repository discovery.

Discovery-phase verdict only: answers "is this path even considerable?"
before candidate creation. It does NOT assign file-kind roles -- that stays
with ``classify_repository_role()`` in ``navigator_scope.py``. The mapping
is one line: any verdict other than ``application`` excludes the path with
the policy reason attached; only ``application`` paths reach file-kind
classification. No parallel owner/proof vocabulary is minted here.

Performance contract: pure string/path logic, zero I/O per call. Anything
needing Git (``git worktree list``) is computed once per run by the caller
and passed in via ``worktree_roots``. Matching is case-insensitive
throughout (Windows checkouts).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

APPLICATION = "application"
MANAGED_WORKTREE = "managed-worktree"
AGENT_MANAGED = "agent-managed"
TAILTRIAL_MANAGED = "tailtrail-managed"
GENERATED = "generated"
EXTERNAL = "external"
UNKNOWN = "unknown"

ROLES = frozenset({
    APPLICATION, MANAGED_WORKTREE, AGENT_MANAGED, TAILTRIAL_MANAGED,
    GENERATED, EXTERNAL, UNKNOWN,
})

DEFAULT_AGENT_ROOTS = frozenset({".claude", ".codex", ".copilot"})

TAILTRIAL_ROOTS = frozenset({".tailtrail", "tailtrail-meta", "tailtrail"})

# Workspace-context states: which repository is being classified.
# `tailtrail-source-checkout` is the verified TailTrail product repo where
# top-level product paths are application-eligible. Every other state
# preserves the existing exclusions (fail closed).
WORKSPACE_SOURCE_CHECKOUT = "tailtrail-source-checkout"
WORKSPACE_INSTALLED_PACK = "installed-tailtrail-pack"
WORKSPACE_ORDINARY = "ordinary-repository"
WORKSPACE_UNKNOWN = "unknown"
WORKSPACE_CONTEXTS = frozenset({
    WORKSPACE_SOURCE_CHECKOUT, WORKSPACE_INSTALLED_PACK,
    WORKSPACE_ORDINARY, WORKSPACE_UNKNOWN,
})
DETECTOR_VERSION = "1"
DETECTOR_MARKERS = (
    "pyproject-tailtrail-identity",
    "package-manifest-tailtrail-identity",
    "scripts-tailtrail-launcher",
    "tailtrail-package-marker",
    "tailtrail-registry-marker",
)
_MAX_MARKER_BYTES = 32_768

# Repo-owned convention guides (never implementation scope; cf. SKIP_DIRS
# parity and TAILTRAIL_MANAGED_PATH_PREFIXES for the tailtrail/ runtime).
CONVENTION_ROOTS = frozenset({"aidlc-rules"})

# IDE workspace metadata (never application code; old-list parity).
IDE_METADATA_DIRS = frozenset({".idea"})

VCS_METADATA_DIRS = frozenset({".git", ".hg", ".svn"})

# Local mirror of the generated/vendor dir names for workspace exclusion.
# File-kind classification stays canonical in navigator_scope.py; this set
# exists only so the hot path needs no imports.
GENERATED_PARTS = frozenset({
    ".cache", ".gradle", ".next", ".nuxt", ".pytest_cache", ".tox", ".venv",
    "__pycache__", "bin", "build", "coverage", "dist", "generated",
    "node_modules", "obj", "out", "target", "venv",
})
VENDOR_PARTS = frozenset({"deps", "third_party", "third-party", "vendor"})


def _normalize_parts(relative: str) -> tuple[str, ...] | None:
    text = str(relative).replace("\\", "/").strip().strip("/")
    if not text:
        return None
    pure = PurePosixPath(text)
    if pure.is_absolute() or ".." in pure.parts:
        return None
    return tuple(part.casefold() for part in pure.parts)


def _under_any(parts: tuple[str, ...], roots: Iterable[str]) -> bool:
    normalized = []
    for root in roots:
        cleaned = str(root).replace("\\", "/").strip().strip("/")
        if cleaned:
            normalized.append(tuple(part.casefold() for part in PurePosixPath(cleaned).parts))
    return any(parts[: len(prefix)] == prefix for prefix in normalized if prefix)


def git_worktree_roots(root: Path | str, *, timeout: float = 5.0) -> tuple[str, ...]:
    """Resolve linked Git worktree roots nested under ``root``, once per run.

    Calls ``git worktree list --porcelain`` exactly once; callers must cache
    the result for the whole run and pass it into ``classify_path``/
    ``exclusion_records`` as ``worktree_roots`` -- never re-invoked per path,
    per the classifier's zero-I/O-per-call contract. Returns root-relative
    POSIX paths for linked worktrees nested inside ``root``; the primary
    checkout itself and worktrees outside ``root`` are omitted. Fails closed
    to an empty tuple when Git is unavailable, absent, or the call errors.
    """
    root_path = Path(root).resolve()
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=root_path,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ()
    if result.returncode != 0:
        return ()
    roots: list[str] = []
    for line in result.stdout.splitlines():
        if not line.startswith("worktree "):
            continue
        candidate = Path(line[len("worktree "):].strip())
        try:
            candidate_resolved = candidate.resolve()
        except OSError:
            continue
        if candidate_resolved == root_path:
            continue
        try:
            relative = candidate_resolved.relative_to(root_path)
        except ValueError:
            continue
        roots.append(relative.as_posix())
    return tuple(roots)


def _read_bounded_text(path: Path, limit: int = _MAX_MARKER_BYTES) -> str | None:
    try:
        if not path.is_file():
            return None
        try:
            if path.stat().st_size > limit * 4:
                return None
        except OSError:
            return None
        with path.open("r", encoding="utf-8", errors="strict") as stream:
            return stream.read(limit)
    except (OSError, UnicodeDecodeError):
        return None


def _pyproject_has_tailtrail_identity(root: Path) -> tuple[bool, str]:
    text = _read_bounded_text(root / "pyproject.toml")
    if text is None:
        return False, "missing"
    found = re.search(r"""name\s*=\s*["']tailtrail["']""", text) is not None
    return found, "name=tailtrail" if found else "name-mismatch"


def _package_manifest_has_tailtrail_identity(root: Path) -> tuple[bool, str]:
    text = _read_bounded_text(root / "package-manifest.json")
    if text is None:
        return False, "missing"
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return False, "unparseable"
    package = payload.get("package") if isinstance(payload, dict) else None
    if package == "tailtrail":
        return True, "package=tailtrail"
    return False, f"package={package!r}"


def _normalize_workspace_context(value: Any) -> str:
    if isinstance(value, dict):
        state = str(value.get("state", "")).strip().casefold()
    else:
        state = str(value or "").strip().casefold()
    if state in WORKSPACE_CONTEXTS:
        return state
    return WORKSPACE_UNKNOWN


def detect_workspace_context(root: Path | str) -> dict[str, Any]:
    """Detect which workspace `root` is, with bounded one-time I/O.

    Installed-pack evidence (root-level `.tailtrail-install.json`) takes
    precedence over source-like files. Source checkout requires all five
    independent markers; a partial match is `unknown` (fail closed), zero
    markers is `ordinary-repository`. Never raises; I/O failures fail
    closed to `unknown`.
    """
    try:
        resolved = Path(root).resolve()
    except OSError:
        resolved = Path(str(root))
    try:
        if (resolved / ".tailtrail-install.json").is_file():
            markers = [{"name": "installed-pack-manifest", "present": True, "detail": ".tailtrail-install.json"}]
            return _workspace_receipt(WORKSPACE_INSTALLED_PACK, markers, ("installed-pack-evidence",))
    except OSError:
        pass
    checks: list[tuple[str, tuple[bool, str]]] = []
    try:
        checks.append((DETECTOR_MARKERS[0], _pyproject_has_tailtrail_identity(resolved)))
        checks.append((DETECTOR_MARKERS[1], _package_manifest_has_tailtrail_identity(resolved)))
        launcher = (resolved / "scripts" / "tailtrail.py").is_file()
        checks.append((DETECTOR_MARKERS[2], (bool(launcher), "scripts/tailtrail.py" if launcher else "missing")))
        package_marker = (resolved / "tailtrail" / "__init__.py").is_file()
        checks.append((DETECTOR_MARKERS[3], (bool(package_marker), "tailtrail/__init__.py" if package_marker else "missing")))
        registry = (resolved / "tailtrail-registry.json").is_file()
        checks.append((DETECTOR_MARKERS[4], (bool(registry), "tailtrail-registry.json" if registry else "missing")))
    except OSError:
        markers = [{"name": name, "present": False, "detail": "unreadable"} for name in DETECTOR_MARKERS]
        return _workspace_receipt(WORKSPACE_UNKNOWN, markers, ("detection-unreadable",))
    markers = [{"name": name, "present": bool(present), "detail": str(detail)} for name, (present, detail) in checks]
    matched = sum(1 for item in markers if item["present"])
    if matched == len(markers):
        return _workspace_receipt(WORKSPACE_SOURCE_CHECKOUT, markers, ("verified-source-markers",))
    if matched == 0:
        return _workspace_receipt(WORKSPACE_ORDINARY, markers, ("no-product-identity",))
    return _workspace_receipt(WORKSPACE_UNKNOWN, markers, ("partial-markers-fail-closed",))


def _workspace_receipt(state: str, markers: list[dict[str, Any]], reason_codes: tuple[str, ...]) -> dict[str, Any]:
    fingerprint = "sha256:" + hashlib.sha256(
        json.dumps(
            {"state": state, "markers": markers, "detector_version": DETECTOR_VERSION},
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "1",
        "type": "tailtrail-workspace-context",
        "state": state,
        "markers_checked": markers,
        "reason_codes": list(reason_codes),
        "detector_version": DETECTOR_VERSION,
        "fingerprint": fingerprint,
    }


def unknown_workspace_receipt() -> dict[str, Any]:
    markers = [{"name": name, "present": False, "detail": "not-checked"} for name in DETECTOR_MARKERS]
    return _workspace_receipt(WORKSPACE_UNKNOWN, markers, ("context-unavailable-fail-closed",))


def classify_path(
    root: Path | str,
    relative: str,
    *,
    worktree_roots: Iterable[str] = (),
    agent_roots: Iterable[str] | None = None,
    workspace_context: Any = WORKSPACE_UNKNOWN,
) -> tuple[str, tuple[str, ...]]:
    """Classify one repo-relative path. Never touches disk.

    First match wins (fixed precedence keeps fingerprints stable):
    external -> managed-worktree (Git list, then generic `worktrees`
    component) -> agent-managed -> generated/vendor/VCS metadata ->
    verified source-checkout product exception -> tailtrail-managed ->
    application. State (tailtrail, including the tailtrail/ runtime),
    agent, VCS, convention-guide (aidlc-rules), and IDE-metadata roots
    also match at any depth: nested copies of these directories are never
    application code. Empty or escaping paths are `external` when they
    leave the root, else `unknown`. ``worktree_roots`` should come from one
    cached ``git_worktree_roots()`` call per run, not a call per path.
    ``workspace_context`` is a precomputed state string or receipt dict;
    per-path calls never detect (zero I/O preserved). Omitted or
    unrecognized contexts fail closed to `unknown`, preserving the
    historical exclusions byte-for-byte.
    """
    _ = root  # Reserved: keeps the (root, relative) call shape stable.
    text = str(relative).replace("\\", "/").strip()
    if not text:
        return UNKNOWN, ("unclassifiable-path",)
    pure = PurePosixPath(text.strip("/"))
    if pure.is_absolute() or ".." in pure.parts:
        return EXTERNAL, ("outside-target-root",)
    parts = tuple(part.casefold() for part in pure.parts)
    if not parts:
        return APPLICATION, ("repository-root",)
    agents = {str(name).casefold() for name in (agent_roots if agent_roots is not None else DEFAULT_AGENT_ROOTS)}
    context = _normalize_workspace_context(workspace_context)
    if context == WORKSPACE_SOURCE_CHECKOUT and parts[0] in ("tailtrail", "aidlc-rules"):
        # Verified source-checkout exception only: top-level product paths
        # may be application-eligible. Every stronger precedence stays
        # stronger: worktree, agent, VCS, generated/vendor, and any nested
        # tailtrail/aidlc-rules copy never reaches here as parts[0].
        if (
            not _under_any(parts, worktree_roots)
            and "worktrees" not in parts
            and not (parts[0] in agents or any(part in agents for part in parts[1:]))
            and not (parts[0] in VCS_METADATA_DIRS or any(part in VCS_METADATA_DIRS for part in parts[1:]))
            and not (set(parts) & (GENERATED_PARTS | VENDOR_PARTS))
        ):
            if parts[0] == "tailtrail":
                return APPLICATION, ("tailtrail-product-source",)
            return APPLICATION, ("bundled-aidlc-product-asset",)
    if parts[0] in TAILTRIAL_ROOTS:
        return TAILTRIAL_MANAGED, ("tailtrail-state",)
    if _under_any(parts, worktree_roots):
        return MANAGED_WORKTREE, ("git-worktree-copy",)
    if "worktrees" in parts:
        return MANAGED_WORKTREE, ("generic-worktrees-component",)
    if parts[0] in agents:
        return AGENT_MANAGED, ("agent-managed-root",)
    if parts[0] in VCS_METADATA_DIRS:
        return GENERATED, ("vcs-metadata",)
    if any(part in TAILTRIAL_ROOTS for part in parts[1:]):
        return TAILTRIAL_MANAGED, ("tailtrail-state-nested",)
    if any(part in agents for part in parts[1:]):
        return AGENT_MANAGED, ("agent-managed-nested",)
    if any(part in VCS_METADATA_DIRS for part in parts[1:]):
        return GENERATED, ("vcs-metadata-nested",)
    if parts[0] in CONVENTION_ROOTS:
        return TAILTRIAL_MANAGED, ("managed-conventions",)
    if parts[0] in IDE_METADATA_DIRS:
        return GENERATED, ("ide-metadata",)
    if any(part in CONVENTION_ROOTS for part in parts[1:]):
        return TAILTRIAL_MANAGED, ("managed-conventions-nested",)
    if any(part in IDE_METADATA_DIRS for part in parts[1:]):
        return GENERATED, ("ide-metadata-nested",)
    hit = set(parts) & (GENERATED_PARTS | VENDOR_PARTS)
    if hit:
        dirnames = sorted(hit)
        if any(name in VENDOR_PARTS for name in dirnames):
            return GENERATED, ("vendor-path",)
        return GENERATED, ("generated-path",)
    return APPLICATION, ("application-path",)


def is_eligible(role: str) -> bool:
    """Whether a policy verdict may proceed to candidate creation."""
    return role == APPLICATION


def audit_record(root: Path | str, relative: str, **kwargs: Any) -> dict[str, Any]:
    """Explainable record for debugging without granting scope."""
    role, reasons = classify_path(root, relative, **kwargs)
    return {
        "path": str(relative).replace("\\", "/"),
        "role": role,
        "status": "eligible" if is_eligible(role) else "excluded",
        "reason_codes": list(reasons),
    }


def exclusion_records(
    root: Path | str, relatives: list[str] | tuple[str, ...] | set[str], **kwargs: Any
) -> list[dict[str, Any]]:
    """Candidate-level exclusion provenance (Phase 2 leftover).

    Returns one audit record per input path whose verdict is anything but
    ``application``. Pure string logic, no I/O; walkers feed it their own
    candidate pools so every exclusion carries its policy reason codes.
    """
    return [
        record
        for relative in relatives
        for record in [audit_record(root, str(relative), **kwargs)]
        if record["status"] == "excluded"
    ]
