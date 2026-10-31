from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


verbose = load("start_plan_presentation_verbose", "scripts/verbose-reporting.py")
lock = load("start_plan_presentation_lock", "scripts/planning_lock.py")
ledger = load("start_plan_presentation_ledger", "scripts/run-ledger.py")
audit = load("start_plan_presentation_audit", "scripts/planning-audit.py")
task_start = load("start_plan_presentation_task_start", "scripts/task-start.py")


def sample_report() -> dict[str, object]:
    return {
        "goal": "Render a reviewable Start Plan.",
        "navigator": {
            "scope_evidence": {"implementation_owners": ["scripts/presenter.py"]},
            "requirement_matrix": [{
                "display_id": "REQ-01",
                "requirement_uid": "req-presentation",
                "kind": "change",
                "statement": "Render a reviewable Start Plan.",
                "acceptance_criteria": ["The normal plan is readable."],
                "preserve_rules": ["Keep machine records available."],
                "likely_paths": ["scripts/presenter.py"],
                "scope_evidence": {
                    "implementation_owners": ["scripts/presenter.py"],
                    "inspection_paths": ["scripts/source.py"],
                    "proof_paths": ["tests/test_presenter.py"],
                },
                "validation_contract": {
                    "state": "required",
                    "tiers": ["unit"],
                    "commands": ["python3 -m unittest tests.test_presenter"],
                    "candidate_paths": ["tests/test_presenter.py"],
                },
            }],
        },
        "guided_delivery": {"stages": ["render", "validate"], "selected": [{"name": "Navigator"}]},
        "risks": ["projection drift"],
    }


