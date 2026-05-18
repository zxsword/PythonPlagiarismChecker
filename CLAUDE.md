# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# python-plagiarism-checker

面向大学教师的 Python 作业查重 + 自动批改桌面工具。基于 tkinter，支持 AST 静态分析、云端大模型（Gemini/DeepSeek）和本地 GGUF 模型三种批改方式。

## 技术栈

- 语言：Python 3.8+（需要 `ast.unparse`，实际要求 3.9+）
- GUI：tkinter（标准库）
- 关键依赖：`pyyaml`（配置）、`openai`（云端 LLM）、`gpt4all`（本地 LLM，可选）
- 核心算法：`difflib.SequenceMatcher`（相似度）、`ast`（代码规范打分）、`multiprocessing`（并发加速）

## 启动

```bash
# 首次运行前：复制配置模板并填入 API Key
cp config.example.yaml config.yaml

# 安装依赖
pip install pyyaml openai

# 启动 GUI
python main.py

# 或直接双击
run.bat
```

## 运行测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行单个测试文件（对 analysis.py 的核心逻辑测试）
python tests/test_analysis.py
```

## 架构要点

### 模块分层

```
main.py                          # 入口，启动 PlagiarismCheckerApp
plagiarism_checker/
  analysis.py                    # 核心算法：代码标准化、相似度计算、图论分组、AST质量打分
  grader.py                      # AutoGrader：三种批改模式的调度器
  ai_service.py                  # 云端/本地 LLM 客户端初始化
  config.py                      # ConfigManager：config.yaml 读写
  exporter.py                    # CSV/HTML 报告导出
  file_utils.py                  # 文件合并工具
  ui/
    app.py                       # PlagiarismCheckerApp（主窗口，程序核心）
    widgets.py                   # FileSelectionFrame / TaskOptionsFrame / ResultsFrame
    comparison_window.py         # 并排差异对比窗口
    dialogs.py                   # API设置、AI详细评语、习题设置等弹窗
```

### 并发模型（关键约束）

- **分析任务**：在后台 `threading.Thread` 中调用，该线程内部再开 `multiprocessing.Pool` 做 CPU 密集型工作（AST 解析 + difflib 比对），绕过 GIL。
- **UI 线程安全**：tkinter 不是线程安全的。所有从后台线程发起的 UI 更新必须通过 `self.after(0, callback)` 派发回主线程。`app.py` 中有注释标注此约束，绝不可在子线程直接读写 tkinter 变量（包括 `tk.StringVar.get()`）。
- **进程池资源释放**：`pool.terminate() + pool.join()` 写在 `finally` 块中，确保用户点击"取消"时子进程被彻底回收。
- **`multiprocessing.freeze_support()`**：`main.py` 第一行调用，PyInstaller 打包后多进程必须。

### 查重算法流程

1. `normalize_code()`：优先用 `ast.unparse()` 去除注释和格式差异；深度模式提取 AST 节点类型序列（免疫变量重命名）；语法有误的文件回退到正则后备策略。
2. `find_suspicious_pairs()`：多进程并发标准化 → 多进程并发两两 `difflib.SequenceMatcher` 比对 → 筛选超过阈值的对。
3. `find_plagiarism_groups()`：用 DFS 找图的连通分量（互相抄袭的分组）。
4. `detect_original_source()`：基于文件修改时间（早得分高）+ 文件长度（长得分高）的启发式算法推断原创者。

### 配置文件

- `config.yaml` 在 `.gitignore` 中，不进版本控制。模板为 `config.example.yaml`。
- `ConfigManager` 在程序启动时自动加载，窗口关闭前保存（API Key、模型名称、习题描述等）。

### 本地 LLM 模型

- GGUF 模型文件存储在 `~/.cache/gpt4all/`，不放在项目目录下。
- 支持从国内镜像（hf-mirror.com）自动下载内置模型（Qwen2.5-3B/7B、Gemma-3-4B）。
- 依赖 `gpt4all` 库，仅在选择本地模型时才 `import`，未安装时会给出友好提示而不崩溃。
