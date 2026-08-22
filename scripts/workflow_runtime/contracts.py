"""Validate closed DWR-0 contracts, safe references, sizes, and privacy fields."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from workflow_runtime import reason_codes


ROOT = Path(__file__).resolve().parents[2]
MAX_ARTIFACT_BYTES = 256 * 1024
MAX_EVENT_BYTES = 16 * 1024
DISALLOWED_FIELDS = {"prompt", "raw_prompt", "raw_source", "source_body", "raw_log", "secret", "credential", "password", "private_key", "api_key", "access_token", "authorization", "cookie", "user_identity", "customer_data", "email", "ip_address", "full_name"}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bBearer [A-Za-z0-9._-]{20,}\b", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
)
SCHEMA_BY_TYPE = {
    "tailtrail-workflow-instance": "workflow-instance.schema.json",
    "tailtrail-workflow-stage": "workflow-stage.schema.json",
    "tailtrail-workflow-action": "workflow-action.schema.json",
    "tailtrail-workflow-transition": "workflow-transition.schema.json",
    "tailtrail-workflow-approval-record": "workflow-approval-record.schema.json",
    "tailtrail-workflow-evidence-record": "workflow-evidence-record.schema.json",
    "tailtrail-workflow-context-receipt": "workflow-context-receipt.schema.json",
    "tailtrail-workflow-token-telemetry": "workflow-token-telemetry.schema.json",
    "tailtrail-workflow-learning-link": "workflow-learning-link.schema.json",
    "tailtrail-workflow-evaluation-event": "workflow-evaluation-event.schema.json",
    "tailtrail-workflow-meta-harness-signal": "workflow-meta-harness-signal.schema.json",
    "tailtrail-workflow-ci-policy": "workflow-ci-policy.schema.json",
    "tailtrail-workflow-ci-receipt": "workflow-ci-receipt.schema.json",
    "tailtrail-workflow-ci-continuation": "workflow-ci-continuation.schema.json",
    "tailtrail-workflow-denial-audit": "workflow-denial-audit.schema.json",
    "tailtrail-workflow-retention-policy": "workflow-retention-policy.schema.json",
    "tailtrail-workflow-retention-plan": "workflow-retention-plan.schema.json",
    "tailtrail-workflow-retention-cleanup": "workflow-retention-cleanup.schema.json",
    "tailtrail-workflow-assurance-report": "workflow-assurance-report.schema.json",
    "tailtrail-workflow-release-scenario": "workflow-release-scenario.schema.json",
    "tailtrail-workflow-real-run-proof": "workflow-real-run-proof.schema.json",
    "tailtrail-workflow-release-gate": "workflow-release-gate.schema.json",
    "tailtrail-workflow-compatibility-report": "workflow-compatibility-report.schema.json",
    "tailtrail-workflow-retirement-decision": "workflow-retirement-decision.schema.json",
    "tailtrail-workflow-enterprise-policy": "workflow-enterprise-policy.schema.json",
    "tailtrail-workflow-enterprise-binding": "workflow-enterprise-binding.schema.json",
    "tailtrail-workflow-enterprise-lease": "workflow-enterprise-lease.schema.json",
    "tailtrail-workflow-enterprise-event": "workflow-enterprise-event.schema.json",
    "tailtrail-workflow-enterprise-link": "workflow-enterprise-link.schema.json",
    "tailtrail-workflow-enterprise-backup": "workflow-enterprise-backup.schema.json",
    "tailtrail-workflow-enterprise-migration": "workflow-enterprise-migration.schema.json",
    "tailtrail-workflow-enterprise-conformance": "workflow-enterprise-conformance.schema.json",
    "tailtrail-workflow-enterprise-entry": "workflow-enterprise-entry.schema.json",
    "tailtrail-workflow-enterprise-replay": "workflow-enterprise-replay.schema.json",
    "tailtrail-workflow-enterprise-observability": "workflow-enterprise-observability.schema.json",
    "tailtrail-workflow-enterprise-restore-validation": "workflow-enterprise-restore-validation.schema.json",
    "tailtrail-workflow-completion-contract": "workflow-completion-contract.schema.json",
    "tailtrail-workflow-runtime-event": "workflow-runtime-event.schema.json",
    "tailtrail-workflow-ownership-binding": "workflow-ownership.schema.json",
    "tailtrail-workflow-capability-plan": "workflow-capability-plan.schema.json",
    "tailtrail-workflow-preapproval": "workflow-preapproval.schema.json",
    "tailtrail-workflow-task-scope": "workflow-task-scope.schema.json",
    "tailtrail-workflow-code-change-reservation": "workflow-code-change-reservation.schema.json",
    "tailtrail-workflow-storage-event": "workflow-storage-event.schema.json",
    "tailtrail-workflow-projection": "workflow-projection.schema.json",
    "tailtrail-workflow-compiler-plan": "workflow-compiler-plan.schema.json",
    "tailtrail-workflow-stage-approvals": "workflow-stage-approvals.schema.json",
    "tailtrail-workflow-evidence": "workflow-evidence.schema.json",
    "tailtrail-workflow-completion-receipt": "workflow-completion-receipt.schema.json",
    "tailtrail-workflow-adapter-input": "workflow-adapter-input.schema.json",
    "tailtrail-workflow-adapter-output": "workflow-adapter-output.schema.json",
    "tailtrail-workflow-template-execution": "workflow-template-execution.schema.json",
    "tailtrail-workflow-risk-authority": "workflow-risk-authority.schema.json",
    "tailtrail-workflow-operational-checkpoint": "workflow-operational-checkpoint.schema.json",
    "tailtrail-workflow-freshness-assessment": "workflow-freshness-assessment.schema.json",
    "tailtrail-workflow-retry-attempts": "workflow-retry-attempts.schema.json",
    "tailtrail-workflow-correction-packet": "workflow-correction-packet.schema.json",
}


def safe_relative(value: str) -> bool:
    path = Path(value.partition("#")[0])
    return bool(value) and not path.is_absolute() and ".." not in path.parts and not re.match(r"^[A-Za-z]:", value)


def _matches_type(value: Any, expected: str) -> bool:
    mapping = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool, "null": type(None)}
    return isinstance(value, mapping[expected]) and not (expected in {"integer", "number"} and isinstance(value, bool))


def validate_document(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    issues: list[str] = []
    if "const" in schema and value != schema["const"]: issues.append(f"{path} must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]: issues.append(f"{path} has unsupported value {value!r}")
    expected = schema.get("type")
    if expected:
        choices = expected if isinstance(expected, list) else [expected]
        if not any(_matches_type(value, item) for item in choices):
            return [f"{path} must have type {' or '.join(choices)}"]
    if isinstance(value, dict):
        required = schema.get("required", [])
        issues.extend(f"{path}.{key} is required" for key in required if key not in value)
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            issues.extend(f"{path}.{key} is not allowed" for key in value if key not in properties)
        additional = schema.get("additionalProperties")
        for key, item in value.items():
            child = properties.get(key, additional if isinstance(additional, dict) else None)
            if isinstance(child, dict): issues.extend(validate_document(item, child, f"{path}.{key}"))
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0): issues.append(f"{path} has too few items")
        maximum = schema.get("maxItems")
        if maximum is not None and len(value) > maximum: issues.append(f"{path} has too many items")
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value): issues.append(f"{path} must contain unique items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value): issues.extend(validate_document(item, item_schema, f"{path}[{index}]"))
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0): issues.append(f"{path} is too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]: issues.append(f"{path} is too long")
        if "pattern" in schema and re.search(schema["pattern"], value) is None: issues.append(f"{path} does not match {schema['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]: issues.append(f"{path} is below minimum")
    return issues


def _privacy_issues(value: Any, path: str = "$") -> list[str]:
    issues: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in DISALLOWED_FIELDS: issues.append(f"{path}.{key} is a disallowed privacy field")
            issues.extend(_privacy_issues(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value): issues.extend(_privacy_issues(item, f"{path}[{index}]"))
    elif isinstance(value, str) and any(pattern.search(value) for pattern in SECRET_PATTERNS):
        issues.append(f"{path} contains secret-like material")
    return issues


def privacy_issues(value: Any) -> list[str]:
    """Return categorical-safe validation findings; callers must not echo values."""
    return _privacy_issues(value)


def _reference_issues(value: Any, path: str = "$") -> list[str]:
    issues: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if (key.endswith("_ref") or key in {"ref", "artifact"}) and isinstance(item, str) and not safe_relative(item): issues.append(f"{path}.{key} must be a safe relative reference")
            if key.endswith("_refs") and isinstance(item, list):
                issues.extend(f"{path}.{key}[{index}] must be a safe relative reference" for index, ref in enumerate(item) if isinstance(ref, str) and not safe_relative(ref))
            issues.extend(_reference_issues(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value): issues.extend(_reference_issues(item, f"{path}[{index}]"))
    return issues


def validate_artifact(value: dict[str, Any], root: Path = ROOT) -> list[str]:
    if value.get("schema_version") != "1": return ["$.schema_version is unsupported; only version 1 is accepted"]
    artifact_type = value.get("type")
    filename = SCHEMA_BY_TYPE.get(str(artifact_type))
    if not filename: return [f"$.type has no registered DWR-0 schema: {artifact_type!r}"]
    encoded = json.dumps(value, separators=(",", ":")).encode("utf-8")
    limit = MAX_EVENT_BYTES if artifact_type in {"tailtrail-workflow-runtime-event", "tailtrail-workflow-storage-event"} else MAX_ARTIFACT_BYTES
    issues = ["artifact exceeds its DWR-0 size limit"] if len(encoded) > limit else []
    schema = json.loads((root / "schemas" / filename).read_text(encoding="utf-8"))
    issues.extend(validate_document(value, schema)); issues.extend(_privacy_issues(value)); issues.extend(_reference_issues(value))
    if artifact_type == "tailtrail-workflow-stage-approvals":
        record_schema = json.loads((root / "schemas" / "workflow-approval-record.schema.json").read_text(encoding="utf-8"))
        for index, record in enumerate(value.get("approvals", [])):
            issues.extend(validate_document(record, record_schema, f"$.approvals[{index}]"))
    if artifact_type == "tailtrail-workflow-transition":
        if value.get("reason_code") not in reason_codes.REASON_CODES: issues.append("$.reason_code is not registered")
        if bool(value.get("legal")) != reason_codes.transition_allowed(str(value.get("scope")), str(value.get("from_state")), str(value.get("to_state"))): issues.append("transition legality differs from the canonical table")
    if artifact_type in {"tailtrail-workflow-approval-record", "tailtrail-workflow-runtime-event"} and value.get("reason_code") not in reason_codes.REASON_CODES: issues.append("$.reason_code is not registered")
    if artifact_type == "tailtrail-workflow-stage":
        skip_code = value.get("skip_rule", {}).get("reason_code") if isinstance(value.get("skip_rule"), dict) else None
        if skip_code is not None and skip_code not in reason_codes.REASON_CODES: issues.append("$.skip_rule.reason_code is not registered")
    return issues


def require_valid(value: dict[str, Any], root: Path = ROOT) -> None:
    issues = validate_artifact(value, root)
    if issues: raise ValueError("DWR-0 contract violation: " + "; ".join(issues))
