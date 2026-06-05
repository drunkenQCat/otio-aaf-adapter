---
name: pr-branch-extraction-workflow
description: Extract a clean PR branch from a messy dev branch — remove process artifacts, fix linting, and organize into reviewable commits
source: auto-skill
extracted_at: '2026-06-05T06:34:00.728Z'
updated_at: '2026-06-05T09:30:00.000Z'
---

# PR Branch Extraction Workflow

When a development branch has accumulated process artifacts (diagnostic scripts, AI-generated docs, binary test data, temporary debug files) alongside the actual deliverable code changes, you need a systematic approach to extract a clean PR branch.

## When to Apply

- Dev branch contains both deliverable code AND process artifacts
- You need to submit a PR to an upstream repository
- Upstream repo has linting requirements (e.g., flake8)
- Test files were modified as part of refactoring
- Binary test files exist that shouldn't be in the PR

## Critical: What NOT to Commit

**These files should NEVER be included in PRs:**

1. **Lockfiles** (`uv.lock`, `package-lock.json`, `poetry.lock`, etc.)
   - These are local dependency snapshots
   - They cause merge conflicts and version pinning issues
   - Only commit `pyproject.toml`, `package.json`, etc.
   - If accidentally staged: `git restore --staged <lockfile>`

2. **Binary Test Data** (`.aaf`, `.wav`, `.otio`, `.mov`, `.dnx`, etc.)
   - Keep these local for development/testing
   - They bloat the repository
   - If needed for CI, use GitHub Actions artifacts or external storage

3. **AI-Generated Documentation**
   - Planning docs, journey docs, analysis reports
   - These are process artifacts, not deliverables
   - Keep them local or in a separate branch

4. **Diagnostic/Analysis Tools**
   - `diagnostics/`, `tools/`, `check_*.py`, `compare_*.py`
   - These are development aids, not part of the codebase
   - Keep them local

5. **Temporary Debug Files**
   - `debug_*.py`, `*_result.txt`, `*_output.aaf`
   - Delete these before committing

**When in doubt, DON'T commit it.** Ask the user explicitly if unsure.

## Reorganizing Commits After the Fact

If you've already committed and need to reorganize:

### Method 1: Reset and Re-commit

```bash
# Undo last N commits but keep changes staged
git reset --soft HEAD~N

# Unstage specific files you don't want
git restore --staged uv.lock
git restore --staged diagnostics/
git restore --staged tools/

# Commit only what you want
git commit -m "feat(scope): description"

# Add more files for next commit
git add src/other_file.py
git commit -m "fix(scope): description"

# Force push to update remote branch
git push --force origin branch_name
```

### Method 2: Interactive Rebase

```bash
# Rebase last N commits interactively
git rebase -i HEAD~N

# In the editor, you can:
# - reorder commits
# - squash multiple commits into one
# - edit commit messages
# - drop commits entirely
```

### Method 3: Cherry-Pick

```bash
# Create a new branch from main
git checkout -b new_branch origin/main

# Cherry-pick specific commits
git cherry-pick <commit-hash-1>
git cherry-pick <commit-hash-2>
```

## Restoring Accidentally Removed Functionality

If you removed code that shouldn't have been removed (e.g., hooks, plugins, utilities):

```bash
# Restore specific file from origin/main
git checkout origin/main -- src/path/to/file.py

# Restore entire directory
git checkout origin/main -- src/module_directory/

# Restore test directory
git checkout origin/main -- tests/

# Then commit the restoration
git add -A
git commit -m "revert: restore <functionality> and related tests

Restore the <feature> feature that was previously removed:
- Restore <module>.py
- Restore configuration in <config_file>
- Restore <feature>_example test directory
- Restore all <feature>-related tests in test_<file>.py

The <feature> functionality is necessary for <reason>
and provides <benefit>.

Co-Authored-By: Qwen AI <noreply@qwen.ai>"
```

**Common scenarios:**
- Removed hooks/plugins that are used by the framework
- Removed test utilities that other tests depend on
- Removed "example" code that demonstrates API usage
- Removed functionality that users rely on

**Verification:**
```bash
# Check if tests pass after restoration
uv run pytest tests/test_file.py -v

# Check if the module is imported/used elsewhere
grep -r "module_name" src/ tests/
```

## The Five-Step Workflow

### Step 1: Audit All Changes

First, get the full picture of what changed between main and your dev branch:

```bash
# What files changed and how?
git diff --name-status origin/main dev

# Output categories:
# M = Modified, A = Added, D = Deleted
```

Then classify every changed file into one of these categories:

| Category | Include in PR? | Examples |
|----------|---------------|----------|
| Core source code | ✅ Yes | Modified `src/` files, new modules |
| Dependencies | ✅ Yes | `pyproject.toml`, `uv.lock` |
| Tests | ✅ Yes (with analysis) | Modified test files |
| CI config | ❓ Maybe | `.github/workflows/` — only if needed |
| Binary test data | ❌ No | `.aaf`, `.wav`, `.otio` files |
| Diagnostic scripts | ❌ No | `diagnostics/`, `tools/`, `check_*.py` |
| AI-generated docs | ❌ No | `docs/parity_plan/`, journey docs |
| Local config | ❌ No | `.gitignore` changes for local paths |
| Temp debug files | ❌ No (delete) | `debug_*.py`, `*_result.txt` |

### Step 2: Analyze Test File Changes

**Before deciding whether to include test changes**, understand what was deleted/added:

```bash
# See what tests were removed
git diff origin/main..dev -- tests/ | grep "^-.*def test_"

# See what tests were added
git diff origin/main..dev -- tests/ | grep "^+.*def test_"
```

