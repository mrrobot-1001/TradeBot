"""
Logging configuration — shared logger factory.

Provides a single ``get_logger(name)`` function that returns a logger with:
- **File handler**: DEBUG+, rotating, writes to ``logs/trading_bot.log``
- **Console handler**: INFO+, clean human-readable format

All logged strings are scrubbed to ensure the API secret never leaks.
"""

from __future__ import annotations

import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path


# ---------------------------------------------------------------------------
# Secret-redaction filter
# ---------------------------------------------------------------------------

class _SecretRedactionFilter(logging.Filter):
    """Replaces any occurrence of the API secret in log records."""

    def __init__(self) -> None:
        super().__init__()
        self._secret: str | None = os.getenv("BINANCE_API_SECRET")

    def filter(self, record: logging.LogRecord) -> bool:
        if self._secret:
            record.msg = str(record.msg).replace(self._secret, "***REDACTED***")
            if record.args:
                # Handle both tuple and dict args
                if isinstance(record.args, dict):
                    record.args = {
                        k: str(v).replace(self._secret, "***REDACTED***")
                        if isinstance(v, str) else v
                        for k, v in record.args.items()
                    }
                elif isinstance(record.args, tuple):
                    record.args = tuple(
                        str(a).replace(self._secret, "***REDACTED***")
                        if isinstance(a, str) else a
                        for a in record.args
                    )
        return True


# ---------------------------------------------------------------------------
# Signature redaction filter (query string parameters)
# ---------------------------------------------------------------------------

class _SignatureRedactionFilter(logging.Filter):
    """Redacts signature= query parameter values from logged URLs."""

    _PATTERN = re.compile(r"(signature=)[a-fA-F0-9]+")

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._PATTERN.sub(r"\1***REDACTED***", str(record.msg))
        if record.args and isinstance(record.args, tuple):
            record.args = tuple(
                self._PATTERN.sub(r"\1***REDACTED***", str(a))
                if isinstance(a, str) else a
                for a in record.args
            )
        return True


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------

# Track whether the root trading-bot logger has been configured already
_configured: bool = False

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"

MAX_LOG_BYTES = 5 * 1024 * 1024  # 5 MB per file
BACKUP_COUNT = 3


def get_logger(name: str) -> logging.Logger:
    """Return a named child logger under the ``trading_bot`` namespace.

    On first invocation the root ``trading_bot`` logger is configured with
    file and console handlers. Subsequent calls simply return a child.

    Args:
        name: Dot-qualified module name (e.g. ``"client"``).

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    global _configured  # noqa: PLW0603

    root_logger = logging.getLogger("trading_bot")

    if not _configured:
        _setup_root_logger(root_logger)
        _configured = True

    return root_logger.getChild(name)


def _setup_root_logger(logger: logging.Logger) -> None:
    """Attach file + console handlers to *logger*."""
    log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
    logger.setLevel(getattr(logging, log_level, logging.DEBUG))

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # --- File handler (DEBUG+, rotating) ---
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(_SecretRedactionFilter())
    file_handler.addFilter(_SignatureRedactionFilter())
    logger.addHandler(file_handler)

    # --- Console handler (INFO+) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(_SecretRedactionFilter())
    console_handler.addFilter(_SignatureRedactionFilter())
    logger.addHandler(console_handler)
