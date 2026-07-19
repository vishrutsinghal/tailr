#!/usr/bin/env python3

from __future__ import annotations

# Thin CLI wrapper: keep as a pure import-and-call shim; see tests/test_cli_dispatch.py.
from prompt_profile import main


if __name__ == "__main__":
    raise SystemExit(main())
