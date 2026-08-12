# Navigator Context Discovery - Prevention & Code Review

## Issue Summary

Navigator returned generic placeholder files instead of analyzing actual repository structure:

```
Expected:
- Real source files from the actual repository
- Files matching the project tech stack (Node/TS for Eventure, Python for TailTrail)
- Files related to the audit events generator feature

Actual:
- Generic Node.js/TypeScript template files
- Files that don't exist (eslint.config.js, package-lock.json, src/pages/dashboard/utils/savedColumnViews.ts)
- Fallback suggestions from empty code graph cache
```

---

## Root Cause: Empty Code Graph Cache

Navigator's file discovery uses this priority order:

```
1. Code Graph Analysis (from .tailtrail/code-graph-cache.json)
   ├─ Source file inventory
   ├─ Module relationships
   ├─ Import graph
   └─ Called/caller analysis

2. Bootstrap Snapshot (from .tailtrail/bootstrap-snapshot.json)
   ├─ Project type detection
   ├─ Tech stack detection
   └─ Language/framework detection

3. Git Change Analysis
   ├─ Recent file changes
   └─ Untracked files

4. Goal-Based Dictionary Search (FALLBACK - PROBLEMATIC)
   ├─ Parse goal for keywords
   ├─ Match against generic templates
   └─ RETURNS WRONG FILES ❌
```

**What Happened:**
- Steps 1-3 returned empty/insufficient results
- Step 4 fallback kicked in with generic templates
- Navigator couldn't distinguish between "Python project with audit logic" and "Node/TypeScript frontend"

---

## Why Code Graph Was Empty

### Possible Cause 1: Stale Cache
```
Last update: > 1 week old
Action: Requires manual refresh with `graph refresh --root .`
Result: Navigator uses outdated data
```

### Possible Cause 2: Bootstrap Never Ran
```
.tailtrail/bootstrap-snapshot.json: MISSING
Reason: First-time setup in repository
Action: Must run `bootstrap snapshot --root . --write-result` first
Result: No tech stack detection, falls back to generic templates
```

### Possible Cause 3: Wrong Repository
```
Current directory: /Users/vsingha7/Desktop/TailTrail (Python project)
Task belongs in: /path/to/eventure (Node/TypeScript project)
Result: Graph populated with Python files, goal searches for "audit events" (frontend)
Mismatch: Generic fallback with Node/TypeScript templates (wrong stack)
```

### Possible Cause 4: Graph Refresh Failed
```
Attempt: `python3 scripts/tailtrail.py graph refresh --root .`
Error: Permissions, disk space, or Python environment issue
Result: Cache remains empty, fallback to templates
```

---

## Prevention: What Should Be Fixed

### Fix 1: Require Fresh Bootstrap Before Navigator

**Current flow:**
```
User: tailtrail start "goal"
Navigator: Check if bootstrap exists
  ├─ If exists: Use it
  ├─ If missing: Try anyway (potential issue)
  └─ If stale: Use stale data
```

**Proposed flow:**
```
User: tailtrail start "goal"
Navigator: Check bootstrap freshness
  ├─ If missing: FAIL and suggest bootstrap snapshot command
  ├─ If > 7 days old: WARN and offer refresh
  ├─ If fresh: CONTINUE
  └─ If error reading: FAIL with diagnostic
```

**Implementation:**
```python
# In navigator.py
def require_fresh_bootstrap(root: Path, max_age_days: int = 7) -> tuple[bool, str]:
    snapshot_path = root / ".tailtrail" / "bootstrap-snapshot.json"
    
    if not snapshot_path.exists():
        return False, f"Bootstrap snapshot missing. Create one with:\n" \
                      f"  python3 scripts/tailtrail.py bootstrap snapshot --root {root} --write-result"
    
    age_days = (datetime.now().timestamp() - snapshot_path.stat().st_mtime) / 86400
    if age_days > max_age_days:
        return False, f"Bootstrap is {age_days:.0f} days old (max: {max_age_days}). Refresh with:\n" \
                      f"  python3 scripts/tailtrail.py bootstrap snapshot --root {root} --write-result"
    
    return True, ""
```

