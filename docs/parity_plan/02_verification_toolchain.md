# Phase 2: 验证工具链 — 实现 `parity_gate.py`

## 背景

### 项目是什么
`otio-aaf-adapter` 是 OpenTimelineIO (OTIO) 的 AAF 格式适配器。我们正在让它的输出与 DaVinci Resolve 的 AAF 输出在结构上完全一致，以解决 Pro Tools 导入兼容性问题。

### 本阶段目标
实现 `parity_gate.py` —— 一个一键运行的验证入口，整合语义检查和二进制差异统计。后续每次代码修改后都会运行这个脚本来判定修改是否有效。它是整个修复流程的裁判。

### 前置条件
- Phase 1 已完成，`parity_tracker.md` 存在且包含完整差异清单（27 项差异）
- 项目环境已搭建（Python + pyaaf2 + opentimelineio）
- `correct_timeline.aaf` 和 `test_output.aaf` 都存在
- `SimpleTimeline.otio` 已更新（clip name 和 media reference 已对齐 correct 的 `"A1-0001_ICE"`）

---

## 设计规范

### 核心职责

`parity_gate.py` 做三件事：
1. 自动导出 `test_output.aaf`（调用 test_export.py 的逻辑）
2. 对 `correct_timeline.aaf` 和 `test_output.aaf` 进行语义级对比
3. 对两个文件进行二进制级对比（**仅统计，不参与 PASS/FAIL 判定**）

最终输出一个 **PASS / FAIL** 判定，**完全由语义检查决定**。

### 命令行接口

```bash
# 默认模式：运行全部检查，输出摘要
python parity_gate.py

# 详细模式：输出每一项检查的详情
python parity_gate.py --verbose

# 只运行语义检查
python parity_gate.py --semantic-only

# 只运行二进制对比
python parity_gate.py --binary-only

# 指定文件路径（覆盖默认值）
python parity_gate.py --correct correct_timeline.aaf --test test_output.aaf

# 跳过导出步骤（直接对比已有文件）
python parity_gate.py --skip-export

# 更新 parity_tracker.md 的收敛日志
python parity_gate.py --update-tracker
```

### 输出格式

#### 默认模式

```
AAF Parity Gate
═══════════════

[L1 - Header]           13 checks: 8 PASS, 3 FAIL, 2 SKIP
[L2 - Mob Structure]   22 checks: 12 PASS, 10 FAIL
[L3 - Descriptor]      12 checks: 5 PASS, 7 FAIL
[Binary]              36333 diff groups, 370548 diff bytes (info only)

RESULT: FAIL (20 errors)
  #1   L1.Header.Version: expected {1,1}, got {1,2}
  #4   L1.Identification[0].ProductVersion: expected {19,0,0,0,Released}, got None
  #5   L1.Identification[0].ToolkitVersion: expected {1,1,6,0,Released}, got None
  #8   L2.CompositionMob.Slots.count: expected 2, got 3
  ...
```

**注意**: 每条 FAIL 前面的 `#N` 是 `parity_tracker.md` 差异清单中的编号，方便追踪。

#### 详细模式 (--verbose)

