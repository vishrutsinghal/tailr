from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


architecture = load("tailtrail_architecture_planning_test", "scripts/architecture_planning.py")
task_start = load("tailtrail_architecture_start_test", "scripts/task-start.py")


GOAL = (
    "Add idempotent payment retry handling to order submission. "
    "Reuse the existing payment adapter, preserve successful create-order behaviour, "
    "map every service and API caller, and add focused unit and integration proof. "
    "Do not add a dependency or a second payment abstraction."
)


class ArchitecturePlanningTests(unittest.TestCase):
    def test_explicit_validation_adds_existing_boundary_and_focused_unit_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for relative in ("src/orders/validation.py", "tests/unit/test_validation.py"):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")
            expanded = architecture.add_explicit_role_candidates(
                root,
                "Add validation across the service and gather focused evidence.",
                [],
            )

        paths = {item["path"] for item in expanded}
        self.assertEqual(paths, {"src/orders/validation.py", "tests/unit/test_validation.py"})
        self.assertEqual(architecture.role("src/orders/validation.py"), "validation boundary")

    def test_filters_unrelated_spec_and_adds_explicit_api_role(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            api = root / "src" / "order_service" / "api.py"
            api.parent.mkdir(parents=True); api.write_text("", encoding="utf-8")
            impacted = [
                {"path": "src/order_service/payments.py", "reason": "goal-matched target"},
                {"path": "specs/014-order-amendment/tasks.md", "reason": "suggested by Code Review Graph Lite"},
            ]
            filtered = architecture.filter_weak_suggestions(GOAL, impacted)
            expanded = architecture.add_explicit_role_candidates(root, GOAL, filtered)

        paths = [item["path"] for item in expanded]
        self.assertNotIn("specs/014-order-amendment/tasks.md", paths)
        self.assertIn("src/order_service/api.py", paths)
        self.assertEqual(architecture.role("src/order_service/api.py"), "interface boundary")

    def test_start_renders_requirement_linked_architecture_contract_and_validation_tiers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for relative, body in (
                ("src/order_service/payments.py", ""),
                ("src/order_service/service.py", ""),
                ("src/order_service/api.py", ""),
                ("tests/integration/test_order_service.py", "import unittest\n"),
            ):
                path = root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(body, encoding="utf-8")
            report = task_start.build_report(
                GOAL,
                root,
                ["src/order_service/payments.py", "src/order_service/service.py", "tests/integration/test_order_service.py"],
                "tailtrail",
            )
            rendered = task_start.verbose_start_report(report)

        statements = [row["statement"] for row in report["navigator"]["requirement_matrix"]]
        self.assertTrue(any(statement.startswith("Map every service") for statement in statements))
        self.assertIn("## Architecture Fitness Plan", rendered)
        self.assertIn("Retries must not duplicate payment", rendered)
        self.assertIn("Architecture scope roles", rendered)
        self.assertIn("`src/order_service/api.py`", rendered)
        self.assertIn("| unit | `not resolved from planning evidence` | must be discovered after approval |", rendered)
        self.assertIn("tests/integration/test_order_service.py", rendered)
        contracts = [row["architecture_contract"] for row in report["navigator"]["requirement_matrix"]]
        self.assertTrue(any(contract.get("invariants") for contract in contracts))
        self.assertTrue(any(contract.get("no_new_dependencies") for contract in contracts))

    def test_approved_handoff_preserves_architecture_steering_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for relative in ("src/payments.py", "src/service.py"):
                path = root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("", encoding="utf-8")
            report = task_start.build_report(GOAL, root, ["src/payments.py", "src/service.py"], "tailtrail")
            report["planning_lock"] = task_start.planning_lock.create(root, GOAL, "architecture-handoff")
            task_start.planning_lock.save_start_report(root, "architecture-handoff", report)
            activated = task_start.planning_lock.activate(root, "architecture-handoff", True)
            handoff = activated["execution_handoff"]
            approved = json.loads((root / handoff["anchor"]).read_text(encoding="utf-8"))

        self.assertTrue(handoff["architecture_plan"]["selected"])
        self.assertTrue(any(row["architecture_contract"].get("invariants") for row in handoff["active_requirements"]))
        self.assertEqual(
            handoff["active_requirements"][0]["architecture_contract"],
            approved["requirements"][0]["architecture_contract"],
        )


if __name__ == "__main__":
    unittest.main()
