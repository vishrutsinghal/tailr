#!/usr/bin/env python3
"""One common ground for Start requests across CLI, MCP-JSON, and MCP-markdown.

Every transport computes scope from the same normalized request through the
same argv builder, so identical requests cannot diverge by transport. A new
CLI knob flows through this module instead of needing per-transport mirrors.
Rendering (JSON vs Markdown) stays a pure view over identical data and never
enters any fingerprint.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

AIDLC_MODES = ("lite", "standard", "medium", "full", "off")
GRAPH_MODES = ("auto", "reuse", "refresh", "rebuild", "off")
HOSTS = ("codex", "copilot", "claude")
FORMATS = ("json", "markdown")


def normalize_start_request(
    goal: str,
    *,
    root: str | Path | None = None,
    changed: list[str] | tuple[str, ...] | None = None,
    aidlc: str | None = None,
    graph: str | None = None,
    host: str | None = None,
    verbose: bool = False,
    planning_lock: bool = True,
    output_format: str = "json",
) -> dict[str, Any]:
    """Validate and canonicalize one Start request. Raises ValueError."""
    clean_goal = " ".join(str(goal).split())
    if not clean_goal:
        raise ValueError("start request needs a non-empty goal")
    clean_changed = [str(item).replace("\\", "/").strip() for item in (changed or [])]
    clean_changed = [item for item in clean_changed if item]
    if aidlc is not None and aidlc not in AIDLC_MODES:
        raise ValueError(f"aidlc must be one of {', '.join(AIDLC_MODES)}")
    if graph is not None and graph not in GRAPH_MODES:
        raise ValueError(f"graph must be one of {', '.join(GRAPH_MODES)}")
    if host is not None and host not in HOSTS:
        raise ValueError(f"host must be one of {', '.join(HOSTS)}")
    if output_format not in FORMATS:
        raise ValueError(f"format must be one of {', '.join(FORMATS)}")
    return {
        "goal": clean_goal,
        "root": Path(root).expanduser().as_posix() if root else None,
        "changed": clean_changed,
        "aidlc": aidlc,
        "graph": graph,
        "host": host,
        "verbose": bool(verbose),
        "planning_lock": bool(planning_lock),
        "format": output_format,
    }


def start_argv(request: dict[str, Any], script: str = "task-start.py") -> list[str]:
    """Serialize a normalized request to task-start.py argv (script first).

    Only explicitly set knobs become flags, so two transports holding the
    same normalized request always spawn byte-identical commands.
    """
    if not isinstance(request, dict) or not request.get("goal"):
        raise ValueError("start_argv needs a normalized request with a goal")
    argv = [script, request["goal"]]
    if request.get("root"):
        argv.extend(["--root", str(request["root"])])
    for item in request.get("changed", []):
        argv.extend(["--changed", str(item)])
    if request.get("aidlc") is not None:
        argv.extend(["--aidlc", str(request["aidlc"])])
    if request.get("graph") is not None:
        argv.extend(["--graph", str(request["graph"])])
    if request.get("host") is not None:
        argv.extend(["--host", str(request["host"])])
    if request.get("verbose"):
        argv.append("--verbose")
    if not request.get("planning_lock", True):
        argv.append("--no-planning-lock")
    argv.extend(["--format", str(request.get("format", "json"))])
    return argv
