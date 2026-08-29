#!/usr/bin/env python3
"""Normalize one exact local validation result into a requirement-linked receipt."""
from __future__ import annotations
import argparse,json,importlib.util
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def ledger():
 s=importlib.util.spec_from_file_location("receipt_ledger",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
L=ledger()
def evidence_tiers():
 s=importlib.util.spec_from_file_location("validation_receipt_evidence_tiers",ROOT/"scripts"/"evidence-tiers.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
EVIDENCE_TIERS=evidence_tiers();TIERS=set(EVIDENCE_TIERS.CANONICAL_EVIDENCE_TIERS);TIER_INPUTS=TIERS|set(EVIDENCE_TIERS.EVIDENCE_TIER_ALIASES);OUTCOMES={"pass","fail","blocked","timed-out","unavailable"}
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());p.add_argument("--run-id");p.add_argument("--requirement-uid",required=True);p.add_argument("--tier",choices=sorted(TIER_INPUTS),required=True);p.add_argument("--command",required=True);p.add_argument("--outcome",choices=sorted(OUTCOMES),required=True);p.add_argument("--environment",required=True);p.add_argument("--asserted-behavior",required=True);p.add_argument("--artifact",default="");p.add_argument("--evidence-label",default="local-command");p.add_argument("--output",type=Path);a=p.parse_args();tier=EVIDENCE_TIERS.normalize(a.tier)
 payload={"schema_version":"1","type":"tailtrail-validation-evidence-receipt","requirement_uid":a.requirement_uid,"tier":tier,"command":a.command,"outcome":a.outcome,"environment":a.environment,"asserted_behavior":a.asserted_behavior,"artifact_path":a.artifact,"evidence_label":a.evidence_label,"created_at":datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
 if a.run_id:
  directory=L.state_dir(a.root.resolve(),a.run_id)/"validation-receipts";directory.mkdir(parents=True,exist_ok=True);path=directory/f"{a.requirement_uid}-{tier}-{len(list(directory.glob('*.json')))+1}.json";L.atomic_json(path,payload);L.append_event(a.root.resolve(),a.run_id,"validation_receipt",{"artifact":path.relative_to(a.root.resolve()).as_posix(),"requirement_uid":a.requirement_uid,"tier":tier,"outcome":a.outcome,"environment":a.environment,"command":a.command});payload["run_artifact"]=path.as_posix()
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps(payload,indent=2,sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
