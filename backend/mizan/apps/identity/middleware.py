"""Resolves the principal (JWT or browser session) and opens the tenant scope.

Order in MIDDLEWARE: after AuthenticationMiddleware. Everything downstream (Ninja views,
services, audit) runs inside ``tenant_scope`` so row-level security applies; the Django
admin and the allauth headless endpoints run under ``platform_scope`` (ADR 0003).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from contextlib import ExitStack

from django.http import HttpRequest, HttpResponse

from mizan.apps.identity.principal import Principal
from mizan.platform import context
from mizan.platform.auth.jwt import InvalidToken, decode_access_token
from mizan.platform.db.tenancy import platform_scope, tenant_scope

SESSION_TENANT_KEY = "mizan_tenant_id"
PLATFORM_PATH_PREFIXES = ("/admin/", "/_allauth/")
UNSCOPED_PATHS = ("/health", "/ready")


def _principal_from_bearer(request: HttpRequest) -> Principal | None:
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    token = header[7:].strip()
    try:
        claims = decode_access_token(token)
    except InvalidToken:
        return None
    return Principal(
        user_id=claims.user_id,
        tenant_id=claims.tenant_id,
        realm=claims.realm,
        session_id=claims.session_id,
        step_up_at=claims.step_up_at,
    )


def _principal_from_session(request: HttpRequest) -> Principal | None:
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None
    tenant_raw = request.session.get(SESSION_TENANT_KEY)
    tenant_id = uuid.UUID(tenant_raw) if tenant_raw else user.tenant_id
    return Principal(
        user_id=user.id,
        tenant_id=tenant_id,
        realm=user.realm,
        display_name=user.display_name,
        locale=user.locale,
    )


def _branch_header(request: HttpRequest) -> uuid.UUID | None:
    raw = request.headers.get("X-Branch-Id")
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


class PrincipalMiddleware:
    sync_capable = True
    async_capable = False

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        path = request.path
        if path.startswith(UNSCOPED_PATHS):
            request.principal = None  # type: ignore[attr-defined]
            return self.get_response(request)

        if path.startswith(PLATFORM_PATH_PREFIXES):
            # Django admin (platform operators) and the browser login realm: the user is
            # loaded before any tenant is known, so these run under the platform bypass.
            request.principal = None  # type: ignore[attr-defined]
            with platform_scope():
                request.principal = _principal_from_session(request)  # type: ignore[attr-defined]
                return self.get_response(request)

        principal = _principal_from_bearer(request)
        with ExitStack() as stack:
            if principal is None:
                # Session realm: the tenant id was stored in the session at login.
                tenant_raw = (
                    request.session.get(SESSION_TENANT_KEY) if hasattr(request, "session") else None
                )
                if tenant_raw:
                    stack.enter_context(tenant_scope(uuid.UUID(tenant_raw)))
                    principal = _principal_from_session(request)
                else:
                    with platform_scope():
                        principal = _principal_from_session(request)
                    if principal is not None and principal.tenant_id is not None:
                        stack.enter_context(tenant_scope(principal.tenant_id))
            elif principal.tenant_id is not None:
                stack.enter_context(tenant_scope(principal.tenant_id))

            if (
                principal is not None
                and principal.is_platform_operator
                and principal.tenant_id is None
            ):
                stack.enter_context(platform_scope())

            if principal is not None:
                principal.branch_id = _branch_header(request)
                actor_type: context.ActorType = "CLIENT" if principal.is_client else "USER"
                stack.enter_context(_actor(context.Actor(id=principal.user_id, type=actor_type)))
            request.principal = principal  # type: ignore[attr-defined]
            return self.get_response(request)
        raise AssertionError("unreachable")


class _actor:
    def __init__(self, actor: context.Actor) -> None:
        self.actor = actor
        self.token: object = None

    def __enter__(self) -> None:
        self.token = context.current_actor.set(self.actor)

    def __exit__(self, *exc: object) -> None:
        context.current_actor.reset(self.token)  # type: ignore[arg-type]
