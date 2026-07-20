# TailTrail Build Week Video Production Guide

**Target:** 2 minutes 45 seconds, 16:9, 1080p, narrated and captioned.

Record the product honestly. Use OpenMontage to edit the supplied screen clips;
do not use generated terminal, code, test results, or Codex UI.

## Source clips to record

| Clip | Record | Length |
| --- | --- | ---: |
| `01-logo` | TailTrail logo or README hero | 5 sec |
| `02-failing-test` | From `buildweek-demo-project/`, run the test suite and leave the zero-amount failure visible | 12 sec |
| `03-navigator` | Navigator report, especially approval and files to inspect | 18 sec |
| `04-graph` | AST graph symbols, likely test, and impact | 12 sec |
| `05-codex-fix` | Approval in Codex and the one-line `amount < 0` to `amount <= 0` edit | 20 sec |
| `06-passing-test` | The test suite with all three tests passing | 10 sec |
| `07-review-proof` | Review output followed by the Evaluation Harness report | 16 sec |
| `08-close` | TailTrail logo and workflow | 7 sec |

From the submission repository root, record:

```bash
python3 tailtrail/scripts/tailtrail.py start "fix the claim amount validation bug and add focused validation" --root buildweek-demo-project --changed src/claims_api/validation.py
python3 tailtrail/scripts/tailtrail.py graph ast --root buildweek-demo-project --changed src/claims_api/validation.py --depth v2
python3 tailtrail/scripts/tailtrail.py review --root buildweek-demo-project
python3 tailtrail/scripts/tailtrail.py eval scenario report --scenario buildweek-validation
```

For the failing and passing test clips:

```bash
cd buildweek-demo-project
python3 -m unittest discover -s tests -v
```

Use `python` instead of `python3` on Windows if needed.

## Exact 2:45 narration

### 0:00–0:10 — Hook

**Visual:** Logo, then claims-service source.

> AI coding can move fast, but even small tasks can drift into broad edits and
> weak evidence. TailTrail keeps the work focused: plan first, then prove the
> change.

### 0:10–0:28 — Real problem

**Visual:** Intentional zero-dollar test failure.

> This small claims service has one regression. A zero-dollar claim is accepted,
> although every claim amount must be positive. The failing test is intentional:
> it is the exact bug I will fix.

### 0:28–0:53 — Navigator before edits

**Visual:** Navigator report; pause on approval and files to inspect.

> Instead of asking Codex to edit immediately, I start TailTrail Navigator. It
> turns the request into an approval-first plan, identifies the validation code
> and focused test, and keeps implementation behind my decision.

### 0:53–1:08 — Map the scope

**Visual:** Code Graph output.

> The local Code Graph maps the validation function, its caller, and the likely
> regression test. Codex gets the context that matters, rather than a broad
> repository read.

### 1:08–1:42 — Minimal Codex fix

**Visual:** Codex approval, then one-line `amount < 0` to `amount <= 0` edit.

> I approve the plan. Using GPT-5.6, Codex reads the focused scope and makes the
> smallest maintainable fix: zero is now rejected along with negative amounts.
> No new dependency, no rewrite, and no unrelated files changed.

### 1:42–1:57 — Validate

**Visual:** Passing focused test suite.

> The same focused test suite now passes. TailTrail does not declare success for
> us—it makes validation an explicit part of the workflow.

### 1:57–2:28 — Review and evidence

**Visual:** TailTrail review, then Evaluation Harness claim boundaries and
report summary.

> TailTrail reviews requirement fulfillment and code health after the change.
> Its Evaluation Harness replays committed evidence locally. This is
> deterministic saved-artifact proof, not a claim about live model performance
> or exact token savings.

### 2:28–2:45 — Close

**Visual:** Logo and workflow: Navigator, Graph, Approve, Fix, Test, Review,
Evidence.

> TailTrail gives Codex a disciplined local loop: plan, inspect, approve, change,
> validate, review, and preserve evidence. It helps simple code changes stay
> simple.

## OpenMontage prompt

Place the clips above and `assets/brand/tailtrail-mark.png` into an OpenMontage
project. Then give its agent this prompt:

```text
Create a 2-minute-45-second, 16:9, 1080p product demo video for TailTrail, an
OpenAI Build Week Developer Tools submission. Use only the supplied screen
recordings as evidence of the product. Do not generate fake code, terminal
output, test results, Codex UI, or claims that are not visible in the clips.

Audience: OpenAI Build Week judges. Tone: clear, confident, technical, human.
Style: premium but restrained developer-tool launch video. Use midnight navy,
teal, and small amber accents matching the supplied logo. Use the supplied logo
in opening and closing cards. Add accessible captions. Use subtle cuts, zooms,
and callouts so code and terminal output are legible. Avoid flashy transitions,
stock footage, robot imagery, and generic AI visuals. Keep music quiet beneath
narration.

Use this exact timeline and narration:
0:00–0:10: Logo then source. “AI coding can move fast, but even small tasks can
drift into broad edits and weak evidence. TailTrail keeps the work focused: plan
first, then prove the change.”

0:10–0:28: Intentional zero-dollar failing test. “This small claims service has
one regression. A zero-dollar claim is accepted, although every claim amount
must be positive. The failing test is intentional: it is the exact bug I will
fix.”

0:28–0:53: Navigator report. “Instead of asking Codex to edit immediately, I
start TailTrail Navigator. It turns the request into an approval-first plan,
identifies the validation code and focused test, and keeps implementation behind
my decision.”

0:53–1:08: Code Graph. “The local Code Graph maps the validation function, its
caller, and the likely regression test. Codex gets the context that matters,
rather than a broad repository read.”

1:08–1:42: Codex approval and one-line amount less-than-zero to
less-than-or-equal-zero fix. “I approve the plan. Using GPT-5.6, Codex reads the
focused scope and makes the smallest maintainable fix: zero is now rejected
along with negative amounts. No new dependency, no rewrite, and no unrelated
files changed.”

1:42–1:57: Passing test suite. “The same focused test suite now passes.
TailTrail does not declare success for us—it makes validation an explicit part
of the workflow.”

1:57–2:28: Review, then Evaluation Harness report. “TailTrail reviews
requirement fulfillment and code health after the change. Its Evaluation Harness
replays committed evidence locally. This is deterministic saved-artifact proof,
not a claim about live model performance or exact token savings.”

2:28–2:45: Logo and workflow close. “TailTrail gives Codex a disciplined local
loop: plan, inspect, approve, change, validate, review, and preserve evidence.
It helps simple code changes stay simple.”

Before rendering, show me a timeline/storyboard for approval. Render only after
I approve it. Export an MP4 suitable for YouTube upload.
```

## Final check

- [ ] Under three minutes, with narration and readable captions.
- [ ] The failure, one-line fix, and passing test are visibly real.
- [ ] No unsupported token, security, or performance claims were introduced.
- [ ] Watch the final MP4 at normal speed before uploading.
