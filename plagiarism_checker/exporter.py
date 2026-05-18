# -*- coding: utf-8 -*-
"""
数据导出模块
负责将分析与批改的结果格式化并导出为 HTML 或 CSV 文件。
将繁杂的字符串拼接逻辑从 UI 主应用中剥离。
"""

import csv
import time
import os
from string import Template
from pathlib import Path

# HTML 模板文件与本模块同目录
_TEMPLATE_PATH = Path(__file__).parent / "report_template.html"

def _load_template() -> Template:
    """读取 HTML 模板文件，返回 string.Template 对象。"""
    with open(_TEMPLATE_PATH, encoding='utf-8') as f:
        return Template(f.read())

def export_csv_report(file_path, current_tab, tree_to_export, ai_results_map):
    """导出纯文本 CSV 报告"""
    # 打开文件准备写入。
    # encoding='utf-8-sig': 带有 BOM 头的 UTF-8 编码，防止用 Excel 打开时中文变成乱码。
    # newline='': 防止在 Windows 系统下每次写入多出一个空行。
    with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        if current_tab == 0:
            # 先写第一行（表头）
            writer.writerow(["分组文件数", "最高相似度", "疑似原创文件", "所有成员"])
            # 遍历表格中的每一行数据，逐行写入
            for item_id in tree_to_export.get_children():
                writer.writerow(tree_to_export.item(item_id)['values'])
        else:
            writer.writerow(["文件名", "评分", "评分模式", "批改状态", "详细评语"])
            for item_id in tree_to_export.get_children():
                values = tree_to_export.item(item_id)['values']
                name, score, method, review = ai_results_map.get(item_id, ("", "-", "", ""))
                writer.writerow([name, score, method, values[2], review])

def export_html_report(file_path, current_tab, tree_to_export, ai_results_map):
    """生成带有 CSS 排版和高亮表格的精美 HTML 网页报告。

    报告结构由 report_template.html 决定，本函数只负责填充数据。
    """
    tmpl = _load_template()

    if current_tab == 0:
        title = "🔍 代码抄袭检测报告"
        table_header = "<tr><th>分组文件数</th><th>最高相似度</th><th>疑似原创文件</th><th>所有成员</th></tr>"
        table_rows = _build_plag_rows(tree_to_export)
    else:
        title = "📝 AI 自动批改报告"
        table_header = "<tr><th>文件名</th><th>评分</th><th>状态</th><th>详细评语</th></tr>"
        table_rows = _build_grading_rows(tree_to_export, ai_results_map)

    html = tmpl.substitute(
        title=title,
        generated_at=time.strftime('%Y-%m-%d %H:%M:%S'),
        table_header=table_header,
        table_rows=table_rows,
    )

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html)

def _build_plag_rows(tree) -> str:
    """构建抄袭检测结果的 HTML 表格行。"""
    rows = []
    for item_id in tree.get_children():
        v = tree.item(item_id)['values']
        sim_val = str(v[1]).replace('%', '')
        color = ""
        if sim_val.replace('.', '', 1).isdigit() and float(sim_val) >= 90:
            color = "color: #e74c3c; font-weight: bold;"
        rows.append(
            f"<tr>"
            f"<td>{v[0]}</td>"
            f"<td style='{color}'>{v[1]}</td>"
            f"<td>{v[2]}</td>"
            f"<td>{v[3]}</td>"
            f"</tr>"
        )
    return "\n    ".join(rows)

def _build_grading_rows(tree, ai_results_map) -> str:
    """构建 AI 批改结果的 HTML 表格行。"""
    rows = []
    for item_id in tree.get_children():
        v = tree.item(item_id)['values']
        name, score, method, review = ai_results_map.get(item_id, ("", "-", "", ""))
        if str(score).isdigit() and int(score) < 60:
            color = "color: #e74c3c; font-weight: bold;"
        elif str(score).isdigit() and int(score) >= 90:
            color = "color: #27ae60; font-weight: bold;"
        else:
            color = ""
        rows.append(
            f"<tr>"
            f"<td width='15%'><b>{name}</b></td>"
            f"<td width='10%' style='{color}; font-size: 18px;'>{score}</td>"
            f"<td width='15%'>{v[2]}<br><small style='color:gray;'>{method}</small></td>"
            f"<td><div class='review'>{review}</div></td>"
            f"</tr>"
        )
    return "\n    ".join(rows)
