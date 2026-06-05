# Phase 4: L3 修复 — Descriptor 和 Essence 对齐

## 背景

### 项目是什么
`otio-aaf-adapter` 是 OpenTimelineIO 的 AAF 格式适配器。我们正在让它的输出与 DaVinci Resolve 的 AAF 输出在结构上完全一致，以解决 Pro Tools 导入兼容性问题（采样率被误读为 30 Hz）。

### 本阶段目标
修复 L3 层（Descriptor 和 Essence）的所有差异。L3 层包含 WAVEDescriptor、TapeDescriptor 的属性，以及 EssenceSummary（嵌入的 WAV Header 字节）和 NetworkLocator。

**这一层可能是 30 Hz 问题的根因所在。** Pro Tools 从 Descriptor 和 Essence 中读取采样率信息。如果这些值与 DaVinci Resolve 的输出不一致，即使结构正确，Pro Tools 也可能误解析。

### 前置条件
- Phase 1 完成：`parity_tracker.md` 存在
- Phase 2 完成：`parity_gate.py` 可运行
- Phase 3 已完成或可并行（L3 与 L1/L2 在代码层面大体独立）

---

## 关键文件指引

### Descriptor 创建位置

**`src/otio_aaf_adapter/adapters/aaf_adapter/aaf_writer.py`** — `AudioTrackTranscriber.default_descriptor()` 方法（972 行起）

这个方法创建 WAVEDescriptor，是 L3 层的核心。当前实现：

```python
def default_descriptor(self, otio_clip):
    descriptor = self.aaf_file.create.WAVEDescriptor()
    descriptor["SampleRate"].value = self.audio_sampling_rate      # 48000
    descriptor["Length"].value = length_samples                     # 438000
    
    # NetworkLocator
    locator["URLString"].value = "file:///" + media.target_url.replace("\\", "/")
    descriptor["Locator"].append(locator)
    
    # EssenceSummary (WAV Header bytes, 44 bytes)
    descriptor["Summary"].value = bytearray([...])
    
    return descriptor
```

### FileMob 创建位置

**`aaf_writer.py`** — `_TrackTranscriber._create_filemob()` 方法（697 行起）

FileMob 是挂载 WAVEDescriptor 的 SourceMob。当前实现：
- `filemob.name = otio_clip.name`（ICE.wav）
- `filemob.descriptor = self.default_descriptor(otio_clip)` — 调用上面的方法
- 创建一个 timeline slot，EditRate = 48000
- slot 中放一个 SourceClip，指向 TapeDescriptor SourceMob

### TapeMob 创建位置

**`aaf_writer.py`** — `AAFFileTranscriber._unique_tapemob()` 方法（184 行起）

TapeDescriptor SourceMob 的创建。当前实现：
- `tapemob.name = ""`（空名字）
- `tapemob.descriptor = self.aaf_file.create.TapeDescriptor()`
- 创建 Timecode slot（EditRate = clip 的 rate）
- Timecode 的 start 和 length 来自 clip 的 available_range

### TapeMob slot 创建

**`aaf_writer.py`** — `_TrackTranscriber._create_tapemob()` 方法（668 行起）

在 TapeMob 上创建 empty slot（Filler）。对于音频轨道：
- EditRate = 48000
- Length = 音频采样数

### 参考文件
- `correct_timeline.aaf` — DaVinci Resolve 导出的参考
- `parity_tracker.md` — Phase 1 的差异清单

---

## 修复项

### L3.A — WAVEDescriptor 属性对齐

**需要核对并修复的属性**：

| 属性 | 说明 | 当前代码中的值 | 需要与 correct 核对 |
|------|------|--------------|-------------------|
| `SampleRate` | 采样率（Rational） | 48000 (int，pyaaf2 可能转为 48000/1) | 确认 Rational 格式 |
| `Length` | 采样总数 | 438000 (计算值) | 确认计算正确 |
| `AudioSamplingRate` | 音频采样率 | 未显式设置 | **可能缺失！** |
| `Channels` | 通道数 | 未显式设置 | **可能缺失！** |
| `QuantizationBits` | 量化位深 | 未显式设置 | **可能缺失！** |
| `ContainerFormat` | 容器格式 AUID | 未显式设置 | **可能缺失！** |
| `Summary` | WAV Header 字节 | 44 字节 | 逐字节核对 |

