from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[name]=m;s.loader.exec_module(m);return m
ledger=load("architecture_test_ledger","scripts/run-ledger.py");anchor=load("architecture_test_anchor","scripts/change-intent-anchor.py");fitness=load("architecture_test","scripts/architecture-fitness.py")
class ArchitectureFitnessTests(unittest.TestCase):
 def setup(self,root):
  ledger.init_run(root,"run","architecture");(root/"src").mkdir();(root/"src"/"service.py").write_text("import storage.db\n",encoding="utf-8");proposal=root/"proposal.json";proposal.write_text(json.dumps({"requirements":[{"statement":"validate through service","likely_paths":["src/service.py"],"acceptance_criteria":[],"preserve_rules":[],"evidence_plan":[],"architecture_contract":{"required_paths":["src/caller.py"],"forbidden_imports":[{"source_prefix":"src","target_prefix":"storage"}]}}]}),encoding="utf-8");anchor.draft(root,"run",proposal);anchor.approve(root,"run")
 def test_reports_missed_caller_and_forbidden_import(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup(root);result=fitness.assess(root,"run",["src/service.py"]);activity=ledger.projection(root,"run")["activity"]
  self.assertFalse(result["complete"]);self.assertEqual(len(result["findings"]),2);self.assertEqual(activity["architecture_assessed"],1)
 def test_reports_unexpected_changed_path(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup(root);result=fitness.assess(root,"run",["other.py"])
  self.assertEqual(result["findings"][0]["category"],"scope")
