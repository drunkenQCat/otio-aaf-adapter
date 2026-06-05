# AAF 二进制对齐工程方案

**目标**: 使 otio-aaf-adapter 输出的 AAF 文件与 DaVinci Resolve 输出的 AAF 文件在结构层面严丝合缝，最终被 Pro Tools 正确导入。

**基准文件**: `correct_timeline.aaf` (DaVinci Resolve 导出)
**测试输入**: `SimpleTimeline.otio` (DaVinci Resolve 导出的 OTIO)

---

## 一、核心原则

### 1.1 分层对齐，逐层收敛

AAF 文件本质是 Microsoft Structured Storage (OLE/CFB) 容器内的对象图。我们不追求逐字节完全一致（GUID、时间戳等必然不同），而是追求**结构等价**——在剥离不可控变量后，所有可控字节完全相同。

对齐工作分为四层，从外到内依次推进。**这是整个方案的核心分层模型，后续所有文档、差异清单、验证工具都基于这四层展开：**

| 层级 | 内容 | 可控性 | 说明 |
|------|------|--------|------|
| L0 - CFB 容器 | Sector 大小、FAT 表、Directory Entry 排列 | 部分可控（pyaaf2 决定） | Microsoft Structured Storage 底层格式。不同写入引擎的布局可能不同，但语义等价。 |
| L1 - Header 对象 | Version、OperationalPattern、Identification、Dictionary | 完全可控 | AAF 文件级元数据。影响全局解析行为，必须优先对齐。 |
| L2 - Mob 图 | Mob 类型/数量/顺序、Slot 结构、Segment 树、MobID 格式 | 完全可控 | AAF 的核心数据结构。定义了时间线中所有媒体对象的引用关系。 |
| L3 - Essence/Descriptor | WAVEDescriptor 属性、EssenceSummary (WAV Header)、Locator | 完全可控 | 媒体描述层。包含采样率、位深、通道数等音频属性，最可能是 30 Hz 问题的根因所在。 |

### 1.2 不可控变量白名单

以下差异**预期存在**，不视为失败：

- MobID 中的 UUID 部分（每次生成不同）
- Identification 中的 Date 时间戳
- Identification 中的 GenerationAUID
- CFB 容器层的 sector 分配顺序（如果对象数量和大小一致，pyaaf2 通常会产生相同布局）
- Dictionary 中未引用的 class definition 差异（pyaaf2 可能注册更多类型）

除此之外的一切差异，都需要解释原因并消除。

---

## 二、工作阶段

### Phase 1: 建立精确基线（诊断）

**目标**: 生成一份完整的差异清单，精确到每个 AAF 属性。

**执行手册**: [`docs/parity_plan/01_diagnostic_baseline.md`](docs/parity_plan/01_diagnostic_baseline.md)

**门禁条件**: `parity_tracker.md` 存在且包含所有已知差异，每条差异有明确的层级（L0-L3）、属性路径和可控性标注。

> 注: Phase 1 仅使用 `deep_compare_aaf.py` + `compare_binary.py` + `enumerate_properties.py` 进行手动对比和整理。`parity_gate.py` 在 Phase 2 才开始实施。

---

### Phase 2: 构建验证工具链

**目标**: 实现 `parity_gate.py`，为后续修复阶段提供自动化验证。

**执行手册**: [`docs/parity_plan/02_verification_toolchain.md`](docs/parity_plan/02_verification_toolchain.md)

**门禁条件**: `parity_gate.py` 可运行，输出的 FAIL 项与 `parity_tracker.md` 一致。

---

### Phase 3: L1 + L2 修复（Header 和 Mob 结构）

**目标**: 消除 Header 层和 Mob 结构层的所有差异。

**执行手册**: [`docs/parity_plan/03_L1_L2_header_mob_fixes.md`](docs/parity_plan/03_L1_L2_header_mob_fixes.md)

#### 工作流（单项修复循环）

```
┌──────────────────────────────────────────────────────┐
│  1. 从 parity_tracker.md 选取一项 OPEN 差异          │
│  2. 分析根因，确定修改点（aaf_writer.py 或 pyaaf2）   │
│  3. 编写最小修复代码                                  │
│  4. 运行验证管线 (见下文)                             │
│  5. 如果验证通过 → 标记 FIXED，提交                   │
│     如果验证失败 → 回滚，记录失败原因，标记 BLOCKED    │
│  6. 如果新增差异出现 → 追加到清单                      │
└──────────────────────────────────────────────────────┘
```

