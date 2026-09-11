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
    def test_static_validation_selects_lint_and_one_build_or_type_check(self) -> None:
        task_start = load_task_start_module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "package.json").write_text(
                json.dumps({"scripts": {
                    "lint": "eslint .",
                    "typecheck": "tsc --noEmit",
                    "build": "vite build",
                }}),
                encoding="utf-8",
            )
            rows = task_start.static_validation_plan(root, ["src/pages/Checkout.tsx"])

        self.assertEqual(["npm run lint", "npm run typecheck"], [row["command"] for row in rows])
        self.assertTrue(all(row["required"] for row in rows))

    def test_scope_relationship_summary_uses_the_displayed_paths_direction(self) -> None:
        task_start = load_task_start_module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            page = root / "src" / "pages" / "status" / "StatusPage.tsx"
            service = page.with_name("statusService.ts")
            proof = page.with_name("StatusPage.cy.tsx")
            page.parent.mkdir(parents=True)
            service.write_text(
                "export function warning() { return 'Trace endpoint is not configured.'; }\n",
                encoding="utf-8",
            )
            page.write_text(
                "import { warning } from './statusService';\n"
                "export function StatusPage() { const value = warning(); "
                "return <main>{value && <aside>{value}</aside>}</main>; }\n",
                encoding="utf-8",
            )
            proof.write_text("import { StatusPage } from './StatusPage';\n", encoding="utf-8")
            (root / "package.json").write_text(
                json.dumps({"scripts": {"cypress:component": "cypress run --component"}}),
                encoding="utf-8",
            )
            report = task_start.build_report(
                "On the status page remove the banner Trace endpoint is not configured.",
                root,
                [],
                "tailtrail",
                aidlc_mode="lite",
            )
            rendered = task_start.verbose_start_report(report)

        self.assertIn("produces a value rendered by the UI owner", rendered)
        self.assertNotIn("statusService.ts`**\n  - **Requirements:** REQ-01\n  - **Confidence:** `high`\n  - **Evidence:** 7 strong relationship edge(s): renders returned value", rendered)

    def test_page_proof_proposal_is_derived_for_an_arbitrary_ui_owner(self) -> None:
        task_start = load_task_start_module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src" / "features" / "checkout").mkdir(parents=True)
            (root / "src" / "features" / "checkout" / "CheckoutPanel.tsx").write_text(
                "export function CheckoutPanel() { return <main>Checkout</main>; }\n",
                encoding="utf-8",
            )
            (root / "package.json").write_text(
                json.dumps({"scripts": {"component:test": "cypress run --component"}}),
                encoding="utf-8",
            )
            (root / "cypress.config.ts").write_text("export default {};\n", encoding="utf-8")

            proposed = task_start.proposed_ui_proof(
                root,
                ["src/features/checkout/CheckoutPanel.tsx"],
            )

        self.assertEqual(
            proposed,
            (
                "src/features/checkout/CheckoutPanel.cy.tsx",
                'npm run component:test -- --spec "src/features/checkout/CheckoutPanel.cy.tsx"',
            ),
        )

    def test_ui_navigation_plan_is_atomic_evidence_backed_and_test_required(self) -> None:
        task_start = load_task_start_module()
        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "navigator-scope" / "ui-handler-import-ownership.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for relative, body in fixture["repository_files"].items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding="utf-8")

            report = task_start.build_report(fixture["goal"], root, [], "tailtrail")
            rendered = task_start.verbose_start_report(report)
            automatic_expert = task_start.render_markdown(report)
            explicit_verbose = task_start.render_markdown(report, verbose=True)
            quick = task_start.render_markdown(report, presentation_mode="quick")
            guided = task_start.render_markdown(report, presentation_mode="guided")
            report["planning_lock"] = task_start.planning_lock.create(root, fixture["goal"], "ui-cohesive-proof")
            task_start.planning_lock.save_start_report(root, "ui-cohesive-proof", report)
            activated = task_start.planning_lock.activate(root, "ui-cohesive-proof", True)

        statements = [row["statement"] for row in report["navigator"]["requirement_matrix"]]
        contracts = report["ui_plan"]["contracts"]
        test_cases = report["testing_plan"]["test_cases"]
        self.assertEqual(len(statements), 3)
        self.assertEqual(
            [f"TC-{index:02d}" for index in range(1, len(test_cases) + 1)],
            [row["test_case_id"] for row in test_cases],
        )
        self.assertEqual({"REQ-01", "REQ-02", "REQ-03"}, {row["requirement_id"] for row in test_cases})
        self.assertIn("validation succeeds", statements[0])
        self.assertIn("copy succeeds", statements[1])
        self.assertTrue(statements[2].startswith("Preserve the existing generate event flow"))
        self.assertIn("advance to the requested Validate", contracts[0]["outcome"])
        self.assertIn("clipboard failure", contracts[1]["states"])
        self.assertIn("Preserve the existing Generate Event Flow", contracts[2]["outcome"])
        self.assertNotIn("dependency", report["navigator"]["risk_indicators"])
        self.assertNotIn("multi-file", report["navigator"]["risk_indicators"])
        self.assertNotIn("dependency_review", report["navigator"]["recommended_workflow"])
        self.assertIn("## Plan", rendered)
        decision_order = [
            "## Goal",
            "## Requirements",
            "## Scope",
            "## Requirement-to-UI contract",
            "## Plan",
            "## Validation",
            "## Navigator Decision",
        ]
        for surface in (automatic_expert, explicit_verbose):
            surface_lines = surface.splitlines()
            positions = [surface_lines.index(heading) for heading in decision_order]
            self.assertEqual(positions, sorted(positions))
        compact_order = [
            "## Requirements",
            "## Scope",
            "## Requirement-to-UI contract",
            "## Plan",
        ]
        for surface in (quick, guided):
            surface_lines = surface.splitlines()
            positions = [surface_lines.index(heading) for heading in compact_order]
            self.assertEqual(positions, sorted(positions))
        self.assertNotIn("### Excluded candidates", automatic_expert)
        self.assertNotIn("### Excluded candidates", quick)
        self.assertNotIn("### Excluded candidates", guided)
        self.assertIn("### Excluded candidates", explicit_verbose)
        self.assertIn("Scope evidence source: `bounded in-memory graph`", rendered)
        self.assertIn("Graph source: `bounded in-memory graph`", rendered)
        self.assertIn("implementation owner", rendered)
        self.assertIn("contains user visible literal", rendered)
        self.assertIn("in-file behavior evidence", rendered)
        self.assertNotIn("PipelineAuditEventsGeneratorPage.tsx` -> `src/pages/pipelineAuditEventsGenerator/PipelineAuditEventsGeneratorPage.tsx", rendered)
        precision_features = [
            item
            for item in report["guided_delivery"]["selected"]
            if item["name"] == "Test Precision Planner"
        ]
        self.assertEqual(1, len(precision_features))
        self.assertEqual(
            "Planning now and after implementation",
            precision_features[0]["when"],
        )
        self.assertEqual(report["guided_delivery"]["slice_strategy"]["mode"], "cohesive-ui-slice")
        self.assertIn("one cohesive UI slice", " ".join(report["guided_delivery"]["stages"]))
        self.assertIn("create the approved page-level proof", " ".join(report["guided_delivery"]["stages"]))
        self.assertNotIn("confirm the planned page-level", " ".join(report["guided_delivery"]["stages"]))
        self.assertNotIn("one approved requirement at a time", " ".join(report["guided_delivery"]["stages"]))
        proof_path = "src/pages/pipelineAuditEventsGenerator/PipelineAuditEventsGeneratorPage.cy.tsx"
        self.assertEqual(len(report["focused_validation"]), 1)
        focused = report["focused_validation"][0]
        self.assertEqual(focused["candidate"], proof_path)
        self.assertEqual(focused["candidate_state"], "proposed")
        self.assertEqual(focused["tiers"], ["component", "behaviour"])
        self.assertEqual(focused["tier"], "component + behaviour")
        self.assertEqual(
            focused["command"],
            'npm run cypress:component -- --spec "src/pages/pipelineAuditEventsGenerator/PipelineAuditEventsGeneratorPage.cy.tsx"',
        )
        self.assertIn("### Existing proof paths", rendered)
        self.assertIn("### Proposed proof additions", rendered)
        self.assertIn("create or edit as proof-only scope", rendered)
        self.assertIn(proof_path, rendered)
        self.assertNotIn("required: select the repository-owned test convention", rendered)
        self.assertIn("Exact run usage: not knowable during planning", rendered)
        self.assertIn("Baseline comparison: optional", rendered)
        self.assertIn("Full scoped-file ceiling:", rendered)
        self.assertIn("Repository inventory ceiling (informational only):", rendered)
        self.assertIn("### Planned context slices", rendered)
        self.assertIn("Estimated reduction versus full scoped files:", rendered)
        self.assertIn("Major techniques:", rendered)
        self.assertNotIn("Estimated context reduction: `0%`", rendered)
        for surface in (automatic_expert, quick, guided):
            self.assertIn("Planned TailTrail working set:", surface)
            self.assertIn("Estimated reduction versus full scoped files:", surface)
            self.assertIn("Major techniques:", surface)
            self.assertNotIn("Repository inventory ceiling", surface)
            self.assertNotIn("Exact run usage:", surface)
            self.assertNotIn("Baseline comparison:", surface)
        self.assertTrue(all(
            proof_path in row["validation_contract"]["proposed_paths"]
            for row in report["navigator"]["requirement_matrix"]
        ))
        handoff = activated["execution_handoff"]
        self.assertIn(proof_path, handoff["proof_paths"])
        self.assertIn(proof_path, handoff["scope_drift_rule"]["approved_editable_paths"])
        self.assertNotIn(proof_path, handoff["scope_drift_rule"]["approved_implementation_paths"])
        self.assertNotIn("must be discovered after approval", rendered)
        self.assertEqual(task_start.ui_planning._role("src/components/Button.cy.tsx"), "UI evidence")

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

    def test_hands_free_ui_plan_keeps_ui_preservation_in_the_canonical_requirement_contract(self) -> None:
        task_start = load_task_start_module()
        with tempfile.TemporaryDirectory() as temp:
            report = task_start.build_report("hands-free: add a checkout confirmation screen UI end to end", Path(temp), [], "tailtrail")
        requirements = report["guided_delivery"]["hands_free_program"]["feature_requirements"]
        matrix = report["navigator"]["requirement_matrix"]
        self.assertEqual(
            [(row["display_id"], row["statement"]) for row in requirements],
            [(row["display_id"], row["statement"]) for row in matrix],
        )
        self.assertIn(
            "Reuse existing layout",
            report["ui_plan"]["reuse_boundary"],
        )

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
            report = task_start.build_report(
                goal,
                root,
                ["ui/order-operations.html", "ui/design-tokens.css", "tests/ui/test_ui_baseline.py"],
                "tailtrail",
            )
            rendered = task_start.verbose_start_report(report)

        statements = [row["statement"] for row in report["navigator"]["requirement_matrix"]]
        impacted = [
            row["path"] for row in report["navigator"]["likely_impacted_files"]
            if row.get("status") in {"included", "proof-only"}
        ]
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
        self.assertIn("## Requirement-to-UI contract", rendered)
        self.assertIn("## UI consistency details", rendered)
        self.assertIn("pending, valid, invalid, and failure", rendered)
        self.assertIn("UI behaviour evidence", rendered)
        self.assertNotIn("authoritative transition", rendered)
        self.assertNotIn("tests/ui/__init__.py", rendered)
        self.assertIn("- **component + behaviour**", rendered)
        self.assertIn("- **Candidate:** `tests/ui/test_ui_baseline.py`", rendered)
        self.assertNotIn("| Requirement | Observable UI outcome |", rendered)
        self.assertNotIn("| Feature | When | Why |", rendered)
        self.assertNotIn("| Tier | Candidate | Status / command |", rendered)

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

        included = [
            row for row in report["navigator"]["likely_impacted_files"]
            if row.get("status") == "included"
        ]
        self.assertEqual(included, [])
        self.assertEqual(report["ui_plan"]["surface_status"], "not-discovered")
        self.assertIn("UI implementation surface: **not-discovered**", rendered)
        self.assertIn("will not treat backend candidates as the missing ui surface", rendered.lower())
        self.assertIn("status=inspection-only", rendered)

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
