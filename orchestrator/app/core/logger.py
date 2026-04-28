"""Loguru 日志统一配置，业务代码 `from app.core.logger import logger`。"""
from __future__ import annotations

import sys

from loguru import logger

logger.remove()
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<7}</level> | "
           "<cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    enqueue=True,
)

__all__ = ["logger"]
