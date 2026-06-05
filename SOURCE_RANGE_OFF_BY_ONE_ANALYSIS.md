# Source Range Off-by-One 问题分析

## 问题概述

在 pt_compat 分支中，有 2 个测试失败，都是 source_range.start_time 的 off-by-one 错误：

1. **test_aaf_roundtrip_first_clip**: source_range.start_time 从 101 变成 102（+1）
2. **test_transcribe_embed_dnx_data**: source_range.start_time 从 1 变成 2（-1）

有趣的是，这两个错误的方向相反！第一个是 +1，第二个是 -1。

## 详细分析

### 测试 1: test_aaf_roundtrip_first_clip

**原始 Timeline:**
- source_range.start_time: 101
- available_range.start_time: 1
- global_start_time: None

**Roundtripped Timeline:**
- source_range.start_time: 102 (+1)
- available_range.start_time: 2 (+1)
- global_start_time: 0

**计算:**
- offset = visible_range.start_time - available_range.start_time = 101 - 1 = 100
- start = int(offset.value) = 100

**问题:**
在 roundtrip 后，source_range.start_time 变成了 102，available_range.start_time 变成了 2。

这说明在读取 AAF 文件时，source_range.start_time 被计算为：
```
source_range.start_time = timecode.start + offset + available_range.start_time
                        = 0 + 100 + 2
                        = 102
```

但是，原始的 source_range.start_time 是 101，available_range.start_time 是 1。

这说明在写入 AAF 文件时，available_range.start_time 被写成了 2（+1），导致在读取时 source_range.start_time 变成了 102（+1）。

### 测试 2: test_transcribe_embed_dnx_data

**原始 Clip:**
- source_range.start_time: 1
- available_range.start_time: 1
- global_start_time: None

**Roundtripped Clip:**
- source_range.start_time: 2 (-1 from expected)
- available_range.start_time: 2 (+1)

**问题:**
在 roundtrip 后，source_range.start_time 变成了 2，available_range.start_time 变成了 2。

这说明在读取 AAF 文件时，source_range.start_time 被计算为：
```
source_range.start_time = timecode.start + offset + available_range.start_time
                        = 0 + 0 + 2
                        = 2
```

但是，原始的 source_range.start_time 是 1，available_range.start_time 是 1。

这说明在写入 AAF 文件时，available_range.start_time 被写成了 2（+1），导致在读取时 source_range.start_time 变成了 2（+1）。

## 根因分析

### 假设 1: timecode_length + 1 影响 available_range.start_time

**结论:** 不太可能。timecode_length 只用于 timecode 的长度，不应该影响 available_range.start_time 的计算。

### 假设 2: timecode.start 影响 available_range.start_time

**结论:** 不太可能。timecode.start 只用于 timecode 的起始值，不应该影响 available_range.start_time 的计算。

### 假设 3: 其他地方的 +1 问题

**结论:** 需要进一步调查。可能是 AAF 写入器或读取器中的某个地方导致了 +1 的问题。

## 可能的解决方案

### 方案 1: 修复 AAF 写入器

检查 AAF 写入器中是否有地方导致了 available_range.start_time +1 的问题。

可能的地方：
- `_create_filemob` 方法
- `_create_tapemob` 方法
- `_create_mastermob` 方法
- `aaf_sourceclip` 方法

### 方案 2: 修复 AAF 读取器

检查 AAF 读取器中是否有地方导致了 source_range.start_time 计算错误的问题。

可能的地方：
- `_transcribe_sourceclip` 方法
- `_transcribe_available_range` 方法

### 方案 3: 调整测试

如果 +1 的问题是预期的行为（例如，为了匹配 DaVinci Resolve 的行为），那么需要调整测试以反映这个行为。

## 下一步行动

1. **深入分析 AAF 写入器**
   - 检查 `_create_filemob` 方法
   - 检查 `_create_tapemob` 方法
   - 检查 `_create_mastermob` 方法
   - 检查 `aaf_sourceclip` 方法

2. **深入分析 AAF 读取器**
   - 检查 `_transcribe_sourceclip` 方法
   - 检查 `_transcribe_available_range` 方法

3. **与 dev 分支对比**
   - 运行 dev 分支的测试，确保它们通过
   - 导出相同的 OTIO 文件到 AAF（dev 和 pt_compat）
   - 对比两个 AAF 文件的结构
   - 找出导致 +1 问题的具体代码

4. **修复问题**
   - 根据分析结果修复问题
   - 运行测试验证修复
   - 确保所有测试通过

## 关键指标

- **目标:** 所有测试通过
- **当前:** 64/66 测试通过 (97.0%)
- **差距:** 2 个测试失败

## 时间估计

- **分析 AAF 写入器:** 2-3 小时
- **分析 AAF 读取器:** 2-3 小时
- **与 dev 分支对比:** 2-3 小时
- **修复问题:** 2-3 小时
- **总计:** 8-12 小时

## 风险和缓解措施

### 风险 1: +1 问题难以定位
**缓解措施:**
- 使用调试工具逐步跟踪代码执行
- 添加日志输出以跟踪变量值
- 使用二分法逐步缩小问题范围

### 风险 2: 修复可能引入新问题
**缓解措施:**
- 运行完整测试套件
- 与 dev 分支对比
- 与 DaVinci Resolve 对比

### 风险 3: +1 问题可能是预期行为
**缓解措施:**
- 检查 DaVinci Resolve 的行为
- 检查 AAF 规范
- 咨询 OpenTimelineIO 社区

## 总结

这是一个复杂的 off-by-one 问题，涉及 AAF 写入器和读取器的多个方面。需要深入分析才能找出根本原因并修复。预计需要 8-12 小时的工作时间。
