"""Core exceptions for the application."""


class AppError(Exception):
    """Base class for all application errors."""


class ConfigError(AppError):
    """Configuration related errors."""


class ValidationError(AppError):
    """Validation errors."""


class CommandError(AppError):
    """CLI command related errors."""
