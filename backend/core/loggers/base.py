from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Literal

from core.config import config

LoggerType = Literal["ai", "code", "http"]

_LOGGER_NAMES: dict[LoggerType, str] = {
    "ai": "news_agent.ai",
    "code": "news_agent.code",
    "http": "news_agent.http",
}

_LOGGER_FILE_NAMES: dict[LoggerType, str] = {
    "ai": "ai.log",
    "code": "code.log",
    "http": "http.log",
}

_LOG_LEVELS: dict[str, int] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}

_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

_is_configured = False


def configure_project_loggers(*, force: bool = False) -> None:
    global _is_configured

    if _is_configured and not force:
        return

    for logger_type in _LOGGER_NAMES:
        _configure_single_logger(logger_type)

    _is_configured = True


def get_logger(logger_type: LoggerType) -> logging.Logger:
    configure_project_loggers()
    logger_name = _LOGGER_NAMES[logger_type]
    return logging.getLogger(logger_name)


def _configure_single_logger(logger_type: LoggerType) -> None:
    logger_name = _LOGGER_NAMES[logger_type]
    file_name = _LOGGER_FILE_NAMES[logger_type]
    logger = logging.getLogger(logger_name)
    logger_level = _resolve_logger_level(logger_type)
    logger_handler = _build_logger_handler(file_name)

    logger.handlers.clear()
    logger.setLevel(logger_level)
    logger.propagate = False
    logger_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(logger_handler)


def _resolve_logger_level(logger_type: LoggerType) -> int:
    fallback_level_name = config.log_level

    logger_level_name: str | None = None
    if logger_type == "ai":
        logger_level_name = config.log_level_ai
    elif logger_type == "code":
        logger_level_name = config.log_level_code
    elif logger_type == "http":
        logger_level_name = config.log_level_http

    selected_level_name = logger_level_name or fallback_level_name
    normalized_level_name = selected_level_name.strip().upper()

    return _LOG_LEVELS.get(normalized_level_name, logging.INFO)


def _build_logger_handler(file_name: str) -> logging.Handler:
    output_directory = config.logs_output_directory
    if output_directory is None:
        return logging.StreamHandler(sys.stdout)

    output_directory.mkdir(parents=True, exist_ok=True)
    output_file_path = Path(output_directory) / file_name
    return logging.FileHandler(output_file_path, encoding="utf-8")
