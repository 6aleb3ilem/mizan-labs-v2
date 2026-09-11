"""Recording audit events from every write path."""

from __future__ import annotations

import datetime as dt
import decimal
import uuid
from collections.abc import Iterable
from typing import Any

from django.db import models

from mizan.apps.audit.models import AuditEvent
from mizan.platform import context

Json = dict[str, Any]

SNAPSHOT_EXCLUDED = frozenset(
    {"password", "token_hash", "hashed_key", "row_version", "updated_at", "updated_by"}
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID | decimal.Decimal):
        return str(value)
    if isinstance(value, dt.datetime | dt.date | dt.time):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return value


def snapshot(
    instance: models.Model, *, fields: Iterable[str] | None = None, exclude: Iterable[str] = ()
) -> Json:
    """A JSON-safe copy of the concrete fields of a model instance (secrets excluded)."""
    excluded = SNAPSHOT_EXCLUDED | set(exclude)
    wanted = set(fields) if fields is not None else None
    data: Json = {}
    for f in instance._meta.concrete_fields:
        name = f.attname
        if name in excluded or f.name in excluded:
            continue
        if wanted is not None and f.name not in wanted and name not in wanted:
            continue
        data[name] = _jsonable(getattr(instance, name))
    return data


def diff(before: Json | None, after: Json | None) -> Json:
    """Only the keys whose value changed, as ``{key: [old, new]}``."""
    before = before or {}
    after = after or {}
    changed: Json = {}
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            changed[key] = [before.get(key), after.get(key)]
    return changed


def record(
    aggregate_type: str,
    aggregate_id: uuid.UUID | None,
    action: str,
    *,
    before: Json | None = None,
    after: Json | None = None,
    branch_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    actor: context.Actor | None = None,
    extra: Json | None = None,
) -> AuditEvent:
    actor = actor or context.actor()
    ctx = context.request_context().as_audit_context()
    if context.rls_bypass_active.get():
        ctx["rls_bypass"] = True
    if extra:
        ctx.update(_jsonable(extra))
    return AuditEvent.objects.create(
        tenant_id=tenant_id if tenant_id is not None else context.current_tenant_id.get(),
        branch_id=branch_id,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        action=action,
        actor_id=actor.id,
        actor_type=actor.type,
        before=before,
        after=after,
        context=ctx,
    )


def record_change(
    instance: models.Model, action: str, before: Json | None, **kwargs: Any
) -> AuditEvent:
    """Record an update of ``instance``: stores the previous snapshot and the current one."""
    after = snapshot(instance)
    return record(
        instance._meta.model_name or "", instance.pk, action, before=before, after=after, **kwargs
    )
