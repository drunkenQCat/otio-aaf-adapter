# Phase 1: 诊断基线 — 建立完整差异清单

## 背景

### 项目是什么
`otio-aaf-adapter` 是 OpenTimelineIO (OTIO) 的 AAF 格式适配器。它能将 OTIO 时间线导出为 AAF 文件。当前问题是：导出的 AAF 文件无法被 Avid Pro Tools 正确导入（采样率被误读为 30 Hz，应为 48000 Hz）。

### 为什么要做这件事
DaVinci Resolve 导出的 AAF 文件可以被 Pro Tools 完美导入。我们的策略是：让我们的输出在结构上与 DaVinci Resolve 的输出完全一致。差异越小，越容易定位 Pro Tools 的兼容性问题根因。

### 本阶段目标
**纯分析，不改项目核心源码。** 运行所有对比工具，产出一份结构化的差异清单 `parity_tracker.md`，作为后续修复工作的完整输入。

### 层级定义

本方案将 AAF 文件的差异分为四个层级（详见 `BINARY_PARITY_PLAN.md` §1.1）：

| 层级 | 内容 | 说明 |
|------|------|------|
| L0 | CFB 容器层 | Microsoft Structured Storage 的 Sector 大小、FAT 表、Directory Entry 排列。由 pyaaf2 底层写入引擎决定。 |
| L1 | Header 对象层 | AAF Header 中的 Version、OperationalPattern、Identification、Dictionary 等文件级元数据。 |
| L2 | Mob 图结构层 | Mob 的类型、数量、顺序；每个 Mob 的 Slot 结构（SlotID、EditRate、Segment 树）；SourceClip 引用链。 |
| L3 | Essence/Descriptor 层 | WAVEDescriptor、TapeDescriptor 的属性值；EssenceSummary（嵌入的 WAV Header 字节）；NetworkLocator。 |

### 不可控变量白名单

以下差异**预期存在**，在差异清单中标记为"不可控"，不视为需修复的问题：

- **MobID 中的 UUID 部分** — 每次生成不同的唯一标识符
- **Identification 中的 Date 时间戳** — 导出时间必然不同
- **Identification 中的 GenerationAUID** — 每次生成不同
- **CFB 容器层的 sector 分配顺序** — pyaaf2 和 DaVinci Resolve 使用不同的写入引擎
- **Dictionary 中未引用的 ClassDefinition 差异** — pyaaf2 可能注册比 DaVinci Resolve 更多的类型定义

---

## 前置条件

### 环境
- Python 3.9+，已安装项目依赖（`pip install -e .`）
- `pyaaf2` 已安装（项目本地有修改版，位于 `pyaaf2/`，需要 `pip install -e ./pyaaf2`）
- Windows 环境（因为参考文件路径和测试环境为 Windows）

### 关键文件
| 文件 | 路径 | 说明 |
|------|------|------|
| 参考 AAF（黄金标准） | `correct_timeline.aaf`（项目根目录） | DaVinci Resolve 导出的 AAF |
| 测试输入 | `SimpleTimeline.otio`（项目根目录） | DaVinci Resolve 导出的 OTIO 时间线 |
| 导出脚本 | `test_export.py`（项目根目录） | 将 SimpleTimeline.otio 导出为 test_output.aaf |
| 语义对比 | `deep_compare_aaf.py` | 用 pyaaf2 API 逐属性对比两个 AAF 文件 |
| 二进制对比 | `compare_binary.py` | 逐字节对比两个 AAF 文件 |
| Dump 对比 | `diff_dumps.py` | 对比两个 AAF dump 文本输出（可选补充手段，仅在需要 AAF SDK dump 工具时使用） |
| 专项检查 | `check_*.py`（多个） | 各种专项属性检查脚本 |

### 参考 AAF 的备用路径
如果 `correct_timeline.aaf` 不在项目根目录，历史路径为：
```
C:\TechProjects\About_Voice_Cloning\AAF-src-1.2.0\AAF\aaf-rs\output\correct_timeline.aaf
```

---

## 执行步骤

### Step 0: 前置校验

在开始任何分析之前，确认以下文件全部存在：

