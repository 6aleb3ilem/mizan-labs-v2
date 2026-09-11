"""Tenant scope: the request/task transaction with ``app.tenant_id`` set locally.

See ADR 0003. ``tenant_scope`` is the only place that sets ``app.tenant_id``;
``platform_scope`` is the only place that sets the bypass used by platform operators,
login lookups, provisioning and seeds.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from django.db import connections, transaction

from mizan.platform import context

TENANT_SETTING = "app.tenant_id"
BYPASS_SETTING = "app.rls_bypass"
BYPASS_VALUE = "platform"


def _set_local(using: str, name: str, value: str) -> None:
    with connections[using].cursor() as cursor:
        cursor.execute("SELECT set_config(%s, %s, true)", [name, value])


def _current(using: str, name: str) -> str:
    with connections[using].cursor() as cursor:
        cursor.execute("SELECT coalesce(current_setting(%s, true), '')", [name])
        row = cursor.fetchone()
    return str(row[0]) if row else ""


@contextmanager
def tenant_scope(tenant_id: uuid.UUID | str, *, using: str = "default") -> Iterator[None]:
    """Run the block inside a transaction where row-level security sees ``tenant_id``."""
    tenant_uuid = uuid.UUID(str(tenant_id))
    token = context.current_tenant_id.set(tenant_uuid)
    try:
        with transaction.atomic(using=using):
            previous = _current(using, TENANT_SETTING)
            _set_local(using, TENANT_SETTING, str(tenant_uuid))
            yield
            # Successful block: restore the previous value so an enclosing transaction
            # (tests, nested scopes) does not inherit this tenant. On error the savepoint
            # rollback restores the setting by itself.
            if connections[using].in_atomic_block:
                _set_local(using, TENANT_SETTING, previous)
    finally:
        context.current_tenant_id.reset(token)


@contextmanager
def platform_scope(*, using: str = "default") -> Iterator[None]:
    """Run the block with the row-level-security bypass (platform operations only)."""
    token = context.rls_bypass_active.set(True)
    try:
        with transaction.atomic(using=using):
            previous = _current(using, BYPASS_SETTING)
            _set_local(using, BYPASS_SETTING, BYPASS_VALUE)
            yield
            if connections[using].in_atomic_block:
                _set_local(using, BYPASS_SETTING, previous)
    finally:
        context.rls_bypass_active.reset(token)


def active_tenant_setting(using: str = "default") -> str:
    """The tenant id the database currently sees (empty when none). Used by tests."""
    return _current(using, TENANT_SETTING)
