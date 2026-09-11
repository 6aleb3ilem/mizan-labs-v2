"""Signed QR payloads (SPEC §18.4, ADR 0004): JWS compact, EdDSA/Ed25519, ``kid`` = key id."""

from __future__ import annotations

import base64
import json
import warnings
from typing import Any, cast

from joserfc import jws
from joserfc.errors import JoseError
from joserfc.jwk import KeySet, OKPKey

ALGORITHMS = ["EdDSA"]


class InvalidQr(Exception):
    pass


def canonical_json(data: Any) -> bytes:
    return json.dumps(
        data, separators=(",", ":"), sort_keys=True, ensure_ascii=False, default=str
    ).encode()


def hash_prefix(content_hash_hex: str, length: int = 16) -> str:
    return base64.urlsafe_b64encode(bytes.fromhex(content_hash_hex)[:length]).decode().rstrip("=")


def build_payload(
    *,
    issuer: str,
    kind: str,
    number: str,
    issued_at_epoch: int,
    subject: dict[str, Any],
    digest: dict[str, Any],
    content_hash_hex: str,
    verify_token: str,
) -> dict[str, Any]:
    return {
        "v": 1,
        "iss": issuer,
        "kind": kind,
        "num": number,
        "iat": issued_at_epoch,
        "sub": subject,
        "dg": digest,
        "h": hash_prefix(content_hash_hex),
        "t": verify_token,
    }


def sign_payload(payload: dict[str, Any], key: OKPKey, kid: str) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return jws.serialize_compact(
            {"alg": "EdDSA", "kid": kid}, canonical_json(payload), key, algorithms=ALGORITHMS
        )


def verify_payload(token: str, jwks: dict[str, Any]) -> dict[str, Any]:
    keyset = KeySet.import_key_set(cast(Any, jwks))
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            obj = jws.deserialize_compact(token, keyset, algorithms=ALGORITHMS)
    except (JoseError, ValueError) as exc:
        raise InvalidQr("signature verification failed") from exc
    data: dict[str, Any] = json.loads(obj.payload)
    return data


def qr_url(base_url: str, token: str) -> str:
    return f"{base_url.rstrip('/')}/#{token}"


def qr_svg_data_uri(url: str, scale: int = 3) -> str:
    import segno

    code = segno.make(url, error="m")
    uri: str = code.svg_data_uri(scale=scale, border=1)
    return uri
