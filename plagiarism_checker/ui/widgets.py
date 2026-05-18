# -*- coding: utf-8 -*-
"""
UI 组件模块

将主窗口中可复用的、独立的UI区块（如文件选择、任务设置、结果展示）封装成独立的类，
以降低主 `app.py` 文件的复杂度和代码行数，提高可维护性。

【设计约定】组件通过属性暴露关键控件，主 App 在 _init_ui 里显式读回挂到自己身上：
    self.file_frame = FileSelectionFrame(parent, self)
    self.file_listbox = self.file_frame.file_listbox

不要再让组件反过来直接给 self.app.xxx 赋值——那会让"这个属性是在哪里定义的"
变得无从查起。
"""

import tkinter as tk
from tkinter import ttk
from .theme import PROFESSIONAL_THEME as PRO

class FileSelectionFrame(ttk.LabelFrame):
    """文件选择UI面板"""
    def __init__(self, parent, app_controller):
        super().__init__(parent, text="选择待检查的代码", padding="10")

        # 【教学说明】组件化与控制器传参 (MVC 模式雏形)
        # 这里的 app_controller 其实就是 app.py 里的 PlagiarismCheckerApp 实例。
        # 保存为 self.app 是为了让按钮 command 能直接挂到主程序的方法上，
        # 避免把业务逻辑写到这个负责长相的 UI 类里。组件【不应】反过来给 self.app.xxx 赋值。
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

        # 控件挂在自己身上，让主 App 在 _init_ui 里通过 self.file_frame.file_listbox 读回
        self.file_listbox = tk.Listbox(list_container, height=6)
        file_scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.config(yscrollcommand=file_scrollbar.set)

        file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)

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

        # 按钮挂在自己身上；主 App 在 _init_ui 里通过 self.task_frame.cancel_btn / start_btn 读回
        self.cancel_btn = ttk.Button(row2, text="⏹ 取消任务", command=self.app.cancel_check, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.RIGHT, padx=(0, 5))
        self.start_btn = ttk.Button(row2, text="▶ 开始运行", command=self.app.run_check)
        self.start_btn.pack(side=tk.RIGHT)

class ResultsFrame(ttk.LabelFrame):
    """结果显示UI面板"""
    def __init__(self, parent, app_controller):
        super().__init__(parent, text="检查结果", padding="10")
        self.app = app_controller

        self._setup_styles()
        self._setup_notebook()
        self._setup_bottom_bar()

        # 最后 pack Notebook 标签容器，使其占据剩余的全部空间
        self.notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def _setup_styles(self):
        style = ttk.Style()
        style.configure("Treeview", rowheight=30, font=("Helvetica", 9))
        style.configure("Treeview.Heading", font=("Helvetica", 9))
        style.map('Treeview', background=[('selected', PRO['select_bg'])], foreground=[('selected', PRO['select_fg'])])

    def _setup_notebook(self):
        self.notebook = ttk.Notebook(self)
        self._setup_plagiarism_tab()
        self._setup_grading_tab()

    def _setup_plagiarism_tab(self):
        self.tab_plag = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_plag, text="抄袭检测结果")

        tree_cols = ("分组文件数", "最高相似度", "疑似原创文件", "所有成员")
        self.result_tree = ttk.Treeview(self.tab_plag, columns=tree_cols, show='headings')
        for col in tree_cols:
            self.result_tree.heading(col, text=col)

        self.result_tree.tag_configure('oddrow', background=PRO['row_alt_bg'])
        self.result_tree.tag_configure('evenrow', background=PRO['paper_bg'])
        self.result_tree.tag_configure('high_risk', foreground=PRO['error_fg'])

        self.result_tree.column("分组文件数", width=80, anchor=tk.CENTER)
        self.result_tree.column("最高相似度", width=80, anchor=tk.CENTER)
        self.result_tree.column("疑似原创文件", width=150)
        self.result_tree.column("所有成员", width=400)

        tree_scrollbar = ttk.Scrollbar(self.tab_plag, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.config(yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.result_tree.bind("<Double-1>", lambda event: self.app.show_comparison())
        self.result_tree.bind("<Button-3>", self.app.popup_plag_menu)
        self.result_tree.bind("<Button-2>", self.app.popup_plag_menu)

    def _setup_grading_tab(self):
        self.tab_ai = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ai, text="自动批改结果")

        ai_cols = ("文件名", "评分", "批改状态")
        self.ai_tree = ttk.Treeview(self.tab_ai, columns=ai_cols, show='headings')
        self.ai_tree.heading("文件名", text="文件名")
        self.ai_tree.heading("评分", text="评分")
        self.ai_tree.heading("批改状态", text="批改状态")
        self.ai_tree.column("文件名", width=200, anchor=tk.W)
        self.ai_tree.column("评分", width=60, anchor=tk.CENTER)
        self.ai_tree.column("批改状态", width=450, anchor=tk.W)

        self.ai_tree.tag_configure('oddrow', background=PRO['row_alt_bg'])
        self.ai_tree.tag_configure('evenrow', background=PRO['paper_bg'])
        self.ai_tree.tag_configure('error', foreground=PRO['error_fg'])
        self.ai_tree.tag_configure('success', foreground=PRO['success_fg'])

        ai_scrollbar = ttk.Scrollbar(self.tab_ai, orient=tk.VERTICAL, command=self.ai_tree.yview)
        self.ai_tree.config(yscrollcommand=ai_scrollbar.set)
        ai_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.ai_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.ai_tree.bind("<Double-1>", lambda event: self.app.show_ai_review())
        self.ai_tree.bind("<Button-3>", self.app.popup_ai_menu)
        self.ai_tree.bind("<Button-2>", self.app.popup_ai_menu)

    def _setup_bottom_bar(self):
        bottom_result_frame = ttk.Frame(self)
        bottom_result_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0))

        btn_frame = ttk.Frame(bottom_result_frame)
        btn_frame.pack(side=tk.LEFT)

        ttk.Button(btn_frame, text="对比选中的抄袭文件", command=self.app.show_comparison).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="查看详细批改评语", command=self.app.show_ai_review).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="导出报告", command=self.app.export_report).pack(side=tk.LEFT)

        # 进度条挂在自己身上；主 App 通过 self.results_frame.progress 读回
        self.progress = ttk.Progressbar(bottom_result_frame, mode='indeterminate')
