#!/usr/bin/env python3

from __future__ import annotations

import os
from pathlib import Path

# Explicit source-checkout compatibility. Installed execution resolves only
# package-owned resources and never scans cwd or parent directories.
os.environ.setdefault("TAILTRAIL_SOURCE_COMPAT_ROOT", Path(__file__).resolve().parent.as_posix())

from tailtrail.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
