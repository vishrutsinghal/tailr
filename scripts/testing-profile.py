#!/usr/bin/env python3
"""Validate local repository testing tiers; JSON is valid YAML for the example profile."""
from __future__ import annotations
import argparse,importlib.util,json
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
def evidence_tiers():
 s=importlib.util.spec_from_file_location("testing_profile_evidence_tiers",ROOT/"scripts"/"evidence-tiers.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
EVIDENCE_TIERS=evidence_tiers();TIERS=set(EVIDENCE_TIERS.CANONICAL_EVIDENCE_TIERS)
def load(path:Path)->dict[str,Any]:
 data=json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(data,dict) or not isinstance(data.get("tiers"),list):raise ValueError("profile needs a tiers list")
 for tier in data["tiers"]:
  required={"name","command","environment","requires_approval","prerequisites","cleanup"}
  if not isinstance(tier,dict) or required-set(tier):raise ValueError("each tier needs name, command, environment, requires_approval, prerequisites, cleanup")
  if tier["name"] not in TIERS or not isinstance(tier["command"],list):raise ValueError("invalid tier name or command")
  if "adapter" in tier and tier["adapter"] not in {"integration","contract","e2e","infrastructure","release-smoke"}:raise ValueError("invalid higher-tier adapter")
  if "remote" in tier and not isinstance(tier["remote"],bool):raise ValueError("remote must be boolean")
  if "safe_test_account" in tier and not isinstance(tier["safe_test_account"],bool):raise ValueError("safe_test_account must be boolean")
 return data
def main()->int:
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest="action",required=True)
 for name in ("validate","list"):
  x=sub.add_parser(name);x.add_argument("--profile",type=Path,required=True);x.add_argument("--changed",action="append",default=[])
 a=p.parse_args()
 try:
  profile=load(a.profile);tiers=profile["tiers"]
  payload={"schema_version":"1","type":"tailtrail-testing-profile","valid":True,"tiers":[{"name":t["name"],"environment":t["environment"],"requires_approval":t["requires_approval"],"prerequisites":t["prerequisites"]} for t in tiers],"changed_paths":a.changed}
  print(json.dumps(payload,indent=2,sort_keys=True));return 0
 except (ValueError,OSError,json.JSONDecodeError) as e:print(f"Testing profile error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
