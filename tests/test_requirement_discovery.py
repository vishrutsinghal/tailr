from __future__ import annotations

import importlib.util
import base64
import json
import subprocess
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
    sys.modules[name] = module; spec.loader.exec_module(module)
    return module


discovery = load("tailtrail_requirement_discovery_test", "scripts/requirement_discovery.py")
task_start = load("tailtrail_requirement_start_test", "scripts/task-start.py")
planning_lock = task_start.planning_lock


class RequirementDiscoveryTests(unittest.TestCase):
    def test_ui_symptom_and_pronoun_action_become_one_outcome_requirement(self) -> None:
        goal = (
            "in the push to dom page after the push to dom there is a banner "
            "**CloudWatch trace endpoint is not configured.** we need to remove it,"
        )

        interpreted = discovery.interpretation(goal)
        frame = discovery.scope_query_frame(goal, interpreted)
        rows = discovery.matrix(goal, ["src/pages/PushToDomPage.tsx"], interpreted)

        expected = 'Remove the "CloudWatch trace endpoint is not configured." banner from the push to dom page.'
        self.assertEqual(discovery.statements(goal), [expected])
        self.assertEqual([row["statement"] for row in rows], [expected])
        self.assertEqual(frame["requirements"][0]["query_terms"], ["remove", "banner", "push", "dom", "page"])
        self.assertEqual(frame["requirements"][0]["quoted_literals"], ["CloudWatch trace endpoint is not configured."])
        self.assertEqual(frame["requirements"][0]["intent_class"], "ui-visibility")
        self.assertEqual([clause["role"] for clause in interpreted["clauses"]], ["context", "outcome"])

    def test_ui_literal_contract_is_stable_across_markdown_presentation_wrappers(self) -> None:
        variants = [
            "CloudWatch trace endpoint is not configured.",
            "*CloudWatch trace endpoint is not configured.*",
            "_CloudWatch trace endpoint is not configured._",
            "**CloudWatch trace endpoint is not configured.**",
            "__CloudWatch trace endpoint is not configured.__",
            "`CloudWatch trace endpoint is not configured.`",
            "'CloudWatch trace endpoint is not configured.'",
            '"CloudWatch trace endpoint is not configured."',
        ]

        frames = [
            discovery.frames(
                f"in the push to dom page there is a banner {literal} we need to remove it"
            )
            for literal in variants
        ]

        self.assertTrue(all(frame == frames[0] for frame in frames[1:]))
        self.assertEqual(
            frames[0][0]["quoted_literals"],
            ["CloudWatch trace endpoint is not configured."],
        )

    def test_host_interpretation_is_goal_bound_and_excludes_private_reasoning(self) -> None:
        goal = "A warning is visible. Remove it."
        proposal = {
            "schema_version": "1",
            "type": "tailtrail-host-requirement-interpretation",
            "host": "codex",
            "goal": goal,
            "private_reasoning_excluded": True,
            "clauses": [
                {"clause_id": "C-01", "role": "context", "text": "A warning is visible."},
                {"clause_id": "C-02", "role": "outcome", "text": "Remove it."},
            ],
            "requirements": [{
                "display_id": "REQ-01",
                "statement": "Remove the visible warning.",
                "kind": "change",
                "source_clause_ids": ["C-01", "C-02"],
                "intent_terms": ["remove", "warning"],
                "quoted_literals": [],
                "intent_class": "ui-visibility",
                "confidence": "high",
            }],
            "material_questions": [],
        }

        interpreted = discovery.interpretation(goal, proposal, "codex")

        self.assertEqual(interpreted["source"], "host-assisted")
        self.assertEqual(interpreted["host"], "codex")
        self.assertEqual(interpreted["requirements"][0]["intent_terms"], ["remove", "warning"])
        with self.assertRaisesRegex(ValueError, "exact goal"):
            discovery.interpretation(goal + " changed", proposal, "codex")
        proposal["goal"] = goal + " changed"
        proposal["private_reasoning_excluded"] = False
        with self.assertRaisesRegex(ValueError, "private reasoning"):
            discovery.interpretation(goal + " changed", proposal, "codex")

    def test_host_interpretation_consumes_hash_bound_requirement_artifact(self) -> None:
        goal = "Add the scenarios described in the requirement artifact."
        content = "Cover pipeline_summary_v4 and step_summary end to end."
        digest = __import__("hashlib").sha256(content.encode("utf-8")).hexdigest()
        artifacts = [{
            "input_id": "IN-02",
            "locator": "/tmp/requirements.md",
            "sha256": digest,
            "size_bytes": len(content.encode("utf-8")),
            "content": content,
        }]
        proposal = {
            "schema_version": "1",
            "type": "tailtrail-host-requirement-interpretation",
            "host": "codex",
            "goal": goal,
            "private_reasoning_excluded": True,
            "clauses": [
                {"clause_id": "C-01", "role": "outcome", "text": goal},
                {
                    "clause_id": "C-02",
                    "role": "scope",
                    "text": content,
                    "source_input_id": "IN-02",
                },
            ],
            "artifact_evidence": [{
                "input_id": "IN-02",
                "sha256": digest,
                "source_clause_ids": ["C-02"],
            }],
            "requirements": [{
                "display_id": "REQ-01",
                "statement": "Add end-to-end scenarios for pipeline_summary_v4 and step_summary.",
                "source_clause_ids": ["C-01", "C-02"],
                "intent_terms": ["add", "scenarios", "pipeline_summary_v4", "step_summary"],
                "confidence": "high",
            }],
            "material_questions": [],
        }

        interpreted = discovery.interpretation(goal, proposal, "codex", artifacts)

        self.assertEqual(interpreted["artifact_evidence"][0]["sha256"], digest)
        self.assertEqual(interpreted["clauses"][1]["source_input_id"], "IN-02")
        proposal["artifact_evidence"] = []
        with self.assertRaisesRegex(ValueError, "every required artifact"):
            discovery.interpretation(goal, proposal, "codex", artifacts)

    def test_host_general_class_cannot_erase_explicit_ui_visibility_intent(self) -> None:
        goal = (
            "in the push to dom page there is a banner "
            "CloudWatch trace endpoint is not configured. we need to remove it"
        )
        proposal = {
            "schema_version": "1",
            "type": "tailtrail-host-requirement-interpretation",
            "host": "codex",
            "goal": goal,
            "private_reasoning_excluded": True,
            "clauses": [
                {"clause_id": "C-01", "role": "context", "text": "in the push to dom page there is a banner CloudWatch trace endpoint is not configured."},
                {"clause_id": "C-02", "role": "outcome", "text": "we need to remove it"},
            ],
            "requirements": [{
                "display_id": "REQ-01",
                "statement": "Remove the CloudWatch trace endpoint configuration banner from the Push to DOM page.",
                "kind": "change",
                "source_clause_ids": ["C-01", "C-02"],
                "intent_terms": ["push", "dom", "remove"],
                "quoted_literals": ["CloudWatch trace endpoint is not configured."],
                "intent_class": "general",
                "confidence": "high",
            }],
            "material_questions": [],
        }

        interpreted = discovery.interpretation(goal, proposal, "codex")
        frame = discovery.scope_query_frame(goal, interpreted)

        self.assertEqual("ui-visibility", interpreted["requirements"][0]["intent_class"])
        self.assertEqual("ui-visibility", frame["requirements"][0]["intent_class"])

    def test_cli_accepts_one_typed_host_interpretation_for_every_start_projection(self) -> None:
        goal = "A warning is visible. Remove it."
        proposal = {
            "schema_version": "1",
            "type": "tailtrail-host-requirement-interpretation",
            "host": "codex",
            "goal": goal,
            "private_reasoning_excluded": True,
            "clauses": [
                {"clause_id": "C-01", "role": "context", "text": "A warning is visible."},
                {"clause_id": "C-02", "role": "outcome", "text": "Remove it."},
            ],
            "requirements": [{
                "display_id": "REQ-01",
                "statement": "Remove the visible warning.",
                "kind": "change",
                "source_clause_ids": ["C-01", "C-02"],
                "intent_terms": ["remove", "warning"],
                "quoted_literals": [],
                "intent_class": "ui-visibility",
                "confidence": "high",
            }],
            "material_questions": [],
        }
        encoded = base64.b64encode(json.dumps(proposal).encode("utf-8")).decode("ascii")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src" / "WarningPanel.tsx"
            source.parent.mkdir(parents=True)
            source.write_text("export const WarningPanel = () => <div>warning</div>;\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "task-start.py"),
                    goal,
                    "--root", str(root),
                    "--changed", "src/WarningPanel.tsx",
                    "--host", "codex",
                    "--aidlc", "off",
                    "--no-planning-lock",
                    "--requirement-interpretation-base64", encoded,
                    "--format", "json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        report = json.loads(completed.stdout)
        self.assertEqual(report["navigator"]["requirement_interpretation"]["source"], "host-assisted")
        self.assertEqual(
            [row["statement"] for row in report["navigator"]["requirement_matrix"]],
            ["Remove the visible warning."],
        )
        rendered = task_start.render_markdown(report)
        self.assertIn("Interpretation evidence", rendered)
        self.assertIn("host-assisted by `codex`", rendered)

    def test_host_cannot_promote_context_only_wording_to_a_requirement(self) -> None:
        goal = "A warning is visible."
        proposal = {
            "schema_version": "1",
            "type": "tailtrail-host-requirement-interpretation",
            "host": "codex",
            "goal": goal,
            "private_reasoning_excluded": True,
            "clauses": [{"clause_id": "C-01", "role": "context", "text": goal}],
            "requirements": [{
                "display_id": "REQ-01",
                "statement": "Configure the warning integration.",
                "source_clause_ids": ["C-01"],
                "intent_terms": ["configure", "warning"],
            }],
            "material_questions": [],
        }
        with self.assertRaisesRegex(ValueError, "outcome, constraint, or scope"):
            discovery.interpretation(goal, proposal, "codex")

    def test_host_cannot_promote_quoted_message_words_to_semantic_scope_terms(self) -> None:
        goal = "The banner says 'CloudWatch endpoint missing'. Remove the banner."
        proposal = {
            "schema_version": "1",
            "type": "tailtrail-host-requirement-interpretation",
            "host": "codex",
            "goal": goal,
            "private_reasoning_excluded": True,
            "clauses": [
                {"clause_id": "C-01", "role": "context", "text": "The banner says 'CloudWatch endpoint missing'."},
                {"clause_id": "C-02", "role": "outcome", "text": "Remove the banner."},
            ],
            "requirements": [{
                "display_id": "REQ-01",
                "statement": "Remove the CloudWatch warning banner.",
                "source_clause_ids": ["C-01", "C-02"],
                "intent_terms": ["remove", "banner", "cloudwatch"],
                "quoted_literals": ["CloudWatch endpoint missing"],
                "intent_class": "ui-visibility",
            }],
            "material_questions": [],
        }
        with self.assertRaisesRegex(ValueError, "outside quoted literals"):
            discovery.interpretation(goal, proposal, "codex")

    def test_conversational_ui_progression_becomes_atomic_change_and_preservation_rows(self) -> None:
        goal = (
            "when user clicks on generate event flow the screen moves to event flow but "
            "when user clicks on validate it just showing the message 'Audit event inputs are valid' "
            "but it should also move to validate page, similarly for copy json it should message "
            "like json copied and move the screen to session summary page"
        )

        self.assertEqual(
            discovery.statements(goal),
            [
                "When the user clicks validate and validation succeeds, preserve the message "
                "'Audit event inputs are valid' and move to validate page.",
                "When the user clicks copy json and the copy succeeds, show the message "
                "'json copied' and move to session summary page.",
                "Preserve the existing generate event flow transition to event flow.",
            ],
        )

    def test_soft_wrapped_prose_is_stable_across_lf_crlf_and_cr(self) -> None:
        variants = [
            "Add delivery-address validation without breaking valid\naddresses.",
            "Add delivery-address validation without breaking valid\r\naddresses.",
            "Add delivery-address validation without breaking valid\raddresses.",
        ]

        framed = [discovery.frames(goal) for goal in variants]

        self.assertEqual(framed[0], framed[1])
        self.assertEqual(framed[1], framed[2])
        self.assertEqual(
            framed[0],
            [
                {
                    "display_id": "REQ-01",
                    "requirement_id": "req-frame-c08d2a5a5e24",
                    "statement": "Add delivery-address validation without breaking valid addresses.",
                    "query_terms": [
                        "add",
                        "delivery",
                        "address",
                        "validation",
                        "breaking",
                        "valid",
                        "addresses",
                    ],
                }
            ],
        )

    def test_soft_wrap_after_punctuation_is_not_a_requirement_boundary(self) -> None:
        self.assertEqual(
            discovery.statements(
                "Add delivery-address validation without breaking valid.\naddresses."
            ),
            ["Add delivery-address validation without breaking valid. addresses."],
        )
        self.assertEqual(
            discovery.statements(
                "Add address validation. Preserve valid addresses."
            ),
            ["Add address validation.", "Preserve valid addresses."],
        )

    def test_debug_query_frame_excludes_reproduction_example_and_loose_prefix(self) -> None:
        goal = """debug an - issue `fix multiline requirement splitting.`

Example:

## Requirements

- **REQ-01:** Add delivery-address validation without breaking valid.
- **REQ-02:** Addresses.

##

there are 2 requirements but ideally it should be 1.
"""
        frame = discovery.debug_scope_query_frame(goal)

        self.assertEqual(len(frame["requirements"]), 1)
        self.assertEqual(frame["requirements"][0]["display_id"], "REQ-DEBUG-01")
        self.assertEqual(frame["requirements"][0]["statement"], "Fix multiline requirement splitting.")
        self.assertEqual(
            frame["requirements"][0]["query_terms"],
            ["fix", "multiline", "requirement", "splitting"],
        )

    def test_long_conversational_ui_request_retains_decisive_terms(self) -> None:
        goal = (
            "there is an issue when user clicks on generate event flow the screen moves "
            "to event flow but when user clicks on validate it just showing the message "
            "'Audit event inputs are valid' but it should also move to validate page, "
            "similarly for copy json it should move to session summary page"
        )

        terms = discovery.frames(goal)[0]["query_terms"]

        self.assertEqual(
            terms,
            [
                "generate", "event", "flow", "validate", "audit", "inputs",
                "valid", "copy", "json", "session", "summary", "there",
            ],
        )
        self.assertNotIn("but", terms)
        self.assertNotIn("user", terms)

    def test_explicit_lists_paragraphs_and_semicolons_remain_boundaries(self) -> None:
        cases = {
            "bullets": (
                "- Add address validation\n- Preserve valid addresses",
                ["Add address validation.", "Preserve valid addresses."],
            ),
            "numbered": (
                "1. Add address validation\n2) Preserve valid addresses",
                ["Add address validation.", "Preserve valid addresses."],
            ),
            "paragraphs": (
                "Add address validation without\nbreaking valid addresses\n\nPreserve the existing error contract",
                [
                    "Add address validation without breaking valid addresses.",
                    "Preserve the existing error contract.",
                ],
            ),
            "semicolon": (
                "Add address validation; preserve valid addresses",
                ["Add address validation.", "Preserve valid addresses."],
            ),
        }

        for label, (goal, expected) in cases.items():
            with self.subTest(case=label):
                self.assertEqual(discovery.statements(goal), expected)

    def test_mixed_structure_joins_only_soft_wraps(self) -> None:
        goal = """Add address validation without
breaking valid addresses.

- Preserve the existing error
  contract
- Add focused unit proof; retain integration behavior"""

        self.assertEqual(
            discovery.statements(goal),
            [
                "Add address validation without breaking valid addresses.",
                "Preserve the existing error contract.",
                "Add focused unit proof.",
                "Retain integration behavior.",
            ],
        )

    def test_query_frame_drives_navigator_without_replacing_exact_goal(self) -> None:
        goal = "Add delivery-address validation without breaking valid\r\naddresses."
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report(goal, root, ["src/address_validation.py"], "tailtrail")

        frame = report["navigator"]["requirement_query_frame"]
        matrix = report["navigator"]["requirement_matrix"]
        self.assertEqual(report["goal"], goal)
        self.assertTrue(frame["exact_goal_preserved"])
        self.assertEqual(
            [item["statement"] for item in frame["requirements"]],
            [item["statement"] for item in matrix],
        )
        self.assertEqual(
            [item["requirement_id"] for item in frame["requirements"]],
            [item["requirement_id"] for item in matrix],
        )
        self.assertEqual(frame["requirements"][0]["query_terms"], matrix[0]["query_terms"])

    def test_all_start_surfaces_lock_and_anchor_share_identical_rows(self) -> None:
        goal = """Add address validation without
breaking valid addresses.

- Preserve the existing error contract
- Add focused unit proof"""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report(goal, root, ["src/address_validation.py"], "tailtrail")
            report["planning_lock"] = planning_lock.create(root, goal, "ns1-surface-run")
            rendered = {
                "quick": task_start.quick_start_report(report),
                "compact": task_start.compact_start_report(report),
                "normal": task_start.navigator.markdown(report["navigator"]),
                "verbose": task_start.verbose_start_report(report),
                "planning-lock": task_start.render_markdown(report, presentation_mode="guided"),
            }
            planning_lock.save_start_report(root, "ns1-surface-run", report)
            saved = planning_lock.active_start_report(root, "ns1-surface-run")
            activated = planning_lock.activate(root, "ns1-surface-run", True)
            approved = json.loads((root / activated["execution_handoff"]["anchor"]).read_text(encoding="utf-8"))

        matrix = report["navigator"]["requirement_matrix"]
        for surface, output in rendered.items():
            with self.subTest(surface=surface):
                for row in matrix:
                    self.assertIn(row["display_id"], output)
                    self.assertIn(row["statement"], output)
        self.assertEqual(saved["goal"], goal)
        self.assertEqual(saved["report"]["navigator"]["requirement_matrix"], matrix)
        self.assertEqual(
            [
                (row["display_id"], row["requirement_id"], row["statement"], row["query_terms"])
                for row in approved["requirements"]
            ],
            [
                (row["display_id"], row["requirement_id"], row["statement"], row["query_terms"])
                for row in matrix
            ],
        )

    def test_workflow_routing_prefix_is_not_a_delivery_requirement(self) -> None:
        statements = discovery.statements(
            "using AIDLC, add delivery-address validation across the API and service. "
            "Preserve existing create-order behavior."
        )
        self.assertNotIn("Using AIDLC.", statements)
        self.assertEqual(
            statements,
            [
                "Add delivery-address validation across the API and service.",
                "Preserve existing create-order behavior.",
            ],
        )

    def test_bullets_sentences_and_semicolons_become_stable_requirement_rows(self) -> None:
        goal = """Add cancellation eligibility.
- Release inventory exactly once
- Preserve shipped-order behavior; update the API contract."""
        rows = discovery.matrix(goal, ["src/service.py"])
        self.assertEqual([row["display_id"] for row in rows], ["REQ-01", "REQ-02", "REQ-03", "REQ-04"])
        self.assertEqual(rows[2]["kind"], "preserve")
        self.assertTrue(all(row["likely_paths"] == ["src/service.py"] for row in rows))

    def test_shared_subject_action_list_splits_without_splitting_object_lists(self) -> None:
        goal = "Cancellation releases stock, refunds payment, sends one notification, retains an audit event with actor, reason, and revision, and updates the API contract and tests."
        statements = discovery.statements(goal)
        self.assertEqual(len(statements), 5)
        self.assertIn("Cancellation refunds payment.", statements)
        self.assertIn("actor, reason, and revision", statements[3])
        self.assertIn("API contract and tests", statements[4])

    def test_compact_and_verbose_start_render_the_same_segregated_matrix(self) -> None:
        goal = "Add cancellation eligibility; release inventory; preserve shipped orders; update the API contract and add integration tests."
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report(goal, root, ["src/service.py"], "tailtrail")
            compact = task_start.compact_start_report(report)
            verbose = task_start.verbose_start_report(report)
        self.assertGreaterEqual(len(report["navigator"]["requirement_matrix"]), 5)
        self.assertEqual(report["guided_delivery"]["mode"], "guided-delivery")
        self.assertIn("Requirement Completion Harness", [item["name"] for item in report["guided_delivery"]["selected"]])
        for index in range(1, 6):
            label = f"REQ-{index:02d}"
            self.assertIn(label, compact); self.assertIn(label, verbose)
        self.assertIn("map and implement one approved requirement at a time", compact)
        self.assertIn("map and implement one approved requirement at a time", verbose)

    def test_quick_guided_and_expert_are_distinct_views_of_one_plan(self) -> None:
        goal = "Add cancellation eligibility; release inventory; preserve shipped orders; add integration proof."
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report(goal, root, ["src/service.py"], "tailtrail")
            report["planning_lock"] = planning_lock.create(root, goal, "presentation-run")
            quick = task_start.render_markdown(report, presentation_mode="quick")
            guided = task_start.render_markdown(report, presentation_mode="guided")
            expert = task_start.render_markdown(report, presentation_mode="expert")
            verbose = [
                task_start.render_markdown(report, presentation_mode=mode, verbose=True)
                for mode in ("quick", "guided", "expert")
            ]
        for mode, rendered in (("quick", quick), ("guided", guided), ("expert", expert)):
            self.assertIn(f"**Plan detail:** `{mode.title()}` (legacy compatibility override)", rendered)
            for heading in ("Planning Lock", "Requirements", "Selected TailTrail features", "Approval"):
                self.assertIn(heading, rendered)
        self.assertLess(len(quick), len(guided))
        self.assertLess(len(guided), len(expert))
        normalized = [item.replace("`quick`", "`mode`").replace("`guided`", "`mode`").replace("`expert`", "`mode`") for item in verbose]
        self.assertEqual(normalized[0], normalized[1])
        self.assertEqual(normalized[1], normalized[2])

    def test_approved_anchor_uses_the_displayed_requirement_rows(self) -> None:
        goal = "Add cancellation eligibility; release inventory; preserve shipped orders."
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report(goal, root, ["src/service.py"], "tailtrail")
            report["planning_lock"] = planning_lock.create(root, goal, "segregated-run")
            planning_lock.save_start_report(root, "segregated-run", report)
            activated = planning_lock.activate(root, "segregated-run", True)
            approved = json.loads((root / activated["execution_handoff"]["anchor"]).read_text(encoding="utf-8"))
        displayed = [row["statement"] for row in report["navigator"]["requirement_matrix"]]
        self.assertEqual([row["statement"] for row in approved["requirements"]], displayed)
        self.assertEqual(len(activated["execution_handoff"]["active_requirements"]), len(displayed))

    def test_hands_free_scope_program_and_plan_share_one_canonical_requirement_set(self) -> None:
        goal = (
            "hands-free: add tests for pipeline_summary_v4, step_summary, "
            "task_summary, and pipeline_event_details end to end"
        )
        with tempfile.TemporaryDirectory() as temp:
            report = task_start.build_report(goal, Path(temp), [], "tailtrail")

        plan = report["navigator"]
        canonical = plan["canonical_requirements"]
        expected = [
            (row["display_id"], row["statement"])
            for row in canonical["requirements"]
        ]
        self.assertEqual(
            expected,
            [(row["display_id"], row["statement"]) for row in plan["requirement_query_frame"]["requirements"]],
        )
        self.assertEqual(
            expected,
            [(row["display_id"], row["statement"]) for row in plan["requirement_matrix"]],
        )
        self.assertEqual(
            expected,
            [
                (row["display_id"], row["statement"])
                for row in report["guided_delivery"]["hands_free_program"]["feature_requirements"]
            ],
        )
        self.assertTrue(canonical["fingerprint"].startswith("sha256:"))
        self.assertEqual(
            {canonical["fingerprint"]},
            {row["canonical_requirement_set_fingerprint"] for row in plan["requirement_matrix"]},
        )

    def test_canonical_requirement_binding_rejects_downstream_rewording(self) -> None:
        goal = "Add order validation."
        interpreted = discovery.interpretation(goal)
        canonical = discovery.canonical_set(goal, interpreted)
        matrix = discovery.matrix(goal, [], interpreted)
        matrix[0]["statement"] = "Replace order validation."

        with self.assertRaisesRegex(ValueError, "canonical requirement set"):
            discovery.bind_canonical_matrix(matrix, canonical)


if __name__ == "__main__":
    unittest.main()
