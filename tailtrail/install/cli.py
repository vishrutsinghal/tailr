"""CLI adapter for the shared transactional installer."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Sequence

from ..hosts.contracts import contract
from .catalog import HOSTS, PROFILES
from .engine import InstallEngine, InstallFailure


def _render(payload: dict[str, object], as_json: bool, *, verbose: bool = False) -> None:
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
        reload = diagnostics.get("reload", {})
        if isinstance(reload, dict):
            print(f"Reload: {reload.get('instruction')}")
    counts = payload.get("counts", {})
    if isinstance(counts, dict):
        print("Changes: " + ", ".join(f"{key.replace('_', ' ')}={value}" for key, value in counts.items()))
    for label, key in (("Changed", "changed"), ("Removed", "removed"), ("Preserved", "preserved"), ("Issues", "issues"), ("Recovered", "recovered_transactions")):
        values = payload.get(key, [])
        if values and (verbose or key == "issues"):
            print(f"{label}:")
            for value in values:
                print(f"- {value}")


def _auto_hosts(engine: InstallEngine) -> tuple[str, ...]:
    installed = engine.installed_hosts()
    if len(installed) == 1:
        return installed
    if len(installed) > 1:
        raise InstallFailure("host-selection-required", f"automatic host detection found multiple installed hosts ({', '.join(installed)}); choose one --host value or --host all")
    candidates: set[str] = set()
    for host in HOSTS:
        entry = contract(host, engine._contract_root())
        if any((engine.target / item["destination"]).exists() for item in entry["core_files"]):
            candidates.add(host)
    if shutil.which("codex"):
        candidates.add("codex")
    if shutil.which("claude"):
        candidates.add("claude")
    if len(candidates) != 1:
        detail = ", ".join(sorted(candidates)) if candidates else "none"
        raise InstallFailure("host-selection-required", f"automatic host detection found {detail}; choose --host codex, copilot, claude, or all")
    return tuple(candidates)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("setup", "install", "verify", "doctor", "status", "update", "repair", "rollback", "uninstall", "recover"))
    parser.add_argument("--host", choices=(*HOSTS, "all", "auto"))
    parser.add_argument("--profile", choices=PROFILES)
    parser.add_argument("--target", "--root", dest="target", type=Path, default=Path.cwd())
    parser.add_argument("--to", dest="transaction_id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--verbose", action="store_true", help="include managed path and full plan details")
    parser.add_argument("--compact", action="store_true", help="use the summary JSON envelope for compatibility-controlled lifecycle commands")
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
            payload = {"schema_version": "1", "type": "tailtrail-install-result", "ok": True, "operation": "recover", "status": "passed", "target": engine.target.as_posix(), "host": args.host or "all", "profile": args.profile or "installed", "version": engine.version, "transaction_id": None, "changed": [], "removed": [], "preserved": [], "issues": [], "recovered_transactions": recovered, "plan": None, "counts": {"changed": 0, "removed": 0, "preserved": 0, "issues": 0, "recovered_transactions": len(recovered)}}
            _render(payload, as_json, verbose=args.verbose)
            return 0
        else:
            requested_host = args.host or ("auto" if args.operation == "setup" else "all")
            hosts = _auto_hosts(engine) if requested_host == "auto" else (HOSTS if requested_host == "all" else (requested_host,))
            if requested_host == "all" and args.operation in {"update", "repair"}:
                hosts = engine.installed_hosts()
                if not hosts:
                    raise InstallFailure("not-installed", "no TailTrail host installation was found")
            results = []
            for host in hosts:
                if args.operation in {"setup", "install", "update", "repair"}:
                    operation = ("update" if host in engine.installed_hosts() else "install") if args.operation == "setup" else args.operation
                    result = engine.apply(operation, host, args.profile, dry_run=args.dry_run, force=args.force)
                    if args.operation == "setup":
                        result.operation = "setup"
                    if result.ok and not args.dry_run and (args.operation == "setup" or result.transaction_id):
                        diagnostic = engine.doctor(host)
                        result.diagnostics = diagnostic.diagnostics
                        result.issues.extend(item for item in diagnostic.issues if item not in result.issues)
                        if diagnostic.status == "failed":
                            result.status = "failed"
                    results.append(result)
                elif args.operation == "uninstall":
                    results.append(engine.uninstall(host, force=args.force, dry_run=args.dry_run))
                else:
                    results.append(getattr(engine, args.operation)(host))
        full_payloads = [result.as_dict(details=True) for result in results]
        compact_json = as_json and not args.verbose and (args.compact or args.operation == "setup")
        payloads = [result.as_dict(details=False) for result in results] if compact_json else full_payloads
        if len(payloads) == 1:
            _render(payloads[0] if as_json else full_payloads[0], as_json, verbose=args.verbose)
        elif as_json:
            print(json.dumps({"schema_version": "1", "type": "tailtrail-install-results", "ok": all(item["ok"] for item in payloads), "results": payloads}, indent=2, sort_keys=True))
        else:
            for index, payload in enumerate(payloads):
                if index:
                    print()
                _render(full_payloads[index], False, verbose=args.verbose)
        return 0 if all(result.ok for result in results) else 3
    except InstallFailure as error:
        payload = {"schema_version": "1", "type": "tailtrail-install-error", "ok": False, "error": error.code, "message": str(error), "exit_code": 3}
        print(json.dumps(payload, sort_keys=True) if as_json else f"TailTrail installer failed [{error.code}]: {error}")
        return 3
