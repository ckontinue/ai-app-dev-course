"""日志模块 — 控制台 + 按天切割的文件"""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(name, level="INFO", log_file="logs/app.log",
                 max_bytes=10*1024*1024, backup_count=5):
    """返回配置好的 logger，同时输出到控制台和文件"""

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 控制台：简洁
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter(
        "%(levelname)-7s %(message)s"))

    # 文件：详细（时间戳 + 模块 + 行号）
    fh = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count,
        encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"))

    logger.addHandler(console)
    logger.addHandler(fh)

    return logger
