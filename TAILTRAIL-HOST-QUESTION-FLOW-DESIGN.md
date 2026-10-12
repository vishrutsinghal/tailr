# TailTrail Host Question Flow

Status: draft for review

## Purpose

TailTrail should guide the host through missing task information instead of
requiring the host to repeat the complete TailTrail rulebook or allowing
incomplete information to become an inferred implementation plan.

The desired behavior is:

- no silent inference of implementation ownership or proof;
- no unnecessary questionnaire for simple tasks;
- no hard termination when information is missing;
- resumable clarification between the host, TailTrail, and the user;
- no Planning Lock until the required contract is complete.

A missing answer should create a clarification state, not a misleading scope
or an unexplained failure.

## Flow

```text
User starts TailTrail
        |
        v
Task profiler
        |
        v
Profile-specific question set
        |
        v
Host answers questions
        |
        v
TailTrail due diligence
        |
   +----+----+
   |         |
accepted  clarification
   |         |
Planning   host/user
Lock       follow-up
```

## Task Profiling

The profiler should classify the request before detailed scope resolution.
Relevant dimensions include:

- task type: implementation, documentation, QA, infrastructure, or review;
- existing file versus proposed new file;
- single-file versus multi-file change;
- source, configuration, data, documentation, or test paths;
- behavior and compatibility impact;
- risk level;
- existing proof versus proposed proof;
- edit authority versus read-only analysis.

The profile selects the smallest useful question set. A prose-only document
change should not receive the same questionnaire as a new production feature.

## Profile Questions

### Documentation

Ask only:

- Which document is changing?
- Is the change prose-only?
- What audience or behavior should the document describe?
- Are code and configuration changes excluded?

### Existing Code

Ask:

- Which existing path owns the behavior?
- What behavior changes?
- Which callers or consumers must remain compatible?
- Which existing test proves the behavior?
- What command should run after the edit?
- What behavior must remain unchanged?

### New Feature

Ask:

- Which new files may be created?
- Which path is the proposed implementation owner?
- Which paths are inspection-only?
- Which test path will be created?
- Which public entry point or caller uses the feature?
- What command proves the feature?
- What are the positive and negative acceptance criteria?

### Configuration or Data

Ask:

- Is the path implementation-owned, inspection-only, generated, or proof-only?
- Which consumer owns the behavior?
- What schema or format must remain valid?
- Is write authority explicitly granted?

## Host Input Contract

The host answers should be stored once in a hash-bound contract. Later
requirement, scope, proof, and report artifacts should reference the contract
rather than repeat and reinterpret its fields.

```json
{
  "type": "tailtrail-host-input-contract",
  "profile": "new-feature",
  "paths": [
    {
      "path": "scripts/feature-health-audit.py",
      "role": "proposed-implementation-owner"
    },
    {
      "path": "tests/test_feature_health_audit.py",
      "role": "proposed-proof-path"
    },
    {
      "path": "tailtrail-registry.json",
      "role": "inspection-input"
    }
  ],
  "criteria": {
    "positive": ["The audit emits machine-readable findings."],
    "negative": ["The audit does not modify repository files."]
  },
  "proof": {
    "command": "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_feature_health_audit -v",
    "tiers": ["unit"]
  }
}
```

The contract should distinguish existing paths from proposed paths. A new
feature is allowed to name a test that does not exist yet, but completion must
require that the test is created and passes.

## TailTrail Due Diligence

After receiving the host answers, TailTrail independently checks:

- paths exist or are explicitly proposed as new;
- roles do not conflict;
- implementation ownership has evidence;
- proof is relevant to the requirement;
- validation commands are executable;
- test paths are not promoted to implementation owners;
- generated and worktree paths are excluded from product scope;
- positive and negative criteria are covered;
- callers, dependencies, and protected behavior are accounted for.

The result should be one of:

- accepted: create the Planning Lock;
- clarification: ask the host for missing or contradictory information;
- user-decision: ask the user to resolve a product or scope choice;
- revise-profile: change the task profile and ask a smaller or different set of
  questions.

TailTrail must not promote a generic graph match into an implementation owner
when the host contract is incomplete.

## Resumable States

The workflow should represent progress explicitly:

```text
intake
  -> profiling
  -> awaiting-host-answers
  -> due-diligence
  -> awaiting-clarification
  -> awaiting-user-decision
  -> awaiting-approval
  -> approved
  -> activated
```

A missing answer keeps the run resumable. It does not create a Planning Lock and
does not silently infer scope.

Clarification should be bounded:

- no more than five host-question rounds;
- no more than three material questions per round;
- after the limit, ask the user for a decision with the unresolved evidence
  clearly named.

The workflow should not loop indefinitely between the host and TailTrail.

## Responsibility Split

### Host

- provide the user's goal and known context;
- answer profile-specific questions;
- declare path roles when known;
- clarify unknowns when TailTrail asks.

### TailTrail

- select the task profile;
- generate the smallest relevant question set;
- validate host answers;
- perform scope and proof due diligence;
- preserve the hash-bound contract;
- ask follow-up questions when evidence is insufficient;
- prevent bypasses across CLI and MCP entry points.

### User

- resolve genuine product, ownership, or scope decisions that repository
  evidence and host context cannot determine.

## Entry-Point Consistency

The preflight contract should be shared by:

- the top-level CLI;
- the orchestration facade;
- MCP Start tools;
- any direct internal Start entry point.

No entry point should be able to skip profiling or create a Planning Lock from
an incomplete host contract.

## P7 Acceptance Boundary

The P7 incident should become a regression test for this flow:

```text
P7 goal with no declared implementation owner or proof
  -> awaiting-host-answers or awaiting-clarification
  -> no resolved implementation owner
  -> no test_delivery_record.py proof
  -> no Planning Lock
```

A valid P7 packet with an explicit proposed implementation path and proposed
proof path should progress to scope and proof due diligence.

## Recommended Delivery Order

1. Add a shared semantic host-input preflight validator.
2. Route CLI and MCP Start through the validator.
3. Return typed questions without creating a Planning Lock when input is
   incomplete.
4. Support proposed-new implementation and proof paths.
5. Store one hash-bound host contract and reference it from projections.
6. Add the P7 regression test.
7. Add profile-specific question selection.
8. Add bounded clarification and user-decision states if existing lifecycle
   states cannot represent them.

## Design Constraint

The system should be strict about silent inference but flexible about explicit
proposals for new files, tests, and ownership. This preserves safety without
making new feature development impossible.
