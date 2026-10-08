#!/usr/bin/env python3
"""Maturity classification lookup for CLI commands and MCP tools, backed by
maturity-registry.json at the repository root.

Anything not listed in the registry defaults to "stable" -- the registry
only needs to record exceptions, so a newly-added command/tool is never
silently gated just because nobody remembered to classify it.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "maturity-registry.json"
DEFAULT_LEVEL = "stable"
LEVELS = ("stable", "incubating", "experimental")


@lru_cache(maxsize=1)
def _registry() -> dict[str, Any]:
    if not REGISTRY_PATH.is_file():
        return {"default_level": DEFAULT_LEVEL, "cli_commands": {}, "mcp_tools": {}}
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def cli_command_maturity(command: str, action: str | None = None) -> tuple[str, str | None]:
    """Return (level, reason) for a CLI command, checking the more specific
    "<command> <action>" key first, then the bare command name, then the
    registry's default level."""
    registry = _registry()
    commands = registry.get("cli_commands", {})
    default = registry.get("default_level", DEFAULT_LEVEL)
    if action is not None:
        entry = commands.get(f"{command} {action}")
        if entry:
            return entry.get("level", default), entry.get("reason")
    entry = commands.get(command)
    if entry:
        return entry.get("level", default), entry.get("reason")
    return default, None


def mcp_tool_maturity(tool_name: str) -> tuple[str, str | None]:
    registry = _registry()
    entry = registry.get("mcp_tools", {}).get(tool_name)
    default = registry.get("default_level", DEFAULT_LEVEL)
    if entry:
        return entry.get("level", default), entry.get("reason")
    return default, None


def is_gated(level: str) -> bool:
    return level in {"incubating", "experimental"}


def allow_flag_for(level: str) -> str:
    return "--allow-incubating" if level == "incubating" else "--allow-experimental"


def strip_allow_flags(args: list[str]) -> list[str]:
    """Remove --allow-incubating/--allow-experimental so downstream
    per-command argument parsers never see an option they don't know."""
    return [a for a in args if a not in {"--allow-incubating", "--allow-experimental"}]
