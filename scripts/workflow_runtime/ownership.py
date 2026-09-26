"""DWR-A canonical workflow-to-run ownership binding.

The binding is metadata only. It references, rather than copies, TailTrail's
Planning Lock and approved anchor so later workflow phases have no second
source of truth for task identity or requirements.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ID = re.compile(r"^ttw-[a-z0-9][a-z0-9-]{3,80}$")


def _module(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    loaded = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(loaded)
    return loaded


LEDGER = _module("workflow_ownership_ledger", "run-ledger.py")
LOCK = _module("workflow_ownership_lock", "planning_lock.py")
TARGET = _module("workflow_ownership_target", "target_workspace.py")


def _workflow_dir(root: Path, workflow_id: str) -> Path:
    if not WORKFLOW_ID.fullmatch(workflow_id):
        raise ValueError("workflow-id must match ttw- followed by lowercase letters, digits, or hyphens")
    return root.resolve() / ".tailtrail" / "workflows" / workflow_id


def _path_ref(root: Path, path: Path, pointer: str = "") -> str:
    return path.resolve().relative_to(root.resolve()).as_posix() + pointer


def _resolve_ref(root: Path, value: str) -> tuple[Path, str]:
    raw_path, separator, pointer = value.partition("#")
    candidate = Path(raw_path)
    if not raw_path or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("canonical reference must be a safe repository-relative path")
    resolved = (root.resolve() / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("canonical reference escapes repository root") from error
    if not resolved.is_file():
        raise ValueError(f"canonical reference is missing: {raw_path}")
    return resolved, f"#{pointer}" if separator else ""


def _read_ref(root: Path, value: str) -> Any:
    path, pointer = _resolve_ref(root, value)
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    if pointer:
        for token in pointer.removeprefix("#/").split("/"):
            if not isinstance(payload, dict) or token not in payload:
                raise ValueError(f"canonical JSON pointer cannot be resolved: {value}")
            payload = payload[token]
    return payload


def suggested_id(run_id: str) -> str:
    return "ttw-" + hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:12]


def binding_path(root: Path, workflow_id: str) -> Path:
    return _workflow_dir(root, workflow_id) / "ownership-v1.json"


def _canonical_refs(root: Path, run_id: str) -> tuple[dict[str, Any], dict[str, str]]:
    lock = LOCK.show(root, run_id)
    if lock.get("status") != "approved" or lock.get("writes_allowed") is not True:
        raise ValueError(f"DWR-A requires an approved Planning Lock for run `{run_id}`")
    identity = TARGET.verify_identity(lock.get("target_identity", {}), root)
    if identity.get("blocking"):
        raise ValueError(f"DWR-A target identity mismatch: {identity.get('reason', 'unknown mismatch')}")
    anchor_path = LEDGER.state_dir(root, run_id) / "anchors" / "approved-v1.json"
    if not anchor_path.is_file():
        raise ValueError(f"DWR-A requires the immutable approved anchor for run `{run_id}`")
    anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    rows = anchor.get("requirements")
    if anchor.get("run_id") != run_id or anchor.get("status") != "approved" or not isinstance(rows, list) or not rows:
        raise ValueError("approved anchor is invalid or has no canonical requirements")
    if any(not isinstance(row, dict) or not str(row.get("requirement_uid", "")).strip() for row in rows):
        raise ValueError("approved anchor requirements must each have a requirement_uid")
    lock_path = LEDGER.state_dir(root, run_id) / "planning" / "lock-v1.json"
    refs = {
        "planning_lock_ref": _path_ref(root, lock_path),
        "approved_anchor_ref": _path_ref(root, anchor_path),
        "requirement_matrix_ref": _path_ref(root, anchor_path, "#/requirements"),
    }
    return {"lock": lock, "anchor": anchor, "identity": identity}, refs


def bind(root: Path, run_id: str, workflow_id: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    workflow_id = workflow_id or suggested_id(run_id)
    destination = binding_path(root, workflow_id)
    if destination.exists():
        raise ValueError(f"workflow ownership binding already exists: {workflow_id}")
    values, refs = _canonical_refs(root, run_id)
    payload = {
        "schema_version": "1",
        "type": "tailtrail-workflow-ownership-binding",
        "workflow_id": workflow_id,
        "tailtrail_run_id": run_id,
        **refs,
        "target_identity_fingerprint": values["lock"]["target_identity"].get("fingerprint"),
        "approved_anchor_fingerprint": values["anchor"].get("approved_fingerprint"),
        "requirement_uids": [row["requirement_uid"] for row in values["anchor"]["requirements"]],
        "rebases": [],
        "state": "bound",
        "boundary": "DWR-A metadata only. This binding grants no execution, approval, resume, recovery, or completion authority.",
    }
    LEDGER.atomic_json(destination, payload)
    LEDGER.append_event(root, run_id, "workflow_ownership_bound", {"workflow_id": workflow_id, "artifact": destination.relative_to(root).as_posix(), "requirement_uids": payload["requirement_uids"]})
    return {"artifact": destination.relative_to(root).as_posix(), **payload}


def show(root: Path, workflow_id: str) -> dict[str, Any]:
    path = binding_path(root.resolve(), workflow_id)
    if not path.is_file():
        raise ValueError(f"workflow ownership binding does not exist: {workflow_id}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "tailtrail-workflow-ownership-binding" or payload.get("workflow_id") != workflow_id:
        raise ValueError("workflow ownership binding is invalid")
    return {"artifact": path.relative_to(root.resolve()).as_posix(), **payload}


def validate(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); binding = show(root, workflow_id); issues: list[str] = []; notices: list[str] = []
    run_id = str(binding.get("tailtrail_run_id", "")); identity: dict[str, Any] = {}
    try:
        lock = _read_ref(root, str(binding.get("planning_lock_ref", "")))
        anchor = _read_ref(root, str(binding.get("approved_anchor_ref", "")))
        rows = _read_ref(root, str(binding.get("requirement_matrix_ref", "")))
        if not isinstance(lock, dict) or lock.get("run_id") != run_id or lock.get("status") != "approved": issues.append("Planning Lock reference is not the approved bound run")
        if not isinstance(anchor, dict) or anchor.get("run_id") != run_id or anchor.get("status") != "approved": issues.append("approved anchor reference is not the bound approved anchor")
        if not isinstance(rows, list) or [row.get("requirement_uid") for row in rows if isinstance(row, dict)] != binding.get("requirement_uids"): issues.append("requirement matrix reference no longer matches bound requirement IDs")
        identity = TARGET.verify_identity(lock.get("target_identity", {}) if isinstance(lock, dict) else {}, root)
        if identity.get("blocking"): issues.append("target identity no longer matches the bound Planning Lock")
        if isinstance(anchor, dict) and binding.get("approved_anchor_fingerprint") != anchor.get("approved_fingerprint"): issues.append("approved anchor fingerprint differs from binding")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        issues.append(str(error))
    drift = identity.get("inventory_drift") if isinstance(identity.get("inventory_drift"), dict) else None
    if not issues and identity.get("status") == "inventory-drift" and drift is not None and not drift.get("in_sync", True):
        notices.append(f"target inventory drifted from the Planning Lock ({drift.get('change_count', 0)} change(s)); informational — run `rebind` to record explicit acceptance")
    return {"type": "tailtrail-workflow-ownership-validation", "workflow_id": workflow_id, "tailtrail_run_id": run_id, "valid": not issues, "status": "valid" if not issues else "blocked", "issues": issues, "notices": notices, "inventory_drift": drift, "boundary": "Validation is read-only and does not resume, execute, recover, rebind, or complete work."}


def _drift_changes(drift: dict[str, Any]) -> list[dict[str, str]]:
    """Flatten an inventory-drift report into named per-path changes."""
    changes = [{"path": path, "change": "added", "before": "absent", "after": "present"} for path in drift.get("added", [])]
    changes += [{"path": path, "change": "removed", "before": "present", "after": "absent"} for path in drift.get("removed", [])]
    changes += [{"path": str(row.get("path", "?")), "change": "changed", "before": str(row.get("before", "?")), "after": str(row.get("after", "?"))} for row in drift.get("changed", []) if isinstance(row, dict)]
    manifests = drift.get("manifests", {}) if isinstance(drift.get("manifests"), dict) else {}
    if manifests.get("before") != manifests.get("after"):
        changes.append({"path": "<project-manifests>", "change": "changed", "before": ",".join(manifests.get("before", [])), "after": ",".join(manifests.get("after", []))})
    languages = drift.get("languages", {}) if isinstance(drift.get("languages"), dict) else {}
    if languages.get("before") != languages.get("after"):
        changes.append({"path": "<project-languages>", "change": "changed", "before": ",".join(languages.get("before", [])), "after": ",".join(languages.get("after", []))})
    return sorted(changes, key=lambda row: row["path"])


def rebind(root: Path, workflow_id: str, confirmed: bool = False) -> dict[str, Any]:
    """Report target drift and, on explicit confirmation, record acceptance.

    Without confirmation this only reports the delta against the bound
    Planning Lock. With confirmation it appends the current workspace
    identity as an accepted rebase baseline and expires session approvals,
    so continuation re-approves against current state. The Planning Lock
    itself is never mutated: acceptance lives in the binding's rebase log.
    """
    root = root.resolve(); binding = show(root, workflow_id)
    lock = _read_ref(root, str(binding.get("planning_lock_ref", "")))
    verdict = TARGET.verify_identity(lock.get("target_identity", {}) if isinstance(lock, dict) else {}, root)
    if verdict.get("blocking"):
        raise ValueError(f"DWR-A target identity mismatch: {verdict.get('reason', 'unknown mismatch')}; rebind cannot accept a different workspace")
    drift = verdict.get("inventory_drift") if isinstance(verdict.get("inventory_drift"), dict) else {}
    changed = _drift_changes(drift)
    if not changed:
        return {"type": "tailtrail-workflow-ownership-rebind", "workflow_id": workflow_id, "state": "in-sync", "changed": changed,
                "boundary": "Rebind is read-only while in sync; nothing was recorded and no approvals were expired."}
    if not confirmed:
        return {"type": "tailtrail-workflow-ownership-rebind", "workflow_id": workflow_id, "state": "rebind-required", "changed": changed,
                "boundary": "Unconfirmed rebind reports the delta only. Nothing was recorded, no approvals were expired. Confirm explicitly to record acceptance."}
    baseline = TARGET.identity(root)
    rebases = list(binding.get("rebases", [])) if isinstance(binding.get("rebases"), list) else []
    rebases.append({"baseline": baseline, "accepted_drift": changed, "prior_rebase_count": len(rebases)})
    destination = binding_path(root, workflow_id)
    payload = json.loads(destination.read_text(encoding="utf-8"))
    payload["rebases"] = rebases
    LEDGER.atomic_json(destination, payload)
    from workflow_runtime import approvals
    approvals.expire_session(root, workflow_id, None, "target-identity-changed")
    LEDGER.append_event(root, str(binding.get("tailtrail_run_id", "")), "workflow_ownership_rebased", {"workflow_id": workflow_id, "artifact": destination.relative_to(root).as_posix(), "rebase_count": len(rebases), "accepted_changes": len(changed)})
    return {"type": "tailtrail-workflow-ownership-rebind", "workflow_id": workflow_id, "state": "rebased", "changed": changed, "rebase_count": len(rebases),
            "boundary": "Acceptance recorded at current state; session approvals expired and must be re-granted."}


def rebind_covers(root: Path, workflow_id: str) -> bool:
    """Check whether the latest recorded rebind baseline matches live state.

    Used by approval freshness checks: drift accepted explicitly via rebind
    does not stale approvals granted after that acceptance. Legacy bindings
    without a rebase log are never covered.
    """
    try:
        binding = show(root.resolve(), workflow_id)
        rebases = binding.get("rebases", [])
        baseline = rebases[-1].get("baseline") if isinstance(rebases, list) and rebases and isinstance(rebases[-1], dict) else None
        if not isinstance(baseline, dict):
            return False
        return bool(TARGET.inventory_drift(baseline, TARGET.identity(root.resolve())).get("in_sync", False))
    except (OSError, ValueError):
        return False
