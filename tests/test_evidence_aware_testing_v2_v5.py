from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[name]=m;s.loader.exec_module(m);return m
ledger=load("eat_ledger","scripts/run-ledger.py");anchor=load("eat_anchor","scripts/change-intent-anchor.py");selector=load("eat_selector","scripts/test-tier-selector.py");ingest=load("eat_ingest","scripts/ci-evidence-ingest.py");flaky=load("eat_flaky","scripts/flaky-test-tracker.py");metrics=load("eat_metrics","scripts/evidence-metrics.py")
class EvidenceAwareTestingV2V5Tests(unittest.TestCase):
 def setup_run(self,root):
  ledger.init_run(root,"run","service change");proposal=root/"proposal.json";proposal.write_text(json.dumps({"requirements":[{"statement":"claim submits","likely_paths":["src/service.py"],"acceptance_criteria":[],"preserve_rules":[],"evidence_plan":[],"validation_contract":{"state":"required","tiers":["unit"]},"behavior_contract":{"scenarios":["submit"]}}]}),encoding="utf-8");draft=anchor.draft(root,"run",proposal);anchor.approve(root,"run");return draft["requirements"][0]["requirement_uid"]
 def profile(self,root):
  path=root/"profile.json";path.write_text(json.dumps({"tiers":[{"name":"unit","command":["x"],"environment":"local","requires_approval":False,"prerequisites":[],"cleanup":[]},{"name":"integration","command":["x"],"environment":"local-service","requires_approval":True,"prerequisites":[],"cleanup":[]}]}),encoding="utf-8");return path
 def test_selector_adds_declared_integration_for_behavior(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup_run(root);result=selector.select(root,"run",self.profile(root),["src/service.py"])
  self.assertEqual(result["requirements"][0]["selected_tiers"],["unit","integration"])
 def test_ci_ingestion_and_calibrated_metrics(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup_run(root);source=root/"ci.json";source.write_text(json.dumps({"results":[{"requirement_uid":uid,"tier":"unit","outcome":"pass","command":"ci test","environment":"ci","asserted_behavior":"claim validates"}]}),encoding="utf-8");result=ingest.ingest(root,"run",source);receipts=root/"receipts.json";receipts.write_text(json.dumps({"receipts":result["receipts"]}),encoding="utf-8");report=metrics.report(root,"run",receipts)
  self.assertEqual(report["completeness_ratio"],1.0);self.assertEqual(report["receipt_outcomes"]["pass"],1)
 def test_flaky_history_does_not_mask_failure(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup_run(root);flaky.record(root,"run","tests/test_service.py::test_submit","pass");result=flaky.record(root,"run","tests/test_service.py::test_submit","fail")
  self.assertEqual(result["status"],"flaky");self.assertEqual(result["outcome"],"fail")
if __name__=="__main__":unittest.main()
