#!/usr/bin/env python3
"""Fail-closed sensitive-data boundary for official AI-DLC bridge artifacts."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SHA256 = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
SECRET_PATTERNS = (
    ("private-key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", re.IGNORECASE)),
    ("bearer-token", re.compile(r"\bbearer\s+[a-z0-9._~+/-]{12,}=*", re.IGNORECASE)),
    ("secret-assignment", re.compile(r"\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password|passwd|secret|token)\b\s*[:=]\s*['\"]?[^'\"\s,;]{8,}", re.IGNORECASE)),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("credential-uri", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/@:]+:[^\s/@]+@", re.IGNORECASE)),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
)
PROMPT_PATTERNS = (
    re.compile(r"\bignore\s+(?:all\s+)?previous\s+instructions\b", re.IGNORECASE),
    re.compile(r"(?:^|\n)\s*(?:system|developer)\s*:", re.IGNORECASE),
    re.compile(r"<\/?(?:system|developer|assistant)>\s*", re.IGNORECASE),
    re.compile(r"```"),
)
BLOCKED_FIELDS = {
    "raw_prompt", "prompt", "source_code", "source_body", "diff", "patch", "log", "logs",
    "stdout", "stderr", "stack_trace", "traceback", "environment_dump", "environment_variables",
    "credentials", "credential", "password", "secret", "token", "authorization", "customer_data",
    "pii", "phi", "receipt_body", "deployment_data",
}
COMMON = {"schema_version", "type", "run_id", "boundary"}
CONTEXT_FIELDS = {
    "bridge": COMMON | {"phase", "tailtrail_run_id", "mode", "state", "official_source", "official_revision", "official_intent_id", "official_session_id", "official_stage", "host_adapter", "compatibility_manifest", "compatibility_state"},
    "activation": COMMON | {"phase", "tailtrail_run_id", "bridge_artifact", "state", "official_intent_id", "official_session_id", "official_stage"},
    "requirements": {"stage", "authority", "official_stage", "official_references", "official_intent_id", "official_session_id", "goal", "requirements", "questions", "question_markdown", "stage_gate"},
    "requirements-revision": {"goal", "requirements", "official_decisions", "official_stage", "authority", "approval_summary"},
    "closure": COMMON | {"official_intent_id", "official_session_id", "official_revision", "completion_report", "official_handoff_reference", "official_operations_references", "official_runtime_session", "official_current_stage", "official_transition_count", "acceptance_state"},
    "learning": COMMON | {"candidate_id", "acceptance", "requirements_completed", "evidence_tiers", "selected_harnesses", "pattern", "promotion", "sanitization", "source_report", "debug_profile"},
    "evaluation": COMMON | {"evaluation_id", "evidence_label", "mode", "baseline", "tailtrail_outcome", "comparison"},
    "runtime-session": COMMON | {"runtime_adapter_version", "bridge_artifact", "compatibility_manifest", "official_source", "official_revision", "official_intent_id", "official_session_id", "initial_stage", "host_adapter", "state", "approved_anchor_fingerprint"},
    "runtime-transition": COMMON | {"receipt_id", "official_session_id", "official_revision", "sequence", "action", "from_stage", "to_stage", "authority", "runtime_adapter_version", "approved_anchor_fingerprint", "reason_code", "requirement_uids", "evidence_references", "integrity"},
    "host-runtime-receipt": COMMON | {"receipt_id", "host", "host_version", "adapter_version", "scenario_version", "bundle_digest", "scenario_id", "observed_transitions", "observations", "artifact_references", "declared_outcome", "failure_codes", "integrity"},
}
CHECKPOINT_FIELDS = {
    "tailtrail-official-aidlc-design-plan": COMMON | {"official_stage", "official_intent_id", "requirements", "perspectives", "decisions", "discovery_frame"},
    "tailtrail-official-aidlc-design-decision": COMMON | {"official_stage", "approved", "design_plan", "decisions", "perspectives"},
    "tailtrail-official-aidlc-test-plan-bridge": COMMON | {"official_stage", "official_test_strategy", "design_decision", "requirements"},
    "tailtrail-official-aidlc-construction-checkpoint": COMMON | {"official_stage", "source_checkpoint", "requirements", "missing_requirement_uids", "complete"},
    "tailtrail-official-aidlc-evidence-checkpoint": COMMON | {"official_stage", "test_plan", "requirements", "receipt_artifacts", "gaps", "complete"},
    "tailtrail-official-aidlc-correction-packet": COMMON | {"official_return_stage", "gaps", "checkpoint"},
    "tailtrail-official-aidlc-handoff": COMMON | {"official_stage", "evidence_checkpoint", "ready", "next_stage"},
}


class SanitizationError(ValueError):
    def __init__(self, code: str, field: str) -> None:
        self.code = code
        self.field = field
        super().__init__(f"official AI-DLC sanitization rejected field `{field}` [{code}]")


def _reject_secret(value: str, field: str) -> None:
    for code, pattern in SECRET_PATTERNS:
        if pattern.search(value):
            raise SanitizationError(code, field)


def identifier(value: Any, field: str) -> str:
    text = str(value or "").strip()
    _reject_secret(text, field)
    if text in {"", ".", ".."} or not IDENTIFIER.fullmatch(text):
        raise SanitizationError("invalid-identifier", field)
    return text


def summary(value: Any, field: str, maximum: int = 2000, *, allow_multiline: bool = False) -> str:
    text = str(value or "").strip()
    if not text or len(text) > maximum or (not allow_multiline and ("\n" in text or "\r" in text)):
        raise SanitizationError("invalid-summary-shape", field)
    _reject_secret(text, field)
    if any(pattern.search(text) for pattern in PROMPT_PATTERNS):
        raise SanitizationError("raw-prompt-shape", field)
    return text


def local_reference(root: Path, value: Any, field: str, *, must_exist: bool = True) -> str:
    text = str(value or "").strip()
    _reject_secret(text, field)
    candidate = Path(text)
    if not text or candidate.is_absolute() or any(part == ".." for part in candidate.parts):
        raise SanitizationError("unsafe-local-reference", field)
    resolved = (root.resolve() / candidate).resolve()
    try:
        relative = resolved.relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise SanitizationError("unsafe-local-reference", field) from error
    if must_exist and not resolved.is_file():
        raise SanitizationError("missing-local-reference", field)
    return relative


def external_reference(value: Any, field: str) -> str:
    text = str(value or "").strip()
    _reject_secret(text, field)
    parsed = urlsplit(text)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise SanitizationError("unsafe-external-reference", field)
    return text


def _scan(value: Any, field: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            name = str(key)
            child_field = f"{field}.{name}"
            if name.lower() in BLOCKED_FIELDS:
                raise SanitizationError("blocked-field", child_field)
            _scan(child, child_field)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan(child, f"{field}[{index}]")
    elif isinstance(value, str):
        if len(value) > 12000:
            raise SanitizationError("value-too-long", field)
        _reject_secret(value, field)
        leaf = field.rsplit(".", 1)[-1].split("[", 1)[0].lower()
        if leaf in {"goal", "statement", "detail", "comment", "selected", "reasoning", "question", "question_markdown", "approval_summary", "pattern"} and any(pattern.search(value) for pattern in PROMPT_PATTERNS):
            raise SanitizationError("raw-prompt-shape", field)


def _top_level(payload: dict[str, Any], allowed: set[str], context: str) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise SanitizationError("unknown-field", f"{context}.{unknown[0]}")


def validate_artifact(root: Path, payload: dict[str, Any], context: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SanitizationError("invalid-object", context)
    allowed = CHECKPOINT_FIELDS.get(str(payload.get("type"))) if context == "checkpoint" else CONTEXT_FIELDS.get(context)
    if allowed is None:
        raise SanitizationError("unsupported-context-or-type", context)
    _top_level(payload, allowed, context)
    _scan(payload, context)

    for field in ("run_id", "tailtrail_run_id", "official_intent_id", "official_session_id", "candidate_id", "evaluation_id"):
        if field in payload:
            identifier(payload[field], f"{context}.{field}")
    if context == "bridge":
        external_reference(payload.get("official_source"), "bridge.official_source")
        local_reference(root, payload.get("compatibility_manifest"), "bridge.compatibility_manifest")
        adapter = payload.get("host_adapter")
        if not isinstance(adapter, dict) or set(adapter) - {"host", "rules_path"}:
            raise SanitizationError("unknown-field", "bridge.host_adapter")
        identifier(adapter.get("host"), "bridge.host_adapter.host")
        manifest = (root / str(payload["compatibility_manifest"])).resolve()
        local_reference(manifest.parent, adapter.get("rules_path"), "bridge.host_adapter.rules_path")
    if context == "runtime-session":
        external_reference(payload.get("official_source"), "runtime-session.official_source")
        local_reference(root, payload.get("bridge_artifact"), "runtime-session.bridge_artifact")
        local_reference(root, payload.get("compatibility_manifest"), "runtime-session.compatibility_manifest")
        adapter = payload.get("host_adapter")
        if not isinstance(adapter, dict) or set(adapter) - {"host", "rules_path"}:
            raise SanitizationError("unknown-field", "runtime-session.host_adapter")
        identifier(adapter.get("host"), "runtime-session.host_adapter.host")
    if context == "runtime-transition":
        for field in ("receipt_id", "official_session_id", "official_revision", "action", "from_stage", "to_stage", "authority", "runtime_adapter_version", "reason_code"):
            identifier(payload.get(field), f"runtime-transition.{field}")
        if payload.get("action") not in {"advance", "resume", "redo", "jump", "recovery"}:
            raise SanitizationError("invalid-transition-action", "runtime-transition.action")
        stages = {"requirements", "design", "implementation", "build-and-test", "handoff", "operations"}
        if payload.get("from_stage") not in stages or payload.get("to_stage") not in stages:
            raise SanitizationError("invalid-transition-stage", "runtime-transition.stage")
        if not isinstance(payload.get("sequence"), int) or payload["sequence"] < 1:
            raise SanitizationError("invalid-transition-sequence", "runtime-transition.sequence")
        integrity = payload.get("integrity")
        if not isinstance(integrity, dict) or set(integrity) != {"algorithm", "digest"} or integrity.get("algorithm") != "sha256" or not SHA256.fullmatch(str(integrity.get("digest", ""))):
            raise SanitizationError("invalid-integrity", "runtime-transition.integrity")
        for index, uid in enumerate(payload.get("requirement_uids", [])):
            identifier(uid, f"runtime-transition.requirement_uids[{index}]")
        for index, value in enumerate(payload.get("evidence_references", [])):
            local_reference(root, value, f"runtime-transition.evidence_references[{index}]")
    if context == "host-runtime-receipt":
        for field in ("receipt_id", "host", "host_version", "adapter_version", "scenario_version", "scenario_id", "declared_outcome"):
            identifier(payload.get(field), f"host-runtime-receipt.{field}")
        if payload.get("host") not in {"codex", "copilot", "claude"}:
            raise SanitizationError("invalid-host", "host-runtime-receipt.host")
        if payload.get("declared_outcome") not in {"pass", "fail"}:
            raise SanitizationError("invalid-outcome", "host-runtime-receipt.declared_outcome")
        if not SHA256.fullmatch(str(payload.get("bundle_digest", ""))):
            raise SanitizationError("invalid-integrity", "host-runtime-receipt.bundle_digest")
        integrity = payload.get("integrity")
        if not isinstance(integrity, dict) or set(integrity) != {"algorithm", "digest"} or integrity.get("algorithm") != "sha256" or not SHA256.fullmatch(str(integrity.get("digest", ""))):
            raise SanitizationError("invalid-integrity", "host-runtime-receipt.integrity")
        for index, transition in enumerate(payload.get("observed_transitions", [])):
            if not isinstance(transition, dict) or set(transition) != {"sequence", "state"}:
                raise SanitizationError("invalid-transition-shape", f"host-runtime-receipt.observed_transitions[{index}]")
            identifier(transition.get("state"), f"host-runtime-receipt.observed_transitions[{index}].state")
        for field in ("observations", "failure_codes"):
            for index, value in enumerate(payload.get(field, [])):
                identifier(value, f"host-runtime-receipt.{field}[{index}]")
        for index, value in enumerate(payload.get("artifact_references", [])):
            local_reference(root, value, f"host-runtime-receipt.artifact_references[{index}]")
    if context in {"requirements", "requirements-revision"}:
        summary(payload.get("goal"), f"{context}.goal")
        for index, row in enumerate(payload.get("requirements", [])):
            if not isinstance(row, dict):
                raise SanitizationError("invalid-object", f"{context}.requirements[{index}]")
            if row.get("requirement_uid"):
                identifier(row["requirement_uid"], f"{context}.requirements[{index}].requirement_uid")
            summary(row.get("statement"), f"{context}.requirements[{index}].statement")
            for path_index, path in enumerate(row.get("likely_paths", [])):
                local_reference(root, path, f"{context}.requirements[{index}].likely_paths[{path_index}]", must_exist=False)
        for key, value in payload.get("official_references", {}).items():
            local_reference(root, value, f"{context}.official_references.{key}")
    if context == "checkpoint":
        for field in ("design_plan", "design_decision", "source_checkpoint", "test_plan", "checkpoint", "evidence_checkpoint"):
            if payload.get(field):
                local_reference(root, payload[field], f"checkpoint.{field}")
        for index, value in enumerate(payload.get("receipt_artifacts", [])):
            local_reference(root, value, f"checkpoint.receipt_artifacts[{index}]")
    if context == "closure":
        for field in ("completion_report", "official_handoff_reference", "official_runtime_session"):
            if payload.get(field):
                local_reference(root, payload[field], f"closure.{field}")
        for index, value in enumerate(payload.get("official_operations_references", [])):
            local_reference(root, value, f"closure.official_operations_references[{index}]")
    return {"status": "passed", "context": context, "type": payload.get("type"), "fields_checked": len(payload), "boundary": "No raw values are copied into this report. Validation is read-only and fail-closed."}


def validate_input(payload: dict[str, Any], context: str) -> dict[str, Any]:
    """Check supplied exact evidence without rewriting it or copying its values."""
    if not isinstance(payload, dict):
        raise SanitizationError("invalid-object", context)
    _scan(payload, context)
    return {"status": "passed", "context": context, "fields_checked": len(payload), "boundary": "Input was inspected in place. No values were copied or rewritten."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate",))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--context", choices=sorted([*CONTEXT_FIELDS, "checkpoint"]), required=True)
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        reference = local_reference(root, args.input, "input")
        payload = json.loads((root / reference).read_text(encoding="utf-8"))
        print(json.dumps(validate_artifact(root, payload, args.context), indent=2, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, SanitizationError) as error:
        print(str(error) if isinstance(error, SanitizationError) else "official AI-DLC sanitization rejected input [invalid-json]")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
