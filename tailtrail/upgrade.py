"""Verified local-wheel package and project-payload upgrade orchestration.

Validation: ``python3 -m unittest tests.test_installation_experience`` covers
digest rejection, offline planning, and transaction rollback boundaries.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Sequence

from .install import InstallEngine, InstallFailure
from .install.catalog import HOSTS, payload_version
from .resources import verify_package


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _extract_verified_wheel(path: Path, expected: str, destination: Path) -> tuple[Path, str]:
    if not path.is_file() or path.suffix != ".whl" or not path.name.startswith("tailtrail-"):
        raise ValueError("--artifact must be an existing TailTrail wheel")
    if len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
        raise ValueError("--sha256 must be one full lowercase SHA-256 digest")
    actual = _digest(path)
    if actual != expected:
        raise ValueError(f"wheel SHA-256 mismatch: expected {expected}, got {actual}")
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            member = Path(name.replace("\\", "/"))
            if member.is_absolute() or ".." in member.parts:
                raise ValueError(f"wheel contains an unsafe path: {name}")
        archive.extractall(destination)
    package_root = destination / "tailtrail"
    issues = verify_package(package_root)
    if issues:
        raise ValueError("wheel package integrity failed: " + "; ".join(issues))
    return package_root, payload_version(package_root)


def upgrade(argv: Sequence[str] | None = None) -> tuple[int, dict[str, Any]]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--host", choices=(*HOSTS, "all"), default="all")
    parser.add_argument("--target", "--root", dest="target", type=Path, default=Path.cwd())
    parser.add_argument("--profile", choices=("core", "extended"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    artifact = args.artifact.resolve()
    try:
        with tempfile.TemporaryDirectory(prefix="tailtrail-upgrade-") as temporary:
            package_root, version = _extract_verified_wheel(artifact, args.sha256, Path(temporary))
            engine = InstallEngine(args.target, package_root=package_root)
            hosts = engine.installed_hosts() if args.host == "all" else (args.host,)
            if args.host != "all" and args.host not in engine.installed_hosts():
                raise InstallFailure("not-installed", f"{args.host} is not installed in the target")
            plans = [engine.plan("update", host, args.profile, force=args.force) for host in hosts]
            conflicts = sorted({item for plan in plans for item in plan.conflicts})
            if conflicts:
                raise InstallFailure("managed-path-conflict", "project update preflight found managed-path conflicts; review them or rerun with --force")
            payload: dict[str, Any] = {
                "schema_version": "1",
                "type": "tailtrail-upgrade-result",
                "ok": True,
                "status": "dry-run" if args.dry_run else "passed",
                "artifact": artifact.as_posix(),
                "artifact_sha256": args.sha256,
                "version": version,
                "target": engine.target.as_posix(),
                "hosts": list(hosts),
                "preflight": [{"host": plan.host, "profile": plan.profile, "plan_id": plan.plan_id, "entries": len(plan.entries), "removals": len(plan.removals)} for plan in plans],
                "package": "planned" if args.dry_run else "pending",
                "projects": [],
                "boundary": "The wheel is local, hash-pinned, package-integrity verified, and installed without dependency or index access.",
            }
            if args.dry_run:
                return 0, payload
            if not args.approved:
                raise InstallFailure("approval-required", "upgrade changes the active Python environment; inspect --dry-run and rerun with --approved")
            results = []
            applied_transactions: list[str] = []
            for host in hosts:
                result = engine.apply("update", host, args.profile, force=args.force)
                results.append(result)
                if not result.ok:
                    for transaction_id in reversed(applied_transactions):
                        engine.rollback(transaction_id, force=True)
                    raise InstallFailure("project-update-failed", f"{host} project payload update failed before the package environment changed: {'; '.join(result.issues)}")
                if result.transaction_id:
                    applied_transactions.append(result.transaction_id)
                diagnostic = engine.doctor(host)
                result.diagnostics = diagnostic.diagnostics
                if not diagnostic.ok:
                    for transaction_id in reversed(applied_transactions):
                        engine.rollback(transaction_id, force=True)
                    raise InstallFailure("project-verification-failed", f"{host} diagnostics failed before the package environment changed: {'; '.join(diagnostic.issues)}")
            command = [sys.executable, "-m", "pip", "install", "--no-index", "--no-deps", "--upgrade", artifact.as_posix()]
            completed = subprocess.run(command, text=True, capture_output=True, check=False)
            if completed.returncode != 0:
                rollback_issues = []
                for transaction_id in reversed(applied_transactions):
                    restored = engine.rollback(transaction_id, force=True)
                    if not restored.ok:
                        rollback_issues.extend(restored.issues)
                detail = (completed.stderr or completed.stdout).strip() or "pip failed without output"
                if rollback_issues:
                    detail += "; project rollback issues: " + "; ".join(rollback_issues)
                raise InstallFailure("package-upgrade-failed", detail)
            payload["package"] = "passed"
            payload["projects"] = [result.as_dict(details=False) for result in results]
            payload["reload"] = {result.host: result.diagnostics["reload"] for result in results if result.diagnostics}
            payload["ok"] = all(result.ok for result in results)
            payload["status"] = "passed" if payload["ok"] else "project-update-failed"
            return (0 if payload["ok"] else 3), payload
    except (OSError, ValueError, zipfile.BadZipFile, InstallFailure) as error:
        return 3, {"schema_version": "1", "type": "tailtrail-upgrade-result", "ok": False, "status": "failed", "error": getattr(error, "code", error.__class__.__name__), "message": str(error)}


def main(argv: Sequence[str] | None = None) -> int:
    code, payload = upgrade(argv)
    as_json = "--format=json" in (argv or sys.argv[1:]) or any(value == "--format" and index + 1 < len(argv or sys.argv[1:]) and (argv or sys.argv[1:])[index + 1] == "json" for index, value in enumerate(argv or sys.argv[1:]))
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif payload.get("ok"):
        print(f"TailTrail upgrade: {payload['status']}")
        print(f"Version: {payload['version']}")
        print(f"Package: {payload['package']}")
        print(f"Project hosts: {', '.join(payload['hosts']) or 'none'}")
    else:
        print(f"TailTrail upgrade failed [{payload.get('error')}]: {payload.get('message')}")
    return code
