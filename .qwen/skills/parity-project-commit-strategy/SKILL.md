---
name: parity-project-commit-strategy
description: Organize commits for large parity projects with multiple file categories (core code, tools, docs, test data)
source: auto-skill
extracted_at: '2026-06-04T18:59:35.795Z'
---

# Parity Project Commit Strategy

When completing a large parity alignment project, organizing commits effectively is crucial for maintainability and code review.

## File Classification Methodology

Before committing, classify all changes into these categories:

### 1. Core Functionality Code
- Modified source files implementing the parity fixes
- New modules (e.g., audio transcoding)
- Dependency updates (pyproject.toml only, NOT lockfiles)

**Example from AAF parity project:**
```
src/otio_aaf_adapter/adapters/aaf_adapter/aaf_writer.py     (+313 lines)
src/otio_aaf_adapter/audio_transcoder.py                    (new file)
src/otio_aaf_adapter/adapters/advanced_authoring_format.py  (+65 lines)
pyproject.toml                                               (dependency)
```

**Important:** Do NOT commit lockfiles (uv.lock, Pipfile.lock, etc.) to PRs. Lockfiles are local to each developer's environment and cause dependency conflicts. Add them to .gitignore.

### 2. Diagnostic Tools
- Scripts used to discover and analyze differences
- Comparison utilities
- Property enumeration scripts

**Typical location:** `diagnostics/` or `tools/`

**Example:**
```
diagnostics/exhaustive_compare.py
diagnostics/three_file_compare.py
diagnostics/investigate_start_times.py
tools/parity_gate.py
tools/compare_aaf_references.py
```

### 3. Verification Tools
- Automated verification scripts
- Regression test utilities
- Export and validation scripts

**Example:**
```
tools/test_export.py
tools/remap_and_export.py
diagnostics/verify_operationdef_uuid.py
```

### 4. Documentation
- Planning documents
- Phase reports
- Technical handovers

**Example:**
```
docs/parity_plan/01_diagnostic_baseline.md
docs/parity_plan/02_verification_toolchain.md
docs/parity_plan/03_L1_L2_header_mob_fixes.md
```

### 5. Test Data
- Reference files (golden standard)
- Test fixtures (input files)
- Expected outputs

**Size considerations:**
- WAV files: ~24MB for 24 files is reasonable to commit
- AAF files: ~3MB for 5 files is reasonable
- PTX files: ~0.1MB is negligible
- **Total test data: ~44MB is acceptable**

**Example:**
```
test_data/飞驰人生测试_20260515.20260602163810.aaf  (DaVinci reference)
test_data/飞驰人生测试_testdata.otio                (input timeline)
test_data/A1-0001_..._SJH.wav                       (24 WAV files, 20.5MB)
```

### 6. Configuration
- .gitignore updates
- CI/CD configuration

## Commit Ordering Strategy

Order commits by **dependency and logical grouping**:

### Commit 1: Foundation (Dependencies + Core Infrastructure)
```
feat(aaf): 添加音频自动转码功能，支持 48kHz/24bit/mono 标准

- 新增 audio_transcoder.py 模块，自动检测并转码非标准音频
- 集成到 write_to_file 流程，导出前自动转码，导出后恢复引用
- 添加 pydub 依赖用于音频处理
- 支持缓存机制，避免重复转码
```

**Files:** `audio_transcoder.py` + `pyproject.toml` + `uv.lock` + integration changes

### Commit 2: Core Fixes (P0 Issues)
```
fix(aaf): 修复 AAF 导出与 DaVinci Resolve 的结构差异（P0 级别）

修复 3 个关键问题：
1. OperationGroup 内 SourceClip 的 StartTime 设为 0（之前是负值）
2. Audio Gain OperationDef UUID 修正为 9d2ea894-...
3. Audio Gain ParameterDef 名称修正为 "Amplitude"，UUID 为 e4962321-...

附带修复：
- Filler 长度使用 ceil 计算（clip 用 floor）
- clip 长度使用 floor 计算（与 DaVinci 一致）
- 改进 WAVEDescriptor Summary 生成（支持默认回退）
- 改进文件路径处理（Path.as_uri）
```

**Files:** Core source files with parity fixes

### Commit 3: Test Data and Verification Tools
```
test: 添加飞驰人生多轨测试数据和 AAF 验证工具

测试数据：
- 24 个 WAV 文件（4 轨道 x 6 片段）
- DaVinci Resolve 导出的参考 AAF
- OTIO 时间线文件

验证工具：
- tools/parity_gate.py - 自动化验证网关
- tools/ 下 16 个分析脚本
- diagnostics/ 下深度对比工具
```

**Files:** `test_data/` (excluding caches) + `tools/`

