"""Unit tests for CLI config loading."""

from __future__ import annotations

import pytest

from repo.cli import config as cli_config
from repo.core.exceptions import ValidationError


def test_load_config_uses_defaults_when_config_file_is_missing(tmp_path) -> None:
    """Missing config file should resolve to default logging level."""
    config = cli_config.load_config(config_path=tmp_path / "missing.ini")
    assert config.logging.level == "INFO"


def test_load_config_reads_logging_level_from_file(tmp_path) -> None:
    """Config parser value should populate logging level."""
    config_path = tmp_path / "cli.ini"
    config_path.write_text("[logging]\nlevel = debug\n", encoding="utf-8")

    config = cli_config.load_config(config_path=config_path)
    assert config.logging.level == "debug"


def test_load_config_env_override_wins(monkeypatch, tmp_path) -> None:
    """Environment variable should override config file value."""
    config_path = tmp_path / "cli.ini"
    config_path.write_text("[logging]\nlevel = info\n", encoding="utf-8")
    monkeypatch.setenv("REPO_LOGGING_LEVEL", "WARNING")

    config = cli_config.load_config(config_path=config_path)
    assert config.logging.level == "WARNING"


def test_load_config_invalid_level_raises(monkeypatch, tmp_path) -> None:
    """Invalid logging levels should fail fast with ValidationError."""
    config_path = tmp_path / "cli.ini"
    config_path.write_text("[logging]\nlevel = info\n", encoding="utf-8")
    monkeypatch.setenv("REPO_LOGGING_LEVEL", "LOUD")

    with pytest.raises(ValidationError, match="Invalid logging level"):
        cli_config.load_config(config_path=config_path)
