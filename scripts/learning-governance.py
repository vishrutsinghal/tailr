#!/usr/bin/env python3
"""PM-L4 challenge, conflict, revalidation, and negative-learning governance."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LEDGER = Path(".tailtrail/learning-conflicts.jsonl")
EVENT_TYPE = "tailtrail-learning-governance-event"
NEGATIVE_THRESHOLD = 2
ACTIONS = {
    "challenge", "confirm", "amend", "supersede", "revoke", "conflict",
    "learning-a-wins", "learning-b-wins", "both-revoked", "scoped-coexistence",
    "revalidate", "negative-candidate", "promote", "dismiss",
}
OPEN_ACTIONS = {"challenge", "conflict", "negative-candidate"}
RESOLUTIONS = ACTIONS - OPEN_ACTIONS - {"revalidate"}
SIGNAL_DECISIONS = {"rejected", "stale"}
SIGNAL_ASSOCIATIONS = {"possible-harm", "rejected-by-evidence", "stale"}


def load(name: str, relative: str) -> Any:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


V3 = load("learning_governance_v3", "learning-v3.py")
RECEIPTS = load("learning_governance_receipts", "learning-use-receipt.py")
LOCKS = load("learning_governance_ledger", "run-ledger.py")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def event_digest(event: dict[str, Any]) -> str:
    unsigned = copy.deepcopy(event)
    unsigned["chain"].pop("digest", None)
    return digest(unsigned)


def safe_evidence(root: Path, refs: list[str], *, required: bool = True) -> list[str]:
    values = sorted(set(refs))
    if required and not values:
        raise ValueError("governance transition requires evidence by project-relative reference")
    for ref in values:
        if not V3.safe_relative(ref) or not (root / ref).is_file():
            raise ValueError("governance evidence must be an existing project-relative file")
    return values


def validate_event(event: dict[str, Any], *, expected_frame: str | None = None) -> list[str]:
    issues: list[str] = []
    top = {
        "schema_version", "type", "event_id", "sequence", "entity_id", "event_kind", "action",
        "learning_ids", "record_ids", "project_frame", "reason", "evidence_refs", "created_at",
        "actor", "approved", "previous_event_id", "invalidator_snapshot", "negative_signal",
        "promoted_learning_id", "privacy", "chain", "boundary",
    }
    if set(event) != top:
        issues.append("learning governance contract is not closed")
    if event.get("schema_version") != "1" or event.get("type") != EVENT_TYPE:
        issues.append("learning governance identity is invalid")
    if event.get("event_kind") not in {"challenge", "conflict", "revalidation", "negative-learning"}:
        issues.append("event_kind is invalid")
    if event.get("action") not in ACTIONS:
        issues.append("action is invalid")
    kind_actions = {
        "challenge": {"challenge", "confirm", "amend", "supersede", "revoke"},
        "conflict": {"conflict", "learning-a-wins", "learning-b-wins", "both-revoked", "scoped-coexistence"},
        "revalidation": {"revalidate"},
        "negative-learning": {"negative-candidate", "promote", "dismiss"},
    }
    if event.get("action") not in kind_actions.get(str(event.get("event_kind")), set()):
        issues.append("action does not belong to event_kind")
    if not isinstance(event.get("sequence"), int) or int(event.get("sequence", 0)) < 1:
        issues.append("sequence must be positive")
    if not re.fullmatch(r"lgov-[0-9a-f]{20}", str(event.get("event_id", ""))):
        issues.append("event_id is invalid")
    if not re.fullmatch(r"(chg|cnf|rvl|neg)-[0-9a-f]{20}", str(event.get("entity_id", ""))):
        issues.append("entity_id is invalid")
    learning_ids = event.get("learning_ids", [])
    if not isinstance(learning_ids, list) or not learning_ids or learning_ids != sorted(set(learning_ids)) or any(not str(item).startswith("lrn-") for item in learning_ids):
        issues.append("learning_ids must be a non-empty sorted unique array")
    record_ids = event.get("record_ids", [])
    if not isinstance(record_ids, list) or record_ids != sorted(set(record_ids)) or any(not str(item).startswith("lrnrec-") for item in record_ids):
        issues.append("record_ids must be a sorted unique array")
    frame = event.get("project_frame", {})
    if not isinstance(frame, dict) or set(frame) != {"kind", "id"} or frame.get("kind") != "repository":
        issues.append("project_frame is invalid")
    elif expected_frame and frame.get("id") != expected_frame:
        issues.append("governance event crosses the project-frame boundary")
    if event.get("approved") is not True or not event.get("actor") or not event.get("reason") or not event.get("boundary"):
        issues.append("approved actor, reason, and boundary are required")
    try:
        V3.clean_text(str(event.get("reason", "")))
    except V3.LearningV3Error as error:
        issues.append(str(error))
    refs = event.get("evidence_refs", [])
    if not isinstance(refs, list) or refs != sorted(set(refs)) or any(not V3.safe_relative(str(ref)) for ref in refs):
        issues.append("evidence_refs must be safe, sorted, and unique")
    snapshot = event.get("invalidator_snapshot")
    if snapshot is not None and (
        not isinstance(snapshot, dict) or set(snapshot) != V3.INVALIDATOR_KINDS
        or any(not re.fullmatch(r"sha256:[0-9a-f]{64}", str(value)) for value in snapshot.values())
    ):
        issues.append("invalidator_snapshot is invalid")
    signal = event.get("negative_signal")
    if signal is not None and (
        not isinstance(signal, dict) or set(signal) != {"count", "categories", "receipt_refs", "threshold"}
        or not isinstance(signal.get("count"), int) or signal.get("count", 0) < NEGATIVE_THRESHOLD
        or signal.get("threshold") != NEGATIVE_THRESHOLD
        or signal.get("categories") != sorted(set(signal.get("categories", [])))
        or signal.get("receipt_refs") != sorted(set(signal.get("receipt_refs", [])))
        or any(not V3.safe_relative(str(ref)) for ref in signal.get("receipt_refs", []))
    ):
        issues.append("negative_signal is invalid")
    promoted = event.get("promoted_learning_id")
    if promoted is not None and not str(promoted).startswith("lrn-"):
        issues.append("promoted_learning_id is invalid")
    privacy = event.get("privacy")
    if privacy != {"sanitized": True, "raw_failure": False, "raw_log": False, "raw_prompt": False, "identity_fields": False}:
        issues.append("privacy boundary is invalid")
    chain = event.get("chain", {})
    if not isinstance(chain, dict) or set(chain) != {"previous_digest", "digest"} or event_digest(event) != chain.get("digest"):
        issues.append("event digest is invalid")
    elif (
        chain.get("previous_digest") is not None
        and not re.fullmatch(r"[0-9a-f]{64}", str(chain.get("previous_digest")))
    ):
        issues.append("previous digest is invalid")
    return issues


def valid_transition(previous: dict[str, Any] | None, event: dict[str, Any]) -> bool:
    if previous is None:
        return event["action"] in OPEN_ACTIONS | {"revalidate"}
    allowed = {
        "challenge": {"confirm", "amend", "supersede", "revoke"},
        "conflict": {"learning-a-wins", "learning-b-wins", "both-revoked", "scoped-coexistence"},
        "negative-candidate": {"promote", "dismiss"},
    }
    return event["event_kind"] == previous["event_kind"] and event["action"] in allowed.get(previous["action"], set())


def read_events(root: Path) -> list[dict[str, Any]]:
    path = root / LEDGER
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    prior_digest: str | None = None
    latest: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid learning governance JSON on line {line_number}: {error}") from error
        issues = validate_event(event, expected_frame=V3.project_frame(root))
        if event.get("sequence") != len(events) + 1:
            issues.append("sequence is not contiguous")
        if (event.get("chain") or {}).get("previous_digest") != prior_digest:
            issues.append("append-only digest chain is broken")
        previous = latest.get(str(event.get("entity_id")))
        if event.get("previous_event_id") != (previous or {}).get("event_id"):
            issues.append("entity lifecycle predecessor is invalid")
        if not valid_transition(previous, event):
            issues.append("entity lifecycle transition is invalid")
        for ref in event.get("evidence_refs", []) if isinstance(event.get("evidence_refs"), list) else []:
            if not (root / str(ref)).is_file():
                issues.append(f"referenced governance evidence is missing: {ref}")
        signal = event.get("negative_signal")
        for ref in signal.get("receipt_refs", []) if isinstance(signal, dict) else []:
            if not (root / str(ref)).is_file():
                issues.append(f"referenced negative-learning receipt is missing: {ref}")
        if issues:
            raise ValueError(f"invalid learning governance event on line {line_number}: {'; '.join(issues)}")
        events.append(event)
        prior_digest = event["chain"]["digest"]
        latest[event["entity_id"]] = event
    return events


def append_event(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    target = root / LEDGER
    target.parent.mkdir(parents=True, exist_ok=True)
    with LOCKS.RunLock(target.with_suffix(".lock")):
        events = read_events(root)
        saved = copy.deepcopy(payload)
        current = next((item for item in reversed(events) if item["entity_id"] == saved["entity_id"]), None)
        if saved.get("previous_event_id") != (current or {}).get("event_id"):
            raise ValueError("governance entity changed before append; retry from current state")
        saved["sequence"] = len(events) + 1
        saved["chain"] = {"previous_digest": events[-1]["chain"]["digest"] if events else None, "digest": "0" * 64}
        seed = {key: value for key, value in saved.items() if key not in {"event_id", "chain"}}
        saved["event_id"] = "lgov-" + digest({"seed": seed, "previous": saved["chain"]["previous_digest"]})[:20]
        saved["chain"]["digest"] = event_digest(saved)
        issues = validate_event(saved, expected_frame=V3.project_frame(root))
        if issues:
            raise ValueError("invalid learning governance write: " + "; ".join(issues))
        with target.open("a", encoding="utf-8") as handle:
            handle.write(canonical(saved).decode("utf-8") + "\n")
    return saved


def base_event(
    root: Path, *, entity_id: str, event_kind: str, action: str, learning_ids: list[str],
    record_ids: list[str], reason: str, evidence_refs: list[str], previous_event_id: str | None = None,
    snapshot: dict[str, str] | None = None, signal: dict[str, Any] | None = None,
    promoted_learning_id: str | None = None, actor: str = "Learning Governance",
) -> dict[str, Any]:
    return {
        "schema_version": "1", "type": EVENT_TYPE, "event_id": "lgov-" + "0" * 20, "sequence": 1,
        "entity_id": entity_id, "event_kind": event_kind, "action": action,
        "learning_ids": sorted(set(learning_ids)), "record_ids": sorted(set(record_ids)),
        "project_frame": {"kind": "repository", "id": V3.project_frame(root)},
        "reason": V3.clean_text(reason), "evidence_refs": sorted(set(evidence_refs)), "created_at": now(),
        "actor": V3.clean_text(actor, limit=120), "approved": True, "previous_event_id": previous_event_id,
        "invalidator_snapshot": snapshot, "negative_signal": signal, "promoted_learning_id": promoted_learning_id,
        "privacy": {"sanitized": True, "raw_failure": False, "raw_log": False, "raw_prompt": False, "identity_fields": False},
        "chain": {"previous_digest": None, "digest": "0" * 64},
        "boundary": "Sanitized governance metadata only. Current source, policy, tests, CI, scanners, guardrails, and explicit user evidence always win.",
    }


def current_records(root: Path) -> dict[str, dict[str, Any]]:
    return V3.latest_records(V3.read_records(root))


def require_current(root: Path, learning_ids: list[str]) -> list[dict[str, Any]]:
    latest = current_records(root)
    records: list[dict[str, Any]] = []
    for learning_id in learning_ids:
        record = latest.get(learning_id)
        if not record or record["freshness"]["status"] != "current":
            raise ValueError(f"learning is not current: {learning_id}")
        records.append(record)
    return records


def latest_entities(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for event in events:
        result[event["entity_id"]] = event
    return result


def open_challenge(root: Path, learning_id: str, *, reason: str, evidence_refs: list[str], approved: bool) -> dict[str, Any]:
    if approved is not True:
        raise ValueError("challenge requires --approved")
    refs = safe_evidence(root, evidence_refs)
    record = require_current(root, [learning_id])[0]
    entity_id = "chg-" + digest({"learning_id": learning_id, "record_id": record["record_id"]})[:20]
    if entity_id in latest_entities(read_events(root)):
        raise ValueError("this learning record already has a challenge lifecycle")
    return append_event(root, base_event(root, entity_id=entity_id, event_kind="challenge", action="challenge", learning_ids=[learning_id], record_ids=[record["record_id"]], reason=reason, evidence_refs=refs))


def resolve_challenge(
    root: Path, entity_id: str, *, action: str, reason: str, evidence_refs: list[str], approved: bool,
    summary: str | None = None, advice: str | None = None, replacement_id: str | None = None,
    revalidate_after: str | None = None,
) -> dict[str, Any]:
    if approved is not True or action not in {"confirm", "amend", "supersede", "revoke"}:
        raise ValueError("challenge resolution requires --approved and a supported resolution")
    refs = safe_evidence(root, evidence_refs)
    current = latest_entities(read_events(root)).get(entity_id)
    if not current or current["event_kind"] != "challenge" or current["action"] != "challenge":
        raise ValueError("challenge is missing or already resolved")
    learning_id = current["learning_ids"][0]
    if action == "confirm":
        record = V3.revalidate(root, learning_id, reason=reason, evidence_refs=refs, revalidate_after=revalidate_after)
    elif action == "amend":
        record = V3.amend(root, learning_id, reason=reason, summary=summary, advice=advice)
    else:
        record = V3.terminal_transition(root, learning_id, action, reason, replacement_id)
    return append_event(root, base_event(
        root, entity_id=entity_id, event_kind="challenge", action=action, learning_ids=current["learning_ids"],
        record_ids=[*current["record_ids"], record["record_id"]], reason=reason, evidence_refs=[*current["evidence_refs"], *refs],
        previous_event_id=current["event_id"], snapshot=record["freshness"].get("invalidator_snapshot"),
    ))


def scope_overlap(first: dict[str, Any], second: dict[str, Any]) -> bool:
    a, b = first["applicability"], second["applicability"]
    fields = ("task_types", "tags", "path_patterns", "requirement_ids")
    return not any(set(a[field]) and set(b[field]) and set(a[field]).isdisjoint(b[field]) for field in fields)


def open_conflict(root: Path, learning_ids: list[str], *, reason: str, evidence_refs: list[str], approved: bool) -> dict[str, Any]:
    if approved is not True:
        raise ValueError("conflict recording requires --approved")
    ids = sorted(set(learning_ids))
    if len(ids) != 2:
        raise ValueError("a conflict requires exactly two distinct learning IDs")
    refs = safe_evidence(root, evidence_refs)
    records = require_current(root, ids)
    entity_id = "cnf-" + digest({"learning_ids": ids, "record_ids": sorted(item["record_id"] for item in records)})[:20]
    if entity_id in latest_entities(read_events(root)):
        raise ValueError("this learning pair already has a conflict lifecycle")
    return append_event(root, base_event(root, entity_id=entity_id, event_kind="conflict", action="conflict", learning_ids=ids, record_ids=[item["record_id"] for item in records], reason=reason, evidence_refs=refs))


def resolve_conflict(root: Path, entity_id: str, *, action: str, reason: str, evidence_refs: list[str], approved: bool) -> dict[str, Any]:
    if approved is not True or action not in {"learning-a-wins", "learning-b-wins", "both-revoked", "scoped-coexistence"}:
        raise ValueError("conflict resolution requires --approved and a supported resolution")
    refs = safe_evidence(root, evidence_refs)
    current = latest_entities(read_events(root)).get(entity_id)
    if not current or current["event_kind"] != "conflict" or current["action"] != "conflict":
        raise ValueError("conflict is missing or already resolved")
    records = require_current(root, current["learning_ids"])
    appended: list[str] = []
    if action == "scoped-coexistence":
        if scope_overlap(records[0], records[1]):
            raise ValueError("scoped coexistence requires demonstrably disjoint applicability")
    else:
        losers = records if action == "both-revoked" else [records[1 if action == "learning-a-wins" else 0]]
        for record in losers:
            appended.append(V3.terminal_transition(root, record["learning_id"], "revoke", reason)["record_id"])
    return append_event(root, base_event(root, entity_id=entity_id, event_kind="conflict", action=action, learning_ids=current["learning_ids"], record_ids=[*current["record_ids"], *appended], reason=reason, evidence_refs=[*current["evidence_refs"], *refs], previous_event_id=current["event_id"]))


def receipt_signals(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    runs = root / ".tailtrail" / "runs"
    if not runs.is_dir():
        return result
    revalidated = {
        learning_id: record["created_at"] for learning_id, record in current_records(root).items()
        if record["lifecycle"]["operation"] == "revalidate"
    }
    for directory in sorted(path for path in runs.iterdir() if path.is_dir()):
        receipt_path = directory / "learning" / "use-receipts.jsonl"
        if not receipt_path.is_file():
            continue
        events = RECEIPTS.read_events(root, directory.name)
        signaled: dict[str, tuple[str, str]] = {}
        for event in events:
            category = None
            if event["event_kind"] == "decision" and event["decision"] in SIGNAL_DECISIONS:
                category = event["decision"]
            elif event["event_kind"] == "attribution" and event["outcome"]["association"] in SIGNAL_ASSOCIATIONS:
                category = event["outcome"]["association"]
            if category and event["recorded_at"] > revalidated.get(event["learning_id"], ""):
                signaled[event["receipt_id"]] = (event["learning_id"], category)
        ref = receipt_path.relative_to(root).as_posix()
        for receipt_id, (learning_id, category) in signaled.items():
            row = result.setdefault(learning_id, {"receipt_ids": set(), "receipt_refs": set(), "categories": set()})
            row["receipt_ids"].add(receipt_id)
            row["receipt_refs"].add(ref)
            row["categories"].add(category)
    return {
        learning_id: {
            "count": len(row["receipt_ids"]), "categories": sorted(row["categories"]),
            "receipt_refs": sorted(row["receipt_refs"]), "threshold": NEGATIVE_THRESHOLD,
        }
        for learning_id, row in result.items() if len(row["receipt_ids"]) >= NEGATIVE_THRESHOLD
    }


def negative_candidates(root: Path) -> list[dict[str, Any]]:
    return [{"learning_id": learning_id, **signal} for learning_id, signal in sorted(receipt_signals(root).items())]


def record_negative_candidates(root: Path, *, approved: bool) -> list[dict[str, Any]]:
    if approved is not True:
        raise ValueError("negative candidate recording requires --approved")
    existing = latest_entities(read_events(root))
    saved: list[dict[str, Any]] = []
    for candidate in negative_candidates(root):
        record = require_current(root, [candidate["learning_id"]])[0]
        entity_id = "neg-" + digest({"learning_id": candidate["learning_id"], "record_id": record["record_id"], "receipt_refs": candidate["receipt_refs"]})[:20]
        if entity_id in existing:
            continue
        saved.append(append_event(root, base_event(
            root, entity_id=entity_id, event_kind="negative-learning", action="negative-candidate",
            learning_ids=[candidate["learning_id"]], record_ids=[record["record_id"]],
            reason="Repeated explicit rejection or adverse closure association requires avoid-history review",
            evidence_refs=candidate["receipt_refs"], signal={key: candidate[key] for key in ("count", "categories", "receipt_refs", "threshold")},
        )))
    return saved


def resolve_negative(
    root: Path, entity_id: str, *, action: str, reason: str, evidence_refs: list[str], approved: bool,
    summary: str | None = None, advice: str | None = None,
) -> dict[str, Any]:
    if approved is not True or action not in {"promote", "dismiss"}:
        raise ValueError("negative-learning resolution requires --approved and promote or dismiss")
    refs = safe_evidence(root, evidence_refs)
    current = latest_entities(read_events(root)).get(entity_id)
    if not current or current["event_kind"] != "negative-learning" or current["action"] != "negative-candidate":
        raise ValueError("negative-learning candidate is missing or already resolved")
    promoted: str | None = None
    appended = list(current["record_ids"])
    if action == "promote":
        if not summary or not advice:
            raise ValueError("promotion requires sanitized --summary and --advice")
        source = require_current(root, current["learning_ids"])[0]
        promoted = "lrn-avoid-" + digest({"entity_id": entity_id, "summary": summary, "advice": advice})[:16]
        line = next(index for index, event in enumerate(read_events(root), start=1) if event["event_id"] == current["event_id"])
        avoid = V3.build_record(
            root, learning_id=promoted, learning_class="avoid-history", summary=summary, advice=advice,
            source_kind="negative-learning-candidate", source_ref=f"{LEDGER.as_posix()}#line={line}",
            source_fingerprint="sha256:" + current["chain"]["digest"], captured_by="Learning Governance",
            task_types=source["applicability"]["task_types"], tags=source["applicability"]["tags"],
            path_patterns=source["applicability"]["path_patterns"], requirement_ids=source["applicability"]["requirement_ids"],
            evidence_refs=[*current["evidence_refs"], *refs], invalidators=source["freshness"]["invalidators"],
            stale_when=source["freshness"]["stale_when"], confidence_score=60,
        )
        appended.append(V3.append_record(root, avoid)["record_id"])
        appended.append(V3.terminal_transition(root, source["learning_id"], "revoke", reason)["record_id"])
    return append_event(root, base_event(
        root, entity_id=entity_id, event_kind="negative-learning", action=action,
        learning_ids=current["learning_ids"], record_ids=appended, reason=reason, evidence_refs=[*current["evidence_refs"], *refs],
        previous_event_id=current["event_id"], signal=current["negative_signal"], promoted_learning_id=promoted,
    ))


def record_revalidation(root: Path, learning_id: str, *, reason: str, evidence_refs: list[str], approved: bool, revalidate_after: str | None = None) -> dict[str, Any]:
    if approved is not True:
        raise ValueError("revalidation requires --approved")
    refs = safe_evidence(root, evidence_refs)
    record = V3.revalidate(root, learning_id, reason=reason, evidence_refs=refs, revalidate_after=revalidate_after)
    entity_id = "rvl-" + digest({"learning_id": learning_id, "record_id": record["record_id"]})[:20]
    return append_event(root, base_event(root, entity_id=entity_id, event_kind="revalidation", action="revalidate", learning_ids=[learning_id], record_ids=[record["record_id"]], reason=reason, evidence_refs=refs, snapshot=record["freshness"]["invalidator_snapshot"]))


def blocking_reasons(root: Path) -> dict[str, list[str]]:
    try:
        latest = latest_entities(read_events(root))
        result: dict[str, list[str]] = {}
        for event in latest.values():
            if event["action"] == "challenge":
                result.setdefault(event["learning_ids"][0], []).append(f"open governance challenge `{event['entity_id']}`")
            elif event["action"] == "conflict":
                for learning_id in event["learning_ids"]:
                    result.setdefault(learning_id, []).append(f"open governance conflict `{event['entity_id']}`")
            elif event["action"] == "negative-candidate":
                result.setdefault(event["learning_ids"][0], []).append(f"open negative-learning candidate `{event['entity_id']}`")
        signals = receipt_signals(root)
        for learning_id, signal in signals.items():
            resolved = any(
                event["event_kind"] == "negative-learning"
                and event["learning_ids"] == [learning_id]
                and event.get("negative_signal") == signal
                and event["action"] in {"dismiss", "promote"}
                for event in latest.values()
            )
            if resolved:
                continue
            result.setdefault(learning_id, []).append(f"repeated adverse learning evidence ({signal['count']} receipts; threshold {NEGATIVE_THRESHOLD})")
        return {key: sorted(set(value)) for key, value in result.items()}
    except (OSError, ValueError, json.JSONDecodeError, V3.LearningV3Error) as error:
        return {"*": [f"learning governance evidence is invalid: {error}"]}


def state(root: Path) -> dict[str, Any]:
    events = read_events(root)
    latest = latest_entities(events)
    return {
        "schema_version": "1", "type": "tailtrail-learning-governance-state", "events": len(events),
        "open": [event for event in latest.values() if event["action"] in OPEN_ACTIONS],
        "negative_candidates": negative_candidates(root), "blocking": blocking_reasons(root),
        "ledger": LEDGER.as_posix(),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    def common(item: argparse.ArgumentParser) -> None:
        item.add_argument("--root", type=Path, default=Path.cwd())
        item.add_argument("--format", choices=("json", "markdown"), default="json")
    state_parser = sub.add_parser("state"); common(state_parser)
    validate_parser = sub.add_parser("validate"); common(validate_parser)
    challenge = sub.add_parser("challenge")
    common(challenge)
    challenge.add_argument("--learning-id", required=True); challenge.add_argument("--reason", required=True); challenge.add_argument("--evidence-ref", action="append", default=[]); challenge.add_argument("--approved", action="store_true")
    resolve = sub.add_parser("challenge-resolve")
    common(resolve)
    resolve.add_argument("--challenge-id", required=True); resolve.add_argument("--resolution", required=True, choices=("confirm", "amend", "supersede", "revoke")); resolve.add_argument("--reason", required=True); resolve.add_argument("--evidence-ref", action="append", default=[]); resolve.add_argument("--summary"); resolve.add_argument("--advice"); resolve.add_argument("--replacement-id"); resolve.add_argument("--revalidate-after"); resolve.add_argument("--approved", action="store_true")
    conflict = sub.add_parser("conflict")
    common(conflict)
    conflict.add_argument("--learning-id", action="append", required=True); conflict.add_argument("--reason", required=True); conflict.add_argument("--evidence-ref", action="append", default=[]); conflict.add_argument("--approved", action="store_true")
    conflict_resolve = sub.add_parser("conflict-resolve")
    common(conflict_resolve)
    conflict_resolve.add_argument("--conflict-id", required=True); conflict_resolve.add_argument("--resolution", required=True, choices=("learning-a-wins", "learning-b-wins", "both-revoked", "scoped-coexistence")); conflict_resolve.add_argument("--reason", required=True); conflict_resolve.add_argument("--evidence-ref", action="append", default=[]); conflict_resolve.add_argument("--approved", action="store_true")
    revalidation = sub.add_parser("revalidate")
    common(revalidation)
    revalidation.add_argument("--learning-id", required=True); revalidation.add_argument("--reason", required=True); revalidation.add_argument("--evidence-ref", action="append", default=[]); revalidation.add_argument("--revalidate-after"); revalidation.add_argument("--approved", action="store_true")
    negative = sub.add_parser("negative-scan"); common(negative); negative.add_argument("--approved", action="store_true")
    negative_resolve = sub.add_parser("negative-resolve")
    common(negative_resolve)
    negative_resolve.add_argument("--candidate-id", required=True); negative_resolve.add_argument("--resolution", required=True, choices=("promote", "dismiss")); negative_resolve.add_argument("--reason", required=True); negative_resolve.add_argument("--evidence-ref", action="append", default=[]); negative_resolve.add_argument("--summary"); negative_resolve.add_argument("--advice"); negative_resolve.add_argument("--approved", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    root = args.root.resolve()
    try:
        if args.command == "state": value = state(root)
        elif args.command == "validate": value = {"type": "tailtrail-learning-governance-validation", "status": "passed", "events": len(read_events(root)), "blocking": blocking_reasons(root)}
        elif args.command == "challenge": value = open_challenge(root, args.learning_id, reason=args.reason, evidence_refs=args.evidence_ref, approved=args.approved)
        elif args.command == "challenge-resolve": value = resolve_challenge(root, args.challenge_id, action=args.resolution, reason=args.reason, evidence_refs=args.evidence_ref, approved=args.approved, summary=args.summary, advice=args.advice, replacement_id=args.replacement_id, revalidate_after=args.revalidate_after)
        elif args.command == "conflict": value = open_conflict(root, args.learning_id, reason=args.reason, evidence_refs=args.evidence_ref, approved=args.approved)
        elif args.command == "conflict-resolve": value = resolve_conflict(root, args.conflict_id, action=args.resolution, reason=args.reason, evidence_refs=args.evidence_ref, approved=args.approved)
        elif args.command == "revalidate": value = record_revalidation(root, args.learning_id, reason=args.reason, evidence_refs=args.evidence_ref, approved=args.approved, revalidate_after=args.revalidate_after)
        elif args.command == "negative-scan": value = {"candidates": negative_candidates(root), "recorded": record_negative_candidates(root, approved=True) if args.approved else [], "approval_required_to_record": not args.approved}
        elif args.command == "negative-resolve": value = resolve_negative(root, args.candidate_id, action=args.resolution, reason=args.reason, evidence_refs=args.evidence_ref, approved=args.approved, summary=args.summary, advice=args.advice)
        else: raise ValueError("unsupported governance command")
    except (OSError, ValueError, json.JSONDecodeError, V3.LearningV3Error) as error:
        print(f"Learning governance error: {error}")
        return 2
    if args.format == "json": print(json.dumps(value, indent=2, sort_keys=True))
    else: print("# TailTrail Learning Governance\n\n`" + json.dumps(value, sort_keys=True) + "`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
