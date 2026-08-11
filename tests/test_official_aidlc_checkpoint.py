from __future__ import annotations

import hashlib
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


checkpoint = load("official_checkpoint_test", "scripts/official-aidlc-checkpoint.py")
bridge = load("official_checkpoint_bridge", "scripts/aidlc-official-bridge.py")
runtime = load("official_checkpoint_runtime_test", "scripts/official-aidlc-runtime.py")
lock = load("official_checkpoint_lock", "scripts/planning-lock.py")
anchor = load("official_checkpoint_anchor", "scripts/change-intent-anchor.py")


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
    }.items(): files[relative] = f"# {marker}\n"
    for relative, body in files.items():
        path = pack / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(body, encoding="utf-8")
    manifest = {"schema_version": "1", "type": "tailtrail-official-aidlc-pack", "official": {"source": "https://github.com/awslabs/aidlc-workflows", "revision": "v2.0.0", "license": {"spdx": "MIT-0", "file": "LICENSE"}}, "host_adapter": {"host": "codex", "rules_path": "core-workflow.md"}, "integrity": {"algorithm": "sha256", "files": [{"path": relative, "sha256": digest(pack / relative)} for relative in files]}}
    (pack / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def full_run(root: Path, run_id: str = "full-checkpoint") -> None:
    compatible_pack(root)
    lock.create(root, "add API contract and service behavior", run_id)
    lock.save_start_report(root, run_id, {"goal": "add API contract and service behavior", "aidlc_mode": {"mode": "full"}, "guided_delivery": {"mode": "guided-delivery"}, "navigator": {}})
    bridge.create(root, run_id, "add API contract and service behavior", official_session_id="session-checkpoint")
    proposal = root / "proposal.json"
    proposal.write_text(json.dumps({"goal": "add API contract and service behavior", "requirements": [{"display_id": "REQ-01", "kind": "change", "statement": "Update API contract and service behavior.", "acceptance_criteria": ["contract works"], "preserve_rules": ["preserve callers"], "likely_paths": ["src/api.py"], "evidence_plan": ["contract test"]}]}), encoding="utf-8")
    anchor.draft(root, run_id, proposal); anchor.approve(root, run_id)
    bridge.activate(root, run_id); runtime.attach(root, run_id)


def transition(root: Path, sequence: int, source: str, target: str, action: str = "advance") -> None:
    approved = json.loads((root / ".tailtrail" / "runs" / "full-checkpoint" / "anchors" / "approved-v1.json").read_text(encoding="utf-8"))
    payload = {"schema_version": "1", "type": "official-aidlc-transition-receipt", "receipt_id": f"checkpoint-transition-{sequence}", "run_id": "full-checkpoint", "official_session_id": "session-checkpoint", "official_revision": "v2.0.0", "sequence": sequence, "action": action, "from_stage": source, "to_stage": target, "authority": "official-ai-dlc-pack", "runtime_adapter_version": "v1", "approved_anchor_fingerprint": approved["approved_fingerprint"], "reason_code": "official-stage-decision", "requirement_uids": [approved["requirements"][0]["requirement_uid"]], "evidence_references": [], "boundary": "Official stage receipt for focused checkpoint testing."}
    payload["integrity"] = {"algorithm": "sha256", "digest": runtime.canonical_digest(payload)}
    path = root / f"transition-{sequence}.json"; path.write_text(json.dumps(payload), encoding="utf-8")
    runtime.import_transition(root, "full-checkpoint", path)


class OfficialAidlcCheckpointTests(unittest.TestCase):
    def test_design_to_test_evidence_and_handoff_are_requirement_linked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); full_run(root)
            transition(root, 1, "requirements", "design")
            design = checkpoint.design_plan(root, "full-checkpoint")
            decision = checkpoint.design_approve(root, "full-checkpoint", True)
            transition(root, 2, "design", "implementation")
            source_checkpoint = root / "checkpoint.json"; source_checkpoint.write_text(json.dumps({"type": "tailtrail-harness-checkpoint", "run_id": "full-checkpoint", "requirements": [{"requirement_uid": design["requirements"][0]["requirement_uid"]}]}), encoding="utf-8")
            construction = checkpoint.construction_checkpoint(root, "full-checkpoint", source_checkpoint)
            transition(root, 3, "implementation", "build-and-test")
            plan = checkpoint.test_plan(root, "full-checkpoint", "standard")
            receipt = root / "receipt.json"; receipt.write_text(json.dumps({"results": [{"requirement_uids": [plan["requirements"][0]["requirement_uid"]], "tier": "unit", "outcome": "pass"}, {"requirement_uids": [plan["requirements"][0]["requirement_uid"]], "tier": "integration", "outcome": "pass"}, {"requirement_uids": [plan["requirements"][0]["requirement_uid"]], "tier": "contract", "outcome": "pass"}]}), encoding="utf-8")
            evidence = checkpoint.evidence_checkpoint(root, "full-checkpoint", [receipt])
            transition(root, 4, "build-and-test", "handoff")
            handoff = checkpoint.handoff(root, "full-checkpoint")
        self.assertTrue(design["perspectives"])
        self.assertTrue(decision["approved"])
        self.assertTrue(construction["complete"])
        self.assertEqual(plan["requirements"][0]["required_tiers"], ["unit", "integration", "contract"])
        self.assertTrue(evidence["complete"])
        self.assertTrue(handoff["ready"])

    def test_evidence_gap_routes_back_to_build_and_test(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); full_run(root)
            transition(root, 1, "requirements", "design")
            checkpoint.design_plan(root, "full-checkpoint"); checkpoint.design_approve(root, "full-checkpoint", True)
            transition(root, 2, "design", "implementation")
            source_checkpoint = root / "checkpoint.json"; source_checkpoint.write_text(json.dumps({"type": "tailtrail-harness-checkpoint", "run_id": "full-checkpoint", "requirements": [{"requirement_uid": json.loads((root / ".tailtrail" / "runs" / "full-checkpoint" / "anchors" / "approved-v1.json").read_text(encoding="utf-8"))["requirements"][0]["requirement_uid"]}]}), encoding="utf-8")
            checkpoint.construction_checkpoint(root, "full-checkpoint", source_checkpoint)
            transition(root, 3, "implementation", "build-and-test")
            plan = checkpoint.test_plan(root, "full-checkpoint", "standard")
            receipt = root / "receipt.json"; receipt.write_text(json.dumps({"results": [{"requirement_uids": [plan["requirements"][0]["requirement_uid"]], "tier": "unit", "outcome": "pass"}]}), encoding="utf-8")
            evidence = checkpoint.evidence_checkpoint(root, "full-checkpoint", [receipt])
        self.assertFalse(evidence["complete"])
        self.assertEqual(evidence["gaps"][0]["recommended_official_stage"], "build-and-test")
        self.assertIn("correction_packet", evidence)


if __name__ == "__main__":
    unittest.main()
