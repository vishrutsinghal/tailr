#!/usr/bin/env python3
"""Phase 1: Core code-graph cache infrastructure.

Central file-level cache every later code-graphing phase reads/writes::

    {"version": 1, "last_updated": "<iso>", "files": {rel: entry}}

``entry`` is ``{last_read, symbols, endpoints, imports, size_bytes}``.
File-level granularity only — no AST call graphs, no runtime behavior
(those are Phase 3+). See docs/arch/code-graphing.md §3.1.

Reuse-first: cheap symbol/import extraction delegates to the
dependency-free ``code_relationships.extract`` (text-only, never executes
project code). Persistence follows the repo convention (atomic write via
tempfile + os.replace, corrupt cache never crashes the caller).
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    import code_relationships
except ImportError:  # pragma: no cover - helper is optional
    code_relationships = None  # type: ignore[assignment]

VERSION = 1
SHARED_CACHE = Path("tailtrail-meta") / "code-graph-cache.json"
LOCAL_CACHE = Path(".tailtrail") / "code-graph-cache.json"

MAX_SYMBOLS = 200
MAX_IMPORTS = 100
MAX_ENDPOINTS = 50

_ROUTE_HINTS = (".get(", ".post(", ".put(", ".delete(", ".patch(", ".route(")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_cache() -> dict[str, Any]:
    return {"version": VERSION, "last_updated": None, "files": {}}


def _str_list(value: Any, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item and item not in out:
            out.append(item)
        if len(out) >= limit:
            break
    return out


def _is_mapper_shape(loaded: Any) -> bool:
    """Detect a mapper-shaped payload sharing this cache path (Stage 0a)."""
    if not isinstance(loaded, dict):
        return False
    if isinstance(loaded.get("files"), dict):
        return False
    return any(key in loaded for key in ("graph_mode", "schema_version", "graph", "scope", "source_files"))


CONTAINER_VERSION = 2

PHASE1_SECTION = "phase1_files"
MAPPER_SECTION = "mapper_graph"


def _is_phase1_shape(loaded: Any) -> bool:
    """Detect a Phase 1 files-shaped payload sharing this cache path (Stage 0b)."""
    if not isinstance(loaded, dict):
        return False
    if not isinstance(loaded.get("files"), dict):
        return False
    return not any(key in loaded for key in ("graph_mode", "schema_version", "graph", "scope", "source_files"))


def classify_cache_shape(loaded: Any) -> str:
    """Classify a parsed cache payload: combined | phase1 | mapper | invalid (Stage 0b)."""
    if isinstance(loaded, dict) and isinstance(loaded.get("sections"), dict):
        return "combined"
    if _is_phase1_shape(loaded):
        return "phase1"
    if _is_mapper_shape(loaded):
        return "mapper"
    return "invalid"


def read_container(path: Path | str) -> tuple[dict[str, Any], str | None]:
    """Unified v1/v2 reader (Stage 0b). Never raises.

    Returns ({"kind", "phase1_files", "mapper_graph", "warnings", "raw"}, error).
    ``error`` is None for every legible shape (warnings included); "missing" or
    "invalid: ..." otherwise. v1 shapes carry a migration warning; nothing is
    migrated on read.
    """
    cache_path = Path(path)
    blank = {"kind": "missing", "phase1_files": None, "mapper_graph": None, "warnings": [], "raw": None}
    if not cache_path.exists():
        return blank, "missing"
    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return {**blank, "kind": "invalid"}, f"invalid: {error}"
    kind = classify_cache_shape(raw)
    if kind == "invalid":
        return {**blank, "kind": "invalid"}, "invalid: unrecognized cache shape"
    warnings: list[str] = []
    phase1: dict[str, Any] | None = None
    mapper: dict[str, Any] | None = None
    if kind == "combined":
        sections = raw["sections"]
        if isinstance(sections.get(PHASE1_SECTION), dict):
            phase1 = sections[PHASE1_SECTION]
        else:
            warnings.append("v2 container is missing the phase1_files section")
        if isinstance(sections.get(MAPPER_SECTION), dict):
            mapper = sections[MAPPER_SECTION]
        else:
            warnings.append("v2 container is missing the mapper_graph section")
    elif kind == "phase1":
        phase1 = raw
        warnings.append("legacy v1 Phase-1 shape; migrates to a v2 container on next mapper write")
    else:
        mapper = raw
        warnings.append("legacy v1 mapper shape; migrates to a v2 container on next Phase-1 write")
    return {"kind": kind, "phase1_files": phase1, "mapper_graph": mapper, "warnings": warnings, "raw": raw}, None


def merge_container_section(existing_raw: Any, kind: str, section: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Return the raw payload to persist for one section write (Stage 0b).

    Combined files keep the other section plus unknown top-level keys; a v1
    file holding the other section migrates to a v2 container. Anything else
    (missing, Phase-1-only for a Phase-1 write, mapper-only for a mapper
    write, corrupt, or unrecognized) keeps today's single-shape write.
    """
    if kind == "combined" and isinstance(existing_raw, dict):
        raw = dict(existing_raw)
        sections = dict(existing_raw.get("sections", {}))
        sections[section] = payload
        raw["schema_version"] = CONTAINER_VERSION
        raw["sections"] = sections
        return raw
    if section == PHASE1_SECTION and kind == "mapper" and isinstance(existing_raw, dict):
        return {
            "schema_version": CONTAINER_VERSION,
            "sections": {PHASE1_SECTION: payload, MAPPER_SECTION: existing_raw},
        }
    if section == MAPPER_SECTION and kind == "phase1" and isinstance(existing_raw, dict):
        return {
            "schema_version": CONTAINER_VERSION,
            "sections": {PHASE1_SECTION: existing_raw, MAPPER_SECTION: payload},
        }
    return payload


