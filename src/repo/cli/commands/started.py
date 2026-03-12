"""Connect an existing local project to a new GitHub repository."""

from __future__ import annotations

import os
import argparse
import subprocess
from pathlib import Path
from dataclasses import dataclass

from ..console import ansi
from ...core.exceptions import CommandError
from ...core.github import create_github_api, create_repository, list_authenticated_orgs
from ._shared import (
    confirm_proceed,
    normalize_repo_type,
    normalize_visibility,
    print_section,
    print_summary,
    prompt_required,
    prompt_ssh_key,
    prompt_with_default,
)


@dataclass(frozen=True)
class StartedInputs:
    """Collected input for started command."""

    project_path: Path
    repo_name: str
    repo_type: str
    repo_visibility: str
    username: str
    git_name: str
    git_email: str
    ssh_key: str
    ssh_host: str
    owner: str | None


def register_started_command(subparsers: argparse._SubParsersAction) -> None:
    """Register `repo started`."""
    parser = subparsers.add_parser(
        "started",
        help="Create a GitHub repo from an existing local project",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview actions only")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Require flags instead of prompts",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip preflight confirmation prompt",
    )
    parser.add_argument("--project-path", help="Path to existing project")
    parser.add_argument("--repo-name", help="Override repository name")
    parser.add_argument("--repo-type", choices=["user", "org"], help="Owner type")
    parser.add_argument(
        "--visibility",
        choices=["public", "private"],
        help="Repository visibility",
    )
    parser.add_argument("--username", help="GitHub username")
    parser.add_argument("--git-name", help="Git user.name")
    parser.add_argument("--git-email", help="Git user.email")
    parser.add_argument("--ssh-key", help="SSH public key path")
    parser.add_argument("--ssh-host", help="SSH host alias (default: <username>.github.com)")
    parser.add_argument("--owner", help="Owner login when using --repo-type org")
    parser.set_defaults(func=run_started)


