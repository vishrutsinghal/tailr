from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(n,p):
 s=importlib.util.spec_from_file_location(n,ROOT/p);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[n]=m;s.loader.exec_module(m);return m
ledger=load("behavior_ledger_test","scripts/run-ledger.py");anchor=load("behavior_anchor_test","scripts/change-intent-anchor.py");behavior=load("behavior_test","scripts/behavior-harness.py")
class BehaviorHarnessTests(unittest.TestCase):
 def test_scenario_requires_matching_requirement_tier_and_assertion(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);ledger.init_run(root,"run","behavior");p=root/"p.json";p.write_text(json.dumps({"requirements":[{"statement":"reject zero","acceptance_criteria":[],"preserve_rules":[],"likely_paths":["src/a.py"],"evidence_plan":[]}]}),encoding="utf-8");draft=anchor.draft(root,"run",p);approved=anchor.approve(root,"run");uid=approved["requirements"][0]["requirement_uid"];s=root/"s.json";s.write_text(json.dumps({"scenarios":[{"scenario_id":"zero-rejected","requirement_uid":uid,"preconditions":["claim exists"],"action":"submit zero","expected_outcome":"validation error","preservation":["positive remains valid"],"evidence":[{"tier":"integration","asserted_behavior":"zero rejected through service"}]}]}),encoding="utf-8");e=root/"e.json";e.write_text(json.dumps({"receipts":[{"requirement_uid":uid,"tier":"integration","outcome":"pass","asserted_behavior":"zero rejected through service"}]}),encoding="utf-8");result=behavior.assess(root,"run",s,e);activity=ledger.projection(root,"run")["activity"]
  self.assertTrue(result["complete"]);self.assertEqual(activity["behavior_assessed"],1)
 def test_missing_flow_evidence_stays_incomplete(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);ledger.init_run(root,"run","behavior");p=root/"p.json";p.write_text(json.dumps({"requirements":[{"statement":"x","acceptance_criteria":[],"preserve_rules":[],"likely_paths":[],"evidence_plan":[]}]}),encoding="utf-8");anchor.draft(root,"run",p);uid=anchor.approve(root,"run")["requirements"][0]["requirement_uid"];s=root/"s.json";s.write_text(json.dumps({"scenarios":[{"scenario_id":"x","requirement_uid":uid,"evidence":[{"tier":"e2e","asserted_behavior":"x"}]}]}),encoding="utf-8");e=root/"e.json";e.write_text('{"receipts":[]}',encoding="utf-8");self.assertFalse(behavior.assess(root,"run",s,e)["complete"])
