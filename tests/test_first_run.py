from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path); module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader; sys.modules[name] = module; spec.loader.exec_module(module); return module


first_run = load("first_run_test", "scripts/first-run.py")


class FirstRunTests(unittest.TestCase):
    def test_codex_plugin_check_requires_the_installed_guidance_and_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            for item in first_run.expected("codex-plugin", "tailtrail"):
                path = target / item; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("x", encoding="utf-8")
            result = first_run.check(target, "codex-plugin", "tailtrail")
        self.assertEqual(result["installation"], "passed")
        self.assertIn("Using TailTrail Navigator", result["first_action"]["command"])

    def test_missing_installed_file_is_not_reported_as_a_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = first_run.check(Path(temp), "codex", "tailtrail")
        self.assertEqual(result["installation"], "incomplete")
        self.assertIn("AGENTS.md", result["missing"])
