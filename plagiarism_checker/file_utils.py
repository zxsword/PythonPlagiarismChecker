# -*- coding: utf-8 -*-
"""
文件操作辅助模块
负责处理独立的文件 I/O 逻辑，如合并多份代码文件等。
将单纯的文件读写操作从 UI 主进程中剥离。
"""

import os
import time

def merge_files(file_list, save_path):
    """将列表中的多个文件内容合并写入到指定的保存路径中。"""
    # 'w' 模式代表覆盖写入。如果目标位置已经有同名文件，会被清空重写。
    with open(save_path, 'w', encoding='utf-8') as outfile:
        outfile.write(f"# === 作业合并文件 ===\n# 共包含 {len(file_list)} 份代码\n# 合并时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        for file_path in file_list:
            file_name = os.path.basename(file_path)
            
            # 构建巨大且醒目的分隔符（使用注释符号 #，保证合并后的文件不报语法红线）
            separator = "\n\n" + "#" * 80 + "\n"
            separator += f"#{' ' * 20}>>> 原始文件: {file_name} <<<\n"
            separator += "#" * 80 + "\n\n"
            
            outfile.write(separator)
            try:
                # errors='replace' 是一个非常有用的防御性编程技巧。
                # 如果读取的文件里混入了非 UTF-8 的乱码字符，会被静默替换成问号 '?'，从而防止程序直接报错崩溃。
                with open(file_path, 'r', encoding='utf-8', errors='replace') as infile:
                    outfile.write(infile.read())
            except Exception as e:
                outfile.write(f"# [读取失败]: {e}\n")
    return len(file_list)