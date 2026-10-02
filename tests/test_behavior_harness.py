from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(n,p):
 s=importlib.util.spec_from_file_location(n,ROOT/p);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[n]=m;s.loader.exec_module(m);return m
ledger=load("behavior_ledger_test","scripts/run-ledger.py");anchor=load("behavior_anchor_test","scripts/change-intent-anchor.py");behavior=load("behavior_test","scripts/behavior-harness.py")
class BehaviorHarnessTests(unittest.TestCase):
 def setup_run(self,root,run_id,requirements):
  ledger.init_run(root,run_id,"behavior");p=root/"p.json";p.write_text(json.dumps({"requirements":requirements}),encoding="utf-8");anchor.draft(root,run_id,p);return anchor.approve(root,run_id)["requirements"][0]["requirement_uid"]
 def test_scenario_requires_matching_requirement_tier_and_assertion(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup_run(root,"run",[{"statement":"reject zero","acceptance_criteria":[],"preserve_rules":[],"likely_paths":["src/a.py"],"evidence_plan":[]}]);s=root/"s.json";s.write_text(json.dumps({"scenarios":[{"scenario_id":"zero-rejected","requirement_uid":uid,"preconditions":["claim exists"],"action":"submit zero","expected_outcome":"validation error","preservation":["positive remains valid"],"evidence":[{"tier":"integration","asserted_behavior":"zero rejected through service"}]}]}),encoding="utf-8");e=root/"e.json";e.write_text(json.dumps({"receipts":[{"requirement_uid":uid,"tier":"integration","outcome":"pass","asserted_behavior":"zero rejected through service","evidence_quality":"attested"}]}),encoding="utf-8");result=behavior.assess(root,"run",s,e);activity=ledger.projection(root,"run")["activity"]
  self.assertTrue(result["complete"]);self.assertEqual(activity["behavior_assessed"],1)
 def test_missing_flow_evidence_stays_incomplete(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup_run(root,"run",[{"statement":"x","acceptance_criteria":[],"preserve_rules":[],"likely_paths":[],"evidence_plan":[]}]);s=root/"s.json";s.write_text(json.dumps({"scenarios":[{"scenario_id":"x","requirement_uid":uid,"evidence":[{"tier":"e2e","asserted_behavior":"x"}]}]}),encoding="utf-8");e=root/"e.json";e.write_text('{"receipts":[]}',encoding="utf-8");result=behavior.assess(root,"run",s,e)
  self.assertFalse(result["complete"])
  self.assertEqual(result["coverage"],{"scenarios":1,"validated":0,"incomplete":1})
  self.assertIn("x",result["unknowns"])
 def test_validated_assessment_reports_coverage(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup_run(root,"run",[{"statement":"y","acceptance_criteria":[],"preserve_rules":[],"likely_paths":[],"evidence_plan":[]}]);s=root/"s.json";s.write_text(json.dumps({"scenarios":[{"scenario_id":"y","requirement_uid":uid,"provenance":"host-declared","evidence":[{"tier":"unit","asserted_behavior":"y"}]}]}),encoding="utf-8");e=root/"e.json";e.write_text(json.dumps({"receipts":[{"requirement_uid":uid,"tier":"unit","outcome":"pass","asserted_behavior":"y","evidence_quality":"attested"}]}),encoding="utf-8");result=behavior.assess(root,"run",s,e)
  self.assertTrue(result["complete"])
  self.assertEqual(result["coverage"],{"scenarios":1,"validated":1,"incomplete":0})
  self.assertEqual(result["unknowns"],[])
  self.assertEqual(result["scenarios"][0]["provenance"],"host-declared")
 def test_later_scenarios_are_evaluated_after_an_early_pass(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup_run(root,"run",[{"statement":"z","acceptance_criteria":[],"preserve_rules":[],"likely_paths":[],"evidence_plan":[]}]);s=root/"s.json";s.write_text(json.dumps({"scenarios":[{"scenario_id":"s1","requirement_uid":uid,"evidence":[{"tier":"unit","asserted_behavior":"y"}]},{"scenario_id":"s2","requirement_uid":uid,"evidence":[{"tier":"e2e","asserted_behavior":"missing"}]}]}),encoding="utf-8");e=root/"e.json";e.write_text(json.dumps({"receipts":[{"requirement_uid":uid,"tier":"unit","outcome":"pass","asserted_behavior":"y","evidence_quality":"attested"}]}),encoding="utf-8");result=behavior.assess(root,"run",s,e)
  self.assertEqual([row["scenario_id"] for row in result["scenarios"]],["s1","s2"])
  self.assertEqual(result["coverage"],{"scenarios":2,"validated":1,"incomplete":1})
  self.assertFalse(result["complete"])
 def test_scenario_without_evidence_needs_a_decision(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup_run(root,"run",[{"statement":"w","acceptance_criteria":[],"preserve_rules":[],"likely_paths":[],"evidence_plan":[]}]);s=root/"s.json";s.write_text(json.dumps({"scenarios":[{"scenario_id":"w","requirement_uid":uid,"evidence":[]}]}),encoding="utf-8");e=root/"e.json";e.write_text('{"receipts":[]}',encoding="utf-8");result=behavior.assess(root,"run",s,e)
  self.assertFalse(result["complete"])
  self.assertEqual(result["scenarios"][0]["state"],"incomplete")
  self.assertEqual(result["findings"][0]["classification"],"needs-decision")
