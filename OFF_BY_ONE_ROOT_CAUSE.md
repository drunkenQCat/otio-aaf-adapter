# Off-by-One 问题 - 根源分析和解决方案

## 问题根源

### AAF 写入器中的设置（line 199-206）
```python
timecode_start = int(
    otio_clip.media_reference.available_range.start_time.value
)
timecode_length = int(
    otio_clip.media_reference.available_range.duration.value
)

tape_timecode_slot.segment.start = int(timecode_start)
tape_timecode_slot.segment.length = int(timecode_length)
```

**问题**: SourceMob Timecode 的 start 值被设置为 `available_range.start_time.value`。

### AAF 读取器中的计算（line 544-548）
```python
# don't use start_tc on mastermob
start_tc = _get_mob_start_tc(chain_mob) if isinstance(
    chain_mob, aaf2.mobs.SourceMob) else None
available_range = _get_source_clip_ranges(
    chain_slot, chain_source_clip, in_range, start_tc)
```

**问题**: 当 chain_mob 是 SourceMob 时，会调用 `_get_mob_start_tc(chain_mob)` 来获取 start_tc。

### _get_source_clip_ranges 函数中的计算（line 390-392）
```python
if start_tc:
    start = start + start_tc.start_time.rescaled_to(edit_rate)
    duration_tc = start_tc.duration.rescaled_to(edit_rate)
    duration = max(duration, duration_tc)
```

**问题**: 当 start_tc 存在时，会将 start_tc.start_time 加到 start 上。但是，chain_source_clip.start 已经是相对于 SourceMob 的偏移量了，所以不应该再加一次 SourceMob Timecode 的 start 值。

## 具体例子

**原始 Timeline:**
- available_range.start_time: 1
- source_range.start_time: 101

**AAF 写入器:**
- SourceMob Timecode start: 1 (从 available_range.start_time 复制)
- source_clip.start: 100 (visible_range.start_time - available_range.start_time = 101 - 1 = 100)

**AAF 读取器:**
- start_tc.start_time: 1 (从 SourceMob Timecode 获取)
- start: 100 (source_clip.start)
- start = start + start_tc.start_time = 100 + 1 = 101 ✓ 正确

**但是:**
- available_range.start_time: 1 + 1 = 2 ✗ 错误！重复加了一次

**问题**: 在计算 available_range 时，又将 SourceMob Timecode start (1) 加到了 available_range.start_time 上，导致 1 + 1 = 2。

## 解决方案

### 方案 1: 修改 AAF 写入器（推荐）
在 AAF 写入器中，SourceMob Timecode 的 start 值应该设置为 0，而不是 available_range.start_time。

**理由**: 
- source_clip.start 已经是相对于 SourceMob 的偏移量了
- SourceMob Timecode start 应该表示 SourceMob 的绝对时间码起始值，而不是 available_range.start_time

**修改位置**: `src/otio_aaf_adapter/adapters/aaf_adapter/aaf_writer.py` line 199-206

**修改前**:
```python
timecode_start = int(
    otio_clip.media_reference.available_range.start_time.value
)
```

**修改后**:
```python
timecode_start = 0
```

### 方案 2: 修改 AAF 读取器
在 AAF 读取器中，当计算 available_range 时，不应该将 SourceMob Timecode 的 start 值加到 available_range.start_time 上。

**理由**: 
- available_range.start_time 已经包含了 SourceMob Timecode 的 start 值
- 重复加会导致 +1 问题

**修改位置**: `src/otio_aaf_adapter/adapters/advanced_authoring_format.py` line 390-392

**修改前**:
```python
if start_tc:
    start = start + start_tc.start_time.rescaled_to(edit_rate)
```

**修改后**:
```python
# Don't add start_tc.start_time to start, because start is already relative to SourceMob
# if start_tc:
#     start = start + start_tc.start_time.rescaled_to(edit_rate)
```

## 推荐方案

**推荐方案 1**: 修改 AAF 写入器。

**理由**:
1. 根据 AAF 规范，SourceMob Timecode 的 start 值应该表示 SourceMob 的绝对时间码起始值，而不是 available_range.start_time
2. source_clip.start 已经是相对于 SourceMob 的偏移量了，所以 SourceMob Timecode start 应该设置为 0
3. 这样可以避免在 AAF 读取器中重复加 SourceMob Timecode start 值

## 下一步行动

1. 修改 AAF 写入器中的 SourceMob Timecode start 值设置为 0
2. 运行测试验证修复
3. 确保所有测试通过
4. 与 Dev 分支对比，确保行为一致
5. 与 DaVinci Resolve 对比，确保行为一致

## 时间估计

- 修改代码: 30 分钟
- 运行测试: 30 分钟
- 验证修复: 1 小时
- **总计**: 2 小时

## 风险和缓解措施

### 风险 1: 修改可能会影响其他测试
**缓解措施**:
- 运行完整测试套件
- 与 Dev 分支对比
- 与 DaVinci Resolve 对比

### 风险 2: 修改可能会影响 AAF 文件的兼容性
**缓解措施**:
- 与 DaVinci Resolve 对比
- 咨询 OpenTimelineIO 社区

## 总结

问题的根源是 AAF 写入器将 available_range.start_time 复制到了 SourceMob Timecode start，然后在 AAF 读取器中又将其加到了 available_range.start_time 上，导致重复加了一次。

推荐方案是修改 AAF 写入器，将 SourceMob Timecode start 设置为 0，而不是 available_range.start_time。这样可以避免重复加的问题，并且符合 AAF 规范。

预计需要 2 小时的工作时间。