#### 优先级排序

1. **L1 差异优先** — Header 层的差异影响全局解析行为
2. **L2 结构差异次之** — Mob 数量、槽位数量、Mob 顺序
3. **L2 属性差异** — EditRate、Length、StartTime 等数值
4. **L3 Descriptor 差异** — WAVEDescriptor 属性、EssenceSummary

#### 验证门禁

> **单项修复通过标准**: 该项差异消失，且不引入新的差异（diff 差异总数 <= 修复前）。

---

### Phase 4: L3 修复（Descriptor 和 Essence）

**目标**: 消除 Descriptor 层的所有差异。可与 Phase 3 并行。

**执行手册**: [`docs/parity_plan/04_L3_descriptor_fixes.md`](docs/parity_plan/04_L3_descriptor_fixes.md)

**门禁条件**: `parity_gate.py` 中 L3 区域全部 PASS 或 SKIP。

---

### Phase 5: 回归验证 + L0 调查 + 最终判定

**目标**: 确认所有差异消除后，文件能被 Pro Tools 正确导入。

**执行手册**: [`docs/parity_plan/05_regression_and_L0.md`](docs/parity_plan/05_regression_and_L0.md)

#### 步骤

1. 运行完整验证管线，确认差异数归零（不可控变量除外）
2. 将 `test_output.aaf` 导入 Pro Tools（使用替换 DLL 版本）
3. 将 `test_output.aaf` 导入 Pro Tools（使用原始 DLL）
4. 验证：采样率显示 48000 Hz、音频播放速度正常

---

## 三、验证管线设计（核心）

这是整份方案最关键的部分。每次代码修改后，必须运行以下验证管线。

### 3.1 验证管线架构

```
test_export.py
     │
     ▼
test_output.aaf
     │
     ├──────────────────┬──────────────────┐
     ▼                  ▼                  ▼
  语义对比           结构对比           回归测试
(semantic_diff)   (structural_diff)  (pytest)
     │                  │                  │
     ▼                  ▼                  ▼
  差异报告           差异报告          通过/失败
     │                  │                  │
     └──────────────────┴──────────────────┘
                        │
                        ▼
                   综合判定
               (parity_gate.py)
                        │
                   PASS / FAIL
```

### 3.2 验证脚本: `parity_gate.py`

这是一个一键运行的验证入口，整合所有检查。设计要点：

```python
# parity_gate.py 的输出格式（设计规范，非实现代码）:
#
# ═══════════════════════════════════════════
# AAF Parity Gate Report
# ═══════════════════════════════════════════
#
# [L1 - Header]
#   ✅ Header.Version: {1,1} == {1,1}
#   ✅ OperationalPattern: None == None
#   ✅ Identification.CompanyName: match
#   ⚠️  Identification.Date: SKIPPED (timestamp)
#
# [L2 - Mob Structure]
#   ✅ Mob count: 4 == 4
#   ✅ Mob order: CompositionMob → MasterMob → SourceMob(Tape) → SourceMob(WAVE)
#   ✅ CompositionMob.Slots.count: 2 == 2
#   ❌ CompositionMob.Slot[2].EditRate: 48000 != 24  ← FAIL
#
# [L3 - Descriptor]
#   ✅ WAVEDescriptor.SampleRate: 48000/1 == 48000/1
#   ✅ EssenceSummary.WAVHeader.SampleRate: 48000 == 48000
#
# [Binary]
#   差异字节数: 47 / 221184 (不含白名单区域)
#   差异组数: 3
#
# ───────────────────────────────────────────
# RESULT: FAIL (1 semantic error, 3 binary diff groups)
# ───────────────────────────────────────────
```

**关键设计原则**:

1. **每项检查都有明确的 PASS/FAIL/SKIP 状态**
2. **白名单差异标记为 SKIP，不影响判定**
3. **语义检查失败一票否决** — 即使二进制差异很小，语义错误也是 FAIL
4. **二进制差异提供精确定位** — 显示偏移量、期望值、实际值
5. **输出可直接复制到 parity_tracker.md** — 方便更新清单

### 3.3 语义对比检查项

