"""CLI configuration loading and management."""

import logging
import configparser
from pathlib import Path
from dataclasses import dataclass

from ..core.exceptions import ValidationError
from ..utils.helpers import (
    get_config_file_path,
    get_value,
    get_env_override,
    read_config_file,
)

logger = logging.getLogger("repo")


@dataclass(frozen=True)
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"


@dataclass(frozen=True)
class CLIConfig:
    """CLI application configuration."""

    logging: LoggingConfig

    @classmethod
    def default(cls) -> "CLIConfig":
        """Return default configuration."""
        return cls(logging=LoggingConfig())

    def validate(self) -> None:
        """Validate configuration."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.logging.level.upper() not in valid_levels:
            raise ValidationError(f"Invalid logging level: {self.logging.level}")


def load_config(config_path: Path | None = None) -> CLIConfig:
    """Load CLI configuration from file and environment."""
    parser = configparser.ConfigParser()

    # Default search path
    if not config_path:
        config_path = get_config_file_path(
            "data/config/cli/config.ini",
            "REPO_CLI_CONFIG_FILE",
        )

    read_config_file(parser, config_path)

    # Load values
    logging_level = get_value(parser, "logging", "level") or "INFO"
    logging_level = get_env_override("REPO_LOGGING_LEVEL", logging_level)

    config = CLIConfig(
        logging=LoggingConfig(level=logging_level),
    )
    config.validate()
    return config
