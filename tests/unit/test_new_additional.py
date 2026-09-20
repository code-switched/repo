"""Additional unit tests for `repo new` clone retry behavior."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from repo.cli.commands import new as new_command


def test_clone_repository_with_retry_succeeds_after_repo_provisioning_delay(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Repository-not-found from first attempt should retry and then succeed."""
    calls: list[list[str]] = []
    sleep_calls: list[float] = []
    responses = [
        subprocess.CompletedProcess(
            args=["git", "clone", "git@testuser.github.com:testuser/demo.git"],
            returncode=128,
            stdout="",
            stderr="ERROR: Repository not found.",
        ),
        subprocess.CompletedProcess(
            args=["git", "clone", "git@testuser.github.com:testuser/demo.git"],
            returncode=0,
            stdout="",
            stderr="",
        ),
    ]

    def fake_run(command, **_kwargs):  # noqa: ANN001
        calls.append([str(part) for part in command])
        return responses.pop(0)

    monkeypatch.setattr(new_command.subprocess, "run", fake_run)
    monkeypatch.setattr(new_command.time, "sleep", sleep_calls.append)
    monkeypatch.setattr(new_command, "_CLONE_RETRY_ATTEMPTS", 2)

    new_command.clone_repository_with_retry(
        ["git", "clone", "git@testuser.github.com:testuser/demo.git"],
        cwd=tmp_path,
    )

    assert len(calls) == 2
    assert sleep_calls == [new_command._CLONE_RETRY_DELAY_SECONDS]


def test_clone_repository_with_retry_fails_fast_for_non_retryable_clone_error(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Errors other than repository-not-found should fail without retrying."""
    calls: list[list[str]] = []
    sleep_calls: list[float] = []

    def fake_run(command, **_kwargs):  # noqa: ANN001
        calls.append([str(part) for part in command])
        return subprocess.CompletedProcess(
            args=command,
            returncode=128,
            stdout="",
            stderr="fatal: Could not read from remote repository.",
        )

    monkeypatch.setattr(new_command.subprocess, "run", fake_run)
    monkeypatch.setattr(new_command.time, "sleep", sleep_calls.append)

    with pytest.raises(subprocess.CalledProcessError):
        new_command.clone_repository_with_retry(
            ["git", "clone", "git@testuser.github.com:testuser/demo.git"],
            cwd=tmp_path,
        )

    assert len(calls) == 1
    assert sleep_calls == []


def test_clone_repository_with_retry_raises_after_exhausting_retry_budget(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Persistent repository-not-found should raise after configured retries."""
    calls: list[list[str]] = []
    sleep_calls: list[float] = []

    def fake_run(command, **_kwargs):  # noqa: ANN001
        calls.append([str(part) for part in command])
        return subprocess.CompletedProcess(
            args=command,
            returncode=128,
            stdout="",
            stderr="ERROR: Repository not found.",
        )

    monkeypatch.setattr(new_command.subprocess, "run", fake_run)
    monkeypatch.setattr(new_command.time, "sleep", sleep_calls.append)
    monkeypatch.setattr(new_command, "_CLONE_RETRY_ATTEMPTS", 2)

    with pytest.raises(subprocess.CalledProcessError):
        new_command.clone_repository_with_retry(
            ["git", "clone", "git@testuser.github.com:testuser/demo.git"],
            cwd=tmp_path,
        )

    assert len(calls) == 3
    assert sleep_calls == [
        new_command._CLONE_RETRY_DELAY_SECONDS,
        new_command._CLONE_RETRY_DELAY_SECONDS,
    ]
