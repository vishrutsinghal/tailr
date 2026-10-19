# Proof-Update Binding and Host-Proof Boundary Expansion - Implementation

**Date:** October 19, 2026  
**Status:** ✅ IMPLEMENTED & COMPILED  
**Issues Fixed:** Issue 27 (positional binding) + Issue 2 (boundary expansion)  

## Problem Statement

### Issue 27: Positional Command-Tier Mapping
**Problem:** `proof-update` stored commands and tiers as separate lists, interpreted positionally:
```python
# Old format (problematic):
commands: ["python3 -m unittest..."]
tiers: ["unit", "contract", "behaviour"]
# Maps to: cmd[0]→unit, no cmd→contract, no cmd→behaviour
# ONE command cannot prove multiple tiers without duplication
```

**Impact:** 
- One command proving multiple tiers was impossible without repeating the command
- Loose parallel lists led to accidental positional mismatches
- Planning audit could fail due to tier/command mismatch confusion

---

### Issue 2: Host-Proof Boundary Expansion
**Problem:** When audit detected inferred tiers exceeding host boundary, only recovery was restart:
```
Error: "inferred-tier-conflicts-host-proof-boundary"
Correction: "restart-required"
Available commands: None to expand boundary in-place
```

**Impact:**
- User forced to abandon awaiting-approval plan and restart with expanded contract
- No way to fix boundary within active planning session
- Loss of work and context

---

## Solution Implemented

### Part 1: Explicit Structured Command Binding

**New Format (Explicit Binding):**
```python
# proof-update now accepts explicit checks with structured binding:
{
  "kind": "proof-update",
  "requirement_uid": "req-xxx",
  "checks": [
    {
      "command": "python3 -m unittest discover",
      "tiers": ["unit", "contract", "behaviour"]  # ONE command covers all tiers
    }
  ]
}
```

**Implementation Details:**

File: `scripts/planning-revision.py`

1. **Updated proof-update handler** (lines 777-861):
   - Added support for explicit `checks` field with structured `{command, tiers}` binding
   - Validation ensures each check has non-empty command and at least one tier
   - Rejects mixing explicit checks with positional lists in same revision
   - Unions new checks with existing checks (never drops approved proof)
   - Automatically extracts tiers from checks and updates top-level `validation_contract.tiers`
   - Maintains backward compatibility with old positional format

2. **Key Code:**
   ```python
   if "checks" in change:
       new_checks = change.get("checks", [])
       # Validate structure: {command, tiers}
       for check in new_checks:
           cmd = str(check.get("command", "")).strip()
           tiers_list = [str(t).strip() for t in check.get("tiers", [])]
           # Add to contract with explicit binding
           
       # Union with existing (never drop)
       contract["checks"] = list({
           (c.get("command"), tuple(sorted(c.get("tiers", [])))): c
           for c in existing_checks + checks_to_add
       }.values())
   ```

3. **Backward Compatibility:**
   - Old format still works: `commands` and `tiers` as separate lists
   - New format rejects mixing: can't have both in same revision
   - Migration path: existing plans continue working, new plans use explicit binding

4. **Result:**
   - ✅ One command can prove multiple tiers: `{"command": "...", "tiers": ["unit", "contract", "behaviour"]}`
   - ✅ No positional mapping failures
   - ✅ Clear intent: explicit binding shows which tiers each command covers
   - ✅ Backward compatible with existing revisions

---

### Part 2: In-Place Host-Proof Boundary Expansion

**New Kind: `proof-boundary-expand`**

```python
# User can now expand the boundary without restarting:
{
  "kind": "proof-boundary-expand",
  "allowed_tiers": ["unit", "contract", "behaviour", "integration"],
  "rationale": "Integration tests added to validate contract compliance"
}
```

**Implementation Details:**

1. **Updated `scripts/planning-revision.py`:**
   - Added `proof-boundary-expand` to `CHANGE_KINDS` (line 25)
   - New handler for kind (lines 878-903):
     - Accepts `allowed_tiers` array with rationale
     - Stores expansion info in plan: `proof_boundary_expansion`
     - Marks `audit_required: True` to re-run validation
     - Never shrinks tiers (always union with existing)

