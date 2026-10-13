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

TAILTRIAL_ROOTS = frozenset({".tailtrail", "tailtrail-meta"})

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


def classify_path(
    root: Path | str,
    relative: str,
    *,
    worktree_roots: Iterable[str] = (),
    agent_roots: Iterable[str] | None = None,
) -> tuple[str, tuple[str, ...]]:
    """Classify one repo-relative path. Never touches disk.

    First match wins (fixed precedence keeps fingerprints stable):
    external -> tailtrail-managed -> managed-worktree (Git list, then
    generic `worktrees` component) -> agent-managed -> generated/vendor/VCS
    metadata -> application. Empty or escaping paths are `external` when
    they leave the root, else `unknown`.
    """
    _ = root  # Reserved: keeps the (root, relative) call shape stable.
    text = str(relative).replace("\\", "/").strip()
    if not text:
        return UNKNOWN, ("unclassifiable-path",)
    pure = PurePosixPath(text.strip("/"))
    if pure.is_absolute() or ".." in pure.parts:
        return EXTERNAL, ("outside-target-root",)
    parts = tuple(part.casefold() for part in pure.parts)
    agents = {str(name).casefold() for name in (agent_roots if agent_roots is not None else DEFAULT_AGENT_ROOTS)}
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
