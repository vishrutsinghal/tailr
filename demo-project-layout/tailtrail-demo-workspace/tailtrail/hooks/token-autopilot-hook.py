#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTOPILOT = ROOT / "scripts" / "token-auto.py"


def main() -> int:
    parser = argparse.ArgumentParser(description="Print automatic TailTrail token-saving context for hook-capable hosts.")
    parser.add_argument("prompt", nargs="*", help="Prompt text to classify.")
    parser.add_argument("--no-state", action="store_true", help="Do not update autopilot state.")
    args = parser.parse_args()

    command = [sys.executable, str(AUTOPILOT), *args.prompt, "--format", "json"]
    if args.no_state:
        command.append("--no-state")

    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode

    decision = json.loads(result.stdout)
    print("TailTrail Token Autopilot")
    print("=========================")
    print(f"Action: {decision['action']}")
    print(f"Task size: {decision['task_size']}")
    print(f"Risk: {decision['risk']}")
    print(f"Reason: {decision['reason']}")
    print(f"Next action: {decision['next_action']}")

    route = decision.get("route")
    if isinstance(route, dict):
        print()
        print(f"Route: {route['name']}")
        print(f"Lane: {route['lane']}")
        print(f"Slice: {route['slice']}")
        print("Load only:")
        for item in route["load"]:
            print(f"- {item}")
        print("Avoid:")
        for item in route["avoid"]:
            print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
