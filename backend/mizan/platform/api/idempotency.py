"""``Idempotency-Key`` support for creating POST operations (SPEC §8).

Usage on a Ninja operation::

    @router.post("/accounts", response={201: AccountOut})
    @idempotent
    def create_account(request, payload: AccountIn): ...

The first call stores the serialised response for 24 hours; a repeat with the same key and
the same request body returns the stored response; a repeat with a different body is a 409.
"""

from __future__ import annotations

import functools
import hashlib
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import orjson
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from ninja import Schema, Status

from mizan.platform import context
from mizan.platform.api.errors import Conflict
from mizan.platform.models import IdempotencyKey

TTL = timedelta(hours=24)


def _fingerprint(request: HttpRequest) -> str:
    raw = (
        (request.method or "").encode()
        + b"\n"
        + request.path.encode()
        + b"\n"
        + (request.body or b"")
    )
    return hashlib.sha256(raw).hexdigest()


def _to_json(result: Any) -> tuple[int, Any]:
    status = 200
    body = result
    if isinstance(result, Status):
        status, body = result.status_code, result.value
    elif isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], int):
        status, body = result
    if isinstance(body, Schema):
        body = body.model_dump(mode="json")
    return status, orjson.loads(orjson.dumps(body, default=str))


def idempotent(view: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(view)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        key = request.headers.get("Idempotency-Key")
        tenant_id = context.current_tenant_id.get()
        if not key or tenant_id is None:
            return view(request, *args, **kwargs)
        key = key[:128]
        fingerprint = _fingerprint(request)
        IdempotencyKey.objects.filter(created_at__lt=timezone.now() - TTL).delete()
        existing = IdempotencyKey.objects.filter(tenant_id=tenant_id, key=key).first()
        if existing is not None:
            if existing.fingerprint != fingerprint:
                raise Conflict("common.idempotency_mismatch", code="idempotency_mismatch")
            return HttpResponse(
                orjson.dumps(existing.response_body),
                status=existing.status_code,
                content_type="application/json",
                headers={"Idempotent-Replayed": "true"},
            )
        result = view(request, *args, **kwargs)
        status, body = _to_json(result)
        IdempotencyKey.objects.create(
            tenant_id=tenant_id,
            key=key,
            fingerprint=fingerprint,
            status_code=status,
            response_body=body,
        )
        return result

    return wrapper
