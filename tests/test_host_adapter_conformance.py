from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location("host_adapter_conformance_test", ROOT / "scripts" / "host-adapter-conformance.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


conformance = load()


class HostAdapterConformanceTests(unittest.TestCase):
    def test_generated_codex_copilot_and_claude_surfaces_match_matrix(self) -> None:
        matrix = conformance.load(ROOT)
        self.assertEqual(conformance.check(ROOT, matrix), [])
        self.assertEqual(matrix["precedence"], conformance.PRECEDENCE)
        self.assertEqual({item["id"] for item in matrix["conformance_scenarios"]}, conformance.REQUIRED_SCENARIOS)

    def test_composed_surface_preserves_precedence_and_closure_boundaries(self) -> None:
        matrix = conformance.load(ROOT)
        body = conformance.render(next(item for item in matrix["hosts"] if item["id"] == "copilot"), matrix)
        self.assertIn("1. Host safety", body)
        self.assertIn("2. User request", body)
        self.assertIn("3. Official AI-DLC stage rules", body)
        self.assertIn("4. TailTrail assurance rules", body)
        self.assertIn("`wait-ci` does not create learning", body)


if __name__ == "__main__":
    unittest.main()
