#!/usr/bin/env python3
"""CLI wrapper for TailTrail's verified upgrade orchestrator."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
IMPORT_ROOT = ROOT.parent if (ROOT / "__init__.py").is_file() else ROOT
sys.path.insert(0, IMPORT_ROOT.as_posix())

from tailtrail.upgrade import main


if __name__ == "__main__":
    raise SystemExit(main())