- [ ] `correct_timeline.aaf`（项目根目录，或上述备用路径）
- [ ] `SimpleTimeline.otio`
- [ ] `test_export.py`
- [ ] `deep_compare_aaf.py`
- [ ] `compare_binary.py`
- [ ] `check_sample_rate.py`
- [ ] `check_all_rates.py`
- [ ] `check_mob_order.py`
- [ ] `check_wav_header.py`

如果 `correct_timeline.aaf` 不存在，**立即报告并中止整个 Phase 1**，不要用其他文件替代。

如果某个 `check_*.py` 脚本不存在，记录缺失但继续执行其余步骤。

### Step 1: 生成当前测试输出

```bash
python test_export.py
```

确认生成了 `test_output.aaf`，记录文件大小。同时记录 `correct_timeline.aaf` 的文件大小。

**记录内容**:
- `test_output.aaf` 文件大小（字节）
- `correct_timeline.aaf` 文件大小（字节）
- 大小差异

### Step 2: 运行语义对比

```bash
python deep_compare_aaf.py
```

注意：`deep_compare_aaf.py` 中硬编码了路径，需要调整脚本底部的路径常量使其指向正确的文件：
- `correct_path`：指向 `correct_timeline.aaf`
- `test_path`：指向 `test_output.aaf`

**允许修改对比脚本中的路径常量**（不算修改项目核心源码）。

**记录全部输出**，特别关注所有标记为 `❌` 或 `⚠️` 的项。

### Step 3: 运行二进制对比

```bash
python compare_binary.py
```

同样需要调整脚本底部的路径常量。

**记录内容**:
- 差异字节总数
- 差异占比
- 差异组数
- 每组差异的偏移量、长度、Correct 值、Test 值

### Step 4: 深度属性枚举

创建一个新脚本 `enumerate_properties.py`（这是诊断工具，不算项目核心源码），对两个 AAF 文件分别做全量属性枚举。

脚本内容如下：

