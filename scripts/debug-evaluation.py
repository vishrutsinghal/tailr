#!/usr/bin/env python3
"""Deterministic Debug Harness evaluation and fail-closed release gate."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "benchmarks" / "debug-harness" / "scenarios-v1.json"
HOSTS = ("codex", "copilot", "claude")
EXPECTED = {
    "code-reproducible-defect", "missed-caller-wrong-layer", "database-transaction-failure",
    "api-contract-mismatch", "repeated-inconclusive-experiment", "correction-scope-drift",
    "unit-pass-journey-broken", "sensitive-error-log", "pause-resume-debug-run",
    "approved-build-post-failure",
}


def load(relative: str, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


L = load("scripts/run-ledger.py", "debug_eval_ledger")
HOST = load("scripts/host-runtime-conformance.py", "debug_eval_host")


def read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError(f"{path.name} must contain a JSON object")
    return value


def contract() -> dict[str, Any]:
    value = read(CONTRACT); rows = value.get("scenarios")
    if value.get("type") != "tailtrail-debug-evaluation-scenarios" or value.get("scenario_version") != "v1":
        raise ValueError("Debug evaluation contract is incompatible")
    if not isinstance(rows, list) or {row.get("id") for row in rows if isinstance(row, dict)} != EXPECTED:
        raise ValueError("Debug evaluation contract must define the exact ten DI-12 scenarios")
    return value


def evaluate() -> dict[str, Any]:
    source = contract(); results = []
    totals = {"reproduced":0, "proven":0, "hypotheses":0, "false_hypotheses":0,
              "correction_cycles":0, "duplicates_blocked":0, "unresolved_drift":0,
              "evidence_required":0, "evidence_present":0, "false_routes":0,
              "review_seconds":0, "token_pairs":0, "token_absolute_error":0}
    for scenario in source["scenarios"]:
        observed = scenario.get("observations", {})
        required = ("routed_debug","reproduced","root_cause_proven","hypotheses_total","false_hypotheses",
                    "correction_cycles","duplicate_probe_blocked","unresolved_drift","evidence_required",
                    "evidence_present","review_seconds","estimated_tokens","actual_tokens")
        missing = [name for name in required if name not in observed]
        issues = (["missing observations: " + ", ".join(missing)] if missing else [])
        if observed.get("evidence_present", 0) > observed.get("evidence_required", 0): issues.append("evidence_present exceeds evidence_required")
        if scenario["id"] == "sensitive-error-log" and observed.get("sensitive_values_retained") != 0: issues.append("sensitive values were retained")
        expected_proof = scenario["id"] not in {"repeated-inconclusive-experiment", "sensitive-error-log"}
        if expected_proof and not observed.get("root_cause_proven"): issues.append("expected root cause proof is missing")
        if scenario["id"] == "repeated-inconclusive-experiment" and not observed.get("duplicate_probe_blocked"): issues.append("duplicate probe was not blocked")
        if scenario["id"] in {"correction-scope-drift", "unit-pass-journey-broken"} and observed.get("unresolved_drift", 0) < 1: issues.append("expected unresolved gap was hidden")
        results.append({"scenario_id":scenario["id"], "status":"passed" if not issues else "failed", "issues":issues,
                        "expected":scenario["expected"], "observations":observed})
        totals["reproduced"] += int(bool(observed.get("reproduced"))); totals["proven"] += int(bool(observed.get("root_cause_proven")))
        totals["hypotheses"] += int(observed.get("hypotheses_total",0)); totals["false_hypotheses"] += int(observed.get("false_hypotheses",0))
        totals["correction_cycles"] += int(observed.get("correction_cycles",0)); totals["duplicates_blocked"] += int(bool(observed.get("duplicate_probe_blocked")))
        totals["unresolved_drift"] += int(observed.get("unresolved_drift",0)); totals["evidence_required"] += int(observed.get("evidence_required",0))
        totals["evidence_present"] += int(observed.get("evidence_present",0)); totals["false_routes"] += int(not bool(observed.get("routed_debug")))
        totals["review_seconds"] += int(observed.get("review_seconds",0))
        if isinstance(observed.get("actual_tokens"), int):
            totals["token_pairs"] += 1; totals["token_absolute_error"] += abs(observed["estimated_tokens"] - observed["actual_tokens"])
    count = len(results)
    metrics = {
        "reproduction_success_rate": totals["reproduced"] / count,
        "proven_cause_rate": totals["proven"] / count,
        "false_hypothesis_rate": totals["false_hypotheses"] / totals["hypotheses"] if totals["hypotheses"] else None,
        "average_correction_cycles": totals["correction_cycles"] / count,
        "duplicate_experiment_preventions": totals["duplicates_blocked"],
        "unresolved_drift_findings": totals["unresolved_drift"],
        "false_debug_routes": totals["false_routes"],
        "average_fixture_review_seconds": totals["review_seconds"] / count,
        "evidence_completeness_rate": totals["evidence_present"] / totals["evidence_required"] if totals["evidence_required"] else None,
        "token_estimate_calibration": {"status":"measured" if totals["token_pairs"] else "unavailable", "paired_runs":totals["token_pairs"],
            "mean_absolute_error": totals["token_absolute_error"] / totals["token_pairs"] if totals["token_pairs"] else None},
    }
    return {"schema_version":"1","type":"tailtrail-debug-evaluation-report","scenario_version":"v1",
        "status":"passed" if all(row["status"] == "passed" for row in results) else "failed",
        "scenario_results":results,"metrics":metrics,"evidence_label":"deterministic-local-fixture",
        "claim_boundaries":[source["claim_boundary"],"Review-time values are fixture inputs, not measured developer-time savings.",
            "Token calibration is unavailable until exact host/provider telemetry is paired to a run."]}


def results_path(root: Path) -> Path:
    return root / ".tailtrail" / "evaluation" / "debug-harness" / "report-v1.json"


def run(root: Path, approved: bool) -> dict[str, Any]:
    result = evaluate(); result["artifact"] = None
    if approved:
        path = results_path(root.resolve()); L.atomic_json(path, {key:value for key,value in result.items() if key != "artifact"})
        result["artifact"] = path.relative_to(root.resolve()).as_posix()
    return result


def _latest_json(paths: list[Path]) -> dict[str, Any] | None:
    return read(paths[-1]) if paths else None


def vertical_status(root: Path, host: str) -> dict[str, Any]:
    evaluations = list((root / ".tailtrail" / "host-runtime" / "receipts" / host).glob("*/*/evaluation-v1.json"))
    candidates = []
    for path in evaluations:
        item = read(path)
        if item.get("evaluation") != "passed": continue
        run_id = str(item.get("run_id", "")); directory = root / ".tailtrail" / "runs" / run_id
        ledger = _latest_json(sorted((directory / "debug" / "hypotheses").glob("hypothesis-ledger.json")))
        convergence = _latest_json(sorted((directory / "debug" / "convergence").glob("*.json")))
        completion = _latest_json(sorted((directory / "completion-reports").glob("*.json")))
        decisions = [read(candidate) for candidate in (directory / "closure-decisions").glob("*.json")]
        probes = {
            "approved_reproduction": (directory / "debug" / "reproduction" / "approved-v1.json").is_file(),
            "project_orientation": any((directory / "debug" / "orientation").glob("*.json")),
            "proven_root_cause": bool(ledger and any(row.get("status") == "proven" for row in ledger.get("hypotheses", []))),
            "approved_correction": (directory / "debug" / "correction" / "approved-v1.json").is_file(),
            "harness_convergence": bool(convergence and convergence.get("status") == "pass"),
            "complete_report": bool(completion and completion.get("overall_status") == "complete"),
            "accepted": any(row.get("state") == "accepted" for row in decisions),
        }
        if all(probes.values()): candidates.append({"run_id":run_id,"host_evaluation":path.relative_to(root).as_posix(),"probes":probes})
    return {"status":"passed" if candidates else "not-validated", "validated_runs":candidates,
            "boundary":"Requires a passed host receipt linked to one accepted, evidence-complete Debug vertical run."}


def release_gate(root: Path) -> dict[str, Any]:
    root = root.resolve(); saved = read(results_path(root)) if results_path(root).is_file() else None
    host = HOST.report(root); runtime = {row["host"]:row["runtime_status"] for row in host["runtime_conformance"]}
    vertical = {name:vertical_status(root, name) for name in HOSTS}; reasons = []
    deterministic = saved.get("status") if saved else "missing"
    if deterministic != "passed": reasons.append("ten-scenario deterministic Debug evaluation has not passed and been saved")
    if host["instruction_conformance"]["status"] != "passed": reasons.append("host instruction conformance failed")
    for name in HOSTS:
        if runtime.get(name) != "passed": reasons.append(f"{name} runtime conformance is {runtime.get(name, 'not-validated')}")
        if vertical[name]["status"] != "passed": reasons.append(f"{name} has no accepted complete Debug vertical run")
    return {"schema_version":"1","type":"tailtrail-debug-release-gate","status":"passed" if not reasons else "blocked",
        "deterministic_evaluation":deterministic,"instruction_conformance":host["instruction_conformance"]["status"],
        "host_runtime_conformance":runtime,"debug_vertical_runs":{name:value["status"] for name,value in vertical.items()},
        "blocking_reasons":reasons,"boundary":"Fail-closed release decision. Local fixtures or generated host instructions never substitute for genuine linked runtime receipts and accepted Debug runs."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("catalog")
    run_parser = sub.add_parser("run"); run_parser.add_argument("--root", type=Path, default=Path.cwd()); run_parser.add_argument("--approved", action="store_true")
    report_parser = sub.add_parser("report"); report_parser.add_argument("--root", type=Path, default=Path.cwd())
    gate_parser = sub.add_parser("release-gate"); gate_parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        if args.action == "catalog": result = contract()
        elif args.action == "run": result = run(args.root, args.approved)
        elif args.action == "report": result = read(results_path(args.root.resolve())) if results_path(args.root.resolve()).is_file() else {"status":"missing","artifact":None}
        else: result = release_gate(args.root)
        print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result.get("status") not in {"failed"} else 1
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Debug evaluation error: {error}"); return 2


if __name__ == "__main__": raise SystemExit(main())
