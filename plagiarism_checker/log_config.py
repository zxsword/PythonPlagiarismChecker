# -*- coding: utf-8 -*-
"""
日志配置模块

统一配置程序的文件日志，使用按日轮转的 TimedRotatingFileHandler，
每天产生一个新日志文件，最多保留最近 7 天的记录。

日志文件存储在项目根目录的 logs/ 目录下（已加入 .gitignore）。

【使用方式】
在其他模块中获取 logger：
    import logging
    logger = logging.getLogger(__name__)
    logger.error("发生了错误: %s", str(e))
"""

import logging
import logging.handlers
from pathlib import Path

# 日志文件放在项目根目录的 logs/ 子目录下
_LOG_DIR = Path(__file__).parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "app.log"


def setup_logging(level: int = logging.INFO) -> None:
    """
    初始化全局日志配置，调用一次即可。

    Args:
        level: 日志级别，默认 INFO。开发时可改为 logging.DEBUG。
    """
    _LOG_DIR.mkdir(exist_ok=True)

    # TimedRotatingFileHandler: 每天午夜轮转，保留最近 7 天的日志文件
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=_LOG_FILE,
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    # 根 logger 捕获所有子 logger 的消息
    root = logging.getLogger()
    root.setLevel(level)
    # 避免重复添加（热重载 / 多次 import 时的保护）
    if not any(isinstance(h, logging.handlers.TimedRotatingFileHandler) for h in root.handlers):
        root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """快捷方式：获取以模块名命名的 logger。"""
    return logging.getLogger(name)
