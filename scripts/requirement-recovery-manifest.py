#!/usr/bin/env python3
"""Explicit Mode B requirement patch-stack capture, plan, and selective restore."""
from __future__ import annotations

import argparse, ast, hashlib, importlib.util, json
from difflib import unified_diff
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def ledger() -> Any:
    spec=importlib.util.spec_from_file_location("mode_b_ledger",ROOT/"scripts"/"run-ledger.py"); module=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(module); return module
L=ledger()
def sha(data:bytes)->str:return "sha256:"+hashlib.sha256(data).hexdigest()
def read(path:Path)->dict[str,Any]:return json.loads(path.read_text(encoding="utf-8"))
def safe(value:str)->str:
 p=Path(value)
 if p.is_absolute() or ".." in p.parts:raise ValueError("paths must be repository-relative")
 return p.as_posix()
def symbols(data:bytes,path:str)->list[str]:
 if not path.endswith(".py"):return []
 try: tree=ast.parse(data.decode("utf-8"))
 except (SyntaxError,UnicodeDecodeError):return []
 return [node.name for node in ast.walk(tree) if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]
def root_dir(root:Path,run_id:str,uid:str)->Path:return L.state_dir(root,run_id)/"recovery"/"mode-b"/uid
def manifest_path(root:Path,run_id:str,uid:str)->Path:return root_dir(root,run_id,uid)/"manifest.json"
def requirement(root:Path,run_id:str,uid:str)->dict[str,Any]:
 anchor=read(L.state_dir(root,run_id)/"anchors"/"approved-v1.json"); row=next((r for r in anchor["requirements"] if r["requirement_uid"]==uid),None)
 if not row:raise ValueError("requirement UID is not in the approved anchor")
 return row
def capture(root:Path,run_id:str,uid:str,approved:bool)->dict[str,Any]:
 if not approved:raise ValueError("Mode B capture stores exact local baseline content; rerun with --approved")
 row=requirement(root,run_id,uid); folder=root_dir(root,run_id,uid)
 if manifest_path(root,run_id,uid).exists():raise ValueError("Mode B manifest already exists for this requirement")
 files=[]
 for raw in row["likely_paths"]:
  path=safe(raw); candidate=root/path; exists=candidate.is_file(); data=candidate.read_bytes() if exists else b""
  baseline=folder/"baseline"/path
  if exists: baseline.parent.mkdir(parents=True,exist_ok=True); baseline.write_bytes(data)
  files.append({"path":path,"before_exists":exists,"before_fingerprint":sha(data) if exists else None,"before_symbols":symbols(data,path)})
 payload={"schema_version":"1","type":"tailtrail-requirement-recovery-manifest","mode":"mode-b","run_id":run_id,"requirement_uid":uid,"statement":row["statement"],"state":"captured","files":files,"preservation_receipts":[],"boundary":"explicit local fallback; exact baselines remain under .tailtrail and are never sent to telemetry or providers"}
 L.atomic_json(manifest_path(root,run_id,uid),payload); L.append_event(root,run_id,"mode_b_captured",{"requirement_uid":uid,"artifact":manifest_path(root,run_id,uid).relative_to(L.state_dir(root,run_id)).as_posix(),"paths":[x["path"] for x in files]}); return payload
def seal(root:Path,run_id:str,uid:str,receipts:list[Path],approved:bool)->dict[str,Any]:
 if not approved:raise ValueError("Mode B seal records task-owned delta; rerun with --approved")
 path=manifest_path(root,run_id,uid); payload=read(path)
 if payload["state"]!="captured":raise ValueError("Mode B manifest must be captured before sealing")
 patch=[]
 for item in payload["files"]:
  target=root/item["path"]; after_exists=target.is_file(); after=target.read_bytes() if after_exists else b""; before=(path.parent/"baseline"/item["path"]).read_bytes() if item["before_exists"] else b""
  item.update({"after_exists":after_exists,"after_fingerprint":sha(after) if after_exists else None,"after_symbols":symbols(after,item["path"]),"changed":before!=after})
  if before!=after:patch.extend(unified_diff(before.decode("utf-8",errors="replace").splitlines(True),after.decode("utf-8",errors="replace").splitlines(True),fromfile="a/"+item["path"],tofile="b/"+item["path"]))
 receipt_data=[]
 for receipt in receipts:
  if not receipt.is_file():raise ValueError(f"preservation receipt is unavailable: {receipt}")
  receipt_data.append({"path":receipt.as_posix(),"sha256":sha(receipt.read_bytes())})
 payload.update({"state":"sealed","patch_path":"task-owned.patch","preservation_receipts":receipt_data}); (path.parent/"task-owned.patch").write_text("".join(patch),encoding="utf-8"); L.atomic_json(path,payload); L.append_event(root,run_id,"mode_b_sealed",{"requirement_uid":uid,"changed_paths":[x["path"] for x in payload["files"] if x["changed"]],"receipt_count":len(receipt_data)}); return payload
