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
EVIDENCE = load("closure_recorder_evidence", "execution-evidence.py")


def canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def receipt_rows(validated: dict[str, Any], record_id: str) -> list[dict[str, Any]]:
    return [{
        "schema_version": "2", "type": "tailtrail-validation-evidence-receipt",
        "requirement_uids": receipt["requirement_uids"],
        "tiers": receipt.get("tiers", [receipt["tier"]]),
        "scenario_ids": receipt.get("scenario_ids", []),
        "tier": receipt["tier"], "command": receipt["command"],
        "command_label": receipt["command_label"], "outcome": receipt["outcome"],
        "environment": receipt["environment"], "asserted_behavior": receipt["asserted_behavior"],
        "artifact_path": receipt.get("artifact", ""), "evidence_label": receipt["evidence_label"],
        "evidence_quality": receipt.get("evidence_quality", "declared"),
        **{key: receipt[key] for key in (
            "collector", "exit_code", "started_at", "finished_at", "duration_ms",
            "stdout_artifact", "stderr_artifact", "stdout_sha256", "stderr_sha256",
        ) if key in receipt},
        "closure_record_id": record_id,
    } for receipt in validated["receipts"]]


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


def collected_input(root: Path, run_id: str) -> dict[str, Any]:
    """Build one current closure snapshot from saved factual evidence.

    A later execution of the same approved requirement/command replaces its
    earlier attempt for completion judgment, including when the later run
    records a more complete tier set. The append-only stream still retains
    every attempt for audit and diagnosis.
    """
    saved = EVIDENCE.show(root, run_id)["events"]
    anchor_path = L.state_dir(root, run_id) / "anchors" / "approved-v1.json"
    anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    requirements = {
        str(row.get("requirement_uid")): row
        for row in anchor.get("requirements", [])
        if isinstance(row, dict) and row.get("requirement_uid")
    }
    receipt_fields = (
        "requirement_uids", "tier", "tiers", "scenario_ids", "command_label", "command",
        "outcome", "environment", "asserted_behavior", "artifact", "evidence_label",
        "collector", "evidence_quality", "exit_code", "started_at", "finished_at",
        "duration_ms", "stdout_artifact", "stderr_artifact", "stdout_sha256", "stderr_sha256",
    )
    current: dict[tuple[tuple[str, ...], str], dict[str, Any]] = {}
    for item in saved:
        if item.get("kind") not in {"command-result", "ci-receipt"}:
            continue
        if item.get("kind") == "command-result":
            command = str(item.get("command", ""))
            item_tiers = {
                str(value)
                for value in item.get("tiers", [item.get("tier")])
                if str(value)
            }
            valid_pair = True
            for uid in item.get("requirement_uids", []):
                row = requirements.get(str(uid))
                contract = row.get("validation_contract", {}) if isinstance(row, dict) else {}
                approved_commands = {str(value) for value in contract.get("commands", []) if str(value)}
                checks = [value for value in contract.get("checks", []) if isinstance(value, dict)]
                matching = [value for value in checks if str(value.get("command", "")) == command]
                approved_tiers = {
                    str(value)
                    for check in matching
                    for value in check.get("tiers", [])
                    if str(value)
                } or {str(value) for value in contract.get("tiers", []) if str(value)}
                if approved_commands and (
                    command not in approved_commands or not item_tiers or item_tiers - approved_tiers
                ):
                    valid_pair = False
                    break
            if not valid_pair:
                continue
        identity = (
            tuple(sorted(str(value) for value in item.get("requirement_uids", []))),
            str(item.get("command", "")),
        )
        current[identity] = item
    receipts = [{key: item[key] for key in receipt_fields if key in item} for item in current.values()]
    paths = sorted({path for item in saved for path in item.get("changed_paths", [])})
    return {"schema_version": "1", "type": "tailtrail-execution-closure-input", "run_id": run_id, "changed_paths": paths, "receipts": receipts}


def record(root: Path, input_path: Path | None = None, run_id: str | None = None) -> dict[str, Any]:
    if input_path is None and not run_id:
        raise ValueError("closure record needs --input or --run-id for saved execution evidence")
    source = json.loads(input_path.read_text(encoding="utf-8")) if input_path else collected_input(root, str(run_id))
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
        key: item[key] for key in (
            "requirement_uids", "tier", "tiers", "scenario_ids", "command_label", "command",
            "outcome", "environment", "asserted_behavior", "evidence_label", "evidence_quality",
            "artifact", "collector", "exit_code", "started_at", "finished_at", "duration_ms",
            "stdout_artifact", "stderr_artifact", "stdout_sha256", "stderr_sha256",
        ) if key in item
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
        "validated_input": artifact_pointer(root, input_path) if input_path else "execution/evidence-stream.jsonl", "changed_paths": validated["changed_paths"],
        "receipt_artifacts": receipt_artifacts, "checkpoint": checkpoint["path"], "completion_review": review,
        "completion_gate": gate, "selected_harnesses": selected, "next_action": next_action,
        "boundary": "Recorded validated evidence. Managed-command receipts were executed and captured by TailTrail; declared host receipts remain explicitly unverified.",
    }
    L.atomic_json(record_path, payload)
    L.append_event(root, run_id, "closure_recorded", {"record_id": record_id, "artifact": record_path.relative_to(root).as_posix(), "receipt_count": len(normalized_receipts), "checkpoint": checkpoint["checkpoint"], "gate_complete": gate["complete"], "review_complete": review["complete"]})
    return {**payload, "reused": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--input", type=Path)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    try:
        if args.input is None and not args.run_id:
            raise ValueError("closure record needs --input or --run-id")
        print(json.dumps(record(args.root.resolve(), args.input.resolve() if args.input else None, args.run_id), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Closure recorder error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
