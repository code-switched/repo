"""Additional prompt/key path tests for shared command helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from repo.cli.commands import _shared as shared
from repo.core.exceptions import CommandError


def test_prompt_path_tty_branch_uses_prompt_toolkit(monkeypatch) -> None:
    """TTY branch should use prompt_toolkit return value."""
    monkeypatch.setattr(shared, "supports_path_completion", lambda: True)
    monkeypatch.setattr(shared, "prompt", lambda *_args, **_kwargs: ' "C:/code/tools" ')

    value = shared.prompt_path(" > ")
    assert value == "C:/code/tools"


def test_prompt_path_tty_branch_allows_empty_when_requested(monkeypatch) -> None:
    """TTY path prompt should allow empty values only when configured."""
    monkeypatch.setattr(shared, "supports_path_completion", lambda: True)
    monkeypatch.setattr(shared, "prompt", lambda *_args, **_kwargs: "   ")

    assert shared.prompt_path(" > ", allow_empty=True) == ""


def test_prompt_path_tty_branch_requires_value_by_default(monkeypatch) -> None:
    """TTY path prompt should raise when required value is missing."""
    monkeypatch.setattr(shared, "supports_path_completion", lambda: True)
    monkeypatch.setattr(shared, "prompt", lambda *_args, **_kwargs: "   ")

    with pytest.raises(CommandError, match="required value"):
        shared.prompt_path(" > ")


def test_prompt_ssh_key_returns_default_match_when_selection_blank(monkeypatch, tmp_path) -> None:
    """Blank selection should use detected default key when available."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    default_key = ssh_dir / "id_ed25519_machine_testuser.pub"
    default_key.write_text("ssh-ed25519 AAAATEST", encoding="utf-8")
    (ssh_dir / "id_ed25519_other.pub").write_text("ssh-ed25519 AAAAOTHER", encoding="utf-8")

    monkeypatch.setattr(shared.Path, "home", lambda: tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt: "")

    selected = shared.prompt_ssh_key("testuser")
    assert selected == "~/.ssh/id_ed25519_machine_testuser.pub"


def test_prompt_ssh_key_returns_selected_numeric_key(monkeypatch, tmp_path) -> None:
    """Numeric key selection should map to the selected .pub key."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    first_key = ssh_dir / "id_ed25519_first.pub"
    second_key = ssh_dir / "id_ed25519_second.pub"
    first_key.write_text("ssh-ed25519 AAAA1", encoding="utf-8")
    second_key.write_text("ssh-ed25519 AAAA2", encoding="utf-8")

    monkeypatch.setattr(shared.Path, "home", lambda: tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt: "2")

    selected = shared.prompt_ssh_key("someone")
    assert selected == "~/.ssh/id_ed25519_second.pub"


def test_prompt_ssh_key_rejects_invalid_selection(monkeypatch, tmp_path) -> None:
    """Invalid key choices should raise a CommandError."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    (ssh_dir / "id_ed25519.pub").write_text("ssh-ed25519 AAAA", encoding="utf-8")

    monkeypatch.setattr(shared.Path, "home", lambda: tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt: "not-valid")

    with pytest.raises(CommandError, match="Invalid SSH key selection"):
        shared.prompt_ssh_key("someone")


def test_prompt_ssh_key_requires_path_when_no_public_keys(monkeypatch, tmp_path) -> None:
    """No-key branch should require a path."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(shared.Path, "home", lambda: tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt: "   ")

    with pytest.raises(CommandError, match="SSH public key path is required"):
        shared.prompt_ssh_key("someone")


def test_prompt_ssh_key_accepts_custom_path_when_no_keys(monkeypatch, tmp_path) -> None:
    """Entered custom key path should normalize to ~/.ssh/<filename>."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    custom_key = ssh_dir / "id_ed25519_manual.pub"
    custom_key.write_text("ssh-ed25519 AAAAMANUAL", encoding="utf-8")

    monkeypatch.setattr(shared.Path, "home", lambda: tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt: str(custom_key))

    selected = shared.prompt_ssh_key("someone")
    assert selected == "~/.ssh/id_ed25519_manual.pub"
