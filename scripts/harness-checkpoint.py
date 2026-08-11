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
def read(path:Path)->dict[str,Any]: return json.loads(path.read_text(encoding="utf-8"))
def fingerprint(path:Path)->str: return "sha256:"+hashlib.sha256(path.read_bytes()).hexdigest()
def checkpoint(root:Path,run_id:str,changed:list[str],results_path:Path)->dict[str,Any]:
 directory=L.state_dir(root,run_id); anchor=read(directory/"anchors"/"approved-v1.json"); results=read(results_path).get("results",[])
 existing=sorted((directory/"checkpoints").glob("checkpoint-*.json")); number=len(existing)+1
 req=[]
 for row in anchor["requirements"]:
  uid=row["requirement_uid"]
  evidence=[item for item in results if not item.get("requirement_uids") or uid in item.get("requirement_uids",[])]
  failed=not evidence or any(item.get("outcome") not in {"pass","skipped"} for item in evidence)
  req.append({"requirement_uid":uid,"statement":row["statement"],"state":"implemented-not-validated" if failed else "validated","evidence":evidence})
 prior=read(existing[-1]) if existing else None
 current_states={item["requirement_uid"]:item["state"] for item in req}; prior_states={item["requirement_uid"]:item["state"] for item in prior.get("requirements",[])} if prior else {}
 drift=[]
 for uid,state in current_states.items():
  old=prior_states.get(uid); kind="resolved" if state=="validated" and old!="validated" else ("regressed" if old=="validated" and state!="validated" else "unchanged")
  drift.append({"requirement_uid":uid,"category":"evidence","classification":kind})
 payload={"schema_version":"1","type":"tailtrail-harness-checkpoint","run_id":run_id,"checkpoint":number,"anchor_fingerprint":anchor["approved_fingerprint"],"changed_paths":[{"path":p,"fingerprint":fingerprint(root/p) if (root/p).is_file() else "missing"} for p in changed],"requirements":req,"control_results":results,"drift":drift}
 out=directory/"checkpoints"/f"checkpoint-{number}.json"; L.atomic_json(out,payload); L.append_event(root,run_id,"harness_checkpoint",{"artifact":out.relative_to(root).as_posix(),"checkpoint":number,"requirement_states":current_states,"drift":drift}); return {"path":out.as_posix(),**payload}
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());p.add_argument("--run-id",required=True);p.add_argument("--changed",action="append",default=[]);p.add_argument("--results",type=Path,required=True);a=p.parse_args()
 try: print(json.dumps(checkpoint(a.root.resolve(),a.run_id,a.changed,a.results),indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e: print(f"Harness checkpoint error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
