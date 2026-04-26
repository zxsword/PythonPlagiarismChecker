# 🐍 Python 代码查重与 AI 自动批改系统

这是一个专为计算机编程教学设计的开源桌面工具，致力于帮助教师**高效排查学生作业抄袭**，并利用**大语言模型 (LLMs)** 实现作业的自动批改与代码审判。

纯AI写的。

本项目采用严格的 MVC 架构设计，支持离线运行，并完美兼容市面上所有主流的云端大模型（如 DeepSeek、Kimi、Gemini 等）。

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
   ```bash
   pip install -r requirements.txt
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

## ⚙️ 模型配置指南

在软件主界面的【⚙️ AI设置】中，你可以自由配置：
- **使用 DeepSeek**：API Base URL 填写 `https://api.deepseek.com/v1`，模型名称填写 `deepseek-chat`。
- **使用 Kimi (Moonshot)**：API Base URL 填写 `https://api.moonshot.cn/v1`，模型名称填写 `moonshot-v1-8k`。
- **使用 本地模型**：下载 `.gguf` 格式的开源模型，点击界面的导入按钮即可实现完全断网的离线批改。

## 📄 开源协议

本项目基于 MIT 协议开源。欢迎提交 Issue 和 Pull Request！