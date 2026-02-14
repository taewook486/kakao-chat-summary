"""Structured logging utility for kakao-chat-summary application."""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager

from ..config.config_manager import ConfigManager


class StructuredLogger:
    """
    Structured logger with context support.

    Provides consistent logging format with timestamps, context information,
    and the ability to add contextual metadata to log records.
    """

    def __init__(self, name: str, config_manager: Optional[ConfigManager] = None):
        """
        Initialize structured logger.

        Args:
            name: Logger name (typically __name__ of calling module).
            config_manager: Optional ConfigManager instance for log directory.
        """
        self.name = name
        self.config_manager = config_manager or ConfigManager()
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """
        Set up logger with handlers and formatters.

        Returns:
            Configured logger instance.
        """
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.DEBUG)

        # Avoid adding handlers multiple times
        if logger.handlers:
            return logger

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler
        log_dir = self.config_manager.get_log_directory()
        log_file = log_dir / f"summarizer_{datetime.now().strftime('%Y%m%d')}.log"

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        return logger

    def debug(self, message: str, **context) -> None:
        """Log debug message with optional context."""
        self._log(logging.DEBUG, message, context)

    def info(self, message: str, **context) -> None:
        """Log info message with optional context."""
        self._log(logging.INFO, message, context)

    def warning(self, message: str, **context) -> None:
        """Log warning message with optional context."""
        self._log(logging.WARNING, message, context)

    def error(self, message: str, exc_info: bool = False, **context) -> None:
        """Log error message with optional context and exception info."""
        self._log(logging.ERROR, message, context, exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = False, **context) -> None:
        """Log critical message with optional context and exception info."""
        self._log(logging.CRITICAL, message, context, exc_info=exc_info)

    def _log(
        self,
        level: int,
        message: str,
        context: Dict[str, Any],
        exc_info: bool = False,
    ) -> None:
        """
        Internal logging method with context support.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            message: Log message.
            context: Optional context dictionary.
            exc_info: Whether to include exception info.
        """
        if context:
            # Append context to message
            context_str = " | " + " | ".join(f"{k}={v}" for k, v in context.items())
            message = message + context_str

        self.logger.log(level, message, exc_info=exc_info)

    @contextmanager
    def context(self, **context_kwargs):
        """
        Context manager for adding contextual metadata to logs.

        Usage:
            with logger.context(room_id=123, user="test"):
                logger.info("Processing chat")
                # All logs in this block will have room_id and user context

        Args:
            **context_kwargs: Key-value pairs to add to log context.
        """
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            for key, value in context_kwargs.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        try:
            yield
        finally:
            logging.setLogRecordFactory(old_factory)


class ColoredFormatter(logging.Formatter):
    """Console formatter with ANSI color codes for different log levels."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        """Format log record with colors."""
        levelname = record.levelname
        if levelname in self.COLORS:
            levelname_color = self.COLORS[levelname] + levelname + self.RESET
            record.levelname = levelname_color
        return super().format(record)


def get_logger(name: str) -> StructuredLogger:
    """
    Get or create a structured logger for the given name.

    Args:
        name: Logger name (typically __name__ of calling module).

    Returns:
        StructuredLogger instance.

    Example:
        from src.utils.logging import get_logger

        logger = get_logger(__name__)
        logger.info("Application started", room_id=123)
    """
    return StructuredLogger(name)
