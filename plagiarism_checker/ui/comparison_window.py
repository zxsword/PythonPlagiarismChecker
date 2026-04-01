# -*- coding: utf-8 -*-
"""
代码对比窗口模块

这个文件定义了 `ComparisonWindow` 类，它是一个独立的弹出窗口，
用于并排显示两个代码文件，并高亮它们的相似之处。
"""

import tkinter as tk
from tkinter import ttk
import os
import difflib

class ComparisonWindow(tk.Toplevel):
    """
    一个 Toplevel 窗口，用于并排显示和比较两个文本文件。
    Toplevel 就像是一个新的、独立的子窗口。
    """
    def __init__(self, parent, file1_path, file2_path):
        """
        初始化对比窗口。

        Args:
            parent: 父窗口实例 (这里是主应用的实例)。
            file1_path (str): 第一个待比较文件的路径。
            file2_path (str): 第二个待比较文件的路径。
        """
        # super().__init__(parent) 调用父类的构造函数，完成窗口的基本设置
        super().__init__(parent)
        self.title("代码对比")
        self.geometry("1200x800")  # 设置窗口的默认大小

        # --- 创建UI布局 ---
        # 主框架，用于容纳左右两个文件显示区
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧框架，用于显示第一个文件，LabelFrame 带有一个标题框
        frame1 = ttk.LabelFrame(main_frame, text=os.path.basename(file1_path), padding=5)
        frame1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 右侧框架，用于显示第二个文件
        frame2 = ttk.LabelFrame(main_frame, text=os.path.basename(file2_path), padding=5)
        frame2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # --- 创建文本显示框 (Text Widget) ---
        # wrap=tk.NONE 表示不自动换行，结合水平滚动条查看长代码行
        # font 指定了文本的字体和大小，使用等宽字体 "Courier New" 能让代码对得更整齐
        self.text1 = tk.Text(frame1, wrap=tk.NONE, font=("Courier New", 10))
        self.text2 = tk.Text(frame2, wrap=tk.NONE, font=("Courier New", 10))

        # --- 创建滚动条 ---
        self.scroll1_y = ttk.Scrollbar(frame1, orient=tk.VERTICAL, command=self.text1.yview)
        self.scroll1_x = ttk.Scrollbar(frame1, orient=tk.HORIZONTAL, command=self.text1.xview)
        self.text1.config(yscrollcommand=self.scroll1_y.set, xscrollcommand=self.scroll1_x.set)

        self.scroll2_y = ttk.Scrollbar(frame2, orient=tk.VERTICAL, command=self.text2.yview)
        self.scroll2_x = ttk.Scrollbar(frame2, orient=tk.HORIZONTAL, command=self.text2.xview)
        self.text2.config(yscrollcommand=self.scroll2_y.set, xscrollcommand=self.scroll2_x.set)

        # 将滚动条和文本框打包到界面上
        self.scroll1_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.scroll2_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.scroll1_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.scroll2_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.text1.pack(fill=tk.BOTH, expand=True)
        self.text2.pack(fill=tk.BOTH, expand=True)

        # --- 绑定同步滚动事件 ---
        # 当在一个文本框里滚动鼠标滚轮时，另一个也跟着动
        self.text1.bind("<MouseWheel>", self.on_scroll)
        self.text2.bind("<MouseWheel>", self.on_scroll)
        # 当拖动一个滚动条时，另一个也跟着动
        self.scroll1_y.bind("<B1-Motion>", lambda e: self.sync_scroll(self.text1, self.text2))
        self.scroll2_y.bind("<B1-Motion>", lambda e: self.sync_scroll(self.text2, self.text1))

        # --- 加载文件内容并高亮 ---
        self.load_and_highlight(file1_path, file2_path)

    def on_scroll(self, event):
        """处理鼠标滚轮事件，实现两个文本框的同步滚动。"""
        # event.delta 在 Windows 上通常是 120 的倍数
        # 除以 120 得到滚动的“单位”数，乘以 -1 是因为滚轮向上滚动 delta 为正，但文本应该向上移动
        self.text1.yview_scroll(-1 * (event.delta // 120), "units")
        self.text2.yview_scroll(-1 * (event.delta // 120), "units")
        # return "break" 阻止事件继续传播，防止窗口本身也滚动
        return "break"

    def sync_scroll(self, source, target):
        """处理拖动滚动条事件，实现同步。"""
        # 获取源文本框的滚动条位置
        source_pos = source.yview()
        # 将目标文本框移动到相同的位置
        target.yview_moveto(source_pos[0])

    def load_and_highlight(self, file1_path, file2_path):
        """加载两个文件的内容，并使用 difflib 来高亮相似和不同的部分。"""
        try:
            # .readlines() 将文件内容读取为一个行的列表
            with open(file1_path, 'r', encoding='utf-8', errors='ignore') as f:
                content1 = f.readlines()
            with open(file2_path, 'r', encoding='utf-8', errors='ignore') as f:
                content2 = f.readlines()
        except IOError:
            self.text1.insert(tk.END, "错误：无法读取文件。")
            self.text2.insert(tk.END, "错误：无法读取文件。")
            return

        # --- 定义高亮样式 ---
        # tag_configure 用于定义一个“标签”，我们可以给这个标签设置样式
        # 后面可以把这个标签应用到文本的特定范围上
        self.text1.tag_configure("highlight", background="#d2f4d2")  # 相似部分使用淡绿色背景
        self.text2.tag_configure("highlight", background="#d2f4d2")
        self.text1.tag_configure("diff", background="#ffdddd")  # 差异部分使用淡红色背景
        self.text2.tag_configure("diff", background="#ffdddd")

        # 创建 SequenceMatcher 对象，用于比较两个行列表
        seq_matcher = difflib.SequenceMatcher(None, content1, content2)

        # 先将全部内容插入到文本框中
        for line in content1:
            self.text1.insert(tk.END, line)
        for line in content2:
            self.text2.insert(tk.END, line)
        
        # --- 应用高亮 ---
        # get_opcodes() 是 difflib 的核心，它返回一个指令列表，告诉我们
        #如何从第一个序列变成第二个序列。
        # 每个指令是一个元组 (tag, i1, i2, j1, j2)，其中：
        # - tag: 'equal'(相同), 'replace'(替换), 'delete'(删除), 'insert'(插入)
        # - i1, i2: 第一个序列中的范围 (从 i1 到 i2-1)
        # - j1, j2: 第二个序列中的范围 (从 j1 到 j2-1)
        for tag, i1, i2, j1, j2 in seq_matcher.get_opcodes():
            if tag == 'equal':
                # 如果是 'equal'，我们就用 "highlight" 标签高亮这部分
                # Text widget 的索引是 "行.列" 的形式，例如 "1.0" 是第一行第0列
                self.text1.tag_add("highlight", f"{i1 + 1}.0", f"{i2}.0 + 1 chars")
                self.text2.tag_add("highlight", f"{j1 + 1}.0", f"{j2}.0 + 1 chars")
            elif tag == 'replace':
                # 如果是 'replace'，我们就用 "diff" 标签高亮这部分
                self.text1.tag_add("diff", f"{i1 + 1}.0", f"{i2}.0 + 1 chars")
                self.text2.tag_add("diff", f"{j1 + 1}.0", f"{j2}.0 + 1 chars")
