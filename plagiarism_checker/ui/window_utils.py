# -*- coding: utf-8 -*-
"""
Toplevel 窗口的通用工具函数。
"""

def center_window(toplevel):
    """
    把指定的 Toplevel 窗口居中显示。

    优先以父窗口为基准居中；若父窗口不存在或还没显示，退回到屏幕中央。

    需要在控件 pack 完成后再调用——否则 winfo_width() 拿到的是 1（控件还没渲染，
    没有"自然尺寸"可言）。常见调用位置是 __init__ 末尾、wait_window 之前。
    """
    toplevel.update_idletasks()
    w = toplevel.winfo_width()
    h = toplevel.winfo_height()
    parent = toplevel.master

    if parent is not None and parent.winfo_viewable():
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
    else:
        sw = toplevel.winfo_screenwidth()
        sh = toplevel.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2

    # 只设位置，不动尺寸，让之前 geometry("WxH") 设的宽高继续生效
    toplevel.geometry(f"+{x}+{y}")
