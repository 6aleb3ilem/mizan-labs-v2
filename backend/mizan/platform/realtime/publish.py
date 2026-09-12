"""Publish an event hint on the PostgreSQL channel read by the SSE endpoint.

NOTIFY is transactional: listeners only receive it when the business transaction commits.
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING, Any

from django.db import connection

if TYPE_CHECKING:
    from mizan.platform.events import Event

CHANNEL = "mizan_events"


def payload_for(event: Event) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "tenant_id": str(event.tenant_id) if event.tenant_id else None,
        "user_id": event.payload.get("user_id"),
        "event": event.code,
        "data": {
            "aggregate_type": event.aggregate_type,
            "aggregate_id": str(event.aggregate_id) if event.aggregate_id else None,
            "at": event.at.isoformat(),
        },
    }


def publish(event: Event) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_notify(%s, %s)", [CHANNEL, json.dumps(payload_for(event))])


def publish_to_user(
    tenant_id: uuid.UUID | None, user_id: uuid.UUID, name: str, data: dict[str, Any]
) -> None:
    """Push a user-targeted message (in-app notification, inbox counter) on the SSE channel."""
    payload = {
        "id": str(data.get("id", "")) or None,
        "tenant_id": str(tenant_id) if tenant_id else None,
        "user_id": str(user_id),
        "event": name,
        "data": data,
    }
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_notify(%s, %s)", [CHANNEL, json.dumps(payload, default=str)])
