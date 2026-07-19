#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


try:
    import fcntl  # type: ignore
except ImportError:  # pragma: no cover - exercised on non-POSIX platforms.
    fcntl = None


DEFAULT_LEDGER = Path(".tailtrail") / "token-harness-events.jsonl"
DEFAULT_LOCK = Path(".tailtrail") / "token-harness-events.lock"
EVENT_TYPES = {"route_decision", "context_receipt", "measured_usage", "savings_report", "quality_result"}
EVIDENCE_LABELS = {"estimated", "local-evidence", "measured", "benchmark-measured"}
EXACTNESS_CLASSES = {"must-be-exact", "structure-exact", "summary-safe", "reduce-safe", "skip-reduction"}
VALIDATION_OUTCOMES = {"pass", "fail", "not-run", "skipped", "unknown"}
PRICING_FIELDS = {"cost", "cost_usd", "price", "pricing", "dollars", "usd", "amount_usd"}
UNSAFE_MARKERS = ("BEGIN PRIVATE KEY", "BEGIN RSA PRIVATE KEY", "AKIA", "ghp_", "xoxb-", "password=", "secret=", "http://", "https://", "@")
PRIVACY = "No raw prompt, source, log, path, secret, repo name, or user identity."


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ledger_path(root: Path, override: Path | None) -> Path:
    return override if override else root / DEFAULT_LEDGER


def lock_path(root: Path, ledger: Path) -> Path:
    if ledger.name == DEFAULT_LEDGER.name:
        return root / DEFAULT_LOCK
    return ledger.with_suffix(ledger.suffix + ".lock")


