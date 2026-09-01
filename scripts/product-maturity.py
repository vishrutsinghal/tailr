#!/usr/bin/env python3
"""Capture and enforce the PM-0 product-maturity baseline.

The baseline freezes public surface additions while TailTrail consolidates its
existing product. It inventories names and ownership, not source contents, so
correctness and maintainability work can continue without false freeze drift.
"""

from __future__ import annotations

import argparse
import ast
import copy
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
LEARNING_INVENTORY_PATH = ROOT / "tailtrail-meta" / "product-maturity-learning-inventory-v1.json"
LEARNING_SCHEMA_PATH = ROOT / "schemas" / "product-maturity-learning-inventory.schema.json"
LEARNING_V3_SCHEMA_PATH = ROOT / "schemas" / "learning-v3-record.schema.json"
LEARNING_USE_PROPOSAL_SCHEMA_PATH = ROOT / "schemas" / "learning-use-proposal.schema.json"
LEARNING_USE_RECEIPT_SCHEMA_PATH = ROOT / "schemas" / "learning-use-receipt-event.schema.json"
LEARNING_GOVERNANCE_SCHEMA_PATH = ROOT / "schemas" / "learning-governance-event.schema.json"
LEARNING_CALIBRATION_SCHEMAS = (
    ROOT / "schemas" / "learning-calibration-catalog.schema.json",
    ROOT / "schemas" / "learning-calibration-report.schema.json",
    ROOT / "schemas" / "learning-calibration-projection.schema.json",
)
ADOPTION_VALIDATION_SCHEMAS = (
    ROOT / "schemas" / "adoption-validation-catalog.schema.json",
    ROOT / "schemas" / "adoption-validation-trial.schema.json",
    ROOT / "schemas" / "adoption-validation-report.schema.json",
    ROOT / "schemas" / "adoption-improvement-decision.schema.json",
)

BASELINE_VERSION = "1.0.0"
LEARNING_INVENTORY_VERSION = "1.5.0"
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

LEARNING_FACT_OWNERSHIP: tuple[dict[str, str], ...] = (
    {"fact": "candidate", "owner": "Learning Agent", "canonical_artifact": ".tailtrail/learning-v3/events.jsonl", "state": "current"},
    {"fact": "curated-learning", "owner": "Learning Governance", "canonical_artifact": ".tailtrail/learning-v3/events.jsonl", "state": "current"},
    {"fact": "use-receipt", "owner": "Durable Workflow Runtime", "canonical_artifact": ".tailtrail/runs/<run-id>/learning/use-receipts.jsonl", "state": "current"},
    {"fact": "freshness-action", "owner": "Learning Refresh", "canonical_artifact": ".tailtrail/learning-refresh-actions.json", "state": "current"},
    {"fact": "conflict", "owner": "Learning Governance", "canonical_artifact": ".tailtrail/learning-conflicts.jsonl", "state": "current"},
    {"fact": "class-confidence-calibration", "owner": "Evaluation Harness", "canonical_artifact": ".tailtrail/learning-calibration.json", "state": "current"},
    {"fact": "observed-outcome", "owner": "Outcome Telemetry", "canonical_artifact": ".tailtrail/outcome-events.jsonl", "state": "current"},
)

LEARNING_SYSTEMS: tuple[dict[str, Any], ...] = (
    {"id": "learning-agent", "owner": "Learning Agent", "scripts": ["scripts/learning-v3.py", "scripts/learning-agent.py", "scripts/learnings.py"], "commands": ["tailtrail learn v3 validate|state|migrate|amend|revalidate|supersede|revoke", "tailtrail learn capture|score|search|promote|summarize|prune|rebuild-index", "tailtrail learn init|add|show"]},
    {"id": "learning-retrieval", "owner": "Navigator", "scripts": ["scripts/learning-retrieval.py", "scripts/navigator.py", "scripts/navigator_render.py", "scripts/task-start.py", "scripts/task-next.py"], "commands": ["tailtrail learn retrieve", "tailtrail navigator", "tailtrail start", "tailtrail next"]},
    {"id": "learning-receipts", "owner": "Durable Workflow Runtime", "scripts": ["scripts/learning-use-receipt.py", "scripts/completion-report.py"], "commands": ["tailtrail learn receipt record|attribute|show|validate", "tailtrail completion-report"]},
    {"id": "closure-learning", "owner": "Closure Finalizer", "scripts": ["scripts/closure-learning.py"], "commands": ["tailtrail closure learn"]},
    {"id": "debug-candidates", "owner": "Debug Harness", "scripts": ["scripts/debug-intake.py", "scripts/debug-reproduction.py", "scripts/debug-orientation.py", "scripts/debug-hypothesis.py", "scripts/debug-correction.py", "scripts/debug-harness-convergence.py", "scripts/debug-governance.py", "scripts/debug-evaluation.py", "scripts/debug-completion.py"], "commands": ["tailtrail debug"]},
    {"id": "graph-learning", "owner": "Code Graph Mapper", "scripts": ["scripts/graph-learning.py"], "commands": ["tailtrail learn graph"]},
    {"id": "learning-refresh", "owner": "Learning Refresh", "scripts": ["scripts/learning-refresh.py", "scripts/learning-review.py", "scripts/learning-governance.py"], "commands": ["tailtrail learn refresh", "tailtrail learn review", "tailtrail learn govern", "tailtrail learn governance"]},
    {"id": "learning-calibration", "owner": "Evaluation Harness", "scripts": ["scripts/learning-calibration.py", "scripts/learning-retrieval.py"], "commands": ["tailtrail learn calibration evaluate|validate|apply|meta-feed", "tailtrail eval learning evaluate|validate|apply|meta-feed"]},
    {"id": "quality-loop", "owner": "Quality Loop", "scripts": ["scripts/quality-loop.py"], "commands": ["tailtrail quality-loop"]},
    {"id": "evaluation-harness", "owner": "Evaluation Harness", "scripts": ["scripts/evaluation-harness.py"], "commands": ["tailtrail eval"]},
    {"id": "meta-harness", "owner": "Meta-Harness", "scripts": ["scripts/meta-harness-analyze.py", "scripts/meta-harness-propose.py"], "commands": ["tailtrail eval meta"]},
    {"id": "outcome-telemetry", "owner": "Outcome Telemetry", "scripts": ["scripts/outcome-telemetry.py"], "commands": ["tailtrail eval outcome"]},
    {"id": "workflow-learning-links", "owner": "Durable Workflow Runtime", "scripts": ["scripts/workflow_runtime/outcomes.py"], "commands": ["workflow outcome transitions"]},
)

