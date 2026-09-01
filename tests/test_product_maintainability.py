from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pm4_maintainability", ROOT / "scripts" / "product-maintainability.py")
maintainability = importlib.util.module_from_spec(spec); assert spec and spec.loader
sys.modules[spec.name] = maintainability; spec.loader.exec_module(maintainability)


class ProductMaintainabilityTests(unittest.TestCase):
    def test_repository_inventory_passes_and_is_registry_derived(self):
        result = maintainability.build(ROOT)
        self.assertEqual(result["validation"]["status"], "passed", result["validation"]["issues"])
        registry = json.loads((ROOT / "tailtrail-registry.json").read_text(encoding="utf-8"))
        self.assertEqual(result["registry"]["feature_count"], len(registry["features"]))
        self.assertIn("scripts/orchestration/run_resolution.py", {row["path"] for row in result["modules"]["files"]})

    def test_document_owner_contract_rejects_duplicates(self):
        owners = json.loads((ROOT / maintainability.OWNERS).read_text(encoding="utf-8"))
        owners["owners"].append(copy.deepcopy(owners["owners"][0]))
        _projection, issues = maintainability._documentation_projection(ROOT, owners)
        self.assertTrue(any("duplicated" in item for item in issues))

    def test_feature_dependency_cycle_is_actionable(self):
        registry = {"features":[
            {"id":"one","owner":"team","commands":[],"mcp_tools":[],"docs":[],"scripts":[],"tests":[],"depends_on":["two"]},
            {"id":"two","owner":"team","commands":[],"mcp_tools":[],"docs":[],"scripts":[],"tests":[],"depends_on":["one"]},
        ]}
        _projection, issues = maintainability._registry_projection(ROOT, registry)
        self.assertTrue(any("dependency cycle" in item for item in issues))

    def test_cli_write_requires_approval_and_public_route_works(self):
        denied = subprocess.run([sys.executable, str(ROOT/"scripts"/"tailtrail.py"), "maturity", "maintainability", "inventory", "--root", str(ROOT), "--write"], text=True, capture_output=True)
        self.assertEqual(denied.returncode, 2)
        shown = subprocess.run([sys.executable, str(ROOT/"scripts"/"tailtrail.py"), "maturity", "maintainability", "status", "--root", str(ROOT)], text=True, capture_output=True)
        self.assertEqual(shown.returncode, 0, shown.stdout + shown.stderr)
        self.assertEqual(json.loads(shown.stdout)["validation"]["status"], "passed")

    def test_mcp_and_cli_share_the_same_inventory_service(self):
        mcp_spec = importlib.util.spec_from_file_location("pm4_mcp", ROOT / "scripts" / "mcp-server.py")
        mcp = importlib.util.module_from_spec(mcp_spec); assert mcp_spec and mcp_spec.loader
        sys.modules[mcp_spec.name] = mcp; mcp_spec.loader.exec_module(mcp)
        result = mcp.call_tool("maintainability_inventory", {"root": str(ROOT)})
        self.assertEqual(result["validation"]["status"], "passed")
        self.assertEqual(result["fingerprint"], maintainability.build(ROOT)["fingerprint"])


if __name__ == "__main__": unittest.main()
