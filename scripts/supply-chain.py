#!/usr/bin/env python3
"""Create and verify TailTrail's deterministic release evidence bundle."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def git_value(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def dependencies(lock: dict[str, Any]) -> list[str]:
    return [f"{item['name']}=={item['version']}" for item in lock["dependencies"]]


def verify_build_environment(lock: dict[str, Any]) -> None:
    issues = []
    for item in lock["dependencies"]:
        try:
            actual = importlib.metadata.version(item["name"])
        except importlib.metadata.PackageNotFoundError:
            actual = "not-installed"
        if actual != item["version"]:
            issues.append(f"{item['name']} expected {item['version']}, got {actual}")
    if issues:
        raise ValueError("release build environment does not match lock: " + "; ".join(issues))


def verify_source_identity(commit: str) -> None:
    head = git_value("rev-parse", "HEAD")
    if head != commit:
        raise ValueError(f"source commit does not match checkout HEAD: expected {head or 'unavailable'}, got {commit}")
    if os.environ.get("GITHUB_ACTIONS") != "true" and git_value("status", "--porcelain"):
        raise ValueError("release provenance requires a clean source checkout; local dirty-worktree artifacts are not attributable to HEAD")


def create_bundle(artifacts: list[Path], output: Path, repository: str, commit: str, epoch: int, *, verify_environment: bool = True, verify_source: bool = True) -> dict[str, Any]:
    if not commit or len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise ValueError("source commit must be a full lowercase Git SHA")
    output.mkdir(parents=True, exist_ok=True)
    lock = read_json(ROOT / "release-build-lock.json")
    if verify_environment:
        verify_build_environment(lock)
    if verify_source:
        verify_source_identity(commit)
    records = [
        {"filename": path.name, "sha256": digest(path), "size": path.stat().st_size}
        for path in sorted(artifacts, key=lambda item: item.name)
    ]
    if len({item["filename"] for item in records}) != len(records):
        raise ValueError("artifact filenames must be unique")
    checksums = "".join(f"{item['sha256']}  {item['filename']}\n" for item in records)
    (output / "SHA256SUMS").write_text(checksums, encoding="utf-8", newline="\n")

    components = []
    for item in lock["dependencies"]:
        components.append({
            "type": "library",
            "name": item["name"],
            "version": item["version"],
            "scope": "required",
            "purl": f"pkg:pypi/{item['name']}@{item['version']}",
            "externalReferences": [{"type": "distribution", "url": item["source"]}],
            "properties": [{"name": "tailtrail:dependency-scope", "value": item["scope"]}],
        })
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{commit[:8]}-{commit[8:12]}-4{commit[13:16]}-a{commit[17:20]}-{commit[20:32]}",
        "version": 1,
        "metadata": {
            "component": {"type": "application", "name": "tailtrail", "version": "0.6.0"},
            "properties": [{"name": "tailtrail:runtime-dependency-count", "value": "0"}],
        },
        "components": components,
    }
    write_json(output / "tailtrail.cdx.json", sbom)

    provenance = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": item["filename"], "digest": {"sha256": item["sha256"]}} for item in records],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": "https://tailtrail.local/build-types/python-distribution/v1",
                "externalParameters": {"source_date_epoch": epoch},
                "internalParameters": {"build_dependencies": dependencies(lock)},
                "resolvedDependencies": [{"uri": f"git+{repository}", "digest": {"gitCommit": commit}}],
            },
            "runDetails": {
                "builder": {"id": "https://github.com/actions/runner" if os.environ.get("GITHUB_ACTIONS") == "true" else "local-untrusted"},
                "metadata": {"invocationId": os.environ.get("GITHUB_RUN_ID", "local"), "reproducible": True},
            },
        },
    }
    write_json(output / "provenance-candidate.json", provenance)

    evidence = {
        "schema_version": "1",
        "type": "tailtrail-release-evidence",
        "source": {"repository": repository, "commit": commit},
        "build": {"source_date_epoch": epoch, "dependencies": dependencies(lock)},
        "artifacts": records,
        "sbom": "tailtrail.cdx.json",
        "provenance": "provenance-candidate.json",
        "attestation": "required-on-tag",
        "valid": True,
    }
    write_json(output / "release-evidence.json", evidence)
    return evidence


def verify_bundle(artifacts: list[Path], bundle: Path, *, require_attestation: bool = False) -> list[str]:
    issues: list[str] = []
    try:
        evidence = read_json(bundle / "release-evidence.json")
        sbom = read_json(bundle / str(evidence["sbom"]))
        provenance = read_json(bundle / str(evidence["provenance"]))
    except (OSError, KeyError, json.JSONDecodeError, TypeError) as error:
        return [f"evidence bundle is unreadable: {error}"]
    expected = {item["filename"]: item for item in evidence.get("artifacts", [])}
    actual_names = {path.name for path in artifacts}
    if actual_names != set(expected):
        issues.append(f"artifact inventory mismatch: expected {sorted(expected)}, got {sorted(actual_names)}")
    for path in artifacts:
        item = expected.get(path.name)
        if item and (digest(path) != item.get("sha256") or path.stat().st_size != item.get("size")):
            issues.append(f"artifact digest or size mismatch: {path.name}")
    checksum_lines = (bundle / "SHA256SUMS").read_text(encoding="utf-8").splitlines() if (bundle / "SHA256SUMS").is_file() else []
    wanted_lines = [f"{item['sha256']}  {item['filename']}" for item in evidence.get("artifacts", [])]
    if checksum_lines != wanted_lines:
        issues.append("SHA256SUMS does not exactly match release evidence")
    subjects = {item.get("name"): item.get("digest", {}).get("sha256") for item in provenance.get("subject", [])}
    if subjects != {name: item["sha256"] for name, item in expected.items()}:
        issues.append("provenance subjects do not match release evidence")
    resolved = provenance.get("predicate", {}).get("buildDefinition", {}).get("resolvedDependencies", [])
    provenance_commit = resolved[0].get("digest", {}).get("gitCommit") if resolved else None
    if provenance_commit != evidence.get("source", {}).get("commit"):
        issues.append("provenance source commit does not match release evidence")
    if sbom.get("bomFormat") != "CycloneDX" or sbom.get("specVersion") != "1.6":
        issues.append("SBOM is not CycloneDX 1.6")
    components = {f"{item.get('name')}=={item.get('version')}" for item in sbom.get("components", [])}
    if components != set(evidence.get("build", {}).get("dependencies", [])):
        issues.append("SBOM dependency inventory does not match locked build inputs")
    if sbom.get("metadata", {}).get("properties") != [{"name": "tailtrail:runtime-dependency-count", "value": "0"}]:
        issues.append("SBOM runtime dependency declaration is missing or changed")
    if require_attestation and evidence.get("attestation") != "identity-attested":
        issues.append("identity-backed release attestation is required")
    if evidence.get("valid") is not True:
        issues.append("release evidence is not marked valid")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--artifact", type=Path, action="append", required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--repository", default=os.environ.get("GITHUB_SERVER_URL", "https://github.com") + "/" + os.environ.get("GITHUB_REPOSITORY", "local/tailtrail"))
    create.add_argument("--commit", default=os.environ.get("GITHUB_SHA") or git_value("rev-parse", "HEAD"))
    create.add_argument("--source-date-epoch", type=int, default=1704067200)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--artifact", type=Path, action="append", required=True)
    verify.add_argument("--bundle", type=Path, required=True)
    verify.add_argument("--require-attestation", action="store_true")
    args = parser.parse_args()
    if args.action == "create":
        try:
            payload = create_bundle(args.artifact, args.output, args.repository, args.commit, args.source_date_epoch)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
            print(json.dumps({"schema_version": "1", "type": "tailtrail-release-evidence", "valid": False, "issues": [str(error)]}, indent=2, sort_keys=True))
            return 1
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    issues = verify_bundle(args.artifact, args.bundle, require_attestation=args.require_attestation)
    print(json.dumps({"schema_version": "1", "type": "tailtrail-supply-chain-verification", "valid": not issues, "issues": issues}, indent=2, sort_keys=True))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
