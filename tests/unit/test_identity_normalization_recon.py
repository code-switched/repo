"""Recon coverage for username/SSH-key normalization edge cases."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from repo.cli.commands import existing as existing_command
from repo.cli.commands._shared import find_default_key


def build_existing_args(**overrides) -> Namespace:
    """Build a minimal `run_existing` namespace for normalization checks."""
    values = {
        "dry_run": True,
        "non_interactive": True,
        "force": False,
        "username": "testuser",
        "repo_url": "https://github.com/testuser/demo.git",
        "branch": "main",
        "git_name": "Test User",
        "git_email": "test@example.com",
        "repo_parent_folder": "C:/repos",
        "ssh_key": "~/.ssh/id_ed25519_testuser.pub",
        "ssh_host": None,
        "confirm_permissions": False,
    }
    values.update(overrides)
    return Namespace(**values)


def test_find_default_key_is_case_insensitive_for_exact_username() -> None:
    """Exact username match should ignore case."""
    key = Path("id_ed25519_machine_chrischcodes.pub")
    assert find_default_key([key], "ChrisChCodes") == key


def test_find_default_key_normalizes_dash_to_underscore() -> None:
    """`code-switched` username should match `_code_switched` key names."""
    key = Path("id_ed25519_pcstream_code_switched.pub")
    assert find_default_key([key], "code-switched") == key


def test_find_default_key_avoids_partial_username_collision() -> None:
    """Short username should not auto-match inside another username token."""
    key = Path("id_ed25519_pcstream_chrischcodes.pub")
    assert find_default_key([key], "chris") is None


def test_existing_owner_comparison_ignores_case_only_mismatches() -> None:
    """Case-only differences should not trigger permission mismatch flow."""
    args = build_existing_args(
        username="ChrisChCodes",
        repo_url="https://github.com/chrischcodes/demo.git",
    )
    existing_command.run_existing(args)
