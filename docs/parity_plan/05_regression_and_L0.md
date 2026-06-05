# Phase 5: 回归验证 + L0 调查 + 最终判定

## 背景

### 项目是什么
`otio-aaf-adapter` 是 OpenTimelineIO (OTIO) 的 AAF 格式适配器。经过 Phase 3（L1/L2 修复）和 Phase 4（L3 修复），我们已经消除了所有可控的语义差异。本阶段做最终收尾。

### 本阶段目标

三件事：

1. **全面回归验证** — 确保修复没有破坏任何现有功能
2. **L0 层（CFB 容器）调查** — 理解剩余的二进制差异，记录其性质
3. **最终判定** — 在 `parity_tracker.md` 中追加结论章节，输出能否达成 Pro Tools 兼容的判断

### 前置条件
- Phase 3 和 Phase 4 都已完成
- `parity_gate.py` 的 L1/L2/L3 全部 PASS 或 SKIP
- `parity_tracker.md` 中所有可控差异已标记 FIXED 或 WHITELIST

---

## Part 1: 全面回归验证

### 1.1 单元测试

```bash
pytest tests/test_aaf_adapter.py -v --tb=short
```

**基线对比法**：

1. 先用 `git stash` 保存所有修改
2. 运行测试，记录失败用例名称和数量（这是基线失败数）
3. 用 `git stash pop` 恢复修改
4. 再次运行测试，记录失败用例名称和数量
5. **验收标准**：恢复修改后的失败数 ≤ 基线失败数（不引入新失败）

如果发现新的测试失败，需要回到 Phase 3/4 修正，或者评估是否应该更新测试用例（仅在修复确实改变了正确行为时）。

### 1.2 pyaaf2 测试

我们修改了 pyaaf2 的 `file.py`（Version 1.2→1.1），需要验证这个修改没有破坏 pyaaf2 的核心功能：

```bash
pytest pyaaf2/tests/ -v --tb=short
```

如果 pyaaf2 测试失败，需要评估：
- 失败是否与我们的修改相关？
- 是否应该 upstream 这个修改？（见 Part 4）

### 1.3 端到端验证

使用 `correct_timeline.aaf` 做 round-trip 验证：

```python
import opentimelineio as otio

# 读取 DaVinci Resolve 导出的 AAF
timeline = otio.adapters.read_from_file("correct_timeline.aaf")
print(f"Read OK: {timeline.name}, {len(timeline.tracks)} tracks")

# 导出为新 AAF
otio.adapters.write_to_file(timeline, "roundtrip_correct.aaf")
print("Write OK")

# 重新读取验证
timeline2 = otio.adapters.read_from_file("roundtrip_correct.aaf")
print(f"Re-read OK: {timeline2.name}, {len(timeline2.tracks)} tracks")

# 基本一致性检查
assert len(timeline.tracks) == len(timeline2.tracks), "Track count mismatch!"
print("Round-trip PASS")
```

**验收标准**：round-trip 后轨道数量、clip 数量一致。

### 1.4 SimpleTimeline 的精确验证

这是我们的主测试场景，需要最严格的验证：

```bash
python test_export.py
python parity_gate.py --verbose
```

记录 `parity_gate.py` 的完整输出。

**验收标准**：`parity_gate.py` 返回码为 0（PASS），所有 FAIL 项均已解释并记录为 BLOCKED 或 WHITELIST。

---

## Part 2: L0 层（CFB 容器）调查

AAF 文件使用 Microsoft Compound Binary File (CBF/OLE) 格式存储。pyaaf2 和 DaVinci Resolve 使用不同的写入引擎，它们的 CFB 容器级布局存在结构性差异。

### 2.1 L0 差异的性质

**关键认知**：L0 差异是**结构性差异**，不是**内容差异**。

具体来说：

- **SectorSize 不同**：pyaaf2 默认使用 1024 字节 sector，DaVinci Resolve 使用 512 字节 sector
- **布局差异**：同样的数据在不同的 sector 偏移
- **元数据差异**：CBF 容器自身的管理数据（FAT 表、Directory Entry 等）

