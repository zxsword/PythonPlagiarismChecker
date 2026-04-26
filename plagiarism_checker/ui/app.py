# -*- coding: utf-8 -*-
"""
主应用程序界面模块

这个文件定义了应用程序的主窗口 `PlagiarismCheckerApp`，它是程序的核心UI。
它负责：
1. 构建和布局所有用户能看到的窗口、按钮、滑块等控件。
2. 处理用户的交互，例如点击按钮、选择文件等。
3. 调用 `analysis` 模块执行实际的分析任务。
4. 显示分析结果，并允许用户启动对比窗口。
"""

import tkinter as tk
from tkinter import filedialog, ttk
import os
import time
import threading
import shutil
from pathlib import Path
# 使用相对路径从同一目录下的 `comparison_window` 模块导入 `ComparisonWindow` 类
from .comparison_window import ComparisonWindow
# 使用相对路径从父目录的 `analysis` 模块导入需要的函数
from ..analysis import find_suspicious_pairs, find_plagiarism_groups, detect_original_source
from ..grader import AutoGrader
from .widgets import FileSelectionFrame, TaskOptionsFrame, ResultsFrame
from .dialogs import ApiSettingsDialog, ExerciseDialog, AiReviewDialog, SourceCodeDialog
from ..exporter import export_csv_report, export_html_report
from ..config import ConfigManager
from ..file_utils import merge_files

