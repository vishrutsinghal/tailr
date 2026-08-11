#!/usr/bin/env python3
"""Route an evidence-incomplete closure into one bounded same-run correction.

This is a control-plane handoff only.  It never edits source, re-runs a test,
retries a command, recovers Git state, or mutates the immutable approved anchor.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, script: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


L = load("closure_correction_ledger", "run-ledger.py")
LOCK = load("closure_correction_lock", "planning-lock.py")
CONVERGENCE = load("closure_correction_convergence", "harness-convergence.py")
CONTINUITY = load("closure_correction_continuity", "context-continuity.py")


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_report(root: Path, run_id: str) -> tuple[Path, dict[str, Any]]:
    directory = L.state_dir(root, run_id) / "completion-reports"
    reports = sorted(directory.glob("report-*.json"))
    if not reports:
        raise ValueError("no completion report exists; run tailtrail closure finalize first")
    return reports[-1], read(reports[-1])


def correction_signals(report: dict[str, Any]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for row in report.get("requirement_status", {}).get("requirements", []):
        if row.get("status") == "complete":
            continue
        drift = [item for item in row.get("drift", []) if isinstance(item, dict)]
        findings = [item for item in row.get("findings", []) if isinstance(item, dict)]
        source = next((item for item in drift if item.get("classification") in {"regressed", "new-drift", "needs-decision"}), None)
        source = source or (findings[0] if findings else {})
        classification = str(source.get("classification", "unchanged"))
        category = str(source.get("category", "evidence"))
        signals.append({
            "requirement_uid": row["requirement_uid"], "statement": row.get("statement", ""),
            "classification": classification, "category": category,
            "reason": str(source.get("message", "Requirement is incomplete or lacks required evidence.")),
        })
    if signals:
        return signals
    fallback = next(iter(report.get("requirement_status", {}).get("requirements", [])), None)
    if not isinstance(fallback, dict):
        return signals
    for key, category in (("architecture", "architecture"), ("behaviour", "behaviour")):
        control = report.get(key, {})
        if isinstance(control, dict) and control.get("status") not in {"pass", "not-assessed"}:
            finding = next(iter(control.get("findings", [])), {})
            signals.append({
                "requirement_uid": fallback["requirement_uid"], "statement": fallback.get("statement", ""),
                "classification": str(finding.get("classification", "needs-decision")), "category": category,
                "reason": str(finding.get("message", f"Selected {category} evidence is missing or incomplete.")),
            })
    return signals


def evidence_kind(category: str) -> str:
    return {
        "architecture": "architecture", "behaviour": "behavior", "behavior": "behavior",
        "scope": "scope", "preservation": "preservation",
    }.get(category, "approved-path")


def fingerprint(signals: list[dict[str, Any]]) -> str:
    normalized = [{key: item[key] for key in ("requirement_uid", "classification", "category", "reason")} for item in signals]
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def existing(root: Path, run_id: str, value: str) -> dict[str, Any] | None:
    directory = L.state_dir(root, run_id) / "closure-corrections"
    for path in sorted(directory.glob("correction-*.json"), reverse=True):
        payload = read(path)
        if payload.get("failure_fingerprint") == value:
            return payload
    return None


def handoff(root: Path, run_id: str, max_cycles: int = 2) -> dict[str, Any]:
    root = root.resolve()
    if max_cycles < 1:
        raise ValueError("max cycles must be at least one")
    LOCK.assert_write_allowed(root, run_id)
    report_path, report = latest_report(root, run_id)
    if report.get("overall_status") == "complete":
        return {
            "schema_version": "1", "type": "tailtrail-closure-correction", "run_id": run_id,
            "status": "no-correction-needed", "report": report_path.relative_to(root).as_posix(),
            "boundary": "The saved Completion Report is complete; no correction packet was created.",
        }
    signals = correction_signals(report)
    if not signals:
        raise ValueError("completion report is incomplete but does not name a requirement-scoped correction signal")
    signature = fingerprint(signals)
    prior = existing(root, run_id, signature)
    if prior:
        return {**prior, "reused": True}

    active = signals[0]
    anchor = read(L.state_dir(root, run_id) / "anchors" / "approved-v1.json")
    requirement = next((row for row in anchor.get("requirements", []) if row.get("requirement_uid") == active["requirement_uid"]), None)
    if not requirement:
        raise ValueError("correction signal is not part of the approved anchor")
    paths = [str(path) for path in requirement.get("likely_paths", [])]
    inside_scope = bool(paths) and active["category"] != "scope"
    state = active["classification"] if active["classification"] in {"resolved", "improved", "unchanged", "regressed", "new-drift", "needs-decision"} else "unchanged"
    convergence = CONVERGENCE.assess(root, run_id, active["requirement_uid"], "needs-decision" if not inside_scope else state, max_cycles)
    continuity = CONTINUITY.render(root, run_id, active["requirement_uid"], "unexpected-scope" if not inside_scope else "correction-cycle", 180)
    action = convergence["action"]
    payload = {
        "schema_version": "1", "type": "tailtrail-closure-correction", "run_id": run_id,
        "status": "replan-required" if action == "replan" else "correction-ready",
        "failure_fingerprint": signature, "source_report": report_path.relative_to(root).as_posix(),
        "active_requirement": active, "deferred_signals": signals[1:],
        "scope": {"inside_approved_boundary": inside_scope, "allowed_paths": paths, "evidence_kind": evidence_kind(active["category"])},
        "convergence": {key: value for key, value in convergence.items() if key != "path"},
        "continuity": {"state": Path(continuity["state_path"]).relative_to(root).as_posix(), "packet": Path(continuity["packet_path"]).relative_to(root).as_posix()},
        "next_action": "Use the continuity packet for one scoped correction, then record new evidence and finalize the same run." if action == "bounded-correction" else "Create an approved amendment or replan; retain this run's anchor, checkpoints, and evidence.",
        "boundary": "One requirement-scoped correction route only. No source edit, command retry, Git recovery, or anchor mutation was performed.",
    }
    directory = L.state_dir(root, run_id) / "closure-corrections"
    artifact = directory / f"correction-{len(list(directory.glob('correction-*.json'))) + 1}.json"
    L.atomic_json(artifact, payload)
    L.append_event(root, run_id, "closure_correction_routed", {
        "artifact": artifact.relative_to(L.state_dir(root, run_id)).as_posix(),
        "requirement_uid": active["requirement_uid"], "action": action,
        "cycle": convergence["cycle"], "fingerprint": signature,
    })
    return {**payload, "artifact": artifact.as_posix(), "reused": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-cycles", type=int, default=2)
    args = parser.parse_args()
    try:
        print(json.dumps(handoff(args.root, args.run_id, args.max_cycles), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Closure correction error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
