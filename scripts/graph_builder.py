"""Explicit graph build pipeline (Phase 3 of docs/arch/code-graphing.md).

Commits an explicit AST graph by orchestrating the existing
``scripts/code-graph-mapper.py`` (reuse-first: the mapper already owns
AST extraction, gap-fill, hashing, and cache write). This module adds
what the mapper does not have:

- Passive cross-check: warmed files from the Phase 2 pending queue
  (falling back to Phase 1 cache files) drive the build scope when no
  explicit targets are given.
- Depth levels: shallow (import/reference structure only), medium
  (symbols + call chains — recommended for AIDLC metrics), deep
  (everything the mapper produced).
- Selective clear: built files are discarded from the passive pending
  queue; residual data for untouched files is preserved.
- Schema validation of the mapper payload before the cache write.

Never raises on mapper failure: returns a summary with errors so the
caller can report honestly.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import capture_hooks
import code_graph_cache

SHARED_CACHE = Path("tailtrail-meta") / "code-graph-cache.json"
LOCAL_CACHE = Path(".tailtrail") / "code-graph-cache.json"

DEPTHS = ("shallow", "medium", "deep")

# depth -> (graph_mode label, mapper limit)
_DEPTH_PROFILES = {
    "shallow": ("shallow-commit", 6),
    "medium": ("medium-commit", 12),
    "deep": ("deep-commit", 24),
}

_MAPPER: Any = None


def _mapper() -> Any:
    """Load scripts/code-graph-mapper.py by path (repo convention)."""
    global _MAPPER
    if _MAPPER is None:
        path = Path(__file__).resolve().parent / "code-graph-mapper.py"
        spec = importlib.util.spec_from_file_location("tailtrail_code_graph_mapper", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("code-graph-mapper.py could not be located")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _MAPPER = module
    return _MAPPER


def validate_payload(payload: Any) -> list[str]:
    """Minimal schema validation before the cache write."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload is not an object"]
    for key in ("schema_version", "root", "updated_at", "scope", "graph"):
        if key not in payload:
            errors.append(f"missing required field: {key}")
    graph = payload.get("graph")
    if not isinstance(graph, dict):
        errors.append("graph is not an object")
    elif "symbols" not in graph or "references" not in graph:
        errors.append("graph is missing symbols/references")
    return errors


def _apply_depth(payload: dict[str, Any], depth: str) -> None:
    """Post-filter the mapper payload to the requested depth level."""
    graph = payload.get("graph")
    if not isinstance(graph, dict):
        return
    if depth == "shallow":
        # Imports/reference structure only.
        for key in ("symbols", "call_chains", "type_hierarchy", "endpoints"):
            graph[key] = []
    elif depth == "medium":
        # Symbols + call chains + imports (AIDLC metrics target).
        for key in ("endpoints", "db_tables", "config_usage", "service_edges"):
            graph[key] = []


def commit_graph(
    root: Path | str,
    target_files: list[str] | None = None,
    depth: str = "medium",
    write_shared: bool = True,
    clear_passive: bool = True,
) -> dict[str, Any]:
    """Build and commit an explicit graph for the given scope.

    Scope resolution order: explicit ``target_files`` -> Phase 2 passive
    pending queue (warm cross-check) -> Phase 1 cache files. Raises
    ValueError only when no scope can be resolved at all.
    """
    if depth not in DEPTHS:
        raise ValueError(f"depth must be one of {DEPTHS}, got {depth!r}")

    root_path = Path(root).resolve()
    warmed = capture_hooks.pending(root_path)
    if not warmed and target_files is None:
        found = code_graph_cache.find_cache(root_path)
        if found is not None:
            container, _ = code_graph_cache.read_container(found)
            phase1 = container["phase1_files"]
            section_files = phase1.get("files", {}) if isinstance(phase1, dict) else {}
            warmed = sorted(section_files) if isinstance(section_files, dict) else []

    scope = [item for item in (target_files or warmed) if item]
    if not scope:
        raise ValueError("No scope to build: no target_files and nothing passively captured.")

    mode, limit = _DEPTH_PROFILES[depth]
    mapper = _mapper()
    previous, _ = load_graph(root_path, write_shared)
    payload = mapper.build_graph(root_path, scope, mode, [], limit, previous=previous)
    _apply_depth(payload, depth)

    errors = validate_payload(payload)
    if errors:
        return {"status": "invalid", "errors": errors, "cache_path": None, "built_files": [], "passive_cleared": 0, "passive_residual": len(capture_hooks.pending(root_path))}

    cache_rel = SHARED_CACHE if write_shared else LOCAL_CACHE
    cache_path = root_path / cache_rel
    mapper.write_cache(cache_path, payload)

    built_files = list(payload.get("scope", []))
    cleared = 0
    if clear_passive:
        cleared = capture_hooks.discard(root_path, built_files)

    residual = len(capture_hooks.pending(root_path))
    graph = payload.get("graph", {})
    return {
        "status": "committed",
        "depth": depth,
        "cache_path": cache_path.as_posix(),
        "built_files": built_files,
        "built_count": len(built_files),
        "symbols": len(graph.get("symbols", [])),
        "references": len(graph.get("references", [])),
        "call_chains": len(graph.get("call_chains", [])),
        "confidence": graph.get("confidence", "unknown"),
        "passive_cleared": cleared,
        "passive_residual": residual,
        "errors": [],
    }


def load_graph(root: Path | str, write_shared: bool = True) -> tuple[dict[str, Any] | None, str | None]:
    """Load the committed graph cache (same convention as the mapper)."""
    root_path = Path(root).resolve()
    cache_path = root_path / (SHARED_CACHE if write_shared else LOCAL_CACHE)
    return _mapper().load_cache(cache_path)


def _report(summary: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Explicit Graph Build",
        "",
        f"- Status: `{summary.get('status')}`",
        f"- Depth: `{summary.get('depth')}`",
        f"- Cache: `{summary.get('cache_path')}`",
        f"- Built files: `{summary.get('built_count')}`",
        f"- Symbols: `{summary.get('symbols')}`",
        f"- References: `{summary.get('references')}`",
        f"- Call chains: `{summary.get('call_chains')}`",
        f"- Confidence: `{summary.get('confidence')}`",
        f"- Passive cleared: `{summary.get('passive_cleared')}`",
        f"- Passive residual: `{summary.get('passive_residual')}`",
    ]
    for error in summary.get("errors", []):
        lines.append(f"- Error: {error}")
    for built in summary.get("built_files", [])[:20]:
        lines.append(f"- Built `{built}`")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="On-demand explicit code-graph build (Phase 3).")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument("--changed", action="append", default=[], help="Target file. Repeat for multiple files. Defaults to passively warmed scope.")
    parser.add_argument("--depth", choices=DEPTHS, default="medium", help="Build depth.")
    parser.add_argument("--local", action="store_true", help="Write the local cache instead of the shared one.")
    parser.add_argument("--no-clear-passive", action="store_true", help="Keep the passive pending queue.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = commit_graph(
            args.root,
            target_files=args.changed or None,
            depth=args.depth,
            write_shared=not args.local,
            clear_passive=not args.no_clear_passive,
        )
    except ValueError as error:
        print(json.dumps({"status": "no-scope", "errors": [str(error)]}))
        return 2
    if args.format == "json":
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(_report(summary), end="")
    return 0 if summary["status"] == "committed" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

