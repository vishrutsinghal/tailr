#!/usr/bin/env python3
"""Canonical append-only TailTrail Learning V3 store and legacy migration."""

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


STORE = Path(".tailtrail/learning-v3/events.jsonl")
LEGACY_EVENTS = Path(".tailtrail/learning-events.jsonl")
LEGACY_INDEX = Path(".tailtrail/learning-index.md")
PROJECT_FRAME = Path(".tailtrail/learning-v3/project-frame.json")
SCHEMA_VERSION = "3"
RECORD_TYPE = "tailtrail-learning-v3-record"
LEARNING_CLASSES = {
    "positive-pattern", "avoid-history", "validation-command", "project-convention",
    "dependency-decision", "debug-cause", "general",
}
OPERATIONS = {"create", "amend", "revalidate", "supersede", "revoke"}
INVALIDATOR_KINDS = {
    "source-change", "policy-change", "graph-change", "symbol-change",
    "manifest-change", "ownership-change", "validation-change",
}
DEFAULT_INVALIDATORS = sorted(INVALIDATOR_KINDS)
SENSITIVITY = {"normal", "internal"}
FORBIDDEN_KEYS = {
    "prompt_raw", "source_code", "stack_trace",
    "secret", "password", "token", "credential", "customer_data", "user_identity",
}
SENSITIVE_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|authorization)\s*[:=]\s*\S+"),
    re.compile(r"(?i)bearer\s+[a-z0-9._\-]+"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
)


class LearningV3Error(ValueError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical(value)
    return hashlib.sha256(payload).hexdigest()


def load_ledger():
    name = "tailtrail_learning_v3_run_ledger"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / "run-ledger.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load append lock")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _snapshot_rows(root: Path, paths: list[Path]) -> list[dict[str, str | int | None]]:
    rows: list[dict[str, str | int | None]] = []
    for path in sorted(set(paths), key=lambda item: item.as_posix()):
        try:
            relative = path.resolve().relative_to(root.resolve()).as_posix()
        except (OSError, ValueError):
            continue
        try:
            value = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            modified_ns = path.stat().st_mtime_ns if path.exists() else None
        except OSError:
            value = None
            modified_ns = None
        rows.append({"path": relative, "digest": value, "modified_ns": modified_ns})
    return rows


def invalidator_snapshot(
    root: Path, *, path_patterns: list[str] | None = None, source_ref: str | None = None,
) -> dict[str, str]:
    """Return content-only fingerprints for every PM-L4 invalidator domain."""
    root = root.resolve()
    scoped: list[Path] = []
    for pattern in path_patterns or []:
        if not safe_relative(pattern):
            continue
        matches = [path for path in root.glob(pattern) if path.is_file()]
        scoped.extend(matches or ([root / pattern] if not any(char in pattern for char in "*?[") else []))
    source_path = str(source_ref or "").split("#line=", 1)[0]
    if source_path and not source_path.startswith("learning-v3:") and safe_relative(source_path):
        scoped.append(root / source_path)
    policy = [root / name for name in ("tailtrail-policy.md", "GUARDRAILS.md", "DEPENDENCY-GATE.md", "sonar-project.properties")]
    graph = [root / ".tailtrail" / "code-graph-cache.json", root / ".tailtrail" / "graph-learning-index.json"]
    manifests = [
        root / name for name in (
            "pyproject.toml", "setup.py", "setup.cfg", "package.json", "package-lock.json",
            "pnpm-lock.yaml", "yarn.lock", "Cargo.toml", "Cargo.lock", "go.mod", "go.sum",
            "requirements.txt", "Pipfile", "Pipfile.lock", "poetry.lock", "Gemfile", "Gemfile.lock",
        )
    ]
    ownership = [root / ".github" / "CODEOWNERS", root / "CODEOWNERS"]
    tests = [path for path in scoped if any(part.lower() in {"test", "tests", "__tests__"} for part in path.parts)]
    domains = {
        "source-change": scoped,
        "policy-change": policy,
        "graph-change": graph,
        "symbol-change": scoped,
        "manifest-change": manifests,
        "ownership-change": ownership,
        "validation-change": tests,
    }
    return {name: "sha256:" + sha256(_snapshot_rows(root, paths)) for name, paths in sorted(domains.items())}