class PlagiarismCheckerApp(tk.Tk):
    """
    主应用类，继承自 tkinter 的根窗口 `tk.Tk`。
    """
    def __init__(self):
        """
        初始化主应用程序窗口。
        """
        super().__init__()
        self.title("Python代码相似度检查工具")
        self.geometry("800x600")

        self._init_data_vars()
        self._init_ui()
        self._init_menus()

    def _init_data_vars(self):
        """初始化所有用于存储程序状态的变量。"""

        # --- 数据变量 ---
        # 这些是用来存储程序状态的变量
        self.selected_files = []  # 存储所有待检查的文件路径
        self.threshold = tk.DoubleVar(value=85.0)  # 存储相似度阈值
        self.recursive_search = tk.BooleanVar(value=False) # 存储是否包含子文件夹
        self.advanced_mode = tk.BooleanVar(value=False) # 存储是否启用深度查重（无视变量重命名），默认为False
        self.enable_plag = tk.BooleanVar(value=True)  # 是否启用抄袭检测
        self.enable_grading = tk.BooleanVar(value=False)   # 是否启用自动批改
        self.grading_method = tk.StringVar(value="AST 静态质量打分") # 批改方式
        self.suspicious_pairs_map = {}  # 用于存储结果表格项和文件路径的映射
        self.require_suggestions = tk.BooleanVar(value=True) # 是否要求AI给出修改建议
        self.ai_results_map = {}  # 存储AI评语映射
        self.exercise_text = ""  # 存储习题/作业要求
        self.api_key = tk.StringVar(value="") # 存储 Gemini API Key
        self.api_base = tk.StringVar(value="") # 存储 API Base URL (用于支持 DeepSeek 等)
        self.api_proxy = tk.StringVar(value="") # 存储代理地址
        self.api_model = tk.StringVar(value="gemini-1.5-flash") # 存储 Gemini 模型名称
        self.local_model = tk.StringVar(value="qwen2.5-3b-instruct-q4_k_m.gguf") # 存储本地模型名称
        self.status_text = tk.StringVar(value="欢迎使用！请添加要检查的代码或文本文件。")  # 用于在状态栏显示信息
        self.is_running = False  # 防止重复点击运行按钮的并发锁
        self.time_text = tk.StringVar(value="耗时: 00:00") # 存储耗时文字
        self.start_time = 0.0 # 记录任务开始的时间戳
        self.cancel_event = threading.Event() # 取消任务的全局标记锁
        self.config_manager = ConfigManager() # 实例化配置管理器
        self.load_config() # 启动时自动加载本地配置
        
        # 将需要在其他模块中引用的UI组件也在此处声明
        self.file_listbox = None
        self.notebook = None
        self.tab_plag = None
        self.result_tree = None
        self.tab_ai = None
        self.ai_tree = None
        self.progress = None

    def _init_ui(self):
        """初始化主窗口的用户界面布局。"""

        # --- 主布局 ---
        # 我们将UI划分为顶部控制区、中间结果区和底部状态栏
        # ⚠️ 优先把固定在底部的组件 pack()，防止窗口缩小时被中间具有 expand=True 的控件挤出屏幕边界
        status_frame = ttk.Frame(self, relief=tk.SUNKEN, padding=2)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        status_label = ttk.Label(status_frame, textvariable=self.status_text, padding=3)
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        time_label = ttk.Label(status_frame, textvariable=self.time_text, padding=3, foreground="#555555")
        time_label.pack(side=tk.RIGHT, padx=10)

        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(fill=tk.X)

        self.file_frame = FileSelectionFrame(top_frame, self)
        self.file_frame.pack(fill=tk.X)
        TaskOptionsFrame(top_frame, self).pack(fill=tk.X, pady=10)
        ResultsFrame(self, self).pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
    def _init_menus(self):
        """初始化右键上下文菜单。"""
        # --- 创建右键菜单 ---
        self.plag_menu = tk.Menu(self, tearoff=0)
        self.plag_menu.add_command(label="对比选中的抄袭文件", command=self.show_comparison)

        self.ai_menu = tk.Menu(self, tearoff=0)
        self.ai_menu.add_command(label="查看详细批改评语", command=self.show_ai_review)
        self.ai_menu.add_command(label="📄 查看原始源代码", command=self.show_source_code)

    def load_config(self):
        """从本地文件加载配置信息"""
        config = self.config_manager.load()
        self.api_key.set(config.get('api_key', ''))
        self.api_base.set(config.get('api_base', ''))
        self.api_proxy.set(config.get('api_proxy', ''))
        self.api_model.set(config.get('api_model', 'gemini-1.5-flash'))
        self.local_model.set(config.get('local_model', 'qwen2.5-3b-instruct-q4_k_m.gguf'))
        self.exercise_text = config.get('exercise_text', '')
                
    def save_config(self):
        """将配置信息保存到本地文件"""
        config = {
            'api_key': self.api_key.get(),
            'api_base': self.api_base.get(),
            'api_proxy': self.api_proxy.get(),
            'api_model': self.api_model.get(),
            'local_model': self.local_model.get(),
            'exercise_text': self.exercise_text
        }
        self.config_manager.save(config)

    def cancel_check(self):
        """响应用户点击停止按钮"""
        if self.is_running:
            self.cancel_event.set()
            self.status_text.set("正在安全中止任务，请稍候...")
            self.cancel_btn.config(state=tk.DISABLED)

    def import_local_model(self):
        """选择外部 .gguf 模型文件并复制到程序缓存目录中"""
        file_path = filedialog.askopenfilename(title="选择本地 GGUF 模型", filetypes=[("GGUF 模型文件", "*.gguf")])
        if file_path:
            try:
                cache_dir = os.path.join(Path.home(), ".cache", "gpt4all")
                os.makedirs(cache_dir, exist_ok=True)
                model_name = os.path.basename(file_path)
                dest_path = os.path.join(cache_dir, model_name)
                
                if not os.path.exists(dest_path):
                    self.status_text.set(f"正在复制模型文件到缓存目录，可能需要几分钟，请稍候...")
                    self.update() # 强制刷新 UI，显示提示
                    shutil.copy2(file_path, dest_path)
                    
                self.local_model.set(model_name)
                self.save_config()
                self.status_text.set(f"成功导入并选中本地模型: {model_name}")
            except Exception as e:
                self.status_text.set(f"导入模型失败: {e}")

    def open_api_dialog(self):
        """打开设置 AI 的独立窗口"""
        ApiSettingsDialog(self, self)

    def open_exercise_dialog(self):
        """打开设置习题要求的独立窗口"""
        ExerciseDialog(self, self)

    def select_directory(self):
        """弹出对话框让用户选择一个文件夹，并将其中的代码/文本文件加入列表。"""
        path = filedialog.askdirectory(title="选择包含代码文件的文件夹")
        if path:
            found_files = []
            if self.recursive_search.get():
                for root, dirs, files in os.walk(path):
                    for f in files:
                        if f.lower().endswith(('.py', '.txt')):
                            found_files.append(os.path.join(root, f))
            else:
                for f in os.listdir(path):
                    if f.lower().endswith(('.py', '.txt')):
                        full_path = os.path.join(path, f)
                        if os.path.isfile(full_path):
                            found_files.append(full_path)
                            
            if found_files:
                self.selected_files.extend(found_files)
                self.selected_files = sorted(list(set(self.selected_files)))
                self.update_file_listbox()
                self.status_text.set(f"从文件夹添加了 {len(found_files)} 个文件。当前共 {len(self.selected_files)} 个。")
            else:
                self.status_text.set("选中的文件夹中没有找到 .py 或 .txt 文件。")

    def select_files(self):
        """弹出对话框让用户选择一个或多个代码文件。"""
        files = filedialog.askopenfilenames(title="选择代码或文本文件", filetypes=[("代码与文本文件", "*.py *.txt"), ("所有文件", "*.*")])
        if files:
            self.selected_files.extend(files)
            # 去重并排序
            self.selected_files = sorted(list(set(self.selected_files)))
            self.update_file_listbox()
            self.status_text.set(f"已添加 {len(files)} 个文件。当前共 {len(self.selected_files)} 个。")

    def clear_files(self):
        """清空已选文件列表。"""
        self.selected_files.clear()
        self.update_file_listbox()
        self.status_text.set("文件列表已清空。")

    def update_file_listbox(self):
        """更新文件列表框中显示的内容。"""
        self.file_listbox.delete(0, tk.END) # 先清空
        for f in self.selected_files:
            self.file_listbox.insert(tk.END, os.path.basename(f)) # 只显示文件名，不显示完整路径
        # 动态更新面板标题以显示已添加的文件数量
        if hasattr(self, 'file_frame'):
            self.file_frame.config(text=f"选择待检查的代码 (当前共 {len(self.selected_files)} 份)")

    def merge_and_export_files(self):
        """将列表中所有选中的文件合并为一个大文件并导出。"""
        if not self.selected_files:
            self.status_text.set("合并失败: 列表中没有待处理的文件。")
            return

        save_path = filedialog.asksaveasfilename(
            title="保存合并后的文件",
            defaultextension=".py",
            filetypes=[("Python代码", "*.py"), ("普通文本", "*.txt"), ("所有文件", "*.*")]
        )

        if not save_path:
            return

        try:
            count = merge_files(self.selected_files, save_path)
            self.status_text.set(f"合并完成！已将 {count} 份作业合并保存至: {save_path}")
        except Exception as e:
            self.status_text.set(f"合并导出失败: {str(e)}")

    def _add_single_ai_result(self, file_path, score, method, status, review, is_error=False, custom_name=None):
        """实时将单条批改结果插入到表格中，提供即时视觉反馈"""
        name = custom_name if custom_name else os.path.basename(file_path)
        tags = ('evenrow' if len(self.ai_tree.get_children()) % 2 == 0 else 'oddrow',)
        tags = tags + (('error',) if is_error else ('success',))
        item_id = self.ai_tree.insert('', tk.END, values=(name, score, status), tags=tags)
        self.ai_results_map[item_id] = (name, score, method, review)
        self.notebook.select(self.tab_ai) # 自动切换到AI标签页展示进度
        self.ai_tree.yview_moveto(1) # 滚动到最底部

    def clear_results(self):
        """清空结果表格和相关的映射数据。"""
        self.suspicious_pairs_map.clear()
        for i in self.result_tree.get_children():
            self.result_tree.delete(i)
            
        if hasattr(self, 'ai_results_map'):
            self.ai_results_map.clear()
        if hasattr(self, 'ai_tree'):
            for i in self.ai_tree.get_children():
                self.ai_tree.delete(i)
                
    def _update_timer(self):
        """递归更新耗时秒表"""
        if getattr(self, 'is_running', False):
            elapsed = int(time.time() - self.start_time)
            m, s = divmod(elapsed, 60)
            self.time_text.set(f"耗时: {m:02d}:{s:02d}")
            self.after(1000, self._update_timer)

    def run_check(self):
        """“开始运行”按钮的核心执行函数。"""
        if getattr(self, 'is_running', False):
            self.status_text.set("任务正在运行中，请勿重复点击，请耐心等待...")
            return
            
        self.is_running = True
        self.cancel_event.clear()
        if hasattr(self, 'start_btn'): self.start_btn.config(state=tk.DISABLED)
        if hasattr(self, 'cancel_btn'): self.cancel_btn.config(state=tk.NORMAL)
        self.start_time = time.time()
        self.time_text.set("耗时: 00:00")
        self._update_timer()  # 启动秒表
        self.clear_results()
        
        # 准备待检查的文件列表
        if not self.selected_files:
            self.status_text.set("错误: 请先添加需要检查的代码文件。")
            self.is_running = False
            return
            
        files_to_check = self.selected_files
        
        run_plag = self.enable_plag.get()
        run_grading = self.enable_grading.get()
        grading_method = self.grading_method.get()
        
        if not run_plag and not run_grading:
            self.status_text.set("错误: 请至少勾选一项运行任务。")
            self.is_running = False
            return
            
        if run_plag and len(files_to_check) < 2:
            self.status_text.set("错误: 抄袭检测至少需要两个代码文件。")
            self.is_running = False
            return
            
        self.status_text.set("正在初始化任务...")
        if run_grading:
            self.progress.config(mode='determinate', maximum=len(files_to_check), value=0)
        else:
            self.progress.config(mode='indeterminate')
        self.progress.pack(side=tk.RIGHT, padx=10)
        if not run_grading:
            self.progress.start()
        self.update_idletasks()
        
        threshold_ratio = self.threshold.get() / 100.0
        is_advanced = self.advanced_mode.get()
        
        # ⚠️ 修复严重隐患：必须在主线程提取所有 Tkinter 变量的值
        # 否则在后台线程调用 .get() 会引发底层的 Tcl 解释器死锁，导致后台静默崩溃
        req_sugg_val = self.require_suggestions.get()
        key_val = self.api_key.get().strip()
        base_val = self.api_base.get().strip()
        model_val = self.api_model.get().strip()
        local_val = self.local_model.get().strip()
        proxy_val = self.api_proxy.get().strip()
        
        def combined_task():
            try:
                suspicious_pairs = []
                errors = {}

                # --- 1. 抄袭检测 ---
                if run_plag:
                    def plag_prog(c, t, stage):
                        if stage == "标准化":
                            self.after(0, lambda: self.status_text.set(f"正在预处理文件... {c}/{t}"))
                        else:
                            self.after(0, lambda: self.status_text.set(f"正在进行多进程查重比对... {c}/{t}"))
                            
                    suspicious_pairs, errors = find_suspicious_pairs(files_to_check, threshold_ratio, is_advanced, plag_prog, self.cancel_event)

                # --- 2. 自动批改 ---
                if run_grading and not self.cancel_event.is_set():
                    graded_count = [0]  # 使用列表形式存储，以便在闭包函数内可修改
                    total_files = len(files_to_check)
                    
                    def status_cb(msg):
                        # 在底层传来的状态信息后面拼接具体进度数字
                        self.after(0, self.status_text.set, f"{msg} ({graded_count[0]}/{total_files})")
                        
                    def progress_cb():
                        graded_count[0] += 1
                        self.after(0, self.progress.step)
                        self.after(0, self.status_text.set, f"当前批改进度... ({graded_count[0]}/{total_files})")
                        
                    def result_cb(file_path, score, method, status, review, is_error):
                        if file_path == "ALL":
                            self.after(0, self._add_single_ai_result, "", score, method, status, review, True, "系统环境错误")
                        else:
                            self.after(0, self._add_single_ai_result, file_path, score, method, status, review, is_error)

                    grader = AutoGrader(
                        grading_method=grading_method,
                        files_to_check=files_to_check,
                        exercise_text=self.exercise_text,
                        require_suggestions=req_sugg_val,
                        api_key=key_val,
                        api_base=base_val,
                        api_model=model_val,
                        local_model=local_val,
                        api_proxy=proxy_val,
                        status_cb=status_cb,
                        progress_cb=progress_cb,
                        result_cb=result_cb,
                        cancel_event=self.cancel_event
                    )
                    grader.run()

                # 执行完毕，安全通知主线程更新UI
                self.after(0, self._update_ui_after_task, run_plag, run_grading, suspicious_pairs, errors)
                
            except Exception as e:
                # 防止后台线程“静默死亡”，把所有报错推到前台状态栏
                self.after(0, self.status_text.set, f"发生致命后台崩溃: {str(e)}")
                self.after(0, self.progress.stop)
                self.after(0, self.progress.pack_forget)
                self.is_running = False
            
        threading.Thread(target=combined_task, daemon=True).start()

    def _update_ui_after_task(self, run_plag, run_grading, suspicious_pairs, errors):
        self.progress.stop()
        self.progress.pack_forget()
        self.is_running = False
        if hasattr(self, 'start_btn'): self.start_btn.config(state=tk.NORMAL)
        if hasattr(self, 'cancel_btn'): self.cancel_btn.config(state=tk.DISABLED)

        # --- 1. 更新查重结果 ---
        if run_plag:
            if suspicious_pairs:
                groups = find_plagiarism_groups(suspicious_pairs)
                if groups:
                    for group, max_sim in groups:
                        original_file, scores = detect_original_source(group)
                        original_name = os.path.basename(original_file) if original_file else "未知"
                        members = ", ".join([os.path.basename(f) for f in group])
                        sim_str = f"{max_sim * 100:.1f}%"
                        
                        tags = ('evenrow' if len(self.result_tree.get_children()) % 2 == 0 else 'oddrow',)
                        if max_sim >= 0.90:
                            tags = tags + ('high_risk',)
                            
                        item_id = self.result_tree.insert('', tk.END, values=(len(group), sim_str, original_name, members), tags=tags)
                        self.suspicious_pairs_map[item_id] = (group, original_file)
            
            # 如果检测完毕后，表格里没有任何数据（即没找到互相抄袭的文件）
            if not self.result_tree.get_children() and not self.cancel_event.is_set():
                threshold_str = f"{self.threshold.get()}%"
                self.result_tree.insert('', tk.END, values=("-", "-", "太棒了！未发现抄袭", f"所有文件的相似度均低于设定阈值 ({threshold_str})"), tags=('success',))
            self.notebook.select(self.tab_plag)

        # --- 2. 更新状态栏 ---
        status_msg = "任务已中止。" if self.cancel_event.is_set() else "运行结束。"
        if run_plag:
            status_msg += f" 发现 {len(self.result_tree.get_children())} 组疑似抄袭。"
        if run_grading:
            status_msg += " 自动批改已完成。"
        self.status_text.set(status_msg)

    def show_comparison(self):
        selected_items = self.result_tree.selection()
        if not selected_items:
            self.status_text.set("请先在【抄袭检测结果】标签中选择一组代码。")
            return
        
        item_id = selected_items[0]
        group_files, original_file = self.suspicious_pairs_map[item_id]
        ComparisonWindow(self, group_files, original_file)

    def export_report(self):
        """动态导出报告：当前在哪个标签页，就导出哪份报告"""
        current_tab = self.notebook.index(self.notebook.select())
        tree_to_export = self.result_tree if current_tab == 0 else self.ai_tree
        
        if not tree_to_export.get_children():
            self.status_text.set("没有可导出的结果。")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML 网页报告 (推荐)", "*.html"), ("CSV 表格文件", "*.csv")],
            title="保存分析报告"
        )
        if not file_path:
            return
            
        try:
            if file_path.endswith('.html'):
                export_html_report(file_path, current_tab, tree_to_export, self.ai_results_map)
            else:
                export_csv_report(file_path, current_tab, tree_to_export, self.ai_results_map)
            self.status_text.set(f"报告已成功导出到: {file_path}")
        except Exception as e:
            self.status_text.set(f"导出报告失败: {str(e)}")

    def show_ai_review(self):
        """弹出独立窗口查看选中的AI详细评语"""
        selected_items = self.ai_tree.selection()
        if not selected_items:
            self.status_text.set("请先在【自动批改结果】标签中选择一个文件。")
            return
            
        item_id = selected_items[0]
        name, score, method, review = self.ai_results_map.get(item_id, ("", "-", "", ""))
        if not review:
            return

        # 获取源代码内容
        file_path = next((f for f in self.selected_files if os.path.basename(f) == name), None)
        source_code = ""
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    source_code = f.read()
            except Exception:
                source_code = "无法加载源代码。"

        AiReviewDialog(self, name, score, method, review, source_code, self.exercise_text)

    def popup_plag_menu(self, event):
        """弹出查重结果的右键菜单"""
        item = self.result_tree.identify_row(event.y)
        if item:
            self.result_tree.selection_set(item)  # 强制选中鼠标悬停的行
            self.plag_menu.post(event.x_root, event.y_root)

    def popup_ai_menu(self, event):
        """弹出AI批改结果的右键菜单"""
        item = self.ai_tree.identify_row(event.y)
        if item:
            self.ai_tree.selection_set(item)      # 强制选中鼠标悬停的行
            self.ai_menu.post(event.x_root, event.y_root)
            
    def show_source_code(self):
        """在独立窗口中快速查看原始源代码"""
        selected_items = self.ai_tree.selection()
        if not selected_items:
            return
            
        item_id = selected_items[0]
        name, _, _, _ = self.ai_results_map.get(item_id, ("", "-", "", ""))
        if not name: 
            return
        
        # 通过文件名反查完整文件路径
        file_path = next((f for f in self.selected_files if os.path.basename(f) == name), None)
        if not file_path: 
            return

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
        except Exception as e:
            code = f"读取文件失败: {e}"

        SourceCodeDialog(self, name, code)
