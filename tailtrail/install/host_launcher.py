#!/usr/bin/env python3
"""Stable per-host launcher for a versioned shared Extended payload."""

from __future__ import annotations

import json
import os
import runpy
import sys
from pathlib import Path


def main() -> int:
    launcher = Path(__file__).resolve()
    host = launcher.parents[1].name
    install_root = launcher.parents[3]
    manifest_path = install_root / "manifests" / f"{host}.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        version = str(manifest["version"])
    except (OSError, KeyError, json.JSONDecodeError) as error:
        print(f"TailTrail unavailable: cannot resolve the {host} installed payload: {error}", file=sys.stderr)
        return 69
    shared_root = install_root / "payload" / "common" / version
    entry = shared_root / "scripts" / "tailtrail.py"
    if not entry.is_file():
        print(f"TailTrail unavailable: shared payload is missing: {entry}", file=sys.stderr)
        return 69
    os.environ["TAILTRAIL_SOURCE_COMPAT_ROOT"] = shared_root.as_posix()
    os.environ.setdefault("TAILTRAIL_COMMAND_NAME", f"python3 {launcher.as_posix()}")
    if shared_root.as_posix() not in sys.path:
        sys.path.insert(0, shared_root.as_posix())
    try:
        runpy.run_path(entry.as_posix(), run_name="__main__")
    except SystemExit as error:
        return int(error.code or 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
