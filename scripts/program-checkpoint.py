#!/usr/bin/env python3
"""Append feature-level actual state without overwriting program history."""
from __future__ import annotations
import argparse,importlib.util,json
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
def ledger()->Any:
 s=importlib.util.spec_from_file_location("program_checkpoint_ledger",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
L=ledger()
def path(root:Path,run:str)->Path:return L.state_dir(root,run)/"program"/"state.json"
def checkpoint(root:Path,run:str,feature_id:str,state:str,evidence:list[str],reason:str="")->dict[str,Any]:
 data=json.loads(path(root,run).read_text(encoding="utf-8"));feature=next((x for x in data["features"] if x["id"]==feature_id),None)
 if not feature:raise ValueError("feature ID is unknown")
 if state=="active" and any(next(x for x in data["features"] if x["id"]==dep)["state"]!="validated" for dep in feature["depends_on"]):raise ValueError("feature dependencies are not validated")
 if state not in {"active","validated","paused","failed"}:raise ValueError("invalid feature state")
 record={"number":len(feature["checkpoints"])+1,"state":state,"evidence":evidence,"reason":reason,"at":datetime.now(timezone.utc).replace(microsecond=0).isoformat()};feature["state"]=state;feature["checkpoints"].append(record);L.atomic_json(path(root,run),data);L.append_event(root,run,"program_checkpointed",{"feature_id":feature_id,**record});return data
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());p.add_argument("--run-id",required=True);p.add_argument("--feature",required=True);p.add_argument("--state",required=True);p.add_argument("--evidence",action="append",default=[]);p.add_argument("--reason",default="");a=p.parse_args()
 try:print(json.dumps(checkpoint(a.root.resolve(),a.run_id,a.feature,a.state,a.evidence,a.reason),indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:print(f"Program checkpoint error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
