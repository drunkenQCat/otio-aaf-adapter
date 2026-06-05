# 技术交接文档：OTIO AAF 适配器的 Pro Tools 兼容性修复

**文档类型**: 项目交接 / 知识传承  
**最后更新**: 2026年3月14日  
**项目**: otio-aaf-adapter (OpenTimelineIO AAF 适配器)  
**核心目标**: 使 OTIO 导出的 AAF 文件能够被 Avid Pro Tools 正确导入

---

## 一、问题陈述

### 核心问题
OpenTimelineIO (OTIO) 的 AAF 适配器导出的 AAF 文件**无法被 Avid Pro Tools 正确导入**。

### 对比基准
DaVinci Resolve 导出的 AAF 文件可以被 Pro Tools 完美导入，这证明 Pro Tools 本身支持 AAF 格式，问题出在我们导出的文件上。

---

## 二、问题表象

### 2.1 导入失败
- **原始现象**: 使用 Pro Tools 自带的 `AAFCOAPI.dll` 时，AAF 文件完全无法导入
- **替换 DLL 后**: 将官方 AAF SDK 编译的 `AAFCOAPI.dll` 替换到 Pro Tools 后，文件可以导入

### 2.2 采样率显示异常（核心未解决问题）
- **现象**: Pro Tools 导入后，显示音频采样率为 **30 Hz**
- **预期**: 应该是 **48000 Hz**
- **影响**: 音频播放速度极慢，如同被放慢了无数倍
- **诡异之处**: 在 AAF 文件的所有可检查属性中，**没有任何地方存储了 30 这个值**

### 2.3 已检查的属性（全部正确）
| 属性 | 期望值 | 实际值 | 状态 |
|------|--------|--------|------|
| WAVEDescriptor.SampleRate | 48000/1 | 48000/1 | ✅ |
| WAV Header 中的 SampleRate | 48000 | 48000 | ✅ |
| 音频轨道 EditRate | 48000/1 | 48000/1 | ✅ |
| 音频 SourceClip Length | 438000 采样 | 438000 | ✅ |
| 音频 Sequence 总长度 | 440000 | 440000 | ✅ |
| ByteRate (WAV Header) | 96000 | 96000 | ✅ |
| BlockAlign | 2 | 2 | ✅ |
| BitsPerSample | 16 | 16 | ✅ |

### 2.4 30 Hz 的来源之谜
- 文件中没有任何属性值为 30
- 没有 EditRate = 30 的轨道
- 没有 Timecode FPS = 30
- 唯一接近的巧合：`48000 / 1600 = 30`，但这没有物理意义
- **推测**: Pro Tools 可能通过某种私有逻辑计算出了 30，或者读取了我们未发现的某个属性

---

## 三、可能的根因

### 3.1 OperationalPattern 差异（已修复）
- **问题**: 我们设置了 `OperationalPattern = 0d011201-0100-0000-060e-2b3404010105`
- **DaVinci Resolve**: 没有显式设置此属性（值为 None）
- **状态**: 已注释掉设置代码，现在与 DaVinci Resolve 一致

### 3.2 CompositionMob 槽位数量差异（未修复）
- **DaVinci Resolve**: 2 个槽位（Timecode + Audio）
- **我们的输出**: 3 个槽位（Timecode + Video + Audio）
- **影响**: 未知，可能导致 Pro Tools 误读

### 3.3 Header Version 差异（未修复）
- **DaVinci Resolve**: `{1, 1}`
- **我们的输出**: `{1, 2}`
- **影响**: 未知

### 3.4 Mob 添加顺序（已修复但需验证）
- **正确顺序**: CompositionMob → MasterMob → SourceMob(Tape) → SourceMob(WAVE)
- **当前状态**: 已实现正确顺序
- **验证方式**: 使用 `check_mob_order.py` 检查

### 3.5 MobID 前缀格式（已修复）
- **DaVinci Resolve**: `060a2b34.01010101.01010f00.13000000`
- **原始 pyaaf2**: `060a2b34.01010105.01010f20.13000000`
- **状态**: 已修改为与 DaVinci Resolve 一致

### 3.6 Identification 元数据（已修复）
- **问题**: pyaaf2 默认添加 "PyAAF" 标识
- **解决**: 清除默认标识，添加 "Blackmagic Design / DaVinci Resolve" 标识

