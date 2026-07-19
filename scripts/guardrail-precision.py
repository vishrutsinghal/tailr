#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RULES = ("dependency-gate", "safeguard-removal", "local-state", "validation-claim")
CLAIM_GUARDRAILS = [
    "Precision numbers reflect only these committed fixtures; they are not a universal claim about any repo.",
    "Findings whose rule class does not match the scored rule do not count.",
    "Strict mode fails on below-threshold, insufficient-fixtures, or undefined rule status.",
]


def load_guardrail_check():
    path = ROOT / "scripts" / "guardrail-check.py"
    spec = importlib.util.spec_from_file_location("tailtrail_guardrail_check_precision", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Unable to read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return value


def fixture_paths(fixtures_root: Path, rule: str | None) -> list[Path]:
    rules = [rule] if rule else list(RULES)
    result: list[Path] = []
    for rule_name in rules:
        for label in ("expected-finding", "expected-clean"):
            result.extend(sorted((fixtures_root / rule_name / label).glob("*.diff")))
    return result


def scan_fixture(guardrail: Any, root: Path, diff_path: Path, meta: dict[str, Any]) -> list[Any]:
    diff = diff_path.read_text(encoding="utf-8")
    diff_lines, diff_files = guardrail.parse_diff(diff)
    extra = meta.get("extra_texts") if isinstance(meta.get("extra_texts"), dict) else {}
    extra_texts = [str(value) for value in extra.values()]
    claim_texts = [(f"{diff_path.as_posix()}:{key}", str(value)) for key, value in extra.items()]
    findings: list[Any] = []
    findings.extend(guardrail.check_dependency_gate(diff_lines, diff, extra_texts))
    findings.extend(guardrail.check_safeguard_removal(diff_lines))
    findings.extend(guardrail.check_local_state(diff_files, root))
    findings.extend(guardrail.check_validation_claims(claim_texts))
    return findings


def confidence(fixture_count: int) -> str:
    if fixture_count >= 20:
        return "high"
    if fixture_count >= 12:
        return "medium"
    return "low"


def divide(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def score_rule(rule: str, cases: list[dict[str, Any]], threshold: dict[str, Any]) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for case in cases:
        predicted = any(item.get("rule_class") == rule for item in case["findings"])
        if case["label"] == "expected-finding":
            if predicted:
                tp += 1
            else:
                fn += 1
        else:
            if predicted:
                fp += 1
            else:
                tn += 1
    positives = tp + fn
    negatives = fp + tn
    precision = divide(tp, tp + fp)
    recall = divide(tp, positives)
    fp_rate = divide(fp, negatives)
    fixture_count = positives + negatives
    min_fixtures = int(threshold.get("min_fixtures", 0))
    min_precision = float(threshold.get("min_precision", 1.0))
    if fixture_count < min_fixtures:
        status = "insufficient-fixtures"
        precision_reason = None
    elif precision is None:
        status = "undefined"
        precision_reason = "no-positive-predictions"
    elif precision < min_precision:
        status = "below-threshold"
        precision_reason = None
    else:
        status = "ok"
        precision_reason = None
    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "precision_reason": precision_reason,
        "recall": recall,
        "false_positive_rate": fp_rate,
        "fixture_count": fixture_count,
        "positive_fixtures": positives,
        "negative_fixtures": negatives,
        "confidence": confidence(fixture_count),
        "threshold": min_precision,
        "min_fixtures": min_fixtures,
        "status": status,
    }


def collect_cases(root: Path, fixtures_root: Path, selected_rule: str | None) -> dict[str, list[dict[str, Any]]]:
    guardrail = load_guardrail_check()
    cases: dict[str, list[dict[str, Any]]] = {rule: [] for rule in (selected_rule,) if rule} if selected_rule else {rule: [] for rule in RULES}
    for diff_path in fixture_paths(fixtures_root, selected_rule):
        meta_path = diff_path.with_suffix(".meta.json")
        meta = read_json(meta_path)
        rule = str(meta.get("rule"))
        label = str(meta.get("label"))
        if rule not in cases:
            continue
        if label not in {"expected-finding", "expected-clean"}:
            raise SystemExit(f"{meta_path}: label must be expected-finding or expected-clean")
        findings = [item.as_dict() for item in scan_fixture(guardrail, root, diff_path, meta)]
        cases[rule].append({"path": diff_path.as_posix(), "meta": meta_path.as_posix(), "label": label, "findings": findings})
    return cases


def build_report(root: Path, fixtures_root: Path, thresholds_path: Path, selected_rule: str | None, strict: bool) -> dict[str, Any]:
    thresholds = read_json(thresholds_path)
    threshold_rules = thresholds.get("rules")
    if not isinstance(threshold_rules, dict):
        raise SystemExit(f"{thresholds_path}: missing rules object")
    cases = collect_cases(root, fixtures_root, selected_rule)
    results: dict[str, Any] = {}
    below: list[str] = []
    for rule, rule_cases in cases.items():
        if rule not in threshold_rules:
            raise SystemExit(f"{thresholds_path}: missing threshold for {rule}")
        result = score_rule(rule, rule_cases, threshold_rules[rule])
        results[rule] = result
        if result["status"] != "ok":
            below.append(rule)
    return {
        "type": "tailtrail-guardrail-precision",
        "schema_version": "1",
        "evidence_type": "committed-fixture",
        "fixtures_root": fixtures_root.as_posix(),
        "thresholds": thresholds_path.as_posix(),
        "strict": strict,
        "total_fixtures": sum(item["fixture_count"] for item in results.values()),
        "rules": results,
        "claim_guardrails": CLAIM_GUARDRAILS,
        "below_threshold_rules": below,
    }


def fmt(value: float | None) -> str:
    if value is None:
        return "null"
    return f"{value:.2f}"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Guardrail Precision Baseline",
        "",
        "- Evidence type: `committed-fixture`",
        f"- Total fixtures: `{report['total_fixtures']}`",
        f"- Strict: `{'on' if report['strict'] else 'off'}`",
        "",
        "| Rule | Precision | Recall | FP rate | Fixtures | Confidence | Threshold | Status |",
        "|---|---:|---:|---:|---:|---|---:|---|",
    ]
    for rule, result in report["rules"].items():
        lines.append(
            f"| {rule} | {fmt(result['precision'])} | {fmt(result['recall'])} | {fmt(result['false_positive_rate'])} | "
            f"{result['fixture_count']} | {result['confidence']} | {result['threshold']:.2f} | {result['status']} |"
        )
    lines.extend(["", "## Below-threshold rules", ""])
    if report["below_threshold_rules"]:
        for rule in report["below_threshold_rules"]:
            result = report["rules"][rule]
            if result["precision"] is None:
                lines.append(f"- {rule}: {result['status']} ({result['precision_reason'] or 'no precision'}).")
            else:
                lines.append(f"- {rule}: precision {result['precision']:.2f} < floor {result['threshold']:.2f}.")
    else:
        lines.append("- none")
    lines.extend(["", "## Claim guardrails", ""])
    lines.extend(f"- {item}" for item in report["claim_guardrails"])
    return "\n".join(lines) + "\n"


def write_result(path: Path, report: dict[str, Any], output_format: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "json":
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        path.write_text(render_markdown(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure TailTrail guardrail precision against committed fixtures.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--fixtures-root", type=Path, default=ROOT / "benchmarks" / "guardrail-precision" / "fixtures")
    parser.add_argument("--thresholds", type=Path, default=ROOT / "benchmarks" / "guardrail-precision" / "thresholds.json")
    parser.add_argument("--rule", choices=RULES)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-result", type=Path)
    args = parser.parse_args()

    report = build_report(args.root.resolve(), args.fixtures_root.resolve(), args.thresholds.resolve(), args.rule, args.strict)
    if args.write_result:
        write_result(args.write_result, report, args.format)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report), end="")
    return 1 if args.strict and report["below_threshold_rules"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
