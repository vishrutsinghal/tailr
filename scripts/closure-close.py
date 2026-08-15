#!/usr/bin/env python3
"""Render a closure decision; after acceptance, automate candidate learning and evaluation."""
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


L = load("closure_close_ledger", "run-ledger.py")
LOCK = load("closure_close_lock", "planning-lock.py")
FINALIZER = load("closure_close_finalizer", "closure-finalizer.py")
LEARNING = load("closure_close_learning", "closure-learning.py")
EVALUATION = load("closure_close_evaluation", "closure-evaluation.py")
STATE = load("closure_close_official_state", "official-aidlc-state.py")
SAN = load("closure_close_official_sanitizer", "official-aidlc-sanitize.py")
RUNTIME = load("closure_close_official_runtime", "official-aidlc-runtime.py")


def official_closure_link(root: Path, run_id: str, completion_report: str, acceptance: str) -> dict[str, Any] | None:
    """Write references to Full-mode official artifacts without copying their content."""
    directory = L.state_dir(root, run_id)
    bridge_path = directory / "aidlc-official" / "bridge-v1.json"
    if not bridge_path.is_file():
        return None
    bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
    runtime = RUNTIME.assert_attached(root, run_id) if bridge.get("mode") == "full" else None
    handoff = directory / "aidlc-official" / "checkpoints" / "handoff-v1.json"
    operations = sorted((directory / "aidlc-official" / "checkpoints").glob("operations-*.json"))
    path = directory / "aidlc-official" / "closure" / "closure-link-v1.json"
    completion_path = Path(completion_report)
    completion_path = completion_path.resolve() if completion_path.is_absolute() else (root / completion_path).resolve()
    try:
        completion_reference = completion_path.relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise ValueError("completion report reference must stay inside the project root") from error
    payload = {
        "schema_version": "1",
        "type": "tailtrail-official-aidlc-closure-link",
        "run_id": run_id,
        "official_intent_id": bridge.get("official_intent_id"),
        "official_session_id": bridge.get("official_session_id"),
        "official_revision": bridge.get("official_revision"),
        "completion_report": completion_reference,
        "official_handoff_reference": handoff.relative_to(root).as_posix() if handoff.is_file() else None,
        "official_operations_references": [item.relative_to(root).as_posix() for item in operations],
        "official_runtime_session": runtime.get("session_artifact") if runtime else None,
        "official_current_stage": runtime.get("current_stage") if runtime else None,
        "official_transition_count": runtime.get("transition_count") if runtime else 0,
        "acceptance_state": acceptance,
        "boundary": "References and immutable identifiers only; no source, prompts, logs, receipt bodies, deployment data, or sensitive official artifacts are copied.",
    }
    SAN.validate_artifact(root, payload, "closure")
    L.atomic_json(path, payload)
    L.append_event(root, run_id, "closure_finalized", {"kind": "official-aidlc-closure-link", "artifact": path.relative_to(root).as_posix(), "acceptance_state": acceptance})
    return {"artifact": path.relative_to(root).as_posix(), **payload}


def resolve_run(root: Path, run_id: str | None) -> str:
    if run_id:
        return run_id
    candidates = []
    for path in sorted((root / ".tailtrail" / "runs").glob("*")):
        if path.is_dir() and (path / "closure-records").is_dir():
            try:
                if LOCK.show(root, path.name).get("status") == "approved": candidates.append(path.name)
            except (OSError, ValueError, json.JSONDecodeError):
                pass
    if len(candidates) == 1: return candidates[0]
    if not candidates: raise ValueError("no approved run with closure evidence was found; provide --run-id")
    raise ValueError("multiple approved closure runs exist; provide --run-id: " + ", ".join(candidates))


def baseline(root: Path, run_id: str) -> Path:
    directory = L.state_dir(root, run_id); path = directory / "closure-baselines" / "approved-anchor-v1.json"
    if path.is_file(): return path
    anchor = json.loads((directory / "anchors" / "approved-v1.json").read_text(encoding="utf-8")); total = len(anchor.get("requirements", []))
    if total < 1: raise ValueError("approved anchor has no requirements; cannot derive a baseline")
    L.atomic_json(path, {"type": "tailtrail-closure-baseline", "baseline_kind": "approved-anchor-delivery-start", "requirements_complete": 0, "requirements_total": total, "unresolved_drift": 0, "tests_pass": False, "boundary": "Derived automatically from the immutable pre-implementation approved anchor as a delivery-start snapshot. It measures delivery progression, not agent or quality performance."})
    return path