### 3.7 最可能的根因假设
1. **Pro Tools 的私有验证逻辑**: Avid 可能有未公开的 AAF 验证规则
2. **某个隐藏属性的缺失或错误**: 可能是 AAF 规范中未明确要求的某个属性
3. **字节序或编码问题**: 某些数值在存储时可能有细微差异
4. **AAF SDK 版本兼容性**: Pro Tools 使用的 AAF SDK 版本可能与我们编译的不同

---

## 四、已付出的努力

### 4.1 工具链建设
1. **搭建 GitHub Actions CI**: 编译 AAF 参考实现 SDK
   - 最初只输出了 Linux 版本
   - 调整后成功输出 Windows 版本
   - 获得了关键工具 `dump.bat`（AAF 文件结构化分析器）

2. **创建自动化对比脚本**:
   - `diff_dumps.py`: 对比两个 AAF dump 文件
   - `deep_compare_aaf.py`: 深入对比 AAF 文件属性
   - `simple_compare.py`: 简化版对比
   - `check_sample_rate.py`: 检查采样率
   - `check_all_rates.py`: 检查所有可能的采样率相关属性
   - `check_wav_header.py`: 验证 WAV Header
   - `check_mob_order.py`: 检查 Mob 顺序
   - `check_operational_pattern.py`: 检查 OperationalPattern
   - `compare_binary.py`: 逐字节二进制对比

3. **尝试 Rust 重写**（失败）:
   - 在等待 CI 输出 Windows 版本期间，尝试将 AAF 库从 C++ 转写为 Rust
   - 项目失败，但对 AAF 文件格式有了更深入理解

### 4.2 代码修复
1. **修复音频轨道 EditRate**: 从 24 改为 48000
2. **修复音频 SourceClip 长度**: 从视频帧数 (219) 改为音频采样数 (438000)
3. **修复 MasterMob SlotID**: 从 2 改为 1
4. **添加音频 Filler**: 添加 2000 采样的 Filler 使总长度达到 440000
5. **修复 CompositionMob 槽位顺序**: Timecode 成为第一个槽位
6. **修改 Descriptor 类型**: 从 PCMDescriptor 改为 WAVEDescriptor
7. **修复 SourceMob 结构**: 使用 TapeDescriptor + WAVEDescriptor 组合
8. **修复 Mob 添加顺序**: CompositionMob → MasterMob → SourceMob(Tape) → SourceMob(WAVE)
9. **修复 MobID 前缀**: 匹配 DaVinci Resolve 格式
10. **修复 Header Identification**: 伪装为 DaVinci Resolve
11. **修复 WAV Header ByteRate**: 从错误的 1584896 改为正确的 96000
12. **移除 OperationalPattern**: 与 DaVinci Resolve 保持一致

### 4.3 逆向分析尝试
1. **获取 Pro Tools DLL 符号**: Pro Tools 12 的 DLL 带有 PDB 符号文件
2. **发现库文件差异**: Pro Tools 自带的 `AAFCOAPI.dll` (2.1MB) 与官方 SDK 编译的 (3.4MB) 大小不同
3. **替换 DLL 实验**: 替换后 Pro Tools 可以导入文件，但出现 30 Hz 问题
4. **二进制对比**: 使用 `compare_binary.py` 逐字节对比两个文件
5. **发现 PID 差异**: 偏移 0x28 处，Correct 文件是 PID 30 (OperationalPattern)，Test 文件是 PID 64 (ObjectModelVersion)

### 4.4 Token 消耗
- 整个调试过程消耗了大量 AI tokens
- 进行了数十轮代码修改和验证
- 创建了 10+ 个诊断脚本
- 修改了 pyaaf2 库的源码

---

## 五、当前代码状态

### 5.1 修改的文件
1. **`src/otio_aaf_adapter/adapters/advanced_authoring_format.py`**:
   - 注释掉了 OperationalPattern 设置（第 1646-1649 行）
   - 清除了 pyaaf2 默认 Identification
   - 添加了 DaVinci Resolve 伪装 Identification

2. **`src/otio_aaf_adapter/adapters/aaf_adapter/aaf_writer.py`**:
   - 修复了音频轨道 EditRate (48000)
   - 修复了音频 SourceClip 长度 (438000)
   - 修复了 MasterMob SlotID (1)
   - 添加了音频 Filler (2000)
   - 修改了 CompositionMob 槽位顺序
   - 修改了 Descriptor 类型为 WAVEDescriptor
   - 修改了 SourceMob 结构 (TapeDescriptor + WAVEDescriptor)
   - 修改了 Mob 添加顺序
   - 修改了 MobID 前缀格式
   - 修复了 WAV Header ByteRate 计算

