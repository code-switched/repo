"""Main CLI dispatcher."""

import sys
import argparse

from .console import ansi
from .commands import register_commands
from .console.helpfmt import ColoredHelpFormatter
from ..core.exceptions import AppError, CommandError


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="repo",
        description="Repository setup and SSH workflows",
        formatter_class=ColoredHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    register_commands(parser)
    return parser


def main(argv: list[str] | None = None) -> None:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return

    if not hasattr(args, "func"):
        raise CommandError("No handler registered for command")

    try:
        args.func(args)
    except AppError as exc:
        print(f"{ansi.red}Error:{ansi.reset} {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