这些差异**不影响 AAF 语义**——任何符合 AAF 规范的解析器都能正确读取两个文件。

### 2.2 调查步骤

#### Step 1: 量化剩余二进制差异

Phase 3/4 完成后，`parity_gate.py` 的二进制差异统计：

```
[Binary] (info only)
  File sizes: correct=221184, test=462848
  Total diff bytes: 366167
  Diff groups: 36342
```

**分析**：
- 文件大小差异 2x（1024 vs 512 sector 导致）
- 36342 组差异中，绝大多数是 sector 偏移引起的连锁差异
- 真正的"内容差异"应该为 0（因为 L1/L2/L3 全部 PASS）

#### Step 2: 分类剩余差异

对每组剩余差异，判断属于哪一类：

| 差异类型 | 数量（预估） | 处理方式 |
|---------|-------------|---------|
| 内容差异 | 0 | **不应存在**——如果存在说明 parity_gate 检查项不全面 |
| SectorSize 连锁差异 | ~36000 组 | **记录为结构性差异**——无法消除，不影响语义 |
| CFB 元数据差异 | ~300 组 | **记录为结构性差异**——FAT 表、Directory Entry 等 |
| Dictionary stream 差异 | ~40 组 | **记录为 INFO**——pyaaf2 默认注册的额外定义 |

#### Step 3: CFB 结构对比

使用 pyaaf2 的底层 API 分析 CFB 结构：

```python
import aaf2
from aaf2 import cfb

# 读取两个文件的 CFB 结构
with open("correct_timeline.aaf", "rb") as f:
    correct_cfb = cfb.CompoundFileBinary(f, "rb")
    print("=== Correct CFB Structure ===")
    print(f"  Sector size: {correct_cfb.sector_size}")
    print(f"  Total sectors: {correct_cfb.num_sectors}")
    print(f"  Streams:")
    for path in correct_cfb.listdir("/"):
        size = correct_cfb.get_size(path)
        print(f"    {path}: {size} bytes")

with open("test_output.aaf", "rb") as f:
    test_cfb = cfb.CompoundFileBinary(f, "rb")
    print("\n=== Test CFB Structure ===")
    print(f"  Sector size: {test_cfb.sector_size}")
    print(f"  Total sectors: {test_cfb.num_sectors}")
    print(f"  Streams:")
    for path in test_cfb.listdir("/"):
        size = test_cfb.get_size(path)
        print(f"    {path}: {size} bytes")
```

**预期结果**：
- Sector size 不同（512 vs 1024）
- Stream 数量和内容一致（因为 L1/L2/L3 PASS）
- Stream 的 sector 分配位置不同（布局差异）

### 2.3 判定标准

L0 差异的处理取决于其分类：

| 差异类型 | 处理方式 | 是否需要修复 |
|---------|---------|-------------|
| 内容差异 | **必须修复** | 是——回到 Phase 3/4 补充检查项 |
| SectorSize 差异 | **记录为结构性差异** | 否——pyaaf2 写入引擎决定 |
| CFB 元数据差异 | **记录为结构性差异** | 否——CFB 规范允许不同实现 |
| Dictionary 差异 | **记录为 INFO** | 否——pyaaf2 默认行为 |

**关键结论**：L0 差异是**不可控的结构性差异**，不影响 AAF 语义，无需修复。

### 2.4 SectorSize 对齐的可行性评估

**问题**：能否让 pyaaf2 使用 512 字节 sector（与 DaVinci Resolve 一致）？

**调查方向**：

1. **pyaaf2 API 是否支持设置 SectorSize？**
   - 检查 `aaf2/file.py` 的 `AAFFile.__init__()` 或 `_setup()` 方法
   - 检查是否有 `sector_size` 参数

2. **如果支持，如何设置？**
   - 可能需要在 `open()` 时传入参数
   - 可能需要修改 pyaaf2 源码

3. **如果不支持，是否需要 upstream？**
   - 评估修改复杂度
   - 评估是否值得（文件大小差异 2x，但不影响语义）

**结论**：SectorSize 对齐是**可选优化**，不是必须修复。当前阶段应记录为结构性差异，不尝试修复。

