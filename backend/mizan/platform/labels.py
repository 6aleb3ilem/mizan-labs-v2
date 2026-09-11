"""Helpers for configurable labels stored in ``i18n_text`` (identity is never a label)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable
from typing import Any, ClassVar

from django.db import models

from mizan.platform.models import I18nText

Labels = dict[str, str]


def set_labels(entity: str, entity_id: uuid.UUID, labels: Labels, *, field: str = "label") -> None:
    for locale, text in labels.items():
        I18nText.objects.update_or_create(
            entity=entity, entity_id=entity_id, field=field, locale=locale, defaults={"text": text}
        )


def get_labels(entity: str, entity_id: uuid.UUID, *, field: str = "label") -> Labels:
    rows = I18nText.objects.filter(entity=entity, entity_id=entity_id, field=field).values_list(
        "locale", "text"
    )
    return dict(rows)


def labels_for(
    entity: str, ids: Iterable[uuid.UUID], *, field: str = "label"
) -> dict[uuid.UUID, Labels]:
    result: dict[uuid.UUID, Labels] = defaultdict(dict)
    rows = I18nText.objects.filter(entity=entity, entity_id__in=list(ids), field=field).values_list(
        "entity_id", "locale", "text"
    )
    for entity_id, locale, text in rows:
        result[entity_id][locale] = text
    return result


def delete_labels(entity: str, ids: Iterable[uuid.UUID]) -> int:
    deleted, _ = I18nText.objects.filter(entity=entity, entity_id__in=list(ids)).delete()
    return int(deleted)


def resolve_label(labels: Labels, locale: str, fallbacks: tuple[str, ...] = ("fr", "en")) -> str:
    if locale in labels:
        return labels[locale]
    for candidate in fallbacks:
        if candidate in labels:
            return labels[candidate]
    return next(iter(labels.values()), "")


class LabelledModel(models.Model):
    """Mixin for configurable entities: ``code`` plus translated labels in ``i18n_text``.

    Labels are unique per ``(entity, field, locale, text)`` within a tenant (SPEC §8). The
    entity key includes ``label_scope`` so that lists living under different parents (the
    states of two workflows, the entries of two vocabularies) may reuse the same words.
    """

    label_entity: ClassVar[str] = ""

    class Meta:
        abstract = True

    @property
    def label_scope(self) -> str:
        """Override to narrow uniqueness (e.g. the parent's id). Empty means tenant-wide."""
        return ""

    def label_entity_key(self) -> str:
        base = self.label_entity or self._meta.db_table
        scope = self.label_scope
        return f"{base}/{scope}" if scope else base

    @property
    def labels(self) -> Labels:
        cached: Labels | None = getattr(self, "_labels_cache", None)
        if cached is None:
            cached = get_labels(self.label_entity_key(), self.pk)
            self._labels_cache = cached
        return cached

    def set_labels(self, labels: Labels, *, field: str = "label") -> None:
        set_labels(self.label_entity_key(), self.pk, labels, field=field)
        if field == "label":
            self._labels_cache = {**getattr(self, "_labels_cache", {}), **labels}

    def label(self, locale: str = "fr") -> str:
        return resolve_label(self.labels, locale)

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        """Labels are not foreign-keyed; remove them with their owner."""
        delete_labels(self.label_entity_key(), [self.pk])
        return super().delete(*args, **kwargs)

    @classmethod
    def delete_labels_of(cls, rows: Iterable[Any]) -> None:
        by_key: dict[str, list[Any]] = defaultdict(list)
        for row in rows:
            by_key[row.label_entity_key()].append(row.pk)
        for key, ids in by_key.items():
            delete_labels(key, ids)

    @classmethod
    def attach_labels(cls, rows: Iterable[Any]) -> None:
        by_key: dict[str, list[Any]] = defaultdict(list)
        for row in rows:
            by_key[row.label_entity_key()].append(row)
        for key, group in by_key.items():
            found = labels_for(key, [r.pk for r in group])
            for row in group:
                row._labels_cache = found.get(row.pk, {})
