#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIOS = ROOT / "benchmarks" / "efficacy"
DEFAULT_RESULT = ROOT / "benchmarks" / "results" / "efficacy-latest.md"


@dataclass(frozen=True)
class CriteriaResult:
    passed: bool
    reasons: list[str]


@dataclass(frozen=True)
class CheckResult:
    name: str
    points: int
    baseline_passed: bool | None
    tailtrail_passed: bool
    earned: int
    baseline_reasons: list[str]
    tailtrail_reasons: list[str]
    signal: str


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid JSON in {path}: {error}") from error
    if not isinstance(value, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return value


def read_text(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"Missing benchmark artifact: {path}")
    return path.read_text(encoding="utf-8")


def contains_all(text: str, patterns: list[str]) -> tuple[bool, str]:
    lowered = text.lower()
    missing = [pattern for pattern in patterns if pattern.lower() not in lowered]
    if missing:
        return False, "missing " + ", ".join(f"`{item}`" for item in missing)
    return True, "all expected patterns found"


def contains_any(text: str, patterns: list[str]) -> tuple[bool, str]:
    lowered = text.lower()
    for pattern in patterns:
        if pattern.lower() in lowered:
            return True, f"found `{pattern}`"
    return False, "none found: " + ", ".join(f"`{item}`" for item in patterns)


def must_not_contain_any(text: str, patterns: list[str]) -> tuple[bool, str]:
    lowered = text.lower()
    found = [pattern for pattern in patterns if pattern.lower() in lowered]
    if found:
        return False, "found forbidden " + ", ".join(f"`{item}`" for item in found)
    return True, "no forbidden patterns found"


def changed_line_count(text: str) -> int:
    count = 0
    for line in text.splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith(("+", "-")):
            count += 1
    return count


def criteria_result(text: str, criteria: dict[str, Any], baseline_text: str) -> CriteriaResult:
    reasons: list[str] = []
    passed = True
    for key, checker in (
        ("contains_all", contains_all),
        ("contains_any", contains_any),
        ("must_not_contain_any", must_not_contain_any),
    ):
        patterns = criteria.get(key, [])
        if patterns:
            ok, reason = checker(text, [str(item) for item in patterns])
            reasons.append(f"{key}: {reason}")
            passed = passed and ok

    if criteria.get("changed_lines_lte_baseline"):
        current = changed_line_count(text)
        baseline = changed_line_count(baseline_text)
        ok = current <= baseline
        reasons.append(f"changed_lines_lte_baseline: {current} <= {baseline}")
        passed = passed and ok

    max_changed_lines = criteria.get("max_changed_lines")
    if isinstance(max_changed_lines, int):
        current = changed_line_count(text)
        ok = current <= max_changed_lines
        reasons.append(f"max_changed_lines: {current} <= {max_changed_lines}")
        passed = passed and ok

    if not reasons:
        reasons.append("no criteria supplied")
        passed = False
    return CriteriaResult(passed=passed, reasons=reasons)


def score_check(check: dict[str, Any], baseline_text: str, tailtrail_text: str) -> CheckResult:
    name = str(check.get("name", "unnamed check"))
    points = int(check.get("points", 1))
    signal = str(check.get("signal", "general"))
    baseline_criteria = check.get("baseline")
    tailtrail_criteria = check.get("tailtrail")
    if not isinstance(tailtrail_criteria, dict):
        raise SystemExit(f"Efficacy check `{name}` is missing tailtrail criteria")

    baseline_result: CriteriaResult | None = None
    if isinstance(baseline_criteria, dict):
        baseline_result = criteria_result(baseline_text, baseline_criteria, baseline_text)
    tailtrail_result = criteria_result(tailtrail_text, tailtrail_criteria, baseline_text)
    return CheckResult(
        name=name,
        points=points,
        baseline_passed=baseline_result.passed if baseline_result else None,
        tailtrail_passed=tailtrail_result.passed,
        earned=points if tailtrail_result.passed else 0,
        baseline_reasons=baseline_result.reasons if baseline_result else ["not scored"],
        tailtrail_reasons=tailtrail_result.reasons,
        signal=signal,
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError as error:
            raise SystemExit(f"Invalid telemetry JSON on {path}:{line_number}: {error}") from error
        if not isinstance(value, dict):
            raise SystemExit(f"Invalid telemetry JSON on {path}:{line_number}: expected object")
        value["_line_number"] = line_number
        records.append(value)
    return records


def total_tokens(block: Any) -> int | None:
    if not isinstance(block, dict):
        return None
    total = block.get("total_tokens")
    if isinstance(total, int):
        return total
    input_tokens = block.get("input_tokens")
    output_tokens = block.get("output_tokens")
    if isinstance(input_tokens, int) and isinstance(output_tokens, int):
        return input_tokens + output_tokens
    return None


def percent(saved: int, baseline: int) -> float:
    if baseline <= 0:
        return 0.0
    return round((saved / baseline) * 100, 2)


def telemetry_summary(paths: list[Path]) -> dict[str, Any]:
    measured: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    for path in paths:
        for record in read_jsonl(path):
            if record.get("mode") != "measured":
                ignored.append({"file": path.as_posix(), "line": record.get("_line_number"), "reason": "mode is not measured"})
                continue
            baseline = total_tokens(record.get("baseline"))
            tailtrail = total_tokens(record.get("tailtrail"))
            if baseline is None or tailtrail is None:
                ignored.append({"file": path.as_posix(), "line": record.get("_line_number"), "reason": "missing baseline/tailtrail token totals"})
                continue
            saved = max(0, baseline - tailtrail)
            measured.append(
                {
                    "file": path.as_posix(),
                    "task_id": str(record.get("task_id", "unknown")),
                    "provider": str(record.get("provider", "unknown")),
                    "model": str(record.get("model", "unknown")),
                    "baseline_tokens": baseline,
                    "tailtrail_tokens": tailtrail,
                    "saved_tokens": saved,
                    "reduction_percent": percent(saved, baseline),
                    "source": str(record.get("source", "usage_metadata")),
                }
            )

    baseline_total = sum(item["baseline_tokens"] for item in measured)
    tailtrail_total = sum(item["tailtrail_tokens"] for item in measured)
    saved_total = max(0, baseline_total - tailtrail_total)
    return {
        "mode": "measured" if measured else "none",
        "measured_records": len(measured),
        "ignored_records": len(ignored),
        "records": measured,
        "ignored": ignored,
        "baseline_tokens": baseline_total,
        "tailtrail_tokens": tailtrail_total,
        "saved_tokens": saved_total,
        "reduction_percent": percent(saved_total, baseline_total),
        "claim_guardrail": (
            "Measured token reduction applies only to the listed records."
            if measured
            else "No exact token savings claim is available because no measured model/API telemetry was supplied."
        ),
    }


def scenario_dirs(root: Path, selected: str | None) -> list[Path]:
    if selected:
        path = root / selected
        if not path.is_dir():
            raise SystemExit(f"Unknown efficacy scenario: {selected}")
        return [path]
    return sorted(path for path in root.iterdir() if path.is_dir())


def score_scenario(path: Path) -> dict[str, Any]:
    expected = read_json(path / "expected.json")
    baseline_text = read_text(path / "baseline-artifact.md")
    tailtrail_text = read_text(path / "tailtrail-artifact.md")
    checks = [score_check(item, baseline_text, tailtrail_text) for item in expected.get("checks", [])]
    max_score = sum(item.points for item in checks)
    score = sum(item.earned for item in checks)
    baseline_signal_count = sum(1 for item in checks if item.baseline_passed)
    improved_count = sum(1 for item in checks if item.tailtrail_passed and item.baseline_passed is True)
    return {
        "name": path.name,
        "title": str(expected.get("title", path.name)),
        "description": str(expected.get("description", "")),
        "score": score,
        "max_score": max_score,
        "score_percent": round((score / max_score) * 100, 2) if max_score else 0.0,
        "baseline_signal_count": baseline_signal_count,
        "improved_signal_count": improved_count,
        "baseline_changed_lines": changed_line_count(baseline_text),
        "tailtrail_changed_lines": changed_line_count(tailtrail_text),
        "checks": [
            {
                "name": item.name,
                "signal": item.signal,
                "points": item.points,
                "earned": item.earned,
                "baseline_passed": item.baseline_passed,
                "tailtrail_passed": item.tailtrail_passed,
                "baseline_reasons": item.baseline_reasons,
                "tailtrail_reasons": item.tailtrail_reasons,
            }
            for item in checks
        ],
    }


def payload(scenarios_root: Path, selected: str | None, telemetry: list[Path]) -> dict[str, Any]:
    scenario_paths = scenario_dirs(scenarios_root, selected)
    scenarios = [score_scenario(path) for path in scenario_paths]
    scenario_telemetry = [path / "token-usage.jsonl" for path in scenario_paths]
    telemetry_paths = [*scenario_telemetry, *telemetry]
    token = telemetry_summary(telemetry_paths)
    max_score = sum(item["max_score"] for item in scenarios)
    score = sum(item["score"] for item in scenarios)
    return {
        "type": "tailtrail-efficacy-benchmark",
        "generated_at": now(),
        "scenarios_root": scenarios_root.as_posix(),
        "scenario_count": len(scenarios),
        "score": score,
        "max_score": max_score,
        "score_percent": round((score / max_score) * 100, 2) if max_score else 0.0,
        "baseline_changed_lines": sum(item["baseline_changed_lines"] for item in scenarios),
        "tailtrail_changed_lines": sum(item["tailtrail_changed_lines"] for item in scenarios),
        "scenarios": scenarios,
        "token_evidence": token,
        "claim_guardrails": [
            "This benchmark consumes committed artifacts only; it does not call live models.",
            "Scores are local evidence for these scenarios, not universal model/vendor claims.",
            "Exact token savings require measured model/API telemetry records.",
        ],
    }


def markdown(data: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Efficacy Benchmark",
        "",
        "- Evidence type: `artifact-based`",
        "- Live model calls: `none`",
        f"- Scenarios: `{data['scenario_count']}`",
        f"- Score: `{data['score']} / {data['max_score']}`",
        f"- Score percent: `{data['score_percent']}%`",
        f"- Baseline changed lines: `{data['baseline_changed_lines']}`",
        f"- TailTrail changed lines: `{data['tailtrail_changed_lines']}`",
        "",
        "## Scenarios",
        "",
    ]
    for scenario in data["scenarios"]:
        lines.extend(
            [
                f"### {scenario['title']}",
                "",
                f"- Scenario: `{scenario['name']}`",
                f"- Score: `{scenario['score']} / {scenario['max_score']}`",
                f"- Score percent: `{scenario['score_percent']}%`",
                f"- Baseline changed lines: `{scenario['baseline_changed_lines']}`",
                f"- TailTrail changed lines: `{scenario['tailtrail_changed_lines']}`",
                f"- Improved signals: `{scenario['improved_signal_count']}`",
                "",
                "| Check | Signal | Earned | TailTrail target | Baseline signal |",
                "|---|---|---:|---|---|",
            ]
        )
        for check in scenario["checks"]:
            tailtrail = "pass" if check["tailtrail_passed"] else "miss"
            baseline = "not scored" if check["baseline_passed"] is None else ("pass" if check["baseline_passed"] else "miss")
            lines.append(f"| {check['name']} | {check['signal']} | {check['earned']} / {check['points']} | {tailtrail} | {baseline} |")
        lines.append("")

    token = data["token_evidence"]
    lines.extend(
        [
            "## Token Evidence",
            "",
            f"- Mode: `{token['mode']}`",
            f"- Measured records: `{token['measured_records']}`",
            f"- Baseline tokens: `{token['baseline_tokens']}`",
            f"- TailTrail tokens: `{token['tailtrail_tokens']}`",
            f"- Saved tokens: `{token['saved_tokens']}`",
            f"- Reduction: `{token['reduction_percent']}%`",
            f"- Claim guardrail: {token['claim_guardrail']}",
            "",
        ]
    )
    if token["records"]:
        lines.extend(["| Task | Provider | Model | Before | With TailTrail | Difference | Reduction |", "|---|---|---|---:|---:|---:|---:|"])
        for record in token["records"]:
            lines.append(
                f"| {record['task_id']} | {record['provider']} | {record['model']} | {record['baseline_tokens']} | {record['tailtrail_tokens']} | {record['saved_tokens']} | {record['reduction_percent']}% |"
            )
        lines.append("")

    lines.extend(["## Claim Guardrails", ""])
    lines.extend(f"- {item}" for item in data["claim_guardrails"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run artifact-based TailTrail efficacy benchmarks.")
    parser.add_argument("--root", type=Path, default=DEFAULT_SCENARIOS, help="Efficacy scenario root.")
    parser.add_argument("--scenario", help="Run one efficacy scenario by folder name.")
    parser.add_argument("--telemetry", type=Path, action="append", default=[], help="Optional measured token telemetry JSONL.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--write-result", type=Path, nargs="?", const=DEFAULT_RESULT)
    args = parser.parse_args()

    data = payload(args.root.resolve(), args.scenario, args.telemetry)
    body = json.dumps(data, indent=2, sort_keys=True) if args.format == "json" else markdown(data)
    print(body)
    if args.write_result:
        args.write_result.parent.mkdir(parents=True, exist_ok=True)
        args.write_result.write_text(body + ("\n" if not body.endswith("\n") else ""), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
