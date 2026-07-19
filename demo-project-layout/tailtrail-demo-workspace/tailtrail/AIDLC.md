# TailTrail AIDLC

TailTrail AIDLC is a portable AI Development Lifecycle for local and company projects. It helps an agent move from request to implementation with enough structure to be reliable, without turning every small fix into a process exercise.

Use it for broad, risky, ambiguous, multi-team, regulated, or long-running work. For tiny clear edits, use minimal depth and avoid creating extra artifacts.

## V2 Components

AIDLC V2 adds stage playbooks, handoff rules, security and testing baselines, and local Python scripts:

- `aidlc/stages/`: concise playbooks for each lifecycle stage.
- `aidlc/extensions/`: opt-in security and testing baselines.
- `scripts/aidlc-init.py`: creates `aidlc-docs/` in a target project.
- `scripts/aidlc-check.py`: validates the minimum lifecycle artifact shape.

## Core Contract

- Start by understanding the workspace and user intent.
- Choose the smallest lifecycle depth that can safely handle the work.
- Apply `GUARDRAILS.md` for evidence, uncertainty, approval, validation truth, exactness, and safeguard preservation.
- Read `tailtrail-policy.md` when present for local lifecycle, validation, dependency, ownership, and security expectations.
- Record durable state in `aidlc-docs/aidlc-state.md`.
- Record important decisions and approvals in `aidlc-docs/audit.md`.
- Ask non-trivial clarifying questions in files, not long chat threads.
- Require approval gates for standard and comprehensive work before moving across major boundaries.
- Keep application code out of `aidlc-docs/`.
- Load only the current lifecycle slice when resuming work.

## Artifact Location

In a target project, store lifecycle artifacts under:

```text
aidlc-docs/
```

Recommended names:

- `aidlc-state.md`
- `audit.md`
- `questions.md`
- `requirements.md`
- `workflow-plan.md`
- `implementation-plan.md`
- `diff-handoff.md`
- `validation-handoff.md`
- `operations-notes.md`

Use fewer files for minimal work. Use more files only when they reduce ambiguity, risk, or handoff cost.

To initialize a target project:

```bash
python3 scripts/aidlc-init.py --root /path/to/project --depth standard
python3 scripts/aidlc-check.py --root /path/to/project
```

Use strict answer validation only after question files should be complete:

```bash
python3 scripts/aidlc-check.py --root /path/to/project --strict-answers
```

## Depth Levels

| Depth | Use When | Artifact Style |
|---|---|---|
| `minimal` | Clear, low-risk, small-scope work | Update state, capture the request, run focused validation, hand off briefly. |
| `standard` | Normal feature, bug, or refactor work | Create requirements, workflow plan, implementation handoff, validation handoff, and approval gates. |
| `comprehensive` | High-risk, multi-team, regulated, production-sensitive, or system-wide work | Add deeper requirements, questions, design notes, risk/NFR notes, operations notes, and explicit approvals. |

Depth changes detail level, not discipline. Minimal work still preserves security, validation, data integrity, accessibility, and explicit user requirements.

## Phases

### 1. Inception

Purpose: understand the work before choosing implementation shape.

Always consider:

- workspace detection
- request and requirement analysis
- risk and ambiguity
- workflow planning

Use conditionally:

- reverse engineering for brownfield systems
- user stories for stakeholder-heavy work
- design notes for new boundaries or changed architecture
- NFR notes for performance, reliability, privacy, security, compliance, observability, or operability risk

Outputs:

- `aidlc-docs/aidlc-state.md`
- `aidlc-docs/audit.md`
- `aidlc-docs/questions.md` when needed
- `aidlc-docs/requirements.md`
- `aidlc-docs/workflow-plan.md`

Gate for standard or comprehensive depth: requirements and workflow plan approved.

### 2. Construction

Purpose: implement approved units of work with a clear validation path.

Always consider:

- implementation plan for non-trivial work
- exact source files and tests
- dependency gate before adding packages
- focused validation
- build/test output slicing for noisy logs

Use conditionally:

- per-unit design for multi-unit work
- NFR design notes for high-risk requirements
- migration or data notes when state changes
- rollback notes when production impact exists

Outputs:

- `aidlc-docs/implementation-plan.md`
- code changes in the application repo
- `aidlc-docs/diff-handoff.md`
- `aidlc-docs/validation-handoff.md`

Gate for standard or comprehensive depth: implementation plan approved before coding; validation handoff approved before closeout.

### 3. Operations

Purpose: capture what must be known after code changes ship or move toward production.

Use when deployment, support, monitoring, rollback, migration, or production readiness is in scope.

Outputs:

- `aidlc-docs/operations-notes.md`

Gate for standard or comprehensive depth: operations notes approved before production handoff.

## Question Files

Use `templates/question-file.md` when ambiguity affects scope, safety, data, ownership, user experience, or approval. Keep questions specific and answerable.

Question rules:

- Use file-based questions for non-trivial ambiguity.
- Include meaningful choices.
- Put `Other` as the final option.
- Include one recommended option after each question.
- Add concise reasoning for the recommendation so the user can review the tradeoff.
- State any assumption behind the recommendation instead of presenting it as fact.
- Leave `[Answer]:` for the user to fill in.
- After answers are provided, check for contradictions before proceeding.

## Approval Gates

Use `templates/stage-gate.md` for standard and comprehensive work.

Required gates:

- requirements to workflow planning
- workflow planning to implementation planning
- implementation planning to coding
- validation handoff to closeout
- operations readiness when production handoff is involved

Minimal work can use a short inline approval note in `aidlc-docs/aidlc-state.md` if the user clearly asked to proceed.

## Resume Rule

When resuming AIDLC work:

1. Read `aidlc-docs/aidlc-state.md` first.
2. Read only artifacts needed for the current phase and stage.
3. Use `context/slices.md` and the `aidlc` slice to avoid loading every lifecycle file.
4. Refresh stale facts when source files, requirements, approvals, commands, or policies changed.
5. Update state and audit after meaningful progress.

## Handoff Rule

Handoff is the compact transfer package for the next developer, reviewer, agent, or operations owner. Use `aidlc/stages/handoff.md` and the active handoff template when work changes owner, moves to review, finishes validation, or goes toward production.

Handoff must say:

- what changed
- what was reused
- what was intentionally skipped
- what validation ran
- what risk remains
- what exact files, diffs, commands, or logs can be reopened
- what approval or next action is needed

## Dependency Rule

Before adding a dependency, use `DEPENDENCY-GATE.md`. Prefer existing project capabilities, standard libraries, platform-native features, and already-installed packages.

## TailTrail Fit

AIDLC should make large work safer and easier to resume. It should not make small work heavy. If an artifact does not reduce ambiguity, risk, handoff cost, or validation effort, skip it and record why in state or handoff.
