# -*- coding: utf-8 -*-
"""
对话框模块

将主应用中弹出的各类独立配置窗口（如API设置、评分细则设置）封装成独立的类，
进一步清理 app.py 的逻辑，使其更专注于主流程控制。
"""

import tkinter as tk
from tkinter import ttk
import threading
import os
from pathlib import Path

class ApiSettingsDialog(tk.Toplevel):
    """配置云端 AI (Gemini API) 的对话框"""
    def __init__(self, parent, app_controller):
        super().__init__(parent)
        self.app = app_controller
        
        self.title("AI 模型设置 (云端与本地)")
        self.geometry("550x450")
        
        # 【教学说明】什么是模态窗口 (Modal Window)？
        # 有些弹窗打开后，你必须处理完它（比如点保存或关闭），否则底下的主窗口点不了。
        # 这种“霸道”的窗口就叫模态窗口。
        # transient(parent): 让这个弹窗依附在主窗口上，不会在任务栏出现多余的图标。
        # grab_set(): 捕获所有的鼠标和键盘事件，强制用户只能在这个弹窗里操作。
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text="请输入您的 API Key:").pack(pady=(15, 5))
        ttk.Entry(self, textvariable=self.app.api_key, width=50, show="*").pack(pady=5)
        
        ttk.Label(self, text="API Base URL (兼容OpenAI格式，如 DeepSeek 填 https://api.deepseek.com/v1):").pack(pady=(10, 5))
        ttk.Entry(self, textvariable=self.app.api_base, width=50).pack(pady=5)

        ttk.Label(self, text="模型名称 (例如 deepseek-chat 或 gemini-1.5-flash):").pack(pady=(10, 5))
        ttk.Entry(self, textvariable=self.app.api_model, width=50).pack(pady=5)

        ttk.Label(self, text="本地代理地址 (国内直连通常会失败，请填写科学上网代理)\n例如: http://127.0.0.1:7890 (留空则不使用代理):").pack(pady=(15, 5))
        ttk.Entry(self, textvariable=self.app.api_proxy, width=50).pack(pady=5)
        
        # --- 新增：本地大模型设置 ---
        local_frame = ttk.LabelFrame(self, text="本地大模型设置 (离线)", padding=10)
        local_frame.pack(fill=tk.X, padx=15, pady=(20, 5))

        ttk.Label(local_frame, text="选择或输入本地模型 (.gguf):").pack(anchor=tk.W)
        combo_frame = ttk.Frame(local_frame)
        combo_frame.pack(fill=tk.X, pady=5)

        model_combo = ttk.Combobox(combo_frame, textvariable=self.app.local_model, width=45)
        model_combo['values'] = [
            "qwen2.5-3b-instruct-q4_k_m.gguf",
            "qwen2.5-7b-instruct-q4_k_m.gguf",
            "gemma-3-4b-it-q4_k_m.gguf"
        ]
        model_combo.pack(side=tk.LEFT)
        ttk.Button(combo_frame, text="📁 导入本地模型", command=self.app.import_local_model).pack(side=tk.RIGHT)

        ttk.Button(self, text="保存并关闭", command=self.save_and_close).pack(pady=15)
        
        # 等待窗口关闭
        self.wait_window(self)

    def save_and_close(self):
        self.app.save_config()
        self.app.status_text.set("API 配置已保存。")
        self.destroy()

class ExerciseDialog(tk.Toplevel):
    """设置习题要求与评分细则的对话框"""
    def __init__(self, parent, app_controller):
        super().__init__(parent)
        self.app = app_controller
        
        self.title("自定义作业要求与评分细则")
        self.geometry("600x450")
        
        self.transient(parent)
        self.grab_set()
        
        ttk.Label(self, text="请分条填入本次作业的具体要求和评分细则（AI 将按此进行语义理解和严厉扣分）：\n例如：1. 必须使用 for 循环 (未用扣20分)；2. 变量命名必须见名知意 (乱写扣10分)", padding=10).pack(fill=tk.X)
        
        # 优先把按钮停靠在底部，防止被中间会膨胀的文本框挤出边界
        ttk.Button(self, text="保存并关闭", command=self.save_and_close).pack(side=tk.BOTTOM, pady=10)
        
        # 创建一个 Frame 容器来同时装下文本框和滚动条
        text_frame = ttk.Frame(self)
        text_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("微软雅黑", 10), padx=10, pady=10)
        scroll_y = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_widget.yview)
        self.text_widget.config(yscrollcommand=scroll_y.set)
        
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_widget.insert(tk.END, self.app.exercise_text)
        
        self.wait_window(self)

    def save_and_close(self):
        self.app.exercise_text = self.text_widget.get("1.0", tk.END).strip()
        self.app.save_config()
        self.app.status_text.set("已更新自定义评分细则。")
        self.destroy()

