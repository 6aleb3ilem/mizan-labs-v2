"""Server-Sent Events over PostgreSQL LISTEN/NOTIFY, as a raw ASGI application.

Events are published with ``pg_notify('mizan_events', json)`` where the JSON carries
``tenant_id`` and optionally ``user_id``; each connection only receives its tenant's events
(and user-targeted ones addressed to it). Authentication: the access token, either as a
``Bearer`` header or as ``?access_token=`` (EventSource cannot set headers).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import Any
from urllib.parse import parse_qs

import psycopg
from django.conf import settings
from psycopg import conninfo

from mizan.platform.auth.jwt import InvalidToken, decode_access_token

log = logging.getLogger("mizan.sse")

CHANNEL = "mizan_events"
HEARTBEAT_SECONDS = 25

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[Mapping[str, Any]], Awaitable[None]]


def _dsn() -> str:
    db = settings.DATABASES["default"]
    return conninfo.make_conninfo(
        host=str(db["HOST"]) or None,
        port=str(db["PORT"]) or None,
        dbname=str(db["NAME"]),
        user=str(db["USER"]) or None,
        password=str(db["PASSWORD"]) or None,
        application_name="mizan-sse",
    )


def _token_from_scope(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"authorization" and value.lower().startswith(b"bearer "):
            return str(value[7:].decode())
    raw: bytes = scope.get("query_string", b"")
    query = parse_qs(raw.decode())
    values = query.get("access_token")
    return values[0] if values else None


async def _respond(send: Send, status: int, body: bytes) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/problem+json"),
                (b"cache-control", b"no-store"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body, "more_body": False})


def format_event(name: str, data: Any, event_id: str | None = None) -> bytes:
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {name}")
    lines.append("data: " + json.dumps(data, default=str))
    return ("\n".join(lines) + "\n\n").encode()


async def sse_application(scope: Scope, receive: Receive, send: Send) -> None:
    token = _token_from_scope(scope)
    if not token:
        await _respond(send, 401, b'{"code":"unauthorized","message_key":"auth.unauthorized"}')
        return
    try:
        claims = decode_access_token(token)
    except InvalidToken:
        await _respond(send, 401, b'{"code":"unauthorized","message_key":"auth.unauthorized"}')
        return

    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"text/event-stream; charset=utf-8"),
                (b"cache-control", b"no-cache, no-transform"),
                (b"connection", b"keep-alive"),
                (b"x-accel-buffering", b"no"),
            ],
        }
    )

    disconnected = asyncio.Event()

    async def watch_disconnect() -> None:
        while not disconnected.is_set():
            message = await receive()
            if message["type"] == "http.disconnect":
                disconnected.set()

    watcher = asyncio.create_task(watch_disconnect())
    tenant = str(claims.tenant_id) if claims.tenant_id else None
    user = str(claims.user_id)
    try:
        await send({"type": "http.response.body", "body": b"retry: 3000\n\n", "more_body": True})
        async with await psycopg.AsyncConnection.connect(_dsn(), autocommit=True) as conn:
            await conn.execute(f"LISTEN {CHANNEL}")
            while not disconnected.is_set():
                received = False
                async for notify in conn.notifies(timeout=HEARTBEAT_SECONDS):
                    received = True
                    try:
                        payload = json.loads(notify.payload)
                    except ValueError:
                        continue
                    if payload.get("tenant_id") != tenant:
                        continue
                    target = payload.get("user_id")
                    if target and target != user:
                        continue
                    body = format_event(
                        payload.get("event", "message"), payload.get("data", {}), payload.get("id")
                    )
                    await send({"type": "http.response.body", "body": body, "more_body": True})
                    if disconnected.is_set():
                        break
                if not received and not disconnected.is_set():
                    await send(
                        {"type": "http.response.body", "body": b": ping\n\n", "more_body": True}
                    )
    except (ConnectionError, OSError, psycopg.Error) as exc:
        log.warning("sse stream ended: %s", exc)
    finally:
        watcher.cancel()
        with contextlib.suppress(Exception):  # client already gone
            await send({"type": "http.response.body", "body": b"", "more_body": False})