---

## Part 3: 最终判定

### 3.1 生成最终结论

在 `parity_tracker.md` 末尾追加一个"最终结论"章节：

```markdown
## 最终结论

### 语义对齐结果

- L1 (Header): 13 项检查，10 PASS, 3 SKIP (WHITELIST)
- L2 (Mob Structure): 65 项检查，64 PASS, 1 SKIP (WHITELIST)
- L3 (Descriptor): 13 项检查，13 PASS
- L0 (Binary): 36342 组结构性差异（SectorSize + CFB 布局）

### 收敛日志最终行

| 日期 | 语义差异数 | 二进制差异组数 | 二进制差异字节数 | 备注 |
|------|-----------|--------------|----------------|------|
| 2026-06-02 | 0 | 36342 | 366167 | Phase 3/4 完成，所有可控差异已消除 |

### 剩余差异说明

1. **L0 SectorSize 差异**：pyaaf2 默认 1024 字节，DaVinci Resolve 512 字节。不影响语义，记录为结构性差异。
2. **L0 Dictionary 差异**：pyaaf2 默认注册的额外 ClassDefinition/TypeDefinition。记录为 INFO 级别。
3. **白名单项**：UUID、时间戳等不可控差异。

### 结论

**结论 A: 语义完全对齐**

所有可控的语义差异（L1/L2/L3）已消除。剩余的二进制差异均为不可控的结构性差异（CFB SectorSize + 布局），不影响 AAF 语义。

**建议**：进行 Pro Tools 实测。如果 Pro Tools 能正确导入 `test_output.aaf` 并显示 48000 Hz 采样率，则问题已解决。

### 待 Pro Tools 验证

需要在 Pro Tools 中实际导入 `test_output.aaf` 验证：

1. 文件能否成功导入？
2. 音频轨道是否正确显示？
3. 采样率是否显示为 48000 Hz？
4. 播放音频，速度是否正常？
5. 时间线长度是否正确？

如果以上 5 项全部通过，则 Pro Tools 兼容性问题已解决。

如果仍然显示 30 Hz，则需要进一步调查：
- Pro Tools 是否从其他位置读取采样率？
- Pro Tools 是否有私有验证逻辑？
- 需要 Pro Tools 调试或日志分析
```

### 3.2 Pro Tools 测试指引

如果需要手动在 Pro Tools 中测试，提供以下步骤供用户执行：

```markdown
## Pro Tools 测试步骤

### 准备工作

1. 确保 Pro Tools 已安装并可正常运行
2. 准备 `test_output.aaf`（Phase 3/4 修复后生成）
3. 准备 `correct_timeline.aaf`（DaVinci Resolve 导出的参考文件）

### 测试 1: 导入 test_output.aaf

1. 打开 Pro Tools
2. File → Import → Session Data
3. 选择 `test_output.aaf`
4. 检查：
   - [ ] 文件能否成功导入？
   - [ ] 音频轨道是否正确显示？
   - [ ] 采样率是否显示为 48000 Hz？
   - [ ] 播放音频，速度是否正常？
   - [ ] 时间线长度是否正确？

### 测试 2: 导入 correct_timeline.aaf（对照组）

1. 重复上述步骤，导入 `correct_timeline.aaf`
2. 对比两个文件的导入结果
3. 如果 `correct_timeline.aaf` 正常但 `test_output.aaf` 异常，说明仍有兼容性问题

### 预期结果

- 两个文件都应该能成功导入
- 采样率都应该显示 48000 Hz
- 音频播放速度都应该正常
- 时间线长度都应该一致

### 如果仍然显示 30 Hz

需要进一步调查：

1. **检查 Pro Tools 日志**：是否有错误信息？
2. **检查 AAF 解析方式**：Pro Tools 是否使用了特殊的 AAF 解析库？
3. **考虑 Pro Tools 版本差异**：不同版本的 Pro Tools 可能有不同的 AAF 解析逻辑
4. **联系 Avid 支持**：询问 Pro Tools 对 AAF 文件的具体要求
```

---

## Part 4: pyaaf2 修改的 upstream 策略

