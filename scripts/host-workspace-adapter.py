#!/usr/bin/env python3
"""Resolve a declared Codex, Copilot, or Claude workspace safely.

This TW-4 adapter is local-only. Hosts may supply a workspace path, but
TailTrail never infers hidden host state or maps an unavailable container/WSL
path by guesswork. The resolved path is advisory input to Target Workspace
Resolution; explicit --root remains the highest-precedence target choice.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


HOSTS = {"codex", "copilot", "claude"}
PLATFORMS = {"auto", "windows", "macos", "linux", "wsl", "container"}


def current_platform() -> str:
    if os.name == "nt":
        return "windows"
    release = os.uname().release.lower() if hasattr(os, "uname") else ""
    if "microsoft" in release:
        return "wsl"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def classify_workspace(raw: str, declared_platform: str) -> str:
    if raw.startswith("\\\\") or raw.startswith("//"):
        return "network-share"
    if re.match(r"^/mnt/[a-zA-Z](?:/|$)", raw):
        return "wsl"
    if raw.startswith("/workspace/") or raw.startswith("/workspaces/"):
        return "container"
    if re.match(r"^[A-Za-z]:[\\/]", raw):
        return "windows"
    if raw.startswith("/Users/"):
        return "macos"
    return declared_platform if declared_platform != "auto" else current_platform()


def mapped_path(raw: str, workspace_kind: str, local_platform: str) -> tuple[Path | None, str]:
    if workspace_kind == "wsl" and local_platform == "windows":
        match = re.match(r"^/mnt/([a-zA-Z])(?:/(.*))?$", raw)
        if match:
            suffix = match.group(2) or ""
            return Path(f"{match.group(1).upper()}:/{suffix}"), "wsl-to-windows"
    if workspace_kind == "container" and local_platform != "container":
        return None, "container-unmapped"
    return Path(raw).expanduser(), "native" if workspace_kind != "network-share" else "network-share"


def resolve(host: str, workspace: str | None, *, host_platform: str = "auto", local_platform: str | None = None) -> dict[str, Any]:
    if host not in HOSTS:
        raise ValueError("host must be codex, copilot, or claude")
    if host_platform not in PLATFORMS:
        raise ValueError("host-platform must be auto, windows, macos, linux, wsl, or container")
    local = local_platform or current_platform()
    if not workspace:
        return {
            "schema_version": "1", "type": "tailtrail-host-workspace-resolution", "host": host,
            "host_platform": host_platform, "local_platform": local, "status": "not-provided",
            "source": "host-adapter", "boundary": "No host workspace was supplied; Target Workspace Resolver may use explicit --root, prompt target, or host CWD precedence.",
        }
    kind = classify_workspace(workspace, host_platform)
    candidate, mapping = mapped_path(workspace, kind, local)
    if candidate is None:
        return {
            "schema_version": "1", "type": "tailtrail-host-workspace-resolution", "host": host,
            "host_platform": host_platform, "local_platform": local, "workspace_kind": kind,
            "status": "unmapped", "source": "host-adapter", "mapping": mapping,
            "requested": workspace,
            "boundary": "The host workspace is a container path that is not mapped on this local host; open/select the target or pass an accessible --root.",
        }
    resolved = candidate.resolve()
    return {
        "schema_version": "1", "type": "tailtrail-host-workspace-resolution", "host": host,
        "host_platform": host_platform, "local_platform": local, "workspace_kind": kind,
        "status": "verified" if resolved.is_dir() else "inaccessible", "source": "host-adapter",
        "mapping": mapping, "requested": workspace, "root": resolved.as_posix(),
        "boundary": "Adapter-provided workspace identity is local metadata only. It does not grant writes, inspect source, or override an explicit --root.",
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = ["# TailTrail Host Workspace", "", f"- Host: `{payload['host']}`", f"- Status: **{payload['status']}**", f"- Source: `{payload['source']}`"]
    for key, label in (("host_platform", "Host platform"), ("local_platform", "Local platform"), ("workspace_kind", "Workspace kind"), ("mapping", "Mapping"), ("root", "Resolved root")):
        if payload.get(key) is not None:
            lines.append(f"- {label}: `{payload[key]}`")
    lines.append(f"- Boundary: {payload['boundary']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, choices=sorted(HOSTS))
    parser.add_argument("--workspace")
    parser.add_argument("--host-platform", choices=sorted(PLATFORMS), default="auto")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    try:
        payload = resolve(args.host, args.workspace, host_platform=args.host_platform)
    except ValueError as error:
        parser.error(str(error))
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(markdown(payload), end="")
    return 0 if payload["status"] in {"verified", "not-provided"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
