"""The only place the presenter's token lives: one variable in this process's memory.

Never written to disk, logs, events, error messages or the browser. `redact()` scrubs it from
any text that might leave the process, and a logging filter does the same for log records.
"""
from __future__ import annotations

import logging
import re
import unicodedata

_token: str | None = None


TOKEN_NOT_SENDABLE = "The token contains a character that can't be sent. Paste it again from the source."
SUFFIX_NOT_SENDABLE = "The project suffix contains a character that can't be sent. Type it again."


def clean(value: str | None, message: str = TOKEN_NOT_SENDABLE) -> str:
    """A pasted token or suffix as it can travel in an HTTP header: whitespace and invisible characters
    (zero-width spaces, BOMs, line breaks) are dropped; anything else outside ASCII raises ValueError
    with a plain message for the gate. Never echoes the value."""
    kept = "".join(ch for ch in (value or "")
                   if not (ch.isspace() or unicodedata.category(ch) in ("Cc", "Cf", "Zs", "Zl", "Zp")))
    if not kept.isascii():
        raise ValueError(message)
    return kept


def is_masked_echo(value: str | None) -> bool:
    """True if the browser sent back the masked display value instead of a fresh token."""
    return bool(value) and re.fullmatch("\u2022{2,}[A-Za-z0-9_-]{0,4}", value.strip()) is not None


def set(token: str) -> None:  # noqa: A001 - module-level API: secrets_store.set(...)
    global _token
    _token = clean(token) or None


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
