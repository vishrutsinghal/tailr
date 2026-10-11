#!/usr/bin/env python3
"""Prompt-builder loop contract: simple options, 5-round cap, fail-closed feedback.

Hosts propose grounded prompt options; users approve. This module owns the
rendering shape (so it survives sessions) and the stop rule:

- Options render numbered, one idea per numbered block, blank lines between,
  plain words, approval question always last.
- At most MAX_CLARIFICATION_ROUNDS clarification rounds. Past that, stop with
  a feedback packet -- what stayed ambiguous, what was tried, what to supply,
  how to resume. Never a silent stop.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

MAX_CLARIFICATION_ROUNDS = 5

APPROVAL_FOOTER = "Reply with the option number, or describe your own in one short sentence."


def render_prompt_options(question: str, options: list[str], footer: str = APPROVAL_FOOTER) -> str:
    """Render numbered prompt options with blank-line breaks.

    Raises ValueError on empty question, fewer than 2 options, or an option
    containing a blank line (one idea per block keeps it scannable).
    """
    clean_question = " ".join(str(question).split())
    if not clean_question:
        raise ValueError("prompt options need a non-empty question")
    clean_options = [" ".join(str(item).split()) for item in options if str(item).strip()]
    if len(clean_options) < 2:
        raise ValueError("prompt options need at least two non-empty options")
    for item in clean_options:
        if "\n" in item:
            raise ValueError("each option must be one block (no internal blank lines)")
    lines = [clean_question, ""]
    for index, item in enumerate(clean_options, start=1):
        lines.append(f"{index}. {item}")
        lines.append("")
    lines.append(" ".join(str(footer).split()))
    return "\n".join(lines)


def should_stop(rounds_completed: int) -> bool:
    """True once the clarification budget is spent."""
    return int(rounds_completed) >= MAX_CLARIFICATION_ROUNDS


def feedback_packet(
    goal: str,
    rounds_completed: int,
    ambiguities: list[str],
    tried: list[str] | None = None,
    resume_hint: str = "",
) -> dict[str, Any]:
    """Build the fail-closed packet shown when ambiguity survives all rounds."""
    clean_goal = " ".join(str(goal).split()) or "(no goal recorded)"
    clean_ambiguities = [" ".join(str(item).split()) for item in ambiguities if str(item).strip()]
    clean_tried = [" ".join(str(item).split()) for item in (tried or []) if str(item).strip()]
    lines = [
        f"I could not resolve your prompt after {MAX_CLARIFICATION_ROUNDS} rounds, so I stopped instead of guessing.",
        "",
        f"Goal: {clean_goal}",
        "",
        "Still ambiguous:",
        "",
    ]
    if clean_ambiguities:
        for index, item in enumerate(clean_ambiguities, start=1):
            lines.append(f"{index}. {item}")
            lines.append("")
    else:
        lines.append("1. (no specific ambiguity recorded)")
        lines.append("")
    if clean_tried:
        lines.append("What I tried:")
        lines.append("")
        for index, item in enumerate(clean_tried, start=1):
            lines.append(f"{index}. {item}")
            lines.append("")
    lines.append("To continue, please supply one short sentence per ambiguous point above.")
    lines.append("")
    resume = " ".join(str(resume_hint).split()) or 'Revise the goal with exact words, then run: tailtrail start "<revised goal>"'
    lines.append(resume)
    return {
        "type": "tailtrail-prompt-builder-feedback",
        "goal": clean_goal,
        "rounds_completed": int(rounds_completed),
        "round_cap": MAX_CLARIFICATION_ROUNDS,
        "ambiguities": clean_ambiguities,
        "tried": clean_tried,
        "message": "\n".join(lines),
        "next": resume,
        "boundary": "Fail-closed: no run was created from an ambiguous prompt.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    render = sub.add_parser("render", help="Render numbered prompt options.")
    render.add_argument("--question", required=True)
    render.add_argument("--option", action="append", default=[], dest="options")
    feedback = sub.add_parser("feedback", help="Build the fail-closed packet after 5 unclear rounds.")
    feedback.add_argument("--goal", required=True)
    feedback.add_argument("--rounds", type=int, default=MAX_CLARIFICATION_ROUNDS)
    feedback.add_argument("--ambiguity", action="append", default=[], dest="ambiguities")
    feedback.add_argument("--tried", action="append", default=[], dest="tried")
    feedback.add_argument("--resume-hint", default="")
    args = parser.parse_args()
    try:
        if args.command == "render":
            print(render_prompt_options(args.question, args.options))
        else:
            print(json.dumps(feedback_packet(args.goal, args.rounds, args.ambiguities, args.tried, args.resume_hint), indent=2, sort_keys=True))
    except ValueError as error:
        print(f"Prompt builder error: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