class StartPlanPresentationTests(unittest.TestCase):
    def test_public_plan_renders_validation_only_scope_without_implementation_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "run-validation-only"
            report = sample_report()
            requirement = report["navigator"]["requirement_matrix"][0]  # type: ignore[index]
            # A heuristic path may remain for discovery, but explicit scope
            # authority says this validation-only plan has no editable owner.
            requirement["likely_paths"] = ["scripts/heuristic-candidate.py"]
            requirement["scope_evidence"] = {
                "implementation_owners": [],
                "inspection_paths": ["scripts/source.py"],
                "proof_paths": [],
            }
            requirement["validation_contract"] = {
                "state": "required",
                "tiers": ["unit"],
                "commands": ["python3 -m unittest tests.test_presenter"],
                # A planning revision records proof-only authority here.
                "editable_paths": ["tests/test_presenter.py"],
            }
            report["host_input_contract"] = {"request_mode": "validation-only"}
            lock.create(root, str(report["goal"]), run_id)
            ledger.atomic_json(lock.start_report_path(root, run_id), {"report": report})
            ledger.append_event(
                root, run_id, "planning_audit_completed",
                {"status": "clean", "finding_count": 0},
            )

            rendered = lock.render_start_plan(root, run_id)

        self.assertIn("**Request mode:** `validation-only`", rendered)
        self.assertIn("**Editable owner(s):** not applicable (`validation-only`; no implementation authority).", rendered)
        self.assertIn("**Proof path(s):** `tests/test_presenter.py`", rendered)
        self.assertIn("**Read-only / proof-only scope:** `scripts/source.py`, `tests/test_presenter.py`", rendered)
        self.assertIn("No implementation owner is declared for this `validation-only` plan", rendered)
        self.assertIn("**READY FOR APPROVAL**", rendered)

    def test_implementation_plan_still_blocks_without_an_owner(self) -> None:
        report = sample_report()
        requirement = report["navigator"]["requirement_matrix"][0]  # type: ignore[index]
        requirement["likely_paths"] = []
        requirement["scope_evidence"]["implementation_owners"] = []
        rendered = verbose.generate_start_plan_normal(
            "run-implementation-owner-gate",
            report["navigator"]["requirement_matrix"],  # type: ignore[index]
            {},
            str(report["goal"]),
            plan_data={
                "report": report,
                "planning_lock": {"status": "awaiting-approval"},
                "planning_events": [{"event_type": "planning_audit_completed", "payload": {"status": "clean"}}],
            },
        )

        self.assertIn("**NOT READY FOR APPROVAL**", rendered)
        self.assertIn("implementation ownership", rendered)

    def test_normal_plan_renders_bound_inputs_without_granting_scope_authority(self) -> None:
        report = sample_report()
        report["input_roles"] = {
            "inputs": [
                {"input_id": "IN-01", "role": "target", "locator": "/repo", "access": "read-write", "status": "verified"},
                {
                    "input_id": "IN-02", "role": "design-reference",
                    "locator": "/repo/design.md", "access": "read-only",
                    "status": "verified-unread",
                },
                {
                    "input_id": "IN-03", "role": "requirement-artifact",
                    "locator": "/repo/requirements.md", "access": "read-only",
                    "status": "inspected", "sha256": "abc123",
                },
            ],
        }
        rendered = verbose.generate_start_plan_normal(
            "run-bound-inputs",
            report["navigator"]["requirement_matrix"],  # type: ignore[index]
            {},
            str(report["goal"]),
            plan_data={
                "report": report,
                "planning_lock": {"status": "awaiting-approval"},
                "planning_events": [{"event_type": "planning_audit_completed", "payload": {"status": "clean"}}],
            },
        )

        self.assertIn("## Bound Planning Inputs", rendered)
        self.assertIn("`/repo/design.md`", rendered)
        self.assertIn("`/repo/requirements.md`", rendered)
        self.assertIn("`abc123`", rendered)
        self.assertIn("`not hash-bound`", rendered)
        self.assertIn("never grant editable implementation scope", rendered)
        self.assertIn("**Editable scope:** `scripts/presenter.py`.", rendered)

    def test_multi_requirement_host_proof_is_retained_as_unbound_context(self) -> None:
        scripts_path = str(ROOT / "scripts")
        if scripts_path not in sys.path:
            sys.path.insert(0, scripts_path)
        start = load("start_plan_projection_task_start", "scripts/task-start.py")
        requirements = [
            {
                "display_id": "REQ-01",
                "statement": "Preserve host scope context.",
                "validation_contract": {"state": "required", "tiers": ["unit"]},
            },
            {
                "display_id": "REQ-02",
                "statement": "Do not auto-credit global proof.",
                "validation_contract": {"state": "required", "tiers": ["unit"]},
            },
        ]
        plan = {
            "host_declared_scope_roles": {
                # This proposed owner must never become editable scope merely
                # because it appeared in a validated host contract.
                "implementation_owners": ["scripts/unverified-owner.py"],
                "inspection_paths": ["scripts/read-only-input.py"],
                "proof_paths": ["tests/test_host_context.py"],
            },
            "requirement_matrix": requirements,
        }
        validated = {
            "contract_id": "ctr-global-proof",
            "fingerprint": "sha256:proof-context",
            "paths": [
                {"path": "tests/test_host_context.py", "role": "existing-proof-path"},
            ],
            "proof": {
                "command": "python3 -m unittest tests.test_host_context",
                "tiers": ["unit"],
            },
        }

        start.apply_host_contract_role_projection(plan)
        focused = [{"requirement_id": "REQ-01", "tier": "unit", "command": "python3 -m unittest tests.test_local", "candidate_state": "existing"}]
        projected = start.apply_host_contract_proof(Path("."), requirements, focused, validated)
        lines: list[str] = []
        start.append_proof_authorization_status(lines, {}, requirements, None)
        rendered = "\n".join(lines)

        self.assertEqual(projected, focused)
        for requirement in requirements:
            scope = requirement["scope_evidence"]
            self.assertEqual(scope["implementation_owners"], [])
            self.assertEqual(scope["inspection_paths"], ["scripts/read-only-input.py"])
            self.assertEqual(scope["proof_paths"], ["tests/test_host_context.py"])
            self.assertEqual(requirement["validation_contract"].get("commands", []), [])
            self.assertEqual(requirement["host_contract_proof_context"]["state"], "unbound-global-proof")
        self.assertIn("Global host proof context", rendered)
        self.assertIn("unbound context; not executable requirement proof", rendered)
        self.assertIn("python3 -m unittest tests.test_host_context", rendered)

    def test_verbose_start_plan_resolves_command_id_through_report_registry(self) -> None:
        goal = "Fix Start Plan command rendering."
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scripts").mkdir()
            (root / "scripts" / "task-start.py").write_text(
                "def render_start_plan():\n    return None\n",
                encoding="utf-8",
            )
            report = task_start.build_report(
                goal,
                root,
                ["scripts/task-start.py"],
                "tailtrail",
                aidlc_mode="lite",
                requirement_interpretation=task_start.requirement_discovery.interpretation(goal),
            )

        command = "python3 -m unittest tests.test_start_plan_presentation"
        report["focused_validation"] = [{
            "requirement_id": "REQ-01",
            "tier": "unit",
            "candidate": "tests/test_start_plan_presentation.py",
            "candidate_state": "existing",
            "command_id": "cmd-projected",
            "status": "planned after approval",
        }]
        report["command_registry"] = {
            "cmd-projected": {"command": command, "kind": "proof"}
        }

        rendered = task_start.render_markdown(report, verbose=True)

        self.assertIn(command, rendered)

    def test_verbose_without_aidlc_is_structured_markdown_not_json(self) -> None:
        report = sample_report()
        requirements = report["navigator"]["requirement_matrix"]  # type: ignore[index]
        rendered = verbose.generate_start_plan_verbose(
            "run-presentation", requirements, {}, "Render a reviewable Start Plan.",
            plan_data={"report": report, "planning_lock": {"status": "awaiting-approval"}},
        )

        self.assertIn("## Planning Lock", rendered)
        self.assertIn("## Command Reference Registry", rendered)
        self.assertIn("## Validation Requirements And Focused Validation Matrix", rendered)
        self.assertIn("## Architecture Analysis", rendered)
        self.assertIn("## Behaviour Analysis", rendered)
        self.assertIn("## Token Estimate", rendered)
        self.assertNotIn("## AIDLC Decisions", rendered)
        self.assertNotIn("```json", rendered)
        self.assertNotIn("## Complete Saved Planning Payload", rendered)

    def test_verbose_includes_aidlc_only_when_saved_artifacts_exist(self) -> None:
        report = sample_report()
        requirements = report["navigator"]["requirement_matrix"]  # type: ignore[index]
        rendered = verbose.generate_start_plan_verbose(
            "run-aidlc", requirements, {}, "Render a reviewable Start Plan.",
            plan_data={
                "report": report,
                "planning_lock": {"status": "awaiting-approval"},
                "aidlc": {"aidlc-requirements-v1.json": {"questions": [{"id": "Q1", "question": "Which proof?"}]}},
            },
        )

        self.assertIn("## AIDLC Decisions", rendered)
        self.assertIn("Which proof?", rendered)
        self.assertNotIn("```json", rendered)

    def test_planning_show_defaults_to_the_normal_saved_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "run-public-plan"
            report = sample_report()
            lock.create(root, str(report["goal"]), run_id)
            ledger.atomic_json(lock.start_report_path(root, run_id), {"report": report})
            lock.generate_start_plan_verbose_report(root, run_id)
            visible = root / "session-reports" / run_id / "start-plan.md"
            visible.write_text("# Legacy plan\n\n```json\n{}\n```\n", encoding="utf-8")

            output = io.StringIO()
            with mock.patch.object(sys, "argv", ["planning-lock.py", "show", "--root", str(root), "--run-id", run_id]):
                with contextlib.redirect_stdout(output):
                    self.assertEqual(lock.main(), 0)
            refreshed_verbose = visible.read_text(encoding="utf-8")

        rendered = output.getvalue()
        self.assertIn("# TailTrail Start Plan", rendered)
        self.assertIn("## Command Reference Registry", rendered)
        self.assertIn("## Validation Requirements And Focused Validation Matrix", rendered)
        self.assertIn("## Implementation Boundary", rendered)
        self.assertIn("## Approval Checklist", rendered)
        self.assertIn("## Review Cycles Summary", rendered)
        self.assertIn("session-reports/run-public-plan/start-plan.md", rendered)
        self.assertNotIn('"writes_allowed"', rendered)
        self.assertNotIn("```json", refreshed_verbose)

    def test_initial_review_is_cycle_one_not_zero_revisions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root / ".tailtrail" / "runs" / "run-cycle-one"
            run.mkdir(parents=True)
            (run / "events.jsonl").write_text("", encoding="utf-8")
            summary = audit._build_review_cycles_summary(root, "run-cycle-one")

        self.assertEqual(summary["total_review_cycles"], 1)
        self.assertEqual(summary["revision_cycles"], 0)
        self.assertEqual(summary["cycles"][0]["status"], "initial-review")

    def test_normal_plan_requires_a_clean_audit_before_ready_for_approval(self) -> None:
        report = sample_report()
        requirements = report["navigator"]["requirement_matrix"]  # type: ignore[index]
        rendered = verbose.generate_start_plan_normal(
            "run-audit-gate", requirements, {}, str(report["goal"]),
            plan_data={"report": report, "planning_lock": {"status": "awaiting-approval"}},
        )

        self.assertIn("Mandatory planning audit is clean", rendered)
        self.assertIn("NOT READY FOR APPROVAL", rendered)
        self.assertIn("clean mandatory planning audit", rendered)


