#!/usr/bin/env python3
"""Shared, mode-specific completion policy for one TailTrail run.

Every closure producer and projection (closure record, Completion Report,
closure finalizer) calls `evaluate` so they agree on what a complete run
requires. The policy is derived from the persisted host input contract
`request_mode`:

- implementation: saved changed-path (source-edit) evidence is required in
  addition to passing requirement proof.
- read-only / validation-only: a current, hash-bound `validation-delivery`
  receipt for the produced artifact is required in addition to passing
  requirement proof. A source-edit receipt is not required.
- no persisted contract: legacy behaviour; the policy is `not-applicable`.

The policy never runs commands and never converts missing evidence into a pass.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY_VERSION = "1"
DELIVERY_TYPE = "tailtrail-validation-delivery"
NO_EDIT_MODES = frozenset({"read-only", "validation-only"})
PASSING_STATUSES = frozenset({"pass", "not-applicable"})


def _load(name: str, script: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


L = _load("completion_policy_ledger", "run-ledger.py")
LOCK = _load("completion_policy_lock", "planning_lock.py")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inside(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def request_mode(root: Path, run_id: str) -> str | None:
    """Return the active report's host contract `request_mode`; None only when no contract was saved."""
    root = root.resolve()
    if not (root / str(LOCK.revision_state(root, run_id).get("active_report", ""))).is_file():
        return None
    saved = LOCK.active_start_report(root, run_id)
    payload = saved.get("report")
    if not isinstance(payload, dict):
        raise ValueError("active Start report has no `report` object")
    if "host_input_contract" not in payload:
        return None
    contract = payload["host_input_contract"]
    mode = contract.get("request_mode") if isinstance(contract, dict) else None
    if not isinstance(mode, str) or not mode:
        raise ValueError("active Start report host_input_contract has no request_mode")
    return mode


