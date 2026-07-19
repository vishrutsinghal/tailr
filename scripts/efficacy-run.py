#!/usr/bin/env python3
"""TailTrail measured-efficacy runner (BL-1).

Consumes committed efficacy scenarios and paired token telemetry to produce
a report that clearly separates:

- artifact evidence (deterministic pattern checks on committed baseline/TailTrail
  artifacts), and
- token evidence, labeled `measured` only when a scenario supplies complete
  baseline + TailTrail token records, or `estimate` (with an explicit reason)
  otherwise.

Guardrails:

- No network calls, no live model calls, no provider API keys.
- Reports never label estimated numbers as measured.
- Half-populated telemetry records (mode=measured with missing token totals)
  are ignored by default and cause a non-zero exit under ``--strict``.
- All computation uses the Python standard library only.

Design notes:

- This runner is intentionally separate from ``efficacy-benchmark.py`` (V3.4).
  The V3.4 script produces artifact scores; this runner adds strict token
  evidence labeling and CI-friendly acceptance checks described in the
  ``Review-Driven Backlog`` -> BL-1 in ``ROADMAP.md``.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIOS = ROOT / "benchmarks" / "efficacy"
DEFAULT_RESULT = ROOT / "benchmarks" / "results" / "efficacy-run-latest.md"


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_text(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"Missing efficacy artifact: {path}")
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid JSON in {path}: {error}") from error
    if not isinstance(value, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return value


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
            raise SystemExit(
                f"Invalid telemetry JSON on {path}:{line_number}: {error}"
            ) from error
        if not isinstance(value, dict):
            raise SystemExit(
                f"Invalid telemetry JSON on {path}:{line_number}: expected object"
            )
        value["_line_number"] = line_number
        records.append(value)
    return records


def read_optional_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not path.is_file():
        return [], []
    rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError as error:
            issues.append({"file": path.as_posix(), "line": line_number, "reason": error.msg})
            continue
        if isinstance(value, dict):
            rows.append(value)
        else:
            issues.append({"file": path.as_posix(), "line": line_number, "reason": "record is not an object"})
    return rows, issues


def approx_char_count(text: str) -> int:
    return len(text)


# ---------------------------------------------------------------------------
# artifact evidence (deterministic pattern checks)
# ---------------------------------------------------------------------------


def contains_all(text: str, patterns: list[str]) -> tuple[bool, str]:
    lowered = text.lower()
    missing = [p for p in patterns if p.lower() not in lowered]
    if missing:
        return False, "missing " + ", ".join(f"`{p}`" for p in missing)
    return True, "all expected patterns found"


def contains_any(text: str, patterns: list[str]) -> tuple[bool, str]:
    lowered = text.lower()
    for pattern in patterns:
        if pattern.lower() in lowered:
            return True, f"found `{pattern}`"
    return False, "none found: " + ", ".join(f"`{p}`" for p in patterns)


def must_not_contain_any(text: str, patterns: list[str]) -> tuple[bool, str]:
    lowered = text.lower()
    found = [p for p in patterns if p.lower() in lowered]
    if found:
        return False, "found forbidden " + ", ".join(f"`{p}`" for p in found)
    return True, "no forbidden patterns found"


def changed_line_count(text: str) -> int:
    count = 0
    for line in text.splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith(("+", "-")):
            count += 1
    return count


@dataclass(frozen=True)
class CriteriaResult:
    passed: bool
    reasons: list[str]


def evaluate_criteria(text: str, criteria: dict[str, Any], baseline_text: str) -> CriteriaResult:
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

    max_changed = criteria.get("max_changed_lines")
    if isinstance(max_changed, int):
        current = changed_line_count(text)
        ok = current <= max_changed
        reasons.append(f"max_changed_lines: {current} <= {max_changed}")
        passed = passed and ok

    if not reasons:
        reasons.append("no criteria supplied")
        passed = False
    return CriteriaResult(passed=passed, reasons=reasons)


def score_check(
    check: dict[str, Any], baseline_text: str, tailtrail_text: str
) -> dict[str, Any]:
    name = str(check.get("name", "unnamed check"))
    points = int(check.get("points", 1))
    signal = str(check.get("signal", "general"))
    baseline_criteria = check.get("baseline")
    tailtrail_criteria = check.get("tailtrail")
    if not isinstance(tailtrail_criteria, dict):
        raise SystemExit(f"Efficacy check `{name}` is missing tailtrail criteria")

    baseline_result: CriteriaResult | None = None
    if isinstance(baseline_criteria, dict):
        baseline_result = evaluate_criteria(baseline_text, baseline_criteria, baseline_text)
    tailtrail_result = evaluate_criteria(tailtrail_text, tailtrail_criteria, baseline_text)
    return {
        "name": name,
        "signal": signal,
        "points": points,
        "earned": points if tailtrail_result.passed else 0,
        "baseline_passed": baseline_result.passed if baseline_result else None,
        "tailtrail_passed": tailtrail_result.passed,
        "baseline_reasons": baseline_result.reasons if baseline_result else ["not scored"],
        "tailtrail_reasons": tailtrail_result.reasons,
    }


# ---------------------------------------------------------------------------
# token evidence (strict measured vs estimate)
# ---------------------------------------------------------------------------


def total_tokens(block: Any) -> int | None:
    """Return an integer token total, or ``None`` when the block is incomplete.

    A valid measured token block must supply either ``total_tokens`` as an int,
    or both ``input_tokens`` and ``output_tokens`` as ints. Any other shape
    (missing block, missing keys, or non-int values) is treated as incomplete.
    """
    if not isinstance(block, dict):
        return None
    total = block.get("total_tokens")
    if isinstance(total, int) and not isinstance(total, bool):
        return total
    input_tokens = block.get("input_tokens")
    output_tokens = block.get("output_tokens")
    if (
        isinstance(input_tokens, int)
        and not isinstance(input_tokens, bool)
        and isinstance(output_tokens, int)
        and not isinstance(output_tokens, bool)
    ):
        return input_tokens + output_tokens
    return None


def percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def token_harness_ledger_evidence(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {
            "provided": False,
            "path": "",
            "events": 0,
            "event_types": {},
            "tokens_before": 0,
            "tokens_after": 0,
            "tokens_saved": 0,
            "quality_passed": 0,
            "quality_failed": 0,
            "issues": [],
        }
    rows, issues = read_optional_jsonl(path)
    events = [row for row in rows if row.get("type") == "tailtrail-token-harness-event"]
    before = sum(int(row.get("tokens_before", 0)) for row in events if isinstance(row.get("tokens_before"), int))
    after = sum(int(row.get("tokens_after", 0)) for row in events if isinstance(row.get("tokens_after"), int))
    event_types: dict[str, int] = {}
    for row in events:
        event_type = str(row.get("event_type", "unknown"))
        event_types[event_type] = event_types.get(event_type, 0) + 1
    return {
        "provided": True,
        "path": path.as_posix(),
        "events": len(events),
        "event_types": event_types,
        "tokens_before": before,
        "tokens_after": after,
        "tokens_saved": max(0, before - after),
        "quality_passed": sum(1 for row in events if row.get("event_type") == "quality_result" and row.get("validation_outcome") == "pass"),
        "quality_failed": sum(1 for row in events if row.get("event_type") == "quality_result" and row.get("validation_outcome") == "fail"),
        "issues": issues,
    }


@dataclass(frozen=True)
class TokenEvidence:
    label: str
    reason: str
    records: list[dict[str, Any]]
    ignored: list[dict[str, Any]]
    baseline_tokens: int
    tailtrail_tokens: int
    saved_tokens: int
    reduction_percent: float
    estimate_details: dict[str, Any] | None


def evaluate_token_evidence(
    telemetry_path: Path,
    baseline_text: str,
    tailtrail_text: str,
    *,
    strict: bool,
) -> TokenEvidence:
    """Produce token evidence with a strict measured/estimate label.

    - ``measured``: telemetry file exists, at least one record has complete
      baseline + TailTrail token totals, and no record advertises
      ``mode=measured`` while missing token blocks. Only complete records
      contribute to reduction numbers.
    - ``estimate``: no telemetry file, or telemetry exists but no complete
      measured record could be extracted. In this case, numbers come from a
      local character-count approximation of the two artifact files, which is
      clearly labeled as an estimate and MUST NOT be presented as tokens.

    When ``strict`` is true, any half-populated record (``mode=measured`` but
    missing baseline/tailtrail token totals) causes ``SystemExit(2)``.
    """
    records: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    saw_measured_intent = False
    half_populated: list[dict[str, Any]] = []

    for record in read_jsonl(telemetry_path):
        mode = record.get("mode")
        line_number = record.get("_line_number")
        if mode != "measured":
            ignored.append(
                {
                    "file": telemetry_path.as_posix(),
                    "line": line_number,
                    "reason": "mode is not measured",
                }
            )
            continue
        saw_measured_intent = True
        baseline_total = total_tokens(record.get("baseline"))
        tailtrail_total = total_tokens(record.get("tailtrail"))
        if baseline_total is None or tailtrail_total is None:
            reason_bits: list[str] = []
            if baseline_total is None:
                reason_bits.append("baseline token totals missing")
            if tailtrail_total is None:
                reason_bits.append("tailtrail token totals missing")
            entry = {
                "file": telemetry_path.as_posix(),
                "line": line_number,
                "reason": "; ".join(reason_bits) or "incomplete token block",
            }
            ignored.append(entry)
            half_populated.append(entry)
            continue
        saved = max(0, baseline_total - tailtrail_total)
        records.append(
            {
                "task_id": str(record.get("task_id", "unknown")),
                "provider": str(record.get("provider", "unknown")),
                "model": str(record.get("model", "unknown")),
                "baseline_tokens": baseline_total,
                "tailtrail_tokens": tailtrail_total,
                "saved_tokens": saved,
                "reduction_percent": percent(saved, baseline_total),
                "source": str(record.get("source", "usage_metadata")),
                "line": line_number,
            }
        )

    if strict and half_populated:
        rendered = "; ".join(
            f"{entry['file']}:{entry['line']} ({entry['reason']})" for entry in half_populated
        )
        raise SystemExit(
            "strict mode: half-populated measured telemetry rejected: " + rendered
        )

    if records:
        baseline_total = sum(item["baseline_tokens"] for item in records)
        tailtrail_total = sum(item["tailtrail_tokens"] for item in records)
        saved_total = max(0, baseline_total - tailtrail_total)
        return TokenEvidence(
            label="measured",
            reason=f"{len(records)} complete measured record(s) supplied",
            records=records,
            ignored=ignored,
            baseline_tokens=baseline_total,
            tailtrail_tokens=tailtrail_total,
            saved_tokens=saved_total,
            reduction_percent=percent(saved_total, baseline_total),
            estimate_details=None,
        )

    # No measured records survived. Build an explicit estimate from artifact size.
    baseline_chars = approx_char_count(baseline_text)
    tailtrail_chars = approx_char_count(tailtrail_text)
    saved_chars = max(0, baseline_chars - tailtrail_chars)
    if telemetry_path.is_file():
        if saw_measured_intent:
            reason = (
                "telemetry file present but no complete measured record survived "
                "validation; using local character-count approximation instead"
            )
        else:
            reason = (
                "telemetry file present but no records advertise mode=measured; "
                "using local character-count approximation instead"
            )
    else:
        reason = (
            "no measured token telemetry supplied; using local character-count "
            "approximation of committed artifacts"
        )
    return TokenEvidence(
        label="estimate",
        reason=reason,
        records=[],
        ignored=ignored,
        baseline_tokens=0,
        tailtrail_tokens=0,
        saved_tokens=0,
        reduction_percent=0.0,
        estimate_details={
            "approximation": "character_count",
            "baseline_chars": baseline_chars,
            "tailtrail_chars": tailtrail_chars,
            "saved_chars": saved_chars,
            "reduction_percent_chars": percent(saved_chars, baseline_chars),
            "note": (
                "Character counts are a local approximation of artifact size; "
                "they are NOT tokens and MUST NOT be reported as measured "
                "savings."
            ),
        },
    )


# ---------------------------------------------------------------------------
# scenarios and payload assembly
# ---------------------------------------------------------------------------


def scenario_dirs(root: Path, selected: str | None) -> list[Path]:
    if not root.is_dir():
        raise SystemExit(f"Efficacy scenarios root does not exist: {root}")
    if selected:
        path = root / selected
        if not path.is_dir():
            raise SystemExit(f"Unknown efficacy scenario: {selected}")
        return [path]
    return sorted(path for path in root.iterdir() if path.is_dir())


def scenario_class(expected: dict[str, Any], path: Path) -> str:
    value = expected.get("scenario_class") or expected.get("task_type") or path.name
    return str(value).strip() or path.name


def score_scenario(path: Path, *, strict: bool) -> dict[str, Any]:
    expected = read_json(path / "expected.json")
    baseline_text = read_text(path / "baseline-artifact.md")
    tailtrail_text = read_text(path / "tailtrail-artifact.md")

    checks = [score_check(item, baseline_text, tailtrail_text) for item in expected.get("checks", [])]
    max_score = sum(item["points"] for item in checks)
    score = sum(item["earned"] for item in checks)

    token_evidence = evaluate_token_evidence(
        path / "token-usage.jsonl",
        baseline_text,
        tailtrail_text,
        strict=strict,
    )

    return {
        "name": path.name,
        "title": str(expected.get("title", path.name)),
        "description": str(expected.get("description", "")),
        "scenario_class": scenario_class(expected, path),
        "artifact_evidence": {
            "kind": "deterministic_pattern_check",
            "score": score,
            "max_score": max_score,
            "score_percent": round((score / max_score) * 100, 2) if max_score else 0.0,
            "baseline_changed_lines": changed_line_count(baseline_text),
            "tailtrail_changed_lines": changed_line_count(tailtrail_text),
            "checks": checks,
        },
        "token_evidence": {
            "label": token_evidence.label,
            "reason": token_evidence.reason,
            "records": token_evidence.records,
            "ignored": token_evidence.ignored,
            "baseline_tokens": token_evidence.baseline_tokens,
            "tailtrail_tokens": token_evidence.tailtrail_tokens,
            "saved_tokens": token_evidence.saved_tokens,
            "reduction_percent": token_evidence.reduction_percent,
            "estimate_details": token_evidence.estimate_details,
        },
    }


def overall_label(scenarios: list[dict[str, Any]]) -> tuple[str, str]:
    if not scenarios:
        return "estimate", "no scenarios scored"
    labels = {scenario["token_evidence"]["label"] for scenario in scenarios}
    if labels == {"measured"}:
        return "measured", "every scored scenario has complete measured telemetry"
    if labels == {"estimate"}:
        return "estimate", "no scored scenario has measured telemetry"
    return "mixed", (
        "some scenarios have measured telemetry and others do not; "
        "measured claims apply only to the measured records listed per scenario"
    )


TARGET_PORTFOLIO_CLASSES = {
    "bug-fix",
    "review",
    "security",
    "ci-sonar",
    "dependency",
    "feature",
    "token-heavy",
    "learning-governance",
}


def portfolio_summary(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    class_counts: dict[str, int] = {}
    label_counts: dict[str, int] = {}
    for scenario in scenarios:
        scenario_class_name = str(scenario.get("scenario_class", "unknown"))
        class_counts[scenario_class_name] = class_counts.get(scenario_class_name, 0) + 1
        label = str(scenario["token_evidence"]["label"])
        label_counts[label] = label_counts.get(label, 0) + 1
    covered = set(class_counts)
    missing = sorted(TARGET_PORTFOLIO_CLASSES - covered)
    measured_or_local = label_counts.get("measured", 0) + label_counts.get("local-evidence", 0)
    ready = len(scenarios) >= 8 and not missing and measured_or_local >= 5
    return {
        "target_classes": sorted(TARGET_PORTFOLIO_CLASSES),
        "scenario_classes": class_counts,
        "token_evidence_labels": label_counts,
        "missing_classes": missing,
        "scenario_count_target": 8,
        "measured_or_local_target": 5,
        "measured_or_local_count": measured_or_local,
        "public_claim_ready": ready,
        "public_claim_reason": (
            "portfolio coverage threshold met"
            if ready
            else "public portfolio claims require at least 8 scenarios, all target classes, and at least 5 measured/local-evidence scenarios"
        ),
    }


def payload(root: Path, selected: str | None, *, strict: bool, token_harness_ledger: Path | None = None, portfolio: bool = False) -> dict[str, Any]:
    paths = scenario_dirs(root, selected)
    scenarios = [score_scenario(path, strict=strict) for path in paths]

    total_score = sum(item["artifact_evidence"]["score"] for item in scenarios)
    total_max = sum(item["artifact_evidence"]["max_score"] for item in scenarios)

    measured_records = sum(len(item["token_evidence"]["records"]) for item in scenarios)
    ignored_records = sum(len(item["token_evidence"]["ignored"]) for item in scenarios)
    measured_baseline = sum(item["token_evidence"]["baseline_tokens"] for item in scenarios)
    measured_tailtrail = sum(item["token_evidence"]["tailtrail_tokens"] for item in scenarios)
    measured_saved = max(0, measured_baseline - measured_tailtrail)

    label, label_reason = overall_label(scenarios)
    ledger_evidence = token_harness_ledger_evidence(token_harness_ledger)
    benchmark_measured = (
        label == "measured"
        and total_max > 0
        and total_score == total_max
        and measured_records > 0
        and ledger_evidence["quality_failed"] == 0
    )

    return {
        "type": "tailtrail-efficacy-run",
        "schema_version": "1",
        "generated_at": now_iso(),
        "scenarios_root": root.as_posix(),
        "strict": strict,
        "portfolio_mode": portfolio or selected is None,
        "scenario_count": len(scenarios),
        "portfolio": portfolio_summary(scenarios),
        "artifact_evidence": {
            "kind": "deterministic_pattern_check",
            "score": total_score,
            "max_score": total_max,
            "score_percent": round((total_score / total_max) * 100, 2) if total_max else 0.0,
        },
        "token_evidence": {
            "overall_label": label,
            "overall_reason": label_reason,
            "measured_records": measured_records,
            "ignored_records": ignored_records,
            "measured_baseline_tokens": measured_baseline,
            "measured_tailtrail_tokens": measured_tailtrail,
            "measured_saved_tokens": measured_saved,
            "measured_reduction_percent": percent(measured_saved, measured_baseline),
        },
        "token_harness_ledger_evidence": ledger_evidence,
        "final_evidence_label": "benchmark-measured" if benchmark_measured else label,
        "final_evidence_reason": (
            "benchmark artifact checks passed and measured telemetry is complete; Token Harness ledger has no quality failure"
            if benchmark_measured
            else "benchmark-measured requires passing artifact checks, measured telemetry, and no quality failure in Token Harness ledger"
        ),
        "scenarios": scenarios,
        "claim_guardrails": [
            "This runner consumes committed artifacts only; it does not call live models.",
            "Artifact evidence is deterministic pattern checking, not a universal model claim.",
            "Token evidence is labeled `measured` only when complete baseline + TailTrail token blocks are supplied.",
            "Estimated numbers derived from artifact character counts MUST NOT be presented as measured savings.",
            "Half-populated measured telemetry records are ignored by default and rejected with a non-zero exit under --strict.",
            "Token Harness ledger evidence is local evidence unless paired with complete measured telemetry and passing benchmark checks.",
        ],
    }


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------


def render_markdown(data: dict[str, Any]) -> str:
    artifact = data["artifact_evidence"]
    token = data["token_evidence"]
    ledger = data.get("token_harness_ledger_evidence", {})
    portfolio = data.get("portfolio", {})
    lines = [
        "# TailTrail Measured Efficacy Run",
        "",
        "- Evidence source: committed artifacts + optional paired telemetry",
        "- Live model calls: `none`",
        f"- Scenarios: `{data['scenario_count']}`",
        f"- Strict mode: `{'on' if data['strict'] else 'off'}`",
        f"- Final evidence label: `{data.get('final_evidence_label', token['overall_label'])}`",
        f"- Final evidence reason: {data.get('final_evidence_reason', token['overall_reason'])}",
        "",
        "## Artifact Evidence (Deterministic)",
        "",
        f"- Score: `{artifact['score']} / {artifact['max_score']}`",
        f"- Score percent: `{artifact['score_percent']}%`",
        "",
        "## Portfolio Coverage",
        "",
        f"- Portfolio mode: `{str(data.get('portfolio_mode', False)).lower()}`",
        f"- Public claim ready: `{str(portfolio.get('public_claim_ready', False)).lower()}`",
        f"- Reason: {portfolio.get('public_claim_reason', '')}",
        f"- Scenario classes: `{portfolio.get('scenario_classes', {})}`",
        f"- Token evidence labels: `{portfolio.get('token_evidence_labels', {})}`",
        f"- Missing target classes: `{portfolio.get('missing_classes', [])}`",
        "",
        "## Token Evidence",
        "",
        f"- Overall label: `{token['overall_label']}`",
        f"- Reason: {token['overall_reason']}",
        f"- Measured records: `{token['measured_records']}`",
        f"- Ignored records: `{token['ignored_records']}`",
        f"- Measured baseline tokens: `{token['measured_baseline_tokens']}`",
        f"- Measured TailTrail tokens: `{token['measured_tailtrail_tokens']}`",
        f"- Measured saved tokens: `{token['measured_saved_tokens']}`",
        f"- Measured reduction: `{token['measured_reduction_percent']}%`",
        "",
        "## Token Harness Ledger Evidence",
        "",
        f"- Provided: `{str(ledger.get('provided', False)).lower()}`",
        f"- Path: `{ledger.get('path', '')}`",
        f"- Events: `{ledger.get('events', 0)}`",
        f"- Event types: `{ledger.get('event_types', {})}`",
        f"- Local before: `{ledger.get('tokens_before', 0)}`",
        f"- Local after: `{ledger.get('tokens_after', 0)}`",
        f"- Local estimated saved: `{ledger.get('tokens_saved', 0)}`",
        f"- Quality failed: `{ledger.get('quality_failed', 0)}`",
        "",
        "## Scenarios",
        "",
    ]

    for scenario in data["scenarios"]:
        art = scenario["artifact_evidence"]
        tok = scenario["token_evidence"]
        lines.extend(
            [
                f"### {scenario['title']}",
                "",
                f"- Scenario: `{scenario['name']}`",
                f"- Scenario class: `{scenario.get('scenario_class', 'unknown')}`",
                f"- Artifact score: `{art['score']} / {art['max_score']}` "
                f"({art['score_percent']}%)",
                f"- Baseline changed lines: `{art['baseline_changed_lines']}`",
                f"- TailTrail changed lines: `{art['tailtrail_changed_lines']}`",
                f"- Token evidence label: `{tok['label']}`",
                f"- Token evidence reason: {tok['reason']}",
                "",
            ]
        )
        if tok["records"]:
            lines.extend(
                [
                    "| Task | Provider | Model | Baseline | TailTrail | Saved | Reduction |",
                    "|---|---|---|---:|---:|---:|---:|",
                ]
            )
            for record in tok["records"]:
                lines.append(
                    f"| {record['task_id']} | {record['provider']} | "
                    f"{record['model']} | {record['baseline_tokens']} | "
                    f"{record['tailtrail_tokens']} | {record['saved_tokens']} | "
                    f"{record['reduction_percent']}% |"
                )
            lines.append("")
        elif tok["estimate_details"]:
            details = tok["estimate_details"]
            lines.extend(
                [
                    "Estimate details (NOT tokens; local character approximation):",
                    "",
                    f"- Baseline chars: `{details['baseline_chars']}`",
                    f"- TailTrail chars: `{details['tailtrail_chars']}`",
                    f"- Saved chars: `{details['saved_chars']}`",
                    f"- Approximate reduction: `{details['reduction_percent_chars']}%`",
                    f"- Note: {details['note']}",
                    "",
                ]
            )
        if tok["ignored"]:
            lines.append("Ignored telemetry rows:")
            lines.append("")
            for entry in tok["ignored"]:
                lines.append(
                    f"- `{entry['file']}` line {entry['line']}: {entry['reason']}"
                )
            lines.append("")

        lines.append("| Check | Signal | Earned | TailTrail | Baseline |")
        lines.append("|---|---|---:|---|---|")
        for check in art["checks"]:
            tailtrail = "pass" if check["tailtrail_passed"] else "miss"
            baseline_passed = check["baseline_passed"]
            baseline = (
                "not scored"
                if baseline_passed is None
                else ("pass" if baseline_passed else "miss")
            )
            lines.append(
                f"| {check['name']} | {check['signal']} | "
                f"{check['earned']} / {check['points']} | {tailtrail} | {baseline} |"
            )
        lines.append("")

    lines.extend(["## Claim Guardrails", ""])
    lines.extend(f"- {item}" for item in data["claim_guardrails"])
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run TailTrail measured-efficacy benchmarks (BL-1). Produces a report "
            "that labels token evidence as measured or estimate."
        ),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_SCENARIOS,
        help="Efficacy scenarios root (default: benchmarks/efficacy).",
    )
    parser.add_argument("--scenario", help="Run one efficacy scenario by folder name.")
    parser.add_argument(
        "--portfolio",
        action="store_true",
        help="Run the committed measured evidence portfolio and report scenario-class coverage.",
    )
    parser.add_argument(
        "--format", choices=("markdown", "json"), default="markdown", help="Output format."
    )
    parser.add_argument(
        "--write-result",
        type=Path,
        nargs="?",
        const=DEFAULT_RESULT,
        help="Optionally write the report to a file.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Fail with a non-zero exit code when telemetry records advertise "
            "mode=measured but have missing baseline or TailTrail token totals."
        ),
    )
    parser.add_argument(
        "--token-harness-ledger",
        type=Path,
        help="Optional Token Harness ledger JSONL to include as local proof evidence.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.portfolio and args.scenario:
        raise SystemExit("--portfolio cannot be combined with --scenario")
    data = payload(
        args.root.resolve(),
        args.scenario,
        strict=args.strict,
        token_harness_ledger=args.token_harness_ledger,
        portfolio=args.portfolio,
    )
    body = (
        json.dumps(data, indent=2, sort_keys=True)
        if args.format == "json"
        else render_markdown(data)
    )
    print(body)
    if args.write_result:
        args.write_result.parent.mkdir(parents=True, exist_ok=True)
        args.write_result.write_text(
            body + ("\n" if not body.endswith("\n") else ""),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
