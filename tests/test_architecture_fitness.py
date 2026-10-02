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
 def js_setup(self,root,body):
  ledger.init_run(root,"jsrun","architecture");(root/"web").mkdir();(root/"web"/"app.js").write_text(body,encoding="utf-8");proposal=root/"proposal.json";proposal.write_text(json.dumps({"requirements":[{"statement":"keep store out of web","likely_paths":["web/app.js"],"acceptance_criteria":[],"preserve_rules":[],"evidence_plan":[],"architecture_contract":{"required_paths":[],"forbidden_imports":[{"source_prefix":"web","target_prefix":"store.db"}]}}]}),encoding="utf-8");anchor.draft(root,"jsrun",proposal);anchor.approve(root,"jsrun")
 def test_reports_forbidden_javascript_import(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.js_setup(root,"import db from 'store/db';\nconst lib=require('./lib');\n");result=fitness.assess(root,"jsrun",["web/app.js"])
  hits=[item for item in result["findings"] if item["category"]=="architecture" and item["classification"]=="new-drift"];self.assertEqual(len(hits),1);self.assertIn("store.db",hits[0]["message"])
 def test_ignores_commented_javascript_import(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.js_setup(root,"// const bad=require('store/db');\n/* import x from 'store/db'; */\nconst ok=require('./lib');\n");result=fitness.assess(root,"jsrun",["web/app.js"])
  self.assertEqual(result["findings"],[]);self.assertTrue(result["complete"])
 def test_typescript_dynamic_import_is_checked(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);ledger.init_run(root,"tsrun","architecture");(root/"web").mkdir();(root/"web"/"app.ts").write_text("const db=await import('../store/db');\n",encoding="utf-8");proposal=root/"proposal.json";proposal.write_text(json.dumps({"requirements":[{"statement":"keep store out of web","likely_paths":["web/app.ts"],"acceptance_criteria":[],"preserve_rules":[],"evidence_plan":[],"architecture_contract":{"required_paths":[],"forbidden_imports":[{"source_prefix":"web","target_prefix":"store.db"}]}}]}),encoding="utf-8");anchor.draft(root,"tsrun",proposal);anchor.approve(root,"tsrun");result=fitness.assess(root,"tsrun",["web/app.ts"])
  self.assertTrue(any(item["classification"]=="new-drift" and "store.db" in item["message"] for item in result["findings"]))
 def test_widened_dependency_manifests_drift(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);ledger.init_run(root,"deprun","architecture");proposal=root/"proposal.json";proposal.write_text(json.dumps({"requirements":[{"statement":"no new dependencies","likely_paths":[],"acceptance_criteria":[],"preserve_rules":[],"evidence_plan":[],"architecture_contract":{"required_paths":[],"protected_paths":[],"forbidden_imports":[],"no_new_dependencies":True}}]}),encoding="utf-8");anchor.draft(root,"deprun",proposal);anchor.approve(root,"deprun")
   for manifest in ["setup.py","setup.cfg","package-lock.json","pnpm-lock.yaml","Gemfile","go.sum","Package.swift","requirements-dev.txt"]:
    result=fitness.assess(root,"deprun",[manifest]);self.assertTrue(any(item["category"]=="dependency" and item["path"]==manifest for item in result["findings"]),manifest)
 def test_planning_contract_requires_graph_receipt_and_guards_dependency_boundary(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);ledger.init_run(root,"planned","architecture");(root/"src").mkdir();(root/"src"/"service.py").write_text("",encoding="utf-8")
   proposal=root/"proposal.json";proposal.write_text(json.dumps({"requirements":[{"statement":"map callers without a new dependency","likely_paths":["src/service.py","pyproject.toml"],"acceptance_criteria":[],"preserve_rules":[],"evidence_plan":[],"architecture_contract":{"required_paths":[],"protected_paths":[],"forbidden_imports":[],"requires_caller_map":True,"no_new_dependencies":True}}]}),encoding="utf-8")
   drafted=anchor.draft(root,"planned",proposal);anchor.approve(root,"planned")
   missing=fitness.assess(root,"planned",["src/service.py"])
   anchor.graph_receipt(root,"planned",[drafted["requirements"][0]["requirement_uid"]],["src/service.py"],"local-ast")
   preserved=fitness.assess(root,"planned",["src/service.py"])
   dependency_drift=fitness.assess(root,"planned",["src/service.py","pyproject.toml"])
  self.assertEqual(missing["state"],"unknown")
  self.assertTrue(preserved["complete"]);self.assertEqual(preserved["state"],"preserved")
  self.assertEqual(dependency_drift["state"],"drifted")
