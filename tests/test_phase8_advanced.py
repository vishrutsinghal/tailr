from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[name]=m;s.loader.exec_module(m);return m
ledger=load("p8ledger","scripts/run-ledger.py");anchor=load("p8anchor","scripts/change-intent-anchor.py");phase8=load("p8advanced","scripts/phase8-advanced.py")
class Phase8AdvancedTests(unittest.TestCase):
 def setup_run(self,root):
  ledger.init_run(root,"run","release");p=root/"proposal.json";p.write_text(json.dumps({"requirements":[{"statement":"submit","likely_paths":["src/service.py"],"acceptance_criteria":[],"preserve_rules":[],"evidence_plan":[],"validation_contract":{"state":"required","tiers":["integration"]}}]}),encoding="utf-8");d=anchor.draft(root,"run",p);anchor.approve(root,"run");return d["requirements"][0]["requirement_uid"]
 def write(self,root,name,payload):
  p=root/name;p.write_text(json.dumps(payload),encoding="utf-8");return p
 def test_journey_and_contract_parsers_record_structured_evidence(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup_run(root);j=phase8.journey(root,"run",self.write(root,"j.json",{"journeys":[{"requirement_uid":uid,"test_id":"checkout","framework":"playwright","outcome":"pass","environment":"local","steps":["open"],"fixtures":[],"preservation":["existing"]}]}));c=phase8.contracts(root,"run",self.write(root,"c.json",{"format":"openapi","requirement_uid":uid,"paths":{"/claims":{}}}))
  self.assertEqual(j["journeys"][0]["framework"],"playwright");self.assertEqual(c["contracts"][0]["contract_id"],"openapi:/claims")
 def test_lifecycle_guard_deployment_plan_and_release_signoff(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup_run(root);l=phase8.lifecycle(root,"run",self.write(root,"l.json",{"adapters":[{"id":"health","phase":"health","command":[sys.executable,"-c","pass"],"environment":"local","remote":False,"repository_owned":True}]}),False);d=phase8.deployment(root,"run",self.write(root,"d.json",{"deployment":{"command":["x"]},"migration":{"command":["x"]},"rollback":{"command":["x"]}}));policy=self.write(root,"p.json",{"id":"release","required_tiers":["integration"]});receipts=self.write(root,"r.json",{"receipts":[{"tier":"integration","outcome":"pass"}]});signed=phase8.policy(root,"run",policy,receipts,"owner",True)
  self.assertEqual(l["results"][0]["outcome"],"blocked");self.assertEqual(d["status"],"planned");self.assertEqual(signed["sign_off"]["status"],"recorded-local")
 def test_calibration_labels_unmeasured_input_as_local_evidence(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup_run(root);r=phase8.calibration(root,"run",self.write(root,"m.json",{"runs":[{"baseline_completion":1,"harness_completion":2}]}))
  self.assertEqual(r["delta"],1);self.assertEqual(r["evidence_label"],"local-evidence")
if __name__=="__main__":unittest.main()
