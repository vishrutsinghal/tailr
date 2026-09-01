from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HelloEntrypointTests(unittest.TestCase):
    def test_hello_surfaces_require_the_complete_verbatim_command_response(self) -> None:
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
            "demo-project-layout/tailtrail-demo-workspace/.github/copilot-instructions.md",
            "demo-project-layout/tailtrail-demo-workspace/tailtrail/AGENTS.md",
            "demo-project-layout/tailtrail-demo-workspace/tailtrail/adapters/claude.md",
            "demo-project-layout/tailtrail-demo-workspace/tailtrail/adapters/copilot-instructions.md",
            "demo-project-layout/tailtrail-demo-workspace/tailtrail/adapters/chatgpt-instructions.md",
            "demo-project-layout/tailtrail-demo-workspace/tailtrail/adapters/gemini.md",
            "demo-project-layout/tailtrail-demo-workspace/tailtrail/adapters/cursor.mdc",
        )
        for relative_path in guidance:
            with self.subTest(path=relative_path):
                body = (ROOT / relative_path).read_text(encoding="utf-8").lower()
                body = re.sub(r"\s+", " ", body)
                self.assertIn("ascii tailtrail banner", body)
                self.assertIn("verbatim as the complete response", body)
                self.assertIn("preserve the command-emitted `text` fence", body)
                self.assertIn("todo/status update", body)
                self.assertIn("suggest `doctor` after it", body)


if __name__ == "__main__":
    unittest.main()
