from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


navigator = load("tailtrail_release4_navigator", "navigator.py")
discovery = load("tailtrail_release4_discovery", "navigator_discovery.py")
task_start = load("tailtrail_release4_task_start", "task-start.py")
posture = load("tailtrail_release4_start_posture", "start_posture.py")


class Release4MaintainabilityTests(unittest.TestCase):
    def test_navigator_discovery_wrappers_preserve_local_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src" / "orders" / "validation.py"
            source.parent.mkdir(parents=True)
            source.write_text("def validate_quantity(value):\n    return value > 0\n", encoding="utf-8")
            test = root / "tests" / "test_validation.py"
            test.parent.mkdir(parents=True)
            test.write_text("def test_zero_quantity(): pass\n", encoding="utf-8")
            goal = "fix zero quantity validation"
            self.assertEqual(navigator.goal_discovered_paths(root, goal), discovery.goal_discovered_paths(root, goal))
            self.assertEqual(navigator.repository_discovered_paths(root, goal), discovery.repository_discovered_paths(root, goal))
            self.assertFalse(navigator.is_actionable_changed_path(root, ".tailtrail/state.json"))
            self.assertTrue(navigator.is_actionable_changed_path(root, "src/orders/validation.py"))

    def test_start_posture_extraction_preserves_token_and_operational_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src" / "validation.py"
            source.parent.mkdir(parents=True)
            source.write_text("x" * 40, encoding="utf-8")
            unrelated = root / "src" / "unrelated.py"
            unrelated.write_text("y" * 360, encoding="utf-8")
            plan = {"likely_impacted_files": [{"path": "src/validation.py"}], "avoid": []}
            result = task_start.token_posture(root, plan)
            self.assertEqual(result, posture.token_posture(root, plan, task_start.LARGE_CONTEXT_FILES, task_start.APPROX_CHARS_PER_TOKEN))
            self.assertEqual(10, result["used_tokens"])
            self.assertEqual(10, result["scoped_file_ceiling_tokens"])
            self.assertIsNone(result["planned_working_set_tokens"])
            self.assertEqual(100, result["repository_ceiling_tokens"])
            self.assertEqual(0, result["estimated_saved_tokens"])
            self.assertIsNone(result["estimated_reduction_percent"])
            self.assertEqual(90, result["repository_context_avoided_tokens"])
            self.assertEqual(90.0, result["repository_reduction_percent"])
            self.assertIn("Navigator scope narrowing", result["saving_techniques"])
            self.assertEqual(task_start.setup_posture(root, "tailtrail"), posture.setup_posture(root, "tailtrail", task_start.ROOT))

    def test_graph_slices_reduce_a_large_scoped_file_without_using_repo_as_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            page = root / "src" / "pages" / "PublishPage.tsx"
            service = root / "src" / "pages" / "traceService.ts"
            proof = root / "src" / "pages" / "PublishPage.cy.tsx"
            page.parent.mkdir(parents=True)
            filler = "\n".join(f"const filler{index} = {index};" for index in range(700))
            page.write_text(
                "import { getTrace } from './traceService';\n"
                "export function PublishPage() {\n"
                "  async function refresh() { await getTrace(); }\n"
                "  return <button onClick={refresh}>Publish</button>;\n"
                "}\n" + filler + "\n",
                encoding="utf-8",
            )
            service.write_text(
                "export function getTrace() { throw new Error('Trace endpoint is not configured.'); }\n",
                encoding="utf-8",
            )
            proof.write_text(
                "import { PublishPage } from './PublishPage';\ndescribe('PublishPage', () => { it('publishes', () => PublishPage); });\n",
                encoding="utf-8",
            )
            scoped = [
                "src/pages/PublishPage.tsx",
                "src/pages/traceService.ts",
                "src/pages/PublishPage.cy.tsx",
            ]
            plan = {
                "likely_impacted_files": [{"path": path} for path in scoped],
                "avoid": [],
                "requirement_matrix": [{
                    "query_terms": ["publish", "trace"],
                    "quoted_literals": ["Trace endpoint is not configured."],
                }],
                "scope_evidence": {
                    "requirements": [{
                        "implementation_owners": [scoped[0]],
                        "inspection_paths": [scoped[1]],
                        "proof_paths": [scoped[2]],
                    }],
                    "candidates": [
                        {"path": scoped[0], "role": "implementation-owner"},
                        {"path": scoped[1], "role": "literal-emitter"},
                        {"path": scoped[2], "role": "test"},
                    ],
                    "investigation": {"cache": {"status": "fresh"}},
                },
                "learning_use_proposal": {
                    "state": "proposed",
                    "matches": [{"learning_id": "lrn-not-approved"}],
                },
            }

            result = posture.token_posture(
                root, plan, task_start.LARGE_CONTEXT_FILES, task_start.APPROX_CHARS_PER_TOKEN
            )

        self.assertEqual("graph_slice_forecast", result["mode"])
        self.assertEqual("scoped-file-slice-estimate", result["comparison_state"])
        self.assertEqual("medium", result["forecast_confidence"])
        self.assertIn("exact combined behavior-and-symbol anchor", result["forecast_confidence_reason"])
        self.assertLess(result["planned_working_set_tokens"], result["scoped_file_ceiling_tokens"])
        self.assertGreater(result["estimated_reduction_percent"], 50)
        self.assertEqual({"implementation", "inspection", "proof"}, {row["purpose"] for row in result["context_slices"]})
        self.assertIn("Code Graph slice reuse", result["saving_techniques"])
        self.assertNotIn("Project learning reuse", result["saving_techniques"])
        verbose = task_start.token_estimate_lines(result, detailed=True)
        compact = task_start.token_estimate_lines(result, detailed=False)
        self.assertIn("Confidence reason:", "\n".join(verbose))
        self.assertNotIn("Confidence reason:", "\n".join(compact))
        self.assertTrue(all(
            row.get("confidence_reason")
            for row in result["context_slices"]
            if row.get("confidence") == "medium"
        ))

    def test_start_rendering_contract_remains_intact_after_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src" / "order_service" / "validation.py"
            source.parent.mkdir(parents=True)
            source.write_text("def validate_quantity(value):\n    return value > 0\n", encoding="utf-8")
            test = root / "tests" / "unit" / "test_validation.py"
            test.parent.mkdir(parents=True)
            test.write_text("import unittest\n", encoding="utf-8")
            report = task_start.build_report("fix zero quantity validation", root, ["src/order_service/validation.py", "tests/unit/test_validation.py"], "tailtrail")
            compact = task_start.compact_start_report(report)
            verbose = task_start.verbose_start_report(report)
            for heading in ("## Scope", "## Requirements", "## Selected TailTrail features", "## Focused validation", "## Approval"):
                self.assertIn(heading, compact)
            for heading in ("## Planning Lock", "## Start Here", "## Navigator Decision", "## Selected TailTrail features", "## Required later in this run", "## Conditional TailTrail controls", "## Guided Delivery", "## Validation", "## Evidence posture", "## Approval"):
                self.assertIn(heading, verbose)

    def test_extracted_modules_are_part_of_the_real_planning_path(self) -> None:
        navigator_body = (ROOT / "scripts" / "navigator.py").read_text(encoding="utf-8")
        start_body = (ROOT / "scripts" / "task-start.py").read_text(encoding="utf-8")
        self.assertIn("import navigator_discovery as discovery", navigator_body)
        self.assertIn("return discovery.goal_discovered_paths", navigator_body)
        self.assertIn("import start_posture", start_body)
        self.assertIn("start_posture.token_posture", start_body)
        self.assertIn("start_posture.evaluation_posture", start_body)
