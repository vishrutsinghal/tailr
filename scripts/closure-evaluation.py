#!/usr/bin/env python3
"""Calibrate closure outcomes with saved baseline evidence, never live model calls."""
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


L = load("closure_evaluation_ledger", "run-ledger.py")
REPORT = load("closure_evaluation_report", "completion-report.py")
SAN = load("closure_evaluation_official_sanitizer", "official-aidlc-sanitize.py")


def baseline(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("type") != "tailtrail-closure-baseline":
        raise ValueError("baseline must be a tailtrail-closure-baseline JSON object")
    counts = ("requirements_complete", "requirements_total", "unresolved_drift")
    if any(not isinstance(value.get(key), int) or isinstance(value.get(key), bool) or value[key] < 0 for key in counts):
        raise ValueError("baseline needs non-negative integer requirements_complete, requirements_total, and unresolved_drift")
    if value["requirements_complete"] > value["requirements_total"] or not isinstance(value.get("tests_pass"), bool):
        raise ValueError("baseline needs requirements_complete <= requirements_total and boolean tests_pass")
    return value


def evaluate(root: Path, run_id: str, baseline_path: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    report = REPORT.build(root, run_id, record=False)
    outcome = {
        "requirements_complete": report["requirement_status"]["complete"],
        "requirements_total": report["requirement_status"]["total"],
        "unresolved_drift": len(report["drift"]["findings"]),
        "tests_pass": report["tests"]["status"] == "pass",
        "overall_status": report["overall_status"],
    }
    source = None
    comparison = None
    if baseline_path:
        saved = baseline(baseline_path.resolve())
        source = baseline_path.name
        comparison = {
            "requirement_completion_delta": outcome["requirements_complete"] - saved["requirements_complete"],
            "unresolved_drift_delta": outcome["unresolved_drift"] - int(saved["unresolved_drift"]),
            "tests_pass_delta": int(outcome["tests_pass"]) - int(bool(saved["tests_pass"])),
        }
    key = {"run_id": run_id, "baseline": source, "outcome": outcome}
    evaluation_id = "evaluation-" + hashlib.sha256(json.dumps(key, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    directory = L.state_dir(root, run_id)
    path = directory / "closure-evaluations" / f"{evaluation_id}.json"
    if path.is_file():
        return {**json.loads(path.read_text(encoding="utf-8")), "reused": True}
    payload = {
        "schema_version": "1", "type": "tailtrail-closure-calibrated-evaluation", "evaluation_id": evaluation_id,
        "run_id": run_id, "evidence_label": "saved-local-artifacts", "mode": "paired" if baseline_path else "run-observation",
        "baseline": source, "tailtrail_outcome": outcome, "comparison": comparison,
        "boundary": "This deterministic report compares saved local artifacts only. It does not run a model, infer a baseline, or claim quality improvement from one run.",
    }
    SAN.validate_artifact(root, payload, "evaluation")
    L.atomic_json(path, payload)
    L.append_event(root, run_id, "closure_evaluation_calibrated", {"evaluation_id": evaluation_id, "artifact": path.relative_to(directory).as_posix(), "mode": payload["mode"]})
    return {**payload, "reused": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(evaluate(args.root, args.run_id, args.baseline), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Closure evaluation error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
