#!/usr/bin/env python3
"""Deterministic requirement-linked architecture fitness assessment."""
from __future__ import annotations

import argparse, ast, importlib.util, json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
def load_ledger() -> Any:
 spec=importlib.util.spec_from_file_location("architecture_ledger",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(m);return m
L=load_ledger()
def read(path:Path)->dict[str,Any]: return json.loads(path.read_text(encoding="utf-8"))
def rel(value:str)->str:
 path=Path(value)
 if path.is_absolute() or ".." in path.parts: raise ValueError("changed paths must be repository-relative")
 return path.as_posix()
def matches(path:str,prefix:str)->bool:return path==prefix or path.startswith(prefix.rstrip("/")+"/")
def dependency_path(path:str)->bool:
 name=Path(path).name.lower()
 return name in {"package.json","pyproject.toml","requirements.txt","pom.xml","go.mod","cargo.toml","composer.json"} or name.endswith((".lock",".csproj",".fsproj"))
def imports(path:Path)->list[str]:
 if path.suffix!=".py" or not path.is_file(): return []
 try: tree=ast.parse(path.read_text(encoding="utf-8"))
 except (SyntaxError,UnicodeDecodeError): return []
 result=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.Import):result.extend(alias.name for alias in node.names)
  if isinstance(node,ast.ImportFrom) and node.module:result.append(node.module)
 return result
def assess(root:Path,run_id:str,changed:list[str],profile_path:Path|None=None)->dict[str,Any]:
 directory=L.state_dir(root,run_id); anchor=read(directory/"anchors"/"approved-v1.json")
 paths=sorted(set(rel(item) for item in changed)); profile=read(profile_path) if profile_path else {}
 findings=[]; checks=[]; rules=profile.get("rules",[]) if isinstance(profile,dict) else []
 graph_events=[event for event in L.read_events(directory/"events.jsonl") if event.get("event_type")=="graph_receipt"]
 all_allowed=sorted({item for row in anchor["requirements"] for item in row.get("likely_paths",[])})
 for path in paths:
  if all_allowed and not any(matches(path,item) for item in all_allowed):findings.append({"category":"scope","classification":"new-drift","path":path,"message":"changed path is outside approved likely paths","evidence":"approved-anchor"})
 for row in anchor["requirements"]:
  contract=row.get("architecture_contract",{}) if isinstance(row.get("architecture_contract",{}),dict) else {}
  required=contract.get("required_paths",[])
  for path in required:
   if not any(matches(item,path) for item in paths):findings.append({"requirement_uid":row["requirement_uid"],"category":"architecture","classification":"unchanged","path":path,"message":"required caller or boundary path was not changed","evidence":"approved-architecture-contract"})
  for path in contract.get("protected_paths",[]):
   if any(matches(item,path) for item in paths):findings.append({"requirement_uid":row["requirement_uid"],"category":"architecture","classification":"new-drift","path":path,"message":"approved protected path was changed","evidence":"approved-architecture-contract"})
  for rule in contract.get("forbidden_imports",[]): rules.append({"type":"forbidden-import",**rule})
  linked_graph=[event for event in graph_events if row["requirement_uid"] in event.get("payload",{}).get("requirement_uids",[])]
  if contract.get("no_new_dependencies"):
   changed_manifests=[path for path in paths if dependency_path(path)]
   checks.append({"requirement_uid":row["requirement_uid"],"control":"no-new-dependencies","status":"drifted" if changed_manifests else "preserved","evidence":"changed-paths","paths":changed_manifests})
   for path in changed_manifests:findings.append({"requirement_uid":row["requirement_uid"],"category":"dependency","classification":"new-drift","path":path,"message":"dependency boundary changed despite the approved no-new-dependency invariant","evidence":"approved-architecture-contract + changed-paths"})
  if contract.get("requires_caller_map") or contract.get("no_parallel_boundary"):
   status="preserved" if linked_graph else "unknown"
   checks.append({"requirement_uid":row["requirement_uid"],"control":"caller-and-boundary-map","status":status,"evidence":"graph-receipt" if linked_graph else "missing","paths":sorted({path for event in linked_graph for path in event.get("payload",{}).get("paths",[])})})
   if not linked_graph:findings.append({"requirement_uid":row["requirement_uid"],"category":"architecture","classification":"unknown","path":None,"message":"approved caller/parallel-boundary invariant needs a requirement-linked Code Graph receipt","evidence":"approved-architecture-contract"})
 for rule in rules:
  if not isinstance(rule,dict):continue
  if rule.get("type")=="protected-path" and any(matches(item,str(rule.get("path",""))) for item in paths):findings.append({"rule_id":rule.get("id"),"category":"architecture","classification":"new-drift","path":rule.get("path"),"message":"profile protected path was changed","evidence":"architecture-profile"})
  if rule.get("type")=="required-path" and not any(matches(item,str(rule.get("path",""))) for item in paths):findings.append({"rule_id":rule.get("id"),"requirement_uid":rule.get("requirement_uid"),"category":"architecture","classification":"unchanged","path":rule.get("path"),"message":"required caller or boundary path was not changed","evidence":"architecture-profile"})
  if rule.get("type")=="forbidden-import":
   source,target=str(rule.get("source_prefix","")),str(rule.get("target_prefix",""))
   for path in paths:
    if source and not matches(path,source):continue
    if any(item==target or item.startswith(target+".") for item in imports(root/path)):
     findings.append({"rule_id":rule.get("id"),"category":"architecture","classification":"new-drift","path":path,"message":f"forbidden import toward `{target}` detected","evidence":"local-ast"})
 state="drifted" if any(item.get("classification") in {"new-drift","regressed"} for item in findings) else ("unknown" if findings else "preserved")
 payload={"schema_version":"1","type":"tailtrail-architecture-fitness","run_id":run_id,"changed_paths":paths,"profile":profile_path.as_posix() if profile_path else None,"contract_checks":checks,"findings":findings,"state":state,"complete":not findings,"evidence_label":"local-ast + approved-contract","boundary":"deterministic path/import/dependency rules plus saved graph receipts; source and focused tests remain final proof"}
 artifacts=directory/"architecture";artifact=artifacts/f"assessment-{len(list(artifacts.glob('assessment-*.json')))+1}.json";L.atomic_json(artifact,payload);L.append_event(root,run_id,"architecture_assessed",{"artifact":artifact.relative_to(directory).as_posix(),"findings":len(findings),"complete":payload["complete"]})
 return payload
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());p.add_argument("--run-id",required=True);p.add_argument("--changed",action="append",required=True);p.add_argument("--profile",type=Path);a=p.parse_args()
 try:print(json.dumps(assess(a.root.resolve(),a.run_id,a.changed,a.profile),indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:print(f"Architecture fitness error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
