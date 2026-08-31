from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from workflow_runtime import adapter_catalog, templates


FIXTURES = ROOT / "tests" / "fixtures" / "workflow_runtime" / "templates"


class WorkflowTemplateTests(unittest.TestCase):
    def test_fixtures_select_exact_deterministic_acyclic_graphs(self) -> None:
        files = sorted(FIXTURES.glob("*.json"))
        self.assertEqual(len(files), 7)
        self.assertEqual({path.stem for path in files}, set(templates.TEMPLATES))
        for path in files:
            fixture = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(template=fixture["template_id"]):
                selected = templates.select_template(set(fixture["feature_ids"]))
                resolved = templates.resolve_graph(templates.merge_stages(templates.TEMPLATES[selected]))
                self.assertEqual(selected, fixture["template_id"])
                self.assertEqual([stage["stage_id"] for stage in resolved], fixture["expected_stage_ids"])
                self.assertEqual(resolved, templates.resolve_graph(resolved))
                for stage in resolved:
                    if stage.get("control_kind") is None:
                        adapter_catalog.for_stage(stage["stage_id"], stage["capability_id"])

    def test_repository_discovery_has_no_project_execution_surface(self) -> None:
        stages = templates.TEMPLATES["repository-discovery"]
        actions = {
            adapter_catalog.for_stage(stage["stage_id"], stage["capability_id"])["action_class"]
            for stage in stages
        }
        self.assertLessEqual(actions, {"read_local", "write_tailtrail_state"})

    def test_security_and_quality_policy_signals_select_predictably(self) -> None:
        self.assertEqual(templates.select_template({"security-vulnerability", "quality-signals"}), "risk-sensitive")
        self.assertEqual(templates.select_template({"quality-signals", "code-graph-mapper", "review"}), "ci-scanner-remediation")
        self.assertEqual(templates.select_template({"quality-signals", "review"}), "small-change")


if __name__ == "__main__":
    unittest.main()
