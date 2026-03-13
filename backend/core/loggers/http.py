import logging

from core.loggers.base import get_logger


def get_http_logger() -> logging.Logger:
    return get_logger("http")
