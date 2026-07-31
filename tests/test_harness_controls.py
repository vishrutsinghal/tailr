from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[name]=m;s.loader.exec_module(m);return m
controls=load("harness_controls_test","scripts/harness-controls.py")
class HarnessControlsTests(unittest.TestCase):
 def test_plan_selects_only_impacted_scope(self):
  source=[{"id":"unit","command":[sys.executable,"-c","pass"],"scope":"src/","timeout_seconds":5,"severity":"blocking","evidence_label":"local-command","requires_approval":True}]
  self.assertEqual(controls.plan(source,["src/app.py"])["selected_controls"][0]["id"],"unit")
  self.assertEqual(controls.plan(source,["docs/a.md"])["skipped_controls"][0]["id"],"unit")
 def test_run_captures_exact_failure(self):
  source=[{"id":"fail","command":[sys.executable,"-c","raise SystemExit(2)"],"scope":"src/","timeout_seconds":5,"severity":"blocking","evidence_label":"local-command","requires_approval":True}]
  with tempfile.TemporaryDirectory() as temp: result=controls.run(source,Path(temp),["src/app.py"])
  self.assertEqual(result["results"][0]["outcome"],"fail")
