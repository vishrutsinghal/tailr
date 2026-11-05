import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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
lock = load("official_aidlc_planning_lock_test", "scripts/planning_lock.py")
official_requirements = load("official_aidlc_requirements_test", "scripts/official-aidlc-requirements.py")


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


def requirements_rule_pack(pack: Path) -> dict[str, Path]:
    rules = {
        "core_workflow": pack / "aws-aidlc-rules" / "core-workflow.md",
        "requirements_analysis": pack / "aws-aidlc-rule-details" / "inception" / "requirements-analysis.md",
        "question_format": pack / "aws-aidlc-rule-details" / "common" / "question-format-guide.md",
        "content_validation": pack / "aws-aidlc-rule-details" / "common" / "content-validation.md",
        "session_continuity": pack / "aws-aidlc-rule-details" / "common" / "session-continuity.md",
    }
    contents = {
        "core_workflow": "# Requirements Analysis\n",
        "requirements_analysis": "# Generate Clarifying Questions\n",
        "question_format": "# Other\n",
        "content_validation": "# Content Validation\n",
        "session_continuity": "# Session\n",
    }
    for name, path in rules.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents[name], encoding="utf-8")
    return rules


def host_questions() -> list[dict[str, object]]:
    return [{
        "id": "OQ1",
        "question": "Which observable API outcome is required?",
        "options": [
            {"id": "A", "text": "Service behavior only"},
            {"id": "B", "text": "Service and API behavior"},
            {"id": "Other", "text": "Other (describe)"},
        ],
        "recommended": "Service and API behavior",
        "reasoning": "The stated delivery includes an API and audit evidence, so the caller contract is part of the boundary.",
        "requirement_ids": ["REQ-01"],
        "decision_class": "architecture-decision",
        "decision_impact": ["architecture", "public-contract"],
        "known_context": ["The requested delivery includes service and API behavior."],
        "evidence_refs": ["user-requirement:REQ-01"],
    }]


def start_command(root: Path, goal: str, *extra: str) -> list[str]:
    """Give routing tests a real, explicit implementation owner.

    NS-4 deliberately refuses to create even an AIDLC Planning Lock from an
    empty repository.  These tests exercise AIDLC routing, so their fixture
    supplies typed scope evidence instead of relying on the removed
    explicit-root bypass.
    """
    owner = root / "src" / "service.py"
    owner.parent.mkdir(parents=True, exist_ok=True)
    owner.write_text("def service():\n    return None\n", encoding="utf-8")
    return [
        sys.executable,
        (ROOT / "scripts" / "task-start.py").as_posix(),
        goal,
        "--root",
        root.as_posix(),
        "--changed",
        "src/service.py",
        *extra,
    ]


def bundled_bridge_preflight(root: Path, *, host: str = "codex") -> dict[str, object]:
    """Build one sealed Phase 3A result without resolving mutable project state."""
    fingerprint = "sha256:" + "1" * 64
    pack_fingerprint = "sha256:" + "2" * 64
    projection_fingerprint = "sha256:" + "3" * 64
    pack_path = f".tailtrail/official-aidlc/packs/{pack_fingerprint[7:]}"
    pack = root / pack_path
    rules = pack / "aws-aidlc-rules" / "core-workflow.md"
    rules.parent.mkdir(parents=True, exist_ok=True)
    rules.write_text("# Bundled Full workflow\n", encoding="utf-8")
    (pack / "manifest.json").write_text(
        json.dumps({"schema_version": "2", "pack_fingerprint": pack_fingerprint}),
        encoding="utf-8",
    )
    projection = {
        "state": "ready",
        "network_used": False,
        "source_resolution_fingerprint": fingerprint,
        "projection_fingerprint": projection_fingerprint,
        "pack_fingerprint": pack_fingerprint,
        "pack_path": pack_path,
        "trust_posture": "release-authenticated",
        "issues": [],
    }
    projection["receipt_fingerprint"] = bridge._fingerprint(projection)
    preflight = {
        "mode": "full",
        "requested_mode": "full",
        "effective_mode": "full",
        "state": "official-full-ready",
        "network_used": False,
        "resolution_receipt_fingerprint": fingerprint,
        "source_resolution_fingerprint": fingerprint,
        "project_projection_fingerprint": projection_fingerprint,
        "pack_fingerprint": pack_fingerprint,
        "pack_path": pack_path,
        "trust_posture": "release-authenticated",
        "host": host,
        "official_source": "https://github.com/awslabs/aidlc-workflows",
        "official_revision": "v1.0.1",
        "official_commit": "a" * 40,
        "project_projection": projection,
        "issues": [],
        "boundary": "Bundled Full rules are resolved and projected offline.",
    }
    preflight["preflight_fingerprint"] = bridge._fingerprint(preflight)
    return preflight


