#!/usr/bin/env python3
"""Print the TailTrail ground rules for host agents and developers."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "TAILTRIAL-GROUND-RULES.md"


def show() -> dict[str, Any]:
    return {
        "schema_version": "1",
        "type": "tailtrail-ground-rules",
        "artifact": DOCUMENT.relative_to(ROOT).as_posix(),
        "content": DOCUMENT.read_text(encoding="utf-8"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Print the TailTrail ground rules.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()
    try:
        payload = show()
    except OSError as error:
        print(f"Ground rules error: {error}")
        return 2
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        # Byte output: Windows consoles (cp1252) cannot encode the
        # markdown arrows, and print() would crash there.
        sys.stdout.buffer.write(payload["content"].encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
