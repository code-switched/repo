"""Path resolution utilities."""

import os
from pathlib import Path


def get_project_root() -> Path:
    """Find project root by looking for pyproject.toml or .git."""
    current = Path(__file__).resolve()

    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
        if (parent / ".git").exists():
            return parent

    return Path.cwd()


def get_data_dir() -> Path:
    """Get the data directory."""
    env_value = os.getenv("DATA_DIR")
    if env_value:
        return Path(env_value)

    return get_project_root() / "data"


def get_config_dir() -> Path:
    """Get the config directory."""
    env_value = os.getenv("CONFIG_DIR")
    if env_value:
        return Path(env_value)

    return get_data_dir() / "config"


def get_logs_dir() -> Path:
    """Get the logs directory."""
    env_value = os.getenv("LOG_DIR")
    if env_value:
        return Path(env_value)

    return get_data_dir() / "logs"
