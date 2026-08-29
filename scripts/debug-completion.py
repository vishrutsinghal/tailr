#!/usr/bin/env python3
"""Generate the Debug Harness Completion Report.

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


def report_path(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "debug" / "completion" / "debug-completion-report-v1.json"


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
        state = "correction-implemented" if packet["status"] == "approved" else "correction-proposed"
    else:
        gaps.append("No correction packet has been proposed.")

    evidence_events = EXECUTION_EVIDENCE.show(root, run_id)["events"]
    regression_pass = any(event["kind"] == "command-result" and event.get("outcome") == "pass" and event.get("tier") in {"integration", "system"} for event in evidence_events)
    if packet and packet["status"] == "approved":
        if regression_pass:
            state = "regression-validated"
        else:
            gaps.append("No passing integration/system command-result evidence recorded yet.")

    behavior_evidence = any(event["kind"] == "harness-result" and "restored" in event.get("classification", "").lower() for event in evidence_events)
    if state == "regression-validated":
        if behavior_evidence:
            state = "behavior-restored"
        else:
            gaps.append("No harness-result evidence recorded confirming the user journey is restored.")

    ceiling = contract["max_achievable_confidence_state"] if contract else "symptom-captured"
    state = cap(state, ceiling)

    domains_investigated = sorted({row["domain"] for row in ledger["hypotheses"]})
    domains_eliminated = sorted({
        domain for domain in domains_investigated
        if all(row["status"] == "eliminated" for row in ledger["hypotheses"] if row["domain"] == domain)
    })
    domains_not_investigated = sorted((SUPPORTED_DOMAINS - set(domains_investigated)) | set(intake.get("domains_not_investigated", [])))

    acceptance_state = "accept-user" if (state == ceiling and packet and packet["status"] == "approved" and not gaps) else "evidence-incomplete"

    report = {
        "schema_version": "1",
        "type": "tailtrail-debug-completion-report",
        "run_id": run_id,
        "domain": contract["domain"] if contract else "unknown",
        "domain_confidence_ceiling": ceiling,
        "confidence_state": state,
        "root_cause_statement": proven["statement"] if proven else None,
        "correction_packet_ref": packet_path.relative_to(root).as_posix() if packet else None,
        "domains_investigated": domains_investigated,
        "domains_eliminated": domains_eliminated,
        "domains_not_investigated": domains_not_investigated,
        "acceptance_state": acceptance_state,
        "gaps": gaps,
    }
    L.atomic_json(report_path(root, run_id), report)
    L.append_event(root, run_id, "debug_completion_report_created", {"confidence_state": state, "acceptance_state": acceptance_state})
    return report


def show(root: Path, run_id: str) -> dict[str, Any]:
    path = report_path(root.resolve(), run_id)
    if not path.is_file():
        raise ValueError("no debug completion report has been generated for this run")
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
