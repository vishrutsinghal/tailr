#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())

import context_receipt

MAX_TEXT_BYTES = 512_000
MAX_FINDINGS = 20
MAX_PATHS = 60


def load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


token_harness = load_script("tailtrail_token_harness_router", Path(__file__).resolve().with_name("token-harness.py"))


def approx_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4) if text else 0


def read_text(path: Path | None, inline_text: str | None) -> tuple[str, int, bool]:
    if inline_text is not None:
        data = inline_text.encode("utf-8", errors="replace")
        return inline_text, len(data), False
    if path is None:
        return "", 0, False
    try:
        data = path.read_bytes()
    except OSError as error:
        raise SystemExit(f"Unable to read {path}: {error}") from error
    truncated = len(data) > MAX_TEXT_BYTES
    return data[:MAX_TEXT_BYTES].decode("utf-8", errors="replace"), len(data), truncated


def json_type(value: Any) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if value is None:
        return "null"
    return type(value).__name__


def safe_scalar(value: Any) -> Any:
    if isinstance(value, str):
        if len(value) > 80:
            return f"{value[:77]}..."
        if any(marker in value.lower() for marker in ("password=", "secret=", "token=", "http://", "https://", "@")):
            return "[redacted]"
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return json_type(value)


def walk_json(value: Any, path: str, paths: list[str], array_counts: dict[str, int]) -> Any:
    if len(paths) < MAX_PATHS and path:
        paths.append(path)
    if isinstance(value, dict):
        return {str(key): walk_json(child, f"{path}.{key}" if path else str(key), paths, array_counts) for key, child in list(value.items())[:25]}
    if isinstance(value, list):
        array_counts[path or "$"] = len(value)
        sample = walk_json(value[0], f"{path}[]" if path else "[]", paths, array_counts) if value else "empty"
        return {"type": "array", "count": len(value), "item_shape": sample}
    return {"type": json_type(value), "sample": safe_scalar(value)}


