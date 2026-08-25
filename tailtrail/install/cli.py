"""CLI adapter for the shared transactional installer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .catalog import HOSTS, PROFILES
from .engine import InstallEngine, InstallFailure


def _render(payload: dict[str, object], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print(f"TailTrail {payload['operation']}: {payload['status']}")
    print(f"Host: {payload['host']}")
    print(f"Profile: {payload['profile']}")
    print(f"Target: {payload['target']}")
    if payload.get("transaction_id"):
        print(f"Transaction: {payload['transaction_id']}")
    diagnostics = payload.get("diagnostics")
    if isinstance(diagnostics, dict):
        print(f"Adapter: {diagnostics['adapter_version']} / {diagnostics['qualification']}")
        print(f"Composition: {diagnostics['composition']}")
        print(f"Runtime: {diagnostics['runtime_status']}")
        print(f"Supported: {'yes' if diagnostics['supported'] else 'no'}")
        version = diagnostics.get("version_detection", {})
        if isinstance(version, dict):
            print(f"Host version: {version.get('version') or version.get('state')}")
        action = diagnostics.get("first_action", {})
        if isinstance(action, dict):
            print(f"First action: {action.get('invocation')}")
    for label, key in (("Changed", "changed"), ("Removed", "removed"), ("Preserved", "preserved"), ("Issues", "issues"), ("Recovered", "recovered_transactions")):
        values = payload.get(key, [])
        if values:
            print(f"{label}:")
            for value in values:
                print(f"- {value}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("install", "verify", "doctor", "status", "update", "repair", "rollback", "uninstall", "recover"))
    parser.add_argument("--host", choices=(*HOSTS, "all"), default="all")
    parser.add_argument("--profile", choices=PROFILES)
    parser.add_argument("--target", "--root", dest="target", type=Path, default=Path.cwd())
    parser.add_argument("--to", dest="transaction_id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    as_json = args.format == "json"
    try:
        engine = InstallEngine(args.target)
        if args.operation == "rollback":
            if not args.transaction_id:
                parser.error("rollback requires --to <transaction-id>")
            results = [engine.rollback(args.transaction_id, force=args.force, dry_run=args.dry_run)]
        elif args.operation == "recover":
            with engine._lock():
                recovered = engine.recover()
            payload = {"schema_version": "1", "type": "tailtrail-install-result", "ok": True, "operation": "recover", "status": "passed", "target": engine.target.as_posix(), "host": args.host, "profile": args.profile or "installed", "version": "", "transaction_id": None, "changed": [], "removed": [], "preserved": [], "issues": [], "recovered_transactions": recovered, "plan": None}
            _render(payload, as_json)
            return 0
        else:
            hosts = HOSTS if args.host == "all" else (args.host,)
            if args.host == "all" and args.operation in {"update", "repair"}:
                hosts = engine.installed_hosts()
                if not hosts:
                    raise InstallFailure("not-installed", "no TailTrail host installation was found")
            results = []
            for host in hosts:
                if args.operation in {"install", "update", "repair"}:
                    results.append(engine.apply(args.operation, host, args.profile, dry_run=args.dry_run, force=args.force))
                elif args.operation == "uninstall":
                    results.append(engine.uninstall(host, force=args.force, dry_run=args.dry_run))
                else:
                    results.append(getattr(engine, args.operation)(host))
        payloads = [result.as_dict() for result in results]
        if len(payloads) == 1:
            _render(payloads[0], as_json)
        elif as_json:
            print(json.dumps({"schema_version": "1", "type": "tailtrail-install-results", "ok": all(item["ok"] for item in payloads), "results": payloads}, indent=2, sort_keys=True))
        else:
            for index, payload in enumerate(payloads):
                if index:
                    print()
                _render(payload, False)
        return 0 if all(result.ok for result in results) else 3
    except InstallFailure as error:
        payload = {"schema_version": "1", "type": "tailtrail-install-error", "ok": False, "error": error.code, "message": str(error), "exit_code": 3}
        print(json.dumps(payload, sort_keys=True) if as_json else f"TailTrail installer failed [{error.code}]: {error}")
        return 3