def delivery_path(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "validation-delivery" / "delivery-v1.json"


def validate_delivery(root: Path, run_id: str) -> dict[str, Any]:
    """Accept a validation-delivery receipt only when it is run-bound and hash-current."""
    root = root.resolve()
    path = delivery_path(root, run_id)
    if not path.is_file():
        return {"status": "missing", "reason": "no validation-delivery receipt is recorded for this run"}
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid", "reason": "validation-delivery receipt is unreadable"}
    if not isinstance(receipt, dict) or receipt.get("type") != DELIVERY_TYPE:
        return {"status": "invalid", "reason": "validation-delivery receipt has the wrong type"}
    if receipt.get("run_id") != run_id:
        return {"status": "invalid", "reason": "validation-delivery receipt belongs to a different run"}
    artifact_type = receipt.get("artifact_type")
    value = receipt.get("artifact_path")
    digest = receipt.get("artifact_sha256")
    if not isinstance(artifact_type, str) or not artifact_type.strip() or not isinstance(value, str) or not value:
        return {"status": "invalid", "reason": "validation-delivery receipt is missing its artifact binding"}
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        return {"status": "invalid", "reason": "validation-delivery artifact path is unsafe"}
    artifact = (root / relative).resolve()
    if not _inside(root, artifact) or not artifact.is_file():
        return {"status": "invalid", "reason": f"validation-delivery artifact `{value}` does not exist"}
    if _sha256(artifact) != digest:
        return {"status": "stale", "reason": f"validation-delivery artifact `{value}` changed after it was recorded"}
    return {"status": "accepted", "artifact_type": artifact_type, "artifact_path": value, "artifact_sha256": digest}


def record_delivery(root: Path, run_id: str, artifact: Path, artifact_type: str) -> dict[str, Any]:
    """Bind a produced no-edit artifact to the run by path and SHA-256."""
    root = root.resolve()
    if not artifact_type.strip():
        raise ValueError("validation-delivery needs a non-empty --artifact-type")
    target = (root / artifact).resolve() if not artifact.is_absolute() else artifact.resolve()
    if not _inside(root, target) or not target.is_file():
        raise ValueError(f"validation-delivery artifact `{artifact}` must be an existing file inside the project root")
    payload = {
        "schema_version": POLICY_VERSION,
        "type": DELIVERY_TYPE,
        "run_id": run_id,
        "artifact_type": artifact_type.strip(),
        "artifact_path": target.relative_to(root).as_posix(),
        "artifact_sha256": _sha256(target),
    }
    path = delivery_path(root, run_id)
    L.atomic_json(path, payload)
    L.append_event(root, run_id, "validation_delivery_recorded", {
        "artifact": path.relative_to(root).as_posix(),
        "artifact_path": payload["artifact_path"],
        "artifact_sha256": payload["artifact_sha256"],
    })
    return {**payload, "receipt": path.relative_to(root).as_posix()}


def evaluate(root: Path, run_id: str, changed_paths: list[str]) -> dict[str, Any]:
    """Return the completion policy state shared by every producer and projection."""
    root = root.resolve()
    required: list[str] = []
    missing: list[dict[str, str]] = []
    recovery = ""
    mode: str | None = None
    contract_error: str | None = None
    try:
        mode = request_mode(root, run_id)
    except (ValueError, OSError) as error:
        contract_error = str(error)
    if contract_error is not None:
        status = "evidence-incomplete"
        missing.append({"artifact": "host-input-contract", "message": contract_error})
        recovery = (
            f"repair the active Start report for run `{run_id}` (inspect with "
            f"`tailtrail planning show --run-id {run_id}`), then rerun closure"
        )
    elif mode is None:
        status = "not-applicable"
    elif mode == "implementation":
        required.append("source-edit-receipt")
        if not changed_paths:
            status = "evidence-incomplete"
            missing.append({
                "artifact": "source-edit-receipt",
                "message": "implementation request has no saved changed-path evidence",
            })
            recovery = f"record the approved source edits with `tailtrail closure record --root . --run-id {run_id}` after the changes are made"
        else:
            status = "pass"
    elif mode in NO_EDIT_MODES:
        required.append("validation-delivery")
        delivery = validate_delivery(root, run_id)
        if delivery["status"] == "accepted":
            status = "pass"
        else:
            status = "evidence-incomplete"
            missing.append({"artifact": "validation-delivery", "message": delivery["reason"]})
            recovery = (
                "produce the declared validation artifact, then record it with "
                f"`python3 scripts/completion-policy.py record-delivery --root . --run-id {run_id} "
                "--artifact <path> --artifact-type <type>`"
            )
    else:
        status = "evidence-incomplete"
        missing.append({"artifact": "known-request-mode", "message": f"unknown request_mode `{mode}`"})
    return {
        "schema_version": POLICY_VERSION,
        "type": "tailtrail-completion-policy",
        "run_id": run_id,
        "request_mode": mode,
        "status": status,
        "required_artifacts": required,
        "missing": missing,
        "recovery": recovery,
        "source_edit_required": mode == "implementation",
        "implementation_applicable": mode not in NO_EDIT_MODES,
        "boundary": "Policy derived from the persisted host contract. Missing or stale artifacts are never reported as complete.",
    }


def passes(policy: dict[str, Any]) -> bool:
    return policy.get("status") in PASSING_STATUSES


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    show = sub.add_parser("show", help="print the completion policy for a run")
    show.add_argument("--root", type=Path, default=Path.cwd())
    show.add_argument("--run-id", required=True)
    rec = sub.add_parser("record-delivery", help="record a validation-delivery receipt")
    rec.add_argument("--root", type=Path, default=Path.cwd())
    rec.add_argument("--run-id", required=True)
    rec.add_argument("--artifact", type=Path, required=True)
    rec.add_argument("--artifact-type", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "show":
        print(json.dumps(evaluate(root, args.run_id, []), indent=2, sort_keys=True))
    else:
        print(json.dumps(record_delivery(root, args.run_id, args.artifact, args.artifact_type), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
