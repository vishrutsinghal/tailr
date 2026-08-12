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
review_graph = load_script_module("tailtrail_review_graph_test", "scripts/review-graph.py")
ast_map = load_script_module("tailtrail_ast_map_test", "scripts/ast-map.py")
code_graph_mapper = load_script_module("tailtrail_code_graph_mapper_test", "scripts/code-graph-mapper.py")


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

    def test_changed_file_discovery_excludes_managed_packs_and_bytecode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tailtrail").mkdir()
            (root / "tailtrail" / ".tailtrail-install.json").write_text("{}", encoding="utf-8")
            self.assertFalse(navigator.is_actionable_changed_path(root, "tailtrail/scripts/navigator.py"))
            self.assertFalse(navigator.is_actionable_changed_path(root, "src/__pycache__/service.pyc"))
            self.assertTrue(navigator.is_actionable_changed_path(root, "src/order_service/service.py"))

    def test_start_discovers_goal_matched_source_and_test_before_git_noise(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src" / "order_service").mkdir(parents=True)
            (root / "tests" / "unit").mkdir(parents=True)
            (root / "src" / "order_service" / "validation.py").write_text(
                "def validate(quantity):\n    return quantity >= 0\n", encoding="utf-8"
            )
            (root / "src" / "order_service" / "service.py").write_text(
                "def submit(quantity):\n    return quantity\n", encoding="utf-8"
            )
            (root / "tests" / "unit" / "test_validation.py").write_text(
                "def test_zero_quantity():\n    assert True\n", encoding="utf-8"
            )
            report = navigator.decide(
                "fix the zero quantity validation defect and add focused validation",
                root,
                [],
                "tailtrail",
                detect_git_changes=False,
            )
            paths = [item["path"] for item in report["likely_impacted_files"]]
            self.assertEqual(report["target_origin"], "goal-discovery")
            self.assertIn("src/order_service/validation.py", paths)
            self.assertIn("tests/unit/test_validation.py", paths)
            self.assertNotIn("src/order_service/service.py", paths)
            self.assertEqual(len(paths), len(set(paths)))
            self.assertNotIn("Code Graph Mapper", {item["name"] for item in report["selected_features"]})

    def test_non_review_start_does_not_adopt_unrelated_git_changes_when_goal_discovery_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original_discovery = navigator.goal_discovered_paths
            original_git_changed = navigator.git_changed
            try:
                navigator.goal_discovered_paths = lambda *_args: []
                navigator.git_changed = lambda *_args: [".codex-plugin/plugin.json", "README.md"]
                report = navigator.decide("implement audit events generator", root, [], "tailtrail")
            finally:
                navigator.goal_discovered_paths = original_discovery
                navigator.git_changed = original_git_changed

        self.assertEqual(report["target_origin"], "none")
        self.assertEqual(report["likely_impacted_files"], [])

    def test_explicit_review_may_use_git_changes_when_goal_discovery_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original_discovery = navigator.goal_discovered_paths
            original_git_changed = navigator.git_changed
            try:
                navigator.goal_discovered_paths = lambda *_args: []
                navigator.git_changed = lambda *_args: ["src/service.py"]
                report = navigator.decide("review my uncommitted changes", root, [], "tailtrail")
            finally:
                navigator.goal_discovered_paths = original_discovery
                navigator.git_changed = original_git_changed

        self.assertEqual(report["target_origin"], "git-changes")
        self.assertEqual(report["likely_impacted_files"], [{"path": "src/service.py", "reason": "detected Git change"}])

    def test_task_start_renders_installed_pack_command_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tailtrail" / "scripts").mkdir(parents=True)
            (root / "tailtrail" / "scripts" / "tailtrail.py").write_text("", encoding="utf-8")
            report = task_start.build_report("fix validation", root, [], "python3 tailtrail.py")
            self.assertEqual(report["command_prefix"], "python3 tailtrail/scripts/tailtrail.py")

    def test_task_start_keeps_already_resolved_installed_pack_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tailtrail" / "scripts").mkdir(parents=True)
            (root / "tailtrail" / "scripts" / "tailtrail.py").write_text("", encoding="utf-8")
            prefix = "python3 tailtrail/scripts/tailtrail.py"
            report = task_start.build_report("fix validation", root, [], prefix)
            self.assertEqual(report["command_prefix"], prefix)

    def test_review_graph_paths_are_bounded_for_windows_safe_subprocesses(self) -> None:
        changed = [f"generated/{index:04d}-{'x' * 300}.py" for index in range(100)]
        selected = navigator.bounded_review_graph_paths(changed)
        self.assertLessEqual(len(selected), navigator.MAX_REVIEW_GRAPH_CHANGED_PATHS)
        self.assertLessEqual(
            sum(len("--changed") + 1 + len(path) + 1 for path in selected),
            navigator.MAX_REVIEW_GRAPH_ARGUMENT_CHARS,
        )
        self.assertLess(len(selected), len(changed))

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

    def test_explicit_navigator_parser_keeps_control_words_out_of_task_scope(self) -> None:
        request = core.explicit_navigator_request(
            "using TailTrail Navigator, give me plan for Phase 1 before implementation"
        )
        self.assertIsNotNone(request)
        assert request is not None
        self.assertEqual(request.depth, "plan")
        self.assertEqual(request.subject, "Phase 1")

    def test_explicit_navigator_plan_resolves_phase_and_keeps_edit_gate_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tailtrail-implementation-backlog.md").write_text(
                "# Backlog\n\n## Phase 1 — Canonical local state\n\nPlan the local state.\n",
                encoding="utf-8",
            )
            report = navigator.decide(
                "TailTrail Navigator plan tailtrail-implementation-backlog.md Phase 1",
                root,
                [],
                "tailtrail",
            )
        self.assertEqual(report["navigator_request"]["depth"], "plan")
        self.assertEqual(report["phase_context"]["status"], "resolved")
        rendered = navigator.markdown(report)
        self.assertIn("# TailTrail Navigator Decision", rendered)
        self.assertIn("Approve the Navigator plan", rendered)
        self.assertNotIn("## Detailed Implementation Proposal", rendered)
        self.assertIn("**No files were changed.**", rendered)
        self.assertIn("## Proposed Requirement-to-Impact Matrix", rendered)
        self.assertIn("## Requirement Discovery Feedback", rendered)

    def test_explicit_navigator_implementation_has_separate_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = navigator.decide("TailTrail Navigator implement fix validation", root, [], "tailtrail")
        rendered = navigator.markdown(report)
        self.assertIn("## Navigator Plan", rendered)
        self.assertIn("## Detailed Implementation Proposal", rendered)
        self.assertIn("Approve the implementation proposal", rendered)

    def test_explicit_navigator_does_not_guess_ambiguous_phase_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("ROADMAP.md", "harness-engineering.md"):
                (root / name).write_text("## Phase 1 — Example\n", encoding="utf-8")
            report = navigator.decide("TailTrail Navigator plan Phase 1", root, [], "tailtrail")
        self.assertEqual(report["phase_context"]["status"], "ambiguous")
        self.assertIn("Choose one before implementation planning", navigator.markdown(report))

    def test_add_unit_tests_does_not_become_feature_task_by_itself(self) -> None:
        self.assertEqual(core.task_types("fix payment validation bug and add unit tests"), ["bug", "qa"])
        self.assertEqual(core.task_types("fix claim amount validation and add focused tests"), ["bug", "qa"])
        self.assertEqual(core.task_types("fix the claim amount validation bug and add focused validation"), ["bug", "qa"])
        self.assertIn("feature", core.task_types("add payment approval feature and unit tests"))

    def test_review_graph_excludes_markdown_from_code_caller_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src" / "claims_api").mkdir(parents=True)
            (root / "tests").mkdir()
            (root / "src" / "claims_api" / "validation.py").write_text("def valid(amount):\n    return amount > 0\n", encoding="utf-8")
            (root / "tests" / "test_claim_validation.py").write_text("from claims_api.validation import valid\n", encoding="utf-8")
            for name in ("AGENTS.md", "BUILDWEEK-SUBMISSION.md", "DEMO-PROMPTS.md"):
                (root / name).write_text("Validation demo guidance.\n", encoding="utf-8")

            report = review_graph.graph(root, ["src/claims_api/validation.py"], limit=5)

        self.assertEqual(
            report["suggested_read_order"],
            ["src/claims_api/validation.py", "tests/test_claim_validation.py"],
        )

    def test_review_graph_excludes_installed_tailtrail_pack_from_suggested_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src" / "order_service").mkdir(parents=True)
            (root / "tailtrail" / "hooks").mkdir(parents=True)
            (root / "src" / "order_service" / "validation.py").write_text(
                "def validate(quantity):\n    return quantity > 0\n", encoding="utf-8"
            )
            (root / "tailtrail" / "hooks" / "learning-capture-hook.py").write_text(
                "def validation_hook(quantity):\n    return quantity\n", encoding="utf-8"
            )
            report = review_graph.graph(root, ["src/order_service/validation.py"], limit=5)

        self.assertNotIn("tailtrail/hooks/learning-capture-hook.py", report["suggested_read_order"])

    def test_semantic_v3_markdown_uses_a_provenance_table(self) -> None:
        report = {
            "depth": "v3",
            "scope": ["src/claims_api/validation.py"],
            "symbols": [
                {"name": "validate_claim_amount", "file": "src/claims_api/validation.py", "line": 9, "confidence": "provider-backed"},
                {"name": "validate_claim", "file": "src/claims_api/validation.py", "line": 14, "confidence": "provider-backed"},
            ],
            "references": [{"symbol": "validate_claim_amount", "file": "tests/test_claim_validation.py", "line": 27, "confidence": "provider-backed"}],
            "call_hints": [{"caller": "accept_claim", "callee": "validate_claim", "file": "src/claims_api/service.py", "line": 8, "confidence": "provider-backed"}],
            "semantic": {"provider_outputs": [{"path": "tailtrail-meta/providers/sample-semantic.json"}]},
            "evidence_summary": {"heuristic": 0, "local-ast": 2, "provider-backed": 4, "measured/validated": 0},
        }

        rendered = ast_map.markdown(report)

        self.assertIn("# TailTrail Semantic V3", rendered)
        self.assertIn("| Evidence type | Count | Meaning |", rendered)
        self.assertIn("| `provider-backed` | `4` | Read from the approved local provider-output JSON |", rendered)
        self.assertIn("`validate_claim_amount` reference in `tests/test_claim_validation.py:27`", rendered)
        self.assertIn("`validate_claim` call hint in `src/claims_api/service.py:8`", rendered)
        self.assertIn("The report labels this input as: `provider-backed`.", rendered)
        self.assertNotIn("## Provider Outputs", rendered)

    def test_semantic_v2_markdown_matches_the_compact_evidence_pattern(self) -> None:
        report = {
            "depth": "v2",
            "references": [{"symbol": "validate_claim_amount", "file": "tests/test_claim_validation.py", "line": 27, "confidence": "heuristic"}],
            "call_hints": [{"caller": "accept_claim", "callee": "validate_claim", "file": "src/claims_api/service.py", "line": 8, "confidence": "local-ast"}],
            "evidence_summary": {"heuristic": 14, "local-ast": 24, "provider-backed": 0, "measured/validated": 0},
        }

        rendered = ast_map.markdown(report)

        self.assertIn("# TailTrail Semantic V2", rendered)
        self.assertIn("| Evidence type | Count | Meaning |", rendered)
        self.assertIn("| `provider-backed` | `0` | Not used in Semantic V2 |", rendered)
        self.assertIn("## Local semantic additions include:", rendered)
        self.assertIn("`validate_claim` call hint in `src/claims_api/service.py:8` [`local-ast`]", rendered)
        self.assertIn("The report labels this input as: `local-ast` and `heuristic`.", rendered)

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
        self.assertEqual(
            report["recommended_workflow"],
            ["implementation", "qa_review", "test_precision", "review"],
        )
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
                        "inventory": navigator.graph_inventory(root),
                        "graph": {"confidence": "medium", "suggested_read_order": ["src/parser.py"]},
                    }
                ),
                encoding="utf-8",
            )

            report = navigator.decide("fix parser bug", root, ["src/parser.py"], "tailtrail")

        self.assertEqual(report["graph_cache"]["status"], "fresh")
        self.assertEqual(report["graph_cache"]["source"], "local")
        self.assertIn("Code Graph Mapper", {item["name"] for item in report["selected_features"]})

    def test_navigator_marks_graph_cache_stale_when_relevant_file_is_added(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src"; source.mkdir()
            trail = root / "tailtrail-meta"; trail.mkdir()
            parser = source / "parser.py"; parser.write_text("def parse(value):\n    return value\n", encoding="utf-8")
            digest = navigator.file_sha256(parser)
            (trail / "code-graph-cache.json").write_text(json.dumps({
                "root": root.as_posix(), "scope": ["src/parser.py"], "graph_mode": "review",
                "source_files": {"src/parser.py": {"sha256": digest}}, "watch_files": {}, "scanner_evidence": {},
                "inventory": navigator.graph_inventory(root),
                "graph": {"confidence": "medium", "suggested_read_order": ["src/parser.py"]},
            }), encoding="utf-8")
            (source / "new_rule.py").write_text("def validate(value):\n    return value\n", encoding="utf-8")
            report = navigator.decide("add validation feature", root, ["src/parser.py"], "tailtrail")
        self.assertEqual(report["graph_cache"]["status"], "stale")
        self.assertIn("inventory changed", " ".join(report["graph_cache"]["reasons"]).lower())

    def test_code_graph_mapper_inventory_detects_untracked_relevant_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src"; source.mkdir()
            (source / "parser.py").write_text("def parse(value):\n    return value\n", encoding="utf-8")
            cache = code_graph_mapper.build_graph(root, ["src/parser.py"], "review", [], 20)
            fresh = code_graph_mapper.status_for(root, cache, ["src/parser.py"])
            (source / "new_rule.py").write_text("def validate(value):\n    return value\n", encoding="utf-8")
            stale = code_graph_mapper.status_for(root, cache, ["src/parser.py"])
        self.assertEqual(fresh["status"], "fresh")
        self.assertEqual(stale["status"], "stale")
        self.assertIn("inventory changed", " ".join(stale["reasons"]).lower())

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
        self.assertEqual(report["next_step"], "Review the guided delivery plan, then approve or edit before implementation.")
        actions = {item["action"] for item in report["next_actions"]}
        self.assertIn("review", actions)
        self.assertIn("approve", actions)
        self.assertEqual(report["token_posture"]["mode"], "local_estimate")
        self.assertIn("recommended_check", report["setup_posture"])
        self.assertEqual(report["code_intelligence"]["default_engine_path"], ["lite", "v1", "v2"])
        self.assertIn("V3 is never default", report["code_intelligence"]["v3_rule"])
        self.assertIn("must not auto-run JDT", report["code_intelligence"]["auto_run_rule"])
        self.assertEqual(report["guided_delivery"]["mode"], "lean")
        self.assertIn("Lean delivery", {item["name"] for item in report["guided_delivery"]["selected"]})

    def test_start_compact_report_lists_selected_tailtrail_features(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report("fix zero quantity validation", root, ["src/order_service/validation.py"], "tailtrail")
            rendered = task_start.compact_start_report(report)

        self.assertIn("## Selected TailTrail features", rendered)
        self.assertIn("| Feature | When | Used for this task |", rendered)
        self.assertIn("| Navigator | Planning now |", rendered)
        self.assertIn("Requirement Completion Harness", rendered)
        self.assertIn("## Token posture", rendered)
        self.assertIn("Estimated focused context:", rendered)

    def test_start_focused_validation_uses_only_the_interpreter_when_pack_path_contains_tailtrail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            test_path = root / "tests" / "unit" / "test_validation.py"
            test_path.parent.mkdir(parents=True)
            test_path.write_text("import unittest\n", encoding="utf-8")
            command = task_start.focused_validation_command(
                root,
                [{"path": "tests/unit/test_validation.py"}],
                "python3 D:/PD/TailTrail_Test/tailtrail/scripts/tailtrail.py",
            )
        self.assertEqual(command, "python3 -m unittest discover -s tests/unit -p test_validation.py -v")

    def test_start_verbose_report_has_required_feature_and_evidence_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report("fix zero quantity validation", root, ["src/order_service/validation.py"], "tailtrail")
            report["planning_lock"] = task_start.planning_lock.create(root, report["goal"], "start-verbose-report")
            rendered = task_start.render_markdown(report, verbose=True)

        for heading in (
            "## Planning Lock",
            "## Start Here",
            "## Navigator Decision",
            "## Selected TailTrail features",
            "## Deferred TailTrail features",
            "## Guided Delivery",
            "## Validation",
            "## Evidence posture",
            "## Approval",
        ):
            self.assertIn(heading, rendered)

    def test_verbose_start_lists_every_impacted_file_without_a_verbose_hint(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            changed = [f"src/module_{index}.py" for index in range(9)]
            report = task_start.build_report("add a multi-file service feature", root, changed, "tailtrail")
            rendered = task_start.verbose_start_report(report)

        for path in changed:
            self.assertIn(f"`{path}`", rendered)
        self.assertNotIn("more in verbose Navigator output", rendered)

    def test_task_start_selects_multi_file_delivery_controls_without_auto_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report("add payment API workflow", root, ["src/api.py", "src/service.py"], "tailtrail")
            rendered = task_start.render_markdown(report)

        selected = {item["name"] for item in report["guided_delivery"]["selected"]}
        self.assertTrue({"Canonical requirements", "Requirement Completion Harness", "Architecture Fitness Harness", "Behaviour Harness"}.issubset(selected))
        self.assertIn("## Plan", rendered)
        self.assertIn("does not itself edit source", report["guided_delivery"]["execution_boundary"])

    def test_hands_free_multi_task_request_still_returns_a_program_plan_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report("tailtrail start, work on task 1 and task 2 using hands free mode", root, [], "tailtrail")

        selected = {item["name"] for item in report["guided_delivery"]["selected"]}
        self.assertEqual(report["guided_delivery"]["mode"], "guided-delivery")
        self.assertIn("Program Delivery Harness", selected)
        self.assertIn("propose feature requirements and dependency order", report["guided_delivery"]["stages"])
        self.assertTrue(report["guided_delivery"]["approval_required"])
        self.assertEqual(report["guided_delivery"]["hands_free_program"]["status"], "proposed")
        self.assertIn("no source implementation", report["guided_delivery"]["hands_free_program"]["first_active_slice"])
        self.assertIn("does not itself edit source", report["guided_delivery"]["execution_boundary"])

    def test_compact_hands_free_report_shows_requirement_boundary_and_program_slices(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report(
                "hands-free: add order cancellation, refund payment, release inventory, notify customers, retain an audit event, update API tests, and include rollout safety",
                root, [], "tailtrail",
            )
            rendered = task_start.compact_start_report(report)
        self.assertIn("**REQ-01:** Define the cancellation eligibility rule", rendered)
        self.assertIn("Issue one refund", rendered)
        self.assertIn("## Plan", rendered)
        self.assertIn("Proposed dependency order", rendered)
        self.assertIn("First active slice", rendered)
        self.assertNotIn("Inspect the validator", rendered)

    def test_hands_free_amendment_requirements_preserve_cancellation_without_becoming_cancellation_work(self) -> None:
        goal = (
            "hands-free: add an order-amendment capability. Before fulfilment a customer may change quantity and delivery address; "
            "after allocation quantity may only decrease and release excess inventory; after shipment only an authorized address correction is allowed. "
            "Use idempotent payment delta, audit, notification, API, tests, migration, CI, and rollout evidence. Preserve create-order and cancellation behavior."
        )
        with tempfile.TemporaryDirectory() as temp:
            report = task_start.build_report(goal, Path(temp), [], "tailtrail")

        requirements = report["guided_delivery"]["hands_free_program"]["feature_requirements"]
        statements = [item["statement"] for item in requirements]
        joined = " ".join(statements).lower()
        self.assertIn("amendment eligibility", joined)
        self.assertIn("authoritative order revision", joined)
        self.assertIn("stale concurrent amendment", joined)
        self.assertIn("excess reserved inventory", joined)
        self.assertIn("partial refund", joined)
        self.assertIn("create-order and cancellation behavior", joined)
        self.assertNotIn("eligible cancellation succeeds", joined)
        self.assertGreaterEqual(len(requirements), 10)
        self.assertIn("new Full-mode Planning Lock", report["aidlc_mode"]["full_escalation"]["reason"])

    def test_task_start_uses_only_explicit_run_evidence_for_correction_and_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root / ".tailtrail" / "runs" / "payment-retry"
            (run / "feedback").mkdir(parents=True)
            (run / "checkpoints").mkdir()
            (run / "recovery").mkdir()
            (run / "feedback" / "feedback-1.json").write_text(json.dumps({"packet": {"evidence": "worker proof missing"}}), encoding="utf-8")
            (run / "checkpoints" / "checkpoint-1.json").write_text(json.dumps({"drift": [{"classification": "regressed"}]}), encoding="utf-8")
            (run / "recovery" / "plan-1.json").write_text("{}", encoding="utf-8")
            report = task_start.build_report("fix payment retry", root, ["src/worker.py"], "tailtrail", "payment-retry")

        selected = {item["name"] for item in report["guided_delivery"]["selected"]}
        self.assertIn("Context Continuity Harness", selected)
        self.assertIn("Bounded Correction", selected)
        self.assertIn("Git Readiness / Recovery Boundary", selected)
        self.assertEqual(report["guided_delivery"]["run_signals"]["drift"], ["regressed"])

    def test_task_start_does_not_guess_prior_run_state_without_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".tailtrail" / "runs" / "other-task" / "feedback").mkdir(parents=True)
            (root / ".tailtrail" / "runs" / "other-task" / "feedback" / "feedback-1.json").write_text("{}", encoding="utf-8")
            report = task_start.build_report("fix payment retry", root, ["src/worker.py"], "tailtrail")

        selected = {item["name"] for item in report["guided_delivery"]["selected"]}
        self.assertNotIn("Context Continuity Harness", selected)
        self.assertEqual(report["guided_delivery"]["run_signals"]["status"], "not-requested")

    def test_task_start_keeps_evaluation_harness_available_for_simple_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report("fix typo in README", root, ["README.md"], "tailtrail")
            rendered = task_start.render_markdown(report)

        self.assertFalse(report["evaluation_posture"]["selected"])
        self.assertNotIn("Evaluation Harness", rendered)
        self.assertNotIn("Evaluation scenarios: `tailtrail eval scenario list`", rendered)
        self.assertNotIn("## Evaluation Harness\n\n- Selected: `true`", rendered)

    def test_task_start_selects_evaluation_harness_for_evidence_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report("show evaluation harness evidence", root, [], "tailtrail")
            rendered = task_start.render_markdown(report)

        self.assertTrue(report["evaluation_posture"]["selected"])
        self.assertEqual(report["evaluation_posture"]["scenario"], "validation-bug")
        self.assertIn("## Plan", rendered)
        self.assertNotIn("Evaluation scenarios:", rendered)

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
