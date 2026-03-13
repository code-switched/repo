"""Set up and verify SSH keys for GitHub workflows."""

from __future__ import annotations

import re
import socket
import getpass
import argparse
import logging
import subprocess
from pathlib import Path
from dataclasses import dataclass

from ..console import ansi
from ...core.exceptions import CommandError
from ._shared import (
    YES_VALUES,
    confirm_proceed,
    log_command,
    print_section,
    print_summary,
    prompt_required,
    prompt_with_default,
)

logger = logging.getLogger("repo.cli.commands.ssh")


@dataclass(frozen=True)
class SshSelection:
    """Resolved SSH key selection details."""

    key_path: Path
    account_name: str
    email: str


def register_ssh_command(subparsers: argparse._SubParsersAction) -> None:
    """Register `repo ssh`."""
    parser = subparsers.add_parser(
        "ssh",
        help="Set up SSH keys for GitHub",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview actions only")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Require flags instead of prompts",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip preflight confirmation prompt",
    )
    parser.add_argument("--account-name", help="GitHub account alias for SSH host")
    parser.add_argument("--email", help="SSH key email/comment")
    parser.add_argument("--machine-name", help="Machine label for key filename")
    parser.add_argument("--key-path", help="Use existing private key path")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Force generation of a new key",
    )
    parser.set_defaults(func=run_ssh)


def run_ssh(args: argparse.Namespace) -> None:
    """Execute `repo ssh`."""
    public_keys = sorted((Path.home() / ".ssh").glob("*.pub"))
    mode = "generate" if args.generate else "reuse-or-select"
    key_source = args.key_path if args.key_path else "(auto)"
    logger.info(
        "workflow_start command=repo ssh mode=%s key_source=%s account=%s dry_run=%s non_interactive=%s",
        mode,
        key_source,
        args.account_name or "",
        args.dry_run,
        args.non_interactive,
    )

    print_summary(
        "Preflight Summary",
        [
            ("Command", "repo ssh"),
            ("Mode", mode),
            ("Key Source", key_source),
            ("Account", args.account_name or "(prompt/infer)"),
            ("Dry Run", "yes" if args.dry_run else "no"),
        ],
    )
    if not args.non_interactive and not args.force and not confirm_proceed():
        raise CommandError("Operation cancelled by user")

    try:
        print_section("SSH Key Selection")
        selection = resolve_key_selection(args, public_keys)
        print_section("SSH Config")
        update_ssh_config(selection.key_path, selection.account_name, selection.email, args.dry_run)

        public_key_path = Path(f"{selection.key_path}.pub")
        if args.dry_run:
            print(f"\n{ansi.yellow}[dry-run]{ansi.reset} would read {public_key_path}")
        else:
            if not public_key_path.exists():
                raise CommandError(f"Public key not found: {public_key_path}")

            public_key = public_key_path.read_text(encoding="utf-8").strip()
            print("\nPlease add your public key to GitHub:")
            print(f"{ansi.cyan}{public_key}{ansi.reset}")

        if not args.non_interactive:
            input(f"\nPress {ansi.green}Enter{ansi.reset} when you've added the key to GitHub...")

        host = f"{selection.account_name}.github.com"
        print_section("Verification")
        test_cmd = ["ssh", "-T", f"git@{host}"]
        log_command(logger, test_cmd, dry_run=args.dry_run)
        print(f"\n{ansi.grey}{' '.join(test_cmd)}{ansi.reset}")
        if args.dry_run:
            print(f"{ansi.yellow}[dry-run]{ansi.reset} would test SSH connection")
        else:
            result = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            combined_output = f"{result.stdout}\n{result.stderr}"
            if "successfully authenticated" in combined_output:
                logger.info("workflow_complete command=repo ssh host=%s", host)
                print(f"{ansi.green}SSH setup completed successfully!{ansi.reset}")
            else:
                logger.warning("workflow_verification_failed command=repo ssh host=%s", host)
                print(f"{ansi.red}SSH setup failed. Please check your configuration and try again.{ansi.reset}")

        print(f"\n{ansi.yellow}Reminder:{ansi.reset} Please reorganize your ~/.ssh/config file as needed.")
    except subprocess.CalledProcessError as exc:
        command = exc.cmd if isinstance(exc.cmd, str) else " ".join(exc.cmd)
        logger.error("workflow_failed command=repo ssh subprocess=%s", command)
        raise CommandError(f"Command failed ({exc.returncode}): {command}") from exc
    except FileNotFoundError as exc:
        executable = exc.filename or "unknown executable"
        logger.error("workflow_failed command=repo ssh executable=%s", executable)
        raise CommandError(f"Required executable not found: {executable}") from exc


