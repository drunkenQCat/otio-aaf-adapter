# 从 OTIO 到 AAF：一次失败但收获满满的 Pro Tools 兼容性调试之旅

> **摘要**：记录了一次尝试修复 OpenTimelineIO AAF 适配器导出文件以兼容 Pro Tools 的完整调试过程。从 CI/CD 搭建到 Rust 重写失败，从逆向分析到发现"30Hz 幽灵"，虽然最终未能成功，但分享了大量 AAF 文件格式、音频采样率处理和逆向工程的实战经验。

---

## 故事背景：一个看似简单的需求

一切的起因都很简单：**现有的 OTIO workflow 无法导出 Pro Tools 可以读取的 AAF 文件**。

作为一个音频后期工作者，我需要：

1. 批量导出音频
2. 将导出音频转换为 OTIO 时间线
3. 将OTIO转换为 AAF 格式
4. 在 Pro Tools 中进行音频后期

这个工作流卡在了第 3 步和第 4 步之间。

**奇怪的是**：DaVinci Resolve 直接导出的 AAF 文件，Pro Tools 可以完美导入。但用开源的 OTIO AAF 适配器导出的文件，Pro Tools 就是拒绝打开。

这就很奇怪了——**既然参考实现（DaVinci Resolve）的输出可以用，那我们开源库的输出为什么不能用？是不是文件结构有问题？**

---

## 第一阶段：寻找分析工具

要对比文件结构，首先需要一个能"看懂"AFF 文件的工具。

### 1.1 寻找 prebuilt 工具

我开始在 GitHub 上搜索 AAF 库的 prebuilt 版本，想找个现成的分析工具。结果：**没有找到 Windows 版本**。

AAF 参考实现 SDK 有完整的源代码，但需要自己编译。

### 1.2 搭建 CI/CD 工作流

既然没有现成的，那就自己 build！我搭建了一个 GitHub Actions CI 工作流来自动编译 AAF 库。

**但是**，由于我写工作流时的配置问题，CI 只输出了 Linux 版本，Windows 版本一直没有生成。

### 1.3 苦等 Windows 版本的日子里

在等待 Windows 版本构建出来的这段时间里，我做了一个"疯狂"的决定：

**既然 C++ 的 AAF 库这么难搞，不如用 Rust 重写一个！**

于是我开始了一次**彻底但失败**的 Rust 重写尝试。这个项目后来被我戏称为"轮子重新发明计划"。

按下不表，这次尝试虽然失败了，但让我对 AAF 文件格式有了更深入的理解。

---

## 第二阶段：终于有了分析工具

调整了 CI 工作流配置后，Windows 版本终于成功输出了！

从 build 出来的文件中，我找到了关键工具：**`dumpinfo.exe`**。

这个工具可以结构化地输出 AAF 文件的所有属性，正是我需要的对比工具！

### 2.1 创建自动化对比脚本

虽然我没有写正式的 skill，但我设计了一套简单"话术"，让 AI agent 可以自动调用这个 dump 工具。在此基础上，agent 就可以通过运行dumpinfo.exe来获取 AAF 文件的详细结构信息。

---

## 第三阶段：逐行对比的折磨

经过一轮一轮的比较和修改，开源库导出的 AAF 文件通过官方 `dumpinfo` 输出的信息，已经与 DaVinci Resolve 输出的**相差无几**了。

**关键属性对比**：

| 属性                  | DaVinci Resolve      | 我们的导出 |
| --------------------- | -------------------- | ---------- |
| Mob 顺序              | ✅ 一致              | ✅         |
| EditRate              | ✅ 48000/1           | ✅ 48000/1 |
| SampleRate            | ✅ 48000/1           | ✅ 48000/1 |
| Length                | ✅ 438000            | ✅ 438000  |
| WAVEDescriptor        | ✅                   | ✅         |
| Header Identification | ✅ Blackmagic Design | ✅         |

**但是**，Pro Tools 还是打不开。

---

## 第四阶段：逆向分析的决心

既然文件结构已经"几乎一样"但还是打不开，我决定：**直接逆向 Pro Tools！**

### 4.1 选择目标版本

我用的 Pro Tools 版本是**经典的 12 版**。这个版本稳定，而且网上资料比较多。

### 4.2 准备符号文件

使用我在ci中构建的DLL替换Pro Tools 的 DLL。

```
C:\Program Files\Avid\Pro Tools\
├── AAFCOAPI.dll       (带 PDB)
└── AAFCOAPI.pdb
```

### 4.3 发现库文件大小差异

在准备打断点时，我注意到一个**奇怪的细节**：

**Pro Tools 自带的 `AAFCOAPI.dll` 文件大小，和官方开源代码 build 出来的库大小不一样！**