LEARNING_ARTIFACTS: tuple[dict[str, Any], ...] = (
    {"id": "learning-v3-records", "system": "learning-agent", "path": ".tailtrail/learning-v3/events.jsonl", "role": "canonical", "mutable": True, "owner": "Learning Governance", "writers": ["scripts/learning-v3.py"]},
    {"id": "learning-v3-project-frame", "system": "learning-agent", "path": ".tailtrail/learning-v3/project-frame.json", "role": "configuration", "mutable": True, "owner": "Learning Governance", "writers": ["scripts/learning-v3.py"]},
    {"id": "learning-use-receipts", "system": "learning-receipts", "path": ".tailtrail/runs/<run-id>/learning/use-receipts.jsonl", "role": "canonical", "mutable": True, "owner": "Durable Workflow Runtime", "writers": ["scripts/learning-use-receipt.py"], "migration": "use-receipt-introduction"},
    {"id": "learning-candidates", "system": "learning-agent", "path": ".tailtrail/learning-events.jsonl", "role": "compatibility-projection", "mutable": True, "owner": "Learning Agent", "writers": ["scripts/learning-agent.py", "scripts/closure-learning.py"], "migration": "legacy-candidate-v3-reference"},
    {"id": "curated-learnings", "system": "learning-agent", "path": ".tailtrail/learnings.md", "role": "compatibility-projection", "mutable": True, "owner": "Learning Governance", "writers": ["scripts/learning-agent.py", "scripts/learnings.py"], "migration": "legacy-curated-writer"},
    {"id": "learning-scores", "system": "learning-agent", "path": ".tailtrail/learning-scores.jsonl", "role": "derived", "mutable": True, "owner": "Learning Agent", "writers": ["scripts/learning-agent.py", "scripts/closure-learning.py"]},
    {"id": "learning-index", "system": "learning-agent", "path": ".tailtrail/learning-index.md", "role": "derived", "mutable": True, "owner": "Learning Agent", "writers": ["scripts/learning-agent.py", "scripts/closure-learning.py"]},
    {"id": "learning-policy", "system": "learning-agent", "path": ".tailtrail/learning-policy.json", "role": "configuration", "mutable": True, "owner": "Learning Governance", "writers": ["scripts/learning-agent.py"]},
    {"id": "closure-candidate", "system": "closure-learning", "path": ".tailtrail/runs/<run-id>/positive-learning/<candidate-id>.json", "role": "source-by-reference", "mutable": False, "owner": "Closure Finalizer", "writers": ["scripts/closure-learning.py"], "migration": "closure-candidate-reference"},
    {"id": "debug-candidate-evidence", "system": "debug-candidates", "path": ".tailtrail/runs/<run-id>/debug/**", "role": "source-by-reference", "mutable": False, "owner": "Debug Harness", "writers": ["scripts/debug-intake.py", "scripts/debug-reproduction.py", "scripts/debug-orientation.py", "scripts/debug-hypothesis.py", "scripts/debug-correction.py", "scripts/debug-harness-convergence.py", "scripts/debug-governance.py", "scripts/debug-completion.py"], "migration": "debug-candidate-reference"},
    {"id": "debug-evaluation-report", "system": "debug-candidates", "path": ".tailtrail/evaluation/debug-harness/report-v1.json", "role": "domain-evidence", "mutable": True, "owner": "Debug Harness", "writers": ["scripts/debug-evaluation.py"]},
    {"id": "code-graph-cache", "system": "graph-learning", "path": ".tailtrail/code-graph-cache.json", "role": "source-by-reference", "mutable": True, "owner": "Code Graph Mapper", "writers": ["scripts/code-graph-mapper.py"]},
    {"id": "graph-learning-index", "system": "graph-learning", "path": ".tailtrail/graph-learning-index.json", "role": "derived", "mutable": True, "owner": "Code Graph Mapper", "writers": ["scripts/graph-learning.py"]},
    {"id": "learning-refresh-actions", "system": "learning-refresh", "path": ".tailtrail/learning-refresh-actions.json", "role": "canonical", "mutable": True, "owner": "Learning Refresh", "writers": ["scripts/learning-refresh.py"]},
    {"id": "learning-refresh-report", "system": "learning-refresh", "path": ".tailtrail/learning-refresh-report.md", "role": "derived", "mutable": True, "owner": "Learning Refresh", "writers": ["scripts/learning-refresh.py"]},
    {"id": "learning-governance-review", "system": "learning-refresh", "path": ".tailtrail/learning-governance-review.md", "role": "derived", "mutable": True, "owner": "Learning Governance", "writers": ["scripts/learning-review.py"]},
    {"id": "learning-conflicts", "system": "learning-refresh", "path": ".tailtrail/learning-conflicts.jsonl", "role": "canonical", "mutable": True, "owner": "Learning Governance", "writers": ["scripts/learning-governance.py"], "migration": "conflict-ledger-introduction"},
    {"id": "learning-calibration-catalog", "system": "learning-calibration", "path": "benchmarks/evaluation/learning-calibration/v1.json", "role": "domain-evidence", "mutable": False, "owner": "Evaluation Harness", "writers": []},
    {"id": "learning-calibration-report", "system": "learning-calibration", "path": ".tailtrail/evaluation/learning-calibration/report.json", "role": "derived", "mutable": True, "owner": "Evaluation Harness", "writers": ["scripts/learning-calibration.py"]},
    {"id": "learning-calibration-projection", "system": "learning-calibration", "path": ".tailtrail/learning-calibration.json", "role": "configuration", "mutable": True, "owner": "Evaluation Harness", "writers": ["scripts/learning-calibration.py"], "migration": "class-calibration-introduction"},
    {"id": "learning-calibration-meta-signals", "system": "learning-calibration", "path": ".tailtrail/evaluation/learning-calibration/meta-signals.jsonl", "role": "derived", "mutable": True, "owner": "Evaluation Harness", "writers": ["scripts/learning-calibration.py"]},
    {"id": "quality-events", "system": "quality-loop", "path": ".tailtrail/quality-events.jsonl", "role": "domain-evidence", "mutable": True, "owner": "Quality Loop", "writers": ["scripts/quality-loop.py"]},
    {"id": "quality-summary", "system": "quality-loop", "path": ".tailtrail/quality-summary.md", "role": "derived", "mutable": True, "owner": "Quality Loop", "writers": ["scripts/quality-loop.py"]},
    {"id": "quality-decisions", "system": "quality-loop", "path": ".tailtrail/quality-decisions.md", "role": "domain-evidence", "mutable": True, "owner": "Quality Loop", "writers": ["scripts/quality-loop.py"]},
    {"id": "evaluation-events", "system": "evaluation-harness", "path": ".tailtrail/evaluation/events.jsonl", "role": "domain-evidence", "mutable": True, "owner": "Evaluation Harness", "writers": ["scripts/evaluation-harness.py"]},
    {"id": "evaluation-scenario-results", "system": "evaluation-harness", "path": "benchmarks/evaluation/results/<scenario-id>-scenario-report.{json,md}", "role": "domain-evidence", "mutable": True, "owner": "Evaluation Harness", "writers": ["scripts/evaluation-harness.py"]},
    {"id": "harness-summary-source", "system": "meta-harness", "path": "tailtrail-meta/harness-summary.jsonl", "role": "source-by-reference", "mutable": True, "owner": "Harness Review", "writers": ["scripts/harness-review.py"]},
    {"id": "meta-analysis", "system": "meta-harness", "path": ".tailtrail/meta-harness-analysis.json", "role": "derived", "mutable": True, "owner": "Meta-Harness", "writers": ["scripts/meta-harness-analyze.py"]},
    {"id": "meta-analysis-markdown", "system": "meta-harness", "path": ".tailtrail/meta-harness-analysis.md", "role": "derived", "mutable": True, "owner": "Meta-Harness", "writers": ["scripts/meta-harness-analyze.py"]},
    {"id": "meta-readiness", "system": "meta-harness", "path": ".tailtrail/meta-harness-readiness.json", "role": "derived", "mutable": True, "owner": "Meta-Harness", "writers": ["scripts/meta-harness-analyze.py"]},
    {"id": "meta-readiness-markdown", "system": "meta-harness", "path": ".tailtrail/meta-harness-readiness.md", "role": "derived", "mutable": True, "owner": "Meta-Harness", "writers": ["scripts/meta-harness-analyze.py"]},
    {"id": "meta-proposals", "system": "meta-harness", "path": ".tailtrail/meta-harness-proposals.jsonl", "role": "domain-evidence", "mutable": True, "owner": "Meta-Harness", "writers": ["scripts/meta-harness-propose.py"]},
    {"id": "meta-latest-proposal", "system": "meta-harness", "path": ".tailtrail/meta-harness-proposal.md", "role": "derived", "mutable": True, "owner": "Meta-Harness", "writers": ["scripts/meta-harness-propose.py"]},
    {"id": "outcome-events", "system": "outcome-telemetry", "path": ".tailtrail/outcome-events.jsonl", "role": "canonical", "mutable": True, "owner": "Outcome Telemetry", "writers": ["scripts/outcome-telemetry.py"]},
    {"id": "outcome-summary", "system": "outcome-telemetry", "path": ".tailtrail/outcome-summary.md", "role": "derived", "mutable": True, "owner": "Outcome Telemetry", "writers": ["scripts/outcome-telemetry.py"]},
    {"id": "workflow-learning-link", "system": "workflow-learning-links", "path": ".tailtrail/runs/<run-id>/workflows/<workflow-id>/outcomes/<outcome-id>/learning-link-v1.json", "role": "source-by-reference", "mutable": False, "owner": "Durable Workflow Runtime", "writers": ["scripts/workflow_runtime/outcomes.py"]},
)

