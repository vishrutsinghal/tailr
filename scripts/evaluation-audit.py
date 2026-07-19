#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = Path("reports/evaluation-harness")


FEATURE_GROUPS: tuple[dict[str, Any], ...] = (
    {
        "feature_group": "benchmark-harness",
        "current_commands": ["tailtrail benchmark", "tailtrail analyze"],
        "scripts": ["scripts/benchmark-tailtrail.py", "scripts/analyze-benchmark.py"],
        "docs": ["benchmarks/README.md", "TAILTRAIL-COMMANDS.md", "ROADMAP.md"],
        "tests": ["tests/test_deterministic_tools.py"],
        "registry_ids": [],
        "evidence_labels": ["local-evidence"],
        "writes_require_approval": False,
        "raw_data_storage": "blocked",
        "overlaps": ["measured-efficacy"],
        "decision": "merge",
        "canonical_eval_surface": "eval artifact",
        "reason": "static artifact scoring remains useful but should be grouped under Evaluation Harness artifact/scenario evidence",
    },
    {
        "feature_group": "measured-efficacy",
        "current_commands": ["tailtrail efficacy", "tailtrail benchmark efficacy"],
        "scripts": ["scripts/efficacy-run.py", "scripts/efficacy-benchmark.py"],
        "docs": ["benchmarks/efficacy/README.md", "TAILTRAIL-COMMANDS.md", "ROADMAP.md"],
        "tests": ["tests/test_efficacy_run.py"],
        "registry_ids": [],
        "evidence_labels": ["estimated", "local-evidence", "measured", "benchmark-measured"],
        "writes_require_approval": False,
        "raw_data_storage": "blocked",
        "overlaps": ["benchmark-harness", "token-evidence", "enterprise-reporting"],
        "decision": "alias",
        "canonical_eval_surface": "eval portfolio",
        "reason": "portfolio evidence is active and has a clear umbrella home",
    },
    {
        "feature_group": "guardrail-precision",
        "current_commands": ["tailtrail guardrail precision"],
        "scripts": ["scripts/guardrail-precision.py"],
        "docs": ["benchmarks/guardrail-precision/README.md", "TAILTRAIL-COMMANDS.md", "ROADMAP.md"],
        "tests": ["tests/test_guardrail_precision.py"],
        "registry_ids": ["guardrails"],
        "evidence_labels": ["local-evidence"],
        "writes_require_approval": False,
        "raw_data_storage": "blocked",
        "overlaps": ["quality-loop"],
        "decision": "alias",
        "canonical_eval_surface": "eval guardrails",
        "reason": "precision baseline directly measures guardrail behavior quality",
    },
    {
        "feature_group": "outcome-telemetry",
        "current_commands": ["tailtrail outcome"],
        "scripts": ["scripts/outcome-telemetry.py"],
        "docs": ["USER-GUIDE.md", "TAILTRAIL-COMMANDS.md", "ROADMAP.md"],
        "tests": ["tests/test_deterministic_tools.py"],
        "registry_ids": ["reporting"],
        "evidence_labels": ["local-evidence"],
        "writes_require_approval": True,
        "raw_data_storage": "blocked",
        "overlaps": ["quality-loop", "enterprise-reporting"],
        "decision": "alias",
        "canonical_eval_surface": "eval outcome",
        "reason": "approved outcome events are a direct Evaluation Harness input",
    },
    {
        "feature_group": "quality-loop",
        "current_commands": ["tailtrail quality-loop"],
        "scripts": ["scripts/quality-loop.py"],
        "docs": ["context/quality-loop.md", "USER-GUIDE.md", "TAILTRAIL-COMMANDS.md"],
        "tests": ["tests/test_deterministic_tools.py"],
        "registry_ids": ["quality-signals"],
        "evidence_labels": ["local-evidence"],
        "writes_require_approval": True,
        "raw_data_storage": "blocked",
        "overlaps": ["outcome-telemetry", "meta-harness"],
        "decision": "alias",
        "canonical_eval_surface": "eval workflow",
        "reason": "workflow-fit events measure TailTrail behavior quality",
    },
    {
        "feature_group": "meta-harness",
        "current_commands": ["tailtrail harness"],
        "scripts": ["scripts/harness-review.py", "scripts/meta-harness-analyze.py", "scripts/meta-harness-propose.py"],
        "docs": ["META-HARNESS-IMPLEMENTATION.md", "TAILTRAIL-COMMANDS.md", "ROADMAP.md"],
        "tests": ["tests/test_meta_harness.py", "tests/test_meta_harness_token_feedback.py"],
        "registry_ids": ["meta-harness"],
        "evidence_labels": ["local-evidence"],
        "writes_require_approval": True,
        "raw_data_storage": "sanitized",
        "overlaps": ["quality-loop", "token-evidence"],
        "decision": "alias",
        "canonical_eval_surface": "eval meta",
        "reason": "Meta-Harness remains the product-improvement analysis layer under Evaluation Harness",
    },
    {
        "feature_group": "token-evidence",
        "current_commands": ["tailtrail token-harness", "tailtrail token", "tailtrail budget", "tailtrail receipt", "tailtrail telemetry", "tailtrail savings"],
        "scripts": [
            "scripts/token-harness.py",
            "scripts/token-harness-reduce.py",
            "scripts/token-harness-ledger.py",
            "scripts/token-harness-proof.py",
            "scripts/token-harness-bridge.py",
            "scripts/token-auto.py",
            "scripts/token-budget-coach.py",
            "scripts/context-receipt.py",
            "scripts/token-telemetry.py",
            "scripts/token-savings.py",
        ],
        "docs": ["TOKEN-HARNESS.md", "TOKEN-AUTOPILOT.md", "TOKEN-SLICER.md", "TAILTRAIL-COMMANDS.md"],
        "tests": ["tests/test_token_harness.py", "tests/test_deterministic_tools.py"],
        "registry_ids": ["token-harness"],
        "evidence_labels": ["estimated", "local-evidence", "measured", "benchmark-measured"],
        "writes_require_approval": True,
        "raw_data_storage": "blocked",
        "overlaps": ["measured-efficacy", "enterprise-reporting", "meta-harness"],
        "decision": "merge",
        "canonical_eval_surface": "eval tokens",
        "reason": "Token Harness owns exactness and token proof while Evaluation Harness consumes token evidence",
    },
    {
        "feature_group": "enterprise-reporting",
        "current_commands": ["tailtrail report"],
        "scripts": ["scripts/tailtrail-report.py"],
        "docs": ["ENTERPRISE-REVIEW.md", "TAILTRAIL-PITCH.md", "USER-GUIDE.md", "TAILTRAIL-COMMANDS.md"],
        "tests": ["tests/test_deterministic_tools.py"],
        "registry_ids": ["reporting"],
        "evidence_labels": ["local-evidence"],
        "writes_require_approval": False,
        "raw_data_storage": "blocked",
        "overlaps": ["outcome-telemetry", "token-evidence"],
        "decision": "alias",
        "canonical_eval_surface": "eval report",
        "reason": "value reporting is the public-facing rollup for Evaluation Harness evidence",
    },
    {
        "feature_group": "buildweek-demo-evidence",
        "current_commands": ["tailtrail start", "tailtrail graph ast", "tailtrail ci summarize", "tailtrail report value"],
        "scripts": ["scripts/task-start.py", "scripts/ast-map.py", "scripts/ci-summary.py", "scripts/tailtrail-report.py"],
        "docs": ["buildweek-demo-project/README.md", "buildweek-demo-project/DEMO-PROMPTS.md", "buildweek-demo-project/FEATURE-COVERAGE.md"],
        "tests": ["buildweek-demo-project/tests/test_claim_validation.py"],
        "registry_ids": [],
        "evidence_labels": ["heuristic", "local-ast", "provider-backed", "local-evidence"],
        "writes_require_approval": False,
        "raw_data_storage": "blocked",
        "overlaps": ["benchmark-harness", "measured-efficacy"],
        "decision": "alias",
        "canonical_eval_surface": "eval scenario",
        "reason": "demo evidence should become a formal scenario fixture in EH-8",
    },
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def tailtrail_commands(root: Path) -> set[str]:
    body = read_text(root / "scripts" / "tailtrail.py")
    commands: set[str] = set()
    in_block = False
    for raw in body.splitlines():
        stripped = raw.strip()
        if stripped.startswith("COMMANDS = {"):
            in_block = True
            continue
        if in_block and stripped.startswith("}"):
            break
        if in_block and stripped.startswith('"') and '":' in stripped:
            commands.add("tailtrail " + stripped.split('"', 2)[1])
    return commands


def registry_ids(root: Path) -> set[str]:
    path = root / "tailtrail-registry.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {str(item.get("id")) for item in payload.get("features", []) if isinstance(item, dict) and item.get("id")}


def docs_mention(root: Path, docs: list[str], needles: list[str]) -> bool:
    for doc in docs:
        body = read_text(root / doc)
        if not body:
            continue
        if any(needle.replace("tailtrail ", "").split()[0] in body or needle in body for needle in needles):
            return True
    return False


def enrich_feature(root: Path, feature: dict[str, Any]) -> dict[str, Any]:
    known_commands = tailtrail_commands(root)
    known_registry_ids = registry_ids(root)
    scripts = list(feature["scripts"])
    docs = list(feature["docs"])
    tests = list(feature["tests"])
    commands = list(feature["current_commands"])
    missing_scripts = [item for item in scripts if not (root / item).is_file()]
    missing_docs = [item for item in docs if not (root / item).is_file()]
    missing_tests = [item for item in tests if not (root / item).is_file()]
    missing_registry = [item for item in feature["registry_ids"] if item not in known_registry_ids]
    command_roots = {command.split()[1] for command in commands if command.startswith("tailtrail ") and len(command.split()) > 1}
    exposed_commands = sorted(root for root in command_roots if f"tailtrail {root}" in known_commands)
    documented = docs_mention(root, docs, commands)
    has_real_output = any((root / item).exists() for item in [*docs, *tests])
    result = dict(feature)
    result.update(
        {
            "missing_scripts": missing_scripts,
            "missing_docs": missing_docs,
            "missing_tests": missing_tests,
            "missing_registry_ids": missing_registry,
            "exposed_command_roots": exposed_commands,
            "documented": documented,
            "has_real_output": has_real_output,
        }
    )
    return result


def collect_issues(features: list[dict[str, Any]]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    canonical: dict[str, str] = {}
    for feature in features:
        group = feature["feature_group"]
        decision = feature.get("decision", "")
        surface = feature.get("canonical_eval_surface", "")
        if decision not in {"alias", "merge", "needs-decision", "retire"}:
            issues.append({"severity": "high", "feature_group": group, "message": "feature group has no valid decision"})
        if decision in {"alias", "merge"} and not surface:
            issues.append({"severity": "high", "feature_group": group, "message": "alias/merge feature lacks canonical eval surface"})
        if surface:
            owner = canonical.setdefault(surface, group)
            if owner != group and surface not in {"eval scenario"}:
                issues.append({"severity": "medium", "feature_group": group, "message": f"canonical eval surface `{surface}` also used by `{owner}`"})
        for script in feature.get("missing_scripts", []):
            issues.append({"severity": "high", "feature_group": group, "message": f"missing script `{script}`"})
        if feature.get("raw_data_storage") not in {"blocked", "sanitized"}:
            issues.append({"severity": "high", "feature_group": group, "message": "raw data storage is not blocked or sanitized"})
        if feature.get("writes_require_approval") and feature.get("raw_data_storage") == "unknown":
            issues.append({"severity": "high", "feature_group": group, "message": "write-capable feature has unknown storage behavior"})
    return issues


def audit(root: Path = ROOT) -> dict[str, Any]:
    features = [enrich_feature(root, dict(item)) for item in FEATURE_GROUPS]
    issues = collect_issues(features)
    blocked_aliases = [
        {
            "current_surface": "tailtrail token route",
            "reason": "kept compatibility-only; canonical Evaluation Harness routing is `eval tokens route` -> `token-harness route`",
        }
    ]
    alias_ready = sum(1 for item in features if item["decision"] == "alias")
    merge_needed = sum(1 for item in features if item["decision"] == "merge")
    needs_decision = sum(1 for item in features if item["decision"] == "needs-decision")
    retired = sum(1 for item in features if item["decision"] == "retire")
    status = "failed" if any(item["severity"] == "high" for item in issues) else "needs-decision" if needs_decision else "passed"
    return {
        "schema_version": "1",
        "type": "evaluation-harness-audit",
        "created_at": now_utc(),
        "root": root.as_posix(),
        "status": status,
        "summary": {
            "feature_groups": len(features),
            "alias_ready": alias_ready,
            "merge_needed": merge_needed,
            "needs_decision": needs_decision,
            "retired": retired,
            "issues": len(issues),
        },
        "features": features,
        "blocked_aliases": blocked_aliases,
        "issues": issues,
        "recommendations": [
            "Expose token-harness route as `eval tokens route`.",
            "Keep legacy `tailtrail token route` compatibility-only until usage proves it is still needed.",
            "Do not expose scenario commands beyond audit/pending messages until EH-4.",
            "Keep old evidence commands working while documenting `eval` as the umbrella after EH-2.",
        ],
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# TailTrail Evaluation Harness EH-0 Audit",
        "",
        f"- Status: `{report['status']}`",
        f"- Feature groups audited: `{summary['feature_groups']}`",
        f"- Alias-ready: `{summary['alias_ready']}`",
        f"- Merge-needed: `{summary['merge_needed']}`",
        f"- Needs decision: `{summary['needs_decision']}`",
        f"- Retired: `{summary['retired']}`",
        f"- Issues: `{summary['issues']}`",
        "",
        "## Canonical Mapping",
        "",
    ]
    for feature in report["features"]:
        lines.append(
            f"- `{feature['feature_group']}` -> `{feature.get('canonical_eval_surface', 'none')}` "
            f"({feature['decision']}): {feature['reason']}"
        )
    lines.extend(["", "## Blocked / Compatibility-Only Aliases", ""])
    for item in report["blocked_aliases"]:
        lines.append(f"- `{item['current_surface']}`: {item['reason']}")
    lines.extend(["", "## Issues", ""])
    if report["issues"]:
        for item in report["issues"]:
            lines.append(f"- `{item['severity']}` `{item['feature_group']}`: {item['message']}")
    else:
        lines.append("- none")
    lines.extend(["", "## Recommendations", ""])
    lines.extend(f"- {item}" for item in report["recommendations"])
    return "\n".join(lines) + "\n"


def write_reports(root: Path, report: dict[str, Any]) -> None:
    directory = root / REPORT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "eh0-audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (directory / "eh0-audit.md").write_text(markdown(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit evidence surfaces before Evaluation Harness command consolidation.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--strict", action="store_true", help="Fail when any audit blocker or needs-decision item is present.")
    parser.add_argument("--write-report", action="store_true", help="Write reports/evaluation-harness/eh0-audit.{json,md}. Requires --approved.")
    parser.add_argument("--approved", action="store_true", help="Approve writing EH-0 audit reports.")
    args = parser.parse_args()

    root = args.root.resolve()
    report = audit(root)
    if args.write_report:
        if not args.approved:
            raise SystemExit("--write-report requires --approved")
        write_reports(root, report)

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(markdown(report), end="")

    if args.strict and report["status"] != "passed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

