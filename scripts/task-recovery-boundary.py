#!/usr/bin/env python3
"""Create and maintain an approval-gated Mode A Git recovery boundary."""
from __future__ import annotations

import argparse
import hashlib
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
GIT = load("git-readiness")


def run(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=False)
    if result.returncode != 0: raise ValueError(result.stderr.strip() or result.stdout.strip() or "Git command failed")
    return result.stdout.strip()


def boundary_path(root: Path, run_id: str) -> Path:
    return LEDGER.state_dir(root, run_id) / "recovery" / "boundary.json"


def read(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))


def relative(path: str) -> str:
    value = Path(path)
    if value.is_absolute() or ".." in value.parts: raise ValueError("expected paths must be repository-relative")
    return value.as_posix()


def anchor(root: Path, run_id: str) -> dict[str, Any]:
    path = LEDGER.state_dir(root, run_id) / "anchors" / "approved-v1.json"
    if not path.exists(): raise ValueError("an approved anchor is required before creating a recovery boundary")
    return read(path)


def init(root: Path, run_id: str, expected_paths: list[str], approved: bool) -> dict[str, Any]:
    if not approved: raise ValueError("boundary init changes branches; rerun with --approved")
    report = GIT.readiness(root)
    if not report["ready"]: raise ValueError("Git readiness failed: " + "; ".join(report["issues"]))
    path = boundary_path(root, run_id)
    if path.exists(): raise ValueError("recovery boundary already exists")
    approved_anchor = anchor(root, run_id)
    derived = [item for row in approved_anchor["requirements"] for item in row["likely_paths"]]
    paths = sorted(set(relative(item) for item in (expected_paths or derived)))
    if not paths: raise ValueError("expected paths are required (or must be present in the approved anchor)")
    branch = f"tailtrail/{run_id}"
    existing = subprocess.run(["git", "-C", str(root), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], check=False)
    if existing.returncode == 0: raise ValueError(f"task branch `{branch}` already exists")
    run(root, "switch", "-c", branch)
    payload = {"schema_version": "1", "type": "tailtrail-task-recovery-boundary", "mode": "mode-a", "run_id": run_id, "task_branch": branch, "base_commit": report["head"], "expected_paths": paths, "active_requirement_uid": None, "requirements": {}, "recovery_attempts": []}
    LEDGER.atomic_json(path, payload)
    LEDGER.append_event(root, run_id, "recovery_boundary_created", {"artifact": path.relative_to(LEDGER.state_dir(root, run_id)).as_posix(), "task_branch": branch, "base_commit": report["head"], "expected_paths": paths})
    return payload


def activate(root: Path, run_id: str, requirement_uid: str) -> dict[str, Any]:
    path = boundary_path(root, run_id); payload = read(path); report = GIT.readiness(root)
    if not report["ready"]: raise ValueError("Git readiness failed: " + "; ".join(report["issues"]))
    if report["branch"] != payload["task_branch"]: raise ValueError("current branch does not match the task recovery boundary")
    if payload["active_requirement_uid"]: raise ValueError("another requirement is already active")
    row = next((row for row in anchor(root, run_id)["requirements"] if row["requirement_uid"] == requirement_uid), None)
    if row is None: raise ValueError("requirement UID is not in the approved anchor")
    paths = sorted(set(relative(item) for item in row["likely_paths"]))
    if not paths: raise ValueError("active requirement has no approved likely paths")
    if not all(any(item == allowed or item.startswith(allowed.rstrip("/") + "/") for allowed in payload["expected_paths"]) for item in paths): raise ValueError("requirement paths are outside the approved task boundary")
    payload["active_requirement_uid"] = requirement_uid
    payload["requirements"].setdefault(requirement_uid, {"expected_paths": paths, "state": "active"})
    LEDGER.atomic_json(path, payload)
    LEDGER.append_event(root, run_id, "recovery_requirement_activated", {"requirement_uid": requirement_uid, "expected_paths": paths})
    return payload


