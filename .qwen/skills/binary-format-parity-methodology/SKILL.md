---
name: binary-format-parity-methodology
description: Phase-based methodology for achieving binary format parity between two implementations of the same specification
source: auto-skill
extracted_at: '2026-06-02T07:28:01.238Z'
---

# Binary Format Parity Methodology

A systematic, phase-based approach to achieving structural alignment between two implementations that produce the same binary format (e.g., AAF, MXF, MOV containers). This methodology was developed for aligning otio-aaf-adapter output with DaVinci Resolve's AAF exports, but applies to any binary format parity task.

## When to Apply

- You have two implementations producing the same binary format
- One implementation is the "golden standard" (reference output)
- The other needs to match the reference for compatibility with downstream tools
- Simple semantic comparison isn't enough — you need byte-level parity analysis
- The format has multiple layers (container → header → structure → content)

## The Five-Phase Approach

### Phase 1: Diagnostic Baseline

**Goal**: Establish a complete, structured inventory of all differences between reference and test outputs.

**Key activities**:
1. Generate test output using your implementation
2. Run multiple diagnostic scripts in parallel:
   - Semantic comparison (property-by-property)
   - Binary comparison (byte-by-byte)
   - Property enumeration (discover all attributes, not just known ones)
   - Dictionary/schema comparison (if format has type definitions)
3. Organize findings into a structured tracker with layers:
   - **L0**: Container/structural layer (e.g., CFB sectors, file layout)
   - **L1**: Header/metadata layer
   - **L2**: Object structure layer (e.g., Mob hierarchy, slot organization)
   - **L3**: Content/descriptor layer (e.g., audio/video descriptors, essence data)
4. Classify each difference:
   - **Controllable**: Can be fixed by changing your implementation
   - **Library-dependent**: Requires changes to underlying library (e.g., pyaaf2)
   - **Whitelisted**: Inherent differences (UUIDs, timestamps, random values)
5. Document expected values for both reference and test in the tracker

**Critical principle**: Use property enumeration, not just known property lists. Reference implementations often set attributes you don't know about.

### Phase 2: Verification Toolchain

**Goal**: Build automated verification that can detect regressions and confirm fixes.

**Key activities**:
1. Create a parity gate script that:
   - Exports test output
   - Runs semantic checks at each layer (L1, L2, L3)
   - Runs binary comparison (info-only until L0 is resolved)
   - Outputs structured PASS/FAIL results
   - Can update the tracker with convergence logs
2. Implement robust alignment strategies:
   - **CompositionMob slots**: Align by SlotID, not index (slot counts may differ)
   - **Other objects**: Align by type → subtype → position order
   - Never align by name when names are expected to differ
3. Map each check to a tracker ID for traceability
4. Document expected baseline results (how many PASS/FAIL/SKIP before any fixes)
5. Use anchor comments in markdown for programmatic updates:
   ```markdown
   | date | diffs | notes |
   <!-- convergence-log-end -->
   ```

**Critical principle**: Binary comparison is useless as a PASS/FAIL criterion when container-level differences dominate. Make it info-only until L0 is resolved.

### Phase 3: L1 + L2 Fixes (Header and Structure)

**Goal**: Fix header metadata and object structure differences.

**Key activities**:
1. Start with L1 (Header):
   - Version numbers
   - Identification metadata (company, product, version strings)
   - Operational patterns
   - Essence container definitions
2. Move to L2 (Structure):
   - Object counts and types
   - Slot organization (alignment by ID, not index)
   - MobID prefixes (may require byte-level patching)
   - Physical track numbers
   - Timecode properties
3. After each fix:
   - Re-export test output
   - Run parity gate
   - Verify target item is fixed
   - Confirm no new failures introduced
   - Update tracker status

**Critical principle**: MobID properties return copies, not references. You must read → modify → reassign to persist changes.

### Phase 4: L3 Fixes (Descriptors and Essence)

**Goal**: Fix content descriptors and embedded essence data.

**Key activities**:
1. Enumerate all descriptor properties in reference output
2. Identify missing or incorrect properties in test output
3. For embedded binary data (e.g., WAV headers in AAF Summary):
   - **Never hardcode values** — read from actual source files
   - Handle non-standard chunk ordering (JUNK, bext before fmt)
   - Standardize extensible formats to basic formats (e.g., WAVE_FORMAT_EXTENSIBLE → PCM)
   - Calculate real sizes, not zero placeholders
4. Fix one property at a time, verify after each

**Critical principle**: Reference implementations read actual source files to build embedded data. Hardcoding values (even "reasonable defaults") will cause mismatches.

### Phase 5: Regression + L0 Investigation

**Goal**: Confirm no regressions, investigate remaining binary differences, document final state.

**Key activities**:
1. Run full test suite
2. Use baseline comparison method for test failures:
   - Stash changes, run tests (baseline failures)
   - Pop changes, run tests (current failures)
   - Only investigate NEW failures
3. Investigate L0 (container) differences:
   - Analyze container structure (sector sizes, stream layout)
   - Classify differences as structural vs semantic
   - Document that structural differences don't affect compatibility
