"""Events and the in-process bus that fans them out to SSE subscribers.

Event schema (docs/ARCHITECTURE.md):
  {"run", "seq", "t", "act", "kind", "payload", "ts", "prev_hash", "hash"}
Only decision events carry a hash: the audit record's prev_hash/hash, so the console and the
evidence pack show the same chain. Events never carry the token, prompts or provider settings.
"""
from __future__ import annotations

import asyncio

KINDS = {"run", "act", "caption", "panel", "map", "decision", "call", "llm", "system", "error", "keyview"}


class Bus:
    def __init__(self) -> None:
        self._subs: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    def publish(self, event: dict) -> None:
        for q in list(self._subs):
            q.put_nowait(event)
