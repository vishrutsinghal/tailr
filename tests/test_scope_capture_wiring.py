"""Scope-discovery passive-capture wiring (Phase 2 integration).

Verifies ``navigator_scope.investigate`` queues every file it actually
reads and flushes once into the Phase 1 cache — and that opting out
writes nothing while leaving results unchanged.

Run: python -m unittest tests.test_scope_capture_wiring -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())

import capture_hooks  # noqa: E402
import code_graph_cache  # noqa: E402
import navigator_scope  # noqa: E402
import requirement_discovery  # noqa: E402

SERVICE_PY = '''"""Service module."""

import src.helpers as helpers


def validate_order(order):
    helpers.check(order)
    return True
'''

HELPERS_PY = '''"""Helpers module."""


def check(order):
    return bool(order)
'''

TEST_PY = '''"""Service tests."""

from src.service import validate_order


def test_validate_order():
    assert validate_order({"id": 1})
'''


class ScopeCaptureWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for relative, body in {
            "src/service.py": SERVICE_PY,
            "src/helpers.py": HELPERS_PY,
            "tests/test_service.py": TEST_PY,
        }.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        capture_hooks.reset_for_tests()

    def tearDown(self) -> None:
        capture_hooks.reset_for_tests()
        self.temporary.cleanup()

    def _investigate(self, **kwargs):
        seeds = [navigator_scope.seed("src/service.py", "explicit-path", "user-provided-path")]
        candidates = navigator_scope.candidates_from_seeds(self.root, seeds, ["implementation"])
        frames = requirement_discovery.frames("Change service validation behavior.")
        return navigator_scope.investigate(self.root, frames, candidates, ["bug"], **kwargs)

    def test_investigate_flushes_reads_into_phase1_cache(self) -> None:
        investigated, _, evidence = self._investigate()
        self.assertEqual(evidence["state"], "resolved")
        self.assertEqual(capture_hooks.pending(self.root), [])
        cache_path = code_graph_cache.default_cache_path(self.root)
        self.assertTrue(cache_path.is_file())
        data, error = code_graph_cache.load(cache_path)
        self.assertIsNone(error)
        self.assertTrue(data["files"], "expected discovery reads in the Phase 1 cache")
        for relative in data["files"]:
            self.assertTrue((self.root / relative).is_file())
        self.assertIn("validate_order", data["files"]["src/service.py"]["symbols"])

    def test_opt_out_writes_nothing(self) -> None:
        investigated, _, evidence = self._investigate(allow_passive_capture=False)
        self.assertEqual(evidence["state"], "resolved")
        self.assertIsNone(code_graph_cache.find_cache(self.root))
        self.assertEqual(capture_hooks.pending(self.root), [])


if __name__ == "__main__":
    unittest.main()