4. Append final conclusion to tracker:
   - Semantic alignment results (L1/L2/L3 all PASS)
   - Binary difference classification (L0 structural only)
   - Pro Tools compatibility status (if applicable)

**Critical principle**: Pre-existing test failures are not your responsibility. Focus on not introducing NEW failures.

## Key Patterns

### Parity Tracker Structure

```markdown
| # | Layer | Property | Reference | Test | Status | Notes |
|---|-------|----------|-----------|------|--------|-------|
| 1 | L1 | Header.Version | {1,1} | {1,2} | FIXED | pyaaf2 default |
| 2 | L2 | CompositionMob.Slot[1].name | "" | "TC" | FIXED | Removed hardcoded name |
```

**Columns**:
- `#`: Unique tracker ID for cross-referencing
- `Layer`: L0/L1/L2/L3 classification
- `Property`: Full property path
- `Reference`: Value in golden standard
- `Test`: Value in your output
- `Status`: OPEN, FIXED, WHITELIST, BLOCKED
- `Notes`: Root cause or fix description

### Layered Comparison Strategy

| Layer | Scope | When Binary Comparison Matters |
|-------|-------|--------------------------------|
| L0 | Container (sectors, streams) | Never — always structural |
| L1 | Header (version, identification) | Only after L1 semantic PASS |
| L2 | Structure (mobs, slots, tracks) | Only after L2 semantic PASS |
| L3 | Content (descriptors, essence) | Only after L3 semantic PASS |

### Convergence Logging

Track progress over time:

```markdown
| Date | Semantic Diffs | Binary Diffs | Notes |
|------|----------------|--------------|-------|
| 2026-06-02 | 24 | 36333 | Initial baseline |
| 2026-06-02 | 5 | 36333 | L1+L2 fixed, L3 remaining |
| 2026-06-02 | 0 | 36333 | All semantic fixed |
```

## Common Pitfalls

0. **Misidentifying reference vs test files**: This is the #1 mistake that invalidates entire analysis sessions. Before ANY comparison, you MUST explicitly confirm file identities.

   **CRITICAL LESSON FROM 2026-06-05**: In a real-world session, the AI misidentified files **3+ times** despite having documentation, causing the user to repeatedly correct the analysis:
   
   - First mistake: Assumed `_testdata_new.aaf` was OTIO output based on filename
   - Second mistake: After user correction, still got confused about `correct_timeline.aaf` role
   - Third mistake: Mixed up which file was the golden standard during UUID analysis
   
   **Prevention protocol**:
   ```bash
   # BEFORE starting any comparison, verify file identities:
   # 1. Ask the user explicitly (don't assume from filenames)
   # 2. Inspect file metadata to confirm
   
   # Example verification:
   uv run python -c "
   import aaf2
   for path in ['file1.aaf', 'file2.aaf']:
       with aaf2.open(path) as f:
           ident = list(f.header['IdentificationList'].value)[0]
           company = ident['CompanyName'].value
           product = ident['ProductName'].value
           print(f'{path}: {company} - {product}')
   "
   
   # 3. Document identities at the top of your analysis:
   # GOLDEN STANDARD: test_data/file_20260515.20260602163810.aaf (DaVinci Resolve)
   # TEST OUTPUT: test_data/file_testdata_new.aaf (OTIO export)
   # SIMPLE REFERENCE: correct_timeline.aaf (DaVinci, no OperationGroup)
   ```
   
   **Filename patterns are UNRELIABLE**:
   - `_new` doesn't mean "new version" — could mean "newly generated test"
   - Timestamps like `_20260515.20260602163810` don't indicate source
   - `correct` doesn't mean "golden standard" — could be simple test case
   
   **Always verify with metadata**, not filenames. Getting this backwards invalidates ALL conclusions and wastes significant time.

1. **Assuming binary comparison is useful early**: When L0 differences exist (e.g., sector size), they cause thousands of cascading binary diffs. Binary comparison is noise until L0 is resolved.

2. **Hardcoding embedded data**: Reference implementations read actual source files. Your implementation must too.

3. **Index-based alignment**: When object counts differ (e.g., extra video slot), index alignment causes cascade failures. Use ID-based or type-based alignment.

4. **Property access confusion**: Many libraries have non-obvious APIs. `.get()` may return wrapper objects, not values. Always test with `type()` and `print()`.

5. **Modification persistence**: Properties may return copies. Read → modify → reassign pattern is essential.

6. **Incomplete enumeration**: Reference implementations set attributes you don't know about. Use `enumerate_all_properties()`, not just known property lists.

7. **Ignoring pre-existing failures**: Test suites often have pre-existing failures. Use baseline comparison to isolate your changes' impact.

## Success Metrics

A successful parity alignment achieves:
- **L1/L2/L3**: All semantic checks PASS (0 differences)
- **L0**: All binary differences classified as structural (not semantic)
- **Tests**: No new failures introduced (pre-existing failures are acceptable)
- **Compatibility**: Downstream tools (e.g., Pro Tools) accept the output

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Binary-first approach | Thousands of diffs, impossible to triage | Semantic-first (L1→L2→L3), then L0 |
| Hardcoded defaults | Mismatches with reference | Read actual source files |
| Index alignment | Cascade failures when counts differ | ID-based or type-based alignment |
| Ignoring library defaults | pyaaf2/etc may have wrong defaults | Patch library properties explicitly |
| No traceability | Can't track which fix resolved which diff | Use numbered tracker IDs |
| Fragile updates | String matching breaks when format changes | Use anchor comments |

