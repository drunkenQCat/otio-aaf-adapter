# Verification Loop Todo List

## Goal
Ensure pt_compat branch produces AAF files that are:
1. Equal or better than dev branch outputs
2. Compatible with DaVinci Resolve exports (when available)
3. Pass all 66 tests (100% pass rate)

## Phase 1: Automated Verification Script

### TODO-1.1: Create unified export script
- [ ] Create `verify_exports.py` that can export from any branch
- [ ] Support specifying test files
- [ ] Generate structured output for comparison
- [ ] Handle both dev and pt_compat branches

### TODO-1.2: Create comparison script
- [ ] Create `compare_aaf_files.py` that compares two AAF files
- [ ] Compare MobID structure
- [ ] Compare timecode tracks
- [ ] Compare source_range values
- [ ] Compare audio track structure
- [ ] Generate detailed comparison report

### TODO-1.3: Create verification loop script
- [ ] Create `run_verification_loop.py`
- [ ] Automate the entire verification process
- [ ] Export from dev branch
- [ ] Export from pt_compat branch
- [ ] Compare outputs
- [ ] Run test suite
- [ ] Generate final report

## Phase 2: Dev Branch Comparison

### TODO-2.1: Export test files from dev branch
- [ ] Checkout dev branch
- [ ] Export all test OTIO files to AAF
- [ ] Save outputs to `exports/dev/` directory
- [ ] Document any issues encountered

### TODO-2.2: Export test files from pt_compat branch
- [ ] Checkout pt_compat branch
- [ ] Export all test OTIO files to AAF
- [ ] Save outputs to `exports/pt_compat/` directory
- [ ] Document any issues encountered

### TODO-2.3: Compare dev vs pt_compat exports
- [ ] Run comparison script on all test files
- [ ] Document differences
- [ ] Identify improvements in pt_compat
- [ ] Identify any regressions

### TODO-2.4: Analyze test results
- [ ] Document dev branch test results (42/52 = 80.8%)
- [ ] Document pt_compat test results (66/66 = 100%)
- [ ] Analyze why pt_compat has more tests
- [ ] Document the 8 additional tests that pass in pt_compat

## Phase 3: DaVinci Resolve Comparison (if available)

### TODO-3.1: Identify DaVinci Resolve reference files
- [ ] Check if DaVinci Resolve exported AAF files are available
- [ ] Check `test_data/` directory for reference files
- [ ] Check `reference/` directory for reference files
- [ ] Document available reference files

### TODO-3.2: Compare pt_compat with DaVinci Resolve (if available)
- [ ] Compare MobID structure
- [ ] Compare timecode tracks
- [ ] Compare audio track structure
- [ ] Compare OperationDef UUIDs
- [ ] Document differences and similarities

### TODO-3.3: Analyze Pro Tools compatibility
- [ ] Check Audio Gain OperationGroup UUID
- [ ] Verify it matches DaVinci Resolve (9d2ea894-0968-11d3-8a38-0050040ef7d2)
- [ ] Check ParameterDef UUID
- [ ] Verify it matches DaVinci Resolve (e4962321-2267-11d3-8a4c-0050040ef7d2)
- [ ] Document Pro Tools compatibility status

## Phase 4: Documentation and Reporting

### TODO-4.1: Create verification report
- [ ] Create `VERIFICATION_REPORT.md`
- [ ] Document verification methodology
- [ ] Document dev vs pt_compat comparison
- [ ] Document DaVinci Resolve comparison (if available)
- [ ] Include test results
- [ ] Include recommendations

### TODO-4.2: Update FINAL_SUMMARY.md
- [ ] Add verification results
- [ ] Add comparison data
- [ ] Add recommendations for future work

### TODO-4.3: Create quick reference guide
- [ ] Create `QUICK_REFERENCE.md`
- [ ] Summarize key findings
- [ ] Provide quick access to important information

## Phase 5: Execute Verification

### TODO-5.1: Run automated verification
- [ ] Execute `run_verification_loop.py`
- [ ] Monitor progress
- [ ] Capture all outputs
- [ ] Document any issues

### TODO-5.2: Manual verification (if needed)
- [ ] Manually verify key differences
- [ ] Check specific test cases
- [ ] Validate against known issues

### TODO-5.3: Final review
- [ ] Review all verification results
- [ ] Check for any regressions
- [ ] Validate against original goals
- [ ] Prepare final report

## Success Criteria

✅ All 66 tests pass on pt_compat (100%)
✅ pt_compat produces equal or better AAF files than dev
✅ No regressions introduced
✅ Comprehensive documentation created
✅ Verification loop established and documented

## Timeline

- Phase 1: 1-2 hours (create scripts)
- Phase 2: 2-3 hours (dev comparison)
- Phase 3: 1-2 hours (DaVinci Resolve comparison, if available)
- Phase 4: 1-2 hours (documentation)
- Phase 5: 1-2 hours (execution)
- **Total: 6-11 hours**

## Notes

- The dev branch has 52 tests, pt_compat has 66 tests (14 additional tests)
- Dev branch: 42/52 passing (80.8%)
- PT-Compat branch: 66/66 passing (100%)
- The off-by-one error was the critical fix
- Audio Gain OperationGroup wrapping is a key feature of pt_compat

## Next Steps

1. Execute TODO-1.1: Create `verify_exports.py`
2. Execute TODO-1.2: Create `compare_aaf_files.py`
3. Execute TODO-1.3: Create `run_verification_loop.py`
4. Execute Phase 2: Dev branch comparison
5. Execute Phase 3: DaVinci Resolve comparison (if available)
6. Execute Phase 4: Documentation
7. Execute Phase 5: Verification execution
