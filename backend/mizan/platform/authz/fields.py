"""Field groups at serialisation time: non-granted fields are omitted, never blanked.

Declare a group on a response schema field::

    unit_price: Decimal | None = Field(None, json_schema_extra={"x-field-group": "commercial"})

and declare the Ninja operation with ``exclude_unset=True``; then return
``serialize(obj, Schema, granted)``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from functools import cache
from typing import Any

from ninja import Schema

GROUP_KEY = "x-field-group"


@cache
def field_groups_of(schema: type[Schema]) -> dict[str, str]:
    groups: dict[str, str] = {}
    for name, info in schema.model_fields.items():
        extra = info.json_schema_extra
        if isinstance(extra, Mapping) and GROUP_KEY in extra:
            groups[name] = str(extra[GROUP_KEY])
    return groups


def excluded_fields(schema: type[Schema], granted: Iterable[str]) -> set[str]:
    granted_set = set(granted)
    return {name for name, group in field_groups_of(schema).items() if group not in granted_set}


def serialize(obj: Any, schema: type[Schema], granted: Iterable[str]) -> dict[str, Any]:
    """Validate ``obj`` through ``schema`` and drop fields whose group is not granted."""
    excluded = excluded_fields(schema, granted)
    validated = schema.from_orm(obj) if not isinstance(obj, dict) else schema.model_validate(obj)
    return validated.model_dump(exclude=excluded, exclude_unset=False)


def bind(
    payload: Mapping[str, Any], schema: type[Schema], granted: Iterable[str]
) -> tuple[dict[str, Any], list[str]]:
    """Drop non-granted fields from a request body; returns (data, ignored field names)."""
    excluded = excluded_fields(schema, granted)
    ignored = sorted(name for name in payload if name in excluded)
    data = {k: v for k, v in payload.items() if k not in excluded}
    return data, ignored
