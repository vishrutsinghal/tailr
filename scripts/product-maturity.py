#!/usr/bin/env python3
"""Capture and enforce the PM-0 product-maturity baseline.

The baseline freezes public surface additions while TailTrail consolidates its
existing product. It inventories names and ownership, not source contents, so
correctness and maintainability work can continue without false freeze drift.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "tailtrail-meta" / "product-maturity-baseline-v1.json"
POLICY_PATH = ROOT / "tailtrail-meta" / "product-maturity-policy-v1.json"
SCENARIOS_PATH = ROOT / "benchmarks" / "product-maturity" / "pm0-scenarios-v1.json"
SCHEMA_PATH = ROOT / "schemas" / "product-maturity-baseline.schema.json"

BASELINE_VERSION = "1.0.0"
FREEZE_CATEGORIES = (
    "top_level_commands",
    "mcp_tools",
    "schema_paths",
    "hosts",
    "feature_ids",
    "ownership_domains",
)

OWNERSHIP: tuple[dict[str, str], ...] = (
    {"domain": "task-intent", "owner": "Navigator", "canonical_artifact": "Planning Lock"},
    {"domain": "requirements", "owner": "active requirement authority", "canonical_artifact": "approved anchor"},
    {"domain": "approval", "owner": "Durable Workflow Runtime", "canonical_artifact": "approval decision event"},
    {"domain": "workflow-stage", "owner": "Durable Workflow Runtime", "canonical_artifact": "workflow state projection"},
    {"domain": "execution-evidence", "owner": "Execution Evidence Bridge", "canonical_artifact": "run-local evidence stream"},
    {"domain": "requirement-status", "owner": "Requirement Completion Harness", "canonical_artifact": "requirement checkpoint"},
    {"domain": "drift", "owner": "Harness checkpoint", "canonical_artifact": "requirement-linked drift finding"},
    {"domain": "recovery", "owner": "Task Recovery Boundary", "canonical_artifact": "recovery plan and reconciliation"},
    {"domain": "debug-investigation", "owner": "Debug Harness", "canonical_artifact": "debug run artifacts"},
    {"domain": "closure", "owner": "Closure Finalizer", "canonical_artifact": "Completion Report"},
    {"domain": "tokens", "owner": "Token Harness", "canonical_artifact": "token ledger and linked telemetry"},
    {"domain": "learning", "owner": "Learning Governance", "canonical_artifact": "candidate and curated learning records"},
    {"domain": "evaluation", "owner": "Evaluation Harness", "canonical_artifact": "normalized evaluation event"},
    {"domain": "product-improvement", "owner": "Meta-Harness", "canonical_artifact": "approved improvement proposal"},
)

REQUIRED_OWNERSHIP_DOMAINS = {
    "requirements", "approval", "workflow-stage", "execution-evidence",
    "drift", "recovery", "closure", "tokens", "learning",
}

RATINGS: tuple[dict[str, Any], ...] = (
    {"area": "product-adoption-readiness", "current": 6.3, "target": 8.2, "evidence": ["README.md", "USER-GUIDE.md", "PRODUCT-MATURITY-IMPROVEMENT-PLAN.md"]},
    {"area": "developer-experience", "current": 5.9, "target": 8.5, "evidence": ["TAILTRAIL-COMMANDS.md", "scripts/tailtrail.py", "tests/test_cli_dispatch.py"]},
    {"area": "demonstrated-efficacy", "current": 5.8, "target": 8.3, "evidence": ["benchmarks/evaluation", "benchmarks/efficacy", "EVALUATION-HARNESS.md"]},
    {"area": "maintainability", "current": 6.2, "target": 8.2, "evidence": ["scripts/tailtrail.py", "scripts/task-start.py", "tailtrail-registry.json"]},
    {"area": "host-consistency", "current": 6.5, "target": 8.5, "evidence": ["adapters/host-compatibility-v1.json", "tests/test_host_runtime_conformance.py"]},
    {"area": "enterprise-readiness", "current": 6.7, "target": 8.2, "evidence": ["ENTERPRISE-READINESS-ASSESSMENT.md", "enterprise-closure-registry.json"]},
    {"area": "learning-effectiveness", "current": 7.0, "target": 8.3, "evidence": ["LEARNING-GOVERNANCE.md", "scripts/learning-agent.py", "tailtrail-closure-learning-automation-plan.md"]},
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def seal_payload(report: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in report.items() if key != "integrity"}
    return hashlib.sha256(canonical_json(unsigned)).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def discover_commands(root: Path) -> list[str]:
    tree = ast.parse((root / "scripts" / "tailtrail.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "COMMANDS" for target in node.targets):
            continue
        value = ast.literal_eval(node.value)
        return sorted(str(item) for item in value)
    raise RuntimeError("COMMANDS dictionary was not found in scripts/tailtrail.py")


def discover_mcp_tools(root: Path) -> list[str]:
    module = load_module("tailtrail_pm0_mcp_server", root / "scripts" / "mcp-server.py")
    return sorted(module.tool_definitions())


def discover_schemas(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in (root / "schemas").glob("*.schema.json"))


def discover_state_schemas(schema_paths: list[str]) -> list[str]:
    terms = ("state", "run-", "workflow", "anchor", "checkpoint", "closure", "evidence", "learning", "drift", "recovery", "debug")
    return [path for path in schema_paths if any(term in Path(path).name for term in terms)]


def discover_hosts(root: Path) -> list[dict[str, Any]]:
    contract = read_json(root / "adapters" / "host-compatibility-v1.json")
    result = []
    for host in contract.get("hosts", []):
        result.append(
            {
                "id": host.get("id"),
                "adapter_version": contract.get("adapter_version"),
                "qualification": host.get("qualification"),
                "supported": bool(host.get("supported")),
                "runtime_status": host.get("runtime_status"),
            }
        )
    return sorted(result, key=lambda item: str(item["id"]))


def discover_features(root: Path) -> list[dict[str, Any]]:
    registry = read_json(root / "tailtrail-registry.json")
    return sorted(
        (
            {
                "id": item.get("id"),
                "owner": item.get("owner"),
                "status": item.get("status"),
                "surface": item.get("surface"),
            }
            for item in registry.get("features", [])
            if isinstance(item, dict)
        ),
        key=lambda item: str(item["id"]),
    )


def git_value(root: Path, *args: str) -> str | None:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def build_inventory(root: Path) -> dict[str, Any]:
    schemas = discover_schemas(root)
    hosts = discover_hosts(root)
    features = discover_features(root)
    return {
        "top_level_commands": discover_commands(root),
        "mcp_tools": discover_mcp_tools(root),
        "schema_paths": schemas,
        "state_schema_paths": discover_state_schemas(schemas),
        "hosts": hosts,
        "features": features,
        "ownership": [
            {
                **item,
                "transition_authority": "Durable Workflow Runtime",
                "projection": "canonical artifact referenced by the workflow stage result",
            }
            for item in OWNERSHIP
        ],
    }


def build_report(root: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": "1",
        "type": "tailtrail-product-maturity-baseline",
        "baseline_version": BASELINE_VERSION,
        "program_phase": "PM-0",
        "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "captured_revision": git_value(root, "rev-parse", "HEAD") or "unavailable",
        "freeze": read_json(root / POLICY_PATH.relative_to(ROOT))["freeze"],
        "compatibility": read_json(root / POLICY_PATH.relative_to(ROOT))["compatibility"],
        "inventory": build_inventory(root),
        "ratings": list(RATINGS),
        "usability_scenarios": read_json(root / SCENARIOS_PATH.relative_to(ROOT))["scenarios"],
        "boundaries": {
            "inventory_scope": "Public names and canonical ownership are frozen; implementation contents may change.",
            "signature": "SHA-256 integrity seal detects artifact modification. It is not an organizational identity signature.",
            "telemetry": "No network, model, scanner, source execution, or hidden telemetry is used.",
        },
    }
    report["integrity"] = {
        "algorithm": "sha256",
        "canonicalization": "sorted compact JSON excluding integrity",
        "digest": seal_payload(report),
    }
    return report


def category_values(inventory: dict[str, Any], category: str) -> set[str]:
    if category in {"top_level_commands", "mcp_tools", "schema_paths"}:
        return {str(item) for item in inventory.get(category, [])}
    if category == "hosts":
        return {str(item.get("id")) for item in inventory.get("hosts", [])}
    if category == "feature_ids":
        return {str(item.get("id")) for item in inventory.get("features", [])}
    if category == "ownership_domains":
        return {str(item.get("domain")) for item in inventory.get("ownership", [])}
    return set()


def validate_policy(policy: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if policy.get("schema_version") != "1":
        issues.append("policy schema_version must be `1`")
    freeze = policy.get("freeze", {})
    if freeze.get("state") != "active":
        issues.append("PM-0 feature freeze must remain active")
    if set(freeze.get("categories", [])) != set(FREEZE_CATEGORIES):
        issues.append("freeze categories do not match the PM-0 contract")
    approved = freeze.get("approved_additions", {})
    if set(approved) != set(FREEZE_CATEGORIES):
        issues.append("approved_additions must declare every freeze category")
    for category, entries in approved.items():
        if category not in FREEZE_CATEGORIES or not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict) or not all(entry.get(key) for key in ("id", "approved_by", "reason")):
                issues.append(f"approved addition in `{category}` needs id, approved_by, and reason")
    compatibility = policy.get("compatibility", {})
    if int(compatibility.get("minimum_release_window", 0)) < 2:
        issues.append("compatibility minimum_release_window must be at least 2 releases")
    for item in compatibility.get("deprecations", []):
        if not all(item.get(key) for key in ("category", "id", "announced_in", "remove_after", "replacement", "reason")):
            issues.append("every deprecation needs category, id, announced_in, remove_after, replacement, and reason")
    return issues


def validate_ownership(inventory: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    domains: set[str] = set()
    for item in inventory.get("ownership", []):
        domain = str(item.get("domain", ""))
        if not all(item.get(key) for key in ("domain", "owner", "canonical_artifact", "transition_authority", "projection")):
            issues.append("every ownership entry needs domain, owner, canonical_artifact, transition_authority, and projection")
        if domain in domains:
            issues.append(f"ownership domain `{domain}` is ambiguous")
        domains.add(domain)
    missing = sorted(REQUIRED_OWNERSHIP_DOMAINS - domains)
    if missing:
        issues.append("canonical ownership matrix is missing: " + ", ".join(missing))
    return issues


def validate_scenarios(value: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    scenarios = value.get("scenarios", [])
    ids: set[str] = set()
    for item in scenarios:
        scenario_id = str(item.get("id", ""))
        if scenario_id in ids:
            issues.append(f"usability scenario `{scenario_id}` is duplicated")
        ids.add(scenario_id)
        if not all(item.get(key) for key in ("id", "level", "prompt", "expected_surface", "required_assertions")):
            issues.append(f"usability scenario `{scenario_id or '<missing>'}` is incomplete")
    if len(scenarios) < 6:
        issues.append("PM-0 requires at least six baseline usability/regression scenarios")
    return issues


def validate(root: Path, baseline_path: Path = BASELINE_PATH) -> dict[str, Any]:
    baseline = read_json(root / baseline_path.relative_to(ROOT))
    policy = read_json(root / POLICY_PATH.relative_to(ROOT))
    scenarios = read_json(root / SCENARIOS_PATH.relative_to(ROOT))
    issues = validate_policy(policy) + validate_scenarios(scenarios)
    expected_digest = str(baseline.get("integrity", {}).get("digest", ""))
    actual_digest = seal_payload(baseline)
    if expected_digest != actual_digest:
        issues.append("baseline integrity seal does not match its canonical payload")
    if baseline.get("baseline_version") != BASELINE_VERSION:
        issues.append(f"baseline_version must be `{BASELINE_VERSION}`")
    baseline_inventory = baseline.get("inventory", {})
    current_inventory = build_inventory(root)
    issues.extend(validate_ownership(current_inventory))
    approved = policy.get("freeze", {}).get("approved_additions", {})
    deprecations = {
        (str(item.get("category")), str(item.get("id")))
        for item in policy.get("compatibility", {}).get("deprecations", [])
    }
    drift: list[dict[str, Any]] = []
    for category in FREEZE_CATEGORIES:
        baseline_values = category_values(baseline_inventory, category)
        current_values = category_values(current_inventory, category)
        allowed = {str(item.get("id")) for item in approved.get(category, []) if item.get("approved_by") and item.get("reason")}
        additions = sorted(current_values - baseline_values - allowed)
        removals = sorted(value for value in baseline_values - current_values if (category, value) not in deprecations)
        if additions or removals:
            drift.append({"category": category, "unapproved_additions": additions, "unannounced_removals": removals})
            if additions:
                issues.append(f"{category} has unapproved additions: {', '.join(additions)}")
            if removals:
                issues.append(f"{category} has unannounced removals: {', '.join(removals)}")
    baseline_domains = category_values(baseline_inventory, "ownership_domains")
    if baseline_domains != category_values(current_inventory, "ownership_domains"):
        issues.append("canonical ownership domain set changed")
    return {
        "type": "tailtrail-product-maturity-baseline-validation",
        "baseline_version": baseline.get("baseline_version"),
        "status": "passed" if not issues else "failed",
        "integrity": "passed" if expected_digest == actual_digest else "failed",
        "feature_freeze": "passed" if not drift else "failed",
        "ownership": "passed" if not validate_ownership(current_inventory) else "failed",
        "scenario_count": len(scenarios.get("scenarios", [])),
        "drift": drift,
        "issues": issues,
        "boundary": "Read-only local validation; no source, Git, network, host, model, scanner, or runtime task was changed or executed.",
    }


def render_markdown(value: dict[str, Any]) -> str:
    if value.get("type") == "tailtrail-product-maturity-baseline-validation":
        lines = [
            "# TailTrail Product Maturity PM-0 Validation",
            "",
            f"**Baseline:** `{value.get('baseline_version')}`",
            f"**Status:** `{value.get('status')}`",
            f"**Integrity:** `{value.get('integrity')}`",
            f"**Feature freeze:** `{value.get('feature_freeze')}`",
            f"**Ownership:** `{value.get('ownership')}`",
            f"**Usability/regression scenarios:** `{value.get('scenario_count')}`",
            "",
        ]
        if value.get("issues"):
            lines.extend(["## Issues", "", *[f"- {item}" for item in value["issues"]], ""])
        else:
            lines.extend(["No unapproved public-surface drift or ambiguous ownership was detected.", ""])
        lines.append(str(value.get("boundary")))
        return "\n".join(lines)
    inventory = value["inventory"]
    lines = [
        "# TailTrail Product Maturity PM-0 Baseline",
        "",
        f"**Version:** `{value['baseline_version']}`",
        f"**Captured:** `{value['captured_at']}`",
        f"**Integrity:** `sha256:{value['integrity']['digest']}`",
        f"**Freeze:** `{value['freeze']['state']}`",
        "",
        "| Inventory | Count |",
        "| --- | ---: |",
        f"| Top-level commands | {len(inventory['top_level_commands'])} |",
        f"| MCP tools | {len(inventory['mcp_tools'])} |",
        f"| Schemas | {len(inventory['schema_paths'])} |",
        f"| State-related schemas | {len(inventory['state_schema_paths'])} |",
        f"| Hosts | {len(inventory['hosts'])} |",
        f"| Registered features | {len(inventory['features'])} |",
        f"| Canonical ownership domains | {len(inventory['ownership'])} |",
        f"| Usability/regression scenarios | {len(value['usability_scenarios'])} |",
        "",
        "## Ratings Below 8",
        "",
        "| Area | Current | Target |",
        "| --- | ---: | ---: |",
        *[f"| {item['area']} | {item['current']} | {item['target']} |" for item in value["ratings"]],
        "",
        "The SHA-256 seal detects artifact changes; it is not an organizational identity signature.",
    ]
    return "\n".join(lines)


def output(value: dict[str, Any], fmt: str) -> None:
    print(json.dumps(value, indent=2, sort_keys=True) if fmt == "json" else render_markdown(value))


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture and validate the TailTrail PM-0 product-maturity baseline.")
    parser.add_argument("command", choices=("baseline", "inventory", "validate", "status"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--approved", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command in {"validate", "status"}:
        result = validate(root)
        output(result, args.format)
        return 0 if result["status"] == "passed" else 1
    report = build_report(root)
    if args.command == "inventory":
        output({"type": "tailtrail-product-maturity-inventory", "baseline_version": BASELINE_VERSION, "inventory": report["inventory"]}, args.format)
        return 0
    if args.write:
        if not args.approved:
            raise SystemExit("--write requires --approved because it replaces the committed PM-0 baseline")
        destination = root / BASELINE_PATH.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output(report, args.format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
