"""Workflow contract tests for command execution order."""

from __future__ import annotations

import json
import subprocess
from argparse import Namespace
from pathlib import Path

from repo.cli.commands import existing as existing_command
from repo.cli.commands import new as new_command
from repo.cli.commands import ssh as ssh_command
from repo.cli.commands import started as started_command


class SubprocessRecorder:
    """Record subprocess.run calls and return successful results."""

    def __init__(self, status_stdout: str = "") -> None:
        self.calls: list[list[str]] = []
        self.status_stdout = status_stdout

    def run(self, command, **kwargs):  # noqa: ANN001
        """Record command and return a completed process."""
        command_list = [str(part) for part in command]
        self.calls.append(command_list)

        if command_list and command_list[0] == "ssh-keygen":
            key_path = Path(command_list[command_list.index("-f") + 1])
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.write_text("PRIVATE-KEY", encoding="utf-8")
            Path(f"{key_path}.pub").write_text(
                "ssh-ed25519 AAAATESTKEY test@example.com",
                encoding="utf-8",
            )

        if command_list == ["git", "status", "--porcelain"]:
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout=self.status_stdout,
                stderr="",
            )

        if command_list == ["ssh", "-T", "git@testuser.github.com"]:
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout="",
                stderr="successfully authenticated",
            )

        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="",
            stderr="",
        )


def load_workflow_contracts() -> dict:
    """Load workflow command-sequence contracts."""
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "contracts"
        / "workflows.json"
    )
    with fixture_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def to_command_strings(calls: list[list[str]], home: Path) -> list[str]:
    """Normalize command lists to comparable strings."""
    home_raw = str(home)
    home_slash = home_raw.replace("\\", "/")
    output: list[str] = []
    for command in calls:
        rendered_parts = []
        for part in command:
            rendered = part.replace(home_raw, "<HOME>")
            rendered = rendered.replace(home_slash, "<HOME>")
            rendered = rendered.replace("\\", "/")
            if rendered == "":
                rendered = '""'
            rendered_parts.append(rendered)
        output.append(" ".join(rendered_parts))
    return output


def test_new_workflow_matches_contract(monkeypatch, tmp_path: Path) -> None:
    """`repo new` should execute expected command sequence."""
    contracts = load_workflow_contracts()
    recorder = SubprocessRecorder()

    monkeypatch.setattr(new_command.subprocess, "run", recorder.run)
    monkeypatch.setattr(new_command, "create_github_api", lambda: object())
    monkeypatch.setattr(new_command, "create_repository", lambda **_kwargs: None)

    repo_parent = tmp_path / "repos"
    repo_parent.mkdir(parents=True, exist_ok=True)
    (repo_parent / "demo").mkdir(parents=True, exist_ok=True)

    args = Namespace(
        dry_run=False,
        non_interactive=True,
        force=False,
        repo_parent_folder=str(repo_parent),
        repo_name="demo",
        branch="main",
        repo_type="user",
        visibility="private",
        username="testuser",
        git_name="Test User",
        git_email="test@example.com",
        ssh_key="~/.ssh/id_ed25519_testuser.pub",
        ssh_host=None,
        owner=None,
    )

    new_command.run_new(args)
    actual = to_command_strings(recorder.calls, home=Path.home())
    assert actual == contracts["new_non_interactive_user"]


def test_existing_workflow_matches_contract(monkeypatch, tmp_path: Path) -> None:
    """`repo existing` should execute expected command sequence."""
    contracts = load_workflow_contracts()
    recorder = SubprocessRecorder()
    monkeypatch.setattr(existing_command.subprocess, "run", recorder.run)

    args = Namespace(
        dry_run=False,
        non_interactive=True,
        force=False,
        username="testuser",
        repo_url="https://github.com/testuser/demo.git",
        branch="main",
        git_name="Test User",
        git_email="test@example.com",
        repo_parent_folder=str(tmp_path),
        ssh_key="~/.ssh/id_ed25519_testuser.pub",
        ssh_host=None,
        confirm_permissions=True,
    )

    existing_command.run_existing(args)
    actual = to_command_strings(recorder.calls, home=Path.home())
    assert actual == contracts["existing_non_interactive"]


def test_started_workflow_matches_contract(monkeypatch, tmp_path: Path) -> None:
    """`repo started` should execute expected command sequence."""
    contracts = load_workflow_contracts()
    recorder = SubprocessRecorder(status_stdout=" M changed.py\n")

    monkeypatch.setattr(started_command.subprocess, "run", recorder.run)
    monkeypatch.setattr(started_command, "create_github_api", lambda: object())
    monkeypatch.setattr(started_command, "create_repository", lambda **_kwargs: None)
    monkeypatch.setattr(started_command.os, "chdir", lambda _path: None)

    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)

    args = Namespace(
        dry_run=False,
        non_interactive=True,
        force=False,
        project_path=str(project_path),
        repo_name="demo",
        repo_type="user",
        visibility="private",
        username="testuser",
        git_name="Test User",
        git_email="test@example.com",
        ssh_key="~/.ssh/id_ed25519_testuser.pub",
        ssh_host=None,
        owner=None,
    )

    started_command.run_started(args)
    actual = to_command_strings(recorder.calls, home=Path.home())
    assert actual == contracts["started_non_interactive_dirty"]


def test_ssh_workflow_matches_contract(monkeypatch, tmp_path: Path) -> None:
    """`repo ssh` should execute expected command sequence."""
    contracts = load_workflow_contracts()
    recorder = SubprocessRecorder()

    monkeypatch.setattr(ssh_command.subprocess, "run", recorder.run)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    args = Namespace(
        dry_run=False,
        non_interactive=True,
        force=False,
        account_name="testuser",
        email="test@example.com",
        machine_name="machine",
        key_path=None,
        generate=True,
    )

    ssh_command.run_ssh(args)
    actual = to_command_strings(recorder.calls, home=tmp_path)
    assert actual == contracts["ssh_non_interactive_generate"]