```python
#!/usr/bin/env python
"""枚举 AAF 文件中的所有关键属性，用于 Phase 1 诊断基线。"""

import aaf2
import sys


def enumerate_all_properties(filepath):
    """枚举 AAF 文件中的所有关键属性"""
    with aaf2.open(filepath) as f:
        # === L1: Header 层 ===
        print("=== L1: HEADER ===")
        print(f"  Version: {f.header.version}")
        print(f"  ObjectModelVersion: {f.header.object_model_version}")

        try:
            op = f.header['OperationalPattern'].value
            print(f"  OperationalPattern: {op}")
        except Exception:
            print("  OperationalPattern: NOT SET")

        print("\n=== L1: IDENTIFICATIONS ===")
        idents = list(f.header.identifications)
        print(f"  Count: {len(idents)}")
        for i, ident in enumerate(idents):
            print(f"  [{i}] CompanyName: {ident.company_name}")
            print(f"  [{i}] ProductName: {ident.product_name}")
            print(f"  [{i}] ProductVersionString: {ident.product_version_string}")
            print(f"  [{i}] Platform: {ident.platform}")
            try:
                print(f"  [{i}] ProductID: {ident['ProductID'].value}")
            except Exception:
                print(f"  [{i}] ProductID: N/A")
            try:
                print(f"  [{i}] Date: {ident['Date'].value}")
            except Exception:
                pass
            try:
                print(f"  [{i}] GenerationAUID: {ident['GenerationAUID'].value}")
            except Exception:
                pass

        # === L2: Mob 图结构层 ===
        print("\n=== L2: MOBS ===")
        mobs = list(f.content.mobs)
        print(f"  Total Mobs: {len(mobs)}")
        print(f"  Mob type sequence: {[m.__class__.__name__ for m in mobs]}")

        for i, mob in enumerate(mobs):
            mob_type = mob.__class__.__name__
            print(f"\n  --- Mob [{i}] {mob_type} ---")
            print(f"  Name: '{mob.name}'")
            print(f"  MobID: {mob.mob_id}")
            mob_id_str = str(mob.mob_id)
            print(f"  MobID prefix (first 32 hex): {mob_id_str[:47]}")
            print(f"  Slots: {len(list(mob.slots))}")

            for j, slot in enumerate(mob.slots):
                print(f"    Slot [{j}]:")
                print(f"      SlotID: {slot.slot_id}")
                print(f"      EditRate: {slot.edit_rate}")
                try:
                    print(f"      PhysicalTrackNumber: {slot['PhysicalTrackNumber'].value}")
                except Exception:
                    print("      PhysicalTrackNumber: NOT SET")
                try:
                    print(f"      SlotName: '{slot.name}'")
                except Exception:
                    pass

                seg = slot.segment
                print(f"      Segment: {seg.__class__.__name__}")
                if hasattr(seg, 'length'):
                    print(f"        Length: {seg.length}")
                if hasattr(seg, 'start'):
                    print(f"        Start: {seg.start}")
                if hasattr(seg, 'fps'):
                    print(f"        FPS: {seg.fps}")
                if hasattr(seg, 'drop'):
                    print(f"        Drop: {seg.drop}")

                if hasattr(seg, 'components'):
                    comps = list(seg.components)
                    print(f"        Components: {len(comps)}")
                    for k, comp in enumerate(comps):
                        comp_type = comp.__class__.__name__
                        info = f"          [{k}] {comp_type}"
                        if hasattr(comp, 'length'):
                            info += f" Length={comp.length}"
                        if hasattr(comp, 'start_time'):
                            info += f" StartTime={comp.start_time}"
                        if hasattr(comp, 'source_mob_slot_id'):
                            info += f" SourceMobSlotID={comp.source_mob_slot_id}"
                        if hasattr(comp, 'mob') and comp.mob:
                            info += f" SourceMob={comp.mob.__class__.__name__}"
                        print(info)

            # === L3: Descriptor 层 ===
            if hasattr(mob, 'descriptor') and mob.descriptor:
                desc = mob.descriptor
                print(f"    Descriptor: {desc.__class__.__name__}")
                # 枚举所有已设置的属性（不限于已知列表）
                print("    Descriptor properties (all):")
                try:
                    for prop in desc.properties():
                        val = prop.value
                        # 对于 bytes 类型，只显示长度和前 44 字节 hex
                        if isinstance(val, (bytes, bytearray)):
                            print(f"      {prop.name}: ({len(val)} bytes) {val[:44].hex()}")
                        else:
                            print(f"      {prop.name}: {val}")
                except Exception as e:
                    print(f"    (error enumerating properties: {e})")
                    # 回退到已知属性列表
                    for prop_name in ['SampleRate', 'Length', 'AudioSamplingRate',
                                      'Channels', 'QuantizationBits', 'ContainerFormat',
                                      'Summary']:
                        try:
                            val = desc[prop_name].value
                            if isinstance(val, (bytes, bytearray)):
                                print(f"      {prop_name}: ({len(val)} bytes) {val[:44].hex()}")
                            else:
                                print(f"      {prop_name}: {val}")
                        except Exception:
                            pass
                # Locator
                try:
                    locs = list(desc['Locator'].value)
                    print(f"    Locators: {len(locs)}")
                    for loc in locs:
                        print(f"      URL: {loc['URLString'].value}")
                except Exception:
                    pass


if __name__ == "__main__":
    correct_path = sys.argv[1] if len(sys.argv) > 1 else "correct_timeline.aaf"
    test_path = sys.argv[2] if len(sys.argv) > 2 else "test_output.aaf"

    print("=" * 80)
    print(f"FILE: {correct_path}")
    print("=" * 80)
    enumerate_all_properties(correct_path)

    print("\n\n" + "=" * 80)
    print(f"FILE: {test_path}")
    print("=" * 80)
    enumerate_all_properties(test_path)
```

运行方式：

```bash
python enumerate_properties.py correct_timeline.aaf test_output.aaf
```

**注意**: 这个脚本使用 `desc.properties()` 做全量枚举，不限于已知属性名。这是关键——如果 DaVinci Resolve 设置了某个我们不知道的属性，这里会被捕获到。

### Step 5: 运行专项检查脚本

依次运行以下脚本。对比脚本中的路径常量可以按需调整。

```bash
python check_sample_rate.py
python check_all_rates.py
python check_edit_rates.py
python check_mob_order.py
python check_operational_pattern.py
python check_wav_header.py
python check_wavedescriptor_details.py
python check_pro_tools_compat.py
```

将每个脚本的**完整输出**记录到 `parity_tracker.md` 的附录 A 中。如果某个脚本不存在或运行报错，记录错误信息后继续下一个。

