#!/usr/bin/env python3
"""Plan or apply a verified Mode A active-requirement restore."""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    if spec is None or spec.loader is None: raise RuntimeError(f"{name}.py is unavailable")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


LEDGER = load("run-ledger")
BOUNDARY = load("task-recovery-boundary")
GIT = load("git-readiness")


def run(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=False)
    if result.returncode != 0: raise ValueError(result.stderr.strip() or result.stdout.strip() or "Git command failed")
    return result.stdout.strip()


def boundary(root: Path, run_id: str) -> tuple[Path, dict[str, Any]]:
    path = BOUNDARY.boundary_path(root, run_id)
    if not path.exists(): raise ValueError("no Mode A recovery boundary exists")
    return path, BOUNDARY.read(path)


def plan(root: Path, run_id: str) -> dict[str, Any]:
    path, state = boundary(root, run_id); report = GIT.readiness(root)
    active = state.get("active_requirement_uid")
    issues: list[str] = []
    if not active: issues.append("no active requirement is available for recovery")
    if report.get("branch") != state.get("task_branch"): issues.append("current branch does not match the task recovery boundary")
    changes: list[tuple[str, str]] = []
    expected: list[str] = []
    if active:
        expected = state["requirements"].get(active, {}).get("expected_paths", [])
        try: changes = BOUNDARY.changed_paths(root)
        except ValueError as error: issues.append(str(error))
        if not changes: issues.append("there is no active diff to restore")
        if changes and not all(BOUNDARY.allowed(item[1], expected) for item in changes): issues.append("current diff includes paths outside the active requirement boundary")
    previous = state.get("last_checkpoint_commit", state.get("base_commit"))
    payload = {"schema_version": "1", "type": "tailtrail-task-recovery-plan", "run_id": run_id, "mode": "mode-a", "safe_to_apply": not issues, "active_requirement_uid": active, "restore_from_commit": previous, "expected_paths": expected, "changed_paths": [item[1] for item in changes], "issues": issues, "rule": "restore only verified active tracked paths; never reset or restore the repository as a whole"}
    directory = LEDGER.state_dir(root, run_id) / "recovery" / "plans"; artifact = directory / f"plan-{len(list(directory.glob('plan-*.json'))) + 1}.json"; LEDGER.atomic_json(artifact, payload)
    LEDGER.append_event(root, run_id, "recovery_planned", {"artifact": artifact.relative_to(LEDGER.state_dir(root, run_id)).as_posix(), "active_requirement_uid": active, "safe_to_apply": payload["safe_to_apply"], "issues": issues})
    return payload


def apply(root: Path, run_id: str, approved: bool) -> dict[str, Any]:
    if not approved: raise ValueError("recovery apply changes tracked files; rerun with --approved")
    payload = plan(root, run_id)
    if not payload["safe_to_apply"]: raise ValueError("recovery is unsafe: " + "; ".join(payload["issues"]))
    _, state = boundary(root, run_id)
    run(root, "restore", "--source", payload["restore_from_commit"], "--staged", "--worktree", "--", *payload["changed_paths"])
    remaining = BOUNDARY.changed_paths(root)
    if remaining: raise ValueError("restore did not leave a clean active diff; workspace preserved for inspection")
    state["recovery_attempts"].append({"requirement_uid": payload["active_requirement_uid"], "restore_from_commit": payload["restore_from_commit"], "paths": payload["changed_paths"], "outcome": "restored"})
    state["requirements"][payload["active_requirement_uid"]]["state"] = "restored"
    state["active_requirement_uid"] = None
    BOUNDARY.LEDGER.atomic_json(BOUNDARY.boundary_path(root, run_id), state)
    BOUNDARY.LEDGER.append_event(root, run_id, "recovery_applied", {"requirement_uid": payload["active_requirement_uid"], "restore_from_commit": payload["restore_from_commit"], "changed_paths": payload["changed_paths"], "outcome": "restored"})
    return {**payload, "applied": True}


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan or apply a safe Mode A active-requirement recovery.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "apply"):
        item = sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True)
        if name == "apply": item.add_argument("--approved", action="store_true")
    args = parser.parse_args(); root = args.root.resolve()
    try:
        result = apply(root, args.run_id, args.approved) if args.command == "apply" else plan(root, args.run_id)
        print(json.dumps(result, indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Task recovery error: {error}"); return 2


if __name__ == "__main__": raise SystemExit(main())
