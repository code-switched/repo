"""Web configuration loading and management."""

import logging
import configparser
from pathlib import Path
from dataclasses import dataclass

from ..core.exceptions import ValidationError
from ..utils.helpers import (
    get_config_file_path,
    get_value,
    get_int,
    get_bool,
    get_env_override,
    read_config_file,
)

logger = logging.getLogger("repo.web")

WEB_CONFIG_ENV_VAR = "REPO_WEB_CONFIG_FILE"


@dataclass(frozen=True)
class ServerConfig:
    """Server configuration."""

    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False


@dataclass(frozen=True)
class WebConfig:
    """Web application configuration."""

    server: ServerConfig

    @classmethod
    def default(cls) -> "WebConfig":
        """Return default configuration."""
        return cls(server=ServerConfig())

    def validate(self) -> None:
        """Validate configuration."""
        if not 1 <= self.server.port <= 65535:
            raise ValidationError(f"Invalid server port: {self.server.port}")


def load_web_config(config_path: Path | None = None) -> WebConfig:
    """Load web configuration from config.ini file."""
    parser = configparser.ConfigParser()

    # Default search path
    if not config_path:
        config_path = get_config_file_path(
            "data/config/web/config.ini",
            "REPO_WEB_CONFIG_FILE",
        )

    read_config_file(parser, config_path)

    # Load values
    server_host = get_value(parser, "server", "host") or "127.0.0.1"
    server_port = get_int(parser, "server", "port") or 8000
    server_reload = get_bool(parser, "server", "reload") or False

    server_host = get_env_override("REPO_SERVER_HOST", server_host)
    server_port = int(get_env_override(
        "REPO_SERVER_PORT", str(server_port)
    ))
    server_reload_str = get_env_override(
        "REPO_SERVER_RELOAD", str(server_reload)
    ).lower()
    server_reload = server_reload_str in ("true", "1", "yes")

    config = WebConfig(
        server=ServerConfig(
            host=server_host,
            port=server_port,
            reload=server_reload,
        )
    )
    config.validate()
    return config
