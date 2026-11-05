from __future__ import annotations

import importlib.util
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.intake_pipeline import IntakePipeline


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tailtrail_question_orchestrator", ROOT / "scripts" / "question-orchestrator.py")
assert SPEC and SPEC.loader
orchestrator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(orchestrator)


def question(**overrides):
    payload = {
        "id": "OQ1",
        "question": "Which normalization behavior is required?",
        "options": [
            {"id": "A", "text": "Trim outer whitespace"},
            {"id": "B", "text": "Preserve exact input"},
            {"id": "Other", "text": "Other (describe)"},
        ],
        "recommended": "Trim outer whitespace",
        "reasoning": "The user requested a normalization decision before implementation.",
    }
    payload.update(overrides)
    return payload


def proof_adequacy(
    path: str,
    command: str,
    *,
    role: str = "unchanged-proof",
    outcome: str = "pass",
) -> str:
    return json.dumps({
        "path": path,
        "role": role,
        "test_cases": [f"focused cases in {path}"],
        "fixtures": ["declared fixtures were inspected"],
        "assertions": ["assertions cover the stated behavior"],
        "baseline": {
            "command": command,
            "outcome": outcome,
            "observed": "baseline result recorded before planning",
        },
    })


class QuestionOrchestratorTests(unittest.TestCase):
    def context(self):
        return orchestrator.prepare_context(
            "start-test",
            "standard",
            "Add address validation and clarify normalization.",
            [
                {"display_id": "REQ-01", "statement": "Add address validation."},
                {"display_id": "REQ-02", "statement": "Preserve existing client behavior.", "kind": "preserve"},
            ],
            {
                "architecture_plan": {
                    "scope_roles": [
                        {"path": "src/orders/validation.py", "role": "validation boundary"},
                    ]
                },
                "focused_validation_plan": {"tiers": ["unit", "integration"]},
            },
        )

    def test_context_preserves_authority_and_labels_inventory_as_hypothesis(self):
        context = self.context()
        self.assertEqual(context["question_authority"], "official-ai-dlc-pack")
        self.assertFalse(context["question_policy"]["source_bodies_read"])
        inventory = next(item for item in context["known_facts"] if item["fact_id"].startswith("INV-"))
        self.assertEqual(inventory["confidence"], "repository-inventory-hypothesis")
        self.assertIn("src/orders/validation.py", inventory["evidence"])

    def test_quality_gate_adds_requirement_and_decision_traceability(self):
        result = orchestrator.evaluate_questions([question(requirement_ids=["REQ-01"])], self.context(), "official-ai-dlc-pack")
        saved = result["questions"][0]
        self.assertEqual(result["quality"]["status"], "passed")
        self.assertEqual(saved["authority"], "official-ai-dlc-pack")
        self.assertEqual(saved["requirement_ids"], ["REQ-01"])
        self.assertEqual(saved["decision_class"], "user-decision")
        self.assertIn("acceptance-criteria", saved["decision_impact"])

    def test_quality_gate_rejects_duplicate_questions(self):
        with self.assertRaisesRegex(ValueError, "duplicates another question"):
            orchestrator.evaluate_questions([question(), question(id="OQ2")], self.context(), "official-ai-dlc-pack")

    def test_repository_claim_requires_explicit_evidence(self):
        asserted = question(reasoning="The existing API uses structured address fields and therefore option A is compatible.")
        with self.assertRaisesRegex(ValueError, "explicit evidence_refs"):
            orchestrator.evaluate_questions([asserted], self.context(), "official-ai-dlc-pack")

        asserted["evidence_refs"] = ["saved-investigation:api-address-shape"]
        asserted["requirement_ids"] = ["REQ-01"]
        result = orchestrator.evaluate_questions([asserted], self.context(), "official-ai-dlc-pack")
        self.assertEqual(result["questions"][0]["evidence_refs"], ["saved-investigation:api-address-shape"])

    def test_conditional_reuse_advice_does_not_claim_repository_evidence(self):
        conditional = question(
            recommended="Reuse an existing action when the target project provides one.",
            reasoning="This keeps the change bounded without claiming that such an action exists.",
        )

        result = orchestrator.evaluate_questions([conditional], self.context(), "local-lite")

        self.assertEqual(result["quality"]["status"], "passed")

    def test_navigator_intake_issues_and_records_direct_answer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            intake = orchestrator.NavigatorIntake(root)
            from scripts.intake_pipeline import IntakePipeline

            run = IntakePipeline(root).create_run("collect owner", "existing-code-change")
            question = intake.issue_question(
                run["run_id"],
                "implementation-owner",
                {"id": "Q1", "question": "Which path owns the behavior?"},
            )
            answer = intake.record_direct_answer(
                run["run_id"],
                "implementation-owner",
                "scripts/question-orchestrator.py",
                question_id=question["payload"]["question_id"],
            )

            events_path = root / ".tailtrail" / "intake" / run["run_id"] / "events.jsonl"
            events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual([event["event_type"] for event in events], ["question-issued", "answer-recorded"])
        self.assertEqual(answer["payload"]["source"], "direct-question")

    def test_narration_answer_keeps_observation_and_answer_correlation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            intake = orchestrator.NavigatorIntake(root)
            from scripts.intake_pipeline import IntakePipeline

            run = IntakePipeline(root).create_run("collect owner", "existing-code-change")
            answer = intake.record_narration_answer(
                run["run_id"],
                "implementation-owner",
                "scripts/question-orchestrator.py",
                "The orchestrator should own the question exchange.",
            )

            events_path = root / ".tailtrail" / "intake" / run["run_id"] / "events.jsonl"
            events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual([event["event_type"] for event in events], ["host-observation-recorded", "answer-recorded"])
        self.assertEqual(answer["payload"]["source"], "narration-observation")
        self.assertEqual(answer["payload"]["observation_id"], events[0]["payload"]["observation_id"])

    def test_host_protocol_profiles_questions_and_clarification_are_bounded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            intake = orchestrator.NavigatorIntake(root)
            protocol = orchestrator.NavigatorHostProtocol(intake)
            documentation = protocol.profile_task("Update the guide", paths=["docs/guide.md"])
            feature = protocol.profile_task("Create a new feature", change_intent="new-feature")
            self.assertEqual(documentation["profile"], "documentation-only")
            self.assertEqual(feature["profile"], "new-feature")
            self.assertLess(
                len(protocol.plan_questions(documentation["profile"])),
                len(protocol.plan_questions(feature["profile"])),
            )

            run = IntakePipeline(root).create_run("collect feature context", "new-feature")
            issued = protocol.issue_profile_questions(run["run_id"], feature["profile"])
            self.assertEqual(len(issued), protocol.max_questions_per_round)
            self.assertNotEqual(issued[0]["field_id"], issued[0]["question_id"])

            candidate = protocol.record_direct_candidate(run["run_id"], issued[0]["question_id"], " src/new_feature.py ")
            host_claim = protocol.evidence_check(candidate, {"outcome": "accepted", "verified_by": "host"})
            self.assertEqual(host_claim["state"], "clarification-required")
            self.assertFalse(host_claim["authority_granted"])

            for _ in range(protocol.max_clarification_rounds):
                route = protocol.clarification_route(run["run_id"], feature["profile"], {issued[0]["field_id"]})
                self.assertEqual(route["state"], "awaiting-clarification")
                self.assertLessEqual(len(route["questions"]), protocol.max_questions_per_round)
            dead_end = protocol.clarification_route(run["run_id"], feature["profile"], {issued[0]["field_id"]})
            self.assertEqual(dead_end["state"], "user-decision-required")

    def test_host_protocol_narration_stays_candidate_until_navigator_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            intake = orchestrator.NavigatorIntake(root)
            protocol = orchestrator.NavigatorHostProtocol(intake)
            run = IntakePipeline(root).create_run("collect feature context", "new-feature")
            result = protocol.ingest_narration(
                run["run_id"],
                "new-feature",
                "The public route is the command handler.",
                [{"field_id": "public-route", "value": " command handler "}],
            )

            candidate = result["candidates"][0]
            self.assertEqual(candidate["state"], "mapped-to-profile-field")
            self.assertIsNone(candidate["question_id"])
            self.assertFalse(candidate["authority_granted"])
            accepted = protocol.evidence_check(candidate, {"outcome": "accepted", "verified_by": "navigator"})
            self.assertEqual(accepted["state"], "accepted")
            self.assertFalse(accepted["authority_granted"])
            self.assertFalse(accepted["finalization_allowed"])

    def test_public_intake_mints_readiness_and_emits_exact_start_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "work.py").write_text("def run():\n    return 1\n", encoding="utf-8")
            (root / "tests" / "test_work.py").write_text("def test_work():\n    assert True\n", encoding="utf-8")
            goal = "Extend the existing widget behavior while preserving unrelated behavior."
            contract = {
                "schema_version": "1",
                "type": "tailtrail-host-input-contract",
                "run_id": "",
                "contract_id": "ctr-public-intake",
                "profile": "existing-code change",
                "change_intent": "refactor",
                "request_mode": "implementation",
                "behavior_surface": "internal",
                "paths": [
                    {"path": "src/work.py", "role": "existing-implementation-owner"},
                    {"path": "tests/test_work.py", "role": "existing-proof-path"},
                ],
                "criteria": {
                    "positive": ["The widget returns the revised result."],
                    "negative": ["Unrelated behavior is unchanged."],
                },
                "proof": {"command": "python3 -m unittest tests.test_work", "tiers": ["unit"]},
                "private_reasoning_excluded": True,
            }
            opened = orchestrator.public_intake_open(root, goal, contract, host="codex", aidlc="off")
            values = {
                "expected-behavior": "The widget returns the revised result.",
                "existing-owner": "src/work.py",
                "proof-command": "python3 -m unittest tests.test_work",
                "proof-adequacy-002": proof_adequacy(
                    "tests/test_work.py", "python3 -m unittest tests.test_work"
                ),
            }
            candidates = orchestrator.public_intake_record(
                root,
                opened["run_id"],
                [
                    {"question_id": row["question_id"], "value": values[row["field_id"]]}
                    for row in opened["mandatory_questions"]
                ],
            )
            answer_ids = {row["field_id"]: row["answer_id"] for row in candidates["candidates"]}
            with self.assertRaisesRegex(ValueError, "planning readiness is incomplete"):
                orchestrator.public_intake_finalize(root, opened["run_id"], {})
            validated = orchestrator.public_intake_validate(
                root,
                opened["run_id"],
                [
                    {"answer_id": answer_ids["expected-behavior"], "evidence_paths": ["src/work.py"]},
                    {"answer_id": answer_ids["existing-owner"], "evidence_paths": ["src/work.py"]},
                    {"answer_id": answer_ids["proof-command"], "evidence_paths": ["tests/test_work.py"]},
                    {"answer_id": answer_ids["proof-adequacy-002"], "evidence_paths": ["tests/test_work.py"]},
                ],
            )
            self.assertTrue(validated["completeness"]["complete"])
            source_ids = list(answer_ids.values())
            with self.assertRaisesRegex(ValueError, "requires explicit requirement_kind"):
                orchestrator.public_intake_finalize(
                    root,
                    opened["run_id"],
                    {"operational_bindings": {"requirements": [{
                        "requirement_uid": "req-missing-kind",
                        "statement": goal,
                    }]}},
                )
            result = orchestrator.public_intake_finalize(
                root,
                opened["run_id"],
                {
                    "operational_bindings": {
                        "requirements": [{
                            "requirement_uid": "req-public-intake",
                            "statement": goal,
                            "requirement_kind": "change",
                            "requirement_kind_source_answer_ids": [answer_ids["expected-behavior"]],
                            "source_answer_ids": source_ids,
                            "profile_fields": list(values),
                            "semantic_delta": "validated",
                            "dependencies_checked": True,
                            "path_bindings": [{
                                "path": "src/work.py",
                                "role": "implementation-owner",
                                "existing": True,
                                "new_file_verdict": "not-applicable",
                                "source_answer_ids": [answer_ids["existing-owner"]],
                            }],
                            "proof_bindings": [{
                                "path": "tests/test_work.py",
                                "command": values["proof-command"],
                                "tier": "unit",
                                "asserted_behavior": "The revised widget behavior is proven.",
                                "source_answer_id": answer_ids["proof-command"],
                            }],
                            "criteria": {
                                "positive": contract["criteria"]["positive"],
                                "negative": contract["criteria"]["negative"],
                                "source_answer_ids": [answer_ids["expected-behavior"]],
                            },
                            "correction_premise": {
                                "status": "not-applicable",
                                "source_answer_ids": [answer_ids["expected-behavior"]],
                            },
                        }],
                    },
                },
            )

            self.assertEqual(result["status"], "planning-readiness")
            proof = result["receipt"]["operational_packet"]["requirements"][0]["proof_bindings"][0]
            self.assertEqual(proof["proof_adequacy"]["role"], "unchanged-proof")
            self.assertEqual(proof["proof_adequacy"]["baseline"]["outcome"], "pass")
            self.assertTrue(Path(result["receipt_path"]).is_file())
            self.assertIn("--planning-readiness-receipt-file", result["retry_command"])
            self.assertIn("--host-contract-file", result["retry_command"])
            self.assertIn("--changed src/work.py", result["retry_command"])
            self.assertIn("--host codex", result["retry_command"])
            retry = shlex.split(result["retry_command"])
            executed = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), *retry[1:]],
                cwd=root, text=True, capture_output=True, check=False, timeout=120,
            )
            self.assertNotIn("# TailTrail Planning Readiness Required", executed.stdout)
            self.assertNotIn("planning-readiness-required", executed.stdout)
            self.assertIn("Proof intent", executed.stdout)
            self.assertIn("`unchanged-proof`", executed.stdout)
            report_paths = list((root / ".tailtrail" / "runs").glob("*/planning/start-report-v1.json"))
            self.assertEqual(len(report_paths), 1)
            report = json.loads(report_paths[0].read_text(encoding="utf-8"))["report"]
            requirement = report["navigator"]["requirement_matrix"][0]
            self.assertEqual(requirement["kind"], "change")
            self.assertEqual(
                requirement["requirement_kind_authority"],
                "validated-operational-binding",
            )
            validation = requirement["validation_contract"]
            self.assertTrue(validation["proof_adequacy_required"])
            self.assertEqual(validation["editable_paths"], [])

    def test_readiness_receipt_prevents_goal_resplitting_and_reopens_no_scope_question(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "context.py").write_text("VALUE = 1\n", encoding="utf-8")
            goal = (
                "Add one package resolver with deterministic offline provider selection; "
                "preserve existing resource behavior and exclude edits to context.py."
            )
            command = "python3 -m unittest tests.test_new_work"
            contract = {
                "schema_version": "1",
                "type": "tailtrail-host-input-contract",
                "run_id": "",
                "contract_id": "ctr-readiness-canonical-projection",
                "profile": "new feature",
                "change_intent": "new-capability",
                "request_mode": "implementation",
                "behavior_surface": "internal",
                "paths": [
                    {"path": "src/new_work.py", "role": "proposed-implementation-owner"},
                    {"path": "src/context.py", "role": "inspection-input"},
                    {"path": "tests/test_new_work.py", "role": "proposed-proof-path"},
                ],
                "criteria": {
                    "positive": ["The resolver selects providers deterministically offline."],
                    "negative": ["The existing context module remains unchanged."],
                },
                "proof": {"command": command, "tiers": ["unit"]},
                "private_reasoning_excluded": True,
            }
            opened = orchestrator.public_intake_open(
                root, goal, contract, host="codex", aidlc="off"
            )
            values = {
                "proposed-owner": "src/new_work.py",
                "public-route": "src/new_work.py",
                "proof-command": command,
                "proof-adequacy-003": proof_adequacy(
                    "tests/test_new_work.py", command, role="new-proof", outcome="not-run"
                ),
            }
            recorded = orchestrator.public_intake_record(root, opened["run_id"], [{
                "question_id": row["question_id"],
                "value": row.get("expected_value", values.get(row["field_id"])),
            } for row in opened["mandatory_questions"]])
            answers = {row["field_id"]: row["answer_id"] for row in recorded["candidates"]}
            orchestrator.public_intake_validate(root, opened["run_id"], [{
                "answer_id": row["answer_id"],
                "evidence_paths": ["src/context.py"],
            } for row in recorded["candidates"]])
            result = orchestrator.public_intake_finalize(root, opened["run_id"], {
                "operational_bindings": {"requirements": [{
                    "requirement_uid": "req-canonical-resolver",
                    "statement": goal,
                    "requirement_kind": "change",
                    "requirement_kind_source_answer_ids": [answers["public-route"]],
                    "source_answer_ids": list(answers.values()),
                    "profile_fields": list(answers),
                    "semantic_delta": "validated",
                    "dependencies_checked": True,
                    "path_bindings": [
                        {
                            "path": "src/new_work.py",
                            "role": "implementation-owner",
                            "existing": False,
                            "host_declared": True,
                            "new_file_verdict": "new-confirmed",
                            "ownership_evidence": "The validated intake assigns the new resolver concern to this path.",
                            "source_answer_ids": [answers["proposed-owner"], answers["public-route"]],
                        },
                        {
                            "path": "src/context.py",
                            "role": "inspection-input",
                            "existing": True,
                            "new_file_verdict": "not-applicable",
                            "source_answer_ids": [answers["declared-path-002"]],
                        },
                    ],
                    "proof_bindings": [{
                        "path": "tests/test_new_work.py",
                        "command": command,
                        "tier": "unit",
                        "asserted_behavior": "Provider selection is deterministic and offline.",
                        "source_answer_id": answers["proof-command"],
                    }],
                    "criteria": {
                        "positive": contract["criteria"]["positive"],
                        "negative": contract["criteria"]["negative"],
                        "source_answer_ids": [answers["proposed-owner"]],
                    },
                    "correction_premise": {
                        "status": "not-applicable",
                        "source_answer_ids": [answers["proposed-owner"]],
                    },
                }]},
            })

            retry = shlex.split(result["retry_command"])
            executed = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), *retry[1:]],
                cwd=root, text=True, capture_output=True, check=False, timeout=120,
            )
            self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)
            self.assertIn("# TailTrail Start Plan", executed.stdout)
            self.assertNotIn("# TailTrail Scope Confirmation Required", executed.stdout)
            report_paths = list((root / ".tailtrail" / "runs").glob("*/planning/start-report-v1.json"))
            self.assertEqual(len(report_paths), 1)
            report = json.loads(report_paths[0].read_text(encoding="utf-8"))["report"]
            rows = report["navigator"]["requirement_matrix"]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["requirement_uid"], "req-canonical-resolver")
            self.assertEqual(rows[0]["statement"], goal)
            self.assertEqual(rows[0]["scope_evidence"]["implementation_owners"], ["src/new_work.py"])
            self.assertEqual(rows[0]["scope_evidence"]["proof_paths"], ["tests/test_new_work.py"])

    def test_readiness_scope_confirmations_are_idempotent_and_conflicts_fail_closed(self):
        spec = importlib.util.spec_from_file_location(
            "tailtrail_task_start_readiness_test", ROOT / "scripts" / "task-start.py"
        )
        assert spec and spec.loader
        task_start = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(task_start)
        receipt = {
            "operational_packet": {
                "requirements": [{
                    "path_bindings": [{
                        "path": "src/new_work.py",
                        "role": "implementation-owner",
                    }],
                }],
            },
        }

        task_start.validate_planning_readiness_scope_confirmations(
            receipt,
            ["src/new_work.py"],
            ["REQ-01=new:src/new_work.py"],
        )
        with self.assertRaisesRegex(ValueError, "not an implementation owner"):
            task_start.validate_planning_readiness_scope_confirmations(
                receipt,
                ["src/other.py"],
                [],
            )
        with self.assertRaisesRegex(ValueError, "does not match an implementation owner"):
            task_start.validate_planning_readiness_scope_confirmations(
                receipt,
                [],
                ["src/other.py"],
            )

    def test_public_intake_requires_and_preserves_generated_output_role(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "work.py").write_text("def run(): return 1\n", encoding="utf-8")
            (root / "tests" / "test_work.py").write_text("# proof\n", encoding="utf-8")
            goal = "Generate provenance for the work command."
            contract = {
                "schema_version": "1", "type": "tailtrail-host-input-contract", "run_id": "",
                "contract_id": "ctr-output", "profile": "existing-code change",
                "change_intent": "new-capability", "request_mode": "implementation",
                "behavior_surface": "cli-contract",
                "paths": [
                    {"path": "src/work.py", "role": "existing-implementation-owner"},
                    {"path": "generated/provenance.json", "role": "generated"},
                    {"path": "tests/test_work.py", "role": "existing-proof-path"},
                ],
                "criteria": {"positive": ["provenance is generated"], "negative": ["work stays compatible"]},
                "proof": {"command": "python3 -m unittest tests.test_work", "tiers": ["unit"]},
                "private_reasoning_excluded": True,
            }
            opened = orchestrator.public_intake_open(root, goal, contract)
            values = {
                "expected-behavior": "provenance is generated",
                "existing-owner": "src/work.py",
                "proof-command": "python3 -m unittest tests.test_work",
                "proof-adequacy-003": proof_adequacy(
                    "tests/test_work.py", "python3 -m unittest tests.test_work"
                ),
            }
            recorded = orchestrator.public_intake_record(root, opened["run_id"], [{
                "question_id": row["question_id"],
                "value": row.get("expected_value", values.get(row["field_id"])),
            } for row in opened["mandatory_questions"]])
            orchestrator.public_intake_validate(root, opened["run_id"], [{
                "answer_id": row["answer_id"],
                "evidence_paths": [
                    "tests/test_work.py" if row["field_id"] in {"proof-command", "proof-adequacy-003"}
                    else "src/work.py"
                ],
            } for row in recorded["candidates"]])
            answers = {row["field_id"]: row["answer_id"] for row in recorded["candidates"]}
            source_ids = list(answers.values())
            result = orchestrator.public_intake_finalize(root, opened["run_id"], {
                "operational_bindings": {"requirements": [{
                    "requirement_uid": "req-output", "statement": goal,
                    "requirement_kind": "change",
                    "requirement_kind_source_answer_ids": [answers["expected-behavior"]],
                    "source_answer_ids": source_ids,
                    "profile_fields": list(answers), "semantic_delta": "validated", "dependencies_checked": True,
                    "path_bindings": [
                        {"path": "src/work.py", "role": "implementation-owner", "existing": True,
                         "new_file_verdict": "not-applicable", "source_answer_ids": [answers["existing-owner"]]},
                        {"path": "generated/provenance.json", "role": "generated-output", "existing": False,
                         "host_declared": True, "new_file_verdict": "new-confirmed",
                         "ownership_evidence": "accepted host role plus generated-artifact convention",
                         "source_answer_ids": [answers["declared-path-002"]]},
                    ],
                    "proof_bindings": [{
                        "path": "tests/test_work.py", "command": values["proof-command"], "tier": "unit",
                        "asserted_behavior": "provenance generation is covered", "source_answer_id": answers["proof-command"],
                    }],
                    "criteria": {"positive": contract["criteria"]["positive"], "negative": contract["criteria"]["negative"],
                                 "source_answer_ids": [answers["expected-behavior"]]},
                    "correction_premise": {"status": "not-applicable", "source_answer_ids": [answers["expected-behavior"]]},
                }]},
            })

            operational = result["receipt"]["operational_packet"]
            output = next(row for row in operational["requirements"][0]["path_bindings"] if row["role"] == "generated-output")
            self.assertFalse(output["grants_behavioral_ownership"])
            self.assertTrue(output["new_file_due_diligence"]["write_eligible"])
            self.assertEqual(operational["declared_path_roles"]["paths"][1]["operational_role"], "generated-output")
            retry = shlex.split(result["retry_command"])
            executed = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), *retry[1:]],
                cwd=root, text=True, capture_output=True, check=False, timeout=120,
            )
            self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)
            self.assertIn("generated/provenance.json", executed.stdout)
            self.assertIn("generated-output", executed.stdout)

    def test_public_cli_opens_mandatory_navigator_intake(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "work.py").write_text("x = 1\n", encoding="utf-8")
            (root / "tests" / "test_work.py").write_text("# proof\n", encoding="utf-8")
            contract = {
                "schema_version": "1", "type": "tailtrail-host-input-contract",
                "run_id": "", "contract_id": "ctr-public-cli", "profile": "existing-code change",
                "change_intent": "refactor", "request_mode": "implementation",
                "behavior_surface": "cli-contract",
                "paths": [
                    {"path": "src/work.py", "role": "existing-implementation-owner"},
                    {"path": "tests/test_work.py", "role": "existing-proof-path"},
                ],
                "criteria": {"positive": ["work changes"], "negative": ["other work is preserved"]},
                "proof": {"command": "python3 -m unittest tests.test_work", "tiers": ["unit"]},
                "private_reasoning_excluded": True,
            }
            contract_path = root / "contract.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(),
                    "navigator", "intake", "open", "--root", root.as_posix(),
                    "--goal", "Change work.", "--host-contract-file", contract_path.as_posix(),
                    "--host", "codex", "--aidlc", "off",
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "awaiting-candidate-answers")
            self.assertEqual(len(payload["mandatory_questions"]), 4)
            self.assertEqual(payload["mandatory_questions"][-1]["kind"], "proof-adequacy")

    def test_public_intake_allows_declared_proposed_proof_before_file_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "DESIGN.md").write_text("New widget and its proof are proposed here.\n", encoding="utf-8")
            goal = "Create a new widget."
            contract = {
                "schema_version": "1", "type": "tailtrail-host-input-contract",
                "run_id": "", "contract_id": "ctr-proposed-proof", "profile": "new feature",
                "change_intent": "new-capability", "request_mode": "implementation",
                "behavior_surface": "cli-contract",
                "paths": [
                    {"path": "src/widget.py", "role": "proposed-implementation-owner"},
                    {"path": "tests/test_widget.py", "role": "proposed-proof-path"},
                    {"path": "DESIGN.md", "role": "inspection-input"},
                ],
                "criteria": {"positive": ["widget is available"], "negative": ["existing behavior remains"]},
                "proof": {"command": "python3 -m unittest tests.test_widget", "tiers": ["unit"]},
                "private_reasoning_excluded": True,
            }
            opened = orchestrator.public_intake_open(root, goal, contract)
            values = {
                "proposed-owner": "src/widget.py",
                "public-route": "tailtrail widget",
                "proof-command": "python3 -m unittest tests.test_widget",
                "proof-adequacy-002": proof_adequacy(
                    "tests/test_widget.py",
                    "python3 -m unittest tests.test_widget",
                    role="new-proof",
                    outcome="not-run",
                ),
            }
            candidates = orchestrator.public_intake_record(
                root, opened["run_id"],
                [{
                    "question_id": row["question_id"],
                    "value": row.get("expected_value", values.get(row["field_id"])),
                } for row in opened["mandatory_questions"]],
            )
            validated = orchestrator.public_intake_validate(
                root, opened["run_id"],
                [{"answer_id": row["answer_id"], "evidence_paths": ["DESIGN.md"]} for row in candidates["candidates"]],
            )
            self.assertTrue(validated["completeness"]["complete"])

    def test_proof_adequacy_rejects_run_only_claim_without_passing_baseline(self):
        value = proof_adequacy(
            "tests/test_work.py",
            "python3 -m unittest tests.test_work",
            role="unchanged-proof",
            outcome="fail",
        )
        with self.assertRaisesRegex(ValueError, "unchanged-proof requires a passing baseline"):
            orchestrator._parse_proof_adequacy(
                value,
                expected_path="tests/test_work.py",
                host_role="existing-proof-path",
                command="python3 -m unittest tests.test_work",
            )

    def test_proof_adequacy_accepts_editable_existing_proof(self):
        parsed = orchestrator._parse_proof_adequacy(
            proof_adequacy(
                "tests/test_work.py",
                "python3 -m unittest tests.test_work",
                role="editable-proof",
                outcome="fail",
            ),
            expected_path="tests/test_work.py",
            host_role="existing-proof-path",
            command="python3 -m unittest tests.test_work",
        )
        self.assertEqual(parsed["role"], "editable-proof")
        self.assertEqual(parsed["baseline"]["outcome"], "fail")


if __name__ == "__main__":
    unittest.main()
