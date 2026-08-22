from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader
    sys.modules[name] = module; spec.loader.exec_module(module); return module


LOCK = load("phase9_lock", "scripts/planning-lock.py")
MCP = load("phase9_mcp", "scripts/mcp-server.py")
from workflow_runtime import ci, compiler, contracts, ownership, start_integration, storage, task_scope, transitions


class WorkflowCiContinuationTests(unittest.TestCase):
    def test_read_only_status_creates_no_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); result=ci.show(root,"ttw-phase9-read-only")
        self.assertEqual(result["status"],"not-started"); self.assertFalse((root/".tailtrail").exists())

    def _git(self, root: Path, *args: str) -> str:
        result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr); return result.stdout.strip()

    def setup_workflow(self, root: Path, suffix: str = "", progress: bool = True, feature_ids: list[str] | None = None) -> tuple[str, str, str]:
        self._git(root, "init", "-q"); self._git(root, "config", "user.email", "phase9@example.invalid"); self._git(root, "config", "user.name", "Phase 9 Test")
        (root / "src").mkdir(); (root / "src" / "service.py").write_text("def safe(): return True\n", encoding="utf-8")
        self._git(root, "add", "src/service.py"); self._git(root, "commit", "-qm", "initial")
        run_id = f"phase9-run{suffix}"
        selected = feature_ids or ["code-graph-mapper","requirement-completion-harness","evidence-aware-testing","review"]
        report = {"goal":"continue approved CI validation", "guided_delivery":{"mode":"guided-delivery"}, "navigator":{"registry_workflow":{"feature_ids":selected}, "requirement_matrix":[{"display_id":"REQ-01","statement":"Continue only linked CI validation", "kind":"change", "acceptance_criteria":["Linked proof advances"], "preserve_rules":["No CI project writes"], "likely_paths":["src/service.py"], "evidence_plan":["CI receipt"]}]}}
        report["workflow_runtime"] = start_integration.draft(report, run_id)
        LOCK.create(root, report["goal"], run_id); LOCK.save_start_report(root, run_id, report)
        activated = LOCK.activate(root, run_id, True); workflow_id = activated["workflow_runtime"]["workflow_id"]
        task_scope.initialize(root, workflow_id); transitions.ensure_stages(root, workflow_id)
        storage.append_event(root, workflow_id, "workflow-started", {"from_state":"ready","to_state":"running","reason_code":"workflow-started","boundary":"test fixture metadata"})
        if progress:
            for stage_id in ("bootstrap", "discover", "implement"):
                storage.append_event(root, workflow_id, "stage-ready", {"stage_id":stage_id,"from_state":"pending","to_state":"ready","reason_code":"stage-ready","boundary":"test fixture metadata"})
                storage.append_event(root, workflow_id, "stage-started", {"stage_id":stage_id,"from_state":"ready","to_state":"running","reason_code":"stage-started","approval_id":None,"boundary":"test fixture metadata"})
                storage.append_event(root, workflow_id, "stage-passed", {"stage_id":stage_id,"from_state":"running","to_state":"passed","reason_code":"stage-passed","approval_id":None,"boundary":"test fixture metadata"})
        return run_id, workflow_id, ownership.show(root, workflow_id)["requirement_uids"][0]

    def write_policy(self, root: Path, run_id: str, workflow_id: str, stages: list[dict[str, str]]) -> str:
        binding = ownership.show(root, workflow_id); plan = compiler.show(root, workflow_id); scope = task_scope.show(root, workflow_id)
        policy = {"schema_version":"1","type":"tailtrail-workflow-ci-policy","policy_id":"wfci-policy-phase9","status":"approved","workflow_id":workflow_id,"tailtrail_run_id":run_id,"revision":plan["revision"],"compiler_plan_fingerprint":plan["plan_fingerprint"],"target_identity_fingerprint":binding["target_identity_fingerprint"],"scope_fingerprint":scope["scope_fingerprint"],"allowed_environments":["ci"],"trusted_provenance":[{"provider":"github-actions","pipeline_ref":".github/workflows/ci.yml"}],"allowed_stages":stages,"policy_fingerprint":"","boundary":"Approved CI metadata continuation only; no project or external action authority."}
        policy["policy_fingerprint"] = ci.policy_fingerprint(policy); ref = ".tailtrail/ci-policy-v1.json"
        (root / ref).write_text(json.dumps(policy), encoding="utf-8"); return ref

    def write_receipt(self, root: Path, run_id: str, workflow_id: str, uid: str, policy_ref: str, *, receipt_id: str = "wfci-focused-1", stage_id: str = "focused-test", operation: str = "validation", outcome: str = "pass", attempt: int = 1, **updates: object) -> str:
        artifact_ref = f".tailtrail/ci-artifacts/{receipt_id}.json"; attestation_ref = f".tailtrail/ci-attestations/{receipt_id}.json"
        for ref, value in ((artifact_ref,{"outcome":outcome,"summary":"sanitized"}),(attestation_ref,{"verified":True})):
            path=root/ref; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value),encoding="utf-8")
        binding=ownership.show(root,workflow_id); plan=compiler.show(root,workflow_id); scope=task_scope.show(root,workflow_id); policy=json.loads((root/policy_ref).read_text(encoding="utf-8"))
        receipt={"schema_version":"1","type":"tailtrail-workflow-ci-receipt","receipt_id":receipt_id,"workflow_id":workflow_id,"tailtrail_run_id":run_id,"requirement_uids":[uid],"stage_id":stage_id,"operation_kind":operation,"compiler_revision":plan["revision"],"compiler_plan_fingerprint":plan["plan_fingerprint"],"target_identity_fingerprint":binding["target_identity_fingerprint"],"scope_fingerprint":scope["scope_fingerprint"],"commit_sha":ownership.TARGET.identity(root)["git"]["head"],"environment":"ci","command_label":"focused validation","outcome":outcome,"artifact_ref":artifact_ref,"artifact_hash":ci._file_hash(root/artifact_ref),"provenance":{"provider":"github-actions","pipeline_ref":".github/workflows/ci.yml","provider_run_id":"run-100","job_ref":"validate","attempt":attempt,"attestation_ref":attestation_ref},"policy_ref":policy_ref,"policy_fingerprint":policy["policy_fingerprint"],"observed_at":"2026-08-21T00:00:00Z","boundary":"Sanitized linked CI result only; no raw log, credential, command body, or provider secret."}
        receipt.update(updates); ref=f".tailtrail/incoming/{receipt_id}-{attempt}.json"; path=root/ref; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(receipt),encoding="utf-8"); return ref

    def test_valid_policy_linked_receipt_advances_only_validation_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); run_id,wid,uid=self.setup_workflow(root); policy=self.write_policy(root,run_id,wid,[{"stage_id":"focused-test","operation_kind":"validation"}]); receipt=self.write_receipt(root,run_id,wid,uid,policy)
            source_before=(root/"src/service.py").read_bytes(); result=MCP.call_tool("workflow_ci_ingest",{"root":root.as_posix(),"workflow_id":wid,"receipt_ref":receipt,"policy_ref":policy,"approved":True})["result"]; replay=storage.replay(root,wid)
            shown=subprocess.run([sys.executable,(ROOT/"scripts"/"tailtrail.py").as_posix(),"workflow","ci","show","--root",root.as_posix(),"--workflow-id",wid],cwd=ROOT,text=True,capture_output=True,check=False)
        self.assertEqual(result["status"],"advanced"); self.assertEqual(result["stage_status"],"passed"); self.assertTrue(replay["valid"]); self.assertEqual(source_before,b"def safe(): return True\n"); self.assertEqual(shown.returncode,0,shown.stdout+shown.stderr); self.assertEqual(json.loads(shown.stdout)["status"],"valid")

    def test_explicit_approval_policy_provenance_commit_and_privacy_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); run_id,wid,uid=self.setup_workflow(root); policy=self.write_policy(root,run_id,wid,[{"stage_id":"focused-test","operation_kind":"validation"}]); receipt=self.write_receipt(root,run_id,wid,uid,policy)
            with self.assertRaisesRegex(ValueError,"explicit approved"): ci.ingest(root,wid,receipt,policy,False)
            bad=self.write_receipt(root,run_id,wid,uid,policy,receipt_id="wfci-wrong-commit",commit_sha="a"*40)
            with self.assertRaisesRegex(ValueError,"commit"): ci.ingest(root,wid,bad,policy,True)
            raw=json.loads((root/receipt).read_text(encoding="utf-8")); raw["raw_log"]="secret output"
            self.assertTrue(contracts.validate_artifact(raw)); self.assertNotIn("raw_log",json.dumps(ci.show(root,wid)))

    def test_forbidden_project_scanner_provider_and_publish_actions_are_never_continuable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); run_id,wid,uid=self.setup_workflow(root,progress=False)
            policy=self.write_policy(root,run_id,wid,[{"stage_id":"implement","operation_kind":"validation"}]); receipt=self.write_receipt(root,run_id,wid,uid,policy,receipt_id="wfci-forbidden-write",stage_id="implement",operation="validation")
            with self.assertRaisesRegex(ValueError,"forbids stage action class"): ci.ingest(root,wid,receipt,policy,True)
        risk_features=json.loads((ROOT/"tests"/"fixtures"/"workflow_runtime"/"templates"/"risk-sensitive.json").read_text(encoding="utf-8"))["feature_ids"]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); run_id,wid,uid=self.setup_workflow(root,"-scanner",False,risk_features)
            for stage in ("security","quality"):
                policy=self.write_policy(root,run_id,wid,[{"stage_id":stage,"operation_kind":"reporting"}]); receipt=self.write_receipt(root,run_id,wid,uid,policy,receipt_id=f"wfci-forbidden-{stage}",stage_id=stage,operation="reporting")
                with self.assertRaisesRegex(ValueError,"forbids stage action class"): ci.ingest(root,wid,receipt,policy,True)
        self.assertEqual(ci.FORBIDDEN_ACTIONS,{"write_project","scan_local","external_provider","publish"})

    def test_duplicate_delayed_late_and_out_of_order_receipts_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); run_id,wid,uid=self.setup_workflow(root); policy=self.write_policy(root,run_id,wid,[{"stage_id":"focused-test","operation_kind":"validation"},{"stage_id":"fulfilment","operation_kind":"closure-readiness"}]); receipt=self.write_receipt(root,run_id,wid,uid,policy)
            first=ci.ingest(root,wid,receipt,policy,True); duplicate=ci.ingest(root,wid,receipt,policy,True)
            delayed_ref=self.write_receipt(root,run_id,wid,uid,policy,receipt_id="wfci-focused-delayed",attempt=1); delayed=ci.ingest(root,wid,delayed_ref,policy,True)
            late_ref=self.write_receipt(root,run_id,wid,uid,policy,receipt_id="wfci-focused-late",attempt=2,outcome="fail"); late=ci.ingest(root,wid,late_ref,policy,True)
            review_ref=self.write_receipt(root,run_id,wid,uid,policy,receipt_id="wfci-fulfilment-1",stage_id="fulfilment",operation="closure-readiness"); review=ci.ingest(root,wid,review_ref,policy,True)
        self.assertEqual([first["status"],duplicate["status"],delayed["status"],late["status"],review["status"]],["advanced","duplicate-suppressed","delayed-ignored","late-terminal-ignored","out-of-order-blocked"])

    def test_failed_and_cancelled_receipts_stop_without_recovery_or_completion(self) -> None:
        for suffix,outcome,expected in (("-failed","fail","failed"),("-cancelled","cancelled","blocked")):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as temp:
                root=Path(temp); run_id,wid,uid=self.setup_workflow(root,suffix); policy=self.write_policy(root,run_id,wid,[{"stage_id":"focused-test","operation_kind":"validation"}]); receipt=self.write_receipt(root,run_id,wid,uid,policy,receipt_id=f"wfci-{outcome}-1",outcome=outcome)
                result=ci.ingest(root,wid,receipt,policy,True)
                self.assertEqual(result["workflow_status"],expected); self.assertFalse((root/".tailtrail"/"runs"/run_id/"recovery"/"boundary.json").exists()); self.assertFalse((root/".tailtrail"/"workflows"/wid/"completion-receipt-v1.json").exists())


if __name__ == "__main__": unittest.main()