LEARNING_ALIASES: tuple[dict[str, Any], ...] = (
    {"alias": "tailtrail learn capture|promote", "canonical": "Learning V3 canonical write plus legacy compatibility projection", "state": "delegating-route", "minimum_release_window": 2, "preserves": ["approval", "privacy", "safety", "data"]},
    {"alias": "tailtrail learn agent <action>", "canonical": "tailtrail learn <action>", "state": "compatibility", "minimum_release_window": 2, "preserves": ["approval", "privacy", "safety", "data"]},
    {"alias": "tailtrail learnings <action>", "canonical": "tailtrail learn init|add|show", "state": "compatibility", "minimum_release_window": 2, "preserves": ["approval", "privacy", "safety", "data"]},
    {"alias": "tailtrail learn govern", "canonical": "tailtrail learn review", "state": "compatibility", "minimum_release_window": 2, "preserves": ["approval", "privacy", "safety", "data"]},
    {"alias": "tailtrail eval outcome <action>", "canonical": "Outcome Telemetry via Evaluation Harness", "state": "delegating-route", "minimum_release_window": 2, "preserves": ["approval", "privacy", "safety", "data"]},
    {"alias": "tailtrail eval learning <action>", "canonical": "tailtrail learn calibration <action>", "state": "delegating-route", "minimum_release_window": 2, "preserves": ["approval", "privacy", "safety", "data"]},
)

