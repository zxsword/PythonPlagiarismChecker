# 🎓 Python 代码查重与 AI 自动批改系统 (Python Plagiarism Checker & Auto-Grader)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![UI: Tkinter](https://img.shields.io/badge/GUI-Tkinter-lightgrey.svg)]()
[![Local AI: GPT4All](https://img.shields.io/badge/Local%20AI-GPT4All-orange.svg)]()

这是一个专为计算机科学教师、助教和培训机构打造的**桌面级教学辅助神器**。它采用 MVC 架构，底层由纯 Python 编写，融合了**传统 AST 图论算法**与**最前沿的大语言模型 (LLM)**，旨在解决编程作业批改中的两大痛点：**防作弊查重** 与 **自动化详尽代码审查**。

完全支持 **断网离线运行**，完美保护学生代码隐私！

---

## ✨ 核心杀手锏功能

### 🔍 1. 企业级代码查重引擎 (Plagiarism Detection)
* **无惧“洗稿”的深度 AST 模式**：不仅仅是文本比对，系统会将 Python 代码解析为抽象语法树 (AST)。即使学生**疯狂修改变量名、增删空行/注释、甚至调整无关函数的顺序**，也无法逃过 AST 骨架指纹的法眼。
* **图论连通分组算法**：基于深度优先搜索 (DFS)，自动将“连环抄袭”的多名学生归为一组，并通过启发式算法（时间戳+代码体积）精准指出**谁是原创源头**。
* **IDE 级并排对比窗口**：双击即可调出多文件高亮对比窗口。支持多文本框滚轮绝对同步，提供“专业模式”与“强提醒模式”双主题。
* **🤖 一键 AI 深度审判**：查重抓到了还在狡辩“只是巧合”？在对比窗口中点击一键审判，系统会直接唤醒 AI，为你生成一份诸如“这两份代码在第10行有着完全一样且非标准的错误逻辑...”的**铁证级抄袭鉴定报告**。

### 📝 2. AI/AST 双核自动批改 (Auto-Grading)
* **瞬时 AST 静态质量打分**：无需调用 AI，利用纯粹的 Python 内置库对代码质量进行极度严苛的扣分。精准打击初学者易犯的：不规范命名、超长嵌套、滥用 `global`/`eval`、可变默认参数等坏习惯。
* **🚀 断网可用的本地大模型批改**：
  * 接入 `gpt4all` 引擎，系统内置了对 **Qwen2.5-3B**、**Qwen2.5-7B** 以及 Google 最新 **Gemma-3-4B** 端侧神级模型的完美支持。
  * 自动启用 **GPU 显存加速**，并智能回退 CPU。
  * **支持任意外部模型导入**：网上的最新 `.gguf` 量化模型，一键导入立刻使用！
* **☁️ Gemini 云端大模型批改**：支持接入 Google Gemini 官方 API，内置智能退避限流锁 (Token Bucket)，一口气丢进 500 份作业也绝不触发 429 并发报错崩溃。
* **自定义评分细则**：支持将具体的“作业要求和给分点”填入设置中，AI 将严格遵循您的教鞭进行批改。

### 📊 3. 极致的体验与报告输出
* **带 UI 响应的极速多进程/多线程并发**：无论是几千次的查重对比，还是几百次的网络请求，全部由底层并发池托管。主界面绝不卡顿，并附带秒级精准的 **ETA（预计剩余时间）** 和随时的 **[⏹ 取消任务]** 能力。
* **生成精美 HTML 网页报告**：告别干瘪的 CSV。一键导出带统计图表卡片、红绿高亮分数警告、以及 Markdown 优雅排版的单文件 HTML 报告，发送给他人只需双击浏览器即可完美阅读。
* **防风控“合并导出”功能**：在线平台限制上传文件数量？一键将上百份作业拼装成一个包含巨大醒目分隔符的 `.py` 文件。

---

## 🚀 快速上手 (Installation)

### 方法一：源码运行（适合开发者）
确保您的电脑上安装了 Python 3.8 或更高版本。

1. **克隆项目并安装依赖**
```bash
git clone https://github.com/yourusername/PythonPlagiarismChecker.git
cd PythonPlagiarismChecker
pip install -r requirements.txt
```

### 前提条件
- 需要安装 Python 3.8 或更高版本。

### 运行步骤
1. 下载或克隆本仓库到本地。
2. 双击运行目录下的 `run.bat` 文件（仅限 Windows）。
3. 或者在命令行/终端中运行以下命令：
   ```bash
   python main.py
   ```

## 📂 项目结构

- `main.py`：程序的启动入口。
- `plagiarism_checker/`：核心代码包。
  - `analysis.py`：查重算法核心（AST解析、差异比对、图论算法）。
  - `ui/app.py`：主窗口界面实现。
  - `ui/comparison_window.py`：代码对比高亮窗口实现。
- `tests/`：单元测试目录。
- `run.bat`：Windows 快速启动脚本。