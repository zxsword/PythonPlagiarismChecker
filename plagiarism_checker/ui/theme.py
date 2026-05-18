# -*- coding: utf-8 -*-
"""
集中管理 Tk 桌面端的所有颜色常量。

之前各窗口（comparison_window、widgets、dialogs）里硬编码了一堆 #RRGGBB 字面量，
想统一调风格要全局搜替换。集中到这里后改一处就改全。

注意：本模块只管 Tkinter 桌面端的颜色。导出 HTML 报告 (exporter.py) 用的是独立的
CSS 主题（运行在浏览器里），不放在这里以免变成 god-module。
"""

# 通用 UI 配色（"专业感"）。给状态栏、表格、代码框等使用。
PROFESSIONAL_THEME = {
    'select_bg':       '#0078D7',   # Windows 选中蓝
    'select_fg':       'white',
    'text_secondary':  '#555555',   # 状态栏耗时、弹窗辅助说明等次要文字
    'line_number_bg':  '#f0f0f0',   # 代码框旁的行号槽
    'code_bg':         '#f8f8f8',   # 代码文本框默认背景
    'code_muted':      '#7a7a7a',   # "相同"行的弱化文字色
    'panel_bg':        '#fdfdfd',   # 报告/源码弹窗的背景
    'paper_bg':        '#ffffff',   # 表格 evenrow / 评语区
    'row_alt_bg':      '#f9f9f9',   # 表格 oddrow
    'error_fg':        '#d32f2f',   # 错误 / 高危行
    'success_fg':      '#2e7d32',   # 成功 / 完成
}

# 对比窗口专用：抄袭高亮配色
PLAG_THEME = {
    # 专业模式：弱化相同代码，让差异一眼可见
    'basis_diff_bg':   '#ffe6e6',   # 基准文件的修改行：淡红底
    'basis_diff_hl':   '#ffb3b3',   # 基准文件行内差异字符：深红高亮
    'sus_diff_bg':     '#e6ffe6',   # 疑似文件的修改行：淡绿底
    'sus_diff_hl':     '#b3ffb3',   # 疑似文件行内差异字符：深绿高亮

    # 查重模式：相反的强调方式——把相同（=疑似抄袭）部分高亮
    'plag_same_bg':    '#ffcccc',   # 相同/抄袭行的红底警示
    'plag_diff_hint':  '#f0f0f0',   # 查重模式下差异行的浅灰提示
}
