---
name: verification-toolchain-review
description: Methodology for critically reviewing automated parity/comparison tool designs against empirical baseline data
source: auto-skill
extracted_at: '2026-06-02T03:41:29.675Z'
---

# Verification Toolchain Design Review

A methodology for reviewing the design of automated comparison/parity tools — specifically checking them against empirical baseline data to catch gaps, contradictions, and unrealistic assumptions before implementation.

## When to Apply

When someone has written a detailed plan for an automated tool that compares two outputs (file formats, API responses, serialized data, etc.) and you need to validate the plan is internally consistent and grounded in reality.

## Review Checklist

### 1. Completeness Against Known Differences

**Check**: Does the tool's check list cover every item in the known difference inventory?

- Map each known difference to a specific check ID
- Flag any difference with no corresponding check
- Flag any check with no corresponding known difference (may be fine, but verify)
- The plan should explicitly state this mapping, not leave it implicit

**Common failure**: Plan claims "every item must be implemented" but the check list is missing items that were found during baseline analysis.

### 2. Alignment Strategy Robustness

**Check**: Will the alignment/matching logic work when values necessarily differ?

Common alignment pitfalls:
- **Matching by name** when names are expected to differ (e.g., file name vs clip name)
- **Matching by index** when ordering may vary
- **Assuming 1:1 correspondence** when counts may differ

**Better approach**: Use structural properties that are stable (type → subtype → position order) rather than values that may change.

### 3. Binary vs Semantic Comparison Scope

**Check**: Is binary-level comparison used appropriately?

Red flags:
- Binary comparison used as PASS/FAIL criterion when container-level noise dominates
- Complex whitelisting schemes for binary diffs that could be handled at the semantic layer
- Plan describes both "complex approach" and "simplified fallback" for the same feature — means the author isn't committed to either

**Rule**: If a single structural difference (e.g., sector size, encoding format) causes thousands of cascading binary diffs, binary comparison should be **info-only** until that structural difference is resolved.

### 4. Expected Baseline Documentation

**Check**: Does the plan explicitly document which checks should PASS, FAIL, or SKIP on the current baseline?

Without this, you cannot validate the tool against reality. The plan should include:
- A table of expected results for each check
- The specific expected values for both "correct" and "test" sides
- A count of expected FAILs that can be used as an acceptance test

### 5. Tracker ID Mapping

**Check**: Does each automated check link back to a numbered item in the difference inventory?

Without `tracker_id` fields, there's no way to:
- Know which difference was fixed when a check starts passing
- Verify no differences were missed
- Track convergence over time

### 6. Update Mechanism Robustness

**Check**: If the tool updates a tracking document, is the update mechanism resilient?

Fragile patterns:
- String matching on table rows (breaks if formatting changes)
- Appending to end of file (breaks if file has sections after the table)

Robust patterns:
- Anchor comments (`<!-- marker -->`) as insertion points
- Structured data files (JSON/YAML) instead of markdown

### 7. Example Output vs Reality

**Check**: Do the example outputs in the plan match what would actually happen?

Common failures:
- Example shows mostly PASS results when baseline data shows many FAILs
- Example omits categories of differences that are known to exist
- Example uses placeholder values instead of actual baseline values

## Structural Anti-Patterns

| Anti-Pattern | Problem | Fix |
|---|---|---|
| Self-contradicting design | Plan describes complex approach then says "or just simplify" | Pick one approach and commit |
| Implicit mapping | Check IDs don't reference difference inventory | Add explicit `tracker_id` field |
| Optimistic alignment | Alignment relies on values matching when they're known to differ | Use type+position alignment |
| Binary as judge | Binary diff used for PASS/FAIL when noise dominates | Make binary info-only |
| Unvalidated baseline | No explicit expected PASS/FAIL list | Add expected results table |
| Fragile updates | Markdown updates via string matching | Use anchor comments |

### 8. Cross-Check Against Actual Tool Output

**Check**: Does the plan match what the verification tool actually outputs?

After implementing the verification tool (or if it already exists), run it and compare the actual output against the plan's claims:
- Do expected values in the plan match actual `expected` values from the tool?
- Do the plan's "already fixed" items actually show PASS?
- Does the plan account for ALL FAIL items, including ones discovered during tool implementation?

