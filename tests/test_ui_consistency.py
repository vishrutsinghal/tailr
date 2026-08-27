from __future__ import annotations

import importlib.util
import json
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

    def test_accessibility_and_preview_do_not_false_route_ci_or_review(self) -> None:
        goal = "Add an accessible JSON preview page. Do not introduce a UI library."
        self.assertNotIn("ci-sonar", navigator_core.task_types(goal))
        self.assertNotIn("review", navigator_core.task_types(goal))
        self.assertNotIn("dependency", navigator_core.task_types(goal))
        self.assertNotIn("ci/sonar", navigator_core.risk_indicators(goal, []))
        self.assertNotIn("dependency", navigator_core.risk_indicators(goal, []))

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

    def test_ui_feature_plan_uses_ui_scope_and_atomic_requirements(self) -> None:
        task_start = load_task_start_module()
        goal = (
            "Add a Validate & Review page for order audit events with a session summary, "
            "validation status, export controls, and an all-events JSON preview. "
            "Discover and reuse the repository's existing layout, spacing, typography, colors, "
            "components, responsive breakpoints, accessibility patterns, and interaction states. "
            "Do not introduce a UI library or redesign unrelated screens."
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "ui").mkdir()
            (root / "tests" / "ui").mkdir(parents=True)
            (root / "src" / "order_service").mkdir(parents=True)
            (root / "ui" / "order-operations.html").write_text("<main></main>\n", encoding="utf-8")
            (root / "ui" / "design-tokens.css").write_text(":root {}\n", encoding="utf-8")
            (root / "ui" / "README.md").write_text("# UI baseline\n", encoding="utf-8")
            (root / "tests" / "ui" / "test_ui_baseline.py").write_text("import unittest\n", encoding="utf-8")
            (root / "src" / "order_service" / "service.py").write_text("def validation_status(): pass\n", encoding="utf-8")
            report = task_start.build_report(goal, root, [], "tailtrail")
            rendered = task_start.verbose_start_report(report)

        statements = [row["statement"] for row in report["navigator"]["requirement_matrix"]]
        impacted = [row["path"] for row in report["navigator"]["likely_impacted_files"]]
        workflow = report["navigator"]["recommended_workflow"]
        self.assertEqual(len(statements), 8)
        self.assertIn("Show session summary on the requested UI.", statements)
        self.assertIn("Provide export controls on the requested UI.", statements)
        self.assertIn("Do not introduce a UI library.", statements)
        self.assertIn("Do not redesign unrelated screens.", statements)
        self.assertIn("ui/order-operations.html", impacted)
        self.assertIn("ui/design-tokens.css", impacted)
        self.assertIn("tests/ui/test_ui_baseline.py", impacted)
        self.assertNotIn("src/order_service/service.py", impacted)
        self.assertNotIn("ci_sonar_intelligence", workflow)
        self.assertNotIn("dependency_review", workflow)
        self.assertNotIn("handoff", workflow)
        self.assertEqual(report["ui_plan"]["surface_status"], "discovered")
        self.assertIn("## UI Consistency Plan", rendered)
        self.assertIn("### Requirement-to-UI contract", rendered)
        self.assertIn("pending, valid, invalid, and failure", rendered)
        self.assertIn("UI behaviour evidence", rendered)
        self.assertNotIn("authoritative transition", rendered)
        self.assertNotIn("tests/ui/__init__.py", rendered)
        self.assertIn("| component | `tests/ui/test_ui_baseline.py` |", rendered)

    def test_ui_plan_does_not_substitute_backend_scope_when_ui_is_absent(self) -> None:
        task_start = load_task_start_module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src" / "order_service").mkdir(parents=True)
            (root / "tests" / "unit").mkdir(parents=True)
            (root / "src" / "order_service" / "service.py").write_text("def validation_status(): pass\n", encoding="utf-8")
            (root / "tests" / "unit" / "test_service.py").write_text("import unittest\n", encoding="utf-8")
            report = task_start.build_report("Add an accessible validation status page", root, [], "tailtrail")
            rendered = task_start.verbose_start_report(report)

        self.assertEqual(report["navigator"]["likely_impacted_files"], [])
        self.assertEqual(report["ui_plan"]["surface_status"], "not-discovered")
        self.assertIn("UI surface not discovered", rendered)
        self.assertIn("backend files were not substituted", rendered.lower())
        self.assertNotIn("src/order_service/service.py", rendered)

    def test_approved_handoff_preserves_requirement_linked_ui_contracts(self) -> None:
        task_start = load_task_start_module()
        goal = "Add a validation status page with a session summary and export controls. Preserve accessibility and responsive behavior."
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "ui").mkdir()
            (root / "tests" / "ui").mkdir(parents=True)
            (root / "ui" / "status.html").write_text("<main></main>\n", encoding="utf-8")
            (root / "tests" / "ui" / "test_status.py").write_text("import unittest\n", encoding="utf-8")
            report = task_start.build_report(goal, root, ["ui/status.html"], "tailtrail")
            report["planning_lock"] = task_start.planning_lock.create(root, goal, "ui-handoff")
            task_start.planning_lock.save_start_report(root, "ui-handoff", report)
            activated = task_start.planning_lock.activate(root, "ui-handoff", True)
            handoff = activated["execution_handoff"]
            approved = json.loads((root / handoff["anchor"]).read_text(encoding="utf-8"))

        self.assertTrue(handoff["ui_plan"]["selected"])
        self.assertTrue(all(row["ui_contract"] for row in handoff["active_requirements"]))
        self.assertEqual(handoff["active_requirements"][0]["ui_contract"], approved["requirements"][0]["ui_contract"])


if __name__ == "__main__":
    unittest.main()
