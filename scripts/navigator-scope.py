#!/usr/bin/env python3
"""Read-only CLI for bounded Navigator scope evidence and host proposals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import navigator
import navigator_scope


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read JSON object {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def parser() -> argparse.ArgumentParser:
    item = argparse.ArgumentParser(description="Inspect bounded implementation-owner evidence without creating a run.")
    actions = item.add_subparsers(dest="action", required=True)
    inspect = actions.add_parser("inspect", help="Build a non-persisting scope evidence packet.")
    inspect.add_argument("--root", type=Path, default=Path.cwd())
    inspect.add_argument("--goal", required=True)
    inspect.add_argument("--changed", action="append", default=[])
    inspect.add_argument("--format", choices=("json",), default="json")
    record = actions.add_parser("proposal-record", help="Validate and embed one host proposal in supplied evidence; writes nothing.")
    record.add_argument("--root", type=Path, default=Path.cwd())
    record_input = record.add_mutually_exclusive_group(required=True)
    record_input.add_argument("--evidence", type=Path)
    record_input.add_argument("--packet", type=Path)
    record.add_argument("--proposal", type=Path, required=True)
    record.add_argument("--approved", action="store_true")
    return item


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        root = args.root.resolve()
        if args.action == "inspect":
            report = navigator.decide(
                args.goal,
                root,
                args.changed,
                "tailtrail",
                detect_git_changes=False,
                allow_passive_capture=False,
            )
            result = {
                "type": "tailtrail-navigator-scope-inspection",
                "persisted": False,
                "execution_blocked": True,
                "scope_evidence": report["scope_evidence"],
                "host_packet": report["scope_host_packet"],
            }
        else:
            if not args.approved:
                raise ValueError("proposal-record requires --approved; it grants no execution authority")
            proposal = load_object(args.proposal)
            if args.packet:
                result = navigator_scope.host_packet_proposal_decision(
                    root, load_object(args.packet), proposal
                )
            else:
                result = navigator_scope.host_proposal_decision(
                    root, load_object(args.evidence), proposal
                )
    except ValueError as error:
        print(json.dumps({"status": "invalid", "error": str(error)}, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.action == "proposal-record" and result.get("status") == "rejected":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
