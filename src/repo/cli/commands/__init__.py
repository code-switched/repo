"""CLI command registry for repo."""

import argparse

from .existing import register_existing_command
from .new import register_new_command
from .ssh import register_ssh_command
from .started import register_started_command


def register_commands(parser: argparse.ArgumentParser) -> None:
    """Register all CLI commands."""
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    register_new_command(subparsers)
    register_existing_command(subparsers)
    register_started_command(subparsers)
    register_ssh_command(subparsers)
