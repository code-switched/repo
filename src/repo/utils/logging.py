"""Logging configuration."""

import os
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

from .paths import get_logs_dir


def configure_logging(
    name: str = "app",
    level: str | None = None,
    log_dir: Path | None = None,
) -> logging.Logger:
    """Configure and return the application logger."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    if log_dir is None:
        log_dir = get_logs_dir()

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{name}.log"

    level_str = level or os.getenv("LOG_LEVEL", "INFO")
    log_level = getattr(logging, level_str.upper(), logging.INFO)

    handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(log_level)
    logger.propagate = False

    return logger
