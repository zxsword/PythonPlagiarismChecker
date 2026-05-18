# 🐍 Python 代码查重与 AI 自动批改系统

这是一个专为计算机编程教学设计的开源桌面工具，致力于帮助教师**高效排查学生作业抄袭**，并利用**大语言模型 (LLMs)** 实现作业的自动批改与代码审判。

本项目采用 MVC 架构设计，支持离线运行，兼容所有主流的云端大模型（DeepSeek、Kimi、Gemini 等）。

## ✨ 核心特性

### 🔍 1. 深度代码查重 (Plagiarism Detection)
- **双重分析引擎**：结合纯文本比对与 **AST (抽象语法树)** 节点提取，免疫单纯的“修改变量名”、“增删注释”等洗稿行为。
- **图形化图论分组**：自动将互相抄袭的作业归聚为一个“犯罪团伙”，并推断出谁是真正的原创者。
- **多文件高亮对比**：提供类似 VS Code 的多栏并排对比窗口，支持代码高亮与同步滚动。

### 🤖 2. AI 智能批改 (Auto Grading)
- **模型自由**：
  - **本地离线模式**：基于 `gpt4all` 在本地运行 Qwen、Gemma 等开源大模型，保护学生隐私，支持 GPU 加速。
  - **云端通用模式**：基于标准的 OpenAI API 格式接入云端大模型，支持填写 Base URL 实现 **DeepSeek** 等任意兼容模型的平滑切换。
- **防超载并发锁**：内置严格的线程排队与限流算法，有效避免批量调用 API 时触发 `429 RateLimit` 限流错误。
- **深度抄袭审判**：针对两份高度相似的代码，可一键唤醒 AI 进行深度鉴定，出具详细的“抄袭实锤报告”。

###  3. 灵活的数据导出
- 一键合并批量作业为单一文件。
- 导出纯文本 CSV 表格或精美的 **HTML 可视化分析网页报告**。

## 🚀 快速上手

### 环境要求
- Python 3.8 或更高版本
- 推荐使用虚拟环境 (`venv` 或 `conda`)

### 安装步骤

1. **克隆项目到本地**
   ```bash
   git clone https://github.com/your-username/PythonPlagiarismChecker.git
   cd PythonPlagiarismChecker
   ```

2. **安装依赖模块**

   - 仅使用查重 + 云端批改：
     ```bash
     pip install -r requirements-base.txt
     ```
   - 同时使用本地离线大模型批改（需额外下载 GGUF 模型文件，占用约 2-8 GB 磁盘）：
     ```bash
     pip install -r requirements-local.txt
     ```

3. **配置初始化**
   复制配置模板文件并重命名为 `config.yaml`（该文件已加入 `.gitignore` 以防止密钥泄露）：
   ```bash
   cp config.example.yaml config.yaml
   ```

4. **启动应用**
   ```bash
   python main.py
   ```

## 🔒 隐私与密钥

API Key 等敏感信息**不会存入 config.yaml**，单独保存在项目根目录的 `.env` 文件中（`.env` 已加入 `.gitignore`，不会被提交到 Git）。

有三种方式填入密钥（优先级由高到低）：

1. **系统环境变量**（服务器 / CI 推荐）
   ```bash
   export PLAGIARISM_API_KEY=your-api-key-here
   export PLAGIARISM_API_PROXY=http://127.0.0.1:7890  # 可选
   ```

2. **`.env` 文件**（日常使用推荐）
   ```bash
   cp .env.example .env   # 复制模板
   # 然后用文本编辑器打开 .env 填入真实值
   ```

3. **软件界面的【⚙️ AI设置】**（图形界面）：点击保存后自动写入 `.env`。

> 如果你的旧版 `config.yaml` 里还有 `api_key` 字段，程序启动时会自动将其迁移到 `.env` 并从 yaml 中删除，无需手动操作。

## ⚙️ 模型配置指南

在软件主界面的【⚙️ AI设置】中，你可以自由配置：
- **使用 DeepSeek**：API Base URL 填写 `https://api.deepseek.com/v1`，模型名称填写 `deepseek-chat`。
- **使用 Kimi (Moonshot)**：API Base URL 填写 `https://api.moonshot.cn/v1`，模型名称填写 `moonshot-v1-8k`。
- **使用 本地模型**：下载 `.gguf` 格式的开源模型，点击界面的导入按钮即可实现完全断网的离线批改。

## 🗂️ 模块结构

```
main.py                                  # 入口，调用 multiprocessing.freeze_support()
plagiarism_checker/
  analysis.py                            # 核心算法：代码标准化、相似度、图论分组
  grader.py                              # AutoGrader：三种批改模式调度（AST/云端/本地）
  ai_service.py                          # 云端/本地 LLM 客户端 + LocalModelSingleton
  prompts.py                             # 集中管理所有发给 AI 的 Prompt 模板
  config.py                              # ConfigManager：config.yaml 读写（非敏感字段）
  secrets.py                             # SecretsManager：.env 读写（API Key 等敏感字段）
  exporter.py                            # CSV/HTML 报告导出
  file_utils.py                          # 文件合并工具
  task_runner.py                         # TaskRunner：查重+批改长任务的后台调度
  log_config.py                          # 日志配置：按日轮转写入 logs/app.log
  ui/
    app.py                               # PlagiarismCheckerApp（主窗口，约 420 行）
    widgets.py                           # 三个可复用 LabelFrame 组件
    comparison_window.py                 # 并排差异对比窗口
    dialogs.py                           # API 设置、评语查看、AI 审判等弹窗
    theme.py                             # 颜色常量集中定义（PROFESSIONAL_THEME 等）
    window_utils.py                      # center_window() 工具函数
```

## 🤝 关于本项目

本项目由作者设计并持续维护，开发过程中借助了 AI 代码辅助工具（Claude Code）提升效率。所有功能设计、算法选型和教学注释均经过人工审核与迭代。

## 📄 开源协议

本项目基于 MIT 协议开源。欢迎提交 Issue 和 Pull Request！