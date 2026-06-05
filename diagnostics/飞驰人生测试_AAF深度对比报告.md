# AAF 深度对比报告

## 比较文件

| 项目 | 文件 |
|------|------|
| 文件1 (DaVinci 参考) | `飞驰人生测试_testdata_new.aaf` |
| 文件2 (OTIO 导出) | `飞驰人生测试_20260515.20260602163810.aaf` |

---

## 一、整体结构对比

| 指标 | DaVinci | OTIO | 状态 |
|------|---------|------|------|
| AAF Version | 1.1 | 1.1 | ✓ 一致 |
| ObjectModelVersion | 1 | 1 | ✓ 一致 |
| Mob 总数 | 73 | 73 | ✓ 一致 |
| CompositionMob | 1 | 1 | ✓ 一致 |
| MasterMob | 24 | 24 | ✓ 一致 |
| SourceMob | 48 | 48 | ✓ 一致 |
| OperationGroup 总数 | 24 | 24 | ✓ 一致 |
| Identification | Blackmagic Design/DaVinci Resolve | 同 | ✓ 一致 |

---

## 二、关键差异发现

### 2.1 OperationDef UUID 差异 (严重性: HIGH) ⚠️ **根本原因已找到**

**问题**: Audio Gain 操作定义使用了不同的 UUID

| 项目 | DaVinci | OTIO | pyaaf2 内置定义 |
|------|---------|------|-----------------|
| Audio Gain OperationDef UUID | `e4962321-2267-11d3-8a4c-0050040ef7d2` | `9d2ea894-0968-11d3-8a38-0050040ef7d2` | `9d2ea894-...` (OperationDef_MonoAudioGain) |
| OperationDef 名称 | Audio Gain | Audio Gain | OperationDef_MonoAudioGain |
| ParameterDef 名称 | `ParameterDef_Level` | `Amplitude` | - |
| ParameterDef UUID | `e4962320-2267-11d3-8a4c-0050040ef7d2` | `e4962321-...` (混淆) | `e4962320-...` (ParameterDef_Level) |

**根本原因**: pyaaf2 在 `datadefs.py` 第 18 行内置了不同的 UUID:
```python
# pyaaf2 内置定义
"9d2ea894-0968-11d3-8a38-0050040ef7d2" : ("OperationDef_MonoAudioGain", "")

# DaVinci Resolve 使用的 UUID (在 pyaaf2 中不存在！)
"e4962321-2267-11d3-8a4c-0050040ef7d2"
```

**问题分析**:
1. DaVinci Resolve 使用 AAF SDK 扩展定义的 UUID (`e4962321-...`)
2. pyaaf2 内置了标准 AAF 规范中的 `OperationDef_MonoAudioGain` UUID (`9d2ea894-...`)
3. 当 aaf_writer.py 调用 `create.OperationDef(AAF_OPERATIONDEF_AUDIOGAIN, "Audio Gain")` 时，pyaaf2 可能：
   - 忽略传入的 UUID，使用其内置定义
   - 或者在 `lookup_operationdef()` 时返回内置定义而非新创建的

**Pro Tools 兼容性风险**: **极高**
- Pro Tools 可能只识别 Avid/DaVinci 所用的 UUID 版本 (`e4962321-...`)
- 使用错误的 UUID 可能导致 Pro Tools 无法识别 Audio Gain 效果

**修复方案**:

| 方案 | 描述 | 复杂度 |
|------|------|--------|
| A: 修改 pyaaf2 datadefs.py | 在 datadefs.py 中添加 DaVinci 的 UUID 定义 | 低 |
| B: 修改 aaf_writer.py | 确保创建时使用正确 UUID，不被内置定义覆盖 | 中 |
| C: Fork pyaaf2 | 完全控制 OperationDef UUID | 高 |

---

### 2.2 OperationGroup 参数命名差异 (严重性: MEDIUM)

**问题**: Audio Gain 参数使用了不同的命名和 UUID

| 项目 | DaVinci | OTIO |
|------|---------|------|
| 参数名称 | `ParameterDef_Level` | `Amplitude` |
| 参数 UUID | `e4962320-2267-11d3-8a4c-0050040ef7d2` | `e4962321-...` (OperationDef UUID 混淆!) |

**影响分析**:
- DaVinci 使用 AAF SDK 标准的 `ParameterDef_Level` 参数
- OTIO 使用了错误的 UUID，混淆了 OperationDef 和 ParameterDef 的 UUID
- 这可能导致 Pro Tools 无法正确解析增益值

