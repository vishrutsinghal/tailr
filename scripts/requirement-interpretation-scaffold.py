#!/usr/bin/env python3
"""Scaffold first-try requirement-interpretation drafts from a goal string.

Thin discoverable entry point; all logic lives in
requirement-interpretation-draft.py so the scaffold rules exist exactly
once. This command never writes state, creates runs, or touches the
network.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


def _load() -> Any:
    path = Path(__file__).resolve().with_name("requirement-interpretation-draft.py")
    spec = importlib.util.spec_from_file_location("tailtrail_interpretation_draft", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    return _load().main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
