# Off-by-One 问题分析进展

## 当前发现

### AAF 写入器分析

#### 1. _create_tapemob 方法 (line 812-827)
```python
tapemob_slot.segment.start = int(
    otio_clip.media_reference.available_range.start_time.value)
```
- 直接使用了 available_range.start_time.value
- **没有 +1**

#### 2. _unique_tapemob 方法 (line 181-213)
```python
timecode_start = int(
    otio_clip.media_reference.available_range.start_time.value
)
tape_timecode_slot.segment.start = int(timecode_start)
```
- 直接使用了 available_range.start_time.value
- **没有 +1**

#### 3. _create_filemob 方法 (line 872-893)
```python
filemob_clip.length = tapemob_slot.segment.length
```
- 使用了 tapemob_slot.segment.length
- **没有 +1**

#### 4. _create_mastermob 方法 (line 896-918)
```python
timecode_length = int(otio_clip.media_reference.available_range.duration.value)
mastermob_clip.length = timecode_length
```
- 使用了 available_range.duration.value
- **没有 +1**

### 初步结论
在 AAF 写入器中，没有发现明显的 +1 问题。所有的时间值都是直接使用 available_range 的值，没有进行任何偏移。

## 下一步行动

### 1. 检查 AAF 读取器
需要检查 AAF 读取器中是否有导致 source_range.start_time 计算错误的代码。

可能的地方：
- _transcribe_sourceclip 方法
- _transcribe_available_range 方法
- _transcribe_visible_range 方法

### 2. 对比 Dev 和 PT-Compat 分支的读取器代码
需要对比两个分支中 AAF 读取器的代码差异，找出导致 +1 问题的具体代码。

### 3. 使用调试工具
使用调试工具逐步跟踪代码执行，找出导致 +1 问题的具体代码。

## 时间估计

- 检查 AAF 读取器: 2-3 小时
- 对比 Dev 和 PT-Compat 分支: 2-3 小时
- 使用调试工具: 2-3 小时
- **总计**: 6-9 小时

## 风险和缓解措施

### 风险 1: +1 问题可能出在 AAF 读取器中
**缓解措施**:
- 深入分析 AAF 读取器代码
- 使用调试工具逐步跟踪代码执行

### 风险 2: +1 问题可能出在 AAF 文件格式本身
**缓解措施**:
- 检查 AAF 规范
- 咨询 OpenTimelineIO 社区

### 风险 3: +1 问题可能是预期行为
**缓解措施**:
- 检查 DaVinci Resolve 的行为
- 咨询 OpenTimelineIO 社区

## 总结

在 AAF 写入器中没有发现明显的 +1 问题。需要进一步检查 AAF 读取器，找出导致 +1 问题的具体代码。预计需要 6-9 小时的工作时间。
