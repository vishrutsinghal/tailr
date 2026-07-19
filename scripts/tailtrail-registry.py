#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "tailtrail-registry.json"
SCHEMA_PATH = ROOT / "tailtrail-registry.schema.json"

REQUIRED_REGISTRY_KEYS = {"schema_version", "features"}
REQUIRED_FEATURE_KEYS = {
    "id",
    "title",
    "status",
    "surface",
    "roadmap_ref",
    "owner",
    "governance_class",
    "commands",
    "docs",
    "scripts",
    "tests",
    "mcp_tools",
    "requires_approval",
    "read_only",
    "evidence_label",
    "depends_on",
    "since_version",
    "deprecated_in_version",
}
STRING_LIST_FIELDS = {"commands", "docs", "scripts", "tests", "mcp_tools", "depends_on"}
STATUS_VALUES = {"planned", "implemented", "deprecated"}
SURFACE_VALUES = {"core", "extended"}
GOVERNANCE_CLASSES = {"governance", "product", "dev-experience", "benchmark", "telemetry"}
EVIDENCE_LABELS = {"none", "estimated", "local-evidence", "measured", "benchmark-measured"}
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COMMAND_PATTERN = re.compile(r"^tailtrail\s+([a-z0-9-]+)(?:\s+.*)?$")

WORKFLOW_FEATURES: dict[str, list[str]] = {
    "overview": ["navigator", "code-graph-mapper", "token-harness"],
    "implementation": ["navigator", "guardrails", "code-graph-mapper", "testing", "review"],
    "review": ["navigator", "review", "guardrails", "code-graph-mapper"],
    "qa": ["navigator", "testing", "quality-signals", "review"],
    "sonar": ["navigator", "quality-signals", "code-graph-mapper", "review"],
    "security": ["navigator", "security-vulnerability", "code-graph-mapper", "guardrails"],
    "release": ["navigator", "review", "quality-signals", "reporting", "meta-harness"],
    "harness": ["meta-harness", "reporting", "token-harness", "registry"],
}


def load_registry(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or REGISTRY_PATH).read_text(encoding="utf-8"))


def load_schema(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or SCHEMA_PATH).read_text(encoding="utf-8"))


