# -*- coding: utf-8 -*-
"""
密钥管理模块

将 API Key、代理地址等敏感信息与普通配置彻底分开存储。
敏感信息写入 .env 文件（已加入 .gitignore），绝不进入版本控制。

读取优先级（高到低）：
  1. 系统进程级环境变量——适合 CI/服务器等多机环境
  2. 项目根目录的 .env 文件——日常本地开发的推荐方式
  3. 旧版 config.yaml 遗留字段——仅启动一次自动迁移，之后自动清除
"""

import os
import threading

# 环境变量名带项目前缀，避免与系统其他工具的同名变量冲突
_KEY_API_KEY = "PLAGIARISM_API_KEY"
_KEY_API_PROXY = "PLAGIARISM_API_PROXY"


class SecretsManager:
    """负责 .env 文件的读写与旧配置的自动迁移。"""

    def __init__(self):
        # secrets.py 位于 plagiarism_checker/ 里，两层 dirname 向上到项目根目录
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._env_path = os.path.join(base_dir, ".env")
        self._lock = threading.Lock()
        # 启动时将 .env 注入进程环境变量
        self._load_dotenv()

    def _load_dotenv(self):
        """
        解析 .env 文件，将键值对注入 os.environ。
        使用 setdefault 确保系统已有的环境变量不被 .env 覆盖。
        """
        if not os.path.exists(self._env_path):
            return
        with open(self._env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和以 # 开头的注释行
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key = key.strip()
                # 剥去值两侧可能存在的单引号或双引号
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)

    def get_api_key(self) -> str:
        """返回 API Key（来源：系统环境变量 或 .env 文件）。"""
        return os.environ.get(_KEY_API_KEY, "")

    def get_api_proxy(self) -> str:
        """返回代理地址（来源：系统环境变量 或 .env 文件）。"""
        return os.environ.get(_KEY_API_PROXY, "")

    def save(self, api_key: str, api_proxy: str):
        """
        将 API Key 和代理地址写回 .env 文件，并同步到当前进程的环境变量。

        只更新/新增这两个字段，.env 中其他行原样保留。
        """
        with self._lock:
            # 读取 .env 中的其他行（过滤掉我们将要重写的两个字段）
            existing_lines = []
            if os.path.exists(self._env_path):
                with open(self._env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        stripped = line.strip()
                        if (stripped.startswith(_KEY_API_KEY + '=') or
                                stripped.startswith(_KEY_API_PROXY + '=')):
                            continue
                        existing_lines.append(line.rstrip('\n'))

            # 写入更新后的字段
            existing_lines.append(f"{_KEY_API_KEY}={api_key}")
            existing_lines.append(f"{_KEY_API_PROXY}={api_proxy}")

            with open(self._env_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(existing_lines) + '\n')

            # 同步更新当前进程的环境变量，保证本次运行立即生效
            os.environ[_KEY_API_KEY] = api_key
            os.environ[_KEY_API_PROXY] = api_proxy

    def migrate_from_config(self, config_dict: dict) -> tuple:
        """
        检测旧 config.yaml 中是否遗留了敏感字段。
        若有则迁移到 .env 并从字典中删除，避免旧密钥长期留在 yaml 里。

        Args:
            config_dict: ConfigManager.load() 返回的原始字典（可能含旧字段）。

        Returns:
            tuple: (清理后的 config_dict，是否发生了迁移 bool)
        """
        old_key = config_dict.pop('api_key', None)
        old_proxy = config_dict.pop('api_proxy', None)

        if not (old_key or old_proxy):
            return config_dict, False

        # 迁移时优先保留已存在的环境变量值（避免覆盖用户手动设置的系统变量）
        self.save(
            api_key=old_key if old_key else self.get_api_key(),
            api_proxy=old_proxy if old_proxy else self.get_api_proxy(),
        )
        return config_dict, True
