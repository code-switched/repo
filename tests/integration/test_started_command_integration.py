"""Integration tests for `repo started` command orchestration."""

from __future__ import annotations

from pathlib import Path

from .harness import build_integration_env, load_json_lines, run_repo_command


def build_started_args(project_path: Path, repo_name: str) -> list[str]:
    """Return canonical non-interactive args for repo started tests."""
    return [
        "--non-interactive",
        "--force",
        "--project-path",
        str(project_path),
        "--repo-name",
        repo_name,
        "--repo-type",
        "user",
        "--visibility",
        "private",
        "--username",
        "testuser",
        "--git-name",
        "Test User",
        "--git-email",
        "test@example.com",
        "--ssh-key",
        "~/.ssh/id_ed25519_testuser.pub",
        "--ssh-host",
        "testuser.github.com",
    ]


def test_repo_started_non_interactive_success_flow(tmp_path: Path) -> None:
    """Command should create remote and orchestrate expected git command sequence."""
    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / "README.md").write_text("hello\n", encoding="utf-8")

    harness = build_integration_env(
        tmp_path,
        tools=("git",),
        use_fake_ghapi=True,
    )
    harness.env["FAKE_GIT_STATUS"] = " M README.md\n"
    completed = run_repo_command(
        "started",
        build_started_args(project_path, repo_name="demo-started"),
        env=harness.env,
    )

    assert completed.returncode == 0, completed.stderr

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
        "git checkout -B main",
        "git remote remove origin",
        "git remote add origin git@testuser.github.com:testuser/demo-started.git",
        "git status --porcelain",
        "git add .",
        "git commit -m chore: init",
        "git push -u origin main",
    ]

    git_calls = [call for call in calls if call["tool"] == "git"]
    assert all(call["cwd"] == str(project_path) for call in git_calls)

    ghapi_calls = load_json_lines(harness.ghapi_log_path)
    create_calls = [
        call for call in ghapi_calls if call.get("method") == "create_for_authenticated_user"
    ]
    assert len(create_calls) == 1
    assert create_calls[0]["name"] == "demo-started"
    assert create_calls[0]["private"] is True


def test_repo_started_surfaces_subprocess_failures(tmp_path: Path) -> None:
    """Failing fake git command should surface as command error and non-zero exit."""
    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)

    harness = build_integration_env(
        tmp_path,
        tools=("git",),
        use_fake_ghapi=True,
    )
    harness.env["FAKE_TOOL_FAIL"] = "git|push -u origin main|42"
    completed = run_repo_command(
        "started",
        build_started_args(project_path, repo_name="demo-started"),
        env=harness.env,
    )

    assert completed.returncode == 1
    assert "Command failed (42):" in completed.stderr
    assert "push -u origin main" in completed.stderr

    calls = load_json_lines(harness.tool_log_path)
    rendered_calls = [
        " ".join([str(call["tool"]), *[str(arg) for arg in call["args"]]])
        for call in calls
    ]
    assert "git push -u origin main" in rendered_calls


def test_repo_started_dry_run_has_no_side_effects(tmp_path: Path) -> None:
    """Dry run should not execute subprocess commands or create .git metadata."""
    project_path = tmp_path / "project"
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / "notes.txt").write_text("hello\n", encoding="utf-8")

    harness = build_integration_env(
        tmp_path,
        tools=("git",),
        use_fake_ghapi=True,
    )
    args = ["--dry-run", *build_started_args(project_path, repo_name="demo-started")]
    completed = run_repo_command("started", args, env=harness.env)

    assert completed.returncode == 0, completed.stderr
    assert not (project_path / ".git").exists()
    assert load_json_lines(harness.tool_log_path) == []
    assert load_json_lines(harness.ghapi_log_path) == []
