from __future__ import annotations

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
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ledger = load("phase4_ledger", "scripts/run-ledger.py")
anchor = load("phase4_anchor", "scripts/change-intent-anchor.py")
boundary = load("phase4_boundary", "scripts/task-recovery-boundary.py")
recovery = load("phase4_recovery", "scripts/task-recovery.py")
reconcile = load("phase4_reconcile", "scripts/recovery-reconcile.py")


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


class TaskRecoveryTests(unittest.TestCase):
    def setup_run(self, root: Path) -> tuple[str, str]:
        git(root, "init")
        git(root, "config", "user.email", "tailtrail@example.test")
        git(root, "config", "user.name", "TailTrail Test")
        (root / ".gitignore").write_text(".tailtrail/\nproposal.json\n*.patch\n", encoding="utf-8")
        (root / "src").mkdir()
        (root / "src" / "service.py").write_text("value = 'base'\n", encoding="utf-8")
        (root / "notes.txt").write_text("keep this work\n", encoding="utf-8")
        git(root, "add", ".gitignore", "src/service.py", "notes.txt")
        git(root, "commit", "-m", "initial")
        ledger.init_run(root, "change", "two requirements")
        proposal = root / "proposal.json"
        proposal.write_text(json.dumps({"requirements": [
            {"statement": "Implement first behavior", "likely_paths": ["src/service.py"], "acceptance_criteria": ["first"], "preserve_rules": [], "evidence_plan": ["unit"]},
            {"statement": "Implement second behavior", "likely_paths": ["src/service.py"], "acceptance_criteria": ["second"], "preserve_rules": ["keep first"], "evidence_plan": ["unit"]}
        ]}), encoding="utf-8")
        draft = anchor.draft(root, "change", proposal)
        approved = anchor.approve(root, "change")
        return approved["requirements"][0]["requirement_uid"], approved["requirements"][1]["requirement_uid"]

    def test_validated_requirement_is_preserved_when_active_requirement_recovers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            req1, req2 = self.setup_run(root)
            created = boundary.init(root, "change", ["src"], approved=True)
            self.assertEqual(created["task_branch"], "tailtrail/change")
            boundary.activate(root, "change", req1)
            (root / "src" / "service.py").write_text("value = 'requirement one'\n", encoding="utf-8")
            checkpointed = boundary.checkpoint(root, "change", req1, [], approved=True)
            req1_commit = checkpointed["requirements"][req1]["checkpoint_commit"]
            boundary.activate(root, "change", req2)
            (root / "src" / "service.py").write_text("value = 'broken requirement two'\n", encoding="utf-8")
            planned = recovery.plan(root, "change")
            restored = recovery.apply(root, "change", approved=True)
            content = (root / "src" / "service.py").read_text(encoding="utf-8")
            checkpoint_ref = git(root, "rev-parse", f"refs/tailtrail/change/{req1}")
            activity = ledger.projection(root, "change")["activity"]
        self.assertTrue(planned["safe_to_apply"])
        self.assertTrue(restored["applied"])
        self.assertEqual(content, "value = 'requirement one'\n")
        self.assertEqual(checkpoint_ref, req1_commit)
        self.assertEqual(activity["recovery_applied"], 1)

    def test_recovery_refuses_unexpected_or_untracked_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            req1, _ = self.setup_run(root)
            boundary.init(root, "change", ["src"], approved=True)
            boundary.activate(root, "change", req1)
            (root / "src" / "service.py").write_text("value = 'attempt'\n", encoding="utf-8")
            (root / "outside.txt").write_text("do not touch\n", encoding="utf-8")
            planned = recovery.plan(root, "change")
        self.assertFalse(planned["safe_to_apply"])
        self.assertTrue(any("untracked" in item or "outside" in item for item in planned["issues"]))

    def test_reconciliation_reverses_exact_task_patch_and_preserves_other_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            req1, _ = self.setup_run(root)
            boundary.init(root, "change", ["src"], approved=True)
            boundary.activate(root, "change", req1)
            (root / "src" / "service.py").write_text("value = 'task change'\n", encoding="utf-8")
            patch = root / "task.patch"
            patch.write_text(git(root, "diff", "--", "src/service.py") + "\n", encoding="utf-8")
            (root / "notes.txt").write_text("valid earlier work\n", encoding="utf-8")
            planned = reconcile.plan(root, "change", patch)
            applied = reconcile.apply(root, "change", patch, approved=True)
            source = (root / "src" / "service.py").read_text(encoding="utf-8")
            notes = (root / "notes.txt").read_text(encoding="utf-8")
        self.assertTrue(planned["safe_to_apply"])
        self.assertTrue(applied["applied"])
        self.assertEqual(source, "value = 'base'\n")
        self.assertEqual(notes, "valid earlier work\n")

    def test_reconciliation_refuses_same_hunk_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            req1, _ = self.setup_run(root)
            boundary.init(root, "change", ["src"], approved=True)
            boundary.activate(root, "change", req1)
            (root / "src" / "service.py").write_text("value = 'task change'\n", encoding="utf-8")
            patch = root / "task.patch"
            patch.write_text(git(root, "diff", "--", "src/service.py") + "\n", encoding="utf-8")
            (root / "src" / "service.py").write_text("value = 'later overlapping change'\n", encoding="utf-8")
            planned = reconcile.plan(root, "change", patch)
        self.assertFalse(planned["safe_to_apply"])
        self.assertEqual(planned["classification"], "same-hunk-overlap")
