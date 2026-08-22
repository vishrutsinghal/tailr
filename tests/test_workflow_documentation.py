from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "DURABLE-WORKFLOW-RUNTIME-REVISED.md"
ROADMAP = ROOT / "ROADMAP.md"
COMMANDS = ROOT / "TAILTRAIL-COMMANDS.md"
REGISTRY = ROOT / "tailtrail-registry.json"
CLI = ROOT / "scripts" / "tailtrail.py"


WORKFLOW_COMMAND_PATHS = (
    ("bind",),
    ("show",),
    ("validate",),
    ("capabilities", "propose"),
    ("capabilities", "show"),
    ("capabilities", "validate"),
    ("capabilities", "preapprove"),
    ("capabilities", "preapproval-show"),
    ("capabilities", "preapproval-validate"),
    ("task", "scope-init"),
    ("task", "scope-show"),
    ("task", "freshness"),
    ("task", "acquire"),
    ("task", "lock-show"),
    ("task", "diagnose"),
    ("storage", "init"),
    ("storage", "capture"),
    ("storage", "status"),
    ("storage", "replay"),
    ("storage", "validate"),
    ("state", "create"),
    ("state", "list"),
    ("state", "show"),
    ("state", "status"),
    ("state", "pause"),
    ("state", "resume"),
    ("state", "cancel"),
    ("state", "replay"),
    ("state", "events"),
    ("state", "doctor"),
    ("state", "transition"),
    ("state", "stage"),
    ("state", "follow-up"),
    ("state", "supersede"),
    ("compile", "plan"),
    ("compile", "show"),
    ("compile", "validate"),
    ("approvals", "show"),
    ("approvals", "session"),
    ("approvals", "session-end"),
    ("approvals", "decide"),
    ("approvals", "skip"),
    ("approvals", "validate"),
    ("evidence", "collect"),
    ("evidence", "show"),
    ("evidence", "refresh"),
    ("evidence", "resume"),
    ("evidence", "correction"),
    ("evidence", "close"),
    ("evidence", "validate"),
    ("vertical", "status"),
    ("vertical", "finalize"),
    ("adapters", "list"),
    ("adapters", "contract"),
    ("adapters", "prepare"),
    ("adapters", "record"),
    ("adapters", "show"),
    ("adapters", "validate"),
    ("execute", "status"),
    ("execute", "start"),
    ("execute", "finish"),
    ("execute", "skip"),
    ("freshness", "show"),
    ("freshness", "capture"),
    ("freshness", "assess"),
    ("freshness", "apply"),
    ("retry", "show"),
    ("retry", "decide"),
    ("retry", "prepare"),
    ("retry", "record"),
    ("resume",),
    ("correction", "show"),
    ("correction", "route"),
    ("context", "record"),
    ("context", "telemetry"),
    ("context", "resume-summary"),
    ("outcomes", "learning"),
    ("outcomes", "emit"),
    ("outcomes", "validate"),
    ("ci", "show"),
    ("ci", "ingest"),
    ("assurance", "inspect"),
    ("assurance", "governance"),
    ("assurance", "denials"),
    ("retention", "show"),
    ("retention", "plan"),
    ("retention", "cleanup"),
    ("release", "catalog"),
    ("release", "show"),
    ("release", "compatibility"),
    ("release", "evaluate"),
    ("release", "scenario-record"),
    ("release", "real-run-record"),
    ("release", "retire"),
    ("enterprise", "policy-record"),
    ("enterprise", "entry"),
    ("enterprise", "activate"),
    ("enterprise", "show"),
    ("enterprise", "link"),
    ("enterprise", "lease-acquire"),
    ("enterprise", "lease-release"),
    ("enterprise", "ingest"),
    ("enterprise", "replay"),
    ("enterprise", "observe"),
    ("enterprise", "backup"),
    ("enterprise", "restore-validate"),
    ("enterprise", "migration-plan"),
    ("enterprise", "migrate"),
    ("enterprise", "rollback"),
    ("enterprise", "conformance"),
)

IMPLEMENTED_PHASES = {
    "durable-workflow-ownership-dwr-a",
    "durable-workflow-capability-bridge-dwr-b",
    "durable-workflow-task-scope-dwr-c",
    "durable-workflow-storage-dwr-minus",
    "durable-workflow-state-engine-dwr-1",
    "durable-workflow-compiler-dwr-1-5",
    "durable-workflow-start-integration-dwr-2",
    "durable-workflow-evidence-closure-dwr-3",
    "durable-workflow-proven-vertical-dwr-4",
    "durable-workflow-documentation-phase-0",
    "durable-workflow-contract-dwr-0",
    "durable-workflow-deferred-phase-2",
    "durable-workflow-deferred-phase-3",
    "durable-workflow-deferred-phase-4",
    "durable-workflow-deferred-phase-5",
    "durable-workflow-deferred-phase-6",
    "durable-workflow-deferred-phase-7",
    "durable-workflow-deferred-phase-8",
    "durable-workflow-deferred-phase-9",
    "durable-workflow-deferred-phase-10",
    "durable-workflow-deferred-phase-11",
    "durable-workflow-deferred-phase-12",
}

