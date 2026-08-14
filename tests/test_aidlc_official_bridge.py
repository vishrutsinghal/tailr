import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bridge = load("official_aidlc_bridge_test", "scripts/aidlc-official-bridge.py")
ledger = load("official_aidlc_bridge_ledger_test", "scripts/run-ledger.py")
lock = load("official_aidlc_planning_lock_test", "scripts/planning-lock.py")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compatible_pack(root: Path) -> None:
    pack = root / ".tailtrail" / "official-aidlc"
    pack.mkdir(parents=True)
    (pack / "LICENSE").write_text("MIT-0\n", encoding="utf-8")
    (pack / "core-workflow.md").write_text("# workflow\n", encoding="utf-8")
    official_rules = {
        "aws-aidlc-rules/core-workflow.md": "# Requirements Analysis\n",
        "aws-aidlc-rule-details/inception/requirements-analysis.md": "# Generate Clarifying Questions\n",
        "aws-aidlc-rule-details/common/question-format-guide.md": "# Other\n",
        "aws-aidlc-rule-details/common/content-validation.md": "# Content Validation\n",
        "aws-aidlc-rule-details/common/session-continuity.md": "# Session\n",
    }
    for relative, content in official_rules.items():
        path = pack / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    manifest = {
        "schema_version": "1", "type": "tailtrail-official-aidlc-pack",
        "official": {"source": "https://github.com/awslabs/aidlc-workflows", "revision": "v2.0.0", "license": {"spdx": "MIT-0", "file": "LICENSE"}},
        "host_adapter": {"host": "codex", "rules_path": "core-workflow.md"},
        "integrity": {
            "algorithm": "sha256",
            "files": [
                {"path": "LICENSE", "sha256": digest(pack / "LICENSE")},
                {"path": "core-workflow.md", "sha256": digest(pack / "core-workflow.md")},
            ] + [{"path": relative, "sha256": digest(pack / relative)} for relative in official_rules],
        },
    }
    (pack / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


class OfficialAidlcBridgeTests(unittest.TestCase):
    def test_lite_and_off_do_not_require_an_official_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(bridge.preflight(root, "lite")["state"], "local-lite")
            self.assertEqual(bridge.preflight(root, "standard")["state"], "local-standard")
            self.assertEqual(bridge.preflight(root, "medium")["mode"], "standard")
            self.assertEqual(bridge.preflight(root, "off")["state"], "disabled")

    def test_start_intent_routes_default_using_aidlc_and_hands_free_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            default = subprocess.run([sys.executable, (ROOT / "scripts" / "task-start.py").as_posix(), "fix one local validation", "--root", root.as_posix(), "--no-planning-lock", "--format", "json"], cwd=ROOT, text=True, capture_output=True, check=False)
            requested = subprocess.run([sys.executable, (ROOT / "scripts" / "task-start.py").as_posix(), "using AIDLC: add a service feature", "--root", root.as_posix(), "--no-planning-lock", "--format", "json"], cwd=ROOT, text=True, capture_output=True, check=False)
            hands_free = subprocess.run([sys.executable, (ROOT / "scripts" / "task-start.py").as_posix(), "hands-free: add an API and rollout plan", "--root", root.as_posix(), "--no-planning-lock", "--format", "json"], cwd=ROOT, text=True, capture_output=True, check=False)
            compatible_pack(root)
            escalated = subprocess.run([sys.executable, (ROOT / "scripts" / "task-start.py").as_posix(), "hands-free: regulated multi-team Terraform rollout", "--root", root.as_posix(), "--no-planning-lock", "--format", "json"], cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertEqual(requested.returncode, 0, requested.stderr)
        self.assertEqual(hands_free.returncode, 0, hands_free.stderr)
        self.assertEqual(escalated.returncode, 0, escalated.stderr)
        self.assertEqual(json.loads(default.stdout)["aidlc_mode"]["mode"], "lite")
        self.assertEqual(json.loads(requested.stdout)["aidlc_mode"]["mode"], "standard")
        self.assertEqual(json.loads(hands_free.stdout)["aidlc_mode"]["mode"], "standard")
        self.assertEqual(json.loads(escalated.stdout)["aidlc_mode"]["mode"], "full")
        self.assertIn("Local AIDLC Requirements stage", json.loads(requested.stdout)["aidlc_mode_features"]["included"][3])
        self.assertIn("Arbitrary official-pack script execution", json.loads(escalated.stdout)["aidlc_mode_features"]["not_included"][0])

    def test_standard_aidlc_word_order_and_medium_synonym_select_standard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            goals = ["using standard AIDLC: add a page", "AIDLC standard: add a page", "use medium AIDLC: add a page"]
            reports = [
                subprocess.run([sys.executable, (ROOT / "scripts" / "task-start.py").as_posix(), goal, "--root", root.as_posix(), "--no-planning-lock", "--format", "json"], cwd=ROOT, text=True, capture_output=True, check=False)
                for goal in goals
            ]
        self.assertTrue(all(report.returncode == 0 for report in reports))
        self.assertTrue(all(json.loads(report.stdout)["aidlc_mode"]["mode"] == "standard" for report in reports))

    def test_full_requires_a_compatible_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "compatible pinned official pack"):
                bridge.preflight(Path(tmp), "full")

    def test_full_bridge_maps_official_identity_to_one_run_and_activates_append_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            compatible_pack(root)
            ledger.init_run(root, "run-full", "ship feature")
            created = bridge.create(root, "run-full", "ship feature", official_intent_id="intent-42", official_session_id="session-7", official_stage="design")
            activation = bridge.activate(root, "run-full")
            events = ledger.projection(root, "run-full")["activity"]
        self.assertEqual(created["state"], "planned-attachment")
        self.assertEqual(created["official_intent_id"], "intent-42")
        self.assertEqual(created["official_session_id"], "session-7")
        self.assertEqual(activation["state"], "approved-awaiting-host-attachment")
        self.assertEqual(events["official_aidlc_bridge_created"], 1)
        self.assertEqual(events["official_aidlc_bridge_activated"], 1)

    def test_full_start_uses_official_requirements_before_freezing_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            compatible_pack(root)
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "task-start.py").as_posix(), "add workflow", "--root", root.as_posix(), "--aidlc", "full", "--official-intent-id", "intent-1", "--format", "json"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            report = json.loads(result.stdout)
            run_id = report["planning_lock"]["run_id"]
            with self.assertRaisesRegex(ValueError, "Full AIDLC requires answers"):
                lock.activate(root, run_id, True)
            answers = json.dumps([{"question_id": item["id"], "choice": "A"} for item in report["aidlc_requirements"]["questions"]])
            revision = lock.submit_aidlc_answers(root, run_id, answers)
            activated = lock.approve_aidlc_requirements(root, run_id, True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["aidlc_mode"]["mode"], "full")
        self.assertEqual(report["official_aidlc_bridge"]["official_intent_id"], "intent-1")
        self.assertEqual(report["official_aidlc_bridge"]["state"], "planned-attachment")
        self.assertEqual(report["aidlc_requirements"]["authority"], "official-ai-dlc-pack")
        self.assertEqual(revision["state"], "official-aidlc-revision-ready")
        self.assertTrue(activated["planning_lock"]["writes_allowed"])
        self.assertIn("aidlc-official/requirements/approval-v1.json", activated["official_stage_approval"])
        self.assertIn("anchors/approved-v1.json", activated["anchor"])

    def test_full_hands_free_start_accepts_a_multiline_goal_in_the_official_stage(self):
        goal = """hands-free: add an order-amendment capability end to end.

Before fulfilment starts, a customer may change quantity and delivery address.
After shipment starts, product and quantity changes are forbidden, but an
operations user may correct a delivery address with an audit reason.

Include payment reconciliation, API contract, tests, CI evidence, migration
compatibility, and rollout/rollback planning. Preserve cancellation behavior."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            compatible_pack(root)
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "task-start.py").as_posix(), goal, "--root", root.as_posix(), "--format", "json"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["aidlc_mode"]["mode"], "full")
        self.assertEqual(report["goal"], goal)
        self.assertNotIn("\n", report["aidlc_requirements"]["aidlc_stage"]["goal"])
        self.assertIn("order-amendment capability", report["aidlc_requirements"]["aidlc_stage"]["goal"])

    def test_full_mode_rejection_routes_to_official_design_not_local_questions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            compatible_pack(root)
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "task-start.py").as_posix(), "add a service", "--root", root.as_posix(), "--aidlc", "full", "--format", "json"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            report = json.loads(result.stdout)
            run_id = report["planning_lock"]["run_id"]
            template = lock.feedback_template(root, run_id)
            feedback = json.dumps([{"requirement_uid": row["requirement_uid"], "decision": "reject", "comment": "The architecture design boundary is not clear."} for row in template["requirements"]])
            routed = lock.record_feedback(root, run_id, feedback)
            local_artifact = root / ".tailtrail" / "runs" / run_id / "planning" / "aidlc-requirements-v1.json"
            self.assertFalse(local_artifact.exists())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(routed["state"], "official-aidlc-refinement-required")
        self.assertEqual(routed["official_revision_route"], "official-design")
