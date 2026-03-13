from __future__ import annotations

import logging
from pathlib import Path

from core.config import config
from core.loggers import (
    configure_project_loggers,
    get_ai_logger,
    get_code_logger,
    get_http_logger,
)


def test_configure_project_loggers_uses_stdout_by_default(
    monkeypatch,
) -> None:
    monkeypatch.setattr(config, "output_logs", None)
    monkeypatch.setattr(config, "log_level", "INFO")
    monkeypatch.setattr(config, "log_level_ai", None)
    monkeypatch.setattr(config, "log_level_code", None)
    monkeypatch.setattr(config, "log_level_http", None)

    configure_project_loggers(force=True)

    ai_logger = get_ai_logger()
    code_logger = get_code_logger()
    http_logger = get_http_logger()

    assert ai_logger.level == logging.INFO
    assert code_logger.level == logging.INFO
    assert http_logger.level == logging.INFO

    assert len(ai_logger.handlers) == 1
    assert len(code_logger.handlers) == 1
    assert len(http_logger.handlers) == 1

    assert not isinstance(ai_logger.handlers[0], logging.FileHandler)
    assert not isinstance(code_logger.handlers[0], logging.FileHandler)
    assert not isinstance(http_logger.handlers[0], logging.FileHandler)


def test_configure_project_loggers_uses_stdout_when_output_logs_is_term(
    monkeypatch,
) -> None:
    monkeypatch.setattr(config, "output_logs", "TERM")

    configure_project_loggers(force=True)

    ai_logger = get_ai_logger()
    code_logger = get_code_logger()
    http_logger = get_http_logger()

    assert not isinstance(ai_logger.handlers[0], logging.FileHandler)
    assert not isinstance(code_logger.handlers[0], logging.FileHandler)
    assert not isinstance(http_logger.handlers[0], logging.FileHandler)


def test_configure_project_loggers_uses_directory_output_and_separate_files(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(config, "output_logs", str(tmp_path))
    monkeypatch.setattr(config, "log_level", "WARNING")
    monkeypatch.setattr(config, "log_level_ai", "DEBUG")
    monkeypatch.setattr(config, "log_level_code", "ERROR")
    monkeypatch.setattr(config, "log_level_http", "CRITICAL")

    configure_project_loggers(force=True)

    ai_logger = get_ai_logger()
    code_logger = get_code_logger()
    http_logger = get_http_logger()

    assert ai_logger.level == logging.DEBUG
    assert code_logger.level == logging.ERROR
    assert http_logger.level == logging.CRITICAL

    ai_handler = ai_logger.handlers[0]
    code_handler = code_logger.handlers[0]
    http_handler = http_logger.handlers[0]

    assert isinstance(ai_handler, logging.FileHandler)
    assert isinstance(code_handler, logging.FileHandler)
    assert isinstance(http_handler, logging.FileHandler)

    assert Path(ai_handler.baseFilename).name == "ai.log"
    assert Path(code_handler.baseFilename).name == "code.log"
    assert Path(http_handler.baseFilename).name == "http.log"
