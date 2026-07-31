from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[name]=m;s.loader.exec_module(m);return m
ledger=load("cc_ledger","scripts/run-ledger.py");anchor=load("cc_anchor","scripts/change-intent-anchor.py");continuity=load("cc_continuity","scripts/context-continuity.py")
mcp=load("cc_mcp","scripts/mcp-server.py")
class ContextContinuityTests(unittest.TestCase):
 def setup(self,root):
  ledger.init_run(root,"run","claim");p=root/"proposal.json";p.write_text(json.dumps({"requirements":[{"statement":"Reject zero","acceptance_criteria":["zero raises"],"preserve_rules":["positive valid"],"likely_paths":["src/a.py","src/service.py"],"evidence_plan":[]}]}),encoding="utf-8");d=anchor.draft(root,"run",p);anchor.approve(root,"run");return d["requirements"][0]["requirement_uid"]
 def test_start_packet_uses_approved_requirement_and_pointers(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup(root);result=continuity.render(root,"run",uid,None,220);shown=continuity.show(root,"run",1)
  self.assertEqual(result["trigger"],"implementation-start");self.assertIn("positive valid",result["packet_markdown"]);self.assertIn("anchors/approved-v1.json",result["packet_markdown"]);self.assertEqual(shown["sequence"],1)
 def test_correction_packet_carries_gap_and_do_not_repeat(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup(root);feedback=root/"feedback.json";feedback.write_text(json.dumps({"packet":{"requirement_uid":uid,"evidence":"service proof is missing","next_validation":"run service test"}}),encoding="utf-8");directory=ledger.state_dir(root,"run")/"feedback";ledger.atomic_json(directory/"feedback-1.json",json.loads(feedback.read_text(encoding="utf-8")));result=continuity.render(root,"run",None,None,220)
  self.assertEqual(result["trigger"],"correction-cycle");self.assertIn("service proof is missing",result["packet_markdown"]);self.assertTrue(result["do_not_repeat"])
 def test_unknown_requirement_is_rejected(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup(root)
   with self.assertRaises(ValueError):continuity.render(root,"run","req-missing",None,220)
 def test_rejected_requirement_uses_recorded_feedback(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup(root);ledger.append_event(root,"run","proposal_rejected",{"feedback":[{"requirement_uid":uid,"decision":"reject","comment":"reuse existing flow"}]});result=continuity.render(root,"run",uid,"proposal-rejection",220)
  self.assertIn("reuse existing flow",result["packet_markdown"])
 def test_policy_template_adds_guidance_without_removing_preservation_rules(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup(root);policy=root/"policy.json";policy.write_text(json.dumps({"schema_version":"1","type":"tailtrail-context-continuity-policy","version":"service-v2","max_words":200,"templates":[{"id":"service","triggers":["implementation-start"],"path_prefixes":["src/"],"max_words":180,"additional_guidance":["trace the caller"]}]}),encoding="utf-8");result=continuity.render(root,"run",uid,None,220,policy)
   self.assertEqual(result["policy_version"],"service-v2");self.assertEqual(result["selected_template_id"],"service");self.assertEqual(result["packet_budget_words"],180);self.assertIn("positive valid",result["packet_markdown"]);self.assertIn("trace the caller",result["packet_markdown"]);self.assertTrue(Path(result["receipt_path"]).is_file())
 def test_calibration_reports_saved_artifact_associations(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup(root);source=root/"calibration.json";source.write_text(json.dumps({"missed_interventions":1,"interventions":[{"packet_sequence":1,"words":150,"next_checkpoint_delta":"resolved","assessment":"useful"},{"packet_sequence":2,"words":200,"next_checkpoint_delta":"regressed","assessment":"not-useful"}]}),encoding="utf-8");result=continuity.calibrate(root,"run",source)
   self.assertEqual(result["intervention_count"],2);self.assertEqual(result["average_packet_words"],175);self.assertEqual(result["resolved_or_improved"],1);self.assertEqual(result["false_interventions"],1);self.assertEqual(result["missed_interventions"],1);self.assertTrue(Path(result["artifact"]).is_file())
 def test_mcp_preview_accepts_local_policy_without_writing_artifacts(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup(root);policy=root/"policy.json";policy.write_text(json.dumps({"schema_version":"1","type":"tailtrail-context-continuity-policy","version":"mcp-v2","templates":[{"id":"all","additional_guidance":["keep evidence local"]}]}),encoding="utf-8");result=mcp.call_tool("context_continuity_render",{"root":root.as_posix(),"run_id":"run","requirement_uid":uid,"policy":"policy.json"})
   self.assertTrue(result["read_only"]);self.assertEqual(result["result"]["state"]["policy_version"],"mcp-v2");self.assertFalse((root/".tailtrail"/"runs"/"run"/"continuity").exists())
 def test_v3_accepted_advisory_is_bounded_and_auditable(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup(root);state=continuity.render(root,"run",uid,None,220);policy=root/"selector.json";policy.write_text(json.dumps({"schema_version":"1","type":"tailtrail-context-continuity-selector-policy","version":"v3","enabled":True,"approved":True,"model":"host-model","max_reminder_words":30}),encoding="utf-8");proposal=root/"proposal.json";proposal.write_text(json.dumps({"intervene":True,"requirement_uid":uid,"reason":"The approved service path lacks evidence.","artifact_pointers":[".tailtrail/runs/run/anchors/approved-v1.json"],"reminder":"Keep attention on the approved service path and its evidence gap.","uncertainty":"inferred","authority":"advisory-only","model":"host-model"}),encoding="utf-8");result=continuity.advise(root,"run",proposal,policy,1,True)
   self.assertEqual(result["outcome"],"accepted");self.assertIn("Advisory continuity note",result["advisory_packet"]);self.assertEqual(continuity.advisory_show(root,"run",1)["requirement_uid"],uid);self.assertTrue(Path(result["artifact"]).is_file())
 def test_v3_invalid_proposal_falls_back_to_v2_packet(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup(root);state=continuity.render(root,"run",uid,None,220);policy=root/"selector.json";policy.write_text(json.dumps({"schema_version":"1","type":"tailtrail-context-continuity-selector-policy","version":"v3","enabled":True,"approved":True,"model":"host-model"}),encoding="utf-8");proposal=root/"proposal.json";proposal.write_text(json.dumps({"intervene":True,"requirement_uid":uid,"reason":"Edit the source.","artifact_pointers":[],"reminder":"Edit validation now.","uncertainty":"inferred","authority":"advisory-only","model":"host-model"}),encoding="utf-8");result=continuity.advise(root,"run",proposal,policy,None,True)
   self.assertEqual(result["outcome"],"fallback");self.assertIn("positive valid",result["advisory_packet"]);self.assertIn("source-writing",result["validation"])
if __name__=="__main__":unittest.main()
