"""Starter hello command."""

import argparse


def register_hello_command(subparsers) -> None:
    """Register the hello command."""
    parser = subparsers.add_parser("hello", help="Run a starter command")
    parser.add_argument(
        "--name",
        default="world",
        help="Name to greet",
    )
    parser.set_defaults(func=run_hello)


def run_hello(args: argparse.Namespace) -> None:
    """Execute the hello command."""
    print(f"hello, {args.name}")
