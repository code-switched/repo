"""GitHub API helpers with token fallback."""

from __future__ import annotations

import os
import subprocess

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
