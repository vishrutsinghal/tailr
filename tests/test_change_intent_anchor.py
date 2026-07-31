from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ledger = load("anchor_test_ledger", "scripts/run-ledger.py")
anchor = load("anchor_test_module", "scripts/change-intent-anchor.py")


class ChangeIntentAnchorTests(unittest.TestCase):
    def draft_input(self, root: Path) -> Path:
        path = root / "proposal.json"
        path.write_text(json.dumps({"goal": "reject zero claim amounts", "requirements": [{"kind": "change", "statement": "Reject zero claim amounts", "acceptance_criteria": ["zero raises validation error"], "preserve_rules": ["positive claims remain valid"], "likely_paths": ["src/claims_api/validation.py"], "evidence_plan": ["focused validation test"]}]}), encoding="utf-8")
        return path

    def test_approval_freezes_durable_uid_and_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); ledger.init_run(root, "run-anchor", "validation")
            drafted = anchor.draft(root, "run-anchor", self.draft_input(root))
            approved = anchor.approve(root, "run-anchor")
        self.assertEqual(drafted["requirements"][0]["requirement_uid"], approved["requirements"][0]["requirement_uid"])
        self.assertTrue(approved["approved_fingerprint"].startswith("sha256:"))
        self.assertEqual(approved["requirements"][0]["status"], "approved")

    def test_second_material_rejection_requires_aidlc_requirements_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); ledger.init_run(root, "run-feedback", "validation")
            drafted = anchor.draft(root, "run-feedback", self.draft_input(root))
            feedback = json.dumps([{"requirement_uid": drafted["requirements"][0]["requirement_uid"], "decision": "reject", "comment": "need service path"}])
            first = anchor.feedback(root, "run-feedback", feedback)
            second = anchor.feedback(root, "run-feedback", feedback)
        self.assertEqual(first["next_requirement_mode"], "ask-targeted-questions-or-offer-aidlc")
        self.assertEqual(second["next_requirement_mode"], "aidlc-requirements-required")

    def test_material_invalidation_is_recorded_without_rewriting_approved_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); ledger.init_run(root, "run-invalidate", "validation")
            anchor.draft(root, "run-invalidate", self.draft_input(root)); approved = anchor.approve(root, "run-invalidate")
            invalidated = anchor.invalidate(root, "run-invalidate", "scope")
            stored = json.loads(Path(approved["path"]).read_text(encoding="utf-8"))
        self.assertEqual(invalidated["approved_fingerprint"], stored["approved_fingerprint"])

    def test_graph_receipt_uses_only_approved_requirement_uid(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); ledger.init_run(root, "run-graph", "validation")
            drafted = anchor.draft(root, "run-graph", self.draft_input(root)); anchor.approve(root, "run-graph")
            receipt = anchor.graph_receipt(root, "run-graph", [drafted["requirements"][0]["requirement_uid"]], ["src/claims_api/validation.py"], "local-ast")
        self.assertEqual(receipt["event_type"], "graph_receipt")
