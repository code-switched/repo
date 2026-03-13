"""Integration tests for `repo existing` command orchestration."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Return repository root for subprocess execution."""
    return Path(__file__).resolve().parents[2]


def write_fake_tool_runner(bin_dir: Path) -> None:
    """Write a shared python runner used by fake git/ssh wrappers."""
    runner = bin_dir / "fake_tool.py"
    runner.write_text(
        "import json\n"
        "import os\n"
        "import sys\n"
        "\n"
        "tool = sys.argv[1]\n"
        "args = sys.argv[2:]\n"
        "\n"
        "log_path = os.getenv('FAKE_TOOL_LOG', '').strip()\n"
        "if log_path:\n"
        "    with open(log_path, 'a', encoding='utf-8') as handle:\n"
        "        payload = {'tool': tool, 'args': args, 'cwd': os.getcwd()}\n"
        "        handle.write(json.dumps(payload) + '\\n')\n"
        "\n"
        "fail_spec = os.getenv('FAKE_TOOL_FAIL', '').strip()\n"
        "if fail_spec:\n"
        "    parts = fail_spec.split('|')\n"
        "    if len(parts) == 3:\n"
        "        fail_tool, fail_prefix, fail_code = parts\n"
        "        command = ' '.join(args)\n"
        "        if tool == fail_tool and command.startswith(fail_prefix):\n"
        "            sys.exit(int(fail_code))\n"
        "\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )


def write_fake_tool_wrappers(bin_dir: Path) -> None:
    """Create platform wrappers for fake git/ssh binaries."""
    tool_names = ("git", "ssh")
    if os.name == "nt":
        for tool_name in tool_names:
            wrapper = bin_dir / f"{tool_name}.cmd"
            wrapper.write_text(
                "@echo off\r\n"
                "\"%REPO_TEST_PYTHON%\" \"%~dp0fake_tool.py\" "
                f"{tool_name} %*\r\n",
                encoding="utf-8",
            )
        return

    for tool_name in tool_names:
        wrapper = bin_dir / tool_name
        wrapper.write_text(
            "#!/usr/bin/env sh\n"
            "\"$REPO_TEST_PYTHON\" \"$(dirname \"$0\")/fake_tool.py\" "
            f"{tool_name} \"$@\"\n",
            encoding="utf-8",
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)


def build_integration_env(tmp_path: Path) -> tuple[dict[str, str], Path]:
    """Build isolated env with fake git/ssh command wrappers."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    write_fake_tool_runner(bin_dir)
    write_fake_tool_wrappers(bin_dir)

    log_path = tmp_path / "tool_calls.jsonl"
    env = os.environ.copy()
    env["REPO_TEST_PYTHON"] = sys.executable
    env["FAKE_TOOL_LOG"] = str(log_path)
    if os.name == "nt":
        env["REPO_GIT_BIN"] = str(bin_dir / "git.cmd")
        env["REPO_SSH_BIN"] = str(bin_dir / "ssh.cmd")
    else:
        env["REPO_GIT_BIN"] = str(bin_dir / "git")
        env["REPO_SSH_BIN"] = str(bin_dir / "ssh")
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["DATA_DIR"] = str(tmp_path / "data")
    env["LOG_DIR"] = str(tmp_path / "data" / "logs")
    env["HOME"] = str(tmp_path / "home")
    env["USERPROFILE"] = str(tmp_path / "home")
    return env, log_path


def run_repo_existing_command(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run `python -m repo existing ...` as a subprocess."""
    command = [sys.executable, "-m", "repo", "existing", *args]
    return subprocess.run(
        command,
        cwd=get_project_root(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def load_tool_calls(log_path: Path) -> list[dict[str, object]]:
    """Load fake tool call records from JSONL file."""
    if not log_path.exists():
        return []
    with log_path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def test_repo_existing_non_interactive_success_flow(tmp_path: Path) -> None:
    """Command should orchestrate expected git/ssh sequence and create repo folder."""
    env, log_path = build_integration_env(tmp_path)
    repo_parent = tmp_path / "repos"

    completed = run_repo_existing_command(
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
        env=env,
    )

    assert completed.returncode == 0, completed.stderr
    repo_path = repo_parent / "demo"
    assert repo_path.exists()

    calls = load_tool_calls(log_path)
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
    env, log_path = build_integration_env(tmp_path)
    env["FAKE_TOOL_FAIL"] = "git|fetch origin|42"

    completed = run_repo_existing_command(
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
        env=env,
    )

    assert completed.returncode == 1
    assert "Command failed (42):" in completed.stderr
    assert "fetch origin" in completed.stderr

    calls = load_tool_calls(log_path)
    rendered_calls = [
        " ".join([str(call["tool"]), *[str(arg) for arg in call["args"]]])
        for call in calls
    ]
    assert "git fetch origin" in rendered_calls
