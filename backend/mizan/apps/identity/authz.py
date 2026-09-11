"""Resolver: principal → effective permissions; ``requires`` for API operations (SPEC §9.4)."""

from __future__ import annotations

import functools
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.db.models import Model, Q, QuerySet
from django.http import HttpRequest
from ninja.security import HttpBearer

from mizan.apps.identity.models import Grant, Membership, MembershipStatus, RoleStatus
from mizan.apps.identity.principal import Principal
from mizan.platform.api.errors import Forbidden, Unauthorized
from mizan.platform.authz.fields import serialize as serialize_fields
from mizan.platform.authz.permissions import (
    DEFAULT_SCOPE_FIELDS,
    EffectivePermissions,
    GrantBinding,
    ScopeFields,
)

CACHE_KEY = "effective_permissions"


def resolve_permissions(user_id: uuid.UUID, tenant_id: uuid.UUID | None) -> EffectivePermissions:
    """Union of the grants of every active membership, bound to that membership's scope."""
    memberships = (
        Membership.objects.filter(
            user_id=user_id, status=MembershipStatus.ACTIVE, role__status=RoleStatus.ACTIVE
        )
        .select_related("role")
        .order_by("created_at")
    )
    grants_by_role: dict[uuid.UUID, list[Grant]] = {}
    for grant in Grant.objects.filter(role__in=[m.role_id for m in memberships]):
        grants_by_role.setdefault(grant.role_id, []).append(grant)
    bindings: list[GrantBinding] = []
    for membership in memberships:
        for grant in grants_by_role.get(membership.role_id, []):
            bindings.append(
                GrantBinding(
                    resource=grant.resource,
                    action=grant.action,
                    scope=grant.scope,
                    field_groups=frozenset(grant.field_groups or []),
                    role_code=membership.role.code,
                    membership_id=membership.id,
                    branch_id=membership.branch_id,
                    department_id=membership.department_id,
                    account_id=membership.account_id,
                    project_ids=tuple(uuid.UUID(str(p)) for p in (membership.project_ids or [])),
                )
            )
    return EffectivePermissions(user_id=user_id, tenant_id=tenant_id, bindings=bindings)


def permissions_for(principal: Principal) -> EffectivePermissions:
    cached = principal.cache.get(CACHE_KEY)
    if isinstance(cached, EffectivePermissions):
        return cached
    if principal.is_platform_operator and principal.tenant_id is None:
        perms = EffectivePermissions.for_platform_operator(principal.user_id)
    else:
        perms = resolve_permissions(principal.user_id, principal.tenant_id)
    principal.cache[CACHE_KEY] = perms
    return perms


@dataclass(slots=True)
class Authorization:
    """What the current operation may do; attached to ``request.authz`` by ``requires``."""

    principal: Principal
    permissions: EffectivePermissions
    resource: str
    action: str

    @property
    def field_groups(self) -> frozenset[str]:
        return self.permissions.field_groups(self.resource, self.action)

    def predicate(
        self, model: type[Model] | None = None, fields: ScopeFields = DEFAULT_SCOPE_FIELDS
    ) -> Q:
        return self.permissions.predicate(
            self.resource,
            self.action,
            model=model,
            fields=fields,
            branch_id=self.principal.branch_id,
        )

    def scope(
        self, queryset: QuerySet[Any], fields: ScopeFields = DEFAULT_SCOPE_FIELDS
    ) -> QuerySet[Any]:
        return queryset.filter(self.predicate(queryset.model, fields))

    def can(self, resource: str, action: str) -> bool:
        return self.permissions.allows(resource, action, branch_id=self.principal.branch_id)

    def serialize(self, obj: Any, schema: Any, resource: str | None = None) -> dict[str, Any]:
        groups = self.permissions.field_groups(resource or self.resource, "view")
        return serialize_fields(obj, schema, groups)


def authorize(request: HttpRequest, resource: str, action: str) -> Authorization:
    principal: Principal | None = getattr(request, "principal", None)
    if principal is None:
        raise Unauthorized()
    perms = permissions_for(principal)
    if not perms.allows(resource, action, branch_id=principal.branch_id):
        raise Forbidden(params={"action": f"{resource}.{action}"})
    authz = Authorization(principal=principal, permissions=perms, resource=resource, action=action)
    request.authz = authz  # type: ignore[attr-defined]
    return authz


class Requires(HttpBearer):
    """Ninja auth callback checking one permission before the request body is parsed."""

    def __init__(self, resource: str, action: str) -> None:
        super().__init__()
        self.resource = resource
        self.action = action

    def __call__(self, request: HttpRequest) -> Principal | None:
        principal: Principal | None = getattr(request, "principal", None)
        if principal is None:
            return None  # Ninja turns this into 401
        authorize(request, self.resource, self.action)  # raises Forbidden (403)
        return principal

    def authenticate(self, request: HttpRequest, token: str) -> Any:
        return self(request)


def requires(resource: str, action: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Declare the ``(resource, action)`` of an API operation (SPEC §33.1 rule 3).

    ``install_permissions`` later moves the check into the operation's auth callbacks so it
    runs before body validation; the decorator still guards direct calls to the view.
    """

    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(view)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            if getattr(request, "authz", None) is None or request.authz.resource != resource:  # type: ignore[attr-defined]
                authorize(request, resource, action)
            return view(request, *args, **kwargs)

        wrapper.permission = (resource, action)  # type: ignore[attr-defined]
        return wrapper

    return decorator


def install_permissions(api: Any) -> dict[str, tuple[str, str]]:
    """Attach ``Requires`` auth callbacks and ``x-permission`` to every declared operation."""
    declared: dict[str, tuple[str, str]] = {}
    for _prefix, router in api._routers:
        for path, path_view in router.path_operations.items():
            for operation in path_view.operations:
                permission = getattr(operation.view_func, "permission", None)
                if permission is None:
                    continue
                resource, action = permission
                # _set_auth records the explicit auth so binding keeps it instead of the API default
                guard = Requires(resource, action)
                operation.auth_param = guard  # an explicit auth survives cloning into bound routers
                operation.auth_callbacks = [guard]
                extra = dict(operation.openapi_extra or {})
                extra["x-permission"] = f"{resource}.{action}"
                operation.openapi_extra = extra
                declared[f"{','.join(operation.methods)} {path}"] = permission
    return declared
