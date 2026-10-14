import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "host-question-flow-event.schema.json"
sys.path.insert(0, str(ROOT / "scripts"))

from intake_pipeline import IntakePipeline  # noqa: E402


def _events(run_root: Path) -> list[dict]:
    text = (run_root / "events.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


class HostQuestionFlowEventSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.validator = jsonschema.Draft202012Validator(self.schema)

    def test_schema_itself_is_structurally_valid(self) -> None:
        jsonschema.Draft202012Validator.check_schema(self.schema)

    def test_real_intake_pipeline_events_validate_against_schema(self) -> None:
        """Regression: this schema must match scripts/intake_pipeline.py's
        actual emitted envelope exactly, not an aspirational shape."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = IntakePipeline(root)
            created = pipeline.create_run("example goal", "new feature")
            run_id = created["run_id"]

            question_event = pipeline.issue_question(run_id, "implementation-owner", "Which path owns the behavior?")
            question_id = question_event["payload"]["question_id"]
            observation_event = pipeline.record_observation(
                run_id, {"path": "scripts/example.py", "exists": True}, question_id=question_id
            )
            observation_id = observation_event["payload"]["observation_id"]
            pipeline.record_answer(
                run_id, "implementation-owner", "scripts/example.py",
                source="direct-question", question_id=question_id, observation_id=observation_id,
            )

            run_root = pipeline.runs_root / run_id
            events = _events(run_root)
            self.assertEqual(len(events), 3)
            for event in events:
                errors = list(self.validator.iter_errors(event))
                self.assertEqual(errors, [], f"event failed validation: {event!r} -> {errors}")

    def test_question_issued_payload_shape_is_enforced(self) -> None:
        event = {
            "schema_version": "1",
            "type": "tailtrail-intake-event",
            "event_id": "event-1",
            "run_id": "run-1",
            "contract_id": "contract-1",
            "packet_version": 1,
            "sequence": 1,
            "event_type": "question-issued",
            "payload": {"question_id": "question-1", "field_id": "owner"},  # missing "text"
        }
        self.assertFalse(self.validator.is_valid(event))

    def test_unknown_event_type_is_rejected(self) -> None:
        event = {
            "schema_version": "1",
            "type": "tailtrail-intake-event",
            "event_id": "event-1",
            "run_id": "run-1",
            "contract_id": "contract-1",
            "packet_version": 1,
            "sequence": 1,
            "event_type": "not-a-real-event",
            "payload": {},
        }
        self.assertFalse(self.validator.is_valid(event))

    def test_reserved_future_event_types_accept_any_object_payload(self) -> None:
        for event_type in ("run-created", "packet-finalized", "approval-recorded"):
            with self.subTest(event_type=event_type):
                event = {
                    "schema_version": "1",
                    "type": "tailtrail-intake-event",
                    "event_id": "event-1",
                    "run_id": "run-1",
                    "contract_id": "contract-1",
                    "packet_version": 1,
                    "sequence": 1,
                    "event_type": event_type,
                    "payload": {"anything": "goes-for-now"},
                }
                self.assertTrue(self.validator.is_valid(event))

    def test_answer_recorded_requires_a_question_or_observation_reference(self) -> None:
        event = {
            "schema_version": "1",
            "type": "tailtrail-intake-event",
            "event_id": "event-1",
            "run_id": "run-1",
            "contract_id": "contract-1",
            "packet_version": 1,
            "sequence": 1,
            "event_type": "answer-recorded",
            "payload": {
                "answer_id": "answer-1",
                "field_id": "owner",
                "value": "scripts/example.py",
                "source": "direct-question",
                # question_id/observation_id omitted entirely
            },
        }
        self.assertFalse(self.validator.is_valid(event))

    def test_additional_envelope_properties_are_rejected(self) -> None:
        event = {
            "schema_version": "1",
            "type": "tailtrail-intake-event",
            "event_id": "event-1",
            "run_id": "run-1",
            "contract_id": "contract-1",
            "packet_version": 1,
            "sequence": 1,
            "event_type": "question-issued",
            "payload": {"question_id": "question-1", "field_id": "owner", "text": "Which path?"},
            "unexpected": "field",
        }
        self.assertFalse(self.validator.is_valid(event))


if __name__ == "__main__":
    unittest.main()
