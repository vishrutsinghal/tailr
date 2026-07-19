#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = Path(".tailtrail/token-usage.jsonl")
SUPPORTED_PROVIDERS = {"openai", "claude", "anthropic", "gemini", "generic"}


@dataclass(frozen=True)
class TokenUsage:
    total_tokens: int
    input_tokens: int | None = None
    output_tokens: int | None = None

    def as_dict(self) -> dict[str, int]:
        data = {"total_tokens": self.total_tokens}
        if self.input_tokens is not None:
            data["input_tokens"] = self.input_tokens
        if self.output_tokens is not None:
            data["output_tokens"] = self.output_tokens
        return data


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, float) and value >= 0 and value.is_integer():
        return int(value)
    return None


def first_int(data: dict[str, Any], keys: list[str]) -> int | None:
    for key in keys:
        value = positive_int(data.get(key))
        if value is not None:
            return value
    return None


def usage_from_dict(data: Any) -> TokenUsage | None:
    if not isinstance(data, dict):
        return None

    input_tokens = first_int(
        data,
        [
            "input_tokens",
            "prompt_tokens",
            "cache_read_input_tokens",
            "inputTokenCount",
            "promptTokenCount",
        ],
    )
    output_tokens = first_int(
        data,
        [
            "output_tokens",
            "completion_tokens",
            "candidatesTokenCount",
            "outputTokenCount",
            "completionTokenCount",
        ],
    )
    total_tokens = first_int(
        data,
        [
            "total_tokens",
            "totalTokenCount",
            "total_token_count",
        ],
    )

    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    if total_tokens is None:
        return None
    return TokenUsage(total_tokens=total_tokens, input_tokens=input_tokens, output_tokens=output_tokens)


def extract_usage(value: Any) -> TokenUsage | None:
    direct = usage_from_dict(value)
    if direct:
        return direct
    if not isinstance(value, dict):
        return None
    for key in (
        "usage",
        "usage_metadata",
        "usageMetadata",
        "token_usage",
        "tokenUsage",
        "response_usage",
        "responseUsage",
    ):
        usage = usage_from_dict(value.get(key))
        if usage:
            return usage
    metadata = value.get("metadata")
    if isinstance(metadata, dict):
        usage = extract_usage(metadata)
        if usage:
            return usage
    response = value.get("response")
    if isinstance(response, dict):
        usage = extract_usage(response)
        if usage:
            return usage
    return None


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

    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise SystemExit(f"Invalid telemetry JSON on line {line_number}: {error}") from error
        if not isinstance(value, dict):
            raise SystemExit(f"Invalid telemetry record on line {line_number}: expected object")
        value["_line_number"] = line_number
        rows.append(value)
    return rows


def baseline_block(record: dict[str, Any]) -> Any:
    for key in ("baseline", "before", "baseline_usage", "before_usage", "without_tailtrail"):
        if key in record:
            return record[key]
    return None


def tailtrail_block(record: dict[str, Any]) -> Any:
    for key in ("tailtrail", "after", "tailtrail_usage", "after_usage", "with_tailtrail"):
        if key in record:
            return record[key]
    return None


def normalize_record(record: dict[str, Any], provider: str, source_label: str) -> dict[str, Any] | None:
    baseline = extract_usage(baseline_block(record))
    tailtrail = extract_usage(tailtrail_block(record))
    if baseline is None or tailtrail is None:
        return None

    normalized_provider = record.get("provider") or provider
    if normalized_provider == "claude":
        normalized_provider = "anthropic"

    return {
        "mode": "measured",
        "task_id": str(record.get("task_id") or record.get("id") or f"task-{record.get('_line_number', 'unknown')}"),
        "provider": str(normalized_provider),
        "model": str(record.get("model") or record.get("model_id") or record.get("modelId") or "unknown"),
        "source": str(record.get("source") or source_label),
        "timestamp": str(record.get("timestamp") or record.get("created_at") or now()),
        "baseline": baseline.as_dict(),
        "tailtrail": tailtrail.as_dict(),
    }


