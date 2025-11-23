"""
日志工具模块

该模块提供统一的日志管理功能，包括：
- 多种日志级别支持
- 控制台和文件双输出
- 日志轮转功能
- 结构化日志输出
- 彩色日志显示

遵循Google Style Guide和PEP 8规范
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler
from datetime import datetime
from enum import Enum


class LogColor(Enum):
    """日志颜色枚举类（用于终端输出）"""
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"


class ColoredFormatter(logging.Formatter):
    """
    彩色日志格式化器
    
    为不同级别的日志添加颜色，提高日志可读性
    """
    
    # 日志级别与颜色的映射
    LEVEL_COLORS = {
        logging.DEBUG: LogColor.CYAN.value,
        logging.INFO: LogColor.GREEN.value,
        logging.WARNING: LogColor.YELLOW.value,
        logging.ERROR: LogColor.RED.value,
        logging.CRITICAL: f"{LogColor.BOLD.value}{LogColor.RED.value}"
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录
        
        Args:
            record: 日志记录对象
            
        Returns:
            格式化后的日志字符串
        """
        # 获取对应级别的颜色
        color = self.LEVEL_COLORS.get(record.levelno, LogColor.WHITE.value)
        
        # 为日志级别添加颜色
        record.levelname = f"{color}{record.levelname}{LogColor.RESET.value}"
        
        # 为时间添加颜色
        record.asctime = f"{LogColor.BLUE.value}{self.formatTime(record, self.datefmt)}{LogColor.RESET.value}"
        
        # 为日志名称添加颜色
        record.name = f"{LogColor.MAGENTA.value}{record.name}{LogColor.RESET.value}"
        
        # 调用父类的格式化方法
        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """
    结构化日志格式化器
    
    将日志输出为结构化格式（JSON），便于日志分析和处理
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录为JSON格式
        
        Args:
            record: 日志记录对象
            
        Returns:
            JSON格式的日志字符串
        """
        import json
        
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # 添加额外的上下文信息
        if hasattr(record, "context"):
            log_data["context"] = record.context
        
        return json.dumps(log_data, ensure_ascii=False)


