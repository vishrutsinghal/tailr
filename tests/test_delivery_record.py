from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ledger = load("dr_ledger", "scripts/run-ledger.py")
anchor_mod = load("dr_anchor", "scripts/change-intent-anchor.py")
lock = load("dr_lock", "scripts/planning_lock.py")
delivery_record = load("dr_live", "scripts/delivery-record.py")


class DeliveryRecordRoleTaggedPathTests(unittest.TestCase):
    def test_plan_shows_traceability_only_proof_and_safe_next_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            proposal = root / "proposal.json"
            proposal.write_text(json.dumps({"requirements": [{
                "statement": "Show proof clarity", "display_id": "REQ-01",
                "likely_paths": ["scripts/task-start.py"],
                "quoted_literals": ["python3 -m unittest tests.test_example -v"],
                "validation_contract": {"state": "required", "tiers": ["unit"], "commands": []},
                "acceptance_criteria": [], "preserve_rules": [], "evidence_plan": [],
            }]}), encoding="utf-8")
            lock.create(root, "proof clarity", "run")
            anchor_mod.draft(root, "run", proposal)
            anchor_mod.approve(root, "run")
            lock.approve(root, "run", True)
            (ledger.state_dir(root, "run") / "planning" / "start-report-v1.json").write_text(
                json.dumps({"report": {"navigator": {"requirement_matrix": [{
                    "display_id": "REQ-01",
                    "quoted_literals": ["python3 -m unittest tests.test_example -v"],
                }]}}}),
                encoding="utf-8",
            )

            section = delivery_record.render_plan(root, "run")

        self.assertIn("Traceability evidence", section)
        self.assertIn("Approved executable proof: none registered", section)
        self.assertIn("traceability-only; not executable yet", section)
        self.assertIn("planning revise", section)

    def test_role_tagged_likely_path_still_matches_changed_files(self) -> None:
        """Regression test: a role-tagged {"path": ..., "role": ...} entry in
        an approved requirement's likely_paths must still match against the
        completion report's changed_scope -- a bare str(dict) here corrupts
        the match to the literal text "{'path': ..., 'role': ...}", silently
        dropping the "Files touched" line for every role-tagged requirement.
        """
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger.init_run(root, "run", "claim")
            proposal = root / "proposal.json"
            proposal.write_text(json.dumps({"requirements": [{
                "statement": "Fix the thing", "likely_paths": ["src/service.py"],
                "acceptance_criteria": [], "preserve_rules": [], "evidence_plan": [],
            }]}), encoding="utf-8")
            draft = anchor_mod.draft(root, "run", proposal)
            anchor_mod.approve(root, "run")
            uid = draft["requirements"][0]["requirement_uid"]
            # Correct the anchor to a role-tagged likely_paths entry, exactly
            # the shape change-intent-anchor.py's own correct() CLI accepts.
            anchor_mod.correct(
                root, "run", uid,
                [{"path": "src/service.py", "role": "implementation-owner"}],
                "role-tagged for this regression test",
            )
            directory = ledger.state_dir(root, "run")
            (directory / "completion-reports").mkdir(parents=True)
            report = {
                "requirement_status": {"requirements": [{
                    "requirement_uid": uid,
                    "implementation_status": "implemented",
                    "verification_status": "pass",
                    "status": "complete",
                }]},
                "changed_scope": {"changed_paths": [
                    {"path": "src/service.py", "vcs_status": "modified", "verified": True, "fingerprint": "sha256:abc"},
                ]},
                "source_artifacts": {},
            }
            (directory / "completion-reports" / "report-1.json").write_text(
                json.dumps(report), encoding="utf-8")
            section = delivery_record.render_closure(root, "run")
        self.assertIn("Files touched", section)
        self.assertIn("`src/service.py`", section)
        self.assertNotIn("{'path'", section)


    def test_approved_command_suppresses_revision_guidance_for_non_command_literals(self) -> None:
        """Issue 23.2 regression: an output path or status sentence must never
        be proposed as a proof-revision command once a real command is approved."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            command = "python3 -m unittest tests.test_example -v"
            proposal = root / "proposal.json"
            proposal.write_text(json.dumps({"requirements": [{
                "statement": "Show proof clarity", "display_id": "REQ-01",
                "likely_paths": ["scripts/task-start.py"],
                "quoted_literals": [
                    command,
                    ".tailtrail/runs/run/delivery-record.md",
                    "CloudWatch trace endpoint is not configured.",
                ],
                "validation_contract": {"state": "required", "tiers": ["unit"], "commands": [command]},
                "acceptance_criteria": [], "preserve_rules": [], "evidence_plan": [],
            }]}), encoding="utf-8")
            lock.create(root, "proof clarity", "run")
            anchor_mod.draft(root, "run", proposal)
            anchor_mod.approve(root, "run")
            lock.approve(root, "run", True)
            (ledger.state_dir(root, "run") / "planning" / "start-report-v1.json").write_text(
                json.dumps({"report": {"navigator": {"requirement_matrix": [{
                    "display_id": "REQ-01",
                    "quoted_literals": [
                        command,
                        ".tailtrail/runs/run/delivery-record.md",
                        "CloudWatch trace endpoint is not configured.",
                    ],
                }]}}}),
                encoding="utf-8",
            )

            section = delivery_record.render_plan(root, "run")

        self.assertIn(f"`{command}`", section)
        self.assertIn("Status", section)
        self.assertNotIn("traceability-only", section)
        self.assertNotIn("planning revise", section)

    def test_proof_row_renders_all_recorded_tiers_not_just_singular_tier(self) -> None:
        """Issue 23.3 regression: a multi-tier receipt must render every tier,
        not only the legacy singular `tier` field."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger.init_run(root, "run", "claim")
            proposal = root / "proposal.json"
            proposal.write_text(json.dumps({"requirements": [{
                "statement": "Fix the thing", "likely_paths": ["src/service.py"],
                "acceptance_criteria": [], "preserve_rules": [], "evidence_plan": [],
            }]}), encoding="utf-8")
            draft = anchor_mod.draft(root, "run", proposal)
            anchor_mod.approve(root, "run")
            uid = draft["requirements"][0]["requirement_uid"]
            directory = ledger.state_dir(root, "run")
            (directory / "completion-reports").mkdir(parents=True)
            report = {
                "requirement_status": {"requirements": [{
                    "requirement_uid": uid,
                    "implementation_status": "implemented",
                    "verification_status": "pass",
                    "status": "complete",
                    "evidence": [{
                        "command": "python3 -m unittest tests.test_example -v",
                        "command_label": "example suite",
                        "tiers": ["unit", "behaviour", "integration"],
                        "outcome": "pass",
                        "evidence_quality": "trusted",
                    }],
                }]},
                "changed_scope": {"changed_paths": []},
                "source_artifacts": {},
            }
            (directory / "completion-reports" / "report-1.json").write_text(
                json.dumps(report), encoding="utf-8")
            section = delivery_record.render_closure(root, "run")

        self.assertIn("Tier: unit, behaviour, integration", section)


if __name__ == "__main__":
    unittest.main()
