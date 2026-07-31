#!/usr/bin/env python3
"""Classify and safely reverse an exact active-requirement patch when possible."""
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
    if spec is None or spec.loader is None:
        raise RuntimeError(f"{name}.py is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LEDGER = load("run-ledger")
BOUNDARY = load("task-recovery-boundary")


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=False)


def patch_paths(patch: Path) -> list[str]:
    text = patch.read_text(encoding="utf-8")
    if "GIT binary patch" in text or "rename from " in text or "copy from " in text:
        raise ValueError("binary, renamed, or copied patches are not safe for automated reconciliation")
    paths: list[str] = []
    for line in text.splitlines():
        if not line.startswith("diff --git a/"):
            continue
        parts = line.split()
        if len(parts) != 4 or not parts[2].startswith("a/") or not parts[3].startswith("b/"):
            raise ValueError("task patch has an unsupported diff header")
        path = parts[3][2:]
        if not path or path == "/dev/null" or Path(path).is_absolute() or ".." in Path(path).parts:
            raise ValueError("task patch has an unsafe path")
        paths.append(path)
    if not paths:
        raise ValueError("task patch contains no supported tracked-file diff")
    return sorted(set(paths))


def allowed(path: str, expected: list[str]) -> bool:
    return any(path == item or path.startswith(item.rstrip("/") + "/") for item in expected)


def digest(root: Path, path: str) -> str | None:
    candidate = root / path
    return "sha256:" + hashlib.sha256(candidate.read_bytes()).hexdigest() if candidate.is_file() else None


def plan(root: Path, run_id: str, patch: Path) -> dict[str, Any]:
    boundary_path = BOUNDARY.boundary_path(root, run_id)
    state = BOUNDARY.read(boundary_path)
    active = state.get("active_requirement_uid")
    if not active:
        raise ValueError("no active requirement is available for reconciliation")
    record = state.get("requirements", {}).get(active, {})
    expected = record.get("expected_paths", [])
    paths = patch_paths(patch)
    status = BOUNDARY.changed_paths(root)
    changed = [item[1] for item in status]
    outside = [path for path in paths if not allowed(path, expected)]
    unrelated = [path for path in changed if path not in paths]
    reverse = git(root, "apply", "--check", "--reverse", str(patch))
    forward = git(root, "apply", "--check", str(patch))
    if outside:
        classification, decision, safe = "scope-conflict", "preserve-work-and-replan", False
        reason = "task patch contains paths outside the approved active requirement boundary"
    elif reverse.returncode == 128 or forward.returncode == 128:
        classification, decision, safe = "invalid-task-patch", "preserve-work-and-recapture-patch", False
        reason = "Git rejected the supplied task patch; recapture an exact valid patch before recovery"
    elif reverse.returncode == 0:
        classification, decision, safe = "exact-task-patch", "auto-reverse-task-patch", True
        reason = "Git proved the exact task-owned reverse patch applies cleanly"
    elif forward.returncode == 0:
        classification, decision, safe = "task-patch-absent", "preserve-work-no-recovery", False
        reason = "the supplied task patch is not present in the working tree"
    else:
        classification, decision, safe = "same-hunk-overlap", "bounded-reconciliation-plan", False
        reason = "the task reverse patch no longer applies cleanly; later or concurrent edits overlap its hunks"
    payload = {
        "schema_version": "1", "type": "tailtrail-recovery-reconciliation", "run_id": run_id,
        "active_requirement_uid": active, "patch": patch.as_posix(), "task_paths": paths,
        "changed_paths": changed, "unrelated_changed_paths": unrelated,
        "classification": classification, "decision": decision, "safe_to_apply": safe,
        "reason": reason, "reverse_check": {"exit_code": reverse.returncode, "stderr": reverse.stderr.strip()},
        "preservation_fingerprints": {path: digest(root, path) for path in unrelated},
        "boundary": "only a Git-verified reverse of the supplied task-owned patch may be applied; no whole-file restore or repository reset",
    }
    folder = LEDGER.state_dir(root, run_id) / "recovery" / "reconciliation"
    artifact = folder / f"assessment-{len(list(folder.glob('assessment-*.json'))) + 1}.json"
    LEDGER.atomic_json(artifact, payload)
    LEDGER.append_event(root, run_id, "recovery_reconciled", {"artifact": artifact.relative_to(LEDGER.state_dir(root, run_id)).as_posix(), "classification": classification, "decision": decision, "safe_to_apply": safe})
    return payload


def apply(root: Path, run_id: str, patch: Path, approved: bool) -> dict[str, Any]:
    if not approved:
        raise ValueError("reconciliation apply changes only task-owned hunks; rerun with --approved")
    payload = plan(root, run_id, patch)
    if not payload["safe_to_apply"]:
        raise ValueError("reconciliation is not safe to apply: " + payload["classification"])
    before = payload["preservation_fingerprints"]
    result = git(root, "apply", "--reverse", str(patch))
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "reverse patch apply failed")
    changed = {path: digest(root, path) for path in before}
    if changed != before:
        raise ValueError("reconciliation unexpectedly changed a preserved path")
    LEDGER.append_event(root, run_id, "recovery_reconciled", {"classification": "applied", "decision": "reversed-exact-task-patch", "task_paths": payload["task_paths"]})
    return {**payload, "applied": True}


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify or safely apply an exact task-patch reconciliation.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "apply"):
        item = sub.add_parser(name)
        item.add_argument("--root", type=Path, default=Path.cwd())
        item.add_argument("--run-id", required=True)
        item.add_argument("--task-patch", type=Path, required=True)
        if name == "apply": item.add_argument("--approved", action="store_true")
    args = parser.parse_args()
    try:
        result = apply(args.root.resolve(), args.run_id, args.task_patch.resolve(), args.approved) if args.command == "apply" else plan(args.root.resolve(), args.run_id, args.task_patch.resolve())
        print(json.dumps(result, indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Recovery reconciliation error: {error}"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
