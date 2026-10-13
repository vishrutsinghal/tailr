from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.intake_pipeline import IntakePipeline


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


if __name__ == "__main__":
    unittest.main()
