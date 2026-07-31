from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[name]=m;s.loader.exec_module(m);return m
profile=load("testing_profile_test","scripts/testing-profile.py")
class TestingProfileTests(unittest.TestCase):
 def test_profile_lists_declared_tier(self):
  with tempfile.TemporaryDirectory() as temp:
   file=Path(temp)/"profile.json";file.write_text(json.dumps({"tiers":[{"name":"unit","command":["python","-m","unittest"],"environment":"local","requires_approval":True,"prerequisites":[],"cleanup":[]}]}),encoding="utf-8");result=profile.load(file)
  self.assertEqual(result["tiers"][0]["name"],"unit")
