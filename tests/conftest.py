"""Shared pytest fixtures."""

import pytest


@pytest.fixture
def mock_config(tmp_path):
    """Provide a temporary config file path."""
    return tmp_path / "config.ini"
