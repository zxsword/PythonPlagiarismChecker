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
import shutil
from pathlib import Path
from .comparison_window import ComparisonWindow
from .widgets import FileSelectionFrame, TaskOptionsFrame, ResultsFrame
from .dialogs import ApiSettingsDialog, ExerciseDialog, AiReviewDialog, SourceCodeDialog
from .theme import PROFESSIONAL_THEME as PRO
from ..exporter import export_csv_report, export_html_report
from ..config import ConfigManager
from ..secrets import SecretsManager
from ..file_utils import merge_files
from ..task_runner import TaskRunner

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
        # 关闭窗口时自动保存，而不是直接销毁
        self.protocol("WM_DELETE_WINDOW", self._on_close)

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
        # 云端 API 两次请求之间的最小间隔（秒）。仅通过 config.yaml 调整，目前不在 UI 暴露。
        self.api_min_interval = 5.0
        self.status_text = tk.StringVar(value="欢迎使用！请添加要检查的代码或文本文件。")  # 用于在状态栏显示信息
        self.time_text = tk.StringVar(value="耗时: 00:00") # 存储耗时文字
        # is_running / cancel_event / start_time 由 TaskRunner 持有，不再挂在 self 上
        self.task_runner = TaskRunner(self)
        self.secrets_manager = SecretsManager()  # 优先初始化，load_config 会用到
        self.config_manager = ConfigManager()
        self.load_config()  # 启动时自动加载配置（含旧版自动迁移）

        # 关键 UI 控件不在这里占位；统一在 _init_ui 里从各 widgets 实例读回赋值，
        # 这样 Ctrl+F 搜 self.file_listbox 等就能直接命中唯一定义点。

    def _init_ui(self):
        """初始化主窗口的用户界面布局。"""

        # --- 主布局 ---
        # 我们将UI划分为顶部控制区、中间结果区和底部状态栏
        # ⚠️ 优先把固定在底部的组件 pack()，防止窗口缩小时被中间具有 expand=True 的控件挤出屏幕边界
        status_frame = ttk.Frame(self, relief=tk.SUNKEN, padding=2)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        status_label = ttk.Label(status_frame, textvariable=self.status_text, padding=3)
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        time_label = ttk.Label(status_frame, textvariable=self.time_text, padding=3, foreground=PRO['text_secondary'])
        time_label.pack(side=tk.RIGHT, padx=10)

        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(fill=tk.X)

        # 各 widgets 把内部控件挂在自身上；这里读回赋给 self，作为这些控件
        # 在 app.py 中的唯一定义点（Ctrl+F 可定位）。
        self.file_frame = FileSelectionFrame(top_frame, self)
        self.file_frame.pack(fill=tk.X)
        self.file_listbox = self.file_frame.file_listbox

        self.task_frame = TaskOptionsFrame(top_frame, self)
        self.task_frame.pack(fill=tk.X, pady=10)
        self.start_btn = self.task_frame.start_btn
        self.cancel_btn = self.task_frame.cancel_btn

        self.results_frame = ResultsFrame(self, self)
        self.results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.notebook = self.results_frame.notebook
        self.tab_plag = self.results_frame.tab_plag
        self.tab_ai = self.results_frame.tab_ai
        self.result_tree = self.results_frame.result_tree
        self.ai_tree = self.results_frame.ai_tree
        self.progress = self.results_frame.progress
        
    def _init_menus(self):
        """初始化右键上下文菜单。"""
        # --- 创建右键菜单 ---
        self.plag_menu = tk.Menu(self, tearoff=0)
        self.plag_menu.add_command(label="对比选中的抄袭文件", command=self.show_comparison)

        self.ai_menu = tk.Menu(self, tearoff=0)
        self.ai_menu.add_command(label="查看详细批改评语", command=self.show_ai_review)
        self.ai_menu.add_command(label="📄 查看原始源代码", command=self.show_source_code)

    def load_config(self):
        """从本地文件加载全部配置（含旧版敏感字段自动迁移）。"""
        config = self.config_manager.load()

        # 检测并迁移旧 config.yaml 中遗留的 api_key/api_proxy
        config, migrated = self.secrets_manager.migrate_from_config(config)
        if migrated:
            self.config_manager.save(config)
            self.status_text.set(
                "✅ 已自动将 API Key 迁移到 .env 文件（不会进 Git），config.yaml 已清理。"
            )

        # --- 非敏感字段从 config.yaml 读取 ---
        self.api_base.set(config.get('api_base', ''))
        self.api_model.set(config.get('api_model', 'gemini-1.5-flash'))
        self.local_model.set(config.get('local_model', 'qwen2.5-3b-instruct-q4_k_m.gguf'))
        # 容错：用户可能填了字符串或非法值，转不动就退回 5.0
        try:
            self.api_min_interval = float(config.get('api_min_interval', 5.0))
        except (TypeError, ValueError):
            self.api_min_interval = 5.0
        self.exercise_text = config.get('exercise_text', '')

        # UI 状态（阈值、开关、批改方式等）
        self.threshold.set(config.get('threshold', 85.0))
        self.advanced_mode.set(config.get('advanced_mode', False))
        self.enable_plag.set(config.get('enable_plag', True))
        self.enable_grading.set(config.get('enable_grading', False))
        self.grading_method.set(config.get('grading_method', 'AST 静态质量打分'))
        self.require_suggestions.set(config.get('require_suggestions', True))

        # 文件列表：只恢复磁盘上仍然存在的文件，丢失的静默剔除
        saved_files = config.get('selected_files', [])
        if isinstance(saved_files, list):
            self.selected_files = [f for f in saved_files if os.path.isfile(f)]

        # --- 敏感字段从 .env / 系统环境变量读取 ---
        self.api_key.set(self.secrets_manager.get_api_key())
        self.api_proxy.set(self.secrets_manager.get_api_proxy())

    def save_config(self):
        """将非敏感配置保存到 config.yaml。"""
        config = {
            'api_base': self.api_base.get(),
            'api_model': self.api_model.get(),
            'local_model': self.local_model.get(),
            'api_min_interval': self.api_min_interval,
            'exercise_text': self.exercise_text,
            'threshold': self.threshold.get(),
            'advanced_mode': bool(self.advanced_mode.get()),
            'enable_plag': bool(self.enable_plag.get()),
            'enable_grading': bool(self.enable_grading.get()),
            'grading_method': self.grading_method.get(),
            'require_suggestions': bool(self.require_suggestions.get()),
            'selected_files': self.selected_files,
        }
        self.config_manager.save(config)

    def save_secrets(self):
        """将敏感字段（api_key、api_proxy）保存到 .env 文件。"""
        self.secrets_manager.save(
            api_key=self.api_key.get().strip(),
            api_proxy=self.api_proxy.get().strip(),
        )

    def _on_close(self):
        """关闭主窗口时自动保存配置，再销毁窗口。"""
        self.save_config()
        self.save_secrets()
        self.destroy()

    # 长任务（查重 + 批改）的具体执行交给 TaskRunner；这里只保留 widgets 需要的入口
    def run_check(self):
        self.task_runner.start()

    def cancel_check(self):
        self.task_runner.cancel()

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

        self.ai_results_map.clear()
        for i in self.ai_tree.get_children():
            self.ai_tree.delete(i)
                
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