```
AAF Parity Gate (verbose)
═════════════════════════

[L1 - Header]
  PASS  [#-]  Header.OperationalPattern: None == None
  FAIL  [#1]  Header.Version: expected {1,1}, got {1,2}
  SKIP  [#-]  Header.ObjectModelVersion: 30 vs 64 (whitelisted: pyaaf2 internal)
  PASS  [#-]  Identification count: 1 == 1
  PASS  [#-]  Identification[0].CompanyName: "Blackmagic Design" == "Blackmagic Design"
  PASS  [#-]  Identification[0].ProductName: "DaVinci Resolve" == "DaVinci Resolve"
  FAIL  [#3]  Identification[0].ProductVersionString: expected "Unknown version", got "19.0.0.000"
  FAIL  [#4]  Identification[0].ProductVersion: expected {19,0,0,0,Released}, got None
  FAIL  [#5]  Identification[0].ToolkitVersion: expected {1,1,6,0,Released}, got None
  PASS  [#-]  Identification[0].Platform: "win32" == "win32"
  PASS  [#-]  Identification[0].ProductID: <AUID> == <AUID>
  SKIP  [#6]  Identification[0].Date: (timestamp, whitelisted)
  SKIP  [#7]  Identification[0].GenerationAUID: (uuid, whitelisted)

[L2 - Mob Structure]
  PASS  [#-]  Mob count: 4 == 4
  PASS  [#-]  Mob type sequence: [CompositionMob, MasterMob, SourceMob, SourceMob]
  PASS  [#-]  CompositionMob.name: "Timeline 1" == "Timeline 1"
  PASS  [#-]  MasterMob.name: "A1-0001_ICE" == "A1-0001_ICE"
  FAIL  [#8]  CompositionMob.Slots.count: expected 2, got 3
  FAIL  [#9]  CompositionMob.Slot[0](Timecode).Segment.length: expected 220, got 219
  FAIL  [#12] CompositionMob.Slot[1](Audio).PhysicalTrackNumber: expected 1, got None
  ...
  SKIP  [#-]  MobID UUID parts: (uuid, whitelisted)

[L3 - Descriptor]
  PASS  [#-]  SourceMob[Tape].Descriptor.type: TapeDescriptor == TapeDescriptor
  PASS  [#-]  SourceMob[WAVE].Descriptor.type: WAVEDescriptor == WAVEDescriptor
  PASS  [#-]  WAVEDescriptor.SampleRate: 48000/1 == 48000/1
  PASS  [#-]  WAVEDescriptor.Length: 438000 == 438000
  FAIL  [#19] WAVEDescriptor.Summary.wav_byte_rate: expected 144000, got 96000
  FAIL  [#20] WAVEDescriptor.Summary.wav_block_align: expected 3, got 2
  FAIL  [#21] WAVEDescriptor.Summary.wav_bits_per_sample: expected 24, got 16
  FAIL  [#22] WAVEDescriptor.Summary[4:8] (RIFF size): expected non-zero, got 0
  FAIL  [#23] WAVEDescriptor.Summary[40:44] (data size): expected non-zero, got 0
  PASS  [#-]  EssenceSummary byte length: 44 == 44
  PASS  [#-]  Locator count: 1 == 1
  FAIL  [#24] NetworkLocator.URLString filename: expected "A1-0001_ICE.wav", got "ICE.wav"

[Binary] (info only — does not affect PASS/FAIL)
  Total file sizes: correct=221184, test=462848
  Raw diff bytes: 370548
  Diff groups: 36333
  Note: majority of binary diffs caused by CFB SectorSize difference (512 vs 1024)

───────────────────────────────
RESULT: FAIL (20 semantic errors)
───────────────────────────────
```

### 返回码

- `0`: PASS（所有语义检查通过或 SKIP）
- `1`: FAIL（存在语义 FAIL 项）
- `2`: ERROR（脚本运行错误，如文件不存在）

---

## 实现规范

### 文件结构

```
parity_gate.py          # 主入口
```

整个工具在一个文件中实现。不需要拆分模块——保持简单，方便后续 AI 直接运行和理解。

### 架构设计

```python
# 伪代码结构

class CheckResult:
    """单项检查结果"""
    status: str       # "PASS", "FAIL", "SKIP"
    layer: str        # "L1", "L2", "L3", "L0"
    path: str         # e.g. "Header.Version"
    expected: Any
    actual: Any
    reason: str       # SKIP 时的原因，如 "whitelisted: timestamp"
    tracker_id: int   # 对应 parity_tracker.md 差异清单中的编号，无对应则为 None

class ParityGate:
    def __init__(self, correct_path, test_path):
        ...

    def run_semantic_checks(self) -> list[CheckResult]:
        results = []
        results.extend(self._check_L1_header())
        results.extend(self._check_L2_mob_structure())
        results.extend(self._check_L3_descriptors())
        return results

    def run_binary_diff(self) -> dict:
        """返回二进制差异统计摘要，不逐项对比。"""
        ...

    def _check_L1_header(self) -> list[CheckResult]:
        """检查 Header 层属性"""
        ...

    def _check_L2_mob_structure(self) -> list[CheckResult]:
        """检查 Mob 结构"""
        ...

    def _check_L3_descriptors(self) -> list[CheckResult]:
        """检查 Descriptor 属性"""
        ...
```