class RequirementDraftingRegressionTests(unittest.TestCase):
    def test_mode_marker_is_never_a_requirement_row(self) -> None:
        import requirement_discovery

        rows = requirement_discovery.statements("Add a focused parser check. Planning only.")
        self.assertFalse(any(requirement_discovery.MODE_MARKER.match(row.strip()) for row in rows), rows)
        self.assertTrue(any("parser" in row.lower() for row in rows), rows)

    def test_generic_template_criteria_are_fallbacks_only(self) -> None:
        import requirement_discovery

        interpreted = {"requirements": [{
            "display_id": "REQ-01",
            "statement": "Reject empty parser input.",
            "kind": "change",
            "extracted_acceptance_criteria": ["The parser rejects empty input."],
        }]}
        rows = requirement_discovery.matrix("Reject empty parser input.", [], interpreted)
        self.assertTrue(rows)
        for row in rows:
            self.assertNotIn(requirement_discovery.ACCEPTANCE_TEMPLATE, row["acceptance_criteria"])
            self.assertIn("The parser rejects empty input.", row["acceptance_criteria"])


def requirement_section(rendered: str, identifier: str) -> str:
    start = rendered.index(f"### {identifier}")
    end = rendered.find("\n### ", start + 1)
    return rendered[start:end if end != -1 else len(rendered)]


