"""Shared prompt and parsing helpers for CLI commands."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from ..console import ansi
from ...core.exceptions import CommandError

YES_VALUES = {"y", "yes"}


def prompt_with_default(message: str, default: str) -> str:
    """Prompt for text with a default value."""
    response = input(f"{message} {ansi.grey}(default: {default}){ansi.reset} ")
    value = response.strip()
    if value:
        return value
    return default


def prompt_required(message: str) -> str:
    """Prompt for required text."""
    value = input(message).strip()
    if value:
        return value
    raise CommandError("A required value was not provided")


def normalize_repo_type(value: str) -> str:
    """Normalize org alias values."""
    normalized = value.strip().lower()
    if normalized in {"org", "organization"}:
        return "org"
    if normalized == "user":
        return "user"
    raise CommandError("Invalid repo type. Use user or org")


def normalize_visibility(value: str) -> str:
    """Validate and normalize visibility."""
    normalized = value.strip().lower()
    if normalized in {"public", "private"}:
        return normalized
    raise CommandError("Invalid repo visibility. Use public or private")


def prompt_ssh_key(username: str) -> str:
    """Prompt the user to select or enter an SSH public key."""
    ssh_folder = Path.home() / ".ssh"
    public_keys = sorted(ssh_folder.glob("*.pub"))
    default_key = find_default_key(public_keys, username)

    if public_keys:
        print(
            "Select the SSH public key for this account "
            f"(e.g. {ansi.grey}id_ed25519_machine_{ansi.reset}"
            f"{ansi.magenta}{username}{ansi.reset}.pub): "
        )
        for index, key in enumerate(public_keys, start=1):
            marker = " (default)" if key == default_key else ""
            print(f"{ansi.yellow}{index}.{ansi.reset} {key.name}{marker}")

        default_label = default_key.name if default_key else "None"
        selection = input(
            "Select a key number or enter a custom path: "
            f"{ansi.grey}(default: {default_label}){ansi.reset} "
        ).strip()
        if not selection and default_key:
            return f"~/.ssh/{default_key.name}"

        if selection.isdigit():
            numeric_index = int(selection)
            if 1 <= numeric_index <= len(public_keys):
                chosen_key = public_keys[numeric_index - 1]
                return f"~/.ssh/{chosen_key.name}"

        custom_path = Path(selection).expanduser()
        if custom_path.exists():
            return f"~/.ssh/{custom_path.name}"

        raise CommandError("Invalid SSH key selection")

    print("No public SSH keys found in ~/.ssh folder.")
    print(
        "Enter the path to the SSH public key for this account "
        f"(e.g. {ansi.blue}~/.ssh/id_ed25519_machine_{ansi.reset}"
        f"{ansi.magenta}{username}{ansi.reset}.pub): "
    )
    entered = input(" > ").strip()
    if not entered:
        raise CommandError("SSH public key path is required")

    return f"~/.ssh/{Path(entered).expanduser().name}"


def find_default_key(public_keys: list[Path], username: str) -> Path | None:
    """Find a likely default key by username token in the filename."""
    username_token = username.lower()
    for key in public_keys:
        if username_token in key.name.lower():
            return key
    return None


def parse_repo_coordinates(repo_url: str) -> tuple[str, str]:
    """Parse owner/name from GitHub HTTPS or SSH repo URL."""
    value = repo_url.strip().rstrip("/")
    if not value:
        raise CommandError("Repository URL is required")

    path_part = ""
    if value.startswith("git@"):
        if ":" not in value:
            raise CommandError("Invalid SSH repository URL")
        path_part = value.split(":", maxsplit=1)[1]
    else:
        parsed = urlparse(value)
        path_part = parsed.path.lstrip("/")

    path_part = re.sub(r"\.git$", "", path_part)
    parts = [part for part in path_part.split("/") if part]
    if len(parts) != 2:
        raise CommandError("Unable to parse repository owner/name from URL")

    return parts[0], parts[1]