def features(registry: dict[str, Any]) -> list[dict[str, Any]]:
    value = registry.get("features", [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def feature_by_id(registry: dict[str, Any], feature_id: str) -> dict[str, Any] | None:
    for feature in features(registry):
        if feature.get("id") == feature_id:
            return feature
    return None


def feature_map(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(feature["id"]): feature for feature in features(registry) if isinstance(feature.get("id"), str)}


def registry_surface_entries(registry: dict[str, Any], surface: str) -> dict[str, list[str]]:
    selected = [feature for feature in features(registry) if feature.get("surface") == surface and feature.get("status") == "implemented"]
    return {
        "docs": sorted({item for feature in selected for item in feature.get("docs", []) if isinstance(item, str)}),
        "scripts": sorted({item for feature in selected for item in feature.get("scripts", []) if isinstance(item, str)}),
        "commands": sorted({item for feature in selected for item in feature.get("commands", []) if isinstance(item, str)}),
        "features": sorted({str(feature["id"]) for feature in selected if isinstance(feature.get("id"), str)}),
    }


def mcp_projection(registry: dict[str, Any]) -> list[dict[str, Any]]:
    projection: list[dict[str, Any]] = []
    for feature in features(registry):
        tools = feature.get("mcp_tools")
        if not isinstance(tools, list):
            continue
        for tool in tools:
            if not isinstance(tool, str) or not tool:
                continue
            projection.append(
                {
                    "tool": tool,
                    "feature_id": feature.get("id"),
                    "feature_title": feature.get("title"),
                    "read_only": True,
                    "requires_approval": False,
                    "feature_read_only": feature.get("read_only"),
                    "feature_requires_approval": feature.get("requires_approval"),
                    "surface": feature.get("surface"),
                    "evidence_label": feature.get("evidence_label"),
                }
            )
    return projection


def workflow_projection(registry: dict[str, Any], workflow: str) -> dict[str, Any]:
    fmap = feature_map(registry)
    ids = WORKFLOW_FEATURES.get(workflow, WORKFLOW_FEATURES["implementation"])
    selected = [fmap[feature_id] for feature_id in ids if feature_id in fmap]
    return {
        "workflow": workflow,
        "feature_ids": [str(feature["id"]) for feature in selected],
        "commands": sorted({item for feature in selected for item in feature.get("commands", []) if isinstance(item, str)}),
        "docs": sorted({item for feature in selected for item in feature.get("docs", []) if isinstance(item, str)}),
        "scripts": sorted({item for feature in selected for item in feature.get("scripts", []) if isinstance(item, str)}),
        "evidence_labels": {str(feature["id"]): feature.get("evidence_label") for feature in selected},
    }


def evidence_label_for(registry: dict[str, Any], feature_id: str) -> str:
    feature = feature_by_id(registry, feature_id)
    if not feature:
        return "none"
    value = feature.get("evidence_label")
    return value if isinstance(value, str) else "none"


def discover_tailtrail_commands(root: Path = ROOT) -> set[str]:
    path = root / "scripts" / "tailtrail.py"
    if not path.is_file():
        return set()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    commands: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name) or target.id != "COMMANDS":
                continue
            if not isinstance(node.value, ast.Dict):
                continue
            for key in node.value.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    commands.add(key.value)
    return commands


def discover_scripts(root: Path = ROOT) -> set[str]:
    scripts_dir = root / "scripts"
    if not scripts_dir.is_dir():
        return set()
    return {path.relative_to(root).as_posix() for path in scripts_dir.glob("*.py")}


def command_root(command: str) -> str | None:
    match = COMMAND_PATTERN.match(command)
    if not match:
        return None
    return match.group(1)


def validate_registry(registry: dict[str, Any], root: Path = ROOT) -> list[str]:
    issues: list[str] = []
    installed_pack_without_tests = (root / ".tailtrail-install.json").is_file() and not (root / "tests").exists()
    installed_surface = None
    manifest_path = root / ".tailtrail-install.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(manifest, dict) and manifest.get("surface") in SURFACE_VALUES:
                installed_surface = manifest.get("surface")
        except (OSError, json.JSONDecodeError):
            installed_surface = None
    if not isinstance(registry, dict):
        return ["registry root must be an object"]

    missing_root = REQUIRED_REGISTRY_KEYS - set(registry)
    for key in sorted(missing_root):
        issues.append(f"registry missing required key `{key}`")

    extra_root = set(registry) - REQUIRED_REGISTRY_KEYS
    for key in sorted(extra_root):
        issues.append(f"registry has unexpected key `{key}`")

    if registry.get("schema_version") != "1":
        issues.append("schema_version must be `1`")

    raw_features = registry.get("features")
    if not isinstance(raw_features, list):
        issues.append("features must be a list")
        return issues
    if not raw_features:
        issues.append("features must not be empty")

    seen_ids: dict[str, int] = {}
    seen_scripts: dict[str, str] = {}
    claimed_command_roots: dict[str, str] = {}
    feature_ids: set[str] = set()

    for index, feature in enumerate(raw_features):
        if not isinstance(feature, dict):
            issues.append(f"features[{index}] must be an object")
            continue

        label = str(feature.get("id", f"features[{index}]"))
        feature_surface = feature.get("surface")
        skip_installed_file_checks = installed_surface == "core" and feature_surface == "extended"
        missing = REQUIRED_FEATURE_KEYS - set(feature)
        for key in sorted(missing):
            issues.append(f"{label} missing required key `{key}`")

        extra = set(feature) - REQUIRED_FEATURE_KEYS
        for key in sorted(extra):
            issues.append(f"{label} has unexpected key `{key}`")

        feature_id = feature.get("id")
        if not isinstance(feature_id, str) or not ID_PATTERN.match(feature_id):
            issues.append(f"{label} id must be kebab-case")
        else:
            feature_ids.add(feature_id)
            seen_ids[feature_id] = seen_ids.get(feature_id, 0) + 1

        if feature.get("status") not in STATUS_VALUES:
            issues.append(f"{label} status must be one of {sorted(STATUS_VALUES)}")
        if feature.get("surface") not in SURFACE_VALUES:
            issues.append(f"{label} surface must be one of {sorted(SURFACE_VALUES)}")
        if feature.get("governance_class") not in GOVERNANCE_CLASSES:
            issues.append(f"{label} governance_class must be one of {sorted(GOVERNANCE_CLASSES)}")
        if feature.get("evidence_label") not in EVIDENCE_LABELS:
            issues.append(f"{label} evidence_label must be one of {sorted(EVIDENCE_LABELS)}")

        for key in ("title", "roadmap_ref", "owner", "since_version"):
            if not isinstance(feature.get(key), str) or not feature.get(key):
                issues.append(f"{label} {key} must be a non-empty string")

        if not isinstance(feature.get("requires_approval"), bool):
            issues.append(f"{label} requires_approval must be a boolean")
        if not isinstance(feature.get("read_only"), bool):
            issues.append(f"{label} read_only must be a boolean")
        if feature.get("deprecated_in_version") is not None and not isinstance(feature.get("deprecated_in_version"), str):
            issues.append(f"{label} deprecated_in_version must be a string or null")

        for key in STRING_LIST_FIELDS:
            values = feature.get(key)
            if not isinstance(values, list):
                issues.append(f"{label} {key} must be a list")
                continue
            if any(not isinstance(item, str) for item in values):
                issues.append(f"{label} {key} must contain only strings")

        for field in ("docs", "scripts", "tests"):
            values = feature.get(field)
            if not isinstance(values, list):
                continue
            if skip_installed_file_checks:
                continue
            if field == "tests" and installed_pack_without_tests:
                continue
            for relative in values:
                if isinstance(relative, str) and not (root / relative).is_file():
                    issues.append(f"{label} listed {field[:-1]} missing: {relative}")

        scripts = feature.get("scripts")
        if isinstance(scripts, list):
            for relative in scripts:
                if not isinstance(relative, str):
                    continue
                owner = seen_scripts.get(relative)
                if owner is not None:
                    issues.append(f"script `{relative}` is claimed by both `{owner}` and `{label}`")
                else:
                    seen_scripts[relative] = label

        commands = feature.get("commands")
        if isinstance(commands, list):
            for command in commands:
                if not isinstance(command, str):
                    continue
                root_command = command_root(command)
                if root_command is None:
                    issues.append(f"{label} command must start with `tailtrail <command>`: {command}")
                    continue
                claimed_command_roots.setdefault(root_command, label)

        if feature.get("status") == "implemented":
            tests = feature.get("tests")
            if not isinstance(tests, list) or not tests:
                issues.append(f"{label} implemented feature must list at least one test file")
            if feature.get("governance_class") in {"benchmark", "telemetry"} and feature.get("evidence_label") == "none":
                issues.append(f"{label} benchmark/telemetry feature must not use evidence_label `none`")

    for feature_id, count in sorted(seen_ids.items()):
        if count > 1:
            issues.append(f"feature id `{feature_id}` is duplicated")

    for feature in features(registry):
        label = str(feature.get("id", "unknown"))
        depends_on = feature.get("depends_on")
        if not isinstance(depends_on, list):
            continue
        for dependency in depends_on:
            if isinstance(dependency, str) and dependency not in feature_ids:
                issues.append(f"{label} depends_on unknown feature `{dependency}`")
            if isinstance(dependency, str) and dependency in feature_ids:
                dependency_feature = feature_by_id(registry, dependency)
                if feature.get("surface") == "core" and dependency_feature and dependency_feature.get("surface") == "extended":
                    issues.append(f"{label} core feature must not depend on extended feature `{dependency}`")

    tailtrail_commands = discover_tailtrail_commands(root)
    for root_command in sorted(tailtrail_commands):
        if root_command not in claimed_command_roots:
            issues.append(f"tailtrail command `{root_command}` is not claimed by any registry feature")

    for feature in features(registry):
        label = str(feature.get("id", "unknown"))
        commands = feature.get("commands")
        if not isinstance(commands, list):
            continue
        for command in commands:
            if not isinstance(command, str):
                continue
            root_command = command_root(command)
            if root_command and tailtrail_commands and root_command not in tailtrail_commands:
                issues.append(f"{label} lists command `{command}` but `tailtrail {root_command}` is not dispatched")

    discovered_scripts = discover_scripts(root)
    for script in sorted(discovered_scripts - set(seen_scripts)):
        issues.append(f"script `{script}` is not claimed by any registry feature")

    return issues


def filtered_features(registry: dict[str, Any], surface: str | None, status: str | None) -> list[dict[str, Any]]:
    result = features(registry)
    if surface:
        result = [feature for feature in result if feature.get("surface") == surface]
    if status:
        result = [feature for feature in result if feature.get("status") == status]
    return result


def print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def command_list(args: argparse.Namespace) -> int:
    registry = load_registry()
    selected = filtered_features(registry, args.surface, args.status)
    if args.format == "json":
        print_json({"schema_version": registry.get("schema_version"), "features": selected})
        return 0

    print("TailTrail Feature Registry")
    print("")
    for feature in selected:
        commands = ", ".join(feature.get("commands", [])) or "no commands"
        print(f"- {feature['id']} [{feature['status']}/{feature['surface']}] {feature['title']} :: {commands}")
    return 0


def command_show(args: argparse.Namespace) -> int:
    registry = load_registry()
    feature = feature_by_id(registry, args.feature_id)
    if feature is None:
        print(f"Unknown registry feature: {args.feature_id}", file=sys.stderr)
        return 2
    if args.format == "json":
        print_json(feature)
        return 0

    print(f"# {feature['title']}")
    print("")
    print(f"- id: `{feature['id']}`")
    print(f"- status: `{feature['status']}`")
    print(f"- surface: `{feature['surface']}`")
    print(f"- roadmap: `{feature['roadmap_ref']}`")
    print(f"- evidence: `{feature['evidence_label']}`")
    print(f"- read_only: `{str(feature['read_only']).lower()}`")
    print(f"- requires_approval: `{str(feature['requires_approval']).lower()}`")
    for key in ("commands", "docs", "scripts", "tests", "mcp_tools", "depends_on"):
        print("")
        print(f"## {key.replace('_', ' ').title()}")
        values = feature.get(key, [])
        if values:
            for value in values:
                print(f"- `{value}`")
        else:
            print("- none")
    return 0


def command_surfaces(args: argparse.Namespace) -> int:
    registry = load_registry()
    grouped = {surface: registry_surface_entries(registry, surface) for surface in ("core", "extended")}

    if args.format == "json":
        print_json(grouped)
        return 0

    print("TailTrail Registry Surfaces")
    print("")
    for surface in ("core", "extended"):
        items = grouped[surface]["features"]
        print(f"{surface}: {len(items)}")
        for feature_id in items:
            feature = feature_by_id(registry, feature_id)
            title = feature.get("title") if feature else feature_id
            print(f"- {feature_id}: {title}")
        print("")
    return 0


def command_workflow(args: argparse.Namespace) -> int:
    registry = load_registry()
    payload = workflow_projection(registry, args.workflow)
    if args.format == "json":
        print_json(payload)
        return 0
    print(f"TailTrail Registry Workflow: {payload['workflow']}")
    print("")
    print("Features:")
    for feature_id in payload["feature_ids"]:
        print(f"- `{feature_id}`")
    print("")
    print("Commands:")
    for command in payload["commands"]:
        print(f"- `{command}`")
    return 0


def command_mcp(args: argparse.Namespace) -> int:
    registry = load_registry()
    payload = {"tools": mcp_projection(registry)}
    if args.format == "json":
        print_json(payload)
        return 0
    print("TailTrail Registry MCP Projection")
    print("")
    for item in payload["tools"]:
        approval = "approval required" if item["requires_approval"] else "no approval required"
        read_only = "read-only" if item["read_only"] else "write-capable"
        print(f"- `{item['tool']}` -> `{item['feature_id']}` ({read_only}, {approval})")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    registry = load_registry()
    issues = validate_registry(registry)
    if args.format == "json":
        print_json({"valid": not issues, "strict": args.strict, "issues": issues})
    elif issues:
        print("TailTrail registry validation issues:")
        for issue in issues:
            print(f"- {issue}")
        if not args.strict:
            print("")
            print("Advisory mode: exiting 0. Use --strict to fail on drift.")
    else:
        print("TailTrail registry validation passed.")
    return 1 if issues and args.strict else 0


def command_drift(args: argparse.Namespace) -> int:
    script = ROOT / "scripts" / "registry-drift.py"
    command = [sys.executable, script.as_posix(), "--since", args.since, "--format", args.format]
    if args.strict:
        command.append("--strict")
    return subprocess.run(command, check=False).returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect the TailTrail feature registry.")
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH, help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List registered TailTrail features.")
    list_parser.add_argument("--surface", choices=sorted(SURFACE_VALUES))
    list_parser.add_argument("--status", choices=sorted(STATUS_VALUES))
    list_parser.add_argument("--format", choices=("text", "json"), default="text")
    list_parser.set_defaults(func=command_list)

    show_parser = subparsers.add_parser("show", help="Show one registered feature.")
    show_parser.add_argument("feature_id")
    show_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    show_parser.set_defaults(func=command_show)

    surfaces_parser = subparsers.add_parser("surfaces", help="Show Core and Extended feature groups.")
    surfaces_parser.add_argument("--format", choices=("text", "json"), default="text")
    surfaces_parser.set_defaults(func=command_surfaces)

    workflow_parser = subparsers.add_parser("workflow", help="Show registry projection for a workflow.")
    workflow_parser.add_argument("workflow", choices=sorted(WORKFLOW_FEATURES))
    workflow_parser.add_argument("--format", choices=("text", "json"), default="text")
    workflow_parser.set_defaults(func=command_workflow)

    mcp_parser = subparsers.add_parser("mcp", help="Show MCP-safe tool projection from the registry.")
    mcp_parser.add_argument("--format", choices=("text", "json"), default="text")
    mcp_parser.set_defaults(func=command_mcp)

    validate_parser = subparsers.add_parser("validate", help="Validate registry structure and drift.")
    validate_parser.add_argument("--strict", action="store_true", help="Exit non-zero when registry drift is found.")
    validate_parser.add_argument("--format", choices=("text", "json"), default="text")
    validate_parser.set_defaults(func=command_validate)

    drift_parser = subparsers.add_parser("drift", help="Detect registry, command, roadmap, changelog, and public-claim drift.")
    drift_parser.add_argument("--strict", action="store_true", help="Exit non-zero when actionable drift is found.")
    drift_parser.add_argument("--since", default="HEAD", help="Git revision/range base used for changed-file detection.")
    drift_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    drift_parser.set_defaults(func=command_drift)

    return parser


def main(argv: list[str] | None = None) -> int:
    global REGISTRY_PATH
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.registry != REGISTRY_PATH:
        REGISTRY_PATH = args.registry
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
