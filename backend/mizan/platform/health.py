"""Liveness and readiness probes (root paths for Cloud Run, API paths for the catalogue)."""

from __future__ import annotations

from django.db import connection
from django.http import HttpRequest, JsonResponse
from ninja import Router

router = Router()


def _db_ok() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return bool(cursor.fetchone() == (1,))
    except Exception:  # readiness must never raise
        return False


def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


def ready(request: HttpRequest) -> JsonResponse:
    ok = _db_ok()
    return JsonResponse(
        {"status": "ready" if ok else "degraded", "database": ok}, status=200 if ok else 503
    )


@router.get("/health", auth=None, summary="Liveness")
def api_health(request: HttpRequest) -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", auth=None, summary="Readiness (database reachable)")
def api_ready(request: HttpRequest) -> dict[str, object]:
    ok = _db_ok()
    return {"status": "ready" if ok else "degraded", "database": ok}
