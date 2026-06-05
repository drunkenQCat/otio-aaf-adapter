# Off-by-One 问题分析 - 详细进展

## 当前发现总结

### AAF 写入器分析（已完成）

#### 1. compmob_clip 创建 (line 667)
```python
offset = (otio_clip.visible_range().start_time -
          otio_clip.available_range().start_time)
start = int(offset.value)
length = int(otio_clip.visible_range().duration.value)

compmob_clip = self.compositionmob.create_source_clip(
    slot_id=self.timeline_mobslot.slot_id,
    start=int(start),
    length=int(length),
    media_kind=self.media_kind
)
```
- **分析**: start 是 visible_range 相对于 available_range 的偏移量
- **结论**: 没有 +1 问题

#### 2. filemob_clip 创建 (line 886)
```python
filemob_clip = filemob.create_source_clip(
    slot_id=filemob_slot.slot_id,
    length=tapemob_slot.segment.length,
    media_kind=tapemob_slot.segment.media_kind)
```
- **分析**: 没有设置 start，默认为 0
- **结论**: 没有 +1 问题

#### 3. mastermob_clip 创建 (line 913)
```python
mastermob_clip = mastermob.create_source_clip(
    slot_id=mastermob_slot.slot_id,
    length=timecode_length,
    media_kind=self.media_kind)
```
- **分析**: 没有设置 start，默认为 0
- **结论**: 没有 +1 问题

#### 4. tape_clip 创建 (line 1110)
```python
start = int(available_range.start_time.value)
tape_clip = tape_mob.create_source_clip(self._master_mob_slot_id, start=start)
```
- **分析**: 直接使用 available_range.start_time
- **结论**: 没有 +1 问题

### AAF 读取器分析（进行中）

#### 1. _get_mob_start_tc 函数 (line 361)
```python
def _get_mob_start_tc(mob):
    tc_slot = None
    tc_primary = None

    for slot in mob.slots:
        timecode = _resolve_single_slot_component(slot, aaf2.components.Timecode)
        if not timecode:
            continue

        if slot['PhysicalTrackNumber'].value == 1:
            tc_slot = slot
            tc_primary = timecode
            break

    if tc_primary:
        edit_rate = float(tc_slot.edit_rate)
        start = otio.opentime.RationalTime(tc_primary.start, edit_rate)
        length = otio.opentime.RationalTime(tc_primary.length, edit_rate)
        return otio.opentime.TimeRange(start, length)

    return None
```
- **分析**: 从 mob 的 slots 中查找 PhysicalTrackNumber == 1 的 Timecode slot
- **关键点**: start = tc_primary.start
- **待检查**: tc_primary.start 是如何设置的

#### 2. _get_source_clip_ranges 函数 (line 384)
```python
def _get_source_clip_ranges(slot, source_clip, in_range, start_tc):
    edit_rate = float(slot.edit_rate)

    start = otio.opentime.RationalTime(source_clip.start, edit_rate)
    duration = otio.opentime.RationalTime(source_clip.length, edit_rate)

    if start_tc:
        start = start + start_tc.start_time.rescaled_to(edit_rate)
        duration_tc = start_tc.duration.rescaled_to(edit_rate)
        duration = max(duration, duration_tc)

    if in_range:
        start += in_range.start_time.rescaled_to(edit_rate)
        available_range = otio.opentime.TimeRange(start, duration)
        available_range = available_range.clamped(in_range)
    else:
        available_range = otio.opentime.TimeRange(start, duration)

    return available_range
```
- **分析**: 计算 source_clip 的 available_range
- **关键点**: 
  - start = source_clip.start
  - 如果 start_tc 存在，start = start + start_tc.start_time
  - 如果 in_range 存在，start += in_range.start_time
- **待检查**: 这些加法是否会导致 +1 问题

#### 3. _transcribe_master_mob_slot 函数 (line 456)
```python
def _transcribe_master_mob_slot(mob, metadata, source_range, media_references,
                                global_start_time, indent):
    assert isinstance(mob, aaf2.mobs.MasterMob)

    if global_start_time:
        start = source_range.start_time + global_start_time.start_time
        duration = source_range.duration
        source_range = otio.opentime.TimeRange(start, duration)

    clip = otio.schema.Clip(name=mob.name,
                            source_range=source_range)
```
- **分析**: 如果 global_start_time 存在，source_range.start_time 会被加上 global_start_time.start_time
- **关键点**: 这个加法可能会导致 +1 问题
- **待检查**: global_start_time.start_time 的值

## 下一步行动计划

### 立即执行（高优先级）

#### Task 1: 检查 tc_primary.start 的设置
- 检查 AAF 写入器中 Timecode slot 的 start 是如何设置的
- 检查是否有 +1 的问题

#### Task 2: 检查 global_start_time.start_time 的值
- 检查 global_start_time 是如何计算的
- 检查是否有 +1 的问题

#### Task 3: 使用调试工具跟踪代码执行
- 在 _get_source_clip_ranges 函数中添加日志输出
- 跟踪 start 的计算过程
- 找出导致 +1 问题的具体代码

### 短期目标（1-2 小时）

1. 完成 Task 1-3
2. 找出导致 +1 问题的具体代码
3. 修复问题并运行测试验证

### 中期目标（3-5 小时）

1. 确保所有测试通过
2. 与 Dev 分支对比，确保行为一致
3. 与 DaVinci Resolve 对比，确保行为一致

## 关键指标

- **目标**: 所有测试通过 (66/66)
- **当前**: 64/66 测试通过 (97.0%)
- **差距**: 2 个测试失败

## 风险和缓解措施

### 风险 1: +1 问题可能出在 Timecode slot 的 start 设置中
**缓解措施**:
- 深入分析 Timecode slot 的 start 设置代码
- 使用调试工具跟踪代码执行

### 风险 2: +1 问题可能出在 global_start_time 的计算中
**缓解措施**:
- 深入分析 global_start_time 的计算代码
- 使用调试工具跟踪代码执行

### 风险 3: +1 问题可能是 AAF 文件格式的预期行为
**缓解措施**:
- 检查 AAF 规范
- 咨询 OpenTimelineIO 社区
- 与 DaVinci Resolve 对比

## 时间估计

- Task 1: 30 分钟
- Task 2: 30 分钟
- Task 3: 1 小时
- **总计**: 2 小时

## 总结

在 AAF 写入器中没有发现明显的 +1 问题。需要进一步检查 AAF 读取器中的 Timecode slot 和 global_start_time 的计算，找出导致 +1 问题的具体代码。预计需要 2 小时的工作时间。