def write_records(records: list[dict[str, Any]], output: Path, append: bool, dry_run: bool) -> None:
    if dry_run or not records:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with output.open(mode, encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def import_file(args: argparse.Namespace, provider: str) -> dict[str, Any]:
    source = Path(args.source)
    rows = read_json_or_jsonl(source)
    imported: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    for row in rows:
        normalized = normalize_record(row, provider, f"{provider}_usage_import")
        if normalized is None:
            ignored.append(
                {
                    "line": row.get("_line_number"),
                    "reason": "missing baseline/before and tailtrail/after usage blocks",
                }
            )
            continue
        imported.append(normalized)

    output_path = Path(args.output)
    write_records(imported, output_path, args.append, args.dry_run)
    return {
        "mode": "provider_import",
        "provider": provider,
        "source": source.as_posix(),
        "output": output_path.as_posix(),
        "records_read": len(rows),
        "imported_records": len(imported),
        "ignored_records": len(ignored),
        "dry_run": args.dry_run,
        "ignored": ignored,
        "claim_guardrail": "Provider import only normalizes supplied usage metadata. It does not call APIs or infer missing baseline/TailTrail pairs.",
    }


def manual(args: argparse.Namespace) -> dict[str, Any]:
    baseline = TokenUsage(
        total_tokens=args.baseline_total
        if args.baseline_total is not None
        else args.baseline_input + args.baseline_output,
        input_tokens=args.baseline_input,
        output_tokens=args.baseline_output,
    )
    tailtrail = TokenUsage(
        total_tokens=args.tailtrail_total
        if args.tailtrail_total is not None
        else args.tailtrail_input + args.tailtrail_output,
        input_tokens=args.tailtrail_input,
        output_tokens=args.tailtrail_output,
    )
    record = {
        "mode": "measured",
        "task_id": args.task_id,
        "provider": args.provider,
        "model": args.model,
        "source": "manual_measured_entry",
        "timestamp": args.timestamp or now(),
        "baseline": baseline.as_dict(),
        "tailtrail": tailtrail.as_dict(),
    }
    output_path = Path(args.output)
    write_records([record], output_path, args.append, args.dry_run)
    return {
        "mode": "manual",
        "output": output_path.as_posix(),
        "records_written": 0 if args.dry_run else 1,
        "dry_run": args.dry_run,
        "record": record,
        "claim_guardrail": "Manual records are measured only when the numbers came from real model/API usage metadata.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    if report["mode"] == "manual":
        record = report["record"]
        lines = [
            "# TailTrail Manual Token Telemetry",
            "",
            f"- Output: `{report['output']}`",
            f"- Records written: `{report['records_written']}`",
            f"- Dry run: `{report['dry_run']}`",
            f"- Task: `{record['task_id']}`",
            f"- Provider/model: `{record['provider']}` / `{record['model']}`",
            f"- Baseline tokens: `{record['baseline']['total_tokens']}`",
            f"- TailTrail tokens: `{record['tailtrail']['total_tokens']}`",
            f"- Claim guardrail: {report['claim_guardrail']}",
        ]
        return "\n".join(lines)

    lines = [
        "# TailTrail Token Telemetry Import",
        "",
        f"- Provider adapter: `{report['provider']}`",
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


def output(report: dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report))


def add_common_import_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", required=True, help="Provider export JSON/JSONL with baseline/before and tailtrail/after usage blocks.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT.as_posix(), help="Normalized output JSONL path.")
    parser.add_argument("--append", action="store_true", help="Append instead of replacing output.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and summarize without writing.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Create normalized measured token telemetry without API calls.")
    subparsers = root.add_subparsers(dest="command", required=True)

    manual_parser = subparsers.add_parser("manual", help="Write one manually entered measured token record.")
    manual_parser.add_argument("--task-id", required=True)
    manual_parser.add_argument("--provider", required=True)
    manual_parser.add_argument("--model", required=True)
    manual_parser.add_argument("--baseline-input", type=int, default=0)
    manual_parser.add_argument("--baseline-output", type=int, default=0)
    manual_parser.add_argument("--baseline-total", type=int)
    manual_parser.add_argument("--tailtrail-input", type=int, default=0)
    manual_parser.add_argument("--tailtrail-output", type=int, default=0)
    manual_parser.add_argument("--tailtrail-total", type=int)
    manual_parser.add_argument("--timestamp")
    manual_parser.add_argument("--output", default=DEFAULT_OUTPUT.as_posix())
    manual_parser.add_argument("--append", action="store_true")
    manual_parser.add_argument("--dry-run", action="store_true")
    manual_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")

    for command, provider in (
        ("import-openai", "openai"),
        ("import-claude", "anthropic"),
        ("import-anthropic", "anthropic"),
        ("import-gemini", "gemini"),
        ("import-generic", "generic"),
    ):
        import_parser = subparsers.add_parser(command, help=f"Import {provider} usage exports without API calls.")
        import_parser.set_defaults(provider=provider)
        add_common_import_args(import_parser)

    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "manual":
        if args.baseline_total is None and args.baseline_input + args.baseline_output <= 0:
            raise SystemExit("Provide --baseline-total or baseline input/output tokens.")
        if args.tailtrail_total is None and args.tailtrail_input + args.tailtrail_output <= 0:
            raise SystemExit("Provide --tailtrail-total or TailTrail input/output tokens.")
        report = manual(args)
    elif args.command.startswith("import-"):
        report = import_file(args, args.provider)
    else:
        raise SystemExit(f"Unknown command: {args.command}")
    output(report, args.format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