LEARNING_MIGRATIONS: tuple[dict[str, Any], ...] = (
    {"id": "legacy-candidate-v3-reference", "source": ".tailtrail/learning-events.jsonl", "target": ".tailtrail/learning-v3/events.jsonl", "phase": "current", "strategy": "retain the legacy store; append only sanitized candidate fields, project frame, source line reference, and source fingerprint", "preserve_existing": True, "minimum_release_window": 2},
    {"id": "legacy-curated-writer", "source": ".tailtrail/learnings.md via scripts/learnings.py", "target": ".tailtrail/learning-v3/events.jsonl via Learning Governance", "phase": "current", "strategy": "write the canonical V3 record first and retain the Markdown compatibility projection", "preserve_existing": True, "minimum_release_window": 2},
    {"id": "closure-candidate-reference", "source": ".tailtrail/runs/<run-id>/positive-learning/<candidate-id>.json", "target": ".tailtrail/learning-events.jsonl", "phase": "current", "strategy": "retain immutable run-local source and append a sanitized reference event", "preserve_existing": True, "minimum_release_window": 2},
    {"id": "debug-candidate-reference", "source": ".tailtrail/runs/<run-id>/debug/**", "target": ".tailtrail/learning-v3/events.jsonl", "phase": "current", "strategy": "retain run evidence and migrate only sanitized candidate references", "preserve_existing": True, "minimum_release_window": 2},
    {"id": "domain-evidence-join", "source": "Quality Loop, Evaluation Harness, Meta-Harness, graph, and outcome artifacts", "target": "Learning V3 provenance references", "phase": "current", "strategy": "join by reference; do not copy, overwrite, or reclassify source evidence", "preserve_existing": True, "minimum_release_window": 2},
    {"id": "use-receipt-introduction", "source": "workflow learning-link-v1.json", "target": ".tailtrail/runs/<run-id>/learning/use-receipts.jsonl", "phase": "current", "strategy": "retain workflow candidate links and introduce a distinct append-only decision and closure-attribution receipt contract", "preserve_existing": True, "minimum_release_window": 2},
    {"id": "conflict-ledger-introduction", "source": ".tailtrail/learning-governance-review.md and freshness actions", "target": ".tailtrail/learning-conflicts.jsonl", "phase": "current", "strategy": "introduce append-only challenge, conflict, revalidation, and negative-learning facts; preserve reports and actions as evidence", "preserve_existing": True, "minimum_release_window": 2},
    {"id": "class-calibration-introduction", "source": "validated later PM-L3 use receipt attributions", "target": ".tailtrail/learning-calibration.json", "phase": "current", "strategy": "derive a bounded project-framed class adjustment without changing V3 history or raw receipt evidence", "preserve_existing": True, "minimum_release_window": 2},
)

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


def build_learning_inventory(root: Path) -> dict[str, Any]:
    """Build the sealed PM-L0 ownership inventory without reading runtime stores."""
    report: dict[str, Any] = {
        "schema_version": "1",
        "type": "tailtrail-product-maturity-learning-inventory",
        "inventory_version": LEARNING_INVENTORY_VERSION,
        "program_phase": "PM-L0",
        "fact_ownership": copy.deepcopy(list(LEARNING_FACT_OWNERSHIP)),
        "systems": copy.deepcopy(list(LEARNING_SYSTEMS)),
        "artifacts": copy.deepcopy(list(LEARNING_ARTIFACTS)),
        "aliases": copy.deepcopy(list(LEARNING_ALIASES)),
        "migrations": copy.deepcopy(list(LEARNING_MIGRATIONS)),
        "boundaries": {
            "authority": "PM-L0 inventories and assigns ownership; PM-L1 through PM-L5 own contract, governance, calibration, and data migrations.",
            "preservation": "Existing stores remain in place and migration is by reference or compatibility routing; no artifact is silently discarded.",
            "privacy": "This committed inventory names paths and controls only; it never reads learning content, prompts, source, logs, or user data.",
            "ownership": "A script may delegate writes, but each fact and mutable artifact has exactly one canonical owner.",
        },
    }
    report["integrity"] = {
        "algorithm": "sha256",
        "canonicalization": "sorted compact JSON excluding integrity",
        "digest": seal_payload(report),
    }
    return report


