import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DemoAssetTests(unittest.TestCase):
    def test_heavy_demo_documents_are_present(self) -> None:
        required = (
            "TAILTRAIL-DEMO-PROMPTS.md",
            "DEMO-PLAYBOOK.md",
            "FEATURE-COVERAGE-MATRIX.md",
            "DEBUG-FEATURE-DEMO.md",
            "test-scenarios/aidlc-all-modes-heavy.md",
            "test-scenarios/all-harnesses-returns-program.md",
            "test-scenarios/interactive-plan-and-aidlc.md",
            "test-scenarios/intent-bridge.md",
            "test-scenarios/durable-workflow-runtime.md",
            "test-scenarios/ui-consistency-heavy.md",
            "test-scenarios/mcp-host-enterprise.md",
            "test-scenarios/evidence-token-learning.md",
            "test-scenarios/debug-harness-native.md",
            "test-scenarios/product-maturity-learning-adoption.md",
            "test-scenarios/fixtures/debug-reproduction.example.json",
            "test-scenarios/fixtures/debug-correction.example.json",
            "debug_lab/retry_race.py",
            "debug_lab/run_duplicate_effect_failure.py",
        )
        for relative in required:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file())

    def test_root_prompt_book_matches_current_daily_product(self) -> None:
        content = re.sub(r"\s+", " ", (ROOT / "TAILTRAIL-DEMO-PROMPTS.md").read_text(encoding="utf-8"))
        required_terms = (
            "tailtrail discuss --question",
            "tailtrail approve",
            "tailtrail continue",
            "tailtrail flow status",
            "tailtrail close",
            "--presentation quick",
            "--presentation guided",
            "--presentation expert",
            "--verbose",
            "Requirement Completion",
            "Architecture Fitness",
            "Behaviour Harness",
            "Maintainability Harness",
            "Context Continuity",
            "Program Delivery",
            "Evidence-Aware Testing",
            "Higher-Tier Testing",
            "Token Harness",
            "Evaluation Harness",
            "Meta-Harness",
            "Safe Git Recovery",
            "Intent Bridge",
            "Durable Workflow Runtime",
            "Completion Report",
            "MCP",
            "Learning V3",
            "Adoption Validation",
        )
        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, content)

    def test_every_demo_level_and_prompt_explains_its_utility(self) -> None:
        content = (ROOT / "TAILTRAIL-DEMO-PROMPTS.md").read_text(encoding="utf-8")
        levels = list(re.finditer(r"^## Level (\d+) — .+$", content, re.MULTILINE))
        prompts = list(re.finditer(r"^### Prompt (\d+): .+$", content, re.MULTILINE))
        self.assertEqual([str(index) for index in range(1, 13)], [match.group(1) for match in levels])
        self.assertEqual([str(index) for index in range(1, 35)], [match.group(1) for match in prompts])
        for index, match in enumerate(levels):
            end = levels[index + 1].start() if index + 1 < len(levels) else len(content)
            section = content[match.end():end]
            with self.subTest(level=match.group(1)):
                self.assertIn("**Level purpose:**", section)
                self.assertIn("**What this teaches:**", section)
        for index, match in enumerate(prompts):
            end = prompts[index + 1].start() if index + 1 < len(prompts) else len(content)
            section = content[match.end():end]
            with self.subTest(prompt=match.group(1)):
                self.assertIn("**Purpose:**", section)
                self.assertIn("**Why it helps:**", section)
                self.assertIn("**Example:**", section)

    def test_normal_flow_omits_run_id_but_ambiguity_rule_is_explicit(self) -> None:
        content = (ROOT / "TAILTRAIL-DEMO-PROMPTS.md").read_text(encoding="utf-8")
        self.assertIn("automatically resolves the active run", content)
        self.assertIn("multiple eligible runs", content)
        self.assertIn("--run-id <exact-id>", content)
        self.assertNotIn("tailtrail approve --run-id <run-id>", content)
        self.assertNotIn("tailtrail continue --run-id <run-id>", content)

    def test_demo_prompts_forbid_terraform_apply(self) -> None:
        paths = (ROOT / "TAILTRAIL-DEMO-PROMPTS.md", *(ROOT / "test-scenarios").glob("*.md"))
        for path in paths:
            content = path.read_text(encoding="utf-8").lower()
            with self.subTest(path=path.name):
                self.assertNotIn("run terraform apply", content)

    def test_debug_harness_track_covers_the_native_lifecycle(self) -> None:
        content = (ROOT / "test-scenarios" / "debug-harness-native.md").read_text(encoding="utf-8")
        for term in (
            "Debug Planning Lock", "Reproduction approval", "Durable state, resume, and replay",
            "Project orientation and Code Graph freshness", "Falsifiable hypotheses",
            "Bounded experiment", "Root-cause proof", "Correction proposal",
            "Harness convergence", "Privacy, continuity, token posture, and learning",
            "MCP and three-host parity", "Deterministic evaluation and fail-closed release",
        ):
            with self.subTest(term=term):
                self.assertIn(term, content)

    def test_debug_lab_reproduces_the_documented_duplicate_effect(self) -> None:
        from debug_lab.retry_race import AmbiguousPaymentGateway, RecordingNotifier, submit_with_faulty_retry
        from decimal import Decimal

        gateway = AmbiguousPaymentGateway()
        notifier = RecordingNotifier()
        submit_with_faulty_retry("order-debug-test", Decimal("10.00"), gateway, notifier)
        self.assertEqual(2, len(gateway.charges))
        self.assertEqual(2, len(notifier.messages))

    def test_demo_assets_use_current_launcher_contract(self) -> None:
        content = (ROOT / "TAILTRAIL-DEMO-PROMPTS.md").read_text(encoding="utf-8")
        self.assertNotIn(r"tailtrail\scripts\tailtrail.py", content)
        self.assertIn("tailtrail start", content)
        self.assertIn("tailtrail flow status", content)


if __name__ == "__main__":
    unittest.main()
