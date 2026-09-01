#!/usr/bin/env python3
"""Select and converge existing TailTrail Harness evidence for a debug correction."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


LEDGER = load("debug_convergence_ledger", "run-ledger.py")
CORRECTION = load("debug_convergence_correction", "debug-correction.py")
EVIDENCE = load("debug_convergence_evidence", "execution-evidence.py")
ARCHITECTURE = load("debug_convergence_architecture", "architecture-fitness.py")
MAINTAINABILITY = load("debug_convergence_maintainability", "maintainability-harness.py")

PASS = {"pass", "passed", "complete", "completed", "preserved", "validated", "improved", "within-approved-scope", "not-triggered", "not-needed"}


def directory(root: Path, run_id: str) -> Path: return LEDGER.state_dir(root.resolve(), run_id) / "debug" / "convergence"
def latest_path(root: Path, run_id: str) -> Path: return directory(root, run_id) / "harness-convergence-v1.json"


def _read(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def _latest(folder: Path, pattern: str) -> tuple[Path | None, dict[str, Any] | None]:
    paths = sorted(folder.glob(pattern)); return (paths[-1], _read(paths[-1])) if paths else (None, None)
def _rel(root: Path, path: Path | None) -> str | None: return path.relative_to(root).as_posix() if path else None


def selection(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve(); packet = CORRECTION.show(root, run_id)
    if packet.get("status") == "not-created":
        hypothesis = load("debug_convergence_hypothesis_preview", "debug-hypothesis.py").read_ledger(root, run_id)
        return {"schema_version":"1", "type":"tailtrail-debug-harness-selection-preview", "run_id":run_id,
            "requirement_uid":hypothesis.get("requirement_uid"), "status":"not-created",
            "lifecycle_classification":"not-yet-expected", "expected_after_stage":"d-09-regression-validation",
            "selected":[
                {"control":"Requirement Completion Harness","reason":"Every approved correction must satisfy its approved requirement."},
                {"control":"Evidence-Aware Testing","reason":"Every correction requires passing requirement-linked computational receipts."},
                {"control":"Drift Control","reason":"Every correction must compare actual paths with immutable correction scope."}],
            "conditional_controls":["Architecture Fitness Harness","Behaviour Harness","Maintainability Harness","Context Continuity Harness","Safe Git Recovery"],
            "reason":"Conditional Harness selection cannot be finalized until an approved correction defines paths, symbols, behavior scenarios, and recovery posture.",
            "next":"Prove a root cause and approve a bounded correction before convergence.",
            "boundary":"Read-only deterministic preview. No Harness, test, correction, or project command ran."}
    text = " ".join([packet.get("root_cause", {}).get("statement", ""), *packet.get("architecture_constraints", [])]).lower()
    selected = [
        {"control":"Requirement Completion Harness", "reason":"Every approved correction must satisfy its approved requirement."},
        {"control":"Evidence-Aware Testing", "reason":"Every correction requires passing requirement-linked computational receipts for its selected tiers."},
        {"control":"Drift Control", "reason":"Every correction must compare actual changed paths with immutable correction scope."},
    ]
    if packet.get("domain") in {"architecture","database","api-integration"} or packet.get("expected_changed_symbols") or len(packet.get("expected_changed_paths", [])) > 1:
        selected.append({"control":"Architecture Fitness Harness", "reason":"The correction crosses symbols, callers, layers, API/data boundaries, or multiple files."})
    if packet.get("behaviour_scenarios"):
        selected.append({"control":"Behaviour Harness", "reason":"The approved correction declares an externally observable behaviour scenario."})
    if any(term in text for term in ("refactor","duplicate","duplication","workaround","abstraction","scope growth")):
        selected.append({"control":"Maintainability Harness", "reason":"The correction concerns refactoring, duplication, workaround, abstraction, or scope growth."})
    hypothesis = load("debug_convergence_hypothesis", "debug-hypothesis.py").read_ledger(root, run_id)
    if int(hypothesis.get("cycle", 1)) > 1 or hypothesis.get("recovery_replan_ref"):
        selected.append({"control":"Context Continuity Harness", "reason":"The investigation entered a repeated or exhausted correction cycle."})
    recovery = packet.get("rollback_recovery_boundary", {})
    if recovery.get("mode") == "mode-b-task-scoped-recovery-required":
        selected.append({"control":"Safe Git Recovery", "reason":"Git readiness cannot support the primary clean-checkpoint mode."})
    return {"schema_version":"1", "type":"tailtrail-debug-harness-selection", "run_id":run_id, "requirement_uid":packet["requirement_uid"], "selected":selected, "boundary":"Deterministic selection only. It runs no Harness, test, scanner, Git, recovery, source, provider, or deployment action."}


def _result(control: str, status: str, artifact: str | None, evidence: list[str], reason: str) -> dict[str, Any]:
    return {"control":control, "status":status, "artifact":artifact, "evidence":evidence, "reason":reason}


def finalize(root: Path, run_id: str, approved: bool) -> dict[str, Any]:
    if not approved: raise ValueError("debug Harness convergence requires --approved")
    root = root.resolve(); packet = CORRECTION.show(root, run_id)
    if packet.get("status") != "approved": raise ValueError("Harness convergence requires an approved DI-7 correction")
    selected = selection(root, run_id); names = [row["control"] for row in selected["selected"]]; uid = packet["requirement_uid"]; changed = packet["expected_changed_paths"]
    events = EVIDENCE.show(root, run_id)["events"]; requirement_events = [row for row in events if uid in row.get("requirement_uids", [])]
    results: list[dict[str, Any]] = []

    scope_path, scope = _latest(CORRECTION.directory(root, run_id), "scope-check-v*.json")
    source = [row for row in requirement_events if row.get("kind") == "source-edit"]
    requirement_ok = bool(source and scope and scope.get("status") == "within-approved-scope")
    results.append(_result("Requirement Completion Harness", "pass" if requirement_ok else "required-evidence-missing", _rel(root, scope_path), [row.get("fingerprint") for row in source], "Approved source-edit evidence and in-scope comparison are required."))

    required_tiers = [str(item) for item in packet.get("validation_plan", {}).get("tiers", [])]
    aliases = {"focused":{"unit","focused"}, "integration":{"integration"}, "contract":{"contract"}, "e2e":{"e2e","system"}}
    missing = [tier for tier in required_tiers if not any(row.get("kind") in {"command-result","ci-receipt"} and row.get("outcome") == "pass" and row.get("tier") in aliases.get(tier, {tier}) for row in requirement_events)]
    testing_refs = [str(row.get("fingerprint")) for row in requirement_events if row.get("kind") in {"command-result","ci-receipt"} and row.get("outcome") == "pass"]
    results.append(_result("Evidence-Aware Testing", "pass" if not missing else "required-evidence-missing", None, testing_refs, "Missing required tiers: " + (", ".join(missing) if missing else "none")))

    drift_ok = bool(scope and scope.get("status") == "within-approved-scope" and not scope.get("unexpected_paths"))
    results.append(_result("Drift Control", "pass" if drift_ok else "drift-unresolved", _rel(root, scope_path), [str(scope.get("evidence_event_id"))] if scope else [], "Unexpected correction paths must be resolved before convergence."))

    if "Architecture Fitness Harness" in names:
        value = ARCHITECTURE.assess(root, run_id, changed); path, _ = _latest(LEDGER.state_dir(root, run_id) / "architecture", "assessment-*.json")
        results.append(_result("Architecture Fitness Harness", "pass" if value.get("complete") else "required-evidence-missing", _rel(root, path), [], "Existing deterministic Architecture Fitness assessment."))
    if "Behaviour Harness" in names:
        path, value = _latest(LEDGER.state_dir(root, run_id) / "behavior", "assessment-*.json")
        linked = bool(value and value.get("type") == "tailtrail-behavior-harness" and value.get("complete") and any(row.get("requirement_uid") == uid and row.get("state") == "validated" for row in value.get("scenarios", [])))
        results.append(_result("Behaviour Harness", "pass" if linked else "required-evidence-missing", _rel(root, path), [], "A typed validated scenario linked to this requirement is required; textual Harness labels are ignored."))
    if "Maintainability Harness" in names:
        value = MAINTAINABILITY.assess(root, run_id, changed); path, _ = _latest(LEDGER.state_dir(root, run_id) / "maintainability", "assessment-*.json")
        results.append(_result("Maintainability Harness", "pass" if value.get("complete") else "required-evidence-missing", _rel(root, path), [], "Existing deterministic Maintainability assessment and baseline rules."))
    if "Context Continuity Harness" in names:
        path, _ = _latest(LEDGER.state_dir(root, run_id) / "continuity", "state-*.json")
        results.append(_result("Context Continuity Harness", "pass" if path else "required-evidence-missing", _rel(root, path), [], "Repeated cycles require a saved continuity state."))
    if "Safe Git Recovery" in names:
        recovery = LEDGER.state_dir(root, run_id) / "recovery" / "boundary.json"
        results.append(_result("Safe Git Recovery", "pass" if recovery.is_file() else "required-evidence-missing", _rel(root, recovery) if recovery.is_file() else None, [], "Mode B requires the existing task-scoped recovery boundary."))

    complete = all(row["status"] in PASS for row in results)
    by_requirement = [{"requirement_uid":uid, "status":"complete" if complete else "evidence-incomplete", "controls":[{"control":row["control"], "status":row["status"]} for row in results]}]
    payload = {"schema_version":"1", "type":"tailtrail-debug-harness-convergence", "run_id":run_id, "workflow_id":packet["workflow_id"], "requirement_uid":uid, "selected_controls":selected["selected"], "control_results":results, "requirement_results":by_requirement, "complete":complete, "status":"pass" if complete else "evidence-incomplete", "next":"Continue to canonical debug closure." if complete else "Resolve only the listed missing selected-Harness evidence, then rerun convergence.", "boundary":"Typed local Harness convergence only. No arbitrary textual label can produce a pass. No test, source edit, recovery, Git, scanner, provider, publish, deployment, or closure acceptance was executed."}
    folder = directory(root, run_id); revision = len(list(folder.glob("harness-convergence-v*.json"))) + 1; archive = folder / f"harness-convergence-v{revision}.json"
    LEDGER.atomic_json(archive, payload); LEDGER.atomic_json(latest_path(root, run_id), payload); LEDGER.append_event(root, run_id, "debug_harness_converged", {"artifact":archive.relative_to(root).as_posix(), "status":payload["status"], "selected_controls":names})
    return {**payload, "artifact":archive.relative_to(root).as_posix()}


def show(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve(); path = latest_path(root, run_id)
    if not path.is_file(): return selection(root, run_id)
    return {**_read(path), "artifact":path.relative_to(root).as_posix()}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest="action",required=True)
    for action in ("select","finalize","show"):
        item=sub.add_parser(action); item.add_argument("--root",type=Path,default=Path.cwd()); item.add_argument("--run-id",required=True)
        if action=="finalize": item.add_argument("--approved",action="store_true")
    args=parser.parse_args()
    try:
        result=selection(args.root,args.run_id) if args.action=="select" else finalize(args.root,args.run_id,args.approved) if args.action=="finalize" else show(args.root,args.run_id)
        print(json.dumps(result,indent=2,sort_keys=True));return 0
    except (OSError,ValueError,KeyError,json.JSONDecodeError) as error: print(f"Debug Harness convergence error: {error}");return 2


if __name__=="__main__": raise SystemExit(main())
