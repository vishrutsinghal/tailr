from __future__ import annotations
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[name]=m;s.loader.exec_module(m);return m
ledger=load("checkpoint_ledger","scripts/run-ledger.py");anchor=load("checkpoint_anchor","scripts/change-intent-anchor.py");checkpoint=load("checkpoint_module","scripts/harness-checkpoint.py");review=load("completion_review_module","scripts/completion-review.py");mapper=load("checkpoint_mapper","scripts/code-graph-mapper.py")
class HarnessCheckpointTests(unittest.TestCase):
 def setup_run(self,root):
  ledger.init_run(root,"run", "validation");proposal=root/"proposal.json";proposal.write_text(json.dumps({"requirements":[{"statement":"Reject zero","acceptance_criteria":["raises"],"preserve_rules":["positive valid"],"likely_paths":["src/a.py"],"evidence_plan":["unit"]}]}),encoding="utf-8");anchor.draft(root,"run",proposal);anchor.approve(root,"run");(root/"src").mkdir();(root/"src/a.py").write_text("x",encoding="utf-8")
 def test_checkpoint_marks_passing_requirement_validated(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup_run(root);results=root/"results.json";results.write_text(json.dumps({"results":[{"control_id":"unit","outcome":"pass","tier":"unit","tiers":["unit"],"evidence_quality":"trusted"}]}),encoding="utf-8");actual=checkpoint.checkpoint(root,"run",["src/a.py"],results);out=review.review(root,"run")
   self.assertEqual(actual["requirements"][0]["state"],"validated");self.assertTrue(out["complete"])
   activity=ledger.projection(root,"run")["activity"]
   self.assertEqual(activity["harness_checkpoint"],1)
   self.assertEqual(activity["completion_review"],1)
 def test_checkpoint_failure_produces_evidence_gap(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup_run(root);results=root/"results.json";results.write_text(json.dumps({"results":[{"control_id":"unit","outcome":"fail","tier":"unit","tiers":["unit"],"evidence_quality":"trusted"}]}),encoding="utf-8");checkpoint.checkpoint(root,"run",["src/a.py"],results);out=review.review(root,"run")
  self.assertFalse(out["complete"]);self.assertEqual(out["findings"][0]["category"],"evidence")
 def test_explicitly_proposed_proof_addition_is_approved_edit_scope(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);ledger.init_run(root,"run","ui change");proposal=root/"proposal.json"
   proposal.write_text(json.dumps({"requirements":[{"statement":"Advance after validation","acceptance_criteria":["page advances"],"preserve_rules":["failure stays put"],"likely_paths":["src/Page.tsx"],"evidence_plan":["component"],"validation_contract":{"state":"required","tiers":["component"],"candidate_paths":["src/Page.cy.tsx"],"proposed_paths":["src/Page.cy.tsx"],"commands":["npm run cypress:component -- --spec src/Page.cy.tsx"]}}]}),encoding="utf-8")
   anchor.draft(root,"run",proposal);anchor.approve(root,"run");(root/"src").mkdir();(root/"src/Page.tsx").write_text("page",encoding="utf-8");(root/"src/Page.cy.tsx").write_text("proof",encoding="utf-8")
   results=root/"results.json";results.write_text(json.dumps({"results":[{"control_id":"component","outcome":"pass"}]}),encoding="utf-8")
   actual=checkpoint.checkpoint(root,"run",["src/Page.tsx","src/Page.cy.tsx"],results)
  self.assertEqual(actual["scope_assessment"]["status"],"within-approved-scope")
  self.assertEqual(actual["scope_assessment"]["unexpected_paths"],[])
 def test_mid_run_correction_is_visible_to_checkpoint(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup_run(root)
   uid=json.loads((root/".tailtrail"/"runs"/"run"/"anchors"/"approved-v1.json").read_text(encoding="utf-8"))["requirements"][0]["requirement_uid"]
   anchor.correct(root,"run",uid,["src/a.py",{"path":"src/b.py","role":"proof-only"}],"test file needed mid-run")
   (root/"src/b.py").write_text("y",encoding="utf-8")
   results=root/"results.json";results.write_text(json.dumps({"results":[{"control_id":"unit","outcome":"pass","tier":"unit","tiers":["unit"],"evidence_quality":"trusted"}]}),encoding="utf-8")
   actual=checkpoint.checkpoint(root,"run",["src/a.py","src/b.py"],results)
   self.assertEqual(actual["scope_assessment"]["status"],"within-approved-scope")
   self.assertEqual(actual["scope_assessment"]["unexpected_paths"],[])
  def test_existing_requirement_linked_proof_is_approved_validation_scope(self):
    with tempfile.TemporaryDirectory() as temp:
     root=Path(temp);ledger.init_run(root,"run","ui change");proposal=root/"proposal.json"
     proposal.write_text(json.dumps({"requirements":[{"statement":"Hide one banner","acceptance_criteria":["banner absent"],"preserve_rules":["other errors visible"],"likely_paths":["src/Page.tsx"],"evidence_plan":["component"],"validation_contract":{"state":"required","tiers":["component"],"candidate_paths":["src/Page.cy.tsx"],"proposed_paths":[],"editable_paths":["src/Page.cy.tsx"],"commands":["npm run component"]}}]}),encoding="utf-8")
     anchor.draft(root,"run",proposal);anchor.approve(root,"run");(root/"src").mkdir();(root/"src/Page.tsx").write_text("page",encoding="utf-8");(root/"src/Page.cy.tsx").write_text("proof",encoding="utf-8")
     results=root/"results.json";results.write_text(json.dumps({"results":[{"control_id":"component","outcome":"pass"}]}),encoding="utf-8")
     actual=checkpoint.checkpoint(root,"run",["src/Page.tsx","src/Page.cy.tsx"],results)
    self.assertEqual(actual["scope_assessment"]["status"],"within-approved-scope")
    self.assertEqual(actual["scope_assessment"]["approved_editable_paths"],["src/Page.cy.tsx","src/Page.tsx"])
class VcsVerificationTests(unittest.TestCase):
  def git_repo(self,root):
   import subprocess
   subprocess.run(["git","init"],cwd=root,check=True,capture_output=True)
   subprocess.run(["git","config","user.email","t@t"],cwd=root,check=True,capture_output=True)
   subprocess.run(["git","config","user.name","t"],cwd=root,check=True,capture_output=True)
  def test_vcs_state_reports_modified_and_untracked(self):
   with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);self.git_repo(root)
    (root/"a.py").write_text("1",encoding="utf-8");(root/"b.py").write_text("1",encoding="utf-8")
    import subprocess;subprocess.run(["git","add","."],cwd=root,check=True,capture_output=True);subprocess.run(["git","commit","-m","x"],cwd=root,check=True,capture_output=True)
    (root/"a.py").write_text("2",encoding="utf-8");(root/"c.py").write_text("new",encoding="utf-8")
    state=checkpoint.vcs_state(root)
    self.assertTrue(state["available"]);self.assertIn("a.py",state["modified"]);self.assertIn("c.py",state["untracked"]);self.assertNotIn("b.py",state["modified"])
  def test_verify_changed_path_marks_phantom_unverified(self):
   with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);self.git_repo(root)
    (root/"a.py").write_text("1",encoding="utf-8");(root/"b.py").write_text("1",encoding="utf-8")
    import subprocess;subprocess.run(["git","add","."],cwd=root,check=True,capture_output=True);subprocess.run(["git","commit","-m","x"],cwd=root,check=True,capture_output=True)
    (root/"a.py").write_text("2",encoding="utf-8")
    state=checkpoint.vcs_state(root)
    self.assertTrue(checkpoint.verify_changed_path(root,"a.py",state)["verified"])
    self.assertFalse(checkpoint.verify_changed_path(root,"b.py",state)["verified"])
    self.assertEqual(checkpoint.verify_changed_path(root,"b.py",state)["vcs_status"],"clean")
    self.assertEqual(checkpoint.verify_changed_path(root,"nope.py",state)["vcs_status"],"missing")
  def test_non_git_repo_reports_unavailable(self):
   with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);(root/"a.py").write_text("1",encoding="utf-8")
    state=checkpoint.vcs_state(root)
    self.assertFalse(state["available"])
    self.assertEqual(checkpoint.verify_changed_path(root,"a.py",state)["vcs_status"],"unavailable")
  def test_checkpoint_flags_phantom_claim_as_drift(self):
   with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);self.git_repo(root)
    ledger.init_run(root,"run","validation");proposal=root/"proposal.json";proposal.write_text(json.dumps({"requirements":[{"statement":"Reject zero","acceptance_criteria":["raises"],"preserve_rules":["positive valid"],"likely_paths":["src/a.py"],"evidence_plan":["unit"]}]}),encoding="utf-8");anchor.draft(root,"run",proposal);anchor.approve(root,"run")
    (root/"src").mkdir();(root/"src/a.py").write_text("x",encoding="utf-8");(root/"src/b.py").write_text("y",encoding="utf-8")
    import subprocess;subprocess.run(["git","add","."],cwd=root,check=True,capture_output=True);subprocess.run(["git","commit","-m","x"],cwd=root,check=True,capture_output=True)
    (root/"src/a.py").write_text("xx",encoding="utf-8")
    results=root/"results.json";results.write_text(json.dumps({"results":[{"control_id":"unit","outcome":"pass","tier":"unit","tiers":["unit"],"evidence_quality":"trusted"}]}),encoding="utf-8")
    actual=checkpoint.checkpoint(root,"run",["src/a.py","src/b.py"],results)
    by_path={item["path"]:item for item in actual["changed_paths"]}
    self.assertTrue(by_path["src/a.py"]["verified"]);self.assertFalse(by_path["src/b.py"]["verified"])
    self.assertIn("src/b.py",actual["scope_assessment"]["unverified_paths"])
    self.assertTrue(any(row.get("classification")=="unverified-change" and row.get("path")=="src/b.py" for row in actual["drift"]))
  def test_checkpoint_refreshes_verified_slices(self):
   with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);import subprocess
    subprocess.run(["git","init"],cwd=root,check=True,capture_output=True);subprocess.run(["git","config","user.email","t@t"],cwd=root,check=True,capture_output=True);subprocess.run(["git","config","user.name","t"],cwd=root,check=True,capture_output=True)
    ledger.init_run(root,"run","validation");proposal=root/"proposal.json";proposal.write_text(json.dumps({"requirements":[{"statement":"Reject zero","acceptance_criteria":["raises"],"preserve_rules":["positive valid"],"likely_paths":["src/a.py"],"evidence_plan":["unit"]}]}),encoding="utf-8");anchor.draft(root,"run",proposal);anchor.approve(root,"run")
    (root/"src").mkdir();(root/"src/a.py").write_text("def build():\n return 1\n",encoding="utf-8")
    subprocess.run(["git","add","."],cwd=root,check=True,capture_output=True);subprocess.run(["git","commit","-m","x"],cwd=root,check=True,capture_output=True)
    (root/"src/a.py").write_text("def build():\n return 2\n",encoding="utf-8")
    results=root/"results.json";results.write_text(json.dumps({"results":[{"control_id":"unit","outcome":"pass","tier":"unit","tiers":["unit"],"evidence_quality":"trusted"}]}),encoding="utf-8")
    actual=checkpoint.checkpoint(root,"run",["src/a.py"],results)
    self.assertIn(actual["graph_refresh"]["status"],{"refreshed","refresh-unavailable"})
    refreshed=set(actual["graph_refresh"].get("refreshed",[]))
    verified={item["path"] for item in actual["changed_paths"] if item.get("verified")}
    self.assertTrue(refreshed or verified=={"src/a.py"})
