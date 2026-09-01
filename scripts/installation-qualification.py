#!/usr/bin/env python3
"""Prepare real-host trials or aggregate every installation support gate."""

from __future__ import annotations

import argparse
import importlib.util
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HOSTS = ("codex", "copilot", "claude")


def _load_runtime() -> Any:
    spec = importlib.util.spec_from_file_location("tailtrail_installation_runtime", ROOT / "scripts" / "host-runtime-conformance.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("host runtime conformance module is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _read(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return payload


def _publication_valid(payload: dict[str, Any] | None) -> bool:
    return bool(
        payload
        and set(payload) == {"schema_version", "type", "observed", "provider", "repository", "version", "commit", "release_url", "artifact", "artifact_sha256", "identity_verified", "workflow_run_url"}
        and payload.get("schema_version") == "1"
        and payload.get("type") == "tailtrail-release-publication-receipt"
        and payload.get("observed") is True
        and payload.get("provider") == "github"
        and payload.get("repository") == "vishrutsinghal/tailr"
        and payload.get("identity_verified") is True
        and isinstance(payload.get("commit"), str)
        and len(payload["commit"]) == 40
        and all(character in "0123456789abcdef" for character in payload["commit"])
        and payload.get("release_url") == f"https://github.com/vishrutsinghal/tailr/releases/tag/v{payload.get('version')}"
        and payload.get("artifact") == f"tailtrail-{payload.get('version')}-py3-none-any.whl"
        and isinstance(payload.get("workflow_run_url"), str)
        and payload["workflow_run_url"].startswith("https://github.com/vishrutsinghal/tailr/actions/runs/")
        and payload["workflow_run_url"].rsplit("/", 1)[-1].isdigit()
        and isinstance(payload.get("artifact_sha256"), str)
        and len(payload["artifact_sha256"]) == 64
        and all(character in "0123456789abcdef" for character in payload["artifact_sha256"])
    )


def _identity_verified(path: Path | None) -> bool:
    if path is None or not path.is_file() or shutil.which("gh") is None:
        return False
    result = subprocess.run(["gh", "attestation", "verify", path.as_posix(), "--repo", "vishrutsinghal/tailr"], text=True, capture_output=True, check=False, timeout=60)
    return result.returncode == 0


def aggregate(root: Path, host: str, platform_path: Path | None, publication_path: Path | None, artifact_path: Path | None = None) -> dict[str, Any]:
    runtime = _load_runtime()
    host_report = runtime.report(root, None if host == "all" else host)
    platform = _read(platform_path)
    publication = _read(publication_path)
    version = json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))["product"]["version"]
    runtime_rows = host_report["runtime_conformance"]
    host_passed = all(row["runtime_status"] == "passed" for row in runtime_rows)
    platform_passed = bool(platform and platform.get("type") == "tailtrail-platform-qualification-report" and platform.get("valid") is True and _identity_verified(platform_path))
    publication_passed = bool(
        _publication_valid(publication)
        and platform_passed
        and publication["version"] == version
        and publication["commit"] == platform["commit"]
        and publication["artifact_sha256"] == platform.get("artifacts", {}).get("wheel", {}).get("sha256")
        and publication["artifact"] == platform.get("artifacts", {}).get("wheel", {}).get("filename")
        and artifact_path is not None
        and artifact_path.is_file()
        and hashlib.sha256(artifact_path.read_bytes()).hexdigest() == publication["artifact_sha256"]
        and _identity_verified(artifact_path)
        and _identity_verified(publication_path)
    )
    gates = {
        "instruction_contract": host_report["instruction_conformance"]["status"],
        "real_host_runtime": "passed" if host_passed else "evidence-incomplete",
        "platform_matrix": "passed" if platform_passed else "evidence-incomplete",
        "signed_publication": "passed" if publication_passed else "evidence-incomplete",
    }
    passed = all(value == "passed" for value in gates.values())
    missing = []
    if not host_passed:
        missing.append("Record six fresh validated real-host receipts for every selected host/version.")
    if not platform_passed:
        missing.append("Supply the identity-attested exact hosted OS/Python report with --platform-report and make the GitHub CLI available.")
    if not publication_passed:
        missing.append("Supply the downloaded wheel and identity-attested observed publication receipt with --artifact and --publication-receipt; GitHub CLI verification must pass.")
    return {
        "schema_version": "1",
        "type": "tailtrail-installation-qualification-report",
        "status": "passed" if passed else "evidence-incomplete",
        "supported": passed,
        "gates": gates,
        "host_runtime": host_report,
        "platform_report": platform_path.as_posix() if platform_path else None,
        "publication_receipt": publication_path.as_posix() if publication_path else None,
        "artifact": artifact_path.as_posix() if artifact_path else None,
        "next_actions": missing,
        "boundary": "Configured workflows and local contract tests are not support evidence. Support requires real host receipts, the exact hosted platform matrix, and an observed identity-backed publication receipt.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--root", type=Path, default=Path.cwd())
    prepare.add_argument("--host", choices=(*HOSTS, "all"), default="all")
    prepare.add_argument("--format", choices=("text", "json"), default="text")
    report = sub.add_parser("report")
    report.add_argument("--root", type=Path, default=Path.cwd())
    report.add_argument("--host", choices=(*HOSTS, "all"), default="all")
    report.add_argument("--platform-report", type=Path)
    report.add_argument("--publication-receipt", type=Path)
    report.add_argument("--artifact", type=Path)
    report.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    try:
        runtime = _load_runtime()
        if args.action == "prepare":
            hosts = HOSTS if args.host == "all" else (args.host,)
            payload = {"schema_version": "1", "type": "tailtrail-installation-qualification-preparation", "status": "prepared", "bundles": [runtime.prepare(args.root, host) for host in hosts]}
            code = 0
        else:
            payload = aggregate(args.root.resolve(), args.host, args.platform_report, args.publication_receipt, args.artifact)
            code = 0 if payload["supported"] else 3
    except (OSError, ValueError, KeyError, json.JSONDecodeError, RuntimeError) as error:
        payload = {"schema_version": "1", "type": "tailtrail-installation-qualification-report", "status": "failed", "supported": False, "issues": [str(error)]}
        code = 2
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"TailTrail installation qualification: {payload['status']}")
        if "gates" in payload:
            for name, status in payload["gates"].items():
                print(f"- {name}: {status}")
            for action in payload["next_actions"]:
                print(f"- Next: {action}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
