"""Persist and validate DWR-3 completion receipts for collected evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from workflow_runtime import compiler, contracts, ownership, storage


LEDGER = ownership.LEDGER


def _hash(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def receipt(root: Path, workflow_id: str, report: dict[str, Any], accepted_incomplete: bool = False) -> dict[str, Any]:
    from workflow_runtime import evidence
    collected = evidence.collect(root, workflow_id)
    complete = report.get("overall_status") == "complete"
    state = "completed" if complete else "evidence-incomplete-accepted" if accepted_incomplete else "evidence-incomplete"
    report_ref = report.get("run_artifact")
    if not report_ref:
        candidates = sorted((LEDGER.state_dir(root, str(report["run_id"])) / "completion-reports").glob("report-*.json"))
        report_ref = _relative(root, candidates[-1]) if candidates else None
    stable = {"workflow_id": workflow_id, "tailtrail_run_id": report["run_id"], "completion_report": report_ref, "completion_status": report.get("overall_status"), "evidence_fingerprint": collected["evidence_fingerprint"], "state": state}
    payload = {"schema_version": "1", "type": "tailtrail-workflow-completion-receipt", **stable, "receipt_fingerprint": _hash(stable), "boundary": "Completion follows the canonical TailTrail Completion Report. An evidence-incomplete receipt is not a successful workflow completion and does not authorize a retry or recovery."}
    contracts.require_valid(payload)
    path = evidence.receipt_path(root, workflow_id); LEDGER.atomic_json(path, payload)
    storage.capture(root, workflow_id)
    LEDGER.append_event(root, report["run_id"], "workflow_completion_receipt_recorded", {"workflow_id": workflow_id, "artifact": _relative(root, path), "state": state})
    return {"artifact": _relative(root, path), **payload}


def close(root: Path, workflow_id: str, accepted_incomplete: bool = False, approved: bool = False) -> dict[str, Any]:
    from workflow_runtime import evidence
    root = root.resolve(); binding = ownership.show(root, workflow_id); report = evidence.CLOSURE.show(root, binding["tailtrail_run_id"])
    if report.get("overall_status") != "complete" and (not accepted_incomplete or not approved):
        return receipt(root, workflow_id, report, False)
    return receipt(root, workflow_id, report, accepted_incomplete)


def sync_closure(root: Path, run_id: str, report: dict[str, Any]) -> dict[str, Any] | None:
    root = root.resolve(); workflow_id = ownership.suggested_id(run_id)
    if not ownership.binding_path(root, workflow_id).is_file(): return None
    return receipt(root, workflow_id, report, False)


def validate(root: Path, workflow_id: str) -> dict[str, Any]:
    from workflow_runtime import evidence
    issues: list[str] = []
    try:
        current = evidence.show(root, workflow_id); expected = _hash({key: value for key, value in current.items() if key not in {"artifact", "evidence_fingerprint"}})
        if current.get("evidence_fingerprint") != expected: issues.append("workflow evidence fingerprint differs from declared contents")
        issues.extend(contracts.validate_artifact({key: value for key, value in current.items() if key != "artifact"}))
        known = {row["stage_id"] for row in compiler.show(root, workflow_id)["stages"]}
        if {row.get("stage_id") for row in current.get("stages", [])} != known: issues.append("workflow evidence stages do not match compiler plan")
        path = evidence.receipt_path(root, workflow_id)
        if path.is_file():
            value = _read(path); stable = {key: value.get(key) for key in ("workflow_id", "tailtrail_run_id", "completion_report", "completion_status", "evidence_fingerprint", "state")}
            if value.get("receipt_fingerprint") != _hash(stable): issues.append("completion receipt fingerprint differs from declared contents")
            issues.extend(contracts.validate_artifact(value))
    except (OSError, ValueError, json.JSONDecodeError) as error: issues.append(str(error))
    return {"type": "tailtrail-workflow-evidence-validation", "workflow_id": workflow_id, "valid": not issues, "status": "valid" if not issues else "blocked", "issues": issues, "boundary": "Read-only validation. It does not collect, refresh, resume, correct, close, or execute workflow work."}
