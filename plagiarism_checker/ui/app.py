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
import threading
import csv
# 使用相对路径从同一目录下的 `comparison_window` 模块导入 `ComparisonWindow` 类
from .comparison_window import ComparisonWindow
# 使用相对路径从父目录的 `analysis` 模块导入需要的函数
from ..analysis import find_suspicious_pairs, find_plagiarism_groups, detect_original_source

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
        self.selected_files = []  # 存储所有待检查的文件路径
        self.threshold = tk.DoubleVar(value=85.0)  # 存储相似度阈值
        self.recursive_search = tk.BooleanVar(value=False) # 存储是否包含子文件夹
        self.advanced_mode = tk.BooleanVar(value=False) # 存储是否启用深度查重（无视变量重命名），默认为False
        self.suspicious_pairs_map = {}  # 用于存储结果表格项和文件路径的映射
        self.status_text = tk.StringVar(value="欢迎使用！请添加要检查的Python文件。")  # 用于在状态栏显示信息

        # --- 主布局 ---
        # 我们将UI划分为顶部控制区、中间结果区和底部状态栏
        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(fill=tk.X)
        result_frame = ttk.LabelFrame(self, text="检查结果", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        status_bar = ttk.Label(self, textvariable=self.status_text, relief=tk.SUNKEN, padding=5)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # --- 文件选择UI ---
        file_frame = ttk.LabelFrame(top_frame, text="选择待检查的代码", padding="10")
        file_frame.pack(fill=tk.X)
        
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        add_file_btn = ttk.Button(btn_frame, text="添加文件", command=self.select_files)
        add_file_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        add_dir_btn = ttk.Button(btn_frame, text="添加文件夹", command=self.select_directory)
        add_dir_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        recursive_check = ttk.Checkbutton(btn_frame, text="包含子文件夹", variable=self.recursive_search)
        recursive_check.pack(side=tk.LEFT, padx=(0, 10))
        
        clear_btn = ttk.Button(btn_frame, text="清空列表", command=self.clear_files)
        clear_btn.pack(side=tk.RIGHT)

        list_container = ttk.Frame(file_frame)
        list_container.pack(fill=tk.X, expand=True)
        self.file_listbox = tk.Listbox(list_container, height=6)
        file_scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.config(yscrollcommand=file_scrollbar.set)
        file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # --- 公共控件 (滑块和检查按钮) ---
        common_controls_frame = ttk.Frame(top_frame)
        common_controls_frame.pack(fill=tk.X, pady=10)
        
        advanced_check = ttk.Checkbutton(common_controls_frame, text="检测“变量重命名”作弊 (深度模式)", variable=self.advanced_mode)
        advanced_check.pack(side=tk.LEFT, padx=(0, 15))
        
        threshold_label = ttk.Label(common_controls_frame, text="相似度阈值(%):")
        threshold_label.pack(side=tk.LEFT)
        threshold_scale = ttk.Scale(common_controls_frame, from_=50, to=100, orient=tk.HORIZONTAL, variable=self.threshold, length=100)
        threshold_scale.pack(side=tk.LEFT, padx=5)
        ttk.Label(common_controls_frame, textvariable=self.threshold).pack(side=tk.LEFT)
        check_button = ttk.Button(common_controls_frame, text="开始检查", command=self.run_check)
        check_button.pack(side=tk.RIGHT)

        # --- 美化表格样式 ---
        style = ttk.Style()
        style.configure("Treeview", rowheight=30, font=("Helvetica", 9))
        style.configure("Treeview.Heading", font=("Helvetica", 9))
        # 设置选中行颜色和交替行颜色支持
        style.map('Treeview', background=[('selected', '#0078D7')], foreground=[('selected', 'white')])

        # --- 结果显示区 (Treeview表格) ---
        tree_cols = ("分组文件数", "最高相似度", "疑似原创文件", "所有成员")
        self.result_tree = ttk.Treeview(result_frame, columns=tree_cols, show='headings')
        for col in tree_cols:
            self.result_tree.heading(col, text=col)
            
        self.result_tree.tag_configure('oddrow', background='#f9f9f9')
        self.result_tree.tag_configure('evenrow', background='#ffffff')
        self.result_tree.tag_configure('high_risk', foreground='#d32f2f') # 高危抄袭使用柔和的红色，去除加粗
            
        self.result_tree.column("分组文件数", width=80, anchor=tk.CENTER)
        self.result_tree.column("最高相似度", width=80, anchor=tk.CENTER)
        self.result_tree.column("疑似原创文件", width=150)
        self.result_tree.column("所有成员", width=400)
        tree_scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.config(yscrollcommand=tree_scrollbar.set)

        # 在结果区底部添加操作按钮和进度条的容器
        # 先 pack 底部容器并固定在底部(side=tk.BOTTOM)，防止窗口缩小时被表格挤出视口
        bottom_result_frame = ttk.Frame(result_frame)
        bottom_result_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0))

        btn_frame = ttk.Frame(bottom_result_frame)
        btn_frame.pack(side=tk.LEFT)

        compare_button = ttk.Button(btn_frame, text="对比高亮显示选中文件", command=self.show_comparison)
        compare_button.pack(side=tk.LEFT, padx=(0, 5))

        export_button = ttk.Button(btn_frame, text="导出报告", command=self.export_report)
        export_button.pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(bottom_result_frame, mode='indeterminate')
        # 默认不显示，在检查时显示

        # 最后 pack 表格和滚动条，使其占据剩余的全部空间
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # 初始化时，根据默认模式显示对应的UI
        # UI初始化完成

    def select_directory(self):
        """弹出对话框让用户选择一个文件夹，并将其中的文件加入列表。"""
        path = filedialog.askdirectory(title="选择包含.py文件的文件夹")
        if path:
            found_files = []
            if self.recursive_search.get():
                for root, dirs, files in os.walk(path):
                    for f in files:
                        if f.endswith('.py'):
                            found_files.append(os.path.join(root, f))
            else:
                for f in os.listdir(path):
                    if f.endswith('.py'):
                        full_path = os.path.join(path, f)
                        if os.path.isfile(full_path):
                            found_files.append(full_path)
                            
            if found_files:
                self.selected_files.extend(found_files)
                self.selected_files = sorted(list(set(self.selected_files)))
                self.update_file_listbox()
                self.status_text.set(f"从文件夹添加了 {len(found_files)} 个文件。当前共 {len(self.selected_files)} 个。")
            else:
                self.status_text.set("选中的文件夹中没有找到 .py 文件。")

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
        """清空已选文件列表。"""
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
        
        # 准备待检查的文件列表
        if not self.selected_files:
            self.status_text.set("错误: 请先添加需要检查的代码文件。")
            return
            
        files_to_check = self.selected_files

        if len(files_to_check) < 2:
            self.status_text.set("错误: 需要至少两个.py文件才能进行比较。")
            return
            
        self.status_text.set(f"检查中... 共 {len(files_to_check)} 个文件...")
        self.progress.pack(side=tk.RIGHT, padx=10)
        self.progress.start()
        self.update_idletasks() # 强制UI刷新，以显示“检查中...”的状态
        
        # --- 【教学说明】为什么要用多线程 (Multi-threading)？ ---
        # 如果直接在主线程（负责画界面和响应鼠标点击的线程）中运行查重计算，
        # 因为计算可能需要几秒甚至几十秒，这期间主线程被“卡死”了，整个软件就会显示“无响应”。
        # 所以，我们开辟一个新的“后台线程”去干脏活累活，让主线程继续保持流畅。
        threshold_ratio = self.threshold.get() / 100.0
        is_advanced = self.advanced_mode.get()
        
        def analysis_task():
            suspicious_pairs, errors = find_suspicious_pairs(files_to_check, threshold_ratio, is_advanced)
            # 【教学说明】线程安全 (Thread Safety)
            # Tkinter 规定：只能在主线程中修改 UI 界面！
            # 所以后台线程计算完之后，不能直接改界面，而是用 `self.after(0, ...)` 
            # 把结果像发快递一样“寄回”给主线程，让主线程去调用 `_update_ui_after_analysis` 函数。
            self.after(0, self._update_ui_after_analysis, suspicious_pairs, errors)
            
        # daemon=True 表示这是一个守护线程。当主窗口被用户点击 X 关闭时，这个后台计算线程会立刻自动死亡，防止程序在后台成为僵尸进程。
        threading.Thread(target=analysis_task, daemon=True).start()

    def _update_ui_after_analysis(self, suspicious_pairs, errors):
        """这个函数会在主线程中被调用，安全地更新界面数据。"""
        self.progress.stop()
        self.progress.pack_forget()

        # 如果在分析过程中有文件出错，可以在控制台打印出来
        if errors:
            print("分析过程中的错误:", errors)

        # --- 在UI上显示结果 ---
        if not suspicious_pairs:
            self.status_text.set("检查完成。未发现相似度高于阈值的代码文件。")
        else:
            groups = find_plagiarism_groups(suspicious_pairs)
            if not groups:
                self.status_text.set("检查完成。未发现成组的抄袭。")
                return
            self.status_text.set(f"检查完成。发现 {len(groups)} 组疑似抄袭。")
            for group, max_sim in groups:
                original_file, scores = detect_original_source(group)
                original_name = os.path.basename(original_file) if original_file else "未知"
                members = ", ".join([os.path.basename(f) for f in group])
                sim_str = f"{max_sim * 100:.1f}%"
                
                # 计算交替行的 tag
                tags = ('evenrow' if len(self.result_tree.get_children()) % 2 == 0 else 'oddrow',)
                if max_sim >= 0.90:  # 相似度达到 90% 以上视为高危查重
                    tags = tags + ('high_risk',)
                    
                # 在结果表格中插入一行
                item_id = self.result_tree.insert('', tk.END, values=(len(group), sim_str, original_name, members), tags=tags)
                # 记录这个表格项ID和它对应的分组信息
                self.suspicious_pairs_map[item_id] = (group, original_file)

    def show_comparison(self):
        """“对比高亮显示”按钮的执行函数。"""
        # 获取用户在表格中选中的项
        selected_items = self.result_tree.selection()
        if not selected_items:
            self.status_text.set("请先在表格中选择一个分组进行对比。")
            return
        
        # 获取选中的第一个项的ID
        item_id = selected_items[0]
        # 从映射中找到这对文件对应的完整路径
        group_files, original_file = self.suspicious_pairs_map[item_id]
        
        # 创建并显示对比窗口
        ComparisonWindow(self, group_files, original_file)

    def export_report(self):
        """导出报告按钮的执行函数。"""
        if not self.result_tree.get_children():
            self.status_text.set("没有可导出的结果。")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv")],
            title="保存分析报告"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["分组文件数", "最高相似度", "疑似原创文件", "所有成员"])
                for item_id in self.result_tree.get_children():
                    values = self.result_tree.item(item_id)['values']
                    writer.writerow(values)
            self.status_text.set(f"报告已成功导出到: {file_path}")
        except Exception as e:
            self.status_text.set(f"导出报告失败: {str(e)}")
