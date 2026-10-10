#!/usr/bin/env python3
"""Centralized write-access enforcement for the Sequential Worker Pipeline.

Three enforcement surfaces, all with explicit arguments (no guessing):

- :func:`guard_write` — guards a single in-repo file write. The caller
  passes ``root`` and ``path`` directly.
- :func:`validate_planned_paths` — proposal-time gate: validates planned
  paths against the active badge *before* approval, since host-agent
  writes happen outside this repo and cannot be intercepted in-process.
- the ``hook`` CLI entrypoint (``main()``) — closes that last gap for
  hosts that support a pre-write interception point. Registered as a
  Claude Code ``PreToolUse`` hook on Edit/Write/NotebookEdit, it reads
  the edited path from the hook's own stdin JSON and denies the tool
  call in real time when it falls outside the active run's approved
  scope, instead of only catching the drift after the fact at closure.

A guardian without a pipeline run denies writes unless the caller openly
declares ``permissive=True`` (installer flows, which have no run by
nature). There is no silent pass.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import navigator_scope
from pipeline_manager import PipelineManager
from pipeline_judge import PipelineJudge

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"{filename} is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANCHOR = _load("write_guardian_anchor", "change-intent-anchor.py")


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
    """Guard one file write with explicit root and path. This is the explicit single-file write guard. Raises on violation."""
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


def _latest_anchor_mtime(run_dir: Path) -> float:
    """Newest mtime among this run's approved anchor versions, or 0.0 if none.

    correct() only ever writes a new approved-vN.json under this
    directory -- checking just this glob (not the whole run tree) catches
    every correction without the cost or false-positive risk of a full
    recursive scan (see the module-level risk notes on why that was
    rejected: RunLock's own `.lock` file can be touched by a read-adjacent
    operation, which would make a merely-inspected run look "active").
    """
    anchors_dir = run_dir / "anchors"
    if not anchors_dir.is_dir():
        return 0.0
    best = 0.0
    for path in anchors_dir.glob("approved-v*.json"):
        try:
            best = max(best, path.stat().st_mtime)
        except OSError:
            continue
    return best


def _latest_event_timestamp(run_dir: Path) -> float:
    """Epoch time of this run's last logged event, or 0.0 if none/unreadable.

    Covers checkpoints, closures, and requirement activations -- anything
    that goes through the run ledger's own append_event(), without having
    to enumerate every artifact subdirectory those actions might also
    touch.
    """
    events_path = run_dir / "events.jsonl"
    if not events_path.is_file():
        return 0.0
    try:
        lines = [line for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        return 0.0
    if not lines:
        return 0.0
    try:
        last_event = json.loads(lines[-1])
        created_at = str(last_event.get("created_at", ""))
        return datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
    except (json.JSONDecodeError, ValueError, TypeError, AttributeError):
        return 0.0


def resolve_active_run(root: Path) -> str | None:
    """Resolve which run's approved scope a hook should enforce right now.

    Prefers the explicit ``TAILTRAIL_ACTIVE_RUN_ID`` environment variable
    (unambiguous, set by whoever activated the run). Falls back to the
    most recently *active* run with an approved Planning Lock -- not the
    most recently *approved* one. Those are different questions: a run
    approved an hour ago but corrected a minute ago is more "active" right
    now than a run approved thirty seconds ago and untouched since.
    Confirmed live this session: approving a second, unrelated run after
    already working on a first run made the old mtime-only version of this
    function silently start enforcing the wrong run's scope, even though
    the first run had a genuine correct() call moments earlier.

    "Activity" is the newest of three specific, well-understood signals
    per run -- not a recursive scan of the whole run directory, which was
    considered and rejected: it would cost real latency on every single
    Edit/Write/NotebookEdit call, and RunLock's own `.lock` file can be
    touched by a read-adjacent operation, which would make a run that was
    only ever inspected (e.g. via `tailtrail status`) look "active" too.
    The three signals: this run's ``planning/lock-v1.json`` mtime (the
    original signal, kept as a baseline), the newest ``anchors/
    approved-v*.json`` mtime (a mid-run correction), and the last logged
    event's timestamp in ``events.jsonl`` (a checkpoint, closure, or
    requirement activation).

    Returns ``None`` (nothing to enforce) when no run resolves, which
    callers must treat as "allow": most edits in a session have no active
    TailTrail run at all, and this guard must never become a blanket block
    for unrelated work.
    """
    explicit = os.environ.get("TAILTRAIL_ACTIVE_RUN_ID")
    if explicit:
        return explicit
    runs_dir = root / ".tailtrail" / "runs"
    if not runs_dir.is_dir():
        return None
    candidates: list[tuple[float, str]] = []
    for run_dir in runs_dir.iterdir():
        lock_path = run_dir / "planning" / "lock-v1.json"
        if not lock_path.is_file():
            continue
        try:
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if lock.get("status") != "approved":
            continue
        try:
            lock_mtime = lock_path.stat().st_mtime
        except OSError:
            continue
        freshness = max(lock_mtime, _latest_anchor_mtime(run_dir), _latest_event_timestamp(run_dir))
        candidates.append((freshness, run_dir.name))
    if not candidates:
        return None
    candidates.sort(key=lambda row: row[0])
    return candidates[-1][1]


def _anchor_path_str(item: Any) -> str | None:
    """Extract a path string from a plain-string or {path, role} anchor entry."""
    if isinstance(item, str):
        return item or None
    if isinstance(item, dict):
        path = item.get("path")
        return str(path) if isinstance(path, str) and path.strip() else None
    return None


def _anchor_role_map(anchor: dict[str, Any]) -> dict[str, str | None]:
    """Map approved path -> anchor role, tolerating both likely_paths shapes.

    Plain strings map to None (no trusted role; caller falls back to the
    classifier). Dict entries carry the Navigator/host-approved role the
    guard should trust first, so future extensions work without a
    classifier change.
    """
    roles: dict[str, str | None] = {}
    for row in anchor.get("requirements", []):
        if not isinstance(row, dict):
            continue
        for item in row.get("likely_paths", []) or []:
            if isinstance(item, dict):
                path = item.get("path")
                if isinstance(path, str) and path:
                    roles[str(path)] = str(item.get("role", "unknown"))
            elif isinstance(item, str) and item:
                roles.setdefault(item, None)
    return roles


def _correction_path_set(anchor: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    for correction in anchor.get("corrections", []) or []:
        if not isinstance(correction, dict):
            continue
        for item in correction.get("corrected_likely_paths", []) or []:
            found = _anchor_path_str(item)
            if found:
                paths.add(found)
    return paths


def anchor_aware_write_check(root: Path, run_id: str, path: str) -> tuple[bool, str | None]:
    """Check one path against the approved anchor first, then the active badge.

    Only a path named in one of the anchor's own ``corrections`` entries
    overrides the badge entirely, regardless of file role -- a correction
    is always an individual, reasoned, deliberate addition (see
    ``correct()``), the same way an explicit ``--changed`` path already
    overrides lexical-only classification elsewhere in Navigator. This is
    what lets a mid-run correction -- including adding a test case or any
    other previously-unapproved path -- actually become writable, not
    just recorded.

    Deliberately NOT the same thing as "any path present in the anchor's
    likely_paths": likely_paths is documented in planning_lock.py as
    "navigator hints, not an allow-list" and can legitimately bundle
    inspection-only and proof-only paths (never meant to be edited)
    alongside genuine implementation owners, depending on which internal
    requirement-matrix path a given goal took. Treating every bundled
    path as individually approved would silently let a merely-inspected
    or proof-only file through -- confirmed live: a simple one-line goal
    bundled scripts/mcp-server.py (inspection) and a test file (proof)
    into the same likely_paths as the one real implementation owner.

    Uses :func:`change-intent-anchor.latest_approved` rather than the
    original ``approved-v1.json`` directly, so a mid-run correction is
    honored immediately, not just the stale original approval.

    A path with no correction uses the anchor-approved role first (when the
    anchor stores a {path, role} entry), then the classifier as fallback --
    with one addition preserved from before: during the IMPLEMENTATION badge, an
    "implementation-owner"-role file must still be present in the
    anchor's (possibly bundled) likely_paths, not merely the right *kind*
    of file. The coarse role check alone cannot tell WHICH production
    file was approved, only that it is SOME production file. This is
    tolerant of the bundling concern above in a way the removed
    all-roles check was not: at worst it lets through an inspection-role
    file that happens to also classify as "implementation-owner" (an
    unlikely coincidence), never a test or configuration file. Every
    other role (test, configuration, ...) with no correction falls
    through to the plain role/badge check unchanged, so a never-approved
    test file is still denied there, just via the badge rule.

    A run with no approved anchor at all (not yet past Planning Lock
    approval) skips straight to the plain fallback -- there is nothing yet
    to compare the path against.
    """
    try:
        _, anchor = ANCHOR.latest_approved(root, run_id)
    except ValueError:
        anchor = None
    judge = PipelineJudge(root, run_id)
    if anchor is not None:
        if path in _correction_path_set(anchor):
            return True, None
        role_map = _anchor_role_map(anchor)
        approved_paths = set(role_map.keys())
        anchor_role = role_map.get(path)
        classifier_role, _ = navigator_scope.classify_repository_role(root, path)
        effective_role = anchor_role if anchor_role and anchor_role != "unknown" else classifier_role
        if judge.manager.get_current_stage() == "IMPLEMENTATION":
            if effective_role == "implementation-owner":
                if path not in approved_paths:
                    return False, (
                        f"Write access denied: `{path}` is not in run `{run_id}`'s approved scope. "
                        f"Approved paths: {sorted(approved_paths) or '(none)'}."
                    )
                return True, None
        if anchor_role and anchor_role != "unknown":
            contract = judge.manager.get_active_contract()
            if effective_role in contract.prohibited_write_roles:
                return False, f"Write access denied: Path `{path}` is a `{effective_role}`, which is prohibited for the active stage `{judge.manager.get_current_stage()}`."
            if effective_role not in contract.allowed_write_roles:
                return False, f"Write access denied: Path `{path}` is a `{effective_role}`, which is not in the allowed write-set for the active stage `{judge.manager.get_current_stage()}`."
            return True, None
    return judge.validate_write_access(path)


def _hook_response(decision: str, reason: str | None = None) -> dict[str, Any]:
    output: dict[str, Any] = {"hookEventName": "PreToolUse", "permissionDecision": decision}
    if reason:
        output["permissionDecisionReason"] = reason
    return {"hookSpecificOutput": output}


def run_hook(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Decide one PreToolUse event. Returns a hook response, or None to allow silently.

    Fails open on anything unexpected (missing fields, no active run,
    path outside the project, no anchor yet): a bug here must never
    become a blanket block on unrelated work. Only an affirmative,
    evidence-backed scope violation produces a "deny" response.
    """
    if payload.get("tool_name") not in {"Edit", "Write", "NotebookEdit"}:
        return None
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    file_path = tool_input.get("file_path")
    cwd = payload.get("cwd")
    if not file_path or not cwd:
        return None
    root = Path(cwd).resolve()
    guardian = WriteGuardian(root, permissive=True)
    if guardian.is_exempt(Path(file_path)):
        return None
    run_id = resolve_active_run(root)
    if run_id is None:
        return None
    try:
        relative_path = Path(file_path).resolve().relative_to(root).as_posix()
    except ValueError:
        return None
    try:
        allowed, error = anchor_aware_write_check(root, run_id, relative_path)
    except Exception:
        return None
    if allowed:
        return None
    return _hook_response("deny", error)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    response = run_hook(payload)
    if response is not None:
        print(json.dumps(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
