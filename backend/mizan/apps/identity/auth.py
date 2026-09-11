"""Django Ninja authentication: the principal resolved by ``PrincipalMiddleware``."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from ninja.security import HttpBearer

from mizan.apps.identity.principal import Principal


class PrincipalAuth(HttpBearer):
    """Accepts a bearer token or a browser session (both resolved by the middleware)."""

    def __call__(self, request: HttpRequest) -> Principal | None:
        return getattr(request, "principal", None)

    def authenticate(self, request: HttpRequest, token: str) -> Any:
        return getattr(request, "principal", None)


principal_auth = PrincipalAuth()
