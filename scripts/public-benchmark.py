#!/usr/bin/env python3
"""Offline public-evidence portfolio for TailTrail Release 5.

This tool scores only committed, sanitized fixture artifacts.  It never calls
a model or network service.  ``capture`` is deliberately opt-in: it records
hashes and supplied, sanitized telemetry from a real model run, never prompts,
source code, responses, credentials, or absolute paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIOS = ROOT / "benchmarks" / "public" / "scenarios"
DEFAULT_RUNS = ROOT / "benchmarks" / "results" / "model-runs"
FORBIDDEN_RECEIPT_KEYS = {
    "prompt", "response", "output", "source", "code", "repository",
    "repo", "path", "absolute_path", "api_key", "token", "secret",
}


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Invalid JSON: {path}: {error}") from error
    if not isinstance(value, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scenario_paths(root: Path, selected: str | None) -> list[Path]:
    paths = sorted(path for path in root.iterdir() if path.is_dir() and (path / "scenario.json").is_file())
    if selected:
        paths = [path for path in paths if path.name == selected]
        if not paths:
            raise SystemExit(f"Unknown public scenario: {selected}")
    return paths


def score_artifact(text: str, checks: list[dict[str, Any]]) -> tuple[int, int, list[dict[str, Any]]]:
    score = total = 0
    results: list[dict[str, Any]] = []
    lowered = text.lower()
    for check in checks:
        points = int(check.get("points", 1))
        total += points
        required = [item.lower() for item in check.get("contains_all", [])]
        prohibited = [item.lower() for item in check.get("must_not_contain_any", [])]
        passed = all(item in lowered for item in required) and not any(item in lowered for item in prohibited)
        if passed:
            score += points
        results.append({"id": check.get("id", "unnamed"), "passed": passed, "points": points})
    return score, total, results


def evaluate_scenario(path: Path) -> dict[str, Any]:
    scenario = read_json(path / "scenario.json")
    baseline = (path / "baseline-output.md").read_text(encoding="utf-8")
    tailtrail = (path / "tailtrail-output.md").read_text(encoding="utf-8")
    checks = scenario.get("checks", [])
    if not isinstance(checks, list):
        raise SystemExit(f"{path / 'scenario.json'} checks must be a list")
    baseline_checks = [check for check in checks if check.get("artifact") == "baseline"]
    tailtrail_checks = [check for check in checks if check.get("artifact", "tailtrail") == "tailtrail"]
    baseline_score, baseline_total, baseline_results = score_artifact(baseline, baseline_checks)
    tailtrail_score, tailtrail_total, tailtrail_results = score_artifact(tailtrail, tailtrail_checks)
    return {
        "id": scenario.get("id", path.name),
        "title": scenario.get("title", path.name),
        "category": scenario.get("category", "unspecified"),
        "evidence_label": "fixture-scored",
        "boundary": scenario.get("boundary", "sanitized deterministic artifact checks only"),
        "baseline": {"score": baseline_score, "total": baseline_total, "checks": baseline_results},
        "tailtrail": {"score": tailtrail_score, "total": tailtrail_total, "checks": tailtrail_results},
    }


def public_report(root: Path, selected: str | None) -> dict[str, Any]:
    scenarios = [evaluate_scenario(path) for path in scenario_paths(root, selected)]
    return {
        "type": "tailtrail-public-benchmark-report",
        "schema_version": "1",
        "model_calls": "not-run",
        "evidence_label": "fixture-scored",
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
    }


def render(report: dict[str, Any]) -> str:
    lines = ["# TailTrail Public Benchmark", "", "Evidence: **fixture-scored** — saved, sanitized artifacts; no model or network call.", "", "| Scenario | Baseline | TailTrail | Category |", "| --- | ---: | ---: | --- |"]
    for item in report["scenarios"]:
        lines.append(f"| {item['id']} | {item['baseline']['score']}/{item['baseline']['total']} | {item['tailtrail']['score']}/{item['tailtrail']['total']} | {item['category']} |")
    lines.extend(["", "Model-run evidence is recorded separately only through explicit, sanitized capture."])
    return "\n".join(lines)


def validate_receipt(value: dict[str, Any], scenario_id: str) -> None:
    if value.get("type") != "tailtrail-model-run-receipt" or value.get("schema_version") != "1":
        raise SystemExit("Receipt must be a tailtrail-model-run-receipt schema version 1")
    if value.get("scenario_id") != scenario_id:
        raise SystemExit("Receipt scenario_id must match --scenario")
    if value.get("sanitized") is not True or value.get("consent") != "approved":
        raise SystemExit("Receipt must set sanitized: true and consent: approved")
    if not isinstance(value.get("provider"), str) or not isinstance(value.get("model"), str):
        raise SystemExit("Receipt requires non-empty provider and model strings")
    forbidden: list[str] = []

    def find_forbidden(item: Any, location: str = "") -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                key_location = f"{location}.{key}" if location else key
                if key.lower() in FORBIDDEN_RECEIPT_KEYS:
                    forbidden.append(key_location)
                find_forbidden(nested, key_location)
        elif isinstance(item, list):
            for index, nested in enumerate(item):
                find_forbidden(nested, f"{location}[{index}]")

    find_forbidden(value)
    forbidden.sort()
    if forbidden:
        raise SystemExit("Receipt contains prohibited raw-data key(s): " + ", ".join(forbidden))


def capture(args: argparse.Namespace) -> int:
    if not args.approved:
        print("Refusing model-run capture without --approved. It writes a sanitized evidence record.")
        return 2
    scenario_dir = args.scenarios / args.scenario
    if not (scenario_dir / "scenario.json").is_file():
        raise SystemExit(f"Unknown public scenario: {args.scenario}")
    receipt = read_json(args.receipt)
    validate_receipt(receipt, args.scenario)
    baseline, tailtrail = args.baseline.resolve(), args.tailtrail.resolve()
    if not baseline.is_file() or not tailtrail.is_file():
        raise SystemExit("--baseline and --tailtrail must point to existing sanitized artifact files")
    telemetry = receipt.get("telemetry")
    measured = isinstance(telemetry, dict) and all(
        isinstance(telemetry.get(key), int) and telemetry[key] >= 0
        for key in ("baseline_total_tokens", "tailtrail_total_tokens")
    )
    record = {
        "type": "tailtrail-public-model-run",
        "schema_version": "1",
        "scenario_id": args.scenario,
        "provider": receipt["provider"],
        "model": receipt["model"],
        "recorded_at": receipt.get("recorded_at", "not-provided"),
        "evidence_label": "benchmark-measured" if measured else "model-run-unmeasured",
        "boundary": "Supplied sanitized receipt and SHA-256 artifact identities only; no raw prompt, response, repository, path, or secret is stored.",
        "artifact_sha256": {"baseline": sha256(baseline), "tailtrail": sha256(tailtrail)},
        "telemetry": telemetry if measured else {"status": "unavailable-or-incomplete"},
    }
    output = args.output or (DEFAULT_RUNS / f"{args.scenario}-{sha256(tailtrail)[:12]}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    return 0


def model_run_report(runs: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in sorted(runs.glob("*.json")) if runs.is_dir() else []:
        value = read_json(path)
        if value.get("type") != "tailtrail-public-model-run":
            continue
        records.append({
            "record": path.name,
            "scenario_id": value.get("scenario_id"),
            "provider": value.get("provider"),
            "model": value.get("model"),
            "evidence_label": value.get("evidence_label"),
            "recorded_at": value.get("recorded_at"),
        })
    return {
        "type": "tailtrail-public-model-run-report",
        "schema_version": "1",
        "record_count": len(records),
        "records": records,
        "boundary": "Lists saved provenance-only records; it does not recover or display source artifacts.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline TailTrail public benchmark and sanitized model-run capture.")
    parser.add_argument("action", choices=("list", "run", "capture", "report", "model-runs"))
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--scenario")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--tailtrail", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--runs", type=Path, default=DEFAULT_RUNS)
    parser.add_argument("--approved", action="store_true")
    args = parser.parse_args()
    if args.action == "capture":
        if not all((args.scenario, args.receipt, args.baseline, args.tailtrail)):
            parser.error("capture requires --scenario, --receipt, --baseline, and --tailtrail")
        return capture(args)
    if args.action == "model-runs":
        print(json.dumps(model_run_report(args.runs), indent=2))
        return 0
    report = public_report(args.scenarios, args.scenario)
    if args.action == "list":
        for item in report["scenarios"]:
            print(f"{item['id']}\t{item['category']}\tfixture-scored")
        return 0
    if args.action == "report" and args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2) if args.format == "json" else render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
