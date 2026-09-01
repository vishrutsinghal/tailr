#!/usr/bin/env python3
"""Show the package-owned trusted release channel without network inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=("info",), default="info")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    payload = json.loads((ROOT / "release-channel-v1.json").read_text(encoding="utf-8"))
    release = json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))
    if payload.get("current_source_version") != release.get("product", {}).get("version"):
        print("TailTrail release metadata is inconsistent; release channel version does not match the release manifest.")
        return 3
    version = payload["current_source_version"]
    artifact = payload["artifact"].format(version=version)
    result = {**payload, "resolved_artifact": artifact, "commands": {key: value.format(artifact=artifact, version=version) for key, value in payload["verification"].items() if key in {"identity", "install"}}}
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("TailTrail trusted release channel")
        print(f"Repository: {result['repository']}")
        print(f"Latest release: {result['latest_release']}")
        print(f"Expected artifact: {artifact}")
        print(f"Identity verification: {result['commands']['identity']}")
        print(f"Installation: {result['commands']['install']}")
        print(f"Boundary: {result['boundary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
