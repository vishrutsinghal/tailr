#!/usr/bin/env python3
"""Create and inspect sanitized local execution-failure artifacts.

Phase 1 deliberately accepts structured failure metadata only. It never accepts
or persists a raw command log, stack trace, environment dump, or pasted error
body. Later phases can classify and resolve an artifact using independently
collected local evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1"
SOURCES = ("agent-command", "user-pasted", "external-observation")
CLASSIFICATIONS = ("code", "configuration", "environment", "infrastructure", "dependency", "permission", "data", "external-service", "transient", "unknown")
CONFIDENCES = ("observed", "supported-hypothesis", "unknown")
ACTIONS = ("read-only-diagnosis", "bounded-correction", "safe-retry")
CHECKPOINT_DELTAS = ("resolved", "improved", "unchanged", "regressed", "new-drift", "needs-decision")
MAP_EVIDENCE = ("approved-path", "architecture", "behavior", "preservation", "scope")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
ERROR_CODE = re.compile(r"^[A-Z][A-Z0-9_-]{1,79}$")
SENSITIVE_WORD = re.compile(r"\b(password|secret|token|api[_ -]?key|authorization|bearer)\b", re.IGNORECASE)


def load_module(name: str, relative: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LEDGER = load_module("execution_failure_ledger", "scripts/run-ledger.py")
PLANNING = load_module("execution_failure_planning", "scripts/planning-lock.py")
ANCHOR = load_module("execution_failure_anchor", "scripts/change-intent-anchor.py")
CONVERGENCE = load_module("execution_failure_convergence", "scripts/harness-convergence.py")
SETUP_SCAN = load_module("execution_failure_setup_scan", "scripts/setup-scan.py")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_identifier(value: str, label: str) -> str:
    if not IDENTIFIER.fullmatch(value) or value in {".", ".."}:
        raise ValueError(f"{label} must be a simple identifier")
    return value


def bounded_text(value: str, label: str, maximum: int) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > maximum or "\n" in cleaned or "\r" in cleaned or SENSITIVE_WORD.search(cleaned):
        raise ValueError(f"{label} must be one non-empty line of at most {maximum} characters")
    return cleaned


def stable_error_code(value: str) -> str:
    if not ERROR_CODE.fullmatch(value):
        raise ValueError("error code must be an uppercase stable identifier, not raw error text")
    return value


def safe_relative_path(root: Path, value: str) -> Path:
    candidate = Path(value)
    if not value.strip() or candidate.is_absolute() or any(part == ".." for part in candidate.parts):
        raise ValueError("artifact reference must be a project-relative path")
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("artifact reference must stay within the project root") from error
    if not resolved.is_file():
        raise ValueError("artifact reference must name an existing local file")
    return resolved


def safe_project_relative(root: Path, value: str) -> str:
    candidate = Path(value)
    if not value.strip() or candidate.is_absolute() or any(part == ".." for part in candidate.parts):
        raise ValueError("path must be project-relative")
    resolved = (root / candidate).resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as error:
        raise ValueError("path must stay within the project root") from error


def failure_dir(root: Path, run_id: str) -> Path:
    return LEDGER.state_dir(root, run_id) / "execution-failures"


def intake_dir(root: Path, run_id: str) -> Path:
    return failure_dir(root, run_id) / "intakes"


def list_failures(root: Path, run_id: str) -> list[Path]:
    directory = failure_dir(root, run_id)
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.glob("failure-*.json") if re.fullmatch(r"failure-[0-9]{4}\.json", path.name))


def next_failure_id(root: Path, run_id: str) -> str:
    return f"failure-{len(list_failures(root, run_id)) + 1:04d}"


def next_intake_id(root: Path, run_id: str) -> str:
    directory = intake_dir(root, run_id)
    count = len([path for path in directory.glob("intake-*.json") if re.fullmatch(r"intake-[0-9]{4}\.json", path.name)]) if directory.is_dir() else 0
    return f"intake-{count + 1:04d}"


def classify(error_code: str) -> dict[str, str]:
    """Return a keyword-based observation, never a claimed root cause."""
    code = stable_error_code(error_code)
    groups = {
        "permission": ("ACCESS", "AUTH", "FORBIDDEN", "UNAUTHORIZED", "PERMISSION"),
        "dependency": ("DEPENDENCY", "IMPORT", "MODULE", "VERSION", "PACKAGE"),
        "infrastructure": ("TERRAFORM", "INFRA", "NETWORK", "RESOURCE", "DEPLOY"),
        "data": ("SCHEMA", "MIGRATION", "SERIAL", "CONSTRAINT", "DATA"),
        "configuration": ("CONFIG", "PROVIDER", "SETTING", "ENVIRONMENT_VARIABLE"),
        "transient": ("TIMEOUT", "RATE_LIMIT", "TEMPORARY", "UNAVAILABLE"),
        "external-service": ("VENDOR", "SERVICE", "API"),
        "code": ("ASSERT", "TYPE", "VALUE", "ATTRIBUTE", "TEST_FAILURE"),
    }
    for classification, markers in groups.items():
        if any(marker in code for marker in markers):
            return {"classification": classification, "confidence": "observed", "basis": "stable-error-code"}
    return {"classification": "unknown", "confidence": "unknown", "basis": "insufficient-safe-metadata"}


def authority_decision(classification: str, proposed_action: str) -> dict[str, str | bool]:
    if proposed_action == "read-only-diagnosis":
        return {"status": "allowed", "approval_required": False, "route": "diagnose-read-only", "reason": "Read-only diagnosis is allowed; no source or external state may change."}
    if proposed_action == "safe-retry" and classification in {"environment", "external-service", "transient"}:
        return {"status": "allowed", "approval_required": False, "route": "bounded-retry-proposal", "reason": "A retry may be proposed, but this command never executes it."}
    if classification in {"infrastructure", "dependency", "permission", "data"}:
        return {"status": "blocked", "approval_required": True, "route": "authority-or-design-decision", "reason": "This classification can require protected, external, dependency, IAM, or data mutation."}
    return {"status": "needs-scope-evidence", "approval_required": True, "route": "scope-review", "reason": "The requested correction cannot be proven inside the approved requirement scope in this phase."}


def approved_requirement(root: Path, run_id: str, requirement_uid: str) -> dict[str, Any]:
    path = ANCHOR.anchor_dir(root, run_id) / "approved-v1.json"
    if not path.is_file():
        raise ValueError("an approved anchor is required before requirement mapping")
    anchor = json.loads(path.read_text(encoding="utf-8"))
    for requirement in anchor.get("requirements", []):
        if requirement.get("requirement_uid") == requirement_uid and requirement.get("status") == "approved":
            return requirement
    raise ValueError("requirement_uid is not approved for this run")


def normalize_fingerprint_fields(requirement_uid: str, classification: str, error_code: str, project_frame: str, command_label: str) -> dict[str, str]:
    safe_identifier(requirement_uid, "requirement UID")
    if classification not in CLASSIFICATIONS:
        raise ValueError("classification is not allowed")
    return {
        "requirement_uid": requirement_uid.lower(),
        "classification": classification.lower(),
        "error_code": stable_error_code(error_code).lower(),
        "project_frame": bounded_text(project_frame, "project frame", 240).lower(),
        "command_label": bounded_text(command_label, "command label", 160).lower(),
    }


def failure_fingerprint(fields: dict[str, str]) -> str:
    expected = {"requirement_uid", "classification", "error_code", "project_frame", "command_label"}
    if set(fields) != expected:
        raise ValueError("fingerprint fields have an unsupported shape")
    encoded = json.dumps(fields, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def find_matching_open_failure(root: Path, run_id: str, requirement_uid: str, fingerprint: str, exclude_failure_id: str) -> dict[str, Any] | None:
    for path in reversed(list_failures(root, run_id)):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("failure_id") == exclude_failure_id or payload.get("status") == "resolved":
            continue
        correlation = payload.get("correlation", {})
        if correlation.get("failure_fingerprint") == fingerprint and correlation.get("signature_fields", {}).get("requirement_uid") == requirement_uid:
            return payload
    return None


def artifact_details(root: Path, reference: str | None) -> dict[str, Any]:
    if reference is None:
        return {"reference": None, "sha256": None}
    path = safe_relative_path(root, reference)
    return {
        "reference": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def validate_failure(payload: dict[str, Any]) -> list[str]:
    required = {"schema_version", "type", "failure_id", "run_id", "status", "observed_at", "source", "evidence", "raw_persisted"}
    issues = [f"missing `{field}`" for field in sorted(required - set(payload))]
    if payload.get("schema_version") != SCHEMA_VERSION:
        issues.append("schema_version must be `1`")
    if payload.get("type") != "tailtrail-execution-failure":
        issues.append("type must be `tailtrail-execution-failure`")
    if not isinstance(payload.get("failure_id"), str) or not re.fullmatch(r"failure-[0-9]{4}", payload["failure_id"]):
        issues.append("failure_id must match `failure-0001`")
    if not isinstance(payload.get("run_id"), str) or not IDENTIFIER.fullmatch(payload["run_id"]):
        issues.append("run_id must be a simple identifier")
    if payload.get("status") not in {"observed", "diagnosed", "blocked"}:
        issues.append("status is not allowed")
    if payload.get("source") not in SOURCES:
        issues.append("source is not allowed")
    if payload.get("raw_persisted") is not False:
        issues.append("raw_persisted must be false")
    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        issues.append("evidence must be an object")
    elif set(evidence) != {"artifact_reference", "artifact_sha256", "command_label", "error_code", "exit_code", "project_frame"}:
        issues.append("evidence has an unsupported shape")
    elif not isinstance(evidence.get("exit_code"), (int, type(None))) or (isinstance(evidence.get("exit_code"), int) and evidence["exit_code"] < 0):
        issues.append("exit_code must be a non-negative integer or null")
    diagnosis = payload.get("diagnosis")
    if diagnosis is not None:
        if not isinstance(diagnosis, dict) or set(diagnosis) != {"basis", "classification", "confidence", "hypothesis"}:
            issues.append("diagnosis has an unsupported shape")
        elif diagnosis.get("classification") not in CLASSIFICATIONS or diagnosis.get("confidence") not in CONFIDENCES:
            issues.append("diagnosis classification or confidence is not allowed")
    authority = payload.get("authority")
    if authority is not None:
        if not isinstance(authority, dict) or set(authority) != {"approval_required", "proposed_action", "reason", "route", "status"}:
            issues.append("authority has an unsupported shape")
        elif authority.get("proposed_action") not in ACTIONS or authority.get("status") not in {"allowed", "blocked", "needs-scope-evidence"} or not isinstance(authority.get("approval_required"), bool):
            issues.append("authority decision is not allowed")
    requirement = payload.get("requirement")
    if requirement is not None:
        if not isinstance(requirement, dict) or set(requirement) != {"requirement_uid", "statement"}:
            issues.append("requirement has an unsupported shape")
        elif not isinstance(requirement.get("requirement_uid"), str) or not IDENTIFIER.fullmatch(requirement["requirement_uid"]):
            issues.append("requirement UID is not allowed")
    correlation = payload.get("correlation")
    if correlation is not None:
        required_correlation = {"fingerprint_version", "failure_fingerprint", "signature_fields", "prior_matching_failure_id", "occurrence"}
        if not isinstance(correlation, dict) or set(correlation) != required_correlation:
            issues.append("correlation has an unsupported shape")
        elif correlation.get("fingerprint_version") != "v1" or not isinstance(correlation.get("failure_fingerprint"), str) or not isinstance(correlation.get("occurrence"), int) or correlation["occurrence"] < 1:
            issues.append("correlation is not allowed")
    drift = payload.get("drift_link")
    if drift is not None:
        required_drift = {"drift_created", "requirement_uid", "checkpoint_delta", "evidence_kind", "suspected_paths", "reason"}
        if not isinstance(drift, dict) or set(drift) != required_drift:
            issues.append("drift link has an unsupported shape")
        elif not isinstance(drift.get("drift_created"), bool) or drift.get("checkpoint_delta") not in CHECKPOINT_DELTAS or drift.get("evidence_kind") not in MAP_EVIDENCE or not isinstance(drift.get("suspected_paths"), list):
            issues.append("drift link is not allowed")
    return issues


def intake(root: Path, run_id: str | None, source: str, error_code: str, command_label: str, project_frame: str, exit_code: int | None = None) -> dict[str, Any]:
    """Create an immediate safe receipt; never infer or create a run."""
    root = root.resolve()
    if source not in SOURCES:
        raise ValueError("source is not allowed")
    observed = classify(error_code)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "type": "tailtrail-failure-intake-receipt",
        "source": source,
        "classification": observed,
        "raw_persisted": False,
        "next_action": "attach an approved run before durable failure recording",
    }
    if run_id is None:
        return {**receipt, "status": "not-attached", "reason": "No explicit run ID was supplied; no run-state change was made."}
    safe_identifier(run_id, "run ID")
    try:
        PLANNING.assert_write_allowed(root, run_id)
    except ValueError as error:
        return {**receipt, "status": "not-attached", "run_id": run_id, "reason": str(error)}
    intake_id = next_intake_id(root, run_id)
    payload = {
        **receipt,
        "intake_id": intake_id,
        "run_id": run_id,
        "status": "attached",
        "observed_at": utc_now(),
        "evidence": {
            "command_label": bounded_text(command_label, "command label", 160),
            "error_code": stable_error_code(error_code),
            "exit_code": exit_code,
            "project_frame": bounded_text(project_frame, "project frame", 240),
        },
        "next_action": "record a sanitized failure or diagnose the existing run; no source edit is authorized by this receipt.",
    }
    if not isinstance(exit_code, (int, type(None))) or (isinstance(exit_code, int) and exit_code < 0):
        raise ValueError("exit code must be a non-negative integer or null")
    path = intake_dir(root, run_id) / f"{intake_id}.json"
    LEDGER.atomic_json(path, payload)
    LEDGER.append_event(root, run_id, "execution_failure_intake", {
        "intake_id": intake_id,
        "classification": observed["classification"],
        "confidence": observed["confidence"],
        "error_code": payload["evidence"]["error_code"],
        "status": "attached",
    })
    return {**payload, "artifact": path.relative_to(root).as_posix()}


def diagnose(root: Path, run_id: str, failure_id: str, classification: str, confidence: str, hypothesis: str, proposed_action: str) -> dict[str, Any]:
    root = root.resolve()
    safe_identifier(run_id, "run ID")
    if not re.fullmatch(r"failure-[0-9]{4}", failure_id):
        raise ValueError("failure ID must match `failure-0001`")
    if classification not in CLASSIFICATIONS or confidence not in CONFIDENCES or proposed_action not in ACTIONS:
        raise ValueError("classification, confidence, or proposed action is not allowed")
    PLANNING.assert_write_allowed(root, run_id)
    current = show(root, run_id, failure_id)
    decision = authority_decision(classification, proposed_action)
    payload = {key: value for key, value in current.items() if key != "artifact"}
    payload["status"] = "blocked" if decision["status"] == "blocked" else "diagnosed"
    payload["updated_at"] = utc_now()
    payload["diagnosis"] = {
        "classification": classification,
        "confidence": confidence,
        "basis": "explicit-diagnosis-input",
        "hypothesis": bounded_text(hypothesis, "hypothesis", 280),
    }
    payload["authority"] = {"proposed_action": proposed_action, **decision}
    issues = validate_failure(payload)
    if issues:
        raise ValueError("invalid failure artifact: " + "; ".join(issues))
    path = failure_dir(root, run_id) / f"{failure_id}.json"
    LEDGER.atomic_json(path, payload)
    event_type = "execution_failure_blocked" if payload["status"] == "blocked" else "execution_failure_diagnosed"
    LEDGER.append_event(root, run_id, event_type, {
        "failure_id": failure_id,
        "classification": classification,
        "confidence": confidence,
        "authority_status": decision["status"],
        "route": decision["route"],
    })
    return {**payload, "artifact": path.relative_to(root).as_posix()}


def map_requirement(root: Path, run_id: str, failure_id: str, requirement_uid: str, evidence_kind: str, checkpoint_delta: str, reason: str, suspected_paths: list[str]) -> dict[str, Any]:
    root = root.resolve()
    safe_identifier(run_id, "run ID")
    if not re.fullmatch(r"failure-[0-9]{4}", failure_id):
        raise ValueError("failure ID must match `failure-0001`")
    if evidence_kind not in MAP_EVIDENCE or checkpoint_delta not in CHECKPOINT_DELTAS:
        raise ValueError("evidence kind or checkpoint delta is not allowed")
    PLANNING.assert_write_allowed(root, run_id)
    requirement = approved_requirement(root, run_id, requirement_uid)
    current = show(root, run_id, failure_id)
    allowed_paths = {str(path) for path in requirement.get("likely_paths", [])}
    requested_paths = [safe_project_relative(root, path) for path in suspected_paths]
    architecture = requirement.get("architecture_contract", {})
    behavior = requirement.get("behavior_contract", {})
    supported = {
        "approved-path": bool(requested_paths) and set(requested_paths).issubset(allowed_paths),
        "architecture": bool(architecture.get("required_paths") or architecture.get("protected_paths")),
        "behavior": bool(behavior.get("scenarios")),
        "preservation": bool(requirement.get("preserve_rules")),
        "scope": bool(allowed_paths),
    }[evidence_kind]
    if not supported:
        raise ValueError("mapping evidence does not support this approved requirement")
    classification = current.get("diagnosis", {}).get("classification") or classify(current["evidence"]["error_code"])["classification"]
    fields = normalize_fingerprint_fields(requirement_uid, classification, current["evidence"]["error_code"], current["evidence"]["project_frame"], current["evidence"]["command_label"])
    fingerprint = failure_fingerprint(fields)
    prior = find_matching_open_failure(root, run_id, requirement_uid, fingerprint, failure_id)
    occurrence = int(prior.get("correlation", {}).get("occurrence", 1)) + 1 if prior else 1
    drift_created = checkpoint_delta in {"unchanged", "regressed", "new-drift", "needs-decision"}
    payload = {key: value for key, value in current.items() if key != "artifact"}
    payload["updated_at"] = utc_now()
    payload["requirement"] = {"requirement_uid": requirement_uid, "statement": bounded_text(str(requirement["statement"]), "requirement statement", 280)}
    payload["correlation"] = {
        "fingerprint_version": "v1",
        "failure_fingerprint": fingerprint,
        "signature_fields": fields,
        "prior_matching_failure_id": prior.get("failure_id") if prior else None,
        "occurrence": occurrence,
    }
    payload["drift_link"] = {
        "drift_created": drift_created,
        "requirement_uid": requirement_uid,
        "checkpoint_delta": checkpoint_delta,
        "evidence_kind": evidence_kind,
        "suspected_paths": requested_paths,
        "reason": bounded_text(reason, "drift reason", 320),
    }
    issues = validate_failure(payload)
    if issues:
        raise ValueError("invalid failure artifact: " + "; ".join(issues))
    path = failure_dir(root, run_id) / f"{failure_id}.json"
    LEDGER.atomic_json(path, payload)
    LEDGER.append_event(root, run_id, "execution_failure_mapped", {
        "failure_id": failure_id,
        "requirement_uid": requirement_uid,
        "checkpoint_delta": checkpoint_delta,
        "drift_created": drift_created,
        "occurrence": occurrence,
        "evidence_kind": evidence_kind,
    })
    return {**payload, "artifact": path.relative_to(root).as_posix()}


def correction_route(root: Path, run_id: str, failure_id: str, max_cycles: int) -> dict[str, Any]:
    root = root.resolve()
    PLANNING.assert_write_allowed(root, run_id)
    current = show(root, run_id, failure_id)
    drift = current.get("drift_link")
    requirement = current.get("requirement")
    if not isinstance(drift, dict) or not isinstance(requirement, dict) or drift.get("drift_created") is not True:
        raise ValueError("an evidence-backed requirement drift link is required before correction routing")
    authority = current.get("authority", {})
    if authority.get("status") == "blocked":
        result = {"action": "blocked", "requires_approval": True, "reason": authority.get("reason", "protected authority boundary"), "correction_executed": False}
    else:
        convergence = CONVERGENCE.assess(root, run_id, requirement["requirement_uid"], drift["checkpoint_delta"], max_cycles)
        result = {key: value for key, value in convergence.items() if key != "path"}
        result["artifact"] = Path(convergence["path"]).relative_to(root).as_posix()
        result["correction_executed"] = False
        result["boundary"] = "This route records one bounded next action only; it does not edit source or execute a retry."
    payload = {key: value for key, value in current.items() if key != "artifact"}
    payload["updated_at"] = utc_now()
    payload["correction_route"] = result
    issues = validate_failure(payload)
    if issues:
        raise ValueError("invalid failure artifact: " + "; ".join(issues))
    path = failure_dir(root, run_id) / f"{failure_id}.json"
    LEDGER.atomic_json(path, payload)
    LEDGER.append_event(root, run_id, "execution_failure_correction_routed", {
        "failure_id": failure_id,
        "requirement_uid": requirement["requirement_uid"],
        "action": result["action"],
        "requires_approval": result["requires_approval"],
        "correction_executed": False,
    })
    return {**payload, "artifact": path.relative_to(root).as_posix()}


def readiness(root: Path, run_id: str) -> dict[str, Any]:
    """Read-only setup/failure readiness; it cannot approve or execute work."""
    root = root.resolve(); safe_identifier(run_id, "run ID")
    PLANNING.show(root, run_id)
    scan = SETUP_SCAN.build_report(root, include_untracked=False)
    records = [json.loads(path.read_text(encoding="utf-8")) for path in list_failures(root, run_id)]
    blocked = [item["failure_id"] for item in records if item.get("status") == "blocked"]
    unresolved = [item["failure_id"] for item in records if item.get("status") != "resolved"]
    status = "blocked" if blocked else ("needs-correction" if unresolved else "ready")
    return {"schema_version": SCHEMA_VERSION, "type": "tailtrail-failure-readiness", "run_id": run_id, "status": status, "setup": {"warnings": scan.get("warnings", []), "tracked_local_state": scan.get("summary", {}).get("local runtime state", 0)}, "failures": {"blocked": blocked, "unresolved": unresolved}, "boundary": "Read-only readiness evidence. It does not approve implementation, change setup, run commands, or mutate external systems."}


def record(root: Path, run_id: str, source: str, error_code: str, command_label: str, project_frame: str, exit_code: int | None, artifact_reference: str | None) -> dict[str, Any]:
    root = root.resolve()
    safe_identifier(run_id, "run ID")
    PLANNING.assert_write_allowed(root, run_id)
    details = artifact_details(root, artifact_reference)
    failure_id = next_failure_id(root, run_id)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "type": "tailtrail-execution-failure",
        "failure_id": failure_id,
        "run_id": run_id,
        "status": "observed",
        "observed_at": utc_now(),
        "source": source,
        "raw_persisted": False,
        "evidence": {
            "artifact_reference": details["reference"],
            "artifact_sha256": details["sha256"],
            "command_label": bounded_text(command_label, "command label", 160),
            "error_code": stable_error_code(error_code),
            "exit_code": exit_code,
            "project_frame": bounded_text(project_frame, "project frame", 240),
        },
    }
    issues = validate_failure(payload)
    if issues:
        raise ValueError("invalid failure artifact: " + "; ".join(issues))
    path = failure_dir(root, run_id) / f"{failure_id}.json"
    LEDGER.atomic_json(path, payload)
    LEDGER.append_event(root, run_id, "execution_failure_recorded", {
        "failure_id": failure_id,
        "source": source,
        "error_code": payload["evidence"]["error_code"],
        "command_label": payload["evidence"]["command_label"],
        "artifact_reference": details["reference"],
    })
    return {**payload, "artifact": path.relative_to(root).as_posix()}


def show(root: Path, run_id: str, failure_id: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    safe_identifier(run_id, "run ID")
    selected = failure_id or (list_failures(root, run_id)[-1].stem if list_failures(root, run_id) else None)
    if selected is None:
        raise ValueError(f"run `{run_id}` has no failure artifacts")
    if not re.fullmatch(r"failure-[0-9]{4}", selected):
        raise ValueError("failure ID must match `failure-0001`")
    path = failure_dir(root, run_id) / f"{selected}.json"
    if not path.is_file():
        raise ValueError(f"failure artifact `{selected}` does not exist")
    payload = json.loads(path.read_text(encoding="utf-8"))
    issues = validate_failure(payload)
    if issues:
        raise ValueError("invalid failure artifact: " + "; ".join(issues))
    return {**payload, "artifact": path.relative_to(root).as_posix()}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Record or inspect sanitized TailTrail execution failures.")
    sub = result.add_subparsers(dest="command", required=True)
    record_parser = sub.add_parser("record", help="Save bounded metadata only; raw error text is never accepted.")
    record_parser.add_argument("--root", type=Path, default=Path.cwd())
    record_parser.add_argument("--run-id", required=True)
    record_parser.add_argument("--source", choices=SOURCES, required=True)
    record_parser.add_argument("--error-code", required=True)
    record_parser.add_argument("--command-label", required=True)
    record_parser.add_argument("--project-frame", required=True)
    record_parser.add_argument("--exit-code", type=int)
    record_parser.add_argument("--artifact-reference")
    intake_parser = sub.add_parser("intake", help="Return an immediate sanitized receipt; never creates a new run.")
    intake_parser.add_argument("--root", type=Path, default=Path.cwd())
    intake_parser.add_argument("--run-id")
    intake_parser.add_argument("--source", choices=SOURCES, required=True)
    intake_parser.add_argument("--error-code", required=True)
    intake_parser.add_argument("--command-label", required=True)
    intake_parser.add_argument("--project-frame", required=True)
    intake_parser.add_argument("--exit-code", type=int)
    diagnose_parser = sub.add_parser("diagnose", help="Save provisional classification and authority routing; never edit source.")
    diagnose_parser.add_argument("--root", type=Path, default=Path.cwd())
    diagnose_parser.add_argument("--run-id", required=True)
    diagnose_parser.add_argument("--failure-id", required=True)
    diagnose_parser.add_argument("--classification", choices=CLASSIFICATIONS, required=True)
    diagnose_parser.add_argument("--confidence", choices=CONFIDENCES, required=True)
    diagnose_parser.add_argument("--hypothesis", required=True)
    diagnose_parser.add_argument("--proposed-action", choices=ACTIONS, default="read-only-diagnosis")
    map_parser = sub.add_parser("map", help="Link a failure to approved requirement evidence and record drift state.")
    map_parser.add_argument("--root", type=Path, default=Path.cwd())
    map_parser.add_argument("--run-id", required=True)
    map_parser.add_argument("--failure-id", required=True)
    map_parser.add_argument("--requirement-uid", required=True)
    map_parser.add_argument("--evidence-kind", choices=MAP_EVIDENCE, required=True)
    map_parser.add_argument("--checkpoint-delta", choices=CHECKPOINT_DELTAS, required=True)
    map_parser.add_argument("--reason", required=True)
    map_parser.add_argument("--suspected-path", action="append", default=[])
    correction_parser = sub.add_parser("correction-route", help="Record one bounded correction, recovery, or replan route; never apply it.")
    correction_parser.add_argument("--root", type=Path, default=Path.cwd())
    correction_parser.add_argument("--run-id", required=True)
    correction_parser.add_argument("--failure-id", required=True)
    correction_parser.add_argument("--max-cycles", type=int, default=2)
    readiness_parser = sub.add_parser("readiness", help="Read setup and failure readiness for an existing run.")
    readiness_parser.add_argument("--root", type=Path, default=Path.cwd())
    readiness_parser.add_argument("--run-id", required=True)
    show_parser = sub.add_parser("show", help="Read a sanitized local failure artifact.")
    show_parser.add_argument("--root", type=Path, default=Path.cwd())
    show_parser.add_argument("--run-id", required=True)
    show_parser.add_argument("--failure-id")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "record":
            payload = record(args.root, args.run_id, args.source, args.error_code, args.command_label, args.project_frame, args.exit_code, args.artifact_reference)
        elif args.command == "intake":
            payload = intake(args.root, args.run_id, args.source, args.error_code, args.command_label, args.project_frame, args.exit_code)
        elif args.command == "diagnose":
            payload = diagnose(args.root, args.run_id, args.failure_id, args.classification, args.confidence, args.hypothesis, args.proposed_action)
        elif args.command == "map":
            payload = map_requirement(args.root, args.run_id, args.failure_id, args.requirement_uid, args.evidence_kind, args.checkpoint_delta, args.reason, args.suspected_path)
        elif args.command == "correction-route":
            payload = correction_route(args.root, args.run_id, args.failure_id, args.max_cycles)
        elif args.command == "readiness":
            payload = readiness(args.root, args.run_id)
        else:
            payload = show(args.root, args.run_id, args.failure_id)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"Execution failure error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
