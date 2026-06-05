# Dev 分支改动总结 - Pro Tools 兼容性修复

## 概述

Dev 分支包含 5 个提交，主要目标是对齐 DaVinci Resolve 的 AAF 导出格式，使其能被 Pro Tools 正确导入。

## 提交历史

1. `5ca21d5` - refactor: Improve AAF writer structure and metadata
2. `c452326` - fix: Align AAF export structure with DaVinci Resolve
3. `3322290` - feat: add audio auto-transcoding for Pro Tools compatibility
4. `0dbcde1` - fix: correct OperationDef UUID and SourceClip StartTime
5. `1546e42` - chore: update .gitignore for AAF Parity work

---

## 关键改动详解

### 1. Mob 结构与排序 (5ca21d5)

#### 改动点
- **CompositionMob MobID 格式**: 使用 DaVinci Resolve 的 MobID 前缀
  ```python
  # DaVinci Resolve 格式
  new_mob_id = aaf2.mobid.MobID(
      f"060a2b34-0101-0101-0101-0f0013000000-{unique_part}"
  )
  ```

- **Mob 追加顺序控制**: 引入 `_mobs_to_append` 列表，延迟追加 mobs
  ```python
  def append_all_mobs(self):
      # 按插入顺序追加: CompositionMob -> [MasterMob, TapeMob, FileMob] × N
      self.aaf_file.content.mobs.append(self.compositionmob)
      for mob_type, mob in self._mobs_to_append:
          self.aaf_file.content.mobs.append(mob)
  ```

- **Timecode slot 命名**: 从 "TC" 改为空字符串
  ```python
  slot.name = ""  # 匹配 DaVinci Resolve
  ```

#### 为什么重要
- DaVinci Resolve 有特定的 Mob 排序规则，影响 Pro Tools 的解析
- MobID 前缀需要匹配专业工具链的规范

---

### 2. MobID 前缀与 Slot 属性 (c452326)

#### 改动点
- **MobID 前缀补丁**: 修改 bytes 8-11 从 pyaaf2 默认到 DaVinci Resolve
  ```python
  def _patch_mob_id_prefix(mob):
      """Rewrite MobID bytes 8-11 from pyaaf2 default (01010f20) to DaVinci Resolve (01010d43)."""
      mid = mob.mob_id
      mid.bytes_le[8] = 0x01
      mid.bytes_le[9] = 0x01
      mid.bytes_le[10] = 0x0d
      mid.bytes_le[11] = 0x43
      mob.mob_id = mid
  ```

- **PhysicalTrackNumber**: 为所有 MobSlot 添加此属性
  ```python
  tapemob_slot["PhysicalTrackNumber"].value = 1
  filemob_slot["PhysicalTrackNumber"].value = 1
  mastermob_slot["PhysicalTrackNumber"].value = 1
  ```

- **Audio slot 起始 ID**: 从 SlotID=2 改为 SlotID=3
  ```python
  # SlotID 1 = timecode, SlotID 2 = reserved for video
  # Audio tracks start from SlotID 3 (matching DaVinci Resolve layout)
  slot_id = 3
  ```

- **Timecode length**: +1 以匹配 DaVinci Resolve 的 inclusive 行为
  ```python
  timecode_length = int(timeline_duration.value) + 1
  ```

- **WAV Summary 改进**: 从实际 WAV 文件读取，而非硬编码
  ```python
  def _build_wav_summary(self, media, length_samples):
      """Read actual WAV file and build a standardized 44-byte Summary header."""
      # 读取 WAV header，提取真实的采样率和位深度
  ```

#### 为什么重要
- MobID 前缀是 Avid 工具链的标识符
- PhysicalTrackNumber 是 AAF 规范要求的属性
- SlotID 布局影响 Pro Tools 对轨道的识别
- 真实的 WAV Summary 确保音频元数据准确

---

### 3. 音频自动转码 (3322290)

#### 新增文件
- `src/otio_aaf_adapter/audio_transcoder.py` - 音频转码模块

#### 改动点
- **集成转码到写入流程**: 在 `advanced_authoring_format.py` 的 `write_to_file()` 中
  ```python
  # 导出前：转码非标准音频
  transcoder = AudioTranscoder(timeline)
  transcoder.transcode_all_clips()
  
  # 写入 AAF
  otio.adapters.write_to_file(timeline, filepath)
  
  # 导出后：恢复原始媒体引用
  transcoder.restore_original_references()
  ```

- **缓存机制**: 避免重复转码相同文件
  ```python
  # 使用 MD5 hash 作为缓存键
  cache_key = hashlib.md5(wav_path.encode()).hexdigest()
  ```

- **依赖添加**: `pydub` 用于音频处理
  ```toml
  [project.optional-dependencies]
  audio = ["pydub>=0.25.1"]
  ```

