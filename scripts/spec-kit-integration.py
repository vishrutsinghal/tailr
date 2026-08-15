#!/usr/bin/env python3
"""Thin controlled bridge for Spec Kit CI receipt ingestion."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def module() -> Any:
    spec = importlib.util.spec_from_file_location("spec_kit_ci_ingest", ROOT / "scripts" / "ci-evidence-ingest.py")
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("ci-ingest", nargs="?")
    parser.add_argument("--root", type=Path, default=Path.cwd()); parser.add_argument("--run-id", required=True); parser.add_argument("--input", type=Path, required=True); parser.add_argument("--approved", action="store_true")
    args = parser.parse_args()
    try:
        if not args.approved: raise ValueError("Spec Kit CI receipt ingestion requires --approved")
        result = module().ingest(args.root.resolve(), args.run_id, args.input)
        print(json.dumps({"type": "tailtrail-spec-kit-ci-ingestion", "run_id": args.run_id, "result": result, "boundary": "Supplied CI receipt only; no CI network request or source modification was performed."}, indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Spec Kit CI integration error: {error}"); return 2


if __name__ == "__main__": raise SystemExit(main())