Common reasons for test deletion that ARE appropriate for PR:
- Removed a feature that's no longer needed → tests should be removed too
- Removed binary test fixtures (large files) → tests that depend on them must go
- Refactored test structure → old tests replaced by new ones

Common reasons that are NOT appropriate:
- Tests were failing and were deleted to make CI pass → investigate instead
- Tests were temporarily disabled during development

**Summarize the deletions for the user** before proceeding. They need to confirm.

**When to restore tests to main branch state:**
- If the PR is focused on bug fixes/features and test changes are unrelated refactoring → restore to main
- If test changes are integral to the feature/fix → include them
- When in doubt, restore to main and let the user decide what to add back

```bash
# Restore tests to main branch state
git checkout origin/main -- tests/
```

### Step 3: Create Clean Branch

```bash
# Start from origin/main, not from dev
git checkout -b for_pr origin/main

# Bring in ALL changes from dev
git checkout dev -- .

# Now selectively remove what shouldn't be in the PR
```

**Remove process artifacts:**
```bash
# Restore CI config to main (if changes were local-only)
git checkout origin/main -- .github/workflows/

# Remove binary test files
git rm -f path/to/large_file.aaf path/to/test_data.otio

# Remove diagnostic/tool directories
git rm -rf diagnostics/ tools/

# Remove temp debug files
rm debug_*.py debug_*.txt *_result.txt
```

**CRITICAL: Verify Functionality Removals Before Proceeding**

Before removing any source code (modules, classes, functions), verify it's actually unused:

```bash
# Check if the code is imported/used anywhere
grep -r "module_name" src/ tests/
grep -r "class_name" src/ tests/
grep -r "function_name" src/ tests/

# Check git history to understand why it was removed
git log --all --full-history -- src/path/to/module.py
```

**Common mistakes:**
- Removing hooks/plugins infrastructure that's used by the framework
- Removing test utilities that other tests depend on
- Removing "example" code that demonstrates API usage

**When in doubt, keep it.** It's easier to remove later than to restore and re-integrate.

**Restore .gitignore if changes were local-only:**
```bash
git checkout origin/main -- .gitignore
```

### Step 4: Fix Linting Issues

Run the project's linter on ALL modified files:

```bash
# Example with flake8
uv run flake8 src/modified_file1.py src/modified_file2.py src/new_module.py
```

Common issues to fix:
- **W293**: Blank lines containing whitespace → remove trailing spaces
- **E501**: Lines too long → split into multiple lines
- **F401**: Unused imports → remove them
- **F841**: Unused variables → remove or use them
- **E303**: Too many blank lines → reduce to max 2

**Batch fixing approach**: For large numbers of issues, use agents to fix each file independently. This parallelizes the work and avoids merge conflicts.

After fixing, verify:
```bash
uv run flake8 src/modified_file1.py src/modified_file2.py src/new_module.py
# Should produce no output (exit code 0)
```

### Step 5: Create Clean Commits

Stage and commit in logical groups:

```bash
# Commit 1: Refactoring/cleanup (if applicable)
git add tests/test_file.py src/plugin_manifest.json
git commit -m "refactor(scope): description of cleanup"

# Commit 2: New feature
git add src/new_module.py src/integration_file.py pyproject.toml uv.lock
git commit -m "feat(scope): description of new feature"

# Commit 3: Bug fix
git add src/fixed_file.py
git commit -m "fix(scope): description of fix"
```

**Commit ordering**: Refactoring first → Features → Fixes. This makes the PR easier to review.

## Verification Checklist

Before pushing:

- [ ] `git diff --stat origin/main..HEAD` shows only intended files
- [ ] No binary files (.aaf, .wav, .otio, .dnx) in the diff
- [ ] No diagnostic/tool scripts in the diff
- [ ] No AI-generated documentation in the diff
- [ ] No temp debug files remaining in working directory
- [ ] `flake8` (or project linter) passes with zero errors
- [ ] Test suite runs (pre-existing failures are OK, new failures are not)
- [ ] Commit messages follow project conventions

## Common Pitfalls

1. **Starting from dev instead of main**: `git checkout -b for_pr dev` carries all the mess. Always start from `origin/main`.

2. **Forgetting to restore CI config**: Local CI tweaks (debug branches, extra steps) shouldn't be in the PR.

3. **Including .gitignore changes**: If .gitignore was modified to ignore local files (test_data/, diagnostics/), those rules aren't needed in the PR branch since those files aren't there.

4. **Not analyzing test deletions**: Blindly including test changes can remove important tests. Always summarize what was deleted and why.

5. **Skipping linting**: Upstream CI will reject the PR. Fix linting before pushing.

6. **Committing from dev directly**: `git merge dev` into a new branch carries all commits including WIP messages. Use `git checkout dev -- .` to bring only the file state, then create fresh commits.

7. **Removing functionality without verification**: Deleting hooks, plugins, or utility modules because they "look unused" can break the codebase. Always verify usage with `grep` before removing. If unsure, keep it.

8. **Including test refactoring in feature PRs**: If the PR is about fixing a bug or adding a feature, unrelated test refactoring should be restored to main branch state. Mix concerns = harder review.

## When NOT to Use This Workflow

- If dev branch is already clean (no process artifacts) → just push and create PR
- If changes are small (< 5 files) → manual cherry-pick is faster
- If the PR is internal (to your own fork) → process artifacts are OK

## Related Skills

- `parity-project-commit-strategy` — Commit ordering and what to include/exclude in parity projects
- `binary-format-parity-methodology` — Overall parity methodology (this workflow is the final step)
- `exhaustive-binary-comparison` — Diagnostic scripts used during development (excluded from PR)
