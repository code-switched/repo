"""Integration tests for `repo started` command orchestration."""

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
    """Write shared python runner used by fake git wrapper."""
    runner = bin_dir / "fake_tool.py"
    runner.write_text(
        "import json\n"
        "import os\n"
        "import sys\n"
        "\n"
        "tool = sys.argv[1]\n"
        "args = sys.argv[2:]\n"
        "command = ' '.join(args)\n"
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
        "        if tool == fail_tool and command.startswith(fail_prefix):\n"
        "            sys.exit(int(fail_code))\n"
        "\n"
        "if tool == 'git' and command == 'status --porcelain':\n"
        "    status_output = os.getenv('FAKE_GIT_STATUS', '')\n"
        "    if status_output:\n"
        "        sys.stdout.write(status_output)\n"
        "\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )


def write_fake_git_wrapper(bin_dir: Path) -> Path:
    """Create platform wrapper for fake git binary and return path."""
    if os.name == "nt":
        wrapper = bin_dir / "git.cmd"
        wrapper.write_text(
            "@echo off\r\n"
            "\"%REPO_TEST_PYTHON%\" \"%~dp0fake_tool.py\" git %*\r\n",
            encoding="utf-8",
        )
        return wrapper

    wrapper = bin_dir / "git"
    wrapper.write_text(
        "#!/usr/bin/env sh\n"
        "\"$REPO_TEST_PYTHON\" \"$(dirname \"$0\")/fake_tool.py\" git \"$@\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)
    return wrapper


def write_fake_ghapi(stub_dir: Path) -> None:
    """Write fake ghapi package used by subprocess integration tests."""
    package_dir = stub_dir / "ghapi"
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "all.py").write_text(
        "import json\n"
        "import os\n"
        "\n"
        "def _log(event):\n"
        "    log_path = os.getenv('FAKE_GHAPI_LOG', '').strip()\n"
        "    if not log_path:\n"
        "        return\n"
        "    with open(log_path, 'a', encoding='utf-8') as handle:\n"
        "        handle.write(json.dumps(event) + '\\n')\n"
        "\n"
        "class _Org:\n"
        "    def __init__(self, login):\n"
        "        self.login = login\n"
        "\n"
        "class _Repos:\n"
        "    def create_for_authenticated_user(self, *, name, private):\n"
        "        _log({'method': 'create_for_authenticated_user', 'name': name, 'private': private})\n"
        "\n"
        "    def create_in_org(self, *, org, name, private):\n"
        "        _log({'method': 'create_in_org', 'org': org, 'name': name, 'private': private})\n"
        "\n"
        "class _Orgs:\n"
        "    def list_for_authenticated_user(self, *, per_page=100):\n"
        "        names = os.getenv('FAKE_GHAPI_ORGS', '').strip()\n"
        "        if not names:\n"
        "            return []\n"
        "        return [_Org(login=name) for name in names.split(',') if name]\n"
        "\n"
        "class GhApi:\n"
        "    def __init__(self, *, token):\n"
        "        _log({'method': 'init', 'token': token})\n"
        "        self.repos = _Repos()\n"
        "        self.orgs = _Orgs()\n",
        encoding="utf-8",
    )


def build_integration_env(tmp_path: Path) -> tuple[dict[str, str], Path, Path]:
    """Build isolated env with fake git and fake ghapi stubs."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    write_fake_tool_runner(bin_dir)
    git_wrapper_path = write_fake_git_wrapper(bin_dir)

    stub_dir = tmp_path / "stubs"
    write_fake_ghapi(stub_dir)

    tool_log_path = tmp_path / "tool_calls.jsonl"
    ghapi_log_path = tmp_path / "ghapi_calls.jsonl"
    env = os.environ.copy()
    env["REPO_TEST_PYTHON"] = sys.executable
    env["REPO_GIT_BIN"] = str(git_wrapper_path)
    env["FAKE_TOOL_LOG"] = str(tool_log_path)
    env["FAKE_GHAPI_LOG"] = str(ghapi_log_path)
    env["GH_TOKEN"] = "integration-test-token"
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["HOME"] = str(tmp_path / "home")
    env["USERPROFILE"] = str(tmp_path / "home")
    env["DATA_DIR"] = str(tmp_path / "data")
    env["LOG_DIR"] = str(tmp_path / "data" / "logs")

    current_pythonpath = env.get("PYTHONPATH", "").strip()
    if current_pythonpath:
        env["PYTHONPATH"] = f"{stub_dir}{os.pathsep}{current_pythonpath}"
    else:
        env["PYTHONPATH"] = str(stub_dir)

    return env, tool_log_path, ghapi_log_path


def run_repo_started_command(
    args: list[str],
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    """Run `python -m repo started ...` as a subprocess."""
    command = [sys.executable, "-m", "repo", "started", *args]
    return subprocess.run(
        command,
        cwd=get_project_root(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def load_json_lines(path: Path) -> list[dict[str, object]]:
    """Load JSON lines from file, returning empty list when missing."""
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


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

    env, tool_log_path, ghapi_log_path = build_integration_env(tmp_path)
    env["FAKE_GIT_STATUS"] = " M README.md\n"
    completed = run_repo_started_command(
        build_started_args(project_path, repo_name="demo-started"),
        env=env,
    )

    assert completed.returncode == 0, completed.stderr

    calls = load_json_lines(tool_log_path)
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

    ghapi_calls = load_json_lines(ghapi_log_path)
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

    env, tool_log_path, _ = build_integration_env(tmp_path)
    env["FAKE_TOOL_FAIL"] = "git|push -u origin main|42"
    completed = run_repo_started_command(
        build_started_args(project_path, repo_name="demo-started"),
        env=env,
    )

    assert completed.returncode == 1
    assert "Command failed (42):" in completed.stderr
    assert "push -u origin main" in completed.stderr

    calls = load_json_lines(tool_log_path)
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

    env, tool_log_path, ghapi_log_path = build_integration_env(tmp_path)
    args = ["--dry-run", *build_started_args(project_path, repo_name="demo-started")]
    completed = run_repo_started_command(args, env=env)

    assert completed.returncode == 0, completed.stderr
    assert not (project_path / ".git").exists()
    assert load_json_lines(tool_log_path) == []
    assert load_json_lines(ghapi_log_path) == []
