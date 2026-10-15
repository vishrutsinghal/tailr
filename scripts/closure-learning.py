#!/usr/bin/env python3
"""Capture guarded, sanitized positive-learning candidates from completed runs.

This control-plane command never reads source, prompts, logs, or executes tests.
It requires an explicitly accepted completed closure and only creates a candidate;
promotion into curated learnings remains a separate explicit learning review.
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


L = load("closure_learning_ledger", "run-ledger.py")
REPORT = load("closure_learning_report", "completion-report.py")
LEARNER = load("closure_learning_agent", "learning-agent.py")
SAN = load("closure_learning_official_sanitizer", "official-aidlc-sanitize.py")


def canonical(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def candidate_status(report: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    requirements = report.get("requirement_status", {})
    if report.get("overall_status") != "complete":
        reasons.append("completion report is not complete")
    if requirements.get("complete") != requirements.get("total"):
        reasons.append("not every approved requirement is complete")
    if report.get("drift", {}).get("status") != "none-unresolved":
        reasons.append("unresolved drift is present")
    if report.get("execution_failures", {}).get("status") not in {"none-recorded", "resolved"}:
        reasons.append("an unresolved execution failure is present")
    if report.get("tests", {}).get("status") != "pass" or not report.get("tests", {}).get("passed_tiers"):
        reasons.append("saved passing validation receipts are missing")
    return not reasons, reasons


def success_pattern(report: dict[str, Any]) -> str:
    tiers = ", ".join(report.get("tests", {}).get("passed_tiers", [])) or "saved validation"
    count = report.get("requirement_status", {}).get("total", 0)
    return f"For a {count}-requirement delivery, retain requirement-linked {tiers} receipts and selected harness evidence before declaring completion."


def debug_profile(root: Path, run_id: str, report: dict[str, Any]) -> dict[str, Any] | None:
    debug = report.get("debug", {})
    if debug.get("debug_status") == "not-triggered": return None
    fingerprint_path = L.state_dir(root, run_id) / "debug" / "fingerprint" / "failure-fingerprint-v1.json"
    if not fingerprint_path.is_file(): raise ValueError("accepted Debug learning requires a sanitized failure fingerprint")
    fingerprint = json.loads(fingerprint_path.read_text(encoding="utf-8"))
    if fingerprint.get("portable") is not True or (fingerprint.get("privacy") or {}).get("raw_values") is not False:
        raise ValueError("Debug learning fingerprint is not marked sanitized and portable")
    return {"failure_fingerprint": fingerprint["fingerprint"], "proven_cause_class": debug.get("domain"), "confidence_state": debug.get("confidence_state"), "domain_confidence_ceiling": debug.get("domain_confidence_ceiling"), "validation_tiers": report.get("tests", {}).get("passed_tiers", []), "raw_values": False}


def capture(root: Path, run_id: str, accepted_by: str) -> dict[str, Any]:
    root = root.resolve()
    if accepted_by not in {"user", "trusted-ci"}:
        raise ValueError("accepted_by must be `user` or `trusted-ci`")
    report = REPORT.build(root, run_id, record=False)
    eligible, reasons = candidate_status(report)
    if not eligible:
        raise ValueError("positive learning is not eligible: " + "; ".join(reasons))

    directory = L.state_dir(root, run_id)
    debug = debug_profile(root, run_id, report)
    key = {"run_id": run_id, "accepted_by": accepted_by, "requirements": report["requirement_status"]["total"], "tiers": report["tests"]["passed_tiers"], "debug_fingerprint": debug.get("failure_fingerprint") if debug else None}
    candidate_id = "success-" + hashlib.sha256(canonical(key).encode("utf-8")).hexdigest()[:16]
    path = directory / "positive-learning" / f"{candidate_id}.json"
    if path.is_file():
        return {**json.loads(path.read_text(encoding="utf-8")), "reused": True}

    payload = {
        "schema_version": "1",
        "type": "tailtrail-success-pattern-candidate",
        "candidate_id": candidate_id,
        "run_id": run_id,
        "acceptance": {"accepted_by": accepted_by, "required": True},
        "requirements_completed": report["requirement_status"]["total"],
        "evidence_tiers": report["tests"]["passed_tiers"],
        "selected_harnesses": [item["name"] for item in report.get("harnesses", []) if item.get("used")],
        "pattern": success_pattern(report),
        "promotion": "candidate-only; explicit learning review required",
        "sanitization": "No raw source, prompt, log, repository name, user identity, or customer data is stored.",
        "source_report": "completion report evaluated locally for this run",
        "debug_profile": debug,
        "boundary": "This candidate records one accepted outcome. It is not a universal rule, a quality claim, or an automatic future-agent instruction.",
    }
    SAN.validate_artifact(root, payload, "learning")
    L.atomic_json(path, payload)
    LEARNER.ensure_files(root)
    event_id = f"closure-success-{candidate_id}"
    if not any(item.get("id") == event_id for item in LEARNER.read_events(root)):
        event = {
            "id": event_id, "timestamp": L.utc_now(), "repo": "", "task_type": "closure-success",
            "tags": ["closure", "positive-candidate", accepted_by], "prompt_summary": "Sanitized accepted closure evidence.",
            "files": [], "issue_ids": [], "validation_commands": [], "validation_outcome": "pass",
            "solution_summary": "No source or prompt content captured; see the run-local positive-learning candidate.",
            "acceptance": "accepted", "acceptance_reason": accepted_by, "approved_changes": [], "requested_changes": [],
            "clarifications": [], "fulfillment_status": "aligned", "learning_candidate": payload["pattern"],
            "risk": "normal", "sensitivity": "normal", "review_status": "approved", "user_override": "none",
            "reused_project_pattern": True, "small_focused_change": False, "no_new_dependency": True,
            "dependency_gate_applied": False, "scanner_resolved": False, "guardrail_weakened": False,
            "promotion_decision": "candidate-only", "stale_when": "the completion contract or selected evidence policy changes",
            "source_run_id": run_id, "positive_learning_candidate_id": candidate_id,
        }
        score = LEARNER.score_event(event)
        event["learning_confidence"] = score.__dict__
        event["promotion_decision"] = "candidate-only"
        LEARNER.V3.capture_legacy_event(root, event, captured_by="Closure Learning")
        LEARNER.append_jsonl(root / LEARNER.EVENTS, event)
        LEARNER.append_jsonl(root / LEARNER.SCORES, {"event_id": event_id, "timestamp": L.utc_now(), **score.__dict__})
        LEARNER.rebuild_index(root)
    L.append_event(root, run_id, "closure_positive_learning_captured", {"candidate_id": candidate_id, "accepted_by": accepted_by, "artifact": path.relative_to(directory).as_posix()})
    return {**payload, "event_id": event_id, "reused": False}


def gap_signals(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract candidate-worthy gap signals from a built completion report.

    Pure function over the report dict: drift findings (new-drift,
    regressed, needs-decision, unverified-change) plus required tiers with
    no passing evidence. No I/O, so it unit-tests without a run directory.
    """
    if not isinstance(report, dict):
        return []
    tests = report.get("tests", {}) if isinstance(report.get("tests"), dict) else {}
    passed_tiers = {str(value) for value in tests.get("passed_tiers", []) or []}
    signals: list[dict[str, Any]] = []
    for requirement in (report.get("requirement_status", {}) or {}).get("requirements", []):
        if not isinstance(requirement, dict):
            continue
        uid = str(requirement.get("requirement_uid", ""))
        for finding in requirement.get("drift", []) or []:
            if not isinstance(finding, dict):
                continue
            classification = str(finding.get("classification", ""))
            if classification in {"new-drift", "regressed", "needs-decision", "unverified-change"}:
                signals.append({
                    "kind": "drift-finding",
                    "requirement_uid": uid,
                    "display_id": str(requirement.get("display_id", uid)),
                    "classification": classification,
                })
        for check in tests.get("required_checks", []) or []:
            if not isinstance(check, dict):
                continue
            if uid not in {str(value) for value in check.get("requirement_uids", []) or []}:
                continue
            for tier in check.get("tiers", []) or []:
                if str(tier) not in passed_tiers:
                    display_id = str(requirement.get("display_id", uid))
                    signals.append({
                        "kind": "unproven-tier",
                        "requirement_uid": uid,
                        "display_id": display_id,
                        "tier": str(tier),
                        "text": f"{display_id}: required tier `{tier}` has no passing evidence",
                    })
    return signals


