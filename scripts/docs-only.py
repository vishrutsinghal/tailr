#!/usr/bin/env python3
"""Docs-only fast lane: trivial prose edits without the full plan ceremony.

Strict gate only -- EVERY path must be a prose suffix (.md/.rst/.txt/.adoc)
and the goal must carry no production signal. One code path anywhere forces
the full `tailtrail start` plan. On success this mints a run ID, records one
ledger event plus a minimal approved anchor/lock (so the write guard honors
it even when a code run is active), and prints a short verbal line.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"{filename} is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import navigator_scope as NAV  # noqa: E402

LEDGER = _load("docs_only_run_ledger", "run-ledger.py")


def suggested_run_id(root: Path, goal: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    digest = hashlib.sha256(goal.encode("utf-8")).hexdigest()[:6]
    base = f"doc-{stamp}-{digest}"
    candidate = base
    index = 2
    while LEDGER.state_dir(root.resolve(), candidate).exists():
        candidate = f"{base}-{index}"
        index += 1
    return candidate


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def start(root: Path, goal: str, paths: list[str], run_id: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    clean = sorted({str(item).replace("\\", "/").strip().strip("/") for item in paths if str(item).strip()})
    if not clean:
        raise ValueError("docs-only fast lane needs at least one path")
    if not NAV.is_docs_only_fast_lane(goal, clean):
        raise ValueError(
            "not a docs-only change: every path must be .md/.rst/.txt/.adoc "
            "and the goal must carry no production signal "
            "(implement/feature/refactor/endpoint/production/service); "
            "use the full `tailtrail start` plan instead"
        )
    selected = run_id or suggested_run_id(root, goal)
    if Path(selected).name != selected:
        raise ValueError("run_id must be a single local run identifier")
    LEDGER.init_run(root, selected, goal)
    directory = LEDGER.state_dir(root, selected)

    anchor = {
        "schema_version": "1",
        "type": "tailtrail-change-intent-anchor",
        "run_id": selected,
        "proposal_version": 1,
        "goal": goal.strip(),
        "requirements": [
            {
                "requirement_uid": "req-doc-only",
                "display_id": "REQ-01",
                "kind": "change",
                "statement": goal.strip(),
                "acceptance_criteria": [],
                "preserve_rules": [],
                "likely_paths": [{"path": item, "role": "implementation-owner"} for item in clean],
                "evidence_plan": [],
                "status": "approved",
            }
        ],
        "docs_only_fast_lane": True,
        "status": "approved",
    }
    anchor["approved_fingerprint"] = fingerprint(
        {key: value for key, value in anchor.items() if key != "approved_fingerprint"}
    )
    anchor_path = directory / "anchors" / "approved-v1.json"
    LEDGER.atomic_json(anchor_path, anchor)

    lock = {
        "schema_version": "2",
        "type": "tailtrail-planning-lock",
        "run_id": selected,
        "goal": goal.strip(),
        "status": "approved",
        "writes_allowed": True,
        "docs_only_fast_lane": True,
        "pipeline": {
            "active_stage": "IMPLEMENTATION",
            "completed_stages": [],
            "stage_sequence": ["IMPLEMENTATION", "TESTING", "INFRA"],
            "handoff_manifest": None,
        },
        "boundary": "Docs-only fast lane: trivial prose paths only, no code ownership evidence required.",
    }
    lock_path = directory / "planning" / "lock-v1.json"
    LEDGER.atomic_json(lock_path, lock)
    LEDGER.append_event(
        root,
        selected,
        "anchor_approved",
        {
            "path": anchor_path.relative_to(root).as_posix(),
            "fingerprint": anchor["approved_fingerprint"],
            "requirements": ["req-doc-only"],
            "docs_only_fast_lane": True,
        },
    )
    return {
        "run_id": selected,
        "goal": goal.strip(),
        "paths": clean,
        "anchor": anchor_path.relative_to(root).as_posix(),
        "lock": lock_path.relative_to(root).as_posix(),
        "fingerprint": anchor["approved_fingerprint"],
        "message": (
            f"Docs-only run `{selected}`: editing {', '.join(clean)} "
            f"-- no full plan (trivial lane, fingerprint {anchor['approved_fingerprint'][:19]}...)."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Docs-only fast lane for trivial prose edits.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--goal", required=True)
    parser.add_argument("--path", action="append", default=[], dest="paths")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    try:
        result = start(args.root, args.goal, args.paths, args.run_id)
    except (ValueError, OSError) as error:
        print(f"Docs-only fast lane error: {error}")
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
