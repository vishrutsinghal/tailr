# TailTrail-Guided Artifact

Plan:

- Read the mapper and existing validation path before editing.
- Reuse the existing `validate_claim` safeguard.
- Avoid a new dependency; standard string handling is enough.
- Keep the smallest maintainable diff.

Proposed fix:

```diff
diff --git a/src/claims/mapper.py b/src/claims/mapper.py
--- a/src/claims/mapper.py
+++ b/src/claims/mapper.py
@@ -1,9 +1,10 @@
 def map_claim(raw):
     validate_claim(raw)
     if raw.get("member_id") is None:
         raise ValueError("member_id is required")
     claim = {}
-    claim["member_id"] = raw["member_id"].strip()
+    member_id = str(raw["member_id"]).strip()
+    claim["member_id"] = member_id.zfill(10)
     claim["amount"] = raw.get("amount", 0)
     return claim
```

Review findings:

- Dependency avoided: no package added; standard library string handling is enough.
- Safeguard preserved: `validate_claim(raw)` and the explicit `member_id` guard remain.
- Validation evidence: not run. Recommended check is `python3 -m pytest tests/test_claim_mapper.py`.
- Residual risk: confirm that zero-fill width 10 matches existing downstream claim ID expectations.