def record_decision(root: Path, run_id: str, state: str, completion_report: str, *, decision: str | None = None, baseline_path: Path | None = None, ci_receipt: str | None = None) -> dict[str, Any]:
    """Persist a sanitized acceptance-state transition without promoting learning."""
    directory = L.state_dir(root, run_id)
    key = {"run_id": run_id, "state": state, "decision": decision, "completion_report": completion_report, "ci_receipt": ci_receipt}
    decision_id = "decision-" + hashlib.sha256(json.dumps(key, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    path = directory / "closure-decisions" / f"{decision_id}.json"
    payload = {
        "schema_version": "1", "type": "tailtrail-closure-acceptance", "decision_id": decision_id,
        "run_id": run_id, "state": state, "decision": decision, "completion_report": completion_report,
        "baseline": baseline_path.relative_to(root).as_posix() if baseline_path else None,
        "ci_receipt": ci_receipt,
        "boundary": "Acceptance state only. It does not change source, execute validation, promote learning, or infer missing evidence.",
    }
    if not path.is_file():
        L.atomic_json(path, payload)
    return {"artifact": path.relative_to(root).as_posix(), **payload}


def trusted_ci(root: Path, run_id: str, receipt: Path | None) -> str:
    if receipt is None or not receipt.is_file():
        raise ValueError("CI acceptance requires a saved linked CI ingestion artifact via --ci-receipt")
    resolved = receipt.resolve()
    try:
        relative = resolved.relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise ValueError("CI receipt must be inside the project root") from error
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if payload.get("type") != "tailtrail-ci-evidence-ingestion" or payload.get("run_id") != run_id:
        raise ValueError("CI receipt must be a linked TailTrail CI ingestion artifact for this run")
    if not payload.get("receipts") or not isinstance(payload.get("provenance"), dict):
        raise ValueError("CI receipt must include saved receipts and provenance")
    return relative


def close(root: Path, run_id: str | None = None, decision: str | None = None, input_path: Path | None = None, scenarios: Path | None = None, ci_receipt: Path | None = None) -> dict[str, Any]:
    root = root.resolve(); selected = resolve_run(root, run_id)
    STATE.assert_consistent(root, selected)
    finalized = FINALIZER.finalize(root, selected, input_path, scenarios)
    # The close-out surface is where the user sees the completion decision.
    # Persist a freshly derived report instead of returning an older pointer
    # from a previous finalizer invocation.
    report = FINALIZER.REPORT.build(root, selected, record=True)
    report_artifact = report.get("run_artifact") or finalized.get("completion_report")
    official = official_closure_link(root, selected, str(report_artifact), "evidence-incomplete" if report["overall_status"] != "complete" else "awaiting-acceptance")
    if report["overall_status"] != "complete":
        recorded = record_decision(root, selected, "evidence-incomplete", str(report_artifact))
        return {"type": "tailtrail-closure-close", "run_id": selected, "state": "evidence-incomplete", "completion_report": report_artifact, "official_aidlc": official, "acceptance_record": recorded, "correction": finalized.get("correction"), "next_action": "Review the gap and use bounded correction or approved replan. No acceptance or positive learning was recorded."}
    baseline_path = baseline(root, selected)
    if decision is None:
        recorded = record_decision(root, selected, "awaiting-acceptance", str(report_artifact), baseline_path=baseline_path)
        return {"type": "tailtrail-closure-close", "run_id": selected, "state": "awaiting-acceptance", "completion_report": report_artifact, "official_aidlc": official, "acceptance_record": recorded, "baseline": baseline_path.relative_to(root).as_posix(), "acceptance_prompt": {"question": "TailTrail closure is complete. Accept this delivery?", "options": ["accept-user", "wait-ci", "reopen"]}, "boundary": "No learning or evaluation is written until a decision is supplied."}
    if decision == "wait-ci":
        recorded = record_decision(root, selected, "awaiting-ci", str(report_artifact), decision=decision, baseline_path=baseline_path)
        return {"type": "tailtrail-closure-close", "run_id": selected, "state": "awaiting-ci", "completion_report": report_artifact, "official_aidlc": official_closure_link(root, selected, str(report_artifact), "awaiting-ci"), "acceptance_record": recorded, "baseline": baseline_path.relative_to(root).as_posix(), "next_action": "Link a trusted CI receipt before CI acceptance. No positive learning was recorded."}
    if decision == "reopen":
        recorded = record_decision(root, selected, "reopened", str(report_artifact), decision=decision, baseline_path=baseline_path)
        return {"type": "tailtrail-closure-close", "run_id": selected, "state": "reopened", "completion_report": report_artifact, "official_aidlc": official_closure_link(root, selected, str(report_artifact), "reopened"), "acceptance_record": recorded, "next_action": "Use bounded correction or approved replan; prior evidence remains preserved."}
    if decision not in {"accept-user", "accept-ci"}: raise ValueError("decision must be accept-user, wait-ci, accept-ci, or reopen")
    accepted_by = "trusted-ci" if decision == "accept-ci" else "user"
    ci_reference = trusted_ci(root, selected, ci_receipt) if decision == "accept-ci" else None
    learned = LEARNING.capture(root, selected, accepted_by); evaluated = EVALUATION.evaluate(root, selected, baseline_path)
    recorded = record_decision(root, selected, "accepted", str(report_artifact), decision=decision, baseline_path=baseline_path, ci_receipt=ci_reference)
    return {"type": "tailtrail-closure-close", "run_id": selected, "state": "accepted", "accepted_by": accepted_by, "ci_receipt": ci_reference, "completion_report": report_artifact, "official_aidlc": official_closure_link(root, selected, str(report_artifact), "accepted-ci" if decision == "accept-ci" else "accepted-user"), "acceptance_record": recorded, "baseline": baseline_path.relative_to(root).as_posix(), "positive_learning": learned, "evaluation": evaluated, "boundary": "Acceptance created candidate-only learning and deterministic evaluation; it did not promote guidance or claim quality improvement."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--root", type=Path, default=Path.cwd()); parser.add_argument("--run-id"); parser.add_argument("--decision", choices=("accept-user", "wait-ci", "accept-ci", "reopen")); parser.add_argument("--input", type=Path); parser.add_argument("--scenarios", type=Path); parser.add_argument("--ci-receipt", type=Path); args = parser.parse_args()
    try: print(json.dumps(close(args.root, args.run_id, args.decision, args.input, args.scenarios, args.ci_receipt), indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error: print(f"Closure close error: {error}"); return 2


if __name__ == "__main__": raise SystemExit(main())
