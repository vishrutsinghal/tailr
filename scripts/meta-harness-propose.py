#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TAILTRAIL_DIR = Path(".tailtrail")
PROPOSALS = TAILTRAIL_DIR / "meta-harness-proposals.jsonl"
LATEST_PROPOSAL_MD = TAILTRAIL_DIR / "meta-harness-proposal.md"

STATUS_VALUES = {"proposed", "accepted", "implemented", "rejected", "rolled_back", "superseded"}

LINE_HINT_PATTERNS: dict[str, list[str]] = {
    "scripts/navigator.py": ["def main", "Navigator plan", "selected"],
    "scripts/navigator_core.py": ["def classify", "def build", "workflow"],
    "scripts/navigator_render.py": ["def render", "Selected Features", "Implementation Plan"],
    "scripts/token_budget_coach.py": ["def estimate", "budget", "profile"],
    "scripts/token-auto.py": ["def", "token", "route"],
    "scripts/code-graph-mapper.py": ["def build", "def map", "graph"],
    "scripts/cache-summary.py": ["def", "cache"],
    "scripts/review-run.py": ["def main", "requirement", "finding"],
    "scripts/review-output.py": ["def", "finding", "line"],
    "scripts/learning-agent.py": ["def event", "confidence", "learning"],
    "scripts/learning-refresh.py": ["def", "refresh"],
    "scripts/tailtrail-report.py": ["def build_value", "def report", "token"],
    "scripts/token-telemetry.py": ["def", "telemetry"],
    "scripts/token_telemetry.py": ["def", "telemetry"],
    "scripts/token-harness.py": ["def build_route", "def recommend_strategy", "exactness"],
    "scripts/token-harness-reduce.py": ["def reduce", "def build_reduction", "reducer"],
    "scripts/token-harness-proof.py": ["def confidence_gate", "def report_payload", "holdout"],
    "TOKEN-HARNESS.md": ["### Phase TH-6", "## Feature 11", "Proof"],
    "USER-GUIDE.md": ["Token Harness", "Structured Reducers", "Token Harness Proof"],
    "TAILTRAIL-COMMANDS.md": ["Token Budget Coach", "token-harness proof"],
}

CHANGE_TYPE_FEATURES: dict[str, list[str]] = {
    "navigator-routing": ["navigator", "guardrails"],
    "token-budget": ["token-harness", "navigator"],
    "code-graph": ["code-graph-mapper", "navigator"],
    "review": ["review", "guardrails"],
    "learning-governance": ["learning", "guardrails"],
    "metric-evidence": ["reporting", "token-harness"],
    "meta-harness": ["meta-harness", "registry"],
    "token-router": ["token-harness", "navigator"],
    "token-reducer": ["token-harness"],
    "token-proof-gate": ["token-harness", "meta-harness"],
    "navigator-token-routing": ["navigator", "token-harness"],
    "token-docs": ["token-harness"],
}

