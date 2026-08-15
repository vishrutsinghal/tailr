#!/usr/bin/env python3
"""Validate the local safety contract for a future TailTrail Spec Kit bridge."""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "spec-kit-bridge-policy.example.json"
DEFAULT_POLICY = Path(".tailtrail") / "spec-kit-policy.json"
REQUIRED = {"schema_version", "type", "compatibility", "source", "privacy", "approval", "retention"}
ALLOWED_EXTENSIONS = {".md", ".json", ".yaml", ".yml"}


def safe_path(root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    result = (candidate if candidate.is_absolute() else root / candidate).resolve()
    try:
        result.relative_to(root)
    except ValueError as error:
        raise ValueError("Spec Kit bridge policy must remain inside --root") from error
    return result


def load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("policy must contain one JSON object")
    return payload


def validate(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if set(payload) != REQUIRED:
        issues.append("policy must contain exactly the required top-level contract fields")
    if payload.get("schema_version") != "1": issues.append("schema_version must be `1`")
    if payload.get("type") != "tailtrail-spec-kit-bridge-policy": issues.append("type must be `tailtrail-spec-kit-bridge-policy`")
    compatibility = payload.get("compatibility")
    if not isinstance(compatibility, dict) or compatibility.get("source") != "github/spec-kit": issues.append("compatibility.source must be `github/spec-kit`")
    if not isinstance(compatibility, dict) or compatibility.get("artifact_mode") != "read-only-import": issues.append("compatibility.artifact_mode must be `read-only-import`")
    if not isinstance(compatibility, dict) or compatibility.get("pinned_versions_required_for_execution") is not True: issues.append("pinned_versions_required_for_execution must be true")
    source = payload.get("source")
    if not isinstance(source, dict):
        issues.append("source must be an object")
    else:
        roots = source.get("allowed_roots")
        if not isinstance(roots, list) or not roots or any(item not in {".specify", "specs"} for item in roots): issues.append("source.allowed_roots must contain only `.specify` and/or `specs`")
        extensions = source.get("allowed_extensions")
        if not isinstance(extensions, list) or not extensions or any(item not in ALLOWED_EXTENSIONS for item in extensions): issues.append("source.allowed_extensions contains an unsupported extension")
        for name in ("max_artifact_bytes", "max_total_import_bytes"):
            value = source.get(name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1 or value > 50 * 1024 * 1024: issues.append(f"source.{name} must be an integer from 1 to 52428800")
        if isinstance(source.get("max_artifact_bytes"), int) and isinstance(source.get("max_total_import_bytes"), int) and source["max_artifact_bytes"] > source["max_total_import_bytes"]: issues.append("max_artifact_bytes cannot exceed max_total_import_bytes")
    privacy = payload.get("privacy")
    if not isinstance(privacy, dict):
        issues.append("privacy must be an object")
    else:
        for name in ("store_raw_artifacts", "store_raw_prompts", "store_raw_logs"):
            if privacy.get(name) is not False: issues.append(f"privacy.{name} must be false")
        patterns = privacy.get("deny_reference_patterns")
        if not isinstance(patterns, list) or not patterns: issues.append("privacy.deny_reference_patterns must be a non-empty list")
        elif any(not isinstance(item, str) or len(item) > 200 for item in patterns): issues.append("privacy.deny_reference_patterns must contain short strings")
        else:
            for pattern in patterns:
                try: re.compile(pattern)
                except re.error: issues.append(f"privacy deny pattern is invalid: {pattern}")
    approval = payload.get("approval")
    if not isinstance(approval, dict) or approval.get("require_source_lock") is not True or approval.get("require_material_amendment_approval") is not True or approval.get("allow_automatic_spec_kit_execution") is not False:
        issues.append("approval must lock sources, require material-amendment approval, and disable automatic Spec Kit execution")
    retention = payload.get("retention")
    if not isinstance(retention, dict) or retention.get("keep_versioned_source_snapshots") is not True or not isinstance(retention.get("max_snapshots_per_feature"), int) or not 1 <= retention["max_snapshots_per_feature"] <= 1000:
        issues.append("retention must retain versioned snapshots with max_snapshots_per_feature from 1 to 1000")
    return issues


def policy_status(root: Path, policy: str | None) -> dict[str, Any]:
    root = root.resolve(); path = safe_path(root, policy or DEFAULT_POLICY)
    selected = path if path.is_file() else TEMPLATE
    payload = load(selected)
    issues = validate(payload)
    return {"type": "tailtrail-spec-kit-policy-status", "schema_version": "1", "state": "valid" if not issues else "invalid", "policy": path.relative_to(root).as_posix(), "policy_source": "project" if path.is_file() else "built-in-template", "issues": issues, "boundary": "SK-0 validates policy only. It does not detect, import, execute, or modify Spec Kit artifacts."}


def init_policy(root: Path, policy: str | None) -> dict[str, Any]:
    root = root.resolve(); path = safe_path(root, policy or DEFAULT_POLICY)
    if path.exists(): raise ValueError("policy already exists; validate or edit it explicitly rather than overwriting it")
    path.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(TEMPLATE, path)
    return {**policy_status(root, str(path)), "state": "created"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("check", "init"):
        command = sub.add_parser(action); command.add_argument("--root", type=Path, default=Path.cwd()); command.add_argument("--policy")
    command = sub.add_parser("contracts"); command.add_argument("--format", choices=("json",), default="json")
    args = parser.parse_args()
    try:
        if args.action == "contracts":
            files = ["schemas/spec-kit-source.schema.json", "schemas/spec-kit-import.schema.json", "schemas/spec-kit-mapping.schema.json", "schemas/spec-kit-amendment.schema.json", "schemas/spec-kit-convergence.schema.json"]
            invalid = [item for item in files if not isinstance(load(ROOT / item), dict)]
            result = {"type": "tailtrail-spec-kit-contracts", "schema_version": "1", "state": "valid" if not invalid else "invalid", "contracts": files, "issues": invalid}
        else:
            result = policy_status(args.root, args.policy) if args.action == "check" else init_policy(args.root, args.policy)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Spec Kit bridge policy error: {error}"); return 2
    print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["state"] in {"valid", "created"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
