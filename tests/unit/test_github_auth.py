"""Unit tests for GitHub auth account enforcement helper."""

from __future__ import annotations

import subprocess

import pytest

from repo.core.exceptions import CommandError
from repo.core import github


class FakeSubprocess:
    """Deterministic subprocess runner for auth helper tests."""

    def __init__(self, responses: dict[tuple[str, ...], list[dict[str, object]]]) -> None:
        self.responses = {
            command: list(items)
            for command, items in responses.items()
        }
        self.calls: list[list[str]] = []

    def run(self, command, **kwargs):  # noqa: ANN001
        """Return queued response for command and respect check=True semantics."""
        command_list = [str(part) for part in command]
        key = tuple(command_list)
        self.calls.append(command_list)

        response_list = self.responses.get(key, [])
        if response_list:
            response = response_list.pop(0)
        else:
            response = {"returncode": 0, "stdout": "", "stderr": ""}

        returncode = int(response.get("returncode", 0))
        stdout = str(response.get("stdout", ""))
        stderr = str(response.get("stderr", ""))

        if kwargs.get("check") and returncode != 0:
            raise subprocess.CalledProcessError(
                returncode=returncode,
                cmd=command_list,
                output=stdout,
                stderr=stderr,
            )

        return subprocess.CompletedProcess(
            args=command_list,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )


def test_auth_helper_noop_when_active_user_matches(monkeypatch) -> None:
    """Should not switch/login if active account already matches."""
    login_cmd = (
        "gh",
        "api",
        "user",
        "--hostname",
        "github.com",
        "--jq",
        ".login",
    )
    fake = FakeSubprocess(
        {
            login_cmd: [
                {"returncode": 0, "stdout": "ChrisChCodes\n"},
            ],
        }
    )
    monkeypatch.setattr(github.subprocess, "run", fake.run)

    resolved = github.ensure_github_auth_for_user("chrischcodes")
    assert resolved == "ChrisChCodes"
    assert fake.calls == [list(login_cmd)]


def test_auth_helper_switches_before_login(monkeypatch) -> None:
    """Should switch account when a different active account exists."""
    login_cmd = (
        "gh",
        "api",
        "user",
        "--hostname",
        "github.com",
        "--jq",
        ".login",
    )
    switch_cmd = (
        "gh",
        "auth",
        "switch",
        "--hostname",
        "github.com",
        "--user",
        "chrischcodes",
    )
    fake = FakeSubprocess(
        {
            login_cmd: [
                {"returncode": 0, "stdout": "someoneelse\n"},
                {"returncode": 0, "stdout": "chrischcodes\n"},
            ],
            switch_cmd: [
                {"returncode": 0},
            ],
        }
    )
    monkeypatch.setattr(github.subprocess, "run", fake.run)

    resolved = github.ensure_github_auth_for_user("chrischcodes")
    assert resolved == "chrischcodes"
    assert list(switch_cmd) in fake.calls


def test_auth_helper_logs_in_when_no_active_user(monkeypatch) -> None:
    """Should invoke login when no active account can be resolved."""
    login_cmd = (
        "gh",
        "api",
        "user",
        "--hostname",
        "github.com",
        "--jq",
        ".login",
    )
    auth_login_cmd = (
        "gh",
        "auth",
        "login",
        "--git-protocol",
        "ssh",
        "--hostname",
        "github.com",
        "--web",
    )
    fake = FakeSubprocess(
        {
            login_cmd: [
                {"returncode": 1, "stderr": "not logged in"},
                {"returncode": 0, "stdout": "chrischcodes\n"},
            ],
            auth_login_cmd: [
                {"returncode": 0},
            ],
        }
    )
    monkeypatch.setattr(github.subprocess, "run", fake.run)

    resolved = github.ensure_github_auth_for_user("chrischcodes")
    assert resolved == "chrischcodes"
    assert list(auth_login_cmd) in fake.calls


def test_auth_helper_falls_back_to_login_when_switch_does_not_match(monkeypatch) -> None:
    """Should login when switch does not resolve requested account."""
    login_cmd = (
        "gh",
        "api",
        "user",
        "--hostname",
        "github.com",
        "--jq",
        ".login",
    )
    switch_cmd = (
        "gh",
        "auth",
        "switch",
        "--hostname",
        "github.com",
        "--user",
        "chrischcodes",
    )
    auth_login_cmd = (
        "gh",
        "auth",
        "login",
        "--git-protocol",
        "ssh",
        "--hostname",
        "github.com",
        "--web",
    )
    fake = FakeSubprocess(
        {
            login_cmd: [
                {"returncode": 0, "stdout": "someoneelse\n"},
                {"returncode": 0, "stdout": "someoneelse\n"},
                {"returncode": 0, "stdout": "chrischcodes\n"},
            ],
            switch_cmd: [
                {"returncode": 1, "stderr": "unknown account"},
            ],
            auth_login_cmd: [
                {"returncode": 0},
            ],
        }
    )
    monkeypatch.setattr(github.subprocess, "run", fake.run)

    resolved = github.ensure_github_auth_for_user("chrischcodes")
    assert resolved == "chrischcodes"
    assert list(auth_login_cmd) in fake.calls


def test_auth_helper_raises_when_login_verification_mismatches(monkeypatch) -> None:
    """Should fail fast when login completes but account still mismatches."""
    login_cmd = (
        "gh",
        "api",
        "user",
        "--hostname",
        "github.com",
        "--jq",
        ".login",
    )
    auth_login_cmd = (
        "gh",
        "auth",
        "login",
        "--git-protocol",
        "ssh",
        "--hostname",
        "github.com",
        "--web",
    )
    fake = FakeSubprocess(
        {
            login_cmd: [
                {"returncode": 1, "stderr": "not logged in"},
                {"returncode": 0, "stdout": "wrong-user\n"},
            ],
            auth_login_cmd: [
                {"returncode": 0},
            ],
        }
    )
    monkeypatch.setattr(github.subprocess, "run", fake.run)

    with pytest.raises(CommandError):
        github.ensure_github_auth_for_user("chrischcodes")
