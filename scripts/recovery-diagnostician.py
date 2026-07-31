#!/usr/bin/env python3
"""Threshold-gated, evidence-only recovery diagnosis; it never edits source."""
from __future__ import annotations
import argparse,importlib.util,json
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
def ledger()->Any:
 s=importlib.util.spec_from_file_location("diagnostician_ledger",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
L=ledger()
def diagnose(root:Path,run_id:str,artifacts:list[Path],minimum:int=2)->dict[str,Any]:
 if len(artifacts)<minimum:raise ValueError(f"Recovery Diagnostician needs at least {minimum} failure artifacts")
 categories=[]
 for path in artifacts:
  raw=json.loads(path.read_text(encoding="utf-8")); findings=raw.get("findings",[]) if isinstance(raw,dict) else []
  categories.extend(str(item.get("category","unknown")) for item in findings if isinstance(item,dict))
 repeated=sorted({item for item in categories if categories.count(item)>=2}); hypotheses=[]
 if "architecture" in repeated:hypotheses.append({"kind":"repeated-architecture-gap","confidence":"local-evidence","next_action":"reopen the approved architecture contract and caller-path evidence"})
 if "behaviour" in repeated:hypotheses.append({"kind":"repeated-behaviour-gap","confidence":"local-evidence","next_action":"add or repair the declared scenario evidence before another implementation cycle"})
 if "scope" in repeated:hypotheses.append({"kind":"repeated-scope-drift","confidence":"local-evidence","next_action":"replan against the approved anchor; do not broaden paths silently"})
 if not hypotheses:hypotheses.append({"kind":"insufficient-repeated-signal","confidence":"unknown","next_action":"preserve evidence and request a bounded replan; no root cause is inferred"})
 payload={"schema_version":"1","type":"tailtrail-recovery-diagnosis","run_id":run_id,"trigger":"failure threshold reached","artifact_count":len(artifacts),"repeated_categories":repeated,"hypotheses":hypotheses,"boundary":"diagnosis is derived only from supplied local artifacts; it does not implement, merge, approve scope, or invent a product decision"}; folder=L.state_dir(root,run_id)/"recovery"/"diagnoses";out=folder/f"diagnosis-{len(list(folder.glob('diagnosis-*.json')))+1}.json";L.atomic_json(out,payload);L.append_event(root,run_id,"recovery_diagnosed",{"artifact":out.relative_to(L.state_dir(root,run_id)).as_posix(),"artifact_count":len(artifacts),"hypotheses":len(hypotheses)});return payload
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());p.add_argument("--run-id",required=True);p.add_argument("--failure-artifact",type=Path,action="append",required=True);p.add_argument("--min-failures",type=int,default=2);a=p.parse_args()
 try:print(json.dumps(diagnose(a.root.resolve(),a.run_id,a.failure_artifact,a.min_failures),indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as error:print(f"Recovery diagnosis error: {error}");return 2
if __name__=="__main__":raise SystemExit(main())