### Commit 4: Documentation
```
docs: 添加 Pro Tools 兼容性修复的 5 阶段计划文档

包含：
- 01_diagnostic_baseline.md - 诊断基线
- 02_verification_toolchain.md - 验证工具链构建
- 03_L1_L2_header_mob_fixes.md - Header 和 Mob 修复
- 04_L3_descriptor_fixes.md - Descriptor 修复
- 05_regression_and_L0.md - 回归测试
```

**Files:** `docs/parity_plan/`

### Commit 5: Configuration
```
chore: 更新 .gitignore 规则

添加项目特定的忽略规则：
- 音频转码缓存 (test_data/converted/)
- 临时调试文件 (debug_*.py, *_result.txt)
- IDE 配置和构建产物
```

**Files:** `.gitignore` + any config updates

## What to Gitignore

### Always Gitignore
```gitignore
# Transcoding caches (regenerated on demand)
test_data/converted/

# Temporary debug files
debug_*.py
*_result.txt
*_output.aaf

# IDE and editor files
.vscode/
.idea/
*.swp

# Build artifacts
__pycache__/
*.pyc
dist/
build/

# OS files
.DS_Store
Thumbs.db
```

### Never Gitignore
- Core source code
- Test fixtures needed for CI
- Reference files (golden standards)
- Documentation

## Test Data Size Guidelines

| Category | Size Limit | Example |
|----------|-----------|---------|
| Audio files (WAV) | ~25MB | 24 files × ~1MB each |
| Video files | ~50MB | Short clips only |
| Container files (AAF/MXF) | ~5MB | Reference exports |
| Timeline files (OTIO/XML) | ~1MB | Small test cases |
| **Total test data** | **~50MB** | Reasonable for git |

**Key principle:** Commit test data that's needed for local testing and CI, but gitignore generated caches and large intermediate files.

## Commit Message Best Practices

### Structure
```
<type>(<scope>): <brief description in Chinese>

<root cause explanation>

<fix details>

<verification results>
```

### Example: P0 Fix Commit
```
fix(aaf): 修复 AAF 导出与 DaVinci Resolve 的结构差异（P0 级别）

根本原因：
OTIO 导出的 AAF 文件在 3 个关键结构上与 DaVinci Resolve 不一致，导致 Pro Tools 
无法正确解析音频轨道。

修复内容：
1. OperationGroup 内 SourceClip 的 StartTime 设为 0
   - 之前：使用负值时间线偏移（-28524000）
   - 之后：固定为 0（OperationGroup 处理定位）
   
2. Audio Gain OperationDef UUID 修正
   - 之前：e4962321-2267-11d3-8a4c-0050040ef7d2
   - 之后：9d2ea894-0968-11d3-8a38-0050040ef7d2
   
3. Audio Gain ParameterDef 名称和 UUID 修正
   - 名称：ParameterDef_Level → Amplitude
   - UUID：e4962320-... → e4962321-...

验证结果：
✓ OperationDef UUID 匹配 DaVinci
✓ ParameterDef name/UUID 匹配 DaVinci
✓ 24 个 OperationGroup 的 StartTime 全部为 0
✓ 与 DaVinci 参考文件逐项对比：0 差异

影响：修复后 Pro Tools 可正确导入导出的 AAF 文件
```

## Pre-Commit Checklist

Before committing, verify:

- [ ] All temporary debug files deleted (debug_*.py, *_result.txt)
- [ ] Test data caches gitignored (test_data/converted/)
- [ ] No IDE/editor files included
- [ ] Commit messages follow the structured format
- [ ] Commits ordered by dependency
- [ ] Each commit is atomic (one logical change)
- [ ] Test suite passes (or only pre-existing failures remain)

## Common Pitfalls

1. **Committing caches**: `test_data/converted/` contains regenerated files — gitignore it
2. **Committing debug files**: `debug_*.py` and `*_result.txt` are temporary — delete them
3. **Poor commit messages**: "fix issue" is unacceptable — explain root cause and fix
4. **Wrong commit order**: Dependencies first, then features, then docs
5. **Mixing unrelated changes**: Each commit should be one logical change

## When to Squash

Squash commits when:
- You have "WIP" or "fix typo" commits
- Multiple small fixes for the same issue
- Rebased incorrectly and have duplicate changes

Don't squash:
- Atomic logical changes
- Different feature additions
- Separate bug fixes

## Summary

Effective commit organization for parity projects:
1. **Classify** all files into 6 categories
2. **Order** commits by dependency (infrastructure → fixes → tests → docs → config)
3. **Gitignore** caches and temporary files
4. **Write detailed** commit messages in Chinese with root cause and verification
5. **Keep test data** under ~50MB total
6. **Verify** pre-commit checklist before pushing

## Related Skills

- `pr-branch-extraction-workflow` — For extracting a clean PR branch from a messy dev branch (removing process artifacts, fixing linting, organizing into reviewable commits)
