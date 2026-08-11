#!/usr/bin/env python3
"""Phase 1: persist validated execution facts as local TailTrail closure evidence.

The recorder never executes the commands in its input. It accepts only the
Phase 0 contract, requires an approved Planning Lock, and writes receipts,
checkpoint, gate, and review artifacts for that same run.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, script: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


L = load("closure_recorder_ledger", "run-ledger.py")
CONTRACT = load("closure_recorder_contract", "closure-contract.py")
LOCK = load("closure_recorder_lock", "planning-lock.py")
CHECKPOINT = load("closure_recorder_checkpoint", "harness-checkpoint.py")
REVIEW = load("closure_recorder_review", "completion-review.py")
GATE = load("closure_recorder_gate", "requirement-completion.py")


def canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def receipt_rows(validated: dict[str, Any], record_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for receipt in validated["receipts"]:
        for uid in receipt["requirement_uids"]:
            rows.append({
                "schema_version": "1", "type": "tailtrail-validation-evidence-receipt",
                "requirement_uid": uid, "tier": receipt["tier"], "command": receipt["command"],
                "command_label": receipt["command_label"], "outcome": receipt["outcome"],
                "environment": receipt["environment"], "asserted_behavior": receipt["asserted_behavior"],
                "artifact_path": receipt.get("artifact", ""), "evidence_label": receipt["evidence_label"],
                "closure_record_id": record_id,
            })
    return rows


def selected_harnesses(root: Path, run_id: str) -> list[str]:
    path = L.state_dir(root, run_id) / "planning" / "execution-handoff-v1.json"
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    closure = payload.get("closure", {}) if isinstance(payload, dict) else {}
    return [str(item) for item in closure.get("selected_harnesses", []) if isinstance(item, str)]


def artifact_pointer(root: Path, path: Path) -> str:
    """Keep local records portable when their input lives beneath the project."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def record(root: Path, input_path: Path) -> dict[str, Any]:
    source = json.loads(input_path.read_text(encoding="utf-8"))
    validated = CONTRACT.validate_input(root, source)
    run_id = validated["run_id"]
    LOCK.assert_write_allowed(root, run_id)
    directory = L.state_dir(root, run_id)
    record_id = "closure-" + hashlib.sha256(canonical(validated).encode("utf-8")).hexdigest()[:16]
    records = directory / "closure-records"
    record_path = records / f"{record_id}.json"
    if record_path.is_file():
        saved = json.loads(record_path.read_text(encoding="utf-8"))
        return {**saved, "reused": True}

    normalized_receipts = receipt_rows(validated, record_id)
    receipts_path = records / f"{record_id}-receipts.json"
    results_path = records / f"{record_id}-results.json"
    L.atomic_json(receipts_path, {"receipts": normalized_receipts})
    L.atomic_json(results_path, {"results": [{
        "requirement_uids": item["requirement_uids"], "command_label": item["command_label"],
        "command": item["command"], "outcome": item["outcome"], "environment": item["environment"],
        "asserted_behavior": item["asserted_behavior"], "evidence_label": item["evidence_label"],
    } for item in validated["receipts"]]})
    receipt_dir = directory / "validation-receipts"
    receipt_artifacts: list[str] = []
    for index, item in enumerate(normalized_receipts, start=1):
        path = receipt_dir / f"{record_id}-{index}.json"
        L.atomic_json(path, item)
        receipt_artifacts.append(path.relative_to(root).as_posix())
    checkpoint = CHECKPOINT.checkpoint(root, run_id, validated["changed_paths"], results_path)
    review = REVIEW.review(root, run_id)
    gate = GATE.gate(root, run_id, receipts_path)
    selected = selected_harnesses(root, run_id)
    outstanding = [name for name in selected if name in {"Architecture Fitness Harness", "Behaviour Harness", "Maintainability Harness"}]
    next_action = ("Run the selected harness assessments: " + ", ".join(outstanding) + "; then run tailtrail completion-report." if outstanding else "Run tailtrail completion-report for this run.")
    payload = {
        "schema_version": "1", "type": "tailtrail-closure-record", "record_id": record_id, "run_id": run_id,
        "validated_input": artifact_pointer(root, input_path), "changed_paths": validated["changed_paths"],
        "receipt_artifacts": receipt_artifacts, "checkpoint": checkpoint["path"], "completion_review": review,
        "completion_gate": gate, "selected_harnesses": selected, "next_action": next_action,
        "boundary": "Recorded supplied validated evidence only. No listed command was executed by TailTrail.",
    }
    L.atomic_json(record_path, payload)
    L.append_event(root, run_id, "closure_recorded", {"record_id": record_id, "artifact": record_path.relative_to(root).as_posix(), "receipt_count": len(normalized_receipts), "checkpoint": checkpoint["checkpoint"], "gate_complete": gate["complete"], "review_complete": review["complete"]})
    return {**payload, "reused": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(record(args.root.resolve(), args.input.resolve()), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Closure recorder error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
