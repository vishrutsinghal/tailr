"""Best-effort passive capture hooks for TailTrail code graphing (Phase 2).

Worker/agent read and write paths call these hooks as byproducts of work
they were already doing. Hooks only queue repo-relative file paths in
memory — no disk I/O, no parsing — and never raise, so the main task is
never interrupted or slowed down. A natural boundary (end of a file-read
session, end of a multi-file tool call) calls :func:`flush`, which merges
the queued paths into the Phase 1 cache via ``code_graph_cache.update`` in
a single batched save. Cheap symbol/import/size extraction happens there,
from file content already on disk — never as separate analysis work.

Usage (worker/agent integration)::

    from capture_hooks import on_file_read, flush

    on_file_read(root, "src/claims_api/validation.py")
    on_file_read(root, "src/claims_api/service.py")
    flush(root)  # one batched Phase 1 update

See docs/arch/code-graphing.md §3.2. The legacy ``capture_cache``
parallel store (``.tailtrail/capture-cache.json``) is retired: hooks no
longer persist it; the Phase 1 cache shape is the single system of record.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import code_graph_cache

# Flush after this many queued paths to bound memory when a caller
# never hits a natural flush boundary. Still a batch, not per-line.
_AUTO_FLUSH_AT = 50

_pending: dict[str, set[str]] = {}


def _key(root: Path | str) -> str:
    try:
        return Path(root).resolve().as_posix()
    except OSError:
        return str(root)


def _normalize(file_path: str) -> str:
    return str(file_path or "").replace("\\", "/").strip().strip("/")


def _queue(root: Path | str, *paths: str) -> None:
    key = _key(root)
    queued = _pending.setdefault(key, set())
    for item in paths:
        rel = _normalize(item)
        if rel:
            queued.add(rel)
    if len(queued) >= _AUTO_FLUSH_AT:
        try:
            flush(root)
        except Exception:
            pass


def on_file_read(root: Path | str, file_path: str) -> None:
    """Queue a file read for the next batched flush. Never raises."""
    try:
        _queue(root, file_path)
    except Exception:
        pass


def on_file_edit(root: Path | str, file_path: str, edit_count: int = 1) -> None:
    """Queue an edited file; current content is picked up at flush time."""
    try:
        _queue(root, file_path)
    except Exception:
        pass


def on_import_encountered(
    root: Path | str,
    from_file: str,
    to_file: str,
    import_path: str = "",
) -> None:
    """Queue both ends of an observed import edge. Never raises."""
    try:
        _queue(root, from_file, to_file)
    except Exception:
        pass


def on_symbol_observed(
    root: Path | str,
    file_path: str,
    symbol_name: str,
    symbol_type: str = "",
) -> None:
    """Queue the file a symbol was observed in. Never raises."""
    try:
        _queue(root, file_path)
    except Exception:
        pass


def on_call_site_encountered(
    root: Path | str,
    caller_file: str,
    caller_symbol: str,
    callee_file: str,
    callee_symbol: str,
) -> None:
    """Queue both files of an observed call edge. Never raises."""
    try:
        _queue(root, caller_file, callee_file)
    except Exception:
        pass


def on_traceback_observed(root: Path | str, chain: list[str]) -> None:
    """Kept for signature compatibility; traceback fragments are Phase 3+ territory."""


def pending(root: Path | str) -> list[str]:
    """Return queued paths not yet flushed (sorted, for tests/callers)."""
    return sorted(_pending.get(_key(root), set()))


def discard(root: Path | str, files: list[str]) -> int:
    """Drop queued paths (e.g. consumed by an explicit build). Returns count."""
    key = _key(root)
    queued = _pending.get(key, set())
    before = len(queued)
    for item in files:
        queued.discard(_normalize(item))
    return before - len(queued)


def flush(
    root: Path | str,
    path: Path | str | None = None,
    shared: bool = False,
) -> dict[str, Any]:
    """Merge queued paths into the Phase 1 cache in one batched update.

    Never raises: returns ``code_graph_cache.update`` summary, or a
    zero-summary with the error when the update itself fails.
    """
    key = _key(root)
    queued = sorted(_pending.get(key, set()))
    if not queued:
        return {"cache_path": None, "updated": 0, "pruned": 0, "total": 0, "errors": []}
    try:
        summary = code_graph_cache.update(root, queued, path=path, shared=shared)
    except Exception as error:  # never block the task on capture
        return {"cache_path": None, "updated": 0, "pruned": 0, "total": 0, "errors": [str(error)]}
    if not summary.get("errors"):
        _pending[key] = set()
    else:
        # Partial failure: drop only successfully merged entries.
        data, _ = code_graph_cache.load(summary.get("cache_path") or code_graph_cache.default_cache_path(root))
        _pending[key] = {item for item in queued if item not in data.get("files", {})}
    return summary


def reset_for_tests(root: Path | str | None = None) -> None:
    """Clear queued paths (test helper)."""
    if root is not None:
        _pending.pop(_key(root), None)
    else:
        _pending.clear()
