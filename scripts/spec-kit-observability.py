#!/usr/bin/env python3
"""Create deterministic Spec Kit evaluation, governance, and advisory release artifacts."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def module(file: str, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


LEDGER = module("run-ledger.py", "spec_kit_observability_ledger")
CONVERGE = module("spec-kit-converge.py", "spec_kit_observability_converge")
METRICS = module("evidence-metrics.py", "spec_kit_observability_metrics")
RELEASE = module("release-confidence.py", "spec_kit_observability_release")


def read(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))


def latest(directory: Path, prefix: str) -> Path | None:
    rows: list[tuple[int, Path]] = []
    for path in directory.glob(f"{prefix}-*.json"):
        match = re.fullmatch(re.escape(prefix) + r"-(\d+)\.json", path.name)
        if match: rows.append((int(match.group(1)), path))
    return max(rows, default=(0, None))[1]


def receipts(root: Path, run_id: str) -> dict[str, Any]:
    records = [read(path) for path in sorted((LEDGER.state_dir(root, run_id) / "validation-receipts").glob("*.json"))]
    return {"receipts": records}


def governance(root: Path, run_id: str) -> dict[str, Any]:
    base = LEDGER.state_dir(root, run_id) / "spec-kit"; locks = sorted(base.glob("source-lock-v*.json")); issues: list[str] = []
    if not locks: issues.append("missing immutable source lock")
    else:
        lock = read(locks[-1])
        for key in ("snapshot", "import", "anchor"):
            value = lock.get(key)
            if not isinstance(value, str) or not (root / value).is_file(): issues.append(f"source lock reference is missing: {key}")
        if not str(lock.get("source_revision", "")).startswith("sha256:"): issues.append("source lock revision is not fingerprinted")
    raw_markers = ("raw_prompt", "source_code", "raw_log", "password", "secret")
    for path in [*locks, *base.glob("amendment-v*.json"), *base.glob("convergence-v*.json")]:
        if any(marker in path.read_text(encoding="utf-8").lower() for marker in raw_markers): issues.append(f"sanitization marker found in {path.name}")
    return {"status": "passed" if not issues else "failed", "issues": issues, "boundary": "Governance checks local TailTrail artifacts only; it does not inspect or alter raw Spec Kit source."}


def report(root: Path, run_id: str, baseline: Path | None = None) -> dict[str, Any]:
    root = root.resolve(); convergence = CONVERGE.converge(root, run_id); saved_receipts = receipts(root, run_id)
    receipt_path = LEDGER.state_dir(root, run_id) / "spec-kit" / "observability-receipts.json"; LEDGER.atomic_json(receipt_path, saved_receipts)
    metrics = METRICS.report(root, run_id, receipt_path); release = RELEASE.assess(root, run_id, receipt_path); events = LEDGER.read_events(LEDGER.state_dir(root, run_id) / "events.jsonl")
    requirement_rows = convergence["requirements"]; complete = sum(1 for row in requirement_rows if row["state"] == "complete"); total = len([row for row in requirement_rows if row["state"] != "superseded"])
    amendment_count = sum(1 for item in events if item["event_type"] == "spec_kit_amendment_proposed")
    correction_count = len(list((LEDGER.state_dir(root, run_id) / "spec-kit").glob("correction-v*.json")))
    approval_count = sum(1 for item in events if item["event_type"] in {"planning_lock_approved", "spec_kit_amendment_approved"})
    baseline_data = read(baseline) if baseline else None
    evaluation = {"mode": "saved-local-artifacts", "baseline": baseline_data, "tailtrail": {"requirements_complete": complete, "requirements_total": total, "unresolved_drift": len(convergence["unresolved_drift"]), "release_confidence_complete": release["confidence_complete"]}, "comparison": None, "boundary": "This is a deterministic artifact comparison, not a live-agent benchmark or causal quality claim."}
    if isinstance(baseline_data, dict):
        evaluation["comparison"] = {"requirement_completion_delta": complete - int(baseline_data.get("requirements_complete", 0)), "unresolved_drift_delta": len(convergence["unresolved_drift"]) - int(baseline_data.get("unresolved_drift", 0)), "boundary": "Deltas compare supplied saved artifacts only."}
    payload = {"schema_version": "1", "type": "tailtrail-spec-kit-observability", "run_id": run_id, "convergence": {"artifact": convergence["artifact"], "closure_state": convergence["closure_state"]}, "metrics": {"requirement_completion": {"complete": complete, "total": total, "ratio": complete / total if total else 1.0}, "spec_to_evidence_coverage": metrics["completeness_ratio"], "scope_drift": len(convergence["unresolved_drift"]), "amendment_frequency": amendment_count, "correction_cycles": correction_count, "approval_events": approval_count, "actual_model_tokens": "unavailable without host telemetry"}, "governance": governance(root, run_id), "release": {"state": "advisory-ready" if convergence["closure_state"] == "ready" and release["confidence_complete"] else "not-ready", "confidence": release, "boundary": "Advisory only; this artifact is not deployment authorization or CI merge policy."}, "evaluation": evaluation, "boundary": "No raw prompts, source, logs, identities, CI network calls, model calls, or unsupported quality/token claims are recorded."}
    directory = LEDGER.state_dir(root, run_id) / "spec-kit"; path = directory / f"observability-{len(list(directory.glob('observability-*.json'))) + 1}.json"; LEDGER.atomic_json(path, payload)
    LEDGER.append_event(root, run_id, "spec_kit_observability_recorded", {"artifact": path.relative_to(root).as_posix(), "release_state": payload["release"]["state"], "closure_state": convergence["closure_state"]})
    return {"artifact": path.relative_to(root).as_posix(), **payload}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("action", choices=("report", "release", "governance", "evaluate")); parser.add_argument("--root", type=Path, default=Path.cwd()); parser.add_argument("--run-id", required=True); parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    try:
        value = report(args.root, args.run_id, args.baseline)
        if args.action == "governance": value = {"run_id": args.run_id, "governance": value["governance"]}
        elif args.action == "release": value = {"run_id": args.run_id, "release": value["release"]}
        elif args.action == "evaluate": value = {"run_id": args.run_id, "evaluation": value["evaluation"]}
        print(json.dumps(value, indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, KeyError, StopIteration, json.JSONDecodeError) as error:
        print(f"Spec Kit observability error: {error}"); return 2


if __name__ == "__main__": raise SystemExit(main())