PLANNED_PHASES = set()


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WorkflowDocumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.design = DESIGN.read_text(encoding="utf-8")
        cls.roadmap = ROADMAP.read_text(encoding="utf-8")
        cls.commands = COMMANDS.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.features = {item["id"]: item for item in cls.registry["features"]}

    def test_documented_workflow_commands_are_real_dispatch_paths(self) -> None:
        registry_commands = {
            command
            for feature in self.registry["features"]
            for command in feature.get("commands", [])
        }
        for path in WORKFLOW_COMMAND_PATHS:
            command = "tailtrail workflow " + " ".join(path)
            documented = "python3 scripts/tailtrail.py " + command.removeprefix("tailtrail ")
            with self.subTest(command=command):
                self.assertIn(documented, self.commands)
                self.assertIn(command, registry_commands)
                result = subprocess.run(
                    [sys.executable, CLI.as_posix(), "workflow", *path, "--help"],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_storage_and_cli_sections_use_implemented_contract(self) -> None:
        storage = self.design.split("## Data Storage", 1)[1].split("## Resume And Freshness", 1)[0]
        cli = self.design.split("## CLI Design", 1)[1].split("## Suggested Python Module Layout", 1)[0]
        dwr_minus = self.design.split("### DWR-minus: Storage Proof", 1)[1].split("### DWR-0:", 1)[0]
        for required in (
            "ownership-v1.json",
            "journal-v1.jsonl",
            "projection-v1.json",
            "completion-receipt-v1.json",
        ):
            self.assertIn(required, storage)
        self.assertNotIn("workflow.json", storage)
        self.assertNotIn("events.jsonl", storage)
        self.assertNotIn("workflow events", cli)
        self.assertNotIn("events.jsonl", dwr_minus)

    def test_template_inventory_matches_compiler_and_deferred_boundary(self) -> None:
        templates = load_module(ROOT / "scripts" / "workflow_runtime" / "templates.py", "workflow_doc_templates")
        expected = {
            "small-change",
            "delivery",
            "risk-sensitive",
            "review-only",
            "ci-scanner-remediation",
            "repository-discovery",
        }
        self.assertEqual(set(templates.TEMPLATES), expected)
        for template in expected:
            self.assertIn(f"`{template}`", self.design)
        self.assertIn("`ci-scanner-remediation` | compiled and executable", self.design)

    def test_aidlc_clarification_uses_registered_authority(self) -> None:
        clarification = self.design.split("**`clarify` stage definition**", 1)[1].split("### Risk-Sensitive", 1)[0]
        self.assertIn("Capability ID: `aidlc`", clarification)
        self.assertNotIn("Capability ID: `aidlc-requirements`", self.design)
        for mode in ("Off", "Lite", "Standard", "Full"):
            self.assertIn(f"| {mode} |", clarification)
        self.assertIn("aidlc", self.features)

    def test_phase_status_tables_match_registry(self) -> None:
        for feature_id in IMPLEMENTED_PHASES:
            with self.subTest(feature_id=feature_id):
                self.assertEqual(self.features[feature_id]["status"], "implemented")
                self.assertIn(f"`{feature_id}`", self.design)
        for feature_id in PLANNED_PHASES:
            with self.subTest(feature_id=feature_id):
                self.assertEqual(self.features[feature_id]["status"], "planned")
                self.assertIn(f"`{feature_id}`", self.design)
        self.assertIn("### Durable Workflow Runtime phase status", self.roadmap)
        self.assertIn("DWR-0 | implemented", self.roadmap)
        self.assertIn("Deferred Phase 0 | implemented", self.roadmap)

    def test_design_has_one_test_strategy_and_phase_zero_is_complete(self) -> None:
        self.assertEqual(self.design.count("## Test Strategy"), 1)
        self.assertIn(
            "### Deferred Phase 0 — Documentation And Contract Reconciliation *(implemented)*",
            self.design,
        )
        self.assertIn("tests/test_workflow_documentation.py", self.design)


if __name__ == "__main__":
    unittest.main()
