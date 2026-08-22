from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests import test_workflow_template_execution as template_support
from workflow_runtime import compiler, ownership, release

ROOT=Path(__file__).resolve().parents[1]
FIXTURES=template_support.FIXTURES
spec=importlib.util.spec_from_file_location("phase11_release_mcp",ROOT/"scripts"/"mcp-server.py"); MCP=importlib.util.module_from_spec(spec); assert spec and spec.loader; sys.modules[spec.name]=MCP; spec.loader.exec_module(MCP)


class WorkflowReleaseScenarioTests(unittest.TestCase):
    def test_all_15_scenarios_record_against_compatible_real_local_templates(self) -> None:
        helper=template_support.WorkflowTemplateExecutionTests()
        self.assertEqual(release.catalog()["scenario_count"],15)
        for index,(scenario,required) in enumerate(release.SCENARIOS.items()):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temp:
                root=Path(temp); template=sorted(release.SCENARIO_TEMPLATES[scenario])[0]; fixture=json.loads((FIXTURES/f"{template}.json").read_text()); wid,_uid=helper._activate(root,fixture,f"-release-{index}"); binding=ownership.show(root,wid)
                observation={"scenario_id":scenario,"workflow_id":wid,"tailtrail_run_id":binding["tailtrail_run_id"],"outcome":"passed","observations":list(required),"evidence_refs":[binding["artifact"]]}; ref=".tailtrail/incoming/scenario.json"; path=root/ref; path.parent.mkdir(parents=True); path.write_text(json.dumps(observation))
                receipt=release.record_scenario(root,wid,ref,True)
                self.assertEqual(receipt["outcome"],"passed"); self.assertEqual(receipt["template_id"],compiler.show(root,wid)["template_id"])

    def test_scenario_recording_rejects_missing_approval_privacy_cross_run_and_wrong_template(self) -> None:
        helper=template_support.WorkflowTemplateExecutionTests()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); fixture=json.loads((FIXTURES/"small-change.json").read_text()); wid,_=helper._activate(root,fixture,"-release-negative"); binding=ownership.show(root,wid); ref=".tailtrail/incoming/scenario.json"; path=root/ref; path.parent.mkdir(parents=True)
            source={"scenario_id":"small-bug-focused-proof","workflow_id":wid,"tailtrail_run_id":binding["tailtrail_run_id"],"outcome":"passed","observations":["focused-unit-proof"],"evidence_refs":[binding["artifact"]]}; path.write_text(json.dumps(source))
            with self.assertRaisesRegex(ValueError,"explicit approval"): release.record_scenario(root,wid,ref,False)
            source["raw_prompt"]="private"; path.write_text(json.dumps(source))
            with self.assertRaisesRegex(ValueError,"privacy-safe"): release.record_scenario(root,wid,ref,True)
            source.pop("raw_prompt"); source["tailtrail_run_id"]="other-run"; path.write_text(json.dumps(source))
            with self.assertRaisesRegex(ValueError,"identity"): release.record_scenario(root,wid,ref,True)
            source["tailtrail_run_id"]=binding["tailtrail_run_id"]; source["scenario_id"]="delivery-aidlc-handoff"; source["observations"]=["aidlc-clarification","handoff-recorded"]; path.write_text(json.dumps(source))
            with self.assertRaisesRegex(ValueError,"incompatible compiler template"): release.record_scenario(root,wid,ref,True)

    def test_cli_catalog_and_blocked_gate_are_public_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); catalog=subprocess.run([sys.executable,(ROOT/"scripts"/"tailtrail.py").as_posix(),"workflow","release","catalog","--root",root.as_posix()],cwd=ROOT,text=True,capture_output=True); gate=subprocess.run([sys.executable,(ROOT/"scripts"/"tailtrail.py").as_posix(),"workflow","release","evaluate","--root",root.as_posix()],cwd=ROOT,text=True,capture_output=True)
        self.assertEqual(catalog.returncode,0,catalog.stdout+catalog.stderr); self.assertEqual(json.loads(catalog.stdout)["scenario_count"],15)
        self.assertEqual(gate.returncode,0,gate.stdout+gate.stderr); self.assertEqual(json.loads(gate.stdout)["status"],"blocked")

    def test_mcp_release_reads_are_closed_and_recording_requires_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); result=MCP.call_tool("workflow_release_catalog",{"root":root.as_posix()})
            with self.assertRaisesRegex(ValueError,"approved: true"): MCP.call_tool("workflow_release_scenario_record",{"root":root.as_posix(),"workflow_id":"ttw-release","observation_ref":".tailtrail/incoming/scenario.json","approved":False})
            with self.assertRaisesRegex(ValueError,"unknown MCP field"): MCP.call_tool("workflow_release_evaluate",{"root":root.as_posix(),"unexpected":True})
        self.assertTrue(result["execution"]["read_only"]); self.assertEqual(result["result"]["scenario_count"],15)


if __name__=="__main__": unittest.main()
