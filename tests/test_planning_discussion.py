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


lock = load("planning_discussion_lock_test", "scripts/planning-lock.py")
discussion = load("planning_discussion_test", "scripts/planning-discussion.py")


class PlanningDiscussionTests(unittest.TestCase):
    def test_question_records_sanitized_receipt_without_touching_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src" / "service.py"
            source.parent.mkdir()
            source.write_text("VALUE = 1\n", encoding="utf-8")
            lock.create(root, "fix validation", "discussion-1")
            lock.save_start_report(root, "discussion-1", {"goal": "fix validation"})

            result = discussion.discuss(root, "discussion-1", "Why was src/service.py selected for REQ-02?")
            saved = (root / ".tailtrail" / "runs" / "discussion-1" / "planning" / "plan-conversations.jsonl").read_text(encoding="utf-8")
            source_content = source.read_text(encoding="utf-8")

        self.assertTrue(result["recorded"])
        self.assertEqual(result["receipt"]["conversation_id"], "plan-q-001")
        self.assertEqual(result["receipt"]["classification"], "explain-scope")
        self.assertEqual(result["discussion_state"]["planning_lock_status"], "awaiting-approval")
        self.assertEqual(source_content, "VALUE = 1\n")
        self.assertNotIn("Why was src/service.py selected for REQ-02?", saved)
        self.assertIn('"value":"src/service.py"', saved)

    def test_pasted_error_is_not_a_discussion_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix validation", "discussion-error")
            result = discussion.discuss(root, "discussion-error", "Traceback (most recent call last):\nValueError: invalid value")
            receipts = root / ".tailtrail" / "runs" / "discussion-error" / "planning" / "plan-conversations.jsonl"

        self.assertFalse(result["recorded"])
        self.assertEqual(result["classification"], "pasted-error-or-log")
        self.assertFalse(receipts.exists())

    def test_approved_run_rejects_interactive_plan_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix validation", "discussion-approved")
            lock.approve(root, "discussion-approved", True)
            with self.assertRaisesRegex(ValueError, "awaiting approval"):
                discussion.discuss(root, "discussion-approved", "Why was validation.py selected?")

    def test_unknown_message_remains_ordinary_chat_without_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix validation", "discussion-unknown")
            result = discussion.discuss(root, "discussion-unknown", "Good morning TailTrail")
            receipts = root / ".tailtrail" / "runs" / "discussion-unknown" / "planning" / "plan-conversations.jsonl"

        self.assertFalse(result["recorded"])
        self.assertEqual(result["classification"], "ordinary-chat")
        self.assertFalse(receipts.exists())

    def test_rejection_and_aidlc_are_routed_to_existing_control_planes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix validation", "discussion-routes")
            rejected = discussion.discuss(root, "discussion-routes", "Reject all — the validation boundary is wrong")
            aidlc = discussion.discuss(root, "discussion-routes", "Use AIDLC Requirements mode")

        self.assertEqual(rejected["route"], "tailtrail planning feedback-template")
        self.assertEqual(aidlc["route"], "tailtrail planning aidlc-requirements")

    def test_standard_aidlc_switch_routes_to_a_versioned_mode_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix validation", "discussion-standard")
            result = discussion.discuss(root, "discussion-standard", "Switch to Standard AIDLC mode")

        self.assertFalse(result["recorded"])
        self.assertEqual(result["classification"], "aidlc-standard-switch")
        self.assertIn("planning aidlc-standard", result["route"])

    def test_feature_customization_routes_to_the_single_control_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix validation", "discussion-controls")
            result = discussion.discuss(root, "discussion-controls", "Enable the Behaviour Harness")

        self.assertFalse(result["recorded"])
        self.assertEqual(result["classification"], "feature-customization")
        self.assertIn("feature-controls-show", result["route"])

    def test_show_returns_only_sanitized_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix validation", "discussion-show")
            discussion.discuss(root, "discussion-show", "What validation proof is planned?")
            shown = discussion.discussion_show(root, "discussion-show")
            encoded = json.dumps(shown)

        self.assertEqual(len(shown["receipts"]), 1)
        self.assertEqual(shown["receipts"][0]["classification"], "explain-testing")
        self.assertNotIn("What validation proof is planned?", encoded)

    def test_decision_show_summarizes_saved_state_without_source_access(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src" / "service.py"; source.parent.mkdir(); source.write_text("UNCHANGED\n", encoding="utf-8")
            lock.create(root, "fix validation", "decision-show")
            discussion.discuss(root, "decision-show", "Why was validation.py selected?")
            result = discussion.decision_show(root, "decision-show")
            source_content = source.read_text(encoding="utf-8")

        self.assertEqual(result["planning_lock_status"], "awaiting-approval")
        self.assertEqual(result["discussion_count"], 1)
        self.assertEqual(result["revision"]["active"], 1)
        self.assertEqual(result["authority_routes"], [])
        self.assertEqual(result["aidlc_mode"]["mode"], "lite")
        self.assertEqual(source_content, "UNCHANGED\n")

    def test_explain_uses_saved_file_decision_without_reading_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src" / "service.py"
            source.parent.mkdir()
            source.write_text("UNCHANGED = True\n", encoding="utf-8")
            lock.create(root, "fix validation", "explain-file")
            lock.save_start_report(root, "explain-file", {
                "goal": "fix validation",
                "navigator": {
                    "likely_impacted_files": [
                        {"path": "src/service.py", "reason": "Code Review Graph Lite found a likely caller"},
                        {"path": "tests/test_service.py", "reason": "focused validation candidate"},
                    ],
                    "suggested_commands": ["python3 -m unittest tests.test_service"],
                    "selected_features": [{"name": "Architecture Fitness Harness", "why": "multi-file caller path"}],
                    "risks": ["multi-file"],
                },
                "guided_delivery": {"selected": [{"name": "Evidence-Aware Testing", "why": "focused proof"}], "activated_later": []},
                "aidlc_mode": {"mode": "lite", "selection": "small fix", "boundary": "planning only"},
                "token_posture": {"used_tokens": 120, "evidence": "Approximate file character count only."},
            })
            result = discussion.discuss(root, "explain-file", "Why was src/service.py selected?")
            source_content = source.read_text(encoding="utf-8")
            saved = (root / ".tailtrail" / "runs" / "explain-file" / "planning" / "plan-conversations.jsonl").read_text(encoding="utf-8")

        answer = result["answer"]
        self.assertEqual(answer["status"], "answered")
        self.assertIn("inspection target", answer["direct"])
        self.assertEqual(answer["evidence"][0]["label"], "graph-cache")
        self.assertIn("src/service.py", answer["evidence"][0]["detail"])
        self.assertEqual(source_content, "UNCHANGED = True\n")
        self.assertNotIn("Why was src/service.py selected?", saved)

    def test_explain_marks_missing_saved_evidence_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix validation", "explain-unknown")
            lock.save_start_report(root, "explain-unknown", {"goal": "fix validation", "navigator": {}})
            result = discussion.discuss(root, "explain-unknown", "Why was src/unknown.py selected?")

        self.assertEqual(result["answer"]["status"], "unknown")
        self.assertIn("does not contain enough evidence", result["answer"]["direct"])
        self.assertIn("no plan change", result["answer"]["impact_on_plan"].lower())

    def test_explain_token_and_drift_never_claim_measured_usage_or_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix validation", "explain-posture")
            lock.save_start_report(root, "explain-posture", {
                "goal": "fix validation",
                "navigator": {},
                "token_posture": {"used_tokens": 42, "evidence": "Approximate file character count only."},
            })
            token = discussion.discuss(root, "explain-posture", "What token cost is planned?")["answer"]
            drift = discussion.discuss(root, "explain-posture", "What drift has happened?")["answer"]

        self.assertIn("not measured model usage", token["direct"])
        self.assertIn("No implementation drift has been measured", drift["direct"])

    def test_explain_deferred_control_and_aidlc_assumption_use_saved_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "add cancellation", "explain-decisions")
            lock.save_start_report(root, "explain-decisions", {
                "goal": "add cancellation",
                "navigator": {"skipped_features": [{"name": "Context Continuity Harness", "why": "activates after a correction cycle"}]},
                "guided_delivery": {"selected": [], "activated_later": []},
                "aidlc_requirements": {"aidlc_stage": {"assumptions": ["Refund adapter is already available"], "non_goals": ["No new payment provider"]}},
            })
            feature = discussion.discuss(root, "explain-decisions", "Why is the Context Continuity Harness deferred?")["answer"]
            assumptions = discussion.discuss(root, "explain-decisions", "What assumptions are in this plan?")["answer"]

        self.assertEqual(feature["status"], "answered")
        self.assertIn("deferred controls", feature["alternative"].lower())
        self.assertEqual(assumptions["status"], "answered")
        self.assertIn("Refund adapter is already available", assumptions["evidence"][0]["detail"])

    def test_markdown_explanation_has_required_sections_without_raw_question(self) -> None:
        payload = {
            "run_id": "rendered",
            "answer": {
                "direct": "Saved answer.",
                "evidence": [{"label": "planning-lock", "detail": "Saved boundary."}],
                "alternative": "Keep discussing.",
                "risk": "Do not infer source facts.",
                "impact_on_plan": "No plan change.",
                "next_choice": "Approve or continue discussion.",
            },
        }
        rendered = discussion.render_explanation(payload)

        for heading in ("## Answer", "## Evidence", "## Alternative", "## Risk", "## Impact on the plan", "## Next choice"):
            self.assertIn(heading, rendered)
        self.assertNotIn("Why was service.py selected?", rendered)


if __name__ == "__main__":
    unittest.main()
