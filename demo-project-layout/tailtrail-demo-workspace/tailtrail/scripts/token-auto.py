#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "scripts" / "route-context.py"
DEFAULT_STATE = ROOT / ".tailtrail" / "token-autopilot-state.json"


TRIVIAL_VERBS = {
    "rename",
    "format",
    "explain",
    "summarize",
    "spellcheck",
    "typo",
    "comment",
}

ROUTE_TRIGGERS = {
    "aidlc",
    "api",
    "authorization",
    "build",
    "ci",
    "config",
    "dependency",
    "diff",
    "error",
    "failing",
    "handoff",
    "implement",
    "integration",
    "lifecycle",
    "log",
    "mcp",
    "package",
    "privacy",
    "refactor",
    "review",
    "security",
    "stack trace",
    "test",
    "token",
    "validation",
}

HIGH_RISK_TRIGGERS = {
    "authorization",
    "auth",
    "config",
    "credential",
    "data",
    "dependency",
    "package",
    "privacy",
    "secret",
    "security",
    "token",
    "validation",
}


@dataclass(frozen=True)
class AutopilotDecision:
    action: str
    task_size: str
    route: dict[str, object] | None
    reason: str
    next_action: str
    prompt_words: int
    risk: str


def words(prompt: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_.:/-]+", prompt.lower())


def contains_any(prompt: str, triggers: set[str]) -> bool:
    lowered = prompt.lower()
    return any(trigger in lowered for trigger in triggers)


def estimate(prompt: str) -> tuple[str, str, bool, str]:
    prompt_words = words(prompt)
    word_count = len(prompt_words)
    has_route_trigger = contains_any(prompt, ROUTE_TRIGGERS)
    high_risk = contains_any(prompt, HIGH_RISK_TRIGGERS)
    has_file_hint = any("/" in word or "." in word for word in prompt_words)

    if word_count <= 5 and not has_route_trigger and not high_risk:
        return "tiny", "low", False, "Prompt is tiny and has no route or risk trigger."

    if word_count <= 9 and prompt_words and prompt_words[0] in TRIVIAL_VERBS and not high_risk:
        return "small", "low", False, "Prompt looks like a small local action; routing would cost more than it saves."

    if high_risk:
        return "risk-aware", "high", True, "Prompt touches risk-sensitive material that needs exact handling."

    if has_route_trigger:
        return "routed", "medium", True, "Prompt contains routing triggers for review, logs, lifecycle, dependencies, or implementation."

    if word_count >= 18 or has_file_hint:
        return "routed", "medium", True, "Prompt has enough scope or file hints to benefit from context routing."

    return "small", "low", False, "Prompt appears small enough to answer without TailTrail context routing."


def router_decision(prompt: str) -> dict[str, object]:
    command = [sys.executable, str(ROUTER), "auto", *prompt.split(), "--format", "json", "--no-state"]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "route-context.py failed")
    return json.loads(result.stdout)


def decide(prompt: str) -> AutopilotDecision:
    task_size, risk, should_route, reason = estimate(prompt)
    prompt_word_count = len(words(prompt))
    if not should_route:
        return AutopilotDecision(
            action="skip",
            task_size=task_size,
            route=None,
            reason=reason,
            next_action="Do not load TailTrail docs. Use only exact user-provided context and directly relevant files.",
            prompt_words=prompt_word_count,
            risk=risk,
        )

    route = router_decision(prompt)
    return AutopilotDecision(
        action="route",
        task_size=task_size,
        route=route,
        reason=reason,
        next_action="Load only the selected route context and exact task material.",
        prompt_words=prompt_word_count,
        risk=risk,
    )


def decision_payload(decision: AutopilotDecision, prompt: str) -> dict[str, object]:
    return {
        "action": decision.action,
        "task_size": decision.task_size,
        "risk": decision.risk,
        "prompt_words": decision.prompt_words,
        "reason": decision.reason,
        "next_action": decision.next_action,
        "route": decision.route,
        "prompt": prompt,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_state(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def print_markdown(payload: dict[str, object]) -> None:
    print("# TailTrail Token Autopilot")
    print()
    print(f"- Action: `{payload['action']}`")
    print(f"- Task size: `{payload['task_size']}`")
    print(f"- Risk: `{payload['risk']}`")
    print(f"- Prompt words: `{payload['prompt_words']}`")
    print(f"- Reason: {payload['reason']}")
    print(f"- Next action: {payload['next_action']}")

    route = payload.get("route")
    if not isinstance(route, dict):
        return

    print()
    print(f"Route: `{route['name']}`")
    print(f"Lane: `{route['lane']}`")
    print(f"Slice: `{route['slice']}`")
    print(f"Exactness risk: `{route['exactness_risk']}`")
    print()
    print("Load only:")
    for item in route["load"]:
        print(f"- {item}")
    print()
    print("Avoid:")
    for item in route["avoid"]:
        print(f"- {item}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Automatically decide whether TailTrail token routing is worth using.")
    parser.add_argument("prompt", nargs="*", help="User prompt or task text.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format.")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE, help="State file path.")
    parser.add_argument("--no-state", action="store_true", help="Do not write autopilot state.")
    args = parser.parse_args()

    prompt = " ".join(args.prompt).strip()
    decision = decide(prompt)
    payload = decision_payload(decision, prompt)

    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        print_markdown(payload)

    if not args.no_state:
        write_state(args.state, payload)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