class Logger:
    """
    日志管理器类
    
    提供统一的日志接口，支持多种输出方式和格式
    """
    
    def __init__(
        self,
        name: str,
        level: str = "INFO",
        log_dir: Optional[Path] = None,
        log_file: str = "metagpt.log",
        console_output: bool = True,
        file_output: bool = True,
        colored_output: bool = True,
        structured_output: bool = False,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5
    ):
        """
        初始化日志管理器
        
        Args:
            name: 日志器名称
            level: 日志级别
            log_dir: 日志目录
            log_file: 日志文件名
            console_output: 是否输出到控制台
            file_output: 是否输出到文件
            colored_output: 是否使用彩色输出
            structured_output: 是否使用结构化输出
            max_bytes: 单个日志文件最大字节数
            backup_count: 日志文件备份数量
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self._get_log_level(level))
        self.logger.propagate = False  # 避免重复日志
        
        # 清除已有的处理器
        self.logger.handlers.clear()
        
        # 日志格式
        self.format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        self.date_format = "%Y-%m-%d %H:%M:%S"
        
        # 添加控制台处理器
        if console_output:
            self._add_console_handler(colored_output, structured_output)
        
        # 添加文件处理器
        if file_output:
            if log_dir is None:
                log_dir = Path("logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / log_file
            self._add_file_handler(log_path, structured_output, max_bytes, backup_count)
    
    def _get_log_level(self, level: str) -> int:
        """
        获取日志级别
        
        Args:
            level: 日志级别字符串
            
        Returns:
            日志级别常量
        """
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_map.get(level.upper(), logging.INFO)
    
    def _add_console_handler(self, colored: bool, structured: bool) -> None:
        """
        添加控制台处理器
        
        Args:
            colored: 是否使用彩色输出
            structured: 是否使用结构化输出
        """
        console_handler = logging.StreamHandler(sys.stdout)
        
        if structured:
            formatter = StructuredFormatter()
        elif colored:
            formatter = ColoredFormatter(self.format_string, self.date_format)
        else:
            formatter = logging.Formatter(self.format_string, self.date_format)
        
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def _add_file_handler(
        self,
        log_path: Path,
        structured: bool,
        max_bytes: int,
        backup_count: int
    ) -> None:
        """
        添加文件处理器（支持日志轮转）
        
        Args:
            log_path: 日志文件路径
            structured: 是否使用结构化输出
            max_bytes: 单个日志文件最大字节数
            backup_count: 日志文件备份数量
        """
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        if structured:
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(self.format_string, self.date_format)
        
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """
        记录DEBUG级别日志
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文信息
        """
        self._log_with_context(logging.DEBUG, message, kwargs)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """
        记录INFO级别日志
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文信息
        """
        self._log_with_context(logging.INFO, message, kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """
        记录WARNING级别日志
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文信息
        """
        self._log_with_context(logging.WARNING, message, kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """
        记录ERROR级别日志
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文信息
        """
        self._log_with_context(logging.ERROR, message, kwargs)
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """
        记录CRITICAL级别日志
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文信息
        """
        self._log_with_context(logging.CRITICAL, message, kwargs)
    
    def exception(self, message: str, **kwargs: Any) -> None:
        """
        记录异常日志（包含堆栈跟踪）
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文信息
        """
        self._log_with_context(logging.ERROR, message, kwargs, exc_info=True)
    
    def _log_with_context(
        self,
        level: int,
        message: str,
        context: Dict[str, Any],
        exc_info: bool = False
    ) -> None:
        """
        记录带上下文的日志
        
        Args:
            level: 日志级别
            message: 日志消息
            context: 上下文信息字典
            exc_info: 是否包含异常信息
        """
        # 创建LogRecord
        extra = {"context": context} if context else {}
        
        self.logger.log(level, message, exc_info=exc_info, extra=extra)
    
    def set_level(self, level: str) -> None:
        """
        动态设置日志级别
        
        Args:
            level: 日志级别字符串
        """
        self.logger.setLevel(self._get_log_level(level))
    
    def get_logger(self) -> logging.Logger:
        """
        获取原始logging.Logger对象
        
        Returns:
            logging.Logger对象
        """
        return self.logger


class LoggerFactory:
    """
    日志工厂类
    
    使用工厂模式创建和管理日志器实例，确保相同名称的日志器只创建一次
    """
    
    _loggers: Dict[str, Logger] = {}
    _default_config: Dict[str, Any] = {}
    
    @classmethod
    def set_default_config(cls, **kwargs: Any) -> None:
        """
        设置默认日志配置
        
        Args:
            **kwargs: 日志配置参数
        """
        cls._default_config.update(kwargs)
    
    @classmethod
    def get_logger(cls, name: str, **kwargs: Any) -> Logger:
        """
        获取或创建日志器实例
        
        Args:
            name: 日志器名称
            **kwargs: 日志配置参数（覆盖默认配置）
            
        Returns:
            Logger实例
        """
        if name not in cls._loggers:
            # 合并默认配置和传入的配置
            config = {**cls._default_config, **kwargs}
            cls._loggers[name] = Logger(name, **config)
        
        return cls._loggers[name]
    
    @classmethod
    def clear_loggers(cls) -> None:
        """清除所有日志器实例"""
        cls._loggers.clear()


def get_logger(name: str, **kwargs: Any) -> Logger:
    """
    便捷函数：获取日志器实例
    
    Args:
        name: 日志器名称
        **kwargs: 日志配置参数
        
    Returns:
        Logger实例
    """
    return LoggerFactory.get_logger(name, **kwargs)


def setup_logging_from_config(config: Any) -> None:
    """
    从配置对象设置全局日志配置
    
    Args:
        config: 配置对象（需要有log_config属性）
    """
    if hasattr(config, 'log_config'):
        log_cfg = config.log_config
        LoggerFactory.set_default_config(
            level=log_cfg.level.value,
            log_dir=log_cfg.log_dir,
            log_file=log_cfg.log_file,
            console_output=log_cfg.console_output,
            file_output=log_cfg.file_output,
            max_bytes=log_cfg.max_bytes,
            backup_count=log_cfg.backup_count
        )


if __name__ == "__main__":
    # 测试日志模块
    print("=== Testing Logger Module ===\n")
    
    # 创建日志器
    logger = get_logger("test_logger")
    
    # 测试不同级别的日志
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    logger.critical("This is a CRITICAL message")
    
    # 测试带上下文的日志
    logger.info("User action", user_id=123, action="login", ip="192.168.1.1")
    
    # 测试异常日志
    try:
        result = 1 / 0
    except ZeroDivisionError:
        logger.exception("Division by zero error occurred")
    
    # 测试结构化日志
    structured_logger = Logger(
        "structured_test",
        structured_output=True,
        console_output=True,
        file_output=False
    )
    structured_logger.info("Structured log message", task="test", status="completed")
    
    print("\n=== Logger Module Test Completed ===")