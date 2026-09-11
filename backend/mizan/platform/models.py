"""Platform tables: translations of configurable labels and idempotency keys."""

from __future__ import annotations

import uuid

from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from mizan.platform import context
from mizan.platform.ids import uuid7


def _default_tenant_id() -> uuid.UUID | None:
    return context.current_tenant_id.get()


class I18nText(models.Model):
    """``i18n_text(entity, entity_id, field, locale, text)`` (SPEC §8)."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant_id = models.UUIDField(default=_default_tenant_id, db_index=True)
    entity = models.CharField(max_length=64)
    entity_id = models.UUIDField()
    field = models.CharField(max_length=32, default="label")
    locale = models.CharField(max_length=8)
    text = models.TextField()

    class Meta:
        db_table = "i18n_text"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "entity", "entity_id", "field", "locale"],
                name="uq_i18n_text_key",
            ),
            models.UniqueConstraint(
                "tenant_id",
                "entity",
                "field",
                "locale",
                Lower("text"),
                condition=models.Q(field="label"),
                name="uq_i18n_label",
            ),
        ]
        indexes = [models.Index(fields=["entity", "entity_id"], name="idx_i18n_text_entity")]

    def __str__(self) -> str:
        return f"{self.entity}:{self.entity_id}.{self.field}[{self.locale}]"


class IdempotencyKey(models.Model):
    """Stored response of a creating POST for 24 hours per tenant (SPEC §8)."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant_id = models.UUIDField(default=_default_tenant_id, db_index=True)
    key = models.CharField(max_length=128)
    fingerprint = models.CharField(max_length=64)
    status_code = models.PositiveSmallIntegerField()
    response_body = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "idempotency_key"
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "key"], name="uq_idempotency_key")
        ]

    def __str__(self) -> str:
        return f"{self.key} ({self.status_code})"
