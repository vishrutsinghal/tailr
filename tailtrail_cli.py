#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


def find_root() -> Path:
    override = os.environ.get("TAILTRAIL_ROOT")
    candidates = [Path(override).expanduser()] if override else []
    candidates.extend([Path(__file__).resolve(), Path.cwd().resolve()])
    for candidate in candidates:
        for root in [candidate if candidate.is_dir() else candidate.parent, *candidate.parents]:
            if (root / "scripts" / "tailtrail.py").is_file():
                return root
    raise SystemExit("TailTrail source tree not found. Run from the checkout or set TAILTRAIL_ROOT.")


def main() -> int:
    root = find_root()
    script = root / "scripts" / "tailtrail.py"
    os.environ["TAILTRAIL_COMMAND_NAME"] = "tailtrail"
    sys.argv = [script.as_posix(), *sys.argv[1:]]
    spec = importlib.util.spec_from_file_location("tailtrail_source_dispatcher", script)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return int(module.main())


if __name__ == "__main__":
    raise SystemExit(main())