def resolve_key_selection(args: argparse.Namespace, public_keys: list[Path]) -> SshSelection:
    """Resolve whether to use an existing key or generate a new one."""
    if args.key_path:
        key_path = Path(args.key_path).expanduser()
        account_name, email = infer_or_prompt_key_metadata(args, key_path)
        return SshSelection(key_path=key_path, account_name=account_name, email=email)

    if args.generate:
        return generate_ssh_key(args)

    if not public_keys:
        print("No existing SSH keys found. Generating a new key.")
        return generate_ssh_key(args)

    print("Existing SSH keys found:")
    for index, key in enumerate(public_keys, start=1):
        print(f"{ansi.yellow}{index}.{ansi.reset} {key.name}")

    if args.non_interactive:
        key_path = public_keys[0].with_suffix("")
        account_name, email = infer_or_prompt_key_metadata(args, key_path)
        return SshSelection(key_path=key_path, account_name=account_name, email=email)

    make_new = input("Do you want to make a new key? (y/N): ").strip().lower()
    if make_new in YES_VALUES:
        return generate_ssh_key(args)

    selection = input("Enter the number of the key you want to use: ").strip()
    if not selection.isdigit():
        raise CommandError("Invalid selection")

    numeric_index = int(selection)
    if numeric_index < 1 or numeric_index > len(public_keys):
        raise CommandError("Invalid selection")

    key_path = public_keys[numeric_index - 1].with_suffix("")
    account_name, email = infer_or_prompt_key_metadata(args, key_path)
    return SshSelection(key_path=key_path, account_name=account_name, email=email)


def generate_ssh_key(args: argparse.Namespace) -> SshSelection:
    """Generate a new SSH key pair."""
    account_name = args.account_name
    if not account_name:
        if args.non_interactive:
            raise CommandError("--account-name is required to generate in --non-interactive mode")
        account_name = prompt_required("Enter your git account name (e.g., personal, user_name): ")

    user = getpass.getuser()
    hostname = socket.gethostname().replace(".local", "").replace(".home", "")
    user_hostname = f"{user}@{hostname}.local"

    if args.email:
        email = args.email
    elif args.non_interactive:
        email = user_hostname
    else:
        email = prompt_with_default("Enter your email:", user_hostname)

    default_machine_name = re.sub(r"[^a-z0-9]", "", hostname.lower())
    if args.machine_name:
        machine_name = args.machine_name
    elif args.non_interactive:
        machine_name = default_machine_name
    else:
        machine_name = prompt_with_default(
            "Enter your machine name (e.g., desktop, laptop):",
            default_machine_name,
        )

    key_name = f"id_ed25519_{machine_name}_{account_name}"
    key_path = Path.home() / ".ssh" / key_name

    if not args.non_interactive:
        proceed = input(
            f"Are you sure you want to {ansi.yellow}generate a key{ansi.reset}? (y/N): "
        ).strip().lower()
        if proceed not in YES_VALUES:
            raise CommandError("Key generation cancelled")

    keygen_cmd = [
        "ssh-keygen",
        "-t",
        "ed25519",
        "-f",
        str(key_path),
        "-C",
        email,
        "-N",
        "",
    ]
    log_command(logger, keygen_cmd, dry_run=args.dry_run)
    print(f"\n{ansi.grey}{' '.join(keygen_cmd)}{ansi.reset}")
    if not args.dry_run:
        key_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(keygen_cmd, check=True)

    return SshSelection(key_path=key_path, account_name=account_name, email=email)


def infer_or_prompt_key_metadata(args: argparse.Namespace, key_path: Path) -> tuple[str, str]:
    """Infer account/email metadata for an existing key."""
    if args.account_name:
        account_name = args.account_name
    else:
        match = re.search(r"id_ed25519_\w+_(\w+)$", key_path.name)
        if match:
            account_name = match.group(1)
        elif args.non_interactive:
            raise CommandError(
                "--account-name is required in --non-interactive mode when key name does not encode it"
            )
        else:
            account_name = prompt_required("Enter your GitHub account name: ")

    if args.email:
        email = args.email
    else:
        user_hostname = f"{getpass.getuser()}@{socket.gethostname().replace('.local', '')}.local"
        if args.non_interactive:
            email = user_hostname
        else:
            email = prompt_with_default("Enter your ssh key email:", user_hostname)

    return account_name, email


def update_ssh_config(
    key_path: Path,
    account_name: str,
    email: str,
    dry_run: bool,
) -> None:
    """Append SSH config host block for account alias."""
    config_path = Path.home() / ".ssh" / "config"
    host = f"{account_name}.github.com"
    key_name = key_path.name

    config_entry = (
        f"\nHost {host}\n"
        "  HostName github.com\n"
        "  PreferredAuthentications publickey\n"
        f"  IdentityFile ~/.ssh/{key_name}\n"
        "\n## Commands\n"
        f"  ### cd {key_path.parent}\n"
        f"  ### ssh-keygen -t ed25519 -f {key_name} -C \"{email}\" -N \"\"\n"
        f"  ### cat {key_name}.pub\n"
        f"  ### ssh -T git@{host}\n"
        f"  ### git clone git@{host}:username/repo.git\n"
    )

    if dry_run:
        logger.info("ssh_config_update path=%s host=%s dry_run=%s", config_path, host, dry_run)
        print(f"\n{ansi.yellow}[dry-run]{ansi.reset} would append to {config_path}:")
        print(config_entry)
        return

    logger.info("ssh_config_update path=%s host=%s dry_run=%s", config_path, host, dry_run)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("a", encoding="utf-8") as handle:
        handle.write(config_entry)