### 4.1 当前修改

我们修改了 pyaaf2 的 `src/aaf2/file.py` 第 261 行：

```python
# 原始代码（第 261 行）
self.header['Version'].value = {u'major': 1, u'minor': 2}

# 修改后
self.header['Version'].value = {u'major': 1, u'minor': 1}
```

**修改原因**：DaVinci Resolve 导出的 AAF 文件使用 Version 1.1，而 pyaaf2 默认写入 Version 1.2。为了与 DaVinci Resolve 输出一致，我们改为 1.1。

### 4.2 upstream 可行性评估

**问题**：这个修改是否应该 upstream 到 pyaaf2 主仓库？

**分析**：

1. **兼容性影响**：Version 1.1 和 1.2 都是 AAF 规范支持的版本。改为 1.1 不会破坏 pyaaf2 的核心功能。
2. **下游项目影响**：如果 upstream 到 pyaaf2 主仓库，所有使用 pyaaf2 的项目都会受影响。需要评估：
   - 是否有其他项目依赖 Version 1.2？
   - 是否有其他项目需要与 DaVinci Resolve 兼容？
3. **替代方案**：不 upstream，而是在 otio-aaf-adapter 中使用本地 fork 的 pyaaf2。

### 4.3 upstream 建议

**方案 A: upstream 到 pyaaf2 主仓库**

1. Fork pyaaf2 仓库
2. 提交 PR，说明修改原因（与 DaVinci Resolve 兼容）
3. 如果 PR 被接受，更新 otio-aaf-adapter 的依赖
4. 如果 PR 被拒绝，使用本地 fork

**方案 B: 使用本地 fork（推荐）**

1. Fork pyaaf2 到 `drunkenQCat/pyaaf2`
2. 在 otio-aaf-adapter 的 `pyproject.toml` 中指定使用 fork：

```toml
[project]
dependencies = [
    "pyaaf2 @ git+https://github.com/drunkenQCat/pyaaf2.git",
]
```

3. 在 `README.md` 中说明使用 fork 的原因

**推荐方案 B**，因为：
- 修改影响范围小（只影响 Version 字段）
- 其他项目可能不需要与 DaVinci Resolve 兼容
- upstream 可能被拒绝（pyaaf2 维护者可能有其他考虑）

### 4.4 后续行动

1. Fork pyaaf2 到 `drunkenQCat/pyaaf2`
2. 在 fork 中应用 Version 修改
3. 更新 otio-aaf-adapter 的依赖配置
4. 在 `README.md` 中说明使用 fork 的原因
5. 定期同步 pyaaf2 主仓库的更新

---

## 交付物

1. 回归测试全部通过的确认（基线对比法）
2. L0 差异分类报告（记录为结构性差异）
3. `parity_tracker.md` 最终版本（追加"最终结论"章节）
4. Pro Tools 测试指引
5. pyaaf2 fork 配置完成

## 验收标准

1. 回归测试不引入新失败（基线对比法）
2. 如果修改了 pyaaf2，pyaaf2 测试不引入新失败
3. `python parity_gate.py` 返回码为 0（PASS）
4. `parity_tracker.md` 已追加"最终结论"章节，包含明确结论
5. pyaaf2 fork 已配置完成，otio-aaf-adapter 使用 fork 版本
6. Pro Tools 测试指引已提供

---

## 注意事项

- **不要为了让测试通过而修改测试用例。** 测试失败说明修复引入了回归。
- **L0 差异是结构性差异，不是需要修复的问题。** CFB 容器层的差异大部分是写入引擎决定的，无法消除也不需要消除。
- **`parity_tracker.md` 的结论要诚实。** 如果无法确定是否解决了 30 Hz 问题，说"需要 Pro Tools 验证"而不是"问题已解决"。
- **pyaaf2 修改需要 upstream 或使用 fork。** 不要直接在 pyaaf2 主仓库提交修改，除非 PR 被接受。
- **本阶段结束后，整个 5 Phase 工程完成。** 最终的 `parity_tracker.md` 是交给用户做 Pro Tools 实测决策的依据。
