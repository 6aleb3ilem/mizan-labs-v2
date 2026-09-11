"""API errors as RFC 9457 problem details carrying a translatable ``message_key``.

Body: ``{type, title, status, detail, code, message_key, params, details[]}``.
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from ninja import NinjaAPI
from ninja.errors import AuthenticationError, HttpError, ValidationError

from mizan.platform import context
from mizan.platform.db.models import ConcurrentUpdate

log = logging.getLogger("mizan.api")

PROBLEM_CONTENT_TYPE = "application/problem+json"


class ApiError(Exception):
    """A business or request error with a stable code and a translatable message key."""

    status: int = 400
    code: str = "bad_request"
    message_key: str = "common.bad_request"

    def __init__(
        self,
        message_key: str | None = None,
        *,
        code: str | None = None,
        status: int | None = None,
        params: dict[str, Any] | None = None,
        details: list[dict[str, Any]] | None = None,
        detail: str | None = None,
    ) -> None:
        self.message_key = message_key or self.message_key
        self.code = code or self.code
        self.status = status or self.status
        self.params = params or {}
        self.details = details or []
        self.detail = detail or self.message_key
        super().__init__(self.detail)


class NotFound(ApiError):
    status = 404
    code = "not_found"
    message_key = "common.not_found"


class Forbidden(ApiError):
    status = 403
    code = "forbidden"
    message_key = "authz.forbidden"


class Unauthorized(ApiError):
    status = 401
    code = "unauthorized"
    message_key = "auth.unauthorized"


class Conflict(ApiError):
    status = 409
    code = "conflict"
    message_key = "common.conflict"


class UnprocessableEntity(ApiError):
    status = 422
    code = "validation_error"
    message_key = "common.validation_error"


class TooManyRequests(ApiError):
    status = 429
    code = "rate_limited"
    message_key = "common.rate_limited"


def problem(
    request: HttpRequest | None,
    status: int,
    *,
    code: str,
    message_key: str,
    detail: str = "",
    params: dict[str, Any] | None = None,
    details: list[dict[str, Any]] | None = None,
    title: str | None = None,
) -> HttpResponse:
    body: dict[str, Any] = {
        "type": f"urn:mizan:error:{code}",
        "title": title or code.replace("_", " "),
        "status": status,
        "detail": detail or message_key,
        "code": code,
        "message_key": message_key,
        "params": params or {},
        "details": details or [],
        "request_id": context.request_context().request_id,
    }
    return JsonResponse(body, status=status, content_type=PROBLEM_CONTENT_TYPE)


def install_exception_handlers(api: NinjaAPI) -> None:
    @api.exception_handler(ApiError)
    def _api_error(request: HttpRequest, exc: ApiError) -> HttpResponse:
        return problem(
            request,
            exc.status,
            code=exc.code,
            message_key=exc.message_key,
            detail=exc.detail,
            params=exc.params,
            details=exc.details,
        )

    @api.exception_handler(ValidationError)
    def _validation(request: HttpRequest, exc: ValidationError) -> HttpResponse:
        details = [
            {
                "loc": list(err.get("loc", [])),
                "msg": err.get("msg", ""),
                "type": err.get("type", ""),
            }
            for err in exc.errors
        ]
        return problem(
            request,
            422,
            code="validation_error",
            message_key="common.validation_error",
            detail="Request validation failed",
            details=details,
        )

    @api.exception_handler(DjangoValidationError)
    def _django_validation(request: HttpRequest, exc: DjangoValidationError) -> HttpResponse:
        details = [
            {"loc": [k], "msg": str(m)}
            for k, v in (getattr(exc, "message_dict", {}) or {}).items()
            for m in v
        ]
        if not details:
            details = [{"loc": [], "msg": m} for m in exc.messages]
        return problem(
            request,
            422,
            code="validation_error",
            message_key="common.validation_error",
            detail="Validation failed",
            details=details,
        )

    @api.exception_handler(AuthenticationError)
    def _auth(request: HttpRequest, exc: AuthenticationError) -> HttpResponse:
        return problem(
            request,
            401,
            code="unauthorized",
            message_key="auth.unauthorized",
            detail="Authentication required",
        )

    @api.exception_handler(PermissionDenied)
    def _denied(request: HttpRequest, exc: PermissionDenied) -> HttpResponse:
        return problem(
            request,
            403,
            code="forbidden",
            message_key="authz.forbidden",
            detail=str(exc) or "Forbidden",
        )

    @api.exception_handler(Http404)
    def _404(request: HttpRequest, exc: Http404) -> HttpResponse:
        return problem(
            request, 404, code="not_found", message_key="common.not_found", detail="Not found"
        )

    @api.exception_handler(ConcurrentUpdate)
    def _concurrent(request: HttpRequest, exc: ConcurrentUpdate) -> HttpResponse:
        return problem(
            request,
            409,
            code="concurrent_update",
            message_key="common.concurrent_update",
            detail="The record was modified by someone else; reload and merge",
        )

    @api.exception_handler(IntegrityError)
    def _integrity(request: HttpRequest, exc: IntegrityError) -> HttpResponse:
        log.warning("integrity error: %s", exc)
        return problem(
            request,
            409,
            code="conflict",
            message_key="common.conflict",
            detail="The change conflicts with existing data",
        )

    @api.exception_handler(HttpError)
    def _http_error(request: HttpRequest, exc: HttpError) -> HttpResponse:
        return problem(
            request,
            exc.status_code,
            code=f"http_{exc.status_code}",
            message_key=f"common.http_{exc.status_code}",
            detail=str(exc),
        )

    @api.exception_handler(Exception)
    def _unhandled(request: HttpRequest, exc: Exception) -> HttpResponse:
        log.exception("unhandled error on %s %s", request.method, request.path)
        return problem(
            request,
            500,
            code="internal_error",
            message_key="common.internal_error",
            detail="Unexpected error",
        )
