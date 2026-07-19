#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
DEFAULT_READ_ONLY_TOOLS = (
    "navigator_plan",
    "start_report",
    "guardrail_check",
    "graph_map",
    "install_status",
    "eval_scenario_list",
    "eval_scenario_report",
)
DENIED_TOOL_TERMS = (
    "apply",
    "build",
    "capture",
    "commit",
    "delete",
    "deploy",
    "edit",
    "fix",
    "install",
    "learn",
    "mutate",
    "push",
    "run",
    "scan",
    "test",
    "update",
    "write",
)


def load_registry() -> Any | None:
    path = ROOT / "scripts" / "tailtrail-registry.py"
    spec = importlib.util.spec_from_file_location("tailtrail_registry_for_mcp", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def registry_read_only_tools() -> tuple[str, ...]:
    module = load_registry()
    if module is None:
        return DEFAULT_READ_ONLY_TOOLS
    try:
        registry = module.load_registry()
        tools = [
            item["tool"]
            for item in module.mcp_projection(registry)
            if item.get("read_only") is True and item.get("requires_approval") is False
        ]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return DEFAULT_READ_ONLY_TOOLS
    return tuple(tool for tool in tools if tool in DEFAULT_READ_ONLY_TOOLS) or DEFAULT_READ_ONLY_TOOLS


READ_ONLY_TOOLS = registry_read_only_tools()


def script(name: str) -> Path:
    return ROOT / "scripts" / name


def json_schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


def tool_definitions() -> dict[str, dict[str, Any]]:
    return {
        "navigator_plan": {
            "name": "navigator_plan",
            "description": "Return a TailTrail Navigator plan. Read-only; does not implement, scan, or edit files.",
            "inputSchema": json_schema(
                {
                    "goal": {"type": "string"},
                    "root": {"type": "string"},
                    "changed": {"type": "array", "items": {"type": "string"}},
                    "format": {"type": "string", "enum": ["json", "markdown"]},
                },
                ["goal"],
            ),
        },
        "start_report": {
            "name": "start_report",
            "description": "Return a compact TailTrail Start report. Read-only; does not edit files or capture learnings.",
            "inputSchema": json_schema(
                {
                    "goal": {"type": "string"},
                    "root": {"type": "string"},
                    "changed": {"type": "array", "items": {"type": "string"}},
                    "verbose": {"type": "boolean"},
                    "format": {"type": "string", "enum": ["json", "markdown"]},
                },
                ["goal"],
            ),
        },
        "guardrail_check": {
            "name": "guardrail_check",
            "description": "Run the deterministic guardrail checker on a supplied diff or safe staged diff. Read-only.",
            "inputSchema": json_schema(
                {
                    "root": {"type": "string"},
                    "diff": {"type": "string"},
                    "fail_on": {"type": "array", "items": {"type": "string"}},
                    "enforce": {"type": "boolean"},
                    "format": {"type": "string", "enum": ["json", "markdown"]},
                }
            ),
        },
        "graph_map": {
            "name": "graph_map",
            "description": "Return Code Review Graph Lite read-order guidance. Read-only; does not refresh heavy graph caches.",
            "inputSchema": json_schema(
                {
                    "root": {"type": "string"},
                    "changed": {"type": "array", "items": {"type": "string"}},
                    "format": {"type": "string", "enum": ["json", "markdown"]},
                }
            ),
        },
        "install_status": {
            "name": "install_status",
            "description": "Read TailTrail install manifest state and report Core/Extended/unknown status.",
            "inputSchema": json_schema({"root": {"type": "string"}}),
        },
        "eval_scenario_list": {
            "name": "eval_scenario_list",
            "description": "List committed Evaluation Harness scenarios. Read-only; does not run live agents, scanners, tests, or write reports.",
            "inputSchema": json_schema({"format": {"type": "string", "enum": ["json", "markdown"]}}),
        },
        "eval_scenario_report": {
            "name": "eval_scenario_report",
            "description": "Return a deterministic Evaluation Harness scenario report from committed fixtures. Read-only; does not write result files.",
            "inputSchema": json_schema(
                {
                    "scenario": {"type": "string"},
                    "format": {"type": "string", "enum": ["json", "markdown"]},
                },
                ["scenario"],
            ),
        },
    }


def tool_list() -> list[dict[str, Any]]:
    return [tool_definitions()[name] for name in READ_ONLY_TOOLS]


def ensure_safe_tools() -> list[str]:
    errors: list[str] = []
    definitions = tool_definitions()
    if tuple(definitions) != READ_ONLY_TOOLS:
        errors.append("tool registry order does not match READ_ONLY_TOOLS")
    for name in definitions:
        if name != "install_status" and any(term in name for term in DENIED_TOOL_TERMS):
            errors.append(f"tool name is not read-only: {name}")
    for name in READ_ONLY_TOOLS:
        schema = definitions[name].get("inputSchema")
        if not isinstance(schema, dict) or schema.get("type") != "object":
            errors.append(f"{name}: inputSchema must be an object schema")
    return errors


def root_from(args: dict[str, Any]) -> Path:
    value = args.get("root")
    if isinstance(value, str) and value:
        return Path(value).expanduser().resolve()
    return Path.cwd().resolve()


def as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def output_format(args: dict[str, Any]) -> str:
    value = args.get("format")
    return value if value in {"json", "markdown"} else "json"


def command_result(command: list[str], cwd: Path) -> dict[str, Any]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    return {
        "command": command,
        "cwd": cwd.as_posix(),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "read_only": True,
    }


def parse_stdout(result: dict[str, Any], fmt: str) -> Any:
    if fmt != "json":
        return result["stdout"]
    try:
        return json.loads(result["stdout"])
    except json.JSONDecodeError:
        return result["stdout"]


def navigator_plan(args: dict[str, Any]) -> dict[str, Any]:
    goal = str(args.get("goal", "")).strip()
    if not goal:
        raise ValueError("goal is required")
    root = root_from(args)
    fmt = output_format(args)
    command = [PYTHON, script("navigator.py").as_posix(), goal, "--root", root.as_posix(), "--format", fmt]
    for item in as_string_list(args.get("changed")):
        command.extend(["--changed", item])
    result = command_result(command, root)
    return {"tool": "navigator_plan", "result": parse_stdout(result, fmt), "execution": result}


def start_report(args: dict[str, Any]) -> dict[str, Any]:
    goal = str(args.get("goal", "")).strip()
    if not goal:
        raise ValueError("goal is required")
    root = root_from(args)
    fmt = output_format(args)
    command = [PYTHON, script("task-start.py").as_posix(), goal, "--root", root.as_posix(), "--format", fmt]
    for item in as_string_list(args.get("changed")):
        command.extend(["--changed", item])
    if bool(args.get("verbose")):
        command.append("--verbose")
    result = command_result(command, root)
    return {"tool": "start_report", "result": parse_stdout(result, fmt), "execution": result}


def guardrail_check(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args)
    fmt = output_format(args)
    command = [PYTHON, script("guardrail-check.py").as_posix(), "--root", root.as_posix(), "--format", fmt]
    diff_text = args.get("diff")
    temp_path: Path | None = None
    try:
        if isinstance(diff_text, str):
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".diff") as handle:
                handle.write(diff_text)
                temp_path = Path(handle.name)
            command.extend(["--diff", temp_path.as_posix()])
        elif not (root / ".git").exists():
            command.extend(["--diff", "/dev/null"])
        fail_on = as_string_list(args.get("fail_on"))
        if fail_on:
            command.extend(["--fail-on", ",".join(fail_on)])
        if bool(args.get("enforce")):
            command.append("--enforce")
        result = command_result(command, root)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return {"tool": "guardrail_check", "result": parse_stdout(result, fmt), "execution": result}


