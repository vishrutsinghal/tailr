#!/usr/bin/env python3
"""Build local requirement-to-symbol/caller/test impact evidence (Harness V2)."""
from __future__ import annotations
import argparse, ast, importlib.util, json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
def ledger():
 s=importlib.util.spec_from_file_location("impact_ledger",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
L=ledger()
def read(path:Path)->dict[str,Any]: return json.loads(path.read_text(encoding="utf-8"))
def python_files(root:Path):
 return [p for p in root.rglob("*.py") if not any(x in {".git",".tailtrail",".venv","__pycache__"} for x in p.parts)]
def symbols(path:Path)->list[str]:
 try: tree=ast.parse(path.read_text(encoding="utf-8"))
 except (OSError,UnicodeDecodeError,SyntaxError): return []
 return [node.name for node in ast.walk(tree) if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]
def calls(path:Path,names:set[str])->list[str]:
 try: tree=ast.parse(path.read_text(encoding="utf-8"))
 except (OSError,UnicodeDecodeError,SyntaxError): return []
 found=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in names: found.append(node.func.id)
 return sorted(set(found))
def intersects(path:str,likely:list[str])->bool:
 return any(path==item or path.startswith(item.rstrip("/")+"/") or item.startswith(path.rstrip("/")+"/") for item in likely)
def map_impact(root:Path,run_id:str,changed:list[str])->dict[str,Any]:
 directory=L.state_dir(root,run_id);anchor=read(directory/"anchors"/"approved-v1.json")
 source={p.relative_to(root).as_posix():symbols(p) for p in python_files(root)}
 mapped=[]
 for row in anchor["requirements"]:
  relevant=sorted({p for p in changed if intersects(p,row.get("likely_paths",[]))})
  names={name for path in relevant for name in source.get(path,[])}
  callers=[];tests=[]
  for path in sorted(source):
   used=calls(root/path,names) if names else []
   if used:
    entry={"path":path,"symbols":used}
    (tests if path.startswith("tests/") or "/tests/" in path else callers).append(entry)
  selected=["completion-review","focused-validation"]
  if callers or row.get("architecture_contract",{}).get("required_paths"): selected.append("architecture-fitness")
  if row.get("behavior_contract",{}).get("scenarios"): selected.append("behavior-harness")
  mapped.append({"requirement_uid":row["requirement_uid"],"statement":row["statement"],"approved_paths":row.get("likely_paths",[]),"changed_paths":relevant,"symbols":[{"path":p,"symbols":source.get(p,[])} for p in relevant],"callers":callers,"tests":tests,"selected_controls":selected,"classification":"mapped" if relevant else "new-drift","evidence_label":"local-ast"})
 outdir=directory/"impact-maps";number=len(list(outdir.glob("map-*.json")))+1
 payload={"schema_version":"1","type":"tailtrail-requirement-impact-map","run_id":run_id,"changed_paths":changed,"requirements":mapped,"rule":"Local AST mapping only; callers and tests are candidates, not completion proof."}
 path=outdir/f"map-{number}.json";L.atomic_json(path,payload);L.append_event(root,run_id,"requirement_impact_mapped",{"artifact":path.relative_to(root).as_posix(),"requirements":[r["requirement_uid"] for r in mapped]});return {"path":path.as_posix(),**payload}
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());p.add_argument("--run-id",required=True);p.add_argument("--changed",action="append",required=True);a=p.parse_args()
 try: print(json.dumps(map_impact(a.root.resolve(),a.run_id,a.changed),indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e: print(f"Requirement impact map error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
