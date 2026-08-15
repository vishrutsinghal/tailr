#!/usr/bin/env python3
"""Finalize one approved TailTrail run from recorded closure evidence.

The finalizer runs only deterministic local harness assessments selected by the
approved execution handoff.  It never runs a receipt command, provisions an
environment, performs recovery, or converts missing behavioural evidence into a
pass.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, script: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


L = load("closure_finalizer_ledger", "run-ledger.py")
LOCK = load("closure_finalizer_lock", "planning-lock.py")
RECORDER = load("closure_finalizer_recorder", "closure-recorder.py")
ARCHITECTURE = load("closure_finalizer_architecture", "architecture-fitness.py")
BEHAVIOUR = load("closure_finalizer_behaviour", "behavior-harness.py")
MAINTAINABILITY = load("closure_finalizer_maintainability", "maintainability-harness.py")
REPORT = load("closure_finalizer_report", "completion-report.py")
CORRECTION = load("closure_finalizer_correction", "closure-correction.py")


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def latest_record(root: Path, run_id: str) -> dict[str, Any]:
    records = L.state_dir(root, run_id) / "closure-records"
    candidates: list[dict[str, Any]] = []
    for path in sorted(records.glob("closure-*.json")):
        item = read(path)
        if item.get("type") == "tailtrail-closure-record":
            candidates.append(item)
    if not candidates:
        raise ValueError("no closure record exists; run tailtrail closure record first or provide --input")
    return candidates[-1]


def selected_harnesses(root: Path, run_id: str) -> list[str]:
    path = L.state_dir(root, run_id) / "planning" / "execution-handoff-v1.json"
    if not path.is_file():
        raise ValueError("execution handoff is required; activate the approved Planning Lock first")
    closure = read(path).get("closure", {})
    values = closure.get("selected_harnesses", []) if isinstance(closure, dict) else []
    return [str(value) for value in values if isinstance(value, str)]


def behavior_scenarios(root: Path, run_id: str) -> list[dict[str, Any]]:
    anchor = read(L.state_dir(root, run_id) / "anchors" / "approved-v1.json")
    rows: list[dict[str, Any]] = []
    for requirement in anchor.get("requirements", []):
        contract = requirement.get("behavior_contract", {})
        scenarios = contract.get("scenarios", []) if isinstance(contract, dict) else []
        if not isinstance(scenarios, list):
            continue
        for scenario in scenarios:
            if not isinstance(scenario, dict):
                continue
            rows.append({"requirement_uid": requirement["requirement_uid"], **scenario})
    return rows


def missing_behavior(root: Path, run_id: str) -> dict[str, Any]:
    """Persist a fail-closed assessment rather than inferring a user journey."""
    directory = L.state_dir(root, run_id)
    payload = {
        "schema_version": "1", "type": "tailtrail-behavior-harness", "run_id": run_id,
        "scenarios": [],
        "findings": [{
            "category": "behaviour", "classification": "needs-decision",
            "message": "Behaviour Harness was selected but no declared scenario evidence was supplied.",
            "evidence": "approved-execution-handoff",
        }],
        "complete": False, "evidence_label": "approved-execution-handoff",
        "boundary": "TailTrail does not infer a user-flow pass from unit, integration, or contract receipts.",
    }
    folder = directory / "behavior"
    artifact = folder / f"assessment-{len(list(folder.glob('assessment-*.json'))) + 1}.json"
    L.atomic_json(artifact, payload)
    L.append_event(root, run_id, "behavior_assessed", {
        "artifact": artifact.relative_to(directory).as_posix(), "findings": 1, "complete": False,
    })
    return {**payload, "run_artifact": artifact.as_posix()}


def run_behavior(root: Path, run_id: str, scenarios_path: Path | None) -> dict[str, Any]:
    directory = L.state_dir(root, run_id)
    if scenarios_path is None:
        scenarios = behavior_scenarios(root, run_id)
        if not scenarios:
            return missing_behavior(root, run_id)
        scenarios_path = directory / "finalizers" / "approved-behavior-scenarios.json"
        L.atomic_json(scenarios_path, {"scenarios": scenarios})
    receipts = directory / "closure-records"
    candidates = sorted(receipts.glob("closure-*-receipts.json"))
    if not candidates:
        return missing_behavior(root, run_id)
    return BEHAVIOUR.assess(root, run_id, scenarios_path, candidates[-1])


def higher_tier_status(root: Path, run_id: str) -> dict[str, Any]:
    directory = L.state_dir(root, run_id)
    anchor = read(directory / "anchors" / "approved-v1.json")
    receipts = [read(path) for path in sorted((directory / "validation-receipts").glob("*.json"))]
    high = {"integration", "contract", "e2e", "infrastructure", "release-smoke"}
    required = [
        {"requirement_uid": row["requirement_uid"], "tier": tier}
        for row in anchor.get("requirements", [])
        for tier in (row.get("validation_contract", {}) or {}).get("tiers", [])
        if tier in high and (row.get("validation_contract", {}) or {}).get("state", "required") == "required"
    ]
    missing = [item for item in required if not any(
        receipt.get("requirement_uid") == item["requirement_uid"]
        and receipt.get("tier") == item["tier"] and receipt.get("outcome") == "pass"
        for receipt in receipts
    )]
    return {
        "required": required, "missing": missing,
        "status": "pass" if not missing else "required-evidence-missing",
        "boundary": "The finalizer reads saved higher-tier receipts only; it never runs integration, contract, E2E, infrastructure, or release commands.",
    }


def finalize(root: Path, run_id: str, input_path: Path | None = None, scenarios_path: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    if input_path is not None:
        resolved_input = input_path.resolve()
        if read(resolved_input).get("run_id") != run_id:
            raise ValueError("closure input run_id must match --run-id")
        closure = RECORDER.record(root, resolved_input)
    else:
        try:
            closure = latest_record(root, run_id)
        except ValueError:
            closure = RECORDER.record(root, run_id=run_id)
    LOCK.assert_write_allowed(root, run_id)
    selected = selected_harnesses(root, run_id)
    key = {
        "closure_record_id": closure["record_id"], "selected_harnesses": selected,
        "scenarios": relative(root, scenarios_path.resolve()) if scenarios_path else "approved-anchor",
    }
    finalizer_id = "finalizer-" + hashlib.sha256(canonical(key).encode("utf-8")).hexdigest()[:16]
    directory = L.state_dir(root, run_id)
    saved = directory / "finalizers" / f"{finalizer_id}.json"
    if saved.is_file():
        return {**read(saved), "reused": True}

    changed = [str(item) for item in closure.get("changed_paths", [])]
    assessments: dict[str, dict[str, Any]] = {}
    if "Architecture Fitness Harness" in selected:
        assessments["Architecture Fitness Harness"] = ARCHITECTURE.assess(root, run_id, changed)
    if "Behaviour Harness" in selected:
        assessments["Behaviour Harness"] = run_behavior(root, run_id, scenarios_path.resolve() if scenarios_path else None)
    if "Maintainability Harness" in selected:
        assessments["Maintainability Harness"] = MAINTAINABILITY.assess(root, run_id, changed)

    higher = higher_tier_status(root, run_id)
    report = REPORT.build(root, run_id)
    correction = CORRECTION.handoff(root, run_id) if report["overall_status"] != "complete" else None
    payload = {
        "schema_version": "1", "type": "tailtrail-closure-finalizer", "finalizer_id": finalizer_id,
        "run_id": run_id, "closure_record_id": closure["record_id"], "selected_harnesses": selected,
        "assessments": {name: {"complete": item.get("complete"), "artifact": item.get("run_artifact")} for name, item in assessments.items()},
        "higher_tier_evidence": higher,
        "recovery": report["recovery_checkpoint"],
        "context_continuity": report["drift_learning"],
        "correction": correction,
        "completion_report": report.get("run_artifact"),
        "overall_status": report["overall_status"],
        "boundary": "Finalized deterministic local control evidence only. No receipt command, deployment, recovery action, or external environment was executed.",
    }
    L.atomic_json(saved, payload)
    L.append_event(root, run_id, "closure_finalized", {
        "artifact": saved.relative_to(directory).as_posix(), "closure_record_id": closure["record_id"],
        "overall_status": report["overall_status"], "selected_harnesses": selected,
    })
    return {**payload, "reused": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--input", type=Path, help="Optional Phase 0 closure input; it is recorded idempotently before finalization.")
    parser.add_argument("--scenarios", type=Path, help="Declared Behaviour Harness scenario JSON when behaviour was selected.")
    args = parser.parse_args()
    try:
        print(json.dumps(finalize(args.root, args.run_id, args.input, args.scenarios), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Closure finalizer error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
