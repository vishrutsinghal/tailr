from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "examples" / "tailtrail-test-lab" / "TAILTRAIL-DEMO-PROMPTS.md"


class DemoPromptBookTests(unittest.TestCase):
    def test_book_has_ordered_full_capability_progression(self) -> None:
        content = PROMPTS.read_text(encoding="utf-8")
        levels = re.findall(r"^## Level (\d+) —", content, re.MULTILINE)
        prompts = re.findall(r"^### Prompt (\d+):", content, re.MULTILINE)
        self.assertEqual(levels, [str(index) for index in range(1, 13)])
        self.assertEqual(prompts, [str(index) for index in range(1, 35)])

    def test_normal_flow_is_auto_resolved_and_status_is_unambiguous(self) -> None:
        content = PROMPTS.read_text(encoding="utf-8")
        for command in (
            "tailtrail discuss --question",
            "tailtrail approve",
            "tailtrail continue",
            "tailtrail flow status",
            "tailtrail close",
        ):
            self.assertIn(command, content)
        self.assertIn("automatically resolves the active run", content)
        self.assertIn("multiple eligible runs", content)

    def test_three_presentation_layers_and_verbose_contract_are_rehearsable(self) -> None:
        content = PROMPTS.read_text(encoding="utf-8")
        for mode in ("quick", "guided", "expert"):
            self.assertIn(f"--presentation {mode}", content)
        self.assertIn("--verbose", content)
        self.assertIn("tailtrail presentation conformance", content)
        self.assertIn("--no-planning-lock", content)

    def test_major_current_capabilities_are_named(self) -> None:
        content = re.sub(r"\s+", " ", PROMPTS.read_text(encoding="utf-8"))
        required = (
            "Requirement Completion", "Architecture Fitness", "Behaviour Harness",
            "Maintainability Harness", "Context Continuity", "Program Delivery",
            "Evidence-Aware Testing", "Higher-Tier Testing", "Token Harness",
            "Evaluation Harness", "Meta-Harness", "Safe Git Recovery", "Intent Bridge",
            "Durable Workflow Runtime", "Completion Report", "MCP", "Learning V3",
            "Adoption Validation", "Debug Harness", "negative assurance",
            "repository enforcement", "enterprise conformance",
        )
        for term in required:
            with self.subTest(term=term):
                self.assertIn(term, content)

    def test_every_prompt_explains_purpose_value_and_copyable_example(self) -> None:
        content = PROMPTS.read_text(encoding="utf-8")
        matches = list(re.finditer(r"^### Prompt (\d+): .+$", content, re.MULTILINE))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else content.index("## Recommended live routes")
            section = content[match.end():end]
            with self.subTest(prompt=match.group(1)):
                self.assertIn("**Purpose:**", section)
                self.assertIn("**Why it helps:**", section)
                self.assertIn("**Example:**", section)

    def test_demo_safety_boundaries_are_explicit(self) -> None:
        content = re.sub(r"\s+", " ", PROMPTS.read_text(encoding="utf-8").lower())
        self.assertNotIn("run terraform apply", content)
        for boundary in ("do not apply terraform", "do not implement", "fail closed", "real exit codes"):
            self.assertIn(boundary, content)


if __name__ == "__main__":
    unittest.main()