### 语义检查清单

以下是 `parity_gate.py` 需要实现的全部语义检查项。每一项都标注了 `tracker_id`（对应 `parity_tracker.md` 差异清单的 #编号），无对应项的 `tracker_id` 为 `None`。

**"当前预期"列**表示在初始基线（未做任何 adapter 修复）时该项的预期状态。

#### L1 - Header 层检查（13 项）

| ID | tracker_id | 属性路径 | 比较方式 | 白名单 | 当前预期 |
|----|-----------|---------|---------|--------|---------|
| L1.01 | #1 | `Header.Version` | 精确匹配 tuple | 否 | FAIL: {1,1} vs {1,2} |
| L1.02 | — | `Header.OperationalPattern` | 精确匹配（均应为 None/未设置） | 否 | PASS |
| L1.03 | — | `Header.ObjectModelVersion` | 记录但不判定 | 是 | SKIP |
| L1.04 | — | `len(IdentificationList)` | 精确匹配 | 否 | PASS |
| L1.05 | — | `Identification[0].CompanyName` | 精确匹配字符串 | 否 | PASS |
| L1.06 | — | `Identification[0].ProductName` | 精确匹配字符串 | 否 | PASS |
| L1.07 | #3 | `Identification[0].ProductVersionString` | 精确匹配字符串 | 否 | FAIL: "Unknown version" vs "19.0.0.000" |
| L1.08 | #4 | `Identification[0].ProductVersion` | 精确匹配 dict/tuple | 否 | FAIL: {19,0,0,0,Released} vs None |
| L1.09 | #5 | `Identification[0].ToolkitVersion` | 精确匹配 dict/tuple | 否 | FAIL: {1,1,6,0,Released} vs None |
| L1.10 | — | `Identification[0].Platform` | 精确匹配字符串 | 否 | PASS |
| L1.11 | — | `Identification[0].ProductID` | 精确匹配 AUID | 否 | PASS |
| L1.12 | #6 | `Identification[0].Date` | 跳过 | 是 | SKIP |
| L1.13 | #7 | `Identification[0].GenerationAUID` | 跳过 | 是 | SKIP |

#### L2 - Mob 结构检查（22 项）

| ID | tracker_id | 属性路径 | 比较方式 | 白名单 | 当前预期 |
|----|-----------|---------|---------|--------|---------|
| L2.01 | — | `len(ContentStorage.Mobs)` | 精确匹配 | 否 | PASS: 4 == 4 |
| L2.02 | — | Mob 类型序列 | 有序匹配 `[类名]` 列表 | 否 | PASS |
| L2.03 | — | 每个 Mob 的 `name` | 精确匹配 | 否 | PASS (OTIO 已对齐) |
| L2.04 | #8 | `CompositionMob.len(slots)` | 精确匹配 | 否 | FAIL: 2 vs 3 |
| L2.05 | — | 其他 Mob 的 `len(slots)` | 精确匹配 | 否 | PASS |
| L2.06 | — | 每个 MobID 的前缀部分 | 匹配前 32 hex chars | 否 | PASS |
| L2.07 | — | 每个 MobID 的 UUID 部分 | 跳过 | 是 | SKIP |
| L2.08 | #10 | `CompositionMob.Slot[*].slot_id` | 精确匹配（按槽位顺序） | 否 | FAIL: 视频槽导致偏移 |
| L2.09 | #11 | `CompositionMob.Slot[*].edit_rate` | 精确匹配 Rational | 否 | FAIL: 视频槽 EditRate=24 |
| L2.10 | #12 | `CompositionMob.Slot[*].PhysicalTrackNumber` | 精确匹配 | 否 | FAIL: 全部 None |
| L2.11 | #15 | `MasterMob.Slot[0].PhysicalTrackNumber` | 精确匹配 | 否 | FAIL: None vs 1 |
| L2.12 | #16 | `SourceMob[*].Slot[*].PhysicalTrackNumber` | 精确匹配 | 否 | FAIL: 全部 None |
| L2.13 | — | 每个 Slot 的 `name` | 精确匹配 | 否 | PASS |
| L2.14 | — | 每个 Slot 的 Segment 类型 | 精确匹配类名 | 否 | PASS |
| L2.15 | — | Timecode.start | 精确匹配 | 否 | PASS: 86400/1728 |
| L2.16 | #9 | `CompositionMob.Timecode.length` | 精确匹配 | 否 | FAIL: 220 vs 219 |
| L2.17 | — | Timecode.fps | 精确匹配 | 否 | PASS: 24 |
| L2.18 | — | Timecode.drop | 精确匹配 | 否 | PASS |
| L2.19 | — | Sequence 中的 Component 数量 | 精确匹配 | 否 | PASS: 2 == 2 |
| L2.20 | — | 每个 Component 的类型 | 精确匹配 | 否 | PASS |
| L2.21 | — | 每个 Component 的 `length` | 精确匹配 | 否 | PASS |
| L2.22 | — | SourceClip 的 `start_time` 和 `source_mob_slot_id` | 精确匹配 | 否 | PASS |

