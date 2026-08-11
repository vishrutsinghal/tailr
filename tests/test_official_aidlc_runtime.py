from __future__ import annotations

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


runtime = load("official_runtime_test", "scripts/official-aidlc-runtime.py")
bridge = load("official_runtime_bridge_test", "scripts/aidlc-official-bridge.py")
ledger = load("official_runtime_ledger_test", "scripts/run-ledger.py")
anchor = load("official_runtime_anchor_test", "scripts/change-intent-anchor.py")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compatible_pack(root: Path) -> None:
    pack = root / ".tailtrail" / "official-aidlc"; pack.mkdir(parents=True)
    files = {"LICENSE": "MIT-0\n", "core-workflow.md": "# workflow\n"}
    for relative, marker in {
        "aws-aidlc-rules/core-workflow.md": "Requirements Analysis",
        "aws-aidlc-rule-details/inception/requirements-analysis.md": "Generate Clarifying Questions",
        "aws-aidlc-rule-details/common/question-format-guide.md": "Other",
        "aws-aidlc-rule-details/common/content-validation.md": "Content Validation",
        "aws-aidlc-rule-details/common/session-continuity.md": "Session",
    }.items():
        files[relative] = f"# {marker}\n"
    for relative, body in files.items():
        path = pack / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(body, encoding="utf-8")
    manifest = {
        "schema_version": "1", "type": "tailtrail-official-aidlc-pack",
        "official": {"source": "https://github.com/awslabs/aidlc-workflows", "revision": "v2.0.0", "license": {"spdx": "MIT-0", "file": "LICENSE"}},
        "host_adapter": {"host": "codex", "rules_path": "core-workflow.md"},
        "integrity": {"algorithm": "sha256", "files": [{"path": relative, "sha256": digest(pack / relative)} for relative in files]},
    }
    (pack / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def attached(root: Path, run_id: str = "runtime-run") -> dict:
    compatible_pack(root)
    ledger.init_run(root, run_id, "deliver a service change")
    bridge.create(root, run_id, "deliver a service change", official_intent_id="intent-runtime", official_session_id="session-runtime")
    proposal = root / "proposal.json"
    proposal.write_text(json.dumps({"goal": "deliver a service change", "requirements": [{"display_id": "REQ-01", "statement": "Deliver the approved behavior.", "acceptance_criteria": ["behavior works"], "preserve_rules": ["preserve callers"], "likely_paths": ["src/service.py"], "evidence_plan": ["focused test"]}]}), encoding="utf-8")
    anchor.draft(root, run_id, proposal); approved = anchor.approve(root, run_id)
    bridge.activate(root, run_id)
    runtime.attach(root, run_id)
    return approved


def receipt(root: Path, approved: dict, sequence: int, action: str, source: str, target: str, *, run_id: str = "runtime-run", receipt_id: str | None = None) -> Path:
    payload = {
        "schema_version": "1", "type": "official-aidlc-transition-receipt",
        "receipt_id": receipt_id or f"receipt-{sequence}", "run_id": run_id,
        "official_session_id": "session-runtime", "official_revision": "v2.0.0",
        "sequence": sequence, "action": action, "from_stage": source, "to_stage": target,
        "authority": "official-ai-dlc-pack", "runtime_adapter_version": "v1",
        "approved_anchor_fingerprint": approved["approved_fingerprint"],
        "reason_code": "official-stage-decision", "requirement_uids": [approved["requirements"][0]["requirement_uid"]],
        "evidence_references": [], "boundary": "Official host adapter stage receipt; no source or prompt body included.",
    }
    payload["integrity"] = {"algorithm": "sha256", "digest": runtime.canonical_digest(payload)}
    path = root / f"receipt-{sequence}-{action}.json"; path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class OfficialAidlcRuntimeTests(unittest.TestCase):
    def test_attach_and_ordered_advance_are_restart_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); approved = attached(root)
            created = runtime.import_transition(root, "runtime-run", receipt(root, approved, 1, "advance", "requirements", "design"))
            resumed = runtime.status(root, "runtime-run")
            canonical = runtime.STATE.project(root, "runtime-run")
        self.assertEqual(created["current_stage"], "design")
        self.assertEqual(resumed["transition_count"], 1)
        self.assertEqual(resumed["next_sequence"], 2)
        self.assertEqual(canonical["official_runtime"], {"attached": True, "current_stage": "design", "transition_count": 1})

    def test_public_cli_reports_the_attached_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); attached(root)
            result = subprocess.run([sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "aidlc", "official", "runtime", "status", "--root", root.as_posix(), "--run-id", "runtime-run"], cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(json.loads(result.stdout)["state"], "active")

    def test_stale_out_of_order_wrong_run_and_invalid_digest_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); approved = attached(root)
            stale = receipt(root, approved, 1, "advance", "design", "implementation")
            with self.assertRaisesRegex(ValueError, "stale transition"):
                runtime.import_transition(root, "runtime-run", stale)
            out_of_order = receipt(root, approved, 2, "advance", "requirements", "design")
            with self.assertRaisesRegex(ValueError, "sequence"):
                runtime.import_transition(root, "runtime-run", out_of_order)
            wrong_run = receipt(root, approved, 1, "advance", "requirements", "design", run_id="other")
            with self.assertRaisesRegex(ValueError, "run_id"):
                runtime.import_transition(root, "runtime-run", wrong_run)
            bad = receipt(root, approved, 1, "advance", "requirements", "design")
            payload = json.loads(bad.read_text(encoding="utf-8")); payload["reason_code"] = "altered"; bad.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "integrity"):
                runtime.import_transition(root, "runtime-run", bad)

    def test_resume_redo_and_recovery_require_explicit_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); approved = attached(root)
            runtime.import_transition(root, "runtime-run", receipt(root, approved, 1, "resume", "requirements", "requirements"), expected_action="resume")
            runtime.import_transition(root, "runtime-run", receipt(root, approved, 2, "advance", "requirements", "design"))
            result = runtime.import_transition(root, "runtime-run", receipt(root, approved, 3, "recovery", "design", "requirements"), expected_action="recovery")
            runtime.import_transition(root, "runtime-run", receipt(root, approved, 4, "redo", "requirements", "requirements"), expected_action="redo")
            events = ledger.projection(root, "runtime-run")["activity"]
        self.assertEqual(result["current_stage"], "requirements")
        self.assertEqual(events["official_aidlc_runtime_recovery_routed"], 2)

    def test_duplicate_and_jump_prerequisite_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); approved = attached(root)
            first = receipt(root, approved, 1, "resume", "requirements", "requirements", receipt_id="same-receipt")
            runtime.import_transition(root, "runtime-run", first)
            duplicate = receipt(root, approved, 2, "resume", "requirements", "requirements", receipt_id="same-receipt")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                runtime.import_transition(root, "runtime-run", duplicate)
            jump = receipt(root, approved, 2, "jump", "requirements", "handoff")
            with self.assertRaisesRegex(ValueError, "requires"):
                runtime.import_transition(root, "runtime-run", jump)
            evidence = root / ".tailtrail" / "runs" / "runtime-run" / "aidlc-official" / "checkpoints" / "evidence-checkpoint-v1.json"
            evidence.parent.mkdir(parents=True, exist_ok=True); evidence.write_text(json.dumps({"complete": True}), encoding="utf-8")
            result = runtime.import_transition(root, "runtime-run", jump)
        self.assertEqual(result["current_stage"], "handoff")

    def test_altered_pack_and_pending_session_block_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); attached(root)
            (root / ".tailtrail" / "official-aidlc" / "core-workflow.md").write_text("altered\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not compatible"):
                runtime.assert_attached(root, "runtime-run")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); compatible_pack(root); ledger.init_run(root, "pending", "goal")
            bridge.create(root, "pending", "goal")
            proposal = root / "proposal.json"; proposal.write_text(json.dumps({"goal": "goal", "requirements": [{"statement": "Do work."}]}), encoding="utf-8")
            anchor.draft(root, "pending", proposal); anchor.approve(root, "pending"); bridge.activate(root, "pending")
            with self.assertRaisesRegex(ValueError, "real host-issued"):
                runtime.attach(root, "pending")


if __name__ == "__main__":
    unittest.main()
