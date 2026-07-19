import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MCP_PATH = ROOT / "scripts" / "mcp-server.py"


def load_module():
    spec = importlib.util.spec_from_file_location("tailtrail_mcp_server_test", MCP_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


mcp = load_module()


class McpServerTests(unittest.TestCase):
    def test_tool_list_is_read_only_allowlist(self):
        self.assertEqual(
            mcp.READ_ONLY_TOOLS,
            (
                "navigator_plan",
                "start_report",
                "guardrail_check",
                "graph_map",
                "install_status",
                "eval_scenario_list",
                "eval_scenario_report",
            ),
        )
        self.assertEqual(set(mcp.HANDLERS), set(mcp.READ_ONLY_TOOLS))
        self.assertEqual(mcp.ensure_safe_tools(), [])

    def test_tool_list_is_projected_from_registry(self):
        projection = mcp.load_registry().mcp_projection(mcp.load_registry().load_registry())

        self.assertEqual([item["tool"] for item in projection], list(mcp.READ_ONLY_TOOLS))
        self.assertTrue(all(item["read_only"] is True for item in projection))

    def test_tool_schemas_are_json_objects(self):
        tools = mcp.tool_list()
        self.assertEqual([item["name"] for item in tools], list(mcp.READ_ONLY_TOOLS))
        for tool in tools:
            self.assertIsInstance(tool["description"], str)
            self.assertIsInstance(tool["inputSchema"], dict)
            self.assertEqual(tool["inputSchema"]["type"], "object")
            self.assertIn("additionalProperties", tool["inputSchema"])

    def test_unknown_tool_is_rejected(self):
        with self.assertRaises(ValueError):
            mcp.call_tool("write_file", {})
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "apply_fix", "arguments": {}}}
        response = mcp.handle(request)
        self.assertIn("error", response)
        self.assertIn("Unknown or disallowed", response["error"]["message"])

    def test_stdio_tools_list(self):
        request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n"
        result = subprocess.run(
            [sys.executable, MCP_PATH.as_posix(), "serve"],
            cwd=ROOT,
            input=request,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["id"], 1)
        self.assertEqual([item["name"] for item in payload["result"]["tools"]], list(mcp.READ_ONLY_TOOLS))

    def test_doctor_passes(self):
        result = subprocess.run(
            [sys.executable, MCP_PATH.as_posix(), "doctor"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("read-only", result.stdout)

    def test_navigator_plan_command_construction(self):
        calls = []
        original = mcp.command_result

        def fake_command_result(command, cwd):
            calls.append((command, cwd))
            return {"command": command, "cwd": cwd.as_posix(), "exit_code": 0, "stdout": "{\"ok\": true}", "stderr": ""}

        try:
            mcp.command_result = fake_command_result
            result = mcp.navigator_plan({"goal": "fix bug", "root": ROOT.as_posix(), "changed": ["src/a.py"], "format": "json"})
        finally:
            mcp.command_result = original

        self.assertEqual(result["result"], {"ok": True})
        command, cwd = calls[0]
        self.assertEqual(cwd, ROOT)
        self.assertIn("navigator.py", command[1])
        self.assertIn("--changed", command)
        self.assertIn("src/a.py", command)

    def test_guardrail_check_with_diff_uses_temp_diff_and_cleans_it(self):
        result = mcp.guardrail_check({"root": ROOT.as_posix(), "diff": "+\"left-pad\": \"1.0.0\"", "format": "json"})
        self.assertEqual(result["tool"], "guardrail_check")
        self.assertEqual(result["execution"]["exit_code"], 0)
        self.assertTrue(result["execution"]["read_only"])
        self.assertIn("tailtrail-guardrail-check", result["result"]["type"])

    def test_install_status_reads_manifest_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / ".tailtrail-install.json"
            manifest.write_text(json.dumps({"surface": "core", "pack_dir": "."}), encoding="utf-8")
            before = manifest.read_text(encoding="utf-8")
            result = mcp.install_status({"root": root.as_posix()})
            after = manifest.read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertEqual(result["result"]["surface"], "core")

    def test_eval_scenario_list_is_read_only(self):
        result = mcp.eval_scenario_list({"format": "json"})

        self.assertEqual(result["tool"], "eval_scenario_list")
        self.assertEqual(result["execution"]["exit_code"], 0)
        self.assertTrue(result["execution"]["read_only"])
        self.assertEqual(result["result"]["type"], "evaluation-scenario-list")
        self.assertTrue(any(item["scenario_id"] == "validation-bug" for item in result["result"]["scenarios"]))

    def test_eval_scenario_report_is_read_only_and_does_not_write_result(self):
        result_path = ROOT / "benchmarks" / "evaluation" / "results" / "validation-bug-scenario-report.json"
        before_exists = result_path.exists()

        result = mcp.eval_scenario_report({"scenario": "validation-bug", "format": "json"})

        self.assertEqual(result["tool"], "eval_scenario_report")
        self.assertEqual(result["execution"]["exit_code"], 0)
        self.assertTrue(result["execution"]["read_only"])
        self.assertEqual(result["result"]["type"], "evaluation-scenario-result")
        self.assertEqual(result["result"]["scenario_id"], "validation-bug")
        self.assertEqual(result_path.exists(), before_exists)


if __name__ == "__main__":
    unittest.main()
