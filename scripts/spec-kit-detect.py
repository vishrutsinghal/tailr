#!/usr/bin/env python3
"""Read-only Spec Kit workspace detection and compatibility reporting."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FEATURE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
KIND_PATHS = {
    ".specify/memory/constitution.md": "constitution",
    "spec.md": "spec",
    "plan.md": "plan",
    "tasks.md": "tasks",
    "research.md": "research",
}


def policy_module() -> Any:
    spec = importlib.util.spec_from_file_location("tailtrail_spec_kit_policy", ROOT / "scripts" / "spec-kit-policy.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


POLICY = policy_module()


def inside(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact(root: Path, path: Path, kind: str, max_bytes: int, total: list[int], issues: list[str]) -> dict[str, Any] | None:
    if not inside(root, path):
        issues.append(f"path escapes selected workspace: {path}")
        return None
    if path.suffix.lower() not in POLICY.ALLOWED_EXTENSIONS:
        issues.append(f"unsupported artifact extension: {path.relative_to(root).as_posix()}")
        return None
    size = path.stat().st_size
    relative = path.relative_to(root).as_posix()
    if size > max_bytes:
        issues.append(f"artifact exceeds policy size limit: {relative}")
        return None
    total[0] += size
    return {"path": relative, "kind": kind, "sha256": f"sha256:{sha256(path)}", "bytes": size}


def contract_artifacts(root: Path, feature_root: Path, max_bytes: int, total: list[int], issues: list[str]) -> list[dict[str, Any]]:
    contracts = feature_root / "contracts"
    if not contracts.is_dir() or not inside(root, contracts):
        return []
    result: list[dict[str, Any]] = []
    for path in sorted(contracts.rglob("*")):
        if not path.is_file():
            continue
        item = artifact(root, path, "contract", max_bytes, total, issues)
        if item:
            result.append(item)
    return result


def detect(root: Path, requested_feature: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    if requested_feature and not FEATURE_ID.fullmatch(requested_feature):
        raise ValueError("--feature must be a simple Spec Kit feature identifier")
    policy_result = POLICY.policy_status(root, None)
    if policy_result["state"] != "valid":
        return {"type": "tailtrail-spec-kit-detection", "schema_version": "1", "state": "incompatible", "read_only": True, "issues": [f"policy: {item}" for item in policy_result["issues"]], "boundary": "SK-1 performs read-only local discovery; no Spec Kit or TailTrail artifacts were written."}
    source = POLICY.load(root / ".tailtrail" / "spec-kit-policy.json") if policy_result["policy_source"] == "project" else POLICY.load(POLICY.TEMPLATE)
    limits = source["source"]
    total = [0]
    issues: list[str] = []
    artifacts: list[dict[str, Any]] = []
    constitution = root / ".specify" / "memory" / "constitution.md"
    if constitution.is_file():
        item = artifact(root, constitution, "constitution", limits["max_artifact_bytes"], total, issues)
        if item:
            artifacts.append(item)
    specs = root / "specs"
    features: list[dict[str, Any]] = []
    if specs.is_dir() and inside(root, specs):
        for feature_root in sorted(path for path in specs.iterdir() if path.is_dir() and FEATURE_ID.fullmatch(path.name) and inside(root, path)):
            if requested_feature and feature_root.name != requested_feature:
                continue
            feature_artifacts: list[dict[str, Any]] = []
            for name, kind in KIND_PATHS.items():
                if name.startswith("."):
                    continue
                path = feature_root / name
                if path.is_file():
                    item = artifact(root, path, kind, limits["max_artifact_bytes"], total, issues)
                    if item:
                        feature_artifacts.append(item)
            feature_artifacts.extend(contract_artifacts(root, feature_root, limits["max_artifact_bytes"], total, issues))
            artifacts.extend(feature_artifacts)
            features.append({
                "feature_id": feature_root.name,
                "artifacts": feature_artifacts,
                "readiness": "importable" if any(item["kind"] == "spec" for item in feature_artifacts) else "incomplete",
                "missing": [name for name in ("spec", "plan", "tasks") if not any(item["kind"] == name for item in feature_artifacts)],
            })
    if total[0] > limits["max_total_import_bytes"]:
        issues.append("discovered artifacts exceed policy total size limit")
    marker = (root / ".specify").is_dir()
    detected = marker or bool(features) or constitution.is_file()
    if requested_feature and not features:
        issues.append(f"requested feature not found: {requested_feature}")
    state = "not-detected" if not detected and not requested_feature else "compatible" if detected and not issues else "incompatible"
    source_hash = hashlib.sha256("\n".join(f"{item['path']}:{item['sha256']}" for item in sorted(artifacts, key=lambda entry: entry["path"])).encode("utf-8")).hexdigest() if artifacts else None
    return {
        "type": "tailtrail-spec-kit-detection",
        "schema_version": "1",
        "state": state,
        "read_only": True,
        "spec_kit_detected": detected,
        "policy_source": policy_result["policy_source"],
        "compatibility": "artifact-only-unversioned" if state == "compatible" else "not-applicable" if state == "not-detected" else "blocked",
        "source_revision": f"sha256:{source_hash}" if source_hash else None,
        "feature_count": len(features),
        "features": features,
        "artifacts": artifacts,
        "total_artifact_bytes": total[0],
        "issues": issues,
        "next": "Select an importable feature explicitly for SK-2." if state == "compatible" else "No Spec Kit import or execution was attempted.",
        "boundary": "SK-1 performs read-only local discovery; it does not run `specify`, create a TailTrail run, write a lock, import artifacts, or modify project files.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("detect", "status", "inspect"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--feature")
    args = parser.parse_args()
    if args.action == "inspect" and not args.feature:
        parser.error("inspect requires --feature")
    try:
        result = detect(args.root, args.feature if args.action == "inspect" else None)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Spec Kit detection error: {error}")
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
