"""GitHub API helpers with token fallback."""

from __future__ import annotations

import os
import subprocess
from typing import Callable

from ghapi.all import GhApi

from .exceptions import CommandError


def resolve_github_token() -> str:
    """Resolve a GitHub token from env or gh CLI auth state."""
    env_token = os.getenv("GH_TOKEN", "").strip()
    if env_token:
        return env_token

    token_proc = subprocess.run(
        ["gh", "auth", "token"],
        capture_output=True,
        text=True,
        check=False,
    )
    token = token_proc.stdout.strip()
    if token:
        return token

    stderr = token_proc.stderr.strip()
    if stderr:
        raise CommandError(
            "unable to resolve GitHub token from GH_TOKEN or gh auth token: "
            f"{stderr}"
        )

    raise CommandError(
        "unable to resolve GitHub token from GH_TOKEN or gh auth token"
    )


def create_github_api(token: str | None = None) -> GhApi:
    """Create and return an authenticated GhApi client."""
    resolved = token.strip() if token else resolve_github_token()
    if not resolved:
        raise CommandError("GitHub token is empty")
    return GhApi(token=resolved)


def list_authenticated_orgs(api: GhApi) -> list[str]:
    """Return org logins visible to the authenticated user."""
    orgs = api.orgs.list_for_authenticated_user(per_page=100)
    return [org.login for org in orgs]


def create_repository(
    api: GhApi,
    owner_type: str,
    owner: str,
    repo_name: str,
    private: bool,
) -> None:
    """Create a repository for the authenticated user or org."""
    if owner_type == "user":
        api.repos.create_for_authenticated_user(
            name=repo_name,
            private=private,
        )
        return

    if owner_type == "org":
        api.repos.create_in_org(
            org=owner,
            name=repo_name,
            private=private,
        )
        return

    raise CommandError(f"Unsupported owner type: {owner_type}")


def ensure_github_auth_for_user(
    username: str,
    *,
    hostname: str = "github.com",
    command_logger: Callable[[list[str]], None] | None = None,
) -> str:
    """Ensure gh CLI is authenticated as *username* on *hostname*."""
    desired_user = username.strip()
    if not desired_user:
        raise CommandError("GitHub username is required for authentication")

    desired_fold = desired_user.casefold()
    active_user = get_active_github_login(
        hostname=hostname,
        command_logger=command_logger,
    )
    if active_user and active_user.casefold() == desired_fold:
        return active_user

    if active_user:
        switch_cmd = [
            "gh",
            "auth",
            "switch",
            "--hostname",
            hostname,
            "--user",
            desired_user,
        ]
        emit_command(switch_cmd, command_logger)
        subprocess.run(switch_cmd, check=False)

        switched_user = get_active_github_login(
            hostname=hostname,
            command_logger=command_logger,
        )
        if switched_user and switched_user.casefold() == desired_fold:
            return switched_user

    login_cmd = [
        "gh",
        "auth",
        "login",
        "--git-protocol",
        "ssh",
        "--hostname",
        hostname,
        "--web",
    ]
    emit_command(login_cmd, command_logger)
    subprocess.run(login_cmd, check=True)

    verified_user = get_active_github_login(
        hostname=hostname,
        command_logger=command_logger,
    )
    if not verified_user or verified_user.casefold() != desired_fold:
        raise CommandError(
            "GitHub authentication did not resolve to requested account "
            f"{desired_user!r}"
        )

    return verified_user


def get_active_github_login(
    *,
    hostname: str = "github.com",
    command_logger: Callable[[list[str]], None] | None = None,
) -> str | None:
    """Return active gh login for host, or None when unavailable."""
    login_cmd = [
        "gh",
        "api",
        "user",
        "--hostname",
        hostname,
        "--jq",
        ".login",
    ]
    emit_command(login_cmd, command_logger)
    completed = subprocess.run(
        login_cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None

    login = completed.stdout.strip()
    if not login:
        return None
    return login


def emit_command(
    command: list[str],
    command_logger: Callable[[list[str]], None] | None,
) -> None:
    """Emit command through optional logger callback."""
    if command_logger is None:
        return
    command_logger(command)