3. **`pyaaf2/src/aaf2/file.py`** (已复制到 `.venv/Lib/site-packages/aaf2/file.py`):
   - 注释掉了 OperationalPattern 默认设置（第 258 行）
   - 修改了 IdentificationList 初始化（不再添加默认 PyAAF 标识）

### 5.2 测试脚本
- `test_export.py`: 主测试脚本，导出并验证 AAF 文件
- `check_*.py`: 各种诊断脚本
- `compare_binary.py`: 二进制对比工具

### 5.3 输出文件
- `test_output.aaf`: 最新导出的 AAF 文件
- `result.aaf`: 测试输出的副本
- `test_dump.log`: 使用 dump.bat 生成的结构化输出

---

## 六、未来工作指南

### 6.1 必需工具
1. **AAF SDK dump 工具** (`dump.bat`):
   - 位置: 需要从 AAF 参考实现编译
   - 用途: 生成 AAF 文件的结构化输出
   - 命令: `dump.bat <aaf_file> > <output.txt>`

2. **pyaaf2** (Python AAF 库):
   - 位置: 项目目录 `pyaaf2/`
   - 注意: 已修改源码，需要复制到 `.venv/Lib/site-packages/aaf2/`
   - 用途: 编程访问 AAF 文件

3. **IDA Pro**:
   - 用途: 逆向分析 Pro Tools DLL
   - 目标文件:
     - `C:\Program Files\Avid\Pro Tools\PtAAF.dll` (带 PDB)
     - `C:\Program Files\Avid\Pro Tools\AAFCOAPI.dll` (带 PDB)

4. **OpenTimelineIO**:
   - 版本: >= 0.17.0
   - 用途: 读取 OTIO 时间线并导出 AAF

### 6.2 关键参考文件
1. **DaVinci Resolve 导出的正确 AAF**:
   - 位置: `C:\TechProjects\About_Voice_Cloning\AAF-src-1.2.0\AAF\aaf-rs\output\correct_timeline.aaf`
   - 用途: 作为黄金标准进行对比

