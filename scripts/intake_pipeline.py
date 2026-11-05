"""Minimal Phase 1A intake contract and interaction event pipeline."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import shutil
import uuid
from pathlib import Path
from typing import Any


class IntakeError(ValueError):
    """Raised when an intake operation cannot satisfy its contract."""


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _content_fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


_SENSITIVE_KEY = re.compile(r"(?:password|passphrase|secret|token|api[_-]?key|private[_-]?key)", re.I)
_SENSITIVE_VALUE = re.compile(r"(?:Bearer\s+|token\s*[:=]\s*|secret\s*[:=]\s*)\S+", re.I)
_ANCHOR_VERSION = re.compile(r"^anchor-v[1-9][0-9]*$")
_PACKET_VIEW_PROJECTION_KINDS = frozenset({"scope", "requirement", "validation", "approval"})
_PATH_ROLES = frozenset({
    "implementation-owner",
    "inspection-input",
    "proof-only",
    "configuration-output",
    "generated-output",
})
_OUTPUT_PATH_ROLES = frozenset({"configuration-output", "generated-output"})
_WRITABLE_PATH_ROLES = frozenset({"implementation-owner", *_OUTPUT_PATH_ROLES})
_PATH_ROLE_CLASSES = {
    "implementation-owner": "behavioral-owner",
    "inspection-input": "read-only-input",
    "proof-only": "proof-only",
    "configuration-output": "writable-output",
    "generated-output": "writable-output",
}
_PATH_BINDING_SCHEMA_VERSION = "2"
_NEW_FILE_VERDICTS = frozenset({
    "new-confirmed", "extend-recommended", "collision-blocked", "unverified", "not-applicable",
})
_CORRECTION_PREMISES = frozenset({"accepted", "not-applicable"})
_ANSWER_STATES = frozenset({"candidate", "accepted", "stale", "conflicting", "rejected"})
_INTAKE_RECORDED = "intake-recorded"
_PLANNING_READINESS = "planning-readiness"
_REQUIREMENT_DISCOVERY: Any = None


def _requirement_discovery() -> Any:
    """Load the shared requirement-kind contract without duplicating policy."""
    global _REQUIREMENT_DISCOVERY
    if _REQUIREMENT_DISCOVERY is None:
        path = Path(__file__).resolve().with_name("requirement_discovery.py")
        spec = importlib.util.spec_from_file_location("tailtrail_intake_requirement_discovery", path)
        if spec is None or spec.loader is None:
            raise IntakeError("TailTrail requirement-kind validator is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _REQUIREMENT_DISCOVERY = module
    return _REQUIREMENT_DISCOVERY


def _command_runs_path(command: str, path: str) -> bool:
    """Return True only when the command names the bound proof path or its module."""
    module = path.removesuffix(".py").replace("/", ".")
    module_pattern = rf"(?<![\w.]){re.escape(module)}(?![\w.])"
    return path in command or re.search(module_pattern, command) is not None
_MAX_PERSISTED_EVENT_BYTES = 64 * 1024
_STATE_SCHEMA_VERSION = "1"
_RETENTION_POLICY = {
    "schema_version": "1",
    "type": "tailtrail-intake-retention-policy",
    "raw_input": "never-persisted-after-redaction",
    "state_records": "retained-with-the-intake-run-until-explicit-deletion",
    "access": "local-run-bound",
    "deletion": "delete_run removes the complete intake run and derived projections",
}


def _redact(value: Any, key: str | None = None) -> Any:
    if key and _SENSITIVE_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(name): _redact(item, str(name)) for name, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return _SENSITIVE_VALUE.sub("[REDACTED]", value)
    return value


def _serialized_size(value: Any) -> int:
    try:
        return len(_canonical(value).encode("utf-8"))
    except (TypeError, ValueError) as error:
        raise IntakeError("intake input must be JSON-serializable") from error


def _contains_redaction(value: Any) -> bool:
    if value == "[REDACTED]":
        return True
    if isinstance(value, dict):
        return any(_contains_redaction(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_redaction(item) for item in value)
    return False


class IntakePipeline:
    """Persist the Phase 1A contract and correlate interaction events."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.runs_root = self.root / ".tailtrail" / "intake"

    def create_run(self, goal: str, profile: str) -> dict[str, str]:
        if not goal.strip() or not profile.strip():
            raise IntakeError("goal and profile are required")
        run_id = _new_id("run")
        contract_id = _new_id("contract")
        packet_version = 1
        contract = {
            "schema_version": "1",
            "type": "tailtrail-intake-contract",
            "run_id": run_id,
            "contract_id": contract_id,
            "profile": profile,
            "goal": goal,
            "packet_version": packet_version,
            "status": "intake",
        }
        contract["fingerprint"] = _content_fingerprint(contract)
        run_root = self.runs_root / run_id
        _write_json(run_root / "contract.json", contract)
        return {
            "run_id": run_id,
            "contract_id": str(contract["contract_id"]),
            "packet_version": "1",
            "fingerprint": str(contract["fingerprint"]),
        }

    def load_contract(self, run_id: str) -> dict[str, Any]:
        path = self.runs_root / run_id / "contract.json"
        if not path.is_file():
            raise IntakeError(f"unknown intake run: {run_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _run_root(self, run_id: str) -> Path:
        return self.runs_root / str(run_id)

    def _integrity_path(self, run_id: str) -> Path:
        return self._run_root(run_id) / "event-integrity.jsonl"

    def _projection_path(self, run_id: str) -> Path:
        return self._run_root(run_id) / "projection.json"

    def _answer_state_path(self, run_id: str) -> Path:
        """Keep a versioned, derived state projection beside the event stream."""
        return self._run_root(run_id) / "answer-state-v1.json"

    def _packet_view_path(self, run_id: str, anchor_version: str) -> Path:
        """Return the immutable view location for one authoritative anchor."""
        return self._run_root(run_id) / "packet-views" / f"{anchor_version}.json"

    def _packet_finalization_receipt_path(self, run_id: str, anchor_version: str) -> Path:
        """Keep private source-evidence separate from the public packet-view schema."""
        return self._run_root(run_id) / "packet-views" / f"{anchor_version}.receipt.json"

    def _packet_invalidation_path(self, run_id: str, anchor_version: str) -> Path:
        """Keep invalidation evidence beside, but never inside, immutable views."""
        return self._run_root(run_id) / "packet-views" / f"{anchor_version}.invalidation.json"

    def _planning_readiness_root(self, run_id: str) -> Path:
        return self._run_root(run_id) / "planning-readiness"

    def _planning_readiness_path(self, run_id: str, receipt_id: str) -> Path:
        return self._planning_readiness_root(run_id) / f"{receipt_id}.json"

    @staticmethod
    def _profile_registry_fields(profile: str) -> tuple[list[str], str]:
        """Load the canonical Navigator registry without duplicating its policy."""
        path = Path(__file__).with_name("question-orchestrator.py")
        spec = importlib.util.spec_from_file_location("tailtrail_readiness_profile_registry", path)
        if spec is None or spec.loader is None:
            raise IntakeError("TailTrail profile registry is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        try:
            rows = module.NavigatorHostProtocol.profile_fields(profile)
        except ValueError as error:
            raise IntakeError(str(error)) from error
        fields = [str(row["field_id"]) for row in rows]
        return fields, _content_fingerprint({"profile": profile, "fields": rows})

    def _state_path(self, run_id: str) -> Path:
        return self._run_root(run_id) / "lifecycle.json"

    def _lifecycle(self, run_id: str) -> dict[str, Any]:
        path = self._state_path(run_id)
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"run_id": run_id, "status": "active", "history": []}

    def _save_lifecycle(self, run_id: str, status: str, reason: str) -> dict[str, Any]:
        self.load_contract(run_id)
        lifecycle = self._lifecycle(run_id)
        lifecycle["status"] = status
        lifecycle.setdefault("history", []).append({"status": status, "reason": reason})
        _write_json(self._state_path(run_id), lifecycle)
        return lifecycle

    def pause_run(self, run_id: str, reason: str = "paused") -> dict[str, Any]:
        return self._save_lifecycle(run_id, "paused", reason)

    def expire_run(self, run_id: str, reason: str = "expired") -> dict[str, Any]:
        return self._save_lifecycle(run_id, "expired", reason)

    def abandon_run(self, run_id: str, reason: str = "abandoned") -> dict[str, Any]:
        return self._save_lifecycle(run_id, "abandoned", reason)

    def resume_run(self, run_id: str, reason: str = "explicit resume") -> dict[str, Any]:
        lifecycle = self._lifecycle(run_id)
        if lifecycle.get("status") not in {"paused", "expired", "abandoned"}:
            raise IntakeError(f"run {run_id} is not resumable from {lifecycle.get('status', 'unknown')}")
        return self._save_lifecycle(run_id, "active", reason)

    def assert_execution_allowed(self, run_id: str) -> None:
        status = self._lifecycle(run_id).get("status")
        if status in {"expired", "abandoned", "paused"}:
            raise IntakeError(f"run {run_id} is {status}; explicit resume is required before execution")

    def retention_policy(self) -> dict[str, Any]:
        """Return the explicit local retention and access boundary for intake data."""
        return dict(_RETENTION_POLICY)

    def delete_run(self, run_id: str) -> None:
        """Delete one complete local intake run, including derived state projections."""
        run_root = self._run_root(run_id).resolve()
        try:
            run_root.relative_to(self.runs_root.resolve())
        except ValueError as error:
            raise IntakeError("intake deletion target escapes the intake root") from error
        if not run_root.is_dir():
            raise IntakeError(f"unknown intake run: {run_id}")
        shutil.rmtree(run_root)

    @staticmethod
    def _answer_state_records(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Derive durable answer lifecycle records from the append-only stream.

        This is a projection, not a second authority: every state transition is
        traceable to one sanitized event in ``events.jsonl``.
        """
        questions = {
            str(event.get("payload", {}).get("question_id", "")): event.get("payload", {})
            for event in events if event.get("event_type") == "question-issued"
        }
        observations = {
            str(event.get("payload", {}).get("observation_id", "")): event.get("payload", {})
            for event in events if event.get("event_type") == "host-observation-recorded"
        }
        states: dict[str, dict[str, Any]] = {}
        for event in events:
            payload = event.get("payload", {})
            if not isinstance(payload, dict):
                continue
            event_type = event.get("event_type")
            if event_type == "answer-recorded":
                answer_id = str(payload.get("answer_id", ""))
                if not answer_id:
                    continue
                question_id = payload.get("question_id")
                observation_id = payload.get("observation_id")
                source_evidence = {
                    "source": payload.get("source"),
                    "question": questions.get(str(question_id or "")),
                    "observation": observations.get(str(observation_id or "")),
                }
                states[answer_id] = {
                    "schema_version": _STATE_SCHEMA_VERSION,
                    "type": "tailtrail-intake-answer-state",
                    "answer_id": answer_id,
                    "field_id": payload.get("field_id"),
                    "state": "candidate",
                    "source": payload.get("source"),
                    "question_id": question_id,
                    "observation_id": observation_id,
                    "source_evidence_fingerprint": _content_fingerprint(source_evidence),
                    "state_history": [{"state": "candidate", "event_id": event.get("event_id")}],
                    "authority_granted": False,
                    "finalization_allowed": False,
                }
                continue
            if event_type not in {"answer-accepted", "answer-rejected"}:
                continue
            answer_id = str(payload.get("answer_id", ""))
            record = states.get(answer_id)
            if record is None:
                continue
            state = "accepted" if event_type == "answer-accepted" else str(payload.get("state", "rejected"))
            if state not in _ANSWER_STATES:
                raise IntakeError(f"invalid persisted answer state `{state}`")
            record["state"] = state
            record["state_history"].append({"state": state, "event_id": event.get("event_id")})
            record["authority_granted"] = False
            record["finalization_allowed"] = False
            if state == "accepted":
                record["acceptance_evidence_fingerprint"] = str(payload.get("evidence_fingerprint", ""))
                evidence = payload.get("evidence")
                refs = evidence.get("evidence_refs", []) if isinstance(evidence, dict) else []
                record["evidence_refs"] = [dict(ref) for ref in refs if isinstance(ref, dict)]
            elif payload.get("reason"):
                record["reason"] = str(payload["reason"])
        return [states[key] for key in sorted(states)]

    def replay(self, run_id: str) -> dict[str, Any]:
        """Replay events into a deterministic, redacted packet projection."""
        contract = self.load_contract(run_id)
        events_path = self._run_root(run_id) / "events.jsonl"
        events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()] if events_path.is_file() else []
        integrity_path = self._integrity_path(run_id)
        integrity = [json.loads(line) for line in integrity_path.read_text(encoding="utf-8").splitlines() if line.strip()] if integrity_path.is_file() else []
        if integrity and len(integrity) != len(events):
            raise IntakeError("event integrity ledger does not match event stream length")

        previous = ""
        projection: dict[str, list[Any]] = {"questions": [], "observations": [], "answers": []}
        for index, event in enumerate(events, start=1):
            if event.get("sequence") != index or event.get("run_id") != run_id or event.get("contract_id") != contract["contract_id"]:
                raise IntakeError(f"event stream integrity failure at sequence {index}")
            event_fingerprint = _content_fingerprint(event)
            if integrity:
                record = integrity[index - 1]
                if record.get("event_fingerprint") != event_fingerprint or record.get("previous") != previous:
                    raise IntakeError(f"event integrity failure at sequence {index}")
            previous = event_fingerprint
            event_type = event.get("event_type")
            if event_type == "question-issued":
                projection["questions"].append(_redact(event["payload"]))
            elif event_type == "host-observation-recorded":
                projection["observations"].append(_redact(event["payload"]))
            elif event_type == "answer-recorded":
                projection["answers"].append(_redact(event["payload"]))

        answer_states = self._answer_state_records(events)
        _write_json(self._answer_state_path(run_id), {
            "schema_version": _STATE_SCHEMA_VERSION,
            "type": "tailtrail-intake-answer-state-projection",
            "run_id": run_id,
            "retention": self.retention_policy(),
            "answers": answer_states,
        })
        packet_view = _redact({
            "contract": {key: value for key, value in contract.items() if key != "fingerprint"},
            "events": projection,
        })
        result = {
            "run_id": run_id,
            "status": "valid",
            "contract": contract,
            "packet_view": packet_view,
            "contract_fingerprint": contract["fingerprint"],
            "packet_view_fingerprint": _content_fingerprint(packet_view),
            "event_count": len(events),
            "lifecycle": self._lifecycle(run_id),
            "answer_states": answer_states,
        }
        _write_json(self._projection_path(run_id), result)
        return result

    def finalize_packet_view(
        self,
        run_id: str,
        *,
        anchor_version: str,
        accepted_answers: list[dict[str, Any]],
        requirement_projections: list[dict[str, Any]],
        expected_packet_view_fingerprint: str,
        anchor_fingerprint: str | None = None,
        operational_bindings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Materialize one immutable Navigator packet view for an anchor.

        The caller selects only answers already accepted by Navigator through
        the append-only intake stream; it cannot supply acceptance assertions.
        The pipeline verifies answer lineage and the exact replay snapshot
        before minting an anchor-bound view.  This deliberately does not
        change ``contract.packet_version``: the anchor is the only versioned
        authority for a finalized packet.
        """
        if not _ANCHOR_VERSION.fullmatch(anchor_version):
            raise IntakeError("anchor_version must use the form anchor-vN")
        if not isinstance(expected_packet_view_fingerprint, str) or not re.fullmatch(
            r"sha256:[a-f0-9]{64}", expected_packet_view_fingerprint
        ):
            raise IntakeError("expected_packet_view_fingerprint must be a SHA-256 fingerprint")
        if not isinstance(accepted_answers, list) or not accepted_answers:
            raise IntakeError("packet finalization requires at least one Navigator-accepted answer")
        if not isinstance(requirement_projections, list) or not requirement_projections:
            raise IntakeError("packet finalization requires at least one requirement projection")

        replay = self.replay(run_id)
        if replay["packet_view_fingerprint"] != expected_packet_view_fingerprint:
            raise IntakeError("stale packet finalization input; replay intake and obtain a fresh fingerprint")

        events_path = self._run_root(run_id) / "events.jsonl"
        events = [
            json.loads(line)
            for line in events_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ] if events_path.is_file() else []
        answers = {
            str(event.get("payload", {}).get("answer_id")): event.get("payload", {})
            for event in events
            if event.get("event_type") == "answer-recorded"
            and str(event.get("payload", {}).get("answer_id", "")).strip()
        }
        question_ids = {
            str(event.get("payload", {}).get("question_id"))
            for event in events
            if event.get("event_type") == "question-issued"
        }
        observation_ids = {
            str(event.get("payload", {}).get("observation_id"))
            for event in events
            if event.get("event_type") == "host-observation-recorded"
        }
        accepted_by_navigator = {
            str(event.get("payload", {}).get("answer_id"))
            for event in events
            if event.get("event_type") == "answer-accepted"
            and event.get("payload", {}).get("evidence", {}).get("outcome") == "accepted"
            and event.get("payload", {}).get("evidence", {}).get("verified_by") == "navigator"
        }
        answer_states = {
            str(record.get("answer_id")): record
            for record in replay.get("answer_states", [])
            if isinstance(record, dict)
        }

        accepted_ids: list[str] = []
        accepted_records: list[dict[str, Any]] = []
        values_by_field: dict[str, str] = {}
        for index, accepted in enumerate(accepted_answers, start=1):
            if not isinstance(accepted, dict):
                raise IntakeError(f"accepted answer {index} must be an object")
            answer_id = str(accepted.get("answer_id", "")).strip()
            if not answer_id or answer_id in accepted_ids:
                raise IntakeError("accepted answers must contain unique recorded answer IDs")
            if answer_id not in accepted_by_navigator:
                raise IntakeError(f"accepted answer `{answer_id}` has no Navigator-validated acceptance event")
            if answer_states.get(answer_id, {}).get("state") != "accepted":
                raise IntakeError(f"accepted answer `{answer_id}` is stale, conflicting, or rejected")
            answer = answers.get(answer_id)
            if not isinstance(answer, dict):
                raise IntakeError(f"accepted answer `{answer_id}` is missing from the integrity-checked intake stream")
            field_id = str(answer.get("field_id", "")).strip()
            if not field_id or answer.get("value") in (None, ""):
                raise IntakeError(f"accepted answer `{answer_id}` has incomplete field or value")
            question_id = answer.get("question_id")
            observation_id = answer.get("observation_id")
            if question_id is not None and str(question_id) not in question_ids:
                raise IntakeError(f"accepted answer `{answer_id}` has an unknown question lineage")
            if observation_id is not None and str(observation_id) not in observation_ids:
                raise IntakeError(f"accepted answer `{answer_id}` has an unknown observation lineage")
            value_fingerprint = _canonical(answer["value"])
            previous = values_by_field.get(field_id)
            if previous is not None and previous != value_fingerprint:
                raise IntakeError(f"contradictory accepted answers for profile field `{field_id}`")
            values_by_field[field_id] = value_fingerprint
            accepted_ids.append(answer_id)
            accepted_records.append({
                "answer_id": answer_id,
                "field_id": field_id,
                "value": answer["value"],
                "question_id": question_id,
                "observation_id": observation_id,
                "source_evidence_fingerprint": answer_states[answer_id]["source_evidence_fingerprint"],
            })

        normalized_projections: list[dict[str, str]] = []
        seen_projections: set[tuple[str, str, str]] = set()
        for index, projection in enumerate(requirement_projections, start=1):
            if not isinstance(projection, dict):
                raise IntakeError(f"requirement projection {index} must be an object")
            requirement_uid = str(projection.get("requirement_uid", "")).strip()
            consumer_component_id = str(projection.get("consumer_component_id", "")).strip()
            projection_kind = str(projection.get("projection_kind", "")).strip()
            if not requirement_uid or not consumer_component_id or projection_kind not in _PACKET_VIEW_PROJECTION_KINDS:
                raise IntakeError(f"requirement projection {index} is incomplete or has an unsupported kind")
            key = (requirement_uid, consumer_component_id, projection_kind)
            if key in seen_projections:
                raise IntakeError("packet finalization requires unique requirement projections")
            seen_projections.add(key)
            normalized_projections.append({
                "requirement_uid": requirement_uid,
                "consumer_component_id": consumer_component_id,
                "projection_kind": projection_kind,
            })

        view_path = self._packet_view_path(run_id, anchor_version)
        if view_path.exists():
            raise IntakeError(
                f"packet view for `{anchor_version}` already exists; material changes require a new anchor version"
            )
        packet_view = {
            "schema_version": "1",
            "type": "tailtrail-host-question-flow-packet-view",
            "packet_view_id": _new_id("packet-view"),
            "run_id": run_id,
            "contract_id": replay["contract"]["contract_id"],
            "anchor_version": anchor_version,
            "status": "materialized",
            "requirement_projections": normalized_projections,
        }
        operational_packet: dict[str, Any] | None = None
        if anchor_fingerprint is not None or operational_bindings is not None:
            operational_packet = self._build_operational_packet(
                packet_view_id=packet_view["packet_view_id"],
                anchor_version=anchor_version,
                anchor_fingerprint=anchor_fingerprint,
                operational_bindings=operational_bindings,
                accepted_records=accepted_records,
                projected_requirement_ids={projection["requirement_uid"] for projection in normalized_projections},
            )
        if operational_packet is not None:
            packet_view["operational_packet"] = operational_packet
        source_answer_fingerprint = _content_fingerprint(accepted_records)
        readiness = _PLANNING_READINESS if operational_packet is not None else _INTAKE_RECORDED
        receipt = {
            "schema_version": "1",
            "type": "tailtrail-host-question-flow-packet-finalization-receipt",
            "packet_view_id": packet_view["packet_view_id"],
            "run_id": run_id,
            "contract_id": replay["contract"]["contract_id"],
            "anchor_version": anchor_version,
            "readiness": readiness,
            "authorizes_start": readiness == _PLANNING_READINESS,
            "accepted_answer_ids": accepted_ids,
            "source_answer_fingerprint": source_answer_fingerprint,
            "source_packet_view_fingerprint": replay["packet_view_fingerprint"],
            "packet_view_fingerprint": _content_fingerprint(packet_view),
        }
        if operational_packet is not None:
            receipt["target_fingerprint"] = _content_fingerprint({
                "root": self.root.as_posix(),
                "anchor_fingerprint": anchor_fingerprint,
                "packet_view_fingerprint": receipt["packet_view_fingerprint"],
            })
        _write_json(view_path, packet_view)
        _write_json(self._packet_finalization_receipt_path(run_id, anchor_version), receipt)
        invalidated = self._invalidate_prior_packet_views(run_id, anchor_version, packet_view["packet_view_id"])
        self._append_event(
            replay["contract"],
            "packet-finalized",
            {
                "packet_view_id": packet_view["packet_view_id"],
                "anchor_version": anchor_version,
                "source_answer_fingerprint": source_answer_fingerprint,
                "invalidated_packet_view_ids": invalidated,
            },
        )
        return {"status": "requirements-finalized", "packet_view": packet_view, "receipt": receipt}

    def mint_planning_readiness(
        self,
        run_id: str,
        *,
        accepted_answer_ids: list[str],
        requirement_projections: list[dict[str, Any]],
        operational_bindings: dict[str, Any],
        expected_packet_view_fingerprint: str,
        target_identity: dict[str, Any],
    ) -> dict[str, Any]:
        """Mint a pre-Start receipt without pretending an approved anchor exists."""
        replay = self.replay(run_id)
        contract = replay["contract"]
        if replay["packet_view_fingerprint"] != expected_packet_view_fingerprint:
            raise IntakeError("stale planning-readiness input; replay intake and obtain a fresh fingerprint")
        if not isinstance(target_identity, dict) or not str(target_identity.get("root", "")).strip():
            raise IntakeError("planning-readiness target must match the exact repository root")
        try:
            supplied_root = Path(str(target_identity["root"])).resolve()
        except (OSError, RuntimeError) as error:
            raise IntakeError("planning-readiness target must match the exact repository root") from error
        if supplied_root != self.root:
            raise IntakeError("planning-readiness target must match the exact repository root")
        target_identity = {**target_identity, "root": self.root.as_posix()}
        if not isinstance(accepted_answer_ids, list) or not accepted_answer_ids:
            raise IntakeError("planning readiness requires Navigator-accepted answers")

        required_fields, registry_fingerprint = self._profile_registry_fields(str(contract.get("profile", "")))
        answer_states = {
            str(row.get("answer_id")): row
            for row in replay.get("answer_states", [])
            if isinstance(row, dict)
        }
        events_path = self._run_root(run_id) / "events.jsonl"
        events = [
            json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ] if events_path.is_file() else []
        answers = {
            str(event.get("payload", {}).get("answer_id")): event.get("payload", {})
            for event in events if event.get("event_type") == "answer-recorded"
        }
        accepted_records: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for answer_id in accepted_answer_ids:
            if not isinstance(answer_id, str) or not answer_id or answer_id in seen_ids:
                raise IntakeError("planning readiness requires unique recorded answer IDs")
            seen_ids.add(answer_id)
            state = answer_states.get(answer_id, {})
            answer = answers.get(answer_id)
            if state.get("state") != "accepted" or not isinstance(answer, dict):
                raise IntakeError(f"answer `{answer_id}` is not a fresh Navigator-accepted answer")
            if any(
                self._current_file_fingerprint(str(ref.get("path", ""))) != ref.get("content_fingerprint")
                for ref in state.get("evidence_refs", []) if isinstance(ref, dict)
            ):
                raise IntakeError(f"answer `{answer_id}` has stale source evidence")
            accepted_records.append({
                "answer_id": answer_id,
                "field_id": str(answer.get("field_id", "")),
                "value": answer.get("value"),
                "question_id": answer.get("question_id"),
                "observation_id": answer.get("observation_id"),
                "source_evidence_fingerprint": state.get("source_evidence_fingerprint"),
            })
        accepted_fields = {row["field_id"] for row in accepted_records}
        missing_fields = [field for field in required_fields if field not in accepted_fields]
        if missing_fields:
            raise IntakeError(
                "planning readiness is missing mandatory profile fields: " + ", ".join(missing_fields)
            )

        if not isinstance(requirement_projections, list) or not requirement_projections:
            raise IntakeError("planning readiness requires requirement projections")
        projected_ids = {
            str(row.get("requirement_uid", "")).strip()
            for row in requirement_projections if isinstance(row, dict)
        }
        if "" in projected_ids or len(projected_ids) != len(requirement_projections):
            raise IntakeError("planning readiness requires unique requirement projections")
        requirements = operational_bindings.get("requirements") if isinstance(operational_bindings, dict) else None
        if not isinstance(requirements, list) or not requirements:
            raise IntakeError("planning readiness requires operational requirement bindings")
        for requirement in requirements:
            if not isinstance(requirement, dict):
                raise IntakeError("planning readiness requirement bindings must be objects")
            if requirement.get("semantic_delta") not in {"validated", "not-applicable"}:
                raise IntakeError("planning readiness requires a validated semantic delta for every requirement")
            if requirement.get("dependencies_checked") is not True:
                raise IntakeError("planning readiness requires dependency checks for every requirement")

        request_binding = {
            "run_id": run_id,
            "contract_fingerprint": replay["contract_fingerprint"],
            "packet_view_fingerprint": replay["packet_view_fingerprint"],
            "accepted_answer_ids": sorted(accepted_answer_ids),
            "requirement_projections": requirement_projections,
            "operational_bindings": operational_bindings,
            "target_identity": target_identity,
            "profile_registry_fingerprint": registry_fingerprint,
        }
        request_fingerprint = _content_fingerprint(request_binding)
        readiness_root = self._planning_readiness_root(run_id)
        for path in sorted(readiness_root.glob("readiness-*.json")) if readiness_root.is_dir() else []:
            saved = json.loads(path.read_text(encoding="utf-8"))
            if saved.get("request_fingerprint") == request_fingerprint:
                return saved

        receipt_id = _new_id("readiness")
        target_fingerprint = _content_fingerprint({
            "goal": contract.get("goal"),
            "profile": contract.get("profile"),
            "target_identity": target_identity,
        })
        operational_packet = self._build_operational_packet(
            packet_view_id=receipt_id,
            anchor_version=None,
            anchor_fingerprint=None,
            target_fingerprint=target_fingerprint,
            operational_bindings=operational_bindings,
            accepted_records=accepted_records,
            projected_requirement_ids=projected_ids,
        )
        tracked_paths = sorted({
            str(binding.get("path"))
            for requirement in operational_packet["requirements"]
            for key in ("path_bindings", "proof_bindings")
            for binding in requirement.get(key, [])
            if isinstance(binding, dict) and str(binding.get("path", "")).strip()
        })
        repository_state = [
            {"path": path, "content_fingerprint": self._current_file_fingerprint(path)}
            for path in tracked_paths
        ]
        prior = sorted(readiness_root.glob("readiness-*.json")) if readiness_root.is_dir() else []
        receipt: dict[str, Any] = {
            "schema_version": "1",
            "type": "tailtrail-planning-readiness-receipt",
            "receipt_id": receipt_id,
            "receipt_version": len(prior) + 1,
            "previous_receipt_id": json.loads(prior[-1].read_text(encoding="utf-8")).get("receipt_id") if prior else None,
            "readiness": _PLANNING_READINESS,
            "authorizes_start": True,
            "run_id": run_id,
            "contract_id": contract.get("contract_id"),
            "goal": contract.get("goal"),
            "profile": contract.get("profile"),
            "required_profile_fields": required_fields,
            "profile_registry_fingerprint": registry_fingerprint,
            "accepted_answer_ids": sorted(accepted_answer_ids),
            "source_packet_view_fingerprint": replay["packet_view_fingerprint"],
            "requirement_projections": requirement_projections,
            "operational_packet": operational_packet,
            "target_identity": target_identity,
            "target_fingerprint": target_fingerprint,
            "repository_state": repository_state,
            "request_fingerprint": request_fingerprint,
        }
        receipt["fingerprint"] = _content_fingerprint(receipt)
        _write_json(self._planning_readiness_path(run_id, receipt_id), receipt)
        self._append_event(contract, "planning-readiness-minted", {
            "receipt_id": receipt_id,
            "receipt_version": receipt["receipt_version"],
            "request_fingerprint": request_fingerprint,
        })
        return receipt

    def validate_planning_readiness_receipt(
        self,
        receipt: dict[str, Any],
        *,
        goal: str,
        host_contract_fingerprint: str | None = None,
    ) -> dict[str, Any]:
        """Validate saved authority, freshness, target, and optional host contract binding."""
        if not isinstance(receipt, dict) or receipt.get("type") != "tailtrail-planning-readiness-receipt":
            raise IntakeError("Start requires a TailTrail planning-readiness receipt")
        run_id = str(receipt.get("run_id", ""))
        receipt_id = str(receipt.get("receipt_id", ""))
        path = self._planning_readiness_path(run_id, receipt_id)
        if not run_id or not receipt_id or not path.is_file():
            raise IntakeError("planning-readiness receipt is unknown or was replayed outside its intake run")
        saved = json.loads(path.read_text(encoding="utf-8"))
        if _canonical(saved) != _canonical(receipt):
            raise IntakeError("planning-readiness receipt does not match its immutable saved record")
        fingerprint = saved.get("fingerprint")
        unsigned = {key: value for key, value in saved.items() if key != "fingerprint"}
        if fingerprint != _content_fingerprint(unsigned):
            raise IntakeError("planning-readiness receipt integrity check failed")
        if saved.get("authorizes_start") is not True or saved.get("readiness") != _PLANNING_READINESS:
            raise IntakeError("intake-recorded state does not authorize Start")
        if saved.get("goal") != goal or saved.get("target_identity", {}).get("root") != self.root.as_posix():
            raise IntakeError("planning-readiness receipt does not match the current goal and target")
        expected_contract = saved.get("target_identity", {}).get("host_contract_fingerprint")
        if host_contract_fingerprint is not None and expected_contract != host_contract_fingerprint:
            raise IntakeError("planning-readiness receipt does not match the supplied host contract")
        replay = self.replay(run_id)
        if replay["packet_view_fingerprint"] != saved.get("source_packet_view_fingerprint"):
            raise IntakeError("planning-readiness receipt is stale after intake answers changed")
        states = {str(row.get("answer_id")): row for row in replay.get("answer_states", []) if isinstance(row, dict)}
        for answer_id in saved.get("accepted_answer_ids", []):
            state = states.get(str(answer_id), {})
            if state.get("state") != "accepted":
                raise IntakeError("planning-readiness receipt contains a stale or rejected answer")
            for ref in state.get("evidence_refs", []):
                if self._current_file_fingerprint(str(ref.get("path", ""))) != ref.get("content_fingerprint"):
                    raise IntakeError("planning-readiness receipt source evidence is stale")
        for row in saved.get("repository_state", []):
            if self._current_file_fingerprint(str(row.get("path", ""))) != row.get("content_fingerprint"):
                raise IntakeError("planning-readiness receipt is stale because the target changed")
        return saved

    def load_planning_readiness_receipt(self, run_id: str, receipt_id: str) -> dict[str, Any]:
        """Load one immutable readiness receipt by its saved identity."""
        path = self._planning_readiness_path(run_id, receipt_id)
        if not run_id or not receipt_id or not path.is_file():
            raise IntakeError("planning-readiness receipt is unknown or was replayed outside its intake run")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise IntakeError("planning-readiness receipt has an invalid saved record")
        return value

    def reconcile_planning_readiness_receipt(
        self,
        receipt: dict[str, Any],
        report: dict[str, Any],
        *,
        goal: str,
        host_contract_fingerprint: str | None = None,
        project: bool,
        phase: str,
    ) -> dict[str, Any]:
        """Project and verify readiness facts against one canonical Start report.

        The receipt is already Navigator-validated authority.  Projection may
        copy only its redacted operational packet into the canonical plan;
        validation-only calls never repair a missing fact.  This lets Start
        build a complete v1 while approval and activation fail closed if that
        saved proposal later loses or crosses requirement-specific evidence.
        """
        saved = self.validate_planning_readiness_receipt(
            receipt,
            goal=goal,
            host_contract_fingerprint=host_contract_fingerprint,
        )
        if not isinstance(report, dict):
            raise IntakeError("planning-readiness reconciliation requires a canonical Start report")
        reconciled = copy.deepcopy(report)
        navigator = reconciled.get("navigator")
        if not isinstance(navigator, dict):
            raise IntakeError("planning-readiness reconciliation requires canonical Navigator state")
        rows = navigator.get("requirement_matrix")
        if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
            raise IntakeError("planning-readiness reconciliation requires a canonical requirement matrix")

        operational = saved.get("operational_packet")
        requirements = operational.get("requirements") if isinstance(operational, dict) else None
        if not isinstance(requirements, list) or not requirements:
            raise IntakeError("planning-readiness receipt has no operational requirement projection")
        projected_ids = {
            str(item.get("requirement_uid", ""))
            for item in saved.get("requirement_projections", [])
            if isinstance(item, dict)
        }
        operational_ids = {
            str(item.get("requirement_uid", ""))
            for item in requirements if isinstance(item, dict)
        }
        if "" in projected_ids or projected_ids != operational_ids:
            raise IntakeError("planning-readiness requirement projections do not match operational bindings")

        by_id: dict[str, dict[str, Any]] = {}
        for row in rows:
            identifiers = {
                str(row.get("display_id", "")),
                str(row.get("requirement_uid", "")),
                str(row.get("requirement_id", "")),
            } - {""}
            for identifier in identifiers:
                if identifier in by_id and by_id[identifier] is not row:
                    raise IntakeError(f"canonical requirement identity `{identifier}` is ambiguous")
                by_id[identifier] = row

        matched: list[dict[str, Any]] = []
        reconciled_rows: list[dict[str, Any]] = []
        claimed_rows: set[int] = set()
        for binding in requirements:
            requirement_uid = str(binding.get("requirement_uid", ""))
            statement = " ".join(str(binding.get("statement", "")).split())
            supplied_kind = binding.get("requirement_kind")
            kind_authority = str(
                binding.get("requirement_kind_source")
                or ("legacy-contextual-classifier" if supplied_kind is None else "validated-operational-binding")
            )
            legacy_kind_authority = (
                supplied_kind is None or kind_authority == "legacy-contextual-classifier"
            )
            try:
                requirement_kind = (
                    _requirement_discovery()._kind(statement)
                    if supplied_kind is None
                    else _requirement_discovery().validate_requirement_kind(statement, str(supplied_kind))
                )
            except ValueError as error:
                raise IntakeError(f"planning-readiness requirement `{requirement_uid}` {error}") from error
            row = by_id.get(requirement_uid)
            if row is None:
                statement_matches = [
                    candidate for candidate in rows
                    if id(candidate) not in claimed_rows
                    and statement == " ".join(str(candidate.get("statement", "")).split())
                ]
                if len(statement_matches) == 1:
                    row = statement_matches[0]
                elif project and len(requirements) == 1:
                    expected_owners_for_match = {
                        str(item.get("path")) for item in binding.get("path_bindings", [])
                        if isinstance(item, dict) and item.get("role") == "implementation-owner"
                    }
                    owner_matches = [
                        candidate for candidate in rows
                        if id(candidate) not in claimed_rows
                        and expected_owners_for_match.issubset({
                            str(path) for path in (
                                candidate.get("scope_evidence", {}).get("implementation_owners", [])
                                if isinstance(candidate.get("scope_evidence"), dict) else []
                            )
                        })
                    ]
                    # The receipt is the validated requirement authority. A
                    # single accepted requirement therefore replaces any
                    # heuristic clause expansion, while reusing the best
                    # canonical row as a presentation template.
                    row = owner_matches[0] if owner_matches else rows[0]
                elif len(requirements) == len(rows):
                    row = next(
                        (candidate for candidate in rows if id(candidate) not in claimed_rows),
                        None,
                    )
                else:
                    raise IntakeError(
                        f"planning-readiness requirement `{requirement_uid}` cannot be mapped uniquely "
                        "to a canonical requirement; return to Navigator clarification"
                    )
            if row is None:
                raise IntakeError(
                    f"planning-readiness requirement `{requirement_uid}` has no remaining canonical requirement"
                )
            if id(row) in claimed_rows:
                raise IntakeError(
                    f"planning-readiness requirement `{requirement_uid}` crosses an already-bound canonical requirement"
                )
            claimed_rows.add(id(row))
            canonical_statement = " ".join(str(row.get("statement", "")).split())
            if statement != canonical_statement and not project:
                raise IntakeError(
                    f"planning-readiness requirement `{requirement_uid}` does not match the canonical statement"
                )
            if project:
                row["requirement_uid"] = requirement_uid
                row["statement"] = statement
                row["kind"] = requirement_kind
                row["requirement_kind_authority"] = kind_authority
                row["requirement_kind_source_answer_ids"] = list(
                    binding.get("requirement_kind_source_answer_ids", [])
                )
            else:
                canonical_kind = str(row.get("kind", "")).strip()
                if not canonical_kind and legacy_kind_authority:
                    # Compatibility for pre-kind receipts and their saved
                    # canonical projections.  New explicit-kind receipts must
                    # always match a materialized canonical value.
                    row["kind"] = requirement_kind
                    row["requirement_kind_authority"] = kind_authority
                elif canonical_kind != requirement_kind:
                    raise IntakeError(
                        f"planning-readiness requirement `{requirement_uid}` kind does not match the canonical requirement"
                    )

            path_bindings = binding.get("path_bindings", [])
            proof_bindings = binding.get("proof_bindings", [])
            if not isinstance(path_bindings, list) or not isinstance(proof_bindings, list):
                raise IntakeError(f"planning-readiness requirement `{requirement_uid}` has invalid bindings")
            expected_owners = sorted({
                str(item.get("path")) for item in path_bindings
                if isinstance(item, dict) and item.get("role") == "implementation-owner"
            })
            expected_proof_paths = sorted({
                str(item.get("path")) for item in proof_bindings if isinstance(item, dict)
            })
            expected_outputs = [
                copy.deepcopy(item) for item in path_bindings
                if isinstance(item, dict) and item.get("role") in _OUTPUT_PATH_ROLES
            ]
            scope = row.get("scope_evidence")
            if not isinstance(scope, dict):
                raise IntakeError(f"canonical requirement `{requirement_uid}` has no scope evidence")
            actual_owners = {str(path) for path in scope.get("implementation_owners", []) if str(path)}
            absent_owners = sorted(set(expected_owners) - actual_owners)
            if absent_owners:
                raise IntakeError(
                    f"planning-readiness requirement `{requirement_uid}` is missing implementation-owner scope: "
                    + ", ".join(absent_owners)
                )
            criteria = binding.get("criteria") if isinstance(binding.get("criteria"), dict) else {}
            positives = [str(value) for value in criteria.get("positive", []) if str(value)]
            negatives = [str(value) for value in criteria.get("negative", []) if str(value)]
            # Phase 3 validated these fields before building the immutable
            # operational packet, but older receipts did not persist them.
            # Preserve new values and treat their absence in a saved legacy
            # receipt as the validation result already enforced at mint time.
            semantic_delta = binding.get("semantic_delta", "validated")
            dependencies_checked = binding.get("dependencies_checked", True) is True
            if project:
                row["acceptance_criteria"] = list(dict.fromkeys([
                    *[str(value) for value in row.get("acceptance_criteria", []) if str(value)],
                    *positives,
                ]))
                row["preserve_rules"] = list(dict.fromkeys([
                    *[str(value) for value in row.get("preserve_rules", []) if str(value)],
                    *negatives,
                ]))
                row["semantic_delta"] = semantic_delta
                row["dependencies_checked"] = dependencies_checked
                row["planning_readiness_source_answer_ids"] = list(binding.get("source_answer_ids", []))
                scope["proof_paths"] = expected_proof_paths
                scope["unbound_proof_paths"] = []
                row["writable_outputs"] = expected_outputs
                scope["writable_outputs"] = copy.deepcopy(expected_outputs)
                checks = []
                for proof in proof_bindings:
                    check = {
                        "command": str(proof.get("command", "")),
                        "candidate_paths": [str(proof.get("path", ""))],
                        "tiers": [str(proof.get("tier", ""))],
                        "asserted_behavior": str(proof.get("asserted_behavior", "")),
                        "source_answer_id": str(proof.get("source_answer_id", "")),
                        "evidence_fingerprint": str(proof.get("evidence_fingerprint", "")),
                    }
                    if isinstance(proof.get("proof_adequacy"), dict):
                        check["proof_adequacy"] = copy.deepcopy(proof["proof_adequacy"])
                    checks.append(check)
                editable_proof_paths = sorted({
                    str(proof.get("path", ""))
                    for proof in proof_bindings
                    if isinstance(proof.get("proof_adequacy"), dict)
                    and proof["proof_adequacy"].get("role") in {"editable-proof", "new-proof"}
                })
                proof_adequacy_required = any(
                    isinstance(proof.get("proof_adequacy"), dict) for proof in proof_bindings
                )
                if not proof_adequacy_required:
                    # Legacy receipts predate proof-adequacy classification.
                    # Preserve their conservative, broadly editable proof
                    # scope instead of silently assuming those tests are
                    # unchanged. Public Navigator intake always supplies the
                    # precise role and therefore takes the narrow branch.
                    editable_proof_paths = expected_proof_paths
                validation = row.get("validation_contract")
                validation = validation if isinstance(validation, dict) else {}
                validation.update({
                    "state": "required",
                    "checks": checks,
                    "commands": list(dict.fromkeys(check["command"] for check in checks)),
                    "tiers": sorted({tier for check in checks for tier in check["tiers"]}),
                    "candidate_paths": expected_proof_paths,
                    "editable_paths": editable_proof_paths,
                    "proposed_paths": [],
                    "proof_adequacy_required": proof_adequacy_required,
                })
                row["validation_contract"] = validation
                row["evidence_plan"] = list(dict.fromkeys([
                    *[str(value) for value in row.get("evidence_plan", []) if str(value)],
                    *[str(proof.get("asserted_behavior", "")) for proof in proof_bindings],
                ]))

            acceptance = {str(value) for value in row.get("acceptance_criteria", [])}
            preservation = {str(value) for value in row.get("preserve_rules", [])}
            if not set(positives).issubset(acceptance) or not set(negatives).issubset(preservation):
                raise IntakeError(
                    f"planning-readiness requirement `{requirement_uid}` is missing accepted success or preservation criteria"
                )
            if row.get("semantic_delta") != semantic_delta or row.get("dependencies_checked") is not True:
                raise IntakeError(
                    f"planning-readiness requirement `{requirement_uid}` is missing semantic-delta or dependency reconciliation"
                )
            validation = row.get("validation_contract")
            checks = validation.get("checks", []) if isinstance(validation, dict) else []
            actual_outputs = {
                (str(item.get("path", "")), str(item.get("role", "")))
                for item in row.get("writable_outputs", [])
                if isinstance(item, dict)
            }
            required_outputs = {
                (str(item.get("path", "")), str(item.get("role", "")))
                for item in expected_outputs
            }
            if actual_outputs != required_outputs:
                raise IntakeError(
                    f"planning-readiness requirement `{requirement_uid}` has lost or reclassified writable outputs"
                )

            def exact_check_matches(check: dict[str, Any], proof: dict[str, Any]) -> bool:
                candidates = check.get("exact_bindings")
                values = candidates if isinstance(candidates, list) else [check]
                for candidate in values:
                    if not isinstance(candidate, dict):
                        continue
                    if (
                        str(candidate.get("command", "")) == str(proof.get("command", ""))
                        and str(proof.get("path", "")) in [
                            str(path) for path in candidate.get("candidate_paths", [])
                        ]
                        and str(proof.get("tier", "")) in [
                            str(value) for value in candidate.get("tiers", [])
                        ]
                        and str(candidate.get("asserted_behavior", ""))
                        == str(proof.get("asserted_behavior", ""))
                        and str(candidate.get("source_answer_id", ""))
                        == str(proof.get("source_answer_id", ""))
                        and str(candidate.get("evidence_fingerprint", ""))
                        == str(proof.get("evidence_fingerprint", ""))
                        and candidate.get("proof_adequacy") == proof.get("proof_adequacy")
                    ):
                        return True
                return False

            for proof in proof_bindings:
                if not any(
                    isinstance(check, dict)
                    and exact_check_matches(check, proof)
                    for check in checks
                ):
                    raise IntakeError(
                        f"planning-readiness requirement `{requirement_uid}` is missing its exact proof binding"
                    )
            matched.append({
                "requirement_uid": requirement_uid,
                "implementation_owners": expected_owners,
                "writable_outputs": expected_outputs,
                "proof_paths": expected_proof_paths,
                "proof_count": len(proof_bindings),
                "source_answer_ids": list(binding.get("source_answer_ids", [])),
            })
            reconciled_rows.append(row)

        audit = operational.get("projection_audit", {}) if isinstance(operational, dict) else {}
        if any(audit.get(key) for key in ("unused", "contradicted", "projected_without_source")):
            raise IntakeError("planning-readiness receipt contains unreconciled or contradictory accepted facts")
        reconciliation = {
            "schema_version": "1",
            "type": "tailtrail-planning-readiness-reconciliation",
            "status": "clean",
            "phase": phase,
            "receipt_id": saved.get("receipt_id"),
            "receipt_fingerprint": saved.get("fingerprint"),
            "target_fingerprint": saved.get("target_fingerprint"),
            "requirements": matched,
            "accepted_answer_ids": list(saved.get("accepted_answer_ids", [])),
            "surfaces": [
                "requirements", "preservation", "scope", "dependencies",
                "writable-outputs", "proof-registry", "normal-presentation", "verbose-presentation",
            ],
        }
        reconciliation["fingerprint"] = _content_fingerprint(reconciliation)
        if project:
            navigator["requirement_matrix"] = reconciled_rows
        planning = reconciled.get("planning_readiness")
        planning = planning if isinstance(planning, dict) else {}
        planning.update({
            "receipt_id": saved.get("receipt_id"),
            "fingerprint": saved.get("fingerprint"),
            "run_id": saved.get("run_id"),
            "target_fingerprint": saved.get("target_fingerprint"),
            "authority_source": "planning-readiness-receipt",
            "reconciliation": reconciliation,
        })
        reconciled["planning_readiness"] = planning
        return reconciled

    def _build_operational_packet(
        self,
        *,
        packet_view_id: str,
        anchor_version: str | None,
        anchor_fingerprint: str | None,
        operational_bindings: dict[str, Any] | None,
        accepted_records: list[dict[str, Any]],
        projected_requirement_ids: set[str],
        target_fingerprint: str | None = None,
    ) -> dict[str, Any]:
        """Build the Phase 3 redacted operational projection from accepted IDs only.

        The input remains deliberately narrow: it can cite accepted answer IDs,
        but it cannot import raw host answers or invent an acceptance decision.
        Every derived item carries its source IDs so downstream consumers only
        receive an immutable, auditable projection.
        """
        anchor_bound = isinstance(anchor_fingerprint, str) and re.fullmatch(
            r"sha256:[a-f0-9]{64}", anchor_fingerprint
        ) is not None
        readiness_bound = isinstance(target_fingerprint, str) and re.fullmatch(
            r"sha256:[a-f0-9]{64}", target_fingerprint
        ) is not None
        if anchor_bound == readiness_bound:
            raise IntakeError(
                "operational packet requires exactly one approved-anchor or pre-Start target binding"
            )
        if anchor_bound and (not isinstance(anchor_version, str) or not _ANCHOR_VERSION.fullmatch(anchor_version)):
            raise IntakeError("operational packet finalization requires an anchor version")
        if not isinstance(operational_bindings, dict):
            raise IntakeError("operational packet finalization requires binding objects")
        requirements = operational_bindings.get("requirements")
        if not isinstance(requirements, list) or not requirements:
            raise IntakeError("operational packet finalization requires at least one requirement binding")

        accepted_by_id = {record["answer_id"]: record for record in accepted_records}
        consumed_ids: set[str] = set()
        path_roles: dict[str, str] = {}
        requirement_ids: set[str] = set()
        normalized_requirements: list[dict[str, Any]] = []
        path_authorizations: list[dict[str, Any]] = []
        normalized_declared_paths: list[dict[str, Any]] = []

        def source_ids(value: Any, label: str) -> list[str]:
            if not isinstance(value, list) or not value or any(not isinstance(item, str) or item not in accepted_by_id for item in value):
                raise IntakeError(f"{label} must cite one or more Navigator-accepted answer IDs")
            normalized = sorted(set(value))
            consumed_ids.update(normalized)
            return normalized

        for index, requirement in enumerate(requirements, start=1):
            if not isinstance(requirement, dict):
                raise IntakeError(f"requirement binding {index} must be an object")
            requirement_uid = str(requirement.get("requirement_uid", "")).strip()
            statement = str(requirement.get("statement", "")).strip()
            if not requirement_uid or not statement or requirement_uid in requirement_ids:
                raise IntakeError("requirement bindings need unique requirement_uids and statements")
            supplied_kind = requirement.get("requirement_kind")
            kind_source = "validated-operational-binding"
            if supplied_kind is None:
                # Compatibility for receipts minted before requirement-kind
                # authority existed.  New public intake always materializes
                # the explicit field before calling this boundary.
                requirement_kind = _requirement_discovery()._kind(statement)
                kind_source = "legacy-contextual-classifier"
            else:
                try:
                    requirement_kind = _requirement_discovery().validate_requirement_kind(
                        statement, str(supplied_kind)
                    )
                except ValueError as error:
                    raise IntakeError(f"requirement `{requirement_uid}` {error}") from error
            requirement_ids.add(requirement_uid)
            requirement_sources = source_ids(requirement.get("source_answer_ids"), f"requirement `{requirement_uid}`")
            if supplied_kind is None:
                requirement_kind_sources = list(requirement_sources)
            else:
                requirement_kind_sources = source_ids(
                    requirement.get("requirement_kind_source_answer_ids"),
                    f"requirement kind for `{requirement_uid}`",
                )
                if not set(requirement_kind_sources).issubset(requirement_sources):
                    raise IntakeError(
                        f"requirement kind for `{requirement_uid}` must cite answers already bound to that requirement"
                    )
            profile_fields = requirement.get("profile_fields")
            if not isinstance(profile_fields, list) or not profile_fields or any(not isinstance(field, str) or not field for field in profile_fields):
                raise IntakeError(f"requirement `{requirement_uid}` needs profile_fields")
            accepted_fields = {accepted_by_id[answer_id]["field_id"] for answer_id in requirement_sources}
            if not set(profile_fields).issubset(accepted_fields):
                raise IntakeError(f"requirement `{requirement_uid}` profile_fields must be evidenced by its source answers")

            normalized_paths: list[dict[str, Any]] = []
            path_bindings = requirement.get("path_bindings")
            if not isinstance(path_bindings, list) or not path_bindings:
                raise IntakeError(f"requirement `{requirement_uid}` needs path bindings")
            for path_index, binding in enumerate(path_bindings, start=1):
                if not isinstance(binding, dict):
                    raise IntakeError(f"path binding {path_index} for `{requirement_uid}` must be an object")
                path = str(binding.get("path", "")).strip()
                role = str(binding.get("role", "")).strip()
                if not path or role not in _PATH_ROLES:
                    raise IntakeError(f"path binding {path_index} for `{requirement_uid}` has an unsupported path role")
                existing = binding.get("existing")
                if not isinstance(existing, bool):
                    raise IntakeError(f"path binding `{path}` must declare whether it already exists")
                if existing and not (self.root / path).exists():
                    raise IntakeError(f"existing path `{path}` requires filesystem existence evidence")
                if not existing and binding.get("host_declared") is not True:
                    raise IntakeError(f"proposed path `{path}` requires an explicit host declaration")
                binding_sources = source_ids(binding.get("source_answer_ids"), f"path binding `{path}`")
                previous_role = path_roles.get(path)
                if previous_role is not None and previous_role != role:
                    raise IntakeError(f"contradictory path roles for `{path}`")
                path_roles[path] = role
                verdict = str(binding.get("new_file_verdict", "not-applicable")).strip()
                if verdict not in _NEW_FILE_VERDICTS:
                    raise IntakeError(f"path binding `{path}` has an unsupported new-file verdict")
                if existing and verdict != "not-applicable":
                    raise IntakeError(f"existing path `{path}` must use new-file verdict `not-applicable`")
                if not existing and verdict == "not-applicable":
                    raise IntakeError(f"proposed path `{path}` requires a new-file verdict")
                if not existing and not str(binding.get("ownership_evidence", "")).strip():
                    raise IntakeError(f"proposed path `{path}` requires ownership or convention evidence")
                if not any(
                    accepted_by_id[answer_id]["value"] == path
                    for answer_id in binding_sources
                ):
                    raise IntakeError(
                        f"path binding `{path}` must cite an accepted answer whose value is that path"
                    )
                source_evidence = [
                    {
                        "answer_id": answer_id,
                        "fingerprint": accepted_by_id[answer_id]["source_evidence_fingerprint"],
                    }
                    for answer_id in binding_sources
                ]
                evidence_fingerprint = (
                    str(source_evidence[0]["fingerprint"])
                    if len(source_evidence) == 1
                    else _content_fingerprint(source_evidence)
                )
                supplied_evidence_fingerprint = binding.get("evidence_fingerprint")
                if (
                    supplied_evidence_fingerprint is not None
                    and str(supplied_evidence_fingerprint) != evidence_fingerprint
                ):
                    raise IntakeError(f"path binding `{path}` has stale or mismatched evidence fingerprint")
                role_class = _PATH_ROLE_CLASSES[role]
                is_output = role in _OUTPUT_PATH_ROLES
                grants_behavioral_ownership = role == "implementation-owner"
                requests_write_authority = role in _WRITABLE_PATH_ROLES
                due_diligence_allows_write = existing or verdict == "new-confirmed"
                normalized_binding = {
                    "schema_version": _PATH_BINDING_SCHEMA_VERSION,
                    "path_binding_id": _new_id("path-binding"), "path": path, "role": role,
                    "role_class": role_class,
                    "existing": existing,
                    "path_state": "existing-verified" if existing else f"proposed-new-{verdict}",
                    "new_file_verdict": verdict,
                    "new_file_due_diligence": {
                        "verdict": verdict,
                        "write_eligible": due_diligence_allows_write,
                    },
                    "ownership_evidence": str(binding.get("ownership_evidence", "")).strip() or None,
                    "source_answer_ids": binding_sources,
                    "source_evidence": source_evidence,
                    "evidence_fingerprint": evidence_fingerprint,
                    "grants_behavioral_ownership": grants_behavioral_ownership,
                    "requests_write_authority": requests_write_authority,
                }
                normalized_paths.append(normalized_binding)
                if not is_output:
                    authority_kind = "implementation" if grants_behavioral_ownership else "none"
                else:
                    authority_kind = "configuration-output" if role == "configuration-output" else "generated-output"
                if not requests_write_authority:
                    write_status = "not-requested"
                elif not due_diligence_allows_write:
                    write_status = "blocked-by-new-file-due-diligence"
                elif anchor_bound:
                    write_status = "approved-anchor-bound"
                else:
                    write_status = "pending-planning-approval"
                authorization = {
                    "schema_version": "1",
                    "type": "tailtrail-answer-to-path-authorization",
                    "requirement_uid": requirement_uid,
                    "path_binding_id": normalized_binding["path_binding_id"],
                    "path": path,
                    "role": role,
                    "role_class": role_class,
                    "path_state": normalized_binding["path_state"],
                    "authority_kind": authority_kind,
                    "grants_behavioral_ownership": grants_behavioral_ownership,
                    "write_authority": {
                        "requested": requests_write_authority,
                        "eligible": requests_write_authority and due_diligence_allows_write,
                        "status": write_status,
                    },
                    "accepted_answer_ids": binding_sources,
                    "source_evidence": source_evidence,
                    "evidence_fingerprint": evidence_fingerprint,
                    "packet_view_id": packet_view_id,
                }
                if anchor_bound:
                    authorization.update({
                        "authority_phase": "post-anchor",
                        "anchor_version": anchor_version,
                        "anchor_fingerprint": anchor_fingerprint,
                    })
                else:
                    authorization.update({
                        "authority_phase": _PLANNING_READINESS,
                        "target_fingerprint": target_fingerprint,
                    })
                authorization["path_binding_fingerprint"] = _content_fingerprint(authorization)
                path_authorizations.append(authorization)

            has_implementation_owner = any(
                binding.get("role") == "implementation-owner" for binding in normalized_paths
            )
            if has_implementation_owner and requirement_kind != "change":
                raise IntakeError(
                    f"requirement `{requirement_uid}` grants implementation-owner scope but has "
                    f"requirement_kind `{requirement_kind}`; writable behavior ownership requires `change`"
                )

            normalized_proofs: list[dict[str, Any]] = []
            proofs = requirement.get("proof_bindings")
            if not isinstance(proofs, list) or not proofs:
                raise IntakeError(f"requirement `{requirement_uid}` needs proof bindings")
            for proof_index, proof in enumerate(proofs, start=1):
                if not isinstance(proof, dict):
                    raise IntakeError(f"proof binding {proof_index} for `{requirement_uid}` must be an object")
                command = str(proof.get("command", "")).strip()
                path = str(proof.get("path", "")).strip()
                if not command or not path:
                    raise IntakeError(f"proof binding {proof_index} for `{requirement_uid}` is incomplete")
                if not _command_runs_path(command, path):
                    raise IntakeError(
                        f"proof command for `{path}` must run that path; unrelated passing suites cannot satisfy proof"
                    )
                tier = str(proof.get("tier", "")).strip()
                asserted_behavior = str(proof.get("asserted_behavior", "")).strip()
                source_answer_id = str(proof.get("source_answer_id", "")).strip()
                evidence_fingerprint = str(proof.get("evidence_fingerprint", "")).strip()
                if not tier or not asserted_behavior or not source_answer_id or not evidence_fingerprint:
                    raise IntakeError(
                        f"proof binding {proof_index} for `{requirement_uid}` needs tier, asserted behavior, "
                        "source answer ID, and evidence fingerprint"
                    )
                if source_answer_id not in accepted_by_id:
                    raise IntakeError(
                        f"proof binding {proof_index} for `{requirement_uid}` must cite a Navigator-accepted source answer ID"
                    )
                proof_sources = source_ids(
                    proof.get("source_answer_ids"), f"proof binding `{path}`"
                )
                if source_answer_id not in proof_sources:
                    raise IntakeError(
                        f"proof binding {proof_index} for `{requirement_uid}` source answer ID must be included in source_answer_ids"
                    )
                if evidence_fingerprint != accepted_by_id[source_answer_id]["source_evidence_fingerprint"]:
                    raise IntakeError(
                        f"proof binding {proof_index} for `{requirement_uid}` has stale or mismatched evidence fingerprint"
                    )
                adequacy = proof.get("proof_adequacy")
                normalized_adequacy = None
                if adequacy is not None:
                    if not isinstance(adequacy, dict):
                        raise IntakeError(f"proof binding `{path}` proof adequacy must be an object")
                    adequacy_source = str(adequacy.get("source_answer_id", "")).strip()
                    adequacy_fingerprint = str(adequacy.get("evidence_fingerprint", "")).strip()
                    role = str(adequacy.get("role", "")).strip()
                    baseline = adequacy.get("baseline")
                    if (
                        adequacy.get("schema_version") != "1"
                        or str(adequacy.get("path", "")) != path
                        or role not in {"unchanged-proof", "editable-proof", "new-proof"}
                        or adequacy_source not in accepted_by_id
                        or not isinstance(baseline, dict)
                    ):
                        raise IntakeError(f"proof binding `{path}` has incomplete proof-adequacy evidence")
                    if adequacy_source not in proof_sources:
                        raise IntakeError(f"proof binding `{path}` must include its proof-adequacy source answer")
                    if adequacy_fingerprint != accepted_by_id[adequacy_source]["source_evidence_fingerprint"]:
                        raise IntakeError(f"proof binding `{path}` has stale proof-adequacy evidence")
                    for key in ("test_cases", "fixtures", "assertions"):
                        values = adequacy.get(key)
                        if not isinstance(values, list) or not values or any(not str(value).strip() for value in values):
                            raise IntakeError(f"proof binding `{path}` proof adequacy needs {key}")
                    if (
                        str(baseline.get("command", "")) != command
                        or str(baseline.get("outcome", "")) not in {"pass", "fail", "not-run"}
                        or not str(baseline.get("observed", "")).strip()
                    ):
                        raise IntakeError(f"proof binding `{path}` has an invalid proof-adequacy baseline")
                    if role == "unchanged-proof" and baseline.get("outcome") != "pass":
                        raise IntakeError(f"proof binding `{path}` cannot remain unchanged without a passing baseline")
                    if role == "new-proof" and baseline.get("outcome") != "not-run":
                        raise IntakeError(f"new proof binding `{path}` must use a not-run baseline")
                    normalized_adequacy = copy.deepcopy(adequacy)
                normalized_proofs.append({
                    "proof_binding_id": _new_id("proof-binding"), "command": command, "path": path,
                    "tier": tier,
                    "asserted_behavior": asserted_behavior,
                    "source_answer_id": source_answer_id,
                    "source_answer_ids": proof_sources,
                    "evidence_fingerprint": evidence_fingerprint,
                    **({"proof_adequacy": normalized_adequacy} if normalized_adequacy is not None else {}),
                })

            criteria = requirement.get("criteria")
            if not isinstance(criteria, dict):
                raise IntakeError(f"requirement `{requirement_uid}` needs criteria bindings")
            positive = criteria.get("positive")
            negative = criteria.get("negative")
            if not isinstance(positive, list) or not positive or not isinstance(negative, list) or not negative:
                raise IntakeError(f"requirement `{requirement_uid}` needs positive and negative criteria")
            criteria_sources = source_ids(criteria.get("source_answer_ids"), f"criteria for `{requirement_uid}`")

            premise = requirement.get("correction_premise", {"status": "not-applicable", "source_answer_ids": requirement_sources})
            if not isinstance(premise, dict) or str(premise.get("status", "")).strip() not in _CORRECTION_PREMISES:
                raise IntakeError(f"correction premise for `{requirement_uid}` must be accepted or not-applicable")
            premise_sources = source_ids(premise.get("source_answer_ids"), f"correction premise for `{requirement_uid}`")
            owner_evidence = requirement.get("owner_participation_evidence", [])
            if premise.get("status") == "accepted" and (not isinstance(owner_evidence, list) or not owner_evidence):
                raise IntakeError(f"accepted correction premise for `{requirement_uid}` requires owner participation evidence")
            normalized_owner_evidence = []
            for evidence_index, evidence in enumerate(owner_evidence):
                if not isinstance(evidence, dict) or not str(evidence.get("kind", "")).strip():
                    raise IntakeError(f"owner participation evidence {evidence_index + 1} for `{requirement_uid}` is incomplete")
                normalized_owner_evidence.append({
                    "kind": str(evidence["kind"]),
                    "source_answer_ids": source_ids(evidence.get("source_answer_ids"), f"owner evidence for `{requirement_uid}`"),
                })
            normalized_requirements.append({
                "requirement_id": _new_id("requirement"), "requirement_uid": requirement_uid,
                "statement": statement, "requirement_kind": requirement_kind,
                "requirement_kind_source": kind_source,
                "requirement_kind_source_answer_ids": requirement_kind_sources,
                "source_answer_ids": requirement_sources, "profile_fields": sorted(set(profile_fields)),
                "semantic_delta": requirement.get("semantic_delta"),
                "dependencies_checked": requirement.get("dependencies_checked") is True,
                "path_bindings": normalized_paths, "proof_bindings": normalized_proofs,
                "criteria": {"positive": list(positive), "negative": list(negative), "source_answer_ids": criteria_sources},
                "correction_premise": {"status": str(premise["status"]), "source_answer_ids": premise_sources},
                "owner_participation_evidence": normalized_owner_evidence,
            })

        declared_projection = operational_bindings.get("declared_path_roles")
        if declared_projection is not None:
            declared_rows = declared_projection.get("paths") if isinstance(declared_projection, dict) else None
            if not isinstance(declared_rows, list):
                raise IntakeError("declared path-role projection must contain a paths list")
            proof_paths = {
                str(proof.get("path", ""))
                for requirement in normalized_requirements
                for proof in requirement.get("proof_bindings", [])
                if isinstance(proof, dict)
            }
            allowed_declared_roles = {*_PATH_ROLES, "excluded", "external"}
            seen_declared: dict[str, str] = {}
            for index, row in enumerate(declared_rows, start=1):
                if not isinstance(row, dict):
                    raise IntakeError(f"declared path role {index} must be an object")
                path = str(row.get("path", "")).strip()
                role = str(row.get("operational_role", "")).strip()
                if not path or role not in allowed_declared_roles:
                    raise IntakeError(f"declared path role {index} is incomplete or unsupported")
                if path in seen_declared and seen_declared[path] != role:
                    raise IntakeError(f"declared path `{path}` has contradictory roles")
                seen_declared[path] = role
                if role in _PATH_ROLES and role != "proof-only" and path_roles.get(path) != role:
                    raise IntakeError(f"declared `{role}` path `{path}` is missing from operational path bindings")
                if role == "proof-only" and path not in proof_paths:
                    raise IntakeError(f"declared proof path `{path}` is missing from executable proof bindings")
                declared_sources = row.get("source_answer_ids", [])
                if declared_sources:
                    normalized_sources = source_ids(declared_sources, f"declared path `{path}`")
                else:
                    normalized_sources = []
                normalized_declared_paths.append({
                    "path": path,
                    "host_role": str(row.get("host_role", "")),
                    "operational_role": role,
                    "existing": row.get("existing") is True,
                    "requests_write_authority": row.get("requests_write_authority") is True,
                    "grants_behavioral_ownership": row.get("grants_behavioral_ownership") is True,
                    "source_answer_ids": normalized_sources,
                    "evidence_fingerprint": row.get("evidence_fingerprint"),
                })

        unconsumed = sorted(set(accepted_by_id) - consumed_ids)
        if unconsumed:
            raise IntakeError(f"unused Navigator-accepted answers require clarification: {', '.join(unconsumed)}")
        if projected_requirement_ids != requirement_ids:
            raise IntakeError("operational requirements must exactly match their approved requirement projections")
        audit = {
            "consumed": sorted(consumed_ids), "unused": [], "contradicted": [],
            "inferred": [], "projected_without_source": [],
        }
        result = {
            "requirements": normalized_requirements,
            "path_authorizations": path_authorizations,
            "declared_path_roles": {
                "schema_version": "1",
                "type": "tailtrail-host-path-role-projection",
                "paths": normalized_declared_paths,
            },
            "projection_audit": audit,
        }
        if anchor_bound:
            result["anchor_fingerprint"] = anchor_fingerprint
        else:
            result["target_fingerprint"] = target_fingerprint
        return result

    def _invalidate_prior_packet_views(self, run_id: str, anchor_version: str, replacement_view_id: str) -> list[str]:
        """Record dependent-view invalidation when a newer anchor is finalized."""
        target_number = int(anchor_version.removeprefix("anchor-v"))
        invalidated: list[str] = []
        views_root = self._run_root(run_id) / "packet-views"
        for view_path in sorted(views_root.glob("anchor-v*.json")):
            prior_version = view_path.stem
            if prior_version == anchor_version or not _ANCHOR_VERSION.fullmatch(prior_version):
                continue
            if int(prior_version.removeprefix("anchor-v")) >= target_number:
                continue
            prior_view = json.loads(view_path.read_text(encoding="utf-8"))
            receipt_path = self._packet_invalidation_path(run_id, prior_version)
            if receipt_path.exists():
                continue
            invalidation = {
                "schema_version": "1", "type": "tailtrail-host-question-flow-packet-view-invalidation",
                "invalidated_packet_view_id": prior_view["packet_view_id"], "invalidated_anchor_version": prior_version,
                "replacement_anchor_version": anchor_version, "replacement_packet_view_id": replacement_view_id,
                "reason": "anchor-revised",
            }
            _write_json(receipt_path, invalidation)
            invalidated.append(prior_view["packet_view_id"])
        return invalidated

    def _check_packet_version(self, contract: dict[str, Any], packet_version: int | None) -> None:
        if packet_version is None:
            return
        current = contract.get("packet_version")
        if packet_version != current:
            raise IntakeError(
                f"stale packet version {packet_version} for run {contract['run_id']} (current {current})"
            )

    def revise_contract(
        self,
        run_id: str,
        changes: dict[str, Any],
        *,
        packet_version: int | None = None,
        approved: bool = False,
    ) -> dict[str, Any]:
        """Advance the contract to a new approved packet version and refresh its fingerprint."""
        if not approved:
            raise IntakeError("contract revision requires explicit approval")
        if not isinstance(changes, dict) or not changes:
            raise IntakeError("changes must be a non-empty object")
        contract = self.load_contract(run_id)
        self._check_packet_version(contract, packet_version)
        protected = {"run_id", "contract_id", "schema_version", "type"}
        safe_changes = {key: value for key, value in changes.items() if key not in protected}
        if not safe_changes:
            raise IntakeError("changes must include at least one revisable field")
        updated = dict(contract)
        updated.update(safe_changes)
        updated["packet_version"] = contract["packet_version"] + 1
        stable = {key: value for key, value in updated.items() if key != "fingerprint"}
        updated["fingerprint"] = _content_fingerprint(stable)
        _write_json(self.runs_root / str(run_id) / "contract.json", updated)
        result = self._append_event(
            updated, "anchor-revised", {"packet_version": updated["packet_version"], "changes": safe_changes}
        )
        self.replay(run_id)
        return result

    def issue_question(
        self,
        run_id: str,
        field_id: str,
        text: str,
        *,
        packet_version: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not field_id.strip() or not text.strip():
            raise IntakeError("field_id and question text are required")
        contract = self.load_contract(run_id)
        self._check_packet_version(contract, packet_version)
        question = {
            "question_id": _new_id("question"),
            "field_id": field_id,
            "text": text,
        }
        return self._append_event(
            contract, "question-issued", question, primary_id_key="question_id", idempotency_key=idempotency_key
        )

    def record_observation(
        self,
        run_id: str,
        observation: dict[str, Any],
        *,
        question_id: str | None = None,
        packet_version: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(observation, dict) or not observation:
            raise IntakeError("observation must be a non-empty object")
        contract = self.load_contract(run_id)
        self._check_packet_version(contract, packet_version)
        payload = {
            "observation_id": _new_id("observation"),
            "question_id": question_id,
            "observation": observation,
        }
        return self._append_event(
            contract,
            "host-observation-recorded",
            payload,
            primary_id_key="observation_id",
            idempotency_key=idempotency_key,
        )

    def record_answer(
        self,
        run_id: str,
        field_id: str,
        value: Any,
        *,
        source: str,
        question_id: str | None = None,
        observation_id: str | None = None,
        packet_version: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not field_id.strip() or not source.strip():
            raise IntakeError("field_id and source are required")
        if question_id is None and observation_id is None:
            raise IntakeError("answer requires question_id or observation_id")
        contract = self.load_contract(run_id)
        self._check_packet_version(contract, packet_version)
        payload = {
            "answer_id": _new_id("answer"),
            "field_id": field_id,
            "value": value,
            "source": source,
            "question_id": question_id,
            "observation_id": observation_id,
        }
        return self._append_event(
            contract, "answer-recorded", payload, primary_id_key="answer_id", idempotency_key=idempotency_key
        )

    def accept_answer(
        self,
        run_id: str,
        answer_id: str,
        evidence: dict[str, Any],
        *,
        packet_version: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Record Navigator-owned acceptance for one existing answer.

        Phase 2 produces the acceptance evidence. This method records its
        constrained result so Phase 2B finalization never trusts a caller's
        assertion that an answer was accepted.
        """
        if not answer_id.strip():
            raise IntakeError("answer_id is required for acceptance")
        if not isinstance(evidence, dict) or evidence.get("outcome") != "accepted" or evidence.get("verified_by") != "navigator":
            raise IntakeError("answer acceptance requires Navigator-validated evidence")
        contract = self.load_contract(run_id)
        self._check_packet_version(contract, packet_version)
        replay = self.replay(run_id)
        events_path = self._run_root(run_id) / "events.jsonl"
        answer_exists = any(
            event.get("event_type") == "answer-recorded"
            and str(event.get("payload", {}).get("answer_id", "")) == answer_id
            for event in (
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        )
        if not answer_exists:
            raise IntakeError(f"answer `{answer_id}` is missing from the integrity-checked intake stream")
        state_by_id = {str(record["answer_id"]): record for record in replay["answer_states"]}
        state = state_by_id.get(answer_id)
        if state is None or state.get("state") != "candidate":
            raise IntakeError(f"answer `{answer_id}` is not an eligible candidate for acceptance")
        events = [
            json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        answer = next(
            event["payload"] for event in events
            if event.get("event_type") == "answer-recorded" and event.get("payload", {}).get("answer_id") == answer_id
        )
        if _contains_redaction(answer.get("value")) or _redact(evidence) != evidence:
            raise IntakeError("secret-bearing or redacted input cannot become an accepted answer")
        if _serialized_size(evidence) > _MAX_PERSISTED_EVENT_BYTES:
            raise IntakeError("acceptance evidence exceeds the intake size limit")
        refs = self._validated_evidence_refs(evidence.get("evidence_refs", []))
        return self._append_event(
            contract,
            "answer-accepted",
            {
                "answer_id": answer_id,
                "evidence": {"outcome": "accepted", "verified_by": "navigator", "evidence_refs": refs},
                "evidence_fingerprint": _content_fingerprint(_redact(evidence)),
            },
            idempotency_key=idempotency_key,
        )

    def _current_file_fingerprint(self, path: str) -> str | None:
        target = self.root / path
        if not target.is_file():
            return None
        return "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest()

    def _validated_evidence_refs(self, refs: Any) -> list[dict[str, str]]:
        """Accept only repository-relative evidence whose bytes match the cited fingerprint."""
        if not isinstance(refs, list):
            raise IntakeError("evidence_refs must be a list")
        normalized: list[dict[str, str]] = []
        root = self.root.resolve()
        for index, ref in enumerate(refs, start=1):
            if not isinstance(ref, dict):
                raise IntakeError(f"evidence ref {index} must be an object")
            path = str(ref.get("path", "")).strip()
            fingerprint = ref.get("content_fingerprint")
            if not path or Path(path).is_absolute() or ".." in Path(path).parts:
                raise IntakeError(f"evidence ref {index} must use a repository-relative path")
            try:
                (root / path).resolve().relative_to(root)
            except ValueError as exc:
                raise IntakeError(f"evidence ref {index} escapes the repository") from exc
            if not isinstance(fingerprint, str) or not re.fullmatch(r"sha256:[a-f0-9]{64}", fingerprint):
                raise IntakeError(f"evidence ref `{path}` needs a SHA-256 content fingerprint")
            if self._current_file_fingerprint(path) != fingerprint:
                raise IntakeError(f"evidence ref `{path}` does not match its current content fingerprint")
            normalized.append({"path": path, "content_fingerprint": fingerprint})
        return sorted(normalized, key=lambda ref: ref["path"])

    def refresh_source_evidence(self, run_id: str) -> list[str]:
        """Mark accepted answers stale when any bound evidence file changed or disappeared."""
        self.load_contract(run_id)
        replay = self.replay(run_id)
        stale_ids: list[str] = []
        for record in replay["answer_states"]:
            if record.get("state") != "accepted":
                continue
            refs = record.get("evidence_refs") or []
            if any(self._current_file_fingerprint(str(ref["path"])) != ref["content_fingerprint"] for ref in refs):
                self._record_answer_state(
                    run_id, str(record["answer_id"]), "stale", "source-evidence-fingerprint-changed"
                )
                stale_ids.append(str(record["answer_id"]))
        return stale_ids

    def mark_answer_stale(self, run_id: str, answer_id: str, source_evidence_fingerprint: str) -> dict[str, Any]:
        """Invalidate one answer when its bound source evidence changes."""
        return self._record_answer_state(
            run_id, answer_id, "stale", "source-evidence-fingerprint-changed",
            source_evidence_fingerprint=source_evidence_fingerprint,
        )

    def mark_answer_conflicting(self, run_id: str, answer_id: str, reason: str) -> dict[str, Any]:
        """Record a Navigator-detected conflict without treating host prose as authority."""
        return self._record_answer_state(run_id, answer_id, "conflicting", reason)

    def _record_answer_state(
        self,
        run_id: str,
        answer_id: str,
        state: str,
        reason: str,
        *,
        source_evidence_fingerprint: str | None = None,
    ) -> dict[str, Any]:
        if state not in {"stale", "conflicting", "rejected"}:
            raise IntakeError("only non-authoritative terminal answer states may be recorded")
        contract = self.load_contract(run_id)
        replay = self.replay(run_id)
        states = {str(record["answer_id"]): record for record in replay["answer_states"]}
        record = states.get(answer_id)
        if record is None:
            raise IntakeError(f"answer `{answer_id}` is missing from the integrity-checked intake stream")
        if source_evidence_fingerprint is not None and record.get("source_evidence_fingerprint") != source_evidence_fingerprint:
            raise IntakeError("source evidence fingerprint does not match the answer lineage")
        return self._append_event(
            contract,
            "answer-rejected",
            {"answer_id": answer_id, "state": state, "reason": reason},
        )

    def _idempotency_index_path(self, run_id: str) -> Path:
        return self.runs_root / str(run_id) / "idempotency.json"

    def _load_idempotency_index(self, run_id: str) -> dict[str, Any]:
        path = self._idempotency_index_path(run_id)
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _append_event(
        self,
        contract: dict[str, Any],
        event_type: str,
        payload: dict[str, Any],
        *,
        primary_id_key: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        # The persisted envelope below must match schemas/host-question-flow-event.schema.json
        # (Phase 0, locked) exactly; idempotency and content-fingerprint bookkeeping are kept
        # out-of-band so they never appear as extra envelope or payload keys on disk.
        run_id = str(contract["run_id"])
        run_root = self.runs_root / run_id
        events_path = run_root / "events.jsonl"
        if _serialized_size(payload) > _MAX_PERSISTED_EVENT_BYTES:
            raise IntakeError("intake event exceeds the configured size limit")
        safe_payload = _redact(payload)
        if _serialized_size(safe_payload) > _MAX_PERSISTED_EVENT_BYTES:
            raise IntakeError("redacted intake event exceeds the configured size limit")
        stable_payload = safe_payload
        if primary_id_key is not None:
            stable_payload = {key: value for key, value in safe_payload.items() if key != primary_id_key}
        content_fingerprint = _content_fingerprint({"event_type": event_type, "payload": stable_payload})

        if idempotency_key:
            index = self._load_idempotency_index(run_id)
            existing = index.get(idempotency_key)
            if existing is not None:
                if existing["content_fingerprint"] != content_fingerprint:
                    raise IntakeError(
                        f"idempotency key {idempotency_key!r} already used with different event content"
                    )
                result = dict(existing["event"])
                result["content_fingerprint"] = content_fingerprint
                return result

        sequence = 1
        if events_path.is_file():
            sequence = len(events_path.read_text(encoding="utf-8").splitlines()) + 1
        event = {
            "schema_version": "1",
            "type": "tailtrail-intake-event",
            "event_id": _new_id("event"),
            "run_id": contract["run_id"],
            "contract_id": contract["contract_id"],
            "packet_version": contract["packet_version"],
            "sequence": sequence,
            "event_type": event_type,
            "payload": safe_payload,
        }
        events_path.parent.mkdir(parents=True, exist_ok=True)
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

        previous = ""
        integrity_path = self._integrity_path(run_id)
        if integrity_path.is_file():
            records = [line for line in integrity_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if records:
                previous = str(json.loads(records[-1]).get("event_fingerprint", ""))
        with integrity_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "sequence": sequence,
                "event_id": event["event_id"],
                "event_fingerprint": _content_fingerprint(event),
                "previous": previous,
            }, sort_keys=True) + "\n")

        if idempotency_key:
            index = self._load_idempotency_index(run_id)
            index[idempotency_key] = {"event": event, "content_fingerprint": content_fingerprint}
            _write_json(self._idempotency_index_path(run_id), index)

        result = dict(event)
        result["content_fingerprint"] = content_fingerprint
        self.replay(run_id)
        return result
