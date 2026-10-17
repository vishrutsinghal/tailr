from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.intake_pipeline import IntakeError, IntakePipeline


class IntakePipelineTests(unittest.TestCase):
    def test_creates_immutable_contract_and_correlates_interaction_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline = IntakePipeline(Path(temp))
            run = pipeline.create_run("collect host context", "new-feature")
            contract_path = Path(temp) / ".tailtrail" / "intake" / run["run_id"] / "contract.json"
            original_contract = contract_path.read_text(encoding="utf-8")

            question = pipeline.issue_question(run["run_id"], "implementation-owner", "Which path owns the behavior?")
            observation = pipeline.record_observation(
                run["run_id"], {"path": "scripts/example.py", "exists": True}, question_id=question["payload"]["question_id"]
            )
            answer = pipeline.record_answer(
                run["run_id"],
                "implementation-owner",
                "scripts/example.py",
                source="host-observation",
                observation_id=observation["payload"]["observation_id"],
            )

            self.assertEqual(pipeline.load_contract(run["run_id"])["contract_id"], run["contract_id"])
            self.assertEqual(contract_path.read_text(encoding="utf-8"), original_contract)
            events_path = contract_path.with_name("events.jsonl")
            events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([event["sequence"] for event in events], [1, 2, 3])
            self.assertEqual(events[0]["event_type"], "question-issued")
            self.assertEqual(events[1]["event_type"], "host-observation-recorded")
            self.assertEqual(events[2]["event_type"], "answer-recorded")
            self.assertEqual(answer["contract_id"], run["contract_id"])
            self.assertEqual(answer["packet_version"], 1)

    def test_duplicate_event_submission_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline = IntakePipeline(Path(temp))
            run = pipeline.create_run("collect host context", "new-feature")

            first = pipeline.issue_question(
                run["run_id"], "implementation-owner", "Which path owns the behavior?", idempotency_key="q-1"
            )
            second = pipeline.issue_question(
                run["run_id"], "implementation-owner", "Which path owns the behavior?", idempotency_key="q-1"
            )
            self.assertEqual(first["event_id"], second["event_id"])

            events_path = Path(temp) / ".tailtrail" / "intake" / run["run_id"] / "events.jsonl"
            events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(events), 1)

            with self.assertRaises(IntakeError):
                pipeline.issue_question(
                    run["run_id"], "implementation-owner", "A different question text", idempotency_key="q-1"
                )

    def test_events_from_stale_run_or_packet_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline = IntakePipeline(Path(temp))

            with self.assertRaises(IntakeError):
                pipeline.issue_question("run-does-not-exist", "implementation-owner", "Which path owns the behavior?")

            run = pipeline.create_run("collect host context", "new-feature")
            with self.assertRaises(IntakeError):
                pipeline.issue_question(
                    run["run_id"], "implementation-owner", "Which path owns the behavior?", packet_version=99
                )

    def test_contract_fingerprint_changes_only_through_approved_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline = IntakePipeline(Path(temp))
            run = pipeline.create_run("collect host context", "new-feature")
            original_fingerprint = pipeline.load_contract(run["run_id"])["fingerprint"]

            question = pipeline.issue_question(run["run_id"], "implementation-owner", "Which path owns the behavior?")
            pipeline.record_observation(
                run["run_id"], {"path": "scripts/example.py", "exists": True}, question_id=question["payload"]["question_id"]
            )
            pipeline.record_answer(
                run["run_id"],
                "implementation-owner",
                "scripts/example.py",
                source="host-observation",
                question_id=question["payload"]["question_id"],
            )
            self.assertEqual(pipeline.load_contract(run["run_id"])["fingerprint"], original_fingerprint)

            with self.assertRaises(IntakeError):
                pipeline.revise_contract(run["run_id"], {"status": "revised"})

            revision_event = pipeline.revise_contract(run["run_id"], {"status": "revised"}, approved=True)
            revised_contract = pipeline.load_contract(run["run_id"])
            self.assertNotEqual(revised_contract["fingerprint"], original_fingerprint)
            self.assertEqual(revised_contract["packet_version"], 2)
            self.assertEqual(revision_event["event_type"], "anchor-revised")

    def test_interaction_ids_are_unique_with_stable_content_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline = IntakePipeline(Path(temp))
            run = pipeline.create_run("collect host context", "new-feature")

            first = pipeline.issue_question(run["run_id"], "implementation-owner", "Which path owns the behavior?")
            second = pipeline.issue_question(run["run_id"], "implementation-owner", "Which path owns the behavior?")
            third = pipeline.issue_question(run["run_id"], "implementation-owner", "A different question text")

            self.assertNotEqual(first["payload"]["question_id"], second["payload"]["question_id"])
            self.assertNotEqual(first["event_id"], second["event_id"])
            self.assertEqual(first["content_fingerprint"], second["content_fingerprint"])
            self.assertNotEqual(first["content_fingerprint"], third["content_fingerprint"])

    def test_replay_materializes_the_same_contract_and_packet_view(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline = IntakePipeline(Path(temp))
            run = pipeline.create_run("collect host context", "new-feature")
            question = pipeline.issue_question(run["run_id"], "implementation-owner", "Which path owns the behavior?")
            pipeline.record_answer(
                run["run_id"], "implementation-owner", "scripts/example.py",
                source="direct-question", question_id=question["payload"]["question_id"],
            )
            first = pipeline.replay(run["run_id"])
            second = pipeline.replay(run["run_id"])

        self.assertEqual(first["contract_fingerprint"], second["contract_fingerprint"])
        self.assertEqual(first["packet_view_fingerprint"], second["packet_view_fingerprint"])
        self.assertEqual(first["event_count"], 2)

    def test_tampered_event_is_rejected_by_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline = IntakePipeline(Path(temp))
            run = pipeline.create_run("collect host context", "new-feature")
            pipeline.issue_question(run["run_id"], "implementation-owner", "Which path owns the behavior?")
            events_path = Path(temp) / ".tailtrail" / "intake" / run["run_id"] / "events.jsonl"
            event = json.loads(events_path.read_text(encoding="utf-8").splitlines()[0])
            event["payload"]["text"] = "Tampered question"
            events_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(IntakeError, "event integrity failure"):
                pipeline.replay(run["run_id"])

    def test_redacted_values_do_not_reappear_in_packet_view(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline = IntakePipeline(Path(temp))
            run = pipeline.create_run("collect host context", "new-feature")
            question = pipeline.issue_question(run["run_id"], "credentials", "Provide the access details")
            pipeline.record_observation(
                run["run_id"],
                {"api_token": "super-secret-token", "note": "Bearer bearer-secret"},
                question_id=question["payload"]["question_id"],
            )
            projection = pipeline.replay(run["run_id"])
            rendered = json.dumps(projection["packet_view"])

        self.assertNotIn("super-secret-token", rendered)
        self.assertNotIn("bearer-secret", rendered)
        self.assertIn("[REDACTED]", rendered)

    def test_finalizes_an_immutable_anchor_bound_packet_view_from_navigator_accepted_answers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pipeline = IntakePipeline(root)
            run = pipeline.create_run("collect host context", "new-feature")
            question = pipeline.issue_question(run["run_id"], "public-route", "Which route uses the feature?")
            answer = pipeline.record_answer(
                run["run_id"],
                "public-route",
                "tailtrail start",
                source="direct-question",
                question_id=question["payload"]["question_id"],
            )
            pipeline.accept_answer(
                run["run_id"],
                answer["payload"]["answer_id"],
                {"outcome": "accepted", "verified_by": "navigator"},
            )
            snapshot = pipeline.replay(run["run_id"])

            finalized = pipeline.finalize_packet_view(
                run["run_id"],
                anchor_version="anchor-v1",
                accepted_answers=[{
                    "answer_id": answer["payload"]["answer_id"],
                }],
                requirement_projections=[{
                    "requirement_uid": "req-123",
                    "consumer_component_id": "planning-lock",
                    "projection_kind": "approval",
                }],
                expected_packet_view_fingerprint=snapshot["packet_view_fingerprint"],
            )
            view_path = root / ".tailtrail" / "intake" / run["run_id"] / "packet-views" / "anchor-v1.json"
            saved = json.loads(view_path.read_text(encoding="utf-8"))
            after_finalization = pipeline.replay(run["run_id"])
            with self.assertRaisesRegex(IntakeError, "already exists"):
                pipeline.finalize_packet_view(
                    run["run_id"],
                    anchor_version="anchor-v1",
                    accepted_answers=[{"answer_id": answer["payload"]["answer_id"]}],
                    requirement_projections=[{
                        "requirement_uid": "req-123",
                        "consumer_component_id": "planning-lock",
                        "projection_kind": "approval",
                    }],
                    expected_packet_view_fingerprint=after_finalization["packet_view_fingerprint"],
                )
            self.assertEqual(json.loads(view_path.read_text(encoding="utf-8")), saved)

        self.assertEqual(finalized["status"], "requirements-finalized")
        self.assertEqual(saved, finalized["packet_view"])
        self.assertEqual(saved["anchor_version"], "anchor-v1")
        self.assertNotIn("packet_version", saved)
        self.assertEqual(finalized["receipt"]["accepted_answer_ids"], [answer["payload"]["answer_id"]])

    def test_finalization_rejects_unaccepted_stale_and_contradictory_answer_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline = IntakePipeline(Path(temp))
            run = pipeline.create_run("collect host context", "new-feature")
            first_question = pipeline.issue_question(run["run_id"], "public-route", "Which route uses the feature?")
            first = pipeline.record_answer(
                run["run_id"], "public-route", "tailtrail start", source="direct-question",
                question_id=first_question["payload"]["question_id"],
            )
            snapshot = pipeline.replay(run["run_id"])
            projections = [{
                "requirement_uid": "req-123",
                "consumer_component_id": "planning-lock",
                "projection_kind": "approval",
            }]

            with self.assertRaisesRegex(IntakeError, "no Navigator-validated acceptance event"):
                pipeline.finalize_packet_view(
                    run["run_id"], anchor_version="anchor-v1",
                    accepted_answers=[{"answer_id": first["payload"]["answer_id"]}],
                    requirement_projections=projections,
                    expected_packet_view_fingerprint=snapshot["packet_view_fingerprint"],
                )

            pipeline.accept_answer(
                run["run_id"],
                first["payload"]["answer_id"],
                {"outcome": "accepted", "verified_by": "navigator"},
            )
            snapshot = pipeline.replay(run["run_id"])

            second_question = pipeline.issue_question(run["run_id"], "public-route", "Which route uses the feature?")
            second = pipeline.record_answer(
                run["run_id"], "public-route", "tailtrail planning", source="direct-question",
                question_id=second_question["payload"]["question_id"],
            )
            with self.assertRaisesRegex(IntakeError, "stale packet finalization"):
                pipeline.finalize_packet_view(
                    run["run_id"], anchor_version="anchor-v1",
                    accepted_answers=[{"answer_id": first["payload"]["answer_id"]}],
                    requirement_projections=projections,
                    expected_packet_view_fingerprint=snapshot["packet_view_fingerprint"],
                )

            pipeline.accept_answer(
                run["run_id"],
                second["payload"]["answer_id"],
                {"outcome": "accepted", "verified_by": "navigator"},
            )
            fresh = pipeline.replay(run["run_id"])
            with self.assertRaisesRegex(IntakeError, "contradictory accepted answers"):
                pipeline.finalize_packet_view(
                    run["run_id"], anchor_version="anchor-v1",
                    accepted_answers=[
                        {"answer_id": first["payload"]["answer_id"]},
                        {"answer_id": second["payload"]["answer_id"]},
                    ],
                    requirement_projections=projections,
                    expected_packet_view_fingerprint=fresh["packet_view_fingerprint"],
                )

    def test_phase3_finalization_materializes_source_bound_operational_packet_and_invalidates_prior_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scripts").mkdir()
            (root / "scripts" / "example.py").write_text("# existing\n", encoding="utf-8")
            pipeline = IntakePipeline(root)
            run = pipeline.create_run("collect host context", "existing-code change")
            question = pipeline.issue_question(run["run_id"], "implementation-owner", "Which file owns this change?")
            answer = pipeline.record_answer(
                run["run_id"], "implementation-owner", "scripts/example.py", source="direct-question",
                question_id=question["payload"]["question_id"],
            )
            answer_id = answer["payload"]["answer_id"]
            pipeline.accept_answer(run["run_id"], answer_id, {"outcome": "accepted", "verified_by": "navigator"})

            def bindings(role: str = "implementation-owner", *, existing: bool = True, verdict: str = "not-applicable") -> dict:
                return {
                    "requirements": [{
                        "requirement_uid": "req-phase3",
                        "statement": "Materialize the approved operational packet.",
                        "source_answer_ids": [answer_id],
                        "profile_fields": ["implementation-owner"],
                        "path_bindings": [{
                            "path": "scripts/example.py" if existing else "scripts/new_example.py",
                            "role": role, "existing": existing, "new_file_verdict": verdict,
                            "host_declared": not existing,
                            "ownership_evidence": "project convention" if not existing else "",
                            "source_answer_ids": [answer_id],
                        }],
                        "proof_bindings": [{
                            "path": "tests/test_intake_pipeline.py",
                            "command": "python3 -m unittest tests.test_intake_pipeline -v",
                            "source_answer_ids": [answer_id],
                        }],
                        "criteria": {
                            "positive": ["The packet is materialized."],
                            "negative": ["Raw host values are not projected."],
                            "source_answer_ids": [answer_id],
                        },
                        "correction_premise": {"status": "not-applicable", "source_answer_ids": [answer_id]},
                    }],
                }

            snapshot = pipeline.replay(run["run_id"])
            first = pipeline.finalize_packet_view(
                run["run_id"], anchor_version="anchor-v1", accepted_answers=[{"answer_id": answer_id}],
                requirement_projections=[{"requirement_uid": "req-phase3", "consumer_component_id": "planning-lock", "projection_kind": "requirement"}],
                expected_packet_view_fingerprint=snapshot["packet_view_fingerprint"],
                anchor_fingerprint="sha256:" + "a" * 64, operational_bindings=bindings(),
            )
            packet = first["packet_view"]["operational_packet"]
            self.assertEqual(packet["projection_audit"], {
                "consumed": [answer_id], "unused": [], "contradicted": [], "inferred": [], "projected_without_source": [],
            })
            self.assertNotIn("tailtrail-host-answer", json.dumps(packet))
            self.assertEqual(packet["requirements"][0]["path_bindings"][0]["source_answer_ids"], [answer_id])

            second_snapshot = pipeline.replay(run["run_id"])
            pipeline.finalize_packet_view(
                run["run_id"], anchor_version="anchor-v2", accepted_answers=[{"answer_id": answer_id}],
                requirement_projections=[{"requirement_uid": "req-phase3", "consumer_component_id": "planning-lock", "projection_kind": "requirement"}],
                expected_packet_view_fingerprint=second_snapshot["packet_view_fingerprint"],
                anchor_fingerprint="sha256:" + "b" * 64, operational_bindings=bindings(),
            )
            invalidation_path = root / ".tailtrail" / "intake" / run["run_id"] / "packet-views" / "anchor-v1.invalidation.json"
            invalidation = json.loads(invalidation_path.read_text(encoding="utf-8"))
            self.assertEqual(invalidation["replacement_anchor_version"], "anchor-v2")
            self.assertEqual(invalidation["invalidated_packet_view_id"], first["packet_view"]["packet_view_id"])

    def test_phase3_finalization_rejects_unused_answers_unsafe_premises_and_contradictory_roles(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline = IntakePipeline(Path(temp))
            (Path(temp) / "scripts").mkdir()
            (Path(temp) / "scripts" / "one.py").write_text("# existing\n", encoding="utf-8")
            run = pipeline.create_run("collect host context", "new-feature")
            first_question = pipeline.issue_question(run["run_id"], "implementation-owner", "Which file owns this change?")
            first = pipeline.record_answer(run["run_id"], "implementation-owner", "scripts/one.py", source="direct-question", question_id=first_question["payload"]["question_id"])
            second_question = pipeline.issue_question(run["run_id"], "proof-command", "Which proof command applies?")
            second = pipeline.record_answer(run["run_id"], "proof-command", "python3 -m unittest", source="direct-question", question_id=second_question["payload"]["question_id"])
            for answer in (first, second):
                pipeline.accept_answer(run["run_id"], answer["payload"]["answer_id"], {"outcome": "accepted", "verified_by": "navigator"})
            first_id = first["payload"]["answer_id"]
            second_id = second["payload"]["answer_id"]

            def requirement(uid: str, role: str, *, premise: str = "not-applicable") -> dict:
                return {
                    "requirement_uid": uid, "statement": "A bounded requirement.", "source_answer_ids": [first_id],
                    "profile_fields": ["implementation-owner"],
                    "path_bindings": [{"path": "scripts/one.py", "role": role, "existing": True, "new_file_verdict": "not-applicable", "source_answer_ids": [first_id]}],
                    "proof_bindings": [{"path": "tests/test_intake_pipeline.py", "command": "python3 -m unittest tests.test_intake_pipeline -v", "source_answer_ids": [first_id]}],
                    "criteria": {"positive": ["works"], "negative": ["does not leak"], "source_answer_ids": [first_id]},
                    "correction_premise": {"status": premise, "source_answer_ids": [first_id]},
                }

            snapshot = pipeline.replay(run["run_id"])
            with self.assertRaisesRegex(IntakeError, "unused Navigator-accepted answers"):
                pipeline.finalize_packet_view(
                    run["run_id"], anchor_version="anchor-v1", accepted_answers=[{"answer_id": first_id}, {"answer_id": second_id}],
                    requirement_projections=[{"requirement_uid": "req-one", "consumer_component_id": "planning-lock", "projection_kind": "requirement"}],
                    expected_packet_view_fingerprint=snapshot["packet_view_fingerprint"], anchor_fingerprint="sha256:" + "c" * 64,
                    operational_bindings={"requirements": [requirement("req-one", "implementation-owner")]},
                )
            with self.assertRaisesRegex(IntakeError, "contradictory path roles"):
                pipeline.finalize_packet_view(
                    run["run_id"], anchor_version="anchor-v1", accepted_answers=[{"answer_id": first_id}],
                    requirement_projections=[{"requirement_uid": "req-one", "consumer_component_id": "planning-lock", "projection_kind": "requirement"}],
                    expected_packet_view_fingerprint=snapshot["packet_view_fingerprint"], anchor_fingerprint="sha256:" + "c" * 64,
                    operational_bindings={"requirements": [requirement("req-one", "implementation-owner"), requirement("req-two", "inspection-input")]},
                )
            with self.assertRaisesRegex(IntakeError, "must be accepted or not-applicable"):
                pipeline.finalize_packet_view(
                    run["run_id"], anchor_version="anchor-v1", accepted_answers=[{"answer_id": first_id}],
                    requirement_projections=[{"requirement_uid": "req-one", "consumer_component_id": "planning-lock", "projection_kind": "requirement"}],
                    expected_packet_view_fingerprint=snapshot["packet_view_fingerprint"], anchor_fingerprint="sha256:" + "c" * 64,
                    operational_bindings={"requirements": [requirement("req-one", "implementation-owner", premise="unverified")]},
                )

    def test_phase3_proposed_new_file_remains_bound_as_unverified_until_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline = IntakePipeline(Path(temp))
            run = pipeline.create_run("collect host context", "new-feature")
            question = pipeline.issue_question(run["run_id"], "implementation-owner", "Which new file is proposed?")
            answer = pipeline.record_answer(run["run_id"], "implementation-owner", "scripts/new_feature.py", source="narration", question_id=question["payload"]["question_id"])
            answer_id = answer["payload"]["answer_id"]
            pipeline.accept_answer(run["run_id"], answer_id, {"outcome": "accepted", "verified_by": "navigator"})
            snapshot = pipeline.replay(run["run_id"])
            result = pipeline.finalize_packet_view(
                run["run_id"], anchor_version="anchor-v1", accepted_answers=[{"answer_id": answer_id}],
                requirement_projections=[{"requirement_uid": "req-new", "consumer_component_id": "planning-lock", "projection_kind": "requirement"}],
                expected_packet_view_fingerprint=snapshot["packet_view_fingerprint"], anchor_fingerprint="sha256:" + "d" * 64,
                operational_bindings={"requirements": [{
                    "requirement_uid": "req-new", "statement": "Add a new bounded capability.", "source_answer_ids": [answer_id],
                    "profile_fields": ["implementation-owner"],
                    "path_bindings": [{"path": "scripts/new_feature.py", "role": "implementation-owner", "existing": False, "host_declared": True, "new_file_verdict": "unverified", "ownership_evidence": "scripts convention", "source_answer_ids": [answer_id]}],
                    "proof_bindings": [{"path": "tests/test_intake_pipeline.py", "command": "python3 -m unittest tests.test_intake_pipeline -v", "source_answer_ids": [answer_id]}],
                    "criteria": {"positive": ["new capability works"], "negative": ["existing behavior regresses"], "source_answer_ids": [answer_id]},
                    "correction_premise": {"status": "not-applicable", "source_answer_ids": [answer_id]},
                }]},
            )
            binding = result["packet_view"]["operational_packet"]["requirements"][0]["path_bindings"][0]
            self.assertFalse(binding["existing"])
            self.assertEqual(binding["new_file_verdict"], "unverified")

    def test_expired_and_abandoned_runs_require_explicit_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pipeline = IntakePipeline(Path(temp))
            run = pipeline.create_run("collect host context", "new-feature")
            pipeline.expire_run(run["run_id"])
            with self.assertRaisesRegex(IntakeError, "explicit resume"):
                pipeline.assert_execution_allowed(run["run_id"])
            pipeline.resume_run(run["run_id"])
            pipeline.assert_execution_allowed(run["run_id"])
            pipeline.abandon_run(run["run_id"])
            with self.assertRaisesRegex(IntakeError, "explicit resume"):
                pipeline.assert_execution_allowed(run["run_id"])


if __name__ == "__main__":
    unittest.main()
