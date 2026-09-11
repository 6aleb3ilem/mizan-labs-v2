"""Short-lived access tokens for the single-page applications (HS256, 15 minutes).

Refresh tokens are opaque, stored hashed and rotated by ``mizan.apps.identity``.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass
from typing import Any, Literal

from django.conf import settings
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import OctKey

Realm = Literal["STAFF", "CLIENT", "PLATFORM"]
ALGORITHMS = ["HS256"]


class InvalidToken(Exception):
    pass


@dataclass(frozen=True, slots=True)
class AccessClaims:
    user_id: uuid.UUID
    tenant_id: uuid.UUID | None
    realm: Realm
    session_id: uuid.UUID
    issued_at: int
    expires_at: int
    step_up_at: int | None = None  # last MFA/step-up verification, epoch seconds


def _key() -> OctKey:
    material = hashlib.sha256(f"mizan-jwt:{settings.SECRET_KEY}".encode()).digest()
    return OctKey.import_key(material)


def issue_access_token(
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID | None,
    realm: Realm,
    session_id: uuid.UUID,
    step_up_at: int | None = None,
    ttl_seconds: int | None = None,
    now: int | None = None,
) -> str:
    now_s = now if now is not None else int(time.time())
    ttl = ttl_seconds if ttl_seconds is not None else int(settings.MIZAN_JWT_ACCESS_TTL)
    claims: dict[str, Any] = {
        "iss": settings.MIZAN_JWT_ISSUER,
        "sub": str(user_id),
        "tid": str(tenant_id) if tenant_id else None,
        "realm": realm,
        "sid": str(session_id),
        "typ": "access",
        "iat": now_s,
        "exp": now_s + ttl,
    }
    if step_up_at is not None:
        claims["sua"] = step_up_at
    return jwt.encode({"alg": "HS256", "typ": "JWT"}, claims, _key(), algorithms=ALGORITHMS)


def decode_access_token(token: str, *, now: int | None = None) -> AccessClaims:
    try:
        parsed = jwt.decode(token, _key(), algorithms=ALGORITHMS)
    except (JoseError, ValueError) as exc:
        raise InvalidToken("malformed or badly signed token") from exc
    claims = parsed.claims
    now_s = now if now is not None else int(time.time())
    try:
        if claims.get("iss") != settings.MIZAN_JWT_ISSUER or claims.get("typ") != "access":
            raise InvalidToken("wrong issuer or token type")
        if int(claims["exp"]) <= now_s:
            raise InvalidToken("expired")
        realm = claims["realm"]
        if realm not in ("STAFF", "CLIENT", "PLATFORM"):
            raise InvalidToken("unknown realm")
        return AccessClaims(
            user_id=uuid.UUID(claims["sub"]),
            tenant_id=uuid.UUID(claims["tid"]) if claims.get("tid") else None,
            realm=realm,
            session_id=uuid.UUID(claims["sid"]),
            issued_at=int(claims["iat"]),
            expires_at=int(claims["exp"]),
            step_up_at=int(claims["sua"]) if claims.get("sua") is not None else None,
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidToken("missing or invalid claims") from exc
