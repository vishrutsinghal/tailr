# TailTrail Public Demo

This walkthrough demonstrates the approval-first source-checkout workflow without claiming that TailTrail replaces tests, review, scanners, or release approval.

## 1. Verify the checkout

```text
python3 scripts/tailtrail.py doctor
```

The command validates repository contracts and adapter synchronization. A passing result applies only to the checked checkout.

## 2. Create a planning boundary

```text
python3 scripts/tailtrail.py start "fix order quantity validation" --changed path/to/validation.py
```

Review the saved Planning Lock and approve its exact run ID before implementation. Start does not edit source.

## 3. Record real evidence and close

During an approved run, record actual source edits and command outcomes against the saved requirement IDs. Finalize selected harnesses and run the saved closure command. A completion report remains evidence-incomplete when required proof is absent.

## 4. Validate release truth

```text
python3 scripts/public-doc-audit.py
python3 scripts/release-check.py
python3 scripts/smoke-test.py
```

These gates share `release-manifest.json`. The smoke test builds an isolated candidate snapshot before any command creates local `.tailtrail` state.
