"""Users, memberships, roles and grants (SPEC §9)."""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from mizan.platform.ids import uuid7


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
