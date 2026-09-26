from __future__ import annotations

import base64
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURE = ROOT / "tests" / "fixtures" / "requirement-routing" / "infrastructure-secret-ambiguous.json"
if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


requirement_discovery = load(
    "tailtrail_phase0_requirement_discovery",
    "scripts/requirement_discovery.py",
)
task_start = load("tailtrail_phase0_task_start", "scripts/task-start.py")
requirement_intake = load(
    "tailtrail_phase0_requirement_intake", "scripts/requirement_intake.py"
)


class RequirementRoutingPhase0Tests(unittest.TestCase):
    """Executable red baseline for the requirement-sufficiency routing defect.

    Expected failures describe behavior that later implementation phases must
    make pass.  Passing safeguards remain ordinary tests so Phase 0 also proves
    that host-supplied material questions already stop before scope discovery.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def host_interpretation(self, host: str = "codex") -> dict:
        goal = self.fixture["goal"]
        target = self.fixture["target_scope"]
        return {
            "schema_version": "1",
            "type": "tailtrail-host-requirement-interpretation",
            "host": host,
            "goal": goal,
            "private_reasoning_excluded": True,
            "clauses": [
                {
                    "clause_id": "C-01",
                    "role": "outcome",
                    "text": "Create the dapdes-act/dev/auditlogging/apigee-client-credentials resource",
                },
                {"clause_id": "C-02", "role": "scope", "text": f"in {target}"},
                {
                    "clause_id": "C-03",
                    "role": "context",
                    "text": "because it does not exist in AWS and is needed to store OEM credentials.",
                },
            ],
            "requirements": [
                {
                    "display_id": "REQ-01",
                    "statement": self.fixture["expected_requirement"],
                    "kind": "change",
                    "source_clause_ids": ["C-01", "C-03"],
                    "intent_terms": ["create", "resource", "aws", "store", "oem", "credentials"],
                    "quoted_literals": [],
                    "intent_class": "general",
                    "confidence": "medium",
                }
            ],
            "material_questions": [
                "Which AWS resource type should store these credentials: AWS Secrets Manager, SSM Parameter Store, or another service?"
            ],
        }

    def run_start(self, root: Path, *, host_proposal: dict | None = None) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(SCRIPTS / "task-start.py"),
            self.fixture["goal"],
            "--root",
            str(root),
            "--aidlc",
            "lite",
            "--no-planning-lock",
            "--format",
            "json",
        ]
        if host_proposal is not None:
            encoded = base64.b64encode(json.dumps(host_proposal).encode("utf-8")).decode("ascii")
            command.extend(
                [
                    "--host",
                    str(host_proposal["host"]),
                    "--requirement-interpretation-base64",
                    encoded,
                ]
            )
        return subprocess.run(command, text=True, capture_output=True, check=False)

    def test_deterministic_fallback_detects_unresolved_infrastructure_resource_type(self) -> None:
        interpreted = requirement_discovery.interpretation(self.fixture["goal"])

        self.assertEqual(interpreted["state"], "clarification-required")
        self.assertEqual(interpreted["sufficiency"]["recommended_route"], "lite-questions")
        self.assertEqual(
            interpreted["sufficiency"]["material_decisions"][0]["decision_class"],
            "infrastructure-resource-type",
        )
        question_text = " ".join(interpreted["material_questions"])
        for term in self.fixture["expected_question_terms"]:
            self.assertIn(term, question_text)

    def test_repository_path_is_scope_and_not_requirement_prose(self) -> None:
        interpreted = requirement_discovery.interpretation(self.fixture["goal"])

        self.assertEqual(
            [row["statement"] for row in interpreted["requirements"]],
            [self.fixture["expected_requirement"]],
        )
        self.assertNotIn(
            self.fixture["target_scope"],
            interpreted["requirements"][0]["statement"],
        )
        self.assertTrue(
            any(
                clause["role"] == "scope" and self.fixture["target_scope"] in clause["text"]
                for clause in interpreted["clauses"]
            )
        )
        self.assertEqual(
            interpreted["sufficiency"]["scope"],
            [{"clause_id": "S-01", "text": self.fixture["target_scope"]}],
        )

    def test_navigator_recommends_standard_for_material_infrastructure_uncertainty(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            selected = task_start.aidlc_mode_selection(
                self.fixture["goal"],
                None,
                Path(temp),
                {"risk_indicators": ["infrastructure", "security"]},
                None,
            )

        self.assertEqual(selected.get("requested_mode", selected.get("mode")), "standard")
        self.assertNotEqual(selected.get("selection"), "default")

    def test_navigator_keeps_one_isolated_decision_in_lite(self) -> None:
        interpreted = requirement_discovery.interpretation(self.fixture["goal"])

        routed = task_start.navigator_requirement_route(
            self.fixture["goal"], None, interpreted["sufficiency"]
        )

        self.assertEqual(routed["state"], "clarification-required")
        self.assertEqual(routed["recommended_route"], "lite-questions")
        self.assertEqual(routed["routing_selection"], "navigator-bounded-clarification")

    def test_navigator_routes_multiple_consequential_decisions_to_standard(self) -> None:
        interpreted = requirement_discovery.interpretation(self.fixture["goal"])
        sufficiency = dict(interpreted["sufficiency"])
        first = dict(sufficiency["material_decisions"][0])
        second = dict(first)
        second["id"] = "DEC-02"
        second["decision_class"] = "production-security-boundary"
        sufficiency["material_decisions"] = [first, second]

        routed = task_start.navigator_requirement_route(
            self.fixture["goal"] + " for production security", None, sufficiency
        )

        self.assertEqual(routed["state"], "standard-recommended")
        self.assertEqual(routed["recommended_route"], "aidlc-standard")
        self.assertEqual(routed["routing_selection"], "navigator-risk-routing")

    def test_explicit_lite_prevents_automatic_standard_routing(self) -> None:
        interpreted = requirement_discovery.interpretation(self.fixture["goal"])
        sufficiency = dict(interpreted["sufficiency"])
        second = dict(sufficiency["material_decisions"][0])
        second["id"] = "DEC-02"
        sufficiency["material_decisions"] = [
            sufficiency["material_decisions"][0],
            second,
        ]

        routed = task_start.navigator_requirement_route(
            self.fixture["goal"] + " for production security", "lite", sufficiency
        )

        self.assertEqual(routed["state"], "clarification-required")
        self.assertEqual(routed["recommended_route"], "lite-questions")
        self.assertEqual(routed["routing_selection"], "explicit-mode")

    def test_explicit_full_preserves_full_requirement_routing(self) -> None:
        interpreted = requirement_discovery.interpretation(self.fixture["goal"])

        routed = task_start.navigator_requirement_route(
            self.fixture["goal"], "full", interpreted["sufficiency"]
        )

        self.assertEqual(routed["state"], "full-recommended")
        self.assertEqual(routed["recommended_route"], "aidlc-full")
        self.assertEqual(routed["routing_selection"], "explicit-mode")

    def test_only_qualifying_hands_free_uncertainty_routes_to_full(self) -> None:
        interpreted = requirement_discovery.interpretation(self.fixture["goal"])

        bounded = task_start.navigator_requirement_route(
            self.fixture["goal"] + " hands-free", None, interpreted["sufficiency"]
        )
        consequential = task_start.navigator_requirement_route(
            self.fixture["goal"] + " hands-free production security",
            None,
            interpreted["sufficiency"],
        )

        self.assertEqual(bounded["recommended_route"], "lite-questions")
        self.assertEqual(consequential["state"], "full-recommended")
        self.assertEqual(consequential["recommended_route"], "aidlc-full")

    def test_standard_routing_stops_before_graph_scope_and_lock(self) -> None:
        goal = self.fixture["goal"] + " for production security"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "task-start.py"),
                    goal,
                    "--root",
                    str(root),
                    "--format",
                    "json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            report = json.loads(completed.stdout)
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(report["type"], "tailtrail-aidlc-standard-routing")
            self.assertEqual(report["recommended_route"], "aidlc-standard")
            self.assertTrue((root / ".tailtrail" / "requirement-intakes" / report["intake_id"] / "current.json").is_file())
            self.assertFalse((root / ".tailtrail" / "runs").exists())
            self.assertFalse((root / "tailtrail-meta").exists())

    def test_host_material_question_preempts_scope_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            completed = self.run_start(Path(temp), host_proposal=self.host_interpretation())

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        report = json.loads(completed.stdout)
        self.assertEqual(report["type"], "tailtrail-requirement-clarification")
        self.assertNotIn("scope", report)
        self.assertNotIn("implementation_owner", json.dumps(report))

    def test_agent_hosts_require_typed_interpretation_before_scope(self) -> None:
        for host in ("codex", "copilot", "claude"):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                command = [
                    sys.executable,
                    str(SCRIPTS / "task-start.py"),
                    "Update the order service validation.",
                    "--root",
                    str(root),
                    "--host",
                    host,
                    "--aidlc",
                    "lite",
                    "--format",
                    "json",
                ]
                completed = subprocess.run(command, text=True, capture_output=True, check=False)
                report = json.loads(completed.stdout)

                self.assertEqual(completed.returncode, 2)
                self.assertEqual(
                    report["type"],
                    "tailtrail-host-requirement-interpretation-required",
                )
                self.assertEqual(report["host"], host)
                self.assertEqual(report["status"], "awaiting-host-interpretation")
                self.assertIsNone(report["planning_lock"])
                self.assertFalse((root / ".tailtrail").exists())

    def test_every_agent_host_can_supply_the_same_closed_interpretation_contract(self) -> None:
        for host in ("codex", "copilot", "claude"):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as temp:
                proposal = self.host_interpretation(host)
                completed = self.run_start(Path(temp), host_proposal=proposal)
                report = json.loads(completed.stdout)

                self.assertEqual(completed.returncode, 0)
                self.assertEqual(report["type"], "tailtrail-requirement-clarification")
                self.assertNotEqual(
                    report["type"],
                    "tailtrail-host-requirement-interpretation-required",
                )

    def test_non_agent_client_retains_deterministic_interpretation(self) -> None:
        interpreted = requirement_discovery.interpretation(
            "Create the named AWS Secrets Manager secret for OEM credentials."
        )

        self.assertEqual(interpreted["source"], "deterministic-fallback")
        self.assertEqual(interpreted["state"], "sufficient")

    def test_debug_host_keeps_its_debug_diagnosis_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "task-start.py"),
                    "debug repeated report steps",
                    "--root",
                    temp,
                    "--host",
                    "codex",
                    "--debug",
                    "--format",
                    "json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        report = json.loads(completed.stdout)
        self.assertEqual(report["type"], "tailtrail-debug-diagnosis-required")

    def test_explicit_standard_keeps_official_requirement_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "task-start.py"),
                    "use standard AIDLC to update the order service",
                    "--root",
                    temp,
                    "--host",
                    "codex",
                    "--aidlc",
                    "standard",
                    "--no-planning-lock",
                    "--format",
                    "json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        report = json.loads(completed.stdout)
        self.assertNotEqual(
            report.get("type"),
            "tailtrail-host-requirement-interpretation-required",
        )

    def test_sufficient_requirement_returns_scope_route_without_material_decisions(self) -> None:
        interpreted = requirement_discovery.interpretation(
            "Create the named AWS Secrets Manager secret for OEM credentials."
        )

        self.assertEqual(interpreted["state"], "sufficient")
        self.assertEqual(interpreted["sufficiency"]["recommended_route"], "scope")
        self.assertEqual(interpreted["sufficiency"]["material_decisions"], [])
        statuses = {
            row["id"]: row["status"]
            for row in interpreted["sufficiency"]["dimensions"]
        }
        self.assertEqual(statuses["outcome-coverage"], "satisfied")
        self.assertEqual(statuses["material-decisions"], "satisfied")

    def test_host_interpretation_cannot_drop_an_explicit_outcome(self) -> None:
        goal = "Create the secret and preserve the existing rotation policy."
        proposal = {
            "schema_version": "1",
            "type": "tailtrail-host-requirement-interpretation",
            "host": "codex",
            "goal": goal,
            "private_reasoning_excluded": True,
            "clauses": [
                {"clause_id": "C-01", "role": "outcome", "text": "Create the secret"},
                {"clause_id": "C-02", "role": "constraint", "text": "preserve the existing rotation policy"},
            ],
            "requirements": [{
                "display_id": "REQ-01",
                "statement": "Create the secret.",
                "kind": "change",
                "source_clause_ids": ["C-01"],
                "intent_terms": ["create", "secret"],
            }],
            "material_questions": [],
        }

        with self.assertRaisesRegex(ValueError, "omitted explicit outcome/constraint clauses: C-02"):
            requirement_discovery.interpretation(goal, proposal, "codex")

    def test_host_interpretation_cannot_drop_named_targets(self) -> None:
        goal = (
            "Add end-to-end tests for pipeline_summary_v4, step_summary, "
            "task_summary, and pipeline_event_details."
        )
        proposal = {
            "schema_version": "1",
            "type": "tailtrail-host-requirement-interpretation",
            "host": "codex",
            "goal": goal,
            "private_reasoning_excluded": True,
            "clauses": [{"clause_id": "C-01", "role": "outcome", "text": goal}],
            "requirements": [{
                "display_id": "REQ-01",
                "statement": "Add focused end-to-end tests.",
                "kind": "change",
                "source_clause_ids": ["C-01"],
                "intent_terms": ["add", "end-to-end", "tests"],
            }],
            "material_questions": [],
        }

        with self.assertRaisesRegex(ValueError, "omitted exact named target"):
            requirement_discovery.interpretation(goal, proposal, "codex")

    def test_named_targets_may_be_covered_by_separate_requirements(self) -> None:
        targets = [
            "pipeline_summary_v4",
            "step_summary",
            "task_summary",
            "pipeline_event_details",
        ]
        goal = "Add end-to-end tests for " + ", ".join(targets) + "."
        proposal = {
            "schema_version": "1",
            "type": "tailtrail-host-requirement-interpretation",
            "host": "codex",
            "goal": goal,
            "private_reasoning_excluded": True,
            "clauses": [{"clause_id": "C-01", "role": "outcome", "text": goal}],
            "requirements": [
                {
                    "display_id": f"REQ-{index:02d}",
                    "statement": f"Add end-to-end tests for {target}.",
                    "kind": "change",
                    "source_clause_ids": ["C-01"],
                    "intent_terms": ["add", "tests", target],
                }
                for index, target in enumerate(targets, start=1)
            ],
            "material_questions": [],
        }

        interpreted = requirement_discovery.interpretation(goal, proposal, "codex")
        named_target_dimension = next(
            row
            for row in interpreted["sufficiency"]["dimensions"]
            if row["id"] == "named-target-retention"
        )
        self.assertEqual(interpreted["state"], "sufficient")
        self.assertEqual(named_target_dimension["status"], "satisfied")
        self.assertEqual(named_target_dimension["evidence_refs"], sorted(targets))

    def test_question_clause_cannot_be_silently_declared_sufficient(self) -> None:
        sufficiency = requirement_discovery.requirement_sufficiency_contract(
            [
                {"clause_id": "C-01", "role": "outcome", "text": "Add the tests."},
                {"clause_id": "C-02", "role": "question", "text": "Which environments must the tests cover?"},
            ],
            [{"display_id": "REQ-01", "statement": "Add the tests.", "source_clause_ids": ["C-01"]}],
            [],
            source="host-assisted",
        )

        self.assertEqual(sufficiency["state"], "clarification-required")
        self.assertEqual(sufficiency["material_decisions"][0]["question"], "Which environments must the tests cover?")
        self.assertEqual(
            next(row for row in sufficiency["dimensions"] if row["id"] == "material-decisions")["status"],
            "missing",
        )

    def test_clarification_is_successful_and_returns_durable_continuation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            completed = self.run_start(root, host_proposal=self.host_interpretation())
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            report = json.loads(completed.stdout)
            self.assertEqual(report["state"], "awaiting-requirements")
            self.assertTrue(report["intake_id"])
            self.assertEqual(report["continuation"]["intake_id"], report["intake_id"])
            self.assertEqual(report["continuation"]["action"], "requirements-answer")
            self.assertTrue(
                (root / ".tailtrail" / "requirement-intakes" / report["intake_id"] / "current.json").is_file()
            )
            self.assertFalse((root / ".tailtrail" / "runs").exists())
            self.assertFalse((root / "tailtrail-meta").exists())

    def _write_intake(self, root: Path, intake_id: str, goal: str, questions: list[dict], answers: dict | None = None) -> None:
        evidence_module = load("tailtrail_phase0_requirement_evidence", "scripts/requirement_evidence.py")
        directory = requirement_intake.intake_dir(root, intake_id)
        directory.mkdir(parents=True)
        (directory / "current.json").write_text(json.dumps({
            "intake_id": intake_id,
            "type": "tailtrail-requirement-intake",
            "identity": {"root": root.resolve().as_posix(), "goal": goal},
            "requirement_evidence": evidence_module.gather(root, goal, {}),
            "questions": questions,
            "answers": answers or {},
        }), encoding="utf-8")

    def test_interactive_prompt_collects_open_answers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_intake(root, "intake-0123456789abcdef", "fix the widget", [
                {"decision_id": "MAT-01", "question": "Pick one?"},
                {"decision_id": "MAT-02", "question": "Pick two?"},
            ], {"MAT-02": "already answered"})
            with mock.patch("builtins.input", side_effect=["first answer"]) as prompted:
                collected = requirement_intake.prompt_for_answers(root, "intake-0123456789abcdef")
            self.assertEqual(prompted.call_count, 1)
        self.assertEqual(collected, {"MAT-01": "first answer"})

    def test_interactive_prompt_handles_eof(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_intake(root, "intake-0123456789abcdef", "fix the widget", [
                {"decision_id": "MAT-01", "question": "Pick one?"},
            ])
            with mock.patch("builtins.input", side_effect=EOFError):
                with self.assertRaisesRegex(ValueError, "no answers provided"):
                    requirement_intake.prompt_for_answers(root, "intake-0123456789abcdef")

    def test_interactive_answer_without_tty_ends_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = self.run_start(root, host_proposal=self.host_interpretation())
            intake_id = json.loads(first.stdout)["intake_id"]
            answered = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "tailtrail.py"),
                    "requirements",
                    "answer",
                    "--root",
                    str(root),
                    "--intake-id",
                    intake_id,
                    "--interactive",
                    "--format",
                    "json",
                ],
                text=True,
                capture_output=True,
                check=False,
                stdin=subprocess.DEVNULL,
            )
        self.assertEqual(answered.returncode, 2, answered.stderr or answered.stdout)
        self.assertIn("no answers provided", answered.stderr)

    def test_requirement_intake_is_idempotent_and_answers_are_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = self.run_start(root, host_proposal=self.host_interpretation())
            second = self.run_start(root, host_proposal=self.host_interpretation())
            first_report = json.loads(first.stdout)
            second_report = json.loads(second.stdout)
            self.assertEqual(first_report["intake_id"], second_report["intake_id"])
            self.assertEqual(second_report["revision"], 1)

            decision_id = first_report["requirement_sufficiency"]["material_decisions"][0]["id"]
            answered = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "tailtrail.py"),
                    "requirements",
                    "answer",
                    "--root",
                    str(root),
                    "--intake-id",
                    first_report["intake_id"],
                    "--answers",
                    json.dumps({decision_id: "Use AWS Secrets Manager."}),
                    "--format",
                    "json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(answered.returncode, 0, answered.stderr or answered.stdout)
            artifact = json.loads(answered.stdout)
            self.assertEqual(artifact["state"], "answered")
            self.assertEqual(artifact["revision"], 2)
            self.assertEqual(artifact["continuation"]["action"], "requirements-resume")
            revisions = root / ".tailtrail" / "requirement-intakes" / artifact["intake_id"] / "revisions"
            self.assertTrue((revisions / "revision-0001.json").is_file())
            self.assertTrue((revisions / "revision-0002.json").is_file())
            self.assertFalse((root / ".tailtrail" / "runs").exists())

            shown = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "tailtrail.py"),
                    "requirements",
                    "show",
                    "--root",
                    str(root),
                    "--intake-id",
                    artifact["intake_id"],
                    "--format",
                    "json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(shown.returncode, 0, shown.stderr or shown.stdout)
            self.assertEqual(json.loads(shown.stdout)["revision"], 2)

            rejected = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "tailtrail.py"),
                    "requirements",
                    "answer",
                    "--root",
                    str(root),
                    "--intake-id",
                    artifact["intake_id"],
                    "--answers",
                    json.dumps({decision_id: "password=do-not-store-this"}),
                    "--format",
                    "json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("must not contain credentials", rejected.stderr)
            current = json.loads((revisions.parent / "current.json").read_text(encoding="utf-8"))
            self.assertEqual(current["revision"], 2)

    def test_bounded_evidence_attaches_repository_convention_without_answering(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.tf").write_text(
                'resource "aws_secretsmanager_secret" "credentials" {\n'
                '  name = "example"\n}\n',
                encoding="utf-8",
            )
            completed = self.run_start(root)

            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            report = json.loads(completed.stdout)
            evidence = report["requirement_evidence"]
            decision = evidence["decisions"][0]
            self.assertEqual(evidence["type"], "tailtrail-requirement-evidence")
            self.assertEqual(evidence["metrics"]["files_read"], 1)
            self.assertEqual(decision["state"], "supported")
            self.assertEqual(decision["recommendation"]["option"], "aws-secrets-manager")
            self.assertEqual(decision["resolution"], "ask-user")
            self.assertEqual(report["state"], "awaiting-requirements")
            self.assertNotIn("source", decision)
            self.assertFalse((root / ".tailtrail" / "runs").exists())
            self.assertFalse((root / "tailtrail-meta").exists())

    def test_agent_host_question_receives_the_same_bounded_evidence_assistance(self) -> None:
        for host in ("codex", "copilot", "claude"):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                (root / "main.tf").write_text(
                    'resource "aws_secretsmanager_secret" "credentials" {}\n',
                    encoding="utf-8",
                )

                completed = self.run_start(root, host_proposal=self.host_interpretation(host))
                report = json.loads(completed.stdout)
                decision = report["requirement_evidence"]["decisions"][0]

                self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
                self.assertEqual(decision["decision_class"], "infrastructure-resource-type")
                self.assertEqual(decision["state"], "supported")
                self.assertEqual(decision["recommendation"]["option"], "aws-secrets-manager")
                self.assertEqual(decision["resolution"], "ask-user")
                self.assertFalse((root / ".tailtrail" / "runs").exists())

    def test_conflicting_requirement_evidence_never_guesses(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.tf").write_text(
                'resource "aws_secretsmanager_secret" "one" {}\n'
                'resource "aws_ssm_parameter" "two" { type = "SecureString" }\n',
                encoding="utf-8",
            )
            completed = self.run_start(root)
            decision = json.loads(completed.stdout)["requirement_evidence"]["decisions"][0]

            self.assertEqual(decision["state"], "conflicting")
            self.assertIsNone(decision["recommendation"])
            self.assertEqual(decision["resolution"], "ask-user")

    def test_requirement_evidence_stops_at_the_file_limit_and_ignores_managed_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            managed = root / ".tailtrail"
            managed.mkdir()
            (managed / "unsupported.tf").write_text(
                'resource "aws_ssm_parameter" "managed" {}\n', encoding="utf-8"
            )
            for index in range(30):
                (root / f"resource-{index:02d}.tf").write_text(
                    'resource "aws_secretsmanager_secret" "credentials" {}\n',
                    encoding="utf-8",
                )

            completed = self.run_start(root)
            evidence = json.loads(completed.stdout)["requirement_evidence"]
            decision = evidence["decisions"][0]

            self.assertEqual(evidence["metrics"]["files_read"], 24)
            self.assertEqual(evidence["metrics"]["stopped_by_limit"], 1)
            self.assertEqual(decision["state"], "limit-reached")
            self.assertEqual(decision["recommendation"]["option"], "aws-secrets-manager")
            self.assertTrue(all(row["option"] != "ssm-parameter-store" for row in decision["findings"]))
            self.assertEqual(decision["resolution"], "ask-user")

    def test_requirement_evidence_stops_at_the_file_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for index in range(30):
                (root / f"resource-{index:02d}.tf").write_text(
                    'resource "aws_secretsmanager_secret" "value" {}\n',
                    encoding="utf-8",
                )

            completed = self.run_start(root)
            evidence = json.loads(completed.stdout)["requirement_evidence"]

            self.assertEqual(evidence["metrics"]["files_read"], 24)
            self.assertEqual(evidence["metrics"]["stopped_by_limit"], 1)
            self.assertEqual(evidence["decisions"][0]["state"], "limit-reached")
            self.assertIsNotNone(evidence["decisions"][0]["recommendation"])
            self.assertEqual(evidence["decisions"][0]["resolution"], "ask-user")

    def test_tampered_requirement_evidence_cannot_be_shown_or_answered(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            started = self.run_start(root)
            artifact = json.loads(started.stdout)
            current_path = (
                root / ".tailtrail" / "requirement-intakes" /
                artifact["intake_id"] / "current.json"
            )
            current = json.loads(current_path.read_text(encoding="utf-8"))
            current["requirement_evidence"]["decisions"][0]["resolution"] = "auto-answer"
            current_path.write_text(json.dumps(current), encoding="utf-8")

            shown = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "tailtrail.py"),
                    "requirements",
                    "show",
                    "--root",
                    str(root),
                    "--intake-id",
                    artifact["intake_id"],
                    "--format",
                    "json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(shown.returncode, 2)
            self.assertIn("fingerprint is invalid", shown.stderr)

    def test_missing_graph_does_not_replace_requirement_clarification_with_scope_question(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            completed = self.run_start(Path(temp))

        report = json.loads(completed.stdout)
        self.assertEqual(report["type"], "tailtrail-requirement-clarification")
        self.assertEqual(
            report["scope_question_precondition"]["state"], "deferred"
        )
        self.assertNotIn("TailTrail Scope Confirmation Required", completed.stdout)
        self.assertNotIn("module, symbol, caller", completed.stdout)

    def test_requirement_intake_precedes_disabled_scope_investigation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            policy_path = root / task_start.navigator_scope.SCOPE_POLICY_PATH
            policy_path.parent.mkdir(parents=True)
            policy_path.write_text(
                json.dumps(
                    task_start.navigator_scope.seal_scope_policy(
                        task_start.navigator_scope.SCOPE_UNAVAILABLE,
                        "phase-seven-precedence-proof",
                    )
                ) + "\n",
                encoding="utf-8",
            )
            completed = self.run_start(
                root, host_proposal=self.host_interpretation()
            )
            report = json.loads(completed.stdout)
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual("tailtrail-requirement-clarification", report["type"])
            self.assertEqual("deferred", report["scope_question_precondition"]["state"])
            self.assertNotIn("scope_investigation_boundary", report)
            self.assertFalse((root / "tailtrail-meta").exists())

    def test_scope_boundary_suppresses_question_without_sufficiency_proof(self) -> None:
        boundary = task_start.scope_quality_boundary_report(
            {
                "goal": "create a resource",
                "root": "/tmp/project",
                "navigator": {
                    "requirement_interpretation": {
                        "state": "clarification-required",
                        "sufficiency": {
                            "state": "clarification-required",
                            "material_decisions": [{"id": "MAT-01"}],
                        },
                    },
                    "scope_quality": {
                        "blocking": True,
                        "question": {
                            "question_id": "SCOPE-Q1",
                            "question": "Which file owns this behavior?",
                        },
                    },
                },
            }
        )

        self.assertEqual("deferred", boundary["scope_question_precondition"]["state"])
        self.assertIsNone(boundary["scope_quality"]["question"])
        rendered = task_start.render_scope_quality_boundary_report(boundary)
        self.assertIn("Requirement intake first", rendered)
        self.assertNotIn("One bounded scope question", rendered)

    def test_unanswered_intake_cannot_resume_or_start_scope_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            started = self.run_start(root)
            intake = json.loads(started.stdout)
            resumed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "task-start.py"),
                    self.fixture["goal"],
                    "--root",
                    root.as_posix(),
                    "--requirement-intake-id",
                    intake["intake_id"],
                    "--aidlc",
                    "lite",
                    "--format",
                    "json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(resumed.returncode, 2)
            self.assertIn("must be fully answered", resumed.stderr)
            self.assertFalse((root / ".tailtrail" / "runs").exists())
            self.assertFalse((root / "tailtrail-meta").exists())

    def test_answered_intake_cannot_change_its_saved_aidlc_route(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            started = self.run_start(root)
            intake = json.loads(started.stdout)
            requirement_intake.answer(
                root,
                intake["intake_id"],
                {"MAT-01": "Use AWS Secrets Manager."},
                command_prefix="tailtrail",
            )
            resumed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "task-start.py"),
                    self.fixture["goal"],
                    "--root",
                    root.as_posix(),
                    "--requirement-intake-id",
                    intake["intake_id"],
                    "--aidlc",
                    "standard",
                    "--format",
                    "json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(resumed.returncode, 2)
            self.assertIn("without downgrade or escalation", resumed.stderr)
            self.assertFalse((root / ".tailtrail" / "runs").exists())

    def _write_conversation_intake(self, root: Path, intake_id: str, goal: str, revision: int = 1) -> None:
        evidence_module = load("tailtrail_phase0_conversation_evidence", "scripts/requirement_evidence.py")
        evidence = evidence_module.gather(root, goal, {"material_decisions": [
            {"id": "MAT-01", "decision_class": "material-requirement-decision", "question": "Which cache?"},
        ]})
        for row in evidence.get("decisions", []):
            if isinstance(row, dict) and row.get("decision_id") == "MAT-01":
                row["recommendation"] = {"option": "Use memory cache", "confidence": "medium"}
        unsigned = {key: value for key, value in evidence.items() if key != "fingerprint"}
        evidence["fingerprint"] = evidence_module.fingerprint(unsigned)
        directory = requirement_intake.intake_dir(root, intake_id)
        directory.mkdir(parents=True)
        (directory / "current.json").write_text(json.dumps({
            "intake_id": intake_id,
            "type": "tailtrail-requirement-intake",
            "revision": revision,
            "state": "awaiting-requirements",
            "identity": {"root": root.resolve().as_posix(), "goal": goal, "route": "lite-questions", "host": "none"},
            "requirement_evidence": evidence,
            "questions": [{"decision_id": "MAT-01", "decision_class": "material-requirement-decision",
                           "question": "Which cache?", "impact": ["acceptance-criteria"],
                           "evidence_refs": ["host-interpretation"]}],
            "answers": {},
            "continuation": {"action": "requirements-answer", "intake_id": intake_id,
                             "prompt": "Answer the material questions.",
                             "boundary": "Answers update only this pre-lock intake."},
            "boundary": "Durable requirement intake only.",
        }), encoding="utf-8")

    def test_skip_records_advisory_default_and_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_conversation_intake(root, "intake-0123456789abcdef", "fix the widget")
            updated = requirement_intake.answer(root, "intake-0123456789abcdef", {"MAT-01": "skip"}, command_prefix="tailtrail")
            noted = requirement_intake.answer(root, "intake-0123456789abcdef", {"MAT-01": "skip: prefer disk"}, command_prefix="tailtrail")
        self.assertEqual(updated["state"], "answered")
        self.assertIn("Use memory cache", updated["answers"]["MAT-01"])
        self.assertTrue(updated["answers"]["MAT-01"].startswith("skip:"))
        self.assertIn("prefer disk", noted["answers"]["MAT-01"])

    def test_skip_without_recommendation_defers_to_plan_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_conversation_intake(root, "intake-0123456789abcdef", "fix the widget")
            directory = requirement_intake.intake_dir(root, "intake-0123456789abcdef")
            payload = json.loads((directory / "current.json").read_text(encoding="utf-8"))
            evidence_module = load("tailtrail_phase0_conversation_evidence", "scripts/requirement_evidence.py")
            for row in payload["requirement_evidence"].get("decisions", []):
                if isinstance(row, dict):
                    row["recommendation"] = None
            unsigned = {key: value for key, value in payload["requirement_evidence"].items() if key != "fingerprint"}
            payload["requirement_evidence"]["fingerprint"] = evidence_module.fingerprint(unsigned)
            (directory / "current.json").write_text(json.dumps(payload), encoding="utf-8")
            updated = requirement_intake.answer(root, "intake-0123456789abcdef", {"MAT-01": "SKIP"}, command_prefix="tailtrail")
        self.assertIn("host-decision-deferred-to-plan-approval", updated["answers"]["MAT-01"])

    def test_revision_cap_fails_closed_with_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_conversation_intake(root, "intake-0123456789abcdef", "fix the widget",
                                            revision=requirement_intake.INTAKE_MAX_REVISIONS)
            with self.assertRaisesRegex(ValueError, "exceeded.*answer rounds") as raised:
                requirement_intake.answer(root, "intake-0123456789abcdef", {"MAT-01": "Use memory cache"}, command_prefix="tailtrail")
        self.assertIn("intake-0123456789abcdef", str(raised.exception))

    def test_render_ships_reply_channel_why_and_skip_per_question(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_conversation_intake(root, "intake-0123456789abcdef", "fix the widget")
            artifact = requirement_intake.load(root, "intake-0123456789abcdef")
            rendered = requirement_intake.render(artifact, "tailtrail")
        self.assertIn("intake-0123456789abcdef", rendered)
        self.assertIn("Why it matters: acceptance-criteria", rendered)
        self.assertIn("requirements answer --root . --intake-id intake-0123456789abcdef", rendered)
        self.assertIn('"skip"', rendered)
        self.assertIn("Use memory cache", rendered)
        self.assertIn(f"capped at {requirement_intake.INTAKE_MAX_REVISIONS}", rendered)

    def test_prompt_passes_explicit_skip_through_for_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_conversation_intake(root, "intake-0123456789abcdef", "fix the widget")
            with mock.patch("builtins.input", side_effect=["skip"]):
                collected = requirement_intake.prompt_for_answers(root, "intake-0123456789abcdef")
            updated = requirement_intake.answer(root, "intake-0123456789abcdef", collected, command_prefix="tailtrail")
        self.assertEqual(collected, {"MAT-01": "skip"})
        self.assertEqual(updated["state"], "answered")
        self.assertTrue(updated["answers"]["MAT-01"].startswith("skip:"))

    def test_clarification_report_renders_continuation_command(self) -> None:
        command = "tailtrail requirements answer --root . --intake-id intake-0123456789abcdef --answers '{\"?\": \"?\"}'"
        rendered = task_start.render_requirement_clarification_report({
            "type": "tailtrail-requirement-clarification",
            "boundary": "No graph lifecycle or Planning Lock was created.",
            "intake_id": "intake-0123456789abcdef",
            "recommended_route": "lite-questions",
            "material_questions": ["Which cache?"],
            "requirement_evidence": {},
            "continuation": {"prompt": "Answer the material question.", "command": command},
        })
        self.assertIn(command, rendered)
        self.assertIn("Which cache?", rendered)
        without_command = task_start.render_requirement_clarification_report({
            "type": "tailtrail-requirement-clarification",
            "boundary": "No graph lifecycle or Planning Lock was created.",
            "intake_id": "intake-0123456789abcdef",
            "recommended_route": "lite-questions",
            "material_questions": ["Which cache?"],
            "requirement_evidence": {},
            "continuation": {"prompt": "Answer the material question."},
        })
        self.assertIn("Answer the material question.", without_command)


if __name__ == "__main__":
    unittest.main()
