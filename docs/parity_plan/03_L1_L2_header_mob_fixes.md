# Phase 3: L1 + L2 修复 — Header 和 Mob 结构对齐

## 背景

### 项目是什么
`otio-aaf-adapter` 是 OpenTimelineIO 的 AAF 格式适配器。我们正在让它的输出与 DaVinci Resolve 的 AAF 输出在结构上完全一致，以解决 Pro Tools 导入兼容性问题。

### 本阶段目标
根据 `parity_tracker.md` 中的差异清单，逐项修复 L1（Header 层）和 L2（Mob 结构层）的所有差异。每修一项，用 `parity_gate.py` 验证。

### 前置条件
- Phase 1 完成：`parity_tracker.md` 存在
- Phase 2 完成：`parity_gate.py` 可运行
- 熟悉项目代码结构（下文提供关键文件指引）

---

## 关键文件指引

在开始修复之前，必须先阅读以下文件，理解当前的代码结构：

### 写入主入口
**`src/otio_aaf_adapter/adapters/advanced_authoring_format.py`** — `write_to_file()` 函数（约 1641 行起）

这个函数是 OTIO → AAF 导出的入口。它：
1. 打开 AAF 文件句柄
2. 设置 Header 和 Identification（约 1646-1662 行）
3. 调用 `AAFFileTranscriber` 处理 Mob 图
4. 添加 Timecode 槽位（1683 行）
5. 遍历 OTIO track，逐个转录（1686-1734 行）
6. 追加 Filler（1708-1725 行）
7. 按顺序追加所有 Mob（1737 行）

**当前已有的 Pro Tools 兼容性改动**（在此函数中）：
- 注释掉了 OperationalPattern 设置（1646-1649 行）
- 清除了 pyaaf2 默认 Identification，替换为 DaVinci Resolve 伪装标识（1651-1662 行）

### Mob 图构建
**`src/otio_aaf_adapter/adapters/aaf_adapter/aaf_writer.py`** — 几个关键类：

- `AAFFileTranscriber`（85 行起）— 文件级管理器
  - 管理 CompositionMob、MasterMob、TapeMob、FileMob 的创建和追加顺序
  - `append_all_mobs()`（125 行）— 按 CompositionMob → MasterMob → SourceMob(Tape) → SourceMob(WAVE) 顺序追加
  - `add_timecode_first()`（228 行）— 添加 Timecode 作为第一个槽位
  - MobID 前缀已修改为 `060a2b34-0101-0101-0101-0f0013000000`（112 行）

- `VideoTrackTranscriber`（774 行起）— 视频轨道
  - `_master_mob_slot_id = 2`
  - 使用 `CDCIDescriptor`

- `AudioTrackTranscriber`（874 行起）— 音频轨道
  - `_master_mob_slot_id = 1`
  - `audio_sampling_rate = 48000`
  - 使用 `WAVEDescriptor`
  - 有独立的 `aaf_sourceclip()` 覆盖（930 行），做帧→采样的时长转换

### pyaaf2 修改
**`pyaaf2/src/aaf2/file.py`**（约 258 行）— 已注释掉 OperationalPattern 默认设置

### 参考文件
- `correct_timeline.aaf` — DaVinci Resolve 导出的黄金标准 AAF
- `SimpleTimeline.otio` — 测试输入。包含一个视频轨道（Gap 219帧@24fps）和一个音频轨道（ICE.wav 219帧@24fps）
- `parity_tracker.md` — Phase 1 产出的差异清单

---

## 工作流程

### 每项修复的标准流程

```
1. 从 parity_tracker.md 选取一项 OPEN 差异
2. 阅读相关源码，确定修改点
3. 编写最小修复代码
4. 运行验证：
   python parity_gate.py --verbose
5. 检查结果：
   - 该项差异是否消失？
   - 是否引入了新的 FAIL？
   - 二进制差异字节数是否减少（或至少不增加）？
6. 如果通过 → 更新 parity_tracker.md，标记 FIXED
   如果失败 → 回滚修改，记录失败原因
7. 运行回归测试：
   pytest tests/test_aaf_adapter.py -x -q
8. 如果回归测试失败 → 回滚修改，分析原因
```

