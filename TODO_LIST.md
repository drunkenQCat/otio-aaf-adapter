# PT-Compat 分支完善计划 - Todo List

## 阶段 1: 验证循环建立（高优先级）

### 1.1 导出 dev 分支参考 AAF
- [ ] 切换到 dev 分支
- [ ] 使用 `tests/sample_data/no_metadata.otio` 导出 AAF
- [ ] 保存为 `reference/dev_branch_output.aaf`
- [ ] 切回 pt_compat 分支

### 1.2 运行验证循环
- [ ] 运行 verification_loop.py 对比 pt_compat vs dev
- [ ] 分析差异报告
- [ ] 记录所有不匹配项

### 1.3 与 DaVinci Resolve 参考对比（如果有）
- [ ] 获取 DaVinci Resolve 导出的参考 AAF
- [ ] 运行 verification_loop.py 对比
- [ ] 分析差异报告

## 阶段 2: 修复 MobID 相关问题（高优先级）

### 2.1 分析 4 个 MobID 失败测试
- [ ] test_aaf_writer_duplicates
  - 运行测试，记录错误详情
  - 对比期望的 MobID 和实际的 MobID
  - 确定字节顺序差异
  
- [ ] test_aaf_writer_nesting
  - 运行测试，记录错误详情
  - 分析 MobID 差异原因
  
- [ ] test_aaf_writer_nested_stack
  - 运行测试，记录错误详情
  - 分析 MobID 差异原因
  
- [ ] test_aaf_writer_external_reference
  - 运行测试，记录错误详情
  - 分析 MobID 差异原因

### 2.2 确定修复策略
- [ ] 分析测试期望的 MobID 格式
- [ ] 确定是否需要恢复 _patch_mob_id_prefix
- [ ] 或者调整 MobID 生成逻辑

### 2.3 实施修复
- [ ] 根据分析结果实施修复
- [ ] 运行测试验证
- [ ] 确保不破坏其他测试

## 阶段 3: 修复 source_range 差异（中优先级）

### 3.1 分析 3 个 source_range 失败测试
- [ ] test_aaf_roundtrip_first_clip
  - 运行测试，记录错误详情
  - 对比期望的 source_range 和实际的 source_range
  - 确定差值（应该是 1）
  
- [ ] test_aaf_writer_nometadata
  - 运行测试，记录错误详情
  - 分析 source_range 差异原因
  
- [ ] test_transcribe_embed_dnx_data
  - 运行测试，记录错误详情
  - 分析 source_range 差异原因

### 3.2 调查根本原因
- [ ] 检查 timecode length +1 是否影响 source_range
- [ ] 检查 offset 计算逻辑
- [ ] 对比 dev 分支的实现

### 3.3 实施修复
- [ ] 根据分析结果实施修复
- [ ] 运行测试验证
- [ ] 确保不破坏其他测试

## 阶段 4: 修复 URL 格式问题（低优先级）

### 4.1 分析 3 个 URL 失败测试
- [ ] test_aaf_writer_simple
  - 运行测试，记录错误详情
  - 对比期望的 URL 和实际的 URL
  
- [ ] test_aaf_writer_transitions
  - 运行测试，记录错误详情
  - 分析 URL 差异原因
  
- [ ] test_aaf_writer_audio_pan
  - 运行测试，记录错误详情
  - 分析 URL 差异原因

### 4.2 确定修复策略
- [ ] 决定使用 file:/// 还是 file://
- [ ] 统一所有 URL 处理逻辑
- [ ] 更新测试期望（如果需要）

### 4.3 实施修复
- [ ] 根据分析结果实施修复
- [ ] 运行测试验证
- [ ] 确保不破坏其他测试

## 阶段 5: 完整测试验证

### 5.1 运行完整测试套件
- [ ] pytest tests/test_aaf_adapter.py -v
- [ ] 记录所有测试结果
- [ ] 确保所有测试通过

### 5.2 运行验证循环
- [ ] 使用 verification_loop.py 对比 dev 分支
- [ ] 确保所有关键属性匹配
- [ ] 生成对比报告

### 5.3 使用多个测试文件验证
- [ ] tests/sample_data/simple_example.otio
- [ ] tests/sample_data/transitions.otio
- [ ] tests/sample_data/nesting.otio
- [ ] tests/sample_data/nested_stack.otio
- [ ] 确保所有文件都能正确导出

## 阶段 6: Pro Tools 实际测试

### 6.1 导出测试 AAF
- [ ] 使用 pt_compat 分支导出多个测试 AAF
- [ ] 记录导出参数和配置

### 6.2 Pro Tools 导入测试
- [ ] 在 Pro Tools 中导入导出的 AAF
- [ ] 验证音频轨道识别
- [ ] 验证音频播放
- [ ] 验证时间码显示

### 6.3 问题记录
- [ ] 记录任何导入问题
- [ ] 记录任何播放问题
- [ ] 记录任何显示问题

## 阶段 7: 文档完善

### 7.1 更新迁移状态报告
- [ ] 更新测试结果
- [ ] 更新验证循环结果
- [ ] 更新 Pro Tools 测试结果

### 7.2 编写用户文档
- [ ] 编写 Pro Tools 兼容性说明
- [ ] 编写使用指南
- [ ] 编写已知限制

### 7.3 准备 PR 描述
- [ ] 总结所有改动
- [ ] 列出解决的问题
- [ ] 提供测试证据

## 阶段 8: 最终检查

### 8.1 代码质量检查
- [ ] 运行 flake8
- [ ] 修复所有警告
- [ ] 确保代码风格一致

### 8.2 性能检查
- [ ] 对比导出速度
- [ ] 确保没有性能回归

### 8.3 提交 PR
- [ ] 创建 pull request
- [ ] 填写详细的 PR 描述
- [ ] 提供测试证据
- [ ] 请求代码审查

## 当前状态

- ✅ 阶段 1.1: 未开始
- ✅ 阶段 1.2: 未开始
- ✅ 阶段 1.3: 未开始（可选）

## 下一步行动

1. **立即执行**: 开始阶段 1 - 建立验证循环
   - 切换到 dev 分支
   - 导出参考 AAF
   - 切回 pt_compat 分支
   - 运行 verification_loop.py

2. **然后根据结果**: 开始阶段 2 - 修复 MobID 问题
   - 分析失败测试
   - 确定修复策略
   - 实施修复

3. **最后**: 继续其他阶段
   - 根据验证循环结果调整优先级
