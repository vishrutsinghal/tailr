#!/usr/bin/env python3
"""Report calibrated receipt completeness rather than an invented confidence score."""
from __future__ import annotations
import argparse,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def ledger():
 s=importlib.util.spec_from_file_location("metrics_ledger",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
L=ledger()
def report(root,run_id,receipts_path):
 anchor=json.loads((L.state_dir(root,run_id)/"anchors"/"approved-v1.json").read_text(encoding="utf-8"));raw=json.loads(receipts_path.read_text(encoding="utf-8"));receipts=raw.get("receipts",raw);required=[(r["requirement_uid"],tier) for r in anchor["requirements"] for tier in r.get("validation_contract",{}).get("tiers",["unit"])];passed=sum(1 for uid,tier in required if any(x.get("requirement_uid")==uid and x.get("tier")==tier and x.get("outcome")=="pass" for x in receipts));total=len(required);outcomes={key:sum(1 for x in receipts if x.get("outcome")==key) for key in ("pass","fail","blocked","timed-out","unavailable")};payload={"schema_version":"1","type":"tailtrail-calibrated-evidence-metrics","run_id":run_id,"required_receipts":total,"passing_required_receipts":passed,"completeness_ratio":passed/total if total else 1.0,"receipt_outcomes":outcomes,"calibration":"ratio measures only approved receipt completeness; it is not probability of correctness, release approval, or production confidence."};out=L.state_dir(root,run_id)/"evidence-metrics";path=out/f"metrics-{len(list(out.glob('metrics-*.json')))+1}.json";L.atomic_json(path,payload);L.append_event(root,run_id,"evidence_metrics_reported",{"artifact":path.relative_to(root).as_posix(),"completeness_ratio":payload["completeness_ratio"]});return {"path":path.as_posix(),**payload}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());p.add_argument("--run-id",required=True);p.add_argument("--receipts",type=Path,required=True);a=p.parse_args()
 try:print(json.dumps(report(a.root.resolve(),a.run_id,a.receipts),indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:print(f"Evidence metrics error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
