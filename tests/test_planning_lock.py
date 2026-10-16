from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lock = load("planning_lock_test", "scripts/planning_lock.py")
ledger = load("planning_lock_ledger_test", "scripts/run-ledger.py")
revision = load("planning_lock_revision_test", "scripts/planning-revision.py")


class PlanningLockTests(unittest.TestCase):
    def test_proof_runner_uses_bare_interpreter_not_launcher_path(self) -> None:
        self.assertEqual(lock._proof_runner("python3 D:/proj/.tailtrail/install/payload/codex/scripts/tailtrail.py"), "python3")
        self.assertEqual(lock._proof_runner("python D:/proj/scripts/tailtrail.py"), "python")
        self.assertEqual(lock._proof_runner("py -3 D:/proj/tailtrail.py"), "py -3")
        self.assertEqual(lock._proof_runner("python3"), "python3")
        self.assertEqual(lock._proof_runner(""), "python3")

    def test_resolved_validation_prefers_real_test_module_over_init(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "notify on status change", "plan-proof-cmd")
            report = {
                "goal": "notify on status change",
                "command_prefix": "python3 D:/proj/.tailtrail/install/payload/codex/scripts/tailtrail.py",
                "navigator": {"likely_impacted_files": [{"path": "tests/__init__.py"}, {"path": "tests/test_notify.py"}]},
                "guided_delivery": {},
            }
            path = lock.start_report_path(root, "plan-proof-cmd")
            ledger.atomic_json(path, {"report": report})
            resolved = lock._resolved_aidlc_plan(root, "plan-proof-cmd", {"requirements": [{
                "requirement_uid": "req-1", "display_id": "REQ-01",
                "validation_contract": {"tiers": ["e2e"]},
            }]})
        self.assertEqual(resolved["validation"], [{
            "tier": "e2e", "candidate": "tests/test_notify.py",
            "command": "python3 -m unittest discover -s tests -p test_notify.py -v",
        }])

    def test_official_revision_binds_saved_v2_scope_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "notify on status change", "plan-official-scope")
            scope = {
                "decision_fingerprint": "sha256:abc",
                "implementation_owners": ["src/notify.py"],
                "inspection_paths": [],
                "proof_paths": ["tests/test_notify.py"],
            }
            ledger.atomic_json(lock.start_report_path(root, "plan-official-scope"), {"report": {
                "goal": "notify on status change",
                "navigator": {"requirement_matrix": [{
                    "requirement_uid": "req-1", "display_id": "REQ-01",
                    "statement": "Notify on status change.",
                    "likely_paths": ["tests/test_notify.py"], "scope_evidence": scope,
                    "validation_contract": {"state": "required", "tiers": ["unit"]},
                }], "scope_evidence": {"schema_version": "2", "decision_fingerprint": "sha256:abc"}},
            }})
            revision = {"requirements": [{"requirement_uid": "req-1", "display_id": "REQ-01", "statement": "Notify on status change.", "validation_contract": {"state": "required", "tiers": ["unit"]}}]}
            bound = lock._bind_official_scope_mapping(root, "plan-official-scope", revision)
            result = lock._validate_aidlc_scope_mapping(root, "plan-official-scope", bound)
        row = bound["requirements"][0]
        self.assertEqual(row["likely_paths"], ["src/notify.py"])
        self.assertEqual(row["scope_evidence"]["decision_fingerprint"], "sha256:abc")
        self.assertEqual(row["validation_contract"]["editable_paths"], ["tests/test_notify.py"])
        self.assertEqual(result["status"], "matched")

    def test_official_revision_without_saved_mapping_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "notify on status change", "plan-official-scope-missing")
            ledger.atomic_json(lock.start_report_path(root, "plan-official-scope-missing"), {"report": {
                "goal": "notify on status change",
                "navigator": {"requirement_matrix": [{
                    "requirement_uid": "req-1", "display_id": "REQ-01", "statement": "Notify.",
                }]},
            }})
            with self.assertRaisesRegex(ValueError, "no saved v2 scope mapping"):
                lock._bind_official_scope_mapping(root, "plan-official-scope-missing", {"requirements": [{
                    "requirement_uid": "req-1", "display_id": "REQ-01", "statement": "Notify.",
                }]})

    def test_official_revision_carries_recorded_proof_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "notify on status change", "plan-official-commands")
            scope = {
                "decision_fingerprint": "sha256:abc",
                "implementation_owners": ["src/notify.py"],
                "inspection_paths": [],
                "proof_paths": ["tests/test_notify.py"],
            }
            ledger.atomic_json(lock.start_report_path(root, "plan-official-commands"), {"report": {
                "goal": "notify on status change",
                "navigator": {"requirement_matrix": [{
                    "requirement_uid": "req-1", "display_id": "REQ-01",
                    "statement": "Notify on status change.",
                    "likely_paths": ["src/notify.py"], "scope_evidence": scope,
                    "validation_contract": {
                        "state": "required", "tiers": ["unit"],
                        "commands": ["python -m unittest tests.test_notify -v"],
                        "checks": [{"kind": "proof", "command": "python -m unittest tests.test_notify -v",
                                    "tiers": ["unit"], "candidate_paths": ["tests/test_notify.py"]}],
                        "candidate_paths": ["tests/test_notify.py"],
                    },
                }], "scope_evidence": {"schema_version": "2", "decision_fingerprint": "sha256:abc"}},
            }})
            revision = {"requirements": [{"requirement_uid": "req-1", "display_id": "REQ-01", "statement": "Notify on status change.", "validation_contract": {"state": "required", "tiers": ["unit"]}}]}
            bound = lock._bind_official_scope_mapping(root, "plan-official-commands", revision)
        row = bound["requirements"][0]
        contract = row["validation_contract"]
        self.assertEqual(contract["commands"], ["python -m unittest tests.test_notify -v"])
        self.assertEqual(contract["checks"], [{"kind": "proof", "command": "python -m unittest tests.test_notify -v",
                                               "tiers": ["unit"], "candidate_paths": ["tests/test_notify.py"]}])
        self.assertEqual(contract["candidate_paths"], ["tests/test_notify.py"])
        # Authority-owned tiers/state survive the carry.
        self.assertEqual(contract["tiers"], ["unit"])
        self.assertEqual(contract["state"], "required")

    def test_official_revision_without_recorded_commands_mints_none(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "notify on status change", "plan-official-nocommands")
            scope = {
                "decision_fingerprint": "sha256:abc",
                "implementation_owners": ["src/notify.py"],
                "inspection_paths": [],
                "proof_paths": [],
            }
            ledger.atomic_json(lock.start_report_path(root, "plan-official-nocommands"), {"report": {
                "goal": "notify on status change",
                "navigator": {"requirement_matrix": [{
                    "requirement_uid": "req-1", "display_id": "REQ-01",
                    "statement": "Notify on status change.",
                    "likely_paths": ["src/notify.py"], "scope_evidence": scope,
                    "validation_contract": {"state": "required", "tiers": ["unit"]},
                }], "scope_evidence": {"schema_version": "2", "decision_fingerprint": "sha256:abc"}},
            }})
            revision = {"requirements": [{"requirement_uid": "req-1", "display_id": "REQ-01", "statement": "Notify on status change.", "validation_contract": {"state": "required", "tiers": ["unit"]}}]}
            bound = lock._bind_official_scope_mapping(root, "plan-official-nocommands", revision)
        self.assertNotIn("commands", bound["requirements"][0]["validation_contract"])

    def test_fail_closed_errors_carry_corrective_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, r"tailtrail start"):
                lock.show(root, "no-such-run")
            lock.create(root, "do work", "plan-err")
            lock.save_start_report(root, "plan-err", {
                "goal": "do work",
                "guided_delivery": {"mode": "guided-delivery"},
                "navigator": {"likely_impacted_files": [{"path": "src/work.py"}]},
            })
            with self.assertRaisesRegex(ValueError, "aidlc-standard"):
                lock.record_official_aidlc_questions(root, "plan-err", "[]")

    def test_official_question_recorder_supports_stdin_for_large_windows_payloads(self) -> None:
        source = (ROOT / "scripts" / "planning_lock.py").read_text(encoding="utf-8")
        self.assertIn('official_question_source.add_argument("--questions-stdin"', source)
        self.assertIn("questions_json = sys.stdin.readline()", source)

    def test_start_is_locked_until_a_separate_explicit_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            created = lock.create(root, "replicate Terraform setup", "plan-1", ["../reference"])
            with self.assertRaisesRegex(ValueError, "explicit approval"):
                lock.assert_write_allowed(root, "plan-1")
            approved = lock.approve(root, "plan-1", True)
            allowed = lock.assert_write_allowed(root, "plan-1")
            activity = ledger.projection(root, "plan-1")["activity"]
        self.assertEqual(created["status"], "awaiting-approval")
        self.assertFalse(created["writes_allowed"])
        self.assertEqual(created["reference_roots"][0]["access"], "read-only")
        self.assertEqual(approved["status"], "approved")
        self.assertTrue(allowed["writes_allowed"])
        self.assertEqual(activity["planning_lock_created"], 1)
        self.assertEqual(activity["planning_lock_approved"], 1)

    def test_approval_flag_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "plan", "plan-2")
            with self.assertRaisesRegex(ValueError, "--approved"):
                lock.approve(root, "plan-2", False)

    def test_new_lock_binds_target_identity_and_write_guard_reports_inventory_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "service.py").write_text("value = 1\n", encoding="utf-8")
            created = lock.create(root, "add a service", "plan-target")
            lock.approve(root, "plan-target", True)
            matched = lock.assert_write_allowed(root, "plan-target")
            (root / "src" / "new_module.py").write_text("value = 2\n", encoding="utf-8")
            drifted = lock.assert_write_allowed(root, "plan-target")
        self.assertEqual(created["schema_version"], "2")
        self.assertTrue(created["target_identity"]["fingerprint"].startswith("sha256:"))
        self.assertEqual(matched["target_identity_check"]["status"], "matched")
        self.assertEqual(drifted["target_identity_check"]["status"], "inventory-drift")
        self.assertEqual(drifted["target_identity_check"]["inventory_drift"]["added"], ["src/new_module.py"])

    def test_activation_reports_inventory_drift_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "service.py").write_text("value = 1\n", encoding="utf-8")
            lock.create(root, "add a service", "plan-target-activation")
            lock.save_start_report(root, "plan-target-activation", {
                "goal": "add a service",
                "guided_delivery": {"mode": "guided-delivery"},
                "navigator": {"likely_impacted_files": [{"path": "src/service.py"}]},
            })
            (root / "src" / "changed_after_plan.py").write_text("value = 2\n", encoding="utf-8")
            activated = lock.activate(root, "plan-target-activation", True)
        self.assertEqual(activated["target_identity"]["status"], "inventory-drift")
        self.assertFalse(activated["target_identity"]["blocking"])

    def test_activation_still_blocks_workspace_root_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "service.py").write_text("value = 1\n", encoding="utf-8")
            lock.create(root, "add a service", "plan-target-root")
            lock.save_start_report(root, "plan-target-root", {
                "goal": "add a service",
                "guided_delivery": {"mode": "guided-delivery"},
                "navigator": {"likely_impacted_files": [{"path": "src/service.py"}]},
            })
            path = lock.lock_path(root, "plan-target-root")
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["target_identity"]["root"] = (root / "elsewhere").as_posix()
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Target identity mismatch"):
                lock.activate(root, "plan-target-root", True)

    def test_lock_persists_input_roles_and_write_guard_rechecks_target_role(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "target"
            reference = Path(temp) / "reference"
            root.mkdir()
            reference.mkdir()
            roles = lock.target_workspace().input_roles(root, reference_roots=[reference.as_posix()])
            created = lock.create(root, "reuse reference validation", "plan-roles", input_roles=roles)
            lock.approve(root, "plan-roles", True)
            allowed = lock.assert_write_allowed(root, "plan-roles")
        self.assertEqual(created["input_roles"]["inputs"][1]["role"], "reference-repo")
        self.assertEqual(allowed["input_roles_check"]["read_only_inputs"], 1)

    def test_legacy_lock_remains_readable_with_a_visible_nonblocking_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "legacy", "plan-legacy")
            path = lock.lock_path(root, "plan-legacy")
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["schema_version"] = "1"
            payload.pop("target_identity")
            path.write_text(json.dumps(payload), encoding="utf-8")
            lock.approve(root, "plan-legacy", True)
            allowed = lock.assert_write_allowed(root, "plan-legacy")
        self.assertEqual(allowed["target_identity_check"]["status"], "legacy")

    def test_activation_creates_anchor_from_the_saved_start_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix claim validation", "plan-3")
            lock.save_start_report(root, "plan-3", {
                "goal": "fix claim validation",
                "guided_delivery": {"mode": "guided-delivery"},
                "navigator": {"likely_impacted_files": [{"path": "src/claims.py"}]},
            })
            activated = lock.activate(root, "plan-3", True)
            artifact = root / activated["anchor"]["artifact"]
            approved = json.loads(artifact.read_text(encoding="utf-8"))
            handoff_path = root / activated["execution_handoff_artifact"]
            handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        self.assertEqual(activated["planning_lock"]["status"], "approved")
        self.assertEqual(activated["anchor"]["status"], "created")
        self.assertEqual(approved["requirements"][0]["statement"], "fix claim validation")
        self.assertEqual(approved["requirements"][0]["likely_paths"], ["src/claims.py"])
        self.assertTrue(handoff["closure"]["required"])
        self.assertEqual(handoff["closure"]["command"], "tailtrail completion-report --root . --run-id plan-3")
        self.assertIn("generic changes-made", handoff["closure"]["response_rule"])
        self.assertEqual(handoff["execution_authority"]["route"], "legacy-no-runtime-authority")

    def test_lean_activation_does_not_create_an_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "rename one local variable", "plan-4")
            lock.save_start_report(root, "plan-4", {
                "goal": "rename one local variable",
                "guided_delivery": {"mode": "lean"},
                "navigator": {},
            })
            activated = lock.activate(root, "plan-4", True)
        self.assertEqual(activated["anchor"]["status"], "not-required")

    def test_rejected_start_returns_complete_requirement_feedback_without_source_access(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix claim validation", "plan-feedback")
            lock.save_start_report(root, "plan-feedback", {
                "goal": "fix claim validation",
                "guided_delivery": {"mode": "guided-delivery"},
                "navigator": {"requirement_matrix": [{
                    "display_id": "REQ-01", "kind": "change", "statement": "Reject zero claims",
                    "acceptance_criteria": ["zero fails"], "preserve_rules": ["positive passes"],
                    "likely_paths": ["src/claims.py"], "evidence_plan": ["focused test"],
                }]},
            })
            template = lock.feedback_template(root, "plan-feedback")
            feedback = json.dumps([{
                "requirement_uid": template["requirements"][0]["requirement_uid"],
                "decision": "reject", "comment": "Include the service caller in scope.",
            }])
            result = lock.record_feedback(root, "plan-feedback", feedback)
            activity = ledger.projection(root, "plan-feedback")["activity"]
        self.assertEqual(template["state"], "feedback-required")
        self.assertIn("no project source", template["source_boundary"])
        self.assertIn("# TailTrail Plan Feedback", lock.render_feedback_template(template))
        self.assertIn("Reject zero claims", lock.render_feedback_template(template))
        self.assertEqual(result["state"], "revision-required")
        self.assertEqual(result["next_requirement_mode"], "ask-targeted-questions-or-offer-aidlc")
        self.assertEqual(activity["proposal_rejected"], 1)

    def test_second_rejection_requires_aidlc_before_another_material_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix claim validation", "plan-second-feedback")
            lock.save_start_report(root, "plan-second-feedback", {
                "goal": "fix claim validation", "guided_delivery": {"mode": "guided-delivery"},
                "navigator": {"likely_impacted_files": [{"path": "src/claims.py"}]},
            })
            template = lock.feedback_template(root, "plan-second-feedback")
            feedback = json.dumps([{"requirement_uid": template["requirements"][0]["requirement_uid"], "decision": "reject", "comment": "Need caller coverage."}])
            lock.record_feedback(root, "plan-second-feedback", feedback)
            second = lock.record_feedback(root, "plan-second-feedback", feedback)
        self.assertEqual(second["next_requirement_mode"], "aidlc-requirements-required")
        self.assertIn("AIDLC", second["next"])

    def test_zero_quantity_feedback_is_split_and_never_prepopulates_user_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix the zero quantity validation defect and add focused validation", "plan-zero")
            lock.save_start_report(root, "plan-zero", {
                "goal": "fix the zero quantity validation defect and add focused validation",
                "guided_delivery": {"mode": "guided-delivery"}, "navigator": {},
            })
            template = lock.feedback_template(root, "plan-zero")
            rendered = lock.render_feedback_template(template)
        self.assertEqual([row["display_id"] for row in template["requirements"]], ["REQ-01", "REQ-02", "REQ-03"])
        self.assertTrue(all(row["decision"] == "pending" and row["comment"] == "" for row in template["requirements"]))
        self.assertIn("Reject all", rendered)
        self.assertIn("Use AIDLC now", rendered)

    def test_reject_all_and_direct_aidlc_are_explicit_user_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix the zero quantity validation defect and add focused validation", "plan-options")
            lock.save_start_report(root, "plan-options", {
                "goal": "fix the zero quantity validation defect and add focused validation",
                "guided_delivery": {"mode": "guided-delivery"}, "navigator": {},
            })
            rejected = lock.reject_all(root, "plan-options", "The requirement boundary is not specific enough.")
            aidlc = lock.request_aidlc_requirements(root, "plan-options")
        self.assertEqual(len(rejected["rejected_requirement_uids"]), 3)
        self.assertEqual(aidlc["state"], "aidlc-requirements-gathering")
        self.assertEqual(len(aidlc["questions"]), 4)
        self.assertEqual(aidlc["aidlc_stage"]["stage"], "AIDLC Requirements")
        self.assertEqual(aidlc["aidlc_stage"]["stage_evidence"]["stage_playbook"], "aidlc/stages/requirements.md")
        self.assertEqual(aidlc["questions"][0]["options"][0]["id"], "A")
        self.assertIn("recommended", aidlc["questions"][0])
        rendered = lock.render_aidlc_requirements(aidlc)
        self.assertIn("# TailTrail AIDLC Requirements", rendered)
        self.assertIn("### Q1", rendered)
        self.assertIn("### Q4", rendered)
        self.assertIn("Validator and service/API path", rendered)

    def test_aidlc_response_requires_every_generated_question(self) -> None:
        questions = [
            {
                "id": f"Q{index}",
                "question": f"Question {index}?",
                "options": [
                    {"id": "A", "text": "First"},
                    {"id": "B", "text": "Second"},
                    {"id": "Other", "text": "Other — describe the intended behavior."},
                ],
                "recommended": "First",
                "reasoning": "Focused reason.",
            }
            for index in range(1, 7)
        ]
        rendered = lock.render_aidlc_requirements({
            "run_id": "all-questions",
            "requirements": [{"display_id": "REQ-01", "statement": "Deliver the feature."}],
            "questions": questions,
        })
        self.assertIn("one answer for every question, `Q1` through `Q6`", rendered)
        self.assertNotIn("and `Q3`", rendered)

    def test_aidlc_report_normalizes_escaped_lines_and_unicode_punctuation(self) -> None:
        rendered = lock.render_aidlc_requirements({
            "run_id": "presentation-cleanup",
            "requirements": [{"display_id": "REQ-01", "statement": "Add API,\\nservice, and journey validation."}],
            "questions": [{
                "id": "Q1",
                "question": "Which boundary applies?\\nChoose one.",
                "options": [
                    {"id": "A", "text": "API and service — preserve compatibility."},
                    {"id": "Other", "text": "Other — explain the boundary."},
                ],
                "recommended": "API and service — preserve compatibility.",
                "reasoning": "The requirement names both layers — this keeps proof aligned.",
                "requirement_ids": ["REQ-01"],
                "decision_class": "architecture-decision",
                "decision_impact": ["architecture"],
            }],
        })
        self.assertNotIn("\\n", rendered)
        self.assertNotIn("—", rendered)
        self.assertNotIn("�", rendered)
        self.assertIn("Add API, service, and journey validation.", rendered)

    def test_aidlc_answers_activate_same_run_and_create_execution_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix the zero quantity validation defect and add focused validation", "plan-aidlc-handoff")
            lock.save_start_report(root, "plan-aidlc-handoff", {
                "goal": "fix the zero quantity validation defect and add focused validation",
                "guided_delivery": {"mode": "guided-delivery", "selected": [{"name": "Requirement Completion Harness", "why": "map requirements"}], "stages": ["inspect approved scope", "implement", "validate"]},
                "navigator": {"likely_impacted_files": [{"path": "src/validation.py"}]},
            })
            aidlc = lock.request_aidlc_requirements(root, "plan-aidlc-handoff")
            answers = json.dumps([
                {"question_id": "Q1", "choice": "B"},
                {"question_id": "Q2", "choice": "A"},
                {"question_id": "Q3", "choice": "B"},
            ])
            revision = lock.submit_aidlc_answers(root, "plan-aidlc-handoff", answers)
            rendered_revision = lock.render_aidlc_revision(revision)
            handoff = lock.approve_aidlc_requirements(root, "plan-aidlc-handoff", True)
            activity = ledger.projection(root, "plan-aidlc-handoff")["activity"]
        self.assertEqual(revision["state"], "aidlc-revision-ready")
        self.assertEqual(revision["evidence_capability"]["status"], "compatible")
        self.assertIn("## Navigator Decision", rendered_revision)
        self.assertIn("## Selected TailTrail features", rendered_revision)
        self.assertIn("## Validation", rendered_revision)
        self.assertIn("## Token estimate", rendered_revision)
        self.assertIn("service/API path", revision["requirements"][0]["statement"])
        self.assertEqual(handoff["state"], "execution-ready")
        self.assertTrue(handoff["planning_lock"]["writes_allowed"])
        self.assertIn("Requirement Completion Harness", lock.render_execution_handoff(handoff))
        self.assertIn("## Mandatory closure", lock.render_execution_handoff(handoff))
        self.assertIn("tailtrail completion-report --root . --run-id plan-aidlc-handoff", lock.render_execution_handoff(handoff))
        self.assertEqual(activity["aidlc_requirements_answered"], 1)
        self.assertEqual(activity["aidlc_requirements_approved"], 1)

    def test_material_free_form_answer_stays_observation_until_projection_is_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "plan-aidlc-observation-only"
            lock.create(root, "notify callers after a status change", run_id)
            ledger.atomic_json(lock.start_report_path(root, run_id), {"report": {
                "goal": "notify callers after a status change",
                "navigator": {"requirement_matrix": [{
                    "requirement_uid": "req-1",
                    "display_id": "REQ-01",
                    "statement": "Change the status.",
                    "acceptance_criteria": [],
                    "preserve_rules": [],
                    "likely_paths": ["src/notify.py"],
                    "scope_evidence": {
                        "implementation_owners": ["src/notify.py"],
                        "inspection_paths": [],
                        "proof_paths": ["tests/test_notify.py"],
                    },
                    "validation_contract": {"state": "required", "tiers": ["unit"]},
                }]},
                "guided_delivery": {},
            }})
            lock.request_aidlc_requirements(root, run_id)
            result = lock.submit_aidlc_answers(root, run_id, json.dumps([
                {"question_id": "Q1", "choice": "Other", "detail": "Notify the caller after the status changes."},
                {"question_id": "Q2", "choice": "A"},
                {"question_id": "Q3", "choice": "A"},
            ]))
            rendered = lock.render_aidlc_revision(result)
            planning = root / ".tailtrail" / "runs" / run_id / "planning"
            with self.assertRaisesRegex(ValueError, "correction projection is revision-required"):
                lock.approve_aidlc_requirements(root, run_id, True)
            self.assertEqual(result["state"], "revision-required")
            self.assertEqual(result["reason_code"], "validated-correction-projection-required")
            self.assertTrue((planning / "aidlc-correction-observations-v1.json").is_file())
            self.assertFalse((planning / "aidlc-revised-requirements-v1.json").exists())
            self.assertIn("Correction Projection Required", rendered)
            self.assertNotIn("## Navigator Decision", rendered)

    def test_validated_correction_projection_updates_canonical_requirement_and_exact_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "plan-aidlc-projected"
            lock.create(root, "notify callers after a status change", run_id)
            ledger.atomic_json(lock.start_report_path(root, run_id), {"report": {
                "goal": "notify callers after a status change",
                "navigator": {
                    "requirement_matrix": [{
                        "requirement_uid": "req-1",
                        "display_id": "REQ-01",
                        "statement": "Change the status.",
                        "acceptance_criteria": [],
                        "preserve_rules": [],
                        "likely_paths": ["src/notify.py"],
                        "scope_evidence": {
                            "implementation_owners": ["src/notify.py"],
                            "inspection_paths": [],
                            "proof_paths": ["tests/test_notify.py"],
                        },
                        "validation_contract": {"state": "required", "tiers": ["unit"]},
                    }],
                    "likely_impacted_files": [
                        {"path": "src/notify.py"},
                        {"path": "tests/test_notify.py"},
                    ],
                },
                "guided_delivery": {},
            }})
            lock.request_aidlc_requirements(root, run_id)
            statement = "Notify the caller after the status changes."
            proof_detail = "Use tests/test_notify.py with command python3 -m unittest tests.test_notify -v for unit and behaviour proof."
            result = lock.submit_aidlc_answers(root, run_id, json.dumps({
                "answers": [
                    {"question_id": "Q1", "choice": "Other", "detail": statement},
                    {"question_id": "Q2", "choice": "A"},
                    {"question_id": "Q3", "choice": "Other", "detail": proof_detail},
                ],
                "correction_projection": {
                    "schema_version": "1",
                    "requirements": [{
                        "requirement_id": "REQ-01",
                        "source_question_ids": ["Q1"],
                        "statement": statement,
                    }],
                    "scope": [],
                    "proof": [{
                        "requirement_id": "REQ-01",
                        "source_question_ids": ["Q3"],
                        "path": "tests/test_notify.py",
                        "command": "python3 -m unittest tests.test_notify -v",
                        "tiers": ["unit", "behaviour"],
                    }],
                },
            }))
            planning = root / ".tailtrail" / "runs" / run_id / "planning"
            projection = json.loads((planning / "aidlc-correction-projection-v1.json").read_text(encoding="utf-8"))
            self.assertEqual(result["state"], "aidlc-revision-ready")
            self.assertEqual(result["requirements"][0]["statement"], statement)
            self.assertEqual(projection["status"], "validated")
            self.assertEqual(projection["changed_surfaces"], ["requirements", "validation"])
            self.assertEqual(result["resolved_plan"]["validation"], [
                {"tier": "unit", "candidate": "tests/test_notify.py", "command": "python3 -m unittest tests.test_notify -v"},
                {"tier": "behaviour", "candidate": "tests/test_notify.py", "command": "python3 -m unittest tests.test_notify -v"},
            ])
            self.assertTrue((planning / "aidlc-revised-requirements-v1.json").is_file())

    def test_aidlc_answer_base64_matches_inline_answers(self) -> None:
        import base64
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix the zero quantity validation defect and add focused validation", "plan-aidlc-b64")
            lock.save_start_report(root, "plan-aidlc-b64", {
                "goal": "fix the zero quantity validation defect and add focused validation",
                "guided_delivery": {"mode": "guided-delivery", "selected": [{"name": "Requirement Completion Harness", "why": "map requirements"}], "stages": ["inspect approved scope", "implement", "validate"]},
                "navigator": {"likely_impacted_files": [{"path": "src/validation.py"}]},
            })
            lock.request_aidlc_requirements(root, "plan-aidlc-b64")
            answers = json.dumps([
                {"question_id": "Q1", "choice": "B"},
                {"question_id": "Q2", "choice": "A"},
                {"question_id": "Q3", "choice": "B"},
            ])
            encoded = base64.b64encode(answers.encode("utf-8")).decode("ascii")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "planning_lock.py"),
                 "aidlc-answer", "--root", root.as_posix(), "--run-id", "plan-aidlc-b64",
                 "--answers-base64", encoded],
                text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Revised Requirements", result.stdout)
            revision_path = root / ".tailtrail" / "runs" / "plan-aidlc-b64" / "planning" / "aidlc-revised-requirements-v1.json"
            saved = json.loads(revision_path.read_text(encoding="utf-8"))
            self.assertEqual(
                {qid: row["choice"] for qid, row in saved["aidlc_answers"].items()},
                {"Q1": "B", "Q2": "A", "Q3": "B"})

    def test_aidlc_answer_malformed_base64_fails_cleanly(self) -> None:
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "planning_lock.py"),
                 "aidlc-answer", "--root", root.as_posix(), "--run-id", "nope",
                 "--answers-base64", "!!!not-base64!!!"],
                text=True, capture_output=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--answers-base64 must be valid", result.stderr + result.stdout)
            self.assertNotIn("Traceback", result.stderr + result.stdout)

    def test_hands_free_plan_approval_accepts_saved_aidlc_recommendations_and_activates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "plan-hands-free"
            goal = "hands-free: add order cancellation and refund end to end before shipment"
            lock.create(root, goal, run_id)
            lock.save_start_report(root, run_id, {
                "goal": goal,
                "guided_delivery": {"mode": "guided-delivery", "hands_free_program": True, "selected": [{"name": "Program Delivery Harness", "why": "end-to-end delivery"}]},
                "navigator": {"likely_impacted_files": [{"path": "src/order_service/service.py"}]},
            })
            gathered = lock.request_aidlc_requirements(root, run_id)
            activated = lock.activate(root, run_id, True)
            handoff_path = root / activated["artifact"]
            handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        self.assertEqual(len(gathered["questions"]), 12)
        self.assertEqual(activated["state"], "execution-ready")
        self.assertTrue(activated["planning_lock"]["writes_allowed"])
        self.assertTrue(handoff["closure"]["required"])
        self.assertEqual(handoff["closure"]["command"], "tailtrail completion-report --root . --run-id plan-hands-free")

    def test_hands_free_activation_preserves_each_displayed_feature_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "plan-granular-program"
            goal = "hands-free: add cancellation, inventory release, refund, notification, audit, API tests, and rollout"
            lock.create(root, goal, run_id)
            lock.save_start_report(root, run_id, {
                "goal": goal,
                "guided_delivery": {"mode": "guided-delivery", "hands_free_program": {"feature_requirements": [
                    {"display_id": "REQ-01", "statement": "Define cancellation eligibility."},
                    {"display_id": "REQ-02", "statement": "Release inventory exactly once."},
                    {"display_id": "REQ-03", "statement": "Issue one refund."},
                ]}},
                "navigator": {"likely_impacted_files": [{"path": "src/order_service/service.py"}]},
            })
            activated = lock.activate(root, run_id, True)
            approved = json.loads((root / activated["anchor"]["artifact"]).read_text(encoding="utf-8"))
        self.assertEqual([row["display_id"] for row in approved["requirements"]], ["REQ-01", "REQ-02", "REQ-03"])
        self.assertEqual(approved["requirements"][1]["validation_contract"]["tiers"], ["integration"])

    def test_aidlc_cycle_batches_safe_lifecycle_transitions_without_duplicate_gathering(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "plan-aidlc-cycle"
            lock.create(root, "fix the zero quantity validation defect and add focused validation", run_id)
            lock.save_start_report(root, run_id, {
                "goal": "fix the zero quantity validation defect and add focused validation",
                "guided_delivery": {"mode": "guided-delivery"},
                "navigator": {"likely_impacted_files": [{"path": "src/validation.py"}]},
            })
            started = lock.aidlc_cycle(root, run_id)
            resumed = lock.aidlc_cycle(root, run_id)
            answers = json.dumps([
                {"question_id": "Q1", "choice": "B"},
                {"question_id": "Q2", "choice": "A"},
                {"question_id": "Q3", "choice": "B"},
            ])
            revised = lock.aidlc_cycle(root, run_id, answers_json=answers)
            activated = lock.aidlc_cycle(root, run_id, approved=True)
            activity = ledger.projection(root, run_id)["activity"]
        self.assertEqual(started["cycle_action"], "start-requirements-gathering")
        self.assertEqual(resumed["cycle_action"], "resume-requirements-gathering")
        self.assertEqual(revised["cycle_action"], "record-answers-and-render-revision")
        self.assertEqual(revised["state"], "aidlc-revision-ready")
        self.assertEqual(activated["cycle_action"], "activate-approved-boundary")
        self.assertEqual(activated["state"], "execution-ready")
        self.assertTrue(activated["planning_lock"]["writes_allowed"])
        self.assertEqual(activity["aidlc_requirements_requested"], 1)
        self.assertEqual(activity["aidlc_requirements_answered"], 1)
        self.assertEqual(activity["aidlc_requirements_approved"], 1)

    def test_aidlc_cycle_rejects_answers_and_approval_in_one_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "plan", "plan-aidlc-cycle-invalid")
            with self.assertRaisesRegex(ValueError, "either --answers or --approved"):
                lock.aidlc_cycle(root, "plan-aidlc-cycle-invalid", answers_json="[]", approved=True)


