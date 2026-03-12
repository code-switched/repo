"""Terminal detection and utilities."""

import os
import sys
import shutil


def is_tty() -> bool:
    """Return whether stdout supports colour output."""
    if os.getenv("NO_COLOR"):
        return False
    if os.getenv("FORCE_COLOR"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def terminal_width(default: int = 80) -> int:
    """Return the current terminal width, or *default*."""
    try:
        size = shutil.get_terminal_size()
        return size.columns
    except (AttributeError, ValueError):
        return default
