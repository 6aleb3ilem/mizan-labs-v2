"""Request context middleware: request id, client ip, calling app; echoes X-Request-Id."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from mizan.platform import context
from mizan.platform.ids import uuid7

log = logging.getLogger("mizan.request")
KNOWN_APPS = frozenset({"back-office", "admin", "portal", "verify"})


def client_ip(request: HttpRequest) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return str(forwarded).split(",")[0].strip()
    remote: str | None = request.META.get("REMOTE_ADDR")
    return remote


class RequestContextMiddleware:
    sync_capable = True
    async_capable = False

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.headers.get("X-Request-Id") or uuid7().hex
        app = request.headers.get("X-Mizan-App", "")
        ctx = context.RequestContext(
            request_id=request_id[:64],
            ip=client_ip(request),
            user_agent=request.headers.get("User-Agent", "")[:256],
            app=app if app in KNOWN_APPS else "",
        )
        token = context.current_request.set(ctx)
        started = time.perf_counter()
        try:
            response = self.get_response(request)
        finally:
            context.current_request.reset(token)
        response["X-Request-Id"] = ctx.request_id
        if not request.path.startswith(("/health", "/ready")):
            log.info(
                "%s %s -> %s",
                request.method,
                request.path,
                response.status_code,
                extra={
                    "event": "http.request",
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
        return response
