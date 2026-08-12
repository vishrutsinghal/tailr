from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, (ROOT / "scripts").as_posix())

import navigator_core  # noqa: E402
def load_task_start_module():
    path = ROOT / "scripts" / "task-start.py"
    spec = importlib.util.spec_from_file_location("task_start_ui_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_ui_module():
    path = ROOT / "scripts" / "ui-consistency.py"
    spec = importlib.util.spec_from_file_location("ui_consistency_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class UiConsistencyTests(unittest.TestCase):
    def test_ui_signal_detects_goal_and_frontend_paths(self) -> None:
        self.assertTrue(navigator_core.ui_change_requested("update the checkout screen layout", []))
        self.assertTrue(navigator_core.ui_change_requested("fix a label", ["src/components/Checkout.tsx"]))
        self.assertFalse(navigator_core.ui_change_requested("fix payment validation", ["src/payments.py"]))

    def test_start_selects_ui_guardrail_and_preservation_plan(self) -> None:
        task_start = load_task_start_module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report("update the checkout page UI", root, ["src/pages/Checkout.tsx"], "tailtrail")
            rendered = task_start.compact_start_report(report)
        selected = {item["name"] for item in report["guided_delivery"]["selected"]}
        self.assertIn("UI Consistency Guardrail", selected)
        self.assertIn("UI discovery:", rendered)
        self.assertIn("Preserve: Reuse existing components", rendered)
        self.assertIn("Preserve the established UI system", rendered)

    def test_hands_free_ui_plan_makes_preservation_an_approved_requirement(self) -> None:
        task_start = load_task_start_module()
        with tempfile.TemporaryDirectory() as temp:
            report = task_start.build_report("hands-free: add a checkout confirmation screen UI end to end", Path(temp), [], "tailtrail")
        requirements = report["guided_delivery"]["hands_free_program"]["feature_requirements"]
        self.assertTrue(any("Preserve the established UI system" in item["statement"] for item in requirements))

    def test_read_only_discovery_finds_existing_ui_conventions(self) -> None:
        module = load_ui_module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src" / "components").mkdir(parents=True)
            (root / "src" / "pages").mkdir()
            (root / "src" / "styles").mkdir()
            (root / "src" / "components" / "Button.tsx").write_text("export const Button = () => null\n", encoding="utf-8")
            (root / "src" / "pages" / "Checkout.tsx").write_text("export const Checkout = () => null\n", encoding="utf-8")
            (root / "src" / "styles" / "tokens.css").write_text(":root {}\n", encoding="utf-8")
            (root / "package.json").write_text('{"dependencies":{"react":"1","tailwindcss":"1"}}', encoding="utf-8")
            profile = module.discover(root, ["src/pages/Checkout.tsx"])
        self.assertEqual(profile["shared_component_candidates"], ["src/components/Button.tsx"])
        self.assertEqual(profile["similar_screen_candidates"], ["src/pages/Checkout.tsx"])
        self.assertEqual(profile["style_and_token_candidates"], ["src/styles/tokens.css"])
        self.assertEqual(profile["package_evidence"], ["react", "tailwindcss"])


if __name__ == "__main__":
    unittest.main()
