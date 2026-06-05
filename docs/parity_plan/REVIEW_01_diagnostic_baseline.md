# Review: 01_diagnostic_baseline.md & BINARY_PARITY_PLAN.md

> 审核日期: 2026-06-02
> 审核范围: `docs/parity_plan/01_diagnostic_baseline.md` + `BINARY_PARITY_PLAN.md`

---

## 一、两份文档的关系问题

`BINARY_PARITY_PLAN.md` 是总纲，`01_diagnostic_baseline.md` 是 Phase 1 的执行细则。但两者存在大量重复且不一致：

| 方面 | 总纲 Phase 1 | 01_diagnostic_baseline.md | 问题 |
|------|-------------|--------------------------|------|
| 步骤 | 3 步（导出→对比→生成清单） | 6 步（含 Dictionary、深度枚举） | 总纲过于粗略 |
| 差异表格式 | 6 列（无"可控"列） | 7 列（有"可控"列） | 格式不统一 |
| 优先级 | 有（L1→L2→L3） | 无 | Phase 1 执行手册缺失 |
| 白名单 | 有明确 4 类列表 | 只在"可控"列暗示 | 执行者无所适从 |

**建议**: 总纲的 Phase 1 部分应直接引用 `01_diagnostic_baseline.md`，不要自己再写一遍简化版。否则两边维护会漂移。

---

## 二、01_diagnostic_baseline.md 结构性问题

### 2.1 Step 4 内联 100+ 行脚本不合理

Step 2/3 已有独立脚本（`deep_compare_aaf.py`、`compare_binary.py`），Step 4 的大块代码也应提取为独立脚本（如 `enumerate_properties.py`）。否则执行者要么手动粘贴，要么临时创建文件——这与"不要修改任何源码"的精神矛盾。

**修改**: 将 Step 4 的 Python 代码提取为 `enumerate_properties.py`，Step 4 改为 `python enumerate_properties.py`。

### 2.2 Step 6 Dictionary 对比代码是半成品

TypeDefinitions 部分只写了 `(similar enumeration for type defs)` 注释就收尾了。

**修改**: 要么补全 TypeDefinitions 的枚举代码，要么明确标注"本阶段仅对比 ClassDefs，TypeDefs 留到 Phase 2"。

### 2.3 L0/L1/L2/L3 层级在验收标准中突然出现，但全文从未定义

差异清单的表头只写了"层级"，没有解释 L0-L3 分别代表什么。执行者只能猜测。

**修改**: 在"背景"章节后、"前置条件"前，增加一段层级定义：

```markdown
### 层级定义

| 层级 | 内容 | 说明 |
|------|------|------|
| L0 | CFB 容器层 | Sector 大小、FAT 表、Directory Entry 排列 |
| L1 | Header 对象层 | Version、OperationalPattern、Identification、Dictionary |
| L2 | Mob 图结构层 | Mob 类型/数量/顺序、Slot 结构、Segment 树 |
| L3 | Essence/Descriptor 层 | WAVEDescriptor 属性、EssenceSummary、Locator |
```

### 2.4 "不要修改任何源码"与路径硬编码自相矛盾

文档一边说 `deep_compare_aaf.py` "硬编码了路径，可能需要调整"，一边又说"不要修改任何源码"。

**修改**: 将"不要修改任何源码"改为更精确的表述：

> 不要修改项目核心源码（`src/` 目录下的文件）。对比脚本（`deep_compare_aaf.py`、`compare_binary.py` 等）中的路径常量可以按需调整。

### 2.5 `correct_timeline.aaf` 存在性检查放得太晚

文件不存在则整个 Phase 1 产出为零，但这个检查被埋在 Step 1 的注意事项里。

**修改**: 增加 Step 0 前置校验：

```markdown
### Step 0: 前置校验

确认以下文件存在：
- `correct_timeline.aaf`（项目根目录，或备用路径）
- `SimpleTimeline.otio`
- `test_export.py`
- 所有对比脚本

如果 `correct_timeline.aaf` 不存在，**立即报告并中止**。
```

### 2.6 缺少对"已知不可控差异"的预判

UUID、MobID、时间戳等每次运行必然不同的字段，文档只在交付物模板的"可控"列提了一句。

**修改**: 在"前置条件"后增加白名单章节（从总纲 1.2 搬过来）：

```markdown
### 不可控变量白名单

以下差异预期存在，不视为失败：
- MobID 中的 UUID 部分
- Identification 中的 Date 时间戳
- CFB 容器层的 sector 分配顺序
- Dictionary 中未引用的 ClassDefinition 差异
```

### 2.7 Step 5 "记录所有输出"太模糊

8 个 `check_*.py` 脚本，有的可能输出几十行。

**修改**: 明确说明是全文粘贴到 `parity_tracker.md` 附录，还是只提取关键结论到主表。建议：