def graph_map(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args)
    fmt = output_format(args)
    command = [PYTHON, script("review-graph.py").as_posix(), "--root", root.as_posix(), "--format", fmt]
    for item in as_string_list(args.get("changed")):
        command.extend(["--changed", item])
    result = command_result(command, root)
    return {"tool": "graph_map", "result": parse_stdout(result, fmt), "execution": result}


def install_status(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args)
    manifest = root / ".tailtrail-install.json"
    nested = sorted(root.glob("*/.tailtrail-install.json"))
    path = manifest if manifest.exists() else nested[0] if nested else None
    if path is None:
        return {
            "tool": "install_status",
            "result": {
                "surface": "unknown",
                "manifest": None,
                "recommended_next": "python3 scripts/tailtrail.py install local --inspect",
            },
            "execution": {"read_only": True, "exit_code": 0},
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {
            "tool": "install_status",
            "result": {"surface": "unknown", "manifest": path.as_posix(), "error": str(error)},
            "execution": {"read_only": True, "exit_code": 1},
        }
    surface = data.get("surface") if isinstance(data, dict) else "unknown"
    return {
        "tool": "install_status",
        "result": {
            "surface": surface if isinstance(surface, str) else "unknown",
            "manifest": path.as_posix(),
            "pack_dir": data.get("pack_dir") if isinstance(data, dict) else None,
            "recommended_next": "python3 scripts/tailtrail.py install status --target .",
        },
        "execution": {"read_only": True, "exit_code": 0},
    }


def eval_scenario_list(args: dict[str, Any]) -> dict[str, Any]:
    fmt = output_format(args)
    command = [PYTHON, script("evaluation-harness.py").as_posix(), "scenario", "list", "--format", fmt]
    result = command_result(command, ROOT)
    return {"tool": "eval_scenario_list", "result": parse_stdout(result, fmt), "execution": result}


def eval_scenario_report(args: dict[str, Any]) -> dict[str, Any]:
    scenario = str(args.get("scenario", "")).strip()
    if not scenario:
        raise ValueError("scenario is required")
    fmt = output_format(args)
    command = [
        PYTHON,
        script("evaluation-harness.py").as_posix(),
        "scenario",
        "report",
        "--scenario",
        scenario,
        "--format",
        fmt,
    ]
    result = command_result(command, ROOT)
    return {"tool": "eval_scenario_report", "result": parse_stdout(result, fmt), "execution": result}


HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "navigator_plan": navigator_plan,
    "start_report": start_report,
    "guardrail_check": guardrail_check,
    "graph_map": graph_map,
    "install_status": install_status,
    "eval_scenario_list": eval_scenario_list,
    "eval_scenario_report": eval_scenario_report,
}


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    if name not in HANDLERS:
        raise ValueError(f"Unknown or disallowed MCP tool: {name}")
    return HANDLERS[name](arguments or {})


