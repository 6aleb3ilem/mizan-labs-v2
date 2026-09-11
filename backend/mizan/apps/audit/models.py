"""``audit_event`` (SPEC §20.1): append-only; UPDATE and DELETE are rejected by a trigger."""

from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone

from mizan.platform import context
from mizan.platform.ids import uuid7


def _default_tenant_id() -> uuid.UUID | None:
    return context.current_tenant_id.get()


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant_id = models.UUIDField(default=_default_tenant_id, null=True, blank=True, db_index=True)
    branch_id = models.UUIDField(null=True, blank=True)
    aggregate_type = models.CharField(max_length=64)
    aggregate_id = models.UUIDField(null=True, blank=True)
    action = models.CharField(max_length=64)
    actor_id = models.UUIDField(null=True, blank=True)
    actor_type = models.CharField(max_length=16, default="SYSTEM")
    at = models.DateTimeField(default=timezone.now, db_index=True)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    context = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "audit_event"
        ordering = ["-at", "-id"]
        indexes = [
            models.Index(
                fields=["aggregate_type", "aggregate_id", "at"], name="idx_audit_aggregate"
            ),
            models.Index(fields=["tenant_id", "at"], name="idx_audit_tenant_at"),
            models.Index(fields=["actor_id", "at"], name="idx_audit_actor_at"),
        ]

    def __str__(self) -> str:
        return f"{self.aggregate_type}:{self.aggregate_id} {self.action}"
