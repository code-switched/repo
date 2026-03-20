"""Additional unit tests for core GitHub helper functions."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from repo.core import github
from repo.core.exceptions import CommandError


def test_resolve_github_token_prefers_environment(monkeypatch) -> None:
    """Environment token should short-circuit subprocess lookup."""
    monkeypatch.setenv("GH_TOKEN", "env-token")
    token = github.resolve_github_token()
    assert token == "env-token"


def test_resolve_github_token_reads_from_gh_cli(monkeypatch) -> None:
    """CLI token output should be used when env token is missing."""
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(
        github.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=["gh", "auth", "token"],
            returncode=0,
            stdout="cli-token\n",
            stderr="",
        ),
    )

    token = github.resolve_github_token()
    assert token == "cli-token"


def test_resolve_github_token_raises_with_stderr(monkeypatch) -> None:
    """CLI stderr should surface in the raised CommandError."""
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(
        github.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=["gh", "auth", "token"],
            returncode=1,
            stdout="",
            stderr="not logged in",
        ),
    )

    with pytest.raises(CommandError, match="not logged in"):
        github.resolve_github_token()


def test_resolve_github_token_raises_when_no_sources_available(monkeypatch) -> None:
    """Missing env token and empty CLI output should raise."""
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(
        github.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=["gh", "auth", "token"],
            returncode=1,
            stdout="",
            stderr="",
        ),
    )

    with pytest.raises(CommandError, match="unable to resolve GitHub token"):
        github.resolve_github_token()


def test_create_github_api_raises_for_empty_token() -> None:
    """Blank explicit token should fail fast."""
    with pytest.raises(CommandError, match="GitHub token is empty"):
        github.create_github_api(token="   ")


def test_create_github_api_uses_resolved_token(monkeypatch) -> None:
    """Resolver token should be passed into GhApi client."""
    monkeypatch.setattr(github, "resolve_github_token", lambda: "resolved-token")
    monkeypatch.setattr(github, "GhApi", lambda token: SimpleNamespace(token=token))

    api = github.create_github_api()
    assert api.token == "resolved-token"


def test_list_authenticated_orgs_extracts_login_values() -> None:
    """Org listing should map models to org login strings."""
    fake_api = SimpleNamespace(
        orgs=SimpleNamespace(
            list_for_authenticated_user=lambda per_page: [
                SimpleNamespace(login="acme"),
                SimpleNamespace(login="widgets"),
            ]
        )
    )

    assert github.list_authenticated_orgs(fake_api) == ["acme", "widgets"]


def test_create_repository_routes_by_owner_type() -> None:
    """Repository creation should call user/org APIs based on owner type."""
    calls: list[tuple[str, str]] = []

    class FakeRepos:
        def create_for_authenticated_user(self, **kwargs):  # noqa: ANN003
            calls.append(("user", kwargs["name"]))

        def create_in_org(self, **kwargs):  # noqa: ANN003
            calls.append(("org", kwargs["name"]))

    fake_api = SimpleNamespace(repos=FakeRepos())

    github.create_repository(fake_api, owner_type="user", owner="acme", repo_name="demo1", private=True)
    github.create_repository(fake_api, owner_type="org", owner="acme", repo_name="demo2", private=False)

    assert calls == [("user", "demo1"), ("org", "demo2")]


def test_create_repository_rejects_unknown_owner_type() -> None:
    """Unsupported owner types should raise CommandError."""
    fake_api = SimpleNamespace(repos=SimpleNamespace())
    with pytest.raises(CommandError, match="Unsupported owner type"):
        github.create_repository(
            fake_api,
            owner_type="team",
            owner="acme",
            repo_name="demo",
            private=True,
        )


def test_get_active_github_login_returns_none_for_failures(monkeypatch) -> None:
    """Non-zero command return should produce None."""
    monkeypatch.setattr(
        github.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=["gh", "api", "user"],
            returncode=1,
            stdout="",
            stderr="error",
        ),
    )

    assert github.get_active_github_login() is None


def test_emit_command_invokes_optional_logger() -> None:
    """Command callback should receive emitted command arrays."""
    received: list[list[str]] = []
    github.emit_command(["gh", "auth", "status"], command_logger=received.append)
    assert received == [["gh", "auth", "status"]]


def test_run_gh_repo_list_emits_and_invokes_gh(monkeypatch) -> None:
    """Repo list verification should log argv and run gh with hostname and limit."""
    logged: list[list[str]] = []
    run_cmds: list[list[str]] = []

    def fake_run(cmd, **_kwargs):  # noqa: ANN001
        run_cmds.append(list(cmd))
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr(github.subprocess, "run", fake_run)
    code = github.run_gh_repo_list(command_logger=logged.append)
    assert code == 0
    expected = [
        "gh",
        "repo",
        "list",
        "--hostname",
        "github.com",
        "--limit",
        "500",
    ]
    assert logged == [expected]
    assert run_cmds == [expected]
