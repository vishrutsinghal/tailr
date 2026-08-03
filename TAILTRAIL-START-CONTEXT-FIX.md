# TailTrail Start Context Carryover Fix

## Status

- Implementation: complete
- Focused tests: passed
- Adapter synchronization: passed
- Governance synchronization: passed
- Registry validation: passed
- Local commit: `0314a99` (`Fix TailTrail Start context carryover`)
- Push status: blocked by GitHub HTTP 403 because the authenticated account
  `vsingha7_uhg` does not have write access to `vishrutsinghal/tailr`

## Problem

A user could explicitly invoke `tailtrail start` for one task and later paste
an error, log, or stack trace without invoking Start again. Because the general
TailTrail skill applies to bug fixing and its Navigator guidance listed
`start` alongside ordinary routing commands, chat history could bias an agent
toward creating another Planning Lock or asking for Start approval again.

The intended boundary is:

| Current situation | Expected behavior |
|---|---|
| Current message explicitly invokes TailTrail Start | Create one new Planning Lock and return its Start Report |
| Follow-up contains only an error, log, or stack trace | Do not create a new Planning Lock |
| Existing run is awaiting approval | Reference the same run ID and request approval for that run |
| Existing run is approved | Continue debugging within that run without another Start approval |
| No active run and no explicit Start invocation | Use ordinary TailTrail steady mode or advisory `guide` routing |

## Root Cause

Two instruction paths overlapped:

1. The `tailtrail-start` skill correctly described Start as explicit, but it
   did not state that activation must be evaluated only against the current
   user message.
2. The general `tailtrail` skill automatically applies to coding and bug-fixing
   work and recommended `guide`, `start`, and `next` together for broad or noisy
   tasks. That made an implicit transition into Start possible, especially when
   a prior Start invocation remained in chat history.

This was an instruction-routing problem. The explicit TailTrail CLI commands
were not the root cause.

## Implementation Plan

### 1. Establish a current-turn activation boundary

Update project and skill guidance so TailTrail Start is activated only when the
current user message explicitly requests it. Prior chat mentions must not count
as a new invocation.

### 2. Define negative triggers

Explicitly state that pasted error output, logs, stack traces, and follow-up
debugging requests do not create a new Planning Lock.

### 3. Define existing-run behavior

- Reuse the same run ID when a run is still awaiting approval.
- Continue within an approved run without requesting Start approval again.
- Never create another lock for a follow-up unless the current message
  explicitly invokes Start.

### 4. Separate implicit routing from Start

Keep `guide` as the advisory command for implicit, broad, or noisy coding work.
Remove `start` from the general skill's implicit Navigator command examples.

### 5. Synchronize supported host guidance

Apply the same current-turn rule to the source adapters for Claude, ChatGPT,
GitHub Copilot, Cursor, and Gemini, then regenerate their checked-in target
files using TailTrail's existing adapter synchronization command.

### 6. Add focused regression coverage

Add checks proving that every supported host surface contains the current-turn,
error-output, and new-lock boundaries. Also verify that the general skill's
implicit Navigator section no longer recommends `start`.

### 7. Validate and review

Run focused unit tests, adapter synchronization checks, governance checks,
strict registry validation, and Git whitespace review. Remove generated local
state and Python bytecode artifacts before committing.

## Files Changed

### Core project and skill guidance

#### `AGENTS.md`

- Added the current-user-message activation rule.
- Added errors, logs, stack traces, and follow-up debugging as negative Start
  triggers.
- Defined reuse behavior for awaiting-approval runs.
- Defined continuation behavior for approved runs.
- Directed implicit coding and bug-fixing work to the ordinary TailTrail
  workflow or `guide`.

#### `skills/tailtrail-start/SKILL.md`

- Tightened the skill description so it activates only from the current user
  message.
- Prevented prior Start mentions and follow-up diagnostic text from activating
  the skill.
- Documented pending-run reuse and approved-run continuation.
- Aligned the response wording with the existing contract phrase: “Return the
  complete Start Report verbatim and stop.”

#### `skills/tailtrail/SKILL.md`

- Changed implicit Navigator routing to use advisory `guide` behavior.
- Removed `python3 scripts/tailtrail.py start "user goal"` from implicit routing
  examples.
- Added the current-turn activation boundary and follow-up run behavior.

### Adapter source files

Each source adapter received the same **Current-turn Start boundary** rule:

- `adapters/claude.md`
- `adapters/chatgpt-instructions.md`
- `adapters/copilot-instructions.md`
- `adapters/cursor.mdc`
- `adapters/gemini.md`

The new rule tells each host to:

- Evaluate Start only against the current user message.
- Ignore prior chat mentions and pasted diagnostic output as Start triggers.
- Use ordinary TailTrail guidance or `guide` for implicit bug fixing.
- Reuse an awaiting-approval run ID.
- Continue an approved run without another Start approval.

### Synchronized host targets

The existing adapter synchronizer propagated the source changes to:

- `CLAUDE.md`
- `GEMINI.md`
- `.github/copilot-instructions.md`
- `.openai/chatgpt-instructions.md`
- `.cursor/rules/tailtrail.mdc`

### TailTrail Start prompt

#### `.github/prompts/tailtrail-start.prompt.md`

- Added “Planning Lock” to the prompt description.
- Aligned the stop instruction with the tested contract phrase: “Return the
  complete Start Report verbatim and stop.”

These two adjustments also repaired pre-existing failures in the Start
entrypoint contract test on `master`.

### Regression tests

#### `tests/test_start_entrypoints.py`

Added `test_start_trigger_is_limited_to_the_current_user_message`, which checks
all supported project, adapter, and skill guidance for:

- `current user message`
- `error output`
- `new Planning Lock`

Added `test_implicit_navigator_routing_does_not_recommend_start`, which verifies
that the general skill's implicit Navigator section does not contain the Start
command example.

## Intentionally Unchanged

- `tailtrail start` CLI behavior remains unchanged.
- The explicit `tailtrail do` and `tailtrail run` aliases still route to Start.
- Planning Lock storage, schema, approval enforcement, and run IDs are
  unchanged.
- No new run-completion or lock-closing lifecycle was added.
- No dependencies were added or changed.
- No unrelated formatting or architecture changes were made.

## Validation Evidence

The following focused test command passed:

```bash
python3 -m unittest tests.test_start_entrypoints tests.test_governance_sync tests.test_cli_dispatch
```

Result:

```text
Ran 27 tests in 4.187s
OK
```

The following consistency checks also passed:

```bash
python3 scripts/tailtrail.py adapters check
python3 scripts/tailtrail.py governance check
python3 scripts/tailtrail.py registry validate --strict
git diff --check
```

Test-generated `.tailtrail/` state and Python bytecode changes were removed
after validation. Only the intended guidance, prompt, adapter, and test changes
were included in commit `0314a99`.

## Remaining Delivery Steps

1. Authenticate Git operations with a GitHub account that has write access to
   `vishrutsinghal/tailr`, or grant `vsingha7_uhg` write access.
2. Push local `master`, which is one commit ahead of `origin/master`.
3. Optionally add model-level conversation evaluations covering multi-turn
   behavior. The current tests validate the instruction contract statically;
   they do not execute a live model conversation.
4. After authentication is fixed, include this document in a follow-up commit
   if it should remain as permanent project documentation.

