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
  contract=row.get("validation_contract",{"state":"required","tiers":["unit"]}); relevant=[x for x in receipts if row["requirement_uid"] in x.get("requirement_uids",[x.get("requirement_uid")])]
  if contract["state"] in {"not-applicable","conditional"}:continue
  for tier in contract.get("tiers",[]):
   matching=[x for x in relevant if tier in x.get("tiers",[x.get("tier")])]
   authoritative=[x for x in matching if x.get("evidence_quality") in {"trusted","attested"}]
   outcomes=[x.get("outcome") for x in authoritative]
   reported_outcomes=[x.get("outcome") for x in matching]
   if any(value in reported_outcomes for value in ("fail","timed-out","blocked","unavailable")):
    state="fail" if "fail" in reported_outcomes else "timed-out" if "timed-out" in reported_outcomes else "blocked" if "blocked" in reported_outcomes else "unavailable"
    findings.append({"requirement_uid":row["requirement_uid"],"tier":tier,"state":state,"message":"required tier has non-passing evidence; declared evidence may block but cannot pass closure"})
   elif "pass" not in outcomes:
    declared=any(x.get("outcome")=="pass" for x in matching)
    findings.append({"requirement_uid":row["requirement_uid"],"tier":tier,"state":"unverified" if declared else "insufficient","message":"label-only evidence is not authoritative" if declared else "required tier lacks passing evidence"})
 findings.sort(key=lambda item: ({"fail":0,"timed-out":1,"blocked":2,"unavailable":3,"unverified":4,"insufficient":5}.get(item.get("state"),6),item.get("requirement_uid",""),item.get("tier","")))
 payload={"schema_version":"2","type":"tailtrail-requirement-completion-gate","run_id":run_id,"complete":not findings,"findings":findings,"rule":"Only trusted managed-command or attested artifact-backed evidence can pass a tier; any reported non-pass blocks and authoritative failure dominates pass."}
 if record:
  directory=L.state_dir(root,run_id)/"completion-gates";directory.mkdir(parents=True,exist_ok=True);path=directory/f"gate-{len(list(directory.glob('*.json')))+1}.json";L.atomic_json(path,payload);L.append_event(root,run_id,"completion_gate",{"artifact":path.relative_to(root).as_posix(),"complete":payload["complete"],"findings":findings});payload["run_artifact"]=path.as_posix()
 return payload
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());p.add_argument("--run-id",required=True);p.add_argument("--receipts",type=Path,required=True);a=p.parse_args()
 try:print(json.dumps(gate(a.root.resolve(),a.run_id,a.receipts),indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:print(f"Requirement completion error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
