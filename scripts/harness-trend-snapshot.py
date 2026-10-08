#!/usr/bin/env python3
"""Run the existing Evaluation Harness and Debug Harness self-tests and emit
one combined, timestamped JSON snapshot -- so harness health can be tracked
as a trend over time (e.g. as a CI artifact per run) instead of only being
visible as a one-off "latest" result after someone happens to run it by hand.

This intentionally does not call any model and does not write anything back
into the repository; it only reads existing committed fixtures and prints a
JSON report to stdout (or to --output, if given).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_json(args: list[str]) -> dict:
    result = subprocess.run(
        [sys.executable, *args], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def evaluation_harness_snapshot() -> dict:
    listing = run_json(["scripts/evaluation-harness.py", "scenario", "list", "--format", "json"])
    scenarios = []
    for entry in listing.get("scenarios", []):
        scenario_id = entry["scenario_id"]
        report = run_json(
            ["scripts/evaluation-harness.py", "scenario", "report", "--scenario", scenario_id, "--format", "json"]
        )
        scenarios.append(
            {
                "scenario_id": scenario_id,
                "title": entry.get("title"),
                "winner_score": report.get("event", {}).get("scores", {}).get("winner_score"),
                "delta_from_baseline": report.get("delta_from_baseline"),
            }
        )
    return {"scenario_count": len(scenarios), "scenarios": scenarios}


def debug_harness_snapshot() -> dict:
    result = run_json(["scripts/debug-evaluation.py", "run", "--root", "."])
    return {"metrics": result.get("metrics"), "evidence_label": result.get("evidence_label")}


def git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None, help="Write JSON here instead of stdout.")
    args = parser.parse_args()

    snapshot = {
        "schema_version": "1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha(),
        "evaluation_harness": evaluation_harness_snapshot(),
        "debug_harness": debug_harness_snapshot(),
        "claim_boundary": (
            "Deterministic fixture-based self-checks of TailTrail's own harness "
            "tooling. Not live-model evidence, not a measure of code quality on "
            "a real task."
        ),
    }

    text = json.dumps(snapshot, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
