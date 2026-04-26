# -*- coding: utf-8 -*-
"""
配置管理模块
负责统一处理 config.yaml 文件的读取与持久化保存，
将本地磁盘 I/O 逻辑从 UI 主进程中抽离。
"""

import os
import yaml

class ConfigManager:
    def __init__(self):
        # 【教学说明】如何获取项目的根目录？
        # __file__ 代表当前文件所在路径 (config.py)
        # abspath 转换为绝对路径
        # dirname 获取文件所在的文件夹 (plagiarism_checker/)
        # 再套一层 dirname 就退到了上一级目录 (即根目录)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_file = os.path.join(base_dir, "config.yaml")
        
    def load(self):
        """读取并返回配置字典，如果失败则返回空字典"""
        if os.path.exists(self.config_file):
            try:
                # 使用 safe_load 安全地读取 YAML 文件，将其转换为 Python 的字典格式
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    return config if config else {}
            except Exception as e:
                print(f"读取配置文件失败: {e}")
        return {}
        
    def save(self, config_dict):
        """将传入的字典数据安全地序列化到 YAML 文件中"""
        try:
            # allow_unicode=True 保证中文字符直接显示为中文，而不是变成 \uXXXX 这种转义码
            # sort_keys=False 保证保存的顺序和我们在字典里定义的顺序一致
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(config_dict, f, allow_unicode=True, sort_keys=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")