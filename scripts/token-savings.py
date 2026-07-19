#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULT = ROOT / "benchmarks" / "results" / "token-savings-latest.md"
DEFAULT_CHARS_PER_TOKEN = 4
SKIP_DIRS = {".git", ".tailtrail", "__pycache__", "node_modules", ".venv", "venv", "target", "build", "dist"}
REQUIRED_MEASURED_FIELDS = ("task_id", "provider", "model", "source", "baseline", "tailtrail")


def registry_evidence_label(feature_id: str) -> str:
    path = ROOT / "scripts" / "tailtrail-registry.py"
    spec = importlib.util.spec_from_file_location("tailtrail_registry_for_token_savings", path)
    if spec is None or spec.loader is None:
        return "none"
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return module.evidence_label_for(module.load_registry(), feature_id)
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return "none"


@dataclass(frozen=True)
class PathStats:
    path: str
    files: int
    chars: int
    approx_tokens: int
    skipped: int


def estimate_tokens(chars: int, chars_per_token: int) -> int:
    if chars <= 0:
        return 0
    return math.ceil(chars / chars_per_token)


def iter_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    files: list[Path] = []
    for child in sorted(path.rglob("*")):
        if any(part in SKIP_DIRS for part in child.parts):
            continue
        if child.is_file():
            files.append(child)
    return files


def read_text_size(path: Path) -> tuple[int, bool]:
    try:
        return len(path.read_text(encoding="utf-8")), False
    except UnicodeDecodeError:
        return 0, True
    except OSError:
        return 0, True


def collect(paths: list[str], chars_per_token: int) -> list[PathStats]:
    stats: list[PathStats] = []
    for item in paths:
        path = Path(item)
        if not path.is_absolute():
            path = Path.cwd() / path
        chars = 0
        files = 0
        skipped = 0
        for file_path in iter_files(path):
            file_chars, was_skipped = read_text_size(file_path)
            if was_skipped:
                skipped += 1
                continue
            chars += file_chars
            files += 1
        stats.append(
            PathStats(
                path=Path(item).as_posix(),
                files=files,
                chars=chars,
                approx_tokens=estimate_tokens(chars, chars_per_token),
                skipped=skipped,
            )
        )
    return stats


def sum_tokens(stats: list[PathStats]) -> int:
    return sum(item.approx_tokens for item in stats)


def percent(saved: int, baseline: int) -> float:
    if baseline <= 0:
        return 0.0
    return round((saved / baseline) * 100, 2)


def estimate_report(args: argparse.Namespace) -> dict[str, Any]:
    used = collect(args.used, args.chars_per_token)
    avoided = collect(args.avoided, args.chars_per_token)
    used_tokens = sum_tokens(used)
    avoided_tokens = sum_tokens(avoided)
    baseline_tokens = used_tokens + avoided_tokens
    saved_tokens = avoided_tokens
    return {
        "mode": "estimated",
        "evidence_level": "local_approximation",
        "registry_evidence_label": registry_evidence_label("token-harness"),
        "created_at": now(),
        "chars_per_token": args.chars_per_token,
        "used": [item.__dict__ for item in used],
        "avoided": [item.__dict__ for item in avoided],
        "tailtrail_tokens": used_tokens,
        "baseline_tokens": baseline_tokens,
        "saved_tokens": saved_tokens,
        "reduction_percent": percent(saved_tokens, baseline_tokens),
        "claim_guardrail": "Estimated only. Do not present this as exact model/API token savings.",
    }


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.is_file():
        raise SystemExit(f"Telemetry file not found: {path}")
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise SystemExit(f"Invalid telemetry JSON on line {line_number}: {error}") from error
        if isinstance(value, dict):
            value["_line_number"] = line_number
            records.append(value)
        else:
            raise SystemExit(f"Invalid telemetry record on line {line_number}: expected a JSON object")
    return records