> 将每个脚本的完整输出记录到 `parity_tracker.md` 的附录 A 中。在主表差异清单中只引用附录条目编号。

---

## 三、01_diagnostic_baseline.md 小问题

| 位置 | 问题 | 建议修改 |
|------|------|---------|
| 前置条件 > 环境 | "因为部分工具依赖 Windows 路径" | 改为"因为参考文件路径和测试环境为 Windows" |
| 收敛日志 | `{today}` 占位 | 改为 ISO 格式示例 `2026-06-02` |
| 差异清单模板 | 状态列含 `FIXED` | Phase 1 是纯诊断，不应出现 FIXED。标注为"后续阶段使用" |
| 交付物 > 二进制差异摘要 | "从 compare_binary.py 输出中复制前 20 组" | 应说明如果不足 20 组则全部复制 |

---

## 四、BINARY_PARITY_PLAN.md 问题

### 4.1 验证管线设计（第三章）过早展开

`parity_gate.py` 在 Phase 2 才需要，但第三章花了大量篇幅设计其输出格式和检查项清单。Phase 1 执行者会产生"我是不是该先写 parity_gate.py"的困惑。

**修改**: 在第三章开头加一句：

> 注: `parity_gate.py` 在 Phase 2 开始实施。Phase 1 仅使用 `deep_compare_aaf.py` + `compare_binary.py` + 人工整理。

### 4.2 dump 层对比在后续架构中消失

三层对比（语义/二进制/dump）中的 dump 层在验证管线架构图（3.1）中完全消失，只剩 semantic_diff 和 structural_diff。

**修改**: 在 Phase 1 步骤中标注 dump 层为"可选补充手段"，或说明其在后续阶段被合并到语义对比中。

### 4.3 反馈环路（第四章）与阶段划分脱节

快速环依赖 `parity_gate.py`（还没写），Phase 1 执行者不知道该用什么反馈环。

**修改**: 明确 Phase 1 没有自动化反馈环，全靠人工对比。在第四章增加：

> Phase 1 反馈方式: 手动运行对比脚本并检查 `parity_tracker.md` 的完整性。

### 4.4 pyaaf2 修改策略中的 editable install 建议重复

第五章建议 `pip install -e ./pyaaf2`，但前置条件已经说过这样做了。

**修改**: 改为"确认 editable install 已生效"。

### 4.5 L0-L3 分层模型未显式定义

L0-L3 是整个方案的核心支柱，但总纲只在 §1.1 的表格中一笔带过。`01_diagnostic_baseline.md` 的验收标准引用了它，却没有定义。

**修改**: 总纲 §1.1 的表格应扩展为完整的层级定义段落，并在 Phase 1 执行手册中交叉引用。

---

## 五、建议的文档结构重组

```
BINARY_PARITY_PLAN.md（总纲，~200行）
  ├── 背景和目标
  ├── L0-L3 分层模型（完整定义）+ 白名单
  ├── Phase 概述（每个 Phase 一段话 + 门禁条件，Phase 1 引用执行手册）
  ├── 验证管线设计（parity_gate.py，标注为 Phase 2 实施工具）
  ├── 反馈环路（按 Phase 区分）
  ├── 风险矩阵
  └── 工具清单

docs/parity_plan/01_diagnostic_baseline.md（Phase 1 执行手册，~300行）
  ├── 前置条件（含 Step 0 文件存在性校验）
  ├── 层级定义（或交叉引用总纲）
  ├── 白名单（从总纲搬入或引用）
  ├── 详细步骤（Step 0-6，所有代码提取为独立脚本）
  ├── parity_tracker.md 模板（格式与总纲统一）
  └── 验收标准
```

**核心原则**: 总纲不写执行细节，执行手册不重复战略设计。两者通过交叉引用连接。

---

## 六、修改优先级建议

| 优先级 | 修改项 | 原因 |
|--------|--------|------|
| P0 | 统一差异表格式（6列 vs 7列） | 格式不统一会导致执行歧义 |
| P0 | 在 Phase 1 执行手册中增加 L0-L3 层级定义 | 验收标准依赖此定义 |
| P0 | 增加 Step 0 前置校验 | 文件不存在则全部白费 |
| P1 | 提取 Step 4 内联脚本为独立文件 | 可执行性 |
| P1 | 解决"不要修改源码"与路径调整的矛盾 | 执行者会卡在这里 |
| P1 | 总纲 Phase 1 改为引用执行手册 | 消除重复和不一致 |
| P2 | 补全 Step 6 Dictionary 对比代码 | 半成品影响可执行性 |
| P2 | 明确 dump 层定位和反馈环路的阶段归属 | 减少困惑 |
| P3 | 小问题修正（措辞、占位符、FIXED 状态） | 锦上添花 |
