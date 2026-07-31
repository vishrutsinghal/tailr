from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[name]=m;s.loader.exec_module(m);return m
ledger=load("validation_ledger","scripts/run-ledger.py");anchor=load("validation_anchor","scripts/change-intent-anchor.py");gate=load("validation_gate","scripts/requirement-completion.py")
class ValidationReceiptTests(unittest.TestCase):
 def test_unavailable_integration_is_not_a_pass(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);ledger.init_run(root,"run","demo");source=root/"proposal.json";source.write_text(json.dumps({"requirements":[{"statement":"Submit claim","acceptance_criteria":[],"preserve_rules":[],"likely_paths":[],"evidence_plan":[],"validation_contract":{"state":"required","tiers":["unit","integration"]}}]}),encoding="utf-8");draft=anchor.draft(root,"run",source);anchor.approve(root,"run");uid=draft["requirements"][0]["requirement_uid"];receipts=root/"receipts.json";receipts.write_text(json.dumps({"receipts":[{"requirement_uid":uid,"tier":"unit","outcome":"pass"},{"requirement_uid":uid,"tier":"integration","outcome":"unavailable"}]}),encoding="utf-8");result=gate.gate(root,"run",receipts)
   self.assertFalse(result["complete"]);self.assertEqual(result["findings"][0]["state"],"unavailable");self.assertEqual(ledger.projection(root,"run")["activity"]["completion_gate"],1)