`parity_gate.py` 需要检查以下属性（这是完整清单，基于 TECHNICAL_HANDOVER.md 中已知问题和 DaVinci Resolve 参考文件的分析）：

#### L1 - Header
| 检查项 | 比较方式 | 白名单？ |
|--------|---------|---------|
| Header.Version | 精确匹配 | 否 |
| Header.OperationalPattern | 精确匹配 | 否 |
| Header.ObjectModelVersion | 记录但不判定 | 是 |
| Identification 数量 | 精确匹配 | 否 |
| Identification.CompanyName | 精确匹配 | 否 |
| Identification.ProductName | 精确匹配 | 否 |
| Identification.ProductVersionString | 精确匹配 | 否 |
| Identification.Platform | 精确匹配 | 否 |
| Identification.Date | 跳过 | 是 |
| Identification.GenerationAUID | 跳过 | 是 |
| Dictionary 中的 ClassDefinition 数量 | 记录差异 | 是 |

#### L2 - Mob 结构
| 检查项 | 比较方式 | 白名单？ |
|--------|---------|---------|
| Mob 总数 | 精确匹配 | 否 |
| Mob 类型序列 | 精确匹配顺序 | 否 |
| 各 Mob 的 name | 精确匹配 | 否 |
| 各 Mob 的 SlotCount | 精确匹配 | 否 |
| MobID 前缀格式 | 前缀匹配 `060a2b34.01010101.01010f00.13000000` | 否 |
| MobID 的 UUID 部分 | 跳过 | 是 |
| 每个 Slot 的 SlotID | 精确匹配 | 否 |
| 每个 Slot 的 EditRate | 精确匹配 | 否 |
| 每个 Slot 的 PhysicalTrackNumber | 精确匹配 | 否 |
| Slot.Segment 类型 | 精确匹配 | 否 |
| Segment.Length | 精确匹配 | 否 |
| Timecode.Start | 精确匹配 | 否 |
| Timecode.FPS | 精确匹配 | 否 |
| Timecode.Drop | 精确匹配 | 否 |
| Sequence 中 Component 数量 | 精确匹配 | 否 |
| SourceClip.SourceID | 前缀匹配 | 否 |
| SourceClip.SourceMobSlotID | 精确匹配 | 否 |
| SourceClip.StartTime | 精确匹配 | 否 |
| SourceClip.Length | 精确匹配 | 否 |
| Filler.Length | 精确匹配 | 否 |

#### L3 - Descriptor
| 检查项 | 比较方式 | 白名单？ |
|--------|---------|---------|
| Descriptor 类型 | 精确匹配 | 否 |
| WAVEDescriptor.SampleRate | 精确匹配 Rational | 否 |
| WAVEDescriptor.AudioSamplingRate | 精确匹配 Rational | 否 |
| WAVEDescriptor.Channels | 精确匹配 | 否 |
| WAVEDescriptor.QuantizationBits | 精确匹配 | 否 |
| WAVEDescriptor.Length | 精确匹配 | 否 |
| WAVEDescriptor.ContainerFormat | 精确匹配 | 否 |
| EssenceSummary (WAV Header) 字节 | 逐字节匹配 | 否 |
| Locator 数量 | 精确匹配 | 否 |
| NetworkLocator.URLString 文件名 | 文件名匹配 | 否 |
| TapeDescriptor 存在性 | 精确匹配 | 否 |

### 3.4 二进制对比增强

当前的 `compare_binary.py` 需要增强：

1. **白名单过滤** — 自动忽略已知的不可控区域（MobID UUID 部分、时间戳等）
2. **Structured Storage 感知** — 标注每个差异所在的 CFB stream/sector
3. **差异分类** — 区分「结构性差异」和「内容性差异」
4. **差异趋势** — 记录每次运行的差异数，绘制收敛趋势

### 3.5 回归保护

每次修复后必须确保：

```bash
# 现有测试套件不能被破坏
pytest tests/test_aaf_adapter.py -x -q

# 如果有修改 pyaaf2，还要跑 pyaaf2 的测试
pytest pyaaf2/tests/ -x -q
```

---

## 四、反馈环路设计

### 4.1 快速反馈环（< 30 秒）

每次代码修改后立即运行：

```bash
python test_export.py && python parity_gate.py
```

