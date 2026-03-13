"""Main CLI dispatcher."""

import sys
import argparse
import logging

from .console import ansi
from .commands import register_commands
from .config import load_config
from .console.helpfmt import ColoredHelpFormatter
from ..core.exceptions import AppError, CommandError
from ..utils.logging import configure_logging


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

    logger: logging.Logger | None = None
    try:
        config = load_config()
        logger = configure_logging(name="repo", level=config.logging.level)
        logger.info(
            "cli_command_start command=%s args=%s",
            args.command,
            format_cli_args(args),
        )
        args.func(args)
        logger.info("cli_command_complete command=%s", args.command)
    except AppError as exc:
        if logger is not None:
            logger.error("cli_command_failed command=%s error=%s", args.command, exc)
        print(f"{ansi.red}Error:{ansi.reset} {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def format_cli_args(args: argparse.Namespace) -> dict[str, str]:
    """Format argparse namespace values for structured logging."""
    formatted: dict[str, str] = {}
    for key, value in vars(args).items():
        if key == "func":
            continue
        formatted[key] = str(value)
    return formatted


if __name__ == "__main__":
    main()
