from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.workflow_enterprise_helpers import policy_source, workflow
from workflow_runtime import enterprise

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("phase12_mcp",ROOT/"scripts"/"mcp-server.py"); mcp=importlib.util.module_from_spec(spec); assert spec and spec.loader; sys.modules[spec.name]=mcp; spec.loader.exec_module(mcp)


class WorkflowEnterpriseMcpTests(unittest.TestCase):
    def test_tool_registry_has_closed_read_and_controlled_surface(self) -> None:
        definitions=mcp.tool_definitions(); names=set(definitions)
        self.assertTrue({"workflow_enterprise_entry","workflow_enterprise_observe","workflow_enterprise_conformance","workflow_enterprise_activate","workflow_enterprise_ingest","workflow_enterprise_rollback"}<=names)
        self.assertEqual(definitions["workflow_enterprise_activate"]["inputSchema"]["required"],["workflow_id","policy_id","tenant_id","repository_id","actor_id","approved"])
        self.assertFalse(definitions["workflow_enterprise_activate"]["inputSchema"]["additionalProperties"])

    def test_policy_and_activation_need_explicit_approval_and_entry_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); wid=workflow(root); ref=policy_source(root)
            with self.assertRaisesRegex(ValueError,"approved: true"): mcp.call_tool("workflow_enterprise_policy_record",{"root":root.as_posix(),"policy_ref":ref,"approved":False})
            mcp.call_tool("workflow_enterprise_policy_record",{"root":root.as_posix(),"policy_ref":ref,"approved":True})
            entry=mcp.call_tool("workflow_enterprise_entry",{"root":root.as_posix(),"policy_id":"entp-reference"})
            with patch.object(enterprise.release,"evaluate",return_value={"status":"passed","gate_fingerprint":"sha256:"+"a"*64}):
                activated=mcp.call_tool("workflow_enterprise_activate",{"root":root.as_posix(),"workflow_id":wid,"policy_id":"entp-reference","tenant_id":"tenant-alpha","repository_id":"repo-primary","actor_id":"actor-operator","approved":True})
        self.assertTrue(entry["execution"]["read_only"]); self.assertEqual(entry["result"]["status"],"blocked"); self.assertEqual(activated["result"]["continuation_mode"],"local")

    def test_unknown_fields_paths_and_types_fail_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with self.assertRaisesRegex(ValueError,"unknown MCP field"): mcp.call_tool("workflow_enterprise_entry",{"root":root.as_posix(),"policy_id":"entp-reference","extra":True})
            with self.assertRaisesRegex(ValueError,"safe relative"): mcp.call_tool("workflow_enterprise_policy_record",{"root":root.as_posix(),"policy_ref":"../policy.json","approved":True})
            with self.assertRaisesRegex(ValueError,"direction is unsupported"): mcp.call_tool("workflow_enterprise_migration_plan",{"root":root.as_posix(),"workflow_id":"ttw-enterprise","direction":"automatic"})
        self.assertFalse((root/".tailtrail").exists())


if __name__=="__main__": unittest.main()
