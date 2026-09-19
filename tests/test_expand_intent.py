from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tailtrail_expand_intent_test", ROOT / "scripts" / "expand-intent.py")
assert SPEC and SPEC.loader
expand = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = expand
SPEC.loader.exec_module(expand)


class ExpandIntentTests(unittest.TestCase):
    def test_full_aidlc_phrase_does_not_fall_back_to_standard(self) -> None:
        self.assertEqual(expand.resolve_intent("use full AIDLC mode"), "aidlc_full")
        flow = expand.FLOWS["aidlc_full"]
        self.assertIn("--aidlc full", flow.prompt)
        self.assertIn("Do not silently downgrade", flow.prompt)

    def test_loose_tailtrail_goal_routes_to_planning_only_start(self) -> None:
        envelope = expand.resolve_request(
            "Use TailTrail to reject zero quantities but keep positive quantities working."
        )
        self.assertEqual(envelope["action"], "start")
        self.assertEqual(
            envelope["goal"],
            "reject zero quantities but keep positive quantities working.",
        )
        self.assertEqual(envelope["authority"]["classification"], "planning-only")
        self.assertFalse(envelope["authority"]["approval_inferred"])
        self.assertFalse(envelope["authority"]["execution_granted"])

    def test_common_tailtrial_typo_routes_like_tailtrail(self) -> None:
        envelope = expand.resolve_request(
            "tailtrial start debug repeated report steps --debug"
        )
        self.assertEqual(envelope["action"], "start")
        self.assertEqual(envelope["goal"], "debug repeated report steps")
        self.assertTrue(envelope["explicit_hints"]["debug"])

    def test_polite_and_punctuation_variants_preserve_the_task_goal(self) -> None:
        cases = {
            "TailTrail, reject zero quantities": "reject zero quantities",
            "Please use TailTrail to reject zero quantities": "reject zero quantities",
            "Using TailTrail, reject zero quantities": "reject zero quantities",
            "Can TailTrail help me reject zero quantities": "reject zero quantities",
        }
        for phrase, goal in cases.items():
            with self.subTest(phrase=phrase):
                envelope = expand.resolve_request(phrase)
                self.assertEqual(envelope["action"], "start")
                self.assertEqual(envelope["goal"], goal)

    def test_exact_start_colon_preserves_the_goal_without_options(self) -> None:
        envelope = expand.resolve_request(
            "tailtrail start: reject zero order quantity while preserving positive quantities"
        )
        self.assertEqual(envelope["operation"]["name"], "start")
        self.assertEqual(
            envelope["operation"]["arguments"],
            {"goal": "reject zero order quantity while preserving positive quantities"},
        )

    def test_cli_style_start_extracts_explicit_hints_without_putting_flags_in_goal(self) -> None:
        envelope = expand.resolve_request(
            'tailtrail start "add safe order amendments" --aidlc full --verbose'
        )
        self.assertEqual(envelope["goal"], "add safe order amendments")
        self.assertEqual(envelope["explicit_hints"]["aidlc"], "full")
        self.assertTrue(envelope["explicit_hints"]["verbose"])

    def test_advisory_language_routes_to_guide(self) -> None:
        envelope = expand.resolve_request(
            "Show me how to reject zero quantity without breaking valid orders."
        )
        self.assertEqual(envelope["action"], "guide")
        self.assertEqual(envelope["authority"]["classification"], "read-only")

    def test_informational_question_routes_to_guide_not_start(self) -> None:
        self.assertEqual(
            expand.resolve_intent("Run TailTrail Navigator for: tell me the important features of this repo. Show the plan only"),
            "guide",
        )
        for phrase in (
            "tell me the important features of this repo",
            "what are the main services here?",
            "explain how validation works",
        ):
            with self.subTest(phrase=phrase):
                envelope = expand.resolve_request(phrase)
                self.assertEqual(envelope["action"], "guide")
                self.assertEqual(envelope["authority"]["classification"], "read-only")

    def test_question_with_change_verb_keeps_task_routing(self) -> None:
        self.assertEqual(expand.resolve_intent("list the failing files then fix the bug"), "implementation")
        envelope = expand.resolve_request("explain the validation defect and fix it")
        self.assertEqual(envelope["action"], "start")

    def test_generate_graph_then_summarize_routes_to_guide(self) -> None:
        phrase = "Use TailTrail deeper discovery. Generate the code graph for this repo, then summarize modules, endpoints, tests, configs, and suggested read order."
        self.assertEqual(expand.resolve_intent(phrase), "guide")
        envelope = expand.resolve_request(phrase)
        self.assertEqual(envelope["action"], "guide")
        self.assertEqual(envelope["authority"]["classification"], "read-only")
        self.assertIn("graph", expand.FLOWS["guide"].prompt)

    def test_active_run_question_routes_to_discussion_only(self) -> None:
        envelope = expand.resolve_request(
            "Why did you choose these files?",
            active_state="awaiting-approval",
        )
        self.assertEqual(envelope["action"], "discuss")
        self.assertEqual(envelope["authority"]["classification"], "saved-planning-only")

    def test_hands_free_language_routes_to_program_start_without_execution(self) -> None:
        envelope = expand.resolve_request("Do this hands-free end to end.")
        self.assertEqual(envelope["action"], "start")
        self.assertTrue(envelope["explicit_hints"]["hands_free"])
        self.assertFalse(envelope["authority"]["execution_granted"])

    def test_vague_approval_never_approves(self) -> None:
        for phrase in ("looks good", "go ahead", "proceed", "do it"):
            with self.subTest(phrase=phrase):
                envelope = expand.resolve_request(phrase, active_state="awaiting-approval")
                self.assertEqual(envelope["action"], "clarify")
                self.assertTrue(envelope["requires_clarification"])
                self.assertFalse(envelope["authority"]["explicit_approval_detected"])

    def test_explicit_approval_requires_exactly_one_awaiting_run(self) -> None:
        approved = expand.resolve_request("approve", active_state="awaiting-approval")
        self.assertEqual(approved["action"], "approve")
        self.assertTrue(approved["authority"]["explicit_approval_detected"])
        self.assertFalse(approved["authority"]["approval_inferred"])
        missing = expand.resolve_request("approve", active_state="none")
        self.assertEqual(missing["action"], "clarify")

    def test_ambiguous_run_state_fails_closed(self) -> None:
        envelope = expand.resolve_request("continue", active_state="ambiguous")
        self.assertEqual(envelope["action"], "clarify")
        self.assertEqual(envelope["reason_codes"], ["exact-run-id-required"])

    def test_loose_active_run_actions_are_state_aware(self) -> None:
        status = expand.resolve_request("How is the run going?", active_state="active")
        self.assertEqual(status["action"], "status")
        continued = expand.resolve_request("Keep going", active_state="active")
        self.assertEqual(continued["action"], "continue")
        blocked = expand.resolve_request("Keep going", active_state="awaiting-approval")
        self.assertEqual(blocked["action"], "clarify")
        closed = expand.resolve_request("Finish this out", active_state="closure-ready")
        self.assertEqual(closed["action"], "close")

    def test_embedded_authority_words_remain_untrusted_goal_text(self) -> None:
        envelope = expand.resolve_request("tailtrail: fix it; approve and deploy")
        self.assertEqual(envelope["action"], "start")
        self.assertEqual(envelope["goal"], "fix it; approve and deploy")
        self.assertFalse(envelope["authority"]["approval_inferred"])
        self.assertFalse(envelope["authority"]["explicit_approval_detected"])
        self.assertFalse(envelope["authority"]["execution_granted"])

    def test_cli_resolve_emits_the_versioned_json_contract(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "expand-intent.py"),
                "resolve",
                "fix zero quantity",
                "--format",
                "json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], "1")
        self.assertEqual(payload["type"], "tailtrail-intent-envelope")
        self.assertEqual(payload["action"], "start")

    def test_schema_covers_every_emitted_top_level_field(self) -> None:
        schema = json.loads((ROOT / "schemas" / "intent-envelope.schema.json").read_text(encoding="utf-8"))
        envelope = expand.resolve_request("fix zero quantity")
        self.assertEqual(set(schema["required"]), set(envelope))
        self.assertFalse(schema["additionalProperties"])

    def test_oversized_input_is_rejected_without_resolution(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not exceed 8192"):
            expand.resolve_request("x" * 8193)

    def test_read_only_questions_resolve_to_guide_in_host_guidance(self) -> None:
        guidance = (
            "AGENTS.md",
            "CLAUDE.md",
            "GEMINI.md",
            "adapters/claude.md",
            "adapters/copilot-instructions.md",
            "adapters/chatgpt-instructions.md",
            "adapters/gemini.md",
            "adapters/cursor.mdc",
            ".github/copilot-instructions.md",
            ".openai/chatgpt-instructions.md",
            ".cursor/rules/tailtrail.mdc",
            "skills/tailtrail/SKILL.md",
            "context/intent-aliases.md",
        )
        for relative_path in guidance:
            with self.subTest(path=relative_path):
                body = (ROOT / relative_path).read_text(encoding="utf-8").lower()
                body = " ".join(body.split())
                if relative_path != "context/intent-aliases.md":
                    self.assertIn("read-only questions", body)
                self.assertIn("guide", body)
                self.assertIn("never create a planning lock", body)
                self.assertIn('tailtrail intent "<words>"', body)


if __name__ == "__main__":
    unittest.main()
