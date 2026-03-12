"""Contract tests for CLI command surface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from repo.cli.main import build_parser


def load_contract() -> dict:
    """Load CLI contract fixture."""
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "contracts"
        / "subcommands.json"
    )
    with fixture_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_subparsers_action(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    """Return the subparsers action from parser."""
    for action in parser._actions:  # pylint: disable=protected-access
        if isinstance(action, argparse._SubParsersAction):
            return action

    raise AssertionError("No subparsers action found")


def test_subcommands_match_contract() -> None:
    """CLI should expose expected top-level subcommands."""
    contract = load_contract()
    parser = build_parser()
    subparsers = get_subparsers_action(parser)

    expected = set(contract["subcommands"])
    actual = set(subparsers.choices.keys())
    assert actual == expected


def test_subcommand_flags_match_contract() -> None:
    """Each subcommand should include required global workflow flags."""
    contract = load_contract()
    parser = build_parser()
    subparsers = get_subparsers_action(parser)

    for command_name, expected_flags in contract["command_flags"].items():
        command_parser = subparsers.choices[command_name]
        option_strings = {
            option
            for action in command_parser._actions  # pylint: disable=protected-access
            for option in action.option_strings
        }
        for flag in expected_flags:
            assert flag in option_strings
