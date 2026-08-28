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


behaviour = load("tailtrail_behaviour_planning_test", "scripts/behaviour_planning.py")
architecture = load("tailtrail_behaviour_architecture_test", "scripts/architecture_planning.py")
task_start = load("tailtrail_behaviour_start_test", "scripts/task-start.py")
behavior_harness = load("tailtrail_behaviour_assessor_test", "scripts/behavior-harness.py")


GOAL = (
    "Add a customer-visible order-status journey from order creation through allocation and shipment. "
    "Preserve existing API responses, publish no duplicate notification, and prove the journey with "
    "behaviour and integration evidence instead of relying only on unit tests."
)


def project(root: Path) -> None:
    files = (
        "src/order_service/api.py",
        "src/order_service/service.py",
        "src/order_service/repository.py",
        "src/order_service/inventory.py",
        "src/order_service/shipping.py",
        "src/order_service/notifications.py",
        "tests/behaviour/test_customer_journey.py",
        "tests/integration/test_order_service.py",
        "tests/contract/test_api_contract.py",
        "pyproject.toml",
    )
    for relative in files:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        body = "import unittest\n" if path.name.startswith("test_") else ""
        path.write_text(body, encoding="utf-8")


class BehaviourPlanningTests(unittest.TestCase):
    def test_cross_layer_customer_journey_adds_existing_integration_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "tests" / "integration" / "test_service.py"
            path.parent.mkdir(parents=True)
            path.write_text("", encoding="utf-8")
            expanded = behaviour.add_role_candidates(
                root,
                "Add validation across the API, service, and customer journey.",
                [],
                True,
            )

        self.assertIn("tests/integration/test_service.py", {item["path"] for item in expanded})

    def test_start_builds_behaviour_contract_scope_and_required_tiers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); project(root)
            report = task_start.build_report(
                GOAL,
                root,
                ["src/order_service/api.py", "tests/behaviour/test_customer_journey.py"],
                "tailtrail",
            )
            rendered = task_start.verbose_start_report(report)

        statements = [row["statement"] for row in report["navigator"]["requirement_matrix"]]
        self.assertEqual(len(statements), 4)
        self.assertTrue(any(statement.startswith("Publish no duplicate notification") for statement in statements))
        self.assertTrue(any(statement.startswith("Prove the journey") for statement in statements))
        paths = {row["path"] for row in report["navigator"]["likely_impacted_files"]}
        self.assertNotIn("pyproject.toml", paths)
        self.assertTrue({
            "src/order_service/service.py",
            "src/order_service/repository.py",
            "src/order_service/notifications.py",
            "src/order_service/shipping.py",
            "tests/integration/test_order_service.py",
            "tests/contract/test_api_contract.py",
        }.issubset(paths))
        self.assertIn("## Behaviour Harness Plan", rendered)
        self.assertIn("BHV-01", {row["scenario_id"] for row in report["behaviour_plan"]["scenarios"]})
        self.assertIn("BHV-03", {row["scenario_id"] for row in report["behaviour_plan"]["scenarios"]})
        self.assertIn("| behaviour | `tests/behaviour/test_customer_journey.py` |", rendered)
        self.assertIn("| integration | `tests/integration/test_order_service.py` |", rendered)
        self.assertIn("| contract | `tests/contract/test_api_contract.py` |", rendered)
        self.assertNotIn("| unit |", rendered)
        self.assertNotIn("retry boundary", rendered.lower())
        self.assertNotIn("payment/service path", rendered.lower())

    def test_approved_handoff_preserves_behaviour_scenarios(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); project(root)
            report = task_start.build_report(GOAL, root, ["src/order_service/api.py"], "tailtrail")
            report["planning_lock"] = task_start.planning_lock.create(root, GOAL, "behaviour-handoff")
            task_start.planning_lock.save_start_report(root, "behaviour-handoff", report)
            activated = task_start.planning_lock.activate(root, "behaviour-handoff", True)
            handoff = activated["execution_handoff"]
            approved = json.loads((root / handoff["anchor"]).read_text(encoding="utf-8"))

        self.assertTrue(handoff["behaviour_plan"]["selected"])
        self.assertTrue(any(row["behavior_contract"].get("scenarios") for row in handoff["active_requirements"]))
        self.assertEqual(
            handoff["active_requirements"][0]["behavior_contract"],
            approved["requirements"][0]["behavior_contract"],
        )

    def test_generated_contract_is_consumable_by_behaviour_assessor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); project(root)
            report = task_start.build_report(GOAL, root, ["src/order_service/api.py"], "tailtrail")
            report["planning_lock"] = task_start.planning_lock.create(root, GOAL, "behaviour-e2e")
            task_start.planning_lock.save_start_report(root, "behaviour-e2e", report)
            activated = task_start.planning_lock.activate(root, "behaviour-e2e", True)
            approved = json.loads((root / activated["execution_handoff"]["anchor"]).read_text(encoding="utf-8"))
            scenarios = []
            receipts = []
            for requirement in approved["requirements"]:
                for scenario in requirement["behavior_contract"].get("scenarios", []):
                    linked = {"requirement_uid": requirement["requirement_uid"], **scenario}
                    scenarios.append(linked)
                    receipts.extend({
                        "requirement_uid": requirement["requirement_uid"],
                        "tier": item["tier"],
                        "outcome": "pass",
                        "asserted_behavior": item["asserted_behavior"],
                    } for item in scenario["evidence"])
            scenarios_path = root / "scenarios.json"; evidence_path = root / "evidence.json"
            scenarios_path.write_text(json.dumps({"scenarios": scenarios}), encoding="utf-8")
            evidence_path.write_text(json.dumps({"receipts": receipts}), encoding="utf-8")
            result = behavior_harness.assess(root, "behaviour-e2e", scenarios_path, evidence_path)

        self.assertTrue(result["complete"])
        self.assertTrue(result["scenarios"])
        self.assertTrue(all(row["state"] == "validated" for row in result["scenarios"]))

    def test_architecture_relevance_check_rejects_foreign_domain_terms(self) -> None:
        with self.assertRaisesRegex(ValueError, "foreign domain terms: retry"):
            architecture._assert_relevant(
                "Add a customer-visible status journey.",
                [{"path": "src/orders/api.py"}],
                {"invariants": [{"invariant": "Keep the retry boundary unchanged."}]},
            )

    def test_refactor_preservation_does_not_invent_api_or_notification_delivery(self) -> None:
        goal = (
            "Refactor duplicate payment and notification orchestration. Preserve all public behaviour and tests, "
            "avoid speculative abstractions, and show reduced duplication without expanding unrelated scope."
        )
        requirements = [{"display_id": "REQ-01", "statement": "Preserve all public behaviour."}]
        plan = behaviour.build(goal, [{"path": "src/order_service/service.py", "reason": "goal-matched target"}], requirements, True)
        rendered = "\n".join(behaviour.markdown_lines(plan, detailed=True))
        self.assertIn("affected existing public behaviour", rendered)
        self.assertNotIn("existing API response", rendered)
        self.assertNotIn("Replay or retry", rendered)
        self.assertEqual(["behaviour", "integration"], plan["required_tiers"])


if __name__ == "__main__":
    unittest.main()
