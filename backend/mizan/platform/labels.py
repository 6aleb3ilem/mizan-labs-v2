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


def resolve_label(labels: Labels, locale: str, fallbacks: tuple[str, ...] = ("fr", "en")) -> str:
    if locale in labels:
        return labels[locale]
    for candidate in fallbacks:
        if candidate in labels:
            return labels[candidate]
    return next(iter(labels.values()), "")


class LabelledModel(models.Model):
    """Mixin for configurable entities: ``code`` plus translated labels in ``i18n_text``."""

    label_entity: ClassVar[str] = ""

    class Meta:
        abstract = True

    @property
    def labels(self) -> Labels:
        cached: Labels | None = getattr(self, "_labels_cache", None)
        if cached is None:
            cached = get_labels(self._label_entity(), self.pk)
            self._labels_cache = cached
        return cached

    def set_labels(self, labels: Labels, *, field: str = "label") -> None:
        set_labels(self._label_entity(), self.pk, labels, field=field)
        if field == "label":
            self._labels_cache = {**getattr(self, "_labels_cache", {}), **labels}

    def label(self, locale: str = "fr") -> str:
        return resolve_label(self.labels, locale)

    @classmethod
    def _label_entity(cls) -> str:
        return cls.label_entity or cls._meta.db_table

    @classmethod
    def attach_labels(cls, rows: Iterable[Any]) -> None:
        rows = list(rows)
        found = labels_for(cls._label_entity(), [r.pk for r in rows])
        for row in rows:
            row._labels_cache = found.get(row.pk, {})
