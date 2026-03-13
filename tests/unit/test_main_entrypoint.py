"""Unit tests for CLI main entrypoint behavior."""

from __future__ import annotations

from argparse import Namespace

import pytest

from repo.cli import main as cli_main
from repo.core.exceptions import CommandError


class FakeParser:
    """Simple parser stub for main entrypoint tests."""

    def __init__(self, args: Namespace) -> None:
        self._args = args
        self.help_called = False

    def parse_args(self, _argv):  # noqa: ANN001
        """Return the configured namespace."""
        return self._args

    def print_help(self) -> None:
        """Record help rendering."""
        self.help_called = True


class FakeLogger:
    """Logger stub to assert log emission."""

    def __init__(self) -> None:
        self.info_calls: list[tuple[str, tuple[object, ...]]] = []
        self.error_calls: list[tuple[str, tuple[object, ...]]] = []

    def info(self, message: str, *args: object) -> None:
        """Capture info records."""
        self.info_calls.append((message, args))

    def error(self, message: str, *args: object) -> None:
        """Capture error records."""
        self.error_calls.append((message, args))


def test_main_prints_help_when_no_command(monkeypatch) -> None:
    """`main` should print help and return when no subcommand is provided."""
    fake_parser = FakeParser(Namespace(command=None))
    monkeypatch.setattr(cli_main, "build_parser", lambda: fake_parser)

    cli_main.main([])
    assert fake_parser.help_called is True


def test_main_raises_when_handler_is_missing(monkeypatch) -> None:
    """`main` should fail fast when command handler is missing."""
    fake_parser = FakeParser(Namespace(command="new"))
    monkeypatch.setattr(cli_main, "build_parser", lambda: fake_parser)

    with pytest.raises(CommandError, match="No handler registered for command"):
        cli_main.main(["new"])


def test_main_emits_error_and_exits_on_app_error(monkeypatch, capsys) -> None:
    """`main` should print formatted error and exit 1 for app-level failures."""
    logger = FakeLogger()

    def failing_handler(_args: Namespace) -> None:
        raise CommandError("boom")

    fake_parser = FakeParser(Namespace(command="new", func=failing_handler))
    fake_config = Namespace(logging=Namespace(level="INFO"))

    monkeypatch.setattr(cli_main, "build_parser", lambda: fake_parser)
    monkeypatch.setattr(cli_main, "load_config", lambda: fake_config)
    monkeypatch.setattr(cli_main, "configure_logging", lambda **_kwargs: logger)

    with pytest.raises(SystemExit) as exc_info:
        cli_main.main(["new"])

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert "Error:" in captured.err
    assert logger.error_calls


def test_main_logs_start_and_completion(monkeypatch) -> None:
    """`main` should log start and completion around successful handlers."""
    logger = FakeLogger()
    called = {"value": False}

    def success_handler(_args: Namespace) -> None:
        called["value"] = True

    fake_parser = FakeParser(Namespace(command="new", func=success_handler))
    fake_config = Namespace(logging=Namespace(level="INFO"))

    monkeypatch.setattr(cli_main, "build_parser", lambda: fake_parser)
    monkeypatch.setattr(cli_main, "load_config", lambda: fake_config)
    monkeypatch.setattr(cli_main, "configure_logging", lambda **_kwargs: logger)

    cli_main.main(["new"])

    assert called["value"] is True
    assert len(logger.info_calls) == 2


def test_format_cli_args_omits_callable_handler() -> None:
    """`format_cli_args` should exclude callable handler from logged args."""
    args = Namespace(command="new", dry_run=True, func=lambda: None)
    formatted = cli_main.format_cli_args(args)

    assert formatted["command"] == "new"
    assert formatted["dry_run"] == "True"
    assert "func" not in formatted