**重点关注**: `AudioSamplingRate`、`Channels`、`QuantizationBits` 这三个属性在当前代码中**未显式设置**。如果 DaVinci Resolve 的输出中包含这些属性，缺失可能导致 Pro Tools 使用默认值——而这个默认值可能就是 30 Hz 的来源。

#### 修复步骤

1. 先用 pyaaf2 读取 `correct_timeline.aaf`，枚举 WAVEDescriptor 的**全部属性**：

```python
import aaf2

with aaf2.open("correct_timeline.aaf") as f:
    for mob in f.content.mobs:
        if hasattr(mob, 'descriptor') and mob.descriptor:
            desc = mob.descriptor
            if desc.__class__.__name__ == 'WAVEDescriptor':
                print(f"WAVEDescriptor on mob: {mob.name}")
                # 枚举所有已设置的属性
                for prop in desc.properties():
                    print(f"  {prop.name}: {prop.value}")
```

2. 将 correct 中有、test 中没有的属性全部补齐到 `default_descriptor()` 中

3. 将 correct 中有但值不同的属性修正

#### WAVEDescriptor 的属性设置参考

以下是 AAF 规范中 WAVEDescriptor 可能包含的属性，以及设置方式：

```python
descriptor = self.aaf_file.create.WAVEDescriptor()

# 必需属性
descriptor["SampleRate"].value = aaf2.rational.AAFRational(48000, 1)
descriptor["Length"].value = 438000

# 可能需要补充的属性
descriptor["AudioSamplingRate"].value = aaf2.rational.AAFRational(48000, 1)
descriptor["Channels"].value = 1
descriptor["QuantizationBits"].value = 16

# ContainerFormat — 可能需要特定的 AUID
# 需要从 correct_timeline.aaf 中读取确切值
# descriptor["ContainerFormat"].value = aaf2.auid.AUID("...")
```

### L3.B — EssenceSummary（WAV Header）逐字节对齐

**当前实现**（aaf_writer.py 1011-1024 行）：
手动构造了一个 44 字节的 WAV Header。

**需要核对**：
1. correct_timeline.aaf 中的 Summary 是多少字节？
2. 逐字节是否一致？

```python
import aaf2

with aaf2.open("correct_timeline.aaf") as f1, aaf2.open("test_output.aaf") as f2:
    for mob in f1.content.mobs:
        if hasattr(mob, 'descriptor') and mob.descriptor:
            if mob.descriptor.__class__.__name__ == 'WAVEDescriptor':
                summary1 = mob.descriptor['Summary'].value
                print(f"Correct Summary ({len(summary1)} bytes):")
                print(f"  hex: {summary1.hex()}")
    
    for mob in f2.content.mobs:
        if hasattr(mob, 'descriptor') and mob.descriptor:
            if mob.descriptor.__class__.__name__ == 'WAVEDescriptor':
                summary2 = mob.descriptor['Summary'].value
                print(f"Test Summary ({len(summary2)} bytes):")
                print(f"  hex: {summary2.hex()}")
    
    if summary1 == summary2:
        print("Summary 完全一致!")
    else:
        print("Summary 不一致!")
        for i in range(min(len(summary1), len(summary2))):
            if summary1[i] != summary2[i]:
                print(f"  byte [{i}]: correct=0x{summary1[i]:02x} test=0x{summary2[i]:02x}")
```

**如果 Summary 不一致**：直接从 correct_timeline.aaf 中提取 Summary 的实际字节值，硬编码到 `default_descriptor()` 中——或者更好的方式是理解每个字段的含义，确保计算逻辑正确。

WAV Header 格式参考（44 字节标准头）：