class LiteAnchorDerivationTests(unittest.TestCase):
    def _save_lite_report(self, root: Path, run_id: str, rows: list[dict]) -> None:
        ledger.atomic_json(lock.start_report_path(root, run_id), {"report": {
            "goal": "do lite work",
            "aidlc_mode": {"mode": "lite"},
            "guided_delivery": {"mode": "guided-delivery"},
            "navigator": {
                "requirement_matrix": rows,
                "scope_evidence": {"schema_version": "2", "decision_fingerprint": "sha256:abc"},
            },
        }})

    def _row(self, **overrides):
        row = {
            "requirement_uid": "req-1", "display_id": "REQ-01", "kind": "change",
            "statement": "Do lite work.", "acceptance_criteria": ["Done."],
            "preserve_rules": [], "likely_paths": ["src/work.py"],
            "evidence_plan": ["Run unit proof."],
            "scope_evidence": {"decision_fingerprint": "sha256:abc"},
            "validation_contract": {
                "state": "required", "tiers": ["unit"],
                "commands": ["python -m unittest tests.test_work -v"],
            },
        }
        row.update(overrides)
        return row

    def _create_scoped(self, root: Path, run_id: str, goal: str = "do lite work"):
        return lock.create(root, goal, run_id, scope_decision={
            "decision_fingerprint": "sha256:abc",
            "target_identity_fingerprint": "sha256:def",
        })

    def test_lite_approve_derives_anchor_with_commands_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._create_scoped(root, "plan-lite-anchor")
            self._save_lite_report(root, "plan-lite-anchor", [self._row()])
            approved = lock.approve(root, "plan-lite-anchor", True)
            self.assertEqual(approved["status"], "approved")
            self.assertEqual(approved["lite_anchor"]["status"], "created")
            self.assertEqual(approved["lite_anchor"]["origin"], "lite-plan-approval")
            anchor = json.loads((root / approved["lite_anchor"]["artifact"]).read_text(encoding="utf-8"))
            self.assertEqual(anchor["status"], "approved")
            row = anchor["requirements"][0]
            self.assertEqual(row["validation_contract"]["commands"], ["python -m unittest tests.test_work -v"])
            self.assertEqual(row["source_reference"]["origin"], "lite-plan-approval")
            self.assertEqual(row["status"], "approved")

    def test_lite_approve_without_recorded_commands_mints_none(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._create_scoped(root, "plan-lite-nocommands")
            row = self._row()
            row["validation_contract"] = {"state": "required", "tiers": ["unit"]}
            self._save_lite_report(root, "plan-lite-nocommands", [row])
            approved = lock.approve(root, "plan-lite-nocommands", True)
            anchor = json.loads((root / approved["lite_anchor"]["artifact"]).read_text(encoding="utf-8"))
            self.assertNotIn("commands", anchor["requirements"][0]["validation_contract"])

    def test_standard_approve_derives_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "do standard work", "plan-standard-noanchor")
            ledger.atomic_json(lock.start_report_path(root, "plan-standard-noanchor"), {"report": {
                "goal": "do standard work",
                "aidlc_mode": {"mode": "standard"},
                "guided_delivery": {"mode": "guided-delivery"},
                "navigator": {"requirement_matrix": [self._row()]},
            }})
            # Standard has no Lite derivation; without an official anchor the
            # plain approval path refuses instead of bypassing the workshop.
            with self.assertRaisesRegex(ValueError, "no approved requirement anchor"):
                lock.approve(root, "plan-standard-noanchor", True)
            self.assertFalse((root / ".tailtrail" / "runs" / "plan-standard-noanchor" / "anchors" / "approved-v1.json").exists())

    def test_approve_without_saved_report_still_approves(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "do work", "plan-no-report")
            approved = lock.approve(root, "plan-no-report", True)
            self.assertEqual(approved["status"], "approved")
            self.assertEqual(approved["lite_anchor"]["status"], "not-applicable")