#### L3 - Descriptor 层检查（12 项）

| ID | tracker_id | 属性路径 | 比较方式 | 白名单 | 当前预期 |
|----|-----------|---------|---------|--------|---------|
| L3.01 | — | 每个 SourceMob 的 Descriptor 类型 | 精确匹配类名 | 否 | PASS |
| L3.02 | — | TapeDescriptor 存在性 | 精确匹配 | 否 | PASS |
| L3.03 | — | `WAVEDescriptor.SampleRate` | 精确匹配 Rational | 否 | PASS: 48000/1 |
| L3.04 | — | `WAVEDescriptor.AudioSamplingRate` | 精确匹配（如果存在） | 否 | PASS |
| L3.05 | — | `WAVEDescriptor.Length` | 精确匹配 | 否 | PASS: 438000 |
| L3.06 | #19 | `Summary.wav_byte_rate` | 精确匹配 | 否 | FAIL: 144000 vs 96000 |
| L3.07 | #20 | `Summary.wav_block_align` | 精确匹配 | 否 | FAIL: 3 vs 2 |
| L3.08 | #21 | `Summary.wav_bits_per_sample` | 精确匹配 | 否 | FAIL: 24 vs 16 |
| L3.09 | #22 | `Summary[4:8]` RIFF chunk size | 非零检查 | 否 | FAIL: non-zero vs 0 |
| L3.10 | #23 | `Summary[40:44]` data chunk size | 非零检查 | 否 | FAIL: non-zero vs 0 |
| L3.11 | — | Locator 数量 | 精确匹配 | 否 | PASS: 1 == 1 |
| L3.12 | #24 | `NetworkLocator.URLString` 文件名部分 | 文件名匹配 | 否 | FAIL (adapter 生成逻辑) |

#### L0 - Dictionary 检查（3 项，info only）

| ID | tracker_id | 属性路径 | 比较方式 | 白名单 | 当前预期 |
|----|-----------|---------|---------|--------|---------|
| L0.01 | #25 | `ContainerDefinitions` 差异 | 记录集合差 | pyaaf2 | INFO: 大小写差异 |
| L0.02 | #26 | `DataDefinitions` 多出项 | 记录集合差 | pyaaf2 | INFO: +2 项 |
| L0.03 | #27 | `CodecDefinitions` 多出项 | 记录集合差 | pyaaf2 | INFO: +1 项 |

**注**: L0 项标记为 INFO，不参与 PASS/FAIL 判定。它们属于 pyaaf2 默认注册行为，在 Phase 5 L0 调查阶段再决定是否修复。

### 检查项总计