def draft_gap_candidates(root: Path, run_id: str) -> dict[str, Any]:
    """Draft learning candidates from closure gaps (staged, never promoted).

    Reads the completion report's drift findings and unverified tiers and
    stages one candidate file per distinct gap signal, following the same
    candidate-only discipline as capture(): sanitized, deduplicated by
    content hash, promotion explicitly deferred to learning review. Returns
    drafted/skipped counts with artifact paths. Read-only against the run
    except the staged candidate files themselves.
    """
    root = root.resolve()
    report = REPORT.build(root, run_id, record=False)
    directory = L.state_dir(root, run_id) / "gap-learning"
    drafted: list[str] = []
    skipped: list[str] = []
    seen: set[str] = set()
    signals = gap_signals(report)
    directory.mkdir(parents=True, exist_ok=True)
    for signal in signals:
        candidate_id = "gap-" + hashlib.sha256(canonical(signal).encode("utf-8")).hexdigest()[:16]
        if candidate_id in seen:
            skipped.append(candidate_id)
            continue
        seen.add(candidate_id)
        path = directory / f"{candidate_id}.json"
        if path.is_file():
            skipped.append(candidate_id)
            continue
        payload = {
            "schema_version": "1",
            "type": "tailtrail-gap-learning-candidate",
            "candidate_id": candidate_id,
            "run_id": run_id,
            "signal": signal,
            "promotion": "candidate-only; explicit learning review required",
            "sanitization": "No raw source, prompt, log, repository name, user identity, or customer data is stored.",
            "boundary": "This candidate records one observed gap. It is not a rule, a quality claim, or an automatic future-agent instruction.",
        }
        L.atomic_json(path, payload)
        drafted.append(candidate_id)
    return {"drafted": sorted(drafted), "skipped": sorted(skipped),
            "artifact_dir": directory.relative_to(root).as_posix()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--accepted-by", choices=("user", "trusted-ci"), required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(capture(args.root, args.run_id, args.accepted_by), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Closure positive learning error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
