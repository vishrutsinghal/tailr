from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[name]=m;s.loader.exec_module(m);return m
ledger=load("harness_feedback_ledger","scripts/run-ledger.py")
feedback=load("harness_feedback_test","scripts/harness-feedback.py")
class HarnessFeedbackTests(unittest.TestCase):
 def test_only_highest_value_gap_becomes_packet(self):
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/"review.json";path.write_text(json.dumps({"findings":[{"requirement_uid":"req-a","category":"evidence","classification":"unchanged","message":"unit failed"},{"requirement_uid":"req-b","category":"scope","classification":"new-drift","message":"missing"}]}),encoding="utf-8");result=feedback.feedback(path)
  self.assertEqual(result["packet"]["requirement_uid"],"req-a");self.assertEqual(len(result["deferred_findings"]),1)
 def test_run_scoped_packet_is_logged(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);ledger.init_run(root,"run","demo");path=root/"review.json";path.write_text(json.dumps({"findings":[{"requirement_uid":"req-a","category":"evidence","classification":"unchanged","message":"unit failed"}]}),encoding="utf-8");result=feedback.feedback(path,root,"run")
   self.assertEqual(result["status"],"correction-needed")
   self.assertEqual(ledger.projection(root,"run")["activity"]["harness_feedback"],1)