### 修复优先级

按以下顺序处理。理由：Header 层影响全局解析，必须先修；Mob 数量/类型影响结构遍历，其次；具体属性值最后。

```
优先级 1 — L1 Header 层
优先级 2 — L2 Mob 数量和类型
优先级 3 — L2 Mob 顺序和 SlotID 布局
优先级 4 — L2 具体属性值（EditRate、Length、StartTime 等）
```

---

## 已知差异及修复指引

以下是基于 `TECHNICAL_HANDOVER.md` 和代码分析得出的**预期**差异。实际差异以 `parity_tracker.md` 为准——如果 Phase 1 发现了这里没列出的差异，同样需要修复。

### L1.A — Header.Version

**预期差异**: Correct `{1,1}`, Test `{1,2}`

**根因**: pyaaf2 在 `pyaaf2/src/aaf2/file.py` 第 261 行默认设置 `self.header['Version'].value = {'major': 1, 'minor': 2}`。

**修复位置**: 修改 `pyaaf2/src/aaf2/file.py` 第 261 行：

```python
# 将：
self.header['Version'].value = {u'major': 1, u'minor': 2}
# 改为：
self.header['Version'].value = {u'major': 1, u'minor': 1}
```

**验证**: `parity_gate.py` 中 L1.01 (#1) 应从 FAIL 变为 PASS。

### L1.B — Header.OperationalPattern

**预期状态**: 已修复。`write_to_file()` 中已注释掉 OperationalPattern 设置。

**验证方式**: 确认 `parity_gate.py` 中 L1.02 为 PASS。如果仍为 FAIL，检查 `pyaaf2/src/aaf2/file.py` 中是否有默认设置（历史上已注释掉，但需要确认当前安装的版本是否与修改版一致）。

### L1.C — Identification 属性

**预期状态**: 已部分修复。`write_to_file()` 中已替换为 DaVinci Resolve 标识。但仍有 3 项差异待修复。

**已修复的属性（无需改动）**:
- `CompanyName`: `"Blackmagic Design"` ✅
- `ProductName`: `"DaVinci Resolve"` ✅
- `Platform`: `"AAFSDK (Win32)"` ✅
- `ProductID`: `00000030-0000-0000-6078-0bb91f020000` ✅

**需要修复的属性**:

| 属性 | Correct 值 | Test 值 | tracker_id | 修复方式 |
|------|-----------|---------|-----------|---------|
| `ProductVersionString` | `"Unknown version"` | `"19.0.0.000"` | #3 | 修改 `advanced_authoring_format.py` 第 1657 行，改为 `"Unknown version"` |
| `ProductVersion` | `{major:19, minor:0, tertiary:0, patchLevel:0, type:'VersionReleased'}` | `None`（未设置） | #4 | 在 Identification 创建后添加 `ident['ProductVersion'].value = {'major': 19, 'minor': 0, 'tertiary': 0, 'patchLevel': 0, 'type': 'VersionReleased'}` |
| `ToolkitVersion` | `{major:1, minor:1, tertiary:6, patchLevel:0, type:'VersionReleased'}` | `None`（未设置） | #5 | 在 Identification 创建后添加 `ident['ToolkitVersion'].value = {'major': 1, 'minor': 1, 'tertiary': 6, 'patchLevel': 0, 'type': 'VersionReleased'}` |

**验证**: L1.07 (#3)、L1.08 (#4)、L1.09 (#5) 从 FAIL 变为 PASS。

### L2.A — CompositionMob 的 Slot 数量

**预期差异**: Correct 有 2 个 slot（Timecode + Audio），Test 有 3 个 slot（Timecode + Video + Audio）

**根因**: `SimpleTimeline.otio` 包含一个 Video 轨道（纯 Gap）和一个 Audio 轨道。DaVinci Resolve 导出 AAF 时，可能跳过了纯 Gap 的视频轨道。而我们的适配器会为每个轨道都创建一个 CompositionMob slot。

**修复思路**: 在 `write_to_file()` 的轨道遍历逻辑中（约 1686 行），检测轨道是否全为 Gap。如果是，跳过该轨道，不创建 slot。

```python
for otio_track in timeline.tracks:
    if len(otio_track) == 0:
        continue
    
    # 新增：如果轨道全部是 Gap，跳过
    if all(_is_considered_gap(child) for child in otio_track):
        continue
    
    transcriber = otio2aaf.track_transcriber(otio_track)
    ...
```

**风险**: 这会改变视频轨道的行为。需要确认：对于包含实际视频 clip 的时间线，这个改动不会误跳过。用 `pytest` 验证回归。

**验证**: L2.04 中 CompositionMob 的 slot count 应从 3 变为 2。

### L2.B — CompositionMob 的 Slot 内容对齐

修复 L2.A 后，CompositionMob 的 slot 布局应该是：
- Slot 1: Timecode
- Slot 2: Audio Sequence

需要核对 `correct_timeline.aaf` 中的实际布局，确认我们的 Slot ID 分配正确。

**需要核对**:
- Audio slot 的 SlotID 是多少？（可能是 2）
- Audio slot 的 EditRate 是多少？（应为 48000）
- Audio slot 的 PhysicalTrackNumber 是多少？（应为 1）
- Audio slot 的 name 是什么？

### L2.C — Mob 数量和类型序列

**预期**（与 DaVinci Resolve 对齐）：
1. CompositionMob × 1
2. MasterMob × 1
3. SourceMob (TapeDescriptor) × 1
4. SourceMob (WAVEDescriptor) × 1

**需要验证**:
- 我们的输出是否也是这 4 个 Mob？
- 如果因为跳过视频轨道，是否会少创建某些 Mob？（不应该——视频轨道只有 Gap，不会创建 MasterMob 和 SourceMob）
- Mob 的追加顺序是否正确？（`append_all_mobs()` 已实现正确顺序）

### L2.D — MasterMob 的 Slot 结构

MasterMob 有 1 个 slot（parity_gate 已验证双方一致）：
- Slot 1: SourceClip（EditRate=48000, length=438000, source_mob_slot_id=1）

**唯一差异**: `PhysicalTrackNumber` 为 None，correct 中为 `1`。

**修复**: 在 MasterMob 的 slot 创建逻辑中，添加 `slot["PhysicalTrackNumber"].value = 1`。

**验证**: tracker #15 从 FAIL 变为 PASS。

### L2.E — SourceMob (TapeDescriptor) 的结构

TapeDescriptor SourceMob 有 2 个 slot（parity_gate 已验证双方一致）：
- Slot 1: Timecode（EditRate=24, start=1728, length=219, fps=24, drop=False）
- Slot 2: SourceClip（EditRate=48000, length=438000, source_mob_slot_id=0）

**唯一差异**: 两个 slot 的 `PhysicalTrackNumber` 均为 None，correct 中为 `1`。

**修复**: 在 TapeMob 创建逻辑中，为每个 slot 添加 `slot["PhysicalTrackNumber"].value = 1`。

**验证**: tracker #16 中 SourceMob[TapeDescriptor] 的 2 项 PhysicalTrackNumber 检查从 FAIL 变为 PASS。

### L2.F — SourceMob (WAVEDescriptor) 的结构

WAVEDescriptor SourceMob 有 1 个 slot（parity_gate 已验证双方一致）：
- Slot 1: SourceClip（EditRate=48000, length=438000, source_mob_slot_id=2）

**唯一差异**: `PhysicalTrackNumber` 为 None，correct 中为 `1`。

**修复**: 在 FileMob (WAVEDescriptor SourceMob) 的 slot 创建逻辑中，添加 `slot["PhysicalTrackNumber"].value = 1`。

**验证**: tracker #16 中 SourceMob[WAVEDescriptor] 的 PhysicalTrackNumber 检查从 FAIL 变为 PASS。

### L2.G — Timecode 属性值

CompositionMob 的 Timecode slot 中的 Timecode 对象：

| 属性 | Correct 值 | Test 值 | 状态 |
|------|-----------|---------|------|
| `fps` | 24 | 24 | ✅ PASS |
| `start` | 86400 | 86400 | ✅ PASS |
| `length` | **220** | 219 | ❌ FAIL (#9) |
| `drop` | False | False | ✅ PASS |

**注意**: Correct 的 TC length 是 **220**（比音频 slot 的 219 多 1 frame），Test 是 219。这可能是因为 DaVinci Resolve 在 TC 尾部添加了 1 frame 的 padding，或 OTIO 的 duration 计算有舍入差异。需要检查 `add_timecode_first()` 中的 length 计算逻辑。

### L2.H — CompositionMob Timecode Slot 名称

**差异**: `add_timecode_first()` 第 246 行设置了 `slot.name = "TC"`，但 correct 文件的 TC slot name 是空字符串 `""`。

**修复**: 将第 246 行改为 `slot.name = ""`，或直接删除该行（pyaaf2 默认即为空）。

**验证**: tracker #11 从 FAIL 变为 PASS。

### L2.I — MasterMob / SourceMob 的 MobID 前缀

**差异**: correct 的 MasterMob 和 SourceMob 的 MobID 前缀第 3 组为 `01010d43`，而 Test 输出为 `01010f20`。

- CompositionMob 前缀: `060a2b34.01010101.01010f00.13000000` — **双方一致** ✅
- MasterMob 前缀: `060a2b34.01010105.01010d43.13000000` (correct) vs `060a2b34.01010105.01010f20.13000000` (test) — ❌
- SourceMob 前缀: 同上 — ❌

**根因**: 当前代码只在 CompositionMob 的 MobID 中显式设置了前缀 `01010f00`（第 108/112 行），但 MasterMob 和 SourceMob 的 MobID 由 pyaaf2 默认生成（`01010f20`）。DaVinci Resolve 使用的是 `01010d43`。

**修复思路**: 在 `aaf_writer.py` 中创建 MasterMob 和 SourceMob 时，显式设置 MobID 前缀为 `01010d43`。需要研究 pyaaf2 的 MobID 生成 API（`aaf2.mobid.MobID` 或类似接口）。

**tracker_id**: #28 (MasterMob), #29 (SourceMob[Tape]), #30 (SourceMob[WAVE])

**验证**: L2.06 中 MasterMob 和 SourceMob 的 MobID.prefix 检查从 FAIL 变为 PASS。

### Phase 3 完整修复清单

以下是 Phase 3 需要修复的所有 L1 + L2 FAIL 项（共 15 项，对应 parity_tracker 中的 12 个 tracker_id）。L3 项留给 Phase 4。

| # | tracker_id | 层级 | 差异描述 | 修复节 |
|---|-----------|------|---------|--------|
| 1 | #1 | L1 | Header.Version {1,2} → {1,1} | L1.A |
| 2 | #3 | L1 | ProductVersionString "19.0.0.000" → "Unknown version" | L1.C |
| 3 | #4 | L1 | ProductVersion None → {19,0,0,0,Released} | L1.C |
| 4 | #5 | L1 | ToolkitVersion None → {1,1,6,0,Released} | L1.C |
| 5 | #8 | L2 | CompositionMob 多余的视频 slot（SlotID=2） | L2.A |
| 6 | #9 | L2 | CompositionMob TC length 219 → 220 | L2.G |
| 7 | #11 | L2 | CompositionMob TC slot name "TC" → "" | L2.H |
| 8 | #15 | L2 | MasterMob.PhysicalTrackNumber None → 1 | L2.D |
| 9 | #16 | L2 | SourceMob[Tape].Slot[0].PhysicalTrackNumber None → 1 | L2.E |
| 10 | #16 | L2 | SourceMob[Tape].Slot[1].PhysicalTrackNumber None → 1 | L2.E |
| 11 | #16 | L2 | SourceMob[WAVE].Slot[0].PhysicalTrackNumber None → 1 | L2.F |
| 12 | #28 | L2 | MasterMob.MobID.prefix 01010f20 → 01010d43 | L2.I |
| 13 | #29 | L2 | SourceMob[Tape].MobID.prefix 01010f20 → 01010d43 | L2.I |
| 14 | #30 | L2 | SourceMob[WAVE].MobID.prefix 01010f20 → 01010d43 | L2.I |

**注意**: L1.01 (#1) 需要修改 pyaaf2 源码（`file.py` 第 261 行）。其余项只需修改 adapter 代码。

---

## 修复 pyaaf2 的指引

如果某些差异无法通过 `aaf_writer.py` 或 `advanced_authoring_format.py` 解决，需要修改 pyaaf2。

### 修改原则

1. **最小修改** — 只改必须改的行为
2. **不破坏 pyaaf2 自身测试** — 每次修改后跑 `pytest pyaaf2/tests/ -x -q`
3. **记录修改** — 在 `parity_tracker.md` 中记录每次 pyaaf2 修改

### 可能需要修改 pyaaf2 的场景

1. **Header.Version 无法通过 API 设置**: 需要在 `pyaaf2/src/aaf2/file.py` 中找到 version 的设置点并开放 API
2. **Dictionary 中注册了多余的 ClassDefinition**: 需要研究 pyaaf2 在 `save()` 或 `close()` 时注册了哪些默认定义
3. **OperationalPattern 被 pyaaf2 在保存时自动设置**: 确认 `file.py` 中的注释是否生效

### pyaaf2 安装同步

**关键提醒**: 项目中有一个 `pyaaf2/` 目录是修改后的本地副本。修改后需要确保安装的是这个版本：

```bash
uv pip install -e ./pyaaf2
```

每次修改 pyaaf2 后，不需要重新安装（editable install 会自动生效），但需要重启 Python 进程。

---

## 验证检查点

每完成一组相关修复后，运行以下命令确认状态：

```bash
# 1. 快速验证（<30秒）
python parity_gate.py

# 2. 详细验证
python parity_gate.py --verbose

# 3. 回归测试
pytest tests/test_aaf_adapter.py -x -q

# 4. 更新收敛日志
python parity_gate.py --update-tracker
```

### 回滚规则

以下任何一种情况发生时，必须回滚本次修改：

1. `parity_gate.py` 报告了新的 FAIL（之前 PASS 的项变成 FAIL）
2. `pytest` 有用例失败
3. 二进制差异字节数显著增加（增加 > 100 字节且无法解释）

回滚方式：`git checkout -- <modified_files>`

---

## 交付物

1. 所有 L1 和 L2 差异已消除（或标注为 WHITELIST/BLOCKED 并附原因）
2. `parity_tracker.md` 已更新：所有修复项标记为 FIXED
3. `parity_gate.py --verbose` 输出中 L1 和 L2 区域全部 PASS 或 SKIP
4. `pytest tests/test_aaf_adapter.py` 全部通过
5. 收敛日志有完整记录

## 验收标准

1. `python parity_gate.py` 输出中 L1 和 L2 无 FAIL
2. `pytest tests/test_aaf_adapter.py -x -q` 全部通过
3. 如果有 pyaaf2 修改，`pytest pyaaf2/tests/ -x -q` 全部通过
4. `parity_tracker.md` 中所有 L1、L2 项状态为 FIXED 或 WHITELIST
5. 收敛日志中二进制差异字节数不应增加（CFB SectorSize 差异留待 Phase 5 处理，L1/L2 修复可能只减少少量字节）

---

## 注意事项

- **一次只修复一项差异。** 不要批量修改后再验证——这会让你无法确定哪个修改导致了新问题。
- **先修 L1，再修 L2。** L1 的修改（如 Header Version）可能影响 L2 的二进制偏移，先修 L1 能让 L2 的二进制对比结果更稳定。
- **不要修改 L3 的属性。** L3（Descriptor 层）留给 Phase 4 处理。
- **不要删除或修改 `parity_gate.py`。** 如果发现 `parity_gate.py` 有 bug，记录下来但不修复——那是 Phase 2 的范围。
- 如果遇到无法解决的差异（例如 pyaaf2 的行为无法控制），标记为 BLOCKED，记录原因和你尝试过的方法，继续处理下一项。
