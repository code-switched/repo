"""Custom argparse help formatter with colors."""

import re
import argparse

from . import ansi


class ColoredHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """HelpFormatter that adds colour to key parts of the help output."""

    def start_section(self, heading: str) -> None:  # type: ignore[override]
        coloured_heading = f"{ansi.green}{heading}{ansi.RESET}"
        super().start_section(coloured_heading)

    def add_usage(self, usage, actions, groups, prefix=None):
        if prefix is None:
            prefix = f"{ansi.green}usage:{ansi.RESET} "
        super().add_usage(usage, actions, groups, prefix)

    def _format_action_invocation(self, action: argparse.Action) -> str:
        if not action.option_strings:
            return super()._format_action_invocation(action)

        parts = [f"{ansi.cyan}{flag}{ansi.RESET}" for flag in action.option_strings]

        if action.nargs != 0:
            metavar = self._format_args(action, action.dest.upper())
            parts[-1] = f"{parts[-1]} {metavar}"
        return ", ".join(parts)

    def _format_args(self, action, default_metavar):
        text = super()._format_args(action, default_metavar)
        return f"{ansi.grey}{text}{ansi.RESET}"

    def _get_help_string(self, action: argparse.Action) -> str:  # noqa: N802
        """Return help string with coloured default values (if any)."""
        help_text = super()._get_help_string(action)
        placeholder = "%(default)s"
        if placeholder in help_text:
            coloured_placeholder = f"{ansi.yellow}{placeholder}{ansi.RESET}"
            return help_text.replace(placeholder, coloured_placeholder)

        match = re.search(r"\(default: ([^)]+)\)", help_text)
        if match:
            value = match.group(1)
            coloured_value = f"{ansi.yellow}{value}{ansi.RESET}"
            help_text = help_text.replace(match.group(0), f"(default: {coloured_value})")
        return help_text
