"""Identity services: sessions (login, refresh, logout), users, memberships, roles."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from mizan.apps.identity.models import (
    Grant,
    Membership,
    MembershipStatus,
    RefreshToken,
    Role,
    RoleStatus,
    User,
    UserStatus,
)
from mizan.platform import context
from mizan.platform.api.errors import (
    ApiError,
    Conflict,
    NotFound,
    Unauthorized,
    UnprocessableEntity,
)
from mizan.platform.auth.jwt import Realm, issue_access_token
from mizan.platform.authz.catalog import validate_grant
from mizan.platform.db.tenancy import platform_scope


class InvalidCredentials(ApiError):
    status = 401
    code = "invalid_credentials"
    message_key = "auth.invalid_credentials"


class AccountDisabled(ApiError):
    status = 403
    code = "account_disabled"
    message_key = "auth.account_disabled"


class TenantRequired(ApiError):
    status = 409
    code = "tenant_required"
    message_key = "auth.tenant_required"


@dataclass(frozen=True, slots=True)
class Session:
    user: User
    session_id: uuid.UUID
    access_token: str
    refresh_token: str
    expires_in: int


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _new_refresh_token(
    user: User, session_id: uuid.UUID, *, user_agent: str = "", ip: str = ""
) -> str:
    raw = secrets.token_urlsafe(48)
    RefreshToken.objects.create(
        tenant_id=user.tenant_id,
        user=user,
        session_id=session_id,
        token_hash=_hash(raw),
        expires_at=timezone.now() + timedelta(seconds=int(settings.MIZAN_JWT_REFRESH_TTL)),
        user_agent=user_agent[:256],
        ip=ip[:64],
    )
    return raw


def _session_for(
    user: User, session_id: uuid.UUID, *, user_agent: str = "", ip: str = ""
) -> Session:
    realm: Realm = user.realm  # type: ignore[assignment]
    access = issue_access_token(
        user_id=user.id, tenant_id=user.tenant_id, realm=realm, session_id=session_id
    )
    refresh = _new_refresh_token(user, session_id, user_agent=user_agent, ip=ip)
    return Session(
        user=user,
        session_id=session_id,
        access_token=access,
        refresh_token=refresh,
        expires_in=int(settings.MIZAN_JWT_ACCESS_TTL),
    )


def login(
    email: str, password: str, *, tenant_code: str | None = None, user_agent: str = "", ip: str = ""
) -> Session:
    """Password login for every realm. Runs under the platform bypass: no tenant is known yet."""
    with platform_scope(), transaction.atomic():
        candidates = list(User.objects.filter(email__iexact=email).order_by("created_at"))
        if tenant_code:
            from mizan.apps.org.models import Tenant

            tenant_ids = set(Tenant.objects.filter(code=tenant_code).values_list("id", flat=True))
            candidates = [u for u in candidates if u.tenant_id in tenant_ids]
        if not candidates:
            # constant-time-ish: still run a hash to blunt user enumeration by timing
            User().set_password(password)
            raise InvalidCredentials()
        if len(candidates) > 1:
            raise TenantRequired()
        user = candidates[0]
        if not user.check_password(password):
            raise InvalidCredentials()
        if user.status != UserStatus.ACTIVE:
            raise AccountDisabled()
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        return _session_for(user, uuid.uuid4(), user_agent=user_agent, ip=ip)


def refresh(raw_refresh_token: str, *, user_agent: str = "", ip: str = "") -> Session:
    """Rotate a refresh token. Reusing a rotated token revokes the whole session (theft signal)."""
    token_hash = _hash(raw_refresh_token)
    with platform_scope():
        token = RefreshToken.objects.select_related("user").filter(token_hash=token_hash).first()
    if token is None:
        raise Unauthorized("auth.invalid_refresh_token", code="invalid_refresh_token")
    now = timezone.now()
    if token.revoked_at is not None or token.used_at is not None:
        # Writes happen in their own transaction so that raising afterwards keeps them.
        with platform_scope():
            RefreshToken.objects.filter(
                session_id=token.session_id, revoked_at__isnull=True
            ).update(revoked_at=now)
        raise Unauthorized("auth.refresh_token_reused", code="refresh_token_reused")
    if token.expires_at <= now:
        raise Unauthorized("auth.refresh_token_expired", code="refresh_token_expired")
    if token.user.status != UserStatus.ACTIVE:
        raise AccountDisabled()
    with platform_scope(), transaction.atomic():
        claimed = RefreshToken.objects.filter(
            pk=token.pk, used_at__isnull=True, revoked_at__isnull=True
        ).update(used_at=now)
        if claimed != 1:  # lost a race with a concurrent refresh of the same token
            RefreshToken.objects.filter(
                session_id=token.session_id, revoked_at__isnull=True
            ).update(revoked_at=now)
            raise Unauthorized("auth.refresh_token_reused", code="refresh_token_reused")
        return _session_for(token.user, token.session_id, user_agent=user_agent, ip=ip)


def logout(raw_refresh_token: str) -> None:
    with platform_scope():
        token = RefreshToken.objects.filter(token_hash=_hash(raw_refresh_token)).first()
        if token is not None:
            RefreshToken.objects.filter(
                session_id=token.session_id, revoked_at__isnull=True
            ).update(revoked_at=timezone.now())


def revoke_all_sessions(user: User) -> None:
    RefreshToken.objects.filter(user=user, revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )


def change_password(user: User, current_password: str, new_password: str) -> None:
    if not user.check_password(current_password):
        raise InvalidCredentials()
    try:
        validate_password(new_password, user)
    except DjangoValidationError as exc:
        raise UnprocessableEntity(
            "auth.weak_password",
            details=[{"loc": ["new_password"], "msg": m} for m in exc.messages],
        ) from exc
    user.set_password(new_password)
    user.must_change_password = False
    user.save(update_fields=["password", "must_change_password", "updated_at"])
    revoke_all_sessions(user)


# --- users ----------------------------------------------------------------------------


def create_user(
    *,
    email: str,
    display_name: str = "",
    locale: str = "fr",
    realm: str = "STAFF",
    temporary_password: str | None = None,
) -> User:
    tenant_id = context.require_tenant_id()
    if User.objects.filter(email__iexact=email).exists():
        raise Conflict("identity.user.email_exists", code="email_exists")
    password = temporary_password or secrets.token_urlsafe(12)
    user = User.objects.create_user(
        email, password, tenant_id=tenant_id, realm=realm, display_name=display_name, locale=locale
    )
    user.must_change_password = True
    user.save(update_fields=["must_change_password"])
    return user


def disable_user(user: User) -> User:
    user.status = UserStatus.DISABLED
    user.disabled_at = timezone.now()
    user.save(update_fields=["status", "disabled_at", "updated_at"])
    revoke_all_sessions(user)
    return user


# --- memberships and roles ------------------------------------------------------------


def add_membership(
    *,
    user: User,
    role: Role,
    branch_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    account_id: uuid.UUID | None = None,
    project_ids: list[uuid.UUID] | None = None,
) -> Membership:
    if role.status != RoleStatus.ACTIVE:
        raise UnprocessableEntity("identity.role.retired", code="role_retired")
    membership: Membership = Membership.objects.create(
        user=user,
        role=role,
        branch_id=branch_id,
        department_id=department_id,
        account_id=account_id,
        project_ids=[str(p) for p in (project_ids or [])],
        status=MembershipStatus.ACTIVE,
    )
    return membership


def create_role(
    *, code: str, labels: dict[str, str], description: str = "", grants: list[dict[str, object]]
) -> Role:
    if Role.objects.filter(code=code).exists():
        raise Conflict("identity.role.code_exists", code="role_code_exists")
    role: Role = Role.objects.create(code=code, description=description)
    role.set_labels({k: v for k, v in labels.items() if v})
    replace_grants(role, grants)
    return role


def replace_grants(role: Role, grants: list[dict[str, Any]]) -> Role:
    seen: set[tuple[str, str, str]] = set()
    rows: list[Grant] = []
    for spec in grants:
        resource, action, scope = str(spec["resource"]), str(spec["action"]), str(spec["scope"])
        groups = [str(g) for g in (spec.get("field_groups") or [])]
        try:
            validate_grant(resource, action, scope, groups)
        except ValueError as exc:
            raise UnprocessableEntity(
                "identity.grant.invalid", details=[{"msg": str(exc)}]
            ) from exc
        key = (resource, action, scope)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            Grant(
                role=role,
                resource=resource,
                action=action,
                scope=scope,
                field_groups=sorted(set(groups)),
            )
        )
    with transaction.atomic():
        role.grants.all().delete()
        Grant.objects.bulk_create(rows)
    return role


def duplicate_role(role: Role, new_code: str, labels: dict[str, str]) -> Role:
    grants = [
        {
            "resource": g.resource,
            "action": g.action,
            "scope": g.scope,
            "field_groups": g.field_groups,
        }
        for g in role.grants.all()
    ]
    return create_role(code=new_code, labels=labels, description=role.description, grants=grants)


def retire_role(role: Role) -> Role:
    """Roles in use cannot be deleted; they are retired (SPEC §9.4)."""
    role.status = RoleStatus.RETIRED
    role.save(update_fields=["status", "updated_at"])
    return role


def get_role(role_id: uuid.UUID) -> Role:
    try:
        role: Role = Role.objects.get(pk=role_id)
    except Role.DoesNotExist as exc:
        raise NotFound() from exc
    return role
