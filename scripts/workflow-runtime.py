#!/usr/bin/env python3
"""DWR-A/B CLI: canonical workflow ownership and declarative capabilities."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from workflow_runtime import adapters, approvals, capabilities, compiler, correction, evidence, executor, freshness, ownership, resume, retry, start_integration, state, storage, task_scope, vertical


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    bind = sub.add_parser("bind", help="Bind one durable workflow to an approved TailTrail run.")
    bind.add_argument("--root", type=Path, default=Path.cwd()); bind.add_argument("--run-id", required=True); bind.add_argument("--workflow-id")
    for name in ("show", "validate"):
        item = sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--workflow-id", required=True)
    capabilities_parser = sub.add_parser("capabilities", help="Declare or validate DWR-B registered capabilities.")
    capabilities_sub = capabilities_parser.add_subparsers(dest="capability_command", required=True)
    propose = capabilities_sub.add_parser("propose", help="Declare registered capabilities only; does not execute them.")
    propose.add_argument("--root", type=Path, default=Path.cwd()); propose.add_argument("--workflow-id", required=True)
    propose.add_argument("--capability", action="append", default=[], help="Registered feature ID; repeat for each declared stage.")
    for name in ("show", "validate"):
        item = capabilities_sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--workflow-id", required=True)
    grant = capabilities_sub.add_parser("preapprove", help="Grant a time-bound read-only or TailTrail-state pre-approval.")
    grant.add_argument("--root", type=Path, default=Path.cwd()); grant.add_argument("--workflow-id", required=True)
    grant.add_argument("--stage-id", action="append", default=[]); grant.add_argument("--expires-at", required=True)
    for name in ("preapproval-show", "preapproval-validate"):
        item = capabilities_sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--workflow-id", required=True)
    task_parser = sub.add_parser("task", help="DWR-C task scope, reservation, and stale diagnosis.")
    task_sub = task_parser.add_subparsers(dest="task_command", required=True)
    for name in ("scope-init", "scope-show", "freshness", "acquire", "diagnose"):
        item = task_sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--workflow-id", required=True)
    lock_show = task_sub.add_parser("lock-show")
    lock_show.add_argument("--root", type=Path, default=Path.cwd())
    storage_parser = sub.add_parser("storage", help="DWR-minus append-only journal and projection proof.")
    storage_sub = storage_parser.add_subparsers(dest="storage_command", required=True)
    for name in ("init", "capture", "status", "replay", "validate"):
        item = storage_sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--workflow-id", required=True)
    state_parser = sub.add_parser("state", help="DWR-1 local lifecycle and read-only workflow status.")
    state_sub = state_parser.add_subparsers(dest="state_command", required=True)
    create = state_sub.add_parser("create")
    create.add_argument("--root", type=Path, default=Path.cwd()); create.add_argument("--run-id", required=True); create.add_argument("--workflow-id")
    list_parser = state_sub.add_parser("list"); list_parser.add_argument("--root", type=Path, default=Path.cwd())
    for name in ("show", "status", "pause", "resume", "replay", "events", "doctor"):
        item = state_sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--workflow-id", required=True)
    cancel = state_sub.add_parser("cancel")
    cancel.add_argument("--root", type=Path, default=Path.cwd()); cancel.add_argument("--workflow-id", required=True); cancel.add_argument("--confirmed", action="store_true")
    transition = state_sub.add_parser("transition", help="Apply one legal workflow metadata transition.")
    transition.add_argument("--root", type=Path, default=Path.cwd()); transition.add_argument("--workflow-id", required=True); transition.add_argument("--to", required=True); transition.add_argument("--reason-code", required=True)
    stage = state_sub.add_parser("stage", help="Apply one legal stage metadata transition.")
    stage.add_argument("--root", type=Path, default=Path.cwd()); stage.add_argument("--workflow-id", required=True); stage.add_argument("--stage-id", required=True); stage.add_argument("--to", required=True); stage.add_argument("--reason-code", required=True)
    stage.add_argument("--approval-id")
    follow_up = state_sub.add_parser("follow-up", help="Link new approved work to a completed workflow.")
    follow_up.add_argument("--root", type=Path, default=Path.cwd()); follow_up.add_argument("--parent-workflow-id", required=True); follow_up.add_argument("--run-id", required=True); follow_up.add_argument("--workflow-id")
    supersede = state_sub.add_parser("supersede", help="Supersede without deleting the prior workflow record.")
    supersede.add_argument("--root", type=Path, default=Path.cwd()); supersede.add_argument("--workflow-id", required=True); supersede.add_argument("--successor-workflow-id", required=True)
    compile_parser = sub.add_parser("compile", help="DWR-1.5 deterministic, non-executing workflow compiler.")
    compile_sub = compile_parser.add_subparsers(dest="compile_command", required=True)
    for name in ("plan", "show", "validate"):
        item = compile_sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--workflow-id", required=True)
    approvals_parser = sub.add_parser("approvals", help="DWR-2 stage-approval records for a frozen compiler graph.")
    approvals_sub = approvals_parser.add_subparsers(dest="approval_command", required=True)
    for name in ("show", "validate"):
        item = approvals_sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--workflow-id", required=True)
    session = approvals_sub.add_parser("session")
    session.add_argument("--root", type=Path, default=Path.cwd()); session.add_argument("--workflow-id", required=True); session.add_argument("--action-class", action="append", default=[]); session.add_argument("--approved", action="store_true"); session.add_argument("--session-id", default="local-session"); session.add_argument("--expires-at")
    decide = approvals_sub.add_parser("decide", help="Record a bounded interactive stage decision; does not execute it.")
    decide.add_argument("--root", type=Path, default=Path.cwd()); decide.add_argument("--workflow-id", required=True); decide.add_argument("--stage-id", action="append", default=[]); decide.add_argument("--action-class", action="append", default=[]); decide.add_argument("--operation-kind", required=True); decide.add_argument("--operation-ref", required=True); decide.add_argument("--decision", choices=["approved", "rejected", "edited"], required=True); decide.add_argument("--rationale", required=True); decide.add_argument("--expires-at"); decide.add_argument("--policy-ref")
    skip = approvals_sub.add_parser("skip", help="Record an explicit categorized stage-skip approval.")
    skip.add_argument("--root", type=Path, default=Path.cwd()); skip.add_argument("--workflow-id", required=True); skip.add_argument("--stage-id", action="append", default=[]); skip.add_argument("--operation-ref", required=True); skip.add_argument("--reason-code", required=True); skip.add_argument("--rationale", required=True); skip.add_argument("--approved", action="store_true")
    end = approvals_sub.add_parser("session-end", help="Expire approvals from one ended host session.")
    end.add_argument("--root", type=Path, default=Path.cwd()); end.add_argument("--workflow-id", required=True); end.add_argument("--session-id", required=True)
    evidence_parser = sub.add_parser("evidence", help="DWR-3 evidence, freshness, resume, correction, and closure bridge.")
    evidence_sub = evidence_parser.add_subparsers(dest="evidence_command", required=True)
    for name in ("collect", "show", "resume", "validate", "correction"):
        item = evidence_sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--workflow-id", required=True)
    refresh = evidence_sub.add_parser("refresh")
    refresh.add_argument("--root", type=Path, default=Path.cwd()); refresh.add_argument("--workflow-id", required=True); refresh.add_argument("--change-type", action="append", default=[])
    close = evidence_sub.add_parser("close")
    close.add_argument("--root", type=Path, default=Path.cwd()); close.add_argument("--workflow-id", required=True)
    close.add_argument("--accept-evidence-incomplete", action="store_true"); close.add_argument("--approved", action="store_true")
    vertical_parser = sub.add_parser("vertical", help="DWR-4 proven small-change evidence path.")
    vertical_sub = vertical_parser.add_subparsers(dest="vertical_command", required=True)
    for name in ("status", "finalize"):
        item = vertical_sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--workflow-id", required=True)
    adapter_parser = sub.add_parser("adapters", help="Deferred Phase 4 typed capability-adapter contracts.")
    adapter_sub = adapter_parser.add_subparsers(dest="adapter_command", required=True)
    adapter_sub.add_parser("list", help="List and validate the closed core adapter catalog.")
    contract = adapter_sub.add_parser("contract", help="Show one typed adapter contract without running it.")
    contract.add_argument("--adapter-id", required=True)
    prepare = adapter_sub.add_parser("prepare", help="Prepare one idempotent typed stage handoff; does not execute it.")
    prepare.add_argument("--root", type=Path, default=Path.cwd()); prepare.add_argument("--workflow-id", required=True); prepare.add_argument("--stage-id", required=True); prepare.add_argument("--adapter-id", required=True); prepare.add_argument("--approval-id")
    record = adapter_sub.add_parser("record", help="Record a factual typed result produced by the existing capability or host.")
    record.add_argument("--root", type=Path, default=Path.cwd()); record.add_argument("--workflow-id", required=True); record.add_argument("--stage-id", required=True); record.add_argument("--adapter-id", required=True); record.add_argument("--result-ref", required=True)
    for name in ("show", "validate"):
        item = adapter_sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--workflow-id", required=True); item.add_argument("--stage-id", required=True)
    execute_parser = sub.add_parser("execute", help="Deferred Phase 5 deterministic template lifecycle executor.")
    execute_sub = execute_parser.add_subparsers(dest="execute_command", required=True)
    status_parser = execute_sub.add_parser("status"); status_parser.add_argument("--root", type=Path, default=Path.cwd()); status_parser.add_argument("--workflow-id", required=True)
    start_parser = execute_sub.add_parser("start"); start_parser.add_argument("--root", type=Path, default=Path.cwd()); start_parser.add_argument("--workflow-id", required=True); start_parser.add_argument("--stage-id"); start_parser.add_argument("--approval-id")
    finish_parser = execute_sub.add_parser("finish"); finish_parser.add_argument("--root", type=Path, default=Path.cwd()); finish_parser.add_argument("--workflow-id", required=True); finish_parser.add_argument("--stage-id", required=True)
    skip_parser = execute_sub.add_parser("skip"); skip_parser.add_argument("--root", type=Path, default=Path.cwd()); skip_parser.add_argument("--workflow-id", required=True); skip_parser.add_argument("--stage-id", required=True); skip_parser.add_argument("--approval-id", required=True)
    freshness_parser = sub.add_parser("freshness", help="Deferred Phase 6 versioned freshness checkpoints and automatic classification.")
    freshness_sub = freshness_parser.add_subparsers(dest="freshness_command", required=True)
    for name in ("show", "assess", "apply"):
        item = freshness_sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--workflow-id", required=True)
    capture = freshness_sub.add_parser("capture"); capture.add_argument("--root", type=Path, default=Path.cwd()); capture.add_argument("--workflow-id", required=True); capture.add_argument("--reason", default="manual-checkpoint")
    retry_parser = sub.add_parser("retry", help="Deferred Phase 6 bounded low-risk retry control.")
    retry_sub = retry_parser.add_subparsers(dest="retry_command", required=True)
    show_retry = retry_sub.add_parser("show"); show_retry.add_argument("--root", type=Path, default=Path.cwd()); show_retry.add_argument("--workflow-id", required=True)
    for name in ("decide", "prepare"):
        item = retry_sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--workflow-id", required=True); item.add_argument("--stage-id", required=True)
    record_retry = retry_sub.add_parser("record"); record_retry.add_argument("--root", type=Path, default=Path.cwd()); record_retry.add_argument("--workflow-id", required=True); record_retry.add_argument("--stage-id", required=True); record_retry.add_argument("--result-ref", required=True)
    resume_parser = sub.add_parser("resume", help="Derive the shortest dependency-ready continuation without dispatching.")
    resume_parser.add_argument("--root", type=Path, default=Path.cwd()); resume_parser.add_argument("--workflow-id", required=True)
    correction_parser = sub.add_parser("correction", help="Route bounded correction or preserved-state Recovery/Replan.")
    correction_sub = correction_parser.add_subparsers(dest="correction_command", required=True)
    show_correction = correction_sub.add_parser("show"); show_correction.add_argument("--root", type=Path, default=Path.cwd()); show_correction.add_argument("--workflow-id", required=True)
    route_correction = correction_sub.add_parser("route"); route_correction.add_argument("--root", type=Path, default=Path.cwd()); route_correction.add_argument("--workflow-id", required=True); route_correction.add_argument("--stage-id", required=True); route_correction.add_argument("--classification"); route_correction.add_argument("--max-cycles", type=int, default=2)
    args = parser.parse_args()
    try:
        if args.command == "bind": result = ownership.bind(args.root, args.run_id, args.workflow_id)
        elif args.command == "show": result = ownership.show(args.root, args.workflow_id)
        elif args.command == "validate": result = ownership.validate(args.root, args.workflow_id)
        elif args.command == "capabilities":
            if args.capability_command == "propose": result = capabilities.propose(args.root, args.workflow_id, args.capability)
            elif args.capability_command == "show": result = capabilities.show(args.root, args.workflow_id)
            elif args.capability_command == "validate": result = capabilities.validate(args.root, args.workflow_id)
            elif args.capability_command == "preapprove": result = capabilities.grant_preapproval(args.root, args.workflow_id, args.stage_id, args.expires_at)
            elif args.capability_command == "preapproval-show": result = capabilities.show_preapproval(args.root, args.workflow_id)
            else: result = capabilities.validate_preapproval(args.root, args.workflow_id)
        elif args.command == "task":
            if args.task_command == "scope-init": result = task_scope.initialize(args.root, args.workflow_id)
            elif args.task_command == "scope-show": result = task_scope.show(args.root, args.workflow_id)
            elif args.task_command == "freshness": result = task_scope.freshness(args.root, args.workflow_id)
            elif args.task_command == "acquire": result = task_scope.acquire(args.root, args.workflow_id)
            elif args.task_command == "diagnose": result = task_scope.diagnose(args.root, args.workflow_id)
            else: result = task_scope.lock_show(args.root)
        elif args.command == "storage":
            if args.storage_command == "init": result = storage.initialize(args.root, args.workflow_id)
            elif args.storage_command == "capture": result = storage.capture(args.root, args.workflow_id)
            elif args.storage_command == "status": result = storage.status(args.root, args.workflow_id)
            elif args.storage_command == "replay": result = storage.replay(args.root, args.workflow_id)
            else: result = storage.validate(args.root, args.workflow_id)
        elif args.command == "state":
            if args.state_command == "create": result = state.create(args.root, args.run_id, args.workflow_id)
            elif args.state_command == "list": result = state.list_workflows(args.root)
            elif args.state_command in {"show", "status"}: result = state.show(args.root, args.workflow_id)
            elif args.state_command == "pause": result = state.pause(args.root, args.workflow_id)
            elif args.state_command == "resume": result = state.resume(args.root, args.workflow_id)
            elif args.state_command == "cancel": result = state.cancel(args.root, args.workflow_id, args.confirmed)
            elif args.state_command == "replay": result = state.replay(args.root, args.workflow_id)
            elif args.state_command == "events": result = state.events(args.root, args.workflow_id)
            elif args.state_command == "transition": result = state.transition(args.root, args.workflow_id, args.to, args.reason_code)
            elif args.state_command == "stage": result = state.transition_stage(args.root, args.workflow_id, args.stage_id, args.to, args.reason_code, args.approval_id)
            elif args.state_command == "follow-up": result = state.follow_up(args.root, args.parent_workflow_id, args.run_id, args.workflow_id)
            elif args.state_command == "supersede": result = state.supersede(args.root, args.workflow_id, args.successor_workflow_id)
            else: result = state.doctor(args.root, args.workflow_id)
        elif args.command == "compile":
            if args.compile_command == "plan": result = compiler.compile(args.root, args.workflow_id)
            elif args.compile_command == "show": result = compiler.show(args.root, args.workflow_id)
            else: result = compiler.validate(args.root, args.workflow_id)
        elif args.command == "evidence":
            if args.evidence_command == "collect": result = evidence.collect(args.root, args.workflow_id)
            elif args.evidence_command == "show": result = evidence.show(args.root, args.workflow_id)
            elif args.evidence_command == "refresh": result = evidence.refresh(args.root, args.workflow_id, args.change_type)
            elif args.evidence_command == "resume": result = evidence.resume(args.root, args.workflow_id)
            elif args.evidence_command == "correction": result = evidence.correction(args.root, args.workflow_id)
            elif args.evidence_command == "close": result = evidence.close(args.root, args.workflow_id, args.accept_evidence_incomplete, args.approved)
            else: result = evidence.validate(args.root, args.workflow_id)
        elif args.command == "vertical":
            result = vertical.status(args.root, args.workflow_id) if args.vertical_command == "status" else vertical.finalize(args.root, args.workflow_id)
        elif args.command == "adapters":
            if args.adapter_command == "list": result = adapters.catalog()
            elif args.adapter_command == "contract": result = adapters.contract(args.adapter_id)
            elif args.adapter_command == "prepare": result = adapters.prepare(args.root, args.workflow_id, args.stage_id, args.adapter_id, args.approval_id)
            elif args.adapter_command == "record": result = adapters.record(args.root, args.workflow_id, args.stage_id, args.adapter_id, args.result_ref)
            elif args.adapter_command == "show": result = adapters.show(args.root, args.workflow_id, args.stage_id)
            else: result = adapters.validate(args.root, args.workflow_id, args.stage_id)
        elif args.command == "execute":
            if args.execute_command == "status": result = executor.status(args.root, args.workflow_id)
            elif args.execute_command == "start": result = executor.start(args.root, args.workflow_id, args.stage_id, args.approval_id)
            elif args.execute_command == "finish": result = executor.finish(args.root, args.workflow_id, args.stage_id)
            else: result = executor.skip(args.root, args.workflow_id, args.stage_id, args.approval_id)
        elif args.command == "freshness":
            if args.freshness_command == "show": result = freshness.show(args.root, args.workflow_id)
            elif args.freshness_command == "assess": result = freshness.assess(args.root, args.workflow_id)
            elif args.freshness_command == "apply": result = freshness.apply(args.root, args.workflow_id)
            else: result = freshness.checkpoint(args.root, args.workflow_id, args.reason)
        elif args.command == "retry":
            if args.retry_command == "show": result = retry.show(args.root, args.workflow_id)
            elif args.retry_command == "decide": result = retry.decide(args.root, args.workflow_id, args.stage_id)
            elif args.retry_command == "prepare": result = retry.prepare(args.root, args.workflow_id, args.stage_id)
            else: result = retry.record(args.root, args.workflow_id, args.stage_id, args.result_ref)
        elif args.command == "resume": result = resume.plan(args.root, args.workflow_id)
        elif args.command == "correction":
            result = correction.show(args.root, args.workflow_id) if args.correction_command == "show" else correction.route(args.root, args.workflow_id, args.stage_id, args.classification, args.max_cycles)
        elif args.approval_command == "show": result = start_integration.show_approvals(args.root, args.workflow_id)
        elif args.approval_command == "session": result = start_integration.grant_session(args.root, args.workflow_id, args.action_class, args.approved, args.session_id, args.expires_at)
        elif args.approval_command == "session-end": result = approvals.expire_session(args.root, args.workflow_id, args.session_id, "host-session-ended")
        elif args.approval_command == "decide": result = approvals.decide(args.root, args.workflow_id, stage_ids=args.stage_id, action_classes=args.action_class, operation_kind=args.operation_kind, operation_ref=args.operation_ref, decision=args.decision, rationale=args.rationale, expires_at=args.expires_at, policy_ref=args.policy_ref)
        elif args.approval_command == "skip":
            if not args.approved: raise ValueError("skip approval requires --approved")
            compiled = compiler.show(args.root, args.workflow_id)
            selected = [row for row in compiled["stages"] if row["stage_id"] in set(args.stage_id)]
            if len(selected) != len(set(args.stage_id)): raise ValueError("skip approval references an unknown compiler stage")
            action_classes = sorted({"write_tailtrail_state", *(row["adapter_action_class"] for row in selected)})
            result = approvals.decide(args.root, args.workflow_id, stage_ids=args.stage_id, action_classes=action_classes, operation_kind="skip", operation_ref=args.operation_ref, decision="approved", rationale=args.rationale, skip_reason_code=args.reason_code)
        else: result = start_integration.validate_approvals(args.root, args.workflow_id)
        print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result.get("valid", True) else 2
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Workflow runtime error: {error}"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
