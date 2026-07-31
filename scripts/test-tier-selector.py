#!/usr/bin/env python3
"""Select the minimum approved, declared testing tiers for each requirement."""
from __future__ import annotations
import argparse,importlib.util,json
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1];ORDER=("unit","component","integration","contract","e2e","infrastructure","release-smoke")
def load_script(name):
 s=importlib.util.spec_from_file_location(name,ROOT/"scripts"/f"{name}.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
L=load_script("run-ledger");PROFILE=load_script("testing-profile")
def intersects(path,likely):return any(path==x or path.startswith(x.rstrip("/")+"/") or x.startswith(path.rstrip("/")+"/") for x in likely)
def select(root:Path,run_id:str,profile_path:Path,changed:list[str])->dict[str,Any]:
 profile=PROFILE.load(profile_path);declared={x["name"]:x for x in profile["tiers"]};anchor=json.loads((L.state_dir(root,run_id)/"anchors"/"approved-v1.json").read_text(encoding="utf-8"));rows=[]
 for req in anchor["requirements"]:
  required=req.get("validation_contract",{}).get("tiers",["unit"]);matched=any(intersects(path,req.get("likely_paths",[])) for path in changed)
  available=[tier for tier in required if tier in declared]
  missing=[tier for tier in required if tier not in declared]
  # Behaviour scenarios require declared integration proof when it is not already stronger.
  if req.get("behavior_contract",{}).get("scenarios") and "integration" in declared and "integration" not in available: available.append("integration")
  rows.append({"requirement_uid":req["requirement_uid"],"statement":req["statement"],"changed_scope_match":matched,"selected_tiers":sorted(set(available),key=ORDER.index),"missing_declared_tiers":missing,"reason":"approved validation contract plus declared behaviour scenario"})
 payload={"schema_version":"1","type":"tailtrail-minimum-tier-selection","run_id":run_id,"changed_paths":changed,"requirements":rows,"boundary":"Selection chooses only repository-declared tiers. It does not invent a command, execute a test, or replace the approved validation contract."}
 out=L.state_dir(root,run_id)/"testing-selections";path=out/f"selection-{len(list(out.glob('selection-*.json')))+1}.json";L.atomic_json(path,payload);L.append_event(root,run_id,"minimum_tier_selected",{"artifact":path.relative_to(root).as_posix(),"requirements":[r["requirement_uid"] for r in rows]});return {"path":path.as_posix(),**payload}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());p.add_argument("--run-id",required=True);p.add_argument("--profile",type=Path,required=True);p.add_argument("--changed",action="append",default=[]);a=p.parse_args()
 try:print(json.dumps(select(a.root.resolve(),a.run_id,a.profile,a.changed),indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:print(f"Tier selection error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
