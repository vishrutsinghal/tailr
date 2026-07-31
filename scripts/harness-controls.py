#!/usr/bin/env python3
"""Select and run approved, repository-native computational controls."""
from __future__ import annotations
import argparse, json, subprocess, time, importlib.util
from pathlib import Path
from typing import Any

OUTCOMES = {"pass", "fail", "skipped", "blocked", "timed-out"}
EVIDENCE = {"local-ast", "local-command", "measured/validated"}
ROOT = Path(__file__).resolve().parents[1]
def ledger():
 spec=importlib.util.spec_from_file_location("harness_ledger",ROOT/"scripts"/"run-ledger.py");module=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(module);return module
L=ledger()
def record(root:Path,run_id:str|None,event_type:str,payload:dict[str,Any],artifact_dir:str)->dict[str,Any]:
 if not run_id:return payload
 directory=L.state_dir(root,run_id)/artifact_dir;directory.mkdir(parents=True,exist_ok=True);number=len(list(directory.glob("*.json")))+1;path=directory/f"{event_type}-{number}.json";L.atomic_json(path,payload);L.append_event(root,run_id,event_type,{"artifact":path.relative_to(root).as_posix(),"impacted_paths":payload.get("impacted_paths",[]),"outcomes":[item.get("outcome") for item in payload.get("results",[])]});payload["run_artifact"]=path.as_posix();return payload

def load(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8")); controls = raw.get("controls", raw)
    if not isinstance(controls, list): raise ValueError("controls must be a JSON list or {controls: [...]}")
    for control in controls:
        required = {"id", "command", "scope", "timeout_seconds", "severity", "evidence_label", "requires_approval"}
        if not isinstance(control, dict) or required - set(control): raise ValueError("each control needs id, command, scope, timeout_seconds, severity, evidence_label, requires_approval")
        if not isinstance(control["command"], list) or not all(isinstance(item, str) for item in control["command"]): raise ValueError("control command must be a string array")
        if control["evidence_label"] not in EVIDENCE: raise ValueError("unsupported evidence label")
    return controls

def plan(controls: list[dict[str, Any]], paths: list[str]) -> dict[str, Any]:
    selected, skipped = [], []
    for control in controls:
        entry = {key: control[key] for key in ("id", "scope", "severity", "evidence_label", "requires_approval")}
        if not paths or any(path.startswith(str(control["scope"]).rstrip("/")) for path in paths): selected.append(entry)
        else: skipped.append({**entry, "reason": "outside supplied impacted paths"})
    return {"schema_version": "1", "type": "tailtrail-harness-plan", "selected_controls": selected, "skipped_controls": skipped, "impacted_paths": paths}

def run(controls: list[dict[str, Any]], root: Path, paths: list[str]) -> dict[str, Any]:
    report = plan(controls, paths); results = []
    selected_ids = {item["id"] for item in report["selected_controls"]}
    for control in controls:
        if control["id"] not in selected_ids:
            results.append({"control_id": control["id"], "outcome": "skipped", "reason": "outside supplied impacted paths", "evidence_label": control["evidence_label"]}); continue
        started = time.monotonic()
        try:
            completed = subprocess.run(control["command"], cwd=root, text=True, capture_output=True, timeout=int(control["timeout_seconds"]), check=False)
            outcome = "pass" if completed.returncode == 0 else "fail"
            results.append({"control_id": control["id"], "outcome": outcome, "exit_code": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:], "duration_ms": int((time.monotonic()-started)*1000), "evidence_label": control["evidence_label"]})
        except subprocess.TimeoutExpired as error:
            results.append({"control_id": control["id"], "outcome": "timed-out", "duration_ms": int((time.monotonic()-started)*1000), "stdout": (error.stdout or "")[-4000:], "stderr": (error.stderr or "")[-4000:], "evidence_label": control["evidence_label"]})
    return {"schema_version": "1", "type": "tailtrail-harness-results", "results": results, "impacted_paths": paths}

def main() -> int:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="action", required=True)
    for name in ("plan", "check"):
        item=sub.add_parser(name); item.add_argument("--controls", type=Path, required=True); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id"); item.add_argument("--changed", action="append", default=[])
        if name == "check": item.add_argument("--approved", action="store_true"); item.add_argument("--output", type=Path)
    args=parser.parse_args()
    try:
        root=args.root.resolve();controls=load(args.controls); payload=record(root,args.run_id,"harness_plan",plan(controls,args.changed),"plans") if args.action=="plan" else None
        if args.action=="check":
            if not args.approved: raise ValueError("refusing to execute controls without --approved")
            payload=record(root,args.run_id,"harness_check",run(controls,root,args.changed),"controls")
            if args.output: args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps(payload,indent=2,sort_keys=True)); return 0
    except (ValueError,OSError,json.JSONDecodeError) as error: print(f"Harness controls error: {error}"); return 2
if __name__=="__main__": raise SystemExit(main())