def read_json_or_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise SystemExit(f"Telemetry source not found: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            value = json.loads(text)
        except json.JSONDecodeError as error:
            raise SystemExit(f"Invalid telemetry JSON array: {error}") from error
        if not isinstance(value, list):
            raise SystemExit("Telemetry JSON must be an array of objects or JSONL.")
        rows = []
        for index, item in enumerate(value, start=1):
            if not isinstance(item, dict):
                raise SystemExit(f"Invalid telemetry record {index}: expected object")
            item["_line_number"] = index
            rows.append(item)
        return rows
    return read_jsonl(path)


def total_tokens(block: Any) -> int | None:
    if not isinstance(block, dict):
        return None
    value = block.get("total_tokens")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    input_tokens = block.get("input_tokens")
    output_tokens = block.get("output_tokens")
    if isinstance(input_tokens, int) and isinstance(output_tokens, int):
        return input_tokens + output_tokens
    return None


def missing_measured_fields(record: dict[str, Any]) -> list[str]:
    missing = [field for field in REQUIRED_MEASURED_FIELDS if field not in record]
    baseline = record.get("baseline")
    tailtrail = record.get("tailtrail")
    if not isinstance(baseline, dict):
        missing.append("baseline object")
    elif total_tokens(baseline) is None:
        missing.append("baseline.total_tokens or baseline input/output tokens")
    if not isinstance(tailtrail, dict):
        missing.append("tailtrail object")
    elif total_tokens(tailtrail) is None:
        missing.append("tailtrail.total_tokens or tailtrail input/output tokens")
    return missing


def report_from_telemetry(args: argparse.Namespace) -> dict[str, Any]:
    telemetry_path = Path(args.telemetry)
    records = read_jsonl(telemetry_path)
    measured: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    for record in records:
        if record.get("mode") != "measured":
            ignored.append({"line": record.get("_line_number"), "reason": "mode is not measured"})
            continue
        missing = missing_measured_fields(record)
        if missing:
            ignored.append({"line": record.get("_line_number"), "task_id": str(record.get("task_id", "unknown")), "reason": f"missing {', '.join(missing)}"})
            continue
        baseline = total_tokens(record.get("baseline"))
        tailtrail = total_tokens(record.get("tailtrail"))
        assert baseline is not None
        assert tailtrail is not None
        saved = max(0, baseline - tailtrail)
        measured.append(
            {
                "task_id": str(record.get("task_id", "unknown")),
                "provider": str(record.get("provider", "unknown")),
                "model": str(record.get("model", "unknown")),
                "timestamp": str(record.get("timestamp", "unknown")),
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
        "mode": "measured" if measured else "unknown",
        "evidence_level": "api_usage_metadata" if measured else "missing_measured_telemetry",
        "registry_evidence_label": registry_evidence_label("token-harness"),
        "created_at": now(),
        "telemetry": telemetry_path.as_posix(),
        "records_read": len(records),
        "measured_records": len(measured),
        "ignored_records": len(ignored),
        "ignored": ignored,
        "records": measured,
        "baseline_tokens": baseline_total,
        "tailtrail_tokens": tailtrail_total,
        "saved_tokens": saved_total,
        "reduction_percent": percent(saved_total, baseline_total),
        "claim_guardrail": (
            "Measured token reduction can be claimed only for the records above, using the listed provider/model usage metadata."
            if measured
            else "Exact token savings are unavailable because no usable measured model/API telemetry was provided. Add JSONL records with mode, task_id, provider, model, source, baseline tokens, and TailTrail tokens."
        ),
    }


def normalize_measured_record(record: dict[str, Any]) -> dict[str, Any] | None:
    if record.get("mode") == "measured" and not missing_measured_fields(record):
        return {key: value for key, value in record.items() if not key.startswith("_")}

    baseline = record.get("baseline")
    tailtrail = record.get("tailtrail")
    if not isinstance(baseline, dict) or not isinstance(tailtrail, dict):
        return None
    normalized = {
        "mode": "measured",
        "task_id": str(record.get("task_id") or record.get("id") or f"task-{record.get('_line_number', 'unknown')}"),
        "provider": str(record.get("provider", "unknown")),
        "model": str(record.get("model", "unknown")),
        "source": str(record.get("source", "usage_metadata")),
        "timestamp": str(record.get("timestamp", now())),
        "baseline": baseline,
        "tailtrail": tailtrail,
    }
    return None if missing_measured_fields(normalized) else normalized


def import_telemetry(args: argparse.Namespace) -> dict[str, Any]:
    source = Path(args.source)
    output_path = Path(args.output)
    rows = read_json_or_jsonl(source)
    imported = []
    ignored = []
    for row in rows:
        normalized = normalize_measured_record(row)
        if normalized is None:
            ignored.append({"line": row.get("_line_number"), "reason": "not a usable measured telemetry record"})
            continue
        imported.append(normalized)
    if imported and not args.dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if args.append else "w"
        with output_path.open(mode, encoding="utf-8") as handle:
            for row in imported:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    return {
        "mode": "import",
        "evidence_level": "api_usage_metadata_import" if imported else "missing_measured_telemetry",
        "created_at": now(),
        "source": source.as_posix(),
        "output": output_path.as_posix(),
        "records_read": len(rows),
        "imported_records": len(imported),
        "ignored_records": len(ignored),
        "dry_run": args.dry_run,
        "ignored": ignored,
        "claim_guardrail": "Import normalizes measured usage records only. Exact savings can be claimed only after running `savings report` on imported records.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    mode = str(report["mode"])
    if mode == "import":
        lines = [
            "# TailTrail Token Telemetry Import",
            "",
            f"- Evidence level: `{report['evidence_level']}`",
            f"- Source: `{report['source']}`",
            f"- Output: `{report['output']}`",
            f"- Records read: `{report['records_read']}`",
            f"- Imported records: `{report['imported_records']}`",
            f"- Ignored records: `{report['ignored_records']}`",
            f"- Dry run: `{report['dry_run']}`",
            f"- Claim guardrail: {report['claim_guardrail']}",
        ]
        if report.get("ignored"):
            lines.extend(["", "## Ignored Records"])
            lines.extend(f"- line `{item.get('line')}`: {item.get('reason')}" for item in report["ignored"])
        return "\n".join(lines)
    title = "TailTrail Token Savings Report"
    lines = [
        f"# {title}",
        "",
        f"- Mode: `{mode}`",
        f"- Evidence level: `{report['evidence_level']}`",
        f"- Created at: `{report['created_at']}`",
        f"- Baseline tokens: `{report['baseline_tokens']}`",
        f"- TailTrail tokens: `{report['tailtrail_tokens']}`",
        f"- Saved tokens: `{report['saved_tokens']}`",
        f"- Reduction: `{report['reduction_percent']}%`",
        f"- Claim guardrail: {report['claim_guardrail']}",
        "",
    ]

    if mode == "estimated":
        lines.extend(
            [
                "## Estimate Inputs",
                "",
                f"- Approximation: `ceil(characters / {report['chars_per_token']})`",
                "- This is useful for planning and demos, not billing or exact provider usage.",
                "",
                "### Used Context",
                "",
            ]
        )
        lines.extend(render_path_table(report.get("used", [])))
        lines.extend(["", "### Avoided Context", ""])
        lines.extend(render_path_table(report.get("avoided", [])))
    elif mode == "measured":
        lines.extend(
            [
                "## Measured Records",
                "",
                "| Task | Provider | Model | Before TailTrail | With TailTrail | Difference | Reduction |",
                "|---|---|---|---:|---:|---:|---:|",
            ]
        )
        for record in report.get("records", []):
            lines.append(
                "| {task_id} | {provider} | {model} | {baseline_tokens} | {tailtrail_tokens} | {saved_tokens} | {reduction_percent}% |".format(
                    **record
                )
            )
        lines.extend(["", f"- Ignored records: `{report['ignored_records']}`"])
        if report.get("ignored"):
            lines.extend(["", "## Ignored Records", ""])
            for item in report["ignored"]:
                lines.append(f"- line `{item.get('line')}` task `{item.get('task_id', 'unknown')}`: {item.get('reason')}")
    else:
        lines.extend(
            [
                "## No Measured Savings Available",
                "",
                "Provide JSONL records with `mode: measured`, `baseline.total_tokens`, and `tailtrail.total_tokens` to calculate exact measured savings.",
            ]
        )

    lines.extend(
        [
            "",
            "## Safe Wording",
            "",
            "- Estimated mode: say `estimated context reduction`, not exact savings.",
            "- Measured mode: say `measured token reduction` only for records backed by model/API usage metadata.",
            "- Missing telemetry: say exact token savings are unavailable.",
            "",
        ]
    )
    return "\n".join(lines)


def render_path_table(items: list[dict[str, Any]]) -> list[str]:
    lines = ["| Path | Files | Approx Tokens | Skipped |", "|---|---:|---:|---:|"]
    if not items:
        lines.append("| none | 0 | 0 | 0 |")
        return lines
    for item in items:
        lines.append(
            f"| `{item['path']}` | {item['files']} | {item['approx_tokens']} | {item['skipped']} |"
        )
    return lines


def output(report: dict[str, Any], fmt: str, write_result: Path | None) -> None:
    if fmt == "json":
        body = json.dumps(report, indent=2, sort_keys=True)
    else:
        body = render_markdown(report)
    print(body)
    if write_result:
        write_result.parent.mkdir(parents=True, exist_ok=True)
        write_result.write_text(body + ("\n" if not body.endswith("\n") else ""), encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Estimate or report TailTrail token savings without overstating precision."
    )
    subparsers = root.add_subparsers(dest="command", required=True)

    estimate = subparsers.add_parser("estimate", help="Estimate context reduction from used and avoided local files.")
    estimate.add_argument("--used", nargs="+", required=True, help="Files or folders that were loaded or selected.")
    estimate.add_argument("--avoided", nargs="+", required=True, help="Files or folders intentionally skipped.")
    estimate.add_argument("--chars-per-token", type=int, default=DEFAULT_CHARS_PER_TOKEN)
    estimate.add_argument("--format", choices=("markdown", "json"), default="markdown")
    estimate.add_argument("--write-result", nargs="?", const=DEFAULT_RESULT, type=Path)

    report = subparsers.add_parser("report", help="Report measured savings from normalized telemetry JSONL.")
    report.add_argument("--telemetry", required=True, help="Path to .tailtrail/token-usage.jsonl or similar JSONL.")
    report.add_argument("--format", choices=("markdown", "json"), default="markdown")
    report.add_argument("--write-result", nargs="?", const=DEFAULT_RESULT, type=Path)

    import_parser = subparsers.add_parser("import", help="Import measured model/API usage telemetry into normalized JSONL.")
    import_parser.add_argument("--source", required=True, help="Source JSONL or JSON array with measured records.")
    import_parser.add_argument("--output", default=".tailtrail/token-usage.jsonl", help="Output normalized JSONL path.")
    import_parser.add_argument("--append", action="store_true", help="Append instead of replacing output.")
    import_parser.add_argument("--dry-run", action="store_true", help="Validate and summarize without writing.")
    import_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    import_parser.add_argument("--write-result", type=Path, default=None)

    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "estimate":
        if args.chars_per_token <= 0:
            raise SystemExit("--chars-per-token must be greater than zero")
        report = estimate_report(args)
    elif args.command == "report":
        report = report_from_telemetry(args)
    elif args.command == "import":
        report = import_telemetry(args)
    else:
        raise SystemExit(f"Unknown command: {args.command}")
    output(report, args.format, args.write_result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
