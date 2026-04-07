# -*- coding: utf-8 -*-
"""
代码对比窗口模块

这个文件定义了 `ComparisonWindow` 类，它是一个独立的弹出窗口，
用于并排显示多个代码文件，并高亮它们的相似之处与差异。
"""

import tkinter as tk
from tkinter import ttk
import os
import difflib

class ComparisonWindow(tk.Toplevel):
    """
    一个 Toplevel 窗口，用于并排显示和比较多个文本文件。
    Toplevel 就像是一个新的、独立的子窗口。
    """
    def __init__(self, parent, file_paths, original_path=None):
        """
        初始化多文件对比窗口。

        Args:
            parent: 父窗口实例 (这里是主应用的实例)。
            file_paths (list): 待比较文件的路径列表。
            original_path (str, optional): 疑似原创文件的路径。
        """
        super().__init__(parent)
        self.title("多文件代码对比")
        self.geometry("1400x800")  # 设置窗口的默认大小为更宽，以适应多个文件

        self.file_paths = file_paths
        self.original_path = original_path
        self.text_widgets = []
        self.line_widgets = []
        self.y_scrollbars = []

        # --- 工具栏与图例 ---
        top_bar = ttk.Frame(self, padding=(10, 10, 10, 0))
        top_bar.pack(fill=tk.X, side=tk.TOP)
        
        # 风格切换控件
        self.theme_var = tk.StringVar(value="专业模式 (弱化相同)")
        theme_combo = ttk.Combobox(top_bar, textvariable=self.theme_var, values=["专业模式 (弱化相同)", "查重模式 (标红抄袭)"], state="readonly", width=20)
        theme_combo.pack(side=tk.RIGHT, padx=5)
        theme_combo.bind("<<ComboboxSelected>>", self.apply_theme)
        ttk.Label(top_bar, text="配色风格:").pack(side=tk.RIGHT)

        self.legend_frame = ttk.Frame(top_bar)
        self.legend_frame.pack(side=tk.LEFT, fill=tk.X)

        # --- 创建UI布局 ---
        # 主框架
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 【教学说明】Canvas 嵌套技巧 ---
        # Tkinter 的普通 Frame 是不支持加滚动条的。
        # 当你同时对比 3 个、4 个甚至更多文件时，屏幕宽度不够怎么办？
        # 解决套路：先创建一个画布 (Canvas)，把 Canvas 加上水平滚动条，
        # 然后把真正装代码的 files_frame 当作“一幅画”塞进 Canvas 里。
        self.canvas = tk.Canvas(main_frame, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.files_frame = ttk.Frame(self.canvas)
        
        # 将 files_frame 放入 canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.files_frame, anchor="nw")
        
        def configure_scrollregion(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
        def configure_canvas(event):
            self.canvas.itemconfig(self.canvas_window, height=event.height)
            req_width = self.files_frame.winfo_reqwidth()
            if req_width < event.width:
                self.canvas.itemconfig(self.canvas_window, width=event.width)
            else:
                self.canvas.itemconfig(self.canvas_window, width="")

        self.files_frame.bind("<Configure>", configure_scrollregion)
        self.canvas.bind("<Configure>", configure_canvas)
        self.canvas.configure(xscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 当文件较多时，调整默认文本框宽度以防过宽
        text_width = 50 if len(file_paths) > 2 else 80

        # 针对每个文件，创建一个并排的框架
        for i, path in enumerate(file_paths):
            title = os.path.basename(path)
            if path == original_path:
                title += " (疑似原创)"
            
            frame = ttk.LabelFrame(self.files_frame, text=title, padding=5)
            # 平均分配空间
            frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)

            # 行号文本框
            line_widget = tk.Text(frame, width=4, padx=3, takefocus=0, border=0, background="#f0f0f0", state=tk.DISABLED, font=("Courier New", 10), wrap=tk.NONE)
            line_widget.pack(side=tk.LEFT, fill=tk.Y)
            self.line_widgets.append(line_widget)

            # 文本框 (清理了上一次修改导致的重复代码)
            # 修改了 bg (背景色) 和 fg (前景色)，让相同代码默认呈现柔和的灰色
            text_widget = tk.Text(frame, wrap=tk.NONE, font=("Courier New", 10), width=text_width, bg="#f8f8f8", fg="#7a7a7a", selectbackground="#0078D7", selectforeground="white", exportselection=False)
            self.text_widgets.append(text_widget)

            # 滚动条
            scroll_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
            scroll_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=text_widget.xview)
            
            # 使用闭包，当文本框Y轴滚动时，同时更新滚动条和旁边的行号框
            def sync_line_and_scroll(*args, sy=scroll_y.set, lw=line_widget):
                sy(*args)
                lw.yview_moveto(args[0])
                
            text_widget.config(yscrollcommand=sync_line_and_scroll, xscrollcommand=scroll_x.set)
            
            self.y_scrollbars.append(scroll_y)

            scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
            scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
            text_widget.pack(fill=tk.BOTH, expand=True)

            # 绑定鼠标滚轮事件 (<MouseWheel> 在 Windows 上有效)
            text_widget.bind("<MouseWheel>", self.on_scroll)
            # 绑定拖动滚动条同步
            # 【教学说明】lambda 与默认参数
            # 这里使用 lambda 匿名函数将当前循环的 text_widget 保存到 source 变量中。
            # <B1-Motion> 代表鼠标左键按下并拖动的事件。
            scroll_y.bind("<B1-Motion>", lambda e, source=text_widget: self.sync_scroll(source))

        # --- 加载文件内容并高亮 ---
        self.load_and_highlight()

    def on_scroll(self, event):
        """处理鼠标滚轮事件，实现所有文本框的同步滚动。"""
        scroll_units = -1 * (event.delta // 120)
        for text_widget in self.text_widgets:
            text_widget.yview_scroll(scroll_units, "units")
        return "break"

    def sync_scroll(self, source):
        """处理拖动滚动条事件，实现同步。"""
        source_pos = source.yview()
        for text_widget in self.text_widgets:
            if text_widget != source:
                text_widget.yview_moveto(source_pos[0])

    def load_and_highlight(self):
        """加载所有文件的内容，并使用基准文件高亮差异。"""
        contents = []
        for path in self.file_paths:
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    contents.append(f.readlines())
            except IOError:
                contents.append(["错误：无法读取文件。\n"])

        # 确定基准文件索引（如果提供了疑似原创文件，则使用它；否则使用第一个文件）
        baseline_idx = 0
        if self.original_path in self.file_paths:
            baseline_idx = self.file_paths.index(self.original_path)

        # 插入内容并配置样式
        for i, (text_widget, lines) in enumerate(zip(self.text_widgets, contents)):
            
            # 提高 sel (选中状态) 标签的优先级，确保蓝底白字的高亮不被上面的背景色覆盖
            text_widget.tag_raise("sel")
            
            for line in lines:
                text_widget.insert(tk.END, line)
                
            # 注入行号数字
            line_widget = self.line_widgets[i]
            line_widget.config(state=tk.NORMAL)
            for line_num in range(1, len(lines) + 1):
                line_widget.insert(tk.END, f"{line_num}\n")
            line_widget.config(state=tk.DISABLED)

        # 进行高亮比对
        baseline_lines = contents[baseline_idx]
        baseline_widget = self.text_widgets[baseline_idx]

        for i, text_widget in enumerate(self.text_widgets):
            if i == baseline_idx:
                continue
            
            compare_lines = contents[i]
            seq_matcher = difflib.SequenceMatcher(None, baseline_lines, compare_lines)

            for tag, i1, i2, j1, j2 in seq_matcher.get_opcodes():
                if tag == 'equal':
                    # 标记相同代码（即抄袭部分），供切换主题使用
                    baseline_widget.tag_add("identical", f"{i1 + 1}.0", f"{i2 + 1}.0")
                    text_widget.tag_add("identical", f"{j1 + 1}.0", f"{j2 + 1}.0")
                elif tag in ('replace', 'insert', 'delete'):
                    # 有差异的部分背景
                    if tag in ('replace', 'delete'):
                        baseline_widget.tag_add("diff_bg_del", f"{i1 + 1}.0", f"{i2 + 1}.0")
                    if tag in ('replace', 'insert'):
                        text_widget.tag_add("diff_bg_add", f"{j1 + 1}.0", f"{j2 + 1}.0")
                        
                    if tag == 'replace':
                        # 逐行进行行内高亮
                        for line_offset in range(max(i2 - i1, j2 - j1)):
                            bl_idx = i1 + line_offset
                            comp_idx = j1 + line_offset
                            
                            if bl_idx < i2 and comp_idx < j2:
                                bl_line = baseline_lines[bl_idx]
                                comp_line = compare_lines[comp_idx]
                                char_matcher = difflib.SequenceMatcher(None, bl_line, comp_line)
                                for c_tag, ci1, ci2, cj1, cj2 in char_matcher.get_opcodes():
                                    if c_tag in ('replace', 'delete'):
                                        baseline_widget.tag_add("diff_del", f"{bl_idx + 1}.{ci1}", f"{bl_idx + 1}.{ci2}")
                                    if c_tag in ('replace', 'insert'):
                                        text_widget.tag_add("diff_add", f"{comp_idx + 1}.{cj1}", f"{comp_idx + 1}.{cj2}")
                            elif bl_idx < i2:
                                baseline_widget.tag_add("diff_del", f"{bl_idx + 1}.0", f"{bl_idx + 2}.0")
                            elif comp_idx < j2:
                                text_widget.tag_add("diff_add", f"{comp_idx + 1}.0", f"{comp_idx + 2}.0")
                    elif tag == 'delete':
                        baseline_widget.tag_add("diff_del", f"{i1 + 1}.0", f"{i2 + 1}.0")
                    elif tag == 'insert':
                        text_widget.tag_add("diff_add", f"{j1 + 1}.0", f"{j2 + 1}.0")

        # 所有标签添加完毕后，应用默认主题渲染
        self.apply_theme()

    def apply_theme(self, event=None):
        """动态切换高亮配色风格"""
        theme = self.theme_var.get()
        
        # 清空现有图例
        for widget in self.legend_frame.winfo_children():
            widget.destroy()
            
        ttk.Label(self.legend_frame, text="图例说明:").pack(side=tk.LEFT, padx=(0, 10))
        
        if theme == "专业模式 (弱化相同)":
            tk.Label(self.legend_frame, text=" 相同代码 (灰色文字) ", bg="#f8f8f8", fg="#7a7a7a", borderwidth=1, relief="solid").pack(side=tk.LEFT, padx=5)
            tk.Label(self.legend_frame, text=" 基准文件修改 ", bg="#ffe6e6", fg="black", borderwidth=1, relief="solid").pack(side=tk.LEFT, padx=5)
            tk.Label(self.legend_frame, text=" 疑似文件修改 ", bg="#e6ffe6", fg="black", borderwidth=1, relief="solid").pack(side=tk.LEFT, padx=5)
            
            for text_widget in self.text_widgets:
                text_widget.config(bg="#f8f8f8", fg="#7a7a7a")
                text_widget.tag_configure("identical", background="#f8f8f8", foreground="#7a7a7a")
                text_widget.tag_configure("diff_bg_del", background="#ffe6e6", foreground="black")
                text_widget.tag_configure("diff_del", background="#ffb3b3", foreground="black")
                text_widget.tag_configure("diff_bg_add", background="#e6ffe6", foreground="black")
                text_widget.tag_configure("diff_add", background="#b3ffb3", foreground="black")
        else:
            tk.Label(self.legend_frame, text=" 抄袭部分 (红底) ", bg="#ffcccc", fg="black", borderwidth=1, relief="solid").pack(side=tk.LEFT, padx=5)
            tk.Label(self.legend_frame, text=" 差异部分 (白底) ", bg="white", fg="black", borderwidth=1, relief="solid").pack(side=tk.LEFT, padx=5)
            
            for text_widget in self.text_widgets:
                text_widget.config(bg="white", fg="black")
                text_widget.tag_configure("identical", background="#ffcccc", foreground="black")
                # 差异部分恢复正常白底黑字，只用细微的浅灰背景辅助提示
                text_widget.tag_configure("diff_bg_del", background="white", foreground="black")
                text_widget.tag_configure("diff_del", background="#f0f0f0", foreground="black")
                text_widget.tag_configure("diff_bg_add", background="white", foreground="black")
                text_widget.tag_configure("diff_add", background="#f0f0f0", foreground="black")
