"""Shared prompt and parsing helpers for CLI commands."""

from __future__ import annotations

import re
import sys
import logging
from pathlib import Path
from urllib.parse import urlparse

from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter

from ..console import ansi
from ...core.exceptions import CommandError

YES_VALUES = {"y", "yes"}
IDENTITY_PART_PATTERN = re.compile(r"[^0-9A-Za-z]+")


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


def prompt_path(
    message: str,
    *,
    only_directories: bool = True,
    allow_empty: bool = False,
) -> str:
    """Prompt for a path with tab completion when running in a TTY."""
    if not supports_path_completion():
        value = normalize_path_input(input(message))
        if value:
            return value
        if allow_empty:
            return ""
        raise CommandError("A required value was not provided")

    completer = PathCompleter(
        expanduser=True,
        only_directories=only_directories,
    )
    value = normalize_path_input(
        prompt(
            message,
            completer=completer,
            complete_while_typing=True,
        )
    )
    if value:
        return value
    if allow_empty:
        return ""
    raise CommandError("A required value was not provided")


def supports_path_completion() -> bool:
    """Return whether interactive path completion is supported for this session."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def normalize_path_input(value: str) -> str:
    """Normalize quoted path input from interactive prompts."""
    return value.strip().strip('"').strip("'")


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
    """Find a likely default key by normalized username token matching."""
    username_parts = split_identity_parts(username)
    if not username_parts:
        return None

    username_compact = "".join(username_parts)
    for key in public_keys:
        if key_matches_username(key, username_parts, username_compact):
            return key
    return None


def split_identity_parts(value: str) -> list[str]:
    """Split an identity into lowercase alphanumeric tokens."""
    normalized = value.casefold().strip()
    if not normalized:
        return []
    return [part for part in IDENTITY_PART_PATTERN.split(normalized) if part]


def key_matches_username(key: Path, username_parts: list[str], username_compact: str) -> bool:
    """Check whether a key filename matches username tokens without substring collisions."""
    key_parts = split_identity_parts(key.stem)
    if not key_parts:
        return False

    if has_part_sequence(key_parts, username_parts):
        return True

    for part in key_parts:
        if part == username_compact:
            return True

    if len(username_parts) < 2:
        return False

    window_size = len(username_parts)
    max_start = len(key_parts) - window_size + 1
    if max_start < 1:
        return False

    for start in range(max_start):
        if "".join(key_parts[start:start + window_size]) == username_compact:
            return True

    return False


def has_part_sequence(parts: list[str], target: list[str]) -> bool:
    """Return whether target appears as a contiguous token sequence in parts."""
    window_size = len(target)
    if window_size == 0:
        return False

    max_start = len(parts) - window_size + 1
    if max_start < 1:
        return False

    for start in range(max_start):
        if parts[start:start + window_size] == target:
            return True

    return False


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


def print_section(title: str) -> None:
    """Print a visually distinct section heading."""
    print(f"\n{ansi.sage}{title}{ansi.reset}")


def print_summary(title: str, rows: list[tuple[str, str]]) -> None:
    """Render a compact key/value summary block."""
    print_section(title)
    for label, value in rows:
        print(f"  {ansi.cyan}{label:<16}{ansi.reset} {value}")


def log_command(
    logger: logging.Logger,
    command: list[str],
    *,
    cwd: Path | None = None,
    dry_run: bool = False,
) -> None:
    """Log an external command invocation for troubleshooting."""
    rendered = " ".join(command)
    if cwd is None:
        logger.info("external_command command=%s dry_run=%s", rendered, dry_run)
        return

    logger.info(
        "external_command command=%s cwd=%s dry_run=%s",
        rendered,
        cwd,
        dry_run,
    )


def confirm_proceed(message: str = "Proceed with these actions?") -> bool:
    """Prompt for explicit confirmation with safe default of no."""
    response = input(
        f"{ansi.yellow}{message} [y/N]: {ansi.reset}"
    ).strip().lower()
    if not response:
        return False
    return response in YES_VALUES
