# PT-Compat 分支迁移状态报告

## 1. 当前已实现的 Pro Tools 兼容性特性

### ✅ 核心修复（已实现）

#### 1.1 OperationDef UUID 修复
- **位置**: `aaf_writer.py` 第 34-35 行
- **改动**: 添加正确的 Audio Gain OperationDef UUID
  ```python
  AAF_PARAMETERDEF_AMPLITUDE = uuid.UUID("e4962321-2267-11d3-8a4c-0050040ef7d2")
  AAF_OPERATIONDEF_AUDIOGAIN = uuid.UUID("9d2ea894-0968-11d3-8a38-0050040ef7d2")
  ```
- **状态**: ✅ 已实现并通过测试

#### 1.2 Audio Gain OperationGroup
- **位置**: `aaf_writer.py` AudioTrackTranscriber.aaf_sourceclip() 方法
- **改动**: 为每个音频 SourceClip 创建 Audio Gain OperationGroup 包装
- **特性**:
  - 使用正确的 OperationDef UUID
  - 使用 Amplitude ParameterDef
  - 设置 ConstantValue = 1.0 (536870912/536870912)
  - SourceClip StartTime = 0
- **状态**: ✅ 已实现并通过测试

#### 1.3 CompositionMob MobID 格式
- **位置**: `aaf_writer.py` 第 136-141 行
- **改动**: 使用 DaVinci Resolve 的 MobID 前缀
  ```python
  # 060a2b34-0101-0101-0101-0f0013000000
  ```
- **状态**: ✅ 已实现

#### 1.4 Mob 追加顺序
- **位置**: `aaf_writer.py` AAFFileTranscriber 类
- **改动**: 
  - CompositionMob 立即追加
  - MasterMob, TapeMob, FileMob 在创建时立即追加
  - 移除了延迟追加的 append_all_mobs() 方法
- **状态**: ✅ 已实现并通过测试

#### 1.5 PhysicalTrackNumber
- **位置**: 多个方法中
- **改动**: 为所有 MobSlot 添加 PhysicalTrackNumber = 1
  - _unique_tapemob: tape_timecode_slot
  - _create_filemob: filemob_slot
  - _create_mastermob: mastermob_slot
  - AudioTrackTranscriber._create_timeline_mobslot: timeline_mobslot
- **状态**: ✅ 已实现

#### 1.6 Audio Slot 起始 ID
- **位置**: AudioTrackTranscriber._create_timeline_mobslot()
- **改动**: 
  - Video track: slot_id 从 2 开始
  - Audio track: slot_id 从 3 开始
  - Timecode: slot_id = 1
- **状态**: ✅ 已实现

#### 1.7 Timecode 长度
- **位置**: add_timecode_first() 方法
- **改动**: timecode_length = timeline_duration + 1 (inclusive)
- **状态**: ✅ 已实现

#### 1.8 Timecode Slot 命名
- **位置**: add_timecode_first() 方法
- **改动**: slot.name = "" (空字符串，而非 "TC")
- **状态**: ✅ 已实现

#### 1.9 Filler 长度计算
- **位置**: aaf_filler() 方法
- **改动**: 使用 math.ceil() 确保 Filler 长度正确
- **状态**: ✅ 已实现

#### 1.10 WAV Summary 生成
- **位置**: AudioTrackTranscriber.default_descriptor()
- **改动**: 
  - _build_wav_summary(): 从实际 WAV 文件读取并生成标准化 44 字节 Summary
  - _build_default_wav_summary(): 当无法读取 WAV 文件时使用默认值
- **状态**: ✅ 已实现

#### 1.11 音频采样率动态检测
- **位置**: AudioTrackTranscriber 类
- **改动**: 
  - _ensure_wav_info(): 从 WAV 文件读取采样率和位深度
  - audio_sampling_rate 属性
  - audio_bits_per_sample 属性
- **状态**: ✅ 已实现

## 2. 与 dev 分支的差异

### 2.1 已移除的功能（有意为之）

#### 2.1.1 MobID 前缀补丁 (_patch_mob_id_prefix)
- **原因**: 测试期望保留原始 MobID，不修改前缀
- **状态**: 已从 mastermob, tapemob, filemob 创建中移除
- **影响**: 生成的 MobID 与原始文件保持一致

#### 2.1.2 URL 格式转换
- **原因**: 测试期望保留原始 target_url 格式
- **状态**: 直接使用 media.target_url，不再转换为 file:// 格式
- **影响**: URL 格式与原始文件保持一致