def project_frame(root: Path, *, create: bool = False) -> str:
    path = root / PROJECT_FRAME
    if path.is_file():
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise LearningV3Error("Learning V3 project frame is corrupt") from error
        if set(value) != {"schema_version", "type", "id"} or value.get("schema_version") != "1" or value.get("type") != "tailtrail-learning-project-frame" or not re.fullmatch(r"sha256:[0-9a-f]{64}", str(value.get("id", ""))):
            raise LearningV3Error("Learning V3 project frame is invalid")
        return str(value["id"])
    frame = "sha256:" + hashlib.sha256(root.resolve().as_posix().encode("utf-8")).hexdigest()
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema_version": "1", "type": "tailtrail-learning-project-frame", "id": frame}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return frame


def clean_text(value: str, *, limit: int = 500) -> str:
    text = " ".join(str(value).split())[:limit]
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            raise LearningV3Error("learning text contains sensitive material")
    return text


def safe_relative(value: str) -> bool:
    if not value or "\\" in value:
        return False
    path = Path(value.split("#line=", 1)[0])
    return not path.is_absolute() and ".." not in path.parts


def confidence_band(score: int) -> str:
    if score < 40:
        return "do-not-use"
    if score < 60:
        return "weak-note"
    if score < 80:
        return "candidate"
    return "trusted"


def _record_digest(record: dict[str, Any]) -> str:
    unsigned = copy.deepcopy(record)
    if isinstance(unsigned.get("chain"), dict):
        unsigned["chain"].pop("digest", None)
    return sha256(unsigned)


