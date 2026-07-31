#!/usr/bin/env python3
"""Compare an approved anchor to one actual checkpoint without claiming success."""
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
def ledger():
 spec=importlib.util.spec_from_file_location("phase1_ledger_review",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(m);return m
L=ledger()
def read(path:Path)->dict[str,Any]:return json.loads(path.read_text(encoding="utf-8"))
def review(root:Path,run_id:str,checkpoint_path:Path|None=None,record:bool=True)->dict[str,Any]:
 directory=L.state_dir(root,run_id); anchor=read(directory/"anchors"/"approved-v1.json")
 if checkpoint_path is None:
  files=sorted((directory/"checkpoints").glob("checkpoint-*.json"))
  if not files: raise ValueError("no checkpoint exists")
  checkpoint_path=files[-1]
 checkpoint=read(checkpoint_path); actual={row["requirement_uid"]:row for row in checkpoint["requirements"]}; findings=[]
 for requirement in anchor["requirements"]:
  observed=actual.get(requirement["requirement_uid"])
  if not observed: findings.append({"requirement_uid":requirement["requirement_uid"],"category":"scope","classification":"new-drift","message":"approved requirement is absent from actual checkpoint"});continue
  if observed["state"]!="validated": findings.append({"requirement_uid":requirement["requirement_uid"],"category":"evidence","classification":"needs-decision" if not observed["evidence"] else "unchanged","message":"requirement lacks passing computational evidence"})
 payload={"schema_version":"1","type":"tailtrail-completion-review","run_id":run_id,"checkpoint":checkpoint["checkpoint"],"complete":not findings,"findings":findings,"next_action":"none" if not findings else "issue one bounded correction packet"}
 if record:
  reviews=directory/"reviews"; index=len(list(reviews.glob("review-*.json")))+1; artifact=reviews/f"review-{index}.json";L.atomic_json(artifact,payload)
  L.append_event(root,run_id,"completion_review",{"artifact":artifact.relative_to(directory).as_posix(),"checkpoint":checkpoint["checkpoint"],"complete":payload["complete"],"findings":len(findings)})
 return payload
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());p.add_argument("--run-id",required=True);p.add_argument("--checkpoint",type=Path);p.add_argument("--output",type=Path);a=p.parse_args()
 try:
  payload=review(a.root.resolve(),a.run_id,a.checkpoint)
  if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\\n",encoding="utf-8")
  print(json.dumps(payload,indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:print(f"Completion review error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