class ApprovalScopeGuardTests(unittest.TestCase):
    def _report(self, **overrides):
        report: dict = {
            "goal": "do the thing",
            "aidlc_mode": {"mode": "lite"},
            "guided_delivery": {"mode": "guided-delivery"},
            "navigator": {"requirement_matrix": [{
                "requirement_uid": "req-1", "display_id": "REQ-01",
                "statement": "Do the thing.",
                "scope_evidence": {"decision_fingerprint": "sha256:abc"},
                "validation_contract": {"state": "required", "tiers": ["unit"]},
            }]},
        }
        report.update(overrides)
        return report

    def _create_scoped(self, root: Path, run_id: str, goal: str = "do the thing"):
        return lock.create(root, goal, run_id, scope_decision={
            "decision_fingerprint": "sha256:abc",
            "target_identity_fingerprint": "sha256:def",
        })

    def test_scopeless_build_approval_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "do standard work", "plan-scopeless", scope_decision=None)
            ledger.atomic_json(lock.start_report_path(root, "plan-scopeless"), {"report": {
                "goal": "do standard work",
                "aidlc_mode": {"mode": "standard"},
                "guided_delivery": {"mode": "guided-delivery"},
                "navigator": {"requirement_matrix": [{
                    "requirement_uid": "req-1", "display_id": "REQ-01",
                    "statement": "Do standard work.",
                    "validation_contract": {"state": "required", "tiers": ["unit"]},
                }]},
            }})
            with self.assertRaisesRegex(ValueError, "no approved requirement anchor"):
                lock.approve(root, "plan-scopeless", True)

    def test_preanchored_standard_approval_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "do standard work", "plan-preanchored")
            ledger.atomic_json(lock.start_report_path(root, "plan-preanchored"), {"report": {
                "goal": "do standard work",
                "aidlc_mode": {"mode": "standard"},
                "guided_delivery": {"mode": "guided-delivery"},
                "navigator": {"requirement_matrix": []},
            }})
            anchors = root / ".tailtrail" / "runs" / "plan-preanchored" / "anchors"
            anchors.mkdir(parents=True, exist_ok=True)
            (anchors / "approved-v1.json").write_text("{}", encoding="utf-8")
            approved = lock.approve(root, "plan-preanchored", True)
            self.assertEqual(approved["status"], "approved")

    def test_lite_scopeless_approval_derives_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "do the thing", "plan-lite-scopeless")
            ledger.atomic_json(lock.start_report_path(root, "plan-lite-scopeless"),
                               {"report": self._report()})
            approved = lock.approve(root, "plan-lite-scopeless", True)
            self.assertEqual(approved["status"], "approved")
            self.assertEqual(approved["lite_anchor"]["status"], "created")

    def test_scoped_build_approval_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "do the thing", "plan-scoped", scope_decision={
                "decision_fingerprint": "sha256:abc",
                "target_identity_fingerprint": "sha256:def",
            })
            ledger.atomic_json(lock.start_report_path(root, "plan-scoped"),
                               {"report": self._report()})
            approved = lock.approve(root, "plan-scoped", True)
            self.assertEqual(approved["status"], "approved")

    def test_debug_orientation_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix the crash", "plan-debug")
            report = self._report()
            report["debug_plan"] = {"reproduction_contract": {}}
            ledger.atomic_json(lock.start_report_path(root, "plan-debug"), {"report": report})
            approved = lock.approve(root, "plan-debug", True)
            self.assertEqual(approved["status"], "approved")

    def test_lean_mode_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "tiny fix", "plan-lean")
            report = self._report()
            report["guided_delivery"] = {"mode": "lean"}
            ledger.atomic_json(lock.start_report_path(root, "plan-lean"), {"report": report})
            approved = lock.approve(root, "plan-lean", True)
            self.assertEqual(approved["status"], "approved")