class OfficialAidlcBridgeTests(unittest.TestCase):
    def test_bundled_full_bridge_identity_is_immutable_idempotent_and_does_not_reresolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            ledger.init_run(root, "run-bundled", "ship bundled Full")
            preflight = bundled_bridge_preflight(root)
            with mock.patch.object(bridge.aidlc_bundle, "resolve") as resolve, mock.patch.object(
                bridge.aidlc_bundle, "provision"
            ) as provision:
                created = bridge.create_bundled(
                    root,
                    "run-bundled",
                    "ship bundled Full",
                    preflight,
                    official_intent_id="intent-bundled",
                    official_session_id="session-bundled",
                )
                repeated = bridge.create_bundled(
                    root,
                    "run-bundled",
                    "ship bundled Full",
                    preflight,
                    official_intent_id="intent-bundled",
                    official_session_id="session-bundled",
                )
            events = ledger.projection(root, "run-bundled")["activity"]

        resolve.assert_not_called()
        provision.assert_not_called()
        self.assertEqual(created["status"], "created")
        self.assertEqual(repeated["status"], "existing")
        self.assertEqual(created["schema_version"], "2")
        self.assertEqual(created["compatibility_mode"], "bundled-v2")
        self.assertEqual(created["resolution_receipt_fingerprint"], preflight["resolution_receipt_fingerprint"])
        self.assertEqual(created["project_projection_fingerprint"], preflight["project_projection_fingerprint"])
        self.assertEqual(created["pack_fingerprint"], preflight["pack_fingerprint"])
        self.assertEqual(created["pack_path"], preflight["pack_path"])
        self.assertEqual(events["official_aidlc_bridge_created"], 1)

    def test_bundled_full_bridge_identity_rejects_unsafe_inconsistent_or_conflicting_input(self):
        invalid_mutations = {
            "not-ready": lambda value: value.update({"state": "official-full-unavailable"}),
            "network-used": lambda value: value.update({"network_used": True}),
            "resolution-mismatch": lambda value: value.update({"source_resolution_fingerprint": "sha256:" + "9" * 64}),
            "projection-mismatch": lambda value: value.update({"project_projection_fingerprint": "sha256:" + "8" * 64}),
        }
        for name, mutate in invalid_mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                ledger.init_run(root, "run-bundled", "ship bundled Full")
                preflight = bundled_bridge_preflight(root)
                mutate(preflight)
                preflight["preflight_fingerprint"] = bridge._fingerprint({
                    key: value for key, value in preflight.items() if key != "preflight_fingerprint"
                })
                with self.assertRaisesRegex(ValueError, "ready offline resolution-to-project identity"):
                    bridge.create_bundled(root, "run-bundled", "ship bundled Full", preflight)
                self.assertFalse((root / ".tailtrail" / "runs" / "run-bundled" / "aidlc-official" / "bridge-v1.json").exists())

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            ledger.init_run(root, "run-bundled", "ship bundled Full")
            preflight = bundled_bridge_preflight(root)
            preflight["official_revision"] = "tampered"
            with self.assertRaisesRegex(ValueError, "intact sealed"):
                bridge.create_bundled(root, "run-bundled", "ship bundled Full", preflight)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            ledger.init_run(root, "run-bundled", "ship bundled Full")
            preflight = bundled_bridge_preflight(root)
            created = bridge.create_bundled(
                root, "run-bundled", "ship bundled Full", preflight,
                official_intent_id="intent-one",
            )
            saved = (root / created["artifact"]).read_bytes()
            with self.assertRaisesRegex(ValueError, "different immutable content"):
                bridge.create_bundled(
                    root, "run-bundled", "ship bundled Full", preflight,
                    official_intent_id="intent-two",
                )
            self.assertEqual((root / created["artifact"]).read_bytes(), saved)

    def test_bundled_full_preflight_projects_one_ready_resolution_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            resolution = {
                "state": "ready",
                "requested_mode": "full",
                "effective_mode": "full",
                "network_used": False,
                "receipt_fingerprint": "sha256:resolution",
                "issues": [],
            }
            projection = {
                "state": "ready",
                "network_used": False,
                "source_resolution_fingerprint": "sha256:resolution",
                "pack_fingerprint": "sha256:pack",
                "pack_path": ".tailtrail/official-aidlc/packs/pack",
                "issues": [],
            }
            with mock.patch.object(bridge.aidlc_bundle, "resolve", return_value=resolution) as resolve, mock.patch.object(
                bridge.aidlc_bundle, "provision", return_value=projection
            ) as provision:
                result = bridge.bundled_full_preflight(root, "codex", environment={})

        self.assertEqual(result["state"], "official-full-ready")
        self.assertEqual(result["requested_mode"], "full")
        self.assertEqual(result["effective_mode"], "full")
        self.assertFalse(result["network_used"])
        self.assertEqual(result["resolution_receipt_fingerprint"], "sha256:resolution")
        self.assertEqual(result["source_resolution_fingerprint"], "sha256:resolution")
        self.assertEqual(result["project_projection"], projection)
        resolver_inputs = resolve.call_args.args[0]
        self.assertEqual(resolver_inputs.requested_mode, "full")
        self.assertEqual(resolver_inputs.host, "codex")
        projection_inputs = provision.call_args.args[0]
        self.assertIs(projection_inputs.resolution_receipt, resolution)
        self.assertEqual(projection_inputs.target_root, root)

    def test_bundled_full_preflight_stops_before_projection_when_resolution_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            blocked = {
                "state": "blocked",
                "requested_mode": "full",
                "effective_mode": None,
                "network_used": False,
                "receipt_fingerprint": "sha256:blocked",
                "issues": [{"category": "provider-unavailable", "detail": "bundle missing"}],
            }
            with mock.patch.object(bridge.aidlc_bundle, "resolve", return_value=blocked), mock.patch.object(
                bridge.aidlc_bundle, "provision"
            ) as provision:
                result = bridge.bundled_full_preflight(Path(tmp), "copilot")

        provision.assert_not_called()
        self.assertEqual(result["mode"], "full")
        self.assertEqual(result["effective_mode"], "unavailable")
        self.assertEqual(result["state"], "official-full-unavailable")
        self.assertEqual(result["issues"][0]["category"], "provider-unavailable")
        self.assertIn("retry Full preflight", result["issues"][0]["action"])
        self.assertNotEqual(result.get("mode"), "lite")

    def test_bundled_full_preflight_rejects_a_blocked_or_mismatched_projection(self):
        resolution = {
            "state": "ready",
            "requested_mode": "full",
            "effective_mode": "full",
            "network_used": False,
            "receipt_fingerprint": "sha256:resolution",
            "issues": [],
        }
        projections = (
            {
                "state": "blocked",
                "network_used": False,
                "issues": [{"category": "selector-conflict", "detail": "selector differs"}],
            },
            {
                "state": "ready",
                "network_used": False,
                "source_resolution_fingerprint": "sha256:different",
                "issues": [],
            },
        )
        for projection in projections:
            with self.subTest(projection=projection), tempfile.TemporaryDirectory() as tmp, mock.patch.object(
                bridge.aidlc_bundle, "resolve", return_value=resolution
            ), mock.patch.object(bridge.aidlc_bundle, "provision", return_value=projection):
                result = bridge.bundled_full_preflight(Path(tmp), "claude")

            self.assertEqual(result["requested_mode"], "full")
            self.assertEqual(result["effective_mode"], "unavailable")
            self.assertEqual(result["state"], "official-full-unavailable")
            self.assertFalse(result["network_used"])
            self.assertNotEqual(result.get("mode"), "lite")
            self.assertTrue(result["issues"][0]["category"])
            self.assertIn("action", result["issues"][0])

    def test_frozen_requirements_adapter_ignores_selector_and_process_cwd(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            root = Path(tmp).resolve()
            pack = root / ".tailtrail" / "official-aidlc" / "packs" / "pack-a"
            requirements_rule_pack(pack)
            selector = root / ".tailtrail" / "official-aidlc" / "current.json"
            selector.write_text(json.dumps({"pack_path": ".tailtrail/official-aidlc/packs/pack-b"}), encoding="utf-8")
            legacy_pack = root / ".tailtrail" / "official-aidlc"
            requirements_rule_pack(legacy_pack)
            (legacy_pack / "manifest.json").write_text("{}", encoding="utf-8")
            resolution = {
                "state": "ready",
                "compatibility_mode": "bundled-v2",
                "pack_path": pack.relative_to(root).as_posix(),
                "selector_consulted": False,
                "issues": [],
            }
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
            with mock.patch.object(official_requirements.aidlc_bundle, "resolve_bound_run", return_value=resolution) as resolve_bound, mock.patch.object(official_requirements.aidlc_bundle, "resolve_legacy_run") as resolve_legacy:
                previous = Path.cwd()
                os.chdir(other)
                try:
                    contract = official_requirements.stage_contract_for_run(root, "run-a")
                    existing_contract = official_requirements.stage_contract(
                        root, {"compatibility_manifest": ".tailtrail/official-aidlc/manifest.json"}
                    )
                finally:
                    os.chdir(previous)
            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())

        self.assertEqual(before, after)
        self.assertEqual(set(contract), {"core_workflow", "requirements_analysis", "question_format", "content_validation", "session_continuity"})
        self.assertTrue(all(path.startswith(".tailtrail/official-aidlc/packs/pack-a/") for path in contract.values()))
        self.assertEqual(len(existing_contract), 5)
        self.assertTrue(all(path.startswith(".tailtrail/official-aidlc/aws-") for path in existing_contract.values()))
        resolve_bound.assert_called_once_with(root, "run-a")
        resolve_legacy.assert_not_called()

    def test_frozen_requirements_adapter_uses_legacy_only_when_binding_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            pack = root / ".tailtrail" / "official-aidlc"
            requirements_rule_pack(pack)
            missing = {"state": "blocked", "issues": [{"category": "missing-run-binding", "detail": "missing"}]}
            legacy = {
                "state": "legacy-read-only",
                "compatibility_mode": "legacy-v1-bounded-continuation",
                "pack_path": pack.relative_to(root).as_posix(),
                "can_authorize_new_full": False,
                "issues": [],
            }
            with mock.patch.object(official_requirements.aidlc_bundle, "resolve_bound_run", return_value=missing), mock.patch.object(official_requirements.aidlc_bundle, "resolve_legacy_run", return_value=legacy) as resolve_legacy:
                contract = official_requirements.stage_contract_for_run(root, "legacy-run")
            self.assertEqual(len(contract), 5)
            resolve_legacy.assert_called_once()

            altered = {"state": "blocked", "issues": [{"category": "altered-run-binding", "detail": "altered"}]}
            with mock.patch.object(official_requirements.aidlc_bundle, "resolve_bound_run", return_value=altered), mock.patch.object(official_requirements.aidlc_bundle, "resolve_legacy_run") as forbidden_legacy:
                with self.assertRaisesRegex(ValueError, "altered-run-binding"):
                    official_requirements.stage_contract_for_run(root, "altered-run")
            forbidden_legacy.assert_not_called()

    def test_frozen_requirements_adapter_rejects_unsafe_and_incomplete_resolved_packs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            unsafe = {"state": "ready", "compatibility_mode": "bundled-v2", "pack_path": "../outside", "issues": []}
            with mock.patch.object(official_requirements.aidlc_bundle, "resolve_bound_run", return_value=unsafe):
                with self.assertRaisesRegex(ValueError, "safe pack"):
                    official_requirements.stage_contract_for_run(root, "unsafe-run")

            pack = root / ".tailtrail" / "official-aidlc" / "packs" / "pack-incomplete"
            rules = requirements_rule_pack(pack)
            rules["content_validation"].write_text("# wrong marker\n", encoding="utf-8")
            incomplete = {
                "state": "ready",
                "compatibility_mode": "bundled-v2",
                "pack_path": pack.relative_to(root).as_posix(),
                "issues": [],
            }
            with mock.patch.object(official_requirements.aidlc_bundle, "resolve_bound_run", return_value=incomplete):
                with self.assertRaisesRegex(ValueError, "incomplete: content_validation"):
                    official_requirements.stage_contract_for_run(root, "incomplete-run")

    def test_agent_host_rejects_stale_official_requirement_authority_before_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            compatible_pack(root)
            goal = "Add a service workflow."
            boundary_result = subprocess.run(
                start_command(
                    root, goal, "--host", "codex", "--aidlc", "standard", "--format", "json"
                ),
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            boundary = json.loads(boundary_result.stdout)
            references = dict(boundary["official_requirement_authority"]["references"])
            references["core_workflow"] = "stale/rules.md"
            proposal = {
                "schema_version": "1",
                "type": "tailtrail-host-requirement-interpretation",
                "host": "codex",
                "goal": goal,
                "private_reasoning_excluded": True,
                "authority": "official-ai-dlc-pack",
                "authority_mode": "standard",
                "authority_stage": "requirements",
                "authority_references": references,
                "clauses": [{"clause_id": "C-01", "role": "outcome", "text": goal}],
                "requirements": [{
                    "display_id": "REQ-01",
                    "statement": goal,
                    "source_clause_ids": ["C-01"],
                    "intent_terms": ["add", "service", "workflow"],
                }],
                "material_questions": [],
            }
            rejected = subprocess.run(
                start_command(
                    root,
                    goal,
                    "--host",
                    "codex",
                    "--aidlc",
                    "standard",
                    "--requirement-interpretation",
                    json.dumps(proposal),
                    "--format",
                    "json",
                ),
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(boundary_result.returncode, 2)
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("does not match the verified governing rules", rejected.stderr)
            self.assertFalse((root / ".tailtrail" / "runs").exists())
            self.assertFalse((root / "tailtrail-meta").exists())

    def test_answered_prelock_intake_resumes_into_official_standard_same_goal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            compatible_pack(root)
            goal = (
                "Create an AWS credential resource for production security because "
                "it is needed to store OEM credentials."
            )
            started = subprocess.run(
                start_command(
                    root, goal, "--host", "codex", "--aidlc", "standard", "--format", "json"
                ),
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            authority_boundary = json.loads(started.stdout)
            authority = authority_boundary["official_requirement_authority"]
            proposal = {
                "schema_version": "1",
                "type": "tailtrail-host-requirement-interpretation",
                "host": "codex",
                "goal": goal,
                "private_reasoning_excluded": True,
                "authority": "official-ai-dlc-pack",
                "authority_mode": "standard",
                "authority_stage": "requirements",
                "authority_references": authority["references"],
                "clauses": [{"clause_id": "C-01", "role": "outcome", "text": goal}],
                "requirements": [{
                    "display_id": "REQ-01",
                    "statement": goal,
                    "source_clause_ids": ["C-01"],
                    "intent_terms": ["create", "aws", "credential", "resource"],
                    "confidence": "high",
                }],
                "material_questions": ["Which AWS credential store must own this resource?"],
            }
            planned = subprocess.run(
                start_command(
                    root,
                    goal,
                    "--host",
                    "codex",
                    "--aidlc",
                    "standard",
                    "--requirement-interpretation",
                    json.dumps(proposal),
                    "--format",
                    "json",
                ),
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            intake = json.loads(planned.stdout)
            answered = subprocess.run(
                [
                    sys.executable,
                    (ROOT / "scripts" / "tailtrail.py").as_posix(),
                    "requirements",
                    "answer",
                    "--root",
                    root.as_posix(),
                    "--intake-id",
                    intake["intake_id"],
                    "--answers",
                    json.dumps({"MAT-01": "Use AWS Secrets Manager."}),
                    "--format",
                    "json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            resumed = subprocess.run(
                start_command(
                    root,
                    goal,
                    "--aidlc",
                    "standard",
                    "--host",
                    "codex",
                    "--requirement-intake-id",
                    intake["intake_id"],
                    "--format",
                    "json",
                ),
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(started.returncode, 2, started.stderr)
            self.assertEqual(authority["authority"], "official-ai-dlc-pack")
            self.assertEqual(planned.returncode, 0, planned.stderr)
            self.assertEqual(intake["intake_stage"], "navigator-prelock-requirement-intake")
            self.assertEqual(intake["post_intake_route"], "aidlc-standard")
            self.assertEqual(intake["route_posture"]["mode"], "standard")
            self.assertEqual(intake["route_posture"]["state"], "official-standard-ready")
            self.assertEqual(answered.returncode, 0, answered.stderr)
            answered_intake = json.loads(answered.stdout)
            self.assertEqual(answered_intake["state"], "answered")
            self.assertIn(
                f"--requirement-intake-id {intake['intake_id']}",
                answered_intake["continuation"]["command"],
            )
            self.assertIn("--aidlc standard", answered_intake["continuation"]["command"])
            self.assertEqual(resumed.returncode, 0, resumed.stderr or resumed.stdout)
            report = json.loads(resumed.stdout)
            with self.assertRaisesRegex(ValueError, "planning approval blocked"):
                lock.activate(root, report["planning_lock"]["run_id"], True)
            self.assertEqual(report["aidlc_mode"]["mode"], "standard")
            self.assertEqual(report["requirement_intake_resolution"]["intake_id"], intake["intake_id"])
            self.assertEqual(
                report["navigator"]["requirement_interpretation"]["source"],
                "answered-requirement-intake",
            )
            self.assertEqual(
                report["aidlc_requirements"]["state"],
                "authority-bound-in-start-plan",
            )
            self.assertTrue(report["planning_lock"]["run_id"])
            self.assertFalse((root / ".tailtrail" / "runs" / report["planning_lock"]["run_id"] / "anchors" / "approved-v1.json").exists())

    def test_lite_and_off_do_not_require_an_official_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(bridge.preflight(root, "lite")["state"], "local-lite")
            self.assertEqual(bridge.preflight(root, "standard")["state"], "official-pack-unavailable-fallback")
            self.assertEqual(bridge.preflight(root, "medium")["mode"], "lite")
            self.assertEqual(bridge.preflight(root, "off")["state"], "disabled")

    def test_start_intent_routes_default_using_aidlc_and_hands_free_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            default = subprocess.run(start_command(root, "fix one local validation", "--no-planning-lock", "--format", "json"), cwd=ROOT, text=True, capture_output=True, check=False)
            compatible_pack(root)
            requested = subprocess.run(start_command(root, "using AIDLC: add a service feature", "--no-planning-lock", "--format", "json"), cwd=ROOT, text=True, capture_output=True, check=False)
            hands_free = subprocess.run(start_command(root, "hands-free: add an API and rollout plan", "--no-planning-lock", "--format", "json"), cwd=ROOT, text=True, capture_output=True, check=False)
            escalated = subprocess.run(start_command(root, "hands-free: regulated multi-team Terraform rollout", "--no-planning-lock", "--format", "json"), cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertEqual(requested.returncode, 0, requested.stderr)
        self.assertEqual(hands_free.returncode, 0, hands_free.stderr)
        self.assertEqual(escalated.returncode, 0, escalated.stderr)
        self.assertEqual(json.loads(default.stdout)["aidlc_mode"]["mode"], "lite")
        self.assertEqual(json.loads(requested.stdout)["aidlc_mode"]["mode"], "standard")
        self.assertEqual(json.loads(hands_free.stdout)["aidlc_mode"]["mode"], "full")
        self.assertEqual(json.loads(escalated.stdout)["aidlc_mode"]["mode"], "full")
        self.assertIn("official AI-DLC Requirements Analysis", json.loads(requested.stdout)["aidlc_mode_features"]["included"][3])
        self.assertIn("substitute questions", json.loads(escalated.stdout)["aidlc_mode_features"]["not_included"][0])

    def test_standard_aidlc_word_order_and_medium_synonym_select_standard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            compatible_pack(root)
            goals = ["using standard AIDLC: add a page", "AIDLC standard: add a page", "use medium AIDLC: add a page"]
            reports = [
                subprocess.run(start_command(root, goal, "--no-planning-lock", "--format", "json"), cwd=ROOT, text=True, capture_output=True, check=False)
                for goal in goals
            ]
        self.assertTrue(all(report.returncode == 0 for report in reports))
        self.assertTrue(all(json.loads(report.stdout)["aidlc_mode"]["mode"] == "standard" for report in reports))

    def test_standard_phrase_variants_use_the_official_standard_route_when_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); compatible_pack(root)
            for goal in ("use standard AIDLC: add a page", "AIDLC standard: add a page", "use medium AIDLC: add a page", "using AIDLC: add a page"):
                with self.subTest(goal=goal):
                    result = subprocess.run(start_command(root, goal, "--no-planning-lock", "--format", "json"), cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    report = json.loads(result.stdout)
                    self.assertEqual(report["aidlc_mode"]["mode"], "standard")
                    self.assertEqual(report["aidlc_mode"]["state"], "official-standard-ready")

    def test_full_without_project_pack_uses_bundled_source_and_never_downgrades(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = bridge.preflight(Path(tmp), "full")
        self.assertEqual(result["mode"], "full")
        self.assertEqual(result["requested_mode"], "full")
        self.assertEqual(result["effective_mode"], "full")
        self.assertEqual(result["state"], "official-full-ready")
        self.assertFalse(result["network_used"])

    def test_full_preflight_uses_installed_launcher_host_when_host_is_not_explicit(self):
        ready = {
            "mode": "full",
            "requested_mode": "full",
            "effective_mode": "full",
            "state": "official-full-ready",
            "network_used": False,
        }
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ, {"TAILTRAIL_ACTIVE_HOST": "copilot"}, clear=False
        ), mock.patch.object(
            bridge, "bundled_full_preflight", return_value=ready
        ) as bundled:
            result = bridge.preflight(Path(tmp), "full")

        self.assertEqual(result, ready)
        self.assertEqual(bundled.call_args.args[1], "copilot")

    def test_invalid_explicit_external_pack_fails_closed_without_bundled_substitution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "external-pack.json"
            manifest.write_text("{}\n", encoding="utf-8")
            result = bridge.preflight(root, "full", manifest.as_posix(), host="codex")
        self.assertEqual(result["mode"], "full")
        self.assertEqual(result["effective_mode"], "unavailable")
        self.assertEqual(result["state"], "official-full-unavailable")
        self.assertFalse(result["network_used"])

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
                start_command(root, "add workflow", "--aidlc", "full", "--official-intent-id", "intent-1", "--format", "json"),
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            report = json.loads(result.stdout)
            run_id = report["planning_lock"]["run_id"]
            with self.assertRaisesRegex(ValueError, "Full AIDLC requires answers"):
                lock.activate(root, run_id, True)
            self.assertEqual(report["aidlc_requirements"]["state"], "official-aidlc-host-generation-required")
            staged = lock.record_official_aidlc_questions(root, run_id, json.dumps(host_questions()))
            answers = json.dumps([{"question_id": item["id"], "choice": "B"} for item in staged["questions"]])
            revision = lock.submit_aidlc_answers(root, run_id, answers)
            with self.assertRaisesRegex(ValueError, "planning approval blocked"):
                lock.approve_aidlc_requirements(root, run_id, True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["aidlc_mode"]["mode"], "full")
        self.assertEqual(report["official_aidlc_bridge"]["official_intent_id"], "intent-1")
        self.assertEqual(report["official_aidlc_bridge"]["state"], "planned-attachment")
        self.assertEqual(report["aidlc_requirements"]["authority"], "official-ai-dlc-pack")
        self.assertEqual(revision["state"], "official-aidlc-revision-ready")
        self.assertFalse((root / ".tailtrail" / "runs" / run_id / "anchors" / "approved-v1.json").exists())

    def test_public_full_start_persists_the_bundled_run_binding_and_bridge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = subprocess.run(
                start_command(root, "add bundled Full workflow", "--aidlc", "full", "--format", "json"),
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            report = json.loads(result.stdout)
            run_id = report["planning_lock"]["run_id"]
            resolved = bridge.aidlc_bundle.resolve_bound_run(root, run_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["aidlc_mode"]["effective_mode"], "full")
        self.assertEqual(report["official_aidlc_bridge"]["compatibility_mode"], "bundled-v2")
        self.assertEqual(report["official_aidlc_run_binding"]["state"], "ready")
        self.assertEqual(resolved["state"], "ready")
        self.assertEqual(resolved["pack_fingerprint"], report["aidlc_mode"]["pack_fingerprint"])

    def test_official_questions_are_host_recorded_with_advisory_recommendations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); compatible_pack(root)
            result = subprocess.run(start_command(root, "add workflow", "--aidlc", "standard", "--format", "json"), cwd=ROOT, text=True, capture_output=True, check=False)
            report = json.loads(result.stdout); run_id = report["planning_lock"]["run_id"]
            recorded = lock.record_official_aidlc_questions(root, run_id, json.dumps(host_questions()))
            saved = json.loads((root / recorded["official_questions"]).read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(recorded["state"], "official-aidlc-requirements-gathering")
        self.assertEqual(saved["questions"][0]["recommendation_origin"], "tailtrail-advisory")
        self.assertEqual(saved["questions"][0]["requirement_ids"], ["REQ-01"])
        self.assertEqual(saved["questions"][0]["decision_class"], "architecture-decision")
        self.assertEqual(saved["questions"][0]["decision_impact"], ["architecture", "public-contract"])
        self.assertEqual(saved["questions"][0]["known_context"], ["The requested delivery includes service and API behavior."])
        self.assertEqual(saved["questions"][0]["evidence_refs"], ["user-requirement:REQ-01"])
        self.assertEqual(recorded["question_quality"]["warnings"], [])
        rendered = lock.render_aidlc_requirements(recorded)
        self.assertIn("**Affects:** REQ-01", rendered)
        self.assertIn("**Decision:** architecture-decision - architecture, public-contract", rendered)
        answers = official_requirements.validate_answers(
            {"questions": saved["questions"]},
            [{"question_id": "OQ1", "choice": "B"}],
        )
        self.assertEqual(answers["OQ1"]["requirement_ids"], ["REQ-01"])
        self.assertEqual(answers["OQ1"]["decision_class"], "architecture-decision")
        self.assertEqual(answers["OQ1"]["decision_impact"], ["architecture", "public-contract"])
        self.assertEqual(answers["OQ1"]["evidence_refs"], ["user-requirement:REQ-01"])

    def test_official_question_validation_keeps_legacy_payloads_compatible(self):
        legacy = host_questions()
        for key in ("requirement_ids", "decision_class", "decision_impact", "known_context", "evidence_refs"):
            legacy[0].pop(key)

        validated = official_requirements.validate_host_questions(legacy)

        self.assertNotIn("requirement_ids", validated[0])

    def test_official_question_validation_rejects_partial_traceability(self):
        partial = host_questions()
        partial[0].pop("evidence_refs")

        with self.assertRaisesRegex(ValueError, "traceability metadata is incomplete"):
            official_requirements.validate_host_questions(partial)

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
                start_command(root, goal, "--format", "json"),
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
                start_command(root, "add a service", "--aidlc", "full", "--format", "json"),
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
