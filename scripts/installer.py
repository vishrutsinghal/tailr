#!/usr/bin/env python3
"""Compatibility entry point for the package-owned transactional installer."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
IMPORT_ROOT = ROOT.parent if (ROOT / "__init__.py").is_file() else ROOT
try:
    sys.path.remove(IMPORT_ROOT.as_posix())
except ValueError:
    pass
sys.path.insert(0, IMPORT_ROOT.as_posix())

from tailtrail.install.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
