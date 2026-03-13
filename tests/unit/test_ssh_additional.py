"""Additional unit coverage for `repo ssh` command branches."""

from __future__ import annotations

import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

from repo.cli.commands import ssh as ssh_command
from repo.core.exceptions import CommandError


def make_args(**overrides) -> Namespace:
    """Build argument namespace for ssh command tests."""
    values = {
        "dry_run": True,
        "non_interactive": True,
        "force": True,
        "account_name": "testuser",
        "email": "test@example.com",
        "machine_name": "machine",
        "key_path": None,
        "generate": False,
    }
    values.update(overrides)
    return Namespace(**values)


def test_resolve_key_selection_generates_when_no_public_keys(monkeypatch) -> None:
    """No existing keys should route to key generation."""
    expected = ssh_command.SshSelection(
        key_path=Path("/tmp/id_ed25519"),
        account_name="testuser",
        email="test@example.com",
    )
    monkeypatch.setattr(ssh_command, "generate_ssh_key", lambda _args: expected)

    selected = ssh_command.resolve_key_selection(make_args(), public_keys=[])
    assert selected == expected


def test_resolve_key_selection_non_interactive_uses_first_key(monkeypatch, tmp_path) -> None:
    """Non-interactive selection should choose the first discovered key."""
    first = tmp_path / "id_ed25519_first.pub"
    first.write_text("ssh-ed25519 AAAAFIRST", encoding="utf-8")
    monkeypatch.setattr(ssh_command, "infer_or_prompt_key_metadata", lambda _a, _p: ("acct", "mail"))

    selected = ssh_command.resolve_key_selection(
        make_args(non_interactive=True),
        public_keys=[first],
    )
    assert selected.key_path == first.with_suffix("")
    assert selected.account_name == "acct"


def test_resolve_key_selection_interactive_invalid_index_raises(monkeypatch, tmp_path) -> None:
    """Interactive key selection should reject invalid inputs."""
    key = tmp_path / "id_ed25519_first.pub"
    key.write_text("ssh-ed25519 AAAA", encoding="utf-8")

    answers = iter(["n", "abc"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    with pytest.raises(CommandError, match="Invalid selection"):
        ssh_command.resolve_key_selection(
            make_args(non_interactive=False),
            public_keys=[key],
        )


def test_generate_ssh_key_requires_account_name_in_non_interactive() -> None:
    """Generation in non-interactive mode requires explicit account name."""
    with pytest.raises(CommandError, match="--account-name is required"):
        ssh_command.generate_ssh_key(make_args(account_name=None, non_interactive=True, generate=True))


def test_generate_ssh_key_can_be_cancelled_interactively(monkeypatch) -> None:
    """Interactive generation should stop when user declines confirmation."""
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")

    with pytest.raises(CommandError, match="Key generation cancelled"):
        ssh_command.generate_ssh_key(
            make_args(
                dry_run=True,
                non_interactive=False,
                generate=True,
                account_name="testuser",
            )
        )


def test_infer_or_prompt_key_metadata_requires_account_for_non_matching_key() -> None:
    """Non-interactive metadata inference should fail for unmatched key names."""
    args = make_args(non_interactive=True, account_name=None, email=None)
    with pytest.raises(CommandError, match="--account-name is required"):
        ssh_command.infer_or_prompt_key_metadata(args, Path("id_ed25519"))


def test_update_ssh_config_writes_expected_host_entry(monkeypatch, tmp_path) -> None:
    """Config updater should append host entry to ~/.ssh/config."""
    monkeypatch.setattr(ssh_command.Path, "home", lambda: tmp_path)
    key_path = tmp_path / ".ssh" / "id_ed25519_machine_testuser"

    ssh_command.update_ssh_config(
        key_path=key_path,
        account_name="testuser",
        email="test@example.com",
        dry_run=False,
    )

    config_text = (tmp_path / ".ssh" / "config").read_text(encoding="utf-8")
    assert "Host testuser.github.com" in config_text
    assert "IdentityFile ~/.ssh/id_ed25519_machine_testuser" in config_text


def test_run_ssh_raises_when_public_key_file_missing(monkeypatch, tmp_path) -> None:
    """Run flow should fail fast when selected public key does not exist."""
    missing_private_key = tmp_path / ".ssh" / "id_ed25519_missing"
    monkeypatch.setattr(
        ssh_command,
        "resolve_key_selection",
        lambda _args, _keys: ssh_command.SshSelection(
            key_path=missing_private_key,
            account_name="testuser",
            email="test@example.com",
        ),
    )
    monkeypatch.setattr(ssh_command, "update_ssh_config", lambda *_args, **_kwargs: None)

    with pytest.raises(CommandError, match="Public key not found"):
        ssh_command.run_ssh(make_args(dry_run=False, non_interactive=True, force=True))


def test_run_ssh_logs_warning_on_failed_verification(monkeypatch, tmp_path) -> None:
    """Verification branch should log warning when auth output is unsuccessful."""
    private_key = tmp_path / ".ssh" / "id_ed25519_machine_testuser"
    private_key.parent.mkdir(parents=True, exist_ok=True)
    private_key.write_text("PRIVATE", encoding="utf-8")
    Path(f"{private_key}.pub").write_text("ssh-ed25519 AAAATESTKEY", encoding="utf-8")

    monkeypatch.setattr(
        ssh_command,
        "resolve_key_selection",
        lambda _args, _keys: ssh_command.SshSelection(
            key_path=private_key,
            account_name="testuser",
            email="test@example.com",
        ),
    )
    monkeypatch.setattr(ssh_command, "update_ssh_config", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        ssh_command.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=["ssh", "-T", "git@testuser.github.com"],
            returncode=1,
            stdout="",
            stderr="permission denied",
        ),
    )

    warnings: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        ssh_command.logger,
        "warning",
        lambda message, *args: warnings.append((message, args)),
    )

    ssh_command.run_ssh(make_args(dry_run=False, non_interactive=True, force=True))
    assert warnings
