"""Minimal Phase 1A intake contract and interaction event pipeline."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any


class IntakeError(ValueError):
    """Raised when an intake operation cannot satisfy its contract."""


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


class IntakePipeline:
    """Persist the Phase 1A contract and correlate interaction events."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.runs_root = self.root / ".tailtrail" / "intake"

    def create_run(self, goal: str, profile: str) -> dict[str, str]:
        if not goal.strip() or not profile.strip():
            raise IntakeError("goal and profile are required")
        run_id = _new_id("run")
        contract = {
            "schema_version": "1",
            "type": "tailtrail-intake-contract",
            "run_id": run_id,
            "contract_id": _new_id("contract"),
            "profile": profile,
            "goal": goal,
            "packet_version": 1,
            "status": "intake",
        }
        run_root = self.runs_root / run_id
        _write_json(run_root / "contract.json", contract)
        return {
            "run_id": run_id,
            "contract_id": str(contract["contract_id"]),
            "packet_version": "1",
        }

    def load_contract(self, run_id: str) -> dict[str, Any]:
        path = self.runs_root / run_id / "contract.json"
        if not path.is_file():
            raise IntakeError(f"unknown intake run: {run_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def issue_question(self, run_id: str, field_id: str, text: str) -> dict[str, Any]:
        if not field_id.strip() or not text.strip():
            raise IntakeError("field_id and question text are required")
        contract = self.load_contract(run_id)
        question = {
            "question_id": _new_id("question"),
            "field_id": field_id,
            "text": text,
        }
        return self._append_event(contract, "question-issued", question)

    def record_observation(
        self,
        run_id: str,
        observation: dict[str, Any],
        *,
        question_id: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(observation, dict) or not observation:
            raise IntakeError("observation must be a non-empty object")
        contract = self.load_contract(run_id)
        payload = {
            "observation_id": _new_id("observation"),
            "question_id": question_id,
            "observation": observation,
        }
        return self._append_event(contract, "host-observation-recorded", payload)

    def record_answer(
        self,
        run_id: str,
        field_id: str,
        value: Any,
        *,
        source: str,
        question_id: str | None = None,
        observation_id: str | None = None,
    ) -> dict[str, Any]:
        if not field_id.strip() or not source.strip():
            raise IntakeError("field_id and source are required")
        if question_id is None and observation_id is None:
            raise IntakeError("answer requires question_id or observation_id")
        contract = self.load_contract(run_id)
        payload = {
            "answer_id": _new_id("answer"),
            "field_id": field_id,
            "value": value,
            "source": source,
            "question_id": question_id,
            "observation_id": observation_id,
        }
        return self._append_event(contract, "answer-recorded", payload)

    def _append_event(
        self,
        contract: dict[str, Any],
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        run_root = self.runs_root / str(contract["run_id"])
        events_path = run_root / "events.jsonl"
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
        return event