def validate_learning_inventory(root: Path, value: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not (root / LEARNING_SCHEMA_PATH.relative_to(ROOT)).is_file():
        issues.append("PM-L0 learning inventory schema is missing")
    expected_keys = {"schema_version", "type", "inventory_version", "program_phase", "fact_ownership", "systems", "artifacts", "aliases", "migrations", "boundaries", "integrity"}
    if set(value) != expected_keys:
        issues.append("learning inventory top-level contract is not closed")
    if value.get("schema_version") != "1" or value.get("type") != "tailtrail-product-maturity-learning-inventory":
        issues.append("learning inventory identity must use schema version `1`")
    if value.get("inventory_version") != LEARNING_INVENTORY_VERSION or value.get("program_phase") != "PM-L0":
        issues.append(f"learning inventory must be PM-L0 version `{LEARNING_INVENTORY_VERSION}`")
    if value.get("integrity", {}).get("digest") != seal_payload(value):
        issues.append("learning inventory integrity seal does not match its canonical payload")

    required_facts = {item["fact"] for item in LEARNING_FACT_OWNERSHIP}
    fact_rows = value.get("fact_ownership", [])
    fact_names = [str(item.get("fact", "")) for item in fact_rows if isinstance(item, dict)]
    if set(fact_names) != required_facts or len(fact_names) != len(set(fact_names)):
        issues.append("fact ownership must declare each PM-L0 fact exactly once")
    canonical_pairs: set[tuple[str, str]] = set()
    for item in fact_rows:
        if not isinstance(item, dict) or not all(item.get(key) for key in ("fact", "owner", "canonical_artifact", "state")):
            issues.append("every learning fact needs fact, owner, canonical_artifact, and state")
            continue
        pair = (str(item["fact"]), str(item["owner"]))
        if pair in canonical_pairs:
            issues.append(f"learning fact `{item['fact']}` has duplicate mutable ownership")
        canonical_pairs.add(pair)

    required_systems = {item["id"] for item in LEARNING_SYSTEMS}
    systems = value.get("systems", [])
    system_ids = [str(item.get("id", "")) for item in systems if isinstance(item, dict)]
    if set(system_ids) != required_systems or len(system_ids) != len(set(system_ids)):
        issues.append("learning systems inventory is incomplete or duplicated")
    for item in systems:
        if not isinstance(item, dict) or not all(item.get(key) for key in ("id", "owner", "scripts", "commands")):
            issues.append("every learning system needs id, owner, scripts, and commands")
            continue
        for script in item["scripts"]:
            if not (root / str(script)).is_file():
                issues.append(f"inventoried learning script is missing: {script}")

    artifact_ids: set[str] = set()
    mutable_path_owners: dict[str, set[str]] = {}
    migration_ids = {str(item.get("id")) for item in value.get("migrations", []) if isinstance(item, dict)}
    for item in value.get("artifacts", []):
        if not isinstance(item, dict) or not all(key in item for key in ("id", "system", "path", "role", "owner", "writers")) or not all(item.get(key) for key in ("id", "system", "path", "role", "owner")):
            issues.append("every learning artifact needs id, system, path, role, owner, and writers")
            continue
        artifact_id = str(item["id"])
        if artifact_id in artifact_ids:
            issues.append(f"learning artifact `{artifact_id}` is duplicated")
        artifact_ids.add(artifact_id)
        if item["system"] not in required_systems:
            issues.append(f"learning artifact `{artifact_id}` has an unknown system")
        if item.get("mutable"):
            mutable_path_owners.setdefault(str(item["path"]), set()).add(str(item["owner"]))
            if not item["writers"]:
                issues.append(f"mutable learning artifact `{item['path']}` needs a writer")
        for script in item["writers"]:
            if not (root / str(script)).is_file():
                issues.append(f"inventoried writer is missing: {script}")
        if item.get("migration") and item["migration"] not in migration_ids:
            issues.append(f"learning artifact `{artifact_id}` references an unknown migration")
    for path, owners in mutable_path_owners.items():
        if len(owners) != 1:
            issues.append(f"mutable learning artifact `{path}` has multiple canonical owners: {', '.join(sorted(owners))}")

    aliases = value.get("aliases", [])
    alias_names = [str(item.get("alias", "")) for item in aliases if isinstance(item, dict)]
    if len(alias_names) != len(set(alias_names)):
        issues.append("learning aliases must be unique")
    for item in aliases:
        if not isinstance(item, dict) or not all(item.get(key) for key in ("alias", "canonical", "state", "preserves")):
            issues.append("every learning alias needs alias, canonical, state, and preserves")
            continue
        if int(item.get("minimum_release_window", 0)) < 2:
            issues.append(f"learning alias `{item['alias']}` needs at least a two-release compatibility window")
        if set(item["preserves"]) != {"approval", "privacy", "safety", "data"}:
            issues.append(f"learning alias `{item['alias']}` must preserve approval, privacy, safety, and data")

    seen_migrations: set[str] = set()
    for item in value.get("migrations", []):
        if not isinstance(item, dict) or not all(item.get(key) for key in ("id", "source", "target", "phase", "strategy")):
            issues.append("every learning migration needs id, source, target, phase, and strategy")
            continue
        migration_id = str(item["id"])
        if migration_id in seen_migrations:
            issues.append(f"learning migration `{migration_id}` is duplicated")
        seen_migrations.add(migration_id)
        if item.get("preserve_existing") is not True:
            issues.append(f"learning migration `{migration_id}` would silently discard existing artifacts")
        if int(item.get("minimum_release_window", 0)) < 2:
            issues.append(f"learning migration `{migration_id}` needs at least a two-release compatibility window")
    expected = build_learning_inventory(root)
    for section in ("fact_ownership", "systems", "artifacts", "aliases", "migrations", "boundaries"):
        if value.get(section) != expected.get(section):
            issues.append(f"learning inventory `{section}` does not match the declared PM-L0 control model")
    return issues


def validate_learning_v3_contract(root: Path, inventory: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    schema_path = root / LEARNING_V3_SCHEMA_PATH.relative_to(ROOT)
    script_path = root / "scripts" / "learning-v3.py"
    if not schema_path.is_file():
        issues.append("PM-L1 Learning V3 schema is missing")
        return issues
    if not script_path.is_file():
        issues.append("PM-L1 Learning V3 implementation is missing")
    try:
        schema = read_json(schema_path)
    except (OSError, json.JSONDecodeError):
        return ["PM-L1 Learning V3 schema is invalid JSON"]
    if schema.get("additionalProperties") is not False:
        issues.append("Learning V3 top-level schema must be closed")
    properties = schema.get("properties", {})
    if properties.get("schema_version", {}).get("const") != "3" or properties.get("type", {}).get("const") != "tailtrail-learning-v3-record":
        issues.append("Learning V3 schema identity is invalid")
    required = {"learning_class", "provenance", "applicability", "freshness", "utility", "privacy", "lifecycle", "chain"}
    if not required <= set(properties):
        issues.append("Learning V3 schema is missing a required contract domain")
    facts = {item.get("fact"): item.get("canonical_artifact") for item in inventory.get("fact_ownership", []) if isinstance(item, dict)}
    for fact in ("candidate", "curated-learning"):
        if facts.get(fact) != ".tailtrail/learning-v3/events.jsonl":
            issues.append(f"PM-L1 `{fact}` writes are not assigned to the canonical V3 store")
    return issues


def validate_learning_retrieval_contract(root: Path) -> list[str]:
    issues: list[str] = []
    schema_path = root / LEARNING_USE_PROPOSAL_SCHEMA_PATH.relative_to(ROOT)
    script_path = root / "scripts" / "learning-retrieval.py"
    navigator_path = root / "scripts" / "navigator.py"
    renderer_path = root / "scripts" / "navigator_render.py"
    if not schema_path.is_file():
        return ["PM-L2 learning use proposal schema is missing"]
    if not script_path.is_file():
        issues.append("PM-L2 project-framed retrieval implementation is missing")
    try:
        schema = read_json(schema_path)
    except (OSError, json.JSONDecodeError):
        return ["PM-L2 learning use proposal schema is invalid JSON"]
    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is not False:
        issues.append("PM-L2 learning use proposal schema must be closed")
    if properties.get("type", {}).get("const") != "tailtrail-learning-use-proposal":
        issues.append("PM-L2 learning use proposal identity is invalid")
    if properties.get("result_cap", {}).get("const") != 3 or properties.get("matches", {}).get("maxItems") != 3:
        issues.append("PM-L2 retrieval must enforce a three-result cap in the contract")
    script_text = script_path.read_text(encoding="utf-8") if script_path.is_file() else ""
    navigator_text = navigator_path.read_text(encoding="utf-8") if navigator_path.is_file() else ""
    renderer_text = renderer_path.read_text(encoding="utf-8") if renderer_path.is_file() else ""
    required_tokens = ("task_frame", "applicability_score", "invalidator_checks", "explicit_conflicts", "do-not-use")
    if any(token not in script_text for token in required_tokens):
        issues.append("PM-L2 retrieval implementation is missing a framing, ranking, invalidator, conflict, or default-deny control")
    if "learning_use_proposal" not in navigator_text or "Learning Use Proposal" not in renderer_text:
        issues.append("Navigator does not consume and render the PM-L2 use proposal")
    return issues


def validate_learning_receipt_contract(root: Path, inventory: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    schema_path = root / LEARNING_USE_RECEIPT_SCHEMA_PATH.relative_to(ROOT)
    script_path = root / "scripts" / "learning-use-receipt.py"
    completion_path = root / "scripts" / "completion-report.py"
    if not schema_path.is_file():
        return ["PM-L3 learning use receipt schema is missing"]
    if not script_path.is_file():
        issues.append("PM-L3 append-only learning use receipt implementation is missing")
    try:
        schema = read_json(schema_path)
    except (OSError, json.JSONDecodeError):
        return ["PM-L3 learning use receipt schema is invalid JSON"]
    if schema.get("additionalProperties") is not False:
        issues.append("PM-L3 learning use receipt schema must be closed")
    properties = schema.get("properties", {})
    if properties.get("type", {}).get("const") != "tailtrail-learning-use-receipt-event":
        issues.append("PM-L3 learning use receipt identity is invalid")
    decisions = set(properties.get("decision", {}).get("enum", []))
    if decisions != {"applied", "advisory", "ignored", "rejected", "stale"}:
        issues.append("PM-L3 receipt decision set is incomplete")
    text = script_path.read_text(encoding="utf-8") if script_path.is_file() else ""
    completion_text = completion_path.read_text(encoding="utf-8") if completion_path.is_file() else ""
    required_tokens = ("requirement_uids", "decision_type", "causal_claim", "domain_cap", "completion_fingerprint")
    if any(token not in text for token in required_tokens):
        issues.append("PM-L3 receipt implementation is missing requirement, decision, attribution, or utility controls")
    if "attribute_completion" not in completion_text or "learning_use" not in completion_text:
        issues.append("Completion Report does not consume PM-L3 learning use receipts")
    facts = {item.get("fact"): item for item in inventory.get("fact_ownership", []) if isinstance(item, dict)}
    receipt = facts.get("use-receipt", {})
    if receipt.get("state") != "current" or receipt.get("canonical_artifact") != ".tailtrail/runs/<run-id>/learning/use-receipts.jsonl":
        issues.append("PM-L3 use-receipt ownership is not current and canonical")
    return issues


def validate_learning_governance_contract(root: Path, inventory: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    schema_path = root / LEARNING_GOVERNANCE_SCHEMA_PATH.relative_to(ROOT)
    script_path = root / "scripts" / "learning-governance.py"
    retrieval_path = root / "scripts" / "learning-retrieval.py"
    if not schema_path.is_file():
        return ["PM-L4 learning governance schema is missing"]
    if not script_path.is_file():
        issues.append("PM-L4 learning governance implementation is missing")
    try:
        schema = read_json(schema_path)
    except (OSError, json.JSONDecodeError):
        return ["PM-L4 learning governance schema is invalid JSON"]
    if schema.get("additionalProperties") is not False:
        issues.append("PM-L4 learning governance schema must be closed")
    properties = schema.get("properties", {})
    if properties.get("type", {}).get("const") != "tailtrail-learning-governance-event":
        issues.append("PM-L4 learning governance identity is invalid")
    actions = set(properties.get("action", {}).get("enum", []))
    required = {"challenge", "amend", "supersede", "revoke", "revalidate", "conflict", "negative-candidate", "promote", "dismiss"}
    if not required <= actions:
        issues.append("PM-L4 governance transition set is incomplete")
    text = script_path.read_text(encoding="utf-8") if script_path.is_file() else ""
    retrieval = retrieval_path.read_text(encoding="utf-8") if retrieval_path.is_file() else ""
    tokens = ("receipt_signals", "negative_candidates", "scope_overlap", "blocking_reasons", "NEGATIVE_THRESHOLD")
    if any(token not in text for token in tokens) or "GOVERNANCE.blocking_reasons" not in retrieval:
        issues.append("PM-L4 implementation is missing repeated-rejection, scope-conflict, or fail-closed retrieval controls")
    facts = {item.get("fact"): item for item in inventory.get("fact_ownership", []) if isinstance(item, dict)}
    conflict = facts.get("conflict", {})
    if conflict.get("state") != "current" or conflict.get("canonical_artifact") != ".tailtrail/learning-conflicts.jsonl":
        issues.append("PM-L4 conflict ownership is not current and canonical")
    return issues


def validate_learning_calibration_contract(root: Path, inventory: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    script_path = root / "scripts" / "learning-calibration.py"
    retrieval_path = root / "scripts" / "learning-retrieval.py"
    catalog_path = root / "benchmarks" / "evaluation" / "learning-calibration" / "v1.json"
    for source in LEARNING_CALIBRATION_SCHEMAS:
        path = root / source.relative_to(ROOT)
        if not path.is_file():
            issues.append(f"PM-L5 calibration schema is missing: {path.relative_to(root).as_posix()}")
            continue
        try:
            schema = read_json(path)
        except (OSError, json.JSONDecodeError):
            issues.append(f"PM-L5 calibration schema is invalid JSON: {path.relative_to(root).as_posix()}")
            continue
        if schema.get("additionalProperties") is not False:
            issues.append(f"PM-L5 calibration schema must be closed: {path.relative_to(root).as_posix()}")
    if not script_path.is_file() or not catalog_path.is_file():
        issues.append("PM-L5 calibration implementation or paired catalog is missing")
    text = script_path.read_text(encoding="utf-8") if script_path.is_file() else ""
    retrieval = retrieval_path.read_text(encoding="utf-8") if retrieval_path.is_file() else ""
    tokens = ("false_intervention_rate", "brier_score", "correction_cycle_delta", "review_time_delta_ms", "token_overhead", "project_observations", "meta_feed", "validate_projection")
    if any(token not in text for token in tokens) or "CALIBRATION.load_adjustments" not in retrieval:
        issues.append("PM-L5 implementation is missing paired metrics, receipt calibration, projection, Meta-Harness, or fail-closed retrieval controls")
    facts = {item.get("fact"): item for item in inventory.get("fact_ownership", []) if isinstance(item, dict)}
    calibration = facts.get("class-confidence-calibration", {})
    if calibration.get("state") != "current" or calibration.get("canonical_artifact") != ".tailtrail/learning-calibration.json":
        issues.append("PM-L5 class-confidence calibration ownership is not current and canonical")
    return issues


def validate_adoption_contract(root: Path) -> list[str]:
    issues: list[str] = []
    script_path = root / "scripts" / "adoption-validation.py"
    catalog_path = root / "benchmarks" / "evaluation" / "adoption" / "v1.json"
    for source in ADOPTION_VALIDATION_SCHEMAS:
        path = root / source.relative_to(ROOT)
        if not path.is_file():
            issues.append(f"PM-7 adoption schema is missing: {path.relative_to(root).as_posix()}")
            continue
        try:
            schema = read_json(path)
        except (OSError, json.JSONDecodeError):
            issues.append(f"PM-7 adoption schema is invalid JSON: {path.relative_to(root).as_posix()}")
            continue
        if schema.get("additionalProperties") is not False:
            issues.append(f"PM-7 adoption schema must be closed: {path.relative_to(root).as_posix()}")
    if not script_path.is_file() or not catalog_path.is_file():
        issues.append("PM-7 adoption runtime or sealed catalog is missing")
        return issues
    try:
        module = load_module("product_maturity_adoption_validation", script_path)
        result = module.validate_catalog()
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        issues.append(f"PM-7 adoption catalog validation failed: {error}")
        return issues
    if result.get("status") != "passed" or result.get("cohorts") != 2 or result.get("scenario_count", 0) < 8:
        issues.append("PM-7 adoption catalog lacks two cohorts, eight scenarios, or a valid integrity seal")
    text = script_path.read_text(encoding="utf-8")
    tokens = ("protocol-fixture", "time_to_plan_p75_ms", "false_intervention_rate", "completion_comprehension_rate", "safety_boundary_weakening_count", "build_recommendations", "observer_attested")
    if any(token not in text for token in tokens):
        issues.append("PM-7 runtime is missing evidence separation, required metrics, safety gate, or repeated recommendations")
    return issues


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
    learning_path = root / LEARNING_INVENTORY_PATH.relative_to(ROOT)
    learning_inventory = read_json(learning_path) if learning_path.is_file() else {}
    learning_issues = validate_learning_inventory(root, learning_inventory) if learning_inventory else ["PM-L0 learning inventory is missing"]
    learning_v3_issues = validate_learning_v3_contract(root, learning_inventory) if learning_inventory else ["PM-L1 Learning V3 contract cannot be validated"]
    learning_retrieval_issues = validate_learning_retrieval_contract(root)
    learning_receipt_issues = validate_learning_receipt_contract(root, learning_inventory) if learning_inventory else ["PM-L3 learning use receipt contract cannot be validated"]
    learning_governance_issues = validate_learning_governance_contract(root, learning_inventory) if learning_inventory else ["PM-L4 learning governance contract cannot be validated"]
    learning_calibration_issues = validate_learning_calibration_contract(root, learning_inventory) if learning_inventory else ["PM-L5 learning calibration contract cannot be validated"]
    adoption_issues = validate_adoption_contract(root)
    issues = validate_policy(policy) + validate_scenarios(scenarios) + learning_issues + learning_v3_issues + learning_retrieval_issues + learning_receipt_issues + learning_governance_issues + learning_calibration_issues + adoption_issues
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
        "learning_ownership": "passed" if not learning_issues else "failed",
        "learning_v3_contract": "passed" if not learning_v3_issues else "failed",
        "learning_retrieval_gate": "passed" if not learning_retrieval_issues else "failed",
        "learning_receipt_contract": "passed" if not learning_receipt_issues else "failed",
        "learning_governance_contract": "passed" if not learning_governance_issues else "failed",
        "learning_calibration_contract": "passed" if not learning_calibration_issues else "failed",
        "adoption_validation_contract": "passed" if not adoption_issues else "failed",
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
            f"**Learning ownership:** `{value.get('learning_ownership')}`",
            f"**Learning V3 contract:** `{value.get('learning_v3_contract')}`",
            f"**Learning retrieval gate:** `{value.get('learning_retrieval_gate')}`",
            f"**Learning receipt contract:** `{value.get('learning_receipt_contract')}`",
            f"**Learning governance contract:** `{value.get('learning_governance_contract')}`",
            f"**Learning calibration contract:** `{value.get('learning_calibration_contract')}`",
            f"**Adoption validation contract:** `{value.get('adoption_validation_contract')}`",
            f"**Usability/regression scenarios:** `{value.get('scenario_count')}`",
            "",
        ]
        if value.get("issues"):
            lines.extend(["## Issues", "", *[f"- {item}" for item in value["issues"]], ""])
        else:
            lines.extend(["No unapproved public-surface drift or ambiguous ownership was detected.", ""])
        lines.append(str(value.get("boundary")))
        return "\n".join(lines)
    if value.get("type") == "tailtrail-product-maturity-learning-inventory":
        lines = [
            "# TailTrail Product Maturity PM-L0 Learning Inventory",
            "",
            f"**Version:** `{value['inventory_version']}`",
            f"**Integrity:** `sha256:{value['integrity']['digest']}`",
            "",
            "| Learning fact | Canonical owner | Canonical artifact | State |",
            "| --- | --- | --- | --- |",
            *[f"| {item['fact']} | {item['owner']} | `{item['canonical_artifact']}` | {item['state']} |" for item in value["fact_ownership"]],
            "",
            f"Inventoried systems: `{len(value['systems'])}`; artifacts: `{len(value['artifacts'])}`; aliases: `{len(value['aliases'])}`; migrations: `{len(value['migrations'])}`.",
            "",
            value["boundaries"]["preservation"],
        ]
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
    parser.add_argument("command", choices=("baseline", "inventory", "learning-inventory", "validate", "status"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--approved", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "learning-inventory":
        report = build_learning_inventory(root)
        if args.write:
            if not args.approved:
                raise SystemExit("--write requires --approved because it replaces the committed PM-L0 learning inventory")
            destination = root / LEARNING_INVENTORY_PATH.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        output(report, args.format)
        return 0
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