## When to Stop

Stop when:
1. All semantic differences (L1/L2/L3) are resolved
2. Remaining binary differences are all L0 (structural)
3. Downstream tools accept the output
4. No new test failures introduced

Don't pursue:
- L0 structural alignment (different libraries have different implementations)
- 100% binary identity (impossible with different libraries)
- Fixing pre-existing test failures (not your responsibility)

## Pro Tools AAF Compatibility: What Actually Matters

After extensive testing with Pro Tools, these are the findings on what Pro Tools actually checks:

### Things That DON'T Matter
- **AAF Version field**: Both 1.1 and 1.2 work. DaVinci Resolve writes 1.1, but Pro Tools accepts 1.2.
- **CFB SectorSize**: Pro Tools correctly parses both 4096-byte and other sector sizes.
- **Dictionary differences**: Extra ClassDefinitions/TypeDefinitions don't cause issues.
- **UUID differences**: MobID UUIDs and Identification UUIDs are expected to differ.
- **Timestamp differences**: Identification dates are expected to differ.

### Things That DO Matter
- **WAV Summary content**: Pro Tools reads the embedded WAV header from WAVEDescriptor.Summary. Hardcoded values (especially bits_per_sample) cause misinterpretation.
- **PhysicalTrackNumber**: Must be set on all Mob slots (CompositionMob, MasterMob, SourceMob).
- **MobID prefix bytes [8:12]**: Must match expected values (e.g., `01010d43` for DaVinci Resolve style).
- **Slot organization**: Extra slots (e.g., unnecessary video slots) can confuse Pro Tools.
- **Timecode properties**: Length, start, fps must be correct and consistent.

### The 30Hz Bug Root Cause
Pro Tools was displaying 30Hz instead of 48000Hz because:
1. The adapter hardcoded a 16-bit WAV header template instead of reading the actual WAV file
2. The actual WAV was 24-bit, causing byte_rate/block_align/bits_per_sample mismatches
3. Pro Tools likely used these mismatched values to calculate timing

### Key Lesson
**Never hardcode embedded binary data** — reference implementations read actual source files. This applies to:
- WAV headers in AAF Summary
- Video frame data in essence containers
- Any embedded binary structures

## Commit Organization for Parity Projects

When committing parity work, keep it professional — **only ship what downstream users need**.

### Include
- Core fixes (modified source files)
- Test fixtures (SimpleTimeline.otio, correct_timeline.aaf)
- Updated .gitignore

### Include in subdirectories (not project root)
- `tools/` — verification and export scripts (parity_gate.py, test_export.py)
- `diagnostics/` — comparison and enumeration scripts

### Exclude (via .gitignore)
- **Intermediate planning documents** (docs/parity_plan/, phase plans) — these are internal process artifacts, not deliverables
- **Tracking documents** (parity_tracker.md) — internal process artifact, the fixes are in the code
- Temporary diagnostic scripts (check_*.py, analyze_*.py)
- Test outputs (test_output.aaf, result.aaf, *.txt, *.csv)
- Journey notes and debug docs (AAF_Debug_Journey.md, etc.)
- Library forks (pyaaf2/) unless you're maintaining them
- IDE and editor files

### Key principle
Don't commit your **process** — commit your **product**. Planning docs, trackers, and journey notes show the messy path to the solution. The repo should only show the clean result. If someone needs to understand the changes, the commit message and code diffs should be self-explanatory.

### Commit Message Structure
```
feat(scope): Brief description

Root cause: What was wrong
Fix: What you changed

Key changes:
- Change 1
- Change 2

Verification:
- Tool 1 result
- Tool 2 result

Result: Final outcome
```

## Git Workflow for Parity Projects

### Rebase for Message Cleanup
When you have commits with poor messages (e.g., "vibe editting"), use interactive rebase:

```bash
# Create two helper scripts
# 1. reword_editor.py - for GIT_SEQUENCE_EDITOR
import sys
f = sys.argv[1]
lines = open(f, 'r').readlines()
for i, line in enumerate(lines):
    if line.startswith('pick'):
        lines[i] = line.replace('pick', 'reword', 1)
        break
open(f, 'w').writelines(lines)

# 2. commit_msg_editor.py - for GIT_EDITOR
import sys
f = sys.argv[1]
new_message = "refactor(scope): Proper message\n\n- Details\n"
open(f, 'w').write(new_message)

# Run rebase
git rebase -i HEAD~2  # Adjust number as needed
# Set environment variables to use your scripts
```

### When to Fork Libraries
- Fork when you need library modifications for compatibility
- Test if the modification is actually necessary (e.g., AAF Version 1.1 vs 1.2)
- If the modification isn't needed, don't maintain the fork
- If it is needed, push to fork and update project dependencies
