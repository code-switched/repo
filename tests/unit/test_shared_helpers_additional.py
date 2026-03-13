"""Additional unit tests for shared CLI helpers."""

from __future__ import annotations

import pytest

from repo.cli.commands import _shared as shared
from repo.core.exceptions import CommandError


def test_prompt_path_non_tty_normalizes_quotes(monkeypatch) -> None:
    """Non-TTY path prompt should return stripped, unquoted values."""
    monkeypatch.setattr(shared, "supports_path_completion", lambda: False)
    monkeypatch.setattr("builtins.input", lambda _prompt: ' "~/code/tools" ')

    value = shared.prompt_path(" > ")
    assert value == "~/code/tools"


def test_prompt_path_non_tty_allows_empty_when_requested(monkeypatch) -> None:
    """Optional path prompt should allow blank values."""
    monkeypatch.setattr(shared, "supports_path_completion", lambda: False)
    monkeypatch.setattr("builtins.input", lambda _prompt: "   ")

    value = shared.prompt_path(" > ", allow_empty=True)
    assert value == ""


def test_prompt_path_non_tty_requires_value_by_default(monkeypatch) -> None:
    """Required path prompt should fail when input is empty."""
    monkeypatch.setattr(shared, "supports_path_completion", lambda: False)
    monkeypatch.setattr("builtins.input", lambda _prompt: "")

    with pytest.raises(CommandError, match="required value"):
        shared.prompt_path(" > ")


def test_normalize_repo_type_accepts_aliases_and_rejects_unknown() -> None:
    """Repo type normalization should map aliases and reject unknown values."""
    assert shared.normalize_repo_type("org") == "org"
    assert shared.normalize_repo_type("organization") == "org"
    assert shared.normalize_repo_type("user") == "user"

    with pytest.raises(CommandError, match="Invalid repo type"):
        shared.normalize_repo_type("team")


def test_normalize_visibility_accepts_known_values_and_rejects_unknown() -> None:
    """Visibility normalization should only allow public/private."""
    assert shared.normalize_visibility("private") == "private"
    assert shared.normalize_visibility("PUBLIC") == "public"

    with pytest.raises(CommandError, match="Invalid repo visibility"):
        shared.normalize_visibility("internal")


def test_parse_repo_coordinates_supports_https_and_ssh() -> None:
    """Repository parser should support both canonical URL styles."""
    assert shared.parse_repo_coordinates("https://github.com/acme/demo.git") == ("acme", "demo")
    assert shared.parse_repo_coordinates("git@github.com:acme/demo.git") == ("acme", "demo")


def test_parse_repo_coordinates_rejects_invalid_urls() -> None:
    """Repository parser should fail fast for invalid coordinates."""
    with pytest.raises(CommandError, match="Repository URL is required"):
        shared.parse_repo_coordinates("   ")

    with pytest.raises(CommandError, match="Invalid SSH repository URL"):
        shared.parse_repo_coordinates("git@github.com")

    with pytest.raises(CommandError, match="Unable to parse repository owner/name"):
        shared.parse_repo_coordinates("https://github.com/acme")
