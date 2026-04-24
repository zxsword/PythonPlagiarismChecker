# -*- coding: utf-8 -*-
"""
UI 组件模块

将主窗口中可复用的、独立的UI区块（如文件选择、任务设置、结果展示）封装成独立的类，
以降低主 `app.py` 文件的复杂度和代码行数，提高可维护性。
"""

import tkinter as tk
from tkinter import ttk

class FileSelectionFrame(ttk.LabelFrame):
    """文件选择UI面板"""
    def __init__(self, parent, app_controller):
        super().__init__(parent, text="选择待检查的代码", padding="10")
        
        # 【教学说明】组件化与控制器传参 (MVC 模式雏形)
        # 这里的 app_controller 其实就是 app.py 里的 PlagiarismCheckerApp 实例。
        # 我们把它传进来保存为 self.app，这样 UI 组件内部的按钮被点击时，
        # 就可以直接调用主程序的方法（如 self.app.select_files），
        # 而不需要把复杂的业务逻辑写在这个单纯负责长相的 UI 类里。
        self.app = app_controller

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(btn_frame, text="添加文件", command=self.app.select_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="添加文件夹", command=self.app.select_directory).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(btn_frame, text="包含子文件夹", variable=self.app.recursive_search).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="清空列表", command=self.app.clear_files).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="📦 合并导出", command=self.app.merge_and_export_files).pack(side=tk.RIGHT, padx=(0, 5))

        list_container = ttk.Frame(self)
        list_container.pack(fill=tk.X, expand=True)
        
        # 将 file_listbox 实例创建的责任交给主 App，Frame 只负责布局
        self.app.file_listbox = tk.Listbox(list_container, height=6)
        file_scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.app.file_listbox.yview)
        self.app.file_listbox.config(yscrollcommand=file_scrollbar.set)
        
        file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.app.file_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)

class TaskOptionsFrame(ttk.LabelFrame):
    """运行任务与设置UI面板"""
    def __init__(self, parent, app_controller):
        super().__init__(parent, text="运行任务选项", padding="10")
        self.app = app_controller
        
        row1 = ttk.Frame(self)
        row1.pack(fill=tk.X, pady=(0, 5))
        row2 = ttk.Frame(self)
        row2.pack(fill=tk.X)
        
        ttk.Checkbutton(row1, text="1. 检测代码抄袭", variable=self.app.enable_plag).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Checkbutton(row1, text="深度查重模式", variable=self.app.advanced_mode).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(row1, text="相似度阈值(%):").pack(side=tk.LEFT)
        ttk.Scale(row1, from_=50, to=100, orient=tk.HORIZONTAL, variable=self.app.threshold, length=100).pack(side=tk.LEFT, padx=5)
        ttk.Label(row1, textvariable=self.app.threshold).pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Checkbutton(row2, text="2. 自动批改代码:", variable=self.app.enable_grading).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Combobox(row2, textvariable=self.app.grading_method, values=["AST 静态质量打分", "AI 本地大模型批改", "AI 云端大模型 (Gemini)"], state="readonly", width=22).pack(side=tk.LEFT)
        ttk.Checkbutton(row2, text="需要AI修改建议", variable=self.app.require_suggestions).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(row2, text="⚙️ AI设置", command=self.app.open_api_dialog).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(row2, text="📝 设定评分细则", command=self.app.open_exercise_dialog).pack(side=tk.LEFT, padx=(10, 0))
        
        self.app.cancel_btn = ttk.Button(row2, text="⏹ 取消任务", command=self.app.cancel_check, state=tk.DISABLED)
        self.app.cancel_btn.pack(side=tk.RIGHT, padx=(0, 5))
        self.app.start_btn = ttk.Button(row2, text="▶ 开始运行", command=self.app.run_check)
        self.app.start_btn.pack(side=tk.RIGHT)

