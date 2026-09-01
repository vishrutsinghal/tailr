"""Resolve canonical TailTrail runs and workflow bindings without presentation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


def run_directories(root: Path) -> list[Path]:
    directory = root.resolve() / ".tailtrail" / "runs"
    return [item for item in sorted(directory.iterdir()) if item.is_dir()] if directory.is_dir() else []


def resolve_run(
    root: Path,
    run_id: str | None,
    show_lock: Callable[[Path, str], dict[str, Any]],
    *,
    states: set[str] | None = None,
) -> str:
    """Resolve exactly one canonical run; ambiguity always fails closed."""
    root = root.resolve()
    if run_id:
        lock = show_lock(root, run_id)
        if states and lock.get("status") not in states:
            raise ValueError(f"run `{run_id}` is `{lock.get('status')}`, expected: {', '.join(sorted(states))}")
        return run_id
    candidates: list[str] = []
    for directory in run_directories(root):
        try:
            lock = show_lock(root, directory.name)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not states or lock.get("status") in states:
            candidates.append(directory.name)
    if not candidates:
        raise ValueError("no matching TailTrail run was found; provide --run-id or start a task")
    if len(candidates) > 1:
        raise ValueError("multiple matching TailTrail runs exist; provide --run-id: " + ", ".join(candidates))
    return candidates[0]


def workflow_id(root: Path, run_id: str, suggested_id: Callable[[str], str], binding_path: Callable[[Path, str], Path]) -> str | None:
    candidate = suggested_id(run_id)
    return candidate if binding_path(root.resolve(), candidate).is_file() else None
