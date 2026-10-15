from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.intake_pipeline import IntakeError, IntakePipeline


class IntakePipelineTests(unittest.TestCase):
    def test_creates_immutable_contract_and_correlates_interaction_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline = IntakePipeline(Path(temp))
            run = pipeline.create_run("collect host context", "new-feature")
            contract_path = Path(temp) / ".tailtrail" / "intake" / run["run_id"] / "contract.json"
            original_contract = contract_path.read_text(encoding="utf-8")

            question = pipeline.issue_question(run["run_id"], "implementation-owner", "Which path owns the behavior?")
            observation = pipeline.record_observation(
                run["run_id"], {"path": "scripts/example.py", "exists": True}, question_id=question["payload"]["question_id"]
            )
            answer = pipeline.record_answer(
                run["run_id"],
                "implementation-owner",
                "scripts/example.py",
                source="host-observation",
                observation_id=observation["payload"]["observation_id"],
            )

            self.assertEqual(pipeline.load_contract(run["run_id"])["contract_id"], run["contract_id"])
            self.assertEqual(contract_path.read_text(encoding="utf-8"), original_contract)
            events_path = contract_path.with_name("events.jsonl")
            events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([event["sequence"] for event in events], [1, 2, 3])
            self.assertEqual(events[0]["event_type"], "question-issued")
            self.assertEqual(events[1]["event_type"], "host-observation-recorded")
            self.assertEqual(events[2]["event_type"], "answer-recorded")
            self.assertEqual(answer["contract_id"], run["contract_id"])
            self.assertEqual(answer["packet_version"], 1)

    def test_duplicate_event_submission_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline = IntakePipeline(Path(temp))
            run = pipeline.create_run("collect host context", "new-feature")

            first = pipeline.issue_question(
                run["run_id"], "implementation-owner", "Which path owns the behavior?", idempotency_key="q-1"
            )
            second = pipeline.issue_question(
                run["run_id"], "implementation-owner", "Which path owns the behavior?", idempotency_key="q-1"
            )
            self.assertEqual(first["event_id"], second["event_id"])

            events_path = Path(temp) / ".tailtrail" / "intake" / run["run_id"] / "events.jsonl"
            events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(events), 1)

            with self.assertRaises(IntakeError):
                pipeline.issue_question(
                    run["run_id"], "implementation-owner", "A different question text", idempotency_key="q-1"
                )

    def test_events_from_stale_run_or_packet_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline = IntakePipeline(Path(temp))

            with self.assertRaises(IntakeError):
                pipeline.issue_question("run-does-not-exist", "implementation-owner", "Which path owns the behavior?")

            run = pipeline.create_run("collect host context", "new-feature")
            with self.assertRaises(IntakeError):
                pipeline.issue_question(
                    run["run_id"], "implementation-owner", "Which path owns the behavior?", packet_version=99
                )

    def test_contract_fingerprint_changes_only_through_approved_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline = IntakePipeline(Path(temp))
            run = pipeline.create_run("collect host context", "new-feature")
            original_fingerprint = pipeline.load_contract(run["run_id"])["fingerprint"]

            question = pipeline.issue_question(run["run_id"], "implementation-owner", "Which path owns the behavior?")
            pipeline.record_observation(
                run["run_id"], {"path": "scripts/example.py", "exists": True}, question_id=question["payload"]["question_id"]
            )
            pipeline.record_answer(
                run["run_id"],
                "implementation-owner",
                "scripts/example.py",
                source="host-observation",
                question_id=question["payload"]["question_id"],
            )
            self.assertEqual(pipeline.load_contract(run["run_id"])["fingerprint"], original_fingerprint)

            with self.assertRaises(IntakeError):
                pipeline.revise_contract(run["run_id"], {"status": "revised"})

            revision_event = pipeline.revise_contract(run["run_id"], {"status": "revised"}, approved=True)
            revised_contract = pipeline.load_contract(run["run_id"])
            self.assertNotEqual(revised_contract["fingerprint"], original_fingerprint)
            self.assertEqual(revised_contract["packet_version"], 2)
            self.assertEqual(revision_event["event_type"], "anchor-revised")

    def test_interaction_ids_are_unique_with_stable_content_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline = IntakePipeline(Path(temp))
            run = pipeline.create_run("collect host context", "new-feature")

            first = pipeline.issue_question(run["run_id"], "implementation-owner", "Which path owns the behavior?")
            second = pipeline.issue_question(run["run_id"], "implementation-owner", "Which path owns the behavior?")
            third = pipeline.issue_question(run["run_id"], "implementation-owner", "A different question text")

            self.assertNotEqual(first["payload"]["question_id"], second["payload"]["question_id"])
            self.assertNotEqual(first["event_id"], second["event_id"])
            self.assertEqual(first["content_fingerprint"], second["content_fingerprint"])
            self.assertNotEqual(first["content_fingerprint"], third["content_fingerprint"])


if __name__ == "__main__":
    unittest.main()
