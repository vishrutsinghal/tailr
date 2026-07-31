#!/usr/bin/env python3
"""Select additive project-specific harness controls (Harness V4)."""
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
def ledger():
 s=importlib.util.spec_from_file_location("template_ledger",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
L=ledger()
def select(root:Path,run_id:str,uid:str,template_path:Path)->dict[str,Any]:
 raw=json.loads(template_path.read_text(encoding="utf-8"));templates=raw.get("templates",[])
 if not isinstance(templates,list): raise ValueError("templates must be a list")
 anchor=json.loads((L.state_dir(root,run_id)/"anchors"/"approved-v1.json").read_text(encoding="utf-8"));row=next((r for r in anchor["requirements"] if r["requirement_uid"]==uid),None)
 if not row: raise ValueError("requirement_uid is not approved")
 selected=[]
 for template in templates:
  if not isinstance(template,dict) or not isinstance(template.get("id"),str): raise ValueError("each template needs an id")
  kinds=template.get("kinds",[]);prefixes=template.get("path_prefixes",[])
  if kinds and row["kind"] not in kinds: continue
  if prefixes and not any(any(path.startswith(prefix.rstrip("/")+"/") or path==prefix.rstrip("/") for prefix in prefixes) for path in row.get("likely_paths",[])): continue
  selected.append({"id":template["id"],"controls":template.get("controls",[]),"required_tiers":template.get("required_tiers",[])})
 existing=row.get("validation_contract",{}).get("tiers",[]);tiers=sorted(set(existing)|{tier for item in selected for tier in item["required_tiers"]})
 controls=sorted({control for item in selected for control in item["controls"]})
 payload={"schema_version":"1","type":"tailtrail-harness-template-selection","run_id":run_id,"requirement_uid":uid,"statement":row["statement"],"selected_templates":selected,"controls":controls,"required_tiers":tiers,"non_weakening_rule":"Template tiers are unioned with the approved validation contract; templates cannot remove approved proof."}
 outdir=L.state_dir(root,run_id)/"template-selections";path=outdir/f"selection-{len(list(outdir.glob('selection-*.json')))+1}.json";L.atomic_json(path,payload);L.append_event(root,run_id,"harness_template_selected",{"artifact":path.relative_to(root).as_posix(),"requirement_uid":uid,"template_ids":[x["id"] for x in selected]});return {"path":path.as_posix(),**payload}
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());p.add_argument("--run-id",required=True);p.add_argument("--requirement-uid",required=True);p.add_argument("--template",type=Path,required=True);a=p.parse_args()
 try:print(json.dumps(select(a.root.resolve(),a.run_id,a.requirement_uid,a.template),indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:print(f"Harness template error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
