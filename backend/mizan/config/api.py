"""The public API (Django Ninja): one NinjaAPI, one router per app.

Every operation declares its permission with ``@requires(resource, action)`` (see
``mizan.apps.identity.authz``); public operations declare ``auth=None`` explicitly.
"""

from __future__ import annotations

from ninja import NinjaAPI

from mizan.apps.identity.auth import principal_auth
from mizan.platform.api.errors import install_exception_handlers
from mizan.platform.api.renderers import ORJSONRenderer
from mizan.platform.health import router as health_router

api = NinjaAPI(
    title="Mizan Labs Platform API",
    version="1.0.0",
    description=(
        "Multi-tenant laboratory operations platform. Tenant is resolved from the token; "
        "branch from the X-Branch-Id header. Errors are RFC 9457 problem details with a "
        "translatable message_key."
    ),
    urls_namespace="api_v1",
    openapi_url="/openapi.json",
    docs_url="/docs",
    auth=principal_auth,
    renderer=ORJSONRenderer(),
    servers=[{"url": "/api/v1"}],
)
install_exception_handlers(api)

api.add_router("", health_router, tags=["platform"])


def _register_app_routers() -> None:
    """Routers are registered lazily so that apps can import the API module for schemas."""
    from mizan.apps.identity.api import router as identity_router

    api.add_router("", identity_router)


_register_app_routers()
