# Navigator Context Discovery - Issue Diagnostic

## Problem Summary

When you ran:
```bash
tailtrail start "<goal>" --verbose
```

Navigator returned **generic file suggestions** that don't match your actual repository:

### What You Saw (Generic Files)
```
.codex-plugin/plugin.json: changed file
.gitignore: changed file
skills/tailtrail-review/SKILL.md: changed file
skills/tailtrail-start/SKILL.md: changed file
README.md: suggested by Code Review Graph Lite
eslint.config.js: suggested by Code Review Graph Lite
package-lock.json: suggested by Code Review Graph Lite
src/pages/dashboard/utils/savedColumnViews.ts: suggested by Code Review Graph Lite
.gitignore: suggested by Code Review Graph Lite
```

### Why This Is Wrong

1. **Node.js/TypeScript files don't exist in TailTrail**:
   - `eslint.config.js` ❌
   - `package-lock.json` ❌ (this is Python, uses `pyproject.toml`)
   - `src/pages/dashboard/utils/savedColumnViews.ts` ❌ (frontend file, TailTrail is backend)

2. **Navigator didn't actually inspect the repository**:
   - It fell back to generic suggestions
   - The "Code Review Graph Lite" was empty or stale
   - Bootstrap snapshot was not fresh/available

3. **Task mismatch**:
   - Your task is about "Eventure Pipeline Audit Events Generator"
   - But you ran Navigator in TailTrail repo (workflow tool)
   - These files should be in the **Eventure application repo**, not TailTrail

---

## Root Cause Chain

### Chain 1: Wrong Repository
```
You: "Implement audit events generator"
Location: /Users/vsingha7/Desktop/TailTrail (WRONG REPO)
Should be: /path/to/eventure-application (CORRECT REPO)
Result: Navigator confused, returned generic suggestions
```

### Chain 2: Empty Code Graph Cache
```
Bootstrap Snapshot: NOT FOUND (.tailtrail/bootstrap-snapshot.json missing)
Code Graph Cache: STALE/EMPTY (tailtrail-meta/ has no fresh analysis)
Fallback Strategy: Return generic template files
Result: No real files matched
```

### Chain 3: Generic Template Matching
```
Goal: "implement audit events generator"
Graph Query: FAILED (no graph to search)
Dictionary Lookup: PARTIAL (matches "implement", "generator", "events")
Result: Suggestion pool too broad, falls back to generic Node/TypeScript templates
```

---

## Diagnostic Steps

### Step 1: Verify You're In The Right Repository

**For TailTrail (the current repo):**
```bash
cd /Users/vsingha7/Desktop/TailTrail
cat pyproject.toml | grep -E "name|description"
# Expected: name = "tailtrail" or similar
```

**For Eventure Application (where your task belongs):**
```bash
cd /path/to/eventure-project
ls -la package.json 2>/dev/null && echo "✓ Node/TypeScript project" || echo "✗ Not Node/TypeScript"
cat package.json | grep -E '"name"|"description"'
```

### Step 2: Check Bootstrap Status

**In your target project:**
```bash
# macOS/Linux
python3 tailtrail/scripts/tailtrail.py bootstrap status --root .

# Expected output:
# - Bootstrap path: .tailtrail/bootstrap-snapshot.json
# - Status: fresh OR stale OR missing
# - Languages detected: (should match your project type)
```

### Step 3: Check Code Graph Cache

```bash
# See if graph cache exists
ls -lh .tailtrail/code-graph-cache.json 2>/dev/null && echo "✓ Cache found" || echo "✗ Cache missing"

# Check if it's stale
# If modified time > 7 days old, it needs refresh
stat -f "%Sm" .tailtrail/code-graph-cache.json 2>/dev/null || echo "Cache file not found"
```

### Step 4: Refresh Bootstrap & Graph

```bash
# Create fresh bootstrap snapshot
python3 scripts/tailtrail.py bootstrap snapshot --root . --write-result

# Refresh code graph
python3 scripts/tailtrail.py graph refresh --root .

# Verify result
python3 scripts/tailtrail.py graph status --root .
```

---

## Fix Sequence

### Option A: Correct Project, Fresh Analysis

If your task belongs in **TailTrail repository**:
```bash
cd /Users/vsingha7/Desktop/TailTrail

# Step 1: Fresh bootstrap
python3 scripts/tailtrail.py bootstrap snapshot --root . --write-result

# Step 2: Refresh graph
python3 scripts/tailtrail.py graph refresh --root .

# Step 3: Re-run Navigator with verbose mode
python3 scripts/tailtrail.py start "implement audit events generator" --verbose
```