| 文件         | 大小    | 来源           |
| ------------ | ------- | -------------- |
| AAFCOAPI.dll | 4.3 MB  | Pro Tools 自带 |
| AAFCOAPI.dll | 37.9 MB | 官方 SDK build |

这说明 Avid 对 AAF 库进行了**定制或裁剪**。

### 4.4 替换库文件

既然有源代码，打个断点应该不是难事。我把官方 build 出来的库替换了 Pro Tools 的库。

**奇迹发生了**！

替换之后，Pro Tools **居然可以正常加载**我们导出的 AAF 文件了！

那一刻的欣喜难以言表——**临门一脚了！**

---

## 第五阶段：30Hz 幽灵

打开文件后，我发现问题并没有完全解决。

### 5.1 音频被"放慢了无数倍"

Clip 片段的长度、位置都是对的，但**音频播放速度慢得离谱**，像是被放慢了无数倍。

这说明 Pro Tools 对音频采样率的理解有问题。

### 5.2 惊人的发现

当我再次查看导入数据的详细信息时，**惊讶地发现**：

**开源代码导出的 AAF，采样率显示为 30 Hz！**

```
WAVEDescriptor:
  SampleRate: 30/1 = 30.0  ← 这怎么可能？！
```

### 5.3 巨大的无力感

**30？！哪里来的 30？！**

我疯狂地 dump、查看、对比所有相关属性：

```python
# 检查所有可能的采样率属性
check_sample_rate()      # → 48000
check_edit_rate()        # → 48000
check_wav_header()       # → 48000
check_all_metadata()     # → 没有 30
```

**没有任何地方设置了 30！**

OTIO 文件中的 `duration.rate` 是 24（视频帧率），不是 30。
代码中设置的 SampleRate 是 48000。
WAV Header 中写入的是 48000。

**那这个 30 到底是从哪里冒出来的？！**

---

## 第六阶段：Agent 的"委屈"

我把这个"30Hz 幽灵"告诉了 AI agent。

他的反应像是**一个被冤枉的孩子**——难以置信，又无法反驳。

他消耗了那么多 token，写了那么多代码，做了那么细致的对比和修复，最终因为一个**荒谬的数字**被宣告失败。

```
Agent: "可是...可是我真的找不到 30 是从哪里来的啊！"
```

我们检查了：

- ✅ WAVEDescriptor SampleRate = 48000
- ✅ WAV Header SampleRate = 48000
- ✅ EditRate = 48000
- ✅ 所有属性都没有 30

**但 Pro Tools 就是显示 30 Hz。**

---

## 未解之谜：30Hz 从哪里来？

### 可能的来源推测

1. **Pro Tools 的私有计算逻辑**
   - 可能用某种公式从其他属性推导出"采样率"
   - 比如：`48000 / 1600 = 30`（纯猜测）

2. **缓存或元数据**
   - Pro Tools 可能缓存了之前导入的信息
   - 或者读取了文件某个隐藏区域的元数据

3. **时间戳或帧率的误读**
   - OTIO 中的 `duration.rate = 24` 接近 30
   - Pro Tools 可能做了某种"智能猜测"

4. **Avid 的私有扩展**
   - AAF 规范允许私有扩展
   - Pro Tools 可能依赖某个我们没有设置的私有属性

### 下一步研究方向（有时间的话）

1. **二进制层面分析**
   - 用 hex editor 对比两个文件的每一个字节
   - 寻找 30 这个值的二进制表示（0x1E）

2. **动态调试 Pro Tools**
   - 在采样率读取函数下断点
   - 追踪 30 这个值是在哪里被写入的

3. **尝试其他版本**
   - Pro Tools 2021、2022、2023
   - 看是否所有版本都有这个问题

**但现在，我确实没有时间继续深入了。**

---

## 经验总结

### 1. OTIO 的音频时长表示

DaVinci Resolve 导出 OTIO 时，音频的 `duration.rate` 是**视频帧率**（24 或 30），而不是音频采样率（48000）：

```json
{
  "OTIO_SCHEMA": "Clip.2",
  "name": "ICE.wav",
  "source_range": {
    "duration": {
      "rate": 24.0, // ❌ 这是视频帧率，不是音频采样率
      "value": 219.0
    }
  }
}
```

这导致很多工具会误以为音频采样率是 24 或 30 Hz。

### 2. 正确的音频长度计算

```python
# 错误做法：直接使用 OTIO 的 rate
length = clip.duration().value  # 219 帧

# 正确做法：转换为音频采样数
duration_seconds = clip.duration().value / clip.duration().rate  # 219/24 = 9.125 秒
length_samples = int(duration_seconds * audio_sampling_rate)  # 9.125 * 48000 = 438000 采样
```

