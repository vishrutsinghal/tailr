"""Re-export of the canonical platform-aware shell quoter.

The implementation lives in `scripts/shell_quote.py` (single source of
truth, reusable by product code); this module keeps the `tests.proc_quote`
import path stable for existing tests.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_quote():
    spec = importlib.util.spec_from_file_location(
        "tailtrail_shell_quote",
        Path(__file__).resolve().parents[1] / "scripts" / "shell_quote.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.quote


quote = _load_quote()
