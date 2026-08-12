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
    "ledger_state",
    "anchor_show",
    "harness_checkpoint_show",
    "completion_feedback_show",
    "profile_view",
    "validation_receipt_show",
    "release_confidence_show",
    "git_readiness",
    "recovery_boundary_show",
    "recovery_reconciliation_show",
    "architecture_assessment_show",
    "maintainability_assessment_show",
    "context_continuity_show",
    "context_continuity_render",
    "context_continuity_advisory_show",
    "completion_report_show",
    "workflow_dashboard_show",
    "planning_lock_show",
    "aidlc_official_status",
    "aidlc_official_bridge_show",
    "aidlc_official_state_show",
    "aidlc_official_sanitize_validate",
    "aidlc_official_session_status",
    "host_conformance_report",
    "enterprise_target_policy_inspect",
)
CONTROLLED_TOOLS = ("harness_control_check", "source_patch_apply", "planning_lock_start", "planning_lock_approve", "tailtrail_start")
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
    return DEFAULT_READ_ONLY_TOOLS


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
        "ledger_state": {"name": "ledger_state", "description": "Read the append-only local run projection. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "anchor_show": {"name": "anchor_show", "description": "Read an approved local change-intent anchor. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "harness_checkpoint_show": {"name": "harness_checkpoint_show", "description": "Read the latest or named requirement checkpoint. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "checkpoint": {"type": "integer", "minimum": 1}}, ["run_id"])},
        "completion_feedback_show": {"name": "completion_feedback_show", "description": "Read the latest completion review and bounded feedback packet. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "profile_view": {"name": "profile_view", "description": "Validate and display a repository testing profile. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "profile": {"type": "string"}}, ["profile"])},
        "validation_receipt_show": {"name": "validation_receipt_show", "description": "Read a requirement-linked validation receipt by filename. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "receipt": {"type": "string"}}, ["run_id", "receipt"])},
        "release_confidence_show": {"name": "release_confidence_show", "description": "Read the latest tier-labelled release confidence assessment. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "git_readiness": {"name": "git_readiness", "description": "Return the read-only Mode A Git readiness report.", "inputSchema": json_schema({"root": {"type": "string"}})},
        "recovery_boundary_show": {"name": "recovery_boundary_show", "description": "Read the Mode A task recovery boundary. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "recovery_reconciliation_show": {"name": "recovery_reconciliation_show", "description": "Read the latest task recovery conflict classification. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "architecture_assessment_show": {"name": "architecture_assessment_show", "description": "Read the latest Architecture Fitness assessment. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "maintainability_assessment_show": {"name": "maintainability_assessment_show", "description": "Read the latest Maintainability Harness assessment. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "context_continuity_show": {"name": "context_continuity_show", "description": "Read a saved Context Continuity V1 state and packet. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "sequence": {"type": "integer", "minimum": 1}}, ["run_id"])},
        "context_continuity_render": {"name": "context_continuity_render", "description": "Preview a deterministic Context Continuity V1/V2 packet without writing state, editing source, running tests, or calling a model. An optional repository-relative policy can add template guidance only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "requirement_uid": {"type": "string"}, "trigger": {"type": "string"}, "policy": {"type": "string"}}, ["run_id"])},
        "context_continuity_advisory_show": {"name": "context_continuity_advisory_show", "description": "Read a saved Context Continuity V3 advisory validation record. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "sequence": {"type": "integer", "minimum": 1}}, ["run_id"])},
        "completion_report_show": {"name": "completion_report_show", "description": "Read a saved end-of-task TailTrail Completion Report. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "sequence": {"type": "integer", "minimum": 1}}, ["run_id"])},
        "workflow_dashboard_show": {"name": "workflow_dashboard_show", "description": "Read the current local TailTrail requirement, checkpoint, drift, evidence, and recovery dashboard. Read-only.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "planning_lock_show": {"name": "planning_lock_show", "description": "Read one TailTrail Planning Lock. Read-only; reports whether managed writes are still blocked or approved.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "aidlc_official_status": {"name": "aidlc_official_status", "description": "Read and validate a pinned official AWS AI-DLC pack manifest. Read-only; it never installs, attaches, or executes the pack.", "inputSchema": json_schema({"root": {"type": "string"}, "manifest": {"type": "string"}})},
        "aidlc_official_bridge_show": {"name": "aidlc_official_bridge_show", "description": "Read a saved official AI-DLC bridge identity for one TailTrail run. Read-only; Phase B never attaches or executes the official engine.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "aidlc_official_state_show": {"name": "aidlc_official_state_show", "description": "Project canonical run state and report ownership conflicts. Read-only; it never reconciles or rewrites artifacts.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "aidlc_official_sanitize_validate": {"name": "aidlc_official_sanitize_validate", "description": "Validate one repository-local official AI-DLC artifact against the fail-closed sensitive-data boundary. Read-only; rejected values are never returned.", "inputSchema": json_schema({"root": {"type": "string"}, "input": {"type": "string"}, "context": {"type": "string", "enum": ["bridge", "activation", "requirements", "requirements-revision", "checkpoint", "closure", "learning", "evaluation", "runtime-session", "runtime-transition"]}}, ["input", "context"])},
        "aidlc_official_session_status": {"name": "aidlc_official_session_status", "description": "Read the verified official AI-DLC runtime attachment and ordered transition projection. Read-only; it never attaches, imports receipts, or executes the pack.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}}, ["run_id"])},
        "host_conformance_report": {"name": "host_conformance_report", "description": "Report instruction and real-host runtime conformance separately for Codex, Copilot, or Claude. Read-only; missing receipts remain not-validated.", "inputSchema": json_schema({"root": {"type": "string"}, "host": {"type": "string", "enum": ["codex", "copilot", "claude"]}})},
        "enterprise_target_policy_inspect": {"name": "enterprise_target_policy_inspect", "description": "Evaluate a repository-local enterprise target policy against one selected root. Read-only; it never creates a Planning Lock, edits source, or writes an audit receipt.", "inputSchema": json_schema({"root": {"type": "string"}, "policy": {"type": "string"}, "actor": {"type": "string"}, "target_alias": {"type": "string"}}, ["policy"])},
        "harness_control_check": {"name": "harness_control_check", "description": "Run only the supplied repository-native control list after explicit approval and an approved matching Planning Lock. It cannot edit source or run an arbitrary command.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "controls": {"type": "string"}, "changed": {"type": "array", "items": {"type": "string"}}, "approved": {"type": "boolean"}}, ["run_id", "controls", "approved"])},
        "source_patch_apply": {"name": "source_patch_apply", "description": "Apply one supplied unified patch only after explicit approval and an approved matching Planning Lock. Validates patch paths stay inside the repository; never commits, pushes, or runs arbitrary commands.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "patch": {"type": "string"}, "approved": {"type": "boolean"}}, ["run_id", "patch", "approved"])},
        "planning_lock_start": {"name": "planning_lock_start", "description": "Create an awaiting-approval Planning Lock after the user explicitly asks to start TailTrail. Writes only TailTrail local metadata; it never edits project source or runs project commands.", "inputSchema": json_schema({"goal": {"type": "string"}, "root": {"type": "string"}, "run_id": {"type": "string"}, "reference_roots": {"type": "array", "items": {"type": "string"}}, "approved": {"type": "boolean"}}, ["goal", "approved"])},
        "planning_lock_approve": {"name": "planning_lock_approve", "description": "Explicitly approve one existing Planning Lock run for managed execution. For a saved TailTrail Start report, it also activates that exact plan's canonical requirement anchor. It never edits project source or runs project commands.", "inputSchema": json_schema({"root": {"type": "string"}, "run_id": {"type": "string"}, "approved": {"type": "boolean"}}, ["run_id", "approved"])},
        "tailtrail_start": {"name": "tailtrail_start", "description": "Atomically create a Planning Lock and return the full TailTrail Start Report. Use only after the user explicitly asks to start TailTrail. It writes TailTrail local metadata only; it never implements, edits project source, runs project commands, scanners, tests, Terraform, or Git mutations.", "inputSchema": json_schema({"goal": {"type": "string"}, "root": {"type": "string"}, "changed": {"type": "array", "items": {"type": "string"}}, "run_id": {"type": "string"}, "reference_roots": {"type": "array", "items": {"type": "string"}}, "aidlc": {"type": "string", "enum": ["lite", "standard", "medium", "full", "off"]}, "official_aidlc_manifest": {"type": "string"}, "official_intent_id": {"type": "string"}, "official_session_id": {"type": "string"}, "official_stage": {"type": "string", "enum": ["requirements", "design", "implementation", "build-and-test", "handoff", "operations"]}, "verbose": {"type": "boolean"}, "format": {"type": "string", "enum": ["json", "markdown"]}, "approved": {"type": "boolean"}}, ["goal", "approved"])},
    }


def tool_list() -> list[dict[str, Any]]:
    return [tool_definitions()[name] for name in (*READ_ONLY_TOOLS, *CONTROLLED_TOOLS)]


def ensure_safe_tools() -> list[str]:
    errors: list[str] = []
    definitions = tool_definitions()
    expected_order = (*READ_ONLY_TOOLS, *CONTROLLED_TOOLS)
    actual_order = tuple(definitions)
    if actual_order != expected_order:
        index = next(
            (index for index, (actual, expected) in enumerate(zip(actual_order, expected_order)) if actual != expected),
            min(len(actual_order), len(expected_order)),
        )
        expected_name = expected_order[index] if index < len(expected_order) else "<none>"
        actual_name = actual_order[index] if index < len(actual_order) else "<none>"
        errors.append(
            "tool registry order mismatch at index "
            f"{index}: expected `{expected_name}`, got `{actual_name}`"
        )
    for name in definitions:
        if name not in (*CONTROLLED_TOOLS, "install_status") and any(term in name for term in DENIED_TOOL_TERMS):
            errors.append(f"tool name is not read-only: {name}")
    for name in (*READ_ONLY_TOOLS, *CONTROLLED_TOOLS):
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
    command = [PYTHON, script("task-start.py").as_posix(), goal, "--root", root.as_posix(), "--format", fmt, "--no-planning-lock"]
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


def run_id(args: dict[str, Any]) -> str:
    value = str(args.get("run_id", "")).strip()
    if not value or Path(value).name != value: raise ValueError("run_id must be a single local run identifier")
    return value


def require_approved_planning_lock(root: Path, identifier: str, action: str) -> None:
    result = command_result(
        [PYTHON, script("planning-lock.py").as_posix(), "assert-write", "--root", root.as_posix(), "--run-id", identifier],
        root,
    )
    if result["exit_code"] != 0:
        raise ValueError(f"{action} denied by Planning Lock; explicitly approve this exact run before managed execution")


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file(): raise ValueError(f"local artifact does not exist: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_artifact(root: Path, identifier: str, section: str, pattern: str) -> dict[str, Any] | None:
    directory = root / ".tailtrail" / "runs" / identifier / section
    matches = sorted(directory.glob(pattern))
    return read_json(matches[-1]) if matches else None


def ledger_state(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args)
    result = command_result([PYTHON, script("run-ledger.py").as_posix(), "state", "--root", root.as_posix(), "--run-id", identifier], root)
    return {"tool": "ledger_state", "result": parse_stdout(result, "json"), "execution": result}


def anchor_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args)
    return {"tool": "anchor_show", "result": read_json(root / ".tailtrail" / "runs" / identifier / "anchors" / "approved-v1.json"), "execution": {"read_only": True, "exit_code": 0}}


def harness_checkpoint_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args); number = args.get("checkpoint")
    path = root / ".tailtrail" / "runs" / identifier / "checkpoints" / (f"checkpoint-{number}.json" if isinstance(number, int) else "")
    result = read_json(path) if isinstance(number, int) else run_artifact(root, identifier, "checkpoints", "checkpoint-*.json")
    if result is None: raise ValueError("no checkpoint artifact exists")
    return {"tool": "harness_checkpoint_show", "result": result, "execution": {"read_only": True, "exit_code": 0}}


def completion_feedback_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args)
    return {"tool": "completion_feedback_show", "result": {"review": run_artifact(root, identifier, "reviews", "review-*.json"), "feedback": run_artifact(root, identifier, "feedback", "feedback-*.json")}, "execution": {"read_only": True, "exit_code": 0}}


def safe_relative(root: Path, value: Any) -> Path:
    path = Path(str(value))
    if path.is_absolute() or ".." in path.parts: raise ValueError("path must be repository-relative")
    resolved = (root / path).resolve()
    if root not in resolved.parents and resolved != root: raise ValueError("path is outside root")
    return resolved


def profile_view(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); profile = safe_relative(root, args.get("profile", ""))
    result = command_result([PYTHON, script("testing-profile.py").as_posix(), "validate", "--profile", profile.as_posix()], root)
    return {"tool": "profile_view", "result": parse_stdout(result, "json"), "execution": result}


def validation_receipt_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args); receipt = Path(str(args.get("receipt", "")))
    if receipt.name != str(receipt): raise ValueError("receipt must be one receipt filename")
    return {"tool": "validation_receipt_show", "result": read_json(root / ".tailtrail" / "runs" / identifier / "validation-receipts" / receipt), "execution": {"read_only": True, "exit_code": 0}}


def release_confidence_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args); result = run_artifact(root, identifier, "release-confidence", "assessment-*.json")
    if result is None: raise ValueError("no release confidence assessment artifact exists")
    return {"tool": "release_confidence_show", "result": result, "execution": {"read_only": True, "exit_code": 0}}


def git_readiness(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); result = command_result([PYTHON, script("git-readiness.py").as_posix(), "--root", root.as_posix()], root)
    return {"tool": "git_readiness", "result": parse_stdout(result, "json"), "execution": result}


def recovery_boundary_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args)
    return {"tool": "recovery_boundary_show", "result": read_json(root / ".tailtrail" / "runs" / identifier / "recovery" / "boundary.json"), "execution": {"read_only": True, "exit_code": 0}}


def recovery_reconciliation_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args); result = run_artifact(root, identifier, "recovery/reconciliation", "assessment-*.json")
    if result is None: raise ValueError("no recovery reconciliation artifact exists")
    return {"tool": "recovery_reconciliation_show", "result": result, "execution": {"read_only": True, "exit_code": 0}}


def architecture_assessment_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args); result = run_artifact(root, identifier, "architecture", "assessment-*.json")
    if result is None: raise ValueError("no architecture assessment artifact exists")
    return {"tool": "architecture_assessment_show", "result": result, "execution": {"read_only": True, "exit_code": 0}}


def maintainability_assessment_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args); result = run_artifact(root, identifier, "maintainability", "assessment-*.json")
    if result is None: raise ValueError("no maintainability assessment artifact exists")
    return {"tool": "maintainability_assessment_show", "result": result, "execution": {"read_only": True, "exit_code": 0}}


def harness_control_check(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("harness_control_check requires approved: true")
    root = root_from(args); identifier = run_id(args); controls = safe_relative(root, args.get("controls", ""))
    require_approved_planning_lock(root, identifier, "harness_control_check")
    if not controls.is_file(): raise ValueError("controls must name an existing repository control file")
    command = [PYTHON, script("harness-controls.py").as_posix(), "check", "--root", root.as_posix(), "--run-id", identifier, "--controls", controls.as_posix(), "--approved"]
    for item in as_string_list(args.get("changed")): command.extend(["--changed", item])
    result = command_result(command, root); result["read_only"] = False; result["requires_approval"] = True
    return {"tool": "harness_control_check", "result": parse_stdout(result, "json"), "execution": result}


def source_patch_apply(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True: raise ValueError("source_patch_apply requires approved: true")
    root = root_from(args); identifier = run_id(args); patch = str(args.get("patch", ""))
    require_approved_planning_lock(root, identifier, "source_patch_apply")
    if not patch.startswith("diff --git "): raise ValueError("patch must be a unified git diff")
    for line in patch.splitlines():
        if line.startswith(("+++ b/", "--- a/")):
            safe_relative(root, line[6:])
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".patch", dir=root, delete=False) as handle:
        handle.write(patch); patch_path = Path(handle.name)
    try:
        checked = command_result(["git", "apply", "--check", patch_path.as_posix()], root)
        if checked["exit_code"] != 0: raise ValueError("patch did not pass git apply --check")
        applied = command_result(["git", "apply", patch_path.as_posix()], root)
        if applied["exit_code"] != 0: raise ValueError("patch apply failed")
        return {"tool": "source_patch_apply", "result": {"applied": True}, "execution": applied, "read_only": False, "requires_approval": True}
    finally:
        patch_path.unlink(missing_ok=True)


def context_continuity_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("context_continuity_mcp", script("context-continuity.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return {"tool": "context_continuity_show", "result": module.show(root_from(args), run_id(args), args.get("sequence"))}


def planning_lock_show(args: dict[str, Any]) -> dict[str, Any]:
    root = root_from(args); identifier = run_id(args)
    result = command_result([PYTHON, script("planning-lock.py").as_posix(), "show", "--root", root.as_posix(), "--run-id", identifier], root)
    return {"tool": "planning_lock_show", "result": parse_stdout(result, "json"), "execution": result}


def aidlc_official_status(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("tailtrail_aidlc_official_detect", script("aidlc-official-detect.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load official AIDLC compatibility detector")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.status(root_from(args), args.get("manifest"))
    return {"tool": "aidlc_official_status", "result": result, "execution": {"read_only": True, "exit_code": 0}}


def aidlc_official_bridge_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("tailtrail_aidlc_official_bridge", script("aidlc-official-bridge.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load official AIDLC bridge")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {"tool": "aidlc_official_bridge_show", "result": module.show(root_from(args), run_id(args)), "execution": {"read_only": True, "exit_code": 0}}


def aidlc_official_state_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("aidlc_official_state_mcp", script("official-aidlc-state.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return {"tool": "aidlc_official_state_show", "result": module.project(root_from(args), run_id(args)), "execution": {"read_only": True, "exit_code": 0}}


def aidlc_official_sanitize_validate(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("aidlc_official_sanitize_mcp", script("official-aidlc-sanitize.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    root = root_from(args); path = safe_relative(root, args.get("input", ""))
    return {"tool": "aidlc_official_sanitize_validate", "result": module.validate_artifact(root, read_json(path), str(args.get("context", ""))), "execution": {"read_only": True, "exit_code": 0}}


def aidlc_official_session_status(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("aidlc_official_runtime_mcp", script("official-aidlc-runtime.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return {"tool": "aidlc_official_session_status", "result": module.status(root_from(args), run_id(args)), "execution": {"read_only": True, "exit_code": 0}}


def host_conformance_report(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("host_conformance_report_mcp", script("host-runtime-conformance.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return {"tool": "host_conformance_report", "result": module.report(root_from(args), args.get("host")), "execution": {"read_only": True, "exit_code": 0}}


def planning_lock_start(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True:
        raise ValueError("planning_lock_start requires approved: true after the user explicitly requests TailTrail Start")
    goal = str(args.get("goal", "")).strip()
    if not goal:
        raise ValueError("goal is required")
    root = root_from(args)
    command = [PYTHON, script("planning-lock.py").as_posix(), "start", "--root", root.as_posix(), "--goal", goal]
    run = str(args.get("run_id", "")).strip()
    if run:
        command.extend(["--run-id", run])
    for reference in as_string_list(args.get("reference_roots")):
        command.extend(["--reference-root", reference])
    result = command_result(command, root)
    result["read_only"] = False
    result["requires_approval"] = True
    result["local_metadata_only"] = True
    return {"tool": "planning_lock_start", "result": parse_stdout(result, "json"), "execution": result}


def planning_lock_approve(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("approved") is not True:
        raise ValueError("planning_lock_approve requires approved: true")
    root = root_from(args)
    identifier = run_id(args)
    action = "activate" if (root / ".tailtrail" / "runs" / identifier / "planning" / "start-report-v1.json").is_file() else "approve"
    result = command_result(
        [PYTHON, script("planning-lock.py").as_posix(), action, "--root", root.as_posix(), "--run-id", identifier, "--approved", "--format", "json"] if action == "activate" else [PYTHON, script("planning-lock.py").as_posix(), action, "--root", root.as_posix(), "--run-id", identifier, "--approved"],
        root,
    )
    result["read_only"] = False
    result["requires_approval"] = True
    result["local_metadata_only"] = True
    return {"tool": "planning_lock_approve", "result": parse_stdout(result, "json"), "execution": result}


def tailtrail_start(args: dict[str, Any]) -> dict[str, Any]:
    """Create one persisted planning run and its complete Start report together."""
    if args.get("approved") is not True:
        raise ValueError("tailtrail_start requires approved: true after the user explicitly requests TailTrail Start")
    goal = str(args.get("goal", "")).strip()
    if not goal:
        raise ValueError("goal is required")
    root = root_from(args)
    # Start is a user-facing Planning Lock. Markdown must be the default so a
    # host receives the complete report instead of a JSON object it may compress.
    fmt = output_format(args) if args.get("format") in {"json", "markdown"} else "markdown"
    command = [PYTHON, script("task-start.py").as_posix(), goal, "--root", root.as_posix(), "--format", fmt]
    run = str(args.get("run_id", "")).strip()
    if run:
        command.extend(["--planning-run-id", run])
    for item in as_string_list(args.get("changed")):
        command.extend(["--changed", item])
    for reference in as_string_list(args.get("reference_roots")):
        command.extend(["--reference-root", reference])
    if args.get("aidlc") in {"lite", "standard", "medium", "full", "off"}:
        command.extend(["--aidlc", str(args["aidlc"])])
    for argument, flag in (("official_aidlc_manifest", "--official-aidlc-manifest"), ("official_intent_id", "--official-intent-id"), ("official_session_id", "--official-session-id"), ("official_stage", "--official-stage")):
        if args.get(argument):
            command.extend([flag, str(args[argument])])
    if args.get("verbose") is True:
        command.append("--verbose")
    result = command_result(command, root)
    result["read_only"] = False
    result["requires_approval"] = True
    result["local_metadata_only"] = True
    result["execution_blocked"] = True
    return {"tool": "tailtrail_start", "result": parse_stdout(result, fmt), "execution": result}


def context_continuity_render(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("context_continuity_mcp", script("context-continuity.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    root = root_from(args)
    policy = module.load_policy(safe_relative(root, args["policy"])) if args.get("policy") else None
    result = module.packet_for(root, run_id(args), args.get("requirement_uid"), args.get("trigger"), 220, policy)
    return {"tool": "context_continuity_render", "result": result, "read_only": True}


def context_continuity_advisory_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("context_continuity_mcp", script("context-continuity.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return {"tool": "context_continuity_advisory_show", "result": module.advisory_show(root_from(args), run_id(args), args.get("sequence")), "read_only": True}


def completion_report_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("completion_report_mcp", script("completion-report.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return {"tool": "completion_report_show", "result": module.show(root_from(args), run_id(args), args.get("sequence")), "execution": {"read_only": True, "exit_code": 0}}


def workflow_dashboard_show(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("workflow_dashboard_mcp", script("workflow-dashboard.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return {"tool": "workflow_dashboard_show", "result": module.dashboard(root_from(args), run_id(args)), "execution": {"read_only": True, "exit_code": 0}}


def enterprise_target_policy_inspect(args: dict[str, Any]) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("enterprise_target_policy_mcp", script("enterprise-target-policy.py")); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    root = root_from(args)
    policy = module.load(safe_relative(root, args["policy"]))
    result = module.evaluate(root, policy, actor=args.get("actor"), selected_alias=args.get("target_alias"))
    return {"tool": "enterprise_target_policy_inspect", "result": result, "execution": {"read_only": True, "exit_code": 0}}


HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "navigator_plan": navigator_plan,
    "start_report": start_report,
    "guardrail_check": guardrail_check,
    "graph_map": graph_map,
    "install_status": install_status,
    "eval_scenario_list": eval_scenario_list,
    "eval_scenario_report": eval_scenario_report,
    "ledger_state": ledger_state, "anchor_show": anchor_show, "harness_checkpoint_show": harness_checkpoint_show,
    "completion_feedback_show": completion_feedback_show, "profile_view": profile_view,
    "validation_receipt_show": validation_receipt_show, "release_confidence_show": release_confidence_show, "git_readiness": git_readiness,
    "recovery_boundary_show": recovery_boundary_show, "recovery_reconciliation_show": recovery_reconciliation_show, "architecture_assessment_show": architecture_assessment_show,
    "maintainability_assessment_show": maintainability_assessment_show, "context_continuity_show": context_continuity_show, "context_continuity_render": context_continuity_render, "context_continuity_advisory_show": context_continuity_advisory_show, "completion_report_show": completion_report_show, "workflow_dashboard_show": workflow_dashboard_show, "planning_lock_show": planning_lock_show, "aidlc_official_status": aidlc_official_status, "aidlc_official_bridge_show": aidlc_official_bridge_show, "aidlc_official_state_show": aidlc_official_state_show, "aidlc_official_sanitize_validate": aidlc_official_sanitize_validate, "aidlc_official_session_status": aidlc_official_session_status, "host_conformance_report": host_conformance_report, "enterprise_target_policy_inspect": enterprise_target_policy_inspect, "harness_control_check": harness_control_check, "source_patch_apply": source_patch_apply, "planning_lock_start": planning_lock_start, "planning_lock_approve": planning_lock_approve, "tailtrail_start": tailtrail_start,
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
    if set(HANDLERS) != set((*READ_ONLY_TOOLS, *CONTROLLED_TOOLS)):
        errors.append("handler registry does not match the MCP tool allowlist")
    if errors:
        print("TailTrail MCP doctor failed.")
        for item in errors:
            print(f"- {item}")
        return 1
    print("TailTrail MCP doctor passed.")
    print(f"Read-only tools: {', '.join(READ_ONLY_TOOLS)}")
    print(f"Controlled tools: {', '.join(CONTROLLED_TOOLS)} (explicit approval required)")
    print("Mode: stdio, local, inspection-first")
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
            print(json.dumps({"tools": tool_list(), "read_only": list(READ_ONLY_TOOLS), "controlled": list(CONTROLLED_TOOLS)}, indent=2, sort_keys=True))
        else:
            print(render_tools(), end="")
        return 0
    return doctor()


if __name__ == "__main__":
    raise SystemExit(main())