class AiReviewDialog(tk.Toplevel):
    """查看AI详细评语与源代码对照的窗口"""
    def __init__(self, parent, name, score, method, review, source_code, exercise_text):
        super().__init__(parent)
        self.title(f"对照批改报告 - {name}")
        self.geometry("1100x650")
        
        # 使用 PanedWindow 实现左右分屏拖拽
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧：源代码区
        code_frame = ttk.LabelFrame(paned, text="源代码")
        
        # 增加独立的行号文本框
        line_widget = tk.Text(code_frame, width=5, padx=3, takefocus=0, border=0, background="#f0f0f0", state=tk.NORMAL, font=("Courier New", 11), wrap=tk.NONE)
        line_widget.pack(side=tk.LEFT, fill=tk.Y)
        
        code_text = tk.Text(code_frame, wrap=tk.NONE, font=("Courier New", 11), bg="#f8f8f8")
        
        # 同步滚动机制
        code_scroll_y = ttk.Scrollbar(code_frame, orient=tk.VERTICAL)
        code_scroll_x = ttk.Scrollbar(code_frame, orient=tk.HORIZONTAL, command=code_text.xview)
        
        # 【教学说明】多个文本框的同步滚动技巧
        # 我们有两个 Text 控件：一个是单纯显示 1,2,3 的行号框，一个是显示代码的框。
        # 当用户拉动滚动条时，必须让这两个框同时上下移动，否则行号就错位了。
        def sync_line_and_scroll(*args):
            # args 通常包含 ('moveto', '0.5') 这种滚动位置信息
            # 让滚动条移动
            code_scroll_y.set(*args)
            # 强制让行号框也移动到相同的比例位置
            line_widget.yview_moveto(args[0])
            
        def on_scrollbar_scroll(*args):
            code_text.yview(*args)
            line_widget.yview(*args)
            
        def on_mouse_wheel(event):
            scroll_units = -1 * (event.delta // 120)
            code_text.yview_scroll(scroll_units, "units")
            line_widget.yview_scroll(scroll_units, "units")
            return "break"
            
        code_text.config(yscrollcommand=sync_line_and_scroll, xscrollcommand=code_scroll_x.set)
        code_scroll_y.config(command=on_scrollbar_scroll)
        code_text.bind("<MouseWheel>", on_mouse_wheel)
        line_widget.bind("<MouseWheel>", on_mouse_wheel)
        
        code_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        code_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        code_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        code_text.insert(tk.END, source_code)
        code_text.config(state=tk.DISABLED)
        
        # 填入具体的行号数字
        lines = source_code.split('\n')
        for line_num in range(1, len(lines) + 1):
            line_widget.insert(tk.END, f"{line_num}\n")
        line_widget.config(state=tk.DISABLED)
        
        paned.add(code_frame, weight=1)
        
        # 右侧：评语区
        review_frame = ttk.LabelFrame(paned, text="详细评语")
        review_text = tk.Text(review_frame, wrap=tk.WORD, font=("微软雅黑", 11), bg="#ffffff")
        review_scroll_y = ttk.Scrollbar(review_frame, orient=tk.VERTICAL, command=review_text.yview)
        review_text.config(yscrollcommand=review_scroll_y.set)
        review_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        review_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        display_text = f"【批改模式】: {method}\n【最终得分】: {score} 分\n"
        if exercise_text:
            display_text += "\n【应用规则】:\n" + exercise_text + "\n"
        display_text += "="*40 + f"\n\n{review}"
        
        review_text.insert(tk.END, display_text)
        review_text.config(state=tk.DISABLED)
        paned.add(review_frame, weight=1)

class SourceCodeDialog(tk.Toplevel):
    """快速查看原始源代码的独立窗口"""
    def __init__(self, parent, name, code):
        super().__init__(parent)
        self.title(f"查看源代码 - {name}")
        self.geometry("800x600")
        
        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(frame, wrap=tk.NONE, font=("Courier New", 11), bg="#fdfdfd", padx=10, pady=10)
        scroll_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
        scroll_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=text_widget.xview)
        text_widget.config(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        text_widget.insert(tk.END, code)
        text_widget.config(state=tk.DISABLED)

class AiJudgementDialog(tk.Toplevel):
    """AI 深度审判窗口：分析两份代码的具体抄袭手段"""
    def __init__(self, parent, app_controller, code_a, code_b, name_a, name_b):
        super().__init__(parent)
        self.app = app_controller
        self.code_a = code_a
        self.code_b = code_b
        self.name_a = name_a
        self.name_b = name_b
        
        self.title("🤖 AI 深度抄袭鉴定报告")
        self.geometry("850x650")
        self.transient(parent)
        self.grab_set()
        
        self.info_var = tk.StringVar(value="正在打包代码并唤醒 AI 模型，请稍候...")
        ttk.Label(self, textvariable=self.info_var, font=("微软雅黑", 10, "bold")).pack(pady=15)
        
        self.progress = ttk.Progressbar(self, mode='indeterminate')
        self.progress.pack(fill=tk.X, padx=20)
        self.progress.start()

        self.btn_frame = ttk.Frame(self)
        self.btn_frame.pack(side=tk.BOTTOM, pady=10)

        text_frame = ttk.Frame(self)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
        
        self.text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("微软雅黑", 11), bg="#fdfdfd")
        scroll_y = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_widget.yview)
        self.text_widget.config(yscrollcommand=scroll_y.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        threading.Thread(target=self._run_analysis, daemon=True).start()
        
    def _run_analysis(self):
        prompt = f"""你是一个资深的计算机科学教授和极具洞察力的代码查重专家。
请对以下两份初学者的 Python 代码进行深度对比分析，判断它们是否存在互相抄袭的行为。
请重点分析并分条指出：
1. 核心逻辑、算法流程以及特殊数值是否高度一致？
2. 是否存在为了掩人耳目而故意修改变量名、调换无关语句顺序、增删无用代码或注释的“洗稿”行为？
3. 给出你的最终鉴定结论（例如：高度疑似抄袭 / 仅仅是思路相似的独立完成）。

【代码 A ({self.name_a})】：\n```python\n{self.code_a}\n```\n
【代码 B ({self.name_b})】：\n```python\n{self.code_b}\n```"""
        try:
            method = self.app.grading_method.get()
            if "本地" in method:
                self.after(0, lambda: self.info_var.set("正在加载本地大模型进行深度分析 (可能需要十几秒)..."))
                from gpt4all import GPT4All
                cache_dir = os.path.join(Path.home(), ".cache", "gpt4all")
                model_name = self.app.local_model.get() or "qwen2.5-3b-instruct-q4_k_m.gguf"
                model = GPT4All(model_name, model_path=cache_dir, allow_download=False, device='gpu')
                with model.chat_session():
                    reply = model.generate(prompt, max_tokens=1024, temp=0.3)
            else:
                self.after(0, lambda: self.info_var.set("正在连接云端大模型进行深度分析..."))
                import openai
                if not self.app.api_key.get(): raise Exception("未填写 API Key，请先在主界面【⚙️ AI设置】中配置。")
                if self.app.api_proxy.get():
                    for p in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']: os.environ[p] = self.app.api_proxy.get()
                
                client_kwargs = {"api_key": self.app.api_key.get()}
                if self.app.api_base.get().strip():
                    client_kwargs["base_url"] = self.app.api_base.get().strip()
                
                client = openai.OpenAI(**client_kwargs)
                response = client.chat.completions.create(
                    model=self.app.api_model.get() or 'gemini-1.5-flash',
                    messages=[{"role": "user", "content": prompt}]
                )
                reply = response.choices[0].message.content
                
            self.after(0, self._render_ui, reply)
        except Exception as e:
            self.after(0, self._render_ui, f"分析失败:\n{str(e)}")
            
    def _render_ui(self, result_text):
        self.progress.stop()
        self.progress.pack_forget()
        self.info_var.set("✅ AI 鉴定分析完成！")
        self.text_widget.insert(tk.END, result_text)
        self.text_widget.config(state=tk.DISABLED)
        ttk.Button(self.btn_frame, text="我知道了，关闭报告", command=self.destroy).pack()