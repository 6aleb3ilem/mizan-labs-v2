"""Identity API: sessions, profile and permissions, users, memberships, roles (SPEC A.1, A.3)."""

import uuid
from typing import Any

from django.http import HttpRequest
from ninja import Query, Router, Status
from ninja.throttling import AnonRateThrottle

from mizan.apps.identity import services
from mizan.apps.identity.authz import permissions_for, requires, resolve_permissions
from mizan.apps.identity.models import Membership, MembershipStatus, Role, User
from mizan.apps.identity.principal import Principal
from mizan.apps.identity.schemas import (
    ChangePasswordIn,
    LoginIn,
    MembershipIn,
    MembershipOut,
    MeOut,
    PermissionsOut,
    RefreshIn,
    RoleIn,
    RoleOut,
    RolePatch,
    TokenOut,
    UserIn,
    UserOut,
    UserPatch,
)
from mizan.platform.api.errors import NotFound, Unauthorized
from mizan.platform.api.idempotency import idempotent
from mizan.platform.api.pagination import CursorParams, Page, paginate
from mizan.platform.api.schemas import OkSchema
from mizan.platform.middleware import client_ip

router = Router(tags=["identity"])


def _principal(request: HttpRequest) -> Principal:
    principal: Principal | None = getattr(request, "principal", None)
    if principal is None:
        raise Unauthorized()
    return principal


def _membership_out(m: Membership) -> dict[str, Any]:
    return {
        "id": m.id,
        "user_id": m.user_id,
        "role_id": m.role_id,
        "role_code": m.role.code,
        "branch_id": m.branch_id,
        "department_id": m.department_id,
        "account_id": m.account_id,
        "project_ids": [uuid.UUID(str(p)) for p in (m.project_ids or [])],
        "status": m.status,
    }


def _me_out(user: User) -> dict[str, Any]:
    memberships = Membership.objects.filter(
        user=user, status=MembershipStatus.ACTIVE
    ).select_related("role")
    return {
        **UserOut.from_orm(user).model_dump(),
        "memberships": [_membership_out(m) for m in memberships],
    }


def _token_out(session: services.Session) -> dict[str, Any]:
    from mizan.platform.db.tenancy import platform_scope

    with platform_scope():
        user_out = _me_out(session.user)
    return {
        "access_token": session.access_token,
        "token_type": "Bearer",
        "expires_in": session.expires_in,
        "refresh_token": session.refresh_token,
        "user": user_out,
    }


# --- sessions --------------------------------------------------------------------------


@router.post(
    "/auth/login",
    auth=None,
    response=TokenOut,
    throttle=[AnonRateThrottle("10/m")],
    summary="Password login",
)
def auth_login(request: HttpRequest, payload: LoginIn) -> dict[str, Any]:
    session = services.login(
        payload.email,
        payload.password,
        tenant_code=payload.tenant_code,
        user_agent=request.headers.get("User-Agent", ""),
        ip=client_ip(request) or "",
    )
    return _token_out(session)


@router.post(
    "/auth/refresh",
    auth=None,
    response=TokenOut,
    throttle=[AnonRateThrottle("30/m")],
    summary="Rotate the refresh token",
)
def auth_refresh(request: HttpRequest, payload: RefreshIn) -> dict[str, Any]:
    session = services.refresh(
        payload.refresh_token,
        user_agent=request.headers.get("User-Agent", ""),
        ip=client_ip(request) or "",
    )
    return _token_out(session)


@router.post("/auth/logout", auth=None, response=OkSchema, summary="Revoke the session")
def auth_logout(request: HttpRequest, payload: RefreshIn) -> dict[str, bool]:
    services.logout(payload.refresh_token)
    return {"ok": True}


@router.post("/auth/change-password", response=OkSchema, summary="Change own password")
def auth_change_password(request: HttpRequest, payload: ChangePasswordIn) -> dict[str, bool]:
    principal = _principal(request)
    user = User.objects.get(pk=principal.user_id)
    services.change_password(user, payload.current_password, payload.new_password)
    return {"ok": True}


# --- me --------------------------------------------------------------------------------


@router.get("/me", response=MeOut, summary="Profile and memberships of the caller")
def me(request: HttpRequest) -> dict[str, Any]:
    principal = _principal(request)
    return _me_out(User.objects.get(pk=principal.user_id))


@router.get("/me/permissions", response=PermissionsOut, summary="Effective grants per membership")
def me_permissions(request: HttpRequest) -> dict[str, Any]:
    principal = _principal(request)
    perms = permissions_for(principal)
    return {
        "user_id": perms.user_id,
        "tenant_id": perms.tenant_id,
        "is_platform_operator": perms.is_platform_operator,
        "grants": perms.summary(),
    }


# --- users -----------------------------------------------------------------------------


@router.get("/users", response=Page[UserOut], summary="List users")
@requires("user", "view")
def list_users(request: HttpRequest, params: Query[CursorParams]) -> dict[str, Any]:
    return paginate(User.objects.all(), params, lambda u: UserOut.from_orm(u).model_dump())


@router.post(
    "/users", response={201: UserOut}, summary="Create a user (temporary password, forced change)"
)
@requires("user", "create")
@idempotent
def create_user(request: HttpRequest, payload: UserIn) -> Status[User]:
    user = services.create_user(
        email=payload.email,
        display_name=payload.display_name,
        locale=payload.locale,
        realm=payload.realm,
        temporary_password=payload.temporary_password,
    )
    return Status(201, user)