def read_jsonl_with_issues(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    issues: list[str] = []
    if not path.exists():
        return rows, issues
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        return rows, [f"ledger could not be read: {error}"]
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            issues.append(f"line {number}: invalid JSON: {error.msg}")
            continue
        if not isinstance(value, dict):
            issues.append(f"line {number}: event is not an object")
            continue
        rows.append(value)
    return rows, issues


def unsafe_values(value: Any, path: str = "") -> list[str]:
    issues: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in PRICING_FIELDS:
                issues.append(f"pricing field `{path + '.' if path else ''}{key}` is not allowed")
            issues.extend(unsafe_values(child, f"{path}.{key}" if path else str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            issues.extend(unsafe_values(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        upper = value.upper()
        lowered = value.lower()
        if any(marker.upper() in upper for marker in UNSAFE_MARKERS) or "token=" in lowered:
            issues.append(f"unsafe text marker at `{path}`")
    return issues


def validate_event(event: dict[str, Any]) -> list[str]:
    required = {
        "schema_version",
        "type",
        "sequence",
        "event_id",
        "created_at",
        "event_type",
        "task_type",
        "content_type",
        "strategy",
        "exactness_class",
        "tokens_before",
        "tokens_after",
        "tokens_saved",
        "evidence_label",
        "validation_outcome",
        "privacy",
    }
    issues = [f"missing field `{field}`" for field in sorted(required - set(event))]
    if event.get("schema_version") != "1":
        issues.append("schema_version must be `1`")
    if event.get("type") != "tailtrail-token-harness-event":
        issues.append("type must be `tailtrail-token-harness-event`")
    if event.get("event_type") not in EVENT_TYPES:
        issues.append(f"event_type `{event.get('event_type')}` is not allowed")
    if event.get("evidence_label") not in EVIDENCE_LABELS:
        issues.append(f"evidence_label `{event.get('evidence_label')}` is not allowed")
    if event.get("exactness_class") not in EXACTNESS_CLASSES:
        issues.append(f"exactness_class `{event.get('exactness_class')}` is not allowed")
    if event.get("validation_outcome") not in VALIDATION_OUTCOMES:
        issues.append(f"validation_outcome `{event.get('validation_outcome')}` is not allowed")
    for field in ("sequence", "tokens_before", "tokens_after", "tokens_saved"):
        if not isinstance(event.get(field), int):
            issues.append(f"{field} must be an integer")
    before = event.get("tokens_before")
    after = event.get("tokens_after")
    saved = event.get("tokens_saved")
    if isinstance(before, int) and isinstance(after, int):
        if after > before:
            issues.append("tokens_after cannot exceed tokens_before")
        if isinstance(saved, int) and saved != before - after:
            issues.append("tokens_saved must equal tokens_before - tokens_after")
    issues.extend(unsafe_values(event))
    return issues


def validate_rows(rows: list[dict[str, Any]], parse_issues: list[str]) -> list[str]:
    issues = list(parse_issues)
    seen_ids: set[str] = set()
    previous = 0
    for index, row in enumerate(rows, start=1):
        prefix = f"event {index}: "
        issues.extend(prefix + issue for issue in validate_event(row))
        sequence = row.get("sequence")
        if isinstance(sequence, int):
            if sequence <= previous:
                issues.append(f"event {index}: sequence is not monotonic")
            previous = sequence
        event_id = str(row.get("event_id", ""))
        if event_id in seen_ids:
            issues.append(f"event {index}: duplicate event_id `{event_id}`")
        if event_id:
            seen_ids.add(event_id)
    return issues


def next_sequence(rows: list[dict[str, Any]]) -> int:
    sequences = [int(row.get("sequence", 0)) for row in rows if isinstance(row.get("sequence"), int)]
    return (max(sequences) if sequences else 0) + 1


def event_id(sequence: int, created_at: str) -> str:
    date = created_at[:10].replace("-", "")
    return f"th-{date}-{sequence:06d}"


def build_event(args: argparse.Namespace, sequence: int, lock_mode: str) -> dict[str, Any]:
    before = int(args.tokens_before)
    after = int(args.tokens_after)
    created = now()
    event = {
        "schema_version": "1",
        "type": "tailtrail-token-harness-event",
        "sequence": sequence,
        "event_id": event_id(sequence, created),
        "created_at": created,
        "event_type": args.event_type,
        "task_type": args.task_type,
        "content_type": args.content_type,
        "strategy": args.strategy,
        "exactness_class": args.exactness_class,
        "tokens_before": before,
        "tokens_after": after,
        "tokens_saved": before - after,
        "evidence_label": args.evidence_label,
        "validation_outcome": args.validation_outcome,
        "receipt_ref": args.receipt_ref or "",
        "lock_mode": lock_mode,
        "privacy": PRIVACY,
    }
    issues = validate_event(event)
    if issues:
        raise SystemExit("Token Harness ledger event validation failed:\n- " + "\n- ".join(issues))
    return event


class LedgerLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle = None
        self.mode = "best-effort"

    def __enter__(self) -> str:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+", encoding="utf-8")
        if fcntl is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
            self.mode = "posix-flock"
        return self.mode

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.handle is None:
            return
        if fcntl is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()


def append_event(root: Path, ledger: Path, args: argparse.Namespace) -> dict[str, Any]:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    lock = lock_path(root, ledger)
    with LedgerLock(lock) as lock_mode:
        rows, parse_issues = read_jsonl_with_issues(ledger)
        existing_issues = validate_rows(rows, parse_issues)
        if existing_issues:
            raise SystemExit("Refusing to append to invalid Token Harness ledger:\n- " + "\n- ".join(existing_issues[:20]))
        event = build_event(args, next_sequence(rows), lock_mode)
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
            handle.flush()
        return event


def summary_payload(root: Path, ledger: Path) -> dict[str, Any]:
    rows, parse_issues = read_jsonl_with_issues(ledger)
    valid_rows = [row for row in rows if not validate_event(row)]
    before = sum(int(row.get("tokens_before", 0)) for row in valid_rows)
    after = sum(int(row.get("tokens_after", 0)) for row in valid_rows)
    return {
        "schema_version": "1",
        "type": "tailtrail-token-harness-ledger-summary",
        "root": root.resolve().as_posix(),
        "ledger": ledger.as_posix(),
        "events": len(rows),
        "valid_events": len(valid_rows),
        "parse_issues": parse_issues,
        "tokens_before": before,
        "tokens_after": after,
        "tokens_saved": before - after,
        "evidence_labels": dict(Counter(str(row.get("evidence_label", "unknown")) for row in valid_rows).most_common()),
        "strategies": dict(Counter(str(row.get("strategy", "unknown")) for row in valid_rows).most_common()),
        "event_types": dict(Counter(str(row.get("event_type", "unknown")) for row in valid_rows).most_common()),
        "claim_guardrail": "Ledger totals are local evidence only. Exact model/API savings require measured telemetry and TH-5 proof gates.",
    }


def render_summary(payload: dict[str, Any]) -> str:
    lines = [
        "# Token Harness Ledger Summary",
        "",
        f"- Events: `{payload['events']}`",
        f"- Valid events: `{payload['valid_events']}`",
        f"- Tokens before: `{payload['tokens_before']}`",
        f"- Tokens after: `{payload['tokens_after']}`",
        f"- Estimated saved: `{payload['tokens_saved']}`",
        "",
        "## Evidence Labels",
        "",
    ]
    evidence_lines = [f"- `{key}`: `{value}`" for key, value in payload["evidence_labels"].items()]
    lines.extend(evidence_lines or ["- none"])
    lines.extend(["", "## Strategies", ""])
    strategy_lines = [f"- `{key}`: `{value}`" for key, value in payload["strategies"].items()]
    lines.extend(strategy_lines or ["- none"])
    lines.extend(["", "## Claim Guardrail", "", payload["claim_guardrail"], ""])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append, summarize, and validate local Token Harness ledger events.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    append = subparsers.add_parser("append", help="Append an approved Token Harness ledger event.")
    append.add_argument("--root", type=Path, default=Path.cwd())
    append.add_argument("--ledger", type=Path)
    append.add_argument("--event-type", required=True, choices=sorted(EVENT_TYPES))
    append.add_argument("--task-type", required=True)
    append.add_argument("--content-type", required=True)
    append.add_argument("--strategy", required=True)
    append.add_argument("--exactness-class", required=True, choices=sorted(EXACTNESS_CLASSES))
    append.add_argument("--tokens-before", required=True, type=int)
    append.add_argument("--tokens-after", required=True, type=int)
    append.add_argument("--evidence-label", required=True, choices=sorted(EVIDENCE_LABELS))
    append.add_argument("--validation-outcome", default="not-run", choices=sorted(VALIDATION_OUTCOMES))
    append.add_argument("--receipt-ref", default="")
    append.add_argument("--approved", action="store_true")
    append.add_argument("--format", choices=("markdown", "json"), default="markdown")
    for command in ("summary", "validate"):
        sub = subparsers.add_parser(command, help=f"{command.title()} Token Harness ledger.")
        sub.add_argument("--root", type=Path, default=Path.cwd())
        sub.add_argument("--ledger", type=Path)
        sub.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    ledger = ledger_path(root, getattr(args, "ledger", None))
    if args.command == "append":
        if not args.approved:
            raise SystemExit("Refusing to write Token Harness ledger event without --approved.")
        event = append_event(root, ledger, args)
        if args.format == "json":
            print(json.dumps(event, indent=2, sort_keys=True))
        else:
            print(f"Appended Token Harness ledger event `{event['event_id']}` sequence `{event['sequence']}` to `{ledger.as_posix()}`.\n")
        return 0
    rows, parse_issues = read_jsonl_with_issues(ledger)
    issues = validate_rows(rows, parse_issues)
    if args.command == "validate":
        payload = {"schema_version": "1", "type": "tailtrail-token-harness-ledger-validation", "ledger": ledger.as_posix(), "valid": not issues, "issues": issues, "events": len(rows)}
        if args.format == "json":
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("# Token Harness Ledger Validation\n")
            print(f"- Ledger: `{ledger.as_posix()}`")
            print(f"- Valid: `{str(payload['valid']).lower()}`")
            print(f"- Events: `{payload['events']}`")
            if issues:
                print("\n## Issues\n")
                for issue in issues:
                    print(f"- {issue}")
        return 0 if not issues else 1
    payload = summary_payload(root, ledger)
    print(json.dumps(payload, indent=2, sort_keys=True) if args.format == "json" else render_summary(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
