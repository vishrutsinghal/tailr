"""Resolve canonical TailTrail runs and workflow bindings without presentation."""
from __future__ import annotations

import json
import importlib.util
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
    # A durable attachment is the conversational authority.  A detached or
    # stop-pending record must never be bypassed by scanning saved run folders.
    session_path = Path(__file__).resolve().parents[1] / "session_control.py"
    if session_path.is_file():
        spec = importlib.util.spec_from_file_location("tailtrail_run_resolution_session", session_path)
        if spec and spec.loader:
            session = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(session)
            attachment = session.status(root)
            if attachment.get("state") in {"detached", "stop-pending", "resume-check"}:
                raise ValueError("TailTrail routing is detached; use `tailtrail resume --run-id <exact-run-id>` first")
            attached = attachment.get("run_id") if attachment.get("state") == "attached" else None
            if attached:
                lock = show_lock(root, str(attached))
                if states and lock.get("status") not in states:
                    raise ValueError(f"run `{attached}` is `{lock.get('status')}`, expected: {', '.join(sorted(states))}")
                return str(attached)
    # Legacy workspaces have no attachment artifact. Preserve their existing
    # single-run behavior until Start or explicit resume creates the record.
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