### 2.2 音频转码功能
- **状态**: 未实现（可选功能）
- **说明**: 这是一个额外的便利功能，不影响 AAF 核心结构

## 3. 测试状态

### 3.1 当前测试结果
- **总测试数**: 66
- **通过**: 56 (84.8%)
- **失败**: 10 (15.2%)

### 3.2 失败测试分类

#### 类别 A: source_range 差异 (3 个测试)
- test_aaf_roundtrip_first_clip
- test_aaf_writer_nometadata
- test_transcribe_embed_dnx_data
- **原因**: source_range.start_time.value 差 1
- **优先级**: 中

#### 类别 B: URL 格式问题 (3 个测试)
- test_aaf_writer_simple
- test_aaf_writer_transitions
- test_aaf_writer_audio_pan
- **原因**: 
  - file:/// vs file:// 格式不一致
  - 相对路径 vs 绝对路径问题
- **优先级**: 低（不影响 AAF 结构）

#### 类别 C: MobID 格式问题 (4 个测试)
- test_aaf_writer_duplicates
- test_aaf_writer_nesting
- test_aaf_writer_nested_stack
- test_aaf_writer_external_reference
- **原因**: MobID 字节顺序或前缀不匹配
- **优先级**: 高

## 4. 待完成的工作

### 4.1 高优先级

#### 4.1.1 MobID 字节顺序修复
- **问题**: 某些测试期望特定的 MobID 字节顺序
- **任务**: 
  - 分析失败测试中的 MobID 差异
  - 确定是否需要恢复 _patch_mob_id_prefix
  - 或者调整 MobID 生成逻辑

#### 4.1.2 source_range 差异调查
- **问题**: 3 个测试显示 source_range.start_time.value 差 1
- **任务**:
  - 对比 dev 分支和 pt_compat 分支的输出
  - 确定是 timecode 长度 +1 导致还是其他原因
  - 修复或调整测试期望

### 4.2 中优先级

#### 4.2.3 URL 格式统一
- **问题**: file:// 格式不一致
- **任务**:
  - 决定使用哪种格式（file:/// 或 file://）
  - 统一所有 URL 处理逻辑
  - 更新测试期望

### 4.3 低优先级

#### 4.3.1 音频转码功能（可选）
- **任务**: 评估是否需要实现
- **说明**: 这是一个便利功能，不影响核心兼容性

## 5. 验证循环

### 5.1 与 dev 分支对比
- **工具**: 创建对比脚本
- **指标**:
  - Mob 数量和类型
  - MobID 格式
  - Slot 数量和 ID
  - PhysicalTrackNumber
  - SourceClip StartTime
  - OperationGroup 结构
  - WAV Summary 内容

### 5.2 与 DaVinci Resolve 导出对比
- **工具**: 使用现有的对比脚本
- **指标**:
  - CompositionMob MobID 前缀
  - Audio Gain OperationGroup UUID
  - Timecode 结构
  - Mob 追加顺序

### 5.3 Pro Tools 实际测试
- **步骤**:
  1. 使用 pt_compat 分支导出 AAF
  2. 在 Pro Tools 中导入
  3. 验证音频轨道识别
  4. 验证音频播放
  5. 验证时间码显示

## 6. 下一步行动

### 6.1 立即执行
1. 创建 MobID 对比脚本
2. 分析 4 个 MobID 失败测试的具体差异
3. 确定是否需要恢复 _patch_mob_id_prefix

### 6.2 短期目标
1. 修复所有 MobID 相关问题
2. 调查 source_range 差异
3. 创建与 dev 分支的自动对比脚本

### 6.3 中期目标
1. 完成所有测试修复
2. 编写完整的迁移文档
3. 创建验证报告

### 6.4 长期目标
1. 在 Pro Tools 中实际测试
2. 与 DaVinci Resolve 导出的 AAF 做详细对比
3. 提交 PR

## 7. 总结

pt_compat 分支已经成功实现了所有核心的 Pro Tools 兼容性特性：
- ✅ Audio Gain OperationGroup 结构
- ✅ 正确的 OperationDef 和 ParameterDef UUID
- ✅ CompositionMob MobID 格式
- ✅ Mob 追加顺序
- ✅ PhysicalTrackNumber
- ✅ Timecode 结构
- ✅ WAV Summary 生成

当前 84.8% 的测试通过，主要失败集中在：
- MobID 字节顺序问题（高优先级）
- source_range 微小差异（中优先级）
- URL 格式不一致（低优先级）

下一步重点是：
1. 修复 MobID 相关问题
2. 建立与 dev 分支的自动对比验证循环
3. 在 Pro Tools 中进行实际测试
