import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location("plan_render", Path(__file__).resolve().parents[1] / "scripts" / "plan_render.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
render_plan = _module.render_plan


def _envelope() -> dict:
    return {
        "schema_version": "1",
        "type": "tailtrail-start-report",
        "run_id": "start-20260914-a1b2c3",
        "goal": "Add JWT token rotation with refresh-token support",
        "report": {
            "aidlc_mode": {
                "mode": "standard",
                "selection": "multi-file feature with a new public token contract",
                "full_escalation": {"state": "not-eligible", "reason": "not requested"},
            },
            "navigator": {
                "selected_features": [
                    {"name": "Navigator Planning", "reason": "Drafts the requirement matrix and scope"},
                    {"name": "Mystery Feature", "reason": "unknown feature note"},
                ],
                "skipped_features": [
                    {"name": "Security Review", "reason": "no security signal detected"},
                ],
                "token_budget": {
                    "budget_band": "5k-12k",
                    "escalation_rule": "If required context appears to exceed 23000 tokens, pause and ask before loading more.",
                },
                "suggested_commands": [
                    "python3 scripts/tailtrail.py test plan --goal \"rotation\"",
                    "python3 scripts/tailtrail.py graph map --changed src/auth/tokens.py",
                ],
            },
            "token_posture": {
                "baseline_tokens": 146996,
                "used_tokens": 423,
                "avoided_tokens": 146573,
                "estimated_reduction_percent": 99.71,
                "evidence": "Approximate file character count only. Do not claim exact model/API token savings.",
            },
            "requirement_matrix": [
                {
                    "display_id": "REQ-01",
                    "kind": "change",
                    "statement": "Implement refresh-token issuance with 15-minute access tokens.",
                    "acceptance_criteria": ["A valid credential exchange returns a 15-minute access token."],
                    "likely_paths": ["src/auth/tokens.py"],
                    "validation_contract": {"state": "required", "tiers": ["unit"]},
                },
            ],
            "planning_lock": {
                "status": "awaiting-approval",
                "run_id": "start-20260914-a1b2c3",
            },
            "next_actions": [
                {"action": "approve", "label": "Approve implementation.", "prompt": "Approve this plan."},
                {"action": "edit", "label": "Edit the plan.", "prompt": "Edit the plan."},
            ],
        },
    }


def _lock() -> dict:
    return {
        "pipeline": {
            "active_stage": "PENDING",
            "completed_stages": [],
            "stage_sequence": ["IMPLEMENTATION", "TESTING", "INFRA"],
        }
    }


class TestPlanRender(unittest.TestCase):
    def setUp(self):
        self.envelope = _envelope()
        self.lock = _lock()

    def test_banner_is_present(self):
        output = render_plan(self.envelope, lock=self.lock)
        self.assertIn("+---", output)
        self.assertIn("| TAILTRAIL", output)
        self.assertIn("Requirement completion and drift control", output)

    def test_aidlc_mode_is_displayed(self):
        output = render_plan(self.envelope, lock=self.lock)
        self.assertIn("AIDLC MODE", output)
        self.assertIn("standard", output)
        self.assertIn("multi-file feature", output)

    def test_features_have_one_liners(self):
        output = render_plan(self.envelope, lock=self.lock)
        self.assertIn("TAILTRAIL FEATURES USED", output)
        self.assertIn("Navigator Planning", output)
        self.assertIn("Drafts the requirement matrix and scope", output)
        self.assertNotIn("Skipped features:", output)

    def test_verbose_adds_explanation_and_skipped(self):
        output = render_plan(self.envelope, verbose=True, lock=self.lock)
        self.assertIn("TAILTRAIL FEATURES USED (verbose)", output)
        self.assertIn("↳ Reads discovery metadata only", output)
        self.assertIn("Skipped features:", output)
        self.assertIn("Security Review", output)
        unknown_note = "Mystery Feature"
        self.assertIn(unknown_note, output)
        self.assertIn("Advisory control", output)

    def test_token_usage_and_reduction_are_displayed(self):
        output = render_plan(self.envelope, lock=self.lock)
        self.assertIn("TOKEN USAGE", output)
        self.assertIn("146,996", output)
        self.assertIn("423", output)
        self.assertIn("146,573", output)
        self.assertIn("99.71%", output)
        self.assertIn("Approximate file character count only", output)
        self.assertIn("5k-12k", output)

    def test_requirements_are_rendered(self):
        output = render_plan(self.envelope, lock=self.lock)
        self.assertIn("REQUIREMENTS (approve these, not just the plan)", output)
        self.assertIn("REQ-01", output)
        self.assertIn("change", output)
        self.assertIn("Implement refresh-token issuance", output)
        self.assertIn("Accept:", output)
        self.assertIn("src/auth/tokens.py", output)
        self.assertIn("Proof:    unit", output)

    def test_requirements_absent_shows_honest_note(self):
        envelope = _envelope()
        del envelope["report"]["requirement_matrix"]
        output = render_plan(envelope, lock=self.lock)
        self.assertIn("No requirement matrix drafted yet", output)

    def test_pipeline_plan_uses_lock_and_scope_contracts(self):
        output = render_plan(self.envelope, lock=self.lock)
        self.assertIn("PIPELINE PLAN", output)
        self.assertIn("IMPLEMENTATION", output)
        self.assertIn("impl-badge", output)
        self.assertIn("implementation-owner", output)
        self.assertIn("SecurityBoundaryError", output)

    def test_drift_gate_preview_is_present(self):
        output = render_plan(self.envelope, lock=self.lock)
        self.assertIn("DRIFT GATE", output)
        self.assertIn("unlinked green tests are not proof", output)
        self.assertIn("design review after 3 strikes", output)

    def test_placeholders_are_never_rendered_as_runnable(self):
        envelope = _envelope()
        envelope["report"]["navigator"]["suggested_commands"].append(
            "tailtrail receipt capture --loaded REPLACE_WITH_FILE --loaded-exactness REPLACE_WITH_strategy --approved"
        )
        output = render_plan(envelope, lock=self.lock)
        self.assertNotIn("REPLACE_WITH", output)
        self.assertNotIn("REPLACE_WITH_FILE", output)
        self.assertNotIn("REPLACE_WITH_strategy", output)
        self.assertIn("<you decide>", output)
        self.assertIn("<you decide: >", output)
        self.assertIn("tailtrail receipt capture", output)
        self.assertIn("<you decide: >", output)
        self.assertIn("<you decide: >", output)
        self.assertIn("<you decide: >", output)
        self.assertIn("<you decide: >", output)
        self.assertIn("<you decide: >", output)
        self.assertIn("<you decide: >", output)
        self.assertIn("<you decide: >", output)
        self.assertIn("<you decide: >", output)
        self.assertIn("<you decide: >", output)

    def test_next_actions_are_summarized(self):
        output = render_plan(self.envelope, lock=self.lock)
        self.assertIn("approve | edit", output)

    def test_awaiting_approval_status_is_explicit(self):
        output = render_plan(self.envelope, lock=self.lock)
        self.assertIn("AWAITING APPROVAL", output)


if __name__ == "__main__":
    unittest.main()