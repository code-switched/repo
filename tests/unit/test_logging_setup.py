"""Logging setup tests."""

from __future__ import annotations

from repo.utils.logging import configure_logging


def test_configure_logging_writes_to_data_logs(monkeypatch, tmp_path) -> None:
    """Configured logger should create and write under data/logs."""
    data_dir = tmp_path / "data"
    monkeypatch.setenv("DATA_DIR", str(data_dir))

    logger_name = f"repo.test.{tmp_path.name}"
    logger = configure_logging(name=logger_name, level="INFO")
    logger.info("test log message")

    for handler in logger.handlers:
        handler.flush()

    log_path = data_dir / "logs" / f"{logger_name}.log"
    assert log_path.exists()
    assert "test log message" in log_path.read_text(encoding="utf-8")
