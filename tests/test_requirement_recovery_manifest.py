from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[name]=m;s.loader.exec_module(m);return m
ledger=load("mode_b_test_ledger","scripts/run-ledger.py");anchor=load("mode_b_test_anchor","scripts/change-intent-anchor.py");mode_b=load("mode_b_test","scripts/requirement-recovery-manifest.py");diagnose=load("mode_b_diagnose","scripts/recovery-diagnostician.py")
class ModeBRecoveryTests(unittest.TestCase):
 def setup(self,root):
  ledger.init_run(root,"run","mode b");(root/"src").mkdir();(root/"src"/"service.py").write_text("value='req1'\n",encoding="utf-8");proposal=root/"proposal.json";proposal.write_text(json.dumps({"requirements":[{"statement":"req2","likely_paths":["src/service.py"],"acceptance_criteria":[],"preserve_rules":["keep req1"],"evidence_plan":[]}]}),encoding="utf-8");draft=anchor.draft(root,"run",proposal);anchor.approve(root,"run");return draft["requirements"][0]["requirement_uid"]
 def test_capture_covers_corrected_role_tagged_paths(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup(root)
   anchor.correct(root,"run",uid,["src/service.py",{"path":"src/extra.py","role":"implementation-owner"}],"extra scope")
   (root/"src"/"extra.py").write_text("value='req1'\n",encoding="utf-8")
   manifest=mode_b.capture(root,"run",uid,True)
   paths=sorted(x["path"] for x in manifest["files"])
   self.assertEqual(paths,["src/extra.py","src/service.py"])
 def test_exact_mode_b_restore_preserves_baseline(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup(root);mode_b.capture(root,"run",uid,True);(root/"src"/"service.py").write_text("value='broken req2'\n",encoding="utf-8");mode_b.seal(root,"run",uid,[],True);plan=mode_b.plan(root,"run",uid);mode_b.apply(root,"run",uid,True);content=(root/"src"/"service.py").read_text(encoding="utf-8")
  self.assertTrue(plan["safe_to_apply"]);self.assertEqual(content,"value='req1'\n")
 def test_mode_b_refuses_later_overlap(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup(root);mode_b.capture(root,"run",uid,True);(root/"src"/"service.py").write_text("value='agent'\n",encoding="utf-8");mode_b.seal(root,"run",uid,[],True);(root/"src"/"service.py").write_text("value='later user edit'\n",encoding="utf-8");plan=mode_b.plan(root,"run",uid)
  self.assertFalse(plan["safe_to_apply"]);self.assertEqual(plan["classification"],"overlap-after-seal")
 def test_diagnostician_requires_repeated_evidence(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup(root);one=root/"one.json";two=root/"two.json";one.write_text(json.dumps({"findings":[{"category":"architecture"}]}),encoding="utf-8");two.write_text(json.dumps({"findings":[{"category":"architecture"}]}),encoding="utf-8");result=diagnose.diagnose(root,"run",[one,two])
  self.assertEqual(result["repeated_categories"],["architecture"])
 def test_seal_before_capture_gives_clean_message(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup(root)
   with self.assertRaisesRegex(ValueError, "Mode B manifest must be captured before sealing"):
    mode_b.seal(root,"run",uid,[],True)
 def test_seal_before_capture_cli_hides_filesystem_path(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);uid=self.setup(root)
   import subprocess,sys
   result=subprocess.run([sys.executable,"scripts/requirement-recovery-manifest.py","seal","--root",root.as_posix(),"--run-id","run","--requirement-uid",uid,"--approved"],cwd=ROOT,text=True,capture_output=True,check=False)
   self.assertEqual(result.returncode,2)
   combined=result.stderr + result.stdout
   self.assertIn("Mode B manifest must be captured before sealing",combined)
   self.assertNotIn("Errno",combined)

if __name__=="__main__":unittest.main()