### Fix 2: Fallback Should Match Project Type

**Current fallback:**
```
Goal: "audit events generator"
Dictionary match: ["events", "generator", "implement"]
Template suggestion: Generic Node/TypeScript frontend files
Problem: Matches goal keywords but IGNORES project type
```

**Proposed fallback:**
```
1. Detect project type from bootstrap snapshot
2. Filter templates to match project type
3. THEN match goal keywords
4. If NO MATCH: Return empty list instead of wrong files
```

**Implementation:**
```python
# In navigator.py
def fallback_template_files(goal: str, project_type: str) -> list[str]:
    """Return template files ONLY if they match the project type."""
    
    # Template files by project type
    templates = {
        "python": [
            "scripts/utils.py",
            "src/models.py", 
            "tests/test_models.py",
            "README.md",
            ".gitignore",
        ],
        "typescript": [
            "src/components/Component.tsx",
            "src/hooks/useHook.ts",
            "src/types/types.ts",
            "src/services/service.ts",
            "tests/Component.test.tsx",
            "package.json",
            "tsconfig.json",
        ],
        "javascript": [
            "src/components/Component.jsx",
            "src/hooks/useHook.js",
            "src/services/service.js",
            "package.json",
            ".eslintrc.js",  # Only if project actually uses eslint
        ],
    }
    
    if project_type not in templates:
        # Unknown project type: return nothing, not generic files
        return []
    
    # Only suggest files for this project's type
    return templates[project_type]
```

### Fix 3: Validate Suggested Files Exist

**Current behavior:**
```
Suggest: eslint.config.js
Validate: None (assumes file is template)
Result: Return non-existent file as suggestion
```

**Proposed behavior:**
```
Suggest: eslint.config.js
Validate: Check if file exists or is project convention
Result: Only return if exists OR is standard convention for this type
```

**Implementation:**
```python
def validate_template_suggestions(suggestions: list[str], root: Path, project_type: str) -> list[str]:
    """Filter suggestions: only include files that exist or are project standards."""
    valid = []
    
    # Standard files that MUST exist
    standard_required = {"package.json", ".gitignore", "README.md", "pyproject.toml"}
    
    # Optional files (suggest only if they exist)
    optional = {"eslint.config.js", "tsconfig.json", "tests.py", "pytest.ini"}
    
    for file in suggestions:
        path = root / file
        if file in standard_required:
            # Must exist
            if path.exists():
                valid.append(file)
        elif file in optional:
            # Suggest only if exists
            if path.exists():
                valid.append(file)
        else:
            # Unknown: only add if exists
            if path.exists():
                valid.append(file)
    
    return valid
```

### Fix 4: Clear Fallback Indication

**Current output:**
```
README.md: suggested by Code Review Graph Lite
eslint.config.js: suggested by Code Review Graph Lite
```

**Problem:** User can't tell if these are:
- Real files from code analysis?
- Template suggestions?
- Fallback guesses?

**Proposed output:**
```
README.md: from real code analysis (Code Graph)
eslint.config.js: NOT FOUND - template suggestion (would normally be here)
```

Or better:

```
## Files from Code Analysis (Real)
- src/components/AuditTree.tsx
- src/hooks/useAuditEvents.ts
- src/types/audit.ts

## Template Suggestions (Not in your repo yet)
- (none - code graph analysis was sufficient)

## Analysis Warnings
- Code graph is 3 days old; refresh with: python3 scripts/tailtrail.py graph refresh --root .
```

---

## Code Changes Needed

### File: scripts/navigator.py

**Change 1: Add validation at Navigator entry point**
```python
def start(goal: str, root: Path, verbose: bool = False) -> dict[str, Any]:
    # NEW: Require fresh bootstrap
    is_fresh, msg = require_fresh_bootstrap(root)
    if not is_fresh:
        return {"error": "bootstrap-missing-or-stale", "message": msg}
    
    # Existing code...
    snapshot = load_bootstrap(root)
    graph = load_code_graph(root)
    # ...
```