| 偏移 | 字节数 | 字段 | 说明 |
|------|--------|------|------|
| 0 | 4 | ChunkID | "RIFF" (0x52494646) |
| 4 | 4 | ChunkSize | 文件大小 - 8 |
| 8 | 4 | Format | "WAVE" (0x57415645) |
| 12 | 4 | Subchunk1ID | "fmt " (0x666D7420) |
| 16 | 4 | Subchunk1Size | 16 (PCM) |
| 20 | 2 | AudioFormat | 1 (PCM) |
| 22 | 2 | NumChannels | 1 (Mono) |
| 24 | 4 | SampleRate | 48000 |
| 28 | 4 | ByteRate | 96000 (SampleRate * NumChannels * BitsPerSample/8) |
| 32 | 2 | BlockAlign | 2 (NumChannels * BitsPerSample/8) |
| 34 | 2 | BitsPerSample | 16 |
| 36 | 4 | Subchunk2ID | "data" (0x64617461) |
| 40 | 4 | Subchunk2Size | NumSamples * NumChannels * BitsPerSample/8 |

**注意 ChunkSize 和 Subchunk2Size**：当前代码中两者都设为 0。DaVinci Resolve 可能设置了实际值。这可能是关键差异。

### L3.C — NetworkLocator URL 格式

**当前实现**（aaf_writer.py 998 行）：
```python
locator["URLString"].value = "file:///" + media.target_url.replace("\\", "/")
```

**需要核对**：
- correct_timeline.aaf 中的 URLString 是什么格式？
- 是否使用 `file:///` 前缀？
- 路径分隔符是 `/` 还是 `\`？
- 路径是否 URL 编码？

### L3.D — TapeDescriptor 属性

TapeDescriptor 通常不需要额外属性，但需要确认 correct_timeline.aaf 中的 TapeDescriptor 是否包含我们没有设置的属性。

```python
import aaf2

with aaf2.open("correct_timeline.aaf") as f:
    for mob in f.content.mobs:
        if hasattr(mob, 'descriptor') and mob.descriptor:
            if mob.descriptor.__class__.__name__ == 'TapeDescriptor':
                print(f"TapeDescriptor on mob: {mob.name}")
                for prop in desc.properties():
                    print(f"  {prop.name}: {prop.value}")
```

### L3.E — Descriptor 类继承关系

AAF 的 Descriptor 有继承关系：

```
EssenceDescriptor
  └── FileDescriptor
        ├── WAVEDescriptor
        ├── AIFCDescriptor
        └── CDCIDescriptor
  └── PhysicalDescriptor
        └── TapeDescriptor
