# OpenTimelineIO AAF Adapter - 项目上下文文档

## 项目概述

这是一个 **OpenTimelineIO (OTIO)** 适配器插件，用于读取和写入 **Advanced Authoring Format (AAF)** 文件。AAF 是视频后期制作行业中用于交换编辑数据的标准格式。

该项目原本作为 OpenTimelineIO 的 contrib adapter 存在，现正被分离为独立项目以提高可维护性并减少依赖。

### 核心技术栈

- **语言**: Python 3.7+
- **核心依赖**:
  - [OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO) >= 0.17.0
  - [pyaaf2](https://github.com/markreidvfx/pyaaf2) >= 1.4.0
- **构建系统**: Hatchling
- **包管理**: uv (推荐) / pip

### 功能矩阵

| 功能 | 读取 | 写入 |
|------|------|------|
| 单轨道片段 | ✔ | ✔ |
| 多视频轨道 | ✔ | ✔ |
| 音频轨道/片段 | ✔ | ✔ |
| 间隙/填充 | ✔ | ✔ |
| 标记 (Markers) | ✔ | ✔ |
| 嵌套结构 | ✔ | ✔ |
| 转场 | ✔ | ✔ |
| 音视频效果 | ✖ | ✖ |
| 线性速度效果 | ✔ | ✖ |
| 复杂速度效果 | ✖ | ✖ |
| 颜色决策列表 | ✖ | ✖ |
| 图像序列引用 | ✖ | ✖ |

## 项目结构

```
otio-aaf-adapter/
├── src/otio_aaf_adapter/          # 主要源代码
│   ├── adapters/
│   │   ├── advanced_authoring_format.py  # AAF 读取适配器
│   │   └── aaf_adapter/
│   │       └── aaf_writer.py             # AAF 写入适配器
│   ├── __init__.py
│   └── plugin_manifest.json       # OTIO 插件清单
├── tests/
│   ├── test_aaf_adapter.py        # 单元测试
│   └── sample_data/               # 测试样本数据
├── docs/                          # 文档
├── .github/workflows/             # CI/CD 配置
│   ├── ci.yaml                    # 持续集成
│   └── deploy_package.yaml        # 部署流程
├── pyproject.toml                 # 项目配置和依赖
├── uv.lock                        # 锁定依赖版本
└── .flake8                        # 代码风格配置
```

## 构建和运行

### 环境设置

```bash
# 使用 uv (推荐)
uv sync

# 或使用 pip
pip install -e .
```

### 运行测试

```bash
# 运行 pytest 测试套件
pytest

# 带覆盖率测试
pytest --cov=otio_aaf_adapter
```

### 代码检查

```bash
# 运行 flake8 代码风格检查
flake8
```

### 构建分发包

```bash
# 构建 wheel 和 sdist
python -m build -s -w --outdir dist .
```

### 使用适配器

```bash
# 使用 otioconvert 转换 AAF 文件
otioconvert -i input.aaf -o output.ext

# 如果 OTIO 中仍有 contrib 版本，需要设置环境变量
export OTIO_PLUGIN_MANIFEST_PATH=/path/to/plugin_manifest.json
```

## 开发规范

### 代码风格

- **行长度**: 最大 88 字符
- **风格指南**: 遵循 PEP 8，使用 flake8 检查
- **忽略规则**:
  - W503: 二元运算符前的换行
  - W504: 二元运算符后的换行

### 测试实践

- 使用 `unittest` 框架编写测试
- 测试文件位于 `tests/` 目录
- 使用样本数据进行集成测试
- CI 在多个 Python 版本 (3.7-3.11) 和操作系统上运行测试

### CI/CD

GitHub Actions 配置了以下流程:

1. **ci.yaml**: 
   - 代码风格检查 (flake8)
   - 多平台测试 (Ubuntu, Windows, macOS)
   - 多 Python 版本测试 (3.7-3.11)
   - 多 OTIO 版本测试 (main, 0.17.0)

2. **deploy_package.yaml**:
   - 构建和发布包到 PyPI

### 贡献指南

- 所有贡献必须遵循 [OpenTimelineIO 贡献指南](https://opentimelineio.readthedocs.io/en/latest/tutorials/contributing.html)
- 通过 Pull Request 提交更改
- 为功能或 bug 创建对应的 Issue

## 许可证

本项目采用 [Apache License, Version 2.0](LICENSE.txt) 许可证。

## 支持的平台

- **操作系统**: Windows, macOS, Linux
- **Python 版本**: 3.7, 3.8, 3.9, 3.10, 3.11
- **VFX Platform**: 2020-2023

## 关键文件说明

| 文件 | 描述 |
|------|------|
| `pyproject.toml` | 项目元数据、依赖和构建配置 |
| `uv.lock` | 依赖版本锁定文件 |
| `plugin_manifest.json` | OTIO 插件注册清单 |
| `advanced_authoring_format.py` | AAF 文件读取实现 |
| `aaf_writer.py` | AAF 文件写入实现 |
| `test_aaf_adapter.py` | 完整的测试套件 (2200+ 行) |
| `.flake8` | 代码风格检查配置 |

## 常见问题

### 与 contrib 版本冲突

如果使用的 OpenTimelineIO 版本仍包含 AAF contrib adapter，需要设置 `OTIO_PLUGIN_MANIFEST_PATH` 环境变量指向本项目的 `plugin_manifest.json` 以覆盖 contrib 版本。

### 依赖问题

确保安装正确版本的依赖:
- OpenTimelineIO >= 0.17.0.dev1
- pyaaf2 >= 1.4.0
