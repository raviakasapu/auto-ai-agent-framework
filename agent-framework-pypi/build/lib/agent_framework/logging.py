from __future__ import annotations

import logging
import os
from typing import Optional

_LOGGER_NAME = "framework"
_CONFIGURED = False

_LEVEL_MAP = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


def _resolve_level(level: Optional[str]) -> int:
    if not level:
        return logging.INFO
    return _LEVEL_MAP.get(level.upper(), logging.INFO)


def get_logger(level: Optional[str] = None) -> logging.Logger:
    """
    Return a shared logger for the agent framework.

    The first call configures the logger based on the environment or the provided level.
    Subsequent calls re-use the same logger, but the log level can be overridden per call.
    """
    global _CONFIGURED
    logger = logging.getLogger(_LOGGER_NAME)

    env_level = os.getenv("AGENT_LOG_LEVEL")
    resolved_level = _resolve_level(level or env_level)

    if not _CONFIGURED:
        logger.setLevel(resolved_level)
        if not logger.handlers:
            handler = logging.StreamHandler()
            fmt = os.getenv(
                "AGENT_LOG_FORMAT",
                "[%(asctime)s] %(levelname)s %(name)s - %(message)s",
            )
            handler.setFormatter(logging.Formatter(fmt))
            logger.addHandler(handler)
        logger.propagate = False
        _CONFIGURED = True
    else:
        if level:
            logger.setLevel(resolved_level)

    return logger


def set_level(level: str) -> None:
    """Programmatically override the shared logger level."""
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(_resolve_level(level))
