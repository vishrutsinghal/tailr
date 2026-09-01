#!/usr/bin/env python3
"""Append-only learning use decisions and evidence-backed closure attribution."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STREAM = Path("learning/use-receipts.jsonl")
DECISIONS = {"applied", "advisory", "ignored", "rejected", "stale"}
DECISION_TYPES = {
    "implementation", "validation", "architecture", "behavior", "maintainability",
    "dependency", "security", "release", "data-migration", "debugging", "review", "other",
}
HIGH_RISK_TYPES = {"dependency", "security", "release", "data-migration"}
ASSOCIATION_DELTAS = {
    "potentially-helped": 2,
    "neutral": 0,
    "insufficient": -3,
    "possible-harm": -6,
    "rejected-by-evidence": -4,
    "stale": -5,
    "inconclusive": 0,
}
EVENT_TYPE = "tailtrail-learning-use-receipt-event"


def load(name: str, relative: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V3 = load("learning_use_receipt_v3", "learning-v3.py")
L = load("learning_use_receipt_ledger", "run-ledger.py")
LOCK = load("learning_use_receipt_lock", "planning-lock.py")
CONTRACT = load("learning_use_receipt_contract", "closure-contract.py")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def stream(root: Path, run_id: str) -> Path:
    if not run_id or Path(run_id).name != run_id or run_id in {".", ".."}:
        raise ValueError("run_id must be a single local run identifier")
    return L.state_dir(root.resolve(), run_id) / STREAM


def relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def clean_ref(value: str) -> str:
    ref = Path(str(value)).as_posix()
    if not V3.safe_relative(ref):
        raise ValueError("learning receipt evidence references must be project-relative")
    return ref


def event_digest(event: dict[str, Any]) -> str:
    unsigned = copy.deepcopy(event)
    unsigned["chain"].pop("digest", None)
    return digest(unsigned)


def validate_event(event: dict[str, Any], *, expected_frame: str | None = None) -> list[str]:
    issues: list[str] = []
    top = {
        "schema_version", "type", "event_id", "sequence", "receipt_id", "run_id", "event_kind",
        "learning_id", "learning_record_id", "project_frame", "requirement_uids", "decision_type",
        "decision", "recorded_at", "previous_event_id", "proposal", "evidence_refs", "rationale",
        "outcome", "utility", "privacy", "chain", "boundary",
    }
    if set(event) != top:
        issues.append("learning use receipt contract is not closed")
    if event.get("schema_version") != "1" or event.get("type") != EVENT_TYPE:
        issues.append("learning use receipt identity is invalid")
    if event.get("event_kind") not in {"decision", "attribution"}:
        issues.append("event_kind is invalid")
    if not isinstance(event.get("sequence"), int) or int(event.get("sequence", 0)) < 1:
        issues.append("sequence must be positive")
    if not str(event.get("event_id", "")).startswith("lusevt-"):
        issues.append("event_id is invalid")
    if not str(event.get("receipt_id", "")).startswith("luse-"):
        issues.append("receipt_id is invalid")
    if not str(event.get("learning_id", "")).startswith("lrn-") or not str(event.get("learning_record_id", "")).startswith("lrnrec-"):
        issues.append("learning identity is invalid")
    frame = event.get("project_frame", {})
    if not isinstance(frame, dict) or set(frame) != {"kind", "id"} or frame.get("kind") != "repository":
        issues.append("project_frame is invalid")
    elif expected_frame and frame.get("id") != expected_frame:
        issues.append("learning use receipt crosses the project-frame boundary")
    uids = event.get("requirement_uids", [])
    if not isinstance(uids, list) or not uids or any(not isinstance(item, str) for item in uids) or uids != sorted(set(uids)):
        issues.append("requirement_uids must be a non-empty sorted unique string array")
    if event.get("decision_type") not in DECISION_TYPES or event.get("decision") not in DECISIONS:
        issues.append("decision or decision_type is invalid")
    refs = event.get("evidence_refs", [])
    if not isinstance(refs, list) or refs != sorted(set(refs)):
        issues.append("evidence_refs must be a sorted unique array")
    else:
        for ref in refs:
            try:
                clean_ref(ref)
            except ValueError as error:
                issues.append(str(error))
    try:
        V3.clean_text(str(event.get("rationale", "")))
    except V3.LearningV3Error as error:
        issues.append(str(error))
    if not event.get("rationale") or not event.get("recorded_at") or not event.get("boundary"):
        issues.append("recorded_at, rationale, and boundary are required")
    privacy = event.get("privacy", {})
    if not isinstance(privacy, dict) or set(privacy) != {"sanitized", "raw_prompt", "raw_source", "raw_log", "identity_fields"}:
        issues.append("privacy contract is invalid")
    elif privacy != {"sanitized": True, "raw_prompt": False, "raw_source": False, "raw_log": False, "identity_fields": False}:
        issues.append("learning receipt privacy boundary is invalid")
    if event.get("event_kind") == "decision":
        proposal = event.get("proposal")
        if not isinstance(proposal, dict) or set(proposal) != {"fingerprint", "task_frame_fingerprint", "applicability_score", "confidence_score"}:
            issues.append("decision event requires a closed proposal reference")
        elif (
            not str(proposal.get("fingerprint", "")).startswith("sha256:")
            or not str(proposal.get("task_frame_fingerprint", "")).startswith("sha256:")
            or not isinstance(proposal.get("applicability_score"), int)
            or not 0 <= proposal["applicability_score"] <= 100
            or not isinstance(proposal.get("confidence_score"), int)
            or not 0 <= proposal["confidence_score"] <= 100
        ):
            issues.append("decision proposal reference is invalid")
        if event.get("outcome") is not None or event.get("utility") is not None:
            issues.append("decision event cannot contain closure attribution")
    else:
        if event.get("proposal") is not None:
            issues.append("attribution event cannot repeat proposal content")
        outcome = event.get("outcome")
        utility = event.get("utility")
        if not isinstance(outcome, dict) or set(outcome) != {"completion_report_ref", "completion_fingerprint", "closure_status", "requirements", "drift_status", "drift_findings", "harnesses", "failure_status", "failures", "validation_status", "validation_refs", "association"}:
            issues.append("attribution event requires a closed outcome")
        elif outcome.get("association") not in ASSOCIATION_DELTAS:
            issues.append("attribution association is invalid")
        elif (
            outcome.get("closure_status") not in {"complete", "evidence-incomplete"}
            or outcome.get("validation_status") not in {"pass", "fail", "blocked", "unavailable", "not-evidenced"}
            or outcome.get("drift_status") not in {"present", "none", "not-assessed"}
            or outcome.get("failure_status") not in {"present", "none", "unrelated"}
            or not str(outcome.get("completion_fingerprint", "")).startswith("sha256:")
        ):
            issues.append("attribution outcome status or fingerprint is invalid")
        else:
            try:
                clean_ref(str(outcome.get("completion_report_ref", "")))
            except ValueError as error:
                issues.append(str(error))
            requirement_rows = outcome.get("requirements", [])
            if not isinstance(requirement_rows, list) or {
                str(item.get("requirement_uid")) for item in requirement_rows if isinstance(item, dict)
            } != set(event.get("requirement_uids", [])):
                issues.append("attribution outcome must cover every linked requirement")
            elif any(
                set(item) != {"requirement_uid", "status"}
                or item.get("status") not in {"complete", "incomplete", "not-evidenced"}
                for item in requirement_rows if isinstance(item, dict)
            ):
                issues.append("attribution requirement outcome is invalid")
            harness_rows = outcome.get("harnesses", [])
            if not isinstance(harness_rows, list) or any(
                not isinstance(item, dict) or set(item) != {"name", "status", "artifact"} or not item.get("name") or not item.get("status")
                for item in harness_rows
            ):
                issues.append("attribution Harness outcomes are invalid")
            for item in harness_rows if isinstance(harness_rows, list) else []:
                if item.get("artifact") is not None:
                    try:
                        clean_ref(str(item["artifact"]))
                    except ValueError as error:
                        issues.append(str(error))
            validation_refs = outcome.get("validation_refs", [])
            if not isinstance(validation_refs, list) or validation_refs != sorted(set(validation_refs)):
                issues.append("attribution validation references are invalid")
            else:
                for ref in validation_refs:
                    try:
                        clean_ref(str(ref))
                    except ValueError as error:
                        issues.append(str(error))
            drift_rows = outcome.get("drift_findings", [])
            if not isinstance(drift_rows, list) or any(
                not isinstance(item, dict) or set(item) != {"requirement_uid", "classification"}
                for item in drift_rows
            ):
                issues.append("attribution drift evidence is invalid")
            failure_rows = outcome.get("failures", [])
            if not isinstance(failure_rows, list) or any(
                not isinstance(item, dict) or set(item) != {"failure_id", "requirement_uid", "classification"}
                for item in failure_rows
            ):
                issues.append("attribution failure evidence is invalid")
        if not isinstance(utility, dict) or set(utility) != {"association", "base_delta", "applied_delta", "domain_cap", "cumulative_domain_delta", "causal_claim", "basis"}:
            issues.append("attribution event requires a closed utility update")
        elif utility.get("causal_claim") is not False or utility.get("association") != (outcome or {}).get("association"):
            issues.append("utility must remain a non-causal observed association")
        else:
            expected_cap = 5 if event.get("decision_type") in HIGH_RISK_TYPES else 10
            if utility.get("base_delta") != ASSOCIATION_DELTAS.get(utility.get("association")):
                issues.append("utility base delta does not match the observed association")
            if utility.get("domain_cap") != expected_cap:
                issues.append("utility domain cap does not match the decision type")
            if not isinstance(utility.get("applied_delta"), int) or not -expected_cap <= utility["applied_delta"] <= expected_cap:
                issues.append("utility applied delta exceeds the domain cap")
            if not isinstance(utility.get("cumulative_domain_delta"), int) or not -expected_cap <= utility["cumulative_domain_delta"] <= expected_cap:
                issues.append("utility cumulative delta exceeds the domain cap")
    chain = event.get("chain", {})
    if not isinstance(chain, dict) or set(chain) != {"previous_digest", "digest"}:
        issues.append("receipt digest chain is invalid")
    elif chain.get("digest") != event_digest(event):
        issues.append("receipt event digest is invalid")
    return issues


def read_events(root: Path, run_id: str) -> list[dict[str, Any]]:
    target = stream(root, run_id)
    if not target.is_file():
        return []
    events: list[dict[str, Any]] = []
    prior_digest: str | None = None
    latest_by_receipt: dict[str, str] = {}
    frame = V3.project_frame(root)
    for line_number, line in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid learning receipt JSON on line {line_number}: {error}") from error
        issues = validate_event(event, expected_frame=frame)
        if event.get("run_id") != run_id:
            issues.append("receipt event run_id does not match its run-local stream")
        if event.get("sequence") != len(events) + 1:
            issues.append("receipt sequence is not contiguous")
        if (event.get("chain") or {}).get("previous_digest") != prior_digest:
            issues.append("receipt digest chain is broken")
        expected_previous = latest_by_receipt.get(str(event.get("receipt_id")))
        if event.get("previous_event_id") != expected_previous:
            issues.append("receipt lifecycle predecessor is invalid")
        if issues:
            raise ValueError(f"invalid learning receipt on line {line_number}: {'; '.join(issues)}")
        events.append(event)
        prior_digest = event["chain"]["digest"]
        latest_by_receipt[event["receipt_id"]] = event["event_id"]
    return events


def append_event(root: Path, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    target = stream(root, run_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    with L.RunLock(target.with_suffix(".lock")):
        events = read_events(root, run_id)
        saved = copy.deepcopy(payload)
        latest = latest_by_receipt(events).get(str(saved.get("receipt_id")))
        expected_previous = latest["event_id"] if latest else None
        if saved.get("previous_event_id") != expected_previous:
            raise ValueError("learning receipt lifecycle changed before append; retry from current state")
        saved["sequence"] = len(events) + 1
        saved["chain"] = {"previous_digest": events[-1]["chain"]["digest"] if events else None, "digest": "0" * 64}
        event_seed = {key: value for key, value in saved.items() if key not in {"event_id", "chain"}}
        saved["event_id"] = "lusevt-" + digest({"seed": event_seed, "previous": saved["chain"]["previous_digest"]})[:20]
        saved["chain"]["digest"] = event_digest(saved)
        issues = validate_event(saved, expected_frame=V3.project_frame(root))
        if issues:
            raise ValueError("invalid learning receipt write: " + "; ".join(issues))
        with target.open("a", encoding="utf-8") as handle:
            handle.write(canonical(saved) + "\n")
    return saved


def saved_proposal(root: Path, run_id: str) -> tuple[dict[str, Any], str]:
    path = L.state_dir(root, run_id) / "planning" / "start-report-v1.json"
    if not path.is_file():
        raise ValueError("saved Start report is required before recording a learning decision")
    raw = json.loads(path.read_text(encoding="utf-8"))
    report = raw.get("report", raw) if isinstance(raw, dict) else {}
    navigator = report.get("navigator", report) if isinstance(report, dict) else {}
    proposal = navigator.get("learning_use_proposal") if isinstance(navigator, dict) else None
    if not isinstance(proposal, dict) or proposal.get("type") != "tailtrail-learning-use-proposal":
        raise ValueError("saved Start report has no Learning V3 use proposal")
    return proposal, relative(root, path)


def proposal_row(proposal: dict[str, Any], learning_id: str) -> tuple[dict[str, Any], str]:
    for source in ("matches", "blocked"):
        for item in proposal.get(source, []):
            if isinstance(item, dict) and item.get("learning_id") == learning_id:
                return item, source
    raise ValueError("learning_id was not surfaced by the saved use proposal")


def latest_by_receipt(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for event in events:
        result[event["receipt_id"]] = event
    return result


def decision_events(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["event_kind"] == "decision":
            result[event["receipt_id"]] = event
    return result


def receipt_id(run_id: str, learning_id: str, requirement_uids: list[str], decision_type: str) -> str:
    return "luse-" + digest({"run_id": run_id, "learning_id": learning_id, "requirements": sorted(set(requirement_uids)), "decision_type": decision_type})[:20]


def record_decision(
    root: Path,
    run_id: str,
    *,
    learning_id: str,
    decision: str,
    decision_type: str,
    requirement_uids: list[str],
    rationale: str,
    evidence_refs: list[str] | None = None,
    approved: bool,
) -> dict[str, Any]:
    if approved is not True:
        raise ValueError("learning use decision recording requires --approved")
    root = root.resolve()
    LOCK.assert_write_allowed(root, run_id)
    if decision not in DECISIONS or decision_type not in DECISION_TYPES:
        raise ValueError("unsupported learning decision or decision type")
    known = CONTRACT.approved_requirement_uids(root, run_id)
    uids = sorted(set(requirement_uids))
    if not uids or set(uids) - known:
        raise ValueError("learning receipt must reference known approved requirement UID(s)")
    proposal, proposal_ref = saved_proposal(root, run_id)
    row, source = proposal_row(proposal, learning_id)
    if decision in {"applied", "advisory"} and source != "matches":
        raise ValueError("blocked learning advice cannot be recorded as applied or advisory")
    records = V3.read_records(root)
    record = next((item for item in records if item["record_id"] == row.get("record_id") and item["learning_id"] == learning_id), None)
    if record is None:
        raise ValueError("saved proposal learning record is missing from the canonical V3 chain")
    current = V3.latest_records(records).get(learning_id)
    if decision in {"applied", "advisory"} and (
        current is None or current["record_id"] != record["record_id"] or current["freshness"]["status"] != "current"
    ):
        raise ValueError("changed or terminal learning advice cannot be recorded as applied or advisory")
    rid = receipt_id(run_id, learning_id, uids, decision_type)
    events = read_events(root, run_id)
    latest = latest_by_receipt(events).get(rid)
    proposal_fingerprint = "sha256:" + digest(proposal)
    refs = sorted(set([proposal_ref, *(clean_ref(item) for item in (evidence_refs or []))]))
    cleaned_rationale = V3.clean_text(rationale)
    if latest and latest["event_kind"] == "decision" and latest["decision"] == decision and latest["proposal"]["fingerprint"] == proposal_fingerprint and latest["rationale"] == cleaned_rationale and latest["evidence_refs"] == refs:
        return {**latest, "reused": True, "artifact": relative(root, stream(root, run_id))}
    payload = {
        "schema_version": "1", "type": EVENT_TYPE, "event_id": "lusevt-pending", "sequence": 1,
        "receipt_id": rid, "run_id": run_id, "event_kind": "decision", "learning_id": learning_id,
        "learning_record_id": record["record_id"], "project_frame": record["applicability"]["project_frame"],
        "requirement_uids": uids, "decision_type": decision_type, "decision": decision,
        "recorded_at": now(), "previous_event_id": latest["event_id"] if latest else None,
        "proposal": {
            "fingerprint": proposal_fingerprint,
            "task_frame_fingerprint": "sha256:" + digest(proposal["task_frame"]),
            "applicability_score": int(row.get("applicability_score", 0)),
            "confidence_score": int(row.get("confidence_score", 0)),
        },
        "evidence_refs": refs, "rationale": cleaned_rationale, "outcome": None, "utility": None,
        "privacy": {"sanitized": True, "raw_prompt": False, "raw_source": False, "raw_log": False, "identity_fields": False},
        "chain": {"previous_digest": None, "digest": "0" * 64},
        "boundary": "Explicit use decision only. It records no causal effect and grants no source, command, Git, deployment, or acceptance authority.",
    }
    saved = append_event(root, run_id, payload)
    L.append_event(root, run_id, "learning_use_decision_recorded", {"receipt_id": rid, "event_id": saved["event_id"], "learning_id": learning_id, "decision": decision, "requirement_uids": uids, "artifact": relative(root, stream(root, run_id))})
    return {**saved, "reused": False, "artifact": relative(root, stream(root, run_id))}


def association(decision: dict[str, Any], completion: dict[str, Any]) -> str:
    if decision["decision"] == "stale":
        return "stale"
    if decision["decision"] == "rejected":
        return "rejected-by-evidence" if len(decision["evidence_refs"]) > 1 else "neutral"
    if decision["decision"] in {"ignored", "advisory"}:
        return "neutral"
    uids = set(decision["requirement_uids"])
    requirements = [item for item in completion["requirement_status"]["requirements"] if item.get("requirement_uid") in uids]
    drift = [item for item in completion["drift"]["findings"] if item.get("requirement_uid") in uids]
    failures = [item for item in completion["execution_failures"].get("unresolved", []) if item.get("requirement_uid") in uids]
    if drift:
        return "possible-harm"
    if failures or completion["tests"]["status"] == "fail":
        return "insufficient"
    if requirements and all(item.get("status") == "complete" for item in requirements) and completion["tests"]["status"] == "pass":
        return "potentially-helped"
    return "inconclusive"


def project_events(root: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    runs = root.resolve() / ".tailtrail" / "runs"
    for target in sorted(runs.glob("*/learning/use-receipts.jsonl")) if runs.is_dir() else []:
        events.extend(read_events(root, target.parents[1].name))
    return events


def active_attributions(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        grouped.setdefault(event["receipt_id"], []).append(event)
    active: list[dict[str, Any]] = []
    for rows in grouped.values():
        latest_decision_index = max((index for index, row in enumerate(rows) if row["event_kind"] == "decision"), default=-1)
        if latest_decision_index < 0:
            continue
        later = [row for row in rows[latest_decision_index + 1:] if row["event_kind"] == "attribution"]
        if later:
            active.append(later[-1])
    return active


def utility_adjustments(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for event in active_attributions(project_events(root)):
        row = result.setdefault(event["learning_id"], {"total_delta": 0, "attribution_count": 0, "associations": []})
        row["total_delta"] = max(-20, min(20, row["total_delta"] + int(event["utility"]["applied_delta"])))
        row["attribution_count"] += 1
        row["associations"].append(event["outcome"]["association"])
    for row in result.values():
        row["associations"] = sorted(row["associations"])
    return result


def domain_cumulative(root: Path, learning_id: str, decision_type: str, *, exclude_receipt: str | None = None) -> int:
    return sum(
        int(event["utility"]["applied_delta"])
        for event in active_attributions(project_events(root))
        if event["learning_id"] == learning_id and event["decision_type"] == decision_type and event["receipt_id"] != exclude_receipt
    )


def outcome_payload(decision: dict[str, Any], completion: dict[str, Any], completion_ref: str) -> tuple[dict[str, Any], dict[str, Any]]:
    uids = set(decision["requirement_uids"])
    requirements = sorted(
        ({"requirement_uid": item["requirement_uid"], "status": item["status"]} for item in completion["requirement_status"]["requirements"] if item.get("requirement_uid") in uids),
        key=lambda item: item["requirement_uid"],
    )
    relation = association(decision, completion)
    relevant_drift = [item for item in completion["drift"]["findings"] if item.get("requirement_uid") in uids]
    relevant_failures = [item for item in completion["execution_failures"].get("unresolved", []) if item.get("requirement_uid") in uids]
    drift_findings = sorted(({
        "requirement_uid": str(item.get("requirement_uid", "")),
        "classification": str(item.get("classification", "unclassified")),
    } for item in relevant_drift), key=lambda item: (item["requirement_uid"], item["classification"]))
    failures = sorted(({
        "failure_id": str(item.get("failure_id", "unknown")),
        "requirement_uid": str(item.get("requirement_uid", "")),
        "classification": str(item.get("classification", "unclassified")),
    } for item in relevant_failures), key=lambda item: (item["requirement_uid"], item["failure_id"]))
    harnesses = []
    for item in completion["harnesses"]:
        artifact = item.get("artifact")
        artifact_ref = clean_ref(f".tailtrail/runs/{decision['run_id']}/{artifact}") if artifact else None
        harnesses.append({"name": item["name"], "status": item["status"], "artifact": artifact_ref})
    harnesses.sort(key=lambda item: item["name"])
    validation_refs = sorted({clean_ref(str(item)) for item in completion["tests"].get("receipt_refs", [])})
    fingerprint_source = {
        "overall_status": completion["overall_status"], "requirements": requirements,
        "drift": drift_findings, "harnesses": harnesses,
        "failures": failures, "validation": completion["tests"]["status"],
        "validation_refs": validation_refs, "association": relation,
    }
    outcome = {
        "completion_report_ref": completion_ref,
        "completion_fingerprint": "sha256:" + digest(fingerprint_source),
        "closure_status": completion["overall_status"],
        "requirements": requirements,
        "drift_status": "present" if relevant_drift else ("none" if completion["drift"]["status"] == "none-unresolved" else "not-assessed"),
        "drift_findings": drift_findings,
        "harnesses": harnesses,
        "failure_status": "present" if relevant_failures else ("none" if completion["execution_failures"]["status"] != "unresolved" else "unrelated"),
        "failures": failures,
        "validation_status": completion["tests"]["status"],
        "validation_refs": validation_refs,
        "association": relation,
    }
    cap = 5 if decision["decision_type"] in HIGH_RISK_TYPES else 10
    cumulative = domain_cumulative(Path(completion["_root"]), decision["learning_id"], decision["decision_type"], exclude_receipt=decision["receipt_id"])
    base = ASSOCIATION_DELTAS[relation]
    applied = max(-cap - cumulative, min(cap - cumulative, base))
    utility = {
        "association": relation, "base_delta": base, "applied_delta": applied,
        "domain_cap": cap, "cumulative_domain_delta": cumulative + applied,
        "causal_claim": False,
        "basis": "Observed closure association only; the domain cap prevents repeated receipts from becoming an unbounded confidence claim.",
    }
    return outcome, utility


def attribute_completion(root: Path, run_id: str, completion: dict[str, Any], *, record: bool = True, completion_ref: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    events = read_events(root, run_id)
    decisions = decision_events(events)
    if not decisions:
        return {"status": "no-receipts", "decisions": 0, "attributed": 0, "associations": {}, "artifact": None, "boundary": "No learning use decision was recorded for this run; closure inferred no influence."}
    if record:
        LOCK.assert_write_allowed(root, run_id)
    project_guard = L.RunLock(root / ".tailtrail" / "learning-use-attribution.lock") if record else nullcontext()
    with project_guard:
        ref = completion_ref or f".tailtrail/runs/{run_id}/completion-reports/pending.json"
        completion_for_outcome = {**completion, "_root": root.as_posix()}
        attributed: list[dict[str, Any]] = []
        for rid, decision in sorted(decisions.items()):
            latest = latest_by_receipt(read_events(root, run_id)).get(rid)
            outcome, utility = outcome_payload(decision, completion_for_outcome, ref)
            latest_outcome = latest.get("outcome") if latest else None
            latest_ref = latest_outcome.get("completion_report_ref") if isinstance(latest_outcome, dict) else None
            latest_ref_exists = isinstance(latest_ref, str) and (root / latest_ref).is_file()
            if (
                latest and latest["event_kind"] == "attribution"
                and latest["outcome"]["completion_fingerprint"] == outcome["completion_fingerprint"]
                and (latest_ref == ref or latest_ref_exists)
            ):
                attributed.append({
                    "receipt_id": rid, "event_id": latest["event_id"],
                    "learning_id": decision["learning_id"], "requirement_uids": decision["requirement_uids"],
                    "decision_type": decision["decision_type"], "decision": decision["decision"],
                    "association": latest["outcome"]["association"],
                    "utility_delta": latest["utility"]["applied_delta"], "reused": True,
                })
                continue
            payload = {
                "schema_version": "1", "type": EVENT_TYPE, "event_id": "lusevt-pending", "sequence": 1,
                "receipt_id": rid, "run_id": run_id, "event_kind": "attribution", "learning_id": decision["learning_id"],
                "learning_record_id": decision["learning_record_id"], "project_frame": decision["project_frame"],
                "requirement_uids": decision["requirement_uids"], "decision_type": decision["decision_type"], "decision": decision["decision"],
                "recorded_at": now(), "previous_event_id": latest["event_id"] if latest else decision["event_id"],
                "proposal": None,
                "evidence_refs": sorted(set([
                    *decision["evidence_refs"], ref, *outcome["validation_refs"],
                    *(item["artifact"] for item in outcome["harnesses"] if item["artifact"]),
                ])),
                "rationale": "Categorical attribution from saved completion evidence.", "outcome": outcome, "utility": utility,
                "privacy": {"sanitized": True, "raw_prompt": False, "raw_source": False, "raw_log": False, "identity_fields": False},
                "chain": {"previous_digest": None, "digest": "0" * 64},
                "boundary": "Observed association only. This event does not prove causality, authorize reuse, or convert missing closure evidence into success.",
            }
            saved = append_event(root, run_id, payload) if record else payload
            if record:
                L.append_event(root, run_id, "learning_use_attribution_recorded", {"receipt_id": rid, "event_id": saved["event_id"], "learning_id": saved["learning_id"], "association": outcome["association"], "utility_delta": utility["applied_delta"], "artifact": relative(root, stream(root, run_id))})
            attributed.append({
                "receipt_id": rid, "event_id": saved["event_id"] if record else None,
                "learning_id": decision["learning_id"], "requirement_uids": decision["requirement_uids"],
                "decision_type": decision["decision_type"], "decision": decision["decision"],
                "association": outcome["association"], "utility_delta": utility["applied_delta"],
                "reused": False,
            })
        associations: dict[str, int] = {}
        for item in attributed:
            associations[item["association"]] = associations.get(item["association"], 0) + 1
        return {
            "status": "attributed" if record else "preview", "decisions": len(decisions), "attributed": len(attributed),
            "associations": associations, "receipts": attributed,
            "artifact": relative(root, stream(root, run_id)) if record else None,
            "boundary": "Requirement-linked observed associations only; no receipt is represented as causal improvement.",
        }


def show(root: Path, run_id: str) -> dict[str, Any]:
    events = read_events(root.resolve(), run_id)
    return {
        "schema_version": "1", "type": "tailtrail-learning-use-receipt-log", "run_id": run_id,
        "events": events, "count": len(events), "utility": utility_adjustments(root.resolve()),
        "boundary": "Read-only sanitized receipt state; no learning decision, attribution, command, source, or task state was changed.",
    }


def validate(root: Path, run_id: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    issues: list[str] = []
    runs = [run_id] if run_id else [path.name for path in sorted((root / ".tailtrail" / "runs").glob("*")) if path.is_dir()]
    count = 0
    for candidate in runs:
        try:
            count += len(read_events(root, candidate))
        except (OSError, ValueError, json.JSONDecodeError) as error:
            issues.append(f"{candidate}: {error}")
    return {
        "schema_version": "1", "type": "tailtrail-learning-use-receipt-validation",
        "status": "passed" if not issues else "failed", "events": count, "issues": issues,
        "boundary": "Read-only structural, project-frame, lifecycle, and digest-chain validation.",
    }


def split_csv(value: str | None) -> list[str]:
    return sorted({item.strip() for item in (value or "").split(",") if item.strip()})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    record = sub.add_parser("record")
    record.add_argument("--root", type=Path, default=Path.cwd()); record.add_argument("--run-id", required=True)
    record.add_argument("--learning-id", required=True); record.add_argument("--decision", choices=sorted(DECISIONS), required=True)
    record.add_argument("--decision-type", choices=sorted(DECISION_TYPES), required=True)
    record.add_argument("--requirement-uid", action="append", default=[]); record.add_argument("--rationale", required=True)
    record.add_argument("--evidence-ref", action="append", default=[]); record.add_argument("--approved", action="store_true")
    attribute = sub.add_parser("attribute")
    attribute.add_argument("--root", type=Path, default=Path.cwd()); attribute.add_argument("--run-id", required=True)
    attribute.add_argument("--completion-report", type=Path); attribute.add_argument("--approved", action="store_true")
    show_parser = sub.add_parser("show"); show_parser.add_argument("--root", type=Path, default=Path.cwd()); show_parser.add_argument("--run-id", required=True)
    validate_parser = sub.add_parser("validate"); validate_parser.add_argument("--root", type=Path, default=Path.cwd()); validate_parser.add_argument("--run-id")
    args = parser.parse_args()
    try:
        if args.command == "record":
            result = record_decision(args.root, args.run_id, learning_id=args.learning_id, decision=args.decision, decision_type=args.decision_type, requirement_uids=args.requirement_uid, rationale=args.rationale, evidence_refs=args.evidence_ref, approved=args.approved)
        elif args.command == "attribute":
            if not args.approved:
                raise ValueError("learning use attribution requires --approved")
            root = args.root.resolve()
            path = args.completion_report
            if path is not None and not path.is_absolute():
                path = root / path
            path = path or sorted((L.state_dir(root, args.run_id) / "completion-reports").glob("report-*.json"))[-1]
            completion = json.loads(path.read_text(encoding="utf-8"))
            result = attribute_completion(root, args.run_id, completion, record=True, completion_ref=relative(root, path.resolve()))
        elif args.command == "show":
            result = show(args.root, args.run_id)
        else:
            result = validate(args.root, args.run_id)
        print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result.get("status") != "failed" else 1
    except (OSError, ValueError, IndexError, json.JSONDecodeError, V3.LearningV3Error) as error:
        print(f"Learning use receipt error: {error}"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