class StartPlanRequirementRenderingTests(unittest.TestCase):
    def render(self, report: dict[str, object], events: list[dict[str, object]]) -> str:
        requirements = report["navigator"]["requirement_matrix"]  # type: ignore[index]
        return verbose.generate_start_plan_normal(
            "run-req-render", requirements, {}, str(report["goal"]),
            plan_data={"report": report, "planning_events": events,
                       "planning_lock": {"status": "awaiting-approval"}},
        )

    def test_requirement_section_shows_its_declared_proof_command_text(self) -> None:
        rendered = self.render(sample_report(), [])
        section = requirement_section(rendered, "REQ-01")
        self.assertIn("python3 -m unittest tests.test_presenter", section)

    def test_requirement_without_command_reports_unresolved_proof_state(self) -> None:
        report = sample_report()
        requirement = report["navigator"]["requirement_matrix"][0]  # type: ignore[index]
        requirement["validation_contract"]["commands"] = []
        section = requirement_section(self.render(report, []), "REQ-01")
        self.assertIn("| unit | `unresolved` |", section)
        self.assertNotIn("| unit | `cmd-", section)

    def test_checklist_follows_latest_audit_not_an_earlier_clean_one(self) -> None:
        events = [
            {"event_type": "planning_audit_completed", "payload": {"status": "clean"}},
            {"event_type": "planning_audit_completed", "payload": {"status": "gaps-found"}},
        ]
        rendered = self.render(sample_report(), events)
        self.assertIn("- [ ] Mandatory planning audit is clean", rendered)
        self.assertNotIn("- [x] Mandatory planning audit is clean", rendered)

    def test_refresh_after_revision_rewrites_visible_plan_from_pending_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "run-regenerate"
            report = sample_report()
            lock.create(root, str(report["goal"]), run_id)
            ledger.atomic_json(lock.start_report_path(root, run_id), {"report": report})
            lock.refresh_visible_start_plan(root, run_id)
            visible = lock.VR.visible_report_path(root, run_id, "start-plan")
            self.assertIn("**Description:** Render a reviewable Start Plan.", visible.read_text(encoding="utf-8"))

            revised = copy.deepcopy(report)
            revised["navigator"]["requirement_matrix"][0]["statement"] = "Render a revised Start Plan."  # type: ignore[index]
            with mock.patch.object(lock, "_pending_report_override", return_value=revised):
                lock.refresh_visible_start_plan(root, run_id)

            text = visible.read_text(encoding="utf-8")
        self.assertIn("**Description:** Render a revised Start Plan.", text)
        self.assertNotIn("**Description:** Render a reviewable Start Plan.", text)


if __name__ == "__main__":
    unittest.main()
