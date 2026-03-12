"""CLI command registry for repo."""

import argparse

from .hello import register_hello_command


def register_commands(parser: argparse.ArgumentParser) -> None:
    """Register all CLI commands."""
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    register_hello_command(subparsers)
