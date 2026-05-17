# -*- coding: utf-8 -*-
"""
配置管理模块

负责 config.yaml 的读写。只处理非敏感配置（阈值、模型名、习题文本等）。
API Key 和代理地址等敏感信息由 secrets.py 的 SecretsManager 负责管理。
"""

import os
import threading
import yaml


# 这些字段属于敏感信息，不应出现在 config.yaml 里
_SENSITIVE_FIELDS = {'api_key', 'api_proxy'}


class ConfigManager:
    """读写 config.yaml（非敏感配置）的管理器。"""

    def __init__(self):
        # config.py 位于 plagiarism_checker/ 里，向上一层是项目根目录
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_file = os.path.join(base_dir, "config.yaml")
        self._lock = threading.Lock()

    def load(self) -> dict:
        """
        读取并返回配置字典。文件不存在或解析失败时返回空字典。
        注意：敏感字段（api_key/api_proxy）若仍在 yaml 里，会原样返回，
        由上层的 SecretsManager.migrate_from_config() 负责迁移和清除。
        """
        if not os.path.exists(self.config_file):
            return {}
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config if config else {}
        except Exception as e:
            print(f"读取配置文件失败: {e}")
            return {}

    def save(self, config_dict: dict):
        """
        将配置字典写入 config.yaml。
        会自动过滤掉敏感字段（即使传入也不会写进去）。
        """
        # 防御：过滤敏感字段，不允许敏感信息通过这里进入 yaml
        clean = {k: v for k, v in config_dict.items() if k not in _SENSITIVE_FIELDS}

        with self._lock:
            try:
                # allow_unicode=True: 中文直接显示，不转义
                # sort_keys=False: 保持定义顺序
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(clean, f, allow_unicode=True, sort_keys=False)
            except Exception as e:
                print(f"保存配置文件失败: {e}")
