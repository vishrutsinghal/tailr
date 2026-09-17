"""Shared installer file ops + lock/interpreter hardening.

Run: python -m unittest tests.test_install_files -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# REPO itself first: tests/__init__.py pre-inserts scripts/, where
# scripts/tailtrail.py would otherwise shadow the tailtrail package.
if REPO.as_posix() not in sys.path:
    sys.path.insert(0, REPO.as_posix())

from tailtrail.install import files  # noqa: E402
from tailtrail.install.cli import check_interpreter  # noqa: E402
from tailtrail.install.engine import LOCK_STALE_AFTER_SECONDS, InstallEngine, InstallFailure  # noqa: E402


class SharedFileOpsTests(unittest.TestCase):
    def test_hash_helpers_agree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.txt"
            path.write_bytes(b"hello")
            self.assertEqual(files.sha256_file(path), files.sha256_bytes(b"hello"))
            self.assertEqual(len(files.sha256_file(path)), 64)

    def test_atomic_write_and_copy_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files.atomic_write_text(root / "sub" / "a.txt", "body")
            self.assertEqual((root / "sub" / "a.txt").read_text(encoding="utf-8"), "body")
            files.atomic_copy(root / "sub" / "a.txt", root / "b.txt")
            self.assertEqual((root / "b.txt").read_text(encoding="utf-8"), "body")

    def test_safe_managed_path_refuses_escapes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(InstallFailure):
                files.safe_managed_path(root, "../outside.txt")
            with self.assertRaises(InstallFailure):
                files.safe_managed_path(root, "C:/outside.txt")
            self.assertEqual(
                files.safe_managed_path(root, "a/b.txt"), root / "a" / "b.txt"
            )


class InstallLockTests(unittest.TestCase):
    def _engine(self, root: Path) -> InstallEngine:
        return InstallEngine(root, package_root=REPO)

    def _write_lock(self, root: Path, pid: int, created_at: int) -> None:
        state = root / ".tailtrail" / "install"
        state.mkdir(parents=True, exist_ok=True)
        (state / "lifecycle.lock").write_text(
            json.dumps({"schema_version": "1", "pid": pid, "created_at": created_at})
        )

    def test_live_lock_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = self._engine(root)
            self._write_lock(root, os.getpid(), int(time.time()))
            with self.assertRaises(InstallFailure):
                with engine._lock():
                    pass

    def test_stale_lock_recovers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = self._engine(root)
            self._write_lock(root, 999999999, int(time.time()) - LOCK_STALE_AFTER_SECONDS - 60)
            with engine._lock():
                pass
            self.assertFalse((root / ".tailtrail" / "install" / "lifecycle.lock").exists())


class InterpreterGuardTests(unittest.TestCase):
    def test_store_alias_refused(self) -> None:
        message = check_interpreter(
            "C:\\Users\\x\\AppData\\Local\\Microsoft\\WindowsApps\\python.exe"
        )
        self.assertTrue(message)
        self.assertIn("Store", message)

    def test_real_interpreter_accepted(self) -> None:
        self.assertIsNone(check_interpreter(sys.executable))


if __name__ == "__main__":
    unittest.main()
