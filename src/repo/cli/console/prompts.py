"""User input prompts."""

from . import ansi
from .terminal import is_tty


def confirm(message: str, default: bool = False) -> bool:
    """Prompt the user for yes/no confirmation."""
    if not is_tty():
        return default

    suffix = " [Y/n]" if default else " [y/N]"
    prompt = f"{message}{suffix}: "

    if is_tty():
        prompt = f"{ansi.yellow}{prompt}{ansi.RESET}"

    response = input(prompt).strip().lower()

    if not response:
        return default

    return response in ("y", "yes")


def ask(message: str, default: str | None = None) -> str:
    """Prompt the user for free-text input."""
    prompt = message
    if default:
        prompt = f"{message} [{default}]"
    prompt = f"{prompt}: "

    if is_tty():
        prompt = f"{ansi.cyan}{prompt}{ansi.RESET}"

    response = input(prompt).strip()
    return response if response else (default or "")


def choose(message: str, options: list[str], default: int = 0) -> int:
    """Prompt the user to pick from a numbered list."""
    if not is_tty():
        return default

    print(f"{ansi.yellow}{message}{ansi.RESET}")
    for i, option in enumerate(options):
        marker = ">" if i == default else " "
        print(f"  {marker} {i + 1}. {option}")

    while True:
        response = input(f"{ansi.cyan}Choice [1-{len(options)}]: {ansi.RESET}").strip()
        if not response:
            return default
        try:
            idx = int(response) - 1
            if 0 <= idx < len(options):
                return idx
        except ValueError:
            pass
        print("Invalid choice. Try again.")
