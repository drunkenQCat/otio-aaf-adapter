# PT-Compat 分支完善计划 - Todo List

## 当前状态
- **总测试数**: 66
- **通过**: 64 (97.0%)
- **失败**: 2 (3.0%)
- **失败的测试**:
  1. `test_aaf_roundtrip_first_clip`: source_range.start_time 从 101 变成 102（+1）
  2. `test_transcribe_embed_dnx_data`: source_range.start_time 从 1 变成 2（+1）

## 目标
确保 pt_compat 分支能够恢复 dev 分支输出的 AAF 文件的特性，并与 DaVinci Resolve 导出的文件做对比，形成验证循环。

---

## Phase 1: 分析失败的测试 (高优先级)

### Task 1.1: 分析 test_aaf_roundtrip_first_clip
- [ ] 检查测试的详细逻辑
- [ ] 检查 NO_METADATA_OTIO_PATH 文件的内容
- [ ] 检查第一个 clip 的 source_range
- [ ] 检查 roundtrip 后的 source_range
- [ ] 找出 source_range.start_time +1 的原因

### Task 1.2: 分析 test_transcribe_embed_dnx_data
- [ ] 检查测试的详细逻辑
- [ ] 检查 DNX 文件的嵌入逻辑
- [ ] 检查 source_range 的计算
- [ ] 找出 source_range.start_time +1 的原因

### Task 1.3: 对比 dev 和 pt_compat 分支
- [ ] 运行 dev 分支的测试，确保它们通过
- [ ] 导出相同的 OTIO 文件到 AAF（dev 和 pt_compat）
- [ ] 对比两个 AAF 文件的结构
- [ ] 找出导致 +1 问题的具体代码

---

## Phase 2: 修复问题 (高优先级)

### Task 2.1: 修复 source_range.start_time +1 问题
- [ ] 根据 Task 1.3 的分析结果修复问题
- [ ] 运行测试验证修复
- [ ] 确保所有测试通过

### Task 2.2: 验证修复
- [ ] 运行完整测试套件
- [ ] 确保所有测试通过
- [ ] 运行 flake8 检查代码风格
- [ ] 修复所有代码风格问题

---

## Phase 3: 与 DaVinci Resolve 对比 (中优先级)

### Task 3.1: 导出 AAF 文件
- [ ] 使用 pt_compat 导出多个 OTIO 文件到 AAF
- [ ] 记录导出参数和配置

### Task 3.2: 与 DaVinci Resolve 对比
- [ ] 使用 DaVinci Resolve 打开 pt_compat 导出的 AAF 文件
- [ ] 检查时间码、音频轨道、视频轨道等
- [ ] 对比 DaVinci Resolve 导出的 AAF 文件
- [ ] 确保与 DaVinci Resolve 的行为一致

### Task 3.3: 修复不一致的地方
- [ ] 根据 Task 3.2 的结果修复任何不一致的地方
- [ ] 运行测试验证修复
- [ ] 确保所有测试通过

---

## Phase 4: 文档和提交 (低优先级)

### Task 4.1: 更新文档
- [ ] 更新 README.md
- [ ] 更新 CHANGELOG.md
- [ ] 更新 PT_COMPAT_ANALYSIS.md

### Task 4.2: 提交代码
- [ ] 提交所有修复
- [ ] 创建 pull request
- [ ] 等待代码审查

---

## 验证循环

### 循环 1: 与 dev 分支对比
1. 运行 dev 分支的测试，确保它们通过
2. 导出相同的 OTIO 文件到 AAF（dev 和 pt_compat）
3. 对比两个 AAF 文件的结构
4. 找出导致 +1 问题的具体代码
5. 修复问题并重新测试
6. 重复步骤 2-5，直到所有测试通过

### 循环 2: 与 DaVinci Resolve 对比
1. 使用 pt_compat 导出 AAF 文件
2. 使用 DaVinci Resolve 打开并检查
3. 对比 DaVinci Resolve 导出的 AAF 文件
4. 确保与 DaVinci Resolve 的行为一致
5. 修复任何不一致的地方
6. 重复步骤 1-5，直到与 DaVinci Resolve 完全一致

---

## 关键指标

### 测试通过率
- **目标**: 100%
- **当前**: 97.0% (64/66)
- **差距**: 2 个测试失败

### 代码覆盖率
- **目标**: 85%+
- **当前**: 50% (需要提高)

### 代码风格
- **目标**: 0 个 flake8 错误
- **当前**: 需要检查

---

## 风险和缓解措施

### 风险 1: source_range.start_time +1 问题难以定位
**缓解措施**:
- 深入分析测试代码
- 对比 dev 和 pt_compat 分支的输出
- 使用调试工具逐步跟踪代码执行

### 风险 2: 与 DaVinci Resolve 的行为不一致
**缓解措施**:
- 使用 DaVinci Resolve 打开并检查 AAF 文件
- 对比 DaVinci Resolve 导出的 AAF 文件
- 确保与 DaVinci Resolve 的行为一致

### 风险 3: 代码覆盖率不足
**缓解措施**:
- 添加更多测试用例
- 确保所有代码路径都被测试覆盖

---

## 时间估计

### Phase 1: 分析失败的测试
- Task 1.1: 2 小时
- Task 1.2: 2 小时
- Task 1.3: 3 小时
- **总计**: 7 小时

### Phase 2: 修复问题
- Task 2.1: 3 小时
- Task 2.2: 2 小时
- **总计**: 5 小时

### Phase 3: 与 DaVinci Resolve 对比
- Task 3.1: 2 小时
- Task 3.2: 3 小时
- Task 3.3: 2 小时
- **总计**: 7 小时

### Phase 4: 文档和提交
- Task 4.1: 2 小时
- Task 4.2: 1 小时
- **总计**: 3 小时

### 总计: 22 小时

---

## 下一步行动

### 立即执行
1. 开始 Task 1.1: 分析 test_aaf_roundtrip_first_clip
2. 开始 Task 1.2: 分析 test_transcribe_embed_dnx_data
3. 开始 Task 1.3: 对比 dev 和 pt_compat 分支

### 短期目标 (1-2 天)
1. 完成 Phase 1: 分析失败的测试
2. 完成 Phase 2: 修复问题
3. 确保所有测试通过

### 中期目标 (3-5 天)
1. 完成 Phase 3: 与 DaVinci Resolve 对比
2. 确保与 DaVinci Resolve 的行为一致
3. 完成 Phase 4: 文档和提交

### 长期目标 (1 周)
1. 创建 pull request
2. 等待代码审查
3. 根据反馈修复问题
4. 合并到主分支
