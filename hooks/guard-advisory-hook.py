#!/usr/bin/env python3
"""Show non-blocking local TailTrail guard and dependency-decision guidance."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_json(command: list[str]) -> dict:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"status": "unavailable", "detail": (result.stderr or result.stdout).strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--diff", type=Path)
    parser.add_argument("--write-state", action="store_true", help="Write the advisory receipt under .tailtrail only when explicitly requested.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    root = args.root.resolve()
    common = ["--root", root.as_posix(), "--format", "json"]
    if args.diff:
        common.extend(["--diff", args.diff.resolve().as_posix()])
    guard = run_json([sys.executable, str(ROOT / "scripts" / "guardrail-check.py"), *common])
    dependency = run_json([sys.executable, str(ROOT / "scripts" / "dependency-decision.py"), "check", *common])
    unavailable = guard.get("status") == "unavailable" or dependency.get("status") == "unavailable"
    attention = bool(guard.get("finding_count")) or dependency.get("status") == "failed"
    payload = {"type": "tailtrail-guard-advisory-hook", "status": "attention" if attention else "unavailable" if unavailable else "clear", "guard": guard, "dependency_decisions": dependency, "advisory": True, "boundary": "This hook is informational only: it never blocks, edits source, stages files, installs dependencies, commits, or pushes.", "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    if args.write_state:
        path = root / ".tailtrail" / "guard-advisory.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        payload["state"] = path.relative_to(root).as_posix()
    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        print("# TailTrail Guard Advisory\n")
        print(f"- Status: `{payload['status']}`")
        print(f"- Guard findings: {guard.get('finding_count', 'unavailable')}")
        print(f"- Dependency decisions: `{dependency.get('status', 'unavailable')}`")
        print(f"- Advisory: {payload['boundary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
