#!/usr/bin/env python3
"""Evaluate, calibrate, and safely project Learning V3 effectiveness evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "benchmarks" / "evaluation" / "learning-calibration" / "v1.json"
REPORT = Path(".tailtrail/evaluation/learning-calibration/report.json")
PROJECTION = Path(".tailtrail/learning-calibration.json")
META_SIGNALS = Path(".tailtrail/evaluation/learning-calibration/meta-signals.jsonl")
PRIVACY = {"sanitized": True, "raw_prompt": False, "raw_source": False, "raw_log": False, "identity_fields": False}
CLASSES = {
    "positive-pattern", "avoid-history", "validation-command", "project-convention",
    "dependency-decision", "debug-cause", "general",
}
POSITIVE = {"potentially-helped"}
NEGATIVE = {"possible-harm", "rejected-by-evidence", "stale"}


class CalibrationError(ValueError):
    pass


def load_module(name: str, relative: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def unsigned_digest(value: dict[str, Any]) -> str:
    unsigned = copy.deepcopy(value)
    unsigned.pop("integrity", None)
    return digest(unsigned)


def parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise CalibrationError(f"invalid evidence timestamp: {value}") from error
    if parsed.tzinfo is None:
        raise CalibrationError("calibration timestamps must include a timezone")
    return parsed


def exact_keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise CalibrationError(f"{label} contract is not closed")


def validate_integrity(value: dict[str, Any], label: str) -> None:
    integrity = value.get("integrity")
    exact_keys(integrity, {"algorithm", "canonicalization", "digest"}, f"{label} integrity")
    if integrity["algorithm"] != "sha256" or integrity["canonicalization"] != "sorted compact JSON excluding integrity":
        raise CalibrationError(f"{label} integrity contract is invalid")
    if integrity["digest"] != unsigned_digest(value):
        raise CalibrationError(f"{label} digest mismatch")


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise CalibrationError(f"{label} is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise CalibrationError(f"{label} is invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise CalibrationError(f"{label} must be an object")
    return value


def validate_catalog(value: dict[str, Any]) -> None:
    exact_keys(value, {"schema_version", "type", "catalog_version", "evidence_label", "minimum_class_samples", "meta_repeat_threshold", "classes", "claim_boundaries", "privacy", "integrity"}, "catalog")
    if value["schema_version"] != "1" or value["type"] != "tailtrail-learning-calibration-catalog":
        raise CalibrationError("catalog identity is invalid")
    if value["evidence_label"] not in {"fixture-observed", "measured"}:
        raise CalibrationError("catalog evidence label is invalid")
    if value["minimum_class_samples"] != 4:
        raise CalibrationError("catalog minimum class samples must be exactly four")
    if not isinstance(value["meta_repeat_threshold"], int) or value["meta_repeat_threshold"] < 2:
        raise CalibrationError("Meta-Harness repeat threshold must be at least two")
    if value["privacy"] != PRIVACY:
        raise CalibrationError("catalog privacy boundary is invalid")
    rows = value["classes"]
    if not isinstance(rows, list) or {row.get("learning_class") for row in rows if isinstance(row, dict)} != CLASSES or len(rows) != len(CLASSES):
        raise CalibrationError("catalog must cover each Learning V3 class exactly once")
    scenario_ids: set[str] = set()
    for row in rows:
        exact_keys(row, {"learning_class", "observations"}, "catalog class")
        observations = row["observations"]
        if not isinstance(observations, list) or len(observations) < value["minimum_class_samples"]:
            raise CalibrationError(f"class {row['learning_class']} has insufficient observations")
        for observation in observations:
            exact_keys(observation, {"scenario_id", "confidence_score", "expected_intervention", "observed_usefulness", "captured_at", "observed_at", "control", "learning"}, "catalog observation")
            if observation["scenario_id"] in scenario_ids:
                raise CalibrationError("scenario IDs must be unique")
            scenario_ids.add(observation["scenario_id"])
            score = observation["confidence_score"]
            if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 100:
                raise CalibrationError("confidence score must be an integer from zero through 100")
            if not isinstance(observation["expected_intervention"], bool) or not isinstance(observation["observed_usefulness"], bool):
                raise CalibrationError("observation labels must be boolean")
            if parse_time(observation["observed_at"]) <= parse_time(observation["captured_at"]):
                raise CalibrationError("observed outcome must be later than learning capture")
            exact_keys(observation["control"], {"correction_cycles", "review_time_ms", "input_tokens"}, "control metrics")
            exact_keys(observation["learning"], {"intervened", "correction_cycles", "review_time_ms", "input_tokens"}, "learning metrics")
            for metrics in (observation["control"], observation["learning"]):
                for key in ("correction_cycles", "review_time_ms", "input_tokens"):
                    if not isinstance(metrics[key], int) or isinstance(metrics[key], bool) or metrics[key] < 0:
                        raise CalibrationError(f"{key} must be a non-negative integer")
    if not isinstance(value["claim_boundaries"], list) or len(value["claim_boundaries"]) < 3:
        raise CalibrationError("catalog claim boundaries are incomplete")
    validate_integrity(value, "catalog")


def rounded(value: float) -> float:
    return round(value, 4)


def metrics(observations: list[dict[str, Any]]) -> dict[str, Any]:
    interventions = [row for row in observations if row["learning"]["intervened"]]
    useful = [row for row in interventions if row["observed_usefulness"]]
    false = [row for row in interventions if not row["observed_usefulness"]]
    non_useful = [row for row in observations if not row["observed_usefulness"]]
    confidence = [row["confidence_score"] / 100 for row in observations]
    outcomes = [1.0 if row["observed_usefulness"] else 0.0 for row in observations]
    return {
        "sample_count": len(observations),
        "intervention_count": len(interventions),
        "useful_interventions": len(useful),
        "false_interventions": len(false),
        "precision": rounded(len(useful) / len(interventions)) if interventions else 0.0,
        "false_intervention_rate": rounded(len(false) / len(non_useful)) if non_useful else 0.0,
        "mean_confidence": rounded(mean(confidence)),
        "observed_usefulness_rate": rounded(mean(outcomes)),
        "calibration_gap": rounded(abs(mean(confidence) - mean(outcomes))),
        "brier_score": rounded(mean((predicted - actual) ** 2 for predicted, actual in zip(confidence, outcomes))),
        "correction_cycle_delta": rounded(mean(row["learning"]["correction_cycles"] - row["control"]["correction_cycles"] for row in observations)),
        "review_time_delta_ms": rounded(mean(row["learning"]["review_time_ms"] - row["control"]["review_time_ms"] for row in observations)),
        "token_overhead": rounded(mean(row["learning"]["input_tokens"] - row["control"]["input_tokens"] for row in observations)),
    }


def project_observations(root: Path) -> list[dict[str, Any]]:
    receipts = load_module("learning_calibration_receipts", "learning-use-receipt.py")
    v3 = load_module("learning_calibration_v3", "learning-v3.py")
    records = {row["record_id"]: row for row in v3.read_records(root)}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in receipts.project_events(root):
        grouped.setdefault(event["receipt_id"], []).append(event)
    observations: list[dict[str, Any]] = []
    for receipt_id, events in sorted(grouped.items()):
        decision_indexes = [index for index, event in enumerate(events) if event["event_kind"] == "decision"]
        if not decision_indexes:
            continue
        decision_index = max(decision_indexes)
        decision = events[decision_index]
        later = [event for event in events[decision_index + 1:] if event["event_kind"] == "attribution"]
        if not later or decision["decision"] != "applied":
            continue
        attribution = later[-1]
        association = attribution["outcome"]["association"]
        if association not in POSITIVE | NEGATIVE:
            continue
        record = records.get(decision["learning_record_id"])
        completion_ref = attribution["outcome"]["completion_report_ref"]
        if (
            not record
            or parse_time(attribution["recorded_at"]) <= parse_time(record["freshness"]["captured_at"])
            or not (root / completion_ref).is_file()
        ):
            continue
        observations.append({
            "receipt_id": receipt_id,
            "learning_class": record["learning_class"],
            "confidence_score": decision["proposal"]["confidence_score"],
            "observed_usefulness": association in POSITIVE,
        })
    return observations


def project_metrics(observations: list[dict[str, Any]], minimum: int) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for learning_class in sorted(CLASSES):
        rows = [row for row in observations if row["learning_class"] == learning_class]
        if not rows:
            continue
        positives = sum(bool(row["observed_usefulness"]) for row in rows)
        negatives = len(rows) - positives
        mean_confidence = mean(row["confidence_score"] for row in rows)
        observed_rate = positives / len(rows) * 100
        eligible = len(rows) >= minimum and positives > 0 and negatives > 0
        adjustment = max(-10, min(10, round((observed_rate - mean_confidence) * 0.25))) if eligible else 0
        result.append({
            "learning_class": learning_class, "sample_count": len(rows), "positive_count": positives,
            "negative_count": negatives, "mean_confidence": rounded(mean_confidence / 100),
            "observed_usefulness_rate": rounded(observed_rate / 100),
            "calibration_gap": rounded(abs(mean_confidence - observed_rate) / 100),
            "suggested_adjustment": adjustment, "eligible": eligible,
        })
    return result


def evaluate(catalog: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    validate_catalog(catalog)
    class_rows = []
    all_observations: list[dict[str, Any]] = []
    for row in sorted(catalog["classes"], key=lambda item: item["learning_class"]):
        all_observations.extend(row["observations"])
        class_rows.append({"learning_class": row["learning_class"], **metrics(row["observations"])})
    project_rows = project_metrics(project_observations(root), catalog["minimum_class_samples"]) if root else []
    fixture_only = catalog["evidence_label"] == "fixture-observed"
    report = {
        "schema_version": "1", "type": "tailtrail-learning-calibration-report",
        "catalog": {"version": catalog["catalog_version"], "digest": catalog["integrity"]["digest"], "evidence_label": catalog["evidence_label"]},
        "project_frame": load_module("learning_calibration_frame", "learning-v3.py").project_frame(root) if root else None,
        "overall": metrics(all_observations), "classes": class_rows, "project_calibration": project_rows,
        "claims": {
            "posture": "fixture-only-no-public-performance-claim" if fixture_only else "scenario-scoped-measured",
            "publishable": [] if fixture_only else ["Metrics apply only to the named, versioned calibration scenarios in this report."],
            "boundaries": catalog["claim_boundaries"],
        },
        "privacy": PRIVACY,
        "integrity": {"algorithm": "sha256", "canonicalization": "sorted compact JSON excluding integrity", "digest": ""},
    }
    report["integrity"]["digest"] = unsigned_digest(report)
    validate_report(report)
    return report


def validate_report(report: dict[str, Any]) -> None:
    exact_keys(report, {"schema_version", "type", "catalog", "project_frame", "overall", "classes", "project_calibration", "claims", "privacy", "integrity"}, "report")
    if report["schema_version"] != "1" or report["type"] != "tailtrail-learning-calibration-report" or report["privacy"] != PRIVACY:
        raise CalibrationError("report identity or privacy boundary is invalid")
    exact_keys(report["catalog"], {"version", "digest", "evidence_label"}, "report catalog reference")
    if (
        not isinstance(report["catalog"]["version"], str)
        or report["catalog"]["evidence_label"] not in {"fixture-observed", "measured"}
        or not re.fullmatch(r"[0-9a-f]{64}", str(report["catalog"]["digest"]))
    ):
        raise CalibrationError("report catalog reference is invalid")
    if report["project_frame"] is not None and not re.fullmatch(r"sha256:[0-9a-f]{64}", str(report["project_frame"])):
        raise CalibrationError("report project frame is invalid")
    metric_keys = {"sample_count", "intervention_count", "useful_interventions", "false_interventions", "precision", "false_intervention_rate", "mean_confidence", "observed_usefulness_rate", "calibration_gap", "brier_score", "correction_cycle_delta", "review_time_delta_ms", "token_overhead"}
    def validate_metrics(row: dict[str, Any], label: str, minimum: int) -> None:
        exact_keys(row, metric_keys | ({"learning_class"} if "learning_class" in row else set()), label)
        for key in ("sample_count", "intervention_count", "useful_interventions", "false_interventions"):
            if not isinstance(row[key], int) or isinstance(row[key], bool) or row[key] < 0:
                raise CalibrationError(f"{label} {key} is invalid")
        if row["sample_count"] < minimum or not row["useful_interventions"] <= row["intervention_count"] <= row["sample_count"] or row["false_interventions"] > row["intervention_count"]:
            raise CalibrationError(f"{label} classification counts are invalid")
        for key in ("precision", "false_intervention_rate", "mean_confidence", "observed_usefulness_rate", "calibration_gap", "brier_score"):
            if not isinstance(row[key], (int, float)) or isinstance(row[key], bool) or not math.isfinite(row[key]) or not 0 <= row[key] <= 1:
                raise CalibrationError(f"{label} {key} is invalid")
        for key in ("correction_cycle_delta", "review_time_delta_ms", "token_overhead"):
            if not isinstance(row[key], (int, float)) or isinstance(row[key], bool) or not math.isfinite(row[key]):
                raise CalibrationError(f"{label} {key} is invalid")
    validate_metrics(report["overall"], "overall metrics", 28)
    if not isinstance(report["classes"], list) or len(report["classes"]) != len(CLASSES) or {row.get("learning_class") for row in report["classes"] if isinstance(row, dict)} != CLASSES:
        raise CalibrationError("report class coverage is incomplete")
    for row in report["classes"]:
        validate_metrics(row, "class metrics", 4)
        if row["learning_class"] not in CLASSES:
            raise CalibrationError("class metric learning class is invalid")
    project_keys = {"learning_class", "sample_count", "positive_count", "negative_count", "mean_confidence", "observed_usefulness_rate", "calibration_gap", "suggested_adjustment", "eligible"}
    if not isinstance(report["project_calibration"], list):
        raise CalibrationError("project calibration must be an array")
    seen_project_classes: set[str] = set()
    for row in report["project_calibration"]:
        exact_keys(row, project_keys, "project calibration")
        counts = (row["sample_count"], row["positive_count"], row["negative_count"])
        numbers = (row["mean_confidence"], row["observed_usefulness_rate"], row["calibration_gap"])
        valid_counts = all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in counts)
        expected_eligible = valid_counts and row["sample_count"] >= 4 and row["positive_count"] > 0 and row["negative_count"] > 0
        if (
            row["learning_class"] not in CLASSES
            or row["learning_class"] in seen_project_classes
            or not valid_counts
            or row["sample_count"] != row["positive_count"] + row["negative_count"]
            or any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or not 0 <= value <= 1 for value in numbers)
            or not isinstance(row["eligible"], bool)
            or row["eligible"] != expected_eligible
            or not isinstance(row["suggested_adjustment"], int)
            or isinstance(row["suggested_adjustment"], bool)
            or not -10 <= row["suggested_adjustment"] <= 10
            or (not row["eligible"] and row["suggested_adjustment"] != 0)
        ):
            raise CalibrationError("project calibration row is invalid")
        seen_project_classes.add(row["learning_class"])
    exact_keys(report["claims"], {"posture", "publishable", "boundaries"}, "claims")
    if (
        report["claims"]["posture"] not in {"fixture-only-no-public-performance-claim", "scenario-scoped-measured"}
        or not isinstance(report["claims"]["publishable"], list)
        or not isinstance(report["claims"]["boundaries"], list)
        or not report["claims"]["boundaries"]
        or any(not isinstance(value, str) or not value for value in report["claims"]["publishable"] + report["claims"]["boundaries"])
    ):
        raise CalibrationError("report claim boundary is invalid")
    if report["catalog"]["evidence_label"] == "fixture-observed" and (report["claims"]["posture"] != "fixture-only-no-public-performance-claim" or report["claims"]["publishable"]):
        raise CalibrationError("fixture evidence cannot support public performance claims")
    validate_integrity(report, "report")


def safe_relative(root: Path, path: Path) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except (OSError, ValueError) as error:
        raise CalibrationError("calibration artifact must be inside the project") from error
    if ".." in relative.parts:
        raise CalibrationError("calibration artifact path is unsafe")
    return relative.as_posix()


def apply_report(root: Path, report_path: Path, approved: bool) -> dict[str, Any]:
    if not approved:
        raise CalibrationError("applying project calibration requires --approved")
    report = read_json(report_path, "calibration report")
    validate_report(report)
    v3 = load_module("learning_calibration_apply_v3", "learning-v3.py")
    frame = v3.project_frame(root)
    if report["project_frame"] != frame:
        raise CalibrationError("calibration report crosses the project-frame boundary")
    expected_rows = project_metrics(project_observations(root), 4)
    if report["project_calibration"] != expected_rows:
        raise CalibrationError("calibration report does not match current validated later project receipts")
    eligible = [row for row in report["project_calibration"] if row["eligible"]]
    if not eligible:
        raise CalibrationError("no learning class has sufficient mixed later receipt outcomes for calibration")
    projection = {
        "schema_version": "1", "type": "tailtrail-learning-calibration-projection", "project_frame": frame,
        "source_report": {"path": safe_relative(root, report_path), "digest": report["integrity"]["digest"]},
        "minimum_class_samples": 4,
        "adjustments": {row["learning_class"]: row["suggested_adjustment"] for row in eligible},
        "boundary": "Project-local confidence adjustment only. It grants no advice-use, source-edit, command, Git, deployment, or acceptance authority.",
        "integrity": {"algorithm": "sha256", "canonicalization": "sorted compact JSON excluding integrity", "digest": ""},
    }
    projection["integrity"]["digest"] = unsigned_digest(projection)
    validate_projection(root, projection)
    target = root / PROJECTION
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(projection, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return projection


def validate_projection(root: Path, projection: dict[str, Any]) -> None:
    exact_keys(projection, {"schema_version", "type", "project_frame", "source_report", "minimum_class_samples", "adjustments", "boundary", "integrity"}, "projection")
    if projection["schema_version"] != "1" or projection["type"] != "tailtrail-learning-calibration-projection":
        raise CalibrationError("projection identity is invalid")
    if not isinstance(projection["minimum_class_samples"], int) or isinstance(projection["minimum_class_samples"], bool) or projection["minimum_class_samples"] < 4:
        raise CalibrationError("projection minimum class samples is invalid")
    v3 = load_module("learning_calibration_validate_v3", "learning-v3.py")
    if projection["project_frame"] != v3.project_frame(root):
        raise CalibrationError("calibration projection crosses the project-frame boundary")
    exact_keys(projection["source_report"], {"path", "digest"}, "projection report reference")
    source = (root / projection["source_report"]["path"]).resolve()
    safe_relative(root, source)
    report = read_json(source, "source calibration report")
    validate_report(report)
    if report["integrity"]["digest"] != projection["source_report"]["digest"] or report["project_frame"] != projection["project_frame"]:
        raise CalibrationError("calibration projection source report changed or crosses the project frame")
    if report["project_calibration"] != project_metrics(project_observations(root), projection["minimum_class_samples"]):
        raise CalibrationError("calibration projection no longer matches current validated later project receipts")
    if not isinstance(projection["adjustments"], dict) or not projection["adjustments"]:
        raise CalibrationError("calibration projection has no adjustments")
    for learning_class, adjustment in projection["adjustments"].items():
        if learning_class not in CLASSES or not isinstance(adjustment, int) or isinstance(adjustment, bool) or not -10 <= adjustment <= 10:
            raise CalibrationError("calibration projection adjustment is invalid")
    expected_adjustments = {
        row["learning_class"]: row["suggested_adjustment"]
        for row in report["project_calibration"] if row["eligible"]
    }
    if projection["adjustments"] != expected_adjustments:
        raise CalibrationError("calibration projection adjustments do not match the source report")
    validate_integrity(projection, "projection")


def load_adjustments(root: Path) -> tuple[dict[str, int], list[str]]:
    path = root / PROJECTION
    if not path.is_file():
        return {}, []
    try:
        projection = read_json(path, "calibration projection")
        validate_projection(root, projection)
    except (CalibrationError, OSError, ValueError, json.JSONDecodeError) as error:
        return {}, [f"learning calibration is invalid: {error}"]
    return {str(key): int(value) for key, value in projection["adjustments"].items()}, []


def shared_event(learning_class: str, month: str, evidence_label: str) -> dict[str, Any]:
    issue = f"learning-class-{learning_class}"
    return {
        "schema_version": "1", "event_type": "harness_summary", "tailtrail_version": "local",
        "created_month": month, "task_type": "learning-calibration", "language_family": "unknown",
        "workflow_selected": ["learning-v3"], "review_scope": "learning-class", "requirement_fulfillment": "aligned",
        "clarification_needed": False, "validation_fit": "strong", "token_budget_fit": "measured-fixture",
        "metric_confidence": "scenario-scoped", "learning_signal": "calibration-gap", "scanner_type": "none",
        "issue_type": issue, "token_strategy": "unknown", "token_exactness_class": "unknown",
        "token_evidence_label": evidence_label, "token_reduction_band": "unknown", "token_proof_label": "scenario-scoped",
        "token_quality_outcome": "measured-fixture", "token_holdout": "true", "token_confidence_gate": "closed",
        "overall_fit": "weak", "overall_score_band": "40-59", "dimension_fits": {"learning_fit": "weak", "metric_confidence": "scenario-scoped", "validation_fit": "strong"},
        "artifact_presence": {"learning_calibration": "present"}, "graph_cache_status": "not-applicable", "graph_cache_source": "not-applicable",
        "recommendation_codes": [f"calibrate-learning-class-{learning_class}"],
        "privacy": "Categorical sanitized learning calibration evidence only",
    }


def meta_feed(catalog: dict[str, Any], output: Path) -> dict[str, Any]:
    validate_catalog(catalog)
    harness = load_module("learning_calibration_harness_review", "harness-review.py")
    events: list[dict[str, Any]] = []
    threshold = catalog["meta_repeat_threshold"]
    for row in sorted(catalog["classes"], key=lambda item: item["learning_class"]):
        gaps = [observation for observation in row["observations"] if abs(observation["confidence_score"] - (100 if observation["observed_usefulness"] else 0)) >= 20]
        if len(gaps) < threshold:
            continue
        for observation in gaps:
            event = shared_event(row["learning_class"], observation["observed_at"][:7], catalog["evidence_label"])
            harness.validate_shared_event(event)
            events.append(event)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(event, sort_keys=True) + "\n" for event in events), encoding="utf-8")
    return {"state": "written" if events else "quiet", "event_count": len(events), "path": output.as_posix(), "repeat_threshold": threshold, "privacy": "categorical-sanitized-only"}


def write_report(root: Path, report: dict[str, Any], output: Path) -> Path:
    target = output if output.is_absolute() else root / output
    safe_relative(root, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    evaluate_parser = sub.add_parser("evaluate")
    evaluate_parser.add_argument("--root", type=Path, default=Path.cwd())
    evaluate_parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    evaluate_parser.add_argument("--include-receipts", action="store_true")
    evaluate_parser.add_argument("--write", action="store_true")
    evaluate_parser.add_argument("--output", type=Path, default=REPORT)
    evaluate_parser.add_argument("--format", choices=("json", "summary"), default="summary")
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("artifact", type=Path)
    validate_parser.add_argument("--root", type=Path, default=Path.cwd())
    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("--root", type=Path, default=Path.cwd())
    apply_parser.add_argument("--report", type=Path, default=REPORT)
    apply_parser.add_argument("--approved", action="store_true")
    meta_parser = sub.add_parser("meta-feed")
    meta_parser.add_argument("--root", type=Path, default=Path.cwd())
    meta_parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    meta_parser.add_argument("--output", type=Path, default=META_SIGNALS)
    args = parser.parse_args()
    try:
        if args.command == "evaluate":
            root = args.root.resolve()
            catalog = read_json(args.catalog, "calibration catalog")
            report = evaluate(catalog, root if args.include_receipts else None)
            if args.write:
                write_report(root, report, args.output)
            if args.format == "json":
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                print(f"Learning calibration: {report['overall']['sample_count']} paired observations; precision={report['overall']['precision']:.4f}; false_intervention_rate={report['overall']['false_intervention_rate']:.4f}; token_overhead={report['overall']['token_overhead']:.4f}; claim_posture={report['claims']['posture']}")
            return 0
        if args.command == "validate":
            value = read_json(args.artifact, "calibration artifact")
            if value.get("type") == "tailtrail-learning-calibration-catalog":
                validate_catalog(value)
            elif value.get("type") == "tailtrail-learning-calibration-report":
                validate_report(value)
            elif value.get("type") == "tailtrail-learning-calibration-projection":
                validate_projection(args.root.resolve(), value)
            else:
                raise CalibrationError("unsupported calibration artifact type")
            print(f"Learning calibration artifact is valid: {args.artifact}")
            return 0
        if args.command == "apply":
            root = args.root.resolve()
            report_path = args.report if args.report.is_absolute() else root / args.report
            value = apply_report(root, report_path, args.approved)
            print(json.dumps(value, indent=2, sort_keys=True))
            return 0
        root = args.root.resolve()
        catalog = read_json(args.catalog, "calibration catalog")
        output = args.output if args.output.is_absolute() else root / args.output
        safe_relative(root, output)
        print(json.dumps(meta_feed(catalog, output), indent=2, sort_keys=True))
        return 0
    except (CalibrationError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Learning calibration error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
