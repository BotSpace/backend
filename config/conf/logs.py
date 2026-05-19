"""Logging configuration.

Console output is structured JSON in production (one log record per
line, easy to ship to Loki/ELK). File handlers keep the human-readable
verbose format so on-host debugging is still tolerable.
"""

import logging
import os
from pathlib import Path

from config.env import env

BASE_DIR = Path(__file__).resolve().parent.parent.parent

LOG_DIR = BASE_DIR / "resources/logs"
os.makedirs(LOG_DIR, exist_ok=True)


class ExcludeErrorsFilter:
    def filter(self, record):  # noqa: D401 — std logging API
        return record.levelno < logging.ERROR


_LOG_LEVEL = env.str("LOG_LEVEL", default="INFO").upper()
_PROD = env.str("PROJECT_ENV", default="prod") == "prod"
_JSON_LOGS = env.bool("JSON_LOGS", default=_PROD)

try:  # pragma: no cover — depends on whether python-json-logger is installed
    import pythonjsonlogger  # noqa: F401
    _HAS_JSON_LOGGER = True
except ImportError:
    _HAS_JSON_LOGGER = False

_JSON_FORMATTER = {
    "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
    "format": "%(asctime)s %(levelname)s %(name)s %(pathname)s %(lineno)d %(message)s",
    "rename_fields": {"asctime": "ts", "levelname": "level", "name": "logger"},
}
_VERBOSE_FORMATTER = {
    "format": "%(asctime)s %(name)s %(levelname)s %(pathname)s:%(lineno)d - %(message)s",
}
_CONSOLE_FORMATTER = "json" if (_JSON_LOGS and _HAS_JSON_LOGGER) else "verbose"


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": _JSON_FORMATTER,
        "verbose": _VERBOSE_FORMATTER,
    },
    "filters": {
        "exclude_errors": {"()": ExcludeErrorsFilter},
    },
    "handlers": {
        "console": {
            "level": _LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": _CONSOLE_FORMATTER,
        },
        "daily_rotating_file": {
            "level": "INFO",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": LOG_DIR / "django.log",
            "when": "midnight",
            "backupCount": 30,
            "formatter": "verbose",
            "filters": ["exclude_errors"],
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": LOG_DIR / "django_error.log",
            "when": "midnight",
            "backupCount": 30,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "daily_rotating_file", "error_file"],
            "level": _LOG_LEVEL,
            "propagate": False,
        },
        "core": {
            "handlers": ["console", "daily_rotating_file", "error_file"],
            "level": _LOG_LEVEL,
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "daily_rotating_file", "error_file"],
        "level": _LOG_LEVEL,
    },
}
