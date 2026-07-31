#!/usr/bin/env python3
"""Gate completion on required evidence; unavailable higher tiers never become passes."""
from __future__ import annotations
import argparse,importlib.util,json
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
def ledger():
 s=importlib.util.spec_from_file_location("phase1_ledger_completion",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
L=ledger()
def gate(root:Path,run_id:str,receipts_path:Path,record:bool=True)->dict[str,Any]:
 anchor=json.loads((L.state_dir(root,run_id)/"anchors"/"approved-v1.json").read_text(encoding="utf-8"));raw=json.loads(receipts_path.read_text(encoding="utf-8"));receipts=raw.get("receipts",raw); findings=[]
 for row in anchor["requirements"]:
  contract=row.get("validation_contract",{"state":"required","tiers":["unit"]}); relevant=[x for x in receipts if x.get("requirement_uid")==row["requirement_uid"]]
  if contract["state"] in {"not-applicable","conditional"}:continue
  for tier in contract.get("tiers",[]):
   outcomes=[x.get("outcome") for x in relevant if x.get("tier")==tier]
   if "pass" not in outcomes: findings.append({"requirement_uid":row["requirement_uid"],"tier":tier,"state":"unavailable" if "unavailable" in outcomes else ("blocked" if "blocked" in outcomes else "insufficient"),"message":"required tier lacks passing evidence"})
 payload={"schema_version":"1","type":"tailtrail-requirement-completion-gate","run_id":run_id,"complete":not findings,"findings":findings,"rule":"missing, blocked, unavailable, or insufficient evidence is not a pass"}
 if record:
  directory=L.state_dir(root,run_id)/"completion-gates";directory.mkdir(parents=True,exist_ok=True);path=directory/f"gate-{len(list(directory.glob('*.json')))+1}.json";L.atomic_json(path,payload);L.append_event(root,run_id,"completion_gate",{"artifact":path.relative_to(root).as_posix(),"complete":payload["complete"],"findings":findings});payload["run_artifact"]=path.as_posix()
 return payload
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());p.add_argument("--run-id",required=True);p.add_argument("--receipts",type=Path,required=True);a=p.parse_args()
 try:print(json.dumps(gate(a.root.resolve(),a.run_id,a.receipts),indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:print(f"Requirement completion error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
