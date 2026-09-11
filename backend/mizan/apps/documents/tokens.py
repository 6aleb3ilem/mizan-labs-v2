"""Verification tokens and short codes (SPEC §18.2)."""

from __future__ import annotations

import base64
import hashlib
import secrets

SHORT_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I


def new_verify_token() -> str:
    """128 random bits, base32 without padding (26 characters)."""
    return base64.b32encode(secrets.token_bytes(16)).decode().rstrip("=")


def new_short_code() -> str:
    """Six unambiguous characters shown as ``XXXX-XX``."""
    chars = "".join(secrets.choice(SHORT_CODE_ALPHABET) for _ in range(6))
    return f"{chars[:4]}-{chars[4:]}"


def normalise_short_code(value: str) -> str:
    cleaned = "".join(ch for ch in value.upper() if ch.isalnum())
    cleaned = cleaned.replace("O", "0").replace("I", "1")  # user typed look-alikes
    cleaned = (
        cleaned.replace("0", "O")
        if "O" in SHORT_CODE_ALPHABET and "0" not in SHORT_CODE_ALPHABET
        else cleaned
    )
    return f"{cleaned[:4]}-{cleaned[4:6]}" if len(cleaned) >= 6 else cleaned


def hash_ip(ip: str | None) -> str:
    return hashlib.sha256((ip or "").encode()).hexdigest()[:32]
