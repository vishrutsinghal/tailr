from __future__ import annotations

import importlib.util
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


readiness = load("phase4_git_readiness", "scripts/git-readiness.py")


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


class GitReadinessTests(unittest.TestCase):
    def test_clean_repository_is_ready_and_dirty_path_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            git(root, "init")
            git(root, "config", "user.email", "tailtrail@example.test")
            git(root, "config", "user.name", "TailTrail Test")
            (root / "a.txt").write_text("one\n", encoding="utf-8")
            git(root, "add", "a.txt")
            git(root, "commit", "-m", "initial")
            clean = readiness.readiness(root)
            (root / "a.txt").write_text("two\n", encoding="utf-8")
            dirty = readiness.readiness(root)
        self.assertTrue(clean["ready"])
        self.assertFalse(dirty["ready"])
        self.assertEqual(dirty["dirty_paths"], ["a.txt"])