def normalize_cache(loaded: Any) -> dict[str, Any]:
    """Coerce a loaded payload to the Phase 1 shape; drop malformed entries."""
    if not isinstance(loaded, dict):
        return empty_cache()
    files = loaded.get("files")
    if not isinstance(files, dict):
        return empty_cache()
    clean: dict[str, dict[str, Any]] = {}
    for rel, entry in files.items():
        if not isinstance(rel, str) or not rel or not isinstance(entry, dict):
            continue
        clean[rel.replace("\\", "/")] = {
            "last_read": entry.get("last_read") if isinstance(entry.get("last_read"), str) else None,
            "symbols": _str_list(entry.get("symbols"), MAX_SYMBOLS),
            "endpoints": _str_list(entry.get("endpoints"), MAX_ENDPOINTS),
            "imports": _str_list(entry.get("imports"), MAX_IMPORTS),
            "size_bytes": entry.get("size_bytes") if isinstance(entry.get("size_bytes"), int) else 0,
        }
    return {"version": VERSION, "last_updated": loaded.get("last_updated"), "files": clean}


def default_cache_path(root: Path | str, shared: bool = False) -> Path:
    root_path = Path(root)
    return root_path / (SHARED_CACHE if shared else LOCAL_CACHE)


def find_cache(root: Path | str) -> Path | None:
    """Return the existing cache path (shared first, then local), if any."""
    root_path = Path(root)
    for rel in (SHARED_CACHE, LOCAL_CACHE):
        candidate = root_path / rel
        if candidate.is_file():
            return candidate
    return None


def load(path: Path | str) -> tuple[dict[str, Any], str | None]:
    """Load and validate the Phase 1 section. Never raises: corrupt → empty + reason."""
    container, error = read_container(path)
    if error is not None:
        return empty_cache(), error
    if container["kind"] == "mapper":
        return empty_cache(), "shape-mismatch: mapper-graph shape; refusing to coerce"
    phase1 = container["phase1_files"]
    if phase1 is None:
        return empty_cache(), None
    try:
        return normalize_cache(phase1), None
    except (ValueError,) as error:
        return empty_cache(), f"invalid: {error}"


