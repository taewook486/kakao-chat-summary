"""Custom exception hierarchy for kakao-chat-summary application."""

from typing import Optional


class AppException(Exception):
    """
    Base exception for all application errors.

    All custom exceptions inherit from this class to enable
    consistent error handling across the application.
    """

    def __init__(self, message: str, details: Optional[dict] = None):
        """
        Initialize application exception.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error context.
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return error message."""
        return self.message


class DatabaseException(AppException):
    """Exception raised for database-related errors."""

    def __init__(
        self,
        message: str,
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        Initialize database exception.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error context.
            original_error: The original exception that caused this error.
        """
        super().__init__(message, details)
        self.original_error = original_error

    def __str__(self) -> str:
        """Return error message with original error info if available."""
        if self.original_error:
            return f"{self.message} (Caused by: {type(self.original_error).__name__})"
        return self.message


class FileOperationException(AppException):
    """Exception raised for file operation errors."""

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        """
        Initialize file operation exception.

        Args:
            message: Human-readable error message.
            file_path: Path to the file that caused the error.
            details: Optional dictionary with additional error context.
        """
        super().__init__(message, details)
        self.file_path = file_path

    def __str__(self) -> str:
        """Return error message with file path if available."""
        if self.file_path:
            return f"{self.message} (File: {self.file_path})"
        return self.message


class LLMException(AppException):
    """Exception raised for LLM-related errors."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        """
        Initialize LLM exception.

        Args:
            message: Human-readable error message.
            provider: LLM provider that caused the error.
            details: Optional dictionary with additional error context.
        """
        super().__init__(message, details)
        self.provider = provider

    def __str__(self) -> str:
        """Return error message with provider info if available."""
        if self.provider:
            return f"{self.message} (Provider: {self.provider})"
        return self.message


class ConfigurationException(AppException):
    """Exception raised for configuration-related errors."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        """
        Initialize configuration exception.

        Args:
            message: Human-readable error message.
            config_key: Configuration key that caused the error.
            details: Optional dictionary with additional error context.
        """
        super().__init__(message, details)
        self.config_key = config_key

    def __str__(self) -> str:
        """Return error message with config key if available."""
        if self.config_key:
            return f"{self.message} (Config: {self.config_key})"
        return self.message


class ValidationException(AppException):
    """Exception raised for validation errors."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        """
        Initialize validation exception.

        Args:
            message: Human-readable error message.
            field: Field that failed validation.
            details: Optional dictionary with additional error context.
        """
        super().__init__(message, details)
        self.field = field

    def __str__(self) -> str:
        """Return error message with field info if available."""
        if self.field:
            return f"{self.message} (Field: {self.field})"
        return self.message


class ParseException(AppException):
    """Exception raised for parsing errors."""

    def __init__(
        self,
        message: str,
        line_number: Optional[int] = None,
        details: Optional[dict] = None,
    ):
        """
        Initialize parse exception.

        Args:
            message: Human-readable error message.
            line_number: Line number where parsing failed.
            details: Optional dictionary with additional error context.
        """
        super().__init__(message, details)
        self.line_number = line_number

    def __str__(self) -> str:
        """Return error message with line number if available."""
        if self.line_number:
            return f"{self.message} (Line: {self.line_number})"
        return self.message
