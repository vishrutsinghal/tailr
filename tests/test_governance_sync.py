from __future__ import annotations

import importlib.util
import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START = "<!-- tailtrail-governance:start -->"
END = "<!-- tailtrail-governance:end -->"


def load_module():
    spec = importlib.util.spec_from_file_location("tailtrail_sync_governance_test", ROOT / "scripts" / "sync-governance.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class GovernanceSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.targets = ("AGENTS.md", "ROADMAP.md", "adapters/claude.md")
        self.snapshots = ("demo-project-layout/tailtrail-demo-workspace/tailtrail/AGENTS.md",)
        self.module.TARGETS = self.targets
        self.module.SNAPSHOT_TARGETS = self.snapshots
        self.write("GOVERNANCE.md", self.document("canonical"))
        self.write("GUARDRAILS.md", "\n".join([
            "Do not act with more certainty than the evidence supports.",
            "Do not claim tests passed unless they were run and succeeded.",
            "Token saving must not hide material facts.",
            "Do not remove or weaken safeguards",
        ]))
        for target in self.targets:
            self.write(target, self.document("old"))
        for target in self.snapshots:
            self.write(target, self.document("snapshot-old"))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def document(self, value: str) -> str:
        return f"before\n{START}\n{value}\n{END}\nafter\n"

    def write(self, relative: str, body: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    def read(self, relative: str) -> str:
        return (self.root / relative).read_text(encoding="utf-8")

    def test_canonical_present(self) -> None:
        block = self.module.canonical_block(self.root)
        self.assertIn(START, block)
        self.assertIn(END, block)
        self.assertIn("canonical", block)

    def test_fresh_sync_leaves_zero_drift(self) -> None:
        self.module.sync(self.root)
        self.assertEqual(self.module.check(self.root), [])

    def test_sync_is_idempotent(self) -> None:
        self.module.sync(self.root)
        before = {target: self.read(target) for target in self.targets}
        self.module.sync(self.root)
        after = {target: self.read(target) for target in self.targets}
        self.assertEqual(before, after)

    def test_detect_drift_with_ci_visible_message(self) -> None:
        self.module.sync(self.root)
        self.write("AGENTS.md", self.read("AGENTS.md").replace("canonical", "drifted", 1))
        errors = self.module.check(self.root)
        self.assertTrue(any("AGENTS.md: governance block is not synced with GOVERNANCE.md" in error for error in errors))

    def test_missing_marker_fails(self) -> None:
        self.module.sync(self.root)
        self.write("ROADMAP.md", self.read("ROADMAP.md").replace(END, "", 1))
        errors = self.module.check(self.root)
        self.assertTrue(any("ROADMAP.md: missing governance sync markers" in error for error in errors))

    def test_snapshot_policy(self) -> None:
        snapshot = self.snapshots[0]
        original = self.read(snapshot)
        self.assertEqual(self.module.check(self.root), [f"{target}: governance block is not synced with GOVERNANCE.md" for target in self.targets])
        self.module.sync(self.root)
        self.assertEqual(self.read(snapshot), original)
        self.assertEqual(self.module.check(self.root), [])
        self.module.sync(self.root, include_snapshots=True)
        self.assertNotEqual(self.read(snapshot), original)

    def test_inventory_shape(self) -> None:
        self.write("UNREGISTERED.md", self.document("unregistered"))
        rows = self.module.inventory(self.root)
        by_path = {row["path"]: row for row in rows}
        self.assertEqual(by_path["GOVERNANCE.md"]["role"], "canonical")
        for target in self.targets:
            self.assertEqual(by_path[target]["role"], "target")
        for target in self.snapshots:
            self.assertEqual(by_path[target]["role"], "snapshot")
        self.assertEqual(by_path["UNREGISTERED.md"]["role"], "unregistered")
        self.assertTrue({"path", "role", "status"} <= set(rows[0]))

    def test_strict_rejects_unregistered(self) -> None:
        self.module.sync(self.root)
        self.write("UNREGISTERED.md", self.document("unregistered"))
        with contextlib.redirect_stderr(io.StringIO()):
            default_errors = self.module.check(self.root)
        strict_errors = self.module.check(self.root, strict=True)
        self.assertEqual(default_errors, [])
        self.assertTrue(any("UNREGISTERED.md: unregistered governance marker block" in error for error in strict_errors))

    def test_real_root_sync_is_noop_after_sync(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            copy_root = Path(temp) / "repo"
            keep = ["GOVERNANCE.md", "GUARDRAILS.md", *self.module.TARGETS, *self.module.SNAPSHOT_TARGETS]
            for relative in keep:
                source = ROOT / relative
                if source.is_file():
                    destination = copy_root / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
            self.module.sync(copy_root)
            before = {relative: (copy_root / relative).read_text(encoding="utf-8") for relative in self.module.TARGETS if (copy_root / relative).is_file()}
            self.module.sync(copy_root)
            after = {relative: (copy_root / relative).read_text(encoding="utf-8") for relative in before}
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
