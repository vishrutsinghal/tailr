#!/usr/bin/env python3
"""Compute next safe program action from deterministic program state."""
from __future__ import annotations
import argparse,importlib.util,json
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
def ledger()->Any:
 s=importlib.util.spec_from_file_location("orchestrator_ledger",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
L=ledger()
def state_path(root:Path,run:str)->Path:return L.state_dir(root,run)/"program"/"state.json"
def next_action(root:Path,run:str)->dict[str,Any]:
 state=json.loads(state_path(root,run).read_text(encoding="utf-8"));features=state["features"]
 if state["corrections_used"]>=state["correction_budget"]:action={"action":"replan","reason":"program correction budget exhausted","requires_approval":True}
 elif any(x["state"] in {"paused","failed"} for x in features):
  item=next(x for x in features if x["state"] in {"paused","failed"});action={"action":"replan","feature_id":item["id"],"reason":"feature has a material design gap or failure","requires_approval":True}
 elif all(x["state"]=="validated" for x in features):action={"action":"integration-checkpoint","reason":"all features validated; run declared integration evidence","requires_approval":False}
 else:
  ready=next((x for x in features if x["state"]=="pending" and all(next(y for y in features if y["id"]==dep)["state"]=="validated" for dep in x["depends_on"])),None)
  action={"action":"activate-feature","feature_id":ready["id"],"requirements":ready["requirements"],"reason":"dependencies validated and feature is next in approved program order","requires_approval":False} if ready else {"action":"wait","reason":"no dependency-safe feature is ready","requires_approval":False}
 payload={"schema_version":"1","type":"tailtrail-delivery-next-action","run_id":run,"activation":state["activation"],"program_version":state["version"],"action":action,"boundary":"orchestrator returns a next action only; it does not edit source, run controls, or bypass feature/material approval"};folder=L.state_dir(root,run)/"program"/"orchestration";out=folder/f"next-{len(list(folder.glob('next-*.json')))+1}.json";L.atomic_json(out,payload);L.append_event(root,run,"program_orchestrated",{"artifact":out.relative_to(L.state_dir(root,run)).as_posix(),"action":action["action"],"feature_id":action.get("feature_id")});return payload
def correction(root:Path,run:str)->dict[str,Any]:
 state=json.loads(state_path(root,run).read_text(encoding="utf-8"));state["corrections_used"]+=1;L.atomic_json(state_path(root,run),state);L.append_event(root,run,"program_correction_recorded",{"corrections_used":state["corrections_used"],"correction_budget":state["correction_budget"]});return state
def main()->int:
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest="action",required=True)
 for n in ("next","correction"):x=sub.add_parser(n);x.add_argument("--root",type=Path,default=Path.cwd());x.add_argument("--run-id",required=True)
 a=p.parse_args()
 try:r=next_action(a.root.resolve(),a.run_id) if a.action=="next" else correction(a.root.resolve(),a.run_id);print(json.dumps(r,indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:print(f"Delivery orchestrator error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
