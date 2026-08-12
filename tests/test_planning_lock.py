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


lock = load("planning_lock_test", "scripts/planning-lock.py")
ledger = load("planning_lock_ledger_test", "scripts/run-ledger.py")


class PlanningLockTests(unittest.TestCase):
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

    def test_new_lock_binds_target_identity_and_write_guard_blocks_inventory_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "service.py").write_text("value = 1\n", encoding="utf-8")
            created = lock.create(root, "add a service", "plan-target")
            lock.approve(root, "plan-target", True)
            matched = lock.assert_write_allowed(root, "plan-target")
            (root / "src" / "new_module.py").write_text("value = 2\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Target identity mismatch"):
                lock.assert_write_allowed(root, "plan-target")
        self.assertEqual(created["schema_version"], "2")
        self.assertTrue(created["target_identity"]["fingerprint"].startswith("sha256:"))
        self.assertEqual(matched["target_identity_check"]["status"], "matched")

    def test_activation_blocks_target_identity_mismatch(self) -> None:
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
            with self.assertRaisesRegex(ValueError, "Target identity mismatch"):
                lock.activate(root, "plan-target-activation", True)

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
        self.assertIn("Q1:", rendered)
        self.assertIn("### Q4", rendered)
        self.assertIn("Validator and service/API path", rendered)

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
            handoff = lock.approve_aidlc_requirements(root, "plan-aidlc-handoff", True)
            activity = ledger.projection(root, "plan-aidlc-handoff")["activity"]
        self.assertEqual(revision["state"], "aidlc-revision-ready")
        self.assertIn("service/API path", revision["requirements"][0]["statement"])
        self.assertEqual(handoff["state"], "execution-ready")
        self.assertTrue(handoff["planning_lock"]["writes_allowed"])
        self.assertIn("Requirement Completion Harness", lock.render_execution_handoff(handoff))
        self.assertIn("## Mandatory closure", lock.render_execution_handoff(handoff))
        self.assertIn("tailtrail completion-report --root . --run-id plan-aidlc-handoff", lock.render_execution_handoff(handoff))
        self.assertEqual(activity["aidlc_requirements_answered"], 1)
        self.assertEqual(activity["aidlc_requirements_approved"], 1)

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


if __name__ == "__main__":
    unittest.main()
