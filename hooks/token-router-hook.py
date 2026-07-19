#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "scripts" / "route-context.py"


def main() -> int:
    parser = argparse.ArgumentParser(description="Print a compact TailTrail context injection for hook-capable hosts.")
    parser.add_argument("route", nargs="?", default="auto", help="Route name or 'auto'.")
    parser.add_argument("prompt", nargs="*", help="Optional prompt text for auto routing.")
    parser.add_argument("--no-state", action="store_true", help="Do not update router state.")
    args = parser.parse_args()

    command = [sys.executable, str(ROUTER), args.route, *args.prompt, "--format", "json"]
    if args.no_state:
        command.append("--no-state")

    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode

    decision = json.loads(result.stdout)
    print("TailTrail context injection")
    print("==========================")
    print(f"Route: {decision['name']}")
    print(f"Lane: {decision['lane']}")
    print(f"Slice: {decision['slice']}")
    print(f"Exactness risk: {decision['exactness_risk']}")
    print(f"Exact text required: {str(decision['exact_text']).lower()}")
    print()
    print("Load only:")
    for item in decision["load"]:
        print(f"- {item}")
    print()
    print("Avoid:")
    for item in decision["avoid"]:
        print(f"- {item}")
    print()
    print(f"Fallback: {decision['fallback']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
