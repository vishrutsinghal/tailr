#!/usr/bin/env python3
"""Validate structured Dependency Gate decisions and match them to a diff."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"schema_version", "type", "decision_id", "status", "package", "version", "manifest_paths", "problem", "alternatives", "rationale", "owner", "validation", "rollback"}
PACKAGE_PATTERN = re.compile(r"^[A-Za-z0-9_.@/-]+$")


def load_guardrail():
    path = ROOT / "scripts" / "guardrail-check.py"
    spec = importlib.util.spec_from_file_location("tailtrail_dependency_guardrail", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GUARD = load_guardrail()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"unable to read {path}: {error}") from error


def validate_decision(value: Any, source: Path) -> list[str]:
    if not isinstance(value, dict):
        return [f"{source}: decision must be an object"]
    errors = [f"{source}: missing `{key}`" for key in sorted(REQUIRED - set(value))]
    if value.get("schema_version") != "1":
        errors.append(f"{source}: schema_version must be `1`")
    if value.get("type") != "tailtrail-dependency-decision":
        errors.append(f"{source}: type must be `tailtrail-dependency-decision`")
    if value.get("status") not in {"approved", "deferred", "rejected"}:
        errors.append(f"{source}: status must be approved, deferred, or rejected")
    if not isinstance(value.get("package"), str) or not PACKAGE_PATTERN.fullmatch(value.get("package", "")):
        errors.append(f"{source}: package must be a package identifier")
    for field in ("decision_id", "version", "problem", "rationale", "owner", "rollback"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            errors.append(f"{source}: {field} must be a non-empty string")
    for field in ("manifest_paths", "alternatives", "validation"):
        if not isinstance(value.get(field), list) or not value[field] or not all(isinstance(item, str) and item.strip() for item in value[field]):
            errors.append(f"{source}: {field} must be a non-empty list of strings")
    return errors


def decision_files(root: Path, directory: str) -> list[Path]:
    location = root / directory
    if not location.is_dir():
        return []
    return sorted(location.glob("*.json"))


def read_decisions(root: Path, directory: str) -> tuple[list[dict[str, Any]], list[str]]:
    decisions: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in decision_files(root, directory):
        try:
            value = json.loads(read_text(path))
        except (ValueError, json.JSONDecodeError) as error:
            errors.append(str(error))
            continue
        errors.extend(validate_decision(value, path))
        if not errors or not any(item.startswith(f"{path}:") for item in errors):
            value["_source"] = path.relative_to(root).as_posix()
            decisions.append(value)
    return decisions, errors


def dependency_name(text: str) -> str | None:
    requirement = re.match(r"\s*([A-Za-z0-9_.-]+)(?:\[[^]]+\])?\s*(?:[<>=!~]|$)", text)
    if requirement:
        return requirement.group(1).lower()
    json_entry = re.search(r'"([^"\s]+)"\s*:\s*"[^"\s]+"', text)
    if json_entry:
        return json_entry.group(1).lower()
    return None


def additions(diff: str) -> list[dict[str, str]]:
    lines, _files = GUARD.parse_diff(diff)
    result: list[dict[str, str]] = []
    for line in lines:
        if line.kind == "added" and GUARD.is_dependency_file(line.path) and GUARD.looks_like_dependency_addition(line):
            result.append({"path": line.path, "package": dependency_name(line.text) or "unknown", "evidence": line.text.strip()})
    return result


def matching_decision(change: dict[str, str], decisions: list[dict[str, Any]]) -> dict[str, Any] | None:
    for decision in decisions:
        if decision.get("status") != "approved" or change["path"] not in decision.get("manifest_paths", []):
            continue
        if change["package"] == "unknown" or str(decision.get("package", "")).lower() == change["package"]:
            return decision
    return None


def check(root: Path, directory: str, diff: str) -> dict[str, Any]:
    decisions, errors = read_decisions(root, directory)
    changes = additions(diff)
    missing = [change for change in changes if not matching_decision(change, decisions)]
    return {
        "type": "tailtrail-dependency-decision-check",
        "status": "passed" if not errors and not missing else "failed",
        "decision_directory": directory,
        "dependency_changes": changes,
        "validated_decisions": [{"decision_id": item["decision_id"], "package": item["package"], "source": item["_source"]} for item in decisions],
        "errors": errors,
        "missing_decisions": missing,
        "boundary": "This validates local decision records and diff evidence only. It does not install packages, fetch registries, approve a dependency, or replace project policy.",
    }


def render(data: dict[str, Any]) -> str:
    lines = ["# TailTrail Dependency Decision Check", "", f"- Status: `{data['status']}`", f"- Dependency changes: {len(data['dependency_changes'])}", f"- Approved decisions: {len(data['validated_decisions'])}", ""]
    if data["errors"] or data["missing_decisions"]:
        lines.extend(["## Required action", ""])
        lines.extend(f"- {item}" for item in data["errors"])
        lines.extend(f"- Add an approved decision for `{item['package']}` in `{item['path']}`." for item in data["missing_decisions"])
    lines.extend(["", "## Boundary", "", f"- {data['boundary']}", ""])
    return "\n".join(lines)


def staged_diff(root: Path) -> str:
    result = subprocess.run(["git", "diff", "--cached", "--unified=3"], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "git diff --cached failed")
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "check"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--decision-dir", default="tailtrail-meta/dependency-decisions")
    parser.add_argument("--diff", type=Path, help="Diff to check; defaults to staged Git diff.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    root = args.root.resolve()
    decisions, errors = read_decisions(root, args.decision_dir)
    if args.action == "validate":
        data = {"type": "tailtrail-dependency-decision-validation", "status": "passed" if not errors else "failed", "decision_directory": args.decision_dir, "validated_decisions": [{"decision_id": item["decision_id"], "package": item["package"], "source": item["_source"]} for item in decisions], "errors": errors, "dependency_changes": [], "missing_decisions": [], "boundary": "Validation checks local decision-record structure only."}
    else:
        try:
            diff = read_text(args.diff) if args.diff else staged_diff(root)
        except ValueError as error:
            parser.error(str(error))
        data = check(root, args.decision_dir, diff)
    print(json.dumps(data, indent=2) if args.format == "json" else render(data), end="")
    return 0 if data["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
