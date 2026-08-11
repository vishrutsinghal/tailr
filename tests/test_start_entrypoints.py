from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StartEntrypointTests(unittest.TestCase):
    def test_host_command_assets_describe_the_atomic_start_boundary(self) -> None:
        assets = (
            ROOT / ".github" / "prompts" / "tailtrail-start.prompt.md",
            ROOT / ".claude" / "commands" / "tailtrail-start.md",
            ROOT / "skills" / "tailtrail-start" / "SKILL.md",
        )
        for path in assets:
            with self.subTest(path=path):
                body = path.read_text(encoding="utf-8")
                self.assertIn("Planning Lock", body)
                self.assertIn("Do not", body)

    def test_copilot_pack_and_codex_payload_include_start_entrypoints(self) -> None:
        install_copilot = (ROOT / "scripts" / "install-copilot.py").read_text(encoding="utf-8")
        install_local = (ROOT / "scripts" / "install-local.py").read_text(encoding="utf-8")
        self.assertIn(".github/prompts/tailtrail-start.prompt.md", install_copilot)
        self.assertIn("start_prompt_body", install_copilot)
        self.assertIn("skills/tailtrail-start/SKILL.md", install_local)

    def test_stop_rule_is_consistent_across_host_guidance(self) -> None:
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
            "skills/tailtrail-start/SKILL.md",
            ".claude/commands/tailtrail-start.md",
        )
        for relative_path in guidance:
            with self.subTest(path=relative_path):
                body = (ROOT / relative_path).read_text(encoding="utf-8").lower()
                self.assertIn("complete start report verbatim", body)
                self.assertIn("collapsible terminal/tool-result panel", body)

    def test_start_trigger_is_limited_to_the_current_user_message(self) -> None:
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
            "skills/tailtrail-start/SKILL.md",
            ".claude/commands/tailtrail-start.md",
            ".github/prompts/tailtrail-start.prompt.md",
        )
        for relative_path in guidance:
            with self.subTest(path=relative_path):
                body = (ROOT / relative_path).read_text(encoding="utf-8").lower()
                self.assertIn("current user message", body)
                self.assertIn("error output", body)
                self.assertIn("new planning lock", body)

    def test_copilot_resolves_installed_pack_before_declaring_start_unavailable(self) -> None:
        body = (ROOT / "adapters" / "copilot-instructions.md").read_text(encoding="utf-8")
        self.assertIn("tailtrail/scripts/tailtrail.py", body)
        self.assertIn("scripts/tailtrail.py", body)
        self.assertIn("before saying TailTrail Start cannot run", body)
        self.assertIn("substitute a manual plan", body)

    def test_copilot_forbids_a_synthesized_start_task_list(self) -> None:
        for relative_path in (
            "adapters/copilot-instructions.md",
            ".github/prompts/tailtrail-start.prompt.md",
            "skills/tailtrail-start/SKILL.md",
        ):
            with self.subTest(path=relative_path):
                body = (ROOT / relative_path).read_text(encoding="utf-8")
                self.assertIn("Never synthesize a substitute plan or task list", body)
                self.assertIn("# TailTrail Start Plan", body)
                self.assertIn("complete Start Report verbatim", body)
                self.assertIn("Selected TailTrail features", body)
                self.assertIn("replace it with `Next step`", body)

    def test_implicit_navigator_routing_does_not_recommend_start(self) -> None:
        body = (ROOT / "skills" / "tailtrail" / "SKILL.md").read_text(encoding="utf-8")
        implicit_section = body.split("For an explicit Navigator request", 1)[0]
        self.assertNotIn('python3 scripts/tailtrail.py start "user goal"', implicit_section)

    def test_rejected_start_has_a_no_inspection_feedback_route(self) -> None:
        for relative_path in (
            "adapters/copilot-instructions.md",
            ".github/prompts/tailtrail-start.prompt.md",
            "skills/tailtrail-start/SKILL.md",
            "AGENTS.md",
        ):
            with self.subTest(path=relative_path):
                body = (ROOT / relative_path).read_text(encoding="utf-8")
                self.assertIn("feedback-template", body)
                self.assertIn("do not inspect", body.lower().replace("**", ""))
                self.assertIn("AIDLC Requirements mode", body)

    def test_activated_run_requires_the_saved_completion_handoff(self) -> None:
        for relative_path in (
            "AGENTS.md",
            "adapters/copilot-instructions.md",
            ".github/copilot-instructions.md",
            ".github/prompts/tailtrail-start.prompt.md",
            "skills/tailtrail-start/SKILL.md",
        ):
            with self.subTest(path=relative_path):
                body = (ROOT / relative_path).read_text(encoding="utf-8")
                self.assertIn("execution_handoff", body)
                self.assertIn("closure.command", body)
                self.assertIn("generic", body.lower())


if __name__ == "__main__":
    unittest.main()
