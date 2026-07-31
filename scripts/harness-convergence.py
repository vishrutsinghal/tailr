#!/usr/bin/env python3
"""Record bounded requirement convergence and route recovery/replan (Harness V3)."""
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; STATES={"resolved","improved","unchanged","regressed","new-drift","needs-decision"}
def ledger():
 s=importlib.util.spec_from_file_location("convergence_ledger",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
L=ledger()
def assess(root:Path,run_id:str,uid:str,state:str,max_cycles:int)->dict[str,Any]:
 if state not in STATES: raise ValueError("unsupported checkpoint state")
 if max_cycles<1: raise ValueError("max cycles must be at least one")
 directory=L.state_dir(root,run_id);anchor=json.loads((directory/"anchors"/"approved-v1.json").read_text(encoding="utf-8"));
 if uid not in {r["requirement_uid"] for r in anchor["requirements"]}: raise ValueError("requirement_uid is not approved")
 outdir=directory/"convergence";prior=[]
 for path in sorted(outdir.glob("cycle-*.json")):
  data=json.loads(path.read_text(encoding="utf-8"));
  if data.get("requirement_uid")==uid: prior.append(data)
 cycle=len(prior)+1
 if state=="resolved": action="complete";approval=False
 elif state=="needs-decision": action="replan";approval=True
 elif cycle<max_cycles: action="bounded-correction";approval=False
 else:
  mode_b=directory/"recovery"/"mode-b"/uid/"manifest.json"; boundary=directory/"recovery"/"boundary.json"
  action="mode-b-recovery-plan" if mode_b.is_file() else ("mode-a-recovery-plan" if boundary.is_file() else "replan")
  approval=action=="replan"
 payload={"schema_version":"1","type":"tailtrail-harness-convergence","run_id":run_id,"requirement_uid":uid,"cycle":cycle,"max_cycles":max_cycles,"checkpoint_delta":state,"history":[item["checkpoint_delta"] for item in prior]+[state],"action":action,"requires_approval":approval,"rule":"One correction per cycle; recovery/replan preserves prior anchor and evidence."}
 path=outdir/f"cycle-{len(list(outdir.glob('cycle-*.json')))+1}.json";L.atomic_json(path,payload);L.append_event(root,run_id,"harness_convergence_assessed",{"artifact":path.relative_to(root).as_posix(),"requirement_uid":uid,"cycle":cycle,"action":action});return {"path":path.as_posix(),**payload}
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());p.add_argument("--run-id",required=True);p.add_argument("--requirement-uid",required=True);p.add_argument("--state",choices=sorted(STATES),required=True);p.add_argument("--max-cycles",type=int,default=2);a=p.parse_args()
 try: print(json.dumps(assess(a.root.resolve(),a.run_id,a.requirement_uid,a.state,a.max_cycles),indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e: print(f"Harness convergence error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
