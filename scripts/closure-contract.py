#!/usr/bin/env python3
"""Validate the Phase 0 record-only closure input contract.

This command intentionally does not run receipts, write evidence, edit source,
or read raw command output. Phase 1 will consume a validated input to create
the run-local closure artifacts.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TIERS = {"unit", "component", "integration", "contract", "e2e", "infrastructure", "release-smoke"}
OUTCOMES = {"pass", "fail", "blocked", "timed-out", "unavailable"}
EVIDENCE_LABELS = {"local-command", "ci-receipt", "host-telemetry"}


def ledger() -> Any:
    spec = importlib.util.spec_from_file_location("closure_contract_ledger", ROOT / "scripts" / "run-ledger.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


L = ledger()


def repository_path(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty repository-relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field} must be repository-relative")
    return path.as_posix()


def short_text(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f"{field} must be a non-empty string")
    if "\n" in value or "\r" in value:
        raise ValueError(f"{field} must be a single line; raw command output is not accepted")
    if len(value) > 4096:
        raise ValueError(f"{field} exceeds the 4096-character contract limit")
    return value.strip()


def approved_requirement_uids(root: Path, run_id: str) -> set[str]:
    path = L.state_dir(root, run_id) / "anchors" / "approved-v1.json"
    if not path.is_file():
        raise ValueError(f"approved anchor for run `{run_id}` does not exist")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(row.get("requirement_uid", "")) for row in payload.get("requirements", []) if isinstance(row, dict)}


def validate_receipt(receipt: Any, known_requirements: set[str], index: int) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        raise ValueError(f"receipts[{index}] must be an object")
    allowed = {"requirement_uids", "tier", "command_label", "command", "outcome", "environment", "asserted_behavior", "artifact", "evidence_label"}
    unknown = set(receipt) - allowed
    if unknown:
        raise ValueError(f"receipts[{index}] has unsupported fields: {', '.join(sorted(unknown))}")
    uids = receipt.get("requirement_uids")
    if not isinstance(uids, list) or not uids or not all(isinstance(item, str) for item in uids):
        raise ValueError(f"receipts[{index}].requirement_uids must be a non-empty list")
    if len(set(uids)) != len(uids):
        raise ValueError(f"receipts[{index}].requirement_uids must not contain duplicates")
    unknown_uids = sorted(set(uids) - known_requirements)
    if unknown_uids:
        raise ValueError(f"receipts[{index}] references unknown approved requirement UID(s): {', '.join(unknown_uids)}")
    tier = receipt.get("tier")
    if tier not in TIERS:
        raise ValueError(f"receipts[{index}].tier is not supported")
    outcome = receipt.get("outcome")
    if outcome not in OUTCOMES:
        raise ValueError(f"receipts[{index}].outcome is not supported")
    label = receipt.get("evidence_label", "local-command")
    if label not in EVIDENCE_LABELS:
        raise ValueError(f"receipts[{index}].evidence_label is not supported")
    normalized = {
        "requirement_uids": sorted(uids),
        "tier": tier,
        "command_label": short_text(receipt.get("command_label"), f"receipts[{index}].command_label"),
        "command": short_text(receipt.get("command"), f"receipts[{index}].command"),
        "outcome": outcome,
        "environment": short_text(receipt.get("environment"), f"receipts[{index}].environment"),
        "asserted_behavior": short_text(receipt.get("asserted_behavior"), f"receipts[{index}].asserted_behavior"),
        "evidence_label": label,
    }
    if "artifact" in receipt:
        normalized["artifact"] = repository_path(receipt["artifact"], f"receipts[{index}].artifact")
    return normalized


def validate_input(root: Path, payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("closure input must be a JSON object")
    allowed = {"schema_version", "type", "run_id", "changed_paths", "receipts", "host_token_telemetry"}
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(f"closure input has unsupported fields: {', '.join(sorted(unknown))}")
    if payload.get("schema_version") != "1" or payload.get("type") != "tailtrail-execution-closure-input":
        raise ValueError("closure input must use schema_version `1` and type `tailtrail-execution-closure-input`")
    run_id = short_text(payload.get("run_id"), "run_id")
    if Path(run_id).name != run_id:
        raise ValueError("run_id must be a single local run identifier")
    known = approved_requirement_uids(root, run_id)
    changed = payload.get("changed_paths")
    if not isinstance(changed, list) or not all(isinstance(item, str) for item in changed):
        raise ValueError("changed_paths must be a list of repository-relative paths")
    normalized_changed = sorted({repository_path(item, "changed_paths item") for item in changed})
    receipts = payload.get("receipts")
    if not isinstance(receipts, list) or not receipts:
        raise ValueError("receipts must contain at least one requirement-linked receipt")
    normalized_receipts = [validate_receipt(item, known, index) for index, item in enumerate(receipts)]
    telemetry = payload.get("host_token_telemetry")
    normalized_telemetry = None
    if telemetry is not None:
        if not isinstance(telemetry, dict) or set(telemetry) - {"artifact", "task_id"}:
            raise ValueError("host_token_telemetry may contain only artifact and task_id")
        task_id = short_text(telemetry.get("task_id"), "host_token_telemetry.task_id")
        if task_id != run_id:
            raise ValueError("host_token_telemetry.task_id must equal run_id")
        normalized_telemetry = {"task_id": task_id, "artifact": repository_path(telemetry.get("artifact"), "host_token_telemetry.artifact")}
    return {
        "schema_version": "1",
        "type": "tailtrail-execution-closure-input",
        "run_id": run_id,
        "changed_paths": normalized_changed,
        "receipts": normalized_receipts,
        "host_token_telemetry": normalized_telemetry,
        "contract_status": "valid",
        "boundary": "Validated record-only closure input. It does not execute commands, write run artifacts, or create a completion claim.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        source = json.loads(args.input.read_text(encoding="utf-8"))
        print(json.dumps(validate_input(args.root.resolve(), source), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Closure contract error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
