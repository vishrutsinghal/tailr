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
SHARED_SUMMARY = Path("tailtrail-meta") / "harness-summary.jsonl"
ANALYSIS_JSON = TAILTRAIL_DIR / "meta-harness-analysis.json"
ANALYSIS_MD = TAILTRAIL_DIR / "meta-harness-analysis.md"
READINESS_JSON = TAILTRAIL_DIR / "meta-harness-readiness.json"
READINESS_MD = TAILTRAIL_DIR / "meta-harness-readiness.md"

WEAK_VALUES = {"missing", "weak", "unknown", "not-run", "skipped", "estimated", "low"}
FULFILLMENT_GAP_VALUES = {"partial", "partially-aligned", "not-aligned", "unclear", "unknown"}
GRAPH_GAP_VALUES = {"missing", "stale", "invalid", "unknown"}
TOKEN_UNDERESTIMATE_VALUES = {"underestimated", "too-small", "low", "weak"}
STRONG_FITS = {"strong", "medium"}
WEAK_FITS = {"missing", "weak", "unknown"}

LIKELY_FILES: dict[str, list[str]] = {
    "navigator-routing": [
        "scripts/navigator.py",
        "scripts/navigator_core.py",
        "scripts/navigator_render.py",
        "tests/test_navigator_core.py",
        "tests/golden/",
    ],
    "token-budget": [
        "scripts/token_budget_coach.py",
        "scripts/token-auto.py",
        "TOKEN-AUTOPILOT.md",
        "tests/test_deterministic_tools.py",
    ],
    "code-graph": [
        "scripts/code-graph-mapper.py",
        "scripts/cache-summary.py",
        "context/code-graph-mapper.md",
        "tests/test_deterministic_tools.py",
    ],
    "review": [
        "scripts/review-run.py",
        "scripts/review-output.py",
        "context/review-lenses.md",
        "tests/test_review_output.py",
        "tests/test_review_scope.py",
    ],
    "learning-governance": [
        "scripts/learning-agent.py",
        "scripts/learning-refresh.py",
        "LEARNING-GOVERNANCE.md",
        "tests/test_deterministic_tools.py",
    ],
    "metric-evidence": [
        "scripts/tailtrail-report.py",
        "scripts/token-telemetry.py",
        "scripts/token_telemetry.py",
        "scripts/token-harness-proof.py",
        "TAILTRAIL-COMMANDS.md",
        "tests/test_deterministic_tools.py",
        "tests/test_token_harness_proof.py",
    ],
    "token-router": [
        "scripts/token-harness.py",
        "tests/test_token_harness.py",
    ],
    "token-reducer": [
        "scripts/token-harness-reduce.py",
        "tests/test_token_harness_reduce.py",
    ],
    "token-proof-gate": [
        "scripts/token-harness-proof.py",
        "tests/test_token_harness_proof.py",
    ],
    "navigator-token-routing": [
        "scripts/navigator.py",
        "scripts/navigator_core.py",
        "tests/test_navigator_core.py",
    ],
    "token-docs": [
        "TOKEN-HARNESS.md",
        "USER-GUIDE.md",
        "TAILTRAIL-COMMANDS.md",
    ],
    "meta-harness": [
        "scripts/meta-harness-analyze.py",
        "scripts/meta-harness-propose.py",
        "templates/meta-harness-proposal.md",
        "META-HARNESS-IMPLEMENTATION.md",
        "ROADMAP.md",
        "tests/test_meta_harness.py",
    ],
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_harness_review() -> Any:
    path = ROOT / "scripts" / "harness-review.py"
    spec = importlib.util.spec_from_file_location("tailtrail_harness_review_for_meta", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_registry() -> Any | None:
    path = ROOT / "scripts" / "tailtrail-registry.py"
    spec = importlib.util.spec_from_file_location("tailtrail_registry_for_meta_harness", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def registry_maturity() -> dict[str, Any]:
    module = load_registry()
    if module is None:
        return {"available": False, "status": "missing", "issue_count": 1, "issues": ["registry module unavailable"]}
    try:
        registry = module.load_registry()
        issues = module.validate_registry(registry)
        features = module.features(registry)
        surfaces = {surface: module.registry_surface_entries(registry, surface)["features"] for surface in ("core", "extended")}
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        return {"available": False, "status": "invalid", "issue_count": 1, "issues": [str(error)]}
    return {
        "available": True,
        "status": "healthy" if not issues else "drift",
        "issue_count": len(issues),
        "issues": issues[:20],
        "feature_count": len(features),
        "surface_counts": {surface: len(items) for surface, items in surfaces.items()},
    }


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    issues: list[str] = []
    if not path.exists():
        issues.append(f"{path.as_posix()}: input missing")
        return rows, issues
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(f"{path.as_posix()} line {number}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(value, dict):
            issues.append(f"{path.as_posix()} line {number}: event is not an object")
            continue
        rows.append(value)
    return rows, issues


def normalize(value: Any) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip().lower().replace(" ", "-").replace("_", "-") or "unknown"


def count_key(events: list[dict[str, Any]], key: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for event in events:
        value = event.get(key)
        if isinstance(value, list):
            if not value:
                counter["unknown"] += 1
            for item in value:
                counter[normalize(item)] += 1
        else:
            counter[normalize(value)] += 1
    return dict(counter.most_common())


def count_dimension(events: list[dict[str, Any]], dimension: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for event in events:
        dimensions = event.get("dimension_fits")
        if isinstance(dimensions, dict):
            counter[normalize(dimensions.get(dimension))] += 1
        else:
            counter["unknown"] += 1
    return dict(counter.most_common())


def event_has_workflow(event: dict[str, Any], workflow: str) -> bool:
    values = event.get("workflow_selected")
    return isinstance(values, list) and workflow in {normalize(item) for item in values}


def finding(
    finding_id: str,
    category: str,
    severity: str,
    evidence_count: int,
    threshold: int,
    evidence: str,
    recommendation_code: str,
    recommendation: str,
    change_type: str,
    verification: list[str],
    rollback: str,
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "category": category,
        "severity": severity,
        "evidence_count": evidence_count,
        "threshold": threshold,
        "evidence": evidence,
        "recommendation_code": recommendation_code,
        "recommendation": recommendation,
        "candidate_change_type": change_type,
        "likely_files": LIKELY_FILES.get(change_type, LIKELY_FILES["meta-harness"]),
        "verification": verification,
        "rollback": rollback,
    }


def build_findings(events: list[dict[str, Any]], threshold: int) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    recommendation_counts: Counter[str] = Counter()
    for event in events:
        codes = event.get("recommendation_codes")
        if isinstance(codes, list):
            recommendation_counts.update(normalize(item) for item in codes)
    for code, count in recommendation_counts.most_common():
        if code != "unknown" and count >= threshold:
            findings.append(
                finding(
                    f"MH-F-{len(findings) + 1:03d}",
                    "repeated-recommendation",
                    "medium",
                    count,
                    threshold,
                    f"Recommendation code `{code}` appeared in {count} shared event(s).",
                    code,
                    "Review the repeated recommendation and decide whether it belongs in TailTrail product behavior, docs, or benchmark coverage.",
                    "meta-harness",
                    [
                        "Add a targeted regression test or scenario for the repeated recommendation.",
                        "Run `python3 scripts/tailtrail.py doctor` after any TailTrail behavior change.",
                    ],
                    "Revert the proposal commit and record `rolled_back` if the recommendation makes TailTrail noisier or weaker.",
                )
            )

    validation_gap = sum(1 for event in events if normalize(event.get("validation_fit")) in WEAK_VALUES)
    if validation_gap >= threshold:
        findings.append(
            finding(
                f"MH-F-{len(findings) + 1:03d}",
                "validation-fit-gap",
                "high",
                validation_gap,
                threshold,
                f"{validation_gap} event(s) had weak, missing, unknown, or skipped validation fit.",
                "strengthen-validation-evidence",
                "Strengthen Navigator, Review, or Test Precision guidance so implementation work ends with focused validation evidence.",
                "navigator-routing",
                [
                    "Add or update a Navigator golden plan where validation is required.",
                    "Run review and test precision unit tests.",
                ],
                "Revert routing or wording changes if they add validation noise to tiny read-only tasks.",
            )
        )

    token_under = sum(1 for event in events if normalize(event.get("token_budget_fit")) in TOKEN_UNDERESTIMATE_VALUES)
    if token_under >= threshold:
        findings.append(
            finding(
                f"MH-F-{len(findings) + 1:03d}",
                "token-budget-underestimate",
                "medium",
                token_under,
                threshold,
                f"{token_under} event(s) show token budget underestimation.",
                "tune-token-budget-profile",
                "Tune token budget profile estimates for the repeated task family, especially when graph, scanner, or test signals are present.",
                "token-budget",
                [
                    "Add a token budget unit test for the repeated task family.",
                    "Compare before/after budget estimate against context receipts or measured telemetry when available.",
                ],
                "Restore the prior budget profile if estimates become too large for small tasks.",
            )
        )

    metric_gap = sum(1 for event in events if normalize(event.get("metric_confidence")) in WEAK_VALUES)
    if metric_gap >= threshold:
        findings.append(
            finding(
                f"MH-F-{len(findings) + 1:03d}",
                "metric-confidence-gap",
                "medium",
                metric_gap,
                threshold,
                f"{metric_gap} event(s) had weak or missing metric confidence.",
                "improve-measured-telemetry-path",
                "Improve value reporting prompts, telemetry import examples, or report labels so claims stay evidence-based.",
                "metric-evidence",
                [
                    "Run value report tests.",
                    "Check public claim guardrails still prevent exact ROI claims without measured telemetry.",
                ],
                "Revert report wording changes if they overclaim token savings or value metrics.",
            )
        )

    fulfillment_gap = sum(1 for event in events if normalize(event.get("requirement_fulfillment")) in FULFILLMENT_GAP_VALUES)
    if fulfillment_gap >= threshold:
        findings.append(
            finding(
                f"MH-F-{len(findings) + 1:03d}",
                "requirement-fulfillment-gap",
                "high",
                fulfillment_gap,
                threshold,
                f"{fulfillment_gap} event(s) had partial, unclear, unknown, or not-aligned requirement fulfillment.",
                "strengthen-requirement-fulfillment-review",
                "Strengthen Requirement Fulfillment Review and clarification prompts before implementation or guarded fix loops.",
                "review",
                [
                    "Add review-output tests that include requirement fulfillment details.",
                    "Run review scope tests for branch, path, and uncommitted changes.",
                ],
                "Revert review prompt changes if findings become vague or overly broad.",
            )
        )

    graph_gap = sum(1 for event in events if normalize(event.get("graph_cache_status")) in GRAPH_GAP_VALUES)
    if graph_gap >= threshold:
        findings.append(
            finding(
                f"MH-F-{len(findings) + 1:03d}",
                "graph-cache-gap",
                "medium",
                graph_gap,
                threshold,
                f"{graph_gap} event(s) had missing, stale, invalid, or unknown graph cache status.",
                "strengthen-graph-first-read-path",
                "Make graph creation, refresh, or reuse clearer for broad code understanding, scanner remediation, and review tasks.",
                "code-graph",
                [
                    "Run code graph mapper tests.",
                    "Run a Navigator plan for repo overview and scanner remediation prompts.",
                ],
                "Revert graph-trigger changes if graph mapping starts running for tiny read-only prompts without benefit.",
            )
        )

    aidlc_overroute = sum(
        1
        for event in events
        if event_has_workflow(event, "aidlc") and normalize(event.get("task_type")) in {"bug", "bug-fix", "small-bug-fix", "bug-fix-with-tests"}
    )
    if aidlc_overroute >= threshold:
        findings.append(
            finding(
                f"MH-F-{len(findings) + 1:03d}",
                "aidlc-overroute",
                "medium",
                aidlc_overroute,
                threshold,
                f"{aidlc_overroute} small bug-fix event(s) selected AIDLC.",
                "suppress-aidlc-for-small-bug-test-only",
                "Tune Navigator so small bug fixes with test requests do not enter AIDLC unless risk, ownership, compliance, or multi-step signals exist.",
                "navigator-routing",
                [
                    "Add a golden Navigator plan for a small bug fix with unit tests.",
                    "Verify broad/risky prompts still select AIDLC.",
                ],
                "Restore the previous AIDLC trigger if broad/risky work stops receiving lifecycle guidance.",
            )
        )

    scanner_graph_gap = sum(
        1
        for event in events
        if normalize(event.get("scanner_type")) not in {"unknown", "none", "not-applicable"} and normalize(event.get("graph_cache_status")) in GRAPH_GAP_VALUES
    )
    if scanner_graph_gap >= threshold:
        findings.append(
            finding(
                f"MH-F-{len(findings) + 1:03d}",
                "scanner-graph-gap",
                "high",
                scanner_graph_gap,
                threshold,
                f"{scanner_graph_gap} scanner-related event(s) lacked a healthy graph cache.",
                "strengthen-scanner-graph-overlay",
                "Route Sonar, static-analysis, and vulnerability tasks toward graph overlays when the user approves deeper reads.",
                "code-graph",
                [
                    "Run scanner overlay tests for Sonar and vulnerability inputs.",
                    "Verify Navigator still asks before heavy scanner reads.",
                ],
                "Revert scanner graph routing if it runs heavy reads without approval.",
            )
        )

    strategy_counts: Counter[str] = Counter(
        normalize(event.get("token_strategy"))
        for event in events
        if normalize(event.get("token_strategy")) not in {"unknown", "none", "not-applicable"}
    )
    weak_token_quality = {"fail", "weak", "missing", "unknown", "not-run", "skipped"}
    for strategy, count in strategy_counts.most_common():
        weak_count = sum(
            1
            for event in events
            if normalize(event.get("token_strategy")) == strategy
            and (
                normalize(event.get("validation_fit")) in WEAK_VALUES
                or normalize(event.get("token_quality_outcome")) in weak_token_quality
            )
        )
        if count >= threshold and weak_count >= threshold:
            findings.append(
                finding(
                    f"MH-F-{len(findings) + 1:03d}",
                    "token-strategy-quality-risk",
                    "high",
                    weak_count,
                    threshold,
                    f"Token strategy `{strategy}` appeared in {count} event(s); {weak_count} had weak validation or token quality outcomes.",
                    "tighten-token-strategy-quality-gate",
                    "Review the repeated token strategy and tighten reducer preservation, exactness routing, validation guidance, or proof gate behavior.",
                    "token-reducer",
                    [
                        "Add a Token Harness reducer or proof regression test for the repeated strategy.",
                        "Run Token Harness proof and reducer tests.",
                    ],
                    "Revert token strategy tuning if it blocks useful reductions or increases context for small safe tasks.",
                )
            )

    local_evidence_count = sum(1 for event in events if normalize(event.get("token_evidence_label")) == "local-evidence")
    measured_count = sum(1 for event in events if normalize(event.get("token_proof_label")) in {"measured", "benchmark-measured"})
    if local_evidence_count >= threshold and measured_count == 0:
        findings.append(
            finding(
                f"MH-F-{len(findings) + 1:03d}",
                "token-proof-gap",
                "medium",
                local_evidence_count,
                threshold,
                f"{local_evidence_count} token event(s) stayed at local-evidence with no measured proof label.",
                "improve-token-proof-path",
                "Improve telemetry import, proof report prompts, or post-task proof guidance so teams can move from local evidence to measured evidence when appropriate.",
                "token-proof-gate",
                [
                    "Run Token Harness proof tests.",
                    "Verify docs still block measured claims without complete telemetry.",
                ],
                "Revert proof guidance if it encourages fake or incomplete measured telemetry.",
            )
        )

    low_reduction_count = sum(1 for event in events if normalize(event.get("token_reduction_band")) in {"none", "low"})
    if low_reduction_count >= threshold:
        findings.append(
            finding(
                f"MH-F-{len(findings) + 1:03d}",
                "token-reduction-too-low",
                "medium",
                low_reduction_count,
                threshold,
                f"{low_reduction_count} token event(s) had none or low reduction bands.",
                "tune-token-reducer-thresholds",
                "Tune reducer thresholds or Navigator routing so Token Harness skips reducers when the expected reduction is too small.",
                "token-reducer",
                [
                    "Add reducer tests for small inputs that should skip reduction.",
                    "Run proof report smoke tests to confirm claim labels remain accurate.",
                ],
                "Restore prior reducer thresholds if useful medium/high reductions stop appearing.",
            )
        )

    eligible_holdout_events = [
        event
        for event in events
        if normalize(event.get("task_type")) not in {"security", "vulnerability", "release", "regulated", "production-incident", "auth", "permission", "permissions"}
        and normalize(event.get("token_strategy")) not in {"unknown", "none", "not-applicable"}
    ]
    holdout_count = sum(1 for event in eligible_holdout_events if normalize(event.get("token_holdout")) == "true")
    if len(eligible_holdout_events) >= threshold and holdout_count == 0:
        findings.append(
            finding(
                f"MH-F-{len(findings) + 1:03d}",
                "token-holdout-gap",
                "medium",
                len(eligible_holdout_events),
                threshold,
                f"{len(eligible_holdout_events)} eligible token event(s) had no holdout/control record.",
                "enable-token-holdout-guidance",
                "Improve proof workflow guidance so eligible non-sensitive tasks can use deterministic holdout when measured proof is needed.",
                "token-proof-gate",
                [
                    "Run holdout decision tests for sensitive and non-sensitive classes.",
                    "Verify sensitive classes remain excluded from holdout.",
                ],
                "Revert holdout guidance if it creates hidden or confusing workflow changes.",
            )
        )

    exactness_mismatch = sum(
        1
        for event in events
        if normalize(event.get("token_exactness_class")) == "must-be-exact"
        and normalize(event.get("token_strategy")) not in {"unknown", "none", "not-applicable", "exact-pass-through", "graph-first"}
    )
    if exactness_mismatch >= threshold:
        findings.append(
            finding(
                f"MH-F-{len(findings) + 1:03d}",
                "token-exactness-mismatch",
                "high",
                exactness_mismatch,
                threshold,
                f"{exactness_mismatch} event(s) paired must-be-exact content with a reduction-like token strategy.",
                "strengthen-token-exactness-gate",
                "Strengthen Token Harness exactness gate and Navigator token routing so must-be-exact content cannot be reduced.",
                "token-router",
                [
                    "Run Token Harness routing tests.",
                    "Run reducer tests that block protected exact content.",
                ],
                "Restore the prior exactness gate if legitimate graph-first source workflows are blocked.",
            )
        )

    return sorted(findings, key=lambda item: (-int(item["evidence_count"]), item["category"], item["finding_id"]))


def build_analysis_from_events(
    valid_events: list[dict[str, Any]],
    invalid_issues: list[str],
    input_count: int,
    threshold: int,
    input_issues: list[str] | None = None,
) -> dict[str, Any]:
    distributions = {
        "task_type": count_key(valid_events, "task_type"),
        "language_family": count_key(valid_events, "language_family"),
        "workflow_selected": count_key(valid_events, "workflow_selected"),
        "review_scope": count_key(valid_events, "review_scope"),
        "requirement_fulfillment": count_key(valid_events, "requirement_fulfillment"),
        "validation_fit": count_key(valid_events, "validation_fit"),
        "token_budget_fit": count_key(valid_events, "token_budget_fit"),
        "metric_confidence": count_key(valid_events, "metric_confidence"),
        "learning_signal": count_key(valid_events, "learning_signal"),
        "scanner_type": count_key(valid_events, "scanner_type"),
        "issue_type": count_key(valid_events, "issue_type"),
        "token_strategy": count_key(valid_events, "token_strategy"),
        "token_exactness_class": count_key(valid_events, "token_exactness_class"),
        "token_evidence_label": count_key(valid_events, "token_evidence_label"),
        "token_reduction_band": count_key(valid_events, "token_reduction_band"),
        "token_proof_label": count_key(valid_events, "token_proof_label"),
        "token_quality_outcome": count_key(valid_events, "token_quality_outcome"),
        "token_holdout": count_key(valid_events, "token_holdout"),
        "token_confidence_gate": count_key(valid_events, "token_confidence_gate"),
        "overall_fit": count_key(valid_events, "overall_fit"),
        "overall_score_band": count_key(valid_events, "overall_score_band"),
        "graph_cache_status": count_key(valid_events, "graph_cache_status"),
        "graph_cache_source": count_key(valid_events, "graph_cache_source"),
        "dimension_validation_fit": count_dimension(valid_events, "validation_fit"),
        "dimension_metric_confidence": count_dimension(valid_events, "metric_confidence"),
        "recommendation_codes": count_key(valid_events, "recommendation_codes"),
    }
    return {
        "schema_version": "1",
        "type": "tailtrail-meta-harness-analysis",
        "created_at": now(),
        "input_count": input_count,
        "valid_event_count": len(valid_events),
        "invalid_event_count": len(invalid_issues),
        "input_issue_count": len(input_issues or []),
        "threshold": threshold,
        "distributions": distributions,
        "findings": build_findings(valid_events, threshold),
        "registry_maturity": registry_maturity(),
        "invalid_issues": invalid_issues,
        "input_issues": input_issues or [],
        "privacy": "Analysis uses sanitized categorical shared metadata only. It does not include raw prompts, source, diffs, paths, repo names, branch names, users, private URLs, scanner raw output, secrets, or exact token usage.",
    }


def collect_paths(args: argparse.Namespace) -> list[Path]:
    paths: list[Path] = []
    roots = list(args.roots or [])
    if args.root is not None:
        roots.append(args.root)
    for root in roots:
        paths.append(root / SHARED_SUMMARY)
    paths.extend(args.summary or [])
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = path.resolve().as_posix() if path.exists() else path.as_posix()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def build_analysis(paths: list[Path], threshold: int = 2) -> dict[str, Any]:
    harness_review = load_harness_review()
    valid_events: list[dict[str, Any]] = []
    invalid_issues: list[str] = []
    input_issues: list[str] = []
    input_count = 0
    for path in paths:
        events, issues = read_jsonl(path)
        for issue in issues:
            if "input missing" in issue:
                input_issues.append(issue)
            else:
                invalid_issues.append(issue)
        for event in events:
            input_count += 1
            try:
                harness_review.validate_shared_event(event)
            except SystemExit as exc:
                invalid_issues.append(f"{path.as_posix()}: {exc}")
                continue
            valid_events.append(event)
    return build_analysis_from_events(valid_events, invalid_issues, input_count, threshold, input_issues)


def readiness_decision(
    tier: str,
    decision: str,
    confidence: str,
    reasons: list[str],
    next_actions: list[str],
    allowed_actions: list[str],
    blocked_actions: list[str],
) -> dict[str, Any]:
    return {
        "tier": tier,
        "decision": decision,
        "confidence": confidence,
        "reasons": reasons,
        "next_actions": next_actions,
        "allowed_actions": allowed_actions,
        "blocked_actions": blocked_actions,
    }


def count_weak_dimension(analysis: dict[str, Any], dimension: str) -> int:
    counts = analysis.get("distributions", {}).get(dimension, {})
    if not isinstance(counts, dict):
        return 0
    return sum(int(count) for label, count in counts.items() if normalize(label) in WEAK_FITS)


def build_readiness(analysis: dict[str, Any]) -> dict[str, Any]:
    valid_events = int(analysis.get("valid_event_count", 0))
    invalid_events = int(analysis.get("invalid_event_count", 0))
    input_issues = int(analysis.get("input_issue_count", 0))
    threshold = int(analysis.get("threshold", 2))
    findings = [item for item in analysis.get("findings", []) if isinstance(item, dict)]
    high_findings = [item for item in findings if item.get("severity") == "high"]
    maturity = analysis.get("registry_maturity", {}) if isinstance(analysis.get("registry_maturity"), dict) else {}
    registry_status = str(maturity.get("status", "unknown"))
    registry_issue_count = int(maturity.get("issue_count", 0) or 0)
    weak_metric = count_weak_dimension(analysis, "metric_confidence")
    weak_validation = count_weak_dimension(analysis, "validation_fit")
    has_enough_evidence = valid_events >= threshold
    sanitizer_clean = invalid_events == 0
    inputs_clean = input_issues == 0
    registry_healthy = registry_status == "healthy" and registry_issue_count == 0

    developer_reasons = [
        "Developer task mode must not run aggregation, proposal generation, hidden capture, or product tuning during normal work.",
    ]
    if findings:
        developer_reasons.append("Repeated harness findings exist, but developer task mode should only surface already-approved/productized guidance.")
    developer = readiness_decision(
        "developer-task",
        "stay_quiet",
        "high",
        developer_reasons,
        [
            "Continue normal Navigator, review, graph, scanner, or validation workflow.",
            "Run `tailtrail harness quick --root .` manually only when the user asks to review TailTrail behavior.",
        ],
        ["short advisory note only when a productized rule is directly relevant"],
        ["aggregation", "proposal generation", "metadata sharing", "automatic TailTrail edits", "user interruption"],
    )

    repo_reasons: list[str] = []
    repo_next: list[str] = []
    if valid_events == 0:
        repo_decision = "stay_quiet"
        repo_confidence = "high"
        repo_reasons.append("No valid sanitized harness events are available.")
        repo_next.append("Capture or dry-run sanitized shared summaries only after meaningful approved task outcomes exist.")
    elif invalid_events or input_issues:
        repo_decision = "advise_repo_maintainer"
        repo_confidence = "high"
        repo_reasons.append("Some shared harness inputs are missing or failed sanitizer validation.")
        repo_next.append("Run `tailtrail harness shared-sanitize --root .` and fix unsafe or malformed shared metadata before sharing.")
    elif findings:
        repo_decision = "advise_repo_maintainer"
        repo_confidence = "medium" if has_enough_evidence else "low"
        repo_reasons.append(f"{len(findings)} repeated behavior finding(s) crossed the local threshold.")
        repo_next.append("Review findings locally and decide whether they are repo-specific workflow training, docs, or central TailTrail candidates.")
    elif weak_metric or weak_validation:
        repo_decision = "advise_repo_maintainer"
        repo_confidence = "medium"
        repo_reasons.append("Weak metric or validation fit appears in sanitized evidence, but no repeated product finding crossed threshold.")
        repo_next.append("Improve local task outcome capture and validation evidence before proposing central TailTrail changes.")
    else:
        repo_decision = "stay_quiet"
        repo_confidence = "medium"
        repo_reasons.append("Sanitized evidence exists, but no repeated issue currently needs maintainer action.")
        repo_next.append("Keep collecting approved categorical evidence only when useful.")
    repo = readiness_decision(
        "repo-maintainer",
        repo_decision,
        repo_confidence,
        repo_reasons,
        repo_next,
        ["sanitizer review", "local harness review", "repo-specific workflow tuning", "dry-run shared summary review"],
        ["central product proposal without repeated clean evidence", "raw prompt/source/log sharing", "automatic source edits"],
    )

    central_reasons: list[str] = []
    central_next: list[str] = []
    central_decision = "stay_quiet"
    central_confidence = "low"
    if not has_enough_evidence:
        central_reasons.append(f"Only {valid_events} valid event(s); threshold is {threshold}.")
        central_next.append("Wait for more sanitized events before central product recommendations.")
    elif not sanitizer_clean or not inputs_clean:
        central_decision = "advise_repo_maintainer"
        central_confidence = "high"
        central_reasons.append("Evidence is not clean enough for central product use.")
        central_next.append("Fix sanitizer/input issues before central aggregation or proposal generation.")
    elif not registry_healthy:
        central_decision = "advise_repo_maintainer"
        central_confidence = "high"
        central_reasons.append(f"Feature registry status is `{registry_status}` with {registry_issue_count} issue(s).")
        central_next.append("Run `tailtrail registry validate --strict` and resolve drift before central proposal validation.")
    elif findings:
        central_decision = "recommend_central_tailtrail_improvement"
        central_confidence = "high" if high_findings else "medium"
        central_reasons.append(f"{len(findings)} clean repeated finding(s) crossed threshold with healthy registry metadata.")
        central_next.append("Run `tailtrail harness propose --root . --proposal-id MH-YYYY-MM-NNN` and review candidate edits before implementation.")
    else:
        central_reasons.append("Evidence is clean, but no repeated finding crossed the product-improvement threshold.")
        central_next.append("Stay quiet for product changes; keep monitoring sanitized evidence.")
    central = readiness_decision(
        "central-tailtrail-maintainer",
        central_decision,
        central_confidence,
        central_reasons,
        central_next,
        ["reviewable proposal generation when evidence is clean and repeated", "registry-aware impact review", "normal git-reviewed product changes"],
        ["automatic TailTrail edits", "weak evidence product claims", "raw data aggregation", "developer scoring"],
    )

    return {
        "schema_version": "1",
        "type": "tailtrail-meta-harness-readiness",
        "created_at": now(),
        "valid_event_count": valid_events,
        "invalid_event_count": invalid_events,
        "input_issue_count": input_issues,
        "threshold": threshold,
        "finding_count": len(findings),
        "high_finding_count": len(high_findings),
        "registry_status": registry_status,
        "registry_issue_count": registry_issue_count,
        "tiers": [developer, repo, central],
        "overall_decision": central["decision"] if central["decision"] != "stay_quiet" else repo["decision"],
        "privacy": "Readiness uses sanitized categorical shared metadata only. It does not include raw prompts, source, diffs, paths, repo names, branch names, users, private URLs, scanner raw output, secrets, or exact token usage.",
    }


def render_readiness_markdown(readiness: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Meta-Harness Readiness",
        "",
        f"- Overall decision: `{readiness['overall_decision']}`",
        f"- Valid events: `{readiness['valid_event_count']}`",
        f"- Invalid events/issues: `{readiness['invalid_event_count']}`",
        f"- Input issues: `{readiness['input_issue_count']}`",
        f"- Evidence threshold: `{readiness['threshold']}`",
        f"- Finding count: `{readiness['finding_count']}`",
        f"- Registry status: `{readiness['registry_status']}`",
        "",
        "## Tiers",
        "",
    ]
    for tier in readiness["tiers"]:
        lines.extend(
            [
                f"### {tier['tier']}",
                "",
                f"- Decision: `{tier['decision']}`",
                f"- Confidence: `{tier['confidence']}`",
                "- Reasons:",
            ]
        )
        lines.extend(f"  - {item}" for item in tier["reasons"])
        lines.append("- Next actions:")
        lines.extend(f"  - {item}" for item in tier["next_actions"])
        lines.append("- Allowed actions:")
        lines.extend(f"  - {item}" for item in tier["allowed_actions"])
        lines.append("- Blocked actions:")
        lines.extend(f"  - {item}" for item in tier["blocked_actions"])
        lines.append("")
    lines.extend(
        [
            "## Boundaries",
            "",
            "- Readiness is advisory and deterministic.",
            "- Developer task mode must stay quiet unless the user explicitly asks for Meta-Harness review.",
            "- Central product improvement requires clean sanitized evidence, repeated findings, and healthy registry metadata.",
            "- This command does not edit files, upload data, run models, score developers, or create product changes automatically.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_markdown(analysis: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Meta-Harness Analysis",
        "",
        f"- Valid events: `{analysis['valid_event_count']}`",
        f"- Invalid events/issues: `{analysis['invalid_event_count']}`",
        f"- Input issues: `{analysis.get('input_issue_count', 0)}`",
        f"- Evidence threshold: `{analysis['threshold']}`",
        "",
        "## Registry Maturity",
        "",
    ]
    maturity = analysis.get("registry_maturity", {})
    lines.extend(
        [
            f"- Status: `{maturity.get('status', 'unknown')}`",
            f"- Feature count: `{maturity.get('feature_count', 0)}`",
            f"- Issue count: `{maturity.get('issue_count', 0)}`",
        ]
    )
    surface_counts = maturity.get("surface_counts")
    if isinstance(surface_counts, dict):
        lines.append("- Surfaces: " + ", ".join(f"{key}={value}" for key, value in sorted(surface_counts.items())))
    if maturity.get("issues"):
        lines.append("- Registry issues:")
        for issue in maturity["issues"][:8]:
            lines.append(f"  - {issue}")
    lines.extend(
        [
            "",
        "## Findings",
        "",
        ]
    )
    findings = analysis.get("findings", [])
    if not findings:
        lines.append("- No repeated behavior pattern crossed the evidence threshold.")
    for item in findings:
        lines.extend(
            [
                f"### {item['finding_id']} - {item['category']}",
                "",
                f"- Severity: `{item['severity']}`",
                f"- Evidence count: `{item['evidence_count']}`",
                f"- Evidence: {item['evidence']}",
                f"- Recommendation: {item['recommendation']}",
                f"- Candidate change type: `{item['candidate_change_type']}`",
                "- Likely files:",
            ]
        )
        for file_name in item["likely_files"]:
            lines.append(f"  - `{file_name}`")
        lines.append("- Verification:")
        for check in item["verification"]:
            lines.append(f"  - {check}")
        lines.append(f"- Rollback: {item['rollback']}")
        lines.append("")

    lines.extend(["## Distributions", ""])
    for key, counts in analysis["distributions"].items():
        if not counts:
            continue
        compact = ", ".join(f"{name}={count}" for name, count in list(counts.items())[:8])
        lines.append(f"- `{key}`: {compact}")

    if analysis["invalid_issues"]:
        lines.extend(["", "## Sanitizer Issues", ""])
        for issue in analysis["invalid_issues"][:20]:
            lines.append(f"- {issue}")
        if len(analysis["invalid_issues"]) > 20:
            lines.append(f"- ... {len(analysis['invalid_issues']) - 20} more issue(s)")

    if analysis.get("input_issues"):
        lines.extend(["", "## Input Issues", ""])
        for issue in analysis["input_issues"][:20]:
            lines.append(f"- {issue}")
        if len(analysis["input_issues"]) > 20:
            lines.append(f"- ... {len(analysis['input_issues']) - 20} more issue(s)")

    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- This analysis is advisory and deterministic.",
            "- It does not edit TailTrail files.",
            "- Review recommendations before changing product behavior.",
            "- Do not use this output to score individual developers or claim exact ROI.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_outputs(root: Path, analysis: dict[str, Any]) -> None:
    directory = root / TAILTRAIL_DIR
    directory.mkdir(parents=True, exist_ok=True)
    (root / ANALYSIS_JSON).write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / ANALYSIS_MD).write_text(render_markdown(analysis), encoding="utf-8")


def write_readiness_outputs(root: Path, readiness: dict[str, Any]) -> None:
    directory = root / TAILTRAIL_DIR
    directory.mkdir(parents=True, exist_ok=True)
    (root / READINESS_JSON).write_text(json.dumps(readiness, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / READINESS_MD).write_text(render_readiness_markdown(readiness), encoding="utf-8")


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", type=Path, help="Target repo root containing tailtrail-meta/harness-summary.jsonl.")
    parser.add_argument("--roots", type=Path, action="append", help="Additional repo root to aggregate.")
    parser.add_argument("--summary", type=Path, action="append", help="Explicit shared harness summary JSONL file.")
    parser.add_argument("--threshold", type=int, default=2, help="Minimum repeated evidence count for a finding.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--write-result", action="store_true", help="Write local .tailtrail analysis outputs.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aggregate sanitized TailTrail Meta-Harness shared metadata.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("aggregate-shared", "analyze", "readiness"):
        sub = subparsers.add_parser(command, help=f"Run Meta-Harness {command}.")
        add_common_args(sub)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.threshold < 2:
        parser.error("--threshold must be 2 or greater; one event is not enough to tune product behavior")
    paths = collect_paths(args)
    if not paths:
        parser.error("provide --root, --roots, or --summary")
    analysis = build_analysis(paths, args.threshold)
    if args.command == "readiness":
        readiness = build_readiness(analysis)
        if args.write_result:
            write_root = args.root or (args.roots[0] if args.roots else Path("."))
            write_readiness_outputs(write_root, readiness)
        if args.format == "json":
            print(json.dumps(readiness, indent=2, sort_keys=True))
        else:
            print(render_readiness_markdown(readiness), end="")
        return 0
    if args.write_result:
        write_root = args.root or (args.roots[0] if args.roots else Path("."))
        write_outputs(write_root, analysis)
    if args.format == "json":
        print(json.dumps(analysis, indent=2, sort_keys=True))
    else:
        print(render_markdown(analysis), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
