#!/usr/bin/env python3
"""Create, approve, inspect, and enforce a local TailTrail Planning Lock."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def ledger() -> Any:
    spec = importlib.util.spec_from_file_location("planning_lock_ledger", ROOT / "scripts" / "run-ledger.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


L = ledger()


def lock_path(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "planning" / "lock-v1.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def suggested_run_id(root: Path, goal: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    digest = hashlib.sha256(goal.encode("utf-8")).hexdigest()[:6]
    base = f"start-{stamp}-{digest}"
    candidate = base
    index = 2
    while L.state_dir(root, candidate).exists():
        candidate = f"{base}-{index}"
        index += 1
    return candidate


def create(root: Path, goal: str, run_id: str | None = None, reference_roots: list[str] | None = None) -> dict[str, Any]:
    root = root.resolve()
    selected_run_id = run_id or suggested_run_id(root, goal)
    if Path(selected_run_id).name != selected_run_id:
        raise ValueError("run_id must be a single local run identifier")
    L.init_run(root, selected_run_id, goal)
    payload = {
        "schema_version": "1",
        "type": "tailtrail-planning-lock",
        "run_id": selected_run_id,
        "goal": goal,
        "status": "awaiting-approval",
        "writes_allowed": False,
        "reference_roots": [{"path": value, "access": "read-only"} for value in (reference_roots or [])],
        "approval": None,
        "boundary": "Planning Lock permits read-only planning artifacts only. Source edits, Git mutations, project commands, scanners, and managed patch application require a separate approval for this run.",
    }
    path = lock_path(root, selected_run_id)
    L.atomic_json(path, payload)
    L.append_event(root, selected_run_id, "planning_lock_created", {"artifact": path.relative_to(L.state_dir(root, selected_run_id)).as_posix(), "writes_allowed": False, "reference_roots": payload["reference_roots"]})
    return {**payload, "artifact": path.relative_to(root).as_posix()}


def show(root: Path, run_id: str) -> dict[str, Any]:
    path = lock_path(root.resolve(), run_id)
    if not path.is_file():
        raise ValueError(f"planning lock for run `{run_id}` does not exist")
    return {**read(path), "artifact": path.relative_to(root.resolve()).as_posix()}


def approve(root: Path, run_id: str, approved: bool) -> dict[str, Any]:
    if approved is not True:
        raise ValueError("planning approval requires --approved")
    root = root.resolve()
    path = lock_path(root, run_id)
    payload = show(root, run_id)
    if payload["status"] == "approved":
        return payload
    if payload["status"] != "awaiting-approval":
        raise ValueError(f"planning lock is not approvable from status `{payload['status']}`")
    payload["status"] = "approved"
    payload["writes_allowed"] = True
    payload["approval"] = {"kind": "explicit-command", "run_id": run_id}
    payload.pop("artifact", None)
    L.atomic_json(path, payload)
    L.append_event(root, run_id, "planning_lock_approved", {"artifact": path.relative_to(L.state_dir(root, run_id)).as_posix(), "writes_allowed": True})
    return show(root, run_id)


def assert_write_allowed(root: Path, run_id: str) -> dict[str, Any]:
    payload = show(root, run_id)
    if payload.get("status") != "approved" or payload.get("writes_allowed") is not True:
        raise ValueError(f"Planning Lock for run `{run_id}` is `{payload.get('status')}`; explicit approval is required before managed source changes")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start", help="Create a planning-only lock and local run.")
    start.add_argument("--root", type=Path, default=Path.cwd())
    start.add_argument("--goal", required=True)
    start.add_argument("--run-id")
    start.add_argument("--reference-root", action="append", default=[])
    approve_parser = sub.add_parser("approve", help="Explicitly allow managed writes for one planning run.")
    approve_parser.add_argument("--root", type=Path, default=Path.cwd())
    approve_parser.add_argument("--run-id", required=True)
    approve_parser.add_argument("--approved", action="store_true")
    for name in ("show", "assert-write"):
        item = sub.add_parser(name)
        item.add_argument("--root", type=Path, default=Path.cwd())
        item.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        if args.command == "start":
            payload = create(args.root, args.goal, args.run_id, args.reference_root)
        elif args.command == "approve":
            payload = approve(args.root, args.run_id, args.approved)
        elif args.command == "show":
            payload = show(args.root, args.run_id)
        else:
            payload = assert_write_allowed(args.root, args.run_id)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Planning Lock error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