@router.patch("/users/{uuid:user_id}", response=UserOut, summary="Update a user")
@requires("user", "edit")
def patch_user(request: HttpRequest, user_id: uuid.UUID, payload: UserPatch) -> User:
    user = _get_user(user_id)
    for name, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, name, value)
    user.save()
    return user


@router.post(
    "/users/{uuid:user_id}:disable", response=UserOut, summary="Disable a user and revoke sessions"
)
@requires("user", "edit")
def disable_user(request: HttpRequest, user_id: uuid.UUID) -> User:
    return services.disable_user(_get_user(user_id))


@router.get(
    "/users/{uuid:user_id}/effective-permissions",
    response=PermissionsOut,
    summary='"View as": effective grants of a user',
)
@requires("user", "impersonate_view")
def user_effective_permissions(request: HttpRequest, user_id: uuid.UUID) -> dict[str, Any]:
    user = _get_user(user_id)
    perms = resolve_permissions(user.id, user.tenant_id)
    return {
        "user_id": user.id,
        "tenant_id": user.tenant_id,
        "is_platform_operator": False,
        "grants": perms.summary(),
    }


def _get_user(user_id: uuid.UUID) -> User:
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist as exc:
        raise NotFound() from exc


# --- memberships -----------------------------------------------------------------------


@router.get("/memberships", response=Page[MembershipOut], summary="List memberships")
@requires("user", "view")
def list_memberships(
    request: HttpRequest, params: Query[CursorParams], user_id: uuid.UUID | None = None
) -> dict[str, Any]:
    qs = Membership.objects.select_related("role")
    if user_id:
        qs = qs.filter(user_id=user_id)
    return paginate(qs, params, _membership_out)


@router.post("/memberships", response={201: MembershipOut}, summary="Add a membership")
@requires("user", "edit")
def create_membership(request: HttpRequest, payload: MembershipIn) -> Status[dict[str, Any]]:
    membership = services.add_membership(
        user=_get_user(payload.user_id),
        role=services.get_role(payload.role_id),
        branch_id=payload.branch_id,
        department_id=payload.department_id,
        account_id=payload.account_id,
        project_ids=payload.project_ids,
    )
    return Status(201, _membership_out(membership))


@router.delete(
    "/memberships/{uuid:membership_id}", response={204: None}, summary="Remove a membership"
)
@requires("user", "edit")
def delete_membership(request: HttpRequest, membership_id: uuid.UUID) -> Status[None]:
    deleted, _ = Membership.objects.filter(pk=membership_id).delete()
    if not deleted:
        raise NotFound()
    return Status(204, None)


# --- roles -----------------------------------------------------------------------------


def _role_out(role: Role) -> dict[str, Any]:
    return {
        "id": role.id,
        "code": role.code,
        "labels": role.labels,
        "description": role.description,
        "is_template": role.is_template,
        "status": role.status,
        "grants": [
            {
                "resource": g.resource,
                "action": g.action,
                "scope": g.scope,
                "field_groups": g.field_groups,
            }
            for g in role.grants.all()
        ],
        "memberships_count": role.memberships.count(),
    }


@router.get("/roles", response=list[RoleOut], summary="List roles with their grants")
@requires("role", "view")
def list_roles(request: HttpRequest) -> list[dict[str, Any]]:
    roles = list(Role.objects.prefetch_related("grants").order_by("code"))
    Role.attach_labels(roles)
    return [_role_out(r) for r in roles]


@router.post("/roles", response={201: RoleOut}, summary="Create a role")
@requires("role", "configure")
def create_role(request: HttpRequest, payload: RoleIn) -> Status[dict[str, Any]]:
    role = services.create_role(
        code=payload.code,
        labels=payload.labels.model_dump(exclude_none=True),
        description=payload.description,
        grants=[g.model_dump() for g in payload.grants],
    )
    return Status(201, _role_out(role))


@router.patch("/roles/{uuid:role_id}", response=RoleOut, summary="Rename or describe a role")
@requires("role", "configure")
def patch_role(request: HttpRequest, role_id: uuid.UUID, payload: RolePatch) -> dict[str, Any]:
    role = services.get_role(role_id)
    if payload.labels is not None:
        role.set_labels(payload.labels.model_dump(exclude_none=True))
    if payload.description is not None:
        role.description = payload.description
        role.save(update_fields=["description"])
    return _role_out(role)


@router.put(
    "/roles/{uuid:role_id}/grants", response=RoleOut, summary="Replace the grants of a role"
)
@requires("role", "configure")
def put_role_grants(
    request: HttpRequest, role_id: uuid.UUID, payload: list[dict[str, Any]]
) -> dict[str, Any]:
    role = services.replace_grants(services.get_role(role_id), payload)
    return _role_out(role)


@router.post("/roles/{uuid:role_id}:duplicate", response={201: RoleOut}, summary="Duplicate a role")
@requires("role", "configure")
def duplicate_role(
    request: HttpRequest, role_id: uuid.UUID, payload: RolePatch, code: str
) -> Status[dict[str, Any]]:
    role = services.duplicate_role(
        services.get_role(role_id),
        code,
        (payload.labels.model_dump(exclude_none=True) if payload.labels else {}),
    )
    return Status(201, _role_out(role))


@router.post(
    "/roles/{uuid:role_id}:retire",
    response=RoleOut,
    summary="Retire a role (never deleted while in use)",
)
@requires("role", "configure")
def retire_role(request: HttpRequest, role_id: uuid.UUID) -> dict[str, Any]:
    return _role_out(services.retire_role(services.get_role(role_id)))
