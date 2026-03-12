"""Set up local access to an existing GitHub repository."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from dataclasses import dataclass

from ..console import ansi
from ...core.exceptions import CommandError
from ._shared import (
    YES_VALUES,
    parse_repo_coordinates,
    prompt_required,
    prompt_ssh_key,
    prompt_with_default,
)


@dataclass(frozen=True)
class ExistingInputs:
    """Collected input for existing repo setup."""

    username: str
    git_repo_url: str
    git_repo_branch: str
    git_name: str
    git_email: str
    repo_parent_folder: Path
    ssh_key: str
    ssh_host: str


def register_existing_command(subparsers: argparse._SubParsersAction) -> None:
    """Register `repo existing`."""
    parser = subparsers.add_parser(
        "existing",
        help="Connect to an existing remote repository",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview actions only")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Require flags instead of prompts",
    )
    parser.add_argument("--username", help="GitHub username")
    parser.add_argument("--repo-url", help="Repository URL (HTTPS or SSH)")
    parser.add_argument("--branch", help="Git branch name (default: main)")
    parser.add_argument("--git-name", help="Git user.name")
    parser.add_argument("--git-email", help="Git user.email")
    parser.add_argument("--repo-parent-folder", help="Parent folder to create repo in")
    parser.add_argument("--ssh-key", help="SSH public key path")
    parser.add_argument("--ssh-host", help="SSH host alias (default: <username>.github.com)")
    parser.add_argument(
        "--confirm-permissions",
        action="store_true",
        help="Skip collaborator confirmation prompt",
    )
    parser.set_defaults(func=run_existing)


def run_existing(args: argparse.Namespace) -> None:
    """Execute `repo existing`."""
    inputs = collect_existing_inputs(args)
    organization, repo_name = parse_repo_coordinates(inputs.git_repo_url)

    if inputs.username != organization and not args.confirm_permissions:
        if args.non_interactive:
            raise CommandError(
                "--confirm-permissions is required when username differs from owner "
                "in --non-interactive mode"
            )

        permission_answer = input(
            "Do you have permissions as "
            f"{ansi.cyan}{inputs.username}{ansi.reset} to access the "
            f"{ansi.red}{organization}{ansi.reset} repo? (y/N): "
        )
        if permission_answer.strip().lower() not in YES_VALUES:
            raise CommandError(
                "Please ask the repo owner to add you as a collaborator and try again"
            )

    repo_path = inputs.repo_parent_folder / repo_name

    try:
        if args.dry_run:
            print(f"\n{ansi.yellow}[dry-run]{ansi.reset} would create {repo_path}")
        else:
            repo_path.mkdir(parents=True, exist_ok=True)

        init_cmd = ["git", "init"]
        print(f"\n{ansi.grey}{' '.join(init_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(init_cmd, cwd=repo_path, check=True)

        user_name_cmd = ["git", "config", "user.name", inputs.git_name]
        print(f"\n{ansi.grey}{' '.join(user_name_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(user_name_cmd, cwd=repo_path, check=True)

        user_email_cmd = ["git", "config", "user.email", inputs.git_email]
        print(f"\n{ansi.grey}{' '.join(user_email_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(user_email_cmd, cwd=repo_path, check=True)

        if not args.non_interactive:
            key_added = input(
                f"Have you added your SSH key to GitHub? "
                f"{ansi.yellow}This is the last step.{ansi.reset} (y/N): "
            )
            if key_added.strip().lower() not in YES_VALUES:
                raise CommandError("Please add your SSH key to GitHub and try again")

        signing_key_cmd = ["git", "config", "user.signingkey", inputs.ssh_key]
        print(f"\n{ansi.grey}{' '.join(signing_key_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(signing_key_cmd, cwd=repo_path, check=True)

        gpg_format_cmd = ["git", "config", "gpg.format", "ssh"]
        print(f"\n{ansi.grey}{' '.join(gpg_format_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(gpg_format_cmd, cwd=repo_path, check=True)

        gpg_sign_cmd = ["git", "config", "commit.gpgsign", "true"]
        print(f"\n{ansi.grey}{' '.join(gpg_sign_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(gpg_sign_cmd, cwd=repo_path, check=True)

        pull_rebase_cmd = ["git", "config", "pull.rebase", "true"]
        print(f"\n{ansi.grey}{' '.join(pull_rebase_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(pull_rebase_cmd, cwd=repo_path, check=True)

        print("Add commit signing to any VSCodium based editor by adding the following to settings.json:")
        print(f"{ansi.cyan}")
        print("{")
        print('    "git.enableCommitSigning": true')
        print("}")
        print(f"{ansi.reset}")
        print(
            f"Alternatively, press {ansi.yellow}Cmd/Ctrl + Shift + P{ansi.reset}, "
            "search for "
            f"{ansi.yellow}\"Preferences: Open Settings (UI)\"{ansi.reset}"
        )
        print(
            "Under User Settings, search "
            f"{ansi.yellow}\"Enable Commit Signing\"{ansi.reset} and turn it on"
        )

        ssh_test_cmd = ["ssh", "-T", f"git@{inputs.ssh_host}"]
        print(f"\n{ansi.grey}{' '.join(ssh_test_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(ssh_test_cmd, check=False)

        remote_url = f"git@{inputs.ssh_host}:{organization}/{repo_name}.git"
        remove_origin_cmd = ["git", "remote", "remove", "origin"]
        print(f"\n{ansi.grey}{' '.join(remove_origin_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(remove_origin_cmd, cwd=repo_path, check=False)

        add_origin_cmd = ["git", "remote", "add", "origin", remote_url]
        print(f"\n{ansi.grey}{' '.join(add_origin_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(add_origin_cmd, cwd=repo_path, check=True)

        fetch_cmd = ["git", "fetch", "origin"]
        print(f"\n{ansi.grey}{' '.join(fetch_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(fetch_cmd, cwd=repo_path, check=True)

        checkout_cmd = [
            "git",
            "checkout",
            "-B",
            inputs.git_repo_branch,
            f"origin/{inputs.git_repo_branch}",
        ]
        print(f"\n{ansi.grey}{' '.join(checkout_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(checkout_cmd, cwd=repo_path, check=True)

        pull_cmd = ["git", "pull"]
        print(f"\n{ansi.grey}{' '.join(pull_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(pull_cmd, cwd=repo_path, check=True)

        print(f"{ansi.green}Repository setup complete!{ansi.reset}")
    except subprocess.CalledProcessError as exc:
        command = exc.cmd if isinstance(exc.cmd, str) else " ".join(exc.cmd)
        raise CommandError(f"Command failed ({exc.returncode}): {command}") from exc
    except FileNotFoundError as exc:
        executable = exc.filename or "unknown executable"
        raise CommandError(f"Required executable not found: {executable}") from exc


def collect_existing_inputs(args: argparse.Namespace) -> ExistingInputs:
    """Collect existing command inputs from args or prompts."""
    if args.username:
        username = args.username.strip()
    elif args.non_interactive:
        raise CommandError("--username is required in --non-interactive mode")
    else:
        username = prompt_required("Enter your GitHub username: ")

    if args.repo_url:
        git_repo_url = args.repo_url.strip().rstrip("/")
    elif args.non_interactive:
        raise CommandError("--repo-url is required in --non-interactive mode")
    else:
        git_repo_url = prompt_required("Enter git repo url: ").rstrip("/")

    if args.branch:
        git_repo_branch = args.branch.strip()
    elif args.non_interactive:
        git_repo_branch = "main"
    else:
        git_repo_branch = prompt_with_default("Enter git repo branch:", "main")

    if args.git_name:
        git_name = args.git_name.strip()
    elif args.non_interactive:
        raise CommandError("--git-name is required in --non-interactive mode")
    else:
        git_name = prompt_required("Enter git name: ")

    if args.git_email:
        git_email = args.git_email.strip()
    elif args.non_interactive:
        raise CommandError("--git-email is required in --non-interactive mode")
    else:
        git_email = prompt_required("Enter git email: ")

    if args.repo_parent_folder:
        repo_parent_folder = Path(args.repo_parent_folder).expanduser()
    elif args.non_interactive:
        raise CommandError("--repo-parent-folder is required in --non-interactive mode")
    else:
        print(
            "Enter the folder where you want to create the repo "
            f"(e.g. {ansi.cyan}~/Documents{ansi.reset} or "
            f"{ansi.cyan}C:\\Users\\YourName\\Documents{ansi.reset}): "
        )
        entered_folder = prompt_required(" > ")
        repo_parent_folder = Path(entered_folder).expanduser()

    if args.ssh_key:
        ssh_key = args.ssh_key.strip()
    elif args.non_interactive:
        raise CommandError("--ssh-key is required in --non-interactive mode")
    else:
        ssh_key = prompt_ssh_key(username)

    default_host = f"{username}.github.com"
    if args.ssh_host:
        ssh_host = args.ssh_host.strip()
    elif args.non_interactive:
        ssh_host = default_host
    else:
        print(f"Enter the SSH host for GitHub: {ansi.grey}(default: {default_host}){ansi.reset}")
        ssh_host = input(f"{ansi.grey} > {ansi.reset}").strip() or default_host

    return ExistingInputs(
        username=username,
        git_repo_url=git_repo_url,
        git_repo_branch=git_repo_branch,
        git_name=git_name,
        git_email=git_email,
        repo_parent_folder=repo_parent_folder,
        ssh_key=ssh_key,
        ssh_host=ssh_host,
    )
