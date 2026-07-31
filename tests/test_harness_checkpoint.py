from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[name]=m;s.loader.exec_module(m);return m
ledger=load("checkpoint_ledger","scripts/run-ledger.py");anchor=load("checkpoint_anchor","scripts/change-intent-anchor.py");checkpoint=load("checkpoint_module","scripts/harness-checkpoint.py");review=load("completion_review_module","scripts/completion-review.py")
class HarnessCheckpointTests(unittest.TestCase):
 def setup_run(self,root):
  ledger.init_run(root,"run", "validation");proposal=root/"proposal.json";proposal.write_text(json.dumps({"requirements":[{"statement":"Reject zero","acceptance_criteria":["raises"],"preserve_rules":["positive valid"],"likely_paths":["src/a.py"],"evidence_plan":["unit"]}]}),encoding="utf-8");anchor.draft(root,"run",proposal);anchor.approve(root,"run");(root/"src").mkdir();(root/"src/a.py").write_text("x",encoding="utf-8")
 def test_checkpoint_marks_passing_requirement_validated(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup_run(root);results=root/"results.json";results.write_text(json.dumps({"results":[{"control_id":"unit","outcome":"pass"}]}),encoding="utf-8");actual=checkpoint.checkpoint(root,"run",["src/a.py"],results);out=review.review(root,"run")
   self.assertEqual(actual["requirements"][0]["state"],"validated");self.assertTrue(out["complete"])
   activity=ledger.projection(root,"run")["activity"]
   self.assertEqual(activity["harness_checkpoint"],1)
   self.assertEqual(activity["completion_review"],1)
 def test_checkpoint_failure_produces_evidence_gap(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup_run(root);results=root/"results.json";results.write_text(json.dumps({"results":[{"control_id":"unit","outcome":"fail"}]}),encoding="utf-8");checkpoint.checkpoint(root,"run",["src/a.py"],results);out=review.review(root,"run")
  self.assertFalse(out["complete"]);self.assertEqual(out["findings"][0]["category"],"evidence")
