from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tailtrail_aidlc_requirements", ROOT / "scripts" / "aidlc-requirements.py")
assert SPEC and SPEC.loader
aidlc_requirements = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(aidlc_requirements)


class AidlcRequirementsTests(unittest.TestCase):
    def test_ui_requirement_questions_are_specific_and_keep_known_facts(self) -> None:
        goal = """Add a React Pipeline Audit Events Generator page. Users enter an Event Header,
        Business Application, Execution Context, and Processing State; common values propagate to
        Step and Task events. Generate Message ID as a UUID, validate required Sender ID, reuse
        existing components and do not add dependencies. A Figma reference and API contract are in scope."""
        stage = aidlc_requirements.gather(goal, [{"id": "REQ-01", "statement": "Implement the audit-event generator UI."}], [])

        questions = {item["id"]: item["question"] for item in stage["questions"]}
        self.assertIn("hierarchy", questions["Q1"].lower())
        self.assertIn("Step and Task", questions["Q2"])
        self.assertIn("Message ID", questions["Q3"])
        self.assertIn("validation experience", questions["Q4"])
        self.assertNotIn("What exact observable outcome defines completion?", questions.values())
        self.assertIn("Existing project components and dependencies must be reused where possible.", stage["known_facts"])

    def test_api_requirement_questions_are_contract_specific(self) -> None:
        stage = aidlc_requirements.gather("Add an API endpoint and update the client contract.", [{"id": "REQ-01", "statement": "Add the endpoint."}], [])
        questions = [item["question"] for item in stage["questions"]]
        self.assertIn("contract", questions[0].lower())
        self.assertIn("clients", questions[1].lower())

    def test_feedback_question_follows_task_shaped_questions(self) -> None:
        stage = aidlc_requirements.gather(
            "Add a React form page.",
            [{"id": "REQ-01", "statement": "Add the UI."}],
            [{"comment": "Keep the form compact."}],
        )
        self.assertEqual(stage["questions"][-1]["id"], "Q6")


if __name__ == "__main__":
    unittest.main()
