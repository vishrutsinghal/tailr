# TailTrail Build Week Video Script

Target duration: 2 minutes 45 seconds. This leaves margin below the Build Week
three-minute limit.

## 0:00-0:20 - Hook

**Screen:** Title card, then the claims service.

**Say:**

> Codex can move fast, but a vague coding task can still cause broad context
> reads, premature edits, and weak validation evidence. TailTrail is a local,
> approval-first control layer that helps keep Codex work focused and reviewable.

## 0:20-0:40 - Problem

**Screen:** Run the intentionally failing test.

```bash
python3 -m unittest discover -s buildweek-demo-project/tests
```

**Say:**

> This small claims service has one regression: zero-dollar claims are accepted,
> even though every claim amount must be positive. Instead of immediately asking
> Codex to edit code, I start with TailTrail Navigator.

## 0:40-1:10 - Plan and inspect

**Screen:** Run Navigator, then Code Graph.

```bash
python3 scripts/tailtrail.py start "fix the claim amount validation bug and add focused validation" --root buildweek-demo-project --changed src/claims_api/validation.py
python3 scripts/tailtrail.py graph ast --root buildweek-demo-project --changed src/claims_api/validation.py --depth v2
```

**Say:**

> Navigator selects a lean bug-fix workflow, recommends the exact files to
> inspect, and keeps implementation behind approval. The local Code Graph maps
> the validation function, its likely caller, and the focused regression test.
> That gives Codex targeted context instead of a broad repository read.

## 1:10-1:50 - Codex change and validation

**Screen:** In Codex, approve the plan. Show it read the focused files and make
the one-line change from `amount < 0` to `amount <= 0`. Run the tests.

```bash
python3 -m unittest discover -s buildweek-demo-project/tests
```

**Say:**

> I now approve the plan. Codex, using GPT-5.6, makes the smallest requested
> change and preserves the existing validation behavior. The focused tests now
> pass.

## 1:50-2:15 - Review

**Screen:**

```bash
python3 scripts/tailtrail.py review --root buildweek-demo-project
```

**Say:**

> TailTrail then reviews the changed scope for code health and requirement
> fulfillment. It is not another automatic fixer: it leaves any follow-up action
> under developer control.

## 2:15-2:35 - Repeatable evidence

**Screen:**

```bash
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
```

**Say:**

> The same story is captured as a deterministic, local Evaluation Harness
> scenario. Judges can replay it without a model/API key, network access, or a
> rebuild. It is saved-artifact evidence for this workflow, not a claim about
> live model performance or exact token savings.

## 2:35-2:45 - Close

**Screen:** TailTrail logo and the workflow.

**Say:**

> TailTrail helps teams use Codex with a clear local loop: plan, inspect,
> approve, change, validate, review, and preserve evidence.

## Submission note

In the Devpost form, submit the `/feedback` Session ID from the primary Codex
thread where the project was built. The video narration explains the Codex and
GPT-5.6 role; the README provides the setup and judge test path.
