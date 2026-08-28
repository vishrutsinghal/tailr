from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