| 层级 | 总项数 | 当前预期 PASS | 当前预期 FAIL | 当前预期 SKIP | 当前预期 INFO |
|------|--------|-------------|-------------|-------------|-------------|
| L1 | 13 | 7 | 4 (#1,#3,#4,#5) | 2 (#6,#7) | — |
| L2 | 22 | 14 | 7 (#8,#9,#10,#11,#12,#15,#16) | 1 (MobID UUID) | — |
| L3 | 12 | 5 | 7 (#19,#20,#21,#22,#23,#24, 加上 #14 Mob name 已在 OTIO 修复后消除) | — | — |
| L0 | 3 | — | — | — | 3 |
| **合计** | **50** | **26** | **18** | **3** | **3** |

**注**: 差异清单中的 #13 (CompositionMob AudioSequence Components 结构一致)、#14 (MasterMob name，OTIO 修复后已消除)、#17-#18 (SourceMob name，OTIO 修复后已消除) 不再出现在 FAIL 中。

### 二进制对比实现规范

#### 定位：信息参考，非判定器

**二进制对比不参与 PASS/FAIL 判定。** 原因：

Phase 1 数据显示，当前 36333 组二进制差异中，绝大多数（>36000 组）是由 CFB SectorSize 不同（512 vs 1024）引起的连锁偏移——与语义层差异无关。在 CFB SectorSize 对齐之前（Phase 5 L0 调查），二进制对比无法有效区分"有意义的差异"和"容器噪声"。

因此，`parity_gate.py` 的二进制对比只做以下统计输出：

```
[Binary] (info only)
  File sizes: correct=221184, test=462848
  Total diff bytes: 370548
  Total diff groups: 36333
```

这些数字记录到收敛日志中，用于观察趋势（如 SectorSize 修复后差异组数应骤降），但不影响返回码。

#### 未来升级路径

当 Phase 5 完成 CFB SectorSize 对齐后，可以升级二进制对比为：
1. 完整差异组列表输出
2. 白名单过滤（MobID UUID、Date、GenerationAUID）
3. 净差异组数参与 PASS/FAIL 判定

但当前阶段不需要实现这些。

### `--update-tracker` 功能

当传入 `--update-tracker` 时，自动在 `parity_tracker.md` 的收敛日志中追加一行。

**实现方式**：在 `parity_tracker.md` 的收敛日志表格末尾有一个锚点注释 `<!-- convergence-log-end -->`，脚本找到该锚点并在其前面插入新行。

```python
def update_tracker(self, semantic_results, binary_stats, note=""):
    """在 parity_tracker.md 的收敛日志表格中追加一行"""
    today = datetime.date.today().isoformat()
    fail_count = sum(1 for r in semantic_results if r.status == "FAIL")
    line = f"| {today} | {fail_count} | {binary_stats['diff_groups']} | {binary_stats['diff_bytes']} | {note} |"

    tracker_path = "parity_tracker.md"
    content = open(tracker_path, encoding='utf-8').read()
    anchor = "<!-- convergence-log-end -->"
    if anchor not in content:
        print(f"WARNING: anchor '{anchor}' not found in {tracker_path}, skipping update")
        return
    content = content.replace(anchor, f"{line}\n{anchor}")
    with open(tracker_path, 'w', encoding='utf-8') as f:
        f.write(content)
```

**注意**: 首次使用此功能前，需要在 `parity_tracker.md` 的收敛日志表格末尾添加锚点：
```markdown
| 2026-06-02 | 27 | 36333 | 370548 | 初始基线 |
<!-- convergence-log-end -->
```

---

## Mob 对齐策略

语义检查需要将 correct 和 test 的 Mob 对齐。

**对齐策略**（按优先级）：

1. **按 Mob 类型分组**：`CompositionMob`、`MasterMob`、`SourceMob`
2. **同类型 Mob 按 Descriptor 类型细分**（仅 SourceMob）：`TapeDescriptor` vs `WAVEDescriptor`
3. **同组内按出现顺序对齐**

**为什么不用 name 对齐**：虽然 SimpleTimeline.otio 已更新使 name 一致，但后续测试可能引入 name 不同的场景。按类型+Descriptor+顺序对齐更鲁棒，且不依赖 name 必须相同。

**对齐伪代码**：

```python
def align_mobs(correct_mobs, test_mobs):
    """返回 [(correct_mob, test_mob), ...] 的对齐列表"""
    from collections import defaultdict

    def mob_key(mob):
        desc_type = ""
        if hasattr(mob, 'descriptor') and mob.descriptor:
            desc_type = mob.descriptor.__class__.__name__
        return (mob.__class__.__name__, desc_type)

    groups_correct = defaultdict(list)
    groups_test = defaultdict(list)

    for mob in correct_mobs:
        groups_correct[mob_key(mob)].append(mob)
    for mob in test_mobs:
        groups_test[mob_key(mob)].append(mob)

    aligned = []
    all_keys = set(groups_correct.keys()) | set(groups_test.keys())
    for key in sorted(all_keys):
        c_list = groups_correct[key]
        t_list = groups_test[key]
        for i in range(max(len(c_list), len(t_list))):
            c = c_list[i] if i < len(c_list) else None
            t = t_list[i] if i < len(t_list) else None
            aligned.append((c, t))
    return aligned
```

如果 correct 和 test 的 Mob 数量或类型不匹配，缺失方用 `None` 填充，对应检查项标记为 FAIL。

---

## 交付物

1. `parity_gate.py` 文件，放在项目根目录
2. 运行 `python parity_gate.py --verbose` 的完整输出，作为验证截图
3. `parity_tracker.md` 收敛日志中添加 `<!-- convergence-log-end -->` 锚点

## 验收标准

1. `python parity_gate.py` 能成功运行，不报错
2. 输出包含 L1、L2、L3 三个层级的检查结果
3. 每项检查有明确的 PASS/FAIL/SKIP 状态
4. 白名单项标记为 SKIP，附带原因
5. 每条 FAIL 项标注 `tracker_id`（对应 parity_tracker 的 #N）
6. 二进制差异有摘要输出（字节数、组数），但不影响 PASS/FAIL
7. 最终有 PASS/FAIL 判定和返回码（0=PASS, 1=FAIL, 2=ERROR）
8. `--verbose` 模式输出每一项的详情
9. 对着当前的 `test_output.aaf` 运行，FAIL 项与下方"当前预期 FAIL 列表"完全一致
10. `--update-tracker` 能正确追加收敛日志（通过锚点定位）

### 当前预期 FAIL 列表（验收基准）

以下 18 项在初始基线运行时应为 FAIL，不多不少：

| # | 检查项 | tracker_id |
|---|--------|-----------|
| 1 | L1.01 Header.Version | #1 |
| 2 | L1.07 ProductVersionString | #3 |
| 3 | L1.08 ProductVersion | #4 |
| 4 | L1.09 ToolkitVersion | #5 |
| 5 | L2.04 CompositionMob.Slots.count | #8 |
| 6 | L2.08 CompositionMob.Slot[*].slot_id | #10 |
| 7 | L2.09 CompositionMob.Slot[*].edit_rate | #11 |
| 8 | L2.10 CompositionMob.PhysicalTrackNumber | #12 |
| 9 | L2.11 MasterMob.PhysicalTrackNumber | #15 |
| 10 | L2.12 SourceMob.PhysicalTrackNumber | #16 |
| 11 | L2.16 CompositionMob.Timecode.length | #9 |
| 12 | L3.06 Summary.wav_byte_rate | #19 |
| 13 | L3.07 Summary.wav_block_align | #20 |
| 14 | L3.08 Summary.wav_bits_per_sample | #21 |
| 15 | L3.09 Summary RIFF size | #22 |
| 16 | L3.10 Summary data size | #23 |
| 17 | L3.12 NetworkLocator URL filename | #24 |

**注**: 实际为 17 项 FAIL。差异清单中的 #14 (MasterMob name)、#17 (SourceMob name) 已通过 OTIO 修改消除。#13 (AudioSequence Components) 在 Phase 1 中已确认一致。

---

## 注意事项

- 不要修改 `src/` 目录下的源码或 `pyaaf2/` 目录下的任何代码
- 可以修改 `test_export.py`（如果需要让它支持静默模式被 parity_gate 调用）
- `parity_gate.py` 中所有路径应使用项目根目录的相对路径：
  ```python
  CORRECT_AAF_PATH = "correct_timeline.aaf"
  TEST_AAF_PATH = "test_output.aaf"
  ```
- 脚本必须兼容 Python 3.9+
- 不要引入 pyaaf2 和 opentimelineio 之外的第三方依赖
- 保持代码简洁——一个文件，不拆模块
- L0 Dictionary 差异只做 INFO 记录，不影响 PASS/FAIL
