"""Cursor pagination (SPEC §8): ``?after=<opaque>&limit=50``, default 50, max 200.

Keyset on ``(created_at, id)`` descending, which every BaseModel provides.
"""

from __future__ import annotations

import base64
import json
import uuid
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any

from django.db.models import Q, QuerySet
from ninja import Schema
from pydantic import Field

from mizan.platform.api.errors import UnprocessableEntity

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


class CursorParams(Schema):
    after: str | None = Field(default=None, description="Opaque cursor from a previous page")
    limit: int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)


class Page[T](Schema):
    items: list[T]
    next: str | None = None
    limit: int


def encode_cursor(created_at: datetime, id_: uuid.UUID) -> str:
    raw = json.dumps([created_at.isoformat(), str(id_)]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        created_at_s, id_s = json.loads(base64.urlsafe_b64decode(padded))
        return datetime.fromisoformat(created_at_s), uuid.UUID(id_s)
    except (ValueError, TypeError) as exc:
        raise UnprocessableEntity("common.invalid_cursor", code="invalid_cursor") from exc


def paginate(
    queryset: QuerySet[Any],
    params: CursorParams,
    serialize: Callable[[Any], Any],
    *,
    timestamp_field: str = "created_at",
) -> dict[str, Any]:
    qs = queryset.order_by(f"-{timestamp_field}", "-id")
    if params.after:
        stamp, id_ = decode_cursor(params.after)
        qs = qs.filter(
            Q(**{f"{timestamp_field}__lt": stamp}) | Q(**{timestamp_field: stamp, "id__lt": id_})
        )
    rows: Sequence[Any] = list(qs[: params.limit + 1])
    has_more = len(rows) > params.limit
    rows = rows[: params.limit]
    next_cursor = (
        encode_cursor(getattr(rows[-1], timestamp_field), rows[-1].id)
        if has_more and rows
        else None
    )
    return {"items": [serialize(row) for row in rows], "next": next_cursor, "limit": params.limit}
