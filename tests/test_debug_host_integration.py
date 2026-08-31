from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DebugHostIntegrationTests(unittest.TestCase):
    def test_codex_copilot_and_claude_publish_the_same_debug_contract(self) -> None:
        files = [ROOT / "AGENTS.md", ROOT / ".github" / "copilot-instructions.md", ROOT / "CLAUDE.md"]
        blocks = []
        for path in files:
            text = path.read_text(encoding="utf-8")
            start = text.index("<!-- tailtrail-debug-host:start -->")
            end = text.index("<!-- tailtrail-debug-host:end -->") + len("<!-- tailtrail-debug-host:end -->")
            blocks.append(text[start:end])
        self.assertEqual(blocks[0], blocks[1])
        self.assertEqual(blocks[0], blocks[2])
        for phrase in ("same run, workflow, and requirement IDs", "experiment proposal",
                       "root-cause proof", "canonical closure finalize", "MCP operations only record"):
            self.assertIn(phrase, blocks[0])

    def test_extended_pack_contains_debug_runtime_schemas_and_host_surfaces(self) -> None:
        installer = (ROOT / "scripts" / "install-copilot.py").read_text(encoding="utf-8")
        for value in ("scripts/debug-reproduction.py", "scripts/debug-hypothesis.py",
                      "scripts/debug-correction.py", "scripts/closure-finalizer.py"):
            self.assertIn(value, installer)
        self.assertTrue((ROOT / "schemas" / "debug-experiment-proposal.schema.json").is_file())
        self.assertTrue((ROOT / "schemas" / "debug-hypothesis-ranking.schema.json").is_file())


if __name__ == "__main__":
    unittest.main()
