"""UUID version 7 (RFC 9562): time-ordered, index-friendly primary keys.

Within one millisecond the 12-bit ``rand_a`` field is a monotonic counter, so ids generated
by one process never go backwards; the remaining 62 bits are random.
"""

from __future__ import annotations

import os
import secrets
import threading
import time
import uuid

_COUNTER_MAX = 0xFFF


class _Clock:
    __slots__ = ("counter", "last_ms", "lock")

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.last_ms = 0
        self.counter = 0

    def next(self) -> tuple[int, int]:
        with self.lock:
            now_ms = time.time_ns() // 1_000_000
            if now_ms <= self.last_ms:
                now_ms = self.last_ms
                self.counter += 1
                if self.counter > _COUNTER_MAX:
                    now_ms += 1
                    self.counter = secrets.randbelow(0x800)
            else:
                self.counter = secrets.randbelow(0x800)
            self.last_ms = now_ms
            return now_ms, self.counter


_clock = _Clock()


def uuid7() -> uuid.UUID:
    now_ms, rand_a = _clock.next()
    rand_b = int.from_bytes(os.urandom(8), "big") & ((1 << 62) - 1)
    value = (now_ms & ((1 << 48) - 1)) << 80
    value |= 0x7 << 76
    value |= (rand_a & 0xFFF) << 64
    value |= 0b10 << 62
    value |= rand_b
    return uuid.UUID(int=value)


def short_id(value: uuid.UUID) -> str:
    """Eight-character display form used for drafts (``DRAFT-<short>``)."""
    return value.hex[-8:].upper()
