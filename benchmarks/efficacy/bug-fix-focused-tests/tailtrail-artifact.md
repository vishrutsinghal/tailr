# TailTrail Output

Root cause: blank strings reached `Decimal` before the existing amount guard produced a clear validation error.

Reused existing validation style and kept `validate_amount(raw)`.

```diff
+    if raw is None or not raw.strip():
+        raise ValidationError("amount is required")
     validate_amount(raw)
```

Focused check: `python3 -m pytest tests/test_claim_amount.py::test_blank_amount_is_rejected`.

Validation evidence: not run in this artifact; recommended focused command is listed.

Residual risk: currency-specific formatting should stay covered by existing parser tests.