class ResultsFrame(ttk.LabelFrame):
    """结果显示UI面板"""
    def __init__(self, parent, app_controller):
        super().__init__(parent, text="检查结果", padding="10")
        self.app = app_controller

        self._setup_styles()
        self._setup_notebook()
        self._setup_bottom_bar()
        
        # 最后 pack Notebook 标签容器，使其占据剩余的全部空间
        self.app.notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def _setup_styles(self):
        style = ttk.Style()
        style.configure("Treeview", rowheight=30, font=("Helvetica", 9))
        style.configure("Treeview.Heading", font=("Helvetica", 9))
        style.map('Treeview', background=[('selected', '#0078D7')], foreground=[('selected', 'white')])

    def _setup_notebook(self):
        self.app.notebook = ttk.Notebook(self)
        self._setup_plagiarism_tab()
        self._setup_grading_tab()

    def _setup_plagiarism_tab(self):
        self.app.tab_plag = ttk.Frame(self.app.notebook)
        self.app.notebook.add(self.app.tab_plag, text="抄袭检测结果")
        
        tree_cols = ("分组文件数", "最高相似度", "疑似原创文件", "所有成员")
        self.app.result_tree = ttk.Treeview(self.app.tab_plag, columns=tree_cols, show='headings')
        for col in tree_cols:
            self.app.result_tree.heading(col, text=col)
            
        self.app.result_tree.tag_configure('oddrow', background='#f9f9f9')
        self.app.result_tree.tag_configure('evenrow', background='#ffffff')
        self.app.result_tree.tag_configure('high_risk', foreground='#d32f2f')
            
        self.app.result_tree.column("分组文件数", width=80, anchor=tk.CENTER)
        self.app.result_tree.column("最高相似度", width=80, anchor=tk.CENTER)
        self.app.result_tree.column("疑似原创文件", width=150)
        self.app.result_tree.column("所有成员", width=400)
        
        tree_scrollbar = ttk.Scrollbar(self.app.tab_plag, orient=tk.VERTICAL, command=self.app.result_tree.yview)
        self.app.result_tree.config(yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.app.result_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.app.result_tree.bind("<Double-1>", lambda event: self.app.show_comparison())
        self.app.result_tree.bind("<Button-3>", self.app.popup_plag_menu)
        self.app.result_tree.bind("<Button-2>", self.app.popup_plag_menu)

    def _setup_grading_tab(self):
        self.app.tab_ai = ttk.Frame(self.app.notebook)
        self.app.notebook.add(self.app.tab_ai, text="自动批改结果")
        
        ai_cols = ("文件名", "评分", "批改状态")
        self.app.ai_tree = ttk.Treeview(self.app.tab_ai, columns=ai_cols, show='headings')
        self.app.ai_tree.heading("文件名", text="文件名")
        self.app.ai_tree.heading("评分", text="评分")
        self.app.ai_tree.heading("批改状态", text="批改状态")
        self.app.ai_tree.column("文件名", width=200, anchor=tk.W)
        self.app.ai_tree.column("评分", width=60, anchor=tk.CENTER)
        self.app.ai_tree.column("批改状态", width=450, anchor=tk.W)
        
        self.app.ai_tree.tag_configure('oddrow', background='#f9f9f9')
        self.app.ai_tree.tag_configure('evenrow', background='#ffffff')
        self.app.ai_tree.tag_configure('error', foreground='#d32f2f')
        self.app.ai_tree.tag_configure('success', foreground='#2e7d32')

        ai_scrollbar = ttk.Scrollbar(self.app.tab_ai, orient=tk.VERTICAL, command=self.app.ai_tree.yview)
        self.app.ai_tree.config(yscrollcommand=ai_scrollbar.set)
        ai_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.app.ai_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.app.ai_tree.bind("<Double-1>", lambda event: self.app.show_ai_review())
        self.app.ai_tree.bind("<Button-3>", self.app.popup_ai_menu)
        self.app.ai_tree.bind("<Button-2>", self.app.popup_ai_menu)

    def _setup_bottom_bar(self):
        bottom_result_frame = ttk.Frame(self)
        bottom_result_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0))

        btn_frame = ttk.Frame(bottom_result_frame)
        btn_frame.pack(side=tk.LEFT)

        ttk.Button(btn_frame, text="对比选中的抄袭文件", command=self.app.show_comparison).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="查看详细批改评语", command=self.app.show_ai_review).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="导出报告", command=self.app.export_report).pack(side=tk.LEFT)

        self.app.progress = ttk.Progressbar(bottom_result_frame, mode='indeterminate')