class FreshnessProofTests(unittest.TestCase):
  def test_post_checkpoint_slices_read_fresh_with_new_content(self):
   with tempfile.TemporaryDirectory() as temp:
    import subprocess
    root=Path(temp)
    subprocess.run(["git","init"],cwd=root,check=True,capture_output=True);subprocess.run(["git","config","user.email","t@t"],cwd=root,check=True,capture_output=True);subprocess.run(["git","config","user.name","t"],cwd=root,check=True,capture_output=True)
    ledger.init_run(root,"run","validation");proposal=root/"proposal.json";proposal.write_text(json.dumps({"requirements":[{"statement":"Reject zero","acceptance_criteria":["raises"],"preserve_rules":["positive valid"],"likely_paths":["src/a.py"],"evidence_plan":["unit"]}]}),encoding="utf-8");anchor.draft(root,"run",proposal);anchor.approve(root,"run")
    (root/"src").mkdir();(root/"src/a.py").write_text("def old_fn():\n return 1\n",encoding="utf-8")
    subprocess.run(["git","add","."],cwd=root,check=True,capture_output=True);subprocess.run(["git","commit","-m","x"],cwd=root,check=True,capture_output=True)
    (root/"src/a.py").write_text("def new_fn():\n return 2\n",encoding="utf-8")
    results=root/"results.json";results.write_text(json.dumps({"results":[{"control_id":"unit","outcome":"pass","tier":"unit","tiers":["unit"],"evidence_quality":"trusted"}]}),encoding="utf-8")
    actual=checkpoint.checkpoint(root,"run",["src/a.py"],results)
    self.assertEqual(actual["graph_refresh"]["status"],"refreshed")
    cache=root/"tailtrail-meta"/"code-graph-cache.json"
    summaries=mapper.expand_finalist_slices(root,["src/a.py"],cache_override=cache)
    self.assertEqual(summaries["src/a.py"]["status"],"fresh")
    self.assertIn("new_fn",[item["name"] for item in summaries["src/a.py"]["symbols"]])
    self.assertNotIn("old_fn",[item["name"] for item in summaries["src/a.py"]["symbols"]])
