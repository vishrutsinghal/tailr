#!/usr/bin/env python3
"""Typed host decision records for TailTrail runs (Option A).

Every approve / revise / discuss / close verb records which option the host
selected, with an optional free-text rationale and timestamp, into an
append-only per-run log. Hosts render natively from this contract: CLI prints
it, MCP returns it, chat surfaces choices. The decision vocabulary mirrors the
requirement-intake answer shape (decision plus detail), not a new invention.

Storage: ``.tailtrail/runs/<run_id>/decisions/decisions-v1.jsonl`` (one JSON
object per line). Recording never raises for malformed input beyond ValueError
on contract violations; callers decide whether a recording failure blocks.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _ledger() -> Any:
    spec = importlib.util.spec_from_file_location(
        "host_decision_ledger", ROOT / "scripts" / "run-ledger.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


L = _ledger()

SCHEMA_VERSION = "1"
DECISION_TYPE = "tailtrail-host-decision"

VERBS = {"approve", "activate", "revise", "discuss", "close"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def log_path(root: Path, run_id: str) -> Path:
    return L.state_dir(root.resolve(), run_id) / "decisions" / "decisions-v1.jsonl"


def _decision_id(run_id: str, verb: str, decision: str, decided_at: str) -> str:
    canonical = json.dumps(
        {"run_id": run_id, "verb": verb, "decision": decision, "decided_at": decided_at},
        sort_keys=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def record(
    root: Path | str,
    run_id: str,
    verb: str,
    decision: str,
    option: str | None = None,
    rationale: str | None = None,
    host: str | None = None,
    prior_state: str | None = None,
    resulting_state: str | None = None,
) -> dict[str, Any]:
    """Append one typed host decision to the run log and return the entry."""
    if not str(run_id).strip() or Path(str(run_id)).name != str(run_id).strip():
        raise ValueError("host decision requires a single local run identifier")
    if verb not in VERBS:
        raise ValueError(f"host decision verb must be one of {sorted(VERBS)}")
    if not str(decision).strip():
        raise ValueError("host decision requires a non-empty decision")
    if option is not None and not str(option).strip():
        raise ValueError("host decision option must be non-empty when supplied")
    if rationale is not None and not str(rationale).strip():
        raise ValueError("host decision rationale must be non-empty when supplied")
    root_path = Path(root).resolve()
    decided_at = _now()
    entry = {
        "schema_version": SCHEMA_VERSION,
        "type": DECISION_TYPE,
        "decision_id": _decision_id(str(run_id).strip(), verb, str(decision).strip(), decided_at),
        "run_id": str(run_id).strip(),
        "verb": verb,
        "decision": str(decision).strip(),
        "option": str(option).strip() if option is not None else None,
        "rationale": str(rationale).strip() if rationale is not None else None,
        "host": str(host).strip() if host is not None and str(host).strip() else None,
        "prior_state": str(prior_state) if prior_state is not None else None,
        "resulting_state": str(resulting_state) if resulting_state is not None else None,
        "decided_at": decided_at,
    }
    path = log_path(root_path, entry["run_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError:
            pass
    L.append_event(root_path, entry["run_id"], "host_decision_recorded", {
        "artifact": path.relative_to(L.state_dir(root_path, entry["run_id"])).as_posix(),
        "verb": verb,
        "decision": entry["decision"],
        "decision_id": entry["decision_id"],
    })
    return entry


def list_decisions(root: Path | str, run_id: str) -> list[dict[str, Any]]:
    """Return every recorded decision for a run, oldest first. Empty when none."""
    path = log_path(Path(root).resolve(), str(run_id).strip())
    if not path.is_file():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("type") == DECISION_TYPE:
            entries.append(value)
    return entries


def latest(root: Path | str, run_id: str) -> dict[str, Any] | None:
    """Return the most recent decision for a run, or None when absent."""
    entries = list_decisions(root, run_id)
    return entries[-1] if entries else None
