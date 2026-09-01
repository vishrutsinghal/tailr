#!/usr/bin/env python3
"""Run and package TailTrail's PM-6 offline enterprise conformance suite."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "benchmarks/enterprise-conformance/v1.json"
SCHEMA = ROOT / "schemas/enterprise-conformance-report.schema.json"
BUNDLE_FILES = ("scripts/enterprise-conformance.py", "benchmarks/enterprise-conformance/v1.json", "schemas/enterprise-conformance-report.schema.json")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain one JSON object")
    return value


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def catalog_errors(catalog: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if catalog.get("schema_version") != "1" or catalog.get("type") != "tailtrail-enterprise-conformance-catalog":
        issues.append("enterprise conformance catalog contract is incompatible")
    controls = catalog.get("controls")
    if not isinstance(controls, list) or len(controls) < 10:
        issues.append("catalog must define at least ten enterprise control domains")
        return issues
    identifiers = [row.get("id") for row in controls if isinstance(row, dict)]
    if len(identifiers) != len(controls) or None in identifiers or len(identifiers) != len(set(identifiers)):
        issues.append("control IDs must be non-empty and unique")
    for row in controls:
        if not isinstance(row, dict) or not isinstance(row.get("required_paths"), list) or not row["required_paths"]:
            issues.append("every control needs one or more required paths")
    if set(catalog.get("threat_cases", [])) != {"path-traversal", "symlink-escape", "command-injection", "untrusted-provider-json", "sensitive-data-leakage"}:
        issues.append("threat model must cover all five PM-6 attack classes")
    return issues


def compatibility(root: Path) -> dict[str, Any]:
    contract = read_json(root / "platform-release-contract.json")
    host_matrix = read_json(root / "adapters/host-compatibility-v1.json")
    manifest_path = root / ".tailtrail/official-aidlc/manifest.json"
    aidlc_manifest = read_json(manifest_path) if manifest_path.is_file() else {}
    return {
        "operating_systems": contract.get("supported_operating_systems", []),
        "python_versions": contract.get("supported_python_versions", []),
        "host_profiles": contract.get("host_profiles", []),
        "mcp_protocol": "stdio-local-json-rpc",
        "host_adapter_version": host_matrix.get("adapter_version"),
        "official_aidlc_revision": aidlc_manifest.get("official", {}).get("revision", "not-installed"),
        "configured_is_observed": contract.get("evidence_policy", {}).get("configured_is_observed"),
    }


def run_probe(root: Path, row: dict[str, Any]) -> dict[str, Any]:
    arguments = [str(item).replace("{root}", root.as_posix()) for item in row["arguments"]]
    command = [sys.executable, *arguments]
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    combined = (result.stdout + result.stderr).encode("utf-8", errors="replace")
    return {
        "id": row["id"],
        "status": "passed" if result.returncode == 0 else "failed",
        "exit_code": result.returncode,
        "output_sha256": digest_bytes(combined),
        "output_bytes": len(combined),
        "boundary": "Only exit status and output fingerprint are retained; command output is not copied into the report.",
    }


def platform_qualification(path: Path | None, expected_cells: int) -> dict[str, Any]:
    if path is None:
        return {"status": "not-observed", "qualified": False, "reason": "No hosted platform qualification report was supplied."}
    value = read_json(path.resolve())
    qualified = value.get("type") == "tailtrail-platform-qualification-report" and value.get("valid") is True and value.get("observed_cells") == expected_cells
    return {
        "status": "qualified" if qualified else "blocked",
        "qualified": qualified,
        "observed_cells": value.get("observed_cells"),
        "expected_cells": expected_cells,
        "reason": "Hosted receipt matrix is complete." if qualified else "Platform report is missing cells, invalid, or not a qualification report.",
    }


def inspect(root: Path, catalog_path: Path = CATALOG, platform_report: Path | None = None, run_probes: bool = True) -> dict[str, Any]:
    root, catalog_path = root.resolve(), catalog_path.resolve()
    catalog = read_json(catalog_path)
    issues = catalog_errors(catalog)
    controls = []
    for row in catalog.get("controls", []):
        missing = [path for path in row["required_paths"] if not (root / path).is_file()]
        controls.append({"id": row["id"], "status": "passed" if not missing else "failed", "missing": missing})
        issues.extend(f"{row['id']}: missing {path}" for path in missing)
    probes = [run_probe(root, row) for row in catalog.get("local_probes", [])] if run_probes and not issues else []
    issues.extend(f"probe failed: {row['id']}" for row in probes if row["status"] != "passed")
    try:
        matrix = compatibility(root)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        matrix = {}
        issues.append(f"compatibility matrix invalid: {error}")
    expected_cells = len(matrix.get("operating_systems", [])) * len(matrix.get("python_versions", []))
    qualification = platform_qualification(platform_report, expected_cells)
    return {
        "schema_version": "1",
        "type": "tailtrail-enterprise-conformance-report",
        "catalog_id": catalog.get("catalog_id"),
        "status": "passed" if not issues else "blocked",
        "controls": controls,
        "probes": probes,
        "compatibility": matrix,
        "release_qualification": qualification,
        "issues": issues,
        "boundary": "Local conformance and offline probes do not prove hosted OS coverage, runtime host behavior, CI acceptance, identity attestation, deployment, or support readiness.",
    }


def bundle_readme() -> bytes:
    return (
        "# TailTrail Offline Enterprise Verification\n\n"
        "Run from an installed/source TailTrail root without network access:\n\n"
        "```text\n"
        "python enterprise-offline-verify.py verify --root /path/to/tailtrail --catalog enterprise-conformance-v1.json\n"
        "```\n\n"
        "The report proves local deterministic controls only. Hosted platform qualification requires a separate linked platform report.\n"
    ).encode("utf-8")


def create_bundle(root: Path, target: Path, approved: bool) -> dict[str, Any]:
    if not approved:
        raise ValueError("offline bundle creation requires --approved")
    root, target = root.resolve(), target.resolve()
    if target.exists():
        raise ValueError("refusing to overwrite an existing offline bundle")
    entries = {
        "enterprise-offline-verify.py": (root / BUNDLE_FILES[0]).read_bytes(),
        "enterprise-conformance-v1.json": (root / BUNDLE_FILES[1]).read_bytes(),
        "enterprise-conformance-report.schema.json": (root / BUNDLE_FILES[2]).read_bytes(),
        "README.md": bundle_readme(),
    }
    manifest = {
        "schema_version": "1",
        "type": "tailtrail-enterprise-offline-bundle-manifest",
        "files": {name: digest_bytes(value) for name, value in sorted(entries.items())},
        "boundary": "Self-contained verifier and contracts only; no source, prompt, logs, credentials, CI receipts, or customer data are included.",
    }
    entries["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (2024, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            archive.writestr(info, value)
    return {"type": "tailtrail-enterprise-offline-bundle", "artifact": target.as_posix(), "sha256": digest_bytes(target.read_bytes()), "files": sorted(entries), "boundary": manifest["boundary"]}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="action", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--root", type=Path, default=Path.cwd())
    verify.add_argument("--catalog", type=Path, default=CATALOG)
    verify.add_argument("--platform-report", type=Path)
    verify.add_argument("--skip-probes", action="store_true")
    bundle = commands.add_parser("bundle")
    bundle.add_argument("--root", type=Path, default=ROOT)
    bundle.add_argument("--target", type=Path, required=True)
    bundle.add_argument("--approved", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        value = inspect(args.root, args.catalog, args.platform_report, not args.skip_probes) if args.action == "verify" else create_bundle(args.root, args.target, args.approved)
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0 if value.get("status", "passed") == "passed" else 2
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"TailTrail enterprise conformance error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