def run_started(args: argparse.Namespace) -> None:
    """Execute `repo started`."""
    inputs = collect_started_inputs(args)
    owner = inputs.owner
    owner_display = owner or (
        inputs.username if inputs.repo_type == "user" else "(select org during run)"
    )

    print_summary(
        "Preflight Summary",
        [
            ("Command", "repo started"),
            ("Project Path", str(inputs.project_path)),
            ("Repo Name", inputs.repo_name),
            ("Owner Type", inputs.repo_type),
            ("Owner", owner_display),
            ("Visibility", inputs.repo_visibility),
            ("SSH Host", inputs.ssh_host),
            ("Mode", "dry-run" if args.dry_run else "execute"),
        ],
    )
    if not args.non_interactive and not args.yes and not confirm_proceed():
        raise CommandError("Operation cancelled by user")

    try:
        if not args.non_interactive:
            print_section("Authentication")
            print("Open the browser profile associated with this GitHub account")
            input(f"This will log you in. Press {ansi.green}Enter{ansi.reset} to continue...")

            status_cmd = ["gh", "auth", "status"]
            print(f"\n{ansi.grey}{' '.join(status_cmd)}{ansi.reset}")
            if not args.dry_run:
                subprocess.run(status_cmd, check=False)

            logout_cmd = ["gh", "auth", "logout"]
            print(f"\n{ansi.grey}{' '.join(logout_cmd)}{ansi.reset}")
            if not args.dry_run:
                subprocess.run(logout_cmd, check=False)

            login_cmd = [
                "gh",
                "auth",
                "login",
                "--git-protocol",
                "ssh",
                "--hostname",
                "github.com",
                "--web",
            ]
            print(f"\n{ansi.grey}{' '.join(login_cmd)}{ansi.reset}")
            if not args.dry_run:
                subprocess.run(login_cmd, check=True)

            verify_cmd = ["gh", "auth", "status"]
            print(f"\n{ansi.grey}{' '.join(verify_cmd)}{ansi.reset}")
            if not args.dry_run:
                subprocess.run(verify_cmd, check=True)

            list_cmd = ["gh", "repo", "list"]
            print(f"\n{ansi.grey}{' '.join(list_cmd)}{ansi.reset}")
            if not args.dry_run:
                subprocess.run(list_cmd, check=True)

        api = None
        if not args.dry_run:
            api = create_github_api()

        if inputs.repo_type == "org" and not owner:
            if args.dry_run:
                owner = "<org>"
            else:
                owner = select_org(api)

        if inputs.repo_type == "user":
            owner = inputs.username

        if not owner:
            raise CommandError("Unable to resolve repository owner")

        print_section("Repository")
        if args.dry_run:
            print(
                f"\n{ansi.yellow}[dry-run]{ansi.reset} would create "
                f"{owner}/{inputs.repo_name} ({inputs.repo_visibility})"
            )
        else:
            create_repository(
                api=api,
                owner_type=inputs.repo_type,
                owner=owner,
                repo_name=inputs.repo_name,
                private=inputs.repo_visibility == "private",
            )

        if args.dry_run:
            print(f"\n{ansi.yellow}[dry-run]{ansi.reset} cwd -> {inputs.project_path}")
        else:
            os.chdir(inputs.project_path)

        print_section("Git Configuration")
        if not (inputs.project_path / ".git").exists():
            init_cmd = ["git", "init"]
            print(f"\n{ansi.grey}{' '.join(init_cmd)}{ansi.reset}")
            if not args.dry_run:
                subprocess.run(init_cmd, cwd=inputs.project_path, check=True)

        user_name_cmd = ["git", "config", "user.name", inputs.git_name]
        print(f"\n{ansi.grey}{' '.join(user_name_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(user_name_cmd, cwd=inputs.project_path, check=True)

        user_email_cmd = ["git", "config", "user.email", inputs.git_email]
        print(f"\n{ansi.grey}{' '.join(user_email_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(user_email_cmd, cwd=inputs.project_path, check=True)

        signing_key_cmd = ["git", "config", "user.signingkey", inputs.ssh_key]
        print(f"\n{ansi.grey}{' '.join(signing_key_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(signing_key_cmd, cwd=inputs.project_path, check=True)

        gpg_format_cmd = ["git", "config", "gpg.format", "ssh"]
        print(f"\n{ansi.grey}{' '.join(gpg_format_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(gpg_format_cmd, cwd=inputs.project_path, check=True)

        gpg_sign_cmd = ["git", "config", "commit.gpgsign", "true"]
        print(f"\n{ansi.grey}{' '.join(gpg_sign_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(gpg_sign_cmd, cwd=inputs.project_path, check=True)

        pull_rebase_cmd = ["git", "config", "pull.rebase", "true"]
        print(f"\n{ansi.grey}{' '.join(pull_rebase_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(pull_rebase_cmd, cwd=inputs.project_path, check=True)

        checkout_cmd = ["git", "checkout", "-B", "main"]
        print(f"\n{ansi.grey}{' '.join(checkout_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(checkout_cmd, cwd=inputs.project_path, check=True)

        remote_url = f"git@{inputs.ssh_host}:{owner}/{inputs.repo_name}.git"
        remove_origin_cmd = ["git", "remote", "remove", "origin"]
        print(f"\n{ansi.grey}{' '.join(remove_origin_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(remove_origin_cmd, cwd=inputs.project_path, check=False)

        add_origin_cmd = ["git", "remote", "add", "origin", remote_url]
        print(f"\n{ansi.grey}{' '.join(add_origin_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(add_origin_cmd, cwd=inputs.project_path, check=True)

        print_section("Initial Commit")
        status_cmd = ["git", "status", "--porcelain"]
        print(f"\n{ansi.grey}{' '.join(status_cmd)}{ansi.reset}")
        status_output = ""
        if not args.dry_run:
            completed = subprocess.run(
                status_cmd,
                cwd=inputs.project_path,
                capture_output=True,
                text=True,
                check=True,
            )
            status_output = completed.stdout.strip()

        if args.dry_run or status_output:
            add_cmd = ["git", "add", "."]
            print(f"\n{ansi.grey}{' '.join(add_cmd)}{ansi.reset}")
            if not args.dry_run:
                subprocess.run(add_cmd, cwd=inputs.project_path, check=True)

            commit_cmd = ["git", "commit", "-m", "chore: init"]
            print(f"\n{ansi.grey}{' '.join(commit_cmd)}{ansi.reset}")
            if not args.dry_run:
                subprocess.run(commit_cmd, cwd=inputs.project_path, check=True)

        push_cmd = ["git", "push", "-u", "origin", "main"]
        print(f"\n{ansi.grey}{' '.join(push_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(push_cmd, cwd=inputs.project_path, check=True)

        print(f"\n{ansi.green}Repository setup complete!{ansi.reset}")
    except subprocess.CalledProcessError as exc:
        command = exc.cmd if isinstance(exc.cmd, str) else " ".join(exc.cmd)
        raise CommandError(f"Command failed ({exc.returncode}): {command}") from exc
    except FileNotFoundError as exc:
        executable = exc.filename or "unknown executable"
        raise CommandError(f"Required executable not found: {executable}") from exc


def collect_started_inputs(args: argparse.Namespace) -> StartedInputs:
    """Collect started command inputs from args or prompts."""
    project_path = resolve_project_path(args)

    default_repo_name = project_path.name
    if args.repo_name:
        repo_name = args.repo_name.strip()
    elif args.non_interactive:
        repo_name = default_repo_name
    else:
        print(
            "Current folder name will be used as repo name: "
            f"{ansi.cyan}{default_repo_name}{ansi.reset}"
        )
        entered_name = input(
            "Press Enter to keep or type new name: "
            f"{ansi.grey}(default: {default_repo_name}){ansi.reset} "
        ).strip()
        repo_name = entered_name or default_repo_name

    if args.repo_type:
        repo_type = normalize_repo_type(args.repo_type)
    elif args.non_interactive:
        raise CommandError("--repo-type is required in --non-interactive mode")
    else:
        entered_type = prompt_with_default(
            f"Is this repo for an organization or a user? "
            f"({ansi.cyan}user{ansi.reset} / {ansi.magenta}org{ansi.reset}):",
            "user",
        )
        repo_type = normalize_repo_type(entered_type)

    if args.visibility:
        repo_visibility = normalize_visibility(args.visibility)
    elif args.non_interactive:
        raise CommandError("--visibility is required in --non-interactive mode")
    else:
        entered_visibility = prompt_with_default(
            f"Enter repo visibility "
            f"({ansi.cyan}public{ansi.reset} / {ansi.magenta}private{ansi.reset}):",
            "private",
        )
        repo_visibility = normalize_visibility(entered_visibility)

    if args.username:
        username = args.username.strip()
    elif args.non_interactive:
        raise CommandError("--username is required in --non-interactive mode")
    else:
        username = prompt_required("Enter your GitHub username: ")

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

    owner = args.owner.strip() if args.owner else None
    if repo_type == "org" and args.non_interactive and not owner:
        raise CommandError("--owner is required for org repos in --non-interactive mode")

    return StartedInputs(
        project_path=project_path,
        repo_name=repo_name,
        repo_type=repo_type,
        repo_visibility=repo_visibility,
        username=username,
        git_name=git_name,
        git_email=git_email,
        ssh_key=ssh_key,
        ssh_host=ssh_host,
        owner=owner,
    )


def resolve_project_path(args: argparse.Namespace) -> Path:
    """Resolve and validate target project path."""
    if args.project_path:
        project_path = Path(args.project_path).expanduser().resolve()
    elif args.non_interactive:
        project_path = Path.cwd().resolve()
    else:
        print(
            "Enter the path to your existing project: "
            f"{ansi.grey}(or press Enter for current directory){ansi.reset}"
        )
        entered_path = input(" > ").strip()
        project_path = Path(entered_path).expanduser().resolve() if entered_path else Path.cwd().resolve()

    if not project_path.exists():
        raise CommandError(f"The specified path does not exist: {project_path}")

    if not project_path.is_dir():
        raise CommandError(f"The specified path is not a directory: {project_path}")

    return project_path


def select_org(api) -> str:
    """Prompt user to select an organization."""
    print(f"\nNote: {ansi.red}NEW organizations must be created via GitHub web interface.{ansi.reset}")
    print("Select the organization you want to create the repo for:")
    org_names = list_authenticated_orgs(api)
    if not org_names:
        raise CommandError("No organizations found for the authenticated user")

    for index, org_name in enumerate(org_names, start=1):
        print(f"{ansi.yellow}{index}.{ansi.reset} {org_name}")

    selection = input("Select the organization by number: ").strip()
    if not selection.isdigit():
        raise CommandError("Invalid selection. Choose an organization from the list")

    numeric_index = int(selection)
    if numeric_index < 1 or numeric_index > len(org_names):
        raise CommandError("Invalid selection. Choose an organization from the list")

    return org_names[numeric_index - 1]
