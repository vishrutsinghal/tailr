#!/usr/bin/env python3

from __future__ import annotations

# Thin CLI wrapper: keep as a pure import-and-call shim; see tests/test_cli_dispatch.py.
from token_budget_coach import main


if __name__ == "__main__":
    raise SystemExit(main())