在主表差异清单中，只引用附录中的条目编号（如"详见附录 A.3"），不在主表中重复粘贴完整输出。

### Step 6: Dictionary 对比

创建 `compare_dictionary.py` 脚本（同样是诊断工具），对比两个文件的 Dictionary 内容。

脚本内容：

```python
#!/usr/bin/env python
"""对比两个 AAF 文件的 Dictionary（ClassDefinition 和 TypeDefinition）。"""

import aaf2
import sys


def compare_dictionaries(correct_path, test_path):
    with aaf2.open(correct_path) as f1, aaf2.open(test_path) as f2:
        # === ClassDefinitions ===
        print("=== ClassDefinition 对比 ===")
        classes1 = set()
        classes2 = set()
        for classdef in f1.dictionary.class_defs():
            classes1.add(classdef.class_name)
        for classdef in f2.dictionary.class_defs():
            classes2.add(classdef.class_name)

        common = classes1 & classes2
        only_in_correct = classes1 - classes2
        only_in_test = classes2 - classes1

        print(f"Common: {len(common)}")
        print(f"Only in correct: {len(only_in_correct)}")
        for c in sorted(only_in_correct):
            print(f"  {c}")
        print(f"Only in test: {len(only_in_test)}")
        for c in sorted(only_in_test):
            print(f"  {c}")

        # === TypeDefinitions ===
        print("\n=== TypeDefinition 对比 ===")
        types1 = set()
        types2 = set()
        try:
            for typedef in f1.dictionary.type_defs():
                types1.add(typedef.type_name)
        except Exception as e:
            print(f"  (error reading correct TypeDefs: {e})")
        try:
            for typedef in f2.dictionary.type_defs():
                types2.add(typedef.type_name)
        except Exception as e:
            print(f"  (error reading test TypeDefs: {e})")

        if types1 or types2:
            common_t = types1 & types2
            only_in_correct_t = types1 - types2
            only_in_test_t = types2 - types1

            print(f"Common: {len(common_t)}")
            print(f"Only in correct: {len(only_in_correct_t)}")
            for t in sorted(only_in_correct_t):
                print(f"  {t}")
            print(f"Only in test: {len(only_in_test_t)}")
            for t in sorted(only_in_test_t):
                print(f"  {t}")
        else:
            print("  (TypeDefinition enumeration not supported or empty)")


if __name__ == "__main__":
    correct_path = sys.argv[1] if len(sys.argv) > 1 else "correct_timeline.aaf"
    test_path = sys.argv[2] if len(sys.argv) > 2 else "test_output.aaf"
    compare_dictionaries(correct_path, test_path)
```

运行方式：

```bash
python compare_dictionary.py correct_timeline.aaf test_output.aaf
```

---

## 交付物

### 主交付物: `parity_tracker.md`

在项目根目录创建 `parity_tracker.md`，包含以下内容：

#### 1. 文件级摘要

```markdown
## 文件级摘要

| 项目 | Correct | Test | 状态 |
|------|---------|------|------|
| 文件大小 | 221184 bytes | ??? bytes | ??? |
| Mob 数量 | 4 | ??? | ??? |
| Identification 数量 | 1 | ??? | ??? |
```

#### 2. 差异清单

每条差异一行，格式如下。**这个格式是整个项目的统一标准**，后续 Phase 3/4/5 都使用相同格式。

```markdown
## 差异清单

| # | 层级 | 属性路径 | Correct 值 | Test 值 | 可控？ | 状态 | 备注 |
|---|------|---------|-----------|---------|-------|------|------|
| 1 | L1 | Header.Version | {1,1} | {1,2} | pyaaf2 | OPEN | pyaaf2 默认值 |
| 2 | L1 | Header.OperationalPattern | None | ??? | 是 | OPEN | 已在 write_to_file 中注释 |
| 3 | L2 | CompositionMob.Slots.count | 2 | 3 | 是 | OPEN | 多了 Video 槽 |
| 4 | L1 | Identification[0].Date | (时间戳) | (时间戳) | 不可控 | WHITELIST | 每次导出时间不同 |
| ... | ... | ... | ... | ... | ... | ... | ... |
```

**"层级"列**: L0 / L1 / L2 / L3，定义见上文"层级定义"章节。

