"""Prompt-flow contract tests for interactive command paths."""

from __future__ import annotations

import json
import subprocess
from argparse import Namespace
from pathlib import Path

from repo.cli.commands import existing as existing_command
from repo.cli.commands import new as new_command
from repo.cli.commands import ssh as ssh_command
from repo.cli.commands import started as started_command
from repo.cli.console import ansi


class InputRecorder:
    """Record prompt text and provide canned responses."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.prompts: list[str] = []

    def __call__(self, prompt: str = "") -> str:
        self.prompts.append(prompt)
        if not self._responses:
            raise AssertionError(f"Unexpected prompt: {prompt!r}")
        return self._responses.pop(0)

    def assert_exhausted(self) -> None:
        """All queued responses should be consumed."""
        if self._responses:
            raise AssertionError(f"Unused input responses remain: {self._responses!r}")


def load_prompt_contracts() -> dict:
    """Load prompt contract templates."""
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "contracts"
        / "prompts.json"
    )
    with fixture_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def expand_prompts(templates: list[str], replacements: dict[str, str] | None = None) -> list[str]:
    """Expand tokenized prompt templates to exact strings."""
    color_tokens = {
        "<RED>": ansi.red,
        "<GREEN>": ansi.green,
        "<YELLOW>": ansi.yellow,
        "<BLUE>": ansi.blue,
        "<MAGENTA>": ansi.magenta,
        "<CYAN>": ansi.cyan,
        "<GREY>": ansi.grey,
        "<RESET>": ansi.reset,
    }
    values = dict(color_tokens)
    if replacements:
        values.update(replacements)

    expanded: list[str] = []
    for template in templates:
        current = template
        for token, value in values.items():
            current = current.replace(token, value)
        expanded.append(current)
    return expanded


def test_collect_new_prompt_flow_matches_contract(monkeypatch, tmp_path: Path) -> None:
    """`collect_new_inputs` should keep its interactive prompt sequence."""
    contracts = load_prompt_contracts()
    recorder = InputRecorder(
        [
            str(tmp_path / "repos"),
            "demo",
            "",
            "",
            "",
            "testuser",
            "Test User",
            "test@example.com",
            "",
        ]
    )

    monkeypatch.setattr(new_command, "prompt_ssh_key", lambda _username: "~/.ssh/id_ed25519_testuser.pub")
    monkeypatch.setattr("builtins.input", recorder)

    args = Namespace(
        non_interactive=False,
        repo_parent_folder=None,
        repo_name=None,
        branch=None,
        repo_type=None,
        visibility=None,
        username=None,
        git_name=None,
        git_email=None,
        ssh_key=None,
        ssh_host=None,
        owner=None,
    )

    new_command.collect_new_inputs(args)
    recorder.assert_exhausted()

    expected = expand_prompts(contracts["collect_new_interactive"])
    assert recorder.prompts == expected


def test_collect_existing_prompt_flow_matches_contract(monkeypatch, tmp_path: Path) -> None:
    """`collect_existing_inputs` should keep its interactive prompt sequence."""
    contracts = load_prompt_contracts()
    recorder = InputRecorder(
        [
            "testuser",
            "https://github.com/testuser/demo.git",
            "",
            "Test User",
            "test@example.com",
            str(tmp_path),
            "",
        ]
    )

    monkeypatch.setattr(existing_command, "prompt_ssh_key", lambda _username: "~/.ssh/id_ed25519_testuser.pub")
    monkeypatch.setattr("builtins.input", recorder)

    args = Namespace(
        non_interactive=False,
        username=None,
        repo_url=None,
        branch=None,
        git_name=None,
        git_email=None,
        repo_parent_folder=None,
        ssh_key=None,
        ssh_host=None,
    )

    existing_command.collect_existing_inputs(args)
    recorder.assert_exhausted()

    expected = expand_prompts(contracts["collect_existing_interactive"])
    assert recorder.prompts == expected


def test_collect_started_prompt_flow_matches_contract(monkeypatch, tmp_path: Path) -> None:
    """`collect_started_inputs` should keep its interactive prompt sequence."""
    contracts = load_prompt_contracts()
    recorder = InputRecorder(
        [
            "",
            "",
            "",
            "",
            "testuser",
            "Test User",
            "test@example.com",
            "",
        ]
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(started_command, "prompt_ssh_key", lambda _username: "~/.ssh/id_ed25519_testuser.pub")
    monkeypatch.setattr("builtins.input", recorder)

    args = Namespace(
        non_interactive=False,
        project_path=None,
        repo_name=None,
        repo_type=None,
        visibility=None,
        username=None,
        git_name=None,
        git_email=None,
        ssh_key=None,
        ssh_host=None,
        owner=None,
    )

    started_command.collect_started_inputs(args)
    recorder.assert_exhausted()

    expected = expand_prompts(
        contracts["collect_started_interactive"],
        replacements={"<PROJECT_NAME>": tmp_path.name},
    )
    assert recorder.prompts == expected


def test_run_new_prompt_flow_matches_contract(monkeypatch, tmp_path: Path) -> None:
    """`run_new` should keep login confirmation prompts in interactive mode."""
    contracts = load_prompt_contracts()
    recorder = InputRecorder(["y", "", "y"])
    monkeypatch.setattr("builtins.input", recorder)

    args = Namespace(
        dry_run=True,
        non_interactive=False,
        yes=False,
        repo_parent_folder=str(tmp_path / "repos"),
        repo_name="demo",
        branch="main",
        repo_type="user",
        visibility="private",
        username="testuser",
        git_name="Test User",
        git_email="test@example.com",
        ssh_key="~/.ssh/id_ed25519_testuser.pub",
        ssh_host="testuser.github.com",
        owner=None,
    )

    new_command.run_new(args)
    recorder.assert_exhausted()

    expected = expand_prompts(contracts["run_new_interactive"])
    assert recorder.prompts == expected


def test_run_existing_prompt_flow_matches_contract(monkeypatch, tmp_path: Path) -> None:
    """`run_existing` should keep permission and key prompts in interactive mode."""
    contracts = load_prompt_contracts()
    recorder = InputRecorder(["y", "y", "y"])
    monkeypatch.setattr("builtins.input", recorder)

    args = Namespace(
        dry_run=True,
        non_interactive=False,
        yes=False,
        username="testuser",
        repo_url="https://github.com/owner/demo.git",
        branch="main",
        git_name="Test User",
        git_email="test@example.com",
        repo_parent_folder=str(tmp_path),
        ssh_key="~/.ssh/id_ed25519_testuser.pub",
        ssh_host="testuser.github.com",
        confirm_permissions=False,
    )

    existing_command.run_existing(args)
    recorder.assert_exhausted()

    expected = expand_prompts(contracts["run_existing_interactive"])
    assert recorder.prompts == expected


def test_run_started_prompt_flow_matches_contract(monkeypatch, tmp_path: Path) -> None:
    """`run_started` should keep login confirmation prompt in interactive mode."""
    contracts = load_prompt_contracts()
    recorder = InputRecorder(["y", ""])
    monkeypatch.setattr("builtins.input", recorder)

    args = Namespace(
        dry_run=True,
        non_interactive=False,
        yes=False,
        project_path=str(tmp_path),
        repo_name="demo",
        repo_type="user",
        visibility="private",
        username="testuser",
        git_name="Test User",
        git_email="test@example.com",
        ssh_key="~/.ssh/id_ed25519_testuser.pub",
        ssh_host="testuser.github.com",
        owner=None,
    )

    started_command.run_started(args)
    recorder.assert_exhausted()

    expected = expand_prompts(contracts["run_started_interactive"])
    assert recorder.prompts == expected


def test_run_ssh_prompt_flow_matches_contract(monkeypatch) -> None:
    """`run_ssh` should keep generation and final confirmation prompts."""
    contracts = load_prompt_contracts()
    recorder = InputRecorder(["y", "y", ""])
    monkeypatch.setattr("builtins.input", recorder)

    args = Namespace(
        dry_run=True,
        non_interactive=False,
        yes=False,
        account_name="testuser",
        email="test@example.com",
        machine_name="machine",
        key_path=None,
        generate=True,
    )

    ssh_command.run_ssh(args)
    recorder.assert_exhausted()

    expected = expand_prompts(contracts["run_ssh_interactive"])
    assert recorder.prompts == expected


def test_run_new_org_prompt_flow_matches_contract(monkeypatch, tmp_path: Path) -> None:
    """`run_new` should prompt for org selection in org mode."""
    contracts = load_prompt_contracts()
    recorder = InputRecorder(["y", "", "y", "1"])
    monkeypatch.setattr("builtins.input", recorder)

    def fake_run(command, **_kwargs):  # noqa: ANN001
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(new_command.subprocess, "run", fake_run)
    monkeypatch.setattr(new_command, "create_github_api", lambda: object())
    monkeypatch.setattr(new_command, "create_repository", lambda **_kwargs: None)
    monkeypatch.setattr(new_command, "ensure_github_auth_for_user", lambda _username, **_kwargs: "testuser")
    monkeypatch.setattr(new_command, "list_authenticated_orgs", lambda _api: ["acme"])

    args = Namespace(
        dry_run=False,
        non_interactive=False,
        yes=False,
        repo_parent_folder=str(tmp_path / "repos"),
        repo_name="demo",
        branch="main",
        repo_type="org",
        visibility="private",
        username="testuser",
        git_name="Test User",
        git_email="test@example.com",
        ssh_key="~/.ssh/id_ed25519_testuser.pub",
        ssh_host="testuser.github.com",
        owner=None,
    )

    new_command.run_new(args)
    recorder.assert_exhausted()

    expected = expand_prompts(contracts["run_new_org_interactive"])
    assert recorder.prompts == expected


def test_run_started_org_prompt_flow_matches_contract(monkeypatch, tmp_path: Path) -> None:
    """`run_started` should prompt for org selection in org mode."""
    contracts = load_prompt_contracts()
    recorder = InputRecorder(["y", "", "1"])
    monkeypatch.setattr("builtins.input", recorder)

    def fake_run(command, **_kwargs):  # noqa: ANN001
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(started_command.subprocess, "run", fake_run)
    monkeypatch.setattr(started_command.os, "chdir", lambda _path: None)
    monkeypatch.setattr(started_command, "create_github_api", lambda: object())
    monkeypatch.setattr(started_command, "create_repository", lambda **_kwargs: None)
    monkeypatch.setattr(started_command, "ensure_github_auth_for_user", lambda _username, **_kwargs: "testuser")
    monkeypatch.setattr(started_command, "list_authenticated_orgs", lambda _api: ["acme"])

    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)

    args = Namespace(
        dry_run=False,
        non_interactive=False,
        yes=False,
        project_path=str(project_path),
        repo_name="demo",
        repo_type="org",
        visibility="private",
        username="testuser",
        git_name="Test User",
        git_email="test@example.com",
        ssh_key="~/.ssh/id_ed25519_testuser.pub",
        ssh_host="testuser.github.com",
        owner=None,
    )

    started_command.run_started(args)
    recorder.assert_exhausted()

    expected = expand_prompts(contracts["run_started_org_interactive"])
    assert recorder.prompts == expected
