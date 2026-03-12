"""Main CLI dispatcher."""

import argparse

from .commands import register_commands
from .console.helpfmt import ColoredHelpFormatter
from ..core.exceptions import CommandError


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="repo",
        description="<description>",
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

    args.func(args)


if __name__ == "__main__":
    main()
