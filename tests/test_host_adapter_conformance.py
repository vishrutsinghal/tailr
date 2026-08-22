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

    def test_all_three_hosts_render_the_same_workflow_mcp_boundary(self) -> None:
        matrix = conformance.load(ROOT)
        rendered = {host["id"]: conformance.render(host, matrix) for host in matrix["hosts"]}
        for body in rendered.values():
            self.assertIn("## Durable Workflow MCP boundary", body)
            self.assertIn("same canonical workflow ID", body)
            self.assertIn("cannot invent Planning Lock, AIDLC", body)
            self.assertIn("canonical workflow status or completion boundary", body)
            self.assertIn("CI continuation requires the exact approved CI policy", body)
            self.assertIn("never fixes source, changes", body)
            self.assertIn("Negative assurance returns categorical", body)
            self.assertIn("There is no background deletion", body)
            self.assertIn("Phase 11 release proof accepts only linked sanitized", body)
            self.assertIn("never retires `--no-workflow`", body)
            self.assertIn("Phase 12 enterprise continuation is optional", body)
            self.assertIn("current fencing token", body)
            self.assertIn("canonical local ownership, approvals", body)


if __name__ == "__main__":
    unittest.main()
