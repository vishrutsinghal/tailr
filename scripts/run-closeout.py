#!/usr/bin/env python3
"""Chain the repeated per-run closure sequence into one command.

Every run closed this session repeated the same steps by hand: build a
closure-input JSON, closure-recorder.py, architecture-fitness.py, (sometimes)
behavior-harness.py with empty scenarios, closure-finalizer.py,
completion-report.py, delivery-record.py. This orchestrates the existing
scripts as subprocesses in that order -- it reimplements none of their logic,
so each step's own behavior and tests are unaffected.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def run(script: str, args: list[str]) -> tuple[int, str, str]:
    import subprocess

    result = subprocess.run(
        [PY, str(ROOT / "scripts" / script), *args], capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr


def step(label: str, script: str, args: list[str]) -> int:
    print(f"== {label} ==")
    code, out, err = run(script, args)
    if out:
        print(out)
    if code != 0:
        if err:
            print(err, file=sys.stderr)
        print(f"-- {label} failed (exit {code}); stopping the chain here.", file=sys.stderr)
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--changed", action="append", required=True, help="Repeatable. A changed path for this run.")
    parser.add_argument("--requirement-uid", action="append", required=True, help="Repeatable. A requirement_uid this proof covers.")
    parser.add_argument("--tier", action="append", default=["unit"], help="Repeatable. Defaults to unit.")
    parser.add_argument("--command-label", required=True)
    parser.add_argument("--command", required=True, help="The proof command actually run (for the record; not executed by this script).")
    parser.add_argument("--asserted", required=True, help="asserted_behavior text for the closure receipt.")
    parser.add_argument("--outcome", default="pass")
    parser.add_argument("--environment", default="local-macos-python3.12")
    parser.add_argument("--evidence-label", default="local-command")
    parser.add_argument("--skip-architecture-fitness", action="store_true")
    parser.add_argument("--skip-behavior", action="store_true")
    parser.add_argument("--scenarios", help="Path to a behavior-harness scenarios JSON; defaults to an empty {\"scenarios\": []}.")
    parser.add_argument("--evidence", help="Path to a behavior-harness evidence JSON; defaults to an empty {\"receipts\": []}.")
    args = parser.parse_args()

    closure_input = {
        "schema_version": "1",
        "type": "tailtrail-execution-closure-input",
        "run_id": args.run_id,
        "changed_paths": args.changed,
        "receipts": [
            {
                "requirement_uids": args.requirement_uid,
                "tiers": args.tier,
                "command_label": args.command_label,
                "command": args.command,
                "outcome": args.outcome,
                "environment": args.environment,
                "asserted_behavior": args.asserted,
                "evidence_label": args.evidence_label,
            }
        ],
    }

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_path = tmp_path / "closure-input.json"
        input_path.write_text(json.dumps(closure_input), encoding="utf-8")

        code = step(
            "closure-recorder",
            "closure-recorder.py",
            ["--root", args.root, "--run-id", args.run_id, "--input", str(input_path)],
        )
        if code != 0:
            return code

        if not args.skip_architecture_fitness:
            af_args = ["--root", args.root, "--run-id", args.run_id]
            for path in args.changed:
                af_args += ["--changed", path]
            code = step("architecture-fitness", "architecture-fitness.py", af_args)
            if code != 0:
                return code

        if not args.skip_behavior:
            scenarios_path = Path(args.scenarios) if args.scenarios else tmp_path / "scenarios.json"
            evidence_path = Path(args.evidence) if args.evidence else tmp_path / "evidence.json"
            if not args.scenarios:
                scenarios_path.write_text(json.dumps({"scenarios": []}), encoding="utf-8")
            if not args.evidence:
                evidence_path.write_text(json.dumps({"receipts": []}), encoding="utf-8")
            code = step(
                "behavior-harness",
                "behavior-harness.py",
                ["--root", args.root, "--run-id", args.run_id, "--scenarios", str(scenarios_path), "--evidence", str(evidence_path)],
            )
            if code != 0:
                return code

        code = step("closure-finalizer", "closure-finalizer.py", ["--root", args.root, "--run-id", args.run_id])
        if code != 0:
            return code

        code = step("completion-report", "completion-report.py", ["--root", args.root, "--run-id", args.run_id])
        if code != 0:
            return code

        code = step("delivery-record", "delivery-record.py", ["--root", args.root, "--run-id", args.run_id])
        if code != 0:
            return code

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