### 3. AAF 文件的 Mob 顺序

正确的 Mob 添加顺序（与 DaVinci Resolve 一致）：

1. **CompositionMob**（顶层组合）
2. **MasterMob**（主素材）
3. **SourceMob with TapeDescriptor**（磁带源）
4. **SourceMob with WAVEDescriptor**（音频文件源）

```python
def append_all_mobs(self):
    # 1. CompositionMob
    self.aaf_file.content.mobs.append(self.compositionmob)

    # 2. MasterMobs
    for mob in master_mobs:
        self.aaf_file.content.mobs.append(mob)

    # 3. TapeDescriptor SourceMobs
    for mob in tape_mobs:
        self.aaf_file.content.mobs.append(mob)

    # 4. WAVEDescriptor SourceMobs
    for mob in file_mobs:
        self.aaf_file.content.mobs.append(mob)
```

### 4. WAVEDescriptor 的完整属性

```python
descriptor = self.aaf_file.create.WAVEDescriptor()
descriptor["SampleRate"].value = 48000  # 音频采样率
descriptor["Length"].value = 438000     # 采样数
descriptor["Locator"].append(locator)   # 文件路径
descriptor["Summary"].value = wav_header_bytes  # WAV 头（可选但推荐）
```

---

## 未解之谜

**Pro Tools 显示的"30 Hz"到底从哪里来？**

经过全面检查：

- ✅ WAVEDescriptor SampleRate = 48000
- ✅ WAV Header SampleRate = 48000
- ✅ EditRate = 48000
- ✅ 没有任何属性值为 30

**推测**：

1. Pro Tools 可能读取了 OTIO 文件中的 `duration.rate`（24 或 30）
2. 或者 Pro Tools 有自己的音频采样率检测逻辑，但算法有误
3. 最可能：Pro Tools 有什么私有的验证逻辑或缓存机制

---

## 经验总结

### 技术层面

1. **AAF 文件格式极其复杂**
   - 一个完整的 AAF 文件包含数百个对象和属性
   - 不同软件对规范的理解和实现有差异
   - 私有扩展和验证逻辑很常见

2. **音频采样率的处理**
   - OTIO 用视频帧率表示音频时长（历史原因）
   - AAF 中必须用实际音频采样率
   - 转换公式：`采样数 = (帧数/帧率) × 采样率`

3. **兼容性调试的最佳实践**
   - 用参考实现（DaVinci Resolve）的输出作为黄金标准
   - 逐属性对比，不放过任何细节
   - 使用多种工具验证（dump、pyaaf2、自定义脚本）

4. **逆向工程的工具链**
   - IDA Pro + PDB 符号 = 快速定位关键代码
   - AAF SDK 头文件帮助理解函数签名
   - 动态调试比静态分析更有效

### 软技能层面

1. **不要过早下结论**
   - 一开始以为是采样率设置错误
   - 实际上是 Pro Tools 的私有逻辑

2. **文档和日志的重要性**
   - 每次修改都记录差异
   - 最终的博客文章就是调试日志的整理

3. **知道何时停止**
   - 当技术问题解决到 99% 时
   - 剩下的 1% 可能是商业壁垒
   - 承认失败也是一种成功

---

## 代码资源

本次调试中创建的工具有：

- `check_sample_rate.py` - 检查 AAF 文件中的采样率
- `check_all_rates.py` - 检查所有可能被误读为采样率的属性
- `check_wav_header.py` - 验证 WAV Header 的正确性
- `diff_dumps.py` - 对比两个 AAF dump 文件
- `deep_compare_aaf.py` - 深入对比 AAF 文件结构

这些工具都开源在：[GitHub 仓库链接]

---

## 结论

虽然最终没能让 Pro Tools 导入我们的 AAF 文件，但这个过程让我们：

1. 深入理解了 AAF 文件格式
2. 掌握了逆向分析的基本方法
3. 发现了 OTIO 音频时长表示的陷阱
4. 修复了 WAV Header ByteRate 的计算错误

**有时候，失败的项目比成功的项目能学到更多。**

---

## 参考资料

- [OpenTimelineIO 官方文档](https://opentimelineio.readthedocs.io/)
- [pyaaf2 GitHub 仓库](https://github.com/markreidvfx/pyaaf2)
- [AAF 参考实现 SDK](https://sourceforge.net/projects/aaf/)
- [SMPTE AAF 规范](https://www.amwa.tv/specifications)

---

_作者：[你的名字]_  
_日期：2026 年 3 月_  
_标签：#AAF #OpenTimelineIO #ProTools #逆向工程 #音频处理_