def _write_raw_atomic(cache_path: Path, raw: dict[str, Any]) -> Path:
    """Atomically persist one raw payload (tempfile + os.replace)."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(raw, indent=2) + "\n").encode("utf-8")
    handle = tempfile.NamedTemporaryFile(
        prefix=cache_path.name + ".", suffix=".tmp", dir=cache_path.parent, delete=False
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, cache_path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return cache_path


def save(path: Path | str, data: dict[str, Any]) -> Path:
    """Atomically write the Phase 1 section (updates ``last_updated``).

    Section-preserving (Stage 0b): a v1 mapper file migrates to a v2
    container and a combined file keeps its mapper section; anything else
    keeps today's single-shape Phase-1 write.
    """
    cache_path = Path(path)
    payload = dict(normalize_cache(data))
    payload["last_updated"] = _now()
    container, error = read_container(cache_path)
    if error is None:
        raw = merge_container_section(container["raw"], container["kind"], PHASE1_SECTION, payload)
    else:
        raw = payload
    return _write_raw_atomic(cache_path, raw)


def _python_endpoints(tree: ast.AST) -> list[str]:
    endpoints: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            try:
                text = ast.unparse(decorator).lower() if hasattr(ast, "unparse") else ""
            except Exception:
                text = ""
            if any(hint in text for hint in _ROUTE_HINTS):
                if node.name not in endpoints:
                    endpoints.append(node.name)
                break
        if len(endpoints) >= MAX_ENDPOINTS:
            break
    return endpoints


def inspect_file(root: Path | str, rel: str) -> dict[str, Any] | None:
    """Build a cache entry for one repo-relative path. None if unreadable."""
    root_path = Path(root)
    path = root_path / rel
    try:
        if not path.is_file():
            return None
        size_bytes = path.stat().st_size
        text = path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return None
    symbols: list[str] = []
    imports: list[str] = []
    endpoints: list[str] = []
    if code_relationships is not None:
        try:
            facts = code_relationships.extract(path, root_path, text)
            for row in facts.get("definitions", []):
                value = str(row.get("value", ""))
                if value and value not in symbols:
                    symbols.append(value)
                if len(symbols) >= MAX_SYMBOLS:
                    break
            for group in ("imports", "loaders"):
                for row in facts.get(group, []):
                    value = str(row.get("value", "")).replace("\\", "/")
                    if value and value not in imports:
                        imports.append(value)
                    if len(imports) >= MAX_IMPORTS:
                        break
        except Exception:
            pass
    if path.suffix == ".py":
        try:
            endpoints = _python_endpoints(ast.parse(text))
        except (SyntaxError, ValueError):
            endpoints = []
    return {
        "last_read": _now(),
        "symbols": symbols[:MAX_SYMBOLS],
        "endpoints": endpoints[:MAX_ENDPOINTS],
        "imports": imports[:MAX_IMPORTS],
        "size_bytes": size_bytes,
    }


def update(
    root: Path | str,
    source_files: list[str],
    path: Path | str | None = None,
    shared: bool = False,
) -> dict[str, Any]:
    """Incrementally merge ``source_files`` into the cache (batched, one save).

    Missing files are dropped from the cache. Unreadable files are skipped
    and reported in ``errors`` — never raised.
    """
    root_path = Path(root)
    cache_path = Path(path) if path is not None else default_cache_path(root_path, shared)
    container, _ = read_container(cache_path)
    phase1 = container["phase1_files"]
    section_files = phase1.get("files", {}) if isinstance(phase1, dict) else {}
    files = dict(section_files) if isinstance(section_files, dict) else {}
    seen: set[str] = set()
    updated = 0
    pruned = 0
    errors: list[str] = []
    for raw in source_files:
        rel = str(raw or "").replace("\\", "/").strip()
        if not rel or rel in seen:
            continue
        seen.add(rel)
        entry = inspect_file(root_path, rel)
        if entry is None:
            if rel in files:
                del files[rel]
                pruned += 1
            else:
                errors.append(f"{rel}: missing or unreadable")
            continue
        files[rel] = entry
        updated += 1
    save(cache_path, {"version": VERSION, "last_updated": None, "files": files})
    return {
        "cache_path": cache_path.as_posix(),
        "updated": updated,
        "pruned": pruned,
        "total": len(files),
        "errors": errors,
    }


def clear(path: Path | str) -> Path:
    """Wipe the cache at ``path``."""
    cache_path = Path(path)
    save(cache_path, empty_cache())
    return cache_path


def _section_files(container: dict[str, Any]) -> dict[str, Any]:
    """Return a mutable copy of the Phase 1 files section (empty when absent)."""
    phase1 = container["phase1_files"]
    section_files = phase1.get("files", {}) if isinstance(phase1, dict) else {}
    return dict(section_files) if isinstance(section_files, dict) else {}


def invalidate(path: Path | str, files: list[str]) -> int:
    """Remove specific entries. Returns the number removed.

    Section-scoped (Stage 0b): a combined file keeps its mapper section; a
    mapper-only file has nothing to remove and is left byte-identical.
    """
    cache_path = Path(path)
    container, error = read_container(cache_path)
    if error is not None:
        return 0
    current = _section_files(container)
    if not current and container["phase1_files"] is None:
        return 0
    targets = {str(item).replace("\\", "/") for item in files if item}
    remaining = {rel: entry for rel, entry in current.items() if rel not in targets}
    removed = len(current) - len(remaining)
    if removed:
        save(cache_path, {"version": VERSION, "last_updated": None, "files": remaining})
    return removed


def prune_missing(root: Path | str, path: Path | str | None = None) -> int:
    """Drop entries whose files no longer exist. Returns the number dropped."""
    root_path = Path(root)
    cache_path = Path(path) if path is not None else (find_cache(root_path) or default_cache_path(root_path))
    container, error = read_container(cache_path)
    if error is not None:
        return 0
    current = _section_files(container)
    missing = [rel for rel in current if not (root_path / rel).is_file()]
    return invalidate(cache_path, missing)


def prune_older_than(path: Path | str, days: int) -> int:
    """Drop entries unread for more than ``days``. Returns the number dropped."""
    cache_path = Path(path)
    container, error = read_container(cache_path)
    if error is not None:
        return 0
    current = _section_files(container)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(0, int(days)))
    old: list[str] = []
    for rel, entry in current.items():
        if not isinstance(entry, dict):
            old.append(rel)
            continue
        last_read = entry.get("last_read")
        try:
            stamp = datetime.fromisoformat(str(last_read)) if last_read else None
        except ValueError:
            stamp = None
        if stamp is None or stamp < cutoff:
            old.append(rel)
    return invalidate(cache_path, old)


def stale_files(root: Path | str, data: dict[str, Any]) -> list[str]:
    """Return cached files changed on disk since ``last_read`` (Phase 7 input)."""
    root_path = Path(root)
    stale: list[str] = []
    for rel, entry in data.get("files", {}).items():
        path = root_path / rel
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        except OSError:
            stale.append(rel)
            continue
        try:
            stamp = datetime.fromisoformat(str(entry.get("last_read"))) if entry.get("last_read") else None
        except ValueError:
            stamp = None
        if stamp is None or mtime > stamp:
            stale.append(rel)
    return sorted(stale)


# --- Phase 7: lifecycle CLI -------------------------------------------------
#
# Explicit-request trigger surface for staleness management: `status` reports
# what is cached and what drifted; the prune/clear commands act on it. All
# read-only except the command named. Session-start and project-reset clears
# are host behaviors; this CLI is how a user requests them.


def _mapper_section_summary(mapper: Any) -> dict[str, Any]:
    graph = mapper.get("graph", {}) if isinstance(mapper, dict) else {}
    scope = mapper.get("scope", []) if isinstance(mapper, dict) else []
    return {
        "scope_files": len(scope) if isinstance(scope, list) else 0,
        "symbols": len(graph.get("symbols", [])) if isinstance(graph, dict) else 0,
    }


def _lifecycle_status(root: Path) -> dict[str, Any]:
    root_path = Path(root)
    found = find_cache(root_path)
    if found is None:
        return {"cache_path": None, "present": False, "kind": "missing", "files": 0, "stale": []}
    container, error = read_container(found)
    if error is not None:
        return {
            "cache_path": found.as_posix(),
            "present": True,
            "kind": "invalid",
            "note": error,
            "files": 0,
            "stale": [],
        }
    kind = container["kind"]
    base: dict[str, Any] = {
        "cache_path": found.as_posix(),
        "present": True,
        "kind": "combined" if kind == "combined" else kind,
        "warnings": container["warnings"],
    }
    if kind == "mapper":
        base.update({
            "note": "mapper-shaped cache: lifecycle ops target the Phase 1 section and preserve this graph",
            **_mapper_section_summary(container["mapper_graph"]),
            "files": 0,
            "stale": [],
        })
        return base
    data, _ = load(found)
    base.update({
        "last_updated": data.get("last_updated"),
        "files": len(data["files"]),
        "stale": stale_files(root_path, data),
    })
    if kind == "combined":
        base["note"] = "v2 container: Phase 1 section plus preserved mapper graph"
        base.update(_mapper_section_summary(container["mapper_graph"]))
    return base


def _render_status(root: Path) -> str:
    status = _lifecycle_status(Path(root))
    lines = ["# TailTrail Code Graph Cache", ""]
    if not status["present"]:
        lines.append("- Cache: `missing` (no shared or local cache file)")
        return "\n".join(lines) + "\n"
    if status["kind"] == "mapper":
        lines.extend([
            f"- Path: `{status['cache_path']}`",
            "- Kind: `mapper-shaped` (rich graph, not Phase 1 file index)",
            f"- Scope files: `{status['scope_files']}`",
            f"- Symbols: `{status['symbols']}`",
            f"- {status['note']}",
        ])
        for warning in status.get("warnings", []):
            lines.append(f"- Warning: {warning}")
        return "\n".join(lines) + "\n"
    if status["kind"] == "invalid":
        lines.extend([
            f"- Path: `{status['cache_path']}`",
            "- Kind: `invalid` (unrecognized cache shape)",
            f"- {status['note']}",
        ])
        return "\n".join(lines) + "\n"
    lines.extend([
        f"- Path: `{status['cache_path']}`",
        f"- Kind: `{status['kind']}`",
        f"- Last updated: `{status['last_updated']}`",
        f"- Files: `{status['files']}`",
        f"- Stale: `{len(status['stale'])}`",
    ])
    if status["kind"] == "combined":
        lines.extend([
            f"- Mapper scope files: `{status.get('scope_files', 0)}`",
            f"- Mapper symbols: `{status.get('symbols', 0)}`",
        ])
    for warning in status.get("warnings", []):
        lines.append(f"- Warning: {warning}")
    for rel in status["stale"][:20]:
        lines.append(f"- Stale `{rel}`")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Code-graph cache lifecycle (Phase 7).")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    parser.add_argument(
        "command",
        choices=("status", "prune-missing", "prune-older-than", "invalidate", "clear"),
        help="status: report; prune-missing: drop gone files; prune-older-than: drop by age; invalidate: drop listed files; clear: wipe.",
    )
    parser.add_argument("--file", action="append", default=[], help="File for invalidate. Repeatable.")
    parser.add_argument("--days", type=int, default=30, help="Age for prune-older-than.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root)
    if args.command == "status":
        if args.format == "json":
            print(json.dumps(_lifecycle_status(root), indent=2, sort_keys=True))
        else:
            print(_render_status(root), end="")
        return 0
    path = find_cache(root) or default_cache_path(root)
    if args.command == "prune-missing":
        removed = prune_missing(root, path)
    elif args.command == "prune-older-than":
        removed = prune_older_than(path, args.days)
    elif args.command == "invalidate":
        removed = invalidate(path, args.file)
    else:
        removed = len(load(path)[0]["files"])
        clear(path)
    result = {"cache_path": Path(path).as_posix(), "command": args.command, "removed": removed}
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{args.command}: removed `{removed}` entries in `{path}`\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
