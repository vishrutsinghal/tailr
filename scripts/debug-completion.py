#!/usr/bin/env python3
"""Generate the non-authoritative Debug Harness closure section.

Confidence state is derived only from structured, verifiable signals (an
approved reproduction contract, a proven hypothesis, an approved correction
packet, passing regression evidence) and is always capped at the domain's
confidence ceiling (DEBUG-HARNESS.md Section 7.5/8). Gaps are reported rather
than assumed away."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIDENCE_ORDER = [
    "symptom-captured", "reproduction-confirmed", "hypothesis-supported", "root-cause-proven",
    "correction-proposed", "correction-implemented", "regression-validated", "behavior-restored",
]
SUPPORTED_DOMAINS = {"code", "architecture", "database", "api-integration"}


def load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


L = load("debug_completion_ledger", "run-ledger.py")
INTAKE = load("debug_completion_intake", "debug-intake.py")
REPRODUCTION = load("debug_completion_reproduction", "debug-reproduction.py")
HYPOTHESIS = load("debug_completion_hypothesis", "debug-hypothesis.py")
CORRECTION = load("debug_completion_correction", "debug-correction.py")
EXECUTION_EVIDENCE = load("debug_completion_evidence", "execution-evidence.py")
CONVERGENCE = load("debug_completion_convergence", "debug-harness-convergence.py")
GOVERNANCE = load("debug_completion_governance", "debug-governance.py")


def report_path(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "debug" / "completion" / "debug-closure-section-v1.json"


def cap(state: str, ceiling: str) -> str:
    if CONFIDENCE_ORDER.index(state) > CONFIDENCE_ORDER.index(ceiling):
        return ceiling
    return state


def generate(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    intake_path = INTAKE.intake_path(root, run_id)
    if not intake_path.is_file():
        raise ValueError("no debug intake recorded for this run")
    intake = json.loads(intake_path.read_text(encoding="utf-8"))
    governance = GOVERNANCE.build(root, run_id)
    contract = REPRODUCTION.read_existing(root, run_id)
    ledger = HYPOTHESIS.read_ledger(root, run_id)
    packet_path = CORRECTION.packet_path(root, run_id)
    packet = json.loads(packet_path.read_text(encoding="utf-8")) if packet_path.is_file() else None

    gaps: list[str] = []
    state = "symptom-captured"
    if contract and contract.get("status") == "approved":
        state = "reproduction-confirmed"
    else:
        gaps.append("Reproduction contract is not approved.")

    proven = next((row for row in ledger["hypotheses"] if row["status"] == "proven"), None)
    if proven:
        state = "root-cause-proven"
    else:
        gaps.append("No hypothesis has been proven yet.")

    if packet:
        state = "correction-proposed"
    else:
        gaps.append("No correction packet has been proposed.")

    evidence_events = EXECUTION_EVIDENCE.show(root, run_id)["events"]
    source_paths = sorted({path for event in evidence_events if event.get("kind") == "source-edit" and packet and packet.get("requirement_uid") in event.get("requirement_uids", []) for path in event.get("changed_paths", [])})
    scope_checks = sorted((CORRECTION.directory(root, run_id)).glob("scope-check-v*.json")) if packet else []
    latest_scope = json.loads(scope_checks[-1].read_text(encoding="utf-8")) if scope_checks else None
    implemented = bool(packet and packet.get("status") == "approved" and source_paths and latest_scope and latest_scope.get("status") == "within-approved-scope" and not (set(source_paths) - set(packet.get("expected_changed_paths", []))))
    if packet and packet.get("status") == "approved":
        if implemented: state = "correction-implemented"
        else: gaps.append("Approved correction has no matching source-edit receipt and passing DI-7 scope comparison.")
    regression_pass = any(event["kind"] == "command-result" and event.get("outcome") == "pass" and event.get("tier") in {"integration", "system"} for event in evidence_events)
    if implemented:
        if regression_pass:
            state = "regression-validated"
        else:
            gaps.append("No passing integration/system command-result evidence recorded yet.")

    convergence_path = CONVERGENCE.latest_path(root, run_id)
    convergence = json.loads(convergence_path.read_text(encoding="utf-8")) if convergence_path.is_file() else None
    if not convergence or not convergence.get("complete"):
        gaps.append("Selected Debug Harness convergence is missing or evidence-incomplete.")
    behavior_result = next((row for row in (convergence or {}).get("control_results", []) if row.get("control") == "Behaviour Harness"), None)
    behavior_evidence = bool(behavior_result and behavior_result.get("status") == "pass")
    if state == "regression-validated":
        if behavior_evidence:
            state = "behavior-restored"
        else:
            gaps.append("No typed, requirement-linked Behaviour Harness pass confirms the user journey is restored.")

    ceiling = contract["max_achievable_confidence_state"] if contract else "symptom-captured"
    state = cap(state, ceiling)

    domains_investigated = sorted({row["domain"] for row in ledger["hypotheses"]})
    domains_eliminated = sorted({
        domain for domain in domains_investigated
        if all(row["status"] == "eliminated" for row in ledger["hypotheses"] if row["domain"] == domain)
    })
    domains_not_investigated = sorted((SUPPORTED_DOMAINS - set(domains_investigated)) | set(intake.get("domains_not_investigated", [])))

    debug_status = "pass" if (state == ceiling and packet and packet["status"] == "approved" and not gaps) else "evidence-incomplete"
    eliminated_competitors = [{"hypothesis_id": row["hypothesis_id"], "statement": row["statement"]} for row in ledger["hypotheses"] if row.get("status") == "eliminated"]
    controls = [
        {"control": "Symptom captured", "status": "pass", "evidence": intake_path.relative_to(root).as_posix(), "detail": str(intake.get("failure_fingerprint", intake.get("fingerprint", "sanitized intake")))},
        {"control": "Reproduction", "status": "pass" if contract and contract.get("status") == "approved" else "required-evidence-missing", "evidence": REPRODUCTION.approved_contract_path(root, run_id).relative_to(root).as_posix() if contract and contract.get("status") == "approved" else None, "detail": f"approved revision {contract.get('revision')}" if contract and contract.get("status") == "approved" else "approved reproduction revision required"},
        {"control": "Root cause", "status": "proven" if proven and eliminated_competitors else "required-evidence-missing", "evidence": proven.get("evidence_fingerprints", []) if proven else [], "detail": f"{len(eliminated_competitors)} competing hypothesis(es) eliminated"},
        {"control": "Correction", "status": "implemented" if implemented else "required-evidence-missing", "evidence": source_paths, "detail": "approved scope and matching source-edit receipts"},
        {"control": "Regression", "status": "pass" if regression_pass else "required-evidence-missing", "evidence": [row.get("fingerprint") for row in evidence_events if row.get("kind") == "command-result" and row.get("outcome") == "pass" and row.get("tier") in {"integration", "system"}], "detail": "requirement-linked integration/system computational evidence"},
        {"control": "Behaviour restored", "status": "pass" if behavior_evidence else "required-evidence-missing", "evidence": behavior_result.get("artifact") if behavior_result else None, "detail": "typed Behaviour Harness result; text labels are not accepted"},
        {"control": "Drift", "status": "none-unresolved" if latest_scope and latest_scope.get("status") == "within-approved-scope" and not latest_scope.get("unexpected_paths") else "unresolved", "evidence": scope_checks[-1].relative_to(root).as_posix() if scope_checks else None, "detail": "final correction-scope checkpoint"},
    ]

    report = {
        "schema_version": "1",
        "type": "tailtrail-debug-closure-section",
        "run_id": run_id,
        "requirement_uid": contract.get("requirement_uid") if contract else intake.get("requirement_uid"),
        "domain": contract["domain"] if contract else "unknown",
        "domain_confidence_ceiling": ceiling,
        "confidence_state": state,
        "root_cause_statement": proven["statement"] if proven else None,
        "correction_packet_ref": packet_path.relative_to(root).as_posix() if packet else None,
        "harness_convergence_ref": convergence_path.relative_to(root).as_posix() if convergence else None,
        "domains_investigated": domains_investigated,
        "domains_eliminated": domains_eliminated,
        "domains_not_investigated": domains_not_investigated,
        "debug_status": debug_status,
        "controls": controls,
        "eliminated_competitors": eliminated_competitors,
        "gaps": gaps,
        "governance": {"artifact": GOVERNANCE.artifact_path(root, run_id).relative_to(root).as_posix(), "privacy_status": governance["privacy"]["status"], "token_posture": governance["token_posture"], "continuity": governance["continuity"], "learning": governance["learning"]},
        "authority": "section-only",
        "boundary": "Debug confidence is domain-capped and distinct from delivery completion. Only the canonical TailTrail Completion Report may declare delivery complete or offer acceptance.",
    }
    L.atomic_json(report_path(root, run_id), report)
    L.append_event(root, run_id, "debug_closure_section_created", {"confidence_state": state, "debug_status": debug_status, "authority": "section-only"})
    return report


def show(root: Path, run_id: str) -> dict[str, Any]:
    path = report_path(root.resolve(), run_id)
    if not path.is_file():
        return {"schema_version":"1", "type":"tailtrail-debug-closure-status", "run_id":run_id,
            "status":"not-created", "lifecycle_classification":"not-yet-expected",
            "expected_after_stage":"d-10-closure",
            "reason":"Completion requires root-cause proof, correction posture, selected-Harness convergence, and governance evidence.",
            "next":"Continue the approved investigation; do not infer completion from planning or advisory evidence.",
            "boundary":"Read-only absence receipt. Delivery completion or acceptance was not inferred."}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    generate_parser = sub.add_parser("generate")
    generate_parser.add_argument("--root", type=Path, default=Path.cwd())
    generate_parser.add_argument("--run-id", required=True)
    show_parser = sub.add_parser("show")
    show_parser.add_argument("--root", type=Path, default=Path.cwd())
    show_parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        result = generate(args.root, args.run_id) if args.action == "generate" else show(args.root, args.run_id)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Debug completion error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
