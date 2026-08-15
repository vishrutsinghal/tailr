#!/usr/bin/env python3
"""Fail a CI job only when saved Spec Kit closure evidence is incomplete."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def module(file: str, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


OBSERVE = module("spec-kit-observability.py", "spec_kit_ci_gate_observe")


def evaluate(root: Path, run_id: str) -> dict[str, Any]:
    report = OBSERVE.report(root.resolve(), run_id)
    passed = report["convergence"]["closure_state"] == "ready" and report["governance"]["status"] == "passed" and report["release"]["state"] == "advisory-ready"
    return {"schema_version": "1", "type": "tailtrail-spec-kit-ci-gate", "run_id": run_id, "status": "passed" if passed else "failed", "convergence": report["convergence"], "governance": report["governance"]["status"], "release": report["release"]["state"], "artifact": report["artifact"], "boundary": "This gate evaluates saved local TailTrail/CI receipts. A CI workflow may use its exit code as policy, but TailTrail does not merge, deploy, or contact CI providers."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--root", type=Path, default=Path.cwd()); parser.add_argument("--run-id", required=True); parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()
    try:
        result = evaluate(args.root, args.run_id)
        if args.format == "json": print(json.dumps(result, indent=2, sort_keys=True))
        else: print(f"Spec Kit CI gate: {result['status']}\nConvergence: {result['convergence']['closure_state']}\nGovernance: {result['governance']}\nRelease: {result['release']}")
        return 0 if result["status"] == "passed" else 1
    except (OSError, ValueError, KeyError, StopIteration, json.JSONDecodeError) as error:
        print(f"Spec Kit CI gate error: {error}"); return 2


if __name__ == "__main__": raise SystemExit(main())
