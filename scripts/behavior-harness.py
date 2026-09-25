#!/usr/bin/env python3
"""Requirement-linked scenario evidence assessment; it never invents user-flow proof."""
from __future__ import annotations
import argparse,importlib.util,json
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
def ledger():
 s=importlib.util.spec_from_file_location("behavior_ledger",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
L=ledger()
def read(p:Path)->dict[str,Any]:return json.loads(p.read_text(encoding="utf-8"))
def assess(root:Path,run_id:str,scenarios_path:Path,evidence_path:Path)->dict[str,Any]:
 directory=L.state_dir(root,run_id);anchor=read(directory/"anchors"/"approved-v1.json");known={r["requirement_uid"] for r in anchor["requirements"]};scenarios=read(scenarios_path).get("scenarios",[]);receipts=read(evidence_path).get("receipts",[]);findings=[];results=[]
 for scenario in scenarios:
  uid=str(scenario.get("requirement_uid",""));sid=str(scenario.get("scenario_id",""));required=scenario.get("evidence",[])
  if not sid or uid not in known:raise ValueError("each scenario needs an ID and approved requirement_uid")
  missing=[]
  for item in required:
   if not any(
    uid in r.get("requirement_uids",[r.get("requirement_uid")])
    and item.get("tier") in r.get("tiers",[r.get("tier")])
    and r.get("outcome")=="pass"
    and r.get("evidence_quality") in {"trusted","attested"}
    and (sid in r.get("scenario_ids",[]) or (not r.get("scenario_ids") and r.get("asserted_behavior")==item.get("asserted_behavior")))
    for r in receipts
   ):missing.append(item)
  state="validated" if not missing else "incomplete";results.append({"scenario_id":sid,"requirement_uid":uid,"state":state,"preconditions":scenario.get("preconditions",[]),"action":scenario.get("action",""),"expected_outcome":scenario.get("expected_outcome",""),"preservation":scenario.get("preservation",[]),"provenance":scenario.get("provenance","template-hypothesis"),"missing_evidence":missing})
  if missing:findings.append({"scenario_id":sid,"requirement_uid":uid,"category":"behaviour","classification":"needs-decision" if not required else "unchanged","message":"user-flow scenario lacks matching passing evidence","missing_evidence":missing})
  payload={"schema_version":"2","type":"tailtrail-behavior-harness","run_id":run_id,"scenarios":results,"findings":findings,"complete":not findings,"coverage":{"scenarios":len(results),"validated":sum(1 for row in results if row["state"]=="validated"),"incomplete":sum(1 for row in results if row["state"]!="validated")},"unknowns":sorted({row["scenario_id"] for row in results if row["state"]!="validated"})+["areas outside declared scenarios are unassessed"] if findings else [],"evidence_label":"approved scenario IDs + authoritative execution receipt","boundary":"scenario evidence must use stable IDs and trusted managed-command or attested artifact-backed receipts"};folder=directory/"behavior";path=folder/f"assessment-{len(list(folder.glob('assessment-*.json')))+1}.json";L.atomic_json(path,payload);L.append_event(root,run_id,"behavior_assessed",{"artifact":path.relative_to(directory).as_posix(),"findings":len(findings),"complete":payload["complete"]});return payload
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());p.add_argument("--run-id",required=True);p.add_argument("--scenarios",type=Path,required=True);p.add_argument("--evidence",type=Path,required=True);a=p.parse_args()
 try:print(json.dumps(assess(a.root.resolve(),a.run_id,a.scenarios,a.evidence),indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:print(f"Behavior harness error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
