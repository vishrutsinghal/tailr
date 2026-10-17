from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from scripts.intake_pipeline import IntakePipeline


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tailtrail_question_orchestrator", ROOT / "scripts" / "question-orchestrator.py")
assert SPEC and SPEC.loader
orchestrator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(orchestrator)


def question(**overrides):
    payload = {
        "id": "OQ1",
        "question": "Which normalization behavior is required?",
        "options": [
            {"id": "A", "text": "Trim outer whitespace"},
            {"id": "B", "text": "Preserve exact input"},
            {"id": "Other", "text": "Other (describe)"},
        ],
        "recommended": "Trim outer whitespace",
        "reasoning": "The user requested a normalization decision before implementation.",
    }
    payload.update(overrides)
    return payload


class QuestionOrchestratorTests(unittest.TestCase):
    def context(self):
        return orchestrator.prepare_context(
            "start-test",
            "standard",
            "Add address validation and clarify normalization.",
            [
                {"display_id": "REQ-01", "statement": "Add address validation."},
                {"display_id": "REQ-02", "statement": "Preserve existing client behavior.", "kind": "preserve"},
            ],
            {
                "architecture_plan": {
                    "scope_roles": [
                        {"path": "src/orders/validation.py", "role": "validation boundary"},
                    ]
                },
                "focused_validation_plan": {"tiers": ["unit", "integration"]},
            },
        )

    def test_context_preserves_authority_and_labels_inventory_as_hypothesis(self):
        context = self.context()
        self.assertEqual(context["question_authority"], "official-ai-dlc-pack")
        self.assertFalse(context["question_policy"]["source_bodies_read"])
        inventory = next(item for item in context["known_facts"] if item["fact_id"].startswith("INV-"))
        self.assertEqual(inventory["confidence"], "repository-inventory-hypothesis")
        self.assertIn("src/orders/validation.py", inventory["evidence"])

    def test_quality_gate_adds_requirement_and_decision_traceability(self):
        result = orchestrator.evaluate_questions([question(requirement_ids=["REQ-01"])], self.context(), "official-ai-dlc-pack")
        saved = result["questions"][0]
        self.assertEqual(result["quality"]["status"], "passed")
        self.assertEqual(saved["authority"], "official-ai-dlc-pack")
        self.assertEqual(saved["requirement_ids"], ["REQ-01"])
        self.assertEqual(saved["decision_class"], "user-decision")
        self.assertIn("acceptance-criteria", saved["decision_impact"])

    def test_quality_gate_rejects_duplicate_questions(self):
        with self.assertRaisesRegex(ValueError, "duplicates another question"):
            orchestrator.evaluate_questions([question(), question(id="OQ2")], self.context(), "official-ai-dlc-pack")

    def test_repository_claim_requires_explicit_evidence(self):
        asserted = question(reasoning="The existing API uses structured address fields and therefore option A is compatible.")
        with self.assertRaisesRegex(ValueError, "explicit evidence_refs"):
            orchestrator.evaluate_questions([asserted], self.context(), "official-ai-dlc-pack")

        asserted["evidence_refs"] = ["saved-investigation:api-address-shape"]
        asserted["requirement_ids"] = ["REQ-01"]
        result = orchestrator.evaluate_questions([asserted], self.context(), "official-ai-dlc-pack")
        self.assertEqual(result["questions"][0]["evidence_refs"], ["saved-investigation:api-address-shape"])

    def test_conditional_reuse_advice_does_not_claim_repository_evidence(self):
        conditional = question(
            recommended="Reuse an existing action when the target project provides one.",
            reasoning="This keeps the change bounded without claiming that such an action exists.",
        )

        result = orchestrator.evaluate_questions([conditional], self.context(), "local-lite")

        self.assertEqual(result["quality"]["status"], "passed")

    def test_navigator_intake_issues_and_records_direct_answer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            intake = orchestrator.NavigatorIntake(root)
            from scripts.intake_pipeline import IntakePipeline

            run = IntakePipeline(root).create_run("collect owner", "existing-code-change")
            question = intake.issue_question(
                run["run_id"],
                "implementation-owner",
                {"id": "Q1", "question": "Which path owns the behavior?"},
            )
            answer = intake.record_direct_answer(
                run["run_id"],
                "implementation-owner",
                "scripts/question-orchestrator.py",
                question_id=question["payload"]["question_id"],
            )

            events_path = root / ".tailtrail" / "intake" / run["run_id"] / "events.jsonl"
            events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual([event["event_type"] for event in events], ["question-issued", "answer-recorded"])
        self.assertEqual(answer["payload"]["source"], "direct-question")

    def test_narration_answer_keeps_observation_and_answer_correlation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            intake = orchestrator.NavigatorIntake(root)
            from scripts.intake_pipeline import IntakePipeline

            run = IntakePipeline(root).create_run("collect owner", "existing-code-change")
            answer = intake.record_narration_answer(
                run["run_id"],
                "implementation-owner",
                "scripts/question-orchestrator.py",
                "The orchestrator should own the question exchange.",
            )

            events_path = root / ".tailtrail" / "intake" / run["run_id"] / "events.jsonl"
            events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual([event["event_type"] for event in events], ["host-observation-recorded", "answer-recorded"])
        self.assertEqual(answer["payload"]["source"], "narration-observation")
        self.assertEqual(answer["payload"]["observation_id"], events[0]["payload"]["observation_id"])

    def test_host_protocol_profiles_questions_and_clarification_are_bounded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            intake = orchestrator.NavigatorIntake(root)
            protocol = orchestrator.NavigatorHostProtocol(intake)
            documentation = protocol.profile_task("Update the guide", paths=["docs/guide.md"])
            feature = protocol.profile_task("Create a new feature", change_intent="new-feature")
            self.assertEqual(documentation["profile"], "documentation-only")
            self.assertEqual(feature["profile"], "new-feature")
            self.assertLess(
                len(protocol.plan_questions(documentation["profile"])),
                len(protocol.plan_questions(feature["profile"])),
            )

            run = IntakePipeline(root).create_run("collect feature context", "new-feature")
            issued = protocol.issue_profile_questions(run["run_id"], feature["profile"])
            self.assertEqual(len(issued), protocol.max_questions_per_round)
            self.assertNotEqual(issued[0]["field_id"], issued[0]["question_id"])

            candidate = protocol.record_direct_candidate(run["run_id"], issued[0]["question_id"], " src/new_feature.py ")
            host_claim = protocol.evidence_check(candidate, {"outcome": "accepted", "verified_by": "host"})
            self.assertEqual(host_claim["state"], "clarification-required")
            self.assertFalse(host_claim["authority_granted"])

            for _ in range(protocol.max_clarification_rounds):
                route = protocol.clarification_route(run["run_id"], feature["profile"], {issued[0]["field_id"]})
                self.assertEqual(route["state"], "awaiting-clarification")
                self.assertLessEqual(len(route["questions"]), protocol.max_questions_per_round)
            dead_end = protocol.clarification_route(run["run_id"], feature["profile"], {issued[0]["field_id"]})
            self.assertEqual(dead_end["state"], "user-decision-required")

    def test_host_protocol_narration_stays_candidate_until_navigator_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            intake = orchestrator.NavigatorIntake(root)
            protocol = orchestrator.NavigatorHostProtocol(intake)
            run = IntakePipeline(root).create_run("collect feature context", "new-feature")
            result = protocol.ingest_narration(
                run["run_id"],
                "new-feature",
                "The public route is the command handler.",
                [{"field_id": "public-route", "value": " command handler "}],
            )

            candidate = result["candidates"][0]
            self.assertEqual(candidate["state"], "mapped-to-profile-field")
            self.assertIsNone(candidate["question_id"])
            self.assertFalse(candidate["authority_granted"])
            accepted = protocol.evidence_check(candidate, {"outcome": "accepted", "verified_by": "navigator"})
            self.assertEqual(accepted["state"], "accepted")
            self.assertFalse(accepted["authority_granted"])
            self.assertFalse(accepted["finalization_allowed"])


if __name__ == "__main__":
    unittest.main()
