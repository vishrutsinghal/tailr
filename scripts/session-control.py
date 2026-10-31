#!/usr/bin/env python3
"""CLI wrapper for TailTrail stop, exact resume, and session status."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import session_control


def _ledger() -> Any:
    spec = importlib.util.spec_from_file_location(
        "session_control_run_ledger", Path(__file__).resolve().parent / "run-ledger.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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
    status.add_argument("--format", choices=("markdown", "json"), default="markdown")
    archive = sub.add_parser("archive", help="Retire a run to the archive with audit continuity; never deletes.")
    archive.add_argument("--root", type=Path, default=Path.cwd())
    archive.add_argument("--run-id", required=True)
    archive.add_argument("--reason", required=True, help="Mandatory rationale recorded in the archive receipt.")
    archive.add_argument("--force", action="store_true", help="Required with --reason to archive an actively locked run.")
    archive.add_argument("--format", choices=("markdown", "json"), default="markdown")
    unarchive = sub.add_parser("unarchive", help="Restore an archived run byte-exactly after receipt verification.")
    unarchive.add_argument("--root", type=Path, default=Path.cwd())
    unarchive.add_argument("--run-id", required=True)
    unarchive.add_argument("--format", choices=("markdown", "json"), default="markdown")
    runs = sub.add_parser("list", help="Inventory live runs, or archived runs with --archived. Read-only.")
    runs.add_argument("--root", type=Path, default=Path.cwd())
    runs.add_argument("--archived", action="store_true")
    runs.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    try:
        ledger = _ledger()
        if args.command == "stop":
            result = session_control.stop(args.root, args.run_id, args.context_key)
        elif args.command == "resume":
            result = session_control.resume(args.root, args.run_id, args.context_key)
        elif args.command == "archive":
            result = ledger.archive_run(args.root, args.run_id, args.reason, args.force)
        elif args.command == "unarchive":
            result = ledger.unarchive_run(args.root, args.run_id)
        elif args.command == "list":
            result = ledger.list_runs(args.root, args.archived)
        else:
            result = session_control.status(args.root, args.context_key)
        if args.format == "json" or args.command in {"archive", "unarchive", "list"}:
            print(json.dumps(result, indent=2, sort_keys=True, default=str))
        elif args.command == "status":
            print(f"# TailTrail Session Status\n\n- State: `{result['state']}`\n- Run ID: `{result.get('run_id') or 'none'}`")
        else:
            print(result["report"], end="")
        if args.command == "stop" and result.get("state") != "detached":
            return 2
        return 0 if result.get("state") not in {"resume-stale", "resume-conflict", "resume-invalid"} else 2
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"TailTrail session control error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
