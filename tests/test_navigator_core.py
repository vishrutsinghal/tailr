from __future__ import annotations

import importlib.util
import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, (ROOT / "scripts").as_posix())

import navigator_core as core
import navigator


def load_script_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


task_start = load_script_module("tailtrail_task_start_test", "scripts/task-start.py")


class NavigatorCoreTests(unittest.TestCase):
    def test_tailtrail_hello_smoke_check(self) -> None:
        result = subprocess.run(
            [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "hello"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Hello from TailTrail.", result.stdout)
        self.assertIn("Installation check: passed", result.stdout)

    def test_classifies_sonar_vulnerability_handoff_prompt(self) -> None:
        goal = "Fix failing Sonar issue, check CVE impact, and prepare PR handoff"
        tasks = core.task_types(goal)
        risks = core.risk_indicators(goal, ["src/main/java/PaymentValidator.java"])

        self.assertIn("ci-sonar", tasks)
        self.assertIn("security", tasks)
        self.assertIn("handoff", tasks)
        self.assertIn("ci/sonar", risks)
        self.assertIn("vulnerability scan", risks)
        self.assertTrue(core.ci_sonar_requested(goal, tasks, risks))
        self.assertTrue(core.vulnerability_requested(goal, risks))

    def test_tiny_task_stays_lean_without_risk(self) -> None:
        risks = core.risk_indicators("fix typo in README", ["README.md"])
        self.assertEqual(risks, [])
        self.assertTrue(core.is_tiny("fix typo in README", risks, ["README.md"]))

    def test_repo_overview_prompt_is_not_feature_implementation(self) -> None:
        self.assertEqual(core.task_types("tell me important features of this repo"), ["repo-overview"])

    def test_add_unit_tests_does_not_become_feature_task_by_itself(self) -> None:
        self.assertEqual(core.task_types("fix payment validation bug and add unit tests"), ["bug", "qa"])
        self.assertEqual(core.task_types("fix claim amount validation and add focused tests"), ["bug", "qa"])
        self.assertIn("feature", core.task_types("add payment approval feature and unit tests"))

    def test_cross_repo_reference_parses_labeled_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            goal = "Use TailTrail cross-repo reference. Target: /tmp/service-a Reference: /tmp/service-b Goal: match validation style"
            plan = core.cross_repo_reference_plan(goal, root, "tailtrail")

        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(plan["target"], "/tmp/service-a")
        self.assertEqual(plan["reference"], "/tmp/service-b")
        self.assertIn('tailtrail reference --target "/tmp/service-a" --reference "/tmp/service-b"', str(plan["command"]))

    def test_navigator_decide_selects_scan_approval_for_sonar_and_vulnerability(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = navigator.decide(
                "Fix Sonar quality gate failure and check vulnerability impact before PR",
                root,
                ["src/main/java/PaymentValidator.java"],
                "tailtrail",
            )

        selected = {item["name"] for item in report["selected_features"]}
        self.assertIn("CI/Sonar Intelligence", selected)
        self.assertIn("Security And Vulnerability Intelligence", selected)
        self.assertIn("Quality Signal Scanner", selected)
        self.assertEqual(report["registry_workflow"]["workflow"], "sonar")
        self.assertIn("quality-signals", report["registry_workflow"]["feature_ids"])
        self.assertIsNotNone(report["scan_approval"])
        self.assertIn("Reply approve to proceed", " ".join(report["approval"]))

    def test_navigator_decide_selects_test_precision_for_unit_tests(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = navigator.decide(
                "fix payment validation bug and add unit tests",
                root,
                ["src/service/payment.py"],
                "tailtrail",
            )

        selected = {item["name"] for item in report["selected_features"]}
        skipped = {item["name"] for item in report["skipped_features"]}
        commands = "\n".join(report["suggested_commands"])
        rendered = navigator.markdown(report)

        self.assertIn("Test Precision Planner", selected)
        self.assertIn("token_budget", report)
        self.assertGreater(report["token_budget"]["budget_tokens"], 0)
        self.assertIn("Budget is guidance", report["token_budget"]["claim_guardrail"])
        self.assertIn("context_strategy", report)
        self.assertEqual(report["context_strategy"]["profile"], "testing")
        self.assertEqual(report["registry_workflow"]["workflow"], "qa")
        self.assertIn("testing", report["registry_workflow"]["feature_ids"])
        self.assertNotIn("AIDLC", selected)
        self.assertIn("AIDLC", skipped)
        self.assertNotIn("Test Precision Planner", skipped)
        self.assertIn("test_precision", report["recommended_workflow"])
        self.assertNotIn("aidlc", report["recommended_workflow"])
        self.assertIn("tailtrail test plan", commands)
        self.assertIn("--root", commands)
        self.assertIn("--goal", commands)
        self.assertIn("--changed src/service/payment.py", commands)
        self.assertIn("Test Precision Planner", rendered)
        self.assertIn("## Token Budget", rendered)
        self.assertIn("## Context Strategy", rendered)
        self.assertIn("regression, negative, boundary, and guard-preservation test cases", rendered)

    def test_navigator_commands_use_explicit_root_and_views(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = navigator.decide(
                "Fix Sonar quality gate failure and check vulnerability impact before PR",
                root,
                ["src/main/java/PaymentValidator.java"],
                "tailtrail",
            )

        commands = "\n".join(report["suggested_commands"])
        compact = navigator.markdown(report, "compact")
        commands_only = navigator.markdown(report, "commands-only")

        self.assertIn(f'graph --root "{root.as_posix()}" --changed src/main/java/PaymentValidator.java', commands)
        self.assertIn(f'vulnerability scan --root "{root.as_posix()}"', commands)
        self.assertIn("Vulnerability routing is planning-only", compact)
        self.assertIn("TailTrail Navigator Commands", commands_only)
        self.assertIn("Approval Required", commands_only)
        self.assertIn("Evidence Needed", commands_only)

    def test_navigator_decide_uses_compact_repo_overview_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = navigator.decide("tell me important features of this repo", root, [], "tailtrail")

        self.assertEqual(report["navigator_mode"], "repo_overview")
        self.assertEqual(report["recommended_workflow"], ["repo_overview"])
        self.assertEqual(report["registry_workflow"]["workflow"], "overview")
        self.assertIsNone(report["scan_approval"])
        self.assertIsNone(report["learning_capture_suggestion"])
        self.assertEqual(report["optional_deeper_discovery"]["name"], "Code Graph Mapper")
        self.assertIn("graph map --root", report["optional_deeper_discovery"]["command"])
        self.assertIn("tailtrail-meta/code-graph-cache.json", report["optional_deeper_discovery"]["creates"])
        self.assertEqual(report["bootstrap_snapshot"]["status"], "missing")
        selected = {item["name"] for item in report["selected_features"]}
        self.assertIn("Repo Overview", selected)
        self.assertIn("Bootstrap Snapshot", selected)

        rendered = navigator.markdown(report)
        self.assertIn("Repo Overview / Discovery", rendered)
        self.assertIn("Bootstrap Snapshot", rendered)
        self.assertIn("Optional Deeper Discovery", rendered)
        self.assertIn("tailtrail-meta/code-graph-cache.json", rendered)
        self.assertNotIn("## Skipped Features", rendered)
        self.assertNotIn("AIDLC.md", rendered)

    def test_repo_overview_markdown_matches_golden_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = navigator.decide("tell me important features of this repo", root, [], "tailtrail")
            rendered = navigator.markdown(report).replace(root.as_posix(), "<ROOT>")

        expected = (ROOT / "tests" / "golden" / "navigator_repo_overview.md").read_text(encoding="utf-8")
        self.assertEqual(rendered, expected)

    def test_learning_capture_command_points_to_tailtrail_install(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = navigator.decide("fix bug in parser", root, ["src/parser.py"], "tailtrail")

        selected = {item["name"] for item in report["selected_features"]}
        commands = "\n".join(report["suggested_commands"])

        self.assertIn("Bootstrap Snapshot", selected)
        self.assertIn("Code Graph Mapper", selected)
        self.assertIn("Learning Capture Trigger", selected)
        self.assertIn("bootstrap snapshot", commands)
        self.assertIn('graph map --root "', commands)
        command = report["learning_capture_suggestion"]["command"]
        compact = navigator.markdown(report, "compact")
        self.assertIn("/hooks/learning-capture-hook.py", command)
        self.assertNotIn("python3 hooks/learning-capture-hook.py", command)
        self.assertIn("Post-Task Learning Capture", compact)
        self.assertIn(command, compact)
        self.assertIn("run only after user approval", compact)
        self.assertIn("After user acceptance or reviewer feedback", " ".join(report["implementation_plan"]))

    def test_navigator_refreshes_stale_code_graph_for_code_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src"
            trail = root / "tailtrail-meta"
            source.mkdir()
            trail.mkdir()
            (source / "parser.py").write_text("def parse(value):\n    return value\n", encoding="utf-8")
            (trail / "code-graph-cache.json").write_text(
                json.dumps(
                    {
                        "root": root.as_posix(),
                        "scope": ["src/parser.py"],
                        "graph_mode": "review",
                        "source_files": {"src/parser.py": {"sha256": "old-hash"}},
                        "watch_files": {},
                        "scanner_evidence": {},
                        "graph": {"confidence": "medium", "suggested_read_order": ["src/parser.py"]},
                    }
                ),
                encoding="utf-8",
            )

            report = navigator.decide("fix parser bug", root, ["src/parser.py"], "tailtrail")

        selected = {item["name"] for item in report["selected_features"]}
        commands = "\n".join(report["suggested_commands"])

        self.assertIn("Code Graph Mapper", selected)
        self.assertEqual(report["graph_cache"]["status"], "stale")
        self.assertEqual(report["graph_cache"]["source"], "shared")
        self.assertIn(f'graph refresh --root "{root.as_posix()}" --changed src/parser.py', commands)

    def test_navigator_uses_legacy_local_code_graph_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src"
            trail = root / ".tailtrail"
            source.mkdir()
            trail.mkdir()
            content = "def parse(value):\n    return value\n"
            (source / "parser.py").write_text(content, encoding="utf-8")
            digest = navigator.file_sha256(source / "parser.py")
            (trail / "code-graph-cache.json").write_text(
                json.dumps(
                    {
                        "root": root.as_posix(),
                        "scope": ["src/parser.py"],
                        "graph_mode": "review",
                        "source_files": {"src/parser.py": {"sha256": digest}},
                        "watch_files": {},
                        "scanner_evidence": {},
                        "graph": {"confidence": "medium", "suggested_read_order": ["src/parser.py"]},
                    }
                ),
                encoding="utf-8",
            )

            report = navigator.decide("fix parser bug", root, ["src/parser.py"], "tailtrail")

        self.assertEqual(report["graph_cache"]["status"], "fresh")
        self.assertEqual(report["graph_cache"]["source"], "local")
        self.assertIn("Code Graph Mapper", {item["name"] for item in report["selected_features"]})

    def test_navigator_surfaces_only_approved_relevant_meta_harness_hints(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trail = root / ".tailtrail"
            trail.mkdir()
            proposal_path = trail / "meta-harness-proposals.jsonl"
            proposed_only = {
                "schema_version": "1",
                "type": "tailtrail-meta-harness-proposal",
                "proposal_id": "MH-PROPOSED",
                "status": "proposed",
                "affected_features": ["navigator"],
                "proposal_evidence_label": "local-evidence",
                "expected_improvement": "Do not show this proposed hint yet.",
                "source_finding": {"category": "navigator-routing"},
            }
            approved = {
                "schema_version": "1",
                "type": "tailtrail-meta-harness-proposal",
                "proposal_id": "MH-APPROVED",
                "status": "proposed",
                "affected_features": ["navigator"],
                "proposal_evidence_label": "local-evidence",
                "expected_improvement": "Prefer graph-first reads for similar implementation work.",
                "source_finding": {"category": "navigator-routing"},
            }
            record = {
                "schema_version": "1",
                "type": "tailtrail-meta-harness-proposal-record",
                "proposal_id": "MH-APPROVED",
                "status": "accepted",
            }
            proposal_path.write_text(
                "\n".join(json.dumps(item) for item in (proposed_only, approved, record)) + "\n",
                encoding="utf-8",
            )

            report = navigator.decide("fix parser bug", root, ["src/parser.py"], "tailtrail")
            rendered = navigator.markdown(report)

        selected = {item["name"] for item in report["selected_features"]}
        self.assertIn("Approved Meta-Harness Hints", selected)
        self.assertEqual(report["meta_harness_hints"]["status"], "available")
        self.assertEqual(len(report["meta_harness_hints"]["hints"]), 1)
        self.assertEqual(report["meta_harness_hints"]["hints"][0]["proposal_id"], "MH-APPROVED")
        self.assertNotIn("MH-PROPOSED", rendered)
        self.assertIn("Prefer graph-first reads", rendered)

    def test_task_start_report_wraps_navigator_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report("fix typo in README", root, ["README.md"], "tailtrail")

        self.assertEqual(report["navigator"]["recommended_workflow"], ["lean"])
        self.assertEqual(report["next_step"], "Review the plan, choose one next action, then approve or edit before implementation.")
        actions = {item["action"] for item in report["next_actions"]}
        self.assertIn("review", actions)
        self.assertIn("approve", actions)
        self.assertEqual(report["token_posture"]["mode"], "local_estimate")
        self.assertIn("recommended_check", report["setup_posture"])
        self.assertEqual(report["code_intelligence"]["default_engine_path"], ["lite", "v1", "v2"])
        self.assertIn("V3 is never default", report["code_intelligence"]["v3_rule"])
        self.assertIn("must not auto-run JDT", report["code_intelligence"]["auto_run_rule"])

    def test_task_start_keeps_evaluation_harness_available_for_simple_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report("fix typo in README", root, ["README.md"], "tailtrail")
            rendered = task_start.render_markdown(report)

        self.assertFalse(report["evaluation_posture"]["selected"])
        self.assertIn("Evaluation Harness: available", rendered)
        self.assertNotIn("Evaluation scenarios: `tailtrail eval scenario list`", rendered)
        self.assertNotIn("## Evaluation Harness\n\n- Selected: `true`", rendered)

    def test_task_start_selects_evaluation_harness_for_evidence_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report("show evaluation harness evidence", root, [], "tailtrail")
            rendered = task_start.render_markdown(report)

        self.assertTrue(report["evaluation_posture"]["selected"])
        self.assertEqual(report["evaluation_posture"]["scenario"], "validation-bug")
        self.assertIn("Evaluation Harness: selected", rendered)
        self.assertIn("Evaluation scenarios: `tailtrail eval scenario list`", rendered)
        self.assertIn("Evaluation run: `tailtrail eval scenario run --scenario validation-bug`", rendered)

    def test_navigator_selects_evaluation_harness_for_evidence_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = navigator.decide("show evaluation harness evidence", root, [], "tailtrail")
            rendered = navigator.markdown(report)
            compact = navigator.markdown(report, "compact")
            commands_only = navigator.markdown(report, "commands-only")

        selected = {item["name"] for item in report["selected_features"]}
        commands = "\n".join(report["suggested_commands"])

        self.assertIn("Evaluation Harness", selected)
        self.assertTrue(report["evaluation_harness"]["selected"])
        self.assertEqual(report["evaluation_harness"]["scenario"], "validation-bug")
        self.assertIn("tailtrail eval scenario list", commands)
        self.assertIn("tailtrail eval scenario run --scenario validation-bug", commands)
        self.assertIn("## Evaluation Harness", rendered)
        self.assertIn("## Evaluation Harness", compact)
        self.assertIn("## Evaluation Harness", commands_only)

    def test_navigator_selects_security_scenario_for_security_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = navigator.decide("create a security proof report", root, [], "tailtrail")

        selected = {item["name"] for item in report["selected_features"]}
        commands = "\n".join(report["suggested_commands"])

        self.assertIn("Evaluation Harness", selected)
        self.assertEqual(report["evaluation_harness"]["scenario"], "security-triage")
        self.assertIn("tailtrail eval scenario run --scenario security-triage", commands)

    def test_navigator_does_not_select_evaluation_harness_for_tiny_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = navigator.decide("fix typo in README", root, ["README.md"], "tailtrail")
            rendered = navigator.markdown(report)

        selected = {item["name"] for item in report["selected_features"]}
        skipped = {item["name"] for item in report["skipped_features"]}
        commands = "\n".join(report["suggested_commands"])

        self.assertNotIn("Evaluation Harness", selected)
        self.assertIn("Evaluation Harness", skipped)
        self.assertFalse(report["evaluation_harness"]["selected"])
        self.assertNotIn("eval scenario", commands)
        self.assertNotIn("## Evaluation Harness", rendered)


if __name__ == "__main__":
    unittest.main()
