#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPAND_INTENT = ROOT / "scripts" / "expand-intent.py"
TOKEN_AUTO = ROOT / "scripts" / "token-auto.py"
DEFAULT_STATE = ROOT / ".tailtrail" / "lifecycle-hook-state.json"

SHORT_COMMANDS = [
    "use TailTrail",
    "use review",
    "use AIDLC",
    "use AIDLC and review",
    "use dependency gate",
    "use handoff",
    "use QA review",
    "use CI Sonar",
    "use release flow",
    "save tokens",
]


def run_json(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or f"{command[0]} failed")
    return json.loads(result.stdout)


def expand_intent(prompt: str) -> dict[str, Any]:
    return run_json([sys.executable, str(EXPAND_INTENT), prompt, "--format", "json"])


def token_decision(prompt: str) -> dict[str, Any]:
    return run_json([sys.executable, str(TOKEN_AUTO), prompt, "--format", "json", "--no-state"])


def startup_payload() -> dict[str, Any]:
    return {
        "kind": "startup",
        "message": "TailTrail is available. Use short commands instead of long workflow prompts.",
        "short_commands": SHORT_COMMANDS,
        "quiet_rule": "Inject this reminder only on explicit startup or host-managed first use.",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def prompt_payload(prompt: str) -> dict[str, Any]:
    return {
        "kind": "prompt",
        "prompt": prompt,
        "flow": expand_intent(prompt),
        "token_autopilot": token_decision(prompt),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def print_startup(payload: dict[str, Any]) -> None:
    print("# TailTrail Lifecycle Hook")
    print()
    print(payload["message"])
    print()
    print("Short commands:")
    for command in payload["short_commands"]:
        print(f"- {command}")
    print()
    print(f"Quiet rule: {payload['quiet_rule']}")


def print_prompt(payload: dict[str, Any]) -> None:
    flow = payload["flow"]
    autopilot = payload["token_autopilot"]
    seen_avoid: set[str] = set()

    print("# TailTrail Lifecycle Hook")
    print()
    print(f"- Flow: `{flow['name']}`")
    print(f"- Token action: `{autopilot['action']}`")
    print(f"- Risk: `{autopilot['risk']}`")
    print(f"- Reason: {autopilot['reason']}")
    print()
    print("Expanded prompt:")
    print(flow["prompt"])
    print()
    print("Run order:")
    for item in flow["run_order"]:
        print(f"- {item}")

    if autopilot["action"] == "skip":
        print()
        print(f"Context: {autopilot['next_action']}")
        print()
        print("Validation:")
        for item in flow["validation"]:
            print(f"- {item}")
        return

    print()
    print("Load only:")
    for item in flow["load"]:
        print(f"- {item}")

    route = autopilot.get("route")
    if isinstance(route, dict):
        print()
        print(f"Token route: `{route['name']}` / `{route['lane']}` / `{route['slice']}`")
        for item in route["load"]:
            print(f"- {item}")

    print()
    print("Avoid:")
    for item in flow["avoid"]:
        seen_avoid.add(item)
        print(f"- {item}")
    if isinstance(route, dict):
        for item in route["avoid"]:
            if item not in seen_avoid:
                print(f"- {item}")
                seen_avoid.add(item)
    print()
    print("Validation:")
    for item in flow["validation"]:
        print(f"- {item}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Print compact TailTrail lifecycle context for hook-capable hosts.")
    parser.add_argument("prompt", nargs="*", help="Short user prompt or TailTrail command.")
    parser.add_argument("--startup", action="store_true", help="Print a quiet startup reminder instead of prompt guidance.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format.")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE, help="State file path.")
    parser.add_argument("--no-state", action="store_true", help="Do not write lifecycle hook state.")
    args = parser.parse_args()

    prompt = " ".join(args.prompt).strip()
    payload = startup_payload() if args.startup or not prompt else prompt_payload(prompt)

    if args.format == "json":
        print(json.dumps(payload, indent=2))
    elif payload["kind"] == "startup":
        print_startup(payload)
    else:
        print_prompt(payload)

    if not args.no_state:
        write_state(args.state, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
