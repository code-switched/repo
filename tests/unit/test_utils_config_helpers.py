"""Unit tests for utility config/path helpers."""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

from repo.core.exceptions import ConfigError
from repo.utils import helpers
from repo.utils import paths


def test_get_value_returns_none_for_missing_section_or_key() -> None:
    """String reader should return None when section/key is absent."""
    parser = configparser.ConfigParser()
    parser.read_dict({"logging": {"level": "INFO"}})

    assert helpers.get_value(parser, "missing", "level") is None
    assert helpers.get_value(parser, "logging", "missing") is None


def test_get_int_and_get_bool_raise_on_invalid_values() -> None:
    """Typed readers should raise ConfigError for invalid values."""
    parser = configparser.ConfigParser()
    parser.read_dict({"server": {"port": "not-an-int", "reload": "sometimes"}})

    with pytest.raises(ConfigError, match="Invalid integer"):
        helpers.get_int(parser, "server", "port")

    with pytest.raises(ConfigError, match="Invalid boolean"):
        helpers.get_bool(parser, "server", "reload")


def test_read_config_file_raises_for_parse_errors(tmp_path) -> None:
    """Malformed config files should raise ConfigError."""
    config_path = tmp_path / "broken.ini"
    config_path.write_text("broken_line_without_section=true", encoding="utf-8")
    parser = configparser.ConfigParser()

    with pytest.raises(ConfigError, match="Failed to parse config"):
        helpers.read_config_file(parser, config_path)


def test_get_config_file_path_prefers_env_override(monkeypatch, tmp_path) -> None:
    """Env override should take precedence over relative config path."""
    env_path = tmp_path / "custom.ini"
    monkeypatch.setenv("REPO_TEST_CONFIG", str(env_path))

    resolved = helpers.get_config_file_path("data/config/cli/config.ini", "REPO_TEST_CONFIG")
    assert resolved == env_path


def test_paths_use_environment_overrides(monkeypatch, tmp_path) -> None:
    """Data/config/log directories should honor explicit env vars."""
    data_dir = tmp_path / "data-dir"
    config_dir = tmp_path / "cfg-dir"
    logs_dir = tmp_path / "logs-dir"

    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("LOG_DIR", str(logs_dir))

    assert paths.get_data_dir() == data_dir
    assert paths.get_config_dir() == config_dir
    assert paths.get_logs_dir() == logs_dir


def test_get_project_root_falls_back_to_cwd(monkeypatch, tmp_path) -> None:
    """Root resolver should fall back to cwd when marker files are absent."""
    class FakeResolvedPath:
        @property
        def parents(self):  # noqa: D401
            return [tmp_path / "a", tmp_path / "b"]

    monkeypatch.setattr(Path, "resolve", lambda _self: FakeResolvedPath())
    monkeypatch.chdir(tmp_path)

    assert paths.get_project_root() == tmp_path