**Change 2: Improve fallback template matching**
```python
def discover_impacted_files(goal: str, root: Path, graph: CodeGraph, snapshot: Bootstrap) -> FileSuggestions:
    # Try primary: Code graph analysis
    graph_files = analyze_code_graph(goal, graph)
    if graph_files:
        return FileSuggestions(source="code-graph", files=graph_files, confidence="high")
    
    # Try secondary: Goal-based search with proper fallback
    fallback_files = fallback_search_with_validation(goal, root, snapshot.project_type)
    if fallback_files:
        return FileSuggestions(source="fallback-search", files=fallback_files, confidence="low")
    
    # NEW: Return empty rather than generic templates
    return FileSuggestions(source="none", files=[], confidence="unknown",
                          note="No files matched; code graph may need refresh")
```

**Change 3: Add warnings for stale cache**
```python
def format_navigator_report(suggestions: FileSuggestions, graph_age: timedelta) -> str:
    # Existing formatting...
    
    # NEW: Add cache freshness warning
    if graph_age > timedelta(days=3):
        warnings.append(f"Code graph is {graph_age.days} days old. "
                       f"Refresh with: python3 scripts/tailtrail.py graph refresh --root .")
    
    return format_report_with_warnings(suggestions, warnings)
```

---

## Testing the Fix

### Test Case 1: Empty Graph Falls Back Correctly

```python
def test_empty_graph_fallback_matches_project_type():
    # Python project
    result_python = fallback_search("audit events generator", "python")
    assert all(file.endswith(".py") for file in result_python)
    assert "eslint.config.js" not in result_python
    
    # TypeScript project  
    result_ts = fallback_search("audit events generator", "typescript")
    assert all(file.endswith((".ts", ".tsx")) or "json" in file for file in result_ts)
    assert any(".tsx" in file for file in result_ts)  # Component files
```

### Test Case 2: Validates Files Exist

```python
def test_suggestions_validate_existence():
    root = Path("/test/repo")
    suggestions = ["existing.ts", "nonexistent.js", "package.json"]
    
    # Mock: existing.ts exists, nonexistent.js doesn't
    result = validate_template_suggestions(suggestions, root, "typescript")
    
    assert "existing.ts" in result
    assert "nonexistent.js" not in result  # Not suggested if it doesn't exist
```

### Test Case 3: Requires Fresh Bootstrap

```python
def test_navigator_requires_fresh_bootstrap():
    # Missing bootstrap
    root_no_bootstrap = Path("/test/no-bootstrap")
    success, msg = require_fresh_bootstrap(root_no_bootstrap)
    assert not success
    assert "bootstrap snapshot" in msg
    
    # Stale bootstrap (> 7 days)
    root_stale = Path("/test/stale")
    success, msg = require_fresh_bootstrap(root_stale, max_age_days=7)
    assert not success
    assert "Refresh with" in msg
```

---

## Deployment Plan

### Phase 1: Add Validation (Non-Breaking)
- Add bootstrap freshness checks with warnings
- Don't fail, just warn user
- Users see clear instructions to refresh

### Phase 2: Improve Fallback (Non-Breaking)
- Filter template suggestions by project type
- Validate suggested files exist
- Keep returning suggestions, but only valid ones

### Phase 3: Require Bootstrap (Breaking)
- Make fresh bootstrap a hard requirement
- Fail clearly with next steps
- Users can't accidentally run with stale data

### Phase 4: Clear Communication
- Change output formatting to show confidence levels
- Distinguish real analysis from fallback suggestions
- Include warnings about cache age

---

## Summary

**The issue:** Navigator's fallback mechanism was too aggressive, suggesting generic files even when they didn't exist or didn't match the project type.

**The fix:** 
1. Require fresh bootstrap snapshot
2. Match fallback suggestions to project type  
3. Validate suggested files exist
4. Clear communication about data freshness

**Expected outcome:** 
- No more generic TypeScript files suggested for Python projects
- No more non-existent files in suggestions
- Clear guidance when code graph needs refresh
- Users understand WHY files were suggested