- `parity_gate.py` 输出一行摘要: `PASS (0 errors, 3 whitelist skips)` 或 `FAIL (2 errors)`
- 不需要手动打开 Pro Tools
- 不需要跑完整测试套件

### 4.2 中速反馈环（< 5 分钟）

每完成一组相关修复后运行：

```bash
python test_export.py && python parity_gate.py --verbose && pytest tests/test_aaf_adapter.py -x -q
```

- 完整的语义对比报告
- 二进制差异详情
- 回归测试

### 4.3 慢速反馈环（手动）

阶段性里程碑时执行：

1. 将 `test_output.aaf` 复制到 Pro Tools 机器
2. 导入 Pro Tools，检查采样率和播放
3. 如果失败，使用 IDA Pro + 动态调试分析 Pro Tools 的解析过程
4. 将发现反馈到 `parity_tracker.md`

### 4.4 差异收敛追踪

在 `parity_tracker.md` 中维护一个收敛日志：

```
## 收敛日志

| 日期 | 语义差异数 | 二进制差异组数 | 二进制差异字节数 | 备注 |
|------|-----------|--------------|----------------|------|
| 2026-06-02 | 5 | 12 | 1847 | 初始基线 |
| 2026-06-02 | 4 | 10 | 1203 | 修复 Header.Version |
| ...  | ...       | ...          | ...            | ...  |
```

**关键指标**: 二进制差异字节数应单调递减。如果一次修复导致差异增加，立即回滚并分析原因。

---

## 五、pyaaf2 修改策略

pyaaf2 的修改是高风险操作，需要特别谨慎。

### 5.1 修改原则

- **能在 aaf_writer.py 层面解决的，不改 pyaaf2** — 减少对上游库的侵入
- **必须改 pyaaf2 时，做最小修改** — 每次只改一个行为
- **所有 pyaaf2 修改记录在案** — 在 `parity_tracker.md` 中单独记录

### 5.2 同步机制

当前 pyaaf2 的修改需要手动复制到 `.venv/`，这很容易遗漏。建议：

```bash
# 在 pyproject.toml 中使用 editable install
pip install -e ./pyaaf2
```

或者在验证管线中增加一步检查：

```python
# 检查 pyaaf2 源码和 site-packages 的一致性
# 如果不一致，报警并中止
```

---

## 六、已知风险和缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| pyaaf2 的 CFB 写入顺序与 DaVinci Resolve 不同 | L0 层二进制差异无法消除 | 确认 Pro Tools 是否对 CFB 布局敏感；如果不敏感，将 L0 差异加入白名单 |
| Dictionary 中的额外 ClassDefinition | 文件体积不同，可能触发 Pro Tools 验证 | 研究是否能控制 pyaaf2 的 Dictionary 输出 |
| 30 Hz 问题根因不在可见属性中 | 所有语义差异消除后 Pro Tools 仍报 30 Hz | 进入逆向分析阶段，使用 IDA Pro 追踪 |
| 某些属性在 pyaaf2 的 API 中无法设置 | 需要深度修改 pyaaf2 | 评估 fork pyaaf2 的可行性 |

---

## 七、工具清单

### 需要构建的新工具

| 工具 | 用途 | 优先级 |
|------|------|--------|
| `parity_gate.py` | 一键验证入口，整合所有检查 | P0 |
| `parity_tracker.md` | 差异清单和收敛日志 | P0 |

### 需要增强的现有工具

| 工具 | 增强内容 | 优先级 |
|------|---------|--------|
| `compare_binary.py` | 白名单过滤、差异分类 | P1 |
| `deep_compare_aaf.py` | 覆盖 L1/L2/L3 全部检查项 | P1 |
| `test_export.py` | 输出到固定路径，支持静默模式 | P2 |

### 现有可直接使用的工具

| 工具 | 用途 |
|------|------|
| `dump.bat` | AAF SDK 官方结构分析 |
| `check_*.py` | 各项专项检查 |
| `pytest` | 回归测试 |

---

## 八、第一步行动

1. 运行 `test_export.py` 生成当前 `test_output.aaf`
2. 对 `correct_timeline.aaf` 和 `test_output.aaf` 执行三层对比
3. 将所有差异整理到 `parity_tracker.md`
4. 实现 `parity_gate.py` 的第一版（语义检查为主）
5. 从 L1 层差异开始修复
