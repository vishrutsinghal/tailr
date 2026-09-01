#!/usr/bin/env python3
"""Exercise installed artifacts and aggregate truthful OS/Python receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def os_id() -> str:
    return {"Linux": "linux", "Darwin": "macos", "Windows": "windows"}.get(platform.system(), platform.system().lower())


def venv_executable(root: Path, name: str) -> Path:
    directory = root / name
    subprocess.run([sys.executable, "-m", "venv", str(directory)], check=True)
    python = directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return python


def console_for(python: Path) -> Path:
    return python.parent / ("tailtrail.exe" if os.name == "nt" else "tailtrail")


def run(command: list[str], *, cwd: Path, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != expected:
        raise RuntimeError(
            f"expected exit {expected}, got {result.returncode}: {command}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def install_artifact(python: Path, artifact: Path, cwd: Path) -> Path:
    run([str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(artifact)], cwd=cwd)
    executable = console_for(python)
    if not executable.is_file():
        raise RuntimeError(f"console launcher missing after artifact install: {executable}")
    return executable


def lifecycle(executable: Path, sandbox: Path, route: str, checks: dict[str, str]) -> None:
    package_info = json.loads(run([str(executable), "package-info", "--format", "json"], cwd=sandbox).stdout)
    if not package_info.get("valid"):
        raise RuntimeError(f"installed package integrity failed: {package_info}")
    checks[f"{route}:artifact-install"] = "pass"
    checks[f"{route}:console-launcher"] = "pass"
    for host in ("codex", "copilot", "claude"):
        target = sandbox / f"{route} target ünicode" / host
        target.mkdir(parents=True)
        sentinel = target / "user-crlf.txt"
        sentinel.write_bytes(b"alpha\r\nbeta\r\n")
        install = json.loads(run([str(executable), "install", "--host", host, "--profile", "core", "--target", str(target), "--format", "json", "--compact"], cwd=sandbox).stdout)
        if not install.get("ok"):
            raise RuntimeError(f"{route}/{host} install failed: {install}")
        checks[f"{route}:{host}:install"] = "pass"
        checks[f"{route}:{host}:space-and-unicode-path"] = "pass"
        checks[f"{route}:{host}:line-ending-preservation"] = "pass" if sentinel.read_bytes() == b"alpha\r\nbeta\r\n" else "fail"
        verify = json.loads(run([str(executable), "verify", "--host", host, "--target", str(target), "--format", "json", "--compact"], cwd=sandbox).stdout)
        if not verify.get("ok"):
            raise RuntimeError(f"{route}/{host} verify failed: {verify}")
        checks[f"{route}:{host}:verify"] = "pass"
        update = json.loads(run([str(executable), "update", "--host", host, "--profile", "extended", "--target", str(target), "--format", "json", "--compact"], cwd=sandbox).stdout)
        if not update.get("ok"):
            raise RuntimeError(f"{route}/{host} update failed: {update}")
        checks[f"{route}:{host}:update"] = "pass"
        if update.get("transaction_id"):
            rollback = json.loads(run([str(executable), "rollback", "--to", str(update["transaction_id"]), "--target", str(target), "--format", "json", "--compact"], cwd=sandbox).stdout)
            if not rollback.get("ok"):
                raise RuntimeError(f"{route}/{host} rollback failed: {rollback}")
        checks[f"{route}:{host}:rollback"] = "pass"
        uninstall = json.loads(run([str(executable), "uninstall", "--host", host, "--target", str(target), "--force", "--format", "json", "--compact"], cwd=sandbox).stdout)
        if not uninstall.get("ok"):
            raise RuntimeError(f"{route}/{host} uninstall failed: {uninstall}")
        checks[f"{route}:{host}:uninstall"] = "pass"


def boundary_checks(executable: Path, sandbox: Path, checks: dict[str, str]) -> None:
    if os.name == "nt":
        checks["permission-model"] = "not-applicable"
    else:
        target = sandbox / "read-only-target"
        target.mkdir()
        target.chmod(stat.S_IRUSR | stat.S_IXUSR)
        try:
            result = subprocess.run([str(executable), "install", "--host", "claude", "--target", str(target), "--format", "json"], cwd=sandbox, text=True, capture_output=True, check=False)
            if result.returncode == 0:
                raise RuntimeError("installer accepted a read-only target")
            checks["permission-model"] = "pass"
        finally:
            target.chmod(stat.S_IRWXU)
    outside = sandbox / "outside"
    outside.mkdir()
    target = sandbox / "symlink-target"
    target.mkdir()
    link = target / ".codex-plugin"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        checks["symlink-boundary"] = "not-applicable"
    else:
        result = subprocess.run([str(executable), "install", "--host", "codex", "--target", str(target), "--format", "json"], cwd=sandbox, text=True, capture_output=True, check=False)
        if result.returncode == 0 or "symlink" not in (result.stdout + result.stderr).lower():
            raise RuntimeError("installer did not fail closed on a managed symlink boundary")
        checks["symlink-boundary"] = "pass"


def exercise(wheel: Path, sdist_wheel: Path, output: Path, commit: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="tailtrail-e5-") as temporary:
        sandbox = Path(temporary)
        checks: dict[str, str] = {}
        wheel_python = venv_executable(sandbox, "wheel-env")
        wheel_cli = install_artifact(wheel_python, wheel.resolve(), sandbox)
        lifecycle(wheel_cli, sandbox, "wheel", checks)
        boundary_checks(wheel_cli, sandbox, checks)
        sdist_python = venv_executable(sandbox, "sdist-env")
        sdist_cli = install_artifact(sdist_python, sdist_wheel.resolve(), sandbox)
        lifecycle(sdist_cli, sandbox, "sdist-to-wheel", checks)
    valid = all(value in {"pass", "not-applicable"} for value in checks.values())
    receipt = {
        "schema_version": "1",
        "type": "tailtrail-platform-qualification-receipt",
        "observed": True,
        "runner": {"os": os_id(), "system": platform.system(), "release": platform.release(), "machine": platform.machine() or "unknown", "ci": os.environ.get("GITHUB_ACTIONS") == "true"},
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "source_commit": commit,
        "artifacts": {
            "wheel": {"filename": wheel.name, "sha256": digest(wheel)},
            "sdist_to_wheel": {"filename": sdist_wheel.name, "sha256": digest(sdist_wheel)},
        },
        "checks": checks,
        "valid": valid,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return receipt


def report(receipt_dir: Path, contract_path: Path, commit: str, wheel: Path, sdist_wheel: Path) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    issues: list[str] = []
    receipts: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted(receipt_dir.rglob("*.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            issues.append(f"invalid receipt JSON {path}: {error}")
            continue
        if item.get("type") != "tailtrail-platform-qualification-receipt":
            continue
        key = (item.get("runner", {}).get("os"), item.get("python"))
        if key in receipts:
            issues.append(f"duplicate receipt for {key[0]}/Python {key[1]}")
        receipts[key] = item
    expected = {(system, python) for system in contract["supported_operating_systems"] for python in contract["supported_python_versions"]}
    if set(receipts) != expected:
        issues.append(f"matrix coverage mismatch: missing {sorted(expected - set(receipts))}, unexpected {sorted(set(receipts) - expected)}")
    wanted_hashes = {"wheel": digest(wheel), "sdist_to_wheel": digest(sdist_wheel)}
    for key, item in receipts.items():
        label = f"{key[0]}/Python {key[1]}"
        if item.get("observed") is not True or item.get("runner", {}).get("ci") is not True:
            issues.append(f"{label} is not a hosted observed receipt")
        if item.get("source_commit") != commit:
            issues.append(f"{label} source commit mismatch")
        if item.get("valid") is not True:
            issues.append(f"{label} is not valid")
        for route, expected_hash in wanted_hashes.items():
            if item.get("artifacts", {}).get(route, {}).get("sha256") != expected_hash:
                issues.append(f"{label} {route} artifact hash mismatch")
            for host_profile in contract["host_profiles"]:
                host = host_profile.split(":", 1)[0]
                for operation in ("install", "verify", "update", "rollback", "uninstall"):
                    if item.get("checks", {}).get(f"{route.replace('_', '-')}:{host}:{operation}") != "pass":
                        issues.append(f"{label} missing {route}/{host}/{operation} pass")
        for check in ("permission-model", "symlink-boundary"):
            if item.get("checks", {}).get(check) not in {"pass", "not-applicable"}:
                issues.append(f"{label} missing platform boundary check {check}")
    return {"schema_version": "1", "type": "tailtrail-platform-qualification-report", "commit": commit, "artifacts": {"wheel": {"filename": wheel.name, "sha256": wanted_hashes["wheel"]}, "sdist_to_wheel": {"filename": sdist_wheel.name, "sha256": wanted_hashes["sdist_to_wheel"]}}, "expected_cells": len(expected), "observed_cells": len(receipts), "valid": not issues, "issues": issues}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    exercise_parser = subparsers.add_parser("exercise")
    exercise_parser.add_argument("--wheel", type=Path, required=True)
    exercise_parser.add_argument("--sdist-wheel", type=Path, required=True)
    exercise_parser.add_argument("--output", type=Path, required=True)
    exercise_parser.add_argument("--commit", required=True)
    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--receipts", type=Path, required=True)
    report_parser.add_argument("--contract", type=Path, default=ROOT / "platform-release-contract.json")
    report_parser.add_argument("--commit", required=True)
    report_parser.add_argument("--wheel", type=Path, required=True)
    report_parser.add_argument("--sdist-wheel", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "exercise":
        payload = exercise(args.wheel, args.sdist_wheel, args.output, args.commit)
    else:
        payload = report(args.receipts, args.contract, args.commit, args.wheel, args.sdist_wheel)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
