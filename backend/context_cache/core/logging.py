"""Logging utilities for Context Cache."""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

import orjson

_DEFAULT_LEVEL = os.environ.get("CTXC_LOG_LEVEL", "INFO")


class JsonFormatter(logging.Formatter):
    """Lightweight JSON log formatter."""

    default_fields = ("timestamp", "level", "name", "message")

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - thin wrapper
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = record.stack_info
        for key, value in record.__dict__.items():
            if key.startswith("ctx_"):
                payload[key] = value
        return orjson.dumps(payload).decode("utf-8")


def configure_logging(level: str | int = _DEFAULT_LEVEL, use_json: bool = True) -> None:
    """Configure root logger with optional JSON formatting."""
    logging.captureWarnings(True)
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    if use_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.handlers = [handler]


def get_logger(name: str = "context_cache") -> logging.Logger:
    """Return configured logger, configuring root on first call."""
    if not logging.getLogger().handlers:
        configure_logging()
    return logging.getLogger(name)


__all__ = ["configure_logging", "get_logger"]
