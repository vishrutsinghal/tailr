#!/usr/bin/env python3
"""Create and maintain an approval-gated Mode A Git recovery boundary."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    if spec is None or spec.loader is None: raise RuntimeError(f"{name}.py is unavailable")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


LEDGER = load("run-ledger")
GIT = load("git-readiness")
ANCHOR = load("change-intent-anchor")
_SCRIPTS_ROOT = str(ROOT / "scripts")
if _SCRIPTS_ROOT not in sys.path:
    sys.path.insert(0, _SCRIPTS_ROOT)
import navigator_scope as NAV_SCOPE  # type: ignore  # noqa: E402


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


def _statement_terms(statement: str) -> list[str]:
    return sorted({word.lower() for word in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", statement or "")})


def _fresh_scope_check(root: Path, run_id: str, row: dict[str, Any], payload: dict[str, Any], frozen_paths: list[str]) -> dict[str, Any]:
    """Re-check one requirement's scope against current repository state.

    Bounded, not a full repository rediscovery: seeds only the originally
    -approved likely_paths plus every path already changed by an earlier,
    already-checkpointed requirement in this same run (the "what's landed
    so far" context, read straight from this boundary's own recorded
    checkpoints -- no separate handoff artifact required, and never
    required for this check to run). Re-investigates with the same bounded,
    read-only engine used at Planning Lock time.
    """
    earlier_changed = sorted({
        str(changed_path)
        for record in payload.get("requirements", {}).values()
        if isinstance(record, dict)
        for changed_path in (record.get("changed_paths") or [])
    })
    seed_paths = sorted(set(frozen_paths) | set(earlier_changed))
    # Deliberately "repository-structure", not "explicit-path": an explicit
    # -path seed is auto-promoted to owner by investigate()'s self-edge rule
    # (the "--changed" trust contract), which would make every frozen path
    # trivially re-qualify regardless of this requirement's own terms --
    # defeating the freshness check. A weak, genuine-investigation seed lets
    # the same lexical/relationship evidence investigate() already computes
    # decide whether each path still qualifies.
    seeds = [NAV_SCOPE.seed(item, "repository-structure", "pre-activation-freshness-check") for item in seed_paths if (root / item).is_file()]
    if not seeds:
        return {"checked": False, "owners": sorted(frozen_paths), "reason": "no-seed-paths-exist-on-disk"}
    candidates = [NAV_SCOPE._candidate_dict(item) for item in NAV_SCOPE.candidates_from_seeds(root, seeds, [])]
    statement = str(row.get("statement", ""))
    frame = {
        "requirement_id": str(row["requirement_uid"]),
        "display_id": str(row.get("display_id", row["requirement_uid"])),
        "statement": statement,
        "query_terms": _statement_terms(statement),
    }
    semantic_matches: dict[str, set[str]] = {}
    rows, edges, investigation = NAV_SCOPE.investigate(
        root, [frame], candidates, [],
        allow_git_inventory=True, allow_persistent_cache=False, allow_passive_capture=False,
        semantic_matches_out=semantic_matches,
    )
    document = NAV_SCOPE.evidence_document(
        root, statement, [frame], [NAV_SCOPE._candidate_dict(item) for item in rows],
        edges=edges, investigation=investigation, semantic_matches=semantic_matches,
    )
    fresh_row = next((item for item in document.get("requirements", []) if item.get("requirement_id") == frame["requirement_id"]), None)
    owners = sorted(str(item) for item in (fresh_row.get("implementation_owners", []) if fresh_row else []))
    return {"checked": True, "owners": owners, "state": document.get("state")}


def _classify_scope_freshness(frozen_paths: list[str], fresh: dict[str, Any]) -> dict[str, Any]:
    if not fresh.get("checked"):
        return {"status": "unchanged", "reason": fresh.get("reason", "freshness-check-not-run")}
    frozen_set, fresh_set = set(frozen_paths), set(fresh["owners"])
    if not fresh_set or fresh_set == frozen_set:
        return {"status": "unchanged"}
    if fresh_set < frozen_set:
        return {"status": "narrowed", "dropped": sorted(frozen_set - fresh_set)}
    return {"status": "expanded-or-changed", "added": sorted(fresh_set - frozen_set), "fresh_owners": sorted(fresh_set)}


def activate(root: Path, run_id: str, requirement_uid: str, scope_decision: str | None = None) -> dict[str, Any]:
    path = boundary_path(root, run_id); payload = read(path); report = GIT.readiness(root)
    if not report["ready"]: raise ValueError("Git readiness failed: " + "; ".join(report["issues"]))
    if report["branch"] != payload["task_branch"]: raise ValueError("current branch does not match the task recovery boundary")
    if payload["active_requirement_uid"]: raise ValueError("another requirement is already active")
    row = next((row for row in anchor(root, run_id)["requirements"] if row["requirement_uid"] == requirement_uid), None)
    if row is None: raise ValueError("requirement UID is not in the approved anchor")
    paths = sorted(set(relative(item) for item in row["likely_paths"]))
    if not paths: raise ValueError("active requirement has no approved likely paths")
    if not all(any(item == allowed or item.startswith(allowed.rstrip("/") + "/") for allowed in payload["expected_paths"]) for item in paths): raise ValueError("requirement paths are outside the approved task boundary")
    if scope_decision is not None and scope_decision not in {"accept-fresh", "keep-original"}:
        raise ValueError("scope_decision must be 'accept-fresh' or 'keep-original'")
    fresh = _fresh_scope_check(root, run_id, row, payload, paths)
    freshness = _classify_scope_freshness(paths, fresh)
    if freshness["status"] == "expanded-or-changed" and scope_decision is None:
        raise ValueError(
            f"requirement {requirement_uid}'s approved scope may be stale: approved={paths}, "
            f"now evidenced={freshness['fresh_owners']}. This activation is stopped, not silently "
            f"resolved either way -- re-run with --scope-decision accept-fresh to adopt the newly "
            f"evidenced scope for this requirement's boundary tracking, or --scope-decision "
            f"keep-original to proceed with the originally approved scope anyway. Neither the "
            f"approved anchor nor any other requirement's state is touched by this check."
        )
    effective_paths = paths
    anchor_correction: dict[str, Any] | None = None
    if freshness["status"] == "expanded-or-changed" and scope_decision == "accept-fresh":
        effective_paths = sorted(set(freshness["fresh_owners"]))
        # Record the correction in the durable, canonical anchor too -- not
        # just this boundary's own local tracking -- so anything reading the
        # plan of record later (delivery-record.py, a future activation)
        # sees the corrected scope, not the stale original. Skipped only
        # when a prior activation already applied the identical correction
        # (retry-safe): correct() itself rejects a no-op change.
        _, latest = ANCHOR.latest_approved(root, run_id)
        current_row = next((item for item in latest["requirements"] if item["requirement_uid"] == requirement_uid), None)
        already_corrected = current_row is not None and sorted(current_row.get("likely_paths", [])) == effective_paths
        if not already_corrected:
            anchor_correction = ANCHOR.correct(
                root, run_id, requirement_uid, effective_paths,
                f"fresh scope re-check at activation found this requirement's approved scope stale "
                f"(approved={paths}, now evidenced={freshness['fresh_owners']}); "
                f"host accepted the fresh evidence via --scope-decision accept-fresh",
            )
    freshness_record = {**freshness, "frozen_paths": paths, "decision": scope_decision if freshness["status"] == "expanded-or-changed" else None}
    if anchor_correction is not None:
        try:
            freshness_record["anchor_correction_path"] = Path(anchor_correction["path"]).resolve().relative_to(Path(root).resolve()).as_posix()
        except ValueError:
            freshness_record["anchor_correction_path"] = anchor_correction["path"]
    payload["active_requirement_uid"] = requirement_uid
    payload["requirements"].setdefault(requirement_uid, {"expected_paths": effective_paths, "state": "active", "scope_freshness": freshness_record})
    LEDGER.atomic_json(path, payload)
    LEDGER.append_event(root, run_id, "recovery_requirement_activated", {"requirement_uid": requirement_uid, "expected_paths": effective_paths, "scope_freshness": freshness_record})
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
        if name == "activate": item.add_argument("--requirement-uid", required=True); item.add_argument("--scope-decision", choices=["accept-fresh", "keep-original"], default=None)
        if name == "checkpoint": item.add_argument("--requirement-uid", required=True); item.add_argument("--receipt", type=Path, action="append", default=[]); item.add_argument("--approved", action="store_true")
    args = parser.parse_args(); root = args.root.resolve()
    try:
        if args.command == "init": result = init(root, args.run_id, args.expected_path, args.approved)
        elif args.command == "activate": result = activate(root, args.run_id, args.requirement_uid, args.scope_decision)
        elif args.command == "checkpoint": result = checkpoint(root, args.run_id, args.requirement_uid, args.receipt, args.approved)
        else: result = read(boundary_path(root, args.run_id))
        print(json.dumps(result, indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Task recovery boundary error: {error}"); return 2


if __name__ == "__main__": raise SystemExit(main())
