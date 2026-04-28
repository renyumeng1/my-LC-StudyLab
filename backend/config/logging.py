"""日志配置模块
"""

import sys
from pathlib import Path
from typing import Optional
from loguru import logger

from .setting import settings


def setup_logging(
    log_level:Optional[str] = None,
    log_file:Optional[str] = None,
    rotation:Optional[str] = None,
    retention:Optional[str] = None
) -> None:
    
    log_level = log_level or settings.log_level
    log_file = log_file or settings.log_file
    rotation = rotation or settings.log_rotation
    retention = retention or settings.log_retention
    
    
    logger.remove()  # 移除默认的日志处理器
    
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level=log_level,
        colorize=True,
        backtrace=True,  # 显示完整的异常追踪
        diagnose=True,   # 显示变量值
    )
    
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)  # 确保日志目录存在
    
    
     # 添加文件日志，支持轮转和自动清理
    logger.add(
        log_file,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
        level=log_level,
        rotation=rotation,      # 文件大小达到限制时轮转
        retention=retention,    # 保留指定时间的日志
        compression="zip",      # 压缩旧日志
        backtrace=True,
        diagnose=True,
        enqueue=True,          # 异步写入，提高性能
    )
    
    logger.info(f"📝 日志系统初始化完成 - 级别: {log_level}, 文件: {log_file}")
    

def get_logger(name:str):
    """
    获取指定名称的 logger
    
    Args:
        name: logger 名称，通常使用模块的 __name__
        
    Returns:
        配置好的 logger 实例
        
    Example:
        >>> from config import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("这是一条日志")
    """
    return logger.bind(name=name)


if "pytest" not in sys.modules:
    setup_logging()  # 仅在非测试环境下初始化日志系统
    
    