---

### 2.3 MasterMob 命名规则差异 (严重性: LOW)

| DaVinci 格式 | OTIO 格式 |
|--------------|-----------|
| `A1-0001_01_叶经理_rate1.0_260515_10PM_69e9_MiniMax_SJH` | `A1-0001_01_叶经理_rate1` |

**影响**: 素材名称截断，可能影响 Pro Tools 中的显示，但不影响功能

---

### 2.4 SourceMob 长度差异 (严重性: MEDIUM)

| Slot | DaVinci Length | OTIO Length | 比例 |
|------|----------------|-------------|------|
| Slot 1 | 189 | 158 | 1.2:1 |
| Slot 2 | 379007 | 316000 | 1.2:1 |

**影响分析**: 可能与帧率/采样率转换计算方式不同有关

---

## 三、UUID 详细验证结果

**验证脚本输出** (来自 `diagnostics/verify_operationdef_uuid.py`):

### DaVinci Resolve 导出 (`飞驰人生测试_testdata_new.aaf`)
```
Slot 3, Component 1: OperationGroup
  Operation Name: Audio Gain
  Operation UUID: e4962321-2267-11d3-8a4c-0050040ef7d2  ✓ (正确)
  Parameter: ParameterDef_Level
    ParamDef UUID: e4962320-2267-11d3-8a4c-0050040ef7d2  ✓ (正确)
```

### OTIO 导出 (`飞驰人生测试_20260515.20260602163810.aaf`)
```
Slot 3, Component 1: OperationGroup
  Operation Name: Audio Gain
  Operation UUID: 9d2ea894-0968-11d3-8a38-0050040ef7d2  ❌ (pyaaf2 内置 UUID)
  Parameter: Amplitude
    ParamDef UUID: e4962321-2267-11d3-8a4c-0050040ef7d2  ❌ (等于 OperationDef UUID，混淆!)
```

---

## 四、Pro Tools 兼容性评估

### 已解决 ✓
- [x] AAF Version (1.1)
- [x] OperationGroup 数量和位置
- [x] Mob 结构完整性

### 待解决 ❌
- [ ] **OperationDef UUID** (P0): 必须使用 `e4962321-2267-11d3-8a4c-0050040ef7d2`
- [ ] **ParameterDef UUID** (P1): 必须使用 `e4962320-2267-11d3-8a4c-0050040ef7d2`
- [ ] **ParameterDef 名称** (P1): 必须使用 `ParameterDef_Level`
- [ ] **MasterMob 命名** (P2): 保持完整素材名称
- [ ] **SourceMob 长度** (P3): 统一计算方式

---

## 五、修复优先级建议

| 优先级 | 问题 | 修复方案 | 预期效果 |
|--------|------|----------|----------|
| P0 | OperationDef UUID | 在 pyaaf2 datadefs.py 中添加 DaVinci UUID 定义 | Pro Tools 识别 Audio Gain |
| P1 | ParameterDef UUID | 确保 aaf_writer.py 正确创建 ParameterDef | Pro Tools 正确读取增益值 |
| P1 | ParameterDef 名称 | 使用 `ParameterDef_Level` | Pro Tools 正确解析参数 |
| P2 | MasterMob 命名 | 保持原始素材名称完整 | 素材显示一致性 |
| P3 | SourceMob 长度 | 统一长度计算逻辑 | 时间轴一致性 |

---

## 六、下一步行动

### 立即修复 (P0)
1. 在 pyaaf2 的 `model/datadefs.py` 中添加:
   ```python
   "e4962321-2267-11d3-8a4c-0050040ef7d2" : ("Audio Gain", "")
   ```
2. 验证 aaf_writer.py 创建 OperationDef 时是否正确使用 UUID

### 后续验证
1. 重新导出 AAF 文件
2. 使用 `verify_operationdef_uuid.py` 验证 UUID
3. 在 Pro Tools 中实际导入测试

---

## 附录：详细数据位置

| 文件 | 路径 |
|------|------|
| 深度比较 JSON | `diagnostics/deep_comparison_results.json` |
| UUID 验证脚本 | `diagnostics/verify_operationdef_uuid.py` |
| pyaaf2 datadefs.py | `.venv/Lib/site-packages/aaf2/model/datadefs.py` |
| aaf_writer.py | `src/otio_aaf_adapter/adapters/aaf_adapter/aaf_writer.py` |