EVIDENCE_LABEL_RANK = {
    "none": 0,
    "estimated": 1,
    "local-evidence": 2,
    "measured": 3,
    "benchmark-measured": 4,
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_analyze() -> Any:
    path = ROOT / "scripts" / "meta-harness-analyze.py"
    spec = importlib.util.spec_from_file_location("tailtrail_meta_harness_analyze", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_registry_module() -> Any | None:
    path = ROOT / "scripts" / "tailtrail-registry.py"
    spec = importlib.util.spec_from_file_location("tailtrail_registry_for_meta_harness_propose", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")


def proposal_id_default(root: Path) -> str:
    prefix = datetime.now(timezone.utc).strftime("MH-%Y-%m")
    existing = [
        item.get("proposal_id")
        for item in read_jsonl(root / PROPOSALS)
        if isinstance(item.get("proposal_id"), str) and str(item.get("proposal_id")).startswith(prefix)
    ]
    return f"{prefix}-{len(set(existing)) + 1:03d}"


def first_line_hint(path: Path, patterns: list[str]) -> int | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    lowered_patterns = [pattern.lower() for pattern in patterns]
    for number, line in enumerate(lines, start=1):
        lowered = line.lower()
        if any(pattern in lowered for pattern in lowered_patterns):
            return number
    return None


def candidate_edits(root: Path, finding: dict[str, Any]) -> list[dict[str, Any]]:
    edits: list[dict[str, Any]] = []
    for file_name in finding.get("likely_files", []):
        if file_name.endswith("/"):
            continue
        path = root / file_name
        line_hint = first_line_hint(path, LINE_HINT_PATTERNS.get(file_name, ["def ", "# ", "## "]))
        edits.append(
            {
                "file": file_name,
                "line_hint": line_hint,
                "prompt_change": (
                    f"Review `{file_name}` for `{finding['recommendation_code']}`. "
                    f"Apply the smallest deterministic change that addresses `{finding['category']}` "
                    "without weakening guardrails, local policy, validation, security, or explicit user requirements."
                ),
                "review_note": "Recommended change only. Review before editing; do not apply automatically.",
            }
        )
    return edits


def select_finding(analysis: dict[str, Any], finding_id: str | None) -> dict[str, Any] | None:
    findings = analysis.get("findings", [])
    if not isinstance(findings, list) or not findings:
        return None
    if finding_id:
        for item in findings:
            if isinstance(item, dict) and item.get("finding_id") == finding_id:
                return item
        return None
    return max(
        (item for item in findings if isinstance(item, dict)),
        key=lambda item: (int(item.get("evidence_count", 0)), 1 if item.get("severity") == "high" else 0),
        default=None,
    )


def build_analysis_for_args(args: argparse.Namespace) -> dict[str, Any]:
    analyze = load_analyze()
    paths = analyze.collect_paths(args)
    if not paths:
        paths = [args.root / analyze.SHARED_SUMMARY]
    return analyze.build_analysis(paths, args.threshold)


def affected_feature_ids(finding: dict[str, Any]) -> list[str]:
    explicit = finding.get("affected_features")
    if isinstance(explicit, list):
        return sorted(dict.fromkeys(str(item) for item in explicit if isinstance(item, str) and item))
    change_type = str(finding.get("candidate_change_type", "meta-harness"))
    return CHANGE_TYPE_FEATURES.get(change_type, ["meta-harness"])


def weakest_evidence_label(labels: list[str]) -> str:
    if not labels:
        return "none"
    return min(labels, key=lambda label: EVIDENCE_LABEL_RANK.get(label, 0))


def registry_feature_impact(registry: dict[str, Any], feature_ids: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    module = load_registry_module()
    if module is None:
        return [], ["registry module unavailable"]
    issues: list[str] = []
    impacts: list[dict[str, Any]] = []
    for feature_id in feature_ids:
        feature = module.feature_by_id(registry, feature_id)
        if not feature:
            issues.append(f"unknown affected feature `{feature_id}`")
            continue
        impacts.append(
            {
                "feature_id": feature_id,
                "title": feature.get("title", ""),
                "surface": feature.get("surface", ""),
                "evidence_label": feature.get("evidence_label", "none"),
                "commands": feature.get("commands", []),
                "docs": feature.get("docs", []),
                "scripts": feature.get("scripts", []),
                "tests": feature.get("tests", []),
                "requires_approval": feature.get("requires_approval", False),
                "read_only": feature.get("read_only", False),
            }
        )
    return impacts, issues


def proposal_registry_context(finding: dict[str, Any]) -> dict[str, Any]:
    module = load_registry_module()
    if module is None:
        return {
            "valid": False,
            "issues": ["registry module unavailable"],
            "affected_features": affected_feature_ids(finding),
            "feature_impacts": [],
            "proposal_evidence_label": "none",
            "evidence_label_rule": "Proposal confidence cannot exceed the weakest affected feature evidence label.",
        }
    try:
        registry = module.load_registry()
    except (OSError, json.JSONDecodeError) as error:
        return {
            "valid": False,
            "issues": [f"registry could not be loaded: {error}"],
            "affected_features": affected_feature_ids(finding),
            "feature_impacts": [],
            "proposal_evidence_label": "none",
            "evidence_label_rule": "Proposal confidence cannot exceed the weakest affected feature evidence label.",
        }
    ids = affected_feature_ids(finding)
    impacts, impact_issues = registry_feature_impact(registry, ids)
    labels = [str(item.get("evidence_label", "none")) for item in impacts]
    proposal_label = weakest_evidence_label(labels)
    issues = impact_issues
    requested_label = str(finding.get("evidence_label") or finding.get("proposal_evidence_label") or proposal_label)
    if EVIDENCE_LABEL_RANK.get(requested_label, 0) > EVIDENCE_LABEL_RANK.get(proposal_label, 0):
        issues.append(f"requested evidence label `{requested_label}` exceeds weakest affected feature label `{proposal_label}`")
    return {
        "valid": not issues,
        "issues": issues,
        "affected_features": ids,
        "feature_impacts": impacts,
        "proposal_evidence_label": proposal_label,
        "evidence_label_rule": "Proposal confidence cannot exceed the weakest affected feature evidence label.",
    }


def build_proposal(root: Path, analysis: dict[str, Any], proposal_id: str, finding_id: str | None = None) -> dict[str, Any]:
    readiness = load_analyze().build_readiness(analysis)
    central = next((tier for tier in readiness.get("tiers", []) if tier.get("tier") == "central-tailtrail-maintainer"), {})
    selected = select_finding(analysis, finding_id)
    if selected is None:
        return {
            "schema_version": "1",
            "type": "tailtrail-meta-harness-proposal",
            "proposal_id": proposal_id,
            "created_at": now(),
            "status": "no_proposal",
            "reason": "No finding crossed the evidence threshold.",
            "analysis_event_count": analysis.get("valid_event_count", 0),
            "analysis_threshold": analysis.get("threshold", 2),
            "readiness": readiness,
            "central_readiness_decision": central.get("decision", "unknown"),
            "safety_boundaries": safety_boundaries(),
        }
    if central.get("decision") != "recommend_central_tailtrail_improvement":
        return {
            "schema_version": "1",
            "type": "tailtrail-meta-harness-proposal",
            "proposal_id": proposal_id,
            "created_at": now(),
            "status": "no_proposal",
            "reason": f"Central readiness decision is `{central.get('decision', 'unknown')}`.",
            "analysis_event_count": analysis.get("valid_event_count", 0),
            "analysis_threshold": analysis.get("threshold", 2),
            "readiness": readiness,
            "central_readiness_decision": central.get("decision", "unknown"),
            "safety_boundaries": safety_boundaries(),
        }
    registry_context = proposal_registry_context(selected)
    if not registry_context["valid"]:
        return {
            "schema_version": "1",
            "type": "tailtrail-meta-harness-proposal",
            "proposal_id": proposal_id,
            "created_at": now(),
            "status": "no_proposal",
            "reason": "Registry-aware proposal validation failed.",
            "analysis_event_count": analysis.get("valid_event_count", 0),
            "analysis_threshold": analysis.get("threshold", 2),
            "readiness": readiness,
            "central_readiness_decision": central.get("decision", "unknown"),
            "registry_validation": registry_context,
            "safety_boundaries": safety_boundaries(),
        }
    edits = candidate_edits(root, selected)
    return {
        "schema_version": "1",
        "type": "tailtrail-meta-harness-proposal",
        "proposal_id": proposal_id,
        "created_at": now(),
        "status": "proposed",
        "source_finding": selected,
        "analysis_event_count": analysis.get("valid_event_count", 0),
        "analysis_threshold": analysis.get("threshold", 2),
        "readiness": readiness,
        "central_readiness_decision": central.get("decision", "unknown"),
        "affected_features": registry_context["affected_features"],
        "registry_validation": registry_context,
        "proposal_evidence_label": registry_context["proposal_evidence_label"],
        "expected_improvement": selected["recommendation"],
        "candidate_edits": edits,
        "implementation_prompt": (
            f"Implement proposal `{proposal_id}` for finding `{selected['finding_id']}`. "
            "Use only the reviewed candidate edits, keep the diff small, add targeted tests, "
            "and record the result with `tailtrail harness proposal-record`."
        ),
        "verification_plan": selected.get("verification", []),
        "degradation_checks": [
            "Confirm existing TailTrail doctor checks still pass.",
            "Confirm related golden Navigator, review, graph, report, or learning tests still pass.",
            "Confirm the change does not increase plan noise for tiny/read-only tasks.",
            "Confirm public claims remain evidence-labeled and do not imply exact ROI without measured telemetry.",
        ],
        "rollback_plan": selected.get("rollback", "Revert the proposal commit and record `rolled_back`."),
        "user_note": "Recommended changes only. Review before adding; this command does not edit TailTrail source files.",
        "safety_boundaries": safety_boundaries(),
    }


def safety_boundaries() -> list[str]:
    return [
        "Do not upload data automatically.",
        "Do not collect raw prompts, raw logs, source code, diffs, file paths, repo names, branch names, users, private URLs, scanner raw output, secrets, or exact token usage in shared evidence.",
        "Do not score individual developers.",
        "Do not rewrite TailTrail automatically.",
        "Do not weaken guardrails, local policy, validation, security, dependency controls, scanner approval, or explicit user instructions.",
    ]


def render_markdown(proposal: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Meta-Harness Proposal",
        "",
        f"- Proposal ID: `{proposal['proposal_id']}`",
        f"- Status: `{proposal['status']}`",
        f"- Created: `{proposal['created_at']}`",
        f"- Central readiness: `{proposal.get('central_readiness_decision', 'unknown')}`",
        f"- Proposal evidence label: `{proposal.get('proposal_evidence_label', proposal.get('registry_validation', {}).get('proposal_evidence_label', 'unknown'))}`",
        "",
    ]
    if proposal["status"] == "no_proposal":
        lines.extend([f"- Reason: {proposal['reason']}", "", "No TailTrail product change is recommended yet."])
        registry = proposal.get("registry_validation")
        if isinstance(registry, dict) and registry.get("issues"):
            lines.extend(["", "## Registry Validation", ""])
            for issue in registry["issues"]:
                lines.append(f"- {issue}")
    else:
        finding = proposal["source_finding"]
        lines.extend(
            [
                "## Evidence",
                "",
                f"- Finding: `{finding['finding_id']}`",
                f"- Category: `{finding['category']}`",
                f"- Severity: `{finding['severity']}`",
                f"- Evidence count: `{finding['evidence_count']}`",
                f"- Evidence: {finding['evidence']}",
                f"- Affected features: {', '.join(f'`{item}`' for item in proposal.get('affected_features', []))}",
                f"- Registry evidence cap: `{proposal.get('proposal_evidence_label', 'none')}`",
                "",
                "## Recommended Improvement",
                "",
                proposal["expected_improvement"],
                "",
                "## Candidate Edits",
                "",
                "Review these recommendations before adding them.",
            ]
        )
        for edit in proposal["candidate_edits"]:
            location = f"{edit['file']}:{edit['line_hint']}" if edit.get("line_hint") else edit["file"]
            lines.extend([f"- `{location}`: {edit['prompt_change']}", f"  Note: {edit['review_note']}"])
        registry = proposal.get("registry_validation", {})
        impacts = registry.get("feature_impacts", []) if isinstance(registry, dict) else []
        if impacts:
            lines.extend(["", "## Registry Impact", ""])
            for impact in impacts:
                lines.extend(
                    [
                        f"### {impact.get('feature_id', 'unknown')}",
                        "",
                        f"- Title: {impact.get('title', '')}",
                        f"- Surface: `{impact.get('surface', '')}`",
                        f"- Evidence label: `{impact.get('evidence_label', 'none')}`",
                        "- Commands:",
                    ]
                )
                lines.extend(f"  - `{item}`" for item in impact.get("commands", [])[:8])
                lines.append("- Docs:")
                lines.extend(f"  - `{item}`" for item in impact.get("docs", [])[:8])
                lines.append("- Scripts:")
                lines.extend(f"  - `{item}`" for item in impact.get("scripts", [])[:8])
                lines.append("- Tests:")
                lines.extend(f"  - `{item}`" for item in impact.get("tests", [])[:8])
        lines.extend(["", "## Verification Plan", ""])
        for check in proposal["verification_plan"]:
            lines.append(f"- {check}")
        lines.extend(["", "## Degradation Checks", ""])
        for check in proposal["degradation_checks"]:
            lines.append(f"- {check}")
        lines.extend(["", "## Rollback Plan", "", proposal["rollback_plan"]])
    lines.extend(["", "## Safety Boundaries", ""])
    for boundary in proposal["safety_boundaries"]:
        lines.append(f"- {boundary}")
    lines.append("")
    return "\n".join(lines)


def write_proposal(root: Path, proposal: dict[str, Any]) -> None:
    (root / TAILTRAIL_DIR).mkdir(parents=True, exist_ok=True)
    append_jsonl(root / PROPOSALS, proposal)
    (root / LATEST_PROPOSAL_MD).write_text(render_markdown(proposal), encoding="utf-8")


def status_summary(root: Path) -> dict[str, Any]:
    rows = read_jsonl(root / PROPOSALS)
    counts = Counter(str(row.get("status", "unknown")) for row in rows)
    latest = rows[-1] if rows else None
    return {
        "schema_version": "1",
        "type": "tailtrail-meta-harness-proposal-status",
        "proposal_count": len(rows),
        "status_counts": dict(counts.most_common()),
        "latest": latest,
        "path": PROPOSALS.as_posix(),
        "note": "Proposal history is local private .tailtrail state. It is not shared metadata.",
    }


def render_status(summary: dict[str, Any]) -> str:
    lines = ["# TailTrail Meta-Harness Proposal Status", ""]
    lines.append(f"- Proposal records: `{summary['proposal_count']}`")
    lines.append(f"- Path: `{summary['path']}`")
    if summary["status_counts"]:
        lines.append("- Status counts:")
        for status, count in summary["status_counts"].items():
            lines.append(f"  - `{status}`: `{count}`")
    else:
        lines.append("- Status counts: none")
    latest = summary.get("latest")
    if isinstance(latest, dict):
        lines.extend(["", "## Latest", ""])
        lines.append(f"- Proposal ID: `{latest.get('proposal_id', 'unknown')}`")
        lines.append(f"- Status: `{latest.get('status', 'unknown')}`")
        if latest.get("source_finding"):
            source = latest["source_finding"]
            if isinstance(source, dict):
                lines.append(f"- Finding: `{source.get('finding_id', 'unknown')}` {source.get('category', '')}")
    lines.extend(["", summary["note"], ""])
    return "\n".join(lines)


def record_status(root: Path, proposal_id: str, status: str, note: str | None, reason: str | None) -> dict[str, Any]:
    if status not in STATUS_VALUES:
        raise SystemExit(f"--status must be one of: {', '.join(sorted(STATUS_VALUES))}")
    record = {
        "schema_version": "1",
        "type": "tailtrail-meta-harness-proposal-record",
        "proposal_id": proposal_id,
        "created_at": now(),
        "status": status,
        "note": note or "",
        "reason": reason or "",
        "privacy": "Local proposal decision record only. Do not include raw prompts, source, repo names, users, private URLs, secrets, or exact token usage.",
    }
    append_jsonl(root / PROPOSALS, record)
    return record


def add_analysis_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", type=Path, default=Path("."), help="Target repo root.")
    parser.add_argument("--roots", type=Path, action="append", help="Additional repo root to aggregate.")
    parser.add_argument("--summary", type=Path, action="append", help="Explicit shared harness summary JSONL file.")
    parser.add_argument("--threshold", type=int, default=2, help="Minimum repeated evidence count for a finding.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and track evidence-gated TailTrail Meta-Harness proposals.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    propose = subparsers.add_parser("propose", help="Create a reviewable proposal from repeated sanitized evidence.")
    add_analysis_args(propose)
    propose.add_argument("--proposal-id", help="Proposal ID, such as MH-2026-07-001.")
    propose.add_argument("--finding-id", help="Specific analysis finding ID to propose.")
    propose.add_argument("--format", choices=("markdown", "json"), default="markdown")
    propose.add_argument("--write-result", action="store_true", help="Write proposal history and latest markdown locally.")

    status = subparsers.add_parser("status", help="Show local proposal history status.")
    status.add_argument("--root", type=Path, default=Path("."), help="Target repo root.")
    status.add_argument("--format", choices=("markdown", "json"), default="markdown")

    record = subparsers.add_parser("record", help="Record an explicit proposal decision.")
    record.add_argument("--root", type=Path, default=Path("."), help="Target repo root.")
    record.add_argument("--proposal-id", required=True)
    record.add_argument("--status", required=True, choices=sorted(STATUS_VALUES))
    record.add_argument("--note")
    record.add_argument("--reason")
    record.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "propose":
        if args.threshold < 2:
            raise SystemExit("--threshold must be 2 or greater; one event is not enough to tune product behavior")
        proposal_id = args.proposal_id or proposal_id_default(args.root)
        proposal = build_proposal(args.root, build_analysis_for_args(args), proposal_id, args.finding_id)
        if args.write_result:
            write_proposal(args.root, proposal)
        if args.format == "json":
            print(json.dumps(proposal, indent=2, sort_keys=True))
        else:
            print(render_markdown(proposal), end="")
        return 0

    if args.command == "status":
        summary = status_summary(args.root)
        if args.format == "json":
            print(json.dumps(summary, indent=2, sort_keys=True))
        else:
            print(render_status(summary), end="")
        return 0

    if args.command == "record":
        record = record_status(args.root, args.proposal_id, args.status, args.note, args.reason)
        if args.format == "json":
            print(json.dumps(record, indent=2, sort_keys=True))
        else:
            print(f"Recorded `{args.status}` for `{args.proposal_id}` in `{PROPOSALS.as_posix()}`.\n")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
