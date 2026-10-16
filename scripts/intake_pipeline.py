"""Minimal Phase 1A intake contract and interaction event pipeline."""
from __future__ import annotations

import hashlib
import json
import re
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
        }
        _write_json(self._projection_path(run_id), result)
        return result

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
        stable_payload = payload
        if primary_id_key is not None:
            stable_payload = {key: value for key, value in payload.items() if key != primary_id_key}
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
            "payload": payload,
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