def reduce_json(text: str, content_type: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        return {
            "strategy": "json-parse-failed",
            "status": "blocked",
            "reason": f"JSON parsing failed at line {error.lineno}, column {error.colno}.",
            "summary": {},
        }
    paths: list[str] = []
    array_counts: dict[str, int] = {}
    shape = walk_json(value, "", paths, array_counts)
    top_level_keys = list(value.keys()) if isinstance(value, dict) else []
    return {
        "strategy": "scanner-focused-summary" if content_type == "scanner-output" else "json-structure-summary",
        "status": "reduced",
        "summary": {
            "top_level_keys": top_level_keys[:40],
            "root_type": json_type(value),
            "array_counts": array_counts,
            "important_paths": paths[:MAX_PATHS],
            "representative_shape": shape,
        },
    }


def nested_get(value: Any, keys: tuple[str, ...]) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def collect_scanner_findings(value: Any, findings: list[dict[str, Any]]) -> None:
    if len(findings) >= MAX_FINDINGS:
        return
    if isinstance(value, dict):
        rule = value.get("ruleId") or value.get("rule_id") or value.get("check_id") or value.get("id")
        severity = value.get("level") or value.get("severity") or nested_get(value, ("vulnerability", "severity"))
        message = value.get("message")
        if isinstance(message, dict):
            message = message.get("text") or message.get("message")
        location = ""
        line = ""
        locations = value.get("locations") or []
        if isinstance(locations, list) and locations:
            first = locations[0]
            location = nested_get(first, ("physicalLocation", "artifactLocation", "uri")) or nested_get(first, ("physicalLocation", "artifactLocation", "uriBaseId")) or ""
            line = nested_get(first, ("physicalLocation", "region", "startLine")) or ""
        package = nested_get(value, ("artifact", "name")) or nested_get(value, ("package", "name")) or value.get("packageName") or ""
        version = nested_get(value, ("artifact", "version")) or nested_get(value, ("package", "version")) or value.get("installedVersion") or ""
        vulnerability = nested_get(value, ("vulnerability", "id")) or value.get("cve") or value.get("ghsa") or ""
        if rule or severity or location or vulnerability:
            findings.append(
                {
                    "rule_id": str(rule or vulnerability or "unknown"),
                    "severity": str(severity or "unknown"),
                    "file": str(location),
                    "line": str(line),
                    "package": str(package),
                    "version": str(version),
                    "message": str(message or "")[:180],
                }
            )
        for child in value.values():
            collect_scanner_findings(child, findings)
    elif isinstance(value, list):
        for item in value:
            collect_scanner_findings(item, findings)


def reduce_scanner(text: str) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = None
    if value is not None:
        collect_scanner_findings(value, findings)
    else:
        for line in text.splitlines():
            if len(findings) >= MAX_FINDINGS:
                break
            if re.search(r"\b(critical|high|medium|low|warning|error|info|cve-\d{4}-\d+|ghsa-)\b", line, re.IGNORECASE):
                match = re.search(r"(?P<severity>critical|high|medium|low|warning|error|info)", line, re.IGNORECASE)
                location = re.search(r"(?P<file>[\w./\\-]+\.\w+)(:(?P<line>\d+))?", line)
                rule = re.search(r"\b(?P<rule>(CVE-\d{4}-\d+|GHSA-[\w-]+|[A-Za-z]+:[A-Za-z0-9_-]+|[A-Z]\d{3,}))\b", line)
                findings.append(
                    {
                        "rule_id": rule.group("rule") if rule else "unknown",
                        "severity": match.group("severity").lower() if match else "unknown",
                        "file": location.group("file") if location else "",
                        "line": location.group("line") if location and location.group("line") else "",
                        "package": "",
                        "version": "",
                        "message": line.strip()[:180],
                    }
                )
    counts: dict[str, int] = {}
    for finding in findings:
        severity = str(finding.get("severity") or "unknown").lower()
        counts[severity] = counts.get(severity, 0) + 1
    return {"strategy": "scanner-focused-summary", "status": "reduced", "summary": {"findings": findings, "severity_counts": counts, "finding_count": len(findings)}}


def reduce_log(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    failure_indexes = [index for index, line in enumerate(lines) if re.search(r"\b(error|exception|failed|failure|traceback|fatal)\b", line, re.IGNORECASE)]
    command_lines = [line.strip() for line in lines if re.match(r"^\s*(\$|>|Running |Command:)", line)]
    repeated: dict[str, int] = {}
    for line in lines:
        normalized = re.sub(r"\d+", "#", line.strip())
        if re.search(r"\b(error|exception|failed|failure|fatal)\b", normalized, re.IGNORECASE):
            repeated[normalized[:160]] = repeated.get(normalized[:160], 0) + 1
    stack_lines = [line.strip() for line in lines if re.match(r"^\s*(at\s+[\w.$<>]+\(|File \".+\", line \d+|Traceback)", line)]
    exit_code = ""
    for line in reversed(lines):
        match = re.search(r"\b(exit code|exited with code|return code)[:= ]+(?P<code>\d+)\b", line, re.IGNORECASE)
        if match:
            exit_code = match.group("code")
            break
    first_failure = lines[failure_indexes[0]].strip() if failure_indexes else ""
    last_failure = lines[failure_indexes[-1]].strip() if failure_indexes else ""
    repeated_errors = [{"line": key, "count": count} for key, count in sorted(repeated.items(), key=lambda item: item[1], reverse=True)[:10]]
    return {
        "strategy": "failure-focused-summary",
        "status": "reduced",
        "summary": {
            "line_count": len(lines),
            "command_boundaries": command_lines[:12],
            "first_failure": first_failure[:240],
            "last_failure": last_failure[:240],
            "stack_trace_lines": stack_lines[:20],
            "repeated_errors": repeated_errors,
            "exit_code": exit_code,
        },
    }


def python_structure(text: str) -> dict[str, Any]:
    tree = ast.parse(text)
    imports: list[str] = []
    classes: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.extend(f"{module}.{alias.name}".strip(".") for alias in node.names)
        elif isinstance(node, ast.ClassDef):
            methods = [
                {
                    "name": child.name,
                    "line": child.lineno,
                    "args": [arg.arg for arg in child.args.args],
                }
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            classes.append({"name": node.name, "line": node.lineno, "methods": methods})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({"name": node.name, "line": node.lineno, "args": [arg.arg for arg in node.args.args]})
    return {"imports": imports, "classes": classes, "functions": functions, "parser": "python-ast"}


def regex_source_structure(text: str, suffix: str) -> dict[str, Any]:
    imports: list[str] = []
    classes: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if re.match(r"^(import|using|package)\b", stripped):
            imports.append(stripped[:180])
        class_match = re.search(r"\b(class|interface|record)\s+(?P<name>[A-Za-z_][\w]*)", stripped)
        if class_match:
            classes.append({"name": class_match.group("name"), "line": number, "methods": []})
        function_match = re.search(r"\b(?P<name>[A-Za-z_][\w]*)\s*\([^;{}]*\)\s*(\{|=>|:)?", stripped)
        if function_match and not re.match(r"^(if|for|while|switch|catch)\b", stripped):
            functions.append({"name": function_match.group("name"), "line": number})
    return {"imports": imports[:80], "classes": classes[:80], "functions": functions[:120], "parser": f"regex-{suffix.lstrip('.') or 'text'}"}


def reduce_source_structure(path: Path | None, text: str) -> dict[str, Any]:
    suffix = path.suffix.lower() if path else ""
    try:
        structure = python_structure(text) if suffix == ".py" else regex_source_structure(text, suffix)
        status = "reduced"
        reason = "Source structure extracted without function bodies."
    except SyntaxError as error:
        structure = regex_source_structure(text, suffix)
        status = "reduced"
        reason = f"Python AST parse failed at line {error.lineno}; used conservative regex structure."
    return {"strategy": "source-structure-view", "status": status, "reason": reason, "summary": structure}


def reduction_allowed(route: dict[str, Any], mode: str) -> tuple[bool, str]:
    content_type = route["classification"]["content_type"]
    exactness = route["classification"]["exactness_class"]
    if content_type == "source" and mode == "structure":
        return True, "Source structure view requested; source bodies remain omitted."
    if exactness == "must-be-exact":
        return False, f"{content_type} is must-be-exact and cannot be reduced."
    if content_type in {"diff", "dependency-manifest", "config", "security-policy"}:
        return False, f"{content_type} is protected exact evidence."
    if exactness == "skip-reduction":
        return False, "Content is tiny, unknown, or not worth reducing."
    return True, "Content can be reduced with its exactness constraints."


def build_reduction(args: argparse.Namespace) -> dict[str, Any]:
    text, size_bytes, truncated = read_text(args.path, args.text)
    route = token_harness.build_route(args.path, text, args.label, args.task)
    content_type = route["classification"]["content_type"]
    exactness = route["classification"]["exactness_class"]
    allowed, reason = reduction_allowed(route, args.mode)
    before = approx_tokens(text)
    retrieval = token_harness.retrieval_command(args.path)
    if not allowed:
        status = "blocked"
        strategy = "skip-reduction"
        summary: dict[str, Any] = {"reason": reason}
    elif content_type == "source":
        result = reduce_source_structure(args.path, text)
        status = result["status"]
        strategy = result["strategy"]
        summary = result["summary"]
        reason = result.get("reason", reason)
        exactness = "structure-exact"
    elif content_type == "scanner-output":
        result = reduce_scanner(text)
        status = result["status"]
        strategy = result["strategy"]
        summary = result["summary"]
    elif content_type in {"json", "tool-output"}:
        result = reduce_json(text, content_type)
        status = result["status"]
        strategy = result["strategy"]
        summary = result["summary"]
        if status == "blocked":
            reason = result["reason"]
    elif content_type == "log":
        result = reduce_log(text)
        status = result["status"]
        strategy = result["strategy"]
        summary = result["summary"]
    elif content_type == "documentation":
        headings = [line.strip() for line in text.splitlines() if line.lstrip().startswith("#")][:30]
        status = "reduced"
        strategy = "doc-section-slice"
        summary = {"headings": headings, "line_count": len(text.splitlines()), "note": "Use exact sections by heading before editing documentation."}
    else:
        status = "blocked"
        strategy = "skip-reduction"
        summary = {"reason": f"No reducer implemented for {content_type}."}
    reduced_text = json.dumps(summary, sort_keys=True)
    after = before if status == "blocked" else min(before, approx_tokens(reduced_text))
    preserve = token_harness.preserve_list(content_type, exactness)
    payload = {
        "schema_version": "1",
        "type": "tailtrail-token-harness-reduction",
        "status": status,
        "content_type": content_type,
        "exactness_class": exactness,
        "strategy": strategy,
        "reason": reason,
        "input": {
            "path": args.path.as_posix() if args.path else "",
            "label": args.label or "",
            "size_bytes": size_bytes,
            "sample_truncated": truncated,
        },
        "tokens_before": before,
        "tokens_after": after,
        "estimated_tokens_saved": max(0, before - after),
        "preserve": preserve,
        "retrieval": {"command": retrieval},
        "summary": summary,
        "claim_guardrail": "Structured reducer output is local approximate context shaping, not exact model/API token savings.",
        "notes": [
            "Original evidence remains retrievable.",
            "Protected exact content is blocked from reduction.",
            "Source structure views omit function bodies.",
        ],
    }
    return payload


def write_receipt(args: argparse.Namespace, payload: dict[str, Any]) -> None:
    if args.path is None:
        raise SystemExit("Refusing to write reducer receipt for inline text; use --path so the original evidence is retrievable.")
    receipt_args = argparse.Namespace(
        root=args.root,
        task=args.task or "token harness reduction",
        profile="token-harness",
        budget=0,
        loaded=[args.path.as_posix()],
        avoided=[],
        loaded_exactness=[payload["exactness_class"]],
        avoided_exactness=[],
        loaded_strategy=[payload["strategy"]],
        avoided_strategy=[],
        preserve=payload["preserve"],
        preserved_evidence=payload["preserve"],
        retrieval=[payload["retrieval"]["command"]],
        route_source="token-harness-reduce",
        reduction_strategy=payload["strategy"],
        loaded_tokens=payload["tokens_after"],
        avoided_tokens=payload["estimated_tokens_saved"],
        graph_first="no",
        budget_escalated="no",
        reason=payload["claim_guardrail"],
    )
    receipt = context_receipt.capture_payload(receipt_args)
    context_receipt.write_jsonl(args.receipts or args.root / context_receipt.DEFAULT_RECEIPTS, receipt)


def write_ledger(args: argparse.Namespace, payload: dict[str, Any]) -> None:
    script = Path(__file__).resolve().with_name("token-harness-ledger.py")
    command = [
        sys.executable,
        script.as_posix(),
        "append",
        "--root",
        args.root.as_posix(),
        "--event-type",
        "context_receipt" if args.write_receipt else "route_decision",
        "--task-type",
        args.task or "token-harness-reduction",
        "--content-type",
        payload["content_type"],
        "--strategy",
        payload["strategy"],
        "--exactness-class",
        payload["exactness_class"],
        "--tokens-before",
        str(payload["tokens_before"]),
        "--tokens-after",
        str(payload["tokens_after"]),
        "--evidence-label",
        "local-evidence",
        "--validation-outcome",
        "not-run",
        "--approved",
    ]
    if args.ledger:
        command.extend(["--ledger", args.ledger.as_posix()])
    if args.write_receipt:
        receipt_ref = args.receipts.as_posix() if args.receipts else ".tailtrail/context-receipts.jsonl"
        command.extend(["--receipt-ref", receipt_ref])
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        raise SystemExit(result.returncode)


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Token Harness Reduction",
        "",
        f"- Status: `{payload['status']}`",
        f"- Content type: `{payload['content_type']}`",
        f"- Exactness: `{payload['exactness_class']}`",
        f"- Strategy: `{payload['strategy']}`",
        f"- Tokens before: `{payload['tokens_before']}`",
        f"- Tokens after: `{payload['tokens_after']}`",
        f"- Estimated saved: `{payload['estimated_tokens_saved']}`",
        f"- Reason: {payload['reason']}",
        f"- Claim guardrail: {payload['claim_guardrail']}",
        "",
        "## Preserve",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["preserve"])
    lines.extend(["", "## Summary", "", "```json", json.dumps(payload["summary"], indent=2, sort_keys=True), "```", "", "## Retrieval", "", f"- `{payload['retrieval']['command']}`", ""])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reduce safe Token Harness content with exactness-preserving structured reducers.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--path", type=Path)
    source.add_argument("--text")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--label")
    parser.add_argument("--task", default="")
    parser.add_argument("--mode", choices=("auto", "structure"), default="auto")
    parser.add_argument("--write-receipt", action="store_true")
    parser.add_argument("--receipts", type=Path)
    parser.add_argument("--write-ledger", action="store_true")
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.root = args.root.resolve()
    if args.path is not None and not args.path.is_absolute():
        args.path = args.root / args.path
    if (args.write_receipt or args.write_ledger) and not args.approved:
        raise SystemExit("Refusing to write reducer receipt or ledger event without --approved.")
    payload = build_reduction(args)
    if payload["status"] == "blocked" and (args.write_receipt or args.write_ledger):
        raise SystemExit("Refusing to write receipt or ledger event for blocked reduction.")
    if args.write_receipt:
        write_receipt(args, payload)
    if args.write_ledger:
        write_ledger(args, payload)
    print(json.dumps(payload, indent=2, sort_keys=True) if args.format == "json" else render_markdown(payload), end="")
    return 1 if payload["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
