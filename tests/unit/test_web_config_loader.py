"""Unit tests for web config loading."""

from __future__ import annotations

import pytest

from repo.core.exceptions import ValidationError
from repo.web import config as web_config


def test_load_web_config_uses_defaults_when_missing(tmp_path) -> None:
    """Missing config files should return default server values."""
    config = web_config.load_web_config(config_path=tmp_path / "missing.ini")

    assert config.server.host == "127.0.0.1"
    assert config.server.port == 8000
    assert config.server.reload is False


def test_load_web_config_reads_values_from_file(tmp_path) -> None:
    """Config parser values should map into server config."""
    config_path = tmp_path / "web.ini"
    config_path.write_text(
        "[server]\n"
        "host = 0.0.0.0\n"
        "port = 9000\n"
        "reload = true\n",
        encoding="utf-8",
    )

    config = web_config.load_web_config(config_path=config_path)
    assert config.server.host == "0.0.0.0"
    assert config.server.port == 9000
    assert config.server.reload is True


def test_load_web_config_applies_env_overrides(monkeypatch, tmp_path) -> None:
    """Environment variables should override file values."""
    config_path = tmp_path / "web.ini"
    config_path.write_text("[server]\nhost = 0.0.0.0\nport = 9000\nreload = false\n", encoding="utf-8")
    monkeypatch.setenv("REPO_SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("REPO_SERVER_PORT", "7777")
    monkeypatch.setenv("REPO_SERVER_RELOAD", "yes")

    config = web_config.load_web_config(config_path=config_path)
    assert config.server.host == "127.0.0.1"
    assert config.server.port == 7777
    assert config.server.reload is True


def test_load_web_config_invalid_port_raises(monkeypatch, tmp_path) -> None:
    """Out-of-range env port should fail validation."""
    config_path = tmp_path / "web.ini"
    config_path.write_text("[server]\nport = 8000\n", encoding="utf-8")
    monkeypatch.setenv("REPO_SERVER_PORT", "70000")

    with pytest.raises(ValidationError, match="Invalid server port"):
        web_config.load_web_config(config_path=config_path)
