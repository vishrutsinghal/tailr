from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"scripts"))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path); module=importlib.util.module_from_spec(spec); assert spec and spec.loader; sys.modules[name]=module; spec.loader.exec_module(module); return module
mcp=load("phase8_mcp","scripts/mcp-server.py"); lock=load("phase8_lock","scripts/planning-lock.py"); anchor=load("phase8_anchor","scripts/change-intent-anchor.py"); recorder=load("phase8_recorder","scripts/closure-recorder.py")
from workflow_runtime import capabilities, compiler, ownership, state, storage, task_scope

class WorkflowMcpTests(unittest.TestCase):
 def workflow(self,root,run="phase8-run"):
  wid=ownership.suggested_id(run); lock.create(root,"mcp workflow",run); lock.save_start_report(root,run,{"goal":"mcp workflow","guided_delivery":{"mode":"guided-delivery"},"navigator":{"requirement_matrix":[{"display_id":"REQ-01","statement":"safe MCP","kind":"change","acceptance_criteria":[],"preserve_rules":[],"likely_paths":["src/service.py"],"evidence_plan":[]}]}}); lock.activate(root,run,True); ownership.bind(root,run,wid); capabilities.propose(root,wid,["code-graph-mapper","requirement-completion-harness","evidence-aware-testing","review"]); task_scope.initialize(root,wid); storage.initialize(root,wid); compiler.compile(root,wid); state.create(root,run,wid); return wid
 def test_read_only_workflow_tools_do_not_create_state_and_closed_fields_fail(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); result=mcp.call_tool("workflow_list",{"root":root.as_posix()}); self.assertFalse((root/".tailtrail").exists())
   with self.assertRaisesRegex(ValueError,"unknown MCP field"): mcp.call_tool("workflow_list",{"root":root.as_posix(),"unexpected":True})
   with self.assertRaisesRegex(ValueError,"root must be a string"): mcp.call_tool("workflow_list",{"root":42})
  self.assertTrue(result["execution"]["read_only"])
 def test_controls_need_approval_and_preserve_cross_workflow_boundaries(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); wid=self.workflow(root)
   with self.assertRaisesRegex(ValueError,"approved: true"): mcp.call_tool("workflow_state_control",{"root":root.as_posix(),"workflow_id":wid,"action":"pause","approved":False})
   paused=mcp.call_tool("workflow_state_control",{"root":root.as_posix(),"workflow_id":wid,"action":"pause","approved":True})
   with self.assertRaisesRegex(ValueError,"safe relative"): mcp.call_tool("workflow_adapter_record",{"root":root.as_posix(),"workflow_id":wid,"stage_id":"bootstrap","adapter_id":"bootstrap","result_ref":"../other.json","approved":True})
  self.assertFalse(paused["execution"]["read_only"])
 def test_tool_list_exposes_canonical_phase8_surface(self):
  names={item["name"] for item in mcp.tool_list()}
  self.assertTrue({"workflow_status","workflow_resume","workflow_closure_finalize","workflow_ci_show","workflow_ci_ingest"} <= names)
  definitions=mcp.tool_definitions(); self.assertEqual(definitions["workflow_create"]["inputSchema"]["required"],["run_id","approved"]); self.assertIn("result_ref",definitions["workflow_adapter_record"]["inputSchema"]["required"]); self.assertEqual(definitions["workflow_ci_ingest"]["inputSchema"]["required"],["workflow_id","receipt_ref","policy_ref","approved"])
 def test_ci_mcp_surface_is_read_only_or_explicitly_controlled(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); shown=mcp.call_tool("workflow_ci_show",{"root":root.as_posix(),"workflow_id":"ttw-phase9-read"})
   self.assertFalse((root/".tailtrail").exists()); self.assertTrue(shown["execution"]["read_only"])
   with self.assertRaisesRegex(ValueError,"approved: true"):
    mcp.call_tool("workflow_ci_ingest",{"root":root.as_posix(),"workflow_id":"ttw-phase9-read","receipt_ref":".tailtrail/receipt.json","policy_ref":".tailtrail/policy.json","approved":False})
   with self.assertRaisesRegex(ValueError,"safe relative"):
    mcp.call_tool("workflow_ci_ingest",{"root":root.as_posix(),"workflow_id":"ttw-phase9-read","receipt_ref":"../receipt.json","policy_ref":".tailtrail/policy.json","approved":True})
 def test_create_refuses_unapproved_canonical_run(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); lock.create(root,"unapproved MCP run","unapproved-run")
   with self.assertRaisesRegex(ValueError,"approved Planning Lock"):
    mcp.call_tool("workflow_create",{"root":root.as_posix(),"run_id":"unapproved-run","approved":True})
 def test_create_finishes_only_the_approved_saved_start_draft_and_preflights_it(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); run_id="phase8-create"
   command=[sys.executable,(ROOT/"scripts"/"task-start.py").as_posix(),"implement a bounded MCP adapter","--root",root.as_posix(),"--planning-run-id",run_id,"--format","json"]
   started=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,check=False); self.assertEqual(started.returncode,0,started.stdout+started.stderr)
   activated=lock.activate(root,run_id,True); wid=activated["workflow_runtime"]["workflow_id"]
   with self.assertRaisesRegex(ValueError,"differs from the approved Start"):
    mcp.call_tool("workflow_create",{"root":root.as_posix(),"run_id":run_id,"workflow_id":ownership.suggested_id("other-run"),"approved":True})
   result=mcp.call_tool("workflow_create",{"root":root.as_posix(),"run_id":run_id,"workflow_id":wid,"approved":True})["result"]; scope_status=task_scope.freshness(root,wid)["status"]
   plan_path=compiler.plan_path(root,wid); plan=json.loads(plan_path.read_text(encoding="utf-8")); plan["template_id"]="forged"; plan_path.write_text(json.dumps(plan),encoding="utf-8")
   with self.assertRaisesRegex(ValueError,"plan/policy preflight failed"):
    mcp.call_tool("workflow_create",{"root":root.as_posix(),"run_id":run_id,"workflow_id":wid,"approved":True})
  self.assertEqual(result["state_view"]["workflow_id"],wid); self.assertEqual(scope_status,"fresh")
 def test_create_does_not_invent_runtime_for_a_legacy_approved_run(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); lock.create(root,"legacy approved run","legacy-run"); lock.save_start_report(root,"legacy-run",{"goal":"legacy"}); lock.approve(root,"legacy-run",True)
   with self.assertRaisesRegex(ValueError,"enabled workflow draft"):
    mcp.call_tool("workflow_create",{"root":root.as_posix(),"run_id":"legacy-run","approved":True})
 def test_evidence_view_includes_canonical_completion_receipt_slot(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); wid=self.workflow(root); result=mcp.call_tool("workflow_evidence_show",{"root":root.as_posix(),"workflow_id":wid})
  self.assertIn("completion_receipt",result["result"]); self.assertIsNone(result["result"]["completion_receipt"])
 def test_closed_types_reject_malformed_stage_approval(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); wid=self.workflow(root)
   with self.assertRaisesRegex(ValueError,"stage_ids must be an array"):
    mcp.call_tool("workflow_approval_decide",{"root":root.as_posix(),"workflow_id":wid,"stage_ids":"bootstrap","action_classes":["read_local"],"operation_kind":"other-guarded","operation_ref":".tailtrail/operation.json","decision":"approved","rationale":"bounded","approved":True})
   with self.assertRaisesRegex(ValueError,"must be a boolean"):
    mcp.call_tool("workflow_closure_finalize",{"root":root.as_posix(),"workflow_id":wid,"accept_evidence_incomplete":"false","approved":True})
 def test_forged_approval_and_stale_scope_fail_before_control(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); wid=self.workflow(root)
   with self.assertRaisesRegex(ValueError,"unknown MCP field"):
    mcp.call_tool("workflow_state_control",{"root":root.as_posix(),"workflow_id":wid,"action":"pause","approval_id":"forged","approved":True})
   (root/"src").mkdir(); (root/"src"/"service.py").write_text("changed",encoding="utf-8")
   with self.assertRaisesRegex(ValueError,"preflight failed"):
    mcp.call_tool("workflow_state_control",{"root":root.as_posix(),"workflow_id":wid,"action":"pause","approved":True})
 def test_modified_plan_and_cross_target_binding_fail_closed(self):
  with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
   root_a=Path(first); root_b=Path(second); wid=self.workflow(root_a); self.workflow(root_b)
   plan_path=compiler.plan_path(root_a,wid); original_plan=plan_path.read_bytes(); plan=json.loads(original_plan); plan["template_id"]="forged"; plan_path.write_text(json.dumps(plan),encoding="utf-8")
   with self.assertRaisesRegex(ValueError,"plan/policy preflight failed"):
    mcp.call_tool("workflow_state_control",{"root":root_a.as_posix(),"workflow_id":wid,"action":"pause","approved":True})
   plan_path.write_bytes(original_plan); binding_a=ownership.binding_path(root_a,wid); binding_b=ownership.binding_path(root_b,wid); binding_a.write_bytes(binding_b.read_bytes())
   with self.assertRaisesRegex(ValueError,"preflight failed"):
    mcp.call_tool("workflow_state_control",{"root":root_a.as_posix(),"workflow_id":wid,"action":"pause","approved":True})
 def test_cross_run_and_incomplete_closure_cannot_forge_success(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); wid=self.workflow(root,"phase8-primary")
   with self.assertRaisesRegex(ValueError,"does not exist"):
    mcp.call_tool("workflow_status",{"root":root.as_posix(),"workflow_id":ownership.suggested_id("another-run")})
   with self.assertRaises((ValueError,FileNotFoundError)):
    mcp.call_tool("workflow_closure_finalize",{"root":root.as_posix(),"workflow_id":wid,"approved":True})
   self.assertNotEqual(state.show(root,wid)["workflow_status"],"completed")
 def test_closure_control_runs_canonical_finalizer_before_linking_receipt(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); (root/"src").mkdir(); (root/"tests").mkdir(); (root/"src"/"service.py").write_text("def safe(): return True\n",encoding="utf-8"); (root/"tests"/"test_service.py").write_text("# proof\n",encoding="utf-8")
   lock.create(root,"complete through MCP","closure-run"); proposal=root/"proposal.json"; proposal.write_text(json.dumps({"requirements":[{"statement":"Complete safely.","acceptance_criteria":["safe"],"preserve_rules":["preserve"],"likely_paths":["src/service.py","tests/test_service.py"],"evidence_plan":[],"validation_contract":{"state":"required","tiers":["unit"]},"architecture_contract":{"required_paths":[],"protected_paths":[],"forbidden_imports":[]},"behavior_contract":{"scenarios":[]}}]}),encoding="utf-8"); anchor.draft(root,"closure-run",proposal); uid=anchor.approve(root,"closure-run")["requirements"][0]["requirement_uid"]; lock.approve(root,"closure-run",True)
   run_dir=root/".tailtrail"/"runs"/"closure-run"; (run_dir/"planning").mkdir(exist_ok=True); (run_dir/"planning"/"execution-handoff-v1.json").write_text(json.dumps({"closure":{"selected_harnesses":[]}}),encoding="utf-8")
   closure_input=root/"closure-input.json"; closure_input.write_text(json.dumps({"schema_version":"1","type":"tailtrail-execution-closure-input","run_id":"closure-run","changed_paths":["src/service.py","tests/test_service.py"],"receipts":[{"requirement_uids":[uid],"tier":"unit","command_label":"safe proof","command":"python -m unittest tests.test_service","outcome":"pass","environment":"local","asserted_behavior":"Safe behavior."}]}),encoding="utf-8"); recorder.record(root,closure_input)
   wid=ownership.suggested_id("closure-run"); ownership.bind(root,"closure-run",wid); capabilities.propose(root,wid,["code-graph-mapper","requirement-completion-harness","evidence-aware-testing","review"]); task_scope.initialize(root,wid); storage.initialize(root,wid); compiler.compile(root,wid); state.create(root,"closure-run",wid)
   result=mcp.call_tool("workflow_closure_finalize",{"root":root.as_posix(),"workflow_id":wid,"approved":True})["result"]
  self.assertEqual(result["completion_report"]["overall_status"],"complete"); self.assertEqual(result["workflow_receipt"]["state"],"completed")

if __name__=="__main__": unittest.main()