def validate_record(record: dict[str, Any], *, expected_frame: str | None = None) -> list[str]:
    issues: list[str] = []
    top = {
        "schema_version", "type", "record_id", "sequence", "learning_id", "learning_class",
        "created_at", "lifecycle", "provenance", "applicability", "freshness", "utility",
        "content", "privacy", "chain",
    }
    if set(record) != top:
        issues.append("record contract is not closed")
    if record.get("schema_version") != SCHEMA_VERSION or record.get("type") != RECORD_TYPE:
        issues.append("record identity must be TailTrail Learning V3")
    if not isinstance(record.get("sequence"), int) or int(record.get("sequence", 0)) < 1:
        issues.append("sequence must be a positive integer")
    if not re.fullmatch(r"lrn-[a-z0-9][a-z0-9._-]{2,95}", str(record.get("learning_id", ""))):
        issues.append("learning_id is invalid")
    if record.get("learning_class") not in LEARNING_CLASSES:
        issues.append("learning_class is invalid")
    if not re.fullmatch(r"lrnrec-[0-9a-f]{16}", str(record.get("record_id", ""))):
        issues.append("record_id is invalid")

    lifecycle = record.get("lifecycle", {})
    if not isinstance(lifecycle, dict):
        issues.append("lifecycle must be an object")
        lifecycle = {}
    if set(lifecycle) != {"operation", "previous_record_id", "reason", "replacement_learning_id"}:
        issues.append("lifecycle contract is not closed")
    if lifecycle.get("operation") not in OPERATIONS:
        issues.append("lifecycle operation is invalid")
    if lifecycle.get("operation") == "create" and lifecycle.get("previous_record_id") is not None:
        issues.append("create cannot reference a previous record")
    if lifecycle.get("operation") != "create" and not lifecycle.get("previous_record_id"):
        issues.append("lifecycle transition requires previous_record_id")
    if lifecycle.get("operation") == "supersede" and not lifecycle.get("replacement_learning_id"):
        issues.append("supersede requires replacement_learning_id")
    if lifecycle.get("operation") != "supersede" and lifecycle.get("replacement_learning_id") is not None:
        issues.append("only supersede may name a replacement")

    provenance = record.get("provenance", {})
    if not isinstance(provenance, dict):
        issues.append("provenance must be an object")
        provenance = {}
    if set(provenance) != {"source_kind", "source_ref", "source_fingerprint", "captured_by", "evidence_refs", "sanitized"}:
        issues.append("provenance contract is not closed")
    if not provenance.get("source_kind") or not provenance.get("captured_by"):
        issues.append("provenance source_kind and captured_by are required")
    source_ref = str(provenance.get("source_ref", ""))
    if not (source_ref.startswith("learning-v3:") or safe_relative(source_ref)):
        issues.append("provenance source_ref must be a project-relative reference")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(provenance.get("source_fingerprint", ""))):
        issues.append("provenance source_fingerprint is invalid")
    if provenance.get("sanitized") is not True:
        issues.append("provenance must be explicitly sanitized")
    evidence_refs = provenance.get("evidence_refs", [])
    if not isinstance(evidence_refs, list) or len(evidence_refs) != len(set(str(item) for item in evidence_refs)):
        issues.append("evidence_refs must be a unique array")
        evidence_refs = []
    for ref in evidence_refs:
        if not isinstance(ref, str) or not safe_relative(ref):
            issues.append("evidence references must remain project-relative")

    applicability = record.get("applicability", {})
    if not isinstance(applicability, dict):
        issues.append("applicability must be an object")
        applicability = {}
    if set(applicability) != {"project_frame", "task_types", "tags", "path_patterns", "requirement_ids", "exclusions"}:
        issues.append("applicability contract is not closed")
    frame = applicability.get("project_frame", {})
    if not isinstance(frame, dict):
        issues.append("project_frame must be an object")
        frame = {}
    if set(frame) != {"kind", "id"} or frame.get("kind") != "repository" or not re.fullmatch(r"sha256:[0-9a-f]{64}", str(frame.get("id", ""))):
        issues.append("applicability project_frame is invalid")
    if expected_frame and frame.get("id") != expected_frame:
        issues.append("learning record crosses the active project-frame boundary")
    for field in ("task_types", "tags", "path_patterns", "requirement_ids", "exclusions"):
        values = applicability.get(field, [])
        if not isinstance(values, list) or any(not isinstance(item, str) for item in values) or len(values) != len(set(values)):
            issues.append(f"applicability {field} must be a unique string array")
    paths = applicability.get("path_patterns", []) if isinstance(applicability.get("path_patterns", []), list) else []
    for path in paths:
        if not isinstance(path, str) or not safe_relative(path):
            issues.append("applicability paths must remain project-relative")

    freshness = record.get("freshness", {})
    if not isinstance(freshness, dict):
        issues.append("freshness must be an object")
        freshness = {}
    freshness_fields = {"status", "captured_at", "revalidate_after", "invalidators", "stale_when"}
    if set(freshness) not in {frozenset(freshness_fields), frozenset({*freshness_fields, "invalidator_snapshot"})}:
        issues.append("freshness contract is not closed")
    expected_status = {"supersede": "superseded", "revoke": "revoked"}.get(lifecycle.get("operation"), "current")
    if freshness.get("status") != expected_status:
        issues.append("freshness status does not match lifecycle operation")
    if not freshness.get("captured_at") or not freshness.get("stale_when"):
        issues.append("freshness captured_at and stale_when are required")
    invalidators = freshness.get("invalidators", [])
    if not isinstance(invalidators, list) or any(not isinstance(item, str) for item in invalidators) or len(invalidators) != len(set(invalidators)):
        issues.append("freshness invalidators must be a unique string array")
    elif any(item not in INVALIDATOR_KINDS for item in invalidators):
        issues.append("freshness invalidator is not recognized")
    snapshot = freshness.get("invalidator_snapshot")
    if snapshot is not None and (
        not isinstance(snapshot, dict)
        or set(snapshot) != INVALIDATOR_KINDS
        or any(not re.fullmatch(r"sha256:[0-9a-f]{64}", str(value)) for value in snapshot.values())
    ):
        issues.append("freshness invalidator snapshot is invalid")

    utility = record.get("utility", {})
    if not isinstance(utility, dict):
        issues.append("utility must be an object")
        utility = {}
    if set(utility) != {"confidence_score", "confidence_band", "observation_count", "use_count", "curated", "causal_claim"}:
        issues.append("utility contract is not closed")
    score = utility.get("confidence_score")
    if not isinstance(score, int) or not 0 <= score <= 100:
        issues.append("utility confidence_score must be between 0 and 100")
    elif utility.get("confidence_band") != confidence_band(score):
        issues.append("utility confidence band does not match score")
    if utility.get("causal_claim") is not False:
        issues.append("Learning V3 utility cannot claim causality")
    for field in ("observation_count", "use_count"):
        if not isinstance(utility.get(field), int) or int(utility.get(field, -1)) < 0:
            issues.append(f"utility {field} must be a non-negative integer")
    if not isinstance(utility.get("curated"), bool):
        issues.append("utility curated must be boolean")

    content = record.get("content", {})
    if not isinstance(content, dict):
        issues.append("content must be an object")
        content = {}
    if set(content) != {"summary", "advice"} or not content.get("summary") or not content.get("advice"):
        issues.append("content requires only summary and advice")
    privacy = record.get("privacy", {})
    if not isinstance(privacy, dict):
        issues.append("privacy must be an object")
        privacy = {}
    if set(privacy) != {"sensitivity", "sanitized", "raw_prompt", "raw_source", "raw_log", "identity_fields"}:
        issues.append("privacy contract is not closed")
    if privacy.get("sensitivity") not in SENSITIVITY or privacy.get("sanitized") is not True:
        issues.append("privacy sensitivity or sanitization is invalid")
    if any(privacy.get(key) is not False for key in ("raw_prompt", "raw_source", "raw_log", "identity_fields")):
        issues.append("raw or identity-bearing learning content is forbidden")
    lowered_keys = {str(key).lower() for key in _walk_keys(record)}
    if lowered_keys.intersection(FORBIDDEN_KEYS):
        issues.append("record contains a forbidden raw or sensitive field")
    for text in (content.get("summary", ""), content.get("advice", ""), lifecycle.get("reason", "")):
        try:
            clean_text(str(text))
        except LearningV3Error as error:
            issues.append(str(error))

    chain = record.get("chain", {})
    if not isinstance(chain, dict):
        issues.append("chain must be an object")
        chain = {}
    if set(chain) != {"previous_digest", "digest"}:
        issues.append("chain contract is not closed")
    if chain.get("previous_digest") is not None and not re.fullmatch(r"[0-9a-f]{64}", str(chain.get("previous_digest", ""))):
        issues.append("chain previous_digest is invalid")
    if chain.get("digest") != _record_digest(record):
        issues.append("record digest is invalid")
    return issues


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def read_records(root: Path) -> list[dict[str, Any]]:
    path = root / STORE
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    previous: str | None = None
    frame = project_frame(root)
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise LearningV3Error(f"invalid Learning V3 JSON on line {line_number}: {error}") from error
        if not isinstance(value, dict):
            raise LearningV3Error(f"Learning V3 line {line_number} is not an object")
        issues = validate_record(value, expected_frame=frame)
        if value.get("sequence") != len(records) + 1:
            issues.append("sequence is not contiguous")
        chain = value.get("chain") if isinstance(value.get("chain"), dict) else {}
        if chain.get("previous_digest") != previous:
            issues.append("append-only digest chain is broken")
        if issues:
            raise LearningV3Error(f"invalid Learning V3 record on line {line_number}: {'; '.join(issues)}")
        records.append(value)
        previous = value["chain"]["digest"]
    _validate_lifecycle(records)
    return records


