"""Progress indicators and spinners."""

import sys
import time
import threading
from contextlib import contextmanager

from .terminal import is_tty


SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class Spinner:
    """A simple terminal spinner."""

    def __init__(self, message: str = "") -> None:
        self.message = message
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def _spin(self) -> None:
        """Spin animation loop."""
        idx = 0
        while not self._stop_event.is_set():
            frame = SPINNER_FRAMES[idx % len(SPINNER_FRAMES)]
            sys.stdout.write(f"\r{frame} {self.message}")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.08)

    def start(self) -> None:
        """Start the spinner in a background thread."""
        if not is_tty():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self, clear: bool = True) -> None:
        """Stop the spinner and optionally clear the line."""
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        if clear and is_tty():
            sys.stdout.write("\r" + " " * (len(self.message) + 2) + "\r")
            sys.stdout.flush()


@contextmanager
def spinner(message: str = ""):
    """Context manager that shows a spinner while work runs."""
    s = Spinner(message)
    s.start()
    try:
        yield s
    finally:
        s.stop()


def progress_bar(current: int, total: int, width: int = 40, prefix: str = "") -> str:
    """Return a text progress bar string."""
    if total == 0:
        pct = 100
    else:
        pct = int(current / total * 100)

    filled = int(width * current / total) if total > 0 else width
    bar_visual = "█" * filled + "░" * (width - filled)
    return f"{prefix}[{bar_visual}] {pct:3d}%"
