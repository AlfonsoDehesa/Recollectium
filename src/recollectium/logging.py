"""Structured JSON logging infrastructure for Recollectium.

Provides a ``JsonFormatter``, a ``setup_logging`` bootstrap that configures
the ``recollectium.*`` logger hierarchy with size-based rotation and a stderr
fallback, and a ``get_logger`` convenience.
"""

from __future__ import annotations

import logging
import re
import sys
import warnings
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Mapping, Protocol

from recollectium.config import LOGGING_SENSITIVITY_FULL


_REDACTED = "[redacted]"
_SENSITIVE_CONTEXT_KEYS = frozenset(
    {
        "id",
        "memory_id",
        "job_id",
        "workspace_uid",
        "canonical_uid",
        "alias_uid",
        "old_uid",
        "new_uid",
        "input_uid",
        "content",
        "metadata",
        "source",
        "query",
        "secret",
        "api_secret",
        "token",
        "password",
        "credential",
        "credentials",
        "key",
        "api_key",
        "access_key",
        "encryption_key",
        "private_key",
        "public_key",
        "secret_key",
        "sensitivity",
    }
)
_SENSITIVE_KEY_RE = re.compile(
    r"(?i)("
    r"(^|[_-])(secret|token|password|credential|credentials|sensitivity)([_-]|$)|"
    r"(^|[_-])(?:api|access|encryption|private|public|secret)?[_-]?key([_-]|$)"
    r")"
)
_SENSITIVE_VALUE_RE = re.compile(
    r"(?i)(?<![\w])("
    r"memory(?:[_ -]?id)?|workspace(?:[_ -]?(?:id|uid|alias))?|"
    r"alias(?:[_ -]?uid)?|embedding(?:[_ -]?job)?|job(?:[_ -]?id)?|"
    r"content|metadata|source|query|secret|api[_ -]?secret|token|password|"
    r"credentials?|key|api[_ -]?key|access[_ -]?key|encryption[_ -]?key|"
    r"private[_ -]?key|public[_ -]?key|secret[_ -]?key|sensitivity"
    r")(?![\w])(?P<label>[^\n:={]{0,80})(?P<sep>[:=]\s*)(?P<value>[^,;\n]+)"
)
_SENSITIVE_BARE_VALUE_RE = re.compile(
    r"(?i)(?<![\w])("
    r"api[_ -]?secret|api[_ -]?key|access[_ -]?key|encryption[_ -]?key|"
    r"private[_ -]?key|public[_ -]?key|secret[_ -]?key|credentials?|"
    r"secret|token|password|key|sensitivity"
    r")(?![\w])(?P<sep>\s+|-{2,})(?P<value>[^,;\s\n]+)"
)
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


class LoggingConfig(Protocol):
    @property
    def effective_config(self) -> Mapping[str, Any]: ...

    @property
    def xdg_dirs(self) -> Mapping[str, Path]: ...


def _event_for_record(record: logging.LogRecord) -> str:
    """Return the stable event name for *record*.

    If an explicit event was provided via ``extra={"event": "..."}`` it takes
    priority.  Otherwise the dotted logger name is used as the event.
    """
    custom = getattr(record, "event", None)
    if isinstance(custom, str) and custom:
        return custom
    return record.name


def _normalized_context_key(key: str) -> str:
    """Return a key form suitable for separator and camelCase sensitive checks."""

    return _CAMEL_BOUNDARY_RE.sub("_", key).lower()


def redact_log_value(value: Any) -> Any:
    """Return a redacted copy of sensitive structured log values."""

    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            normalized = _normalized_context_key(key_text)
            if (
                normalized in _SENSITIVE_CONTEXT_KEYS
                or _SENSITIVE_KEY_RE.search(normalized) is not None
                or any(
                    token in normalized
                    for token in (
                        "memory",
                        "workspace",
                        "alias",
                        "content",
                        "metadata",
                        "source",
                    )
                )
            ):
                redacted[key_text] = _REDACTED
            else:
                redacted[key_text] = redact_log_value(item)
        return redacted
    if isinstance(value, list):
        return [redact_log_value(item) for item in value]
    if isinstance(value, str):
        return redact_log_message(value)
    return value


def redact_log_message(message: str) -> str:
    """Redact sensitive values embedded in unstructured log text."""

    redacted = _SENSITIVE_VALUE_RE.sub(
        lambda match: (
            f"{match.group(1)}{match.group('label')}{match.group('sep')}{_REDACTED}"
        ),
        message,
    )
    return _SENSITIVE_BARE_VALUE_RE.sub(
        lambda match: f"{match.group(1)}{match.group('sep')}{_REDACTED}",
        redacted,
    )


def logging_sensitivity(config: LoggingConfig) -> str:
    """Return the effective logging sensitivity mode."""

    logging_config = config.effective_config.get("logging", {})
    if not isinstance(logging_config, Mapping):
        return "redacted"
    return str(logging_config.get("sensitivity", "redacted")).lower()


