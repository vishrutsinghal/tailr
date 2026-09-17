#!/usr/bin/env python3
"""Centralized write-access enforcement for the Sequential Worker Pipeline.

Two enforcement surfaces, both with explicit arguments (no guessing):

- :func:`guard_write` — guards a single in-repo file write. The caller
  passes ``root`` and ``path`` directly.
- :func:`validate_planned_paths` — proposal-time gate: validates planned
  paths against the active badge *before* approval, since host-agent
  writes happen outside this repo and cannot be intercepted in-process.

A guardian without a pipeline run denies writes unless the caller openly
declares ``permissive=True`` (installer flows, which have no run by
nature). There is no silent pass.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import navigator_scope
from pipeline_manager import PipelineManager
from pipeline_judge import PipelineJudge


class SecurityBoundaryError(Exception):
    """Raised when a write attempt violates the active pipeline stage boundaries."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class WriteGuardian:
    """Intercepts file writes to ensure they align with the active pipeline badge."""

    def __init__(self, root: Path, run_id: str | None = None, *, permissive: bool = False):
        self.root = root.resolve()
        self.run_id = run_id or os.environ.get("TAILTRAIL_ACTIVE_RUN_ID")
        # Declared opt-out only: installer flows with no run state to enforce.
        self.permissive_mode = permissive and not self.run_id
        if self.run_id:
            self.manager = PipelineManager(self.root, self.run_id)
            self.judge = PipelineJudge(self.root, self.run_id)
        else:
            self.manager = None
            self.judge = None

    def is_exempt(self, path: Path) -> bool:
        """Paths that are always writable regardless of the active stage."""
        try:
            relative = path.resolve().relative_to(self.root)
        except ValueError:
            return False

        rel_str = relative.as_posix()
        if rel_str.startswith(".tailtrail/") or rel_str.startswith("tailtrail-meta/"):
            return True
        return False

    def validate_write(self, path: Path | str) -> None:
        """
        Verify if the current active worker has permission to edit the given path.
        Raises SecurityBoundaryError if the write is prohibited — including
        when there is no active run and no declared opt-out.
        """
        if isinstance(path, str):
            path = Path(path)

        path = path.resolve()

        if self.is_exempt(path):
            return

        if self.permissive_mode:
            return

        if self.judge is None:
            raise SecurityBoundaryError(
                "Write access denied: no active pipeline run for "
                f"`{self.root.as_posix()}`. Pass permissive=True to declare "
                "an unenforced write (installer flows only)."
            )

        try:
            relative_path = path.relative_to(self.root).as_posix()
        except ValueError:
            # If path is outside root, it's prohibited unless it's a known external target
            raise SecurityBoundaryError(f"Write access denied: Path `{path}` is outside the project root.")

        allowed, error = self.judge.validate_write_access(relative_path)
        if not allowed:
            raise SecurityBoundaryError(error)


def guard_write(
    root: Path | str,
    path: Path | str,
    *,
    run_id: str | None = None,
    permissive: bool = False,
) -> None:
    """Guard one file write with explicit root and path. Raises on violation."""
    WriteGuardian(Path(root), run_id, permissive=permissive).validate_write(path)


def validate_planned_paths(
    root: Path | str, run_id: str, paths: list[str]
) -> list[dict[str, Any]]:
    """Proposal-time gate: check planned paths against the active badge.

    Returns one row per path: ``{"path", "allowed", "reason"}``. Pure
    validation — writes nothing. Callers reject approval on any
    ``allowed: False`` row.
    """
    root_path = Path(root)
    judge = PipelineJudge(root_path, run_id)
    rows: list[dict[str, Any]] = []
    for raw in paths:
        rel = str(raw or "").replace("\\", "/").strip().strip("/")
        if not rel:
            continue
        allowed, error = judge.validate_write_access(rel)
        rows.append({"path": rel, "allowed": allowed, "reason": error})
    return rows
