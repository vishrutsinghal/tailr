#!/usr/bin/env python3
"""Coordinate multiple owner-scoped Planning Locks under one approval.

The coordinated plan is a custody and authorization layer.  It never invents
child scope: every child must already be an audit-clean TailTrail Start plan
with exactly one implementation owner.  One batch approval activates every
exact child fingerprint, but member writes remain blocked until the batch
commit exists and that child's dependencies are complete.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLAN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PL = _load("tailtrail_coordinated_planning_lock", "planning_lock.py")
REVISION = _load("tailtrail_coordinated_planning_revision", "planning-revision.py")
L = PL.L


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"artifact `{path}` must contain a JSON object")
    return payload


def _directory(root: Path, plan_id: str) -> Path:
    if not PLAN_ID.fullmatch(str(plan_id)):
        raise ValueError("plan_id must use only letters, numbers, dot, underscore, or hyphen")
    return root / ".tailtrail" / "coordinated-plans" / plan_id


def _state_path(root: Path, plan_id: str) -> Path:
    return _directory(root, plan_id) / "state.json"


def _proposal_path(root: Path, plan_id: str) -> Path:
    return _directory(root, plan_id) / "proposal.json"


def _membership_path(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "planning" / "coordinated-membership-v1.json"


def _require_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} is required")
    return text


def _require_string_list(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        suffix = " and cannot be empty" if not allow_empty else ""
        raise ValueError(f"{label} must be a list of strings{suffix}")
    result = [_require_text(item, label) for item in value]
    if len(result) != len(set(result)):
        raise ValueError(f"{label} contains duplicates")
    return result


def _validate_graph(children: list[dict[str, Any]]) -> list[str]:
    run_ids = [_require_text(item.get("run_id"), "child run_id") for item in children]
    if len(run_ids) != len(set(run_ids)):
        raise ValueError("child run IDs must be unique")
    known = set(run_ids)
    remaining: dict[str, set[str]] = {}
    for item in children:
        run_id = str(item["run_id"])
        dependencies = set(_require_string_list(item.get("depends_on", []), f"dependencies for `{run_id}`"))
        if run_id in dependencies:
            raise ValueError(f"child `{run_id}` cannot depend on itself")
        unknown = sorted(dependencies - known)
        if unknown:
            raise ValueError(f"child `{run_id}` has unknown dependencies: {', '.join(unknown)}")
        remaining[run_id] = dependencies
    ordered: list[str] = []
    while remaining:
        ready = sorted(run_id for run_id, dependencies in remaining.items() if not dependencies)
        if not ready:
            raise ValueError("child dependency graph contains a cycle")
        ordered.extend(ready)
        for run_id in ready:
            remaining.pop(run_id)
        for dependencies in remaining.values():
            dependencies.difference_update(ready)
    return ordered


def _owners(report: dict[str, Any]) -> list[str]:
    rows = (report.get("navigator", {}) or {}).get("requirement_matrix", [])
    owners: set[str] = set()
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        scope = row.get("scope_evidence", {})
        if not isinstance(scope, dict):
            continue
        for value in scope.get("implementation_owners", []):
            if isinstance(value, str) and value.strip():
                owners.add(value.strip())
            elif isinstance(value, dict) and str(value.get("path", "")).strip():
                owners.add(str(value["path"]).strip())
    return sorted(owners)


def _has_proof(report: dict[str, Any]) -> bool:
    rows = (report.get("navigator", {}) or {}).get("requirement_matrix", [])
    for row in rows if isinstance(rows, list) else []:
        contract = row.get("validation_contract", {}) if isinstance(row, dict) else {}
        if not isinstance(contract, dict):
            continue
        if contract.get("checks") or contract.get("commands"):
            return True
    return False


def _child_snapshot(root: Path, run_id: str) -> dict[str, Any]:
    lock = PL.show(root, run_id)
    if lock.get("status") not in {"awaiting-approval", "approved"}:
        raise ValueError(
            f"child `{run_id}` is `{lock.get('status')}`; coordinated approval requires an awaiting-approval or already-approved plan"
        )
    revision = PL.revision_state(root, run_id)
    pending_revision = revision.get("pending_revision")
    report, _source = PL.canonical_plan_report(root, run_id, include_pending=pending_revision is not None)
    PL.require_clean_audit(root, run_id, report)
    owners = _owners(report)
    if len(owners) != 1:
        raise ValueError(
            f"child `{run_id}` must have exactly one implementation owner; found {owners or 'none'}"
        )
    if not _has_proof(report):
        raise ValueError(f"child `{run_id}` has no runnable requirement proof binding")
    selected_revision = int(pending_revision or revision.get("active_revision", 1))
    material = {
        "run_id": run_id,
        "revision": selected_revision,
        "report": report,
    }
    return {
        "run_id": run_id,
        "plan_fingerprint": _fingerprint(material),
        "owner": owners[0],
        "revision": selected_revision,
        "pending_revision": int(pending_revision) if pending_revision is not None else None,
    }


def _validate_shared_proof(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("shared_proof must contain at least one final integration proof binding")
    result: list[dict[str, Any]] = []
    for index, row in enumerate(value, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"shared_proof row {index} must be an object")
        tiers = _require_string_list(row.get("tiers"), f"shared_proof row {index} tiers", allow_empty=False)
        result.append({
            "command": _require_text(row.get("command"), f"shared_proof row {index} command"),
            "tiers": tiers,
            "asserted_behavior": _require_text(
                row.get("asserted_behavior"), f"shared_proof row {index} asserted_behavior"
            ),
        })
    return result


def create(root: Path, plan_file: Path) -> dict[str, Any]:
    root = root.resolve()
    supplied = _read(plan_file)
    plan_id = _require_text(supplied.get("plan_id"), "plan_id")
    if not PLAN_ID.fullmatch(plan_id):
        raise ValueError("plan_id must use only letters, numbers, dot, underscore, or hyphen")
    destination = _directory(root, plan_id)
    if destination.exists():
        raise ValueError(f"coordinated plan `{plan_id}` already exists")
    children_input = supplied.get("children")
    if not isinstance(children_input, list) or len(children_input) < 2:
        raise ValueError("a coordinated plan requires at least two child plans")
    ordered = _validate_graph(children_input)
    snapshots = {item["run_id"]: _child_snapshot(root, str(item["run_id"])) for item in children_input}
    children: list[dict[str, Any]] = []
    for item in children_input:
        run_id = str(item["run_id"])
        owner = _require_text(item.get("owner"), f"owner for `{run_id}`")
        if snapshots[run_id]["owner"] != owner:
            raise ValueError(
                f"child `{run_id}` owner `{owner}` does not match its canonical plan owner `{snapshots[run_id]['owner']}`"
            )
        children.append({
            **snapshots[run_id],
            "owner": owner,
            "requirements": _require_string_list(
                item.get("requirements"), f"requirements for `{run_id}`", allow_empty=False
            ),
            "depends_on": _require_string_list(item.get("depends_on", []), f"dependencies for `{run_id}`"),
        })
    proposal = {
        "schema_version": "1",
        "type": "tailtrail-coordinated-plan",
        "plan_id": plan_id,
        "outcome": _require_text(supplied.get("outcome"), "outcome"),
        "children": children,
        "dependency_order": ordered,
        "shared_proof": _validate_shared_proof(supplied.get("shared_proof")),
        "success_criteria": _require_string_list(
            supplied.get("success_criteria"), "success_criteria", allow_empty=False
        ),
        "created_at": _now(),
    }
    proposal["fingerprint"] = _fingerprint(proposal)
    state = {
        "schema_version": "1",
        "type": "tailtrail-coordinated-plan-state",
        "plan_id": plan_id,
        "coordination_fingerprint": proposal["fingerprint"],
        "status": "awaiting-approval",
        "children": [
            {
                "run_id": child["run_id"],
                "owner": child["owner"],
                "plan_fingerprint": child["plan_fingerprint"],
                "revision": child["revision"],
                "pending_revision": child["pending_revision"],
                "depends_on": child["depends_on"],
                "state": "pending",
                "evidence": None,
            }
            for child in children
        ],
        "approval_receipt": None,
        "updated_at": _now(),
    }
    for child in children:
        membership = _membership_path(root, child["run_id"])
        if membership.exists():
            existing = _read(membership)
            if existing.get("plan_id") != plan_id:
                raise ValueError(
                    f"child `{child['run_id']}` already belongs to coordinated plan `{existing.get('plan_id')}`"
                )
    destination.mkdir(parents=True, exist_ok=False)
    L.atomic_json(_proposal_path(root, plan_id), proposal)
    L.atomic_json(_state_path(root, plan_id), state)
    for child in children:
        membership = _membership_path(root, child["run_id"])
        L.atomic_json(membership, {
            "schema_version": "1",
            "type": "tailtrail-coordinated-plan-membership",
            "plan_id": plan_id,
            "coordination_fingerprint": proposal["fingerprint"],
            "child_run_id": child["run_id"],
            "child_plan_fingerprint": child["plan_fingerprint"],
            "depends_on": child["depends_on"],
        })
    return {"proposal": proposal, "state": state}


def _load_plan(root: Path, plan_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    proposal = _read(_proposal_path(root, plan_id))
    state = _read(_state_path(root, plan_id))
    if proposal.get("fingerprint") != state.get("coordination_fingerprint"):
        raise ValueError("coordinated plan state does not match its immutable proposal")
    return proposal, state


def _freshness(root: Path, proposal: dict[str, Any]) -> dict[str, Any]:
    stale: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for child in proposal["children"]:
        run_id = child["run_id"]
        try:
            fingerprint = _child_snapshot(root, run_id)["plan_fingerprint"]
            current[run_id] = fingerprint
            if fingerprint != child["plan_fingerprint"]:
                stale.append({
                    "run_id": run_id,
                    "reason": "canonical child plan changed",
                    "expected": child["plan_fingerprint"],
                    "actual": fingerprint,
                })
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
            stale.append({"run_id": run_id, "reason": str(error), "expected": child["plan_fingerprint"], "actual": "unavailable"})
    return {"fresh": not stale, "stale_children": stale, "current_fingerprints": current}


def _approve_unlocked(root: Path, plan_id: str, approved: bool) -> dict[str, Any]:
    if approved is not True:
        raise ValueError("coordinated-plan approval requires --approved")
    root = root.resolve()
    proposal, state = _load_plan(root, plan_id)
    freshness = _freshness(root, proposal)
    if not freshness["fresh"]:
        raise ValueError("batch approval is blocked because one or more child plans changed: " + json.dumps(freshness["stale_children"], sort_keys=True))
    receipt_path = _directory(root, plan_id) / "batch-approval-v1.json"
    if state.get("status") == "activated" and receipt_path.is_file():
        return {"proposal": proposal, "state": state, "approval_receipt": _read(receipt_path), "freshness": freshness}
    if state.get("status") not in {"awaiting-approval", "activation-failed", "activating"}:
        raise ValueError(f"coordinated plan `{plan_id}` cannot be approved from status `{state.get('status')}`")
    state["status"] = "activating"
    state["last_error"] = None
    state["updated_at"] = _now()
    L.atomic_json(_state_path(root, plan_id), state)
    activated: list[str] = list(state.get("activated_pending_batch_commit", []))
    try:
        for run_id in proposal["dependency_order"]:
            if run_id in activated:
                continue
            child = next(item for item in proposal["children"] if item["run_id"] == run_id)
            pending_revision = child.get("pending_revision")
            if pending_revision is not None:
                REVISION.approve(root, run_id, int(pending_revision), True)
            else:
                PL.activate(root, run_id, True, rationale=f"atomic coordinated-plan approval `{plan_id}`")
            activated.append(run_id)
    except Exception as error:
        state["status"] = "activation-failed"
        state["activated_pending_batch_commit"] = activated
        state["last_error"] = str(error)
        state["updated_at"] = _now()
        L.atomic_json(_state_path(root, plan_id), state)
        raise ValueError(
            "coordinated activation failed before the batch commit; every member remains write-blocked. "
            f"Activated child locks retained for safe retry: {activated}. Cause: {error}"
        ) from error
    receipt = {
        "schema_version": "1",
        "type": "tailtrail-coordinated-plan-batch-approval",
        "plan_id": plan_id,
        "coordination_fingerprint": proposal["fingerprint"],
        "approved": True,
        "children": [
            {
                "run_id": child["run_id"],
                "plan_fingerprint": child["plan_fingerprint"],
                "owner": child["owner"],
                "revision": child["revision"],
                "depends_on": child["depends_on"],
            }
            for child in proposal["children"]
        ],
        "approved_at": _now(),
        "boundary": "One approval authorizes this exact child set; writes remain dependency-gated and any child-plan drift invalidates execution.",
    }
    receipt["fingerprint"] = _fingerprint(receipt)
    L.atomic_json(receipt_path, receipt)
    completed: set[str] = set()
    for child in state["children"]:
        child["state"] = "ready" if set(child["depends_on"]) <= completed else "blocked"
    state["status"] = "activated"
    state["approval_receipt"] = receipt_path.relative_to(root).as_posix()
    state["activated_pending_batch_commit"] = []
    state["updated_at"] = _now()
    L.atomic_json(_state_path(root, plan_id), state)
    return {"proposal": proposal, "state": state, "approval_receipt": receipt, "freshness": freshness}


def approve(root: Path, plan_id: str, approved: bool) -> dict[str, Any]:
    root = root.resolve()
    with L.RunLock(_directory(root, plan_id) / ".lock"):
        return _approve_unlocked(root, plan_id, approved)


def _refresh_ready_states(state: dict[str, Any]) -> None:
    completed = {child["run_id"] for child in state["children"] if child["state"] == "completed"}
    for child in state["children"]:
        if child["state"] == "blocked" and set(child["depends_on"]) <= completed:
            child["state"] = "ready"


def _checkpoint_unlocked(root: Path, plan_id: str, run_id: str, child_state: str, evidence: Path | None) -> dict[str, Any]:
    root = root.resolve()
    proposal, state = _load_plan(root, plan_id)
    freshness = _freshness(root, proposal)
    if state.get("status") != "activated" or not freshness["fresh"]:
        raise ValueError("checkpoint is blocked until the exact coordinated plan is activated and fresh")
    child = next((item for item in state["children"] if item["run_id"] == run_id), None)
    if child is None:
        raise ValueError(f"run `{run_id}` is not a child of coordinated plan `{plan_id}`")
    if child_state == "active":
        if child["state"] != "ready":
            raise ValueError(f"child `{run_id}` is `{child['state']}`; only dependency-ready children may become active")
        child["state"] = "active"
    elif child_state == "completed":
        if child["state"] != "active":
            raise ValueError(f"child `{run_id}` is `{child['state']}`; record active before completed")
        if evidence is None:
            raise ValueError("completed checkpoint requires --evidence")
        evidence_path = evidence if evidence.is_absolute() else root / evidence
        evidence_path = evidence_path.resolve()
        try:
            evidence_path.relative_to(root)
        except ValueError as error:
            raise ValueError("checkpoint evidence must be inside the target repository") from error
        if not evidence_path.is_file():
            raise ValueError(f"checkpoint evidence `{evidence_path}` does not exist")
        try:
            evidence_payload = _read(evidence_path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise ValueError("completed checkpoint evidence must be a canonical TailTrail closure-finalizer JSON artifact") from error
        if (
            evidence_payload.get("type") != "tailtrail-closure-finalizer"
            or evidence_payload.get("run_id") != run_id
            or evidence_payload.get("overall_status") != "complete"
        ):
            raise ValueError(
                "completed checkpoint evidence must be a successful TailTrail closure-finalizer for the exact child run"
            )
        child["state"] = "completed"
        child["evidence"] = {
            "path": evidence_path.relative_to(root).as_posix(),
            "fingerprint": "sha256:" + hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
        }
        _refresh_ready_states(state)
    else:
        raise ValueError("checkpoint state must be `active` or `completed`")
    state["updated_at"] = _now()
    L.atomic_json(_state_path(root, plan_id), state)
    return {"proposal": proposal, "state": state, "freshness": freshness}


def checkpoint(root: Path, plan_id: str, run_id: str, child_state: str, evidence: Path | None) -> dict[str, Any]:
    root = root.resolve()
    with L.RunLock(_directory(root, plan_id) / ".lock"):
        return _checkpoint_unlocked(root, plan_id, run_id, child_state, evidence)


def show(root: Path, plan_id: str) -> dict[str, Any]:
    root = root.resolve()
    proposal, state = _load_plan(root, plan_id)
    freshness = _freshness(root, proposal)
    approval_effective = state.get("status") == "activated" and freshness["fresh"]
    ready = [child["run_id"] for child in state["children"] if child["state"] == "ready"] if approval_effective else []
    blockers = []
    if state.get("status") != "activated":
        blockers.append(f"batch status is `{state.get('status')}`")
    blockers.extend(f"{item['run_id']}: {item['reason']}" for item in freshness["stale_children"])
    return {
        "schema_version": "1",
        "type": "tailtrail-coordinated-plan-status",
        "plan_id": plan_id,
        "outcome": proposal["outcome"],
        "coordination_fingerprint": proposal["fingerprint"],
        "status": state.get("status"),
        "approval_effective": approval_effective,
        "children": state["children"],
        "dependency_order": proposal["dependency_order"],
        "shared_proof": proposal["shared_proof"],
        "ready_children": ready,
        "blockers": blockers,
        "freshness": freshness,
    }


def render_status(payload: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Coordinated Plan",
        "",
        f"**Plan ID:** `{payload['plan_id']}`",
        f"**Status:** `{payload['status']}`",
        f"**Atomic approval effective:** `{'yes' if payload['approval_effective'] else 'no'}`",
        "",
        "## Overall outcome",
        "",
        payload["outcome"],
        "",
        "## Child plans and dependencies",
        "",
        "| Run | Owner | Depends on | State |",
        "| --- | --- | --- | --- |",
    ]
    for child in payload["children"]:
        depends = ", ".join(f"`{item}`" for item in child["depends_on"]) or "None"
        lines.append(f"| `{child['run_id']}` | `{child['owner']}` | {depends} | `{child['state']}` |")
    lines.extend(["", "## Dependency order", "", " → ".join(f"`{item}`" for item in payload["dependency_order"]), ""])
    if payload["ready_children"]:
        lines.extend(["## Ready for execution", "", *[f"- `{item}`" for item in payload["ready_children"]], ""])
    if payload["blockers"]:
        lines.extend(["## Blockers", "", *[f"- {item}" for item in payload["blockers"]], ""])
    lines.extend(["## Shared final proof", ""])
    for proof in payload["shared_proof"]:
        lines.append(f"- `{proof['command']}` ({', '.join(proof['tiers'])}) — {proof['asserted_behavior']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    create_parser = sub.add_parser("create")
    create_parser.add_argument("--root", type=Path, default=Path.cwd())
    create_parser.add_argument("--plan", type=Path, required=True)
    for name in ("show", "approve"):
        item = sub.add_parser(name)
        item.add_argument("--root", type=Path, default=Path.cwd())
        item.add_argument("--plan-id", required=True)
        item.add_argument("--format", choices=("markdown", "json"), default="markdown")
        if name == "approve":
            item.add_argument("--approved", action="store_true")
    checkpoint_parser = sub.add_parser("checkpoint")
    checkpoint_parser.add_argument("--root", type=Path, default=Path.cwd())
    checkpoint_parser.add_argument("--plan-id", required=True)
    checkpoint_parser.add_argument("--run-id", required=True)
    checkpoint_parser.add_argument("--state", choices=("active", "completed"), required=True)
    checkpoint_parser.add_argument("--evidence", type=Path)
    checkpoint_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    try:
        if args.action == "create":
            result = create(args.root, args.plan)
            payload = show(args.root.resolve(), result["proposal"]["plan_id"])
        elif args.action == "approve":
            approve(args.root, args.plan_id, args.approved)
            payload = show(args.root.resolve(), args.plan_id)
        elif args.action == "checkpoint":
            checkpoint(args.root, args.plan_id, args.run_id, args.state, args.evidence)
            payload = show(args.root.resolve(), args.plan_id)
        else:
            payload = show(args.root.resolve(), args.plan_id)
        if getattr(args, "format", "markdown") == "json":
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(render_status(payload))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Coordinated plan error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
