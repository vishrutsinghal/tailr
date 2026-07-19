from __future__ import annotations

import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

WRAPPER_PAIRS = {
    "scripts/context-receipt.py": "context_receipt",
    "scripts/prompt-profile.py": "prompt_profile",
    "scripts/token-budget-coach.py": "token_budget_coach",
    "scripts/token-telemetry.py": "token_telemetry",
}

USER_FACING_DOCS = (
    "README.md",
    "QUICKSTART.md",
    "TAILTRAIL-COMMANDS.md",
    "USER-GUIDE.md",
    "USEFUL-PROMPTS.md",
    "demo-project-layout/tailtrail-demo-workspace/tailtrail/USER-GUIDE.md",
)

TAILTRAIL_DISPATCH = {
    "budget": "token-budget-coach.py",
    "profile": "prompt-profile.py",
    "receipt": "context-receipt.py",
    "telemetry": "token-telemetry.py",
    "token-harness": "token-harness.py",
}


class CliDispatchTests(unittest.TestCase):
    def test_hyphen_wrappers_delegate_to_importable_modules(self) -> None:
        for wrapper, module in WRAPPER_PAIRS.items():
            with self.subTest(wrapper=wrapper):
                tree = ast.parse((ROOT / wrapper).read_text(encoding="utf-8"))
                imports = [node for node in tree.body if isinstance(node, ast.ImportFrom) and node.module == module]
                self.assertEqual(len(imports), 1)
                self.assertEqual([alias.name for alias in imports[0].names], ["main"])
                comments = (ROOT / wrapper).read_text(encoding="utf-8")
                self.assertIn("Thin CLI wrapper", comments)
                function_defs = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
                self.assertEqual(function_defs, [], f"{wrapper} should stay a thin CLI wrapper")

    def test_tailtrail_dispatch_uses_public_hyphenated_wrappers(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        for command, wrapper in TAILTRAIL_DISPATCH.items():
            with self.subTest(command=command):
                self.assertIn(f'if command == "{command}":', body)
                self.assertIn(f'return run_script("{wrapper}", args)', body)

    def test_user_facing_docs_do_not_advertise_importable_module_paths(self) -> None:
        for doc in USER_FACING_DOCS:
            with self.subTest(doc=doc):
                body = (ROOT / doc).read_text(encoding="utf-8")
                self.assertNotIn("scripts/context_receipt.py", body)
                self.assertNotIn("scripts/prompt_profile.py", body)
                self.assertNotIn("scripts/token_budget_coach.py", body)
                self.assertNotIn("scripts/token_telemetry.py", body)

    def test_do_alias_routes_to_start(self) -> None:
        result = subprocess.run(
            [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "do", "fix validation bug", "--format", "json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["goal"], "fix validation bug")
        self.assertIn("navigator", report)
        self.assertEqual(report["next_step"], "Review the plan, choose one next action, then approve or edit before implementation.")

    def test_free_form_task_routes_to_start(self) -> None:
        result = subprocess.run(
            [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "fix", "validation", "bug", "--format", "json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["goal"], "fix validation bug")
        self.assertIn("navigator", report)
        self.assertEqual(report["next_step"], "Review the plan, choose one next action, then approve or edit before implementation.")

    def test_known_review_command_still_dispatches_directly(self) -> None:
        result = subprocess.run(
            [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "review", "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--scope", result.stdout)

    def test_adapters_check_dispatches_to_contract_check(self) -> None:
        result = subprocess.run(
            [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "adapters", "check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Adapter sync passed.", result.stdout)


if __name__ == "__main__":
    unittest.main()
