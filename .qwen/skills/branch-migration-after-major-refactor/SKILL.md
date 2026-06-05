---
name: branch-migration-after-major-refactor
description: Strategy for migrating feature branch changes when upstream has undergone major architectural refactoring
source: auto-skill
extracted_at: '2026-06-05T10:30:00.000Z'
---

# Branch Migration After Major Refactor

## When to Apply

- Your feature branch is based on an old version of main (months/years old)
- Upstream has undergone significant architectural changes (refactoring, API changes, structural reorganization)
- Cherry-picking your commits causes conflicts or doesn't work with new architecture
- You need to preserve the **intent** of your changes while adapting to new structure

## Recognition Signs

You need this workflow when:

1. **Cherry-pick conflicts**: `git cherry-pick` fails with conflicts in most files
2. **Architectural mismatch**: Your changes assume APIs/structures that no longer exist
3. **Large time gap**: Your branch diverged 6+ months ago
4. **Major upstream commits**: Upstream has commits like "refactor", "restructure", "rewrite", "redesign"
5. **Test failures**: After cherry-pick, tests fail because they expect new architecture

## The Four-Phase Migration Strategy

### Phase 1: Assess Upstream Changes

**Goal**: Understand what changed upstream and why.

```bash
# See all commits between your base and current main
git log your_base_commit..origin/main --oneline

# Focus on architectural changes
git log your_base_commit..origin/main --grep="refactor\|restructure\|rewrite" --oneline

# See which files changed most
git diff --stat your_base_commit..origin/main | sort -k2 -rn | head -20
```

**Key questions**:
- What major refactoring happened? (e.g., "mastermob_refactor_v1")
- Which files were most affected?
- What new patterns/APIs were introduced?
- Are there breaking changes you must adapt to?

**Example from otio-aaf-adapter**:
- Main branch had `mastermob_refactor_v1` (May 2025)
- Completely restructured Mob parsing logic
- Changed how OperationGroups are handled
- Modified test expectations

### Phase 2: Document Your Changes

**Goal**: Extract the **intent** of your changes, not just the code.

Create a migration document:

```markdown
# Migration Guide: Dev Branch → Main (New Architecture)

## Critical Fixes (Must Preserve)

1. **OperationDef UUID** (Pro Tools compatibility)
   - Intent: Use correct UUID `9d2ea894-0968-11d3-8a38-0050040ef7d2`
   - Old code: `aaf_writer.py:33`
   - New code: Need to find equivalent location in refactored code

2. **SourceClip StartTime** (Pro Tools compatibility)
   - Intent: Set to 0 inside OperationGroup, not timeline offset
   - Old code: `aaf_writer.py:618`
   - New code: Need to find where SourceClips are created

3. **Audio sampling rate detection**
   - Intent: Read from actual WAV files, not hardcoded 48000
   - Old code: `aaf_writer.py:892-950`
   - New code: May need different approach in new architecture

## Nice-to-Have Improvements

4. **MobID prefix patching**
   - Intent: Match DaVinci Resolve MobID bytes [8:12]
   - Priority: Medium

5. **PhysicalTrackNumber**
   - Intent: Add to all MobSlots
   - Priority: Medium

## Optional Features

6. **Audio transcoding**
   - Intent: Auto-transcode to 48kHz/24bit/mono
   - Priority: Low (can be separate PR)
```

**Why this matters**: Code changes are tied to old architecture. Intent is architecture-agnostic.

### Phase 3: Choose Migration Strategy

#### Strategy A: Reset and Re-implement (Recommended)

**When to use**: Upstream changes are too fundamental, cherry-pick won't work.

```bash
# Start fresh from current main
git checkout -b feature_migrated origin/main

# Manually re-implement changes based on new architecture
# For each item in your migration doc:
#   1. Find the equivalent location in new code
#   2. Adapt your fix to new patterns/APIs
#   3. Test incrementally
```

**Advantages**:
- Clean history
- Adapts to new architecture properly
- No merge conflicts
- Easier to review

**Disadvantages**:
- More manual work
- Risk of missing something
- Loses original commit history

#### Strategy B: Selective Cherry-Pick

**When to use**: Only some changes conflict, others can be cherry-picked cleanly.

```bash
# Create new branch from main
git checkout -b feature_partial origin/main

# Cherry-pick non-conflicting commits
git cherry-pick abc123  # Clean pick
git cherry-pick def456  # Clean pick

# For conflicting commits, manually apply changes
# git cherry-pick ghi789  # Would conflict, skip
# Instead: manually edit files based on migration doc
```

**Advantages**:
- Preserves some commit history
- Less manual work for clean picks

**Disadvantages**:
- Mixed commit styles
- Still need manual work for conflicts
- Harder to review

#### Strategy C: Merge and Resolve

**When to use**: You want to preserve full history and are willing to resolve conflicts.

```bash
# Merge main into your branch
git checkout your_branch
git merge origin/main

# Resolve conflicts manually
# For each conflict, decide:
#   - Keep upstream's new architecture
#   - Adapt your changes to work with it
```

**Advantages**:
- Preserves full history
- Explicit conflict resolution

**Disadvantages**:
- Merge commit with complex history
- Hard to review
- May introduce subtle bugs if conflicts resolved incorrectly

### Phase 4: Verify and Test

**Goal**: Ensure your re-implemented changes work with new architecture.

