"""Shared response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from ninja import Schema


class AuditedSchema(Schema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    row_version: int


class LabelsSchema(Schema):
    """Translations keyed by locale, e.g. ``{"fr": "Béton", "en": "Concrete"}``."""

    fr: str | None = None
    en: str | None = None


class OkSchema(Schema):
    ok: bool = True
