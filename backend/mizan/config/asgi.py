"""ASGI entrypoint.

Django serves everything except the Server-Sent Events stream, which is a long-lived
connection handled by a small raw ASGI application (no request transaction, no thread).
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mizan.config.settings")

from django.core.asgi import get_asgi_application

from mizan.platform.realtime.sse import sse_application

django_application = get_asgi_application()

SSE_PATHS = frozenset({"/api/v1/events/stream"})

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[Mapping[str, Any]], Awaitable[None]]


async def application(scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    elif scope["type"] == "http" and scope.get("path") in SSE_PATHS:
        await sse_application(scope, receive, send)
    else:
        await django_application(scope, receive, send)