def plan(root:Path,run_id:str,uid:str)->dict[str,Any]:
 manifest=read(manifest_path(root,run_id,uid))
 if manifest["state"]!="sealed":raise ValueError("Mode B manifest must be sealed before recovery planning")
 overlap=[]; exact=[]
 for item in manifest["files"]:
  target=root/item["path"]; exists=target.is_file(); current=sha(target.read_bytes()) if exists else None
  if current==item.get("after_fingerprint") and exists==item.get("after_exists"):exact.append(item["path"])
  elif item.get("changed"):overlap.append(item["path"])
 classification="exact-task-state" if not overlap else "overlap-after-seal"; payload={"schema_version":"1","type":"tailtrail-mode-b-recovery-plan","run_id":run_id,"requirement_uid":uid,"classification":classification,"safe_to_apply":not overlap,"task_paths":[x["path"] for x in manifest["files"] if x["changed"]],"exact_paths":exact,"overlap_paths":overlap,"preservation_receipts":manifest["preservation_receipts"],"post_recovery_requirement":"rerun declared preservation evidence before claiming retained work is validated","boundary":"restore only sealed task paths that still match their recorded post-change fingerprints; never overwrite later overlapping edits"}; folder=manifest_path(root,run_id,uid).parent/"plans"; artifact=folder/f"plan-{len(list(folder.glob('plan-*.json')))+1}.json"; L.atomic_json(artifact,payload); L.append_event(root,run_id,"mode_b_planned",{"requirement_uid":uid,"artifact":artifact.relative_to(L.state_dir(root,run_id)).as_posix(),"classification":classification,"safe_to_apply":payload["safe_to_apply"]}); return payload
def apply(root:Path,run_id:str,uid:str,approved:bool)->dict[str,Any]:
 if not approved:raise ValueError("Mode B recovery changes task-owned files; rerun with --approved")
 result=plan(root,run_id,uid)
 if not result["safe_to_apply"]:raise ValueError("Mode B recovery is unsafe: later overlap exists")
 manifest=read(manifest_path(root,run_id,uid))
 for item in manifest["files"]:
  if not item.get("changed"):continue
  target=root/item["path"]
  if item["before_exists"]:target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes((manifest_path(root,run_id,uid).parent/"baseline"/item["path"]).read_bytes())
  elif target.exists():target.unlink()
 manifest["state"]="restored"; L.atomic_json(manifest_path(root,run_id,uid),manifest); L.append_event(root,run_id,"mode_b_applied",{"requirement_uid":uid,"paths":result["task_paths"],"preservation_required":True}); return {**result,"applied":True}
def main()->int:
 p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="action",required=True)
 for name in ("capture","seal","plan","apply"):
  item=sub.add_parser(name); item.add_argument("--root",type=Path,default=Path.cwd()); item.add_argument("--run-id",required=True); item.add_argument("--requirement-uid",required=True)
  if name in {"capture","seal","apply"}:item.add_argument("--approved",action="store_true")
  if name=="seal":item.add_argument("--preservation-receipt",type=Path,action="append",default=[])
 a=p.parse_args()
 try:
  result=capture(a.root.resolve(),a.run_id,a.requirement_uid,a.approved) if a.action=="capture" else seal(a.root.resolve(),a.run_id,a.requirement_uid,a.preservation_receipt,a.approved) if a.action=="seal" else plan(a.root.resolve(),a.run_id,a.requirement_uid) if a.action=="plan" else apply(a.root.resolve(),a.run_id,a.requirement_uid,a.approved); print(json.dumps(result,indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as error:print(f"Mode B recovery error: {error}");return 2
if __name__=="__main__":raise SystemExit(main())
