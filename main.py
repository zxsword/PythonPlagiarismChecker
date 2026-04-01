# -*- coding: utf-8 -*-

"""
主程序入口
这是整个应用程序启动的起点。
它只做一件事：导入主应用窗口类并运行它。
"""

# 从 ui.app 模块中导入主应用程序类 PlagiarismCheckerApp
from plagiarism_checker.ui.app import PlagiarismCheckerApp

# Python 的标准写法，确保只有当这个文件被直接运行时，下面的代码才会被执行
# 如果这个文件被其他文件导入，则不会执行
if __name__ == "__main__":
    # 创建 PlagiarismCheckerApp 类的一个实例（对象）
    app = PlagiarismCheckerApp()
    
    # 调用 app 对象的 mainloop() 方法
    # 这个方法会启动 tkinter 的事件循环，让窗口显示出来并等待用户的操作（如点击按钮）
    # 程序会一直在这里运行，直到用户关闭窗口
    app.mainloop()