```bash
# 1. Run existing test suite
uv run pytest tests/ -v

# 2. Compare outputs with reference implementation
# (e.g., DaVinci Resolve for AAF files)
uv run python tools/compare_outputs.py

# 3. Test downstream compatibility
# (e.g., import in Pro Tools)

# 4. Verify specific fixes
uv run python tools/verify_uuid.py
uv run python tools/verify_structure.py
```

**Critical checks**:
- All tests pass (or same failures as main)
- Output files match reference implementation
- Downstream tools accept the output
- Specific fixes are preserved (UUIDs, timestamps, etc.)

## Common Pitfalls

### 1. Blindly Cherry-Picking

**Problem**: Cherry-picking commits without understanding architectural changes.

```bash
# BAD - just cherry-pick and hope for the best
git cherry-pick abc123 def456 ghi789
# Result: Conflicts, broken code, subtle bugs
```

**Solution**: Always understand upstream changes first. Use migration document to guide re-implementation.

### 2. Preserving Implementation Over Intent

**Problem**: Trying to apply exact code changes to new architecture.

```python
# BAD - exact code from old architecture
# This line number doesn't exist in new code!
edit_file("aaf_writer.py", line=618, old_code=..., new_code=...)

# GOOD - adapt to new architecture
# Find where SourceClips are created in new code
# Apply the same intent (StartTime=0) in the right place
```

**Solution**: Focus on **what** you're fixing, not **where** you fixed it before.

### 3. Ignoring New Patterns

**Problem**: Re-implementing using old patterns that new architecture doesn't follow.

```python
# BAD - old pattern (direct property access)
mob.name = "Timeline"

# GOOD - new pattern (may use different API)
mob["Name"].value = "Timeline"
```

**Solution**: Study how new architecture does similar things. Follow its patterns.

### 4. Skipping Verification

**Problem**: Assuming re-implementation is correct without testing.

**Solution**: Always verify:
- Tests pass
- Output matches reference
- Specific fixes are present (check UUIDs, values, etc.)
- Downstream tools work

### 5. Trying to Preserve Everything

**Problem**: Attempting to migrate every change, including experimental/incomplete work.

**Solution**: Prioritize:
- **Critical**: Fixes for blocking issues (Pro Tools compatibility)
- **Important**: Improvements that align with upstream direction
- **Optional**: Nice-to-haves, experimental features

Drop the optional stuff. It can be re-added later if needed.

## Real-World Example: otio-aaf-adapter

### Situation
- Dev branch: Based on March 2024 version
- Main branch: Had `mastermob_refactor_v1` in May 2025
- Goal: Migrate Pro Tools compatibility fixes

### What Changed Upstream
```
1f57821 Merge pull request #44 from markreidvfx/mastermob_refactor_v1
  - Reworked Mob parsing
  - Only MasterMob tracks become OTIO clips
  - CompositionMob → Stacks
  - SourceMobs → MediaReferences
  - More aggressive simplification
```

### Migration Approach

**Phase 1**: Identified that Mob parsing was completely restructured.

**Phase 2**: Documented 6 critical fixes needed:
1. OperationDef UUID
2. ParameterDef name
3. SourceClip StartTime
4. Audio sampling rate detection
5. MobID prefix patching
6. PhysicalTrackNumber

**Phase 3**: Chose Strategy A (reset and re-implement):
```bash
git checkout -b pt_compat origin/main
# Manually re-implement each fix in new architecture
```

**Phase 4**: Verified:
- Exported AAF files matched DaVinci Resolve structure
- All 24 OperationGroups had correct UUIDs
- SourceClip StartTime was 0
- Audio properties were correct

### Result
Successfully migrated 6 critical fixes to new architecture without merge conflicts.

## Decision Framework

Use this flowchart to choose your strategy:

```
Are upstream changes fundamental?
├─ YES → Strategy A (Reset and Re-implement)
│         - Major refactoring
│         - API changes
│         - Structural reorganization
│
└─ NO → Can you cherry-pick cleanly?
         ├─ YES → Strategy B (Selective Cherry-Pick)
         │         - Most commits pick cleanly
         │         - Only 1-2 conflicts
         │
         └─ NO → Do you need full history?
                  ├─ YES → Strategy C (Merge and Resolve)
                  │         - Important to preserve all commits
                  │         - Willing to resolve conflicts
                  │
                  └─ NO → Strategy A (Reset and Re-implement)
                            - Clean slate
                            - Easier to review
```

## Success Metrics

A successful migration achieves:

1. **Functionality preserved**: All critical fixes work in new architecture
2. **Tests pass**: No new test failures (pre-existing failures are OK)
3. **Clean history**: Easy to review, logical commit structure
4. **Architecture aligned**: Follows new patterns, not old ones
5. **Downstream compatible**: Output works with target tools (Pro Tools, etc.)

## When NOT to Migrate

Don't migrate if:

- Your branch is only slightly behind (use `git merge` or `git rebase`)
- Upstream changes are minor (bug fixes, small features)
- Your changes are experimental/throwaway
- You're planning to abandon the branch anyway

## Related Skills

- `pr-branch-extraction-workflow` — Cleaning up branch for PR (use AFTER migration)
- `binary-format-parity-methodology` — Overall parity methodology (migration is one step)
- `parity-project-commit-strategy` — Organizing commits (use when creating migrated commits)