class AuditGateApprovalTests(unittest.TestCase):
    def _converged_row(self):
        return {
            "requirement_uid": "req-1", "display_id": "REQ-01", "kind": "change",
            "statement": "Do the thing.", "acceptance_criteria": ["Done."],
            "preserve_rules": [], "likely_paths": ["src/work.py"],
            "evidence_plan": ["Run unit proof."],
            "scope_evidence": {"decision_fingerprint": "sha256:abc"},
            "validation_contract": {
                "state": "required", "tiers": ["unit"],
                "commands": ["pytest tests/test_work.py"],
                "checks": [{"kind": "proof", "command": "pytest tests/test_work.py",
                            "tiers": ["unit"], "candidate_paths": ["tests/test_work.py"]}],
                "candidate_paths": ["tests/test_work.py"],
            },
        }

    def _converged_report(self):
        row = self._converged_row()
        report = {
            "goal": "do the thing",
            "aidlc_mode": {"mode": "lite"},
            "guided_delivery": {"mode": "guided-delivery"},
            "navigator": {"requirement_matrix": [row]},
            "focused_validation": [{
                "tier": "unit", "tiers": ["unit"], "candidate": "tests/test_work.py",
                "command": "pytest tests/test_work.py",
                "status": "planned after approval", "candidate_state": "existing",
            }],
        }
        projection = lock.effective_plan_projection(report)
        report["effective_plan_fingerprint"] = projection["fingerprint"]
        return report

    def _create_scoped(self, root: Path, run_id: str):
        return lock.create(root, "do the thing", run_id, scope_decision={
            "decision_fingerprint": "sha256:abc",
            "target_identity_fingerprint": "sha256:def",
        })

    def test_gappy_converged_plan_approval_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._create_scoped(root, "plan-gappy")
            report = self._converged_report()
            report["effective_plan_fingerprint"] = "sha256:tampered"
            ledger.atomic_json(lock.start_report_path(root, "plan-gappy"), {"report": report})
            with self.assertRaisesRegex(ValueError, "audit reports gaps-found"):
                lock.approve(root, "plan-gappy", True)
            self.assertEqual(lock.show(root, "plan-gappy")["status"], "awaiting-approval")

    def test_clean_converged_plan_approves_with_audit_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._create_scoped(root, "plan-clean")
            ledger.atomic_json(lock.start_report_path(root, "plan-clean"),
                               {"report": self._converged_report()})
            approved = lock.approve(root, "plan-clean", True)
            self.assertEqual(approved["status"], "approved")
            self.assertEqual(approved["approval"]["audit"]["status"], "clean")
            self.assertTrue(approved["approval"]["audit"]["report_fingerprint"].startswith("sha256:"))

    def test_thin_legacy_plan_records_exemption(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._create_scoped(root, "plan-thin")
            ledger.atomic_json(lock.start_report_path(root, "plan-thin"), {"report": {
                "goal": "do the thing",
                "aidlc_mode": {"mode": "lite"},
                "guided_delivery": {"mode": "guided-delivery"},
                "navigator": {"requirement_matrix": [{
                    "requirement_uid": "req-1", "display_id": "REQ-01",
                    "statement": "Do the thing.",
                    "scope_evidence": {"decision_fingerprint": "sha256:abc"},
                    "validation_contract": {"state": "required", "tiers": ["unit"]},
                }]},
            }})
            approved = lock.approve(root, "plan-thin", True)
            self.assertEqual(approved["status"], "approved")
            self.assertEqual(approved["approval"]["audit"]["status"], "exempt")
            self.assertEqual(approved["approval"]["audit"]["exemption"], "legacy-thin-plan")

    def test_gappy_pending_revision_approval_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._create_scoped(root, "plan-pending-gappy")
            ledger.atomic_json(lock.start_report_path(root, "plan-pending-gappy"),
                               {"report": self._converged_report()})
            revision.propose(root, "plan-pending-gappy", json.dumps([{
                "kind": "proof-update", "requirement_uid": "req-1",
                "reason": "add tier without command",
                "evidence_plan": ["Run integration proof."],
                "tiers": ["integration"],
            }]), True)
            with self.assertRaisesRegex(ValueError, "audit reports gaps-found"):
                revision.approve(root, "plan-pending-gappy", 2, True)
            self.assertEqual(lock.show(root, "plan-pending-gappy")["status"], "awaiting-approval")


if __name__ == "__main__":
    unittest.main()
