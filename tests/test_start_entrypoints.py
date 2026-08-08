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
                self.assertIn("start report verbatim and stop", body)

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

    def test_implicit_navigator_routing_does_not_recommend_start(self) -> None:
        body = (ROOT / "skills" / "tailtrail" / "SKILL.md").read_text(encoding="utf-8")
        implicit_section = body.split("For an explicit Navigator request", 1)[0]
        self.assertNotIn('python3 scripts/tailtrail.py start "user goal"', implicit_section)


if __name__ == "__main__":
    unittest.main()
