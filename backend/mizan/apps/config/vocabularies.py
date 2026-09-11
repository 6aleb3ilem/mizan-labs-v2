"""Vocabularies (SPEC §10.2): simple admin-defined lists with a "used by" hook before retirement."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Callable

from django.utils import timezone

from mizan.apps.config.models import VocabularyEntry
from mizan.platform.api.errors import NotFound

KINDS: tuple[str, ...] = (
    "task_category", "quote_condition", "contact_function", "participant_role", "priority", "sample_nature",
    "material_family", "block_type", "specimen_shape", "curing_location", "payment_method", "reason",
    "client_tier", "unit", "equipment_condition", "vehicle_document_type",
)  # fmt: skip

UsageCounter = Callable[[VocabularyEntry], int]
_usage: dict[str, list[tuple[str, UsageCounter]]] = defaultdict(list)


def register_usage(kind: str, label: str) -> Callable[[UsageCounter], UsageCounter]:
    def decorator(func: UsageCounter) -> UsageCounter:
        _usage[kind].append((label, func))
        return func

    return decorator


def usage_of(entry: VocabularyEntry) -> dict[str, int]:
    return {label: counter(entry) for label, counter in _usage.get(entry.kind, [])}


def resolve(kind: str, code: str, branch_id: uuid.UUID | None = None) -> VocabularyEntry:
    qs = VocabularyEntry.objects.filter(kind=kind, code=code)
    entry: VocabularyEntry | None = qs.filter(branch_id=branch_id).first() if branch_id else None
    if entry is None:
        entry = qs.filter(branch__isnull=True).first()
    if entry is None:
        raise NotFound("config.vocabulary.unknown_entry", params={"kind": kind, "code": code})
    return entry


def retire(entry: VocabularyEntry) -> VocabularyEntry:
    """Retired entries stay valid on historical records and disappear from pickers."""
    entry.active = False
    entry.retired_at = timezone.now()
    entry.save(update_fields=["active", "retired_at"])
    return entry