2. **AAF 参考实现头文件**:
   - 位置: `C:\TechProjects\Timeline_Projects\aaf\AAFWinSDK\vs10\include\`
   - 关键文件:
     - `AAF.h`: 主 API 头文件
     - `AAFTypes.h`: 类型定义（包括 `aafRational_t`）
     - `AAFPropertyDefs.h`: 属性 ID 定义
     - `AAFStoredObjectIDs.h`: 对象 ID 定义

3. **pyaaf2 源码**:
   - 位置: `C:\TechProjects\Timeline_Projects\otio-aaf-adapter\pyaaf2\`
   - 关键文件:
     - `src/aaf2/file.py`: AAF 文件读写逻辑
     - `src/aaf2/content.py`: ContentStorage 实现
     - `src/aaf2/mobs.py`: Mob 实现

4. **OTIO 测试时间线**:
   - 位置: `C:\TechProjects\Timeline_Projects\otio-aaf-adapter\SimpleTimeline.otio`
   - 内容: 包含视频轨道（Gap）和音频轨道（ICE.wav）

### 6.3 继续工作的步骤

#### 第一阶段：确认当前状态
1. 运行 `test_export.py` 导出最新 AAF 文件
2. 运行 `dump.bat test_output.aaf > test_dump.log` 生成结构化输出
3. 使用 `check_operational_pattern.py` 确认 OperationalPattern 已移除
4. 将 `result.aaf` 导入 Pro Tools 测试

#### 第二阶段：深入逆向分析（如果问题仍存在）
1. **使用 IDA Pro 分析 Pro Tools**:
   - 打开 `PtAAF.dll`（带 PDB 符号）
   - 搜索字符串 "SampleRate"、"Invalid"、"Error"
   - 查找 AAF 导入相关函数
   - 设置断点，动态调试

2. **追踪 30 Hz 的来源**:
   - 在 Pro Tools 读取 SampleRate 的函数处设置断点
   - 观察 Pro Tools 实际读取的值
   - 追踪这个值的计算过程

3. **二进制层面分析**:
   - 使用 `compare_binary.py` 找出所有差异
   - 重点关注 Rational 类型的属性（两个 uint32）
   - 检查是否有隐藏的属性或元数据

#### 第三阶段：尝试其他方案
1. **尝试不同的 OperationalPattern**:
   - OPAtom: `0d011201-0100-0000-060e-2b3404010101`
   - OP1a: `0d011201-0100-0000-060e-2b3404010105`
   - 或者完全不设置（当前状态）

2. **尝试不同的 Header Version**:
   - 修改为 `{1, 1}` 以匹配 DaVinci Resolve

3. **尝试移除视频轨道**:
   - 导出纯音频 AAF 文件，看是否能解决问题

### 6.4 最终目标
使 OTIO AAF 适配器导出的文件能够：
1. ✅ 被 Pro Tools 成功导入（已实现，需替换 DLL）
2. ❌ 正确显示采样率（48000 Hz，不是 30 Hz）
3. ❌ 音频播放速度正常
4. ❌ 无需替换 Pro Tools 自带的 AAF DLL

---

## 七、关键洞察

### 7.1 OTIO 的音频时长表示陷阱
DaVinci Resolve 导出 OTIO 时，音频的 `duration.rate` 是**视频帧率**（24），而不是音频采样率（48000）。这导致很多工具会误以为音频采样率是 24 或 30。

**正确的转换公式**:
```python
duration_seconds = clip.duration().value / clip.duration().rate  # 219/24 = 9.125 秒
length_samples = int(duration_seconds * audio_sampling_rate)  # 9.125 * 48000 = 438000 采样
```

### 7.2 AAF 文件的复杂性
- 一个完整的 AAF 文件包含数百个对象和属性
- 不同软件对 AAF 规范的理解和实现有差异
- 私有扩展和验证逻辑很常见
- Pro Tools 使用的 AAF SDK 版本可能与开源版本不同

### 7.3 调试方法论
1. **对比驱动**: 始终有一个正确的参考文件（DaVinci Resolve 输出）
2. **逐属性验证**: 不放过任何细节，即使是看似无关的属性
3. **多层次验证**: 使用 dump 工具、pyaaf2、二进制对比等多种方法
4. **假设-验证循环**: 提出假设，修改代码，验证结果

### 7.4 30 Hz 问题的本质
这个问题可能不是技术错误，而是**兼容性壁垒**：
- Pro Tools 可能依赖某个 Avid 私有的 AAF 扩展
- 或者 Pro Tools 的 AAF 解析器有特定的 bug
- 或者需要特定的 OperationalPattern 才能正确解析

---

## 八、联系与资源

### 8.1 项目仓库
- **OTIO AAF Adapter**: `C:\TechProjects\Timeline_Projects\otio-aaf-adapter`
- **AAF 参考实现**: `C:\TechProjects\Timeline_Projects\aaf`
- **pyaaf2 (修改版)**: `C:\TechProjects\Timeline_Projects\otio-aaf-adapter\pyaaf2`

### 8.2 关键 URL
- OpenTimelineIO: https://opentimelineio.readthedocs.io/
- pyaaf2: https://github.com/markreidvfx/pyaaf2
- AAF SDK: https://sourceforge.net/projects/aaf/
- SMPTE AAF 规范: https://www.amwa.tv/specifications

### 8.3 Pro Tools 相关文件
- 安装目录: `C:\Program Files\Avid\Pro Tools\`
- PtAAF.dll: 主 AAF 处理库（带 PDB 符号）
- AAFCOAPI.dll: AAF COM API（带 PDB 符号）
- 版本: Pro Tools 12

---

## 九、最后的建议

1. **不要放弃**: 我们已经解决了 90% 的问题，剩下的 10% 可能是最难的部分
2. **优先考虑逆向分析**: Pro Tools 的私有逻辑可能是唯一能找到 30 Hz 来源的方法
3. **考虑替代方案**: 如果无法解决，可以考虑使用其他中间格式（如 XML、EDL）
4. **记录一切**: 每次修改都记录差异，最终的博客文章就是调试日志的整理
5. **寻求帮助**: 可以考虑在 OpenTimelineIO 或 pyaaf2 的 GitHub Issues 中寻求帮助

---

**文档结束**

*这是一份技术交接文档，记录了 OTIO AAF 适配器 Pro Tools 兼容性修复的完整过程。虽然最终未能完全解决问题，但积累了大量关于 AAF 文件格式、音频采样率处理和逆向工程的实战经验。*
