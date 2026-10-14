"""The only place the presenter's token lives: one variable in this process's memory.

Never written to disk, logs, events, error messages or the browser. `redact()` scrubs it from
any text that might leave the process, and a logging filter does the same for log records.
"""
from __future__ import annotations

import logging

_token: str | None = None


def set(token: str) -> None:  # noqa: A001 - module-level API: secrets_store.set(...)
    global _token
    _token = token.strip() or None


def get() -> str | None:
    return _token


def clear() -> None:
    global _token
    _token = None


def masked() -> str | None:
    """At most the last 4 characters, e.g. '••••abcd'."""
    if not _token:
        return None
    secret = _token.split(":", 1)[0]
    return "••••" + (secret[-4:] if len(secret) >= 12 else "")


def redact(text: str) -> str:
    if not _token or not text:
        return text
    for piece in {_token, _token.split(":", 1)[0]}:
        if len(piece) >= 6:
            text = text.replace(piece, "••••")
    return text


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if _token:
            try:
                message = record.getMessage()
            except (TypeError, ValueError):
                message = str(record.msg)
            record.msg, record.args = redact(message), None
        return True


def install_log_filter() -> None:
    f = RedactFilter()
    for name in ("", "uvicorn", "uvicorn.error", "uvicorn.access", "httpx", "app"):
        logging.getLogger(name).addFilter(f)
    for h in logging.getLogger().handlers:
        h.addFilter(f)
