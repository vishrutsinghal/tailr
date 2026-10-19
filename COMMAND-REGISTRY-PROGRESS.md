# Command Registry Refactoring - Implementation Progress

## Completed ✅

### 1. planning_lock.py
- ✅ Added `_command_id()` function to generate deterministic command IDs
- ✅ Modified `effective_plan_projection()` to:
  - Build `command_registry` dict mapping command_id → {command, kind}
  - Emit checks with `command_id` instead of `command` string
  - Emit focused_validation rows with `command_id` instead of `command` string
  - Return registry in projection result
  - Include registry in fingerprint calculation

### 2. planning-audit.py  
- ✅ Added `_resolve_command_from_registry()` helper for backward-compatible lookup
- ✅ Updated `_normalize_check()` to handle both `command` (old) and `command_id` (new) fields
- ✅ Updated `_focused_covers()` to:
  - Accept optional `registry` parameter
  - Resolve command_id to actual command for matching
  - Support both old and new formats
- ✅ Updated `_convergence_findings()` to:
  - Pass registry to helper functions
  - Handle command_id resolution in focused_validation validation
  - Support both formats for backward compatibility
- ✅ Updated behaviour tier check to handle command_id

## Not Yet Updated ⏳

### Files still needing changes:

1. **execution-evidence.py** - Needs to resolve command_id when executing
   - `run_command()` function
   - Commands are read from validation_contract.commands (still present)
   - May work with backward compatibility but should verify

2. **task-start.py** - Needs to emit command_id in focused_validation
   - `coalesce_focused_validation_rows()` 
   - `focused_validation_plan()`

3. **closure-finalizer.py** - Needs to resolve command_id in closure
   - Receipt building 
   - Report generation

4. **completion-report.py** - Needs to resolve command_id in reports
   - Display logic

5. **change-intent-anchor.py** - Needs to handle registry in anchors
   - Anchor creation/approval

6. **Tests** (~30+ files) - Need schema updates
   - Test fixtures with hardcoded `commands` and `checks`

## Backward Compatibility Strategy

**Implemented:**
- Code checks for both `command` (old) and `command_id` (new) fields
- Registry lookup falls back gracefully if command_id not found
- Old format (embedded commands) still works

**Status:** Code should work with mixed old/new formats during migration

## Next Steps

1. Run tests to identify actual breaking changes
2. Fix execution path (run_command, evidence collection)
3. Update task-start to emit registry structure
4. Update test fixtures
5. Verify end-to-end flow

## Current Fingerprint Impact

⚠️ **Note:** Fingerprints now include command_registry, which means:
- Old plans without registry will have different fingerprints
- New plans with registry will validate cleanly
- Audit will detect fingerprint-mismatch for pre-existing runs
- This is expected and safe (planning projection changed)

