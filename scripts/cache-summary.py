#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_CACHE = Path("tailtrail-meta") / "code-graph-cache.json"
LOCAL_FALLBACK_CACHE = Path(".tailtrail") / "code-graph-cache.json"


def load(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid cache JSON: {error}") from error
    if not isinstance(value, dict):
        raise SystemExit("Cache root must be a JSON object.")
    return value


def summarize(cache: dict[str, Any] | None, limit: int, path: Path) -> dict[str, Any]:
    if cache is None:
        return {
            "type": "code-graph-cache-summary",
            "status": "missing",
            "cache_path": path.as_posix(),
            "schema_version": "unknown",
            "created_at": "unknown",
            "updated_at": "unknown",
            "root": "unknown",
            "mode": "unknown",
            "scope": [],
            "confidence": "unknown",
            "language_profiles": {},
            "counts": {},
            "risk_tags": [],
            "suggested_read_order": [],
            "likely_tests": [],
            "likely_callers": [],
            "freshness": {"status": "missing", "reasons": ["No Code Graph Mapper cache exists."]},
            "boundary": "Run `python3 scripts/tailtrail.py graph map --changed path/to/file` before cache-summary.",
        }
    graph = cache.get("graph", {}) if isinstance(cache.get("graph"), dict) else {}
    return {
        "type": "code-graph-cache-summary",
        "status": "available",
        "cache_path": path.as_posix(),
        "schema_version": cache.get("schema_version", "unknown"),
        "created_at": cache.get("created_at", "unknown"),
        "updated_at": cache.get("updated_at", "unknown"),
        "root": cache.get("root", "unknown"),
        "mode": cache.get("graph_mode", "unknown"),
        "scope": cache.get("scope", []),
        "confidence": graph.get("confidence", "unknown"),
        "language_profiles": cache.get("language_profiles", {}),
        "counts": {
            "symbols": len(graph.get("symbols", [])),
            "references": len(graph.get("references", [])),
            "call_chains": len(graph.get("call_chains", [])),
            "type_hierarchy": len(graph.get("type_hierarchy", [])),
            "endpoints": len(graph.get("endpoints", [])),
            "db_tables": len(graph.get("db_tables", [])),
            "config_usage": len(graph.get("config_usage", [])),
            "likely_callers": len(graph.get("likely_callers", [])),
            "likely_tests": len(graph.get("likely_tests", [])),
        },
        "risk_tags": graph.get("risk_tags", []),
        "suggested_read_order": graph.get("suggested_read_order", [])[:limit],
        "likely_tests": graph.get("likely_tests", [])[:limit],
        "likely_callers": graph.get("likely_callers", [])[:limit],
        "freshness": cache.get("freshness", {}),
        "boundary": "Cache summary is metadata only. Read exact source before editing.",
    }


def resolve_cache(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        return requested if requested.is_absolute() else root / requested
    shared = root / DEFAULT_CACHE
    if shared.exists():
        return shared
    return root / LOCAL_FALLBACK_CACHE


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Cache Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Cache path: `{report['cache_path']}`",
        f"- Root: `{report['root']}`",
        f"- Mode: `{report['mode']}`",
        f"- Confidence: `{report['confidence']}`",
        f"- Schema: `{report['schema_version']}`",
        "",
        "## Scope",
        "",
    ]
    lines.extend(f"- `{item}`" for item in report["scope"] or ["none"])
    lines.extend(["", "## Counts", ""])
    if report["counts"]:
        lines.extend(f"- {key.replace('_', ' ')}: `{value}`" for key, value in report["counts"].items())
    else:
        lines.append("- none")
    lines.extend(["", "## Risk Tags", ""])
    lines.extend(f"- `{item}`" for item in report["risk_tags"] or ["none"])
    lines.extend(["", "## Suggested Read Order", ""])
    lines.extend(f"- `{item}`" for item in report["suggested_read_order"] or ["none"])
    lines.extend(["", "## Likely Tests", ""])
    lines.extend(f"- `{item}`" for item in report["likely_tests"] or ["none"])
    lines.extend(["", "## Likely Callers", ""])
    lines.extend(f"- `{item}`" for item in report["likely_callers"] or ["none"])
    lines.extend(["", "## Boundary", "", f"- {report['boundary']}"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize a TailTrail Code Graph Mapper cache.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--cache", type=Path, default=None)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()
    cache_path = resolve_cache(args.root.resolve(), args.cache)
    report = summarize(load(cache_path), max(args.limit, 1), cache_path)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
