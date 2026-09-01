#!/usr/bin/env python3
"""Bridge one proven debug cause into a separately approved implementation slice.

DI-7 reuses TailTrail's immutable anchor, DWR approval ledger, requirement
impact mapper, Git readiness report, and Execution Evidence stream. It never
edits project source, runs validation, creates a dependency decision, commits,
pushes, deploys, or treats correction approval as implementation evidence.
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
sys.path.insert(0, str(ROOT / "scripts"))


def load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


L = load("debug_correction_ledger", "run-ledger.py")
HYPOTHESIS = load("debug_correction_hypothesis", "debug-hypothesis.py")
IMPACT = load("debug_correction_impact", "requirement-impact-map.py")
GIT = load("debug_correction_git", "git-readiness.py")
EVIDENCE = load("debug_correction_evidence", "execution-evidence.py")


def directory(root: Path, run_id: str) -> Path: return L.state_dir(root.resolve(), run_id) / "debug" / "correction"
def packet_path(root: Path, run_id: str) -> Path: return directory(root, run_id) / "correction-packet-v1.json"
def approved_path(root: Path, run_id: str) -> Path: return directory(root, run_id) / "approved-v1.json"
def handoff_path(root: Path, run_id: str) -> Path: return directory(root, run_id) / "implementation-handoff-v1.json"
def approved_anchor_path(root: Path, run_id: str) -> Path: return L.state_dir(root, run_id) / "anchors" / "approved-v1.json"


def _canonical(value: Any) -> str: return json.dumps(value, sort_keys=True, separators=(",", ":"))
def _fingerprint(value: Any) -> str: return "sha256:" + hashlib.sha256(_canonical(value).encode()).hexdigest()


def _safe_path(value: str) -> str:
    path = Path(value)
    if not value.strip() or path.is_absolute() or ".." in path.parts: raise ValueError("correction paths must be safe repository-relative paths")
    return path.as_posix()


def _read(path: Path, expected_type: str) -> dict[str, Any]:
    if not path.is_file(): raise ValueError(f"required correction artifact does not exist: {path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("type") != expected_type: raise ValueError(f"correction artifact has invalid type: {path.name}")
    return value


def _anchor(root: Path, run_id: str, uid: str) -> tuple[dict[str, Any], dict[str, Any]]:
    anchor = _read(approved_anchor_path(root, run_id), "tailtrail-change-intent-anchor")
    requirement = next((row for row in anchor.get("requirements", []) if row.get("requirement_uid") == uid), None)
    if not isinstance(requirement, dict): raise ValueError("proven hypothesis requirement is absent from the approved anchor")
    return anchor, requirement


def _workflow(root: Path, run_id: str) -> tuple[str, dict[str, Any]]:
    handoff = _read(L.state_dir(root, run_id) / "debug" / "investigation-handoff-v1.json", "tailtrail-debug-investigation-handoff")
    runtime = handoff.get("workflow_runtime", {}); workflow_id = str(runtime.get("workflow_id", "")).strip()
    if not workflow_id or runtime.get("compiler", {}).get("template_id") != "debug-investigation": raise ValueError("correction requires the native debug-investigation workflow")
    return workflow_id, handoff


def _source(path: Path | None) -> dict[str, Any]:
    if path is None: return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError("correction input must contain one JSON object")
    return value


def propose(root: Path, run_id: str, hypothesis_id: str, statement: str | None, source: dict[str, Any] | None = None) -> dict[str, Any]:
    root = root.resolve(); source = source or {}; ledger = HYPOTHESIS.read_ledger(root, run_id); row = HYPOTHESIS._find(ledger, hypothesis_id)
    if row["status"] != "proven": raise ValueError(f"hypothesis `{hypothesis_id}` is `{row['status']}`, not proven; prove root cause before proposing a correction")
    uid = str(ledger.get("requirement_uid") or HYPOTHESIS._requirement_uid(root, run_id)); anchor, requirement = _anchor(root, run_id, uid); workflow_id, _ = _workflow(root, run_id)
    expected_paths = sorted({_safe_path(str(item)) for item in source.get("expected_changed_paths", [])})
    expected_symbols = [{"path": _safe_path(str(item.get("path", ""))), "symbols": sorted({str(symbol) for symbol in item.get("symbols", []) if str(symbol).strip()})} for item in source.get("expected_changed_symbols", []) if isinstance(item, dict)]
    preserve = list(dict.fromkeys(str(item) for item in [*requirement.get("preserve_rules", []), *source.get("preserve_rules", [])] if str(item).strip()))
    architecture = list(dict.fromkeys(str(item) for item in source.get("architecture_constraints", ["Apply the correction at the existing owning boundary.", "Do not add a dependency or parallel abstraction without separate approval."]) if str(item).strip()))
    tiers = list(dict.fromkeys(str(item) for item in source.get("validation_tiers", ["focused", "integration"]) if str(item).strip()))
    scenarios = [str(item) for item in source.get("behaviour_scenarios", []) if str(item).strip()]
    assumptions = [str(item) for item in source.get("unresolved_assumptions", []) if str(item).strip()]
    if not expected_paths: assumptions.append("Expected changed paths have not been approved.")
    eliminated = [{"hypothesis_id": item["hypothesis_id"], "evidence": list(item.get("contradicting_evidence", []))} for item in ledger["hypotheses"] if item.get("status") == "eliminated"]
    recovery = GIT.readiness(root); impact = IMPACT.map_impact(root, run_id, expected_paths) if expected_paths else None
    stable = {"run_id":run_id, "workflow_id":workflow_id, "requirement_uid":uid, "hypothesis_id":hypothesis_id, "failure_fingerprint":ledger.get("failure_fingerprint"), "domain":row["domain"], "root_cause":{"hypothesis_id":hypothesis_id, "statement":statement or row["statement"], "supporting_evidence":list(row.get("supporting_evidence", [])), "eliminated_hypotheses":eliminated}, "approved_anchor_ref":approved_anchor_path(root, run_id).relative_to(root).as_posix(), "approved_anchor_fingerprint":anchor.get("approved_fingerprint"), "expected_changed_paths":expected_paths, "expected_changed_symbols":expected_symbols, "preserve_rules":preserve, "architecture_constraints":architecture, "validation_plan":{"tiers":tiers, "commands":[], "required_evidence":["source-edit-receipt", "requirement-linked command receipts", "scope comparison"]}, "behaviour_scenarios":scenarios, "rollback_recovery_boundary":{"git_ready":bool(recovery.get("ready")), "mode":"mode-a-local-checkpoint" if recovery.get("ready") else "mode-b-task-scoped-recovery-required", "readiness_issues":list(recovery.get("issues", [])), "separate_approval_required":True}, "impact_map_ref":Path(impact["path"]).resolve().relative_to(root).as_posix() if impact else None, "unresolved_assumptions":list(dict.fromkeys(assumptions)), "status":"proposed", "approved_at":None, "implementation_authority":None, "boundary":"Correction proposal only. No source edit, test, scanner, dependency, Git mutation, publish, or deployment occurred."}
    packet = {"schema_version":"2", "type":"tailtrail-debug-correction-packet", **stable, "correction_fingerprint":_fingerprint(stable)}
    L.atomic_json(packet_path(root, run_id), packet); L.append_event(root, run_id, "debug_correction_proposed", {"hypothesis_id":hypothesis_id, "requirement_uid":uid, "workflow_id":workflow_id, "expected_changed_paths":expected_paths, "correction_fingerprint":packet["correction_fingerprint"]}); return packet


def approve(root: Path, run_id: str, approved: bool) -> dict[str, Any]:
    if not approved: raise ValueError("approving a correction packet requires --approved")
    root = root.resolve(); path = packet_path(root, run_id); packet = _read(path, "tailtrail-debug-correction-packet")
    if approved_path(root, run_id).is_file(): return _read(approved_path(root, run_id), "tailtrail-debug-correction-packet")
    if packet.get("unresolved_assumptions"): raise ValueError("correction cannot grant implementation authority while assumptions are unresolved: " + "; ".join(packet["unresolved_assumptions"]))
    if not packet.get("expected_changed_paths") or not packet.get("validation_plan", {}).get("tiers"): raise ValueError("correction requires approved changed paths and validation tiers")
    from workflow_runtime import approvals
    decision = approvals.decide(root, packet["workflow_id"], stage_ids=["d-08-correction-implementation"], action_classes=["write_project"], operation_kind="fix-application", operation_ref=path.relative_to(root).as_posix(), decision="approved", rationale="Explicit approval of the exact DI-7 root cause, bounded file/symbol scope, preservation rules, architecture constraints, validation plan, and recovery boundary.")
    packet["status"] = "approved"; packet["approved_at"] = L.utc_now(); packet["implementation_authority"] = {"approval_id":decision["record"]["approval_id"], "stage_id":"d-08-correction-implementation", "action_class":"write_project", "operation_ref":path.relative_to(root).as_posix()}
    packet["correction_fingerprint"] = _fingerprint({key:value for key,value in packet.items() if key != "correction_fingerprint"}); L.atomic_json(path, packet); L.atomic_json(approved_path(root, run_id), packet)
    handoff = {"schema_version":"1", "type":"tailtrail-debug-implementation-handoff", "run_id":run_id, "workflow_id":packet["workflow_id"], "requirement_uid":packet["requirement_uid"], "correction_ref":approved_path(root, run_id).relative_to(root).as_posix(), "correction_fingerprint":packet["correction_fingerprint"], "implementation_authority":packet["implementation_authority"], "expected_changed_paths":packet["expected_changed_paths"], "expected_changed_symbols":packet["expected_changed_symbols"], "preserve_rules":packet["preserve_rules"], "architecture_constraints":packet["architecture_constraints"], "validation_plan":packet["validation_plan"], "behaviour_scenarios":packet["behaviour_scenarios"], "recovery_boundary":packet["rollback_recovery_boundary"], "next":"Acquire the workflow code-change reservation, apply only the approved correction, record source-edit receipts, then run scope-check before regression validation.", "boundary":"Scoped implementation authority only. It does not claim source edits, passing tests, Harness convergence, Git checkpoint creation, dependency approval, publish, deploy, or closure."}
    L.atomic_json(handoff_path(root, run_id), handoff); L.append_event(root, run_id, "debug_correction_approved", {"hypothesis_id":packet["hypothesis_id"], "workflow_id":packet["workflow_id"], "approval_id":packet["implementation_authority"]["approval_id"], "artifact":handoff_path(root, run_id).relative_to(root).as_posix()}); return {**packet, "execution_handoff": {**handoff, "artifact":handoff_path(root, run_id).relative_to(root).as_posix()}}


def scope_check(root: Path, run_id: str, changed: list[str], approved: bool) -> dict[str, Any]:
    if not approved: raise ValueError("scope comparison requires --approved because it records factual drift evidence")
    root = root.resolve(); packet = _read(approved_path(root, run_id), "tailtrail-debug-correction-packet"); actual = sorted({_safe_path(item) for item in changed}); expected = sorted(packet["expected_changed_paths"])
    unexpected = sorted(set(actual) - set(expected)); missing = sorted(set(expected) - set(actual)); status = "drift" if unexpected else "within-approved-scope"; classification = f"DI-7 scope {status}; unexpected={','.join(unexpected) or 'none'}; approved-not-changed={','.join(missing) or 'none'}"
    event = EVIDENCE.append(root, run_id, {"kind":"drift-finding" if unexpected else "harness-result", "requirement_uids":[packet["requirement_uid"]], "classification":classification}, True)
    payload = {"schema_version":"1", "type":"tailtrail-debug-correction-scope-check", "run_id":run_id, "workflow_id":packet["workflow_id"], "requirement_uid":packet["requirement_uid"], "correction_fingerprint":packet["correction_fingerprint"], "expected_changed_paths":expected, "actual_changed_paths":actual, "unexpected_paths":unexpected, "approved_paths_not_changed":missing, "status":status, "evidence_event_id":event["fingerprint"], "next":"Route unexpected paths through correction/replan before validation." if unexpected else "Record exact source-edit receipts and continue to regression validation.", "boundary":"Metadata comparison only. No file was edited, reverted, staged, committed, tested, published, or deployed."}
    destination = directory(root, run_id) / f"scope-check-v{len(list(directory(root, run_id).glob('scope-check-v*.json'))) + 1}.json"; L.atomic_json(destination, payload); return {**payload, "artifact":destination.relative_to(root).as_posix()}


def show(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve(); approved = approved_path(root, run_id); proposed = packet_path(root, run_id)
    path = approved if approved.is_file() else proposed
    if not path.is_file():
        return {"schema_version":"1", "type":"tailtrail-debug-correction-status", "run_id":run_id,
            "status":"not-created", "lifecycle_classification":"not-yet-expected",
            "expected_after_stage":"d-06-root-cause-proof",
            "reason":"A correction packet is created only after one hypothesis has formal supporting evidence and a competing hypothesis is eliminated.",
            "next":"Complete bounded reproduction and root-cause proof before proposing a correction.",
            "boundary":"Read-only absence receipt. No correction was proposed, approved, or implemented."}
    return _read(path, "tailtrail-debug-correction-packet")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="action", required=True)
    proposal = sub.add_parser("propose"); proposal.add_argument("--root", type=Path, default=Path.cwd()); proposal.add_argument("--run-id", required=True); proposal.add_argument("--hypothesis-id", required=True); proposal.add_argument("--statement"); proposal.add_argument("--input", type=Path)
    approval = sub.add_parser("approve"); approval.add_argument("--root", type=Path, default=Path.cwd()); approval.add_argument("--run-id", required=True); approval.add_argument("--approved", action="store_true")
    check = sub.add_parser("scope-check"); check.add_argument("--root", type=Path, default=Path.cwd()); check.add_argument("--run-id", required=True); check.add_argument("--changed", action="append", required=True); check.add_argument("--approved", action="store_true")
    display = sub.add_parser("show"); display.add_argument("--root", type=Path, default=Path.cwd()); display.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        if args.action == "propose": result = propose(args.root, args.run_id, args.hypothesis_id, args.statement, _source(args.input))
        elif args.action == "approve": result = approve(args.root, args.run_id, args.approved)
        elif args.action == "scope-check": result = scope_check(args.root, args.run_id, args.changed, args.approved)
        else: result = show(args.root, args.run_id)
        print(json.dumps(result, indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Debug correction error: {error}"); return 2


if __name__ == "__main__": raise SystemExit(main())
