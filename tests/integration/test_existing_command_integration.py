"""Integration tests for `repo existing` command orchestration."""

from __future__ import annotations

from pathlib import Path

from .harness import build_integration_env, load_json_lines, run_repo_command


def test_repo_existing_non_interactive_success_flow(tmp_path: Path) -> None:
    """Command should orchestrate expected git/ssh sequence and create repo folder."""
    harness = build_integration_env(
        tmp_path,
        tools=("git", "ssh"),
    )
    repo_parent = tmp_path / "repos"

    completed = run_repo_command(
        "existing",
        [
            "--non-interactive",
            "--force",
            "--confirm-permissions",
            "--username",
            "testuser",
            "--repo-url",
            "https://github.com/testuser/demo.git",
            "--branch",
            "main",
            "--git-name",
            "Test User",
            "--git-email",
            "test@example.com",
            "--repo-parent-folder",
            str(repo_parent),
            "--ssh-key",
            "~/.ssh/id_ed25519_testuser.pub",
            "--ssh-host",
            "testuser.github.com",
        ],
        env=harness.env,
    )

    assert completed.returncode == 0, completed.stderr
    repo_path = repo_parent / "demo"
    assert repo_path.exists()

    calls = load_json_lines(harness.tool_log_path)
    rendered_calls = [
        " ".join([str(call["tool"]), *[str(arg) for arg in call["args"]]])
        for call in calls
    ]
    assert rendered_calls == [
        "git init",
        "git config user.name Test User",
        "git config user.email test@example.com",
        "git config user.signingkey ~/.ssh/id_ed25519_testuser.pub",
        "git config gpg.format ssh",
        "git config commit.gpgsign true",
        "git config pull.rebase true",
        "ssh -T git@testuser.github.com",
        "git remote remove origin",
        "git remote add origin git@testuser.github.com:testuser/demo.git",
        "git fetch origin",
        "git checkout -B main origin/main",
        "git pull",
    ]

    git_calls = [call for call in calls if call["tool"] == "git"]
    assert all(call["cwd"] == str(repo_path) for call in git_calls)


def test_repo_existing_surfaces_subprocess_failures(tmp_path: Path) -> None:
    """Failing fake git command should surface as command error and non-zero exit."""
    harness = build_integration_env(
        tmp_path,
        tools=("git", "ssh"),
    )
    harness.env["FAKE_TOOL_FAIL"] = "git|fetch origin|42"

    completed = run_repo_command(
        "existing",
        [
            "--non-interactive",
            "--force",
            "--confirm-permissions",
            "--username",
            "testuser",
            "--repo-url",
            "https://github.com/testuser/demo.git",
            "--branch",
            "main",
            "--git-name",
            "Test User",
            "--git-email",
            "test@example.com",
            "--repo-parent-folder",
            str(tmp_path / "repos"),
            "--ssh-key",
            "~/.ssh/id_ed25519_testuser.pub",
            "--ssh-host",
            "testuser.github.com",
        ],
        env=harness.env,
    )

    assert completed.returncode == 1
    assert "Command failed (42):" in completed.stderr
    assert "fetch origin" in completed.stderr

    calls = load_json_lines(harness.tool_log_path)
    rendered_calls = [
        " ".join([str(call["tool"]), *[str(arg) for arg in call["args"]]])
        for call in calls
    ]
    assert "git fetch origin" in rendered_calls
