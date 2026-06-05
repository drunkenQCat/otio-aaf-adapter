# Fix AAF Export for Pro Tools Compatibility

## 问题背景 (Background)

当前版本的 AAF 导出文件**无法被 Avid Pro Tools 正确导入**。具体表现为：

- Pro Tools 将音频采样率误读为 30 Hz（应为 48000 Hz）
- 音频轨道无法正常识别和播放
- 时间线结构显示异常

然而，使用 DaVinci Resolve 导出的 AAF 文件可以被 Pro Tools 完美导入。

## 根本原因分析 (Root Cause Analysis)

通过对 DaVinci Resolve 导出的 AAF 文件进行深度对比分析，发现以下**3个关键结构性差异**：

### 1. OperationDef UUID 错误 ❌

| 项目 | DaVinci Resolve (正确) | 当前实现 (错误) |
|------|------------------------|-----------------|
| OperationDef UUID | `9d2ea894-0968-11d3-8a38-0050040ef7d2` | `e4962321-2267-11d3-8a4c-0050040ef7d2` |

**影响**：Pro Tools 无法识别 Audio Gain 效果，导致音频处理失败。

**修复**：使用 AAF 标准的 MonoAudioGain OperationDefinition UUID。

### 2. ParameterDef 名称和 UUID 错误 ❌

| 项目 | DaVinci Resolve (正确) | 当前实现 (错误) |
|------|------------------------|-----------------|
| ParameterDef name | `Amplitude` | `ParameterDef_Level` |
| ParameterDef UUID | `e4962321-2267-11d3-8a4c-0050040ef7d2` | `e4962320-2267-11d3-8a4c-0050040ef7d2` |

**影响**：Pro Tools 无法正确解析音频增益参数。

**修复**：使用 DaVinci Resolve 的命名规范和对应的 UUID。

### 3. SourceClip StartTime 负值 ❌

**DaVinci Resolve**：OperationGroup 内部的 SourceClip 的 `StartTime` 始终为 `0`

**当前实现**：`StartTime` 被设置为**时间线上的累积偏移量（负值）**，范围在 -28524000 到 -33544000 之间。

**影响**：负值 StartTime 在物理上不可能（源数据不存在于负偏移位置），导致 Pro Tools 丢弃这些音频片段。

**修复**：OperationGroup 内部 SourceClip 的 StartTime 应设为 0，因为 OperationGroup 本身已经处理了时间线定位。

## 修复方案 (Solution)

### Commit 1: feat(aaf): add audio auto-transcoding for Pro Tools compatibility

新增音频自动转码功能，确保所有音频文件符合 Pro Tools 要求（48kHz, 24-bit, mono WAV）：

- 新增 `audio_transcoder.py` 模块
- 集成转码到 AAF `write_to_file` 工作流
- 自动检测 WAV 文件格式
- 缓存转码文件避免重复处理
- 导出后恢复原始媒体引用

### Commit 2: fix(aaf): correct OperationDef UUID and SourceClip StartTime

修复 3 个关键的 Pro Tools 兼容性问题：

1. **OperationDef UUID**：`e4962321-...` → `9d2ea894-0968-11d3-8a38-0050040ef7d2`
2. **ParameterDef name**：`ParameterDef_Level` → `Amplitude`
3. **ParameterDef UUID**：`e4962320-...` → `e4962321-2267-11d3-8a4c-0050040ef7d2`
4. **SourceClip StartTime**：从时间线偏移改为 `0`
5. **其他改进**：
   - 使用 `ceil()` 计算 Filler 长度
   - 使用 `floor()` 计算 clip 长度
   - 添加 WAV Summary 默认回退机制
   - 改进文件路径处理

## 验证结果 (Verification)

修复后的 AAF 文件与 DaVinci Resolve 导出的文件进行了全面对比：

### ✅ 全部通过的检查项

| 检查项 | 结果 |
|--------|------|
| OperationDef UUID | ✅ PASS (`9d2ea894-...`) |
| ParameterDef name | ✅ PASS (`Amplitude`) |
| ParameterDef UUID | ✅ PASS (`e4962321-...`) |
| SourceClip StartTime | ✅ PASS (所有 OperationGroup 内部均为 0) |
| OperationGroup 数量 | ✅ 24/24 完全匹配 |
| OperationGroup 结构 | ✅ 逐项对比，0 差异 |
| OperationGroup 长度 | ✅ 全部一致 |
| 参数值 | ✅ 1.0 (536870912/536870912) |
| 音频 edit_rate | ✅ 48000 Hz |
| Mob 数量 | ✅ 73 (1 Composition + 24 Master + 48 Source) |
| AAF Version | ✅ 1.1 |

### 对比文件

- **DaVinci Resolve (黄金标准)**：`test_data/飞驰人生测试_20260515.20260602163810.aaf`
- **OTIO 导出 (修复前)**：`test_data/飞驰人生测试_testdata_new.aaf`
- **OTIO 导出 (修复后)**：`test_data/飞驰人生测试_fixed_output.aaf`

## 关于此 PR 的说明 (Notes)

### ⚠️ 为什么这个 PR 可能无法直接合并

1. **测试覆盖不足**：缺少针对 Pro Tools 兼容性问题的单元测试
2. **API 变更**：删除了 `embed_essence` 和 `create_edgecode` 参数（虽然这些参数在原代码中未被使用）
3. **依赖增加**：引入了 `pydub` 用于音频转码
4. **缺乏上游验证**：无法在实际的 Pro Tools 环境中验证修复效果

### 💡 建议的后续步骤

1. **添加单元测试**：为 UUID、参数名称、StartTime 等关键修复添加测试用例
2. **社区验证**：邀请有 Pro Tools 环境的贡献者验证修复效果
3. **API 兼容性**：考虑保留被删除的参数以保持向后兼容
4. **可选依赖**：将 `pydub` 设为可选依赖，仅在需要转码时安装

### 🔬 分析方法

本次修复使用了以下诊断工具（位于 `diagnostics/` 目录）：

- `three_file_compare.py`：三文件 UUID 对比
- `exhaustive_compare.py`：全量属性对比（888 个差异点）
- `investigate_start_times.py`：SourceClip StartTime 深度调查
- `verify_operationdef_uuid.py`：OperationDef UUID 验证

## 相关文件 (Files Changed)

- `src/otio_aaf_adapter/adapters/aaf_adapter/aaf_writer.py`：核心修复
- `src/otio_aaf_adapter/audio_transcoder.py`：新增音频转码模块
- `src/otio_aaf_adapter/adapters/advanced_authoring_format.py`：集成转码
- `pyproject.toml`：添加 pydub 依赖
- `uv.lock`：依赖锁文件

## 致谢 (Acknowledgments)

感谢 OpenTimelineIO 社区维护这个重要的项目。本次修复基于对 DaVinci Resolve 导出文件的深度逆向分析，希望能帮助改进 AAF 导出功能，使其能够被 Pro Tools 等行业标准工具正确识别。

---

**Co-Authored-By**: Qwen AI <noreply@qwen.ai>
