from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Core-shrink budget: host instruction files stay short so models read them.
# Detail lives behind invokable pointers (intent expander, TAILTRAIL-COMMANDS.md,
# GUARDRAILS.md, AIDLC.md, DEBUG-HARNESS.md), not inline.
LINE_BUDGET = 85

BUDGETED_FILES = (
    "AGENTS.md",
    "adapters/claude.md",
    "adapters/copilot-instructions.md",
    "adapters/chatgpt-instructions.md",
    "adapters/cursor.mdc",
    "adapters/gemini.md",
    "skills/tailtrail/SKILL.md",
    "skills/tailtrail-start/SKILL.md",
)

# Every budgeted file must keep the hard-rule contract phrases inline.
# Pointers carry the detail; these phrases are the non-skimmable core.
REQUIRED_PHRASES = (
    "Navigator-first",
    "approval before implementation",
    "tailtrail start",
    "tailtrail stop",
    "Natural TailTrail requests",
    "Scope evidence v2 host boundary",
    "post-change review",
    "scanner approval",
    "learnings as advisory",
    "estimated unless measured telemetry",
    "heuristic, local-ast, provider-backed, measured/validated",
    "tailtrail-policy.md",
    "complete Start Report verbatim",
    "collapsible terminal/tool-result panel",
    "current user message",
    'tailtrail intent "<words>"',
    "never create a Planning Lock",
    "requirement_artifact",
    "before Planning Lock persistence",
    "feedback-template",
    "execution_handoff",
    "approved-plan-auto-grant",
    "do not split",
    "CLI fallback",
    "not persisted",
    "quote the `TailTrail instructions revision`",
    "paste the stdout again",
)


class InstructionBudgetTests(unittest.TestCase):
    def test_core_instruction_files_stay_under_line_budget(self) -> None:
        for relative in BUDGETED_FILES:
            with self.subTest(path=relative):
                lines = (ROOT / relative).read_text(encoding="utf-8").splitlines()
                self.assertLessEqual(
                    len(lines),
                    LINE_BUDGET,
                    f"{relative} has {len(lines)} lines (budget {LINE_BUDGET}); "
                    "move detail behind pointers instead of growing the core",
                )

    def test_shrunk_core_keeps_hard_rule_contract(self) -> None:
        for relative in BUDGETED_FILES:
            with self.subTest(path=relative):
                body = (ROOT / relative).read_text(encoding="utf-8")
                lowered = body.lower()
                for phrase in REQUIRED_PHRASES:
                    self.assertIn(
                        phrase.lower(),
                        lowered,
                        f"{relative} lost hard-rule phrase: {phrase}",
                    )

    def test_shrunk_core_points_to_layered_detail(self) -> None:
        pointers = (
            "TAILTRAIL-COMMANDS.md",
            "GUARDRAILS.md",
            "AIDLC.md",
            "DEBUG-HARNESS.md",
            "intent-aliases.md",
        )
        for relative in BUDGETED_FILES:
            with self.subTest(path=relative):
                body = (ROOT / relative).read_text(encoding="utf-8")
                for pointer in pointers:
                    self.assertIn(pointer, body, f"{relative} missing pointer: {pointer}")

    def test_mcp_is_default_path_with_cli_fallback(self) -> None:
        for relative in BUDGETED_FILES:
            with self.subTest(path=relative):
                body = (ROOT / relative).read_text(encoding="utf-8")
                mcp_pos = body.lower().find("tailtrail_start")
                self.assertGreaterEqual(mcp_pos, 0, f"{relative} missing MCP default path")
                self.assertIn("CLI fallback", body, f"{relative} missing CLI fallback tier")

    def test_all_entrypoint_files_carry_a_fresh_revision_stamp(self) -> None:
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location(
            "tailtrail_sync_governance_budget",
            ROOT / "scripts" / "sync-governance.py",
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        stamped = (
            "AGENTS.md",
            "CLAUDE.md",
            "GEMINI.md",
            "adapters/claude.md",
            "adapters/copilot-instructions.md",
            "adapters/chatgpt-instructions.md",
            "adapters/cursor.mdc",
            "adapters/gemini.md",
            "skills/tailtrail/SKILL.md",
            "skills/tailtrail-start/SKILL.md",
            ".claude/commands/tailtrail-start.md",
            ".github/prompts/tailtrail-start.prompt.md",
        )
        for relative in stamped:
            with self.subTest(path=relative):
                path = ROOT / relative
                self.assertTrue(path.is_file(), f"{relative} is missing")
                self.assertEqual(
                    module.stamp_status(path),
                    "ok",
                    f"{relative} stamp is missing or stale; run sync-governance stamp",
                )


if __name__ == "__main__":
    unittest.main()
