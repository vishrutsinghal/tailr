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
        self.assertEqual(levels, [str(index) for index in range(1, 14)])
        self.assertEqual(prompts, [str(index) for index in range(1, 39)])

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

    def test_task_scaled_planning_and_verbose_contract_are_rehearsable(self) -> None:
        content = PROMPTS.read_text(encoding="utf-8")
        compact = re.sub(r"\s+", " ", content)
        for scenario in (
            "ask for a safe approach",
            "start a routine fix",
            "start a hands-free program",
            "request complete audit detail",
        ):
            self.assertIn(scenario, content)
        self.assertNotIn("Plan detail:", content)
        self.assertNotIn("--presentation", content)
        self.assertNotIn("--surface", content)
        self.assertIn("--verbose", content)
        self.assertNotIn("tailtrail presentation conformance", compact)

    def test_routine_demo_prompt_is_natural_and_creates_a_real_lock(self) -> None:
        content = PROMPTS.read_text(encoding="utf-8")
        section = content[content.index("### Prompt 4:"):content.index("### Prompt 5:")]
        match = re.search(r"\*\*Example:\*\*\s*```text\s*(.*?)\s*```", section, re.DOTALL)
        self.assertIsNotNone(match)
        prompt = re.sub(r"\s+", " ", match.group(1)).strip()
        self.assertEqual(
            prompt,
            "tailtrail start: reject zero order quantity while preserving positive quantities",
        )
        self.assertIn("persisted Planning Lock", section)
        self.assertIn("inferred validation scope", section)
        self.assertNotIn("--", prompt)
        self.assertNotIn("verify", prompt.lower())

    def test_user_examples_are_compact_and_do_not_contain_presenter_checks(self) -> None:
        content = PROMPTS.read_text(encoding="utf-8")
        examples = re.findall(r"\*\*Example:\*\*\s*```text\s*(.*?)\s*```", content, re.DOTALL)
        self.assertEqual(len(examples), 38)
        forbidden = ("return the complete", "raw stdout", "verify the", "preserve every", "do not add")
        for index, example in enumerate(examples, start=1):
            compact = re.sub(r"\s+", " ", example).strip()
            with self.subTest(prompt=index):
                self.assertLessEqual(len(compact.split()), 32)
                for phrase in forbidden:
                    self.assertNotIn(phrase, compact.lower())

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

    def test_manager_showcase_uses_natural_state_aware_prompts(self) -> None:
        content = PROMPTS.read_text(encoding="utf-8")
        section = content[content.index("## Level 13"):content.index("## Recommended live routes")]
        compact_section = re.sub(r"\s+", " ", section)
        for prompt in (
            "Use TailTrail to reject zero order quantity while preserving positive quantities.",
            "Show me how TailTrail would safely add payment retries before starting any work.",
            "Why did TailTrail choose these files and tests?",
            "Looks good",
        ):
            with self.subTest(prompt=prompt):
                self.assertIn(prompt, section)
        for boundary in (
            "planning-only `start`",
            "No run,",
            "single active run",
            "records no approval or execution authority",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, compact_section)

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
        for boundary in ("never apply the terraform", "do not implement", "fail closed", "real status"):
            self.assertIn(boundary, content)


if __name__ == "__main__":
    unittest.main()
