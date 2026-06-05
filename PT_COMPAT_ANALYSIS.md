# PT-Compat 分支特性分析

## 当前状态 (2026-06-05)

### 测试结果
- **总测试数**: 66
- **通过**: 64 (97.0%)
- **失败**: 2 (3.0%)

### 失败的测试
1. `test_aaf_roundtrip_first_clip`: source_range.start_time 从 101 变成 102（+1）
2. `test_transcribe_embed_dnx_data`: source_range.start_time 从 1 变成 2（+1）

### 关键发现
两个失败的测试都显示 source_range.start_time 增加了 1。这是一个系统性的 +1 问题。

## 已实现的 Pro Tools 兼容性特性

### 1. Audio Gain OperationGroup
- ✅ 为音频 SourceClip 创建 Audio Gain OperationGroup
- ✅ 使用正确的 OperationDef UUID: `9d2ea894-0968-11d3-8a38-0050040ef7d2`
- ✅ 使用正确的 ParameterDef UUID: `e4962321-2267-11d3-8a4c-0050040ef7d2`
- ✅ 使用正确的 ParameterDef 名称: `Amplitude`
- ✅ 使用正确的 ConstantValue: 536870912/536870912 (1.0)

### 2. CompositionMob MobID 格式
- ✅ 使用 DaVinci Resolve 的 MobID 前缀: `060a2b34.01010101.01010f00.13000000`

### 3. Mob 追加顺序
- ✅ CompositionMob 立即追加
- ✅ MasterMob, TapeMob, FileMob 在创建时立即追加
- ✅ 移除了延迟追加的 append_all_mobs() 方法

### 4. PhysicalTrackNumber
- ✅ 为所有 MobSlot 添加 PhysicalTrackNumber = 1
  - TapeMob timecode slot
  - FileMob slot
  - MasterMob slot
  - Audio track timeline slot

### 5. Audio Track Slot ID
- ✅ Audio track 使用 slot_id = 3
- ✅ Video track 使用 slot_id = 2
- ✅ Timecode 使用 slot_id = 1

### 6. Timecode 长度
- ✅ 使用 `timeline_duration + 1` 来匹配 DaVinci Resolve 的行为（inclusive end frame）

### 7. Timecode Slot 名称
- ✅ 使用空字符串 `""` 而不是 `"TC"`

### 8. Filler 长度计算
- ✅ 使用 `ceil()` 来确保 Filler 长度正确

### 9. WAV Summary 生成
- ✅ 从实际 WAV 文件读取并生成标准化的 44 字节 Summary

### 10. 音频采样率动态检测
- ✅ 从实际 WAV 文件读取采样率和位深度

## 代码差异分析

### aaf_sourceclip 方法
**dev 分支**:
```python
offset = (
    otio_clip.visible_range().start_time
    - otio_clip.available_range().start_time
)
start = offset.value
length = otio_clip.visible_range().duration.value
```

**pt_compat 分支**:
```python
offset = (otio_clip.visible_range().start_time -
          otio_clip.available_range().start_time)
start = int(offset.value)
length = int(otio_clip.visible_range().duration.value)
```

**差异**: pt_compat 分支在计算 `start` 和 `length` 时使用了 `int()`，而 dev 分支没有。但是，在传递给 `create_source_clip` 时，两个分支都使用了 `int(start)` 和 `int(length)`。

### add_timecode 方法
**dev 分支** (add_timecode_first):
```python
timecode_length = int(timeline_duration.value) + 1
```

**pt_compat 分支** (add_timecode):
```python
timecode_length = int(timeline_duration.value) + 1
```

**差异**: 无，两个分支都使用 `+1`。

## 问题根因分析

### 假设 1: timecode_length + 1 影响 source_range
**结论**: 不太可能。timecode_length 只用于 timecode 的长度，不应该影响 source_range 的计算。

### 假设 2: source_range 计算差异
**结论**: 不太可能。两个分支在 source_range 计算上的唯一差异是 `int()` 的使用，但这不应该导致 +1 的问题。

### 假设 3: timecode 的 start 值影响 source_range
**结论**: 不太可能。timecode.start 只用于 timecode 的起始值，不应该影响 source_range 的计算。

### 假设 4: 其他地方的 +1 问题
**结论**: 需要进一步调查。

## 下一步行动

### 1. 深入分析失败的测试
- 检查 test_aaf_roundtrip_first_clip 的详细逻辑
- 检查 test_transcribe_embed_dnx_data 的详细逻辑
- 找出 source_range.start_time +1 的根本原因

### 2. 与 dev 分支对比
- 运行 dev 分支的测试，确保它们通过
- 对比 dev 和 pt_compat 分支的输出
- 找出导致 +1 问题的具体代码

### 3. 修复问题
- 根据分析结果修复问题
- 运行测试验证修复
- 确保所有测试通过

### 4. 与 DaVinci Resolve 对比
- 导出 AAF 文件
- 使用 DaVinci Resolve 打开并检查
- 确保与 DaVinci Resolve 的行为一致

## 验证循环

### 循环 1: 与 dev 分支对比
1. 运行 dev 分支的测试，确保它们通过
2. 导出相同的 OTIO 文件到 AAF（dev 和 pt_compat）
3. 对比两个 AAF 文件的结构
4. 找出导致 +1 问题的具体代码
5. 修复问题并重新测试

### 循环 2: 与 DaVinci Resolve 对比
1. 使用 pt_compat 导出 AAF 文件
2. 使用 DaVinci Resolve 打开并检查
3. 对比 DaVinci Resolve 导出的 AAF 文件
4. 确保与 DaVinci Resolve 的行为一致
5. 修复任何不一致的地方

## 总结

pt_compat 分支已经实现了大部分 Pro Tools 兼容性特性，测试通过率达到 97.0%。还有 2 个测试失败，都是 source_range.start_time +1 的问题。需要深入分析找出根本原因并修复。
