#!/usr/bin/env python3
"""Create immutable program plans and explicit hands-free delivery state."""
from __future__ import annotations
import argparse,importlib.util,json
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
def ledger()->Any:
 s=importlib.util.spec_from_file_location("program_ledger",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
L=ledger()
def now()->str:return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def directory(root:Path,run_id:str)->Path:return L.state_dir(root,run_id)/"program"
def state_path(root:Path,run_id:str)->Path:return directory(root,run_id)/"state.json"
def read(path:Path)->dict[str,Any]:return json.loads(path.read_text(encoding="utf-8"))
def validate(plan:dict[str,Any])->list[dict[str,Any]]:
 features=plan.get("features",[]);ids=[]
 for item in features:
  if not isinstance(item,dict) or not isinstance(item.get("id"),str) or not item["id"]:raise ValueError("each feature needs an ID")
  ids.append(item["id"])
 if len(ids)!=len(set(ids)):raise ValueError("feature IDs must be unique")
 known=set(ids)
 for item in features:
  if not set(item.get("depends_on",[]))<=known:raise ValueError("feature dependency is unknown")
 # Kahn cycle check
 remaining={item["id"]:set(item.get("depends_on",[])) for item in features}
 while remaining:
  ready=[key for key,value in remaining.items() if not value]
  if not ready:raise ValueError("feature dependency graph contains a cycle")
  for key in ready:remaining.pop(key)
  for value in remaining.values():value.difference_update(ready)
 return features
def init(root:Path,run_id:str,plan_path:Path,hands_free:bool,approved:bool)->dict[str,Any]:
 if not hands_free:raise ValueError("Program Delivery requires explicit --hands-free activation")
 if not approved:raise ValueError("program init records approved program state; rerun with --approved")
 if state_path(root,run_id).exists():raise ValueError("program state already exists")
 plan=read(plan_path);features=validate(plan);payload={"schema_version":"1","type":"tailtrail-program-state","run_id":run_id,"goal":str(plan.get("goal","")),"activation":"hands-free","activation_reason":"explicit --hands-free","global_invariants":plan.get("global_invariants",[]),"integration_evidence":plan.get("integration_evidence",[]),"correction_budget":int(plan.get("correction_budget",2)),"corrections_used":0,"version":1,"features":[{"id":x["id"],"title":x.get("title",x["id"]),"depends_on":x.get("depends_on",[]),"requirements":x.get("requirements",[]),"state":"pending","checkpoints":[]} for x in features],"amendments":[],"created_at":now(),"boundary":"orchestrator coordinates approved feature state only; source edits, material amendments, and execution controls retain their own approval gates"};L.atomic_json(directory(root,run_id)/"approved-v1.json",plan);L.atomic_json(state_path(root,run_id),payload);L.append_event(root,run_id,"program_initialized",{"artifact":state_path(root,run_id).relative_to(L.state_dir(root,run_id)).as_posix(),"features":[x["id"] for x in features],"activation":"hands-free"});return payload
def amend(root:Path,run_id:str,plan_path:Path,reason:str,approved:bool)->dict[str,Any]:
 if not approved:raise ValueError("material program amendment requires --approved")
 state=read(state_path(root,run_id));plan=read(plan_path);validate(plan);version=state["version"]+1;L.atomic_json(directory(root,run_id)/f"approved-v{version}.json",plan);state["version"]=version;state["amendments"].append({"version":version,"reason":reason,"at":now()});L.atomic_json(state_path(root,run_id),state);L.append_event(root,run_id,"program_amended",{"version":version,"reason":reason});return state
def main()->int:
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest="action",required=True)
 for name in ("init","show","amend"):
  q=sub.add_parser(name);q.add_argument("--root",type=Path,default=Path.cwd());q.add_argument("--run-id",required=True)
  if name in {"init","amend"}:q.add_argument("--plan",type=Path,required=True);q.add_argument("--approved",action="store_true")
  if name=="init":q.add_argument("--hands-free",action="store_true")
  if name=="amend":q.add_argument("--reason",required=True)
 a=p.parse_args()
 try:r=init(a.root.resolve(),a.run_id,a.plan,a.hands_free,a.approved) if a.action=="init" else amend(a.root.resolve(),a.run_id,a.plan,a.reason,a.approved) if a.action=="amend" else read(state_path(a.root.resolve(),a.run_id));print(json.dumps(r,indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:print(f"Program plan error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
