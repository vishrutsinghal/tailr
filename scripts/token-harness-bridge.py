#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAX_INPUT_BYTES = 250_000
ALLOWED_CONTENT_TYPES = {"log", "documentation", "scanner-output", "json", "tool-output"}
BLOCKED_CONTENT_TYPES = {
    "source",
    "diff",
    "config",
    "security-policy",
    "dependency-manifest",
    "learning-history",
    "unknown",
}
SAFE_EXACTNESS_CLASSES = {"reduce-safe", "summary-safe", "structure-exact"}
UNSAFE_MARKERS = (
    "BEGIN PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "BEGIN OPENSSH PRIVATE KEY",
    "password=",
    "passwd=",
    "api_key=",
    "apikey=",
    "secret=",
    "token=",
)


def load_script(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


token_harness = load_script("tailtrail_token_harness_bridge_router", Path(__file__).resolve().with_name("token-harness.py"))


def read_text(path: Path, max_bytes: int) -> tuple[str, int, bool]:
    data = path.read_bytes()
    truncated = len(data) > max_bytes
    return data[:max_bytes].decode("utf-8", errors="replace"), len(data), truncated


def parse_scalar(value: str) -> str | int | bool:
    cleaned = value.strip().strip('"').strip("'")
    lowered = cleaned.lower()
    if lowered in {"true", "yes", "enabled", "on"}:
        return True
    if lowered in {"false", "no", "disabled", "off"}:
        return False
    try:
        return int(cleaned)
    except ValueError:
        return cleaned


def default_policy() -> dict[str, Any]:
    return {
        "enabled": False,
        "adapter_command": "",
        "allowed_content_types": sorted(ALLOWED_CONTENT_TYPES),
        "max_input_bytes": DEFAULT_MAX_INPUT_BYTES,
        "require_approval": True,
        "source": "default",
    }


def load_policy(root: Path) -> dict[str, Any]:
    policy = default_policy()
    candidates = [root / "tailtrail-policy.md", root / ".tailtrail" / "policy-overrides.json"]
    markdown_policy = candidates[0]
    if markdown_policy.exists():
        policy["source"] = markdown_policy.as_posix()
        lines = markdown_policy.read_text(encoding="utf-8", errors="replace").splitlines()
        in_section = False
        current_list: str | None = None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## "):
                in_section = stripped.lower() == "## token harness bridge"
                current_list = None
                continue
            if not in_section or not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("- ") and current_list:
                value = stripped[2:].strip()
                if value:
                    policy.setdefault(current_list, []).append(value)
                continue
            if ":" not in stripped:
                current_list = None
                continue
            key, raw_value = stripped.split(":", 1)
            key = key.strip().replace("-", "_")
            raw_value = raw_value.strip()
            if key == "runtime_compression_bridge":
                policy["enabled"] = raw_value.lower() in {"enabled", "true", "yes", "on"}
            elif key == "adapter_command":
                policy["adapter_command"] = str(parse_scalar(raw_value)) if raw_value else ""
            elif key == "allowed_content_types":
                policy["allowed_content_types"] = []
                current_list = "allowed_content_types"
            elif key == "max_input_bytes":
                parsed = parse_scalar(raw_value)
                policy["max_input_bytes"] = parsed if isinstance(parsed, int) and parsed > 0 else DEFAULT_MAX_INPUT_BYTES
            elif key == "require_approval":
                parsed = parse_scalar(raw_value)
                policy["require_approval"] = bool(parsed)
            else:
                current_list = None
    json_policy = candidates[1]
    if json_policy.exists():
        data = json.loads(json_policy.read_text(encoding="utf-8"))
        bridge = data.get("token_harness_bridge", data)
        if isinstance(bridge, dict):
            policy["source"] = json_policy.as_posix()
            if "runtime_compression_bridge" in bridge:
                policy["enabled"] = str(bridge["runtime_compression_bridge"]).lower() in {"enabled", "true", "yes", "on"}
            if "enabled" in bridge:
                policy["enabled"] = bool(bridge["enabled"])
            if "adapter_command" in bridge:
                policy["adapter_command"] = str(bridge["adapter_command"])
            if "allowed_content_types" in bridge and isinstance(bridge["allowed_content_types"], list):
                policy["allowed_content_types"] = [str(item) for item in bridge["allowed_content_types"]]
            if "max_input_bytes" in bridge:
                policy["max_input_bytes"] = int(bridge["max_input_bytes"])
            if "require_approval" in bridge:
                policy["require_approval"] = bool(bridge["require_approval"])
    allowed = [item for item in policy.get("allowed_content_types", []) if item in ALLOWED_CONTENT_TYPES]
    policy["allowed_content_types"] = allowed or sorted(ALLOWED_CONTENT_TYPES)
    return policy


def blocked_reason(route: dict[str, Any], policy: dict[str, Any]) -> str | None:
    content_type = route["classification"]["content_type"]
    exactness = route["classification"]["exactness_class"]
    size_bytes = int(route["input"].get("size_bytes", 0))
    if content_type in BLOCKED_CONTENT_TYPES:
        return f"{content_type} content is protected and must not enter an external compression adapter"
    if exactness not in SAFE_EXACTNESS_CLASSES:
        return f"{exactness} content is not eligible for runtime compression"
    if content_type not in set(policy["allowed_content_types"]):
        return f"{content_type} is not allowed by local bridge policy"
    if size_bytes > int(policy["max_input_bytes"]):
        return f"input size {size_bytes} exceeds policy max_input_bytes {policy['max_input_bytes']}"
    return None


def status_for(path: Path, root: Path, label: str | None, task: str | None) -> dict[str, Any]:
    policy = load_policy(root)
    route = token_harness.build_route(path, None, label, task)
    reason = blocked_reason(route, policy)
    if not policy["enabled"]:
        status = "disabled"
        reason = "no local policy enabled runtime compression bridge"
    elif reason:
        status = "blocked"
    else:
        status = "eligible"
    return {
        "schema_version": "1",
        "type": "tailtrail-token-harness-bridge-plan",
        "status": status,
        "reason": reason or "content is eligible for optional runtime compression",
        "policy": {
            "source": policy["source"],
            "enabled": policy["enabled"],
            "allowed_content_types": policy["allowed_content_types"],
            "max_input_bytes": policy["max_input_bytes"],
            "require_approval": policy["require_approval"],
            "adapter_configured": bool(policy.get("adapter_command")),
        },
        "route": route,
        "fallback": "exact pass-through or internal structured reducer",
    }


def unsafe_text_issues(text: str) -> list[str]:
    lowered = text.lower()
    issues: list[str] = []
    for marker in UNSAFE_MARKERS:
        if marker.lower() in lowered:
            issues.append(f"unsafe marker detected: {marker}")
    return issues


def bridge_input(path: Path, root: Path, label: str | None, task: str | None) -> dict[str, Any]:
    plan = status_for(path, root, label, task)
    if plan["status"] != "eligible":
        raise SystemExit(f"Bridge input blocked.\nReason: {plan['reason']}\nFallback: {plan['fallback']}")
    policy = load_policy(root)
    text, size_bytes, truncated = read_text(path, int(policy["max_input_bytes"]))
    route = plan["route"]
    issues = unsafe_text_issues(text)
    if issues:
        raise SystemExit("Bridge input blocked.\nReason: " + "; ".join(issues) + f"\nFallback: {plan['fallback']}")
    return {
        "schema_version": "1",
        "type": "tailtrail-token-harness-bridge-input",
        "content_type": route["classification"]["content_type"],
        "exactness_class": route["classification"]["exactness_class"],
        "strategy": route["strategy"]["name"],
        "allowed_reductions": route["strategy"].get("allowed_reductions", []),
        "blocked_reductions": route["strategy"].get("blocked_reductions", []),
        "preserve": route["preserve"],
        "retrieval": route["retrieval"],
        "input": {
            "kind": "path",
            "path": path.as_posix(),
            "size_bytes": size_bytes,
            "sample_truncated": truncated,
            "text": text,
        },
    }


def validate_bridge_input(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = {"schema_version", "type", "content_type", "exactness_class", "strategy", "allowed_reductions", "blocked_reductions", "preserve", "retrieval", "input"}
    missing = sorted(required - set(payload))
    issues.extend(f"missing input field: {field}" for field in missing)
    if payload.get("type") != "tailtrail-token-harness-bridge-input":
        issues.append("input type must be tailtrail-token-harness-bridge-input")
    if payload.get("content_type") not in ALLOWED_CONTENT_TYPES:
        issues.append("input content_type is not bridge-allowed")
    if payload.get("exactness_class") not in SAFE_EXACTNESS_CLASSES:
        issues.append("input exactness_class is not bridge-safe")
    if not isinstance(payload.get("preserve"), list) or not payload.get("preserve"):
        issues.append("input preserve must be a non-empty list")
    retrieval = payload.get("retrieval", {})
    if not isinstance(retrieval, dict) or not retrieval.get("command"):
        issues.append("input retrieval.command is required")
    input_body = payload.get("input", {})
    if not isinstance(input_body, dict) or input_body.get("kind") != "path" or not input_body.get("path"):
        issues.append("input.kind path and input.path are required")
    text = input_body.get("text") if isinstance(input_body, dict) else ""
    if isinstance(text, str):
        issues.extend(unsafe_text_issues(text))
    return issues


def validate_output_payload(input_payload: dict[str, Any], output_payload: dict[str, Any]) -> list[str]:
    issues = validate_bridge_input(input_payload)
    required = {"schema_version", "type", "status", "content_type", "exactness_class", "strategy", "preserved", "blocked_reductions_honored", "text", "retrieval", "adapter"}
    missing = sorted(required - set(output_payload))
    issues.extend(f"missing output field: {field}" for field in missing)
    if output_payload.get("type") != "tailtrail-token-harness-bridge-output":
        issues.append("output type must be tailtrail-token-harness-bridge-output")
    if output_payload.get("status") != "compressed":
        issues.append("output status must be compressed")
    if output_payload.get("content_type") != input_payload.get("content_type"):
        issues.append("output content_type must match input")
    if output_payload.get("exactness_class") != input_payload.get("exactness_class"):
        issues.append("output exactness_class must match input")
    preserved = output_payload.get("preserved")
    if not isinstance(preserved, list):
        issues.append("output preserved must be a list")
        preserved = []
    required_preserve = set(str(item) for item in input_payload.get("preserve", []))
    actual_preserve = set(str(item) for item in preserved)
    for item in sorted(required_preserve - actual_preserve):
        issues.append(f"missing required preserved evidence: {item}")
    if output_payload.get("blocked_reductions_honored") is not True:
        issues.append("blocked_reductions_honored must be true")
    input_retrieval = input_payload.get("retrieval", {})
    output_retrieval = output_payload.get("retrieval", {})
    if not isinstance(output_retrieval, dict) or output_retrieval.get("command") != input_retrieval.get("command"):
        issues.append("retrieval command must be preserved")
    text = output_payload.get("text")
    if not isinstance(text, str) or not text.strip():
        issues.append("output text must be non-empty")
    else:
        issues.extend(unsafe_text_issues(text))
        original_text = str(input_payload.get("input", {}).get("text", ""))
        if len(text.encode("utf-8", errors="replace")) > len(original_text.encode("utf-8", errors="replace")):
            issues.append("output text must not be larger than original safe context")
    adapter = output_payload.get("adapter")
    if not isinstance(adapter, dict) or not adapter.get("name"):
        issues.append("adapter.name is required")
    return issues


def render_plan(payload: dict[str, Any]) -> str:
    route = payload["route"]
    lines = [
        "# Token Harness Bridge Plan",
        "",
        f"- Status: `{payload['status']}`",
        f"- Reason: {payload['reason']}",
        f"- Content type: `{route['classification']['content_type']}`",
        f"- Exactness: `{route['classification']['exactness_class']}`",
        f"- Strategy: `{route['strategy']['name']}`",
        f"- Policy source: `{payload['policy']['source']}`",
        f"- Adapter configured: `{str(payload['policy']['adapter_configured']).lower()}`",
        f"- Fallback: {payload['fallback']}",
    ]
    return "\n".join(lines) + "\n"


def render_validation(accepted: bool, issues: list[str]) -> str:
    if accepted:
        return "# Token Harness Bridge Validation\n\n- Status: `accepted`\n"
    lines = ["# Token Harness Bridge Validation", "", "- Status: `rejected`", "", "## Reasons", ""]
    lines.extend(f"- {issue}" for issue in issues)
    lines.extend(["", "- Fallback: exact original or internal structured reducer"])
    return "\n".join(lines) + "\n"


def render_run(status: str, reason: str, output: dict[str, Any] | None, fallback: str) -> str:
    lines = [
        "# Token Harness Bridge",
        "",
        f"- Status: `{status}`",
        f"- Reason: {reason}",
        f"- Fallback used: `{str(status != 'accepted').lower()}`",
    ]
    if output:
        lines.extend(
            [
                f"- Adapter: `{output.get('adapter', {}).get('name', '')}`",
                f"- Content type: `{output.get('content_type', '')}`",
                f"- Exactness: `{output.get('exactness_class', '')}`",
                f"- Retrieval: `{output.get('retrieval', {}).get('command', '')}`",
                "",
                "## Compressed Output",
                "",
                output.get("text", ""),
            ]
        )
    else:
        lines.append(f"- Fallback: {fallback}")
    return "\n".join(lines).rstrip() + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Unable to read JSON {path}: {error}") from error
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected JSON object in {path}")
    return payload


def command_from_policy_or_arg(root: Path, adapter_command: str | None) -> str:
    if adapter_command:
        return adapter_command
    policy = load_policy(root)
    return str(policy.get("adapter_command") or "")


def run_adapter(adapter_command: str, payload: dict[str, Any]) -> tuple[int, str, str]:
    if not adapter_command.strip():
        raise SystemExit("Bridge run blocked.\nReason: no adapter command configured\nFallback: exact original or internal structured reducer")
    command = shlex.split(adapter_command)
    if not command:
        raise SystemExit("Bridge run blocked.\nReason: adapter command is empty\nFallback: exact original or internal structured reducer")
    result = subprocess.run(
        command,
        input=json.dumps(payload, sort_keys=True),
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Optional policy-gated Token Harness runtime compression bridge.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(source_parser: argparse.ArgumentParser) -> None:
        source_parser.add_argument("--root", type=Path, default=Path("."))
        source_parser.add_argument("--path", type=Path, required=True)
        source_parser.add_argument("--label")
        source_parser.add_argument("--task")
        source_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")

    plan = subparsers.add_parser("plan", help="Explain whether a path is bridge-eligible.")
    add_common(plan)

    input_cmd = subparsers.add_parser("input", help="Emit deterministic bridge input JSON.")
    add_common(input_cmd)
    input_cmd.add_argument("--output", type=Path)

    validate = subparsers.add_parser("validate-output", help="Validate adapter output against bridge input.")
    validate.add_argument("--input", type=Path, required=True)
    validate.add_argument("--output", type=Path, required=True)
    validate.add_argument("--format", choices=("markdown", "json"), default="markdown")

    run = subparsers.add_parser("run", help="Run an approved local adapter and validate its output.")
    add_common(run)
    run.add_argument("--adapter-command")
    run.add_argument("--approved", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "plan":
        payload = status_for(args.path, args.root.resolve(), args.label, args.task)
        print(json.dumps(payload, indent=2, sort_keys=True) if args.format == "json" else render_plan(payload), end="")
        return 0
    if args.command == "input":
        payload = bridge_input(args.path, args.root.resolve(), args.label, args.task)
        if args.output:
            write_json(args.output, payload)
        print(json.dumps(payload, indent=2, sort_keys=True), end="\n")
        return 0
    if args.command == "validate-output":
        input_payload = read_json(args.input)
        output_payload = read_json(args.output)
        issues = validate_output_payload(input_payload, output_payload)
        result = {
            "schema_version": "1",
            "type": "tailtrail-token-harness-bridge-validation",
            "status": "accepted" if not issues else "rejected",
            "issues": issues,
        }
        print(json.dumps(result, indent=2, sort_keys=True) if args.format == "json" else render_validation(not issues, issues), end="")
        return 0 if not issues else 1
    if args.command == "run":
        policy = load_policy(args.root.resolve())
        if policy["require_approval"] and not args.approved:
            raise SystemExit("Refusing to run runtime compression bridge without --approved.")
        input_payload = bridge_input(args.path, args.root.resolve(), args.label, args.task)
        adapter_command = command_from_policy_or_arg(args.root.resolve(), args.adapter_command)
        returncode, stdout, stderr = run_adapter(adapter_command, input_payload)
        fallback = "exact original or internal structured reducer"
        if returncode != 0:
            print(render_run("rejected", f"adapter command failed with exit code {returncode}: {stderr.strip()}", None, fallback), end="")
            return 1
        try:
            output_payload = json.loads(stdout)
        except json.JSONDecodeError:
            print(render_run("rejected", "adapter output was not valid JSON", None, fallback), end="")
            return 1
        issues = validate_output_payload(input_payload, output_payload)
        if issues:
            print(render_run("rejected", "; ".join(issues), None, fallback), end="")
            return 1
        print(json.dumps(output_payload, indent=2, sort_keys=True) if args.format == "json" else render_run("accepted", "adapter output satisfied the bridge contract", output_payload, fallback), end="")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
