#!/usr/bin/env python3
"""Draft and approve a Debug Harness correction packet once root cause is proven.

Reuses the run's already-approved investigation requirement (from
debug-reproduction.py) rather than mutating the immutable approved anchor;
the fix is validated as additional evidence against that same requirement_uid
(DEBUG-HARNESS.md Section 6, Phase 5/6)."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


L = load("debug_correction_ledger", "run-ledger.py")
HYPOTHESIS = load("debug_correction_hypothesis", "debug-hypothesis.py")


def packet_path(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "debug" / "correction" / "correction-packet-v1.json"


def approved_anchor_path(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "anchors" / "approved-v1.json"


def propose(root: Path, run_id: str, hypothesis_id: str, statement: str | None) -> dict[str, Any]:
    root = root.resolve()
    ledger = HYPOTHESIS.read_ledger(root, run_id)
    row = HYPOTHESIS._find(ledger, hypothesis_id)
    if row["status"] != "proven":
        raise ValueError(f"hypothesis `{hypothesis_id}` is `{row['status']}`, not proven; prove root cause before proposing a correction")
    anchor_path = approved_anchor_path(root, run_id)
    if not anchor_path.is_file():
        raise ValueError("no approved investigation requirement exists for this run")
    packet = {
        "schema_version": "1",
        "type": "tailtrail-debug-correction-packet",
        "run_id": run_id,
        "hypothesis_id": hypothesis_id,
        "domain": row["domain"],
        "root_cause_statement": statement or row["statement"],
        "anchor_draft_path": anchor_path.relative_to(root).as_posix(),
        "status": "proposed",
        "approved_at": None,
    }
    L.atomic_json(packet_path(root, run_id), packet)
    L.append_event(root, run_id, "debug_correction_proposed", {"hypothesis_id": hypothesis_id, "domain": row["domain"]})
    return packet


def approve(root: Path, run_id: str, approved: bool) -> dict[str, Any]:
    if not approved:
        raise ValueError("approving a correction packet requires --approved")
    root = root.resolve()
    path = packet_path(root, run_id)
    if not path.is_file():
        raise ValueError("no correction packet has been proposed for this run")
    packet = json.loads(path.read_text(encoding="utf-8"))
    if packet["status"] == "approved":
        return packet
    packet["status"] = "approved"
    packet["approved_at"] = L.utc_now()
    L.atomic_json(path, packet)
    L.append_event(root, run_id, "debug_correction_approved", {"hypothesis_id": packet["hypothesis_id"]})
    return packet


def show(root: Path, run_id: str) -> dict[str, Any]:
    path = packet_path(root.resolve(), run_id)
    if not path.is_file():
        raise ValueError("no correction packet has been proposed for this run")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)

    propose_parser = sub.add_parser("propose")
    propose_parser.add_argument("--root", type=Path, default=Path.cwd())
    propose_parser.add_argument("--run-id", required=True)
    propose_parser.add_argument("--hypothesis-id", required=True)
    propose_parser.add_argument("--statement", default=None)

    approve_parser = sub.add_parser("approve")
    approve_parser.add_argument("--root", type=Path, default=Path.cwd())
    approve_parser.add_argument("--run-id", required=True)
    approve_parser.add_argument("--approved", action="store_true")

    show_parser = sub.add_parser("show")
    show_parser.add_argument("--root", type=Path, default=Path.cwd())
    show_parser.add_argument("--run-id", required=True)

    args = parser.parse_args()
    try:
        if args.action == "propose":
            result = propose(args.root, args.run_id, args.hypothesis_id, args.statement)
        elif args.action == "approve":
            result = approve(args.root, args.run_id, args.approved)
        else:
            result = show(args.root, args.run_id)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Debug correction error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
