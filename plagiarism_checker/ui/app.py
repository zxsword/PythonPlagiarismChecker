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
# 使用相对路径从同一目录下的 `comparison_window` 模块导入 `ComparisonWindow` 类
from .comparison_window import ComparisonWindow
# 使用相对路径从父目录的 `analysis` 模块导入 `find_suspicious_pairs` 函数
from ..analysis import find_suspicious_pairs

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

        # --- 数据变量 ---
        # 这些是用来存储程序状态的变量
        self.dir_path = tk.StringVar(value="尚未选择文件夹") # 存储所选文件夹的路径
        self.selected_files = []  # 存储在“文件模式”下选择的所有文件路径
        self.threshold = tk.DoubleVar(value=85.0)  # 存储相似度阈值
        self.check_mode = tk.StringVar(value="folder")  # 'folder' 或 'file'，存储当前的检查模式
        self.suspicious_pairs_map = {}  # 用于存储结果表格项和文件路径的映射
        self.status_text = tk.StringVar(value="欢迎使用！请选择模式并开始检查。")  # 用于在状态栏显示信息

        # --- 主布局 ---
        # 我们将UI划分为顶部控制区、中间结果区和底部状态栏
        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(fill=tk.X)
        result_frame = ttk.LabelFrame(self, text="检查结果", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        status_bar = ttk.Label(self, textvariable=self.status_text, relief=tk.SUNKEN, padding=5)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # --- 模式选择UI ---
        mode_frame = ttk.LabelFrame(top_frame, text="检查模式", padding="10")
        mode_frame.pack(fill=tk.X)
        folder_radio = ttk.Radiobutton(mode_frame, text="文件夹模式", variable=self.check_mode, value="folder", command=self.switch_mode)
        folder_radio.pack(side=tk.LEFT, padx=5)
        file_radio = ttk.Radiobutton(mode_frame, text="文件模式", variable=self.check_mode, value="file", command=self.switch_mode)
        file_radio.pack(side=tk.LEFT, padx=5)

        # --- 两种模式各自的UI框架 ---
        self.folder_frame = ttk.Frame(top_frame)
        self.file_frame = ttk.Frame(top_frame)

        # --- “文件夹模式”下的控件 ---
        dir_button = ttk.Button(self.folder_frame, text="选择学生代码文件夹", command=self.select_directory)
        dir_button.pack(side=tk.LEFT, padx=(0, 10))
        dir_label = ttk.Label(self.folder_frame, textvariable=self.dir_path)
        dir_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # --- “文件模式”下的控件 ---
        file_button = ttk.Button(self.file_frame, text="选择代码文件", command=self.select_files)
        file_button.pack(side=tk.LEFT, padx=(0, 10))
        clear_button = ttk.Button(self.file_frame, text="清空列表", command=self.clear_files)
        clear_button.pack(side=tk.LEFT)
        list_container = ttk.Frame(self.file_frame)
        list_container.pack(fill=tk.X, expand=True, pady=(5,0))
        self.file_listbox = tk.Listbox(list_container, height=4) # 列表框，用于显示已选文件名
        file_scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.config(yscrollcommand=file_scrollbar.set)
        file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # --- 公共控件 (滑块和检查按钮) ---
        common_controls_frame = ttk.Frame(top_frame)
        common_controls_frame.pack(fill=tk.X, pady=10)
        threshold_label = ttk.Label(common_controls_frame, text="相似度阈值(%):")
        threshold_label.pack(side=tk.LEFT)
        threshold_scale = ttk.Scale(common_controls_frame, from_=50, to=100, orient=tk.HORIZONTAL, variable=self.threshold, length=100)
        threshold_scale.pack(side=tk.LEFT, padx=5)
        ttk.Label(common_controls_frame, textvariable=self.threshold).pack(side=tk.LEFT)
        check_button = ttk.Button(common_controls_frame, text="开始检查", command=self.run_check)
        check_button.pack(side=tk.RIGHT)

        # --- 结果显示区 (Treeview表格) ---
        tree_cols = ("File 1", "File 2", "Similarity")
        self.result_tree = ttk.Treeview(result_frame, columns=tree_cols, show='headings')
        for col in tree_cols:
            self.result_tree.heading(col, text=col)
            self.result_tree.column(col, width=150)
        self.result_tree.column("Similarity", width=80, anchor=tk.CENTER) # 居中显示相似度
        tree_scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.config(yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_tree.pack(fill=tk.BOTH, expand=True)

        compare_button = ttk.Button(result_frame, text="对比高亮显示选中文件", command=self.show_comparison)
        compare_button.pack(pady=(5,0))
        
        # 初始化时，根据默认模式显示对应的UI
        self.switch_mode()

    def switch_mode(self):
        """切换“文件夹模式”和“文件模式”的UI显示。"""
        if self.check_mode.get() == "folder":
            self.file_frame.pack_forget()  # 隐藏文件模式的UI
            self.folder_frame.pack(fill=tk.X, pady=5)  # 显示文件夹模式的UI
        else:
            self.folder_frame.pack_forget()  # 隐藏文件夹模式的UI
            self.file_frame.pack(fill=tk.X, pady=5)  # 显示文件模式的UI
        self.clear_results() # 切换模式时清空上次的结果
        
    def select_directory(self):
        """弹出对话框让用户选择一个文件夹。"""
        path = filedialog.askdirectory(title="选择包含.py文件的文件夹")
        if path:
            self.dir_path.set(path)
            self.status_text.set(f"已选择文件夹: {path}")

    def select_files(self):
        """弹出对话框让用户选择一个或多个文件。"""
        files = filedialog.askopenfilenames(title="选择多个Python文件", filetypes=[("Python files", "*.py")])
        if files:
            self.selected_files.extend(files)
            # 去重并排序
            self.selected_files = sorted(list(set(self.selected_files)))
            self.update_file_listbox()
            self.status_text.set(f"已添加 {len(files)} 个文件。当前共 {len(self.selected_files)} 个。")

    def clear_files(self):
        """清空文件模式下的已选文件列表。"""
        self.selected_files.clear()
        self.update_file_listbox()
        self.status_text.set("文件列表已清空。")

    def update_file_listbox(self):
        """更新文件列表框中显示的内容。"""
        self.file_listbox.delete(0, tk.END) # 先清空
        for f in self.selected_files:
            self.file_listbox.insert(tk.END, os.path.basename(f)) # 只显示文件名，不显示完整路径

    def clear_results(self):
        """清空结果表格和相关的映射数据。"""
        self.suspicious_pairs_map.clear()
        for i in self.result_tree.get_children():
            self.result_tree.delete(i)

    def run_check(self):
        """“开始检查”按钮的核心执行函数。"""
        self.clear_results()
        mode = self.check_mode.get()
        
        # 根据当前模式，准备待检查的文件列表
        if mode == 'folder':
            directory = self.dir_path.get()
            if not os.path.isdir(directory):
                self.status_text.set("错误: 请先选择一个有效的文件夹。")
                return
            self.status_text.set(f"检查中... '{os.path.basename(directory)}'")
            files_to_check = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.py')]
        else: # 'file' mode
            if not self.selected_files:
                self.status_text.set("错误: 请先选择至少两个代码文件。")
                return
            self.status_text.set(f"检查中... {len(self.selected_files)} 个已选文件...")
            files_to_check = self.selected_files

        if len(files_to_check) < 2:
            self.status_text.set("错误: 需要至少两个.py文件才能进行比较。")
            return
            
        self.update_idletasks() # 强制UI刷新，以显示“检查中...”的状态
        
        # --- 调用分析模块进行计算 ---
        threshold_ratio = self.threshold.get() / 100.0
        suspicious_pairs, errors = find_suspicious_pairs(files_to_check, threshold_ratio)

        # 如果在分析过程中有文件出错，可以在控制台打印出来
        if errors:
            print("分析过程中的错误:", errors)

        # --- 在UI上显示结果 ---
        if not suspicious_pairs:
            self.status_text.set("检查完成。未发现相似度高于阈值的代码文件。")
        else:
            self.status_text.set(f"检查完成。发现 {len(suspicious_pairs)} 对可疑文件。")
            for (f1, f2), sim in suspicious_pairs:
                # 在结果表格中插入一行
                item_id = self.result_tree.insert('', tk.END, values=(os.path.basename(f1), os.path.basename(f2), f"{sim:.2%}"))
                # 记录这个表格项ID和它对应的两个文件的完整路径
                # 这样当用户点击对比时，我们能知道该对比哪两个文件
                self.suspicious_pairs_map[item_id] = (f1, f2)

    def show_comparison(self):
        """“对比高亮显示”按钮的执行函数。"""
        # 获取用户在表格中选中的项
        selected_items = self.result_tree.selection()
        if not selected_items:
            self.status_text.set("请先在表格中选择一个文件对进行对比。")
            return
        
        # 获取选中的第一个项的ID
        item_id = selected_items[0]
        # 从映射中找到这对文件对应的完整路径
        file1_path, file2_path = self.suspicious_pairs_map[item_id]
        
        # 创建并显示对比窗口
        ComparisonWindow(self, file1_path, file2_path)