def mcp_content(value: Any) -> list[dict[str, str]]:
    return [{"type": "text", "text": json.dumps(value, indent=2, sort_keys=True)}]


def response(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")
    params = request.get("params") if isinstance(request.get("params"), dict) else {}
    try:
        if method == "initialize":
            return response(
                request_id,
                {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "tailtrail-mcp", "version": "1"},
                    "capabilities": {"tools": {}},
                },
            )
        if method == "tools/list":
            return response(request_id, {"tools": tool_list()})
        if method == "tools/call":
            name = str(params.get("name", ""))
            arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            value = call_tool(name, arguments)
            return response(request_id, {"content": mcp_content(value), "isError": False})
        if method == "notifications/initialized":
            return None
        return error_response(request_id, -32601, f"Unsupported method: {method}")
    except Exception as error:
        return error_response(request_id, -32000, str(error))


def serve() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as error:
            print(json.dumps(error_response(None, -32700, str(error))), flush=True)
            continue
        if not isinstance(request, dict):
            print(json.dumps(error_response(None, -32600, "request must be a JSON object")), flush=True)
            continue
        result = handle(request)
        if result is not None:
            print(json.dumps(result), flush=True)
    return 0


def render_tools() -> str:
    lines = ["# TailTrail MCP Tools", ""]
    for item in tool_list():
        lines.append(f"- `{item['name']}`: {item['description']}")
    return "\n".join(lines) + "\n"


def doctor() -> int:
    errors = ensure_safe_tools()
    if set(HANDLERS) != set(READ_ONLY_TOOLS):
        errors.append("handler registry does not match READ_ONLY_TOOLS")
    if errors:
        print("TailTrail MCP doctor failed.")
        for item in errors:
            print(f"- {item}")
        return 1
    print("TailTrail MCP doctor passed.")
    print(f"Tools: {', '.join(READ_ONLY_TOOLS)}")
    print("Mode: stdio, local, read-only")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run TailTrail's opt-in read-only MCP server.")
    parser.add_argument("action", choices=("serve", "tools", "doctor"))
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    if args.action == "serve":
        return serve()
    if args.action == "tools":
        if args.format == "json":
            print(json.dumps({"tools": tool_list(), "read_only": True}, indent=2, sort_keys=True))
        else:
            print(render_tools(), end="")
        return 0
    return doctor()


if __name__ == "__main__":
    raise SystemExit(main())
