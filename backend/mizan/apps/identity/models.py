"""Users, memberships, roles and grants (SPEC §9)."""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from mizan.platform.db import CodeField, TenantModel
from mizan.platform.ids import uuid7
from mizan.platform.labels import LabelledModel


class Realm(models.TextChoices):
    STAFF = "STAFF", "Staff"
    CLIENT = "CLIENT", "Client"
    PLATFORM = "PLATFORM", "Platform operator"


class UserStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    DISABLED = "DISABLED", "Disabled"


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def create_user(
        self,
        email: str,
        password: str | None = None,
        *,
        tenant_id: uuid.UUID | None = None,
        realm: str = Realm.STAFF,
        **extra: Any,
    ) -> User:
        if not email:
            raise ValueError("An e-mail address is required")
        user = self.model(
            email=self.normalize_email(email), tenant_id=tenant_id, realm=realm, **extra
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra: Any) -> User:
        extra.setdefault("display_name", email)
        extra["is_staff"] = True
        extra["is_superuser"] = True
        return self.create_user(email, password, tenant_id=None, realm=Realm.PLATFORM, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """``user`` (SPEC §9.1). Platform operators have no tenant and see the Django admin."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    idp_subject = models.CharField(max_length=255, null=True, blank=True, unique=True)
    email = models.EmailField()
    display_name = models.CharField(max_length=200, blank=True, default="")
    locale = models.CharField(max_length=8, default="fr")
    realm = models.CharField(max_length=16, choices=Realm.choices, default=Realm.STAFF)
    status = models.CharField(max_length=16, choices=UserStatus.choices, default=UserStatus.ACTIVE)
    mfa_enrolled = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)
    is_staff = models.BooleanField(
        default=False, help_text="Access to the platform operator console"
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    disabled_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects: ClassVar[UserManager] = UserManager()

    class Meta:
        db_table = "app_user"
        constraints = [
            models.UniqueConstraint(
                "tenant_id",
                Lower("email"),
                name="uq_app_user_email_per_tenant",
                nulls_distinct=False,
            )
        ]

    def __str__(self) -> str:
        return self.display_name or self.email

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self.status = UserStatus.ACTIVE if value else UserStatus.DISABLED

    @property
    def is_platform_operator(self) -> bool:
        return self.realm == Realm.PLATFORM

    @property
    def last_login_at(self) -> Any:
        return self.last_login


class RoleStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    RETIRED = "RETIRED", "Retired"


class Role(TenantModel, LabelledModel):
    """A set of grants (SPEC §9.1). Roles in use are retired, never deleted."""

    label_entity = "role"

    code = CodeField()
    is_template = models.BooleanField(default=False)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=RoleStatus.choices, default=RoleStatus.ACTIVE)

    class Meta(TenantModel.Meta):
        db_table = "role"
        ordering = ["code"]
        constraints = [models.UniqueConstraint(fields=["tenant_id", "code"], name="uq_role_code")]

    def __str__(self) -> str:
        return str(self.code)


class Grant(TenantModel):
    """``grant(role, resource, action, scope, field_groups[])``."""

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="grants")
    resource = models.CharField(max_length=64)
    action = models.CharField(max_length=32)
    scope = models.CharField(max_length=32)
    field_groups = models.JSONField(default=list, blank=True)

    class Meta(TenantModel.Meta):
        db_table = "grant_"
        ordering = ["resource", "action"]
        constraints = [
            models.UniqueConstraint(
                fields=["role", "resource", "action", "scope"], name="uq_grant_role_resource_action"
            )
        ]

    def __str__(self) -> str:
        return f"{self.role.code}: {self.resource}.{self.action} [{self.scope}]"


class MembershipStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"


class Membership(TenantModel):
    """A user holds a role in a branch/department (staff) or an account (client users)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="memberships")
    branch = models.ForeignKey(
        "org.Branch", on_delete=models.PROTECT, null=True, blank=True, related_name="memberships"
    )
    department = models.ForeignKey(
        "org.Department",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="memberships",
    )
    account_id = models.UUIDField(null=True, blank=True, db_index=True)
    project_ids = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=16, choices=MembershipStatus.choices, default=MembershipStatus.ACTIVE
    )

    class Meta(TenantModel.Meta):
        db_table = "membership"

    def __str__(self) -> str:
        return f"{self.user_id} as {self.role_id}"


class RefreshToken(models.Model):
    """Rotating refresh tokens; the hash is stored, the reuse of a rotated token revokes the session."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refresh_tokens")
    session_id = models.UUIDField(db_index=True)
    token_hash = models.CharField(max_length=64, unique=True)
    issued_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    user_agent = models.CharField(max_length=256, blank=True, default="")
    ip = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        db_table = "refresh_token"

    def __str__(self) -> str:
        return f"session {self.session_id}"


class ApiKey(TenantModel):
    """Integration credentials bound to a role (SPEC §9.1)."""

    name = models.CharField(max_length=120)
    hashed_key = models.CharField(max_length=64, unique=True)
    prefix = models.CharField(max_length=12)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="api_keys")
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantModel.Meta):
        db_table = "api_key"

    def __str__(self) -> str:
        return self.name