**"可控"列的含义**:
- **是**: 可以通过修改 `aaf_writer.py` 或 `advanced_authoring_format.py` 来消除
- **pyaaf2**: 需要修改 pyaaf2 源码才能消除
- **不可控**: 每次运行必然不同（UUID、时间戳等），属于白名单范围

**"状态"列的含义**:
- **OPEN**: 差异存在，待后续阶段修复
- **WHITELIST**: 不可控差异，已确认无需修复
- **BLOCKED**: 需要更多信息才能判断是否可修复

注意：Phase 1 是纯诊断阶段，不会有 **FIXED** 状态的项。FIXED 状态在后续 Phase 3/4 修复时使用。

#### 3. 二进制差异摘要

```markdown
## 二进制差异摘要

- 差异字节总数: ???
- 差异占比: ???%
- 差异组数: ???

### 差异组详情
（从 compare_binary.py 输出中复制。如果总组数 ≤ 20，全部复制；如果超过 20 组，复制前 20 组并注明总数。）
```

#### 4. Dictionary 差异

```markdown
## Dictionary 差异

### ClassDefinition
- Common: ??? 个
- 仅在 Correct 中: ??? 个
  - （列出）
- 仅在 Test 中: ??? 个
  - （列出）

### TypeDefinition
- Common: ??? 个
- 仅在 Correct 中: ??? 个
  - （列出）
- 仅在 Test 中: ??? 个
  - （列出）
```

#### 5. 收敛日志（初始行）

```markdown
## 收敛日志

| 日期 | 语义差异数 | 二进制差异组数 | 二进制差异字节数 | 备注 |
|------|-----------|--------------|----------------|------|
| 2026-06-02 | ??? | ??? | ??? | 初始基线 |
```

#### 6. 附录 A: 专项检查脚本输出

```markdown
## 附录 A: 专项检查脚本完整输出

### A.1 check_sample_rate.py
（完整输出）

### A.2 check_all_rates.py
（完整输出）

### A.3 check_edit_rates.py
（完整输出）

...
```

### 辅助交付物: 诊断脚本

在项目根目录创建以下两个诊断脚本（供后续阶段复用）：

- `enumerate_properties.py`（Step 4 中定义的脚本）
- `compare_dictionary.py`（Step 6 中定义的脚本）

---

## 验收标准

本阶段完成的标志：

1. `test_output.aaf` 已成功生成，无运行时错误
2. `parity_tracker.md` 已创建，包含上述全部 6 个章节（文件级摘要、差异清单、二进制差异摘要、Dictionary 差异、收敛日志、附录 A）
3. 差异清单中的每一条都有明确的层级 (L0/L1/L2/L3) 和属性路径
4. 每条差异都标注了"可控"列（是 / pyaaf2 / 不可控）
5. 没有遗漏：所有 `deep_compare_aaf.py` 标记为 `❌` 或 `⚠️` 的项都出现在清单中
6. 没有遗漏：所有 `compare_binary.py` 输出的差异组都有记录
7. `enumerate_properties.py` 的全量枚举中发现的、不在 `deep_compare_aaf.py` 输出中的额外差异也已记录
8. Dictionary 差异（ClassDefinition 和 TypeDefinition）已记录
9. 收敛日志的初始行已填入具体数值
10. 所有不可控差异已标记为 WHITELIST

---

## 注意事项

- **不要修改项目核心源码**（`src/` 目录下的文件和 `pyaaf2/` 目录下的文件）。对比脚本（`deep_compare_aaf.py`、`compare_binary.py` 等）中的路径常量可以按需调整。新建诊断脚本（`enumerate_properties.py`、`compare_dictionary.py`）属于本阶段的交付物。
- 如果某个脚本运行报错，记录错误信息和 traceback，继续执行其余步骤。
- 如果发现 `correct_timeline.aaf` 文件不存在或路径有误，**立即报告并中止**，不要用其他文件替代。
- 如果发现 `enumerate_properties.py` 的全量枚举中有未预料到的属性或对象类型，全部记录——这可能是 30 Hz 问题的关键线索。
- `parity_tracker.md` 的格式很重要：它将被后续阶段的 AI 直接消费，结构化程度越高越好。
- 本阶段没有自动化反馈环。验证方式是人工检查 `parity_tracker.md` 的完整性：对照验收标准逐条核对。
