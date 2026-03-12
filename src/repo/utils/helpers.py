"""Configuration helper utilities."""

import os
import configparser
from pathlib import Path

from .paths import get_project_root
from ..core.exceptions import ConfigError


def get_config_file_path(
    relative_path: str,
    env_var: str | None = None,
) -> Path:
    """Get config file path from env var or relative path.

    Args:
        relative_path: Relative path from project root.
        env_var: Environment variable name to check first.

    Returns:
        Path to config file.
    """
    if env_var and (env_path := os.getenv(env_var)):
        return Path(env_path)

    return get_project_root() / relative_path


def get_value(
    parser: configparser.ConfigParser,
    section: str,
    key: str,
) -> str | None:
    """Get a string value from config, or None if missing."""
    if not parser.has_section(section):
        return None
    if not parser.has_option(section, key):
        return None
    value = parser.get(section, key).strip()
    if not value:
        return None
    return value


def get_int(
    parser: configparser.ConfigParser,
    section: str,
    key: str,
) -> int | None:
    """Get an integer value from config, or None if missing."""
    if not parser.has_section(section):
        return None
    if not parser.has_option(section, key):
        return None
    try:
        return parser.getint(section, key)
    except ValueError as exc:
        raise ConfigError(f"Invalid integer for {section}.{key}") from exc


def get_bool(
    parser: configparser.ConfigParser,
    section: str,
    key: str,
) -> bool | None:
    """Get a boolean value from config, or None if missing."""
    if not parser.has_section(section):
        return None
    if not parser.has_option(section, key):
        return None
    try:
        return parser.getboolean(section, key)
    except ValueError as exc:
        raise ConfigError(f"Invalid boolean for {section}.{key}") from exc


def get_env_override(env_var: str, default: str) -> str:
    """Get environment variable or return default."""
    return os.getenv(env_var, default)


def read_config_file(parser: configparser.ConfigParser, config_path: Path) -> None:
    """Read config file and raise ConfigError on failure."""
    if config_path.exists():
        try:
            parser.read(config_path)
        except configparser.Error as e:
            raise ConfigError(f"Failed to parse config: {e}") from e
