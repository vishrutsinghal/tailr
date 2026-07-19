#!/usr/bin/env python3
"""Evaluation Harness command router and event normalizer.

EH-2 aliases intentionally delegate to existing TailTrail evidence scripts.
EH-3 adds a small local event normalizer; it does not score scenarios, call
models, upload metadata, or store raw prompts/source/logs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
PYTHON = sys.executable
EVENTS_PATH = Path(".tailtrail/evaluation/events.jsonl")
EVALUATION_ROOT = ROOT / "benchmarks" / "evaluation"
SCENARIOS_ROOT = EVALUATION_ROOT / "scenarios"
SCENARIO_RESULTS_ROOT = EVALUATION_ROOT / "results"
SOURCES = {
    "manual",
    "outcome",
    "quality-loop",
    "meta",
    "token-proof",
    "efficacy",
    "benchmark",
}
REQUIRED_FIELDS = {"schema_version", "event_id", "created_at", "source_feature", "task_class", "scores", "claim_boundaries"}
RAW_FIELD_MARKERS = (
    "raw_prompt",
    "prompt_raw",
    "source_code",
    "raw_source",
    "raw_log",
    "raw_ci",
    "raw_scanner",
    "secret",
    "password",
)


def run_script(name: str, args: list[str]) -> int:
    command = [PYTHON, (SCRIPTS / name).as_posix(), *args]
    return subprocess.run(command, cwd=Path.cwd(), check=False).returncode


def usage() -> int:
    print("Usage: tailtrail eval audit|normalize|validate-events|portfolio|guardrails|outcome|workflow|meta|tokens|report|artifact|scenario [args]")
    print("")
    print("Implemented in EH-2 aliases:")
    print("- eval audit")
    print("- eval portfolio run|report")
    print("- eval guardrails precision")
    print("- eval outcome capture|summarize")
    print("- eval workflow capture|summarize|review|propose|decide")
    print("- eval meta quick|review|readiness|analyze|propose|proposal-status|proposal-record")
    print("- eval tokens route|reduce|receipt|ledger|proof|telemetry|savings|budget|bridge")
    print("- eval report enterprise|value|compare|trend|aggregate|pr")
    print("- eval artifact analyze|benchmark")
    print("")
    print("Implemented in EH-3 events:")
    print("- eval scenario list|run|compare|report")
    print("- eval normalize --source <kind> --input <path>")
    print("- eval validate-events [path]")
    print("")
    print("Pending:")
    print("- eval portfolio compare: later portfolio consolidation")
    print("- eval guardrails report: later guardrail report consolidation")
    print("- eval outcome export: later outcome export consolidation")
    return 2


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Unable to read {path.as_posix()}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path.as_posix()}: {exc}") from exc


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_event_id(source: str, task_class: str, payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(f"{source}:{task_class}:{body}".encode("utf-8")).hexdigest()[:12]
    return f"eval-{source}-{digest}"


def contains_raw_field(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in RAW_FIELD_MARKERS):
                return str(key)
            found = contains_raw_field(nested)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = contains_raw_field(item)
            if found:
                return found
    return None


def event_errors(event: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(event))
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")
    if event.get("schema_version") != "1":
        errors.append("schema_version must be `1`")
    for field in ("event_id", "created_at", "source_feature", "task_class"):
        if field in event and not isinstance(event[field], str):
            errors.append(f"{field} must be a string")
    if "scores" in event and not isinstance(event["scores"], dict):
        errors.append("scores must be an object")
    if "claim_boundaries" in event and not isinstance(event["claim_boundaries"], list):
        errors.append("claim_boundaries must be an array")
    elif "claim_boundaries" in event and not all(isinstance(item, str) for item in event["claim_boundaries"]):
        errors.append("claim_boundaries must contain strings only")
    raw_field = contains_raw_field(event)
    if raw_field:
        errors.append(f"raw or sensitive field is not allowed: {raw_field}")
    return errors


def ensure_valid_event(event: dict[str, Any]) -> None:
    errors = event_errors(event)
    if errors:
        raise SystemExit("Invalid evaluation event: " + "; ".join(errors))


def compact_source_summary(source: str, payload: dict[str, Any]) -> str:
    if isinstance(payload.get("summary"), str):
        return payload["summary"][:500]
    if isinstance(payload.get("title"), str):
        return payload["title"][:500]
    status = payload.get("status")
    if isinstance(status, str):
        return f"{source} event with status `{status}`."
    return f"Normalized {source} evidence event."


def normalize_event(source: str, payload: dict[str, Any], task_class: str, root: Path | None, source_path: Path | None) -> dict[str, Any]:
    if contains_raw_field(payload):
        raise SystemExit("Refusing to normalize input with raw prompt/source/log/secret-like fields.")
    if source == "manual" and REQUIRED_FIELDS <= set(payload):
        event = dict(payload)
        ensure_valid_event(event)
        return event

    evidence_label = payload.get("evidence_label")
    if not isinstance(evidence_label, str):
        evidence_label = "local-evidence"
    scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    claim_boundaries = payload.get("claim_boundaries") if isinstance(payload.get("claim_boundaries"), list) else []
    claim_boundary_strings = [item for item in claim_boundaries if isinstance(item, str)]
    if not claim_boundary_strings:
        claim_boundary_strings = [
            "Evaluation events store compact summaries and references only.",
            "Exact token savings require measured telemetry.",
        ]
    event: dict[str, Any] = {
        "schema_version": "1",
        "event_id": stable_event_id(source, task_class, payload),
        "created_at": utc_now(),
        "source_feature": source,
        "task_class": task_class,
        "evidence_label": evidence_label,
        "scores": scores,
        "claim_boundaries": claim_boundary_strings,
        "summary": compact_source_summary(source, payload),
    }
    if metrics:
        event["metrics"] = metrics
    if root:
        event["root"] = root.as_posix()
    if source_path:
        event["source_path"] = source_path.as_posix()
    for field in ("scenario_id", "variant", "month", "tags", "recommendations"):
        if field in payload and isinstance(payload[field], (str, list)):
            event[field] = payload[field]
    ensure_valid_event(event)
    return event


def write_event(root: Path, event: dict[str, Any]) -> Path:
    destination = root / EVENTS_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return destination


def normalize(args: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Normalize compact evidence into a TailTrail Evaluation Harness event.")
    parser.add_argument("--source", choices=sorted(SOURCES), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--task-class", default="unknown")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--write-event", action="store_true")
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parsed = parser.parse_args(args)

    payload = read_json(parsed.input)
    if not isinstance(payload, dict):
        raise SystemExit("Evaluation input must be a JSON object.")
    event = normalize_event(parsed.source, payload, parsed.task_class, parsed.root.resolve(), parsed.input)
    written: Path | None = None
    if parsed.write_event:
        if not parsed.approved and not parsed.dry_run:
            raise SystemExit("--write-event requires --approved.")
        if not parsed.dry_run:
            written = write_event(parsed.root.resolve(), event)

    if parsed.format == "json":
        print(json.dumps(event, indent=2, sort_keys=True))
    else:
        print("# TailTrail Evaluation Event")
        print("")
        print(f"- Event: `{event['event_id']}`")
        print(f"- Source: `{event['source_feature']}`")
        print(f"- Task class: `{event['task_class']}`")
        print(f"- Evidence label: `{event.get('evidence_label', 'local-evidence')}`")
        print(f"- Summary: {event.get('summary', '')}")
        if written:
            print(f"- Written: `{written.as_posix()}`")
        elif parsed.write_event and parsed.dry_run:
            print("- Written: no, dry run")
        print("")
        print("## Claim Boundaries")
        for boundary in event["claim_boundaries"]:
            print(f"- {boundary}")
    return 0


def validate_events(args: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate TailTrail Evaluation Harness event JSONL.")
    parser.add_argument("path", nargs="?", type=Path, default=EVENTS_PATH)
    parsed = parser.parse_args(args)
    path = parsed.path
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        print(f"No evaluation event file found: {path.as_posix()}")
        return 1
    errors: list[str] = []
    count = 0
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            count += 1
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_number}: invalid JSON: {exc}")
                continue
            if not isinstance(event, dict):
                errors.append(f"line {line_number}: event must be an object")
                continue
            for error in event_errors(event):
                errors.append(f"line {line_number}: {error}")
    if errors:
        print("# TailTrail Evaluation Event Validation")
        print("")
        print("- Status: `failed`")
        print(f"- Events checked: `{count}`")
        print("")
        print("## Issues")
        for error in errors:
            print(f"- {error}")
        return 1
    print("# TailTrail Evaluation Event Validation")
    print("")
    print("- Status: `passed`")
    print(f"- Events checked: `{count}`")
    return 0


def pending(route: str, phase: str, current: str | None = None) -> int:
    print(f"`tailtrail eval {route}` is planned for {phase}.")
    print("No evaluation was run.")
    if current:
        print(f"Use `{current}` today, or run `tailtrail eval audit` to review the alias map.")
    else:
        print("Run `tailtrail eval audit` to review the alias map.")
    return 2


def scenario_dir(scenario_id: str) -> Path:
    path = SCENARIOS_ROOT / scenario_id
    if not path.is_dir():
        raise SystemExit(f"Unknown evaluation scenario: {scenario_id}")
    return path


def scenario_paths() -> list[Path]:
    if not SCENARIOS_ROOT.is_dir():
        return []
    return sorted(path for path in SCENARIOS_ROOT.iterdir() if path.is_dir() and (path / "scenario.json").is_file())


def read_scenario(path: Path) -> dict[str, Any]:
    data = read_json(path / "scenario.json")
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid scenario file: {(path / 'scenario.json').as_posix()}")
    return data


def text_contains(text: str, needle: str) -> bool:
    return needle.lower() in text.lower()


def score_dimension(text: str, dimension: dict[str, Any]) -> dict[str, Any]:
    must_include = [str(item) for item in dimension.get("must_include", [])]
    must_include_any = [str(item) for item in dimension.get("must_include_any", [])]
    must_not_include = [str(item) for item in dimension.get("must_not_include", [])]
    evidence: list[str] = []
    misses: list[str] = []
    forbidden = [item for item in must_not_include if text_contains(text, item)]
    if forbidden:
        return {
            "score": 0.0,
            "weight": float(dimension.get("weight", 1)),
            "weighted_score": 0.0,
            "evidence": evidence,
            "misses": [f"forbidden signal found: {item}" for item in forbidden],
            "label": "heuristic",
        }

    required_total = len(must_include) + (1 if must_include_any else 0)
    matched = 0
    for item in must_include:
        if text_contains(text, item):
            evidence.append(item)
            matched += 1
        else:
            misses.append(item)
    if must_include_any:
        any_match = next((item for item in must_include_any if text_contains(text, item)), None)
        if any_match:
            evidence.append(any_match)
            matched += 1
        else:
            misses.append("one of: " + ", ".join(must_include_any))

    if required_total == 0:
        score = 1.0
    elif matched == required_total:
        score = 1.0
    elif matched > 0:
        score = 0.5
    else:
        score = 0.0
    weight = float(dimension.get("weight", 1))
    return {
        "score": score,
        "weight": weight,
        "weighted_score": round(score * weight, 4),
        "evidence": evidence,
        "misses": misses,
        "label": "heuristic",
    }


def score_variant(scenario_path: Path, scenario_data: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    artifact = scenario_path / str(variant.get("artifact", ""))
    if not artifact.is_file():
        raise SystemExit(f"Missing scenario artifact: {artifact.as_posix()}")
    text = artifact.read_text(encoding="utf-8")
    dimensions = scenario_data.get("dimensions", {})
    if not isinstance(dimensions, dict) or not dimensions:
        raise SystemExit(f"Scenario has no dimensions: {scenario_path.name}")
    scored_dimensions: dict[str, Any] = {}
    total_weight = 0.0
    total_weighted = 0.0
    for name, dimension in dimensions.items():
        if not isinstance(dimension, dict):
            raise SystemExit(f"Invalid dimension `{name}` in scenario `{scenario_path.name}`")
        result = score_dimension(text, dimension)
        scored_dimensions[str(name)] = result
        total_weight += float(result["weight"])
        total_weighted += float(result["weighted_score"])
    total = round(total_weighted / total_weight, 4) if total_weight else 0.0
    return {
        "id": str(variant.get("id", artifact.stem)),
        "artifact": artifact.name,
        "score": total,
        "dimensions": scored_dimensions,
    }


def scenario_result(scenario_id: str) -> dict[str, Any]:
    path = scenario_dir(scenario_id)
    scenario_data = read_scenario(path)
    variants = scenario_data.get("variants", [])
    if not isinstance(variants, list) or not variants:
        raise SystemExit(f"Scenario has no variants: {scenario_id}")
    variant_results = [score_variant(path, scenario_data, item) for item in variants if isinstance(item, dict)]
    if not variant_results:
        raise SystemExit(f"Scenario has no valid variants: {scenario_id}")
    winner = max(variant_results, key=lambda item: float(item["score"]))
    baseline = next((item for item in variant_results if item["id"] == "baseline"), variant_results[0])
    delta = round(float(winner["score"]) - float(baseline["score"]), 4)
    expected_path = path / "expected.json"
    expected = read_json(expected_path) if expected_path.is_file() else {}
    threshold_passed = True
    if isinstance(expected, dict):
        min_tailtrail_total = expected.get("min_tailtrail_total")
        required_winner = expected.get("required_winner")
        min_delta = expected.get("min_delta")
        tailtrail = next((item for item in variant_results if item["id"] == "tailtrail"), winner)
        if isinstance(min_tailtrail_total, (int, float)) and float(tailtrail["score"]) < float(min_tailtrail_total):
            threshold_passed = False
        if isinstance(required_winner, str) and winner["id"] != required_winner:
            threshold_passed = False
        if isinstance(min_delta, (int, float)) and delta < float(min_delta):
            threshold_passed = False
    result = {
        "schema_version": "1",
        "type": "evaluation-scenario-result",
        "scenario_id": scenario_id,
        "title": str(scenario_data.get("title", scenario_id)),
        "task_class": str(scenario_data.get("task_class", "unknown")),
        "evidence_label": str(scenario_data.get("evidence_label", "local-evidence")),
        "claim_boundaries": [str(item) for item in scenario_data.get("claim_boundaries", [])],
        "variants": variant_results,
        "winner": winner["id"],
        "delta_from_baseline": delta,
        "threshold_passed": threshold_passed,
        "generated_at": utc_now(),
    }
    result["event"] = normalize_event(
        "benchmark",
        {
            "summary": f"Scenario {scenario_id} scored with deterministic fixture evidence.",
            "scenario_id": scenario_id,
            "evidence_label": result["evidence_label"],
            "scores": {"winner_score": winner["score"], "delta_from_baseline": delta},
            "claim_boundaries": result["claim_boundaries"],
        },
        result["task_class"],
        ROOT,
        path / "scenario.json",
    )
    return result


def render_scenario_list(output_format: str) -> str:
    scenarios = []
    for path in scenario_paths():
        data = read_scenario(path)
        scenarios.append(
            {
                "scenario_id": path.name,
                "title": str(data.get("title", path.name)),
                "task_class": str(data.get("task_class", "unknown")),
                "evidence_label": str(data.get("evidence_label", "local-evidence")),
                "variants": [str(item.get("id", "")) for item in data.get("variants", []) if isinstance(item, dict)],
                "path": path.relative_to(ROOT).as_posix(),
            }
        )
    if output_format == "json":
        return json.dumps({"schema_version": "1", "type": "evaluation-scenario-list", "scenarios": scenarios}, indent=2, sort_keys=True)
    lines = ["# TailTrail Evaluation Scenarios", ""]
    for item in scenarios:
        lines.append(f"- `{item['scenario_id']}`: {item['title']} ({item['task_class']}, {item['evidence_label']})")
    return "\n".join(lines)


def render_score_table(result: dict[str, Any]) -> list[str]:
    dimension_names = list(result["variants"][0]["dimensions"].keys()) if result["variants"] else []
    header = ["Variant", *dimension_names, "Total"]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---", *["---:" for _ in dimension_names], "---:"]) + " |",
    ]
    for variant in result["variants"]:
        values = [variant["id"]]
        for name in dimension_names:
            values.append(str(variant["dimensions"][name]["score"]).rstrip("0").rstrip("."))
        values.append(str(variant["score"]).rstrip("0").rstrip("."))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def render_scenario_markdown(result: dict[str, Any], mode: str) -> str:
    lines = [
        "# TailTrail Evaluation Scenario Report",
        "",
        f"- Scenario: `{result['scenario_id']}`",
        f"- Task class: `{result['task_class']}`",
        f"- Variants: `{', '.join(item['id'] for item in result['variants'])}`",
        f"- Evidence label: `{result['evidence_label']}`",
        f"- Winner: `{result['winner']}`",
        f"- Delta from baseline: `{result['delta_from_baseline']:+.4f}`",
        f"- Threshold passed: `{str(result['threshold_passed']).lower()}`",
        "",
        "## Claim Boundaries",
        "",
    ]
    for boundary in result["claim_boundaries"]:
        lines.append(f"- {boundary}")
    lines.extend(["", "## Score Summary", "", *render_score_table(result), "", "## Findings", ""])
    for variant in result["variants"]:
        lines.append(f"### {variant['id']}")
        for name, dimension in variant["dimensions"].items():
            evidence = ", ".join(dimension["evidence"]) if dimension["evidence"] else "none"
            misses = ", ".join(dimension["misses"]) if dimension["misses"] else "none"
            lines.append(f"- `{name}`: score `{dimension['score']}`, evidence: {evidence}, misses: {misses}")
        lines.append("")
    if mode == "compare":
        lines.extend([
            "## Comparison",
            "",
            f"- Winning variant: `{result['winner']}`",
            f"- Delta from baseline: `{result['delta_from_baseline']:+.4f}`",
            "",
        ])
    lines.extend([
        "## Repro Commands",
        "",
        f"- `python3 scripts/tailtrail.py eval scenario run --scenario {result['scenario_id']}`",
        f"- `python3 scripts/tailtrail.py eval scenario report --scenario {result['scenario_id']} --format json`",
    ])
    return "\n".join(lines)


def write_scenario_result(result: dict[str, Any], output: str, output_format: str, explicit_path: Path | None) -> Path:
    suffix = "json" if output_format == "json" else "md"
    destination = explicit_path or (SCENARIO_RESULTS_ROOT / f"{result['scenario_id']}-scenario-report.{suffix}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(output + "\n", encoding="utf-8")
    return destination


def scenario(args: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic TailTrail Evaluation Harness scenarios.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    for command in ("run", "compare", "report"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--scenario", required=True)
        sub.add_argument("--format", choices=("markdown", "json"), default="markdown")
        sub.add_argument("--write-result", nargs="?", const="", default=None)
        sub.add_argument("--approved", action="store_true")
    parsed = parser.parse_args(args)
    if parsed.command == "list":
        print(render_scenario_list(parsed.format))
        return 0
    result = scenario_result(parsed.scenario)
    if parsed.format == "json":
        output = json.dumps(result, indent=2, sort_keys=True)
    else:
        output = render_scenario_markdown(result, parsed.command)
    if parsed.write_result is not None:
        if not parsed.approved:
            raise SystemExit("--write-result requires --approved.")
        explicit_path = Path(parsed.write_result) if parsed.write_result else None
        written = write_scenario_result(result, output, parsed.format, explicit_path)
        if parsed.format == "json":
            data = json.loads(output)
            data["written"] = written.as_posix()
            output = json.dumps(data, indent=2, sort_keys=True)
        else:
            output += f"\n\nWritten: `{written.as_posix()}`"
    print(output)
    return 0


def portfolio(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail eval portfolio run|report|compare [args]")
        return 2
    action, rest = args[0], args[1:]
    if action in {"run", "report"}:
        return run_script("efficacy-run.py", rest)
    if action == "compare":
        return pending("portfolio compare", "EH-5 Portfolio Consolidation", "tailtrail efficacy run --portfolio")
    print("Usage: tailtrail eval portfolio run|report|compare [args]")
    return 2


def guardrails(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail eval guardrails precision|report [args]")
        return 2
    action, rest = args[0], args[1:]
    if action == "precision":
        return run_script("guardrail-precision.py", rest)
    if action == "report":
        return pending("guardrails report", "EH-5 Portfolio Consolidation", "tailtrail guardrail precision")
    print("Usage: tailtrail eval guardrails precision|report [args]")
    return 2


def outcome(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail eval outcome capture|summarize|export [args]")
        return 2
    action, rest = args[0], args[1:]
    if action in {"capture", "summarize"}:
        return run_script("outcome-telemetry.py", [action, *rest])
    if action == "export":
        return pending("outcome export", "EH-5 Portfolio Consolidation", "tailtrail outcome summarize --format json")
    print("Usage: tailtrail eval outcome capture|summarize|export [args]")
    return 2


def workflow(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail eval workflow capture|summarize|review|propose|decide|recommend [args]")
        return 2
    action, rest = args[0], args[1:]
    if action in {"capture", "summarize", "review", "propose", "decide"}:
        return run_script("quality-loop.py", [action, *rest])
    if action == "recommend":
        return run_script("quality-loop.py", ["propose", *rest])
    print("Usage: tailtrail eval workflow capture|summarize|review|propose|decide|recommend [args]")
    return 2


def meta(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail eval meta quick|review|readiness|analyze|propose|proposal-status|proposal-record [args]")
        return 2
    action, rest = args[0], args[1:]
    if action in {"quick", "review"}:
        return run_script("harness-review.py", [action, *rest])
    if action == "readiness":
        return run_script("meta-harness-analyze.py", ["readiness", *rest])
    if action == "analyze":
        return run_script("meta-harness-analyze.py", ["analyze", *rest])
    if action == "propose":
        return run_script("meta-harness-propose.py", rest)
    if action == "proposal-status":
        return run_script("meta-harness-propose.py", ["status", *rest])
    if action == "proposal-record":
        return run_script("meta-harness-propose.py", ["record", *rest])
    print("Usage: tailtrail eval meta quick|review|readiness|analyze|propose|proposal-status|proposal-record [args]")
    return 2


def tokens(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail eval tokens route|reduce|receipt|ledger|proof|telemetry|savings|budget|bridge [args]")
        return 2
    action, rest = args[0], args[1:]
    if action in {"route", "reduce", "ledger", "proof", "bridge"}:
        return run_script("token-harness.py", [action, *rest])
    if action == "receipt":
        return run_script("context-receipt.py", rest)
    if action == "telemetry":
        return run_script("token-telemetry.py", rest)
    if action == "savings":
        return run_script("token-savings.py", rest)
    if action == "budget":
        return run_script("token-budget-coach.py", rest)
    print("Usage: tailtrail eval tokens route|reduce|receipt|ledger|proof|telemetry|savings|budget|bridge [args]")
    return 2


def report(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail eval report enterprise|value|compare|trend|aggregate|pr [args]")
        return 2
    return run_script("tailtrail-report.py", args)


def artifact(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail eval artifact analyze|benchmark [args]")
        return 2
    action, rest = args[0], args[1:]
    if action == "analyze":
        return run_script("analyze-benchmark.py", rest)
    if action == "benchmark":
        return run_script("benchmark-tailtrail.py", rest)
    print("Usage: tailtrail eval artifact analyze|benchmark [args]")
    return 2


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help", "help"}:
        return usage()

    action, rest = args[0], args[1:]
    if action == "audit":
        return run_script("evaluation-audit.py", rest)
    if action == "normalize":
        return normalize(rest)
    if action == "validate-events":
        return validate_events(rest)
    if action == "scenario":
        return scenario(rest)
    if action == "portfolio":
        return portfolio(rest)
    if action == "guardrails":
        return guardrails(rest)
    if action == "outcome":
        return outcome(rest)
    if action == "workflow":
        return workflow(rest)
    if action == "meta":
        return meta(rest)
    if action == "tokens":
        return tokens(rest)
    if action == "report":
        return report(rest)
    if action == "artifact":
        return artifact(rest)

    print("Usage: tailtrail eval audit|portfolio|guardrails|outcome|workflow|meta|tokens|report|artifact|scenario [args]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
