#!/usr/bin/env python3
"""Create one bounded correction packet from a completion review."""
from __future__ import annotations
import argparse,importlib.util,json
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
def ledger():
 spec=importlib.util.spec_from_file_location("phase1_ledger_feedback",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(m);return m
L=ledger()
def feedback(review_path:Path,root:Path|None=None,run_id:str|None=None)->dict[str,Any]:
 review=json.loads(review_path.read_text(encoding="utf-8")); findings=review.get("findings",[])
 if not findings:payload={"schema_version":"1","type":"tailtrail-harness-feedback","status":"no-correction-needed","packet":None}
 else:
  item=findings[0];payload={"schema_version":"1","type":"tailtrail-harness-feedback","status":"correction-needed","packet":{"requirement_uid":item["requirement_uid"],"drift_category":item["category"],"classification":item["classification"],"evidence":item["message"],"allowed_scope":"approved requirement paths and focused tests only","preserve_rules":"use the approved anchor row","next_validation":"rerun the failed or missing focused control"},"deferred_findings":findings[1:],"rule":"one highest-value correction only; do not retry indefinitely"}
 if root is not None and run_id is not None:
  directory=L.state_dir(root,run_id); packets=directory/"feedback"; index=len(list(packets.glob("feedback-*.json")))+1;artifact=packets/f"feedback-{index}.json";L.atomic_json(artifact,payload)
  L.append_event(root,run_id,"harness_feedback",{"artifact":artifact.relative_to(directory).as_posix(),"status":payload["status"],"requirement_uid":payload.get("packet",{}).get("requirement_uid") if payload.get("packet") else None})
 return payload
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--review",type=Path,required=True);p.add_argument("--output",type=Path);p.add_argument("--root",type=Path);p.add_argument("--run-id");a=p.parse_args()
 try:
  if (a.root is None)!=(a.run_id is None):raise ValueError("--root and --run-id must be supplied together")
  payload=feedback(a.review,a.root.resolve() if a.root else None,a.run_id)
  if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
  print(json.dumps(payload,indent=2,sort_keys=True));return 0
 except (OSError,ValueError,json.JSONDecodeError) as e:print(f"Harness feedback error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