#### 为什么重要
- Pro Tools 要求 48kHz/24bit/mono WAV
- DaVinci Resolve 导出的音频可能不符合此规范
- 自动转码确保导出文件可直接被 Pro Tools 导入

---

### 4. OperationDef UUID 与 StartTime 修复 (0dbcde1) ⭐ 最关键

#### 改动点

**常量定义**
```python
# Audio Gain uses "Amplitude" ParameterDef (matching DaVinci Resolve)
AAF_PARAMETERDEF_AMPLITUDE = uuid.UUID("e4962321-2267-11d3-8a4c-0050040ef7d2")

# Audio Gain OperationDefinition (AAF standard MonoAudioGain, matching DaVinci Resolve)
AAF_OPERATIONDEF_AUDIOGAIN = uuid.UUID("9d2ea894-0968-11d3-8a38-0050040ef7d2")
```

**SourceClip StartTime 设为 0**
```python
# 在 OperationGroup 内部的 SourceClip
source_clip["StartTime"].value = 0  # 而非 timeline offset
```

**为什么这是关键修复**
- OperationGroup 已经处理了时间线定位
- 内部 SourceClip 应该引用 MasterMob 的起始位置
- 非零 StartTime 导致 Pro Tools 无法定位音频数据

**Mob 追加顺序优化**
```python
# 从延迟追加改为即时追加，保持插入顺序
# 这样 mobs 会按 clip 顺序交错排列
# CompositionMob -> [MasterMob1, TapeMob1, FileMob1] -> [MasterMob2, TapeMob2, FileMob2] -> ...
```

**Filler 长度计算改进**
```python
# 使用 ceil 而非 int (floor)
frame_count = math.ceil(gap_duration.value)
length = int(frame_count * (self.audio_sampling_rate / gap_duration.rate))
```

**为什么这很重要**
- Clip durations 使用 floor（向下取整）
- Gap/Filler durations 使用 ceil（向上取整）
- 这确保总序列长度保持一致

**音频采样率动态检测**
```python
def _ensure_wav_info(self):
    """Read sample rate and bit depth from the first available WAV file."""
    # 从实际 WAV 文件读取，而非硬编码 48000
    with open(wav_path, 'rb') as wf:
        header = wf.read(4096)
        # 解析 WAV fmt chunk
        self._cached_sample_rate = struct.unpack_from('<I', header, pos + 12)[0]
        self._cached_bits_per_sample = struct.unpack_from('<H', header, pos + 22)[0]
```

#### 为什么重要
- 这是 Pro Tools 无法导入的**根本原因**
- UUID 错误导致 Pro Tools 不识别 Audio Gain 效果
- 非零 StartTime 导致音频数据定位失败

---

## 验证方法

### 已验证的改进项

1. **OperationDef UUID**
   ```bash
   uv run python tools/verify_operationdef_uuid.py
   # 输出: Audio Gain UUID: 9d2ea894-0968-11d3-8a38-0050040ef7d2 ✓
   ```

2. **SourceClip StartTime**
   ```bash
   uv run python diagnostics/investigate_start_times.py
   # 输出: All SourceClips in OperationGroups have StartTime=0 ✓
   ```

3. **AAF 结构对比**
   ```bash
   uv run python diagnostics/three_file_compare.py
   # 24/24 OperationGroups match ✓
   ```

4. **Pro Tools 实测**
   - 使用 `test_data/飞驰人生测试_fixed_output.aaf` 在 Pro Tools 中导入
   - 验证音频轨道正确识别和播放

---

## 迁移到 pt_compat 分支的策略

### 需要在新架构基础上重新实现的改动

1. **MobID 前缀补丁** - `_patch_mob_id_prefix()`
2. **CompositionMob MobID 格式** - DaVinci Resolve 前缀
3. **PhysicalTrackNumber** - 为所有 MobSlot 添加
4. **Audio slot 起始 ID** - 从 3 开始
5. **Timecode length** - +1 inclusive
6. **WAV Summary** - 从实际文件读取
7. **OperationDef UUID** - 使用正确的常量
8. **SourceClip StartTime** - 设为 0
9. **Mob 追加顺序** - 按 clip 交错
10. **Filler 长度** - 使用 ceil
11. **音频采样率检测** - 动态读取

### 不需要的改动

- `.gitignore` 更新（已在 pt_compat 分支）
- 音频转码功能（可作为可选功能）

---

## 下一步行动

1. 在 pt_compat 分支上创建新的提交
2. 逐项实现上述 11 个改动点
3. 使用现有测试数据验证
4. 提交 PR 到 upstream

---

## 参考文件

- 详细对比报告: `diagnostics/最终全方位对比报告.md`
- 验证脚本: `tools/verify_*.py`
- 测试数据: `test_data/飞驰人生测试_*`