```

`WAVEDescriptor` 继承自 `FileDescriptor`，而 `FileDescriptor` 有自己的属性（如 `SampleRate`、`Length`、`ContainerFormat`）。`WAVEDescriptor` 增加了 `Summary` 属性。

需要确认：DaVinci Resolve 是否在 `FileDescriptor` 层级设置了我们遗漏的属性。完整枚举 correct_timeline.aaf 中 WAVEDescriptor 的所有属性（包括继承属性）是关键步骤。

---

## 工作流程

与 Phase 3 相同的单项修复循环：

```
1. 从 L3 差异中选取一项
2. 分析根因
3. 修改 default_descriptor() 或相关代码
4. python parity_gate.py --verbose
5. 检查 L3 区域的 PASS/FAIL 变化
6. 检查二进制差异是否减少
7. pytest tests/test_aaf_adapter.py -x -q
8. 更新 parity_tracker.md
```

### 修复优先级

```
优先级 1 — WAVEDescriptor 缺失属性（L3.A 中标红的属性）
优先级 2 — EssenceSummary 字节对齐（L3.B）
优先级 3 — NetworkLocator URL 格式（L3.C）
优先级 4 — TapeDescriptor 属性（L3.D）
```

理由：缺失属性最可能是 30 Hz 问题的根因；Summary 字节可能被 Pro Tools 直接解析；URL 格式影响媒体链接但不影响采样率；TapeDescriptor 属性优先级最低。

---

## 特别注意：30 Hz 问题

### 可能的根因假设

如果在完成 L3 修复后，`parity_gate.py` 全部 PASS 但 Pro Tools 仍显示 30 Hz，以下是进一步排查方向：

1. **WAVEDescriptor vs PCMDescriptor**: 检查 DaVinci Resolve 实际使用的是 `WAVEDescriptor` 还是 `PCMDescriptor`。如果是 `PCMDescriptor`，它有更多的音频属性（如 `AverageBPS`、`BlockAlign` 等直接在对象上而非 Summary 中）。

2. **AudioSamplingRate 的 Rational 精度**: 
   - 48000 作为 `int` 传给 pyaaf2 时，存储为 `48000/1`
   - 如果 DaVinci Resolve 存储为 `48000/1` 但 pyaaf2 存储为其他格式（如 `48000` 不带分母），Pro Tools 可能误解

3. **ContainerFormat 的影响**: 如果 ContainerFormat 指向了错误的容器类型，Pro Tools 可能按错误的解码器解析

4. **Summary 中的 Subchunk2Size**:
   - 如果 DaVinci Resolve 在 Summary 中填写了实际数据大小，而我们填了 0
   - Pro Tools 可能用 `Subchunk2Size / ByteRate` 来计算时长
   - `0 / 96000 = 0`，不是 30
   - 但如果有其他计算路径...

5. **隐藏属性**:
   - AAF 允许私有扩展属性
   - DaVinci Resolve 可能设置了某些非标准属性
   - 用 `desc.properties()` 枚举 correct_timeline.aaf 时要注意不在标准列表中的属性名

### 调试建议

在修复过程中，每次修复后都记录 `parity_gate.py` 的二进制差异变化。如果某次修复导致二进制差异大幅减少，这很可能是一个关键修复。特别关注与以下字节模式相关的差异：

- `0x1E`（十进制 30）— 直接包含 30 这个值的字节
- `0x80BB0000`（48000 的 little-endian 表示）— 采样率相关
- `0x00770100`（96000 的 little-endian 表示）— ByteRate 相关

---

## 交付物

1. 所有 L3 差异已消除（或标注为 WHITELIST/BLOCKED 并附原因）
2. `parity_tracker.md` 中 L3 项全部标记为 FIXED 或 WHITELIST
3. `parity_gate.py --verbose` 输出中 L3 区域全部 PASS 或 SKIP
4. `pytest tests/test_aaf_adapter.py` 全部通过
5. 收敛日志有完整记录

## 验收标准

1. `python parity_gate.py` 输出中 L3 无 FAIL
2. `pytest tests/test_aaf_adapter.py -x -q` 全部通过
3. `parity_tracker.md` 中所有 L3 项状态为 FIXED 或 WHITELIST
4. 如果有 pyaaf2 修改，`pytest pyaaf2/tests/ -x -q` 全部通过
5. WAVEDescriptor 的所有属性（包括 Summary 字节）与 correct_timeline.aaf 一致

---

## 注意事项

- **完整枚举 correct 的属性是第一步。** 不要假设你知道 DaVinci Resolve 设置了哪些属性——用 `desc.properties()` 全量枚举。
- **Rational 类型需要精确处理。** 不要直接传 int，使用 `aaf2.rational.AAFRational(48000, 1)` 确保分子/分母格式正确。
- **Summary 字节不要猜，要算或抄。** 如果计算方式不确定，直接从 correct_timeline.aaf 中提取实际字节值。
- **不要修改 L1/L2 层的代码。** 如果发现 L1/L2 层有新问题，记录到 `parity_tracker.md` 但不修复——那是 Phase 3 的范围。
- 如果发现 pyaaf2 的 `WAVEDescriptor` 不支持设置某个属性，可能需要使用底层 API：
  ```python
  desc[prop_name].value = value  # 直接通过属性名设置
  ```
