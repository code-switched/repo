"""Additional unit tests for shared CLI helpers."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import pytest

from repo.cli.commands import _shared as shared
from repo.core.exceptions import CommandError


def test_prompt_path_non_tty_normalizes_quotes(monkeypatch) -> None:
    """Non-TTY path prompt should return stripped, unquoted values."""
    monkeypatch.setattr(shared, "supports_path_completion", lambda: False)
    monkeypatch.setattr("builtins.input", lambda _prompt: ' "~/code/tools" ')

    value = shared.prompt_path(" > ")
    assert value == "~/code/tools"


def test_prompt_path_non_tty_allows_empty_when_requested(monkeypatch) -> None:
    """Optional path prompt should allow blank values."""
    monkeypatch.setattr(shared, "supports_path_completion", lambda: False)
    monkeypatch.setattr("builtins.input", lambda _prompt: "   ")

    value = shared.prompt_path(" > ", allow_empty=True)
    assert value == ""


def test_prompt_path_non_tty_requires_value_by_default(monkeypatch) -> None:
    """Required path prompt should fail when input is empty."""
    monkeypatch.setattr(shared, "supports_path_completion", lambda: False)
    monkeypatch.setattr("builtins.input", lambda _prompt: "")

    with pytest.raises(CommandError, match="required value"):
        shared.prompt_path(" > ")


def test_normalize_repo_type_accepts_aliases_and_rejects_unknown() -> None:
    """Repo type normalization should map aliases and reject unknown values."""
    assert shared.normalize_repo_type("org") == "org"
    assert shared.normalize_repo_type("organization") == "org"
    assert shared.normalize_repo_type("user") == "user"

    with pytest.raises(CommandError, match="Invalid repo type"):
        shared.normalize_repo_type("team")


def test_normalize_visibility_accepts_known_values_and_rejects_unknown() -> None:
    """Visibility normalization should only allow public/private."""
    assert shared.normalize_visibility("private") == "private"
    assert shared.normalize_visibility("PUBLIC") == "public"

    with pytest.raises(CommandError, match="Invalid repo visibility"):
        shared.normalize_visibility("internal")


def test_parse_repo_coordinates_supports_https_and_ssh() -> None:
    """Repository parser should support both canonical URL styles."""
    assert shared.parse_repo_coordinates("https://github.com/acme/demo.git") == ("acme", "demo")
    assert shared.parse_repo_coordinates("git@github.com:acme/demo.git") == ("acme", "demo")


def test_parse_repo_coordinates_rejects_invalid_urls() -> None:
    """Repository parser should fail fast for invalid coordinates."""
    with pytest.raises(CommandError, match="Repository URL is required"):
        shared.parse_repo_coordinates("   ")

    with pytest.raises(CommandError, match="Invalid SSH repository URL"):
        shared.parse_repo_coordinates("git@github.com")

    with pytest.raises(CommandError, match="Unable to parse repository owner/name"):
        shared.parse_repo_coordinates("https://github.com/acme")


def test_is_repo_propagation_error_detects_known_markers() -> None:
    """Both GitHub propagation stderr markers should be recognized."""
    assert shared.is_repo_propagation_error("ERROR: Repository not found.\n")
    assert shared.is_repo_propagation_error("fatal: Could not read from remote repository.\n")
    assert not shared.is_repo_propagation_error("fatal: Authentication failed\n")
    assert not shared.is_repo_propagation_error("")


class _PropagationFakeRunner:
    """Sequenced fake subprocess.run yielding scripted CompletedProcess results."""

    def __init__(self, results: list[subprocess.CompletedProcess[str]]) -> None:
        self.results = list(results)
        self.calls: list[tuple[list[str], Path]] = []

    def __call__(self, command, **kwargs):  # noqa: ANN001
        self.calls.append((list(command), kwargs.get("cwd")))
        if not self.results:
            raise AssertionError("subprocess.run called more times than scripted")
        return self.results.pop(0)


def _completed(returncode: int, stderr: str = "", stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["git"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_run_git_with_propagation_retries_returns_on_first_success(monkeypatch, tmp_path: Path) -> None:
    """Helper should not retry or sleep when the first attempt succeeds."""
    runner = _PropagationFakeRunner([_completed(0)])
    sleep_calls: list[float] = []
    monkeypatch.setattr(shared.subprocess, "run", runner)

    shared.run_git_with_propagation_retries(
        ["git", "push", "-u", "origin", "main"],
        cwd=tmp_path,
        logger=logging.getLogger("test.propagation"),
        sleep=sleep_calls.append,
    )

    assert len(runner.calls) == 1
    assert runner.calls[0][1] == tmp_path
    assert sleep_calls == []


def test_run_git_with_propagation_retries_retries_then_succeeds(monkeypatch, tmp_path: Path) -> None:
    """Helper should retry on propagation stderr and stop once push succeeds."""
    runner = _PropagationFakeRunner(
        [
            _completed(128, stderr="ERROR: Repository not found.\n"),
            _completed(128, stderr="fatal: Could not read from remote repository.\n"),
            _completed(0, stdout="pushed\n"),
        ]
    )
    sleep_calls: list[float] = []
    monkeypatch.setattr(shared.subprocess, "run", runner)

    shared.run_git_with_propagation_retries(
        ["git", "push", "-u", "origin", "main"],
        cwd=tmp_path,
        logger=logging.getLogger("test.propagation"),
        initial_delay=1.0,
        max_delay=4.0,
        sleep=sleep_calls.append,
    )

    assert len(runner.calls) == 3
    assert sleep_calls == [1.0, 1.5]


def test_run_git_with_propagation_retries_raises_on_non_propagation_error(monkeypatch, tmp_path: Path) -> None:
    """Helper should not retry when stderr does not match propagation markers."""
    runner = _PropagationFakeRunner(
        [_completed(128, stderr="fatal: Authentication failed\n")]
    )
    sleep_calls: list[float] = []
    monkeypatch.setattr(shared.subprocess, "run", runner)

    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        shared.run_git_with_propagation_retries(
            ["git", "push", "-u", "origin", "main"],
            cwd=tmp_path,
            logger=logging.getLogger("test.propagation"),
            sleep=sleep_calls.append,
        )

    assert excinfo.value.returncode == 128
    assert len(runner.calls) == 1
    assert sleep_calls == []


def test_run_git_with_propagation_retries_gives_up_after_max_attempts(monkeypatch, tmp_path: Path) -> None:
    """Helper should raise CalledProcessError once max attempts is reached."""
    runner = _PropagationFakeRunner(
        [_completed(128, stderr="ERROR: Repository not found.\n") for _ in range(3)]
    )
    sleep_calls: list[float] = []
    monkeypatch.setattr(shared.subprocess, "run", runner)

    with pytest.raises(subprocess.CalledProcessError):
        shared.run_git_with_propagation_retries(
            ["git", "push", "-u", "origin", "main"],
            cwd=tmp_path,
            logger=logging.getLogger("test.propagation"),
            max_attempts=3,
            initial_delay=0.5,
            max_delay=2.0,
            sleep=sleep_calls.append,
        )

    assert len(runner.calls) == 3
    assert sleep_calls == [0.5, 0.75]
