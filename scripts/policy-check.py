#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY_NAME = "tailtrail-policy.md"
POLICY_EXAMPLE = ROOT / "tailtrail-policy.example.md"
OVERRIDE_TEMPLATE = ROOT / "templates" / "policy-overrides.json"
LOCAL_OVERRIDE = Path(".tailtrail") / "policy-overrides.json"

REQUIRED_HEADINGS = (
    "## Project Scope",
    "## Local Commands",
    "## Dependency Policy",
    "## Testing And Validation",
    "## Security And Data",
    "## API And Code Conventions",
    "## Review And Handoff",
    "## CI, Sonar, And Release",
    "## Local TailTrail Overrides",
    "## Code Intelligence Policy",
)

REQUIRED_OVERRIDE_KEYS = (
    "schema_version",
    "dependency_policy",
    "validation",
    "security",
    "ci_sonar",
    "ownership",
    "boundaries",
    "data_privacy",
    "release",
)


@dataclass
class CheckResult:
    ok: bool
    errors: list[str]
    warnings: list[str]
    files_checked: list[str]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise SystemExit(f"Unable to read {path}: {error}") from error


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid JSON in {path}: {error}") from error
    except OSError as error:
        raise SystemExit(f"Unable to read {path}: {error}") from error
    if not isinstance(value, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return value


def check_markdown_policy(path: Path, strict: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not path.exists():
        errors.append(f"missing {path}")
        return errors, warnings

    body = read_text(path)
    for heading in REQUIRED_HEADINGS:
        if heading not in body:
            errors.append(f"{path} missing required heading: {heading}")

    if "This file is guidance, not a hidden policy engine." not in body:
        warnings.append(f"{path} should state that local policy is guidance, not a hidden policy engine")
    if "DEPENDENCY-GATE.md" not in body:
        warnings.append(f"{path} should reference DEPENDENCY-GATE.md for dependency changes")
    if "GUARDRAILS.md" not in body:
        warnings.append(f"{path} should reference GUARDRAILS.md or say local policy does not weaken guardrails")
    if strict:
        placeholders = ("Project name:", "Primary owners:", "- Format:", "- Unit test:", "- Required approval owner:")
        for placeholder in placeholders:
            if placeholder in body:
                warnings.append(f"{path} still contains starter placeholder: {placeholder}")
    return errors, warnings


def check_policy_overrides(path: Path, strict: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not path.exists():
        warnings.append(f"optional structured overrides not found: {path}")
        return errors, warnings

    value = read_json(path)
    for key in REQUIRED_OVERRIDE_KEYS:
        if key not in value:
            errors.append(f"{path} missing required key: {key}")
    if str(value.get("schema_version", "")) != "1":
        errors.append(f"{path} schema_version must be '1'")

    for key in ("dependency_policy", "validation", "security", "ci_sonar", "ownership", "boundaries", "data_privacy", "release"):
        if key in value and not isinstance(value[key], dict):
            errors.append(f"{path}.{key} must be an object")

    boundaries = value.get("boundaries", {})
    if isinstance(boundaries, dict):
        for key in ("restricted_paths", "generated_paths", "vendor_paths"):
            if key in boundaries and not isinstance(boundaries[key], list):
                errors.append(f"{path}.boundaries.{key} must be a list")

    if strict:
        validation = value.get("validation", {})
        if isinstance(validation, dict) and not any(str(item).strip() for item in validation.values()):
            warnings.append(f"{path}.validation has no commands filled in")
    return errors, warnings


def run_check(root: Path, strict: bool, include_overrides: bool) -> CheckResult:
    files_checked: list[str] = []
    policy_path = root / POLICY_NAME
    errors, warnings = check_markdown_policy(policy_path, strict)
    files_checked.append(policy_path.as_posix())
    if include_overrides:
        override_path = root / LOCAL_OVERRIDE
        override_errors, override_warnings = check_policy_overrides(override_path, strict)
        errors.extend(override_errors)
        warnings.extend(override_warnings)
        files_checked.append(override_path.as_posix())
    return CheckResult(ok=not errors, errors=errors, warnings=warnings, files_checked=files_checked)


def render_result(result: CheckResult) -> str:
    lines = ["# TailTrail Policy Check", ""]
    lines.append(f"- Status: `{'passed' if result.ok else 'failed'}`")
    lines.append("- Files checked:")
    lines.extend(f"  - `{path}`" for path in result.files_checked)
    lines.extend(["", "## Errors", ""])
    if result.errors:
        lines.extend(f"- {error}" for error in result.errors)
    else:
        lines.append("- none")
    lines.extend(["", "## Warnings", ""])
    if result.warnings:
        lines.extend(f"- {warning}" for warning in result.warnings)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Policy checks validate shape and obvious gaps only.",
            "- Local policy can extend TailTrail guardrails but must not silently weaken them.",
            "- This script does not interpret every policy rule or enforce a hidden central policy engine.",
            "",
        ]
    )
    return "\n".join(lines)


def command_init(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    policy_target = root / POLICY_NAME
    override_target = root / LOCAL_OVERRIDE
    written: list[str] = []
    skipped: list[str] = []

    if policy_target.exists() and not args.force:
        skipped.append(policy_target.as_posix())
    else:
        policy_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(POLICY_EXAMPLE, policy_target)
        written.append(policy_target.as_posix())

    if args.with_overrides:
        if override_target.exists() and not args.force:
            skipped.append(override_target.as_posix())
        else:
            override_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(OVERRIDE_TEMPLATE, override_target)
            written.append(override_target.as_posix())

    print("TailTrail policy init")
    if written:
        print("Written:")
        for path in written:
            print(f"- {path}")
    if skipped:
        print("Skipped existing files:")
        for path in skipped:
            print(f"- {path}")
    print("Next: edit local policy values, then run policy-check.py check.")
    return 0


def command_check(args: argparse.Namespace) -> int:
    result = run_check(args.root.resolve(), args.strict, args.with_overrides)
    if args.format == "json":
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(render_result(result))
    return 0 if result.ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize and validate local TailTrail policy files.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create tailtrail-policy.md from the example.")
    init.add_argument("--root", type=Path, default=Path.cwd())
    init.add_argument("--with-overrides", action="store_true", help="Also create .tailtrail/policy-overrides.json.")
    init.add_argument("--force", action="store_true", help="Overwrite existing target policy files.")

    check = subparsers.add_parser("check", help="Validate local policy shape.")
    check.add_argument("--root", type=Path, default=Path.cwd())
    check.add_argument("--with-overrides", action="store_true", help="Also validate .tailtrail/policy-overrides.json.")
    check.add_argument("--strict", action="store_true", help="Warn about starter placeholders and empty command sections.")
    check.add_argument("--format", choices=("markdown", "json"), default="markdown")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "init":
        return command_init(args)
    if args.command == "check":
        return command_check(args)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
