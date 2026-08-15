#!/usr/bin/env python3
"""Prepare, record, and report real-host TailTrail conformance evidence.

This surface never controls a host or infers runtime success from generated
instructions. It prepares portable scenarios, validates a sanitized receipt
against canonical run artifacts, and reports fresh evidence per host/version.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HOSTS = {"codex", "copilot", "claude"}
STATUSES = {"passed", "failed", "not-validated", "stale", "incompatible"}
MATRIX = ROOT / "adapters" / "host-compatibility-v1.json"
SCENARIOS = ROOT / "adapters" / "runtime-scenarios-v1.json"


def load(relative: str, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


L = load("scripts/run-ledger.py", "host_runtime_ledger")
STATE = load("scripts/official-aidlc-state.py", "host_runtime_state")
SAN = load("scripts/official-aidlc-sanitize.py", "host_runtime_sanitizer")
INSTRUCTIONS = load("scripts/host-adapter-conformance.py", "host_runtime_instruction_conformance")


def read(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain one JSON object")
    return payload


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def receipt_digest(payload: dict[str, Any]) -> str:
    return digest({key: value for key, value in payload.items() if key != "integrity"})


def contracts() -> tuple[dict[str, Any], dict[str, Any]]:
    matrix, scenarios = read(MATRIX), read(SCENARIOS)
    if matrix.get("type") != "tailtrail-host-adapter-compatibility" or matrix.get("adapter_version") != "v2":
        raise ValueError("host compatibility matrix is incompatible")
    if scenarios.get("type") != "tailtrail-host-runtime-scenarios" or scenarios.get("scenario_version") != "v1":
        raise ValueError("host runtime scenario contract is incompatible")
    expected = {item.get("id") for item in matrix.get("conformance_scenarios", [])}
    actual = {item.get("id") for item in scenarios.get("scenarios", [])}
    if expected != actual or expected != {"small-bug", "hands-free-feature", "rejected-requirement", "evidence-failure", "recovery", "ci-wait"}:
        raise ValueError("instruction and runtime scenario sets do not match")
    return matrix, scenarios


def host_entry(matrix: dict[str, Any], host: str) -> dict[str, Any]:
    if host not in HOSTS:
        raise ValueError("host must be codex, copilot, or claude")
    entry = next((item for item in matrix.get("hosts", []) if item.get("id") == host), None)
    if not isinstance(entry, dict):
        raise ValueError(f"host `{host}` is not present in the compatibility matrix")
    return entry


def bundle_payload(host: str) -> dict[str, Any]:
    matrix, scenarios = contracts()
    entry = host_entry(matrix, host)
    source = ROOT / str(entry["source"])
    if not source.is_file():
        raise ValueError(f"host instruction source is missing: {entry['source']}")
    core = {
        "schema_version": "1",
        "type": "tailtrail-host-runtime-bundle",
        "bundle_version": "v1",
        "host": host,
        "adapter_version": matrix["adapter_version"],
        "runtime_adapter": entry.get("runtime_adapter"),
        "scenario_version": scenarios["scenario_version"],
        "instruction_source": entry["source"],
        "instruction_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "scenario_contract": SCENARIOS.relative_to(ROOT).as_posix(),
        "receipt_schema": matrix["runtime_receipt_schema"],
        "scenarios": scenarios["scenarios"],
        "boundary": "Portable observable contract only. It contains no source, prompt, secret, execution result, or runtime pass claim.",
    }
    return {**core, "bundle_digest": digest(core)}


def prepare(root: Path, host: str) -> dict[str, Any]:
    root = root.resolve()
    payload = bundle_payload(host)
    path = root / ".tailtrail" / "host-runtime" / "bundles" / f"{host}-v1.json"
    L.atomic_json(path, payload)
    return {**payload, "artifact": path.relative_to(root).as_posix(), "state": "prepared", "next_action": "Run the six scenarios in the named host, then submit one sanitized receipt per scenario."}


def _run_dir(root: Path, run_id: str) -> Path:
    if not run_id or Path(run_id).name != run_id:
        raise ValueError("run_id must be one local TailTrail run identifier")
    path = L.state_dir(root, run_id)
    if not (path / "manifest.json").is_file():
        raise ValueError(f"TailTrail run `{run_id}` does not exist")
    return path


def _contains_key(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            found = _contains_key(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _contains_key(child, key)
            if found is not None:
                return found
    return None


def _events(directory: Path) -> list[dict[str, Any]]:
    path = directory / "events.jsonl"
    return L.read_events(path) if path.is_file() else []


def _json_contains(directory: Path, value: str) -> bool:
    for path in directory.rglob("*.json"):
        try:
            if value in path.read_text(encoding="utf-8"):
                return True
        except OSError:
            continue
    return False


def canonical_probes(root: Path, run_id: str, scenario: str) -> dict[str, bool]:
    directory = _run_dir(root, run_id)
    events = _events(directory)
    event_types = {item.get("event_type") for item in events}
    lock = directory / "planning" / "lock-v1.json"
    report_path = directory / "planning" / "start-report-v1.json"
    report = read(report_path) if report_path.is_file() else {}
    anchor = directory / "anchors" / "approved-v1.json"
    latest_checkpoints = sorted((directory / "checkpoints").glob("checkpoint-*.json"))
    latest = read(latest_checkpoints[-1]) if latest_checkpoints else {}
    incomplete = any(str(row.get("state", row.get("status", ""))) not in {"complete", "validated", "passed"} for row in latest.get("requirements", []) if isinstance(row, dict))
    recovery = (directory / "recovery" / "boundary.json").is_file() or "recovery_boundary_created" in event_types
    positive_directory = directory / "positive-learning"
    positive = positive_directory.exists() and any(positive_directory.glob("*.json"))
    probes = {
        "planning-lock": lock.is_file(),
        "start-report": report_path.is_file(),
        "hands-free-program": isinstance(_contains_key(report, "hands_free_program"), dict),
        "proposal-rejected": "proposal_rejected" in event_types,
        "incomplete-checkpoint": incomplete or _json_contains(directory / "aidlc-official" / "checkpoints", '"complete": false'),
        "correction-route": bool({"closure_correction_routed", "harness_feedback"} & event_types) or _json_contains(directory, "correction"),
        "approved-anchor": anchor.is_file(),
        "recovery-boundary": recovery,
        "ci-wait-closure": _json_contains(directory, "awaiting-ci"),
        "no-positive-learning": not positive,
    }
    contract = next(item for item in contracts()[1]["scenarios"] if item["id"] == scenario)
    return {name: bool(probes.get(name)) for name in contract["canonical_probes"]}


def _safe_receipt_path(root: Path, value: Path) -> Path:
    path = value.resolve() if value.is_absolute() else (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError("host runtime receipt must stay inside the project root") from error
    if not path.is_file():
        raise ValueError("host runtime receipt does not exist")
    return path


def validate_receipt(root: Path, requested_host: str, payload: dict[str, Any]) -> dict[str, Any]:
    matrix, scenarios = contracts()
    SAN.validate_artifact(root, payload, "host-runtime-receipt")
    if payload.get("schema_version") != "1" or payload.get("type") != "tailtrail-host-runtime-receipt":
        raise ValueError("host runtime receipt contract is incompatible")
    if payload.get("host") != requested_host:
        raise ValueError("receipt host does not match --host")
    entry = host_entry(matrix, requested_host)
    run_id = str(payload.get("run_id", ""))
    canonical_state = STATE.assert_consistent(root, run_id)
    scenario = next((item for item in scenarios["scenarios"] if item["id"] == payload.get("scenario_id")), None)
    if not scenario:
        raise ValueError("receipt scenario is not in the current runtime contract")
    integrity = payload.get("integrity") or {}
    if integrity.get("algorithm") != "sha256" or integrity.get("digest") != receipt_digest(payload):
        raise ValueError("host runtime receipt integrity digest is invalid")
    transitions = payload.get("observed_transitions")
    if not isinstance(transitions, list) or not transitions:
        raise ValueError("host runtime receipt needs at least one observed transition")
    for index, transition in enumerate(transitions, start=1):
        if not isinstance(transition, dict) or set(transition) != {"sequence", "state"} or transition.get("sequence") != index:
            raise ValueError("observed transitions must be contiguous ordered sequence/state objects")
        SAN.identifier(transition.get("state"), f"host-runtime-receipt.observed_transitions[{index-1}].state")
    references = payload.get("artifact_references")
    if not isinstance(references, list) or not references:
        raise ValueError("host runtime receipt needs repository-local artifact references")
    run_directory = _run_dir(root, run_id).resolve()
    linked_to_run = False
    for index, reference in enumerate(references):
        relative = SAN.local_reference(root, reference, f"host-runtime-receipt.artifact_references[{index}]")
        try:
            (root / relative).resolve().relative_to(run_directory)
            linked_to_run = True
        except ValueError:
            pass
    if not linked_to_run:
        raise ValueError("at least one artifact reference must belong to the selected TailTrail run")

    current_bundle = bundle_payload(requested_host)
    incompatible = payload.get("adapter_version") != matrix["adapter_version"] or entry.get("runtime_adapter") != "receipt-v1"
    stale = payload.get("scenario_version") != scenarios["scenario_version"] or payload.get("bundle_digest") != current_bundle["bundle_digest"]
    observations = {str(item) for item in payload.get("observations", [])}
    missing_observations = sorted(set(scenario["required_observations"]) - observations)
    probes = canonical_probes(root, run_id, str(payload["scenario_id"]))
    failed_probes = sorted(name for name, passed in probes.items() if not passed)
    declared_fail = payload.get("declared_outcome") != "pass" or bool(payload.get("failure_codes"))
    if incompatible:
        evaluation = "incompatible"
    elif stale:
        evaluation = "stale"
    elif declared_fail or missing_observations or failed_probes:
        evaluation = "failed"
    else:
        evaluation = "passed"
    return {
        "evaluation": evaluation,
        "scenario_id": payload["scenario_id"],
        "host": requested_host,
        "host_version": payload["host_version"],
        "adapter_version": payload["adapter_version"],
        "run_id": run_id,
        "receipt_id": payload["receipt_id"],
        "missing_observations": missing_observations,
        "canonical_probes": probes,
        "failed_probes": failed_probes,
        "canonical_state": {"status": canonical_state["status"], "valid": canonical_state["valid"]},
        "evidence_label": "supplied-host-receipt + deterministic-local-validation",
        "boundary": "Observed host evidence is advisory until this validator links it to the current scenario contract and canonical run state.",
    }


def record(root: Path, host: str, receipt_path: Path) -> dict[str, Any]:
    root = root.resolve()
    source = _safe_receipt_path(root, receipt_path)
    payload = read(source)
    evaluated = validate_receipt(root, host, payload)
    receipt_id = SAN.identifier(payload.get("receipt_id"), "host-runtime-receipt.receipt_id")
    directory = root / ".tailtrail" / "host-runtime" / "receipts" / host / str(payload["scenario_id"]) / receipt_id
    saved_receipt, saved_evaluation = directory / "receipt-v1.json", directory / "evaluation-v1.json"
    if saved_receipt.exists() and read(saved_receipt) != payload:
        raise ValueError("receipt_id is immutable and already belongs to different evidence")
    if saved_receipt.exists() and saved_evaluation.is_file():
        existing = read(saved_evaluation)
        return {**existing, "artifact": saved_evaluation.relative_to(root).as_posix(), "idempotent": True}
    L.atomic_json(saved_receipt, payload)
    event = L.append_event(root, payload["run_id"], "host_runtime_conformance_recorded", {"host": host, "scenario_id": payload["scenario_id"], "receipt_id": receipt_id, "evaluation": evaluated["evaluation"], "artifact": saved_evaluation.relative_to(root).as_posix()})
    evaluation = {
        "schema_version": "1",
        "type": "tailtrail-host-runtime-evaluation",
        **evaluated,
        "ledger_sequence": event["sequence"],
        "receipt_artifact": saved_receipt.relative_to(root).as_posix(),
    }
    L.atomic_json(saved_evaluation, evaluation)
    return {**evaluation, "artifact": saved_evaluation.relative_to(root).as_posix()}


def report(root: Path, host: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    matrix, scenarios = contracts()
    selected = [host] if host else [item["id"] for item in matrix["hosts"]]
    instruction_errors = INSTRUCTIONS.check(ROOT, matrix)
    rows = []
    expected = {item["id"] for item in scenarios["scenarios"]}
    for host_id in selected:
        host_entry(matrix, host_id)
        evaluations: dict[str, dict[str, Any]] = {}
        base = root / ".tailtrail" / "host-runtime" / "receipts" / host_id
        for scenario_id in expected:
            available = [read(path) for path in (base / scenario_id).glob("*/evaluation-v1.json")]
            if available:
                evaluations[scenario_id] = max(available, key=lambda item: int(item.get("ledger_sequence", 0)))
        states = {row.get("evaluation") for row in evaluations.values()}
        if "incompatible" in states:
            status = "incompatible"
        elif "stale" in states:
            status = "stale"
        elif "failed" in states:
            status = "failed"
        elif set(evaluations) != expected:
            status = "not-validated"
        elif states == {"passed"}:
            status = "passed"
        else:
            status = "not-validated"
        rows.append({"host": host_id, "runtime_status": status, "scenario_coverage": len(evaluations), "scenario_total": len(expected), "scenarios": {key: evaluations[key].get("evaluation") for key in sorted(evaluations)}, "latest_evaluations": {key: evaluations[key].get("receipt_artifact") for key in sorted(evaluations)}})
    return {
        "schema_version": "1",
        "type": "tailtrail-host-runtime-conformance-report",
        "adapter_version": matrix["adapter_version"],
        "scenario_version": scenarios["scenario_version"],
        "instruction_conformance": {"status": "passed" if not instruction_errors else "failed", "issues": instruction_errors},
        "runtime_conformance": rows,
        "allowed_statuses": sorted(STATUSES),
        "boundary": "Instruction and runtime statuses are separate. Missing runtime receipts are not-validated, never passed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare_parser = sub.add_parser("prepare"); prepare_parser.add_argument("--root", type=Path, default=Path.cwd()); prepare_parser.add_argument("--host", choices=sorted(HOSTS), required=True)
    record_parser = sub.add_parser("record"); record_parser.add_argument("--root", type=Path, default=Path.cwd()); record_parser.add_argument("--host", choices=sorted(HOSTS), required=True); record_parser.add_argument("--receipt", type=Path, required=True)
    report_parser = sub.add_parser("report"); report_parser.add_argument("--root", type=Path, default=Path.cwd()); report_parser.add_argument("--host", choices=sorted(HOSTS))
    args = parser.parse_args()
    try:
        payload = prepare(args.root, args.host) if args.action == "prepare" else (record(args.root, args.host, args.receipt) if args.action == "record" else report(args.root, args.host))
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, SAN.SanitizationError) as error:
        print(f"Host runtime conformance error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
