"""Base models: common columns (SPEC §8), soft delete, optimistic locking, tenant scoping."""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.db import models
from django.utils import timezone

from mizan.platform import context
from mizan.platform.ids import uuid7


class ConcurrentUpdate(Exception):
    """Raised when a row was modified by someone else since it was loaded (row_version)."""

    def __init__(self, model: type[models.Model], pk: Any) -> None:
        super().__init__(f"{model.__name__} {pk} was modified concurrently")
        self.model = model
        self.pk = pk


class ActiveQuerySet(models.QuerySet):  # type: ignore[type-arg]
    def alive(self) -> ActiveQuerySet:
        return self.filter(deleted_at__isnull=True)

    def deleted(self) -> ActiveQuerySet:
        return self.filter(deleted_at__isnull=False)


class ActiveManager(models.Manager.from_queryset(ActiveQuerySet)):  # type: ignore[misc]
    """Default manager: hides soft-deleted rows. ``all_objects`` sees everything."""

    def get_queryset(self) -> ActiveQuerySet:
        queryset: ActiveQuerySet = super().get_queryset().filter(deleted_at__isnull=True)
        return queryset


class AllObjectsManager(models.Manager.from_queryset(ActiveQuerySet)):  # type: ignore[misc]
    pass


def _actor_id() -> uuid.UUID | None:
    return context.actor().id


class BaseModel(models.Model):
    """UUID v7 key, audit columns, soft delete and optimistic locking."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
    created_by = models.UUIDField(null=True, blank=True, editable=False)
    updated_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_by = models.UUIDField(null=True, blank=True, editable=False)
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)
    deleted_reason = models.TextField(null=True, blank=True, editable=False)
    row_version = models.PositiveIntegerField(default=1, editable=False)

    objects: ClassVar[ActiveManager] = ActiveManager()
    all_objects: ClassVar[AllObjectsManager] = AllObjectsManager()

    class Meta:
        abstract = True
        ordering = ["-created_at", "-id"]
        base_manager_name = "all_objects"

    def save(self, *args: Any, **kwargs: Any) -> None:
        now = timezone.now()
        actor = _actor_id()
        if self._state.adding:
            if self.created_by is None:
                self.created_by = actor
            self.updated_at = now
            self.updated_by = actor
            super().save(*args, **kwargs)
            return
        self._save_with_version_check(now, actor, kwargs.get("update_fields"))

    def _save_with_version_check(
        self, now: Any, actor: uuid.UUID | None, update_fields: Any
    ) -> None:
        expected_version = self.row_version
        self.updated_at = now
        self.updated_by = actor
        names = (
            set(update_fields) | {"updated_at", "updated_by"}
            if update_fields is not None
            else {f.name for f in self._meta.concrete_fields if not f.primary_key}
        )
        names.discard("row_version")
        names.discard("created_at")
        names.discard("created_by")
        values = {
            f.attname: getattr(self, f.attname)
            for f in self._meta.concrete_fields
            if f.name in names or f.attname in names
        }
        values["row_version"] = expected_version + 1
        updated = (
            type(self).all_objects.filter(pk=self.pk, row_version=expected_version).update(**values)
        )
        if updated != 1:
            raise ConcurrentUpdate(type(self), self.pk)
        self.row_version = expected_version + 1

    def soft_delete(self, reason: str) -> None:
        self.deleted_at = timezone.now()
        self.deleted_reason = reason
        self.save(update_fields=["deleted_at", "deleted_reason"])

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


def _default_tenant_id() -> uuid.UUID | None:
    return context.current_tenant_id.get()


class TenantModel(BaseModel):
    """A row owned by one tenant; row-level security enforces the isolation."""

    tenant_id = models.UUIDField(default=_default_tenant_id, editable=False, db_index=True)

    class Meta(BaseModel.Meta):
        abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        current: uuid.UUID | None = getattr(self, "tenant_id", None)
        if current is None:
            self.tenant_id = context.require_tenant_id()
        super().save(*args, **kwargs)


class BranchScopedModel(TenantModel):
    """A tenant row that also belongs to one branch (laboratory)."""

    branch = models.ForeignKey(
        "org.Branch", on_delete=models.PROTECT, related_name="+", db_column="branch_id"
    )

    class Meta(TenantModel.Meta):
        abstract = True


class CodeField(models.CharField):  # type: ignore[type-arg]
    """Immutable machine code: ``^[A-Z0-9_.-]{2,64}$`` (SPEC §8)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("max_length", 64)
        super().__init__(*args, **kwargs)
