# -*- coding: utf-8 -*-
"""
长任务调度模块

把"开始查重 / 自动批改"这条长耗时流程的所有协调逻辑（线程启动、取消、ETA 秒表、
任务结束后的 UI 写回）从主窗口 PlagiarismCheckerApp 中拆出来，让 app.py 专注于
窗口构建和对话框触发。

设计上仍然需要持有 app 引用以读写 Tk 变量、控件状态——这是 GUI 应用的固有耦合。
但 app.py 不再需要看到 cancel_event / is_running / start_time / combined_task 这些
中间状态，可以瘦身约 100 行。
"""

import os
import time
import threading
import tkinter as tk

from .analysis import find_suspicious_pairs, find_plagiarism_groups, detect_original_source
from .grader import AutoGrader


class TaskRunner:
    """
    驱动主窗口的"开始运行"按钮。负责：
    - 维护 is_running / cancel_event / start_time（之前直接挂在 app 上）
    - 启动后台 combined_task 线程
    - 通过 self.app.after(0, ...) 把 UI 写回派发到主线程
    """
    def __init__(self, app):
        self.app = app
        self.is_running = False
        self.cancel_event = threading.Event()
        self.start_time = 0.0

    # ---------- 用户入口 ----------

    def start(self):
        """对应原 PlagiarismCheckerApp.run_check"""
        if self.is_running:
            self.app.status_text.set("任务正在运行中，请勿重复点击，请耐心等待...")
            return

        self.is_running = True
        self.cancel_event.clear()
        self.app.start_btn.config(state=tk.DISABLED)
        self.app.cancel_btn.config(state=tk.NORMAL)
        self.start_time = time.time()
        self.app.time_text.set("耗时: 00:00")
        self._update_timer()
        self.app.clear_results()

        if not self.app.selected_files:
            self._abort("错误: 请先添加需要检查的代码文件。")
            return

        run_plag = self.app.enable_plag.get()
        run_grading = self.app.enable_grading.get()
        grading_method = self.app.grading_method.get()

        if not run_plag and not run_grading:
            self._abort("错误: 请至少勾选一项运行任务。")
            return

        files_to_check = self.app.selected_files
        if run_plag and len(files_to_check) < 2:
            self._abort("错误: 抄袭检测至少需要两个代码文件。")
            return

        self.app.status_text.set("正在初始化任务...")
        if run_grading:
            self.app.progress.config(mode='determinate', maximum=len(files_to_check), value=0)
        else:
            self.app.progress.config(mode='indeterminate')
        self.app.progress.pack(side=tk.RIGHT, padx=10)
        if not run_grading:
            self.app.progress.start()
        self.app.update_idletasks()

        # ⚠️ 主线程提取所有 Tk 变量，避免后台线程触发 Tcl 解释器死锁
        params = {
            'files_to_check': files_to_check,
            'threshold_ratio': self.app.threshold.get() / 100.0,
            'is_advanced': self.app.advanced_mode.get(),
            'run_plag': run_plag,
            'run_grading': run_grading,
            'grading_method': grading_method,
            'require_suggestions': self.app.require_suggestions.get(),
            'api_key': self.app.api_key.get().strip(),
            'api_base': self.app.api_base.get().strip(),
            'api_model': self.app.api_model.get().strip(),
            'local_model': self.app.local_model.get().strip(),
            'api_proxy': self.app.api_proxy.get().strip(),
            'min_interval': self.app.api_min_interval,
        }
        threading.Thread(target=self._combined_task, args=(params,), daemon=True).start()

    def cancel(self):
        """对应原 cancel_check"""
        if self.is_running:
            self.cancel_event.set()
            self.app.status_text.set("正在安全中止任务，请稍候...")
            self.app.cancel_btn.config(state=tk.DISABLED)

    # ---------- 内部 ----------

    def _abort(self, message):
        """启动阶段参数校验失败的快速退出。"""
        self.app.status_text.set(message)
        self.is_running = False

    def _update_timer(self):
        """递归更新耗时秒表，is_running=False 时自动停止。"""
        if self.is_running:
            elapsed = int(time.time() - self.start_time)
            m, s = divmod(elapsed, 60)
            self.app.time_text.set(f"耗时: {m:02d}:{s:02d}")
            self.app.after(1000, self._update_timer)

    def _combined_task(self, params):
        """后台线程主体：依次跑抄袭检测 + 自动批改"""
        try:
            suspicious_pairs = []
            errors = {}

            # --- 1. 抄袭检测 ---
            if params['run_plag']:
                def plag_prog(c, t, stage):
                    label = "正在预处理文件..." if stage == "标准化" else "正在进行多进程查重比对..."
                    self.app.after(0, lambda: self.app.status_text.set(f"{label} {c}/{t}"))

                suspicious_pairs, errors = find_suspicious_pairs(
                    params['files_to_check'], params['threshold_ratio'], params['is_advanced'],
                    plag_prog, self.cancel_event
                )

            # --- 2. 自动批改 ---
            if params['run_grading'] and not self.cancel_event.is_set():
                graded_count = [0]
                total_files = len(params['files_to_check'])

                def status_cb(msg):
                    self.app.after(0, self.app.status_text.set, f"{msg} ({graded_count[0]}/{total_files})")

                def progress_cb():
                    graded_count[0] += 1
                    self.app.after(0, self.app.progress.step)
                    self.app.after(0, self.app.status_text.set, f"当前批改进度... ({graded_count[0]}/{total_files})")

                def result_cb(file_path, score, method, status, review, is_error):
                    if file_path == "ALL":
                        self.app.after(0, self.app._add_single_ai_result, "", score, method, status, review, True, "系统环境错误")
                    else:
                        self.app.after(0, self.app._add_single_ai_result, file_path, score, method, status, review, is_error)

                grader = AutoGrader(
                    grading_method=params['grading_method'],
                    files_to_check=params['files_to_check'],
                    exercise_text=self.app.exercise_text,
                    require_suggestions=params['require_suggestions'],
                    api_key=params['api_key'],
                    api_base=params['api_base'],
                    api_model=params['api_model'],
                    local_model=params['local_model'],
                    api_proxy=params['api_proxy'],
                    status_cb=status_cb,
                    progress_cb=progress_cb,
                    result_cb=result_cb,
                    cancel_event=self.cancel_event,
                    min_interval=params['min_interval'],
                )
                grader.run()

            # 执行完毕，安全通知主线程更新 UI
            self.app.after(0, self._finish, params['run_plag'], params['run_grading'], suspicious_pairs, errors)

        except Exception as e:
            # 防止后台线程"静默死亡"，把所有报错推到前台状态栏
            self.app.after(0, self.app.status_text.set, f"发生致命后台崩溃: {str(e)}")
            self.app.after(0, self.app.progress.stop)
            self.app.after(0, self.app.progress.pack_forget)
            self.is_running = False

    def _finish(self, run_plag, run_grading, suspicious_pairs, errors):
        """对应原 _update_ui_after_task：主线程渲染最终结果"""
        self.app.progress.stop()
        self.app.progress.pack_forget()
        self.is_running = False
        self.app.start_btn.config(state=tk.NORMAL)
        self.app.cancel_btn.config(state=tk.DISABLED)

        # --- 1. 更新查重结果 ---
        if run_plag:
            if suspicious_pairs:
                groups = find_plagiarism_groups(suspicious_pairs)
                if groups:
                    for group, max_sim in groups:
                        original_file, scores = detect_original_source(group)
                        original_name = os.path.basename(original_file) if original_file else "未知"
                        members = ", ".join([os.path.basename(f) for f in group])
                        sim_str = f"{max_sim * 100:.1f}%"

                        tags = ('evenrow' if len(self.app.result_tree.get_children()) % 2 == 0 else 'oddrow',)
                        if max_sim >= 0.90:
                            tags = tags + ('high_risk',)

                        item_id = self.app.result_tree.insert('', tk.END, values=(len(group), sim_str, original_name, members), tags=tags)
                        self.app.suspicious_pairs_map[item_id] = (group, original_file)

            # 没找到任何互相抄袭：插一行 "未发现抄袭" 的友好提示
            if not self.app.result_tree.get_children() and not self.cancel_event.is_set():
                threshold_str = f"{self.app.threshold.get()}%"
                self.app.result_tree.insert('', tk.END, values=("-", "-", "太棒了！未发现抄袭", f"所有文件的相似度均低于设定阈值 ({threshold_str})"), tags=('success',))
            self.app.notebook.select(self.app.tab_plag)

        # --- 2. 更新状态栏 ---
        status_msg = "任务已中止。" if self.cancel_event.is_set() else "运行结束。"
        if run_plag:
            status_msg += f" 发现 {len(self.app.result_tree.get_children())} 组疑似抄袭。"
        if run_grading:
            status_msg += " 自动批改已完成。"
        self.app.status_text.set(status_msg)
