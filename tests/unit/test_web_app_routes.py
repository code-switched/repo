"""Unit tests for web app route handlers."""

from __future__ import annotations

import asyncio

from repo.web import app as web_app


def test_root_handler_returns_status_payload() -> None:
    """Root handler should return basic status payload."""
    result = asyncio.run(web_app.root())
    assert result == {"status": "ok"}


def test_health_handler_returns_healthy_payload() -> None:
    """Health handler should return expected health payload."""
    result = asyncio.run(web_app.health())
    assert result == {"healthy": True}
