from __future__ import annotations
import importlib.util, json, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path); module=importlib.util.module_from_spec(spec); assert spec and spec.loader; sys.modules[name]=module; spec.loader.exec_module(module); return module
ledger=load("execution_evidence_ledger_test","scripts/run-ledger.py")
anchor=load("execution_evidence_anchor_test","scripts/change-intent-anchor.py")
lock=load("execution_evidence_lock_test","scripts/planning-lock.py")
evidence=load("execution_evidence_test","scripts/execution-evidence.py")

class ExecutionEvidenceTests(unittest.TestCase):
 def setup(self, root):
  lock.create(root,"add page","run"); proposal=root/"proposal.json"; proposal.write_text(json.dumps({"requirements":[{"statement":"Add page.","acceptance_criteria":["page"],"preserve_rules":[],"likely_paths":["src/page.py"],"evidence_plan":[]}]}),encoding="utf-8"); anchor.draft(root,"run",proposal); uid=anchor.approve(root,"run")["requirements"][0]["requirement_uid"]; lock.approve(root,"run",True); return uid
 def test_records_deduplicates_and_indexes_host_evidence(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); uid=self.setup(root); event={"kind":"command-result","requirement_uids":[uid],"changed_paths":["src/page.py"],"tier":"unit","command_label":"page tests","command":"python -m unittest tests.test_page","outcome":"pass","environment":"local","asserted_behavior":"page renders"}; first=evidence.append(root,"run",event,True); second=evidence.append(root,"run",event,True); shown=evidence.show(root,"run"); activity=ledger.projection(root,"run")["activity"]
  self.assertFalse(first["reused"]); self.assertTrue(second["reused"]); self.assertEqual(shown["count"],1); self.assertEqual(activity["execution_evidence_recorded"],1)
 def test_rejects_unapproved_unknown_requirement_and_raw_path(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); uid=self.setup(root); base={"kind":"source-edit","requirement_uids":[uid],"changed_paths":["src/page.py"]}
   with self.assertRaisesRegex(ValueError,"--approved"): evidence.append(root,"run",base,False)
   with self.assertRaisesRegex(ValueError,"unknown approved"): evidence.append(root,"run",{**base,"requirement_uids":["bad"]},True)
   with self.assertRaisesRegex(ValueError,"repository-relative"): evidence.append(root,"run",{**base,"changed_paths":["../secret"]},True)
if __name__=="__main__": unittest.main()
