#!/usr/bin/env python3
"""CLI wrapper for TailTrail stop, exact resume, and session status."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import session_control


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    stop = sub.add_parser("stop")
    stop.add_argument("--root", type=Path, default=Path.cwd())
    stop.add_argument("--run-id")
    stop.add_argument("--context-key")
    stop.add_argument("--format", choices=("markdown", "json"), default="markdown")
    resume = sub.add_parser("resume")
    resume.add_argument("--root", type=Path, default=Path.cwd())
    resume.add_argument("--run-id", required=True)
    resume.add_argument("--context-key")
    resume.add_argument("--format", choices=("markdown", "json"), default="markdown")
    status = sub.add_parser("status")
    status.add_argument("--root", type=Path, default=Path.cwd())
    status.add_argument("--context-key")
    status.add_argument("--format", choices=("markdown", "json"), default="json")
    args = parser.parse_args()
    try:
        if args.command == "stop":
            result = session_control.stop(args.root, args.run_id, args.context_key)
        elif args.command == "resume":
            result = session_control.resume(args.root, args.run_id, args.context_key)
        else:
            result = session_control.status(args.root, args.context_key)
        if args.format == "json":
            print(json.dumps(result, indent=2, sort_keys=True))
        elif args.command == "status":
            print(f"# TailTrail Session Status\n\n- State: `{result['state']}`\n- Run ID: `{result.get('run_id') or 'none'}`")
        else:
            print(result["report"], end="")
        return 0 if result.get("state") not in {"resume-stale", "resume-conflict", "resume-invalid"} else 2
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"TailTrail session control error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
