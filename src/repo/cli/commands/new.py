"""Create a brand-new GitHub repository and local clone."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from dataclasses import dataclass

from ..console import ansi
from ...core.exceptions import CommandError
from ...core.github import create_github_api, create_repository, list_authenticated_orgs
from ._shared import (
    YES_VALUES,
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
class NewInputs:
    """Collected input for the new repo workflow."""

    repo_parent_folder: Path
    repo_name: str
    git_repo_branch: str
    repo_type: str
    repo_visibility: str
    username: str
    git_name: str
    git_email: str
    ssh_key: str
    ssh_host: str
    owner: str | None


def register_new_command(subparsers: argparse._SubParsersAction) -> None:
    """Register `repo new`."""
    parser = subparsers.add_parser(
        "new",
        help="Create a new GitHub repository and local clone",
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
    parser.add_argument("--repo-parent-folder", help="Local parent folder for the repo")
    parser.add_argument("--repo-name", help="Repository name")
    parser.add_argument("--branch", help="Git branch name (default: main)")
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
    parser.set_defaults(func=run_new)


def run_new(args: argparse.Namespace) -> None:
    """Execute `repo new`."""
    inputs = collect_new_inputs(args)
    owner = inputs.owner
    owner_display = owner or (
        inputs.username if inputs.repo_type == "user" else "(select org during run)"
    )

    print_summary(
        "Preflight Summary",
        [
            ("Command", "repo new"),
            ("Repo Name", inputs.repo_name),
            ("Owner Type", inputs.repo_type),
            ("Owner", owner_display),
            ("Visibility", inputs.repo_visibility),
            ("Branch", inputs.git_repo_branch),
            ("Target Dir", str(inputs.repo_parent_folder)),
            ("SSH Host", inputs.ssh_host),
            ("Mode", "dry-run" if args.dry_run else "execute"),
        ],
    )
    if not args.non_interactive and not args.yes and not confirm_proceed():
        raise CommandError("Operation cancelled by user")

    try:
        inputs.repo_parent_folder.mkdir(parents=True, exist_ok=True)

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

            config_familiar = input("\nIs the above configuration familiar? (y/N): ")
            if config_familiar.strip().lower() not in YES_VALUES:
                raise CommandError("Please adjust ~/.ssh/config and run again")

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

        remote_url = f"git@{inputs.ssh_host}:{owner}/{inputs.repo_name}.git"
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

        clone_cmd = ["git", "clone", remote_url]
        print(f"\n{ansi.grey}{' '.join(clone_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(clone_cmd, cwd=inputs.repo_parent_folder, check=True)

        repo_path = inputs.repo_parent_folder / inputs.repo_name
        if not args.dry_run and not repo_path.exists():
            repo_path.mkdir(parents=True, exist_ok=True)

        print_section("Git Configuration")
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

        user_name_cmd = ["git", "config", "user.name", inputs.git_name]
        print(f"\n{ansi.grey}{' '.join(user_name_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(user_name_cmd, cwd=repo_path, check=True)

        email_cmd = ["git", "config", "user.email", inputs.git_email]
        print(f"\n{ansi.grey}{' '.join(email_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(email_cmd, cwd=repo_path, check=True)

        remove_origin_cmd = ["git", "remote", "remove", "origin"]
        print(f"\n{ansi.grey}{' '.join(remove_origin_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(remove_origin_cmd, cwd=repo_path, check=False)

        add_origin_cmd = ["git", "remote", "add", "origin", remote_url]
        print(f"\n{ansi.grey}{' '.join(add_origin_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(add_origin_cmd, cwd=repo_path, check=True)

        checkout_cmd = ["git", "checkout", "-B", inputs.git_repo_branch]
        print(f"\n{ansi.grey}{' '.join(checkout_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(checkout_cmd, cwd=repo_path, check=True)

        print_section("Initial Commit")
        if args.dry_run:
            print(
                f"\n{ansi.yellow}[dry-run]{ansi.reset} would create "
                f"{repo_path / 'README.md'}"
            )
        else:
            readme_path = repo_path / "README.md"
            if not readme_path.exists():
                readme_path.write_text("", encoding="utf-8")

        add_cmd = ["git", "add", "."]
        print(f"\n{ansi.grey}{' '.join(add_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(add_cmd, cwd=repo_path, check=True)

        commit_cmd = ["git", "commit", "-m", "chore: init"]
        print(f"\n{ansi.grey}{' '.join(commit_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(commit_cmd, cwd=repo_path, check=True)

        push_cmd = ["git", "push", "-u", "origin", inputs.git_repo_branch]
        print(f"\n{ansi.grey}{' '.join(push_cmd)}{ansi.reset}")
        if not args.dry_run:
            subprocess.run(push_cmd, cwd=repo_path, check=True)

        print(f"\n{ansi.green}Repository setup complete!{ansi.reset}")
    except subprocess.CalledProcessError as exc:
        command = exc.cmd if isinstance(exc.cmd, str) else " ".join(exc.cmd)
        raise CommandError(f"Command failed ({exc.returncode}): {command}") from exc
    except FileNotFoundError as exc:
        executable = exc.filename or "unknown executable"
        raise CommandError(f"Required executable not found: {executable}") from exc


def collect_new_inputs(args: argparse.Namespace) -> NewInputs:
    """Collect new command inputs from args or prompts."""
    if args.repo_parent_folder:
        repo_parent_folder = Path(args.repo_parent_folder).expanduser()
    elif args.non_interactive:
        raise CommandError("--repo-parent-folder is required in --non-interactive mode")
    else:
        print(
            "Enter the local parent folder for the new repo "
            f"(e.g. {ansi.cyan}~/Documents{ansi.reset} or "
            f"{ansi.cyan}C:\\Users\\Name\\Documents{ansi.reset}): "
        )
        entered = prompt_required(" > ")
        repo_parent_folder = Path(entered).expanduser()

    if args.repo_name:
        repo_name = args.repo_name.strip()
    elif args.non_interactive:
        raise CommandError("--repo-name is required in --non-interactive mode")
    else:
        repo_name = prompt_required("Enter the name of the new repo: ")

    if args.branch:
        git_repo_branch = args.branch.strip()
    elif args.non_interactive:
        git_repo_branch = "main"
    else:
        git_repo_branch = prompt_with_default("Enter git repo branch:", "main")

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

    return NewInputs(
        repo_parent_folder=repo_parent_folder,
        repo_name=repo_name,
        git_repo_branch=git_repo_branch,
        repo_type=repo_type,
        repo_visibility=repo_visibility,
        username=username,
        git_name=git_name,
        git_email=git_email,
        ssh_key=ssh_key,
        ssh_host=ssh_host,
        owner=owner,
    )


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