def changed_paths(root: Path) -> list[tuple[str, str]]:
    result = subprocess.run(["git", "-C", str(root), "status", "--porcelain=v1", "--untracked-files=all"], text=True, capture_output=True, check=False)
    if result.returncode != 0: raise ValueError(result.stderr.strip() or "Git status failed")
    raw = result.stdout
    rows: list[tuple[str, str]] = []
    for line in raw.splitlines():
        if not line: continue
        status, path = line[:2], line[3:]
        if "R" in status or "C" in status or status == "??": raise ValueError("renamed, copied, or untracked files are not safe for Mode A checkpoint/recovery")
        rows.append((status, path.replace("\\", "/")))
    return rows


def allowed(path: str, expected: list[str]) -> bool:
    return any(path == item or path.startswith(item.rstrip("/") + "/") for item in expected)


def checkpoint(root: Path, run_id: str, requirement_uid: str, receipts: list[Path], approved: bool) -> dict[str, Any]:
    if not approved: raise ValueError("checkpoint creates a local commit; rerun with --approved")
    path = boundary_path(root, run_id); payload = read(path)
    if payload["active_requirement_uid"] != requirement_uid: raise ValueError("only the active requirement can be checkpointed")
    report = GIT.readiness(root)
    if report["branch"] != payload["task_branch"]: raise ValueError("current branch does not match the task recovery boundary")
    record = payload["requirements"][requirement_uid]; changes = changed_paths(root)
    if not changes: raise ValueError("active requirement has no changes to checkpoint")
    paths = [item[1] for item in changes]
    if not all(allowed(item, record["expected_paths"]) for item in paths): raise ValueError("current diff includes paths outside the active requirement boundary")
    run(root, "add", "-A", "--", *paths)
    run(root, "commit", "-m", f"tailtrail({run_id}): checkpoint {requirement_uid}")
    commit = run(root, "rev-parse", "HEAD"); ref = f"refs/tailtrail/{run_id}/{requirement_uid}"
    exists = subprocess.run(["git", "-C", str(root), "show-ref", "--verify", "--quiet", ref], check=False)
    if exists.returncode == 0: raise ValueError("requirement checkpoint ref already exists and is immutable")
    run(root, "update-ref", ref, commit)
    evidence = [{"path": item.as_posix(), "sha256": "sha256:" + hashlib.sha256(item.read_bytes()).hexdigest()} for item in receipts]
    record.update({"state": "validated", "checkpoint_commit": commit, "checkpoint_ref": ref, "changed_paths": paths, "validation_receipts": evidence})
    payload["active_requirement_uid"] = None; payload["last_checkpoint_commit"] = commit
    LEDGER.atomic_json(path, payload)
    LEDGER.append_event(root, run_id, "recovery_requirement_checkpointed", {"requirement_uid": requirement_uid, "commit": commit, "ref": ref, "changed_paths": paths, "receipt_count": len(evidence)})
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage TailTrail Mode A task branches and requirement checkpoints.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "activate", "checkpoint", "show"):
        item = sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True)
        if name == "init": item.add_argument("--expected-path", action="append", default=[]); item.add_argument("--approved", action="store_true")
        if name == "activate": item.add_argument("--requirement-uid", required=True)
        if name == "checkpoint": item.add_argument("--requirement-uid", required=True); item.add_argument("--receipt", type=Path, action="append", default=[]); item.add_argument("--approved", action="store_true")
    args = parser.parse_args(); root = args.root.resolve()
    try:
        if args.command == "init": result = init(root, args.run_id, args.expected_path, args.approved)
        elif args.command == "activate": result = activate(root, args.run_id, args.requirement_uid)
        elif args.command == "checkpoint": result = checkpoint(root, args.run_id, args.requirement_uid, args.receipt, args.approved)
        else: result = read(boundary_path(root, args.run_id))
        print(json.dumps(result, indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Task recovery boundary error: {error}"); return 2


if __name__ == "__main__": raise SystemExit(main())