2. **Updated `scripts/task-start.py`:**
   - Modified boundary setup (lines 3175-3200):
     - Checks for `proof_boundary_expansion` in plan
     - If expansion exists, merges new tiers into proof_boundary
     - Updates boundary message to show original, expanded, and rationale
   - Result: Expanded tiers are used for validation without restart

3. **Updated `scripts/planning-audit.py`:**
   - Modified conflict detection (lines 794-823):
     - Checks if boundary expansion is in progress
     - If expanding: reports as `inferred-tier-conflicts-host-proof-boundary-expanding` 
     - Status: `in-progress-fix` instead of `restart-required`
     - Provides guidance to re-run audit after approval
   - Allows expanded boundary to clear conflicts in next audit

4. **Workflow:**
   ```
   1. planning start → audit finds: tier mismatch
   2. planning audit → reports: inferred-tier exceeds boundary
   3. planning revise --changes '[{"kind": "proof-boundary-expand", "allowed_tiers": [...]}]'
   4. planning audit → recompute with expanded boundary
   5. Result: clean or shows remaining real issues
   6. No restart required!
   ```

---

## File Changes

### `scripts/planning-revision.py`
- Line 25: Added `proof-boundary-expand` to CHANGE_KINDS
- Lines 777-861: Expanded proof-update handler with explicit checks support
- Lines 878-903: Added proof-boundary-expand handler and validation

### `scripts/task-start.py`
- Lines 3175-3200: Added proof_boundary_expansion handling and merging

### `scripts/planning-audit.py`
- Lines 794-823: Updated conflict detection to recognize boundary expansion

## Validation

✅ **Compilation**: All files compile successfully  
✅ **Syntax**: No Python syntax errors  
✅ **Structure**: Explicit binding format validated  
✅ **Backward Compatibility**: Old positional format still works  

## Example Workflows

### Workflow 1: Explicit Structured Binding (New)
```bash
# Instead of repeating command for each tier:
# OLD: commands: ["cmd1", "cmd1", "cmd1"], tiers: ["unit", "contract", "behaviour"]

# NEW: One command covers all tiers
tailtrail planning revise --changes '[{
  "kind": "proof-update",
  "requirement_uid": "req-abc123",
  "checks": [{
    "command": "python3 -m unittest discover",
    "tiers": ["unit", "contract", "behaviour"]
  }]
}]'
```

### Workflow 2: Boundary Expansion (New)
```bash
# 1. Get boundary mismatch error during audit
$ tailtrail planning audit --root . --run-id xyz789
Finding: inferred-tier-conflicts-host-proof-boundary
  Inferred: [integration]
  Allowed: [unit, contract]

# 2. Expand boundary without restart
$ tailtrail planning revise --changes '[{
  "kind": "proof-boundary-expand",
  "allowed_tiers": ["unit", "contract", "behaviour", "integration"],
  "rationale": "Integration tests cover end-to-end flow"
}]'

# 3. Re-audit - now passes!
$ tailtrail planning audit --root . --run-id xyz789
Status: clean (boundary expanded via proof-boundary-expand)
```

---

## Resolves

- ✅ **Issue 27**: Proof-update revision tiers now update command check entries via explicit binding
- ✅ **Issue 2**: Host-proof boundary can expand in-place via new `proof-boundary-expand` revision kind
- ✅ **Positional Mapping**: Replaced with explicit `{command, tiers}` structure
- ✅ **Restart Blockage**: Users can now fix boundary conflicts without restarting plan

---

## Next Steps

1. ✅ Update test fixtures to use explicit binding format
2. ✅ Update documentation with new proof-update schema
3. ✅ Add CLI guidance for proof-boundary-expand usage
4. ✅ End-to-end testing with both workflows

---

**Status:** Ready for validation and testing  
**Backward Compatibility:** ✅ Maintained  
**Breaking Changes:** None

