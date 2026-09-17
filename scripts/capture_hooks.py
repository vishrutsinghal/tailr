"""Best-effort passive capture hooks for TailTrail code graphing (Phase 1).

Worker/agent read and write paths call these hooks as byproducts of work
they were already doing. Hooks never raise: if capture fails, the task
continues unaffected. See docs/arch/code-graphing.md, Phase 1.

Usage (worker/agent integration):

    from capture_hooks import on_file_read, on_file_edit, ...

    on_file_read(root, "src/claims_api/validation.py")
    on_import_encountered(root, "src/claims_api/service.py",
                          "src/claims_api/validation.py", "direct")
"""

from __future__ import annotations

from pathlib import Path

from capture_cache import PassiveCaptureCache

_cache: PassiveCaptureCache | None = None
_cache_root: Path | None = None


def get_cache(root: Path | str = ".") -> PassiveCaptureCache:
    """Return a process-wide cache instance bound to the given root."""
    global _cache, _cache_root
    root_path = Path(root)
    if _cache is None or _cache_root != root_path:
        _cache = PassiveCaptureCache(root_path)
        _cache_root = root_path
    return _cache


def _guarded(fn, *args) -> None:
    """Run a capture operation; swallow any failure so work is never blocked."""
    try:
        fn(*args)
    except Exception:
        pass


def on_file_read(root: Path | str, file_path: str) -> None:
    """Called when a file is read for editing, review, or inspection."""
    _guarded(get_cache(root).record_file_read, file_path)


def on_file_edit(root: Path | str, file_path: str, edit_count: int = 1) -> None:
    """Called when a file is modified."""
    _guarded(get_cache(root).record_file_edit, file_path, edit_count)


def on_import_encountered(
    root: Path | str,
    from_file: str,
    to_file: str,
    import_path: str = "",
) -> None:
    """Called when an import statement is observed while reading a file."""
    _guarded(get_cache(root).record_import, from_file, to_file, import_path)


def on_symbol_observed(
    root: Path | str,
    file_path: str,
    symbol_name: str,
    symbol_type: str = "",
) -> None:
    """Called when a function/class is observed in a file."""
    _guarded(get_cache(root).record_symbol, file_path, symbol_name, symbol_type)


def on_call_site_encountered(
    root: Path | str,
    caller_file: str,
    caller_symbol: str,
    callee_file: str,
    callee_symbol: str,
) -> None:
    """Called when a call relationship is observed in a file."""
    _guarded(get_cache(root).record_call, caller_file, caller_symbol, callee_file, callee_symbol)


def on_traceback_observed(root: Path | str, chain: list[str]) -> None:
    """Called when a traceback exposes a call chain fragment."""
    _guarded(get_cache(root).record_traceback, chain)


def reset_for_tests(root: Path | str | None = None) -> None:
    """Reset the module-level cache instance (test helper)."""
    global _cache, _cache_root
    _cache = None
    _cache_root = None
    if root is not None:
        get_cache(root)
