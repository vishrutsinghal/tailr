from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[name]=m;s.loader.exec_module(m);return m
ledger=load("program_test_ledger","scripts/run-ledger.py");program=load("program_test_plan","scripts/program-plan.py");checkpoint=load("program_test_checkpoint","scripts/program-checkpoint.py");orchestrator=load("program_test_orchestrator","scripts/delivery-orchestrator.py")
class ProgramDeliveryTests(unittest.TestCase):
 def setup(self,root):
  ledger.init_run(root,"program","delivery");plan=root/"plan.json";plan.write_text(json.dumps({"goal":"end to end","correction_budget":1,"features":[{"id":"F-01","requirements":["r1"]},{"id":"F-02","depends_on":["F-01"],"requirements":["r2"]}]}),encoding="utf-8");program.init(root,"program",plan,True,True);return plan
 def test_dependency_and_resume_order(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup(root);first=orchestrator.next_action(root,"program");checkpoint.checkpoint(root,"program","F-01","active",[]);checkpoint.checkpoint(root,"program","F-01","validated",["receipt"]);second=orchestrator.next_action(root,"program")
  self.assertEqual(first["action"]["feature_id"],"F-01");self.assertEqual(second["action"]["feature_id"],"F-02")
 def test_pause_routes_to_approved_replan(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup(root);checkpoint.checkpoint(root,"program","F-01","paused",[],"design gap");result=orchestrator.next_action(root,"program")
  self.assertEqual(result["action"]["action"],"replan");self.assertTrue(result["action"]["requires_approval"])
if __name__=="__main__":unittest.main()
