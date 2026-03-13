"""Shared helpers for subprocess-based integration tests."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IntegrationHarness:
    """Holds isolated environment and log file paths for integration tests."""

    env: dict[str, str]
    tool_log_path: Path
    ghapi_log_path: Path | None = None


def get_project_root() -> Path:
    """Return repository root for subprocess execution."""
    return Path(__file__).resolve().parents[2]


def build_integration_env(
    tmp_path: Path,
    *,
    tools: tuple[str, ...],
    use_fake_ghapi: bool = False,
) -> IntegrationHarness:
    """Build isolated env with fake command wrappers and optional fake ghapi."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    write_fake_tool_runner(bin_dir)
    wrappers = write_fake_tool_wrappers(bin_dir, tools)

    env = os.environ.copy()
    env["REPO_TEST_PYTHON"] = sys.executable
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["HOME"] = str(tmp_path / "home")
    env["USERPROFILE"] = str(tmp_path / "home")
    env["DATA_DIR"] = str(tmp_path / "data")
    env["LOG_DIR"] = str(tmp_path / "data" / "logs")

    tool_log_path = tmp_path / "tool_calls.jsonl"
    env["FAKE_TOOL_LOG"] = str(tool_log_path)

    if "git" in wrappers:
        env["REPO_GIT_BIN"] = str(wrappers["git"])

    if "ssh" in wrappers:
        env["REPO_SSH_BIN"] = str(wrappers["ssh"])

    if not use_fake_ghapi:
        return IntegrationHarness(env=env, tool_log_path=tool_log_path)

    stub_dir = tmp_path / "stubs"
    write_fake_ghapi(stub_dir)
    env["GH_TOKEN"] = "integration-test-token"
    ghapi_log_path = tmp_path / "ghapi_calls.jsonl"
    env["FAKE_GHAPI_LOG"] = str(ghapi_log_path)
    prepend_pythonpath(env, stub_dir)
    return IntegrationHarness(
        env=env,
        tool_log_path=tool_log_path,
        ghapi_log_path=ghapi_log_path,
    )


def write_fake_tool_runner(bin_dir: Path) -> None:
    """Write shared python runner used by fake command wrappers."""
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


def write_fake_tool_wrappers(
    bin_dir: Path,
    tools: tuple[str, ...],
) -> dict[str, Path]:
    """Create platform wrappers for selected fake tools."""
    wrappers: dict[str, Path] = {}
    if os.name == "nt":
        for tool_name in tools:
            wrapper = bin_dir / f"{tool_name}.cmd"
            wrapper.write_text(
                "@echo off\r\n"
                "\"%REPO_TEST_PYTHON%\" \"%~dp0fake_tool.py\" "
                f"{tool_name} %*\r\n",
                encoding="utf-8",
            )
            wrappers[tool_name] = wrapper
        return wrappers

    for tool_name in tools:
        wrapper = bin_dir / tool_name
        wrapper.write_text(
            "#!/usr/bin/env sh\n"
            "\"$REPO_TEST_PYTHON\" \"$(dirname \"$0\")/fake_tool.py\" "
            f"{tool_name} \"$@\"\n",
            encoding="utf-8",
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)
        wrappers[tool_name] = wrapper
    return wrappers


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


def prepend_pythonpath(env: dict[str, str], path: Path) -> None:
    """Prepend path to PYTHONPATH in env."""
    existing = env.get("PYTHONPATH", "").strip()
    if not existing:
        env["PYTHONPATH"] = str(path)
        return

    env["PYTHONPATH"] = f"{path}{os.pathsep}{existing}"


def run_repo_command(
    subcommand: str,
    args: list[str],
    *,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    """Run `python -m repo <subcommand> ...` as a subprocess."""
    command = [sys.executable, "-m", "repo", subcommand, *args]
    return subprocess.run(
        command,
        cwd=get_project_root(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def load_json_lines(path: Path | None) -> list[dict[str, object]]:
    """Load JSON lines from file, returning empty list when missing."""
    if path is None:
        return []

    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
