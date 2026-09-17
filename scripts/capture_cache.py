"""Passive capture cache for TailTrail code graphing (Phase 1).

Records file reads, edits, import edges, symbols, call sites, and
traceback fragments observed during normal worker/agent work. The cache
is local (never git-shared) and is cleared when an explicit AST graph
is built (Phase 2) — see docs/arch/code-graphing.md.

Design rules:
- Capture only what is already observed for task reasons.
- Never raise: capture failures must not break the task.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CACHE_RELPATH = Path(".tailtrail") / "capture-cache.json"

_LIST_KEYS = (
    "files_touched",
    "import_edges_captured",
    "symbols_observed",
    "call_edges_captured",
    "traceback_chains_captured",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PassiveCaptureCache:
    """Append-only passive capture store with per-item dedupe."""

    def __init__(self, root: Path | str = ".") -> None:
        self.root = Path(root)
        self.path = self.root / CACHE_RELPATH
        self.data: dict[str, Any] = self._load()

    # -- persistence -----------------------------------------------------

    def _load(self) -> dict[str, Any]:
        try:
            if self.path.exists():
                with self.path.open("r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                if isinstance(loaded, dict):
                    return self._normalize(loaded)
        except (OSError, json.JSONDecodeError, ValueError):
            pass
        return self._empty()

    @staticmethod
    def _empty() -> dict[str, Any]:
        data: dict[str, Any] = {"updated_at": None}
        for key in _LIST_KEYS:
            data[key] = []
        return data

    def _normalize(self, loaded: dict[str, Any]) -> dict[str, Any]:
        data = self._empty()
        for key in _LIST_KEYS:
            value = loaded.get(key)
            data[key] = value if isinstance(value, list) else []
        data["updated_at"] = loaded.get("updated_at")
        return data

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.data["updated_at"] = _now()
            with self.path.open("w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def clear(self) -> None:
        """Reset the cache (used after an explicit graph build)."""
        self.data = self._empty()
        self.save()

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _upsert(
        rows: list[dict[str, Any]],
        key_fields: tuple[str, ...],
        values: dict[str, Any],
    ) -> dict[str, Any]:
        """Find a row matching all key_fields, or create one; update it."""
        for row in rows:
            if all(row.get(field) == values.get(field) for field in key_fields):
                row["last_seen"] = values.get("last_seen", _now())
                row["times_seen"] = int(row.get("times_seen", 1)) + 1
                for field, value in values.items():
                    if field == "edit_count":
                        row[field] = int(row.get(field, 0)) + int(value)
                    elif field not in ("last_seen", "times_seen") and value is not None:
                        row[field] = value
                return row
        row = dict(values)
        row.setdefault("first_seen", _now())
        row.setdefault("last_seen", _now())
        row.setdefault("times_seen", 1)
        rows.append(row)
        return row

    # -- record methods ---------------------------------------------------

    def record_file_read(self, file_path: str) -> None:
        if not file_path:
            return
        self._upsert(self.data["files_touched"], ("path",), {"path": file_path})
        self.save()

    def record_file_edit(self, file_path: str, edit_count: int = 1) -> None:
        if not file_path:
            return
        self._upsert(
            self.data["files_touched"],
            ("path",),
            {"path": file_path, "edit_count": max(1, int(edit_count))},
        )
        self.save()

    def record_import(self, from_file: str, to_file: str, import_path: str = "") -> None:
        if not from_file or not to_file:
            return
        self._upsert(
            self.data["import_edges_captured"],
            ("from", "to"),
            {"from": from_file, "to": to_file, "import_path": import_path},
        )
        self.save()

    def record_symbol(self, file_path: str, symbol_name: str, symbol_type: str = "") -> None:
        if not file_path or not symbol_name:
            return
        self._upsert(
            self.data["symbols_observed"],
            ("file", "symbol"),
            {"file": file_path, "symbol": symbol_name, "type": symbol_type},
        )
        self.save()

    def record_call(self, caller_file: str, caller_symbol: str, callee_file: str, callee_symbol: str) -> None:
        if not caller_file or not callee_file:
            return
        self._upsert(
            self.data["call_edges_captured"],
            ("from", "to"),
            {"from": f"{caller_file}:{caller_symbol}", "to": f"{callee_file}:{callee_symbol}"},
        )
        self.save()

    def record_traceback(self, chain: list[str]) -> None:
        if not chain:
            return
        self.data["traceback_chains_captured"].append(
            {"chain": list(chain), "first_seen": _now()}
        )
        self.save()

    def clear_files(self, built_files: list[str]) -> int:
        """Selectively drain built files; preserve residual (untouched) data.

        Returns the number of file entries removed.
        """
        built = {str(item).replace("\\", "/") for item in built_files if item}

        def involved(row: dict[str, Any], path_key: str) -> bool:
            value = str(row.get(path_key, "")).replace("\\", "/")
            if value in built:
                return True
            # call edges use "file:symbol" — compare the file part
            return value.split(":", 1)[0] in built

        before = len(self.data["files_touched"])
        self.data["files_touched"] = [
            row for row in self.data["files_touched"] if str(row.get("path", "")).replace("\\", "/") not in built
        ]
        self.data["import_edges_captured"] = [
            row for row in self.data["import_edges_captured"]
            if not involved(row, "from") and not involved(row, "to")
        ]
        self.data["symbols_observed"] = [
            row for row in self.data["symbols_observed"] if str(row.get("file", "")).replace("\\", "/") not in built
        ]
        self.data["call_edges_captured"] = [
            row for row in self.data["call_edges_captured"]
            if not involved(row, "from") and not involved(row, "to")
        ]
        removed = before - len(self.data["files_touched"])
        self.save()
        return removed

    # -- coverage helpers (used by Phase 4 commit prompt) -----------------

    def has_imports_and_symbols(self, file_path: str) -> bool:
        has_imports = any(
            row.get("from") == file_path or row.get("to") == file_path
            for row in self.data["import_edges_captured"]
        )
        has_symbols = any(row.get("file") == file_path for row in self.data["symbols_observed"])
        return has_imports and has_symbols

    def file_entry(self, file_path: str) -> dict[str, Any] | None:
        for row in self.data["files_touched"]:
            if row.get("path") == file_path:
                return row
        return None
