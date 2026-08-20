from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lock = load("aidlc_question_lock_test", "scripts/planning-lock.py")
question_control = load("aidlc_question_control_test", "scripts/planning-aidlc-question.py")


class AIDLCQuestionControlTests(unittest.TestCase):
    def _run(self, root: Path, run_id: str) -> dict:
        lock.create(root, "fix the zero quantity validation bug", run_id)
        lock.save_start_report(root, run_id, {
            "goal": "fix the zero quantity validation bug",
            "guided_delivery": {"mode": "guided-delivery"},
            "navigator": {},
            "aidlc_mode": {"mode": "lite"},
        })
        return lock.request_aidlc_requirements(root, run_id)

    def test_clarify_reads_saved_question_without_changing_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); stage = self._run(root, "question-clarify")
            before = (root / stage["artifact"]).read_text(encoding="utf-8")
            result = question_control.clarify(root, "question-clarify", "Q1")
            after = (root / stage["artifact"]).read_text(encoding="utf-8")

        self.assertEqual(result["authority"], "tailtrail-aidlc-lite")
        self.assertEqual(result["question"]["id"], "Q1")
        self.assertIn("Do not change", result["clarification"]["host_action"])
        self.assertEqual(before, after)

    def test_question_revision_requires_candidate_then_user_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._run(root, "question-revise")
            original = question_control.show(root, "question-revise", "Q1")["question"]
            proposed = question_control.challenge(root, "question-revise", "Q1", "unclear-reasoning")
            candidate = {**original, "question": "In simpler terms: " + original["question"]}
            recorded = question_control.record(root, "question-revise", json.dumps(candidate))
            before_approval = question_control.show(root, "question-revise", "Q1")["question"]
            approved = question_control.approve(root, "question-revise", True)
            after_approval = question_control.show(root, "question-revise", "Q1")["question"]

        self.assertEqual(proposed["proposal"]["status"], "host-revision-required")
        self.assertEqual(recorded["proposal"]["status"], "awaiting-question-approval")
        self.assertEqual(before_approval["question"], original["question"])
        self.assertEqual(approved["question_revision"], 2)
        self.assertTrue(after_approval["question"].startswith("In simpler terms:"))

    def test_approved_question_revision_invalidates_prior_answer_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); stage = self._run(root, "question-stale")
            answers = [{"question_id": row["id"], "choice": row["options"][0]["id"]} for row in stage["questions"]]
            lock.submit_aidlc_answers(root, "question-stale", json.dumps(answers))
            original = question_control.show(root, "question-stale", "Q1")["question"]
            question_control.challenge(root, "question-stale", "Q1", "missing-option")
            question_control.record(root, "question-stale", json.dumps({**original, "question": "Updated: " + original["question"]}))
            question_control.approve(root, "question-stale", True)
            with self.assertRaisesRegex(ValueError, "answers are stale"):
                lock.approve_aidlc_requirements(root, "question-stale", True)

    def test_official_question_revision_preserves_official_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); run_id = "official-question"
            lock.create(root, "add a governed capability", run_id)
            question = {
                "id": "OQ5", "question": "Which proof is required?",
                "options": [{"id": "A", "text": "Focused test only"}, {"id": "B", "text": "Focused and integration proof"}, {"id": "Other", "text": "Other â€” describe the intended behavior."}],
                "recommended": "Focused and integration proof", "reasoning": "The feature crosses a service boundary.",
            }
            artifact = root / ".tailtrail" / "runs" / run_id / "planning" / "official-aidlc-requirements-v1.json"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text(json.dumps({"type": "tailtrail-official-aidlc-requirements", "run_id": run_id, "questions": [question], "question_revision": 1}), encoding="utf-8")
            proposal = question_control.challenge(root, run_id, "OQ5", "unclear")
            recorded = question_control.record(root, run_id, json.dumps({**question, "question": "Simply: what proof do we need?"}))

        self.assertEqual(proposal["proposal"]["authority"], "official-ai-dlc-pack")
        self.assertEqual(recorded["proposal"]["candidate"]["recommendation_origin"], "tailtrail-advisory")


if __name__ == "__main__":
    unittest.main()
