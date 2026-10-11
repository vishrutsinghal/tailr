#!/usr/bin/env python3
"""Persist actual requirement state and classify checkpoint deltas."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
def ledger():
 spec=importlib.util.spec_from_file_location("phase1_ledger",ROOT/"scripts"/"run-ledger.py"); m=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(m); return m
L=ledger()
def anchor_module():
 """Load change-intent-anchor.py (hyphenated filename needs a spec loader)."""
 spec=importlib.util.spec_from_file_location("checkpoint_change_intent_anchor",ROOT/"scripts"/"change-intent-anchor.py")
 if spec is None or spec.loader is None: raise RuntimeError("unable to load scripts/change-intent-anchor.py")
 import sys as _sys; module=importlib.util.module_from_spec(spec); _sys.modules[spec.name]=module; spec.loader.exec_module(module); return module
A=anchor_module()
def _anchor_path(value):
 """Extract a path from a plain-string or {path, role} anchor entry."""
 if isinstance(value,str): return value.strip() or None
 if isinstance(value,dict):
  path=value.get("path"); return str(path).strip() or None if isinstance(path,str) else None
 return None
def read(path:Path)->dict[str,Any]: return json.loads(path.read_text(encoding="utf-8"))
def fingerprint(path:Path)->str: return "sha256:"+hashlib.sha256(path.read_bytes()).hexdigest()
def vcs_state(root:Path)->dict[str,Any]:
 """Classify working-tree modifications; never raises.

 Returns {"available": bool, "modified": set, "untracked": set}. A path is a
 verified change when modified/staged (in git diff) or untracked (created by
 the run). Tracked-but-clean paths fail verification: claimed but
 unmodified. Non-git repositories report unavailable instead of faking it.
 """
 import subprocess
 try:
  diff=subprocess.run(["git","diff","--name-only","HEAD"],cwd=root,text=True,capture_output=True,check=False,timeout=60)
  untracked=subprocess.run(["git","ls-files","--others","--exclude-standard"],cwd=root,text=True,capture_output=True,check=False,timeout=60)
 except (OSError, ValueError, subprocess.SubprocessError):
  return {"available":False,"modified":set(),"untracked":set()}
 if diff.returncode!=0 or untracked.returncode!=0:
  return {"available":False,"modified":set(),"untracked":set()}
 norm=lambda line: line.strip().replace("\\","/")
 return {"available":True,
         "modified":{norm(line) for line in diff.stdout.splitlines() if norm(line)},
         "untracked":{norm(line) for line in untracked.stdout.splitlines() if norm(line)}}
def verify_changed_path(root:Path,path:str,state:dict[str,Any])->dict[str,Any]:
 """Verify one asserted path against live VCS state (pure assessment)."""
 rel=str(path).replace("\\","/")
 target=root/rel
 if not target.is_file():
  return {"verified":False,"vcs_status":"missing"}
 if not state.get("available"):
  return {"verified":False,"vcs_status":"unavailable"}
 if rel in state.get("untracked",set()):
  return {"verified":True,"vcs_status":"untracked"}
 if rel in state.get("modified",set()):
  return {"verified":True,"vcs_status":"modified"}
 return {"verified":False,"vcs_status":"clean"}
def checkpoint(root:Path,run_id:str,changed:list[str],results_path:Path)->dict[str,Any]:
 directory=L.state_dir(root,run_id)
 # Latest approved anchor, never the frozen v1 file (v1 == latest when never corrected).
 _,anchor=A.latest_approved(root,run_id); results=read(results_path).get("results",[])
 existing=sorted((directory/"checkpoints").glob("checkpoint-*.json")); number=len(existing)+1
 req=[]
 for row in anchor["requirements"]:
  uid=row["requirement_uid"]
  evidence=[item for item in results if not item.get("requirement_uids") or uid in item.get("requirement_uids",[])]
  authoritative=[item for item in evidence if item.get("evidence_quality") in {"trusted","attested"}]
  required_tiers=set((row.get("validation_contract") or {}).get("tiers",[]))
  passed_tiers={tier for item in authoritative if item.get("outcome")=="pass" for tier in item.get("tiers",[item.get("tier")]) if tier}
  nonpassing=any(item.get("outcome") in {"fail","blocked","timed-out","unavailable"} for item in evidence)
  validated=bool(authoritative) and not nonpassing and required_tiers.issubset(passed_tiers)
  likely={_anchor_path(path) for path in row.get("likely_paths",[])}; likely.discard(None)
  implemented=bool(set(changed)&likely)
  req.append({
   "requirement_uid":uid,"statement":row["statement"],
   "state":"validated" if validated else ("implemented-unverified" if implemented else "not-evidenced"),
   "implementation_state":"implemented" if implemented else "not-evidenced",
   "verification_state":"pass" if validated else ("fail" if nonpassing else "not-evidenced"),
   "required_tiers":sorted(required_tiers),"passed_tiers":sorted(passed_tiers),"evidence":evidence,
  })
 prior=read(existing[-1]) if existing else None
 current_states={item["requirement_uid"]:item["state"] for item in req}; prior_states={item["requirement_uid"]:item["state"] for item in prior.get("requirements",[])} if prior else {}
 drift=[]
 for uid,state in current_states.items():
  old=prior_states.get(uid); kind="resolved" if state=="validated" and old!="validated" else ("regressed" if old=="validated" and state!="validated" else "unchanged")
  drift.append({"requirement_uid":uid,"category":"evidence","classification":kind})
 approved_implementation={_anchor_path(path) for row in anchor["requirements"] for path in row.get("likely_paths",[])}; approved_implementation.discard(None)
 approved_proof={_anchor_path(path) for row in anchor["requirements"] for path in ((row.get("validation_contract",{}) or {}).get("editable_paths",[]))}|{_anchor_path(path) for row in anchor["requirements"] for path in ((row.get("validation_contract",{}) or {}).get("proposed_paths",[]))}; approved_proof.discard(None)
 approved_editable=sorted(approved_implementation|approved_proof)
 unexpected=sorted(set(changed)-set(approved_editable))
 drift.extend({"requirement_uid":anchor["requirements"][0]["requirement_uid"],"category":"scope","classification":"new-drift","path":path,"message":f"actual edit `{path}` is outside approved editable scope"} for path in unexpected)
 vcs=vcs_state(root)
 verified_paths=[{"path":p,"fingerprint":fingerprint(root/p) if (root/p).is_file() else "missing",**verify_changed_path(root,p,vcs)} for p in changed]
 unverified=sorted(item["path"] for item in verified_paths if not item["verified"] and item["vcs_status"] not in {"unavailable","missing"})
 drift.extend({"requirement_uid":anchor["requirements"][0]["requirement_uid"],"category":"scope","classification":"unverified-change","path":path,"message":f"claimed edit `{path}` shows no VCS modification"} for path in unverified)
 scope_assessment={"status":"unresolved" if unexpected else "within-approved-scope","approved_editable_paths":approved_editable,"actual_changed_paths":sorted(set(changed)),"unexpected_paths":unexpected,"unverified_paths":unverified,"vcs_available":bool(vcs.get("available")),"boundary":"Implementation owners are editable for approved source work. Requirement-linked validation paths named by the approved validation contract are editable only for proof assertions; inspection-only paths remain read-only."}
 payload={"schema_version":"1","type":"tailtrail-harness-checkpoint","run_id":run_id,"checkpoint":number,"anchor_fingerprint":anchor["approved_fingerprint"],"changed_paths":verified_paths,"requirements":req,"control_results":results,"scope_assessment":scope_assessment,"drift":drift}
 out=directory/"checkpoints"/f"checkpoint-{number}.json"; L.atomic_json(out,payload); L.append_event(root,run_id,"harness_checkpoint",{"artifact":out.relative_to(root).as_posix(),"checkpoint":number,"requirement_states":current_states,"drift":drift}); refresh=refresh_verified_slices(root,[item for item in verified_paths if item.get("verified")]); return {"path":out.as_posix(),"graph_refresh":refresh,**payload}
def refresh_verified_slices(root:Path,verified_paths:list[dict[str,Any]])->dict[str,Any]:
 """Refresh graph slices for VCS-verified changed paths (best-effort).

 Only paths the checkpoint verified (modified/untracked, never phantoms)
 reach expansion, so unverified claims cannot pollute the graph. Any
 failure — missing mapper, expansion error, persistence error — is
 swallowed into the returned status: refresh is advisory to closure,
 never a gate. Returns {"status": ...} with refreshed/deferred counts.
 """
 paths=[str(item.get("path","")) for item in verified_paths or [] if isinstance(item,dict) and str(item.get("path","")).strip() and bool(item.get("verified"))]
 if not paths:
  return {"status":"nothing-to-refresh","refreshed":[],"deferred":[]}
 try:
  import importlib.util as _ilu
  spec=_ilu.spec_from_file_location("tailtrail_checkpoint_slice_mapper",ROOT/"scripts"/"code-graph-mapper.py")
  if spec is None or spec.loader is None: raise RuntimeError("mapper unavailable")
  module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
  summaries=module.expand_finalist_slices(root,paths)
 except Exception as error:
  return {"status":"refresh-unavailable","error":f"{type(error).__name__}: {error}","refreshed":[],"deferred":sorted(set(paths))}
 refreshed=sorted(path for path,summary in summaries.items() if isinstance(summary,dict) and summary.get("status") in {"fresh","expanded"})
 return {"status":"refreshed","refreshed":refreshed,"deferred":sorted(set(paths)-set(refreshed))}
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());p.add_argument("--run-id",required=True);p.add_argument("--changed",action="append",default=[]);p.add_argument("--results",type=Path,required=True);a=p.parse_args()
 try: print(json.dumps(checkpoint(a.root.resolve(),a.run_id,a.changed,a.results),indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e: print(f"Harness checkpoint error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
