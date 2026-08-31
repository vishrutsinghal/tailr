from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if (ROOT / "scripts").as_posix() not in sys.path:
    sys.path.insert(0, (ROOT / "scripts").as_posix())


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


task_start = load("debug_start_planning_task_start", "scripts/task-start.py")
reproduction = load("debug_start_planning_reproduction", "scripts/debug-reproduction.py")
from workflow_runtime import approvals as workflow_approvals
from workflow_runtime import freshness as workflow_freshness
from workflow_runtime import resume as workflow_resume
from workflow_runtime import state as workflow_state


class DebugStartPlanningTests(unittest.TestCase):
    def build(self, root: Path, **kwargs):
        return task_start.build_report(
            "payments are sometimes charged twice after timeout",
            root,
            kwargs.pop("changed", []),
            "python3 scripts/tailtrail.py",
            workflow_override=kwargs.pop("workflow_override", None),
            has_error_artifact=kwargs.pop("has_error_artifact", False),
            has_reproduction_command=kwargs.pop("has_reproduction_command", False),
        )

    def test_debug_start_builds_planning_payload_without_debug_intake(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = self.build(root)

            self.assertEqual(report["debug_plan"]["workflow_type"], "debug-investigation")
            self.assertEqual(report["navigator"]["task_types"], ["debug"])
            self.assertEqual(report["navigator"]["requirement_matrix"][0]["kind"], "debug-investigation")
            self.assertFalse((root / ".tailtrail").exists())

    def test_persisted_debug_start_uses_canonical_planning_lock_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = self.build(root)
            lock = task_start.planning_lock.create(root, report["goal"], run_id="debug-plan-1")
            report["planning_lock"] = lock
            report["workflow_runtime"] = {
                "enabled": False,
                "state": "deferred-to-di-4",
                "reason": "DI-4",
                "boundary": "planning only",
            }
            report["planning_report"] = task_start.planning_lock.save_start_report(root, lock["run_id"], report)
            markdown = task_start.render_markdown(report, verbose=True)

            for heading in (
                "Planning Lock",
                "Start Here",
                "Navigator Decision",
                "Scope",
                "Requirements",
                "Selected TailTrail features",
                "Deferred TailTrail features",
                "Plan",
                "Focused validation",
                "Evidence posture",
                "Approval",
            ):
                self.assertIn(f"## {heading}", markdown)
            self.assertIn("debug-plan-1", markdown)
            self.assertTrue((root / ".tailtrail" / "runs" / "debug-plan-1" / "planning" / "lock-v1.json").is_file())
            self.assertTrue((root / ".tailtrail" / "runs" / "debug-plan-1" / "planning" / "start-report-v1.json").is_file())
            self.assertFalse((root / ".tailtrail" / "runs" / "debug-plan-1" / "debug").exists())

            activated = task_start.planning_lock.activate(root, "debug-plan-1", True)
            self.assertEqual(activated["state"], "reproduction-approval-required")
            self.assertEqual(activated["reproduction_contract"]["revision"], 1)
            self.assertEqual(activated["reproduction_contract"]["unresolved_fields"], ["expected", "reproduction_method"])
            self.assertFalse(task_start.planning_lock.show(root, "debug-plan-1")["writes_allowed"])
            self.assertFalse((root / ".tailtrail" / "runs" / "debug-plan-1" / "anchors" / "approved-v1.json").exists())

    def test_reproduction_revision_freezes_debug_anchor_and_investigation_only_handoff(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = self.build(root)
            lock = task_start.planning_lock.create(root, report["goal"], run_id="debug-di3")
            report["planning_lock"] = lock
            task_start.planning_lock.save_start_report(root, lock["run_id"], report)
            initial = task_start.planning_lock.activate(root, "debug-di3", True)
            requirement_uid = initial["reproduction_contract"]["requirement_uid"]

            revised = reproduction.draft(root, "debug-di3", {
                "requirement_uid": requirement_uid,
                "domain": "api-integration",
                "trigger": initial["reproduction_contract"]["trigger"],
                "expected": "One payment effect and one notification",
                "actual": "Retry creates duplicate payment and notification effects",
                "reproduction_method": "Run the timeout-after-acceptance integration test with two workers",
                "preserve_rules": ["Successful single-worker checkout remains unchanged"],
                "safety_boundary": "Use local adapters only; never call a real payment provider",
                "validation_contract": {"state": "required", "tiers": ["reproduction", "root-cause", "regression", "behaviour"]},
            })
            approved = reproduction.approve(root, "debug-di3", revised["revision"])

            anchor = json.loads((root / ".tailtrail" / "runs" / "debug-di3" / "anchors" / "approved-v1.json").read_text(encoding="utf-8"))
            self.assertEqual(anchor["requirements"][0]["requirement_uid"], requirement_uid)
            self.assertEqual(anchor["requirements"][0]["kind"], "debug-investigation")
            self.assertEqual(anchor["requirements"][0]["validation_contract"]["tiers"], ["reproduction", "root-cause", "regression", "behaviour"])
            self.assertEqual(approved["execution_handoff"]["state"], "investigation-ready")
            self.assertIn("edit project source", approved["execution_handoff"]["forbidden_actions"])
            runtime = approved["execution_handoff"]["workflow_runtime"]
            self.assertEqual(runtime["compiler"]["template_id"], "debug-investigation")
            self.assertEqual(runtime["current_stage"], "d-01-intake")
            self.assertEqual(runtime["current_stage_display"], "D-01 Intake")
            self.assertNotIn("d-08-correction-implementation", runtime["investigation_approval"]["stage_ids"])
            workflow_id = runtime["workflow_id"]
            self.assertEqual(workflow_resume.plan(root, workflow_id)["next_stage_id"], "d-01-intake")
            before = workflow_state.replay(root, workflow_id)["last_valid_projection"]
            self.assertEqual(workflow_state.pause(root, workflow_id)["workflow_status"], "paused")
            self.assertEqual(workflow_state.resume(root, workflow_id)["workflow_status"], "ready")
            after = workflow_state.replay(root, workflow_id)["last_valid_projection"]
            self.assertEqual(after["current_stage_id"], before["current_stage_id"])
            with self.assertRaisesRegex(ValueError, "blocked-missing-authority"):
                workflow_approvals.authorize_stage(root, workflow_id, "d-08-correction-implementation", None)
            self.assertTrue(task_start.planning_lock.assert_write_allowed(root, "debug-di3")["writes_allowed"])
            with self.assertRaisesRegex(ValueError, "investigation only"):
                task_start.planning_lock.assert_source_write_allowed(root, "debug-di3")

            workflow_freshness.ensure(root, workflow_id)
            approved_reproduction = root / approved["execution_handoff"]["reproduction_contract"]
            tampered = json.loads(approved_reproduction.read_text(encoding="utf-8"))
            tampered["actual"] = "externally modified after approval"
            approved_reproduction.write_text(json.dumps(tampered), encoding="utf-8")
            stale = workflow_freshness.assess(root, workflow_id)
            self.assertIn("reproduction-change", stale["change_types"])
            self.assertIn("d-05-experiment", stale["affected_stage_ids"])

    def test_reproduction_approval_is_revision_specific_and_blocks_unresolved_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = self.build(root)
            lock = task_start.planning_lock.create(root, report["goal"], run_id="debug-revision")
            report["planning_lock"] = lock
            task_start.planning_lock.save_start_report(root, lock["run_id"], report)
            task_start.planning_lock.activate(root, "debug-revision", True)

            with self.assertRaisesRegex(ValueError, "fields are unresolved"):
                reproduction.approve(root, "debug-revision", 1)
            complete = reproduction.draft(root, "debug-revision", {
                "domain": "code", "trigger": "retry duplicates an effect", "expected": "one effect",
                "actual": "two effects", "reproduction_method": "run focused retry test",
                "preserve_rules": ["successful path remains valid"], "safety_boundary": "local test doubles only",
            })
            with self.assertRaisesRegex(ValueError, "revision mismatch"):
                reproduction.approve(root, "debug-revision", 1)
            reproduction.approve(root, "debug-revision", complete["revision"])
            with self.assertRaisesRegex(ValueError, "immutable"):
                reproduction.draft(root, "debug-revision", {
                    "domain": "code", "trigger": "other", "expected": "a", "actual": "b",
                    "reproduction_method": "c", "safety_boundary": "d",
                })

    def test_debug_start_records_presence_flags_without_raw_values(self):
        with tempfile.TemporaryDirectory() as temp:
            report = self.build(
                Path(temp),
                has_error_artifact=True,
                has_reproduction_command=True,
            )
            evidence = report["debug_plan"]["classification_evidence"]

            self.assertTrue(evidence["error_artifact_supplied"])
            self.assertTrue(evidence["reproduction_command_supplied"])
            serialized = json.dumps(report)
            self.assertNotIn("attached_error", serialized)
            self.assertNotIn("attached_command", serialized)

    def test_explicit_build_override_retains_normal_start_path(self):
        with tempfile.TemporaryDirectory() as temp:
            report = self.build(Path(temp), workflow_override="build")

            self.assertNotIn("debug_plan", report)
            self.assertEqual(report["navigator"]["workflow_classification"]["workflow_type"], "build")

    def test_debug_start_uses_saved_graph_without_freshness_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache = root / ".tailtrail" / "code-graph-cache.json"
            cache.parent.mkdir(parents=True)
            cache.write_text(json.dumps({
                "schema_version": "1",
                "scope": ["src/payments.py", "tests/test_payments.py"],
                "graph": {
                    "confidence": "medium",
                    "suggested_read_order": ["src/payments.py", "tests/test_payments.py"],
                },
            }), encoding="utf-8")

            report = self.build(root)

            self.assertEqual(report["debug_plan"]["scope_source"], "saved-code-graph")
            self.assertEqual(report["navigator"]["graph_cache"]["status"], "saved-unverified")
            self.assertEqual(
                [item["path"] for item in report["navigator"]["likely_impacted_files"][:2]],
                ["src/payments.py", "tests/test_payments.py"],
            )

    def test_public_start_cli_persists_and_prints_canonical_debug_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "tailtrail.py"),
                    "start",
                    "investigate why cancellation publishes two events",
                    "--root",
                    str(root),
                    "--planning-run-id",
                    "debug-cli-1",
                    "--verbose",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertIn("# TailTrail Debug Start Plan", result.stdout)
            self.assertIn("Run ID: `debug-cli-1`", result.stdout)
            self.assertIn("## Proposed reproduction questions", result.stdout)
            self.assertTrue((root / ".tailtrail" / "runs" / "debug-cli-1" / "planning" / "start-report-v1.json").is_file())
            self.assertFalse((root / ".tailtrail" / "runs" / "debug-cli-1" / "debug").exists())


if __name__ == "__main__":
    unittest.main()
