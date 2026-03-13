"""Unit tests for console utility modules."""

from __future__ import annotations

import argparse
from types import SimpleNamespace

from repo.cli.console import ansi
from repo.cli.console import helpfmt
from repo.cli.console import progress
from repo.cli.console import prompts
from repo.cli.console import terminal


def test_terminal_is_tty_prefers_no_color_and_force_color(monkeypatch) -> None:
    """NO_COLOR should disable and FORCE_COLOR should enable color output."""
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    assert terminal.is_tty() is False

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert terminal.is_tty() is True


def test_terminal_is_tty_uses_stdout_isatty(monkeypatch) -> None:
    """TTY detection should defer to stdout when no env override is set."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setattr(terminal.sys, "stdout", SimpleNamespace(isatty=lambda: True))
    assert terminal.is_tty() is True


def test_terminal_width_uses_default_on_value_error(monkeypatch) -> None:
    """Terminal width should return default when size lookup fails."""
    monkeypatch.setattr(terminal.shutil, "get_terminal_size", lambda: (_ for _ in ()).throw(ValueError()))
    assert terminal.terminal_width(default=120) == 120


def test_confirm_ask_and_choose_prompts(monkeypatch) -> None:
    """Prompt helpers should respect defaults and input parsing."""
    monkeypatch.setattr(prompts, "is_tty", lambda: False)
    assert prompts.confirm("Proceed?", default=True) is True
    assert prompts.choose("Pick", ["a", "b"], default=1) == 1

    monkeypatch.setattr(prompts, "is_tty", lambda: True)
    answers = iter(["", "yes", "", "bad", "2"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    assert prompts.confirm("Proceed?", default=False) is False
    assert prompts.confirm("Proceed?", default=False) is True
    assert prompts.ask("Name", default="repo") == "repo"
    assert prompts.choose("Pick", ["a", "b"], default=0) == 1


def test_progress_bar_and_spinner_non_tty(monkeypatch) -> None:
    """Progress helpers should work in non-TTY environments."""
    assert "[█████░░░░░]" in progress.progress_bar(current=5, total=10, width=10)
    assert "100%" in progress.progress_bar(current=0, total=0)

    spinner_instance = progress.Spinner("Working")
    monkeypatch.setattr(progress, "is_tty", lambda: False)
    spinner_instance.start()
    assert spinner_instance._thread is None
    spinner_instance.stop()

    with progress.spinner("Doing work") as inner:
        assert isinstance(inner, progress.Spinner)


def test_colored_help_formatter_adds_expected_ansi_tokens() -> None:
    """Custom formatter should color usage, options, and defaults."""
    parser = argparse.ArgumentParser(
        prog="repo",
        formatter_class=helpfmt.ColoredHelpFormatter,
    )
    parser.add_argument("command")
    parser.add_argument(
        "--branch",
        default="main",
        help="Git branch (default: %(default)s)",
    )

    formatted = parser.format_help()
    assert ansi.green in formatted
    assert ansi.cyan in formatted
    assert ansi.grey in formatted
    assert ansi.yellow in formatted
