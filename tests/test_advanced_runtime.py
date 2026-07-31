from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[name]=m;s.loader.exec_module(m);return m
ledger=load("arledger","scripts/run-ledger.py");anchor=load("aranchor","scripts/change-intent-anchor.py");runtime=load("arruntime","scripts/advanced-runtime.py")
class AdvancedRuntimeTests(unittest.TestCase):
 def setup(self,root):
  ledger.init_run(root,"run","advanced");p=root/"p.json";p.write_text(json.dumps({"requirements":[{"statement":"x","likely_paths":[],"acceptance_criteria":[],"preserve_rules":[],"evidence_plan":[]}]}),encoding="utf-8");anchor.draft(root,"run",p);anchor.approve(root,"run")
 def write(self,root,name,data):p=root/name;p.write_text(json.dumps(data),encoding="utf-8");return p
 def test_graph_claims_and_live_eval_boundaries(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup(root);graph=runtime.graph(root,"run",self.write(root,"g.json",{"nodes":[{"id":"n","role":"navigator","depends_on":[]}]}));claims=runtime.claims(root,"run",self.write(root,"c.json",{"claims":[{"claim":"30% faster"}]}));
   with self.assertRaises(ValueError):runtime.live_eval(root,"run",self.write(root,"e.json",{"model":"x","model_result":"pass","artifact_path":"a"}),False)
  self.assertEqual(graph["execution"].split()[0],"opt-in");self.assertEqual(claims["findings"][0]["status"],"rejected")
 def test_cloud_runner_blocks_without_two_approvals(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup(root);result=runtime.cloud(root,"run",self.write(root,"cloud.json",{"commands":[{"id":"k","repository_owned":True,"command":[sys.executable,"-c","pass"]}]}),False,False)
  self.assertEqual(result["results"][0]["outcome"],"blocked")
if __name__=="__main__":unittest.main()