**Common failures found in practice**:
- Plan says "ProductVersionString should be '19.0.0.000'" but actual correct file has `"Unknown version"` — the plan got the expected value backwards
- Plan lists expected values as "needs verification" but actual tool output shows the exact values
- Plan says "Mob structure should be X" but tool reveals MobID prefix differences the plan never mentioned
- Plan documents timecode length as 219 when actual correct file has 220

**Process**: 
1. Run the tool with `--verbose` or equivalent
2. For each FAIL item, verify the plan documents it with correct expected/actual values
3. For each PASS item, verify the plan doesn't claim it needs fixing

### 9. Implementation Gotchas That Plans Often Miss

When reviewing plans for comparison tools, check for these implementation-level issues:

| Gotcha | Description | How to Catch |
|--------|-------------|--------------|
| API returns wrapper objects | `.get()` returns Property objects, not values | Run a test script, compare output types |
| Index vs ID alignment | Slot count differences break index alignment | Check if alignment strategy handles unequal counts |
| Cascade false failures | One structural difference causes many downstream FAILs | Count FAILs — if way more than expected, check alignment |
| Hardcoded test data | Plan references wrong expected values | Cross-check against actual tool output |

### 10. Acceptance Criteria Realism

**Check**: Are the acceptance criteria actually achievable given the constraints?

Common unrealistic criteria:
- "All tests must pass" when pre-existing failures exist → Should be "no NEW test failures"
- "Binary difference count must decrease significantly" when L0 structural differences dominate → Binary comparison is info-only until L0 is resolved
- "Zero differences" when some differences are inherent (UUIDs, timestamps) → Should use WHITELIST status

**Better approach**: Use baseline comparison method:
- Document pre-existing failures (e.g., "8 tests fail on original code")
- Acceptance = "same number or fewer failures after changes"
- Binary differences = "classified as structural, not eliminated"

### 11. Redundant Deliverables

**Check**: Does the plan ask for multiple documents that cover the same information?

Common redundancy:
- Separate "final report" document when tracker already has all information
- Multiple status tracking mechanisms (tracker + report + summary)
- Detailed phase plans that duplicate information in the main tracker

**Fix**: Use a single source of truth (e.g., parity_tracker.md) and append a "Final Conclusion" section instead of creating a separate report document.

### 12. Scope Creep from Related Problems

**Check**: Does the plan include solutions to related but different problems?

Example: A plan for "making our AAF compatible with Pro Tools" might drift into "replacing Pro Tools' AAF parsing DLL" — these are different problems with different solutions.

**Fix**: Keep the plan focused on the stated goal. Related problems should be separate plans.

### 13. Library Fork vs Upstream Strategy

**Check**: If the plan requires modifying a dependency library, is there a clear strategy?

Three options:
1. **Upstream PR**: Submit changes to main library (best if changes are broadly useful)
2. **Local fork**: Maintain a fork with your changes (good if changes are project-specific)
3. **Test if needed**: Verify the modification is actually required before forking

**Process**:
1. Make the library modification
2. Test if the downstream tool works without it
3. If it works without the modification, don't fork
4. If it needs the modification, decide upstream vs fork based on generality

### 14. Commit and Deliverable Scope

**Check**: Does the plan ask for deliverables that are internal process artifacts, not project deliverables?

Common mistakes:
- Plan requires committing planning documents (phase plans, design docs) to the repo
- Plan requires committing tracking documents (parity_tracker.md) to the repo
- Plan puts tools/scripts in the project root instead of subdirectories
- Plan creates multiple overlapping documents (tracker + report + summary)

**Rule**: Don't commit your **process** — commit your **product**. Intermediate planning docs and trackers are useful during development but shouldn't pollute the repo. If a plan asks for deliverables, each should either be:
- Source code (fixes, features)
- Tests or test fixtures
- Tools in appropriate subdirectories (`tools/`, `diagnostics/`)
- User-facing documentation (README, API docs)

Everything else (phase plans, trackers, journey notes, debug logs) should be excluded via .gitignore.

## Output of Review

Present findings as:
1. **Severity-ranked list** of issues (structural problems first, details last)
2. **Direct, no-preamble** critique — skip "this is a good plan but..." framing
3. **Concrete fix suggestions** for each issue, not just "this is wrong"
4. **Mapping table** showing which known differences are/aren't covered
5. **Cross-check results** comparing plan claims against actual tool output