def _validate_lifecycle(records: list[dict[str, Any]]) -> None:
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        learning_id = record["learning_id"]
        operation = record["lifecycle"]["operation"]
        prior = latest.get(learning_id)
        if operation == "create" and prior is not None:
            raise LearningV3Error(f"learning `{learning_id}` has more than one create record")
        if operation != "create" and (prior is None or prior["record_id"] != record["lifecycle"]["previous_record_id"]):
            raise LearningV3Error(f"learning `{learning_id}` has an invalid lifecycle predecessor")
        if prior and prior["freshness"]["status"] in {"superseded", "revoked"}:
            raise LearningV3Error(f"learning `{learning_id}` changes after a terminal transition")
        latest[learning_id] = record


def append_record(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    path = root / STORE
    with load_ledger().RunLock(path.with_suffix(".lock")):
        records = read_records(root)
        record = copy.deepcopy(record)
        record["sequence"] = len(records) + 1
        record["chain"]["previous_digest"] = records[-1]["chain"]["digest"] if records else None
        seed = {key: value for key, value in record.items() if key not in {"record_id", "chain"}}
        record["record_id"] = "lrnrec-" + sha256({"seed": seed, "previous": record["chain"]["previous_digest"]})[:16]
        record["chain"]["digest"] = _record_digest(record)
        issues = validate_record(record, expected_frame=project_frame(root))
        if issues:
            raise LearningV3Error("invalid Learning V3 write: " + "; ".join(issues))
        _validate_lifecycle([*records, record])
        project_frame(root, create=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        rebuild_compatibility_index(root)
    return record


def latest_records(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        result[record["learning_id"]] = record
    return result


def build_record(
    root: Path, *, learning_id: str, learning_class: str, summary: str, advice: str,
    source_kind: str, source_ref: str, source_fingerprint: str, captured_by: str,
    task_types: list[str] | None = None, tags: list[str] | None = None,
    path_patterns: list[str] | None = None, requirement_ids: list[str] | None = None,
    evidence_refs: list[str] | None = None, exclusions: list[str] | None = None,
    invalidators: list[str] | None = None, stale_when: str = "related source, policy, validation, manifest, or ownership changes",
    confidence_score: int = 60, sensitivity: str = "normal", operation: str = "create",
    previous: dict[str, Any] | None = None, reason: str = "initial capture",
    replacement_learning_id: str | None = None, curated: bool = False,
    revalidate_after: str | None = None,
) -> dict[str, Any]:
    timestamp = now()
    return {
        "schema_version": SCHEMA_VERSION,
        "type": RECORD_TYPE,
        "record_id": "lrnrec-0000000000000000",
        "sequence": 1,
        "learning_id": learning_id,
        "learning_class": learning_class,
        "created_at": timestamp,
        "lifecycle": {
            "operation": operation,
            "previous_record_id": previous["record_id"] if previous else None,
            "reason": clean_text(reason),
            "replacement_learning_id": replacement_learning_id,
        },
        "provenance": {
            "source_kind": source_kind,
            "source_ref": source_ref,
            "source_fingerprint": source_fingerprint,
            "captured_by": captured_by,
            "evidence_refs": sorted(set(evidence_refs or [])),
            "sanitized": True,
        },
        "applicability": {
            "project_frame": {"kind": "repository", "id": project_frame(root)},
            "task_types": sorted(set(task_types or [])),
            "tags": sorted(set(tags or [])),
            "path_patterns": sorted(set(path_patterns or [])),
            "requirement_ids": sorted(set(requirement_ids or [])),
            "exclusions": sorted(set(exclusions or [])),
        },
        "freshness": {
            "status": {"supersede": "superseded", "revoke": "revoked"}.get(operation, "current"),
            "captured_at": timestamp,
            "revalidate_after": revalidate_after,
            "invalidators": sorted(set(DEFAULT_INVALIDATORS if invalidators is None else invalidators)),
            "stale_when": clean_text(stale_when),
            "invalidator_snapshot": invalidator_snapshot(root, path_patterns=path_patterns, source_ref=source_ref),
        },
        "utility": {
            "confidence_score": confidence_score,
            "confidence_band": confidence_band(confidence_score),
            "observation_count": int((previous or {}).get("utility", {}).get("observation_count", 0)) + (1 if operation == "create" else 0),
            "use_count": int((previous or {}).get("utility", {}).get("use_count", 0)),
            "curated": curated,
            "causal_claim": False,
        },
        "content": {"summary": clean_text(summary), "advice": clean_text(advice)},
        "privacy": {
            "sensitivity": sensitivity,
            "sanitized": True,
            "raw_prompt": False,
            "raw_source": False,
            "raw_log": False,
            "identity_fields": False,
        },
        "chain": {"previous_digest": None, "digest": "0" * 64},
    }


def capture_legacy_event(
    root: Path, event: dict[str, Any], *, captured_by: str = "Learning Agent",
    legacy_line_number: int | None = None,
) -> dict[str, Any]:
    legacy_id = str(event.get("id", ""))
    advice = clean_text(str(event.get("learning_candidate", "")))
    if not legacy_id or not advice:
        raise LearningV3Error("candidate capture requires a legacy event id and sanitized learning_candidate")
    if event.get("sensitivity") not in {None, "normal"} or event.get("raw_prompt_recorded"):
        raise LearningV3Error("sensitive or raw-prompt legacy events cannot enter Learning V3")
    learning_id = "lrn-" + hashlib.sha256(legacy_id.encode("utf-8")).hexdigest()[:16]
    existing = latest_records(read_records(root)).get(learning_id)
    if existing:
        return existing
    legacy_path = root / LEGACY_EVENTS
    line_number = legacy_line_number or (len(legacy_path.read_text(encoding="utf-8").splitlines()) + 1 if legacy_path.is_file() else 1)
    confidence = event.get("learning_confidence", {})
    score = int(confidence.get("score", 60))
    paths = [Path(str(item)).as_posix() for item in event.get("files", []) if safe_relative(Path(str(item)).as_posix())]
    record = build_record(
        root,
        learning_id=learning_id,
        learning_class="debug-cause" if event.get("positive_learning_candidate_id") else "positive-pattern",
        summary=f"Sanitized learning candidate {legacy_id}",
        advice=advice,
        source_kind="legacy-candidate-reference",
        source_ref=f"{LEGACY_EVENTS.as_posix()}#line={line_number}",
        source_fingerprint="sha256:" + sha256(event),
        captured_by=captured_by,
        task_types=[str(event.get("task_type", "general"))],
        tags=[clean_text(str(item), limit=80) for item in event.get("tags", [])],
        path_patterns=paths,
        requirement_ids=[clean_text(str(item), limit=120) for item in event.get("requirement_ids", [])],
        invalidators=["source-change", "policy-change", "validation-change", "ownership-change"],
        stale_when=str(event.get("stale_when") or "related source, policy, validation, manifest, or ownership changes"),
        confidence_score=max(0, min(100, score)),
        reason="canonical V3 candidate capture",
    )
    return append_record(root, record)


def amend(
    root: Path, learning_id: str, *, reason: str, advice: str | None = None,
    summary: str | None = None, curated: bool | None = None,
) -> dict[str, Any]:
    prior = latest_records(read_records(root)).get(learning_id)
    if not prior:
        raise LearningV3Error(f"Learning V3 record not found: {learning_id}")
    if prior["freshness"]["status"] != "current":
        raise LearningV3Error("terminal Learning V3 records cannot be amended")
    record = build_record(
        root,
        learning_id=learning_id,
        learning_class=prior["learning_class"],
        summary=summary or prior["content"]["summary"],
        advice=advice or prior["content"]["advice"],
        source_kind="learning-v3-amendment",
        source_ref=f"learning-v3:{prior['record_id']}",
        source_fingerprint="sha256:" + prior["chain"]["digest"],
        captured_by="Learning Governance",
        task_types=prior["applicability"]["task_types"],
        tags=prior["applicability"]["tags"],
        path_patterns=prior["applicability"]["path_patterns"],
        requirement_ids=prior["applicability"]["requirement_ids"],
        evidence_refs=prior["provenance"]["evidence_refs"],
        exclusions=prior["applicability"]["exclusions"],
        invalidators=prior["freshness"]["invalidators"],
        stale_when=prior["freshness"]["stale_when"],
        confidence_score=prior["utility"]["confidence_score"],
        sensitivity=prior["privacy"]["sensitivity"],
        operation="amend",
        previous=prior,
        reason=reason,
        curated=prior["utility"]["curated"] if curated is None else curated,
    )
    return append_record(root, record)


def revalidate(
    root: Path, learning_id: str, *, reason: str, evidence_refs: list[str],
    revalidate_after: str | None = None,
) -> dict[str, Any]:
    prior = latest_records(read_records(root)).get(learning_id)
    if not prior:
        raise LearningV3Error(f"Learning V3 record not found: {learning_id}")
    if prior["freshness"]["status"] != "current":
        raise LearningV3Error("terminal Learning V3 records cannot be revalidated")
    refs = sorted(set(evidence_refs))
    if not refs:
        raise LearningV3Error("revalidation requires at least one evidence reference")
    for ref in refs:
        if not safe_relative(ref) or not (root / ref).is_file():
            raise LearningV3Error("revalidation evidence must be an existing project-relative file")
    if revalidate_after:
        try:
            datetime.fromisoformat(revalidate_after.replace("Z", "+00:00"))
        except ValueError as error:
            raise LearningV3Error("revalidate_after must be an ISO-8601 timestamp") from error
    record = build_record(
        root, learning_id=learning_id, learning_class=prior["learning_class"],
        summary=prior["content"]["summary"], advice=prior["content"]["advice"],
        source_kind="learning-v3-revalidation", source_ref=f"learning-v3:{prior['record_id']}",
        source_fingerprint="sha256:" + prior["chain"]["digest"], captured_by="Learning Governance",
        task_types=prior["applicability"]["task_types"], tags=prior["applicability"]["tags"],
        path_patterns=prior["applicability"]["path_patterns"], requirement_ids=prior["applicability"]["requirement_ids"],
        evidence_refs=[*prior["provenance"]["evidence_refs"], *refs], exclusions=prior["applicability"]["exclusions"],
        invalidators=prior["freshness"]["invalidators"], stale_when=prior["freshness"]["stale_when"],
        confidence_score=prior["utility"]["confidence_score"], sensitivity=prior["privacy"]["sensitivity"],
        operation="revalidate", previous=prior, reason=reason, curated=prior["utility"]["curated"],
        revalidate_after=revalidate_after,
    )
    return append_record(root, record)


def terminal_transition(root: Path, learning_id: str, operation: str, reason: str, replacement: str | None = None) -> dict[str, Any]:
    records = read_records(root)
    latest = latest_records(records)
    prior = latest.get(learning_id)
    if not prior:
        raise LearningV3Error(f"Learning V3 record not found: {learning_id}")
    if prior["freshness"]["status"] != "current":
        raise LearningV3Error("Learning V3 record already has a terminal transition")
    if operation == "supersede":
        target = latest.get(str(replacement))
        if not target or target["freshness"]["status"] != "current" or replacement == learning_id:
            raise LearningV3Error("supersession requires a different current replacement learning")
    record = build_record(
        root, learning_id=learning_id, learning_class=prior["learning_class"],
        summary=prior["content"]["summary"], advice=prior["content"]["advice"],
        source_kind=f"learning-v3-{operation}", source_ref=f"learning-v3:{prior['record_id']}",
        source_fingerprint="sha256:" + prior["chain"]["digest"], captured_by="Learning Governance",
        task_types=prior["applicability"]["task_types"], tags=prior["applicability"]["tags"],
        path_patterns=prior["applicability"]["path_patterns"], requirement_ids=prior["applicability"]["requirement_ids"],
        evidence_refs=prior["provenance"]["evidence_refs"], exclusions=prior["applicability"]["exclusions"],
        invalidators=prior["freshness"]["invalidators"], stale_when=prior["freshness"]["stale_when"],
        confidence_score=prior["utility"]["confidence_score"], sensitivity=prior["privacy"]["sensitivity"],
        operation=operation, previous=prior, reason=reason, replacement_learning_id=replacement,
        curated=prior["utility"]["curated"],
    )
    return append_record(root, record)


def read_legacy(root: Path) -> list[tuple[int, dict[str, Any]]]:
    path = root / LEGACY_EVENTS
    if not path.is_file():
        return []
    result: list[tuple[int, dict[str, Any]]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise LearningV3Error(f"invalid legacy learning JSON on line {line_number}: {error}") from error
        if isinstance(event, dict):
            result.append((line_number, event))
    return result


def migrate_legacy(root: Path, *, approved: bool, dry_run: bool = False) -> dict[str, Any]:
    if not dry_run and not approved:
        raise LearningV3Error("legacy migration requires --approved")
    migrated: list[str] = []
    skipped: list[dict[str, str]] = []
    for line_number, event in read_legacy(root):
        legacy_id = str(event.get("id", f"line-{line_number}"))
        try:
            if dry_run:
                advice = clean_text(str(event.get("learning_candidate", "")))
                if not advice or event.get("sensitivity") not in {None, "normal"} or event.get("raw_prompt_recorded"):
                    raise LearningV3Error("not a sanitized normal-sensitivity candidate")
                migrated.append(legacy_id)
            else:
                migrated.append(capture_legacy_event(root, event, captured_by="PM-L1 Legacy Migrator", legacy_line_number=line_number)["learning_id"])
        except LearningV3Error as error:
            skipped.append({"legacy_id": legacy_id, "reason": str(error)})
    return {
        "type": "tailtrail-learning-v3-migration-report",
        "status": "validated" if dry_run else "migrated",
        "migrated": migrated,
        "skipped": skipped,
        "legacy_preserved": True,
        "boundary": "Migration retains the legacy store and copies only sanitized candidate fields with a source reference and fingerprint.",
    }


def compatible_events(root: Path) -> list[dict[str, Any]]:
    legacy = {str(event.get("id")): copy.deepcopy(event) for _, event in read_legacy(root)}
    latest = latest_records(read_records(root))
    result: list[dict[str, Any]] = []
    referenced: set[str] = set()
    for record in latest.values():
        ref = record["provenance"]["source_ref"]
        legacy_id = None
        for candidate_id, event in legacy.items():
            if "sha256:" + sha256(event) == record["provenance"]["source_fingerprint"]:
                legacy_id = candidate_id
                break
        if record["freshness"]["status"] != "current":
            if legacy_id:
                referenced.add(legacy_id)
            continue
        base = legacy.get(legacy_id, {}) if legacy_id else {}
        if legacy_id:
            referenced.add(legacy_id)
        projected = {
            **base,
            "id": legacy_id or record["learning_id"],
            "timestamp": record["freshness"]["captured_at"],
            "task_type": (record["applicability"]["task_types"] or ["general"])[0],
            "tags": record["applicability"]["tags"],
            "files": record["applicability"]["path_patterns"],
            "learning_candidate": record["content"]["advice"],
            "stale_when": record["freshness"]["stale_when"],
            "sensitivity": record["privacy"]["sensitivity"],
            "learning_confidence": {
                **base.get("learning_confidence", {}),
                "score": record["utility"]["confidence_score"],
                "band": record["utility"]["confidence_band"],
            },
            "learning_v3_id": record["learning_id"],
            "learning_v3_record_id": record["record_id"],
        }
        result.append(projected)
    result.extend(event for event_id, event in legacy.items() if event_id not in referenced)
    return sorted(result, key=lambda item: (str(item.get("timestamp", "")), str(item.get("id", ""))))


def rebuild_compatibility_index(root: Path) -> Path:
    lines = [
        "# TailTrail Learning Index", "",
        "This index is the token-safe entry point. Load this before raw learning history.", "",
        "| Event | Score | Band | Type | Tags | Files | Candidate |",
        "|---|---:|---|---|---|---|---|",
    ]
    events = sorted(compatible_events(root), key=lambda item: str(item.get("timestamp", "")), reverse=True)
    for event in events:
        confidence = event.get("learning_confidence", {})
        if event.get("sensitivity") != "normal" or confidence.get("band") in {"do-not-use", "weak-note"}:
            continue
        candidate = str(event.get("learning_candidate", ""))
        if not candidate:
            continue
        lines.append(
            f"| `{event.get('id')}` | {confidence.get('score', 0)} | {confidence.get('band', 'unknown')} | "
            f"{event.get('task_type', 'unknown')} | {', '.join(event.get('tags', []))} | "
            f"{', '.join(event.get('files', [])[:3])} | {candidate} |"
        )
    lines.append("")
    path = root / LEGACY_INDEX
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "state", "migrate", "amend", "revalidate", "supersede", "revoke"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--learning-id")
    parser.add_argument("--replacement-id")
    parser.add_argument("--reason")
    parser.add_argument("--summary")
    parser.add_argument("--advice")
    parser.add_argument("--evidence-ref", action="append", default=[])
    parser.add_argument("--revalidate-after")
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    try:
        if args.command == "validate":
            records = read_records(root)
            value: Any = {"type": "tailtrail-learning-v3-validation", "status": "passed", "records": len(records), "project_frame": project_frame(root)}
        elif args.command == "state":
            value = {"type": "tailtrail-learning-v3-state", "records": list(latest_records(read_records(root)).values())}
        elif args.command == "migrate":
            value = migrate_legacy(root, approved=args.approved, dry_run=args.dry_run)
        elif args.command == "amend":
            if not args.approved or not args.learning_id or not args.reason:
                raise LearningV3Error("amend requires --approved, --learning-id, and --reason")
            value = amend(root, args.learning_id, reason=args.reason, summary=args.summary, advice=args.advice)
        elif args.command == "revalidate":
            if not args.approved or not args.learning_id or not args.reason:
                raise LearningV3Error("revalidate requires --approved, --learning-id, and --reason")
            value = revalidate(root, args.learning_id, reason=args.reason, evidence_refs=args.evidence_ref, revalidate_after=args.revalidate_after)
        elif args.command in {"supersede", "revoke"}:
            if not args.approved or not args.learning_id or not args.reason:
                raise LearningV3Error(f"{args.command} requires --approved, --learning-id, and --reason")
            value = terminal_transition(root, args.learning_id, args.command, args.reason, args.replacement_id)
        else:
            raise LearningV3Error("unsupported Learning V3 command")
    except (OSError, json.JSONDecodeError, LearningV3Error) as error:
        print(f"Learning V3 error: {error}")
        return 2
    if args.format == "json":
        print(json.dumps(value, indent=2, sort_keys=True))
    else:
        print(f"# TailTrail Learning V3\n\n`{json.dumps(value, sort_keys=True)}`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