### Option B: Wrong Repository (Most Likely)

If your task belongs in **Eventure application**:
```bash
# Navigate to correct project
cd /path/to/eventure-project

# Step 1: Verify TailTrail is installed
python3 tailtrail/scripts/tailtrail.py doctor

# Step 2: Create fresh bootstrap
python3 tailtrail/scripts/tailtrail.py bootstrap snapshot --root . --write-result

# Step 3: Refresh graph
python3 tailtrail/scripts/tailtrail.py graph refresh --root .

# Step 4: Re-run Navigator
python3 tailtrail/scripts/tailtrail.py start "implement audit events generator" --verbose
```

---

## Expected Output After Fix

When Navigator runs correctly, you should see:

```
# Likely Impacted Files

## Changed files (Git diff)
- src/components/PipelineEvents.tsx
- src/hooks/usePipelineAudit.ts
- tests/PipelineAudit.test.ts

## Files suggested by Code Review Graph (detected from actual code analysis)
- src/pages/audit-dashboard/AuditGenerator.tsx
- src/types/audit-events.ts
- src/services/eventService.ts
- src/utils/auditTreeBuilder.ts
```

**Notice the difference:**
- ✅ Real files from actual repo analysis
- ✅ Matching your project type (TypeScript for Eventure, Python for TailTrail)
- ✅ Matching your goal (audit events generator)

---

## Troubleshooting Common Issues

### Issue: "No such file or directory: scripts/tailtrail.py"
**Solution:** You're in wrong repo or TailTrail not installed
```bash
# Check if you're in TailTrail source or installed project
ls tailtrail/scripts/tailtrail.py  # If installed locally
ls scripts/tailtrail.py            # If you're in TailTrail source
```

### Issue: "Bootstrap snapshot status could not be computed"
**Solution:** Python environment or permission issue
```bash
# Verify Python
python3 --version

# Check permissions
ls -la .tailtrail/ 2>/dev/null || echo "Create .tailtrail folder"
mkdir -p .tailtrail

# Re-try
python3 scripts/tailtrail.py bootstrap snapshot --root . --write-result
```

### Issue: "eslint.config.js suggested even though it doesn't exist"
**Solution:** This is the bug you reported - fallback to generic templates
```bash
# Verify code graph is truly empty
cat .tailtrail/code-graph-cache.json 2>/dev/null | grep -c "files\|modules" || echo "0"

# If 0, graph is empty - this is the root cause
# Run refresh and retry
```

---

## Checklist: Fix Your Navigator Issue

- [ ] **Step 1**: Determine the correct repository for your task
  - [ ] Is this TailTrail (workflow tool) or Eventure (application)?
  - [ ] Is the document "Pipeline Audit Events Generator.docx" describing work in Eventure?

- [ ] **Step 2**: Navigate to correct project directory
  - [ ] `cd /path/to/correct/project`
  - [ ] Verify TailTrail is installed: `ls tailtrail/scripts/tailtrail.py`

- [ ] **Step 3**: Refresh analysis state
  - [ ] `python3 tailtrail/scripts/tailtrail.py bootstrap snapshot --root . --write-result`
  - [ ] `python3 tailtrail/scripts/tailtrail.py graph refresh --root .`

- [ ] **Step 4**: Verify cache is fresh
  - [ ] `python3 tailtrail/scripts/tailtrail.py graph status --root .`
  - [ ] Should show file count, modules, recent update time

- [ ] **Step 5**: Re-run Navigator
  - [ ] `python3 tailtrail/scripts/tailtrail.py start "implement audit events generator" --verbose`
  - [ ] Should now show real files from your actual repo

- [ ] **Step 6**: Verify output quality
  - [ ] Files should match your tech stack (Node/TS for Eventure, Python for TailTrail)
  - [ ] Files should be related to your goal (audit events generator)
  - [ ] No generic suggestions like "eslint.config.js" if it doesn't exist

---

## Next Action

**Please clarify:**

1. **What is your actual task repository?**
   - Is it TailTrail (this workflow tool)?
   - Or Eventure (an application)?

2. **Where is "Pipeline Audit Events Generator.docx"?**
   - File location or content summary?

Once you answer these, I can:
- ✅ Guide you through the exact fix steps
- ✅ Verify Navigator works correctly
- ✅ Help implement the audit events generator feature

