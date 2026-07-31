from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[name]=m;s.loader.exec_module(m);return m
ledger=load("v234_ledger","scripts/run-ledger.py");anchor=load("v234_anchor","scripts/change-intent-anchor.py");impact=load("v234_impact","scripts/requirement-impact-map.py");convergence=load("v234_convergence","scripts/harness-convergence.py");template=load("v234_template","scripts/harness-template.py")
class RequirementHarnessV2V4Tests(unittest.TestCase):
 def setup_run(self,root):
  ledger.init_run(root,"run","validation")
  proposal=root/"proposal.json";proposal.write_text(json.dumps({"requirements":[{"statement":"Reject zero","acceptance_criteria":["raises"],"preserve_rules":["positive valid"],"likely_paths":["src/a.py"],"evidence_plan":["unit"],"validation_contract":{"state":"required","tiers":["unit"]},"architecture_contract":{"required_paths":["src/a.py"],"protected_paths":[],"forbidden_imports":[]},"behavior_contract":{"scenarios":["submit claim"]}}]}),encoding="utf-8")
  anchor.draft(root,"run",proposal);approved=anchor.approve(root,"run");(root/"src").mkdir();(root/"tests").mkdir();(root/"src/a.py").write_text("def validate(): pass\n",encoding="utf-8");(root/"src/caller.py").write_text("from a import validate\nvalidate()\n",encoding="utf-8");(root/"tests/test_a.py").write_text("from a import validate\nvalidate()\n",encoding="utf-8");return approved["requirements"][0]["requirement_uid"]
 def test_impact_mapping_links_symbols_callers_and_tests(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup_run(root);result=impact.map_impact(root,"run",["src/a.py"])
  row=result["requirements"][0];self.assertEqual(row["symbols"][0]["symbols"],["validate"]);self.assertTrue(row["callers"]);self.assertTrue(row["tests"]);self.assertIn("architecture-fitness",row["selected_controls"])
 def test_convergence_is_bounded_and_routes_to_replan(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup_run(root);first=convergence.assess(root,"run",uid,"unchanged",2);second=convergence.assess(root,"run",uid,"unchanged",2)
  self.assertEqual(first["action"],"bounded-correction");self.assertEqual(second["action"],"replan");self.assertTrue(second["requires_approval"])
 def test_template_adds_but_cannot_remove_required_tier(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup_run(root);path=root/"templates.json";path.write_text(json.dumps({"templates":[{"id":"service","kinds":["change"],"path_prefixes":["src"],"controls":["architecture-fitness"],"required_tiers":["integration"]}]}),encoding="utf-8");result=template.select(root,"run",uid,path)
  self.assertEqual(result["controls"],["architecture-fitness"]);self.assertEqual(result["required_tiers"],["integration","unit"])
if __name__=="__main__":unittest.main()