class JsonFormatter(logging.Formatter):
    """A ``logging.Formatter`` that serialises log records as one JSON line.

    Every line contains these fields:

    - ``timestamp`` -- ISO 8601 UTC with microsecond precision
    - ``level`` -- uppercase level name
    - ``logger`` -- dotted module path
    - ``message`` -- human-readable summary
    - ``event`` -- stable machine-readable event name
    - ``context`` -- optional structured data dict (empty dict when absent)
    """

    def __init__(self, *, redact_sensitive: bool = True) -> None:
        super().__init__()
        self._redact_sensitive = redact_sensitive

    def format(self, record: logging.LogRecord) -> str:
        import json

        event = _event_for_record(record)
        context = getattr(record, "context", None)
        if not isinstance(context, dict):
            context = {}
        message = record.getMessage()
        if self._redact_sensitive:
            message = redact_log_message(message)
            context = redact_log_value(context)

        payload = {
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname.upper(),
            "logger": record.name,
            "message": message,
            "event": event,
            "context": context,
        }
        return json.dumps(payload, sort_keys=True)


def _level_from_name(level: str | int | None, default: int) -> int:
    """Return a logging level for a configured string/int value."""

    if isinstance(level, int):
        return level
    if level is None:
        return default
    return getattr(logging, str(level).upper(), default)


def setup_logging(
    config: LoggingConfig,
    *,
    stderr_level: str | int | None = None,
    library_log_level: str | int | None = None,
) -> None:
    """Bootstrap the ``recollectium`` logger hierarchy.

    Creates the logs directory (mode 0o700), attaches a
    ``RotatingFileHandler`` writing to ``logs/recollectium.log`` (mode 0o600) and
    a ``StreamHandler`` on stderr.  The file handler follows the configured
    ``logging.level``.  The stderr handler defaults to WARNING level so normal
    one-shot CLI commands keep stdout/stderr automation clean; foreground
    service callers can pass ``stderr_level`` to opt into streaming diagnostic
    logs at the effective configured level.  Both handlers use
    ``JsonFormatter``.

    Library loggers ``uvicorn``, ``sqlite3``, and ``httpx`` are captured at
    WARNING by default and routed to the same handlers.  Foreground service
    callers can pass ``library_log_level`` to include uvicorn access logs at the
    effective configured level.
    """
    log_dir = config.xdg_dirs["logs"]
    log_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    log_dir.chmod(0o700)

    log_file = log_dir / "recollectium.log"

    logging_config = config.effective_config.get("logging", {})
    log_level_name = str(logging_config.get("level", "info"))
    log_level = _level_from_name(log_level_name, logging.INFO)
    effective_stderr_level = _level_from_name(stderr_level, logging.WARNING)
    effective_library_log_level = _level_from_name(library_log_level, logging.WARNING)
    max_bytes = int(logging_config.get("max_bytes", 10485760))
    backup_count = int(logging_config.get("backup_count", 5))

    redact_sensitive = logging_sensitivity(config) != LOGGING_SENSITIVITY_FULL
    json_formatter = JsonFormatter(redact_sensitive=redact_sensitive)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    setattr(file_handler, "_recollectium_managed", True)
    file_handler.setFormatter(json_formatter)
    file_handler.setLevel(log_level)
    if log_file.exists():
        log_file.chmod(0o600)

    stream_handler = logging.StreamHandler(sys.stderr)
    setattr(stream_handler, "_recollectium_managed", True)
    stream_handler.setFormatter(json_formatter)
    stream_handler.setLevel(effective_stderr_level)

    root_logger = logging.getLogger("recollectium")
    root_logger.setLevel(log_level)

    def _replace_managed_handlers(logger: logging.Logger) -> None:
        for handler in list(logger.handlers):
            if getattr(handler, "_recollectium_managed", False):
                logger.removeHandler(handler)
                handler.close()

    _replace_managed_handlers(root_logger)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)

    for lib_name in ("uvicorn", "sqlite3", "httpx"):
        lib_logger = logging.getLogger(lib_name)
        lib_logger.setLevel(effective_library_log_level)
        lib_logger.propagate = False
        _replace_managed_handlers(lib_logger)
        lib_logger.addHandler(file_handler)
        lib_logger.addHandler(stream_handler)

    _warnings_logger = logging.getLogger("recollectium.warnings")

    def _handle_warning(
        message: Warning | str,
        category: type[Warning],
        filename: str,
        lineno: int,
        file: object | None = None,
        line: str | None = None,
    ) -> None:
        _warnings_logger.warning(
            str(message),
            extra={
                "event": "warning.captured",
                "context": {
                    "category": category.__name__,
                    "filename": filename,
                    "lineno": lineno,
                },
            },
        )

    warnings.showwarning = _handle_warning


def get_logger(name: str) -> logging.Logger:
    """Return a logger for *name*, typically ``__name__`` of the calling module."""
    return logging.getLogger(